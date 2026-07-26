# unitus/recommendation/embedder.py

from sentence_transformers import SentenceTransformer


class TextEmbedder:

    def __init__(self, model_name="intfloat/multilingual-e5-small"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str, is_query: bool = False):
        prefix = "query: " if is_query else "passage: "
        return self.model.encode(
            f"{prefix}{text}",
            normalize_embeddings=True
        )