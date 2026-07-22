# skills/migrations/0002_seed_categories_and_skills.py
from django.db import migrations

CATEGORIES = [
    (1, 'Programming Languages'),
    (2, 'Front-end Development'),
    (3, 'Back-end Development'),
    (4, 'Mobile Development'),
    (5, 'Databases & Data Management'),
    (6, 'AI & Machine Learning'),
    (7, 'Data Science & Analytics'),
    (8, 'Software Engineering & Architecture'),
    (9, 'QA & Testing'),
    (10, 'DevOps & Infrastructure'),
    (11, 'Cybersecurity'),
    (12, 'Blockchain & Web3'),
    (13, 'Game Dev & 3D Graphics'),
    (14, 'Embedded Systems & IoT'),
    (15, 'Design (UI/UX & Graphics)'),
    (16, 'Project Management & Collaboration'),
    (17, 'Office & Productivity'),
    (18, 'English & Communication'),
    (19, 'Soft Skills'),
]

SKILLS_BY_CATEGORY = {
    1: ['Python', 'JavaScript', 'TypeScript', 'Java', 'C', 'C++', 'C#', 'Go', 'Rust', 'Kotlin',
        'Swift', 'PHP', 'Ruby', 'Dart', 'Scala', 'R', 'MATLAB', 'Perl', 'Objective-C', 'Lua',
        'SQL', 'PL/SQL', 'T-SQL', 'GraphQL', 'Bash/Shell Scripting', 'PowerShell', 'Solidity',
        'Assembly', 'VHDL/Verilog'],
    2: ['HTML5', 'CSS3', 'Sass/SCSS', 'LESS', 'JavaScript (ES6+)', 'React.js', 'Next.js',
        'Vue.js', 'Nuxt.js', 'Angular', 'Svelte/SvelteKit', 'Tailwind CSS', 'Bootstrap',
        'Material UI', 'Chakra UI', 'Redux', 'Zustand', 'MobX', 'React Query', 'Webpack',
        'Vite', 'Babel', 'ESLint/Prettier', 'Progressive Web Apps (PWA)',
        'Responsive & Adaptive Design', 'Web Accessibility (WCAG / a11y)', 'WebSocket', 'WebRTC'],
    3: ['Node.js', 'Express.js', 'NestJS', 'Django', 'Flask', 'FastAPI', 'Spring / Spring Boot',
        'ASP.NET / .NET Core', 'Laravel', 'Symfony', 'Ruby on Rails', 'Go (Gin, Fiber)',
        'RESTful API Design', 'GraphQL API', 'Microservices Architecture',
        'Authentication/Authorization (OAuth2, JWT, SSO)',
        'Message Queues (RabbitMQ, Kafka, Redis Pub/Sub)'],
    4: ['Swift / SwiftUI (iOS)', 'Kotlin / Jetpack Compose (Android)', 'Flutter', 'Dart (Mobile)',
        'React Native', 'Xamarin / .NET MAUI', 'Mobile UI/UX Guidelines',
        'App Store / Google Play Deployment'],
    5: ['MySQL', 'PostgreSQL', 'SQLite', 'MariaDB', 'MongoDB', 'Redis', 'Cassandra', 'DynamoDB',
        'Firebase / Firestore', 'Elasticsearch', 'Database Design & Normalization', 'Prisma',
        'Sequelize', 'SQLAlchemy', 'Hibernate', 'Entity Framework', 'Data Warehousing',
        'Vector Databases'],
    6: ['Machine Learning', 'Deep Learning', 'Neural Networks', 'Natural Language Processing (NLP)',
        'Computer Vision', 'Large Language Models (LLMs)', 'Prompt Engineering',
        'Retrieval-Augmented Generation (RAG)', 'Fine-tuning & Transfer Learning', 'LLM Ops / MLOps',
        'AI Agents / Multi-Agent Systems', 'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn',
        'Hugging Face Transformers', 'OpenCV', 'spaCy', 'NLTK', 'LangChain', 'LlamaIndex',
        'Generative AI', 'Data Preprocessing', 'Model Deployment'],
    7: ['Data Analysis', 'Statistical Analysis', 'Data Visualization', 'Power BI', 'Tableau',
        'Pandas', 'NumPy', 'Big Data (Hadoop/Spark)', 'ETL / Data Pipelines', 'A/B Testing',
        'Business Intelligence (BI)'],
    8: ['Object-Oriented Programming (OOP)', 'Functional Programming', 'Design Patterns',
        'Software Architecture', 'System Design', 'Clean Code / Refactoring',
        'Test-Driven Development (TDD)', 'Behavior-Driven Development (BDD)',
        'Domain-Driven Design (DDD)', 'Algorithm Design & Data Structures',
        'Concurrency & Multithreading'],
    9: ['Manual Testing', 'Unit Testing', 'Integration Testing', 'End-to-End Testing',
        'Performance/Load Testing', 'API Testing', 'Test Automation'],
    10: ['Git', 'GitHub', 'GitLab', 'Bitbucket', 'Docker', 'Kubernetes', 'CI/CD',
         'Infrastructure as Code (Terraform/Ansible)', 'AWS', 'Google Cloud (GCP)',
         'Microsoft Azure', 'Linux/Unix System Administration', 'Nginx', 'Apache',
         'Monitoring & Logging', 'Serverless Computing'],
    11: ['Application Security (OWASP Top 10)', 'Network Security', 'Penetration Testing',
         'Cryptography', 'Identity & Access Management (IAM)', 'Secure Coding Practices',
         'Vulnerability Assessment'],
    12: ['Blockchain Fundamentals', 'Smart Contracts (Solidity)', 'Ethereum', 'Web3.js/Ethers.js',
         'Decatralized Applications (dApps)', 'NFT / Crypto Wallet Integration'],
    13: ['Unity', 'Unreal Engine', 'C# (Game Dev)', 'C++ (Game Dev)', 'Game Design Principles',
         '3D Modeling & Animation', 'Godot Engine', 'Shader Programming'],
    14: ['Embedded C/C++', 'Arduino', 'Raspberry Pi', 'IoT Protocols (MQTT/CoAP)', 'RTOS',
         'PCB Design Basics'],
    15: ['UI Design', 'UX Design', 'User Research', 'Usability Testing',
         'Wireframing & Prototyping', 'Figma', 'Adobe XD', 'Sketch', 'Adobe Photoshop',
         'Illustrator', 'InDesign', 'Adobe After Effects', 'Premiere Pro', 'Canva',
         'Design Systems', 'Typography & Color Theory', 'Motion Design',
         'Interaction Design (IxD)'],
    16: ['Agile Methodology', 'Scrum', 'Kanban', 'Jira', 'Trello', 'Asana', 'Notion', 'ClickUp',
         'Project Planning & Estimation', 'Product Management Basics', 'Technical Documentation',
         'Confluence'],
    17: ['Microsoft Word', 'Microsoft Excel', 'PowerPoint', 'Outlook', 'Google Docs',
         'Google Sheets', 'Google Slides', 'Microsoft Teams', 'Slack', 'Zoom',
         'Data Entry & Reporting'],
    18: ['Beginner (A1–A2)', 'Intermediate (B1–B2)', 'Advanced (C1)', 'Fluent/Native (C2)',
         'Technical Writing', 'Reading Technical Documentation', 'Business Email Writing',
         'Presentation Skills', 'IELTS', 'TOEFL'],
    19: ['Problem Solving', 'Critical Thinking', 'Teamwork & Collaboration',
         'Communication Skills', 'Time Management', 'Adaptability', 'Leadership',
         'Mentoring & Code Review', 'Creativity'],
}


def seed_data(apps, schema_editor):
    SkillCategory = apps.get_model('skills', 'SkillCategory')
    Skill = apps.get_model('skills', 'Skill')

    for cat_id, name in CATEGORIES:
        category, _ = SkillCategory.objects.get_or_create(
            id=cat_id,
            defaults={'category_name': name}
        )
        for skill_name in SKILLS_BY_CATEGORY.get(cat_id, []):
            Skill.objects.get_or_create(
                category=category,
                name=skill_name,
                defaults={'is_custom': False, 'created_by': None}
            )


def reverse_seed(apps, schema_editor):
    Skill = apps.get_model('skills', 'Skill')
    SkillCategory = apps.get_model('skills', 'SkillCategory')
    Skill.objects.filter(is_custom=False).delete()
    SkillCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0001_initial'),   
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_seed),
    ]