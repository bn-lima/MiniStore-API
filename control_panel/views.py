from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from store.models import Product, DiscountCoupon, Order
from store.serializers import ProductSerializer
from rest_framework.viewsets import ModelViewSet
from .pagination import AdminOrderListPagination, SupportRequestsPagination
from support.models import SupportChannel
from .serializers import SupportRequestsSerializer, AdminSendSupportMessageSerializer, CouponSerializer, UpdateStatusSerializer, OrderListSerializer
from .services import get_support_channel_by_id
from support.serializers import  SupportChannelSerializer



#CONTROL-PANEL

class ProductPanel(ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

class CouponPanel(ModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CouponSerializer
    queryset = DiscountCoupon.objects.all()

class UpdateOrderStatus(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        order = get_object_or_404(Order, pk=pk)

        if order.status == 'Delivered':
            return Response({"detail": "The order has already been delivered and cannot be updated"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UpdateStatusSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        order = serializer.save()
        return Response({"detail": f"The order status has been updated to {order.status}"}, status=status.HTTP_200_OK)
    

class PendingOrdersList(APIView):
    permission_classes = [permissions.IsAdminUser]
    pagination_class = AdminOrderListPagination

    def get(self, request, *args, **kwargs):
        query = Order.objects.exclude(status = 'Delivered')

        if not query.exists():
            return Response({"detail": "There are no pending orders"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(query, request)

        serializer = OrderListSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)
    
class SupportRequests(APIView):
    permission_classes = [permissions.IsAdminUser]
    pagination_class = SupportRequestsPagination

    def get(self, request, *args, **kwargs):
        query = SupportChannel.objects.filter(active=True)

        if not query.exists():
            return Response({"detail": "There are no active support channels"}, status=status.HTTP_404_NOT_FOUND)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(query, request)

        serializer = SupportRequestsSerializer(page, many=True)

        return  paginator.get_paginated_response(serializer.data)
    
class ReplySupportMessage(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk, *args, **kwargws):
        channel = get_support_channel_by_id(pk)

        if not channel:
            return Response({"detail": "Channel not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AdminSendSupportMessageSerializer(data=request.data, context={'user': request.user, 'channel': channel})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = SupportChannelSerializer(channel)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
