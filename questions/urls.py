from django.urls import path
from .views import QuestionsView

urlpatterns = [
    path('api/question/', QuestionsView.as_view(), name='question'),
    path('api/question/<int:pk>/', QuestionsView.as_view(), name='question-detail'),
]