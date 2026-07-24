# unitus/recommendation/services.py

from accounts.models import User
from projects.models import JobAd
from recommendation.embedder import TextEmbedder
from recommendation.ranker import Ranker
from recommendation.text_formatter import get_embedding_text

# Singleton Embedder جهت جلوگیری از Re-load شدن متوالی مدل در حافظه
_EMBEDDER_INSTANCE = None

def get_embedder():
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        _EMBEDDER_INSTANCE = TextEmbedder()
    return _EMBEDDER_INSTANCE


class MatchScoreService:

    def __init__(self):
        self.embedder = get_embedder()
        self.ranker = Ranker()

    def recommend_ads_for_user(self, user: User, top_k: int = 10):
        """
        Calculates match scores between a User and all active Job Ads (OPEN).
        """
        user_text = get_embedding_text(user)
        user_vec = self.embedder.embed(user_text, is_query=True)

        open_ads = JobAd.objects.filter(status=JobAd.Status.OPEN).select_related('project', 'project_role')
        if not open_ads.exists():
            return []

        candidates = []
        for ad in open_ads:
            ad_text = get_embedding_text(ad)
            ad_vec = self.embedder.embed(ad_text, is_query=False)
            candidates.append((ad.id, ad_vec))

        ranked_results = self.ranker.rank(user_vec, candidates, top_k=top_k)
        
        # Mapping back to JobAd objects with match score
        ad_dict = {ad.id: ad for ad in open_ads}
        results = []
        for ad_id, score in ranked_results:
            ad = ad_dict[ad_id]
            results.append({
                "ad": ad,
                "score": round(score, 4)
            })

        return results

    def recommend_candidates_for_ad(self, job_ad: JobAd, top_k: int = 10):
        """
        Calculates match scores between a Job Ad and open-to-work Users.
        """
        ad_text = get_embedding_text(job_ad)
        ad_vec = self.embedder.embed(ad_text, is_query=True)

        open_users = User.objects.filter(
            is_open_to_work=True,
            account_status=User.AccountStatus.ACTIVE
        )
        if not open_users.exists():
            return []

        candidates = []
        for user in open_users:
            user_text = get_embedding_text(user)
            user_vec = self.embedder.embed(user_text, is_query=False)
            candidates.append((user.id, user_vec))

        ranked_results = self.ranker.rank(ad_vec, candidates, top_k=top_k)

        user_dict = {u.id: u for u in open_users}
        results = []
        for user_id, score in ranked_results:
            user = user_dict[user_id]
            results.append({
                "user": user,
                "score": round(score, 4)
            })

        return results