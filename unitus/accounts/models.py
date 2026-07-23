from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Avatar(models.Model):
    icon_name = models.CharField(max_length=50)
    image_url_path = models.CharField(max_length=255)

    def __str__(self):
        return self.icon_name


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is needed!")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
    
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
       
        extra_fields.setdefault('birth_year', 2000)        
        extra_fields.setdefault('gender', 'Not Specified')
        extra_fields.setdefault('first_name', 'Admin')     
        extra_fields.setdefault('last_name', 'System')  
        extra_fields.setdefault('system_role', 'Admin') 

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class SystemRole(models.TextChoices):
        ADMIN = 'ADMIN'
        USER = 'USER'

    class Gender(models.TextChoices):
        MALE = 'MALE'
        FEMALE = 'FEMALE'
        OTHER = 'OTHER'
        NOT_SPECIFIED = 'NOT_SPECIFIED'

    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE'
        SUSPENDED = 'SUSPENDED'
        BANNED = 'BANNED'

    system_role = models.CharField(max_length=10, choices=SystemRole.choices, default=SystemRole.USER)
    username = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.NOT_SPECIFIED)
    birth_year = models.SmallIntegerField()
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=100, unique=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    education_background = models.TextField(null=True, blank=True)
    about_me = models.TextField(null=True, blank=True)
    avatar_icon = models.ForeignKey(Avatar, on_delete=models.SET_NULL, null=True, blank=True)
    is_open_to_work = models.BooleanField(default=False, db_index=True)
    account_status = models.CharField(max_length=10, choices=AccountStatus.choices, default=AccountStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    is_staff = models.BooleanField(default=False)   
    is_active = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username


class UserPrivacySettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    show_phone = models.BooleanField(default=False)
    show_email = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    show_birth_year = models.BooleanField(default=True)
    show_education_background = models.BooleanField(default=True)
    show_gender = models.BooleanField(default=True)
