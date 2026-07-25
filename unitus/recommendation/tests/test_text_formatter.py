from django.test import TestCase

from accounts.models import User
from projects.models import JobAd, Project, ProjectRole, ProjectRoleSkill
from skills.models import Skill, SkillCategory, UserSkill
from recommendation.text_formatter import get_embedding_text


class ProfileToTextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dana', email='dana@example.com', password='pass12345',
            birth_year=1998, about_me='Backend developer.', education_background='BSc CS',
        )
        # get_or_create: the skills app seeds a fixed catalog via a data
        # migration (0002_seed_categories_and_skills), which Django's test
        # runner applies to the test DB just like any other migration - so
        # "Programming Languages" / "Python" already exist by the time this
        # setUp runs. create() would collide with that seeded row.
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Python')
        UserSkill.objects.create(user=self.user, skill=self.skill, mastery_level='ADVANCED')

    def test_includes_about_me_and_education(self):
        text = get_embedding_text(self.user)
        self.assertIn('Backend developer.', text)
        self.assertIn('BSc CS', text)

    def test_includes_open_to_work_flag(self):
        text = get_embedding_text(self.user)
        self.assertIn('Open to Work: No', text)
        self.user.is_open_to_work = True
        self.user.save()
        self.assertIn('Open to Work: Yes', get_embedding_text(self.user))

    def test_groups_skills_by_category(self):
        text = get_embedding_text(self.user)
        self.assertIn('Programming Languages:', text)
        self.assertIn('Python (Advanced)', text)

    def test_no_skills_still_produces_text(self):
        other_user = User.objects.create_user(
            username='no_skills', email='noskills@example.com', password='pass12345', birth_year=2000,
        )
        text = get_embedding_text(other_user)
        self.assertIn('- None', text)


class ProjectToTextTests(TestCase):
    def setUp(self):
        self.pm = User.objects.create_user(
            username='pm_user', email='pm@example.com', password='pass12345', birth_year=1990,
        )
        self.project = Project.objects.create(
            pm=self.pm, title='Team Match Platform', short_description='Find teammates with AI.',
            full_description='A platform that recommends teammates using embeddings.', duration_days=90,
        )
        self.role = ProjectRole.objects.create(
            project=self.project, role_title='Backend Developer',
            role_description='Build the Django API.', capacity=2,
        )
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Django')
        ProjectRoleSkill.objects.create(role=self.role, skill=self.skill, min_required_level='INTERMEDIATE')

    def test_includes_project_fields(self):
        text = get_embedding_text(self.project)
        self.assertIn('Team Match Platform', text)
        self.assertIn('Find teammates with AI.', text)

    def test_includes_role_and_required_skills(self):
        text = get_embedding_text(self.project)
        self.assertIn('Backend Developer (Capacity: 2)', text)
        self.assertIn('Django (min: Intermediate)', text)

    def test_no_roles_still_produces_text(self):
        empty_project = Project.objects.create(
            pm=self.pm, title='Empty', short_description='No roles yet.',
            full_description='Nothing here yet.', duration_days=30,
        )
        text = get_embedding_text(empty_project)
        self.assertIn('- None', text)


class JobAdToTextTests(TestCase):
    def setUp(self):
        self.pm = User.objects.create_user(
            username='pm_user2', email='pm2@example.com', password='pass12345', birth_year=1990,
        )
        self.project = Project.objects.create(
            pm=self.pm, title='Team Match Platform', short_description='Find teammates with AI.',
            full_description='A platform that recommends teammates using embeddings.', duration_days=90,
        )
        self.role = ProjectRole.objects.create(
            project=self.project, role_title='Backend Developer',
            role_description='Build the Django API.', capacity=2,
        )
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Django')
        ProjectRoleSkill.objects.create(role=self.role, skill=self.skill, min_required_level='INTERMEDIATE')
        self.job_ad = JobAd.objects.create(project=self.project, project_role=self.role)

    def test_includes_project_and_role_info(self):
        text = get_embedding_text(self.job_ad)
        self.assertIn('Team Match Platform', text)
        self.assertIn('Backend Developer', text)
        self.assertIn('Build the Django API.', text)
        self.assertIn('Django (min: Intermediate)', text)


class GetEmbeddingTextTypeErrorTests(TestCase):
    def test_unsupported_type_raises(self):
        with self.assertRaises(TypeError):
            get_embedding_text(object())
