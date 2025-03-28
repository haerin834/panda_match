from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('game/', include('game.urls')),
    path('leaderboard/', include('leaderboard.urls')),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
]