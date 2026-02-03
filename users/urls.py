from django.urls import path, include
from .views import RegisterClient, LogoutClient, LoginClient, ChangePasswordClient, PasswordResetRequestClient, PasswordResetClient

urlpatterns = [
path('', include([
        path('register/', RegisterClient.as_view(), name='register'),
        path('logout/', LogoutClient.as_view(), name='logout'),
        path('login/', LoginClient.as_view(), name='login'),
        path('change/', ChangePasswordClient.as_view(), name='change'),
        path('reset/request/', PasswordResetRequestClient.as_view(), name='reset/request'),
        path('reset/', PasswordResetClient.as_view(), name='reset',)    
        ])),
]