from django.contrib import admin
from .models import Project, ProjectRole, ProjectRoleSkill, JobAd, ProjectMember


class ProjectRoleSkillInline(admin.TabularInline):
    model = ProjectRoleSkill
    extra = 1


class ProjectRoleInline(admin.TabularInline):
    model = ProjectRole
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'pm', 'state', 'created_at')
    list_filter = ('state',)
    search_fields = ('title', 'short_description')
    inlines = [ProjectRoleInline]


@admin.register(ProjectRole)
class ProjectRoleAdmin(admin.ModelAdmin):
    list_display = ('role_title', 'project', 'capacity')
    inlines = [ProjectRoleSkillInline]


@admin.register(JobAd)
class JobAdAdmin(admin.ModelAdmin):
    list_display = ('project', 'project_role', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'project_role', 'member_status', 'joined_at')
    list_filter = ('member_status',)
