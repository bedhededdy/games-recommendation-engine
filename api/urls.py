from django.urls import path
from .views import LoginView, ValidateView

urlpatterns = [
    path('login', LoginView.as_view()),
    path('validate-id', ValidateView.as_view())
]
