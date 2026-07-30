# unitus/recommendation/services.py

import hashlib

import numpy as np

from accounts.models import User
from projects.models import JobAd, ProjectRoleSkill
from skills.models import UserSkill
from recommendation.embedder import TextEmbedder
from recommendation.models import EmbeddingCache, RecommendationFeedback, RecommendationPreference
from recommendation.ranker import Ranker
from recommendation.skill_matching import score_against_requirements
from recommendation.text_formatter import get_embedding_text

# Singleton Embedder جهت جلوگیری از Re-load شدن متوالی مدل در حافظه
_EMBEDDER_INSTANCE = None

def get_embedder():
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        _EMBEDDER_INSTANCE = TextEmbedder()
    return _EMBEDDER_INSTANCE


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _required_skills_for_role_ids(role_ids):
    """
    role_id -> [(skill_id, min_required_level_display_label), ...] for every
    role in role_ids, fetched in one query instead of one per role.
    """
    required = {}
    skill_rows = ProjectRoleSkill.objects.filter(role_id__in=role_ids).select_related("skill")
    for row in skill_rows:
        required.setdefault(row.role_id, []).append(
            (row.skill_id, row.get_min_required_level_display())
        )
    return required


def _skill_levels_for_user_ids(user_ids):
    """
    user_id -> {skill_id: mastery_level_display_label} for every user in
    user_ids, fetched in one query instead of one per user.
    """
    levels = {}
    skill_rows = UserSkill.objects.filter(user_id__in=user_ids).select_related("skill")
    for row in skill_rows:
        levels.setdefault(row.user_id, {})[row.skill_id] = row.get_mastery_level_display()
    return levels


class MatchScoreService:

    def __init__(self):
        self.embedder = get_embedder()
        self.ranker = Ranker()

    def _get_embedding(self, obj, object_type: str, is_query: bool):
        """
        Returns the embedding vector for obj, reusing a cached vector when
        the object's embedding text hasn't changed since it was last
        computed. Only calls the (expensive) model when the cache is empty
        or stale.
        """
        text = get_embedding_text(obj)
        text_hash = _hash_text(text)

        cached = EmbeddingCache.objects.filter(
            object_type=object_type, object_id=obj.id, is_query=is_query,
        ).first()

        if cached is not None and cached.text_hash == text_hash:
            return np.array(cached.vector, dtype=np.float32)

        vector = self.embedder.embed(text, is_query=is_query)

        EmbeddingCache.objects.update_or_create(
            object_type=object_type, object_id=obj.id, is_query=is_query,
            defaults={"text_hash": text_hash, "vector": np.asarray(vector).tolist()},
        )
        return vector

    def recommend_ads_for_user(self, user: User, top_k: int = 10):
        """
        Calculates match scores between a User and all active Job Ads (OPEN),
        honoring the user's own recommendation preferences and hiding ads
        they've already downvoted. Each ad's score blends embedding
        similarity with how well the user's own skills satisfy that ad's
        required skills (see skill_matching.py / Ranker).
        """
        user_vec = self._get_embedding(user, EmbeddingCache.ObjectType.USER, is_query=True)

        open_ads = JobAd.objects.filter(status=JobAd.Status.OPEN).select_related('project', 'project_role')

        preferences = RecommendationPreference.objects.filter(user=user).first()
        min_score = preferences.min_match_score if preferences else 0.0
        excluded_category_ids = (
            set(preferences.excluded_categories.values_list("id", flat=True)) if preferences else set()
        )
        if excluded_category_ids:
            open_ads = open_ads.exclude(
                project_role__projectroleskill__skill__category_id__in=excluded_category_ids
            ).distinct()

        downvoted_ad_ids = set(
            RecommendationFeedback.objects.filter(
                user=user,
                recommendation_type=RecommendationFeedback.RecommendationType.AD,
                vote=RecommendationFeedback.Vote.DOWN,
            ).values_list("target_id", flat=True)
        )
        if downvoted_ad_ids:
            open_ads = open_ads.exclude(id__in=downvoted_ad_ids)

        if not open_ads.exists():
            return []

        open_ads = list(open_ads)

        # One user, so their own skill levels only need fetching once.
        user_skill_levels = _skill_levels_for_user_ids([user.id]).get(user.id, {})
        required_skills_by_role = _required_skills_for_role_ids(
            [ad.project_role_id for ad in open_ads]
        )

        candidates = []
        for ad in open_ads:
            embedding = self._get_embedding(ad, EmbeddingCache.ObjectType.JOB_AD, is_query=False)
            required_skills = required_skills_by_role.get(ad.project_role_id, [])
            skill_score = score_against_requirements(user_skill_levels, required_skills)
            candidates.append((ad.id, embedding, skill_score))

        ranked_results = self.ranker.rank(user_vec, candidates, top_k=top_k)

        # Mapping back to JobAd objects with match score
        ad_dict = {ad.id: ad for ad in open_ads}
        results = []
        for ad_id, score in ranked_results:
            if score < min_score:
                continue
            ad = ad_dict[ad_id]
            results.append({
                "ad": ad,
                "score": round(score, 4)
            })

        return results

    def recommend_candidates_for_ad(self, job_ad: JobAd, requesting_user: User, top_k: int = 10):
        """
        Calculates match scores between a Job Ad and open-to-work Users,
        honoring the requesting PM's own min-score preference and hiding
        candidates they've already downvoted for this ad. Each candidate's
        score blends embedding similarity with how well their own skills
        satisfy this ad's required skills (see skill_matching.py / Ranker).
        """
        ad_vec = self._get_embedding(job_ad, EmbeddingCache.ObjectType.JOB_AD, is_query=True)

        open_users = User.objects.filter(
            is_open_to_work=True,
            account_status=User.AccountStatus.ACTIVE
        )

        downvoted_user_ids = set(
            RecommendationFeedback.objects.filter(
                user=requesting_user,
                recommendation_type=RecommendationFeedback.RecommendationType.CANDIDATE,
                vote=RecommendationFeedback.Vote.DOWN,
            ).values_list("target_id", flat=True)
        )
        if downvoted_user_ids:
            open_users = open_users.exclude(id__in=downvoted_user_ids)

        preferences = RecommendationPreference.objects.filter(user=requesting_user).first()
        min_score = preferences.min_match_score if preferences else 0.0

        if not open_users.exists():
            return []

        open_users = list(open_users)

        # One ad, so its required skills only need fetching once.
        required_skills = _required_skills_for_role_ids(
            [job_ad.project_role_id]
        ).get(job_ad.project_role_id, [])
        user_skill_levels_by_user = _skill_levels_for_user_ids(
            [user.id for user in open_users]
        )

        candidates = []
        for user in open_users:
            embedding = self._get_embedding(user, EmbeddingCache.ObjectType.USER, is_query=False)
            candidate_skill_levels = user_skill_levels_by_user.get(user.id, {})
            skill_score = score_against_requirements(candidate_skill_levels, required_skills)
            candidates.append((user.id, embedding, skill_score))

        ranked_results = self.ranker.rank(ad_vec, candidates, top_k=top_k)

        user_dict = {u.id: u for u in open_users}
        results = []
        for user_id, score in ranked_results:
            if score < min_score:
                continue
            user = user_dict[user_id]
            results.append({
                "user": user,
                "score": round(score, 4)
            })

        return results
