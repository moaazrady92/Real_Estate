from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    BuyerRegisterView, SellerRegisterView,
    MeView, LogoutView, PublicProfileView,
    PasswordResetRequestView, PasswordResetConfirmView,
    GoogleLoginView, GoogleCallbackView,
)

urlpatterns = [
    path("register/buyer/", BuyerRegisterView.as_view(), name="register_buyer"),
    path("register/seller/", SellerRegisterView.as_view(), name="register_seller"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("profile/<int:pk>/", PublicProfileView.as_view(), name="public_profile"),
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("auth/google/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
]