from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductsStoreView, ProductDetail, RegisterClient, LogoutClient, LoginClient, CartView, ContinueToPayment, OrderView, UpdateOrderStatus, CreatePreference, PaymentStatus, WebhookView, ProductPanel, CouponPanel, ChangePasswordClient, PasswordResetRequestClient, PasswordResetClient, RequestSupport, SendSupportMessage

router = DefaultRouter()
router.register(r'products', ProductPanel, basename='products')
router.register(r'coupons', CouponPanel, basename='coupons')

urlpatterns = [
    path('store/', ProductsStoreView.as_view(), name='store'),

    path('product/', include([
        path('<int:pk>/', include([
            path('detail/<slug:slug>/', ProductDetail.as_view(), name='detail'),
        ]))

        ])),

    path('user/', include([
        path('register/', RegisterClient.as_view(), name='register'),
        path('logout/', LogoutClient.as_view(), name='logout'),
        path('login/', LoginClient.as_view(), name='login'),
        path('change/', ChangePasswordClient.as_view(), name='change'),
        path('reset/request/', PasswordResetRequestClient.as_view(), name='reset/request'),
        path('reset/', PasswordResetClient.as_view(), name='reset')    
        ])),

    path('payment/', include([
        path('continue/', ContinueToPayment.as_view(), name='continue'),
        path('create/', CreatePreference.as_view(), name="create"),
        path('status/<str:state>/', PaymentStatus.as_view(), name='status')
        ])),

    path('admin/panel/', include([
        path('', include(router.urls)),
        path('order/<int:pk>/status/update/', UpdateOrderStatus.as_view(), name='update')
    ])),

    path('support/', include([
        path('request/', RequestSupport.as_view(), name='request'),
        path('send/', SendSupportMessage.as_view(), name='send')
    ])),

    path('order/', OrderView.as_view(), name='order'),

    path('cart/items/<int:pk>/', CartView.as_view(), name='cart'),

    path('webhook/', WebhookView.as_view(), name='webhook'),

]
