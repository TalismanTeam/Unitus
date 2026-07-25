from unittest.mock import patch

import numpy as np
from django.test import TestCase

from accounts.models import User
from recommendation.models import EmbeddingCache
from recommendation.services import MatchScoreService


class FakeEmbedder:
    """Deterministic stand-in for TextEmbedder - same text always produces
    the same vector, without loading a real sentence-transformer model."""

    def __init__(self):
        self.call_count = 0

    def embed(self, text, is_query=False):
        self.call_count += 1
        return np.array([len(text) % 7, 1.0 if is_query else 0.0], dtype=np.float32)


class EmbeddingCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cache_user', email='cache@example.com', password='pass12345',
            birth_year=1995, about_me='I build things.',
        )
        self.fake_embedder = FakeEmbedder()
        patcher = patch('recommendation.services.get_embedder', return_value=self.fake_embedder)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.service = MatchScoreService()

    def test_first_call_computes_and_stores_embedding(self):
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=True)
        self.assertEqual(self.fake_embedder.call_count, 1)
        self.assertEqual(EmbeddingCache.objects.count(), 1)

    def test_second_call_with_unchanged_text_reuses_cache(self):
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=True)
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=True)
        self.assertEqual(self.fake_embedder.call_count, 1)

    def test_changed_profile_invalidates_cache(self):
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=True)
        self.user.about_me = 'I build very different things now.'
        self.user.save()
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=True)
        self.assertEqual(self.fake_embedder.call_count, 2)
        self.assertEqual(EmbeddingCache.objects.count(), 1)  # updated in place, not duplicated

    def test_query_and_passage_directions_are_cached_separately(self):
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=True)
        self.service._get_embedding(self.user, EmbeddingCache.ObjectType.USER, is_query=False)
        self.assertEqual(self.fake_embedder.call_count, 2)
        self.assertEqual(EmbeddingCache.objects.count(), 2)
