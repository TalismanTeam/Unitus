from accounts.models import UserPrivacySettings


class TextFormatter:

    def __init__(self):
        pass

    def profile_to_text(self, user) -> str:
        """
        Converts a User object into a formatted text representation.
        """
        privacy = self._get_privacy_settings(user)
        lines = []

        lines.append(f"Username: {user.username}")

        full_name = f"{user.first_name} {user.last_name}".strip()
        if full_name:
            lines.append(f"Full Name: {full_name}")

        if privacy.show_gender and user.gender:
            lines.append(f"Gender: {user.gender}")

        if privacy.show_birth_year and user.birth_year:
            lines.append(f"Birth Year: {user.birth_year}")

        if privacy.show_location and user.location:
            lines.append(f"Location: {user.location}")

        if privacy.show_email and user.email:
            lines.append(f"Email: {user.email}")

        if privacy.show_phone and user.phone_number:
            lines.append(f"Phone: {user.phone_number}")

        lines.append(f"Open to Work: {'Yes' if user.is_open_to_work else 'No'}")

        if privacy.show_education_background and user.education_background:
            lines.append("")
            lines.append(f"Education Background: {user.education_background}")

        lines.append("")
        lines.append("Skills:")
        lines.extend(self._format_user_skills(user))

        return "\n".join(lines)

    def _get_privacy_settings(self, user):
        """
        Returns the user's UserPrivacySettings, or a sensible default
        object (matching the model's own field defaults) if none exists yet.
        """
        try:
            return user.userprivacysettings
        except UserPrivacySettings.DoesNotExist:
            return UserPrivacySettings(user=user)

    def _format_user_skills(self, user) -> list:
        """
        Groups the user's skills by category, e.g.:

        Programming:
          - Python (ADVANCED)
          - Django (INTERMEDIATE)
        """
        # NOTE: UserSkill.user has no related_name defined in skills/models.py,
        # so the reverse accessor defaults to `userskill_set`.
        # If you later add related_name='skills' to UserSkill, switch this to user.skills.all()
        user_skills = user.userskill_set.select_related('skill__category').all()

        if not user_skills.exists():
            return ["- None"]

        skills_by_category = {}
        for user_skill in user_skills:
            category_name = user_skill.skill.category.category_name
            skills_by_category.setdefault(category_name, []).append(user_skill)

        lines = []
        for category_name, skills in skills_by_category.items():
            lines.append(f"{category_name}:")
            for user_skill in skills:
                lines.append(f"  - {user_skill.skill.name} ({user_skill.mastery_level})")

        return lines



    def project_to_text(self, project) -> str:
        """
        Converts a Project object into a formatted text representation.
        """
        lines = []

        lines.append(f"Title: {project.title}")
        lines.append(f"Short Description: {project.short_description}")

        if project.full_description:
            lines.append(f"Full Description: {project.full_description}")

        lines.append(f"Status: {project.state}")
        lines.append(f"Duration (days): {project.duration_days}")

        lines.append("")
        lines.append("Roles Needed:")
        lines.extend(self._format_project_roles(project))

        return "\n".join(lines)

    def _format_project_roles(self, project) -> list:
        # NOTE: ProjectRole.project has no related_name defined in projects/models.py,
        # so the reverse accessor defaults to `projectrole_set`.
        roles = project.projectrole_set.all()

        if not roles.exists():
            return ["- None"]

        lines = []
        for role in roles:
            lines.append(f"- {role.role_title} (Capacity: {role.capacity})")
            lines.append(f"  Description: {role.role_description}")
            lines.append("  Required Skills:")
            lines.extend(self._format_role_skills(role))
            lines.append("")

        return lines

    def _format_role_skills(self, role) -> list:
        # NOTE: ProjectRoleSkill.role has no related_name defined either,
        # so the reverse accessor defaults to `projectroleskill_set`.
        required_skills = role.projectroleskill_set.select_related('skill').all()

        if not required_skills.exists():
            return ["  - None"]

        return [
            f"  - {rs.skill.name} (min: {rs.min_required_level})"
            for rs in required_skills
        ]


# ----------------------------------------------------------------------
# Module-level convenience helper (used directly by embedder.py callers)
# ----------------------------------------------------------------------

def get_embedding_text(obj) -> str:
    """
    Returns the text to be embedded for a given object.
    Dispatches based on the object's type: User -> profile, Project -> project.
    """
    from accounts.models import User
    from projects.models import Project

    formatter = TextFormatter()

    if isinstance(obj, User):
        return formatter.profile_to_text(obj)
    elif isinstance(obj, Project):
        return formatter.project_to_text(obj)

    raise TypeError(f"get_embedding_text() does not support type {type(obj).__name__}")