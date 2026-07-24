from recommendation.embedder import TextEmbedder

embedder = TextEmbedder()

text = """
من توسعه‌دهنده بک‌اند هستم.
به پایتون و یادگیری ماشین علاقه دارم.
به دنبال یک توسعه‌دهنده فرانت‌اند برای یک پروژه استارتاپی هستم.
"""

embedding = embedder.embed(text)

print("Embedding generated successfully!")
print(f"Shape: {embedding.shape}")
print(f"First 10 values:\n{embedding[:10]}")