from django.contrib import admin
from .models import SkillCategory, Skill, UserSkill


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name',)
    search_fields = ('category_name',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_custom', 'is_approved', 'created_by')
    list_filter = ('category', 'is_custom', 'is_approved')
    search_fields = ('name',)
    autocomplete_fields = ['created_by']
    actions = ['approve_skills']

    @admin.action(description='Approve selected custom skills')
    def approve_skills(self, request, queryset):
        updated = queryset.filter(is_approved=False).update(is_approved=True)
        self.message_user(request, f'{updated} skill(s) approved.')


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'mastery_level')
    list_filter = ('mastery_level', 'skill__category')
    search_fields = ('user__username', 'skill__name')
