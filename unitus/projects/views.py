from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from skills.models import UserSkill

from .forms import (
    ProjectEditForm,
    ProjectForm,
    ProjectResignForm,
    ProjectRoleEditForm,
    ProjectRoleForm,
    ProjectStateChangeForm,
    RoleSkillFormSet,
    TransferOwnershipForm,
)
from .models import JobAd, Project, ProjectMember, ProjectRole
from .permissions import can_view_workspace, is_active_member, is_project_pm
from .services import sync_job_ad_status_for_role


def home(request):

    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'jobads')

    job_ad_results = None
    user_results = None

    if query:
        if search_type == 'users':
            from accounts.models import User

            user_results = User.objects.filter(
                Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            )[:20]
        else:
            job_ad_results = JobAd.objects.filter(
                status=JobAd.Status.OPEN
            ).filter(
                Q(project__short_description__icontains=query) | Q(project_role__role_description__icontains=query)
            ).select_related('project', 'project_role')[:20]

    suggestions = []
    if request.user.is_authenticated:
        my_skill_ids = UserSkill.objects.filter(user=request.user).values_list('skill_id', flat=True)
        if my_skill_ids:
            suggestions = JobAd.objects.filter(
                status=JobAd.Status.OPEN,
                project_role__projectroleskill__skill_id__in=my_skill_ids,
            ).select_related('project', 'project_role').distinct()[:10]

    return render(request, 'projects/home.html', {
        'query': query,
        'search_type': search_type,
        'job_ad_results': job_ad_results,
        'user_results': user_results,
        'suggestions': suggestions,
    })


def jobad_detail(request, pk):

    job_ad = get_object_or_404(JobAd.objects.select_related('project', 'project_role'), pk=pk)
    return render(request, 'projects/jobad_detail.html', {'job_ad': job_ad})


