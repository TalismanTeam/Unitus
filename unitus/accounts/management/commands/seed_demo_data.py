"""
Populate the database with rich, realistic demo data for presentations.

This is NOT seed data (skills/tags are separate, permanent catalog data
seeded by their own app migrations). This command creates disposable demo
users, projects, roles, memberships, and reviews so every feature of the
platform can be shown live during a demo.

Safe to re-run: by default it wipes any previously-created demo data first
(identified by the fixed username/project-title lists below) and rebuilds
everything from scratch, so the demo state is always predictable.

Usage:
    python manage.py seed_demo_data              # reset + recreate (default)
    python manage.py seed_demo_data --no-reset    # only add, don't wipe first

Requires the catalog seed migrations to already be applied:
    python manage.py migrate skills
    python manage.py migrate reviews
(otherwise Skill/Tag lookups below will come back empty and the command
will stop with a clear error instead of creating broken rows).
"""

import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Avatar, User
from projects.models import JobAd, Project, ProjectMember, ProjectRole, ProjectRoleSkill
from projects.services import sync_job_ad_status_for_role
from reviews.models import Review, ReviewTag, Tag, UserHonor
from reviews.views import _maybe_award_badge  # reuse the exact production honor logic
from skills.models import Skill, UserSkill

# Mastery levels exactly as quoted in the SRS / used by the legacy front-end
# mockup. Adjust this list if skills/choices.py::MasteryLevel differs.
LEVELS = ['Beginner', 'Intermediate', 'Advanced', 'Expert', 'Master']

ADMIN_USERNAME = 'admin_demo'

# ---------------------------------------------------------------------------
# Demo users. Each tuple: (username, first, last, gender, birth_year, city,
# open_to_work, bio, [(skill_name, level), ...])
# ---------------------------------------------------------------------------
USERS = [
    ('sara_ahmadi', 'Sara', 'Ahmadi', 'FEMALE', 1998, 'Tehran, Iran', True,
     'Backend engineer who enjoys clean API design and mentoring junior devs.',
     [('Python', 'Expert'), ('Django', 'Advanced'), ('PostgreSQL', 'Advanced'), ('RESTful API Design', 'Expert'), ('Docker', 'Intermediate')]),
    ('reza_karimi', 'Reza', 'Karimi', 'MALE', 1995, 'Tehran, Iran', True,
     'Frontend developer focused on performant, accessible React apps.',
     [('React.js', 'Expert'), ('JavaScript', 'Advanced'), ('TypeScript', 'Intermediate'), ('CSS3', 'Advanced'), ('Tailwind CSS', 'Advanced')]),
    ('mina_hosseini', 'Mina', 'Hosseini', 'FEMALE', 1999, 'Isfahan, Iran', True,
     'Product designer who bridges research and pixel-perfect UI.',
     [('UI Design', 'Expert'), ('UX Design', 'Advanced'), ('Figma', 'Expert'), ('Wireframing & Prototyping', 'Advanced'), ('Design Systems', 'Intermediate')]),
    ('amir_rezaei', 'Amir', 'Rezaei', 'MALE', 1993, 'Shiraz, Iran', True,
     'Mobile engineer shipping cross-platform apps for five years.',
     [('Flutter', 'Advanced'), ('Kotlin / Jetpack Compose (Android)', 'Intermediate'), ('Swift / SwiftUI (iOS)', 'Intermediate')]),
    ('niloofar_sadeghi', 'Niloofar', 'Sadeghi', 'FEMALE', 1997, 'Mashhad, Iran', True,
     'ML engineer interested in NLP and applied deep learning.',
     [('Machine Learning', 'Advanced'), ('PyTorch', 'Advanced'), ('Pandas', 'Expert'), ('NumPy', 'Advanced'), ('Data Analysis', 'Advanced')]),
    ('pouya_jafari', 'Pouya', 'Jafari', 'MALE', 1994, 'Tehran, Iran', True,
     'DevOps engineer obsessed with reliable, boring deployments.',
     [('Docker', 'Expert'), ('Kubernetes', 'Advanced'), ('AWS', 'Advanced'), ('CI/CD', 'Expert'), ('Git', 'Expert')]),
    ('tara_moradi', 'Tara', 'Moradi', 'FEMALE', 1996, 'Tabriz, Iran', True,
     'QA engineer who believes automated tests are a love letter to your future self.',
     [('Unit Testing', 'Advanced'), ('Test Automation', 'Advanced'), ('Manual Testing', 'Expert'), ('API Testing', 'Intermediate')]),
    ('kian_ebrahimi', 'Kian', 'Ebrahimi', 'MALE', 1992, 'Tehran, Iran', True,
     'Product-minded PM who has led four cross-functional teams to launch.',
     [('Agile Methodology', 'Expert'), ('Scrum', 'Expert'), ('Project Planning & Estimation', 'Advanced'), ('Leadership', 'Advanced')]),
    ('yasmin_ghorbani', 'Yasmin', 'Ghorbani', 'FEMALE', 2000, 'Karaj, Iran', True,
     'Junior frontend developer, fast learner, big fan of clean components.',
     [('JavaScript', 'Intermediate'), ('HTML5', 'Advanced'), ('CSS3', 'Intermediate'), ('React.js', 'Beginner')]),
    ('arman_soleimani', 'Arman', 'Soleimani', 'MALE', 1991, 'Isfahan, Iran', False,
     'Senior backend architect, currently focused on internal tools.',
     [('Node.js', 'Expert'), ('Django', 'Advanced'), ('MySQL', 'Expert'), ('MongoDB', 'Intermediate'), ('RESTful API Design', 'Expert')]),
    ('parisa_najafi', 'Parisa', 'Najafi', 'FEMALE', 1998, 'Tehran, Iran', True,
     'Mobile developer who loves turning Figma files into working apps.',
     [('React Native', 'Advanced'), ('Flutter', 'Intermediate'), ('JavaScript', 'Advanced')]),
    ('hamed_bagheri', 'Hamed', 'Bagheri', 'MALE', 1990, 'Shiraz, Iran', False,
     'Infrastructure lead with a decade of on-call scars.',
     [('AWS', 'Expert'), ('Kubernetes', 'Expert'), ('Linux/Unix System Administration', 'Expert'), ('CI/CD', 'Advanced')]),
    ('leila_hashemi', 'Leila', 'Hashemi', 'FEMALE', 1995, 'Tehran, Iran', True,
     'Data analyst who turns messy spreadsheets into decisions.',
     [('Data Analysis', 'Advanced'), ('Pandas', 'Advanced'), ('Power BI', 'Intermediate'), ('Statistical Analysis', 'Intermediate')]),
    ('saeed_moini', 'Saeed', 'Moini', 'MALE', 1997, 'Mashhad, Iran', True,
     'Frontend developer, Vue enthusiast, occasional open-source contributor.',
     [('Vue.js', 'Advanced'), ('JavaScript', 'Advanced'), ('CSS3', 'Intermediate'), ('Next.js', 'Beginner')]),
    ('elham_rostami', 'Elham', 'Rostami', 'FEMALE', 1999, 'Tehran, Iran', True,
     'QA engineer who also loves writing clear technical documentation.',
     [('Manual Testing', 'Advanced'), ('Communication Skills', 'Advanced'), ('Teamwork & Collaboration', 'Advanced')]),
    ('babak_ahmadzadeh', 'Babak', 'Ahmadzadeh', 'MALE', 1993, 'Karaj, Iran', True,
     'Backend developer specializing in high-throughput APIs.',
     [('Python', 'Advanced'), ('FastAPI', 'Advanced'), ('PostgreSQL', 'Intermediate'), ('Redis', 'Intermediate')]),
    ('shirin_kazemi', 'Shirin', 'Kazemi', 'FEMALE', 1996, 'Isfahan, Iran', True,
     'Visual designer with a soft spot for motion and micro-interactions.',
     [('UI Design', 'Advanced'), ('Figma', 'Advanced'), ('Motion Design', 'Intermediate')]),
    ('omid_farahani', 'Omid', 'Farahani', 'MALE', 1994, 'Tehran, Iran', True,
     'Full-stack developer, equally happy in React and Node.',
     [('JavaScript', 'Advanced'), ('Node.js', 'Advanced'), ('React.js', 'Intermediate'), ('MongoDB', 'Intermediate'), ('Docker', 'Beginner')]),
]

DEMO_USERNAMES = [u[0] for u in USERS]

DEMO_PROJECT_TITLES = [
    'Aurora - Online Learning Platform',
    'Nova - Fitness Tracker Mobile App',
    'Phoenix - E-Commerce Marketplace',
    'Atlas - Fleet Management System',
    'Zenith - CRM Suspension Case',
    'Vortex - Blockchain Wallet',
    'Comet - Portfolio Website Builder',
    'Titan - DevOps Toolkit',
    'Helios - Data Pipeline',
    'Orion - Chat SDK',
]


class Command(BaseCommand):
    help = 'Seed the database with realistic demo users, projects, and reviews for presentations.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-reset', action='store_true',
            help="Don't delete previously-created demo data before seeding.",
        )

    def handle(self, *args, **options):
        random.seed(42)  # deterministic output across re-runs, nicer for rehearsed demos

        self.skills_by_name = {s.name: s for s in Skill.objects.all()}
        self.tags_by_name = {t.name: t for t in Tag.objects.all()}
        if not self.skills_by_name:
            raise CommandError("No Skill rows found. Run 'python manage.py migrate skills' first.")
        if not self.tags_by_name:
            raise CommandError("No Tag rows found. Run 'python manage.py migrate reviews' first.")

        if not options['no_reset']:
            self.reset_demo_data()

        with transaction.atomic():
            self.users_by_username = self.create_users()
            self.create_projects()

        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {len(DEMO_USERNAMES)} users + 1 admin, '
            f'{len(DEMO_PROJECT_TITLES)} projects. All demo passwords: password123'
        ))

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def reset_demo_data(self):
        self.stdout.write('Removing previous demo data (if any)...')
        # Order matters: Review.project is on_delete=RESTRICT, so reviews
        # must go before projects. ProjectMember/ProjectRole/JobAd cascade
        # automatically when their Project is deleted.
        Review.objects.filter(project__title__in=DEMO_PROJECT_TITLES).delete()
        UserHonor.objects.filter(user__username__in=DEMO_USERNAMES).delete()
        Project.objects.filter(title__in=DEMO_PROJECT_TITLES).delete()
        UserSkill.objects.filter(user__username__in=DEMO_USERNAMES).delete()
        User.objects.filter(username__in=DEMO_USERNAMES + [ADMIN_USERNAME]).delete()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def create_users(self):
        self.stdout.write('Creating demo users...')
        users_by_username = {}
        avatar = Avatar.objects.order_by('?').first()  # optional; fine if none exist yet

        for i, (username, first, last, gender, birth_year, city, open_to_work, bio, skills) in enumerate(USERS):
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'  {username} already exists, skipping.'))
                users_by_username[username] = User.objects.get(username=username)
                continue

            user = User.objects.create_user(
                username=username,
                email=f'{username}@unitus.demo',
                password='password123',
                first_name=first,
                last_name=last,
                gender=gender,
                birth_year=birth_year,
                phone_number=f'0912{1000000 + i:07d}',
                location=city,
                education_background="Bachelor's in Computer Engineering",
                about_me=bio,
                is_open_to_work=open_to_work,
                avatar_icon=avatar,
            )
            users_by_username[username] = user

            for skill_name, level in skills:
                skill = self.skills_by_name.get(skill_name)
                if skill is None:
                    self.stdout.write(self.style.WARNING(f'  Skill "{skill_name}" not found, skipping.'))
                    continue
                UserSkill.objects.get_or_create(user=user, skill=skill, defaults={'mastery_level': level})

        if not User.objects.filter(username=ADMIN_USERNAME).exists():
            User.objects.create_superuser(
                username=ADMIN_USERNAME,
                email='admin@unitus.demo',
                password='password123',
                first_name='Site',
                last_name='Administrator',
                location='Tehran, Iran',
            )

        return users_by_username

    # ------------------------------------------------------------------
    # Role/member helper (mirrors projects.views.project_add_role logic)
    # ------------------------------------------------------------------
    def add_role(self, project, title, description, capacity, skill_reqs, member_usernames=None, owner_role=False):
        role = ProjectRole.objects.create(
            project=project, role_title=title, role_description=description, capacity=capacity,
        )
        for skill_name, level in skill_reqs:
            skill = self.skills_by_name.get(skill_name)
            if skill:
                ProjectRoleSkill.objects.create(role=role, skill=skill, min_required_level=level)

        JobAd.objects.create(project=project, project_role=role, status=JobAd.Status.OPEN)

        if owner_role:
            pm_membership = ProjectMember.objects.get(project=project, user=project.pm)
            pm_membership.project_role = role
            pm_membership.save(update_fields=['project_role'])

        for username in (member_usernames or []):
            user = self.users_by_username[username]
            ProjectMember.objects.update_or_create(
                project=project, user=user,
                defaults={'project_role': role, 'member_status': ProjectMember.MemberStatus.ACTIVE},
            )

        sync_job_ad_status_for_role(role)
        return role

    def set_state(self, project, state, termination_reason=None):
        """Mirrors projects.views.project_state_change: cancel open ads on leaving RECRUITING."""
        if project.state == Project.State.RECRUITING and state != Project.State.RECRUITING:
            JobAd.objects.filter(project=project, status=JobAd.Status.OPEN).update(status=JobAd.Status.CANCELLED)
        project.state = state
        project.termination_reason = termination_reason
        project.save(update_fields=['state', 'termination_reason'])

    # ------------------------------------------------------------------
    # Reviews (round-robin per finished project, reusing production badge logic)
    # ------------------------------------------------------------------
    def seed_reviews(self, project, member_usernames, forced_tags=None):
        members = [self.users_by_username[u] for u in member_usernames]
        positive = [t for t in self.tags_by_name.values() if t.tag_type == Tag.TagType.POSITIVE]
        negative = [t for t in self.tags_by_name.values() if t.tag_type == Tag.TagType.NEGATIVE]

        for reviewer in members:
            for reviewee in members:
                if reviewer == reviewee:
                    continue

                if forced_tags and reviewee.username in forced_tags:
                    tag_names = list(forced_tags[reviewee.username])
                    rating = 5
                else:
                    rating = random.choice([3, 4, 4, 5, 5])
                    tag_names = [t.name for t in random.sample(positive, k=random.randint(1, 2))]
                    if random.random() < 0.15:
                        tag_names.append(random.choice(negative).name)

                review, created = Review.objects.get_or_create(
                    reviewer=reviewer, reviewee=reviewee, project=project,
                    defaults={'rating': rating},
                )
                if not created:
                    continue
                for tag_name in tag_names:
                    tag = self.tags_by_name[tag_name]
                    ReviewTag.objects.get_or_create(review=review, tag=tag)
                    if tag.tag_type == Tag.TagType.POSITIVE:
                        _maybe_award_badge(reviewee, tag)

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def create_projects(self):
        self.stdout.write('Creating demo projects...')
        u = self.users_by_username

        # --- P1: Recruiting, partially staffed --------------------------
        p1 = Project.objects.create(
            pm=u['kian_ebrahimi'], title='Aurora - Online Learning Platform',
            short_description='A platform connecting students with live online courses.',
            full_description='Aurora lets instructors run live cohort-based courses with assignments, '
                              'discussion boards, and certificates on completion.',
            duration_days=90,
        )
        self.add_role(p1, 'Frontend Developer', 'Build the student & instructor dashboards in React.', 2,
                      [('React.js', 'Advanced'), ('JavaScript', 'Advanced')], ['reza_karimi'])
        self.add_role(p1, 'Backend Developer', 'Design the course/enrollment API and grading engine.', 1,
                      [('Django', 'Advanced'), ('PostgreSQL', 'Intermediate')], ['sara_ahmadi'])
        self.add_role(p1, 'UI/UX Designer', 'Design the course player and instructor tools.', 1,
                      [('Figma', 'Advanced'), ('UI Design', 'Advanced')], [])

        # --- P2: Recruiting, brand new, nothing filled yet ---------------
        p2 = Project.objects.create(
            pm=u['parisa_najafi'], title='Nova - Fitness Tracker Mobile App',
            short_description='Mobile app for tracking workouts, nutrition, and progress photos.',
            full_description='Nova is a mobile-first fitness app with workout logging, nutrition '
                              'tracking, and social progress sharing with friends.',
            duration_days=60,
        )
        self.add_role(p2, 'Mobile Developer', 'Build the workout logging and progress screens in Flutter.', 2,
                      [('Flutter', 'Advanced')], [])
        self.add_role(p2, 'Backend Developer', 'Build the sync API and nutrition database.', 1,
                      [('Node.js', 'Intermediate'), ('MongoDB', 'Intermediate')], [])

        # --- P3: In progress, fully staffed, PM has a technical role -----
        p3 = Project.objects.create(
            pm=u['arman_soleimani'], title='Phoenix - E-Commerce Marketplace',
            short_description='A marketplace connecting local sellers with buyers.',
            full_description='Phoenix is a multi-vendor marketplace with seller dashboards, order '
                              'tracking, and integrated payments.',
            duration_days=120,
        )
        self.add_role(p3, 'Technical Lead', 'Own the overall architecture and code reviews.', 1,
                      [('RESTful API Design', 'Expert')], owner_role=True)
        self.add_role(p3, 'Frontend Developer', 'Build the storefront and seller dashboard UI.', 2,
                      [('React.js', 'Intermediate')], ['yasmin_ghorbani', 'saeed_moini'])
        self.add_role(p3, 'Backend Developer', 'Build the catalog, orders, and payments API.', 2,
                      [('Django', 'Advanced')], ['babak_ahmadzadeh', 'omid_farahani'])
        self.add_role(p3, 'QA Engineer', 'Own the test automation suite.', 1,
                      [('Test Automation', 'Intermediate')], ['tara_moradi'])
        self.set_state(p3, Project.State.IN_PROGRESS)

        # --- P4: In progress, one role never got filled (ad auto-cancelled) --
        p4 = Project.objects.create(
            pm=u['pouya_jafari'], title='Atlas - Fleet Management System',
            short_description='Real-time tracking and maintenance scheduling for delivery fleets.',
            full_description='Atlas gives logistics companies live vehicle tracking, maintenance '
                              'scheduling, and driver performance reports.',
            duration_days=100,
        )
        self.add_role(p4, 'DevOps Lead', 'Own CI/CD and the AWS infrastructure.', 1,
                      [('AWS', 'Advanced')], owner_role=True)
        self.add_role(p4, 'Backend Developer', 'Build the tracking ingestion pipeline.', 2,
                      [('Node.js', 'Advanced')], ['arman_soleimani'])
        self.add_role(p4, 'Frontend Developer', 'Build the fleet dashboard.', 1,
                      [('React.js', 'Intermediate')], ['reza_karimi'])
        self.set_state(p4, Project.State.IN_PROGRESS)

        # --- P5: Suspended -------------------------------------------------
        p5 = Project.objects.create(
            pm=u['hamed_bagheri'], title='Zenith - CRM Suspension Case',
            short_description='A lightweight CRM for small sales teams.',
            full_description='Zenith tracks leads, deals, and follow-ups for small sales teams. '
                              'Paused pending a scope decision from stakeholders.',
            duration_days=75,
        )
        self.add_role(p5, 'Backend Developer', 'Build the deals/leads API.', 1,
                      [('MySQL', 'Intermediate')], ['babak_ahmadzadeh'])
        self.add_role(p5, 'Frontend Developer', 'Build the pipeline board UI.', 1,
                      [('React.js', 'Intermediate')], [])
        self.set_state(p5, Project.State.SUSPENDED)

        # --- P6: Suspended ---------------------------------------------
        p6 = Project.objects.create(
            pm=u['omid_farahani'], title='Vortex - Blockchain Wallet',
            short_description='A non-custodial wallet for a small blockchain ecosystem.',
            full_description='Vortex is a browser-extension wallet with staking and swap support. '
                              'On hold while the team reassesses the regulatory landscape.',
            duration_days=150,
        )
        self.add_role(p6, 'Smart Contract Developer', 'Write and audit the staking contracts.', 1,
                      [('Smart Contracts (Solidity)', 'Advanced')], [])
        self.add_role(p6, 'Frontend Developer', 'Build the wallet extension UI.', 1,
                      [('React.js', 'Intermediate')], ['saeed_moini'])
        self.set_state(p6, Project.State.SUSPENDED)

        # --- P7: Terminated / SUCCESS - the "star" review project ---------
        p7 = Project.objects.create(
            pm=u['kian_ebrahimi'], title='Comet - Portfolio Website Builder',
            short_description='A drag-and-drop portfolio site builder for freelancers.',
            full_description='Comet let freelancers build and publish a portfolio site with a '
                              'drag-and-drop editor. Shipped successfully and wrapped up on schedule.',
            duration_days=45,
        )
        self.add_role(p7, 'Backend Developer', 'Build the site-publishing API.', 1,
                      [('Django', 'Advanced')], ['sara_ahmadi'])
        self.add_role(p7, 'Frontend Developer', 'Build the drag-and-drop editor.', 1,
                      [('React.js', 'Advanced')], ['reza_karimi'])
        self.add_role(p7, 'UI/UX Designer', 'Design the editor and public site templates.', 1,
                      [('Figma', 'Advanced')], ['mina_hosseini'])
        self.add_role(p7, 'QA Engineer', 'Test cross-browser rendering of published sites.', 1,
                      [('Manual Testing', 'Intermediate')], ['tara_moradi'])
        self.add_role(p7, 'Mobile Developer', 'Build the companion preview app.', 1,
                      [('Flutter', 'Intermediate')], ['amir_rezaei'])
        self.set_state(p7, Project.State.TERMINATED, Project.TerminationReason.SUCCESS)

        # Every other member reviews sara_ahmadi with the SAME two positive
        # tags -> 5 distinct reviewers -> unlocks both honors for her, on
        # top of a full round-robin so everyone has review history/ratings.
        self.seed_reviews(
            p7,
            member_usernames=['kian_ebrahimi', 'sara_ahmadi', 'reza_karimi', 'mina_hosseini', 'tara_moradi', 'amir_rezaei'],
            forced_tags={'sara_ahmadi': ['Reliable', 'Great Communicator']},
        )

        # --- P8: Terminated / SUCCESS - second successful project ---------
        p8 = Project.objects.create(
            pm=u['hamed_bagheri'], title='Titan - DevOps Toolkit',
            short_description='An internal CLI + dashboard for standardizing deploys.',
            full_description='Titan gave every team the same one-command deploy pipeline and a '
                              'shared dashboard for deployment history. Delivered on time and adopted org-wide.',
            duration_days=50,
        )
        self.add_role(p8, 'DevOps Lead', 'Own the CLI and the shared pipeline templates.', 1,
                      [('CI/CD', 'Advanced')], owner_role=True)
        self.add_role(p8, 'Backend Developer', 'Build the deployment history API.', 1,
                      [('Python', 'Advanced')], ['sara_ahmadi'])
        self.add_role(p8, 'Data/Analytics', 'Build the deploy-frequency reporting dashboard.', 1,
                      [('Data Analysis', 'Intermediate')], ['leila_hashemi'])
        self.set_state(p8, Project.State.TERMINATED, Project.TerminationReason.SUCCESS)

        self.seed_reviews(p8, member_usernames=['hamed_bagheri', 'sara_ahmadi', 'leila_hashemi'])

        # --- P9: Terminated / TEAM_FAILURE - no reviews (not SUCCESS) -----
        p9 = Project.objects.create(
            pm=u['niloofar_sadeghi'], title='Helios - Data Pipeline',
            short_description='A batch ETL pipeline for merging partner data feeds.',
            full_description='Helios was meant to unify three partner data feeds into one warehouse. '
                              'Shut down after the team could not agree on a schema.',
            duration_days=80,
        )
        self.add_role(p9, 'Data Engineer', 'Build the ingestion and transform jobs.', 1,
                      [('ETL / Data Pipelines', 'Advanced')], ['leila_hashemi'])
        self.add_role(p9, 'ML Engineer', 'Build the anomaly-detection model on merged data.', 1,
                      [('Machine Learning', 'Intermediate')], [])
        self.set_state(p9, Project.State.TERMINATED, Project.TerminationReason.TEAM_FAILURE)

        # --- P10: Terminated / PM_CANCELED - no reviews -------------------
        p10 = Project.objects.create(
            pm=u['elham_rostami'], title='Orion - Chat SDK',
            short_description='An embeddable chat widget SDK for third-party sites.',
            full_description='Orion aimed to be a drop-in chat widget for any website. '
                              'Cancelled by the PM due to a change in priorities.',
            duration_days=70,
        )
        self.add_role(p10, 'Backend Developer', 'Build the websocket relay service.', 1,
                      [('Node.js', 'Intermediate')], [])
        self.add_role(p10, 'Frontend Developer', 'Build the embeddable widget itself.', 1,
                      [('JavaScript', 'Intermediate')], ['shirin_kazemi'])
        self.set_state(p10, Project.State.TERMINATED, Project.TerminationReason.PM_CANCELED)