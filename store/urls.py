from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductsStoreView, ProductDetail, CartView, OrderView, UpdateOrderStatus, ProductPanel, CouponPanel, RequestSupport, SendSupportMessage, SupportRequests, ReplySupportMessage

router = DefaultRouter()
router.register(r'products', ProductPanel, basename='products')
router.register(r'coupons', CouponPanel, basename='coupons')

urlpatterns = [
    path('store/', ProductsStoreView.as_view(), name='store'),

    path('product/', include([
            path('detail/<slug:slug>/', ProductDetail.as_view(), name='detail'),
        ])),

    path('control/panel/', include([
        path('', include(router.urls)),

        path('orders/', include([
            path('', UpdateOrderStatus.as_view(), name='orders'),
            path('<int:pk>/status/', UpdateOrderStatus.as_view(), name='status')
        ])),
        
        path('support/', include([
            path('requests/', SupportRequests.as_view(), name='requests'),
            path('<int:pk>/reply/', ReplySupportMessage.as_view(), name='reply')
        ]))
    ])),

    path('support/', include([
        path('request/', RequestSupport.as_view(), name='request'),
        path('send/', SendSupportMessage.as_view(), name='send')
    ])),

    path('order/', OrderView.as_view(), name='order'),

    path('cart/items/<int:pk>/', CartView.as_view(), name='cart'),

]
