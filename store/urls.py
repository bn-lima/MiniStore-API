from django.urls import path, include
from .views import ProductsStoreView, ProductDetail, CartView, OrderView


urlpatterns = [
    path('store/', ProductsStoreView.as_view(), name='store'),

    path('product/', include([
            path('detail/<slug:slug>/', ProductDetail.as_view(), name='detail'),
        ])),

    path('order/', OrderView.as_view(), name='order'),

    path('cart/items/<int:pk>/', CartView.as_view(), name='cart'),

]
