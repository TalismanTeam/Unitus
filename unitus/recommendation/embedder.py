from sentence_transformers import SentenceTransformer

class TextEmbedder:

    def __init__(self, model_name="intfloat/multilingual-e5-small"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str):

        return self.model.encode(
            f"passage: {text}",
            normalize_embeddings=True
        )