@login_required
def project_create(request):

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.pm = request.user
            project.save()
            messages.success(request, 'Project created. Now add at least one role.')
            return redirect('project_add_role', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_create.html', {'form': form})


@login_required
def project_add_role(request, pk):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can add roles.')

    role_form = ProjectRoleForm(request.POST or None)
    formset = RoleSkillFormSet(request.POST or None, queryset=RoleSkillFormSet.model.objects.none())

    if request.method == 'POST' and role_form.is_valid() and formset.is_valid():
        role = role_form.save(commit=False)
        role.project = project
        role.save()

        for skill_form in formset:
            if skill_form.cleaned_data and not skill_form.cleaned_data.get('DELETE'):
                role_skill = skill_form.save(commit=False)
                role_skill.role = role
                role_skill.save()

        JobAd.objects.create(project=project, project_role=role, status=JobAd.Status.OPEN)
        messages.success(request, f'Role "{role.role_title}" added and job ad published.')
        return redirect('project_add_role', pk=project.pk)

    existing_roles = project.projectrole_set.select_related('jobad').all()
    return render(request, 'projects/project_add_role.html', {
        'project': project,
        'role_form': role_form,
        'formset': formset,
        'existing_roles': existing_roles,
    })


@login_required
def project_workspace(request, pk):

    project = get_object_or_404(Project, pk=pk)
    if not can_view_workspace(request.user, project):
        raise PermissionDenied("You don't have access to this project's workspace.")

    # filled_count: active ProjectMember rows currently on that role, so the
    # template can show "X/Y filled" without doing its own DB queries.
    roles = project.projectrole_set.prefetch_related(
        'projectroleskill_set__skill'
    ).annotate(
        filled_count=Count(
            'projectmember',
            filter=Q(projectmember__member_status=ProjectMember.MemberStatus.ACTIVE),
        )
    ).all()

    members = project.projectmember_set.filter(
        member_status=ProjectMember.MemberStatus.ACTIVE
    ).select_related('user', 'project_role')

    # The PM is enrolled as a ProjectMember too (see signals.py), but may or
    # may not have a technical ProjectRole assigned — surface that
    # separately since the workspace page shows it next to "Owner".
    owner_membership = next(
        (m for m in members if m.user_id == project.pm_id), None
    )
    owner_role_title = (
        owner_membership.project_role.role_title
        if owner_membership and owner_membership.project_role
        else None
    )

    return render(request, 'projects/project_workspace.html', {
        'project': project,
        'roles': roles,
        'members': members,
        'is_pm': is_project_pm(request.user, project),
        'is_member': is_active_member(request.user, project),
        'owner_role_title': owner_role_title,
    })


@login_required
def project_state_change(request, pk):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can change project state.')

    if request.method == 'POST':
        old_state = project.state
        form = ProjectStateChangeForm(request.POST, instance=project)
        if form.is_valid():
            updated_project = form.save()
            if old_state == Project.State.RECRUITING and updated_project.state != Project.State.RECRUITING:
                JobAd.objects.filter(project=updated_project, status=JobAd.Status.OPEN).update(
                    status=JobAd.Status.CANCELLED
                )
            messages.success(request, 'Project status updated.')
            return redirect('project_workspace', pk=project.pk)
    else:
        form = ProjectStateChangeForm(instance=project)
    return render(request, 'projects/project_state_change.html', {'project': project, 'form': form})


@login_required
def project_remove_member(request, pk, member_id):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can remove members.')

    member = get_object_or_404(ProjectMember, pk=member_id, project=project)

    if request.method == 'POST':
        member.member_status = ProjectMember.MemberStatus.REMOVED
        member.save(update_fields=['member_status'])
        if member.project_role:
            sync_job_ad_status_for_role(member.project_role)
        messages.success(request, f'{member.user.username} has been removed from the project.')
        return redirect('project_workspace', pk=project.pk)

    return render(request, 'projects/project_remove_member_confirm.html', {
        'project': project, 'member': member,
    })


@login_required
def project_transfer_ownership(request, pk):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the current project manager can transfer ownership.')

    from accounts.models import User

    candidate_ids = ProjectMember.objects.filter(
        project=project, member_status=ProjectMember.MemberStatus.ACTIVE
    ).exclude(user=project.pm).values_list('user_id', flat=True)
    candidates = User.objects.filter(id__in=candidate_ids)

    if not candidates.exists():
        messages.error(request, 'There are no active members to transfer ownership to.')
        return redirect('project_workspace', pk=project.pk)

    if request.method == 'POST':
        form = TransferOwnershipForm(request.POST, candidate_users=candidates)
        if form.is_valid():
            new_owner = form.cleaned_data['new_owner']
            old_pm = project.pm
            project.pm = new_owner
            project.save(update_fields=['pm'])
            ProjectMember.objects.get_or_create(
                project=project, user=old_pm,
                defaults={'member_status': ProjectMember.MemberStatus.ACTIVE},
            )
            messages.success(request, f'Ownership transferred to {new_owner.username}.')
            return redirect('project_workspace', pk=project.pk)
    else:
        form = TransferOwnershipForm(candidate_users=candidates)

    return render(request, 'projects/project_transfer_ownership.html', {'project': project, 'form': form})


@login_required
def project_edit(request, pk):
    """PM edits basic project details (SRS 3.4)."""
    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can edit the project details.')

    if request.method == 'POST':
        form = ProjectEditForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project details updated successfully.')
            return redirect('project_workspace', pk=project.pk)
    else:
        form = ProjectEditForm(instance=project)

    return render(request, 'projects/project_edit.html', {'project': project, 'form': form})


@login_required
def project_delete(request, pk):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can delete this project.')

    if request.method == 'POST':
        project.delete()
        messages.success(request, 'Project deleted successfully.')
        return redirect('accounts:dashboard')

    return render(request, 'projects/project_delete_confirm.html', {'project': project})


@login_required
def project_edit_role(request, pk, role_id):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can edit roles.')

    role = get_object_or_404(ProjectRole, pk=role_id, project=project)

    role_form = ProjectRoleEditForm(request.POST or None, instance=role)
    formset = RoleSkillFormSet(request.POST or None, queryset=role.projectroleskill_set.all())

    if request.method == 'POST' and role_form.is_valid() and formset.is_valid():
        role_form.save()

        skills = formset.save(commit=False)
        for skill in skills:
            skill.role = role
            skill.save()

        for obj in formset.deleted_objects:
            obj.delete()

        sync_job_ad_status_for_role(role)
        messages.success(request, f'Role "{role.role_title}" updated successfully.')
        return redirect('project_workspace', pk=project.pk)

    return render(request, 'projects/project_edit_role.html', {
        'project': project,
        'role': role,
        'role_form': role_form,
        'formset': formset,
    })


@login_required
def project_delete_role(request, pk, role_id):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can delete roles.')

    role = get_object_or_404(ProjectRole, pk=role_id, project=project)

    if request.method == 'POST':
        JobAd.objects.filter(project_role=role, status=JobAd.Status.OPEN).update(status=JobAd.Status.CANCELLED)
        role.delete()
        messages.success(request, 'Role deleted successfully.')
        return redirect('project_workspace', pk=project.pk)

    return render(request, 'projects/project_delete_role_confirm.html', {'project': project, 'role': role})


@login_required
def project_resign(request, pk):

    project = get_object_or_404(Project, pk=pk)

    if is_project_pm(request.user, project):
        messages.error(request, 'Project Managers cannot resign. Transfer ownership first.')
        return redirect('project_workspace', pk=project.pk)

    member = ProjectMember.objects.filter(
        project=project, user=request.user, member_status=ProjectMember.MemberStatus.ACTIVE
    ).first()

    if not member:
        raise PermissionDenied('You are not an active member of this project.')

    if request.method == 'POST':
        form = ProjectResignForm(request.POST)
        if form.is_valid():
            member.member_status = ProjectMember.MemberStatus.RESIGNED
            member.save(update_fields=['member_status'])

            if member.project_role:
                sync_job_ad_status_for_role(member.project_role)

            messages.success(request, 'You have resigned from the project.')
            return redirect('accounts:dashboard')
    else:
        form = ProjectResignForm()

    return render(request, 'projects/project_resign.html', {'project': project, 'form': form})