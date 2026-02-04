from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductPanel, CouponPanel, UpdateOrderStatus, SupportRequests, ReplySupportMessage, PendingOrdersList

router = DefaultRouter()
router.register(r'products', ProductPanel, basename='products')
router.register(r'coupons', CouponPanel, basename='coupons')

urlpatterns = [
    path('', include([
        path('', include(router.urls)),

        path('orders/', include([
            path('', PendingOrdersList.as_view(), name='orders'),
            path('<int:pk>/status/', UpdateOrderStatus.as_view(), name='status')
        ])),
        
        path('support/', include([
            path('requests/', SupportRequests.as_view(), name='requests'),
            path('<int:pk>/reply/', ReplySupportMessage.as_view(), name='reply')
        ]))
    ])),
]