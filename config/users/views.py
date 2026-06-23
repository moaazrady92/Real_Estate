from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from .serializers import (
    BuyerRegisterSerializer, SellerRegisterSerializer,
    UserSerializer, PublicProfileSerializer
)

User = get_user_model()


class BuyerRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = BuyerRegisterSerializer
    permission_classes = [permissions.AllowAny]


class SellerRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SellerRegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes_from_settings = True

    def get_object(self):
        return self.request.user


class PublicProfileView(generics.RetrieveAPIView):
    """Anyone can view a user's public profile."""
    queryset = User.objects.all()
    serializer_class = PublicProfileSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=205)
        except (KeyError, TokenError):
            return Response({"detail": "Invalid or missing refresh token."}, status=400)