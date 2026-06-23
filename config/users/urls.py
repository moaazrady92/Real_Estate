from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    BuyerRegisterView, SellerRegisterView,
    MeView, LogoutView, PublicProfileView
)

urlpatterns = [
    path("register/buyer/", BuyerRegisterView.as_view(), name="register_buyer"),
    path("register/seller/", SellerRegisterView.as_view(), name="register_seller"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("profile/<int:pk>/", PublicProfileView.as_view(), name="public_profile"),
]