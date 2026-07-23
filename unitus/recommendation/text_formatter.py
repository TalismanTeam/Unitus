from accounts.models import UserPrivacySettings


class TextFormatter:

    def __init__(self):
        pass

    def profile_to_text(self, user) -> str:
        """
        Converts a User object into a text representation optimized for embeddings.
        """

        lines = []

        if user.education_background:
            lines.append(f"Education: {user.education_background}")

        lines.append(f"Open to Work: {'Yes' if user.is_open_to_work else 'No'}")

        lines.append("")
        lines.append("Skills:")
        lines.extend(self._format_user_skills(user))

        return "\n".join(lines)

    def _format_user_skills(self, user) -> list:
        """
        Groups user skills by category.
        """

        user_skills = (
            user.userskill_set
            .select_related("skill__category")
            .all()
        )

        if not user_skills.exists():
            return ["- None"]

        skills_by_category = {}

        for user_skill in user_skills:
            category = user_skill.skill.category.category_name
            skills_by_category.setdefault(category, []).append(user_skill)

        lines = []

        for category, skills in skills_by_category.items():
            lines.append(f"{category}:")
            for skill in skills:
                lines.append(
                    f"  - {skill.skill.name} ({skill.mastery_level})"
                )

        return lines

    def project_to_text(self, project) -> str:
        """
        Converts a Project object into a text representation optimized for embeddings.
        """

        pass

    def _format_project_roles(self, project) -> list:
        """
        Formats all project roles.
        """

        roles = project.projectrole_set.all()

        if not roles.exists():
            return ["- None"]

        lines = []

        for role in roles:

            lines.append(
                f"- {role.role_title} (Capacity: {role.capacity})"
            )

            if role.role_description:
                lines.append(
                    f"  Description: {role.role_description}"
                )

            lines.append("  Required Skills:")
            lines.extend(self._format_role_skills(role))
            lines.append("")

        return lines

    def _format_role_skills(self, role) -> list:
        """
        Formats required skills for a project role.
        """

        required_skills = (
            role.projectroleskill_set
            .select_related("skill")
            .all()
        )

        if not required_skills.exists():
            return ["  - None"]

        return [
            f"  - {skill.skill.name} (min: {skill.min_required_level})"
            for skill in required_skills
        ]


def get_embedding_text(obj) -> str:
    """
    Returns the text representation used for embedding.
    """

    from accounts.models import User
    from projects.models import Project

    formatter = TextFormatter()

    if isinstance(obj, User):
        return formatter.profile_to_text(obj)

    if isinstance(obj, Project):
        return formatter.project_to_text(obj)

    raise TypeError(
        f"Unsupported object type: {type(obj).__name__}"
    )