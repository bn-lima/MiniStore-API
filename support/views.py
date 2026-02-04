from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import SupportChannel
from .serializers import SendSupportMessageSerializer, SupportChannelSerializer
from .support_services import get_support_channel

# SUPPORT

class RequestSupport(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        channel, _ = SupportChannel.objects.get_or_create(active=True, user=request.user)
        serializer = SupportChannelSerializer(channel)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class SendSupportMessage(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        channel = get_support_channel(request.user)

        if not channel:
            return Response({"detail": "You do not have an active support channel"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = SendSupportMessageSerializer(data=request.data, context={"channel":channel, "user":request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = SupportChannelSerializer(channel)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
