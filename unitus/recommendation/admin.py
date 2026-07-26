from django.contrib import admin

from .models import EmbeddingCache, RecommendationFeedback, RecommendationPreference


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'recommendation_type', 'target_id', 'vote', 'updated_at')
    list_filter = ('recommendation_type', 'vote')
    search_fields = ('user__username',)


@admin.register(RecommendationPreference)
class RecommendationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'min_match_score', 'updated_at')
    search_fields = ('user__username',)
    autocomplete_fields = ['excluded_categories']


@admin.register(EmbeddingCache)
class EmbeddingCacheAdmin(admin.ModelAdmin):
    list_display = ('object_type', 'object_id', 'is_query', 'updated_at')
    list_filter = ('object_type', 'is_query')
    readonly_fields = ('text_hash', 'vector', 'updated_at')
