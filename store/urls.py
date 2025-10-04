from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductsStoreView, CartViewSet, ProductDetail, RegisterClient, LogoutClient, LoginClient, ChangePasswordClient, PasswordResetRequestClient, PasswordResetClient

router = DefaultRouter()
router.register(r'cart', CartViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('store/', ProductsStoreView.as_view(), name='store'),

    path('product/', include([
        path('<int:pk>/<slug:slug>/', ProductDetail.as_view())
    ])),

    path('user/', include([
        path('register/', RegisterClient.as_view(), name='register'),
        path('logout/', LogoutClient.as_view(), name='logout'),
        path('login/', LoginClient.as_view(), name='login'),

        path('change_password/', ChangePasswordClient.as_view(), name='change_password/'),
        path('password_reset_request/', PasswordResetRequestClient.as_view(), name='password_reset_request'),
        path('password_reset/', PasswordResetClient.as_view(), name='password_reset')
    ])),
]
