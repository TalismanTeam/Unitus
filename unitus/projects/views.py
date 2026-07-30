from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from moderation.audit import log_action
from skills.models import UserSkill
from reviews.models import Review

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


@login_required
def projects_hub(request):
    return render(request, 'projects/hub.html')


def browse(request):
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
            log_action(
                entity_type='Project',
                entity_id=project.pk,
                action='CREATE',
                performed_by=request.user,
                details=f'Created project "{project.title}"',
            )
            messages.success(request, 'Project created. Now add at least one role.')
            return redirect('projects:project_add_role', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_create.html', {'form': form})


@login_required
def project_add_role(request, pk):

    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can add roles.')

    pm_membership, _ = ProjectMember.objects.get_or_create(
        project=project, user=project.pm,
        defaults={'member_status': ProjectMember.MemberStatus.ACTIVE},
    )
    pm_already_has_role = pm_membership.project_role_id is not None

    role_form = ProjectRoleForm(request.POST or None)
    formset = RoleSkillFormSet(request.POST or None, queryset=RoleSkillFormSet.model.objects.none())

    if request.method == 'POST' and role_form.is_valid() and formset.is_valid():
        wants_owner_role = role_form.cleaned_data.get('is_owner_role', False)

        if wants_owner_role and pm_already_has_role:
            role_form.add_error(
                None, 'You already have a role on this project. Remove it first if you want to reassign yourself.'
            )
        else:
            role = role_form.save(commit=False)
            role.project = project
            role.save()

            for skill_form in formset:
                if skill_form.cleaned_data and not skill_form.cleaned_data.get('DELETE'):
                    role_skill = skill_form.save(commit=False)
                    role_skill.role = role
                    role_skill.save()

            job_ad = JobAd.objects.create(project=project, project_role=role, status=JobAd.Status.OPEN)

            log_action(
                entity_type='ProjectRole',
                entity_id=role.pk,
                action='CREATE',
                performed_by=request.user,
                details=f'Added role "{role.role_title}" to project "{project.title}"',
            )
            log_action(
                entity_type='JobAd',
                entity_id=job_ad.pk,
                action='CREATE',
                performed_by=request.user,
                details=f'Job ad published for role "{role.role_title}" on "{project.title}"',
            )

            if wants_owner_role:
                pm_membership.project_role = role
                pm_membership.save(update_fields=['project_role'])
                sync_job_ad_status_for_role(role)
                messages.success(request, f'Role "{role.role_title}" added and assigned to you.')
            else:
                messages.success(request, f'Role "{role.role_title}" added and job ad published.')

            return redirect('projects:project_add_role', pk=project.pk)

    existing_roles = project.projectrole_set.select_related('jobad').all()
    return render(request, 'projects/project_add_role.html', {
        'project': project,
        'role_form': role_form,
        'formset': formset,
        'existing_roles': existing_roles,
        'pm_already_has_role': pm_already_has_role,
    })


@login_required
def project_workspace(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_view_workspace(request.user, project):
        raise PermissionDenied("You don't have access to this project's workspace.")

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

    owner_membership = next(
        (m for m in members if m.user_id == project.pm_id), None
    )
    owner_role_title = (
        owner_membership.project_role.role_title
        if owner_membership and owner_membership.project_role
        else None
    )

    can_leave_reviews = (
        project.state == Project.State.TERMINATED
        and project.termination_reason == Project.TerminationReason.SUCCESS
        and ProjectMember.objects.filter(project=project, user=request.user).exists()
    )

    reviewable_members = []
    if can_leave_reviews:
        already_reviewed_ids = set(
            Review.objects.filter(reviewer=request.user, project=project)
            .values_list('reviewee_id', flat=True)
        )
        teammates = ProjectMember.objects.filter(project=project).exclude(
            user=request.user
        ).select_related('user', 'project_role')

        for m in teammates:
            if m.project_role:
                role_title = m.project_role.role_title
            elif m.user_id == project.pm_id:
                role_title = 'Project Manager'
            else:
                role_title = 'Unassigned Role'

            reviewable_members.append({
                'user_id': m.user_id,
                'username': m.user.username,
                'role_title': role_title,
                'already_reviewed': m.user_id in already_reviewed_ids,
            })

    return render(request, 'projects/project_workspace.html', {
        'project': project,
        'roles': roles,
        'members': members,
        'is_pm': is_project_pm(request.user, project),
        'is_member': is_active_member(request.user, project),
        'owner_role_title': owner_role_title,
        'can_leave_reviews': can_leave_reviews,
        'reviewable_members': reviewable_members,
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
            details = f'State changed from {old_state} to {updated_project.state}'
            if updated_project.termination_reason:
                details += f' (reason: {updated_project.termination_reason})'
            log_action(
                entity_type='Project',
                entity_id=updated_project.pk,
                action='STATUS_CHANGE',
                performed_by=request.user,
                details=details,
            )
            messages.success(request, 'Project status updated.')
            return redirect('projects:project_workspace', pk=project.pk)
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
        log_action(
            entity_type='ProjectMember',
            entity_id=member.pk,
            action='STATUS_CHANGE',
            performed_by=request.user,
            details=f'Removed {member.user.username} from project "{project.title}"',
        )
        messages.success(request, f'{member.user.username} has been removed from the project.')
        return redirect('projects:project_workspace', pk=project.pk)

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
        return redirect('projects:project_workspace', pk=project.pk)

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
            log_action(
                entity_type='Project',
                entity_id=project.pk,
                action='UPDATE',
                performed_by=request.user,
                details=f'Ownership transferred from {old_pm.username} to {new_owner.username}',
            )
            messages.success(request, f'Ownership transferred to {new_owner.username}.')
            return redirect('projects:project_workspace', pk=project.pk)
    else:
        form = TransferOwnershipForm(candidate_users=candidates)

    return render(request, 'projects/project_transfer_ownership.html', {'project': project, 'form': form})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can edit the project details.')

    if request.method == 'POST':
        form = ProjectEditForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_action(
                entity_type='Project',
                entity_id=project.pk,
                action='UPDATE',
                performed_by=request.user,
                details=f'Edited details for project "{project.title}"',
            )
            messages.success(request, 'Project details updated successfully.')
            return redirect('projects:project_workspace', pk=project.pk)
    else:
        form = ProjectEditForm(instance=project)

    return render(request, 'projects/project_edit.html', {'project': project, 'form': form})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not is_project_pm(request.user, project):
        raise PermissionDenied('Only the project manager can delete this project.')

    if request.method == 'POST':
        project_id, project_title = project.pk, project.title
        project.delete()
        log_action(
            entity_type='Project',
            entity_id=project_id,
            action='DELETE',
            performed_by=request.user,
            details=f'Deleted project "{project_title}"',
        )
        messages.success(request, 'Project deleted successfully.')
        return redirect('accounts:my-projects')

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
        log_action(
            entity_type='ProjectRole',
            entity_id=role.pk,
            action='UPDATE',
            performed_by=request.user,
            details=f'Edited role "{role.role_title}" on project "{project.title}"',
        )
        messages.success(request, f'Role "{role.role_title}" updated successfully.')
        return redirect('projects:project_workspace', pk=project.pk)

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
        role_id, role_title = role.pk, role.role_title
        role.delete()
        log_action(
            entity_type='ProjectRole',
            entity_id=role_id,
            action='DELETE',
            performed_by=request.user,
            details=f'Deleted role "{role_title}" from project "{project.title}"',
        )
        messages.success(request, 'Role deleted successfully.')
        return redirect('projects:project_workspace', pk=project.pk)

    return render(request, 'projects/project_delete_role_confirm.html', {'project': project, 'role': role})


@login_required
def project_resign(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if is_project_pm(request.user, project):
        messages.error(request, 'Project Managers cannot resign. Transfer ownership first.')
        return redirect('projects:project_workspace', pk=project.pk)

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

            log_action(
                entity_type='ProjectMember',
                entity_id=member.pk,
                action='STATUS_CHANGE',
                performed_by=request.user,
                details=f'{request.user.username} resigned from project "{project.title}"',
            )

            messages.success(request, 'You have resigned from the project.')
            return redirect('accounts:my-projects')
    else:
        form = ProjectResignForm()

    return render(request, 'projects/project_resign.html', {'project': project, 'form': form})