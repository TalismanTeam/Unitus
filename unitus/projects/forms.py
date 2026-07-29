from django import forms
from django.forms import BaseModelFormSet, modelformset_factory
from django.forms import modelformset_factory
from skills.models import Skill

from .models import Project, ProjectRole, ProjectRoleSkill


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ['title', 'short_description', 'full_description', 'duration_days']
        widgets = {
            'short_description': forms.TextInput(attrs={'maxlength': 255}),
            'full_description': forms.Textarea(attrs={'rows': 5}),
        }


class ProjectRoleForm(forms.ModelForm):
    """Step 2: one role at a time. Project is set in the view."""

    is_owner_role = forms.BooleanField(
        required=False,
        label="This is the project owner's own role",
        help_text="Check this only if YOU (the PM) will personally fill this role. "
                  "Leave unchecked to publish it as an open job ad.",
    )

    class Meta:
        model = ProjectRole
        fields = ['role_title', 'role_description', 'capacity']
        widgets = {
            'role_description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data['capacity']
        if capacity < 1:
            raise forms.ValidationError('Capacity must be at least 1.')
        return capacity

class ProjectRoleSkillForm(forms.ModelForm):
    """Restricts skill choices to the pre-approved catalog (seed data from
    skills/migrations/0002_seed_categories_and_skills.py). PM can't type an
    arbitrary skill name here — only pick from what's already in the DB."""

    class Meta:
        model = ProjectRoleSkill
        fields = ['skill', 'min_required_level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['skill'].queryset = Skill.objects.filter(
            is_approved=True
        ).select_related('category').order_by('category__category_name', 'name')


class BaseRoleSkillFormSet(BaseModelFormSet):
    """
    Rejects duplicate skill selections across the rows of one submission.
    Without this, two rows picking the same skill both pass per-form
    validation and only fail when saved, as a raw IntegrityError from the
    (role, skill) unique constraint on ProjectRoleSkill.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        seen_skills = set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cleaned_data = form.cleaned_data
            if not cleaned_data or cleaned_data.get('DELETE'):
                continue

            skill = cleaned_data.get('skill')
            if skill is None:
                continue

            if skill in seen_skills:
                raise forms.ValidationError(
                    f'"{skill.name}" is selected more than once — each skill can only be added once per role.'
                )
            seen_skills.add(skill)


RoleSkillFormSet = modelformset_factory(
    ProjectRoleSkill,
    form=ProjectRoleSkillForm,
    extra=0,
    can_delete=True,
    formset=BaseRoleSkillFormSet,
)


class ProjectStateChangeForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['state', 'termination_reason']

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get('state')
        reason = cleaned_data.get('termination_reason')
        if state == Project.State.TERMINATED and not reason:
            raise forms.ValidationError('You must specify a termination reason when ending a project.')
        if state != Project.State.TERMINATED:
            cleaned_data['termination_reason'] = None
        return cleaned_data


class TransferOwnershipForm(forms.Form):
    """Step 2 of ownership transfer: pick the new PM + an explicit warning acknowledgement."""

    new_owner = forms.ModelChoiceField(queryset=None, label='New Project Manager')
    confirm = forms.BooleanField(
        required=True,
        label='I understand this is permanent - I will lose Project Manager privileges immediately.',
    )

    def __init__(self, *args, candidate_users=None, **kwargs):
        super().__init__(*args, **kwargs)
        if candidate_users is not None:
            self.fields['new_owner'].queryset = candidate_users


class ProjectEditForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ['title', 'short_description', 'full_description', 'duration_days']
        widgets = {
            'short_description': forms.TextInput(attrs={'maxlength': 255}),
            'full_description': forms.Textarea(attrs={'rows': 5}),
        }


class ProjectRoleEditForm(forms.ModelForm):

    class Meta:
        model = ProjectRole
        fields = ['role_title', 'role_description', 'capacity']
        widgets = {
            'role_description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data['capacity']
        if capacity < 1:
            raise forms.ValidationError('Capacity must be at least 1.')
        return capacity


class ProjectResignForm(forms.Form):

    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Please state your reason for resigning...'}),
        label='Resignation Reason',
        required=True,
    )
