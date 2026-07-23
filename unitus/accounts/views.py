# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import RegisterForm, LoginForm
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration completed successfully. You can now sign in.")
            return redirect('accounts:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier'].strip()
            password = form.cleaned_data['password']

            # کاربر می‌تونه با یوزرنیم یا ایمیل لاگین کنه
            username_to_check = identifier
            if '@' in identifier:
                # اگه شبیه ایمیله، یوزرنیم متناظرش رو از دیتابیس پیدا می‌کنیم
                try:
                    matched_user = User.objects.get(email__iexact=identifier)
                    username_to_check = matched_user.username
                except User.DoesNotExist:
                    username_to_check = identifier  # عمداً معتبر نیست، authenticate شکست می‌خوره

            user = authenticate(request, username=username_to_check, password=password)

            if user is None:
                messages.error(request, "Invalid username/email or password.")
            elif user.account_status == User.AccountStatus.BANNED:
                messages.error(request, "This account has been blocked.")
            elif user.account_status == User.AccountStatus.SUSPENDED:
                messages.error(request, "This account has been temporarily suspended.")
            else:
                login(request, user)
                return redirect(next_url or 'accounts:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def dashboard_view(request):
    return render(request, 'accounts/dashboard.html')