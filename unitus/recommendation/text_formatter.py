# unitus/recommendation/text_formatter.py

from accounts.models import User
from projects.models import Project, JobAd


class TextFormatter:

    def profile_to_text(self, user: User) -> str:
        """
        Converts a User object into a text representation optimized for embeddings.

        Skills are listed first since they're the actual signal used to match
        against job ad requirements. `about_me` is intentionally excluded: it's
        freeform prose that isn't a reliable skill signal and tends to pull the
        embedding toward semantically-similar-sounding but skill-irrelevant ads.
        `Open to Work` is also excluded - it's constant across every profile in
        the candidate pool (already enforced via is_open_to_work=True at the
        query level), so it only added noise, never discriminative signal.
        """
        lines = ["Skills:"]
        lines.extend(self._format_user_skills(user))

        if user.education_background:
            lines.append("")
            lines.append(f"Education: {user.education_background}")

        return "\n".join(lines)

    def _format_user_skills(self, user: User) -> list:
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
                    f"  - {skill.skill.name} ({skill.get_mastery_level_display()})"
                )

        return lines

    def project_to_text(self, project: Project) -> str:
        """
        Converts a Project object into a text representation optimized for embeddings.
        """
        lines = [
            f"Project Title: {project.title}",
            f"Short Description: {project.short_description}",
            f"Full Description: {project.full_description}",
            "",
            "Roles:"
        ]
        lines.extend(self._format_project_roles(project))
        return "\n".join(lines)

    def job_ad_to_text(self, job_ad: JobAd) -> str:
        """
        Converts a JobAd entity (Project + specific ProjectRole) into a text representation.

        Required Skills are listed first to mirror the ordering in profile_to_text,
        keeping the two sides of the match symmetric in how strongly skills
        dominate the embedded text relative to descriptive prose.
        """
        project = job_ad.project
        role = job_ad.project_role

        lines = ["Required Skills:"]
        lines.extend(self._format_role_skills(role))
        lines.append("")
        lines.append(f"Role Title: {role.role_title}")
        lines.append(f"Role Description: {role.role_description}")
        lines.append(f"Project Title: {project.title}")
        lines.append(f"Project Description: {project.short_description}")
        return "\n".join(lines)

    def _format_project_roles(self, project: Project) -> list:
        roles = project.projectrole_set.all()

        if not roles.exists():
            return ["- None"]

        lines = []
        for role in roles:
            lines.append(f"- {role.role_title} (Capacity: {role.capacity})")
            if role.role_description:
                lines.append(f"  Description: {role.role_description}")
            lines.append("  Required Skills:")
            lines.extend(self._format_role_skills(role))
            lines.append("")

        return lines

    def _format_role_skills(self, role) -> list:
        required_skills = (
            role.projectroleskill_set
            .select_related("skill")
            .all()
        )

        if not required_skills.exists():
            return ["  - None"]

        return [
            f"  - {skill.skill.name} (min: {skill.get_min_required_level_display()})"
            for skill in required_skills
        ]


def get_embedding_text(obj) -> str:
    """
    Returns the text representation used for embedding.
    """
    formatter = TextFormatter()

    if isinstance(obj, User):
        return formatter.profile_to_text(obj)
    if isinstance(obj, Project):
        return formatter.project_to_text(obj)
    if isinstance(obj, JobAd):
        return formatter.job_ad_to_text(obj)

    raise TypeError(
        f"Unsupported object type: {type(obj).__name__}"
    )
