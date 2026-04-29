from django.urls import path
from .views import hr_dashboard

urlpatterns = [
    path('', hr_dashboard, name='hr_dashboard'),


]