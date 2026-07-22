from recommendation.similarity import Similarity


class Ranker:

    def __init__(self):
        self.similarity = Similarity()

    def rank(self, query_embedding, candidates, top_k=10):

        scores = []

        for candidate_id, embedding in candidates:
            score = self.similarity.cosine_similarity(query_embedding, embedding)
            scores.append((candidate_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]