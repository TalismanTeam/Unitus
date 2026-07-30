from recommendation.similarity import Similarity


class Ranker:

    def __init__(self, semantic_weight: float = 0.6):
        """
        semantic_weight controls the blend between embedding similarity and
        the skill-overlap score (see skill_matching.py):

            final_score = semantic_weight * cosine_similarity
                         + (1 - semantic_weight) * skill_score

        0.6 leans toward semantic similarity (so role/project description
        text still matters) while still letting a candidate's literal skill
        match meaningfully move their rank. Tune based on what you see in
        practice - push it down toward e.g. 0.4 if under-qualified profiles
        are still ranking too high, push it up if good semantic matches with
        slightly thin skill data are getting buried.
        """
        self.similarity = Similarity()
        self.semantic_weight = semantic_weight

    def rank(self, query_embedding, candidates, top_k=10):
        """
        candidates: list of (candidate_id, embedding, skill_score) tuples.

        skill_score is a 0..1 float from
        skill_matching.score_against_requirements(), or None if there's
        nothing to score skills against - in which case that candidate
        falls back to pure semantic similarity rather than being penalized
        for missing data.

        Returns [(candidate_id, blended_score), ...] sorted descending,
        truncated to top_k - same shape callers already expect.
        """
        scores = []

        for candidate_id, embedding, skill_score in candidates:
            semantic_score = self.similarity.cosine_similarity(query_embedding, embedding)

            if skill_score is None:
                blended_score = semantic_score
            else:
                blended_score = (
                    self.semantic_weight * semantic_score
                    + (1 - self.semantic_weight) * skill_score
                )

            scores.append((candidate_id, blended_score))

        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]
