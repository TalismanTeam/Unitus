import json

from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import SkillCategory, Skill


class SkillsCatalogApiTests(TestCase):
    def setUp(self):
        self.category = SkillCategory.objects.create(category_name='Programming Languages')
        self.skill = Skill.objects.create(category=self.category, name='Python')
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995
        )
        self.client = Client()
        self.client.login(username='alice', password='pass12345')

    def test_list_categories(self):
        response = self.client.get(reverse('skills:categories'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['category_name'], 'Programming Languages')

    def test_list_skills(self):
        response = self.client.get(reverse('skills:list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Python')

    def test_filter_skills_by_category(self):
        other_category = SkillCategory.objects.create(category_name='Databases')
        Skill.objects.create(category=other_category, name='PostgreSQL')

        response = self.client.get(reverse('skills:list'), {'category': self.category.pk})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Python')

    def test_search_skills_by_name(self):
        Skill.objects.create(category=self.category, name='JavaScript')

        response = self.client.get(reverse('skills:list'), {'q': 'script'})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'JavaScript')

    def test_create_custom_skill(self):
        response = self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['is_custom'])
        self.assertEqual(data['created_by'], self.user.pk)
        self.assertTrue(Skill.objects.filter(name='Rust', is_custom=True, created_by=self.user).exists())

    def test_create_custom_skill_rejects_duplicate_case_insensitive(self):
        Skill.objects.create(category=self.category, name='Rust')
        response = self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'rust'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_create_custom_skill_requires_login(self):
        anon_client = Client()
        response = anon_client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Go'}),
            content_type='application/json',
        )
        self.assertNotEqual(response.status_code, 201)
        self.assertFalse(Skill.objects.filter(name='Go').exists())

    def test_create_custom_skill_requires_category_and_name(self):
        response = self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'name': 'Go'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_custom_skill_hidden_from_public_catalog_until_approved(self):
        self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        response = self.client.get(reverse('skills:list'))
        names = [s['name'] for s in response.json()]
        self.assertNotIn('Rust', names)

    def test_staff_can_see_pending_skills_with_include_pending(self):
        self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        staff = User.objects.create_user(
            username='admin', email='admin@example.com', password='pass12345',
            birth_year=1990, is_staff=True,
        )
        staff_client = Client()
        staff_client.login(username='admin', password='pass12345')
        response = staff_client.get(reverse('skills:list'), {'include_pending': '1'})
        names = [s['name'] for s in response.json()]
        self.assertIn('Rust', names)

    def test_non_staff_cannot_see_pending_even_with_flag(self):
        self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        response = self.client.get(reverse('skills:list'), {'include_pending': '1'})
        names = [s['name'] for s in response.json()]
        self.assertNotIn('Rust', names)

    def test_creator_can_delete_own_pending_suggestion(self):
        create_response = self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        skill_id = create_response.json()['id']
        response = self.client.delete(reverse('skills:delete-custom', args=[skill_id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Skill.objects.filter(pk=skill_id).exists())

    def test_other_user_cannot_delete_someone_elses_suggestion(self):
        create_response = self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        skill_id = create_response.json()['id']
        other = User.objects.create_user(
            username='bob', email='bob@example.com', password='pass12345', birth_year=1996
        )
        other_client = Client()
        other_client.login(username='bob', password='pass12345')
        response = other_client.delete(reverse('skills:delete-custom', args=[skill_id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Skill.objects.filter(pk=skill_id).exists())

    def test_cannot_delete_skill_already_in_use(self):
        from .models import UserSkill
        from .choices import MasteryLevel
        create_response = self.client.post(
            reverse('skills:create-custom'),
            data=json.dumps({'category': self.category.pk, 'name': 'Rust'}),
            content_type='application/json',
        )
        skill_id = create_response.json()['id']
        UserSkill.objects.create(user=self.user, skill_id=skill_id, mastery_level=MasteryLevel.BEGINNER)

        response = self.client.delete(reverse('skills:delete-custom', args=[skill_id]))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Skill.objects.filter(pk=skill_id).exists())

    def test_skill_stats_endpoint(self):
        from .models import UserSkill
        from .choices import MasteryLevel
        UserSkill.objects.create(user=self.user, skill=self.skill, mastery_level=MasteryLevel.ADVANCED)

        response = self.client.get(reverse('skills:stats', args=[self.skill.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user_count'], 1)
        self.assertEqual(data['project_role_count'], 0)
