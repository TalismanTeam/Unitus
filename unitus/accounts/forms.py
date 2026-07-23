# accounts/forms.py
import re
from datetime import date

from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from .models import User

# ------------------------------------------------------------------
# الگوهای مجاز (Regex Patterns)
# ------------------------------------------------------------------
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_.]{3,50}$')
# فقط حروف انگلیسی، عدد، آندرلاین و نقطه، بین ۳ تا ۵۰ کاراکتر

PHONE_REGEX = re.compile(r'^\+?[0-9]{9,15}$')
# عدد، با یا بدون + در ابتدا (فرمت بین‌المللی)، بین ۹ تا ۱۵ رقم

MIN_BIRTH_YEAR = 1940
MAX_AGE_YEAR = date.today().year - 10   # حداقل سن ۱۰ سال


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Repeat password",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'gender', 'birth_year', 'phone_number', 'location',
            'education_background', 'avatar_icon',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فیلدهای اختیاری طبق ساختار دیتابیس (nullable در مدل)
        self.fields['phone_number'].required = False
        self.fields['location'].required = False
        self.fields['education_background'].required = False
        self.fields['avatar_icon'].required = False

    # ---------------- فیلدهای تکی ----------------

    def clean_username(self):
        username = self.cleaned_data['username'].strip()

        if not USERNAME_REGEX.match(username):
            raise ValidationError(
                "Username must be 3-50 characters and contain only letters, numbers, dots, or underscores."
            )

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is not available.")

        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        # نکته: خود forms.EmailField/models.EmailField یک اعتبارسنجی فرمت پایه انجام می‌ده،
        # اینجا فقط یکتایی و normalize کردن (lowercase) رو اضافه می‌کنیم.

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email has already been used.")

        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not phone:
            return phone   # فیلد اختیاریه، اگه خالیه مشکلی نیست

        phone = phone.strip()

        if not PHONE_REGEX.match(phone):
            raise ValidationError(
                "Enter a valid phone number (9-15 digits, optionally starting with +)."
            )

        if User.objects.filter(phone_number=phone).exists():
            raise ValidationError("This phone number has already been used.")

        return phone

    def clean_birth_year(self):
        birth_year = self.cleaned_data['birth_year']

        if birth_year < MIN_BIRTH_YEAR or birth_year > MAX_AGE_YEAR:
            raise ValidationError(
                f"Enter a valid birth year between {MIN_BIRTH_YEAR} and {MAX_AGE_YEAR}."
            )

        return birth_year

    # ---------------- اعتبارسنجی کل فرم (رمزها + شباهت به اطلاعات کاربر) ----------------

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2:
            if password1 != password2:
                self.add_error('password2', "Passwords do not match.")
            else:
                # یک نمونه‌ی موقت از User می‌سازیم (بدون save) تا
                # UserAttributeSimilarityValidator بتونه پسورد رو با
                # username/email/first_name/last_name مقایسه کنه
                temp_user = User(
                    username=cleaned_data.get('username', ''),
                    email=cleaned_data.get('email', ''),
                    first_name=cleaned_data.get('first_name', ''),
                    last_name=cleaned_data.get('last_name', ''),
                )
                try:
                    password_validation.validate_password(password2, user=temp_user)
                except ValidationError as e:
                    self.add_error('password2', e)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])   # هرگز پسورد خام ذخیره نمی‌شه
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    # می‌تونه یوزرنیم یا ایمیل باشه — منطق تشخیص در view هست
    identifier = forms.CharField(label="Username or Email")
    password = forms.CharField(label="Password", widget=forms.PasswordInput)