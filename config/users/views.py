import logging
import requests as http_requests
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from .models import PasswordResetCode
from .serializers import (
    BuyerRegisterSerializer, SellerRegisterSerializer,
    UserSerializer, PublicProfileSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


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


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        expiry_minutes = getattr(settings, "PASSWORD_RESET_CODE_EXPIRY_MINUTES", 10)
        reset_code = PasswordResetCode.create_code(email, expiry_minutes=expiry_minutes)

        try:
            send_mail(
                subject="Your Password Reset Code",
                message=f"Your password reset code is: {reset_code.code}\nThis code expires in {expiry_minutes} minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info("Password reset code sent to %s", email)
        except Exception as e:
            logger.error("Failed to send password reset email to %s: %s", email, e)
            return Response({"detail": "Failed to send email. Please try again."}, status=500)

        return Response({"detail": "Password reset code sent to your email."}, status=200)


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        new_password = serializer.validated_data["new_password"]
        reset_code = serializer.validated_data["reset_code"]

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        reset_code.used = True
        reset_code.save()

        logger.info("Password reset completed for %s", email)
        return Response({"detail": "Password reset successful."}, status=200)


class GoogleLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_id = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]
        redirect_uri = request.build_absolute_uri("/api/users/auth/google/callback/")
        scope = " ".join(settings.SOCIALACCOUNT_PROVIDERS["google"]["SCOPE"])
        access_type = settings.SOCIALACCOUNT_PROVIDERS["google"]["AUTH_PARAMS"]["access_type"]

        auth_url = (
            f"{GOOGLE_AUTH_URL}?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&access_type={access_type}"
        )
        return HttpResponseRedirect(auth_url)


class GoogleCallbackView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.GET.get("code")
        if not code:
            return Response({"detail": "Authorization code missing."}, status=400)

        token_data = self._exchange_code(code)
        if "error" in token_data:
            logger.error("Google token exchange failed: %s", token_data)
            return Response({"detail": "Google authentication failed."}, status=400)

        user_info = self._get_user_info(token_data["access_token"])
        if not user_info:
            return Response({"detail": "Failed to get user info from Google."}, status=400)

        email = user_info.get("email")
        if not email:
            return Response({"detail": "Email not provided by Google."}, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
                "role": "buyer",
                "phone_number": "",
            },
        )

        if created:
            user.set_unusable_password()
            user.save()
            logger.info("New user created via Google: %s", email)
        else:
            logger.info("Existing user logged in via Google: %s", email)

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            },
        })

    def _exchange_code(self, code):
        redirect_uri = self.request.build_absolute_uri("/api/users/auth/google/callback/")
        data = {
            "code": code,
            "client_id": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"],
            "client_secret": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        resp = http_requests.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
        return resp.json()

    def _get_user_info(self, access_token):
        resp = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None