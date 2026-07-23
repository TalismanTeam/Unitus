# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, Avatar, UserPrivacySettings


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'system_role', 'account_status', 'is_active', 'created_at')
    list_filter = ('system_role', 'account_status', 'gender', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('-created_at',)

    # چون از AbstractBaseUser (نه AbstractUser) ارث‌بری کردیم، باید fieldsets رو خودمون بنویسیم
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', (
            {'fields': ('first_name', 'last_name', 'email', 'gender', 'birth_year',
                        'phone_number', 'location', 'education_background', 'avatar_icon')}
        )),
        ('Status', {'fields': ('system_role', 'account_status', 'is_open_to_work',
                                'is_active', 'is_staff', 'is_superuser')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),
    )
    readonly_fields = ('created_at',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


admin.site.register(Avatar)
admin.site.register(UserPrivacySettings)