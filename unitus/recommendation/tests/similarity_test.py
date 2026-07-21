from recommendation.embedder import TextEmbedder
from recommendation.similarity import Similarity

embedder = TextEmbedder()

profile1 = """
من توسعه‌دهنده پایتون هستم.
به یادگیری ماشین علاقه دارم.
"""

profile2 = """
هستمpython developer 
به هوش مصنوعی علاقه دارم.
"""

profile3 = """
تست برنامه
"""

e1 = embedder.embed(profile1)
e2 = embedder.embed(profile2)
e3 = embedder.embed(profile3)

print("Profile 1 vs Profile 2:")
print(Similarity.cosine_similarity(e1, e2))

print()

print("Profile 1 vs Profile 3:")
print(Similarity.cosine_similarity(e1, e3))