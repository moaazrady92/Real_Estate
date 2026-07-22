import logging
import requests as http_requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Avg
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
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


# ──────────────────────────────────────────────────
# Template-based views
# ──────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")
        role = request.POST.get("role", "buyer")
        national_id = request.POST.get("national_id", "").strip()

        errors = {}
        if not first_name:
            errors["first_name"] = ["First name is required."]
        if not last_name:
            errors["last_name"] = ["Last name is required."]
        if not email:
            errors["email"] = ["Email is required."]
        elif User.objects.filter(email=email).exists():
            errors["email"] = ["A user with this email already exists."]
        if not phone_number:
            errors["phone_number"] = ["Phone number is required."]
        if len(password) < 8:
            errors["password"] = ["Password must be at least 8 characters."]
        if password != password_confirm:
            errors["password_confirm"] = ["Passwords do not match."]
        if role == "seller" and not national_id:
            errors["national_id"] = ["National ID is required for sellers."]
        if role == "seller" and national_id and (not national_id.isdigit() or len(national_id) != 14):
            errors["national_id"] = ["National ID must be exactly 14 digits."]

        if not errors:
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                role=role,
                national_id=national_id,
            )
            user.set_password(password)
            user.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            logger.info("New user registered: %s (%s)", email, role)
            return redirect("home")

        return render(request, "accounts/register.html", {
            "form": type("Form", (), {"errors": errors, "first_name": type("F", (), {"value": lambda: first_name})(), "last_name": type("F", (), {"value": lambda: last_name})(), "email": type("F", (), {"value": lambda: email})(), "phone_number": type("F", (), {"value": lambda: phone_number})(), "national_id": type("F", (), {"value": lambda: national_id})(), "password": type("F", (), {"value": lambda: ""})(), "password_confirm": type("F", (), {"value": lambda: ""})()}),
        })

    return render(request, "accounts/register.html")


from django.views.decorators.http import require_POST


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Please enter both email and password.")
            return render(request, "accounts/login.html", {
                "form": type("F", (), {"errors": False, "email": type("E", (), {"value": lambda: email})(), "password": type("P", (), {"value": lambda: ""})()})(),
            })

        try:
            user = authenticate(request, username=email, password=password)
        except Exception as e:
            logger.error("Authentication error for %s: %s", email, e)
            user = None

        if user is not None:
            login(request, user)
            logger.info("User logged in: %s", email)
            next_url = request.GET.get("next", "")
            if next_url:
                return redirect(next_url)
            return redirect("home")

        messages.error(request, "Invalid email or password.")
        return render(request, "accounts/login.html", {
            "form": type("F", (), {"errors": True, "email": type("E", (), {"value": lambda: email})(), "password": type("P", (), {"value": lambda: ""})()})(),
        })

    return render(request, "accounts/login.html")


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        user.display_name = request.POST.get("display_name", user.display_name).strip()
        user.whatsapp = request.POST.get("whatsapp", user.whatsapp).strip()
        user.bio = request.POST.get("bio", user.bio).strip()

        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    from favorites.models import Favorite
    favorites = Favorite.objects.filter(user=request.user).select_related("listing")
    for fav in favorites:
        fav.listing.is_favorited = True

    return render(request, "profile/me.html", {
        "favorites": favorites,
    })


def public_profile_view(request, pk):
    profile_user = get_object_or_404(User, pk=pk)
    listings = profile_user.listings.filter(is_active=True).prefetch_related("images")

    listings_count = listings.count()
    avg_rating = listings.exclude(rating__isnull=True).aggregate(
        avg=Avg("rating")
    )["avg"]
    if avg_rating:
        avg_rating = round(avg_rating, 1)

    city_counts = {}
    for listing in listings:
        if listing.city:
            city_counts[listing.city] = city_counts.get(listing.city, 0) + 1

    return render(request, "profile/public.html", {
        "profile_user": profile_user,
        "listings": listings,
        "listings_count": listings_count,
        "avg_rating": avg_rating,
        "city_counts": city_counts,
    })


def password_reset_view(request):
    email_from_get = request.GET.get("email", "")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "request_code":
            email = request.POST.get("email", "").strip()
            if not email:
                messages.error(request, "Please enter your email address.")
                return render(request, "accounts/forgot_password.html")

            if not User.objects.filter(email=email).exists():
                messages.error(request, "No account found with this email.")
                return render(request, "accounts/forgot_password.html")

            expiry_minutes = getattr(settings, "PASSWORD_RESET_CODE_EXPIRY_MINUTES", 10)
            reset_code = PasswordResetCode.create_code(email, expiry_minutes=expiry_minutes)

            try:
                send_mail(
                    subject="Your Password Reset Code",
                    message=f"Your password reset code is: {reset_code.code}\nThis code expires in {expiry_minutes} minutes.\n\nReset your password here: {request.build_absolute_uri(reverse('password_reset'))}?email={email}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                logger.info("Password reset code sent to %s", email)
            except Exception as e:
                logger.error("Failed to send password reset email to %s: %s", email, e)
                messages.error(request, "Failed to send email. Please try again.")
                return render(request, "accounts/forgot_password.html")

            messages.success(request, f"Reset code sent to {email}. Check your inbox.")
            return render(request, "accounts/forgot_password.html", {"sent_email": email})

        elif action == "confirm_reset":
            email = request.POST.get("email", "").strip()
            code = request.POST.get("code", "").strip()
            new_password = request.POST.get("new_password", "")

            if not email or not code or not new_password:
                messages.error(request, "All fields are required.")
                return redirect(f"{reverse('password_reset')}?email={email}")

            try:
                reset_code = PasswordResetCode.objects.filter(
                    email=email, code=code, used=False
                ).latest("created_at")
            except PasswordResetCode.DoesNotExist:
                messages.error(request, "Invalid or expired code.")
                return redirect(f"{reverse('password_reset')}?email={email}")

            if not reset_code.is_valid():
                messages.error(request, "This code has expired. Request a new one.")
                return redirect(f"{reverse('password_reset')}?email={email}")

            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters.")
                return redirect(f"{reverse('password_reset')}?email={email}")

            user = get_object_or_404(User, email=email)
            user.set_password(new_password)
            user.save()

            reset_code.used = True
            reset_code.save()

            logger.info("Password reset completed for %s", email)
            messages.success(request, "Password reset successful! You can now log in.")
            return redirect("login")

    return render(request, "accounts/forgot_password.html", {
        "sent_email": email_from_get,
    })


def google_login_view(request):
    client_id = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]
    redirect_uri = request.build_absolute_uri("/auth/google/callback/")
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


def google_callback_view(request):
    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google authentication failed.")
        return redirect("login")

    token_data = _exchange_code_for_google(request)
    if "error" in token_data:
        logger.error("Google token exchange failed: %s", token_data)
        messages.error(request, "Google authentication failed.")
        return redirect("login")

    user_info = _get_google_user_info(token_data.get("access_token", ""))
    if not user_info:
        messages.error(request, "Failed to get user info from Google.")
        return redirect("login")

    email = user_info.get("email")
    if not email:
        messages.error(request, "Email not provided by Google.")
        return redirect("login")

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

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("home")


def _exchange_code_for_google(request):
    redirect_uri = request.build_absolute_uri("/auth/google/callback/")
    data = {
        "code": request.GET.get("code"),
        "client_id": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"],
        "client_secret": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["secret"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    resp = http_requests.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
    return resp.json()


def _get_google_user_info(access_token):
    resp = http_requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()
    return None