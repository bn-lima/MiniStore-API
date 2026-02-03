from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContinueToPayment, CreatePreference, PaymentStatus, WebhookView


urlpatterns = [
    path('', include([
        path('continue/', ContinueToPayment.as_view(), name='continue'),
        path('create/', CreatePreference.as_view(), name="create"),
        path('status/<str:state>/', PaymentStatus.as_view(), name='status')
        ])),

    path('webhook/', WebhookView.as_view(), name='webhook'),
]