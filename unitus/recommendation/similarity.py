import numpy as np


class Similarity:

    @staticmethod
    def cosine_similarity(vec1, vec2):
        return float(np.dot(vec1, vec2))