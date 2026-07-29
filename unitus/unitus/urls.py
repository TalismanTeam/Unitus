"""
URL configuration for unitus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),

    # Was 'auth/' -> now mounted directly at the root. Every accounts.urls
    # path (users/me, register/, login/, logout/, my-projects/, profile/...)
    # is now reachable with no prefix at all, e.g. /login/ instead of
    # /auth/login/. NOTE: this app is also mounted at '' below, right
    # before reviews.urls — order matters if the two ever define an
    # overlapping path, so accounts is listed first.
    path('', include('accounts.urls')),

    path('projects/', include('projects.urls')),
    path('search/', include('search.urls')),
    path('recommendations/', include('recommendation.urls')),
    path('collaboration/', include('collaboration.urls')),
    path('', include('reviews.urls')),
    path('chat/', include('chat.urls')),
    path('skills/', include('skills.urls')),
    path('moderation/', include('moderation.urls')),

    path('', lambda request: redirect('accounts:login'), name='home'),
]
