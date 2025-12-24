from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductsStoreView, ProductDetail, RegisterClient, LogoutClient, LoginClient, AddToCart, DeleteCartItem, Continue_Payment, CreateOrder, UpdateOrderStatus, UserOrdersList, CreatePreference, PaymentStatus, WebhookView, ProductPanel, CouponPanel

router = DefaultRouter()
router.register(r'products', ProductPanel, basename='products')
router.register(r'coupons', CouponPanel, basename='coupons')

urlpatterns = [
    path('store/', ProductsStoreView.as_view(), name='store'),

    path('product/', include([
        path('<int:pk>/add_to_cart/', AddToCart.as_view(), name='add_to_cart'),
        path('<int:pk>/remove_to_cart/', DeleteCartItem.as_view(), name='remove_to_cart'),
        path('<int:pk>/<slug:slug>/', ProductDetail.as_view(), name='product_detail'),
        ])),

    path('user/', include([
        path('register/', RegisterClient.as_view(), name='register'),
        path('logout/', LogoutClient.as_view(), name='logout'),
        path('login/', LoginClient.as_view(), name='login'),     
        ])),

    path('payment/', include([
        path('continue_to_payment/', Continue_Payment.as_view(), name='continue_to_payment'),
        path('create_preference/', CreatePreference.as_view(), name="create_preference"),
        path('payment_status/<str:payment_state>/', PaymentStatus.as_view(), name='payment_status')
        ])),

    path('order/', include([
        path('create_order/', CreateOrder.as_view(), name='create_order'),
        path('<int:pk>/update_status/', UpdateOrderStatus.as_view(), name='update_status'),
        path('order_list/', UserOrdersList.as_view(), name='order_list'),   
        ])),

    path('admin_panel/', include(router.urls)),

    path('webhook/', WebhookView.as_view(), name='webhook'),
]
