class TextFormatter:

    def __init__(self):
        pass

    def profile_to_text(self, user) -> str:
        
        # Converts a User object into a formatted text representation.
        
        lines = []

        lines.append(f"Education: {user.education_background}")

        lines.append("")
        lines.append("Skills:")

        if user.skills.exists():
            for skill in user.skills.all():
                lines.append(
                    f"- {skill.skill.name} ({skill.mastery_level})"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append("Honors & Strengths:")

        if user.tags.exists():
            for tag in user.tags.all():
                lines.append(f"- {tag.name}")
        else:
            lines.append("- None")

        lines.append("")
        lines.append("Additional Information:")

        if user.additional_information:
            lines.append(user.additional_information)
        else:
            lines.append("None")

        return "\n".join(lines)

    def project_to_text(self, project) -> str:
        
        # Converts a Project object into a formatted text representation.
        
        lines = []

        lines.append("Project:")
        lines.append(f"Title: {project.title}")
        lines.append(f"Short Description: {project.short_description}")
        lines.append(f"Full Description: {project.full_description}")
        lines.append(f"Status: {project.state}")

        lines.append("")
        lines.append("Roles Needed:")

        if project.roles.exists():

            for role in project.roles.all():

                lines.append(
                    f"- {role.title} (Capacity: {role.capacity})"
                )

                lines.append(
                    f"  Description: {role.description}"
                )

                lines.append("  Required Skills:")

                if role.required_skills.exists():

                    for skill in role.required_skills.all():
                        lines.append(
                            f"  - {skill.skill.name} (min: {skill.min_required_level})"
                        )

                else:
                    lines.append("  - None")

                lines.append("")

        else:
            lines.append("- None")


        return "\n".join(lines)