from recommendation.embedder import TextEmbedder
from recommendation.ranker import Ranker

embedder = TextEmbedder()
ranker = Ranker()


project = """
عنوان پروژه:
سیستم پیشنهاددهنده هم‌تیمی با استفاده از هوش مصنوعی

توضیحات:
در حال توسعه یک وب‌سایت هستیم که افراد بتوانند برای پروژه‌های خود
هم‌تیمی مناسب پیدا کنند.

مهارت‌های مورد نیاز:
- Python
- Django
- Machine Learning
- Git

مسئولیت‌ها:
- توسعه Backend
- طراحی REST API
- پیاده‌سازی مدل‌های یادگیری ماشین

ترجیحاً فردی که:
- با سیستم‌های پیشنهاددهنده آشنا باشد.
- به هوش مصنوعی علاقه داشته باشد.
- روحیه کار تیمی داشته باشد.
"""

project_embedding = embedder.embed(project)


candidates = [

    (
        "Ali",
        embedder.embed("""
نقش:
توسعه‌دهنده بک‌اند

مهارت‌ها:
- Python
- Django
- PostgreSQL
- Docker
- Git

علایق:
- هوش مصنوعی
- سیستم‌های پیشنهاددهنده

تجربه:
- توسعه REST API
- طراحی پایگاه داده

درباره من:
به توسعه سیستم‌های مقیاس‌پذیر علاقه دارم و دوست دارم روی پروژه‌های هوش مصنوعی کار کنم.
""")
    ),

    (
        "Nima",
        embedder.embed("""
نقش:
توسعه‌دهنده فول‌استک

مهارت‌ها:
- Python
- Django
- React
- Docker
- Git

علایق:
- توسعه وب
- استارتاپ
- هوش مصنوعی

تجربه:
- توسعه Full Stack
- طراحی REST API

درباره من:
به ساخت محصولات نرم‌افزاری از صفر تا صد علاقه دارم.
""")
    ),

    (
        "Mohammad",
        embedder.embed("""
نقش:
مهندس یادگیری ماشین

مهارت‌ها:
- Python
- PyTorch
- TensorFlow
- Git

علایق:
- یادگیری ماشین
- بینایی ماشین

تجربه:
- آموزش مدل‌های یادگیری عمیق
- طراحی مدل‌های هوش مصنوعی

درباره من:
به تحقیق و توسعه مدل‌های هوش مصنوعی علاقه‌مندم.
""")
    ),

    (
        "Sara",
        embedder.embed("""
نقش:
توسعه‌دهنده فرانت‌اند

مهارت‌ها:
- React
- Vue.js
- JavaScript
- TypeScript

علایق:
- رابط کاربری
- تجربه کاربری

تجربه:
- توسعه پنل‌های مدیریتی
- طراحی صفحات وب

درباره من:
به ساخت رابط‌های کاربری مدرن علاقه دارم.
""")
    ),

    (
        "Reza",
        embedder.embed("""
نقش:
تحلیلگر داده

مهارت‌ها:
- Python
- Pandas
- NumPy
- Power BI
- Excel

علایق:
- تحلیل داده
- آمار

تجربه:
- تحلیل فروش
- ساخت داشبوردهای مدیریتی

درباره من:
به استخراج اطلاعات از داده‌ها و تحلیل کسب‌وکار علاقه دارم.
""")
    ),

    (
        "Fatemeh",
        embedder.embed("""
نقش:
حسابدار

مهارت‌ها:
- Excel
- حسابداری مالی
- مالیات
- تهیه گزارش‌های مالی

علایق:
- مدیریت مالی
- حسابرسی

تجربه:
- تهیه صورت‌های مالی
- مدیریت هزینه‌ها

درباره من:
چندین سال در حوزه حسابداری شرکت‌های خصوصی فعالیت کرده‌ام.
""")
    ),

    (
        "Hossein",
        embedder.embed("""
نقش:
وکیل

مهارت‌ها:
- حقوق تجارت
- قراردادها
- داوری

علایق:
- حقوق کسب‌وکار
- مالکیت فکری

تجربه:
- تنظیم قرارداد
- مشاوره حقوقی

درباره من:
در زمینه قراردادهای تجاری و حقوق استارتاپ‌ها فعالیت می‌کنم.
""")
    )
]



results = ranker.rank(
    query_embedding=project_embedding,
    candidates=candidates,
    top_k=len(candidates)
)

print("\n========== Recommended Users ==========\n")

for rank, (user_id, score) in enumerate(results, start=1):
    print(f"{rank}. {user_id:<10} Score: {score:.4f}")

# What matters for similarity search/text ranking is the relative order of the scores instead of the absolute values.