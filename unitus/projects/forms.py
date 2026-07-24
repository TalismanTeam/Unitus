from django import forms
from django.forms import modelformset_factory

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


RoleSkillFormSet = modelformset_factory(
    ProjectRoleSkill,
    fields=['skill', 'min_required_level'],
    extra=3,
    can_delete=True,
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