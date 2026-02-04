
from django.urls import path, include
from .views import RequestSupport, SendSupportMessage

urlpatterns = [
    path('', include([
        path('request/', RequestSupport.as_view(), name='request'),
        path('send/', SendSupportMessage.as_view(), name='send')
])),
]