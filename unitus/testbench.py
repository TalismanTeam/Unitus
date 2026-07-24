import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unitus.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectRole, JobAd
from skills.models import SkillCategory, Skill, UserSkill
from recommendation.services import MatchScoreService


def setup_testbench_data():
    print("🧹 Cleaning previous test data...")

    cat_backend, _ = SkillCategory.objects.get_or_create(category_name="Backend Development")
    cat_frontend, _ = SkillCategory.objects.get_or_create(category_name="Frontend Development")
    cat_ai, _ = SkillCategory.objects.get_or_create(category_name="AI & Data Science")
    cat_devops, _ = SkillCategory.objects.get_or_create(category_name="DevOps & Infrastructure")

    skill_py, _ = Skill.objects.get_or_create(category=cat_backend, name="Python")
    skill_dj, _ = Skill.objects.get_or_create(category=cat_backend, name="Django")
    skill_react, _ = Skill.objects.get_or_create(category=cat_frontend, name="React")
    skill_css, _ = Skill.objects.get_or_create(category=cat_frontend, name="Tailwind CSS")
    skill_ml, _ = Skill.objects.get_or_create(category=cat_ai, name="PyTorch")
    skill_ds, _ = Skill.objects.get_or_create(category=cat_ai, name="Pandas")
    skill_docker, _ = Skill.objects.get_or_create(category=cat_devops, name="Docker")
    skill_k8s, _ = Skill.objects.get_or_create(category=cat_devops, name="Kubernetes")


    users_data = [
        {
            "username": "tb_backend_dev",
            "first_name": "Reza",
            "about": "Backend specialist with deep experience in Python, Django REST Framework, and SQL databases.",
            "skills": [(skill_py, "EXPERT"), (skill_dj, "ADVANCED")]
        },
        {
            "username": "tb_frontend_dev",
            "first_name": "Mona",
            "about": "Frontend developer focusing on modern UI design, React components, state management, and CSS architectures.",
            "skills": [(skill_react, "EXPERT"), (skill_css, "ADVANCED")]
        },
        {
            "username": "tb_ai_engineer",
            "first_name": "Kaveh",
            "about": "Machine Learning engineer specialized in Deep Learning, PyTorch, model optimization, and data analysis.",
            "skills": [(skill_ml, "EXPERT"), (skill_ds, "EXPERT"), (skill_py, "ADVANCED")]
        },
        {
            "username": "tb_devops_engineer",
            "first_name": "Samin",
            "about": "DevOps engineer focusing on CI/CD pipelines, Docker containerization, Kubernetes orchestration, and cloud deployment.",
            "skills": [(skill_docker, "EXPERT"), (skill_k8s, "ADVANCED")]
        },
    ]

    created_users = []
    for u_info in users_data:
        user, _ = User.objects.get_or_create(
            username=u_info["username"],
            defaults={
                "email": f"{u_info['username']}@testbench.com",
                "first_name": u_info["first_name"],
                "last_name": "Testbench",
                "birth_year": 1998,
                "about_me": u_info["about"],
                "is_open_to_work": True
            }
        )

        user.about_me = u_info["about"]
        user.is_open_to_work = True
        user.save()

        for sk, mastery in u_info["skills"]:
            UserSkill.objects.get_or_create(user=user, skill=sk, defaults={"mastery_level": mastery})

        created_users.append(user)

    pm, _ = User.objects.get_or_create(
        username="tb_pm_manager",
        defaults={
            "email": "pm@testbench.com",
            "first_name": "Project",
            "last_name": "Manager",
            "birth_year": 1990
        }
    )

    projects_data = [
        {
            "title": "Scalable E-Commerce Backend",
            "short": "High performance backend API development.",
            "full": "We are building a large scale e-commerce platform requiring scalable Python and Django APIs with PostgreSQL.",
            "role_title": "Python Backend Engineer",
            "role_desc": "Design REST APIs and handle database integrations using Django."
        },
        {
            "title": "Interactive Dashboard UI",
            "short": "Modern Web Application Interface.",
            "full": "Building an enterprise admin dashboard using React, Tailwind CSS, and frontend optimization techniques.",
            "role_title": "React Frontend Specialist",
            "role_desc": "Develop responsive components and integrate frontend with backend REST endpoints."
        },
        {
            "title": "LLM Recommendation Engine",
            "short": "Machine Learning and Neural Networks.",
            "full": "Research and implement embedding models and recommendation algorithms using PyTorch and Pandas.",
            "role_title": "AI/ML Scientist",
            "role_desc": "Train neural network models and evaluate Cosine Similarity metrics on candidate profiles."
        },
        {
            "title": "Cloud Infrastructure Automation",
            "short": "Kubernetes & Docker Deployment.",
            "full": "Automate deployment pipelines and manage server clusters using Docker containers and Kubernetes environments.",
            "role_title": "DevOps Architect",
            "role_desc": "Maintain CI/CD pipelines, container orchestration, and server monitoring."
        },
    ]

    created_ads = []
    for p_info in projects_data:
        proj, _ = Project.objects.get_or_create(
            pm=pm,
            title=p_info["title"],
            defaults={
                "short_description": p_info["short"],
                "full_description": p_info["full"],
                "duration_days": 60
            }
        )

        role, _ = ProjectRole.objects.get_or_create(
            project=proj,
            role_title=p_info["role_title"],
            defaults={"capacity": 1, "role_description": p_info["role_desc"]}
        )

        ad, _ = JobAd.objects.get_or_create(
            project=proj,
            project_role=role,
            defaults={"status": JobAd.Status.OPEN}
        )
        ad.status = JobAd.Status.OPEN
        ad.save()
        created_ads.append(ad)

    print("✅ Testbench setup complete! (4 Users, 4 Projects/JobAds Created)\n")
    return created_users, created_ads


def run_testbench():
    users, ads = setup_testbench_data()
    service = MatchScoreService()

    print("=" * 70)
    print("📊 TESTBENCH RESULTS: USER TO JOB AD RECOMMENDATIONS")
    print("=" * 70)

    for user in users:
        print(f"\n👤 USER: {user.username} ({user.first_name})")
        print(f"📝 Profile Summary: {user.about_me[:80]}...")
        
        recs = service.recommend_ads_for_user(user, top_k=4)

        print("-" * 55)
        for idx, rec in enumerate(recs, 1):
            project_title = rec['ad'].project.title
            role_title = rec['ad'].project_role.role_title
            score = rec['score']
            

            rank_emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "  "
            print(f"  {rank_emoji} Rank {idx}: [{score:.4f}] -> {role_title} ({project_title})")
        print("-" * 55)


if __name__ == "__main__":
    run_testbench()