# Recommendation Module

This module contains the machine learning components of the recommendation system. It is responsible for generating semantic embeddings, computing similarity scores, and ranking users or projects based on their relevance.

---

## Current Features

- Text embedding using `intfloat/multilingual-e5-small`
- Cosine similarity between embeddings
- Generic ranking engine
- Unit tests for each component

---

## Model

Current embedding model:

- `intfloat/multilingual-e5-small`

Reasons for choosing this model:

- Supports both Persian and English
- Lightweight and fast
- Designed for semantic retrieval tasks

---

## Running the Tests

From the project root:

```bash
python -m recommendation.tests.embedder_test
python -m recommendation.tests.similarity_test
python -m recommendation.tests.ranker_test
```

---
