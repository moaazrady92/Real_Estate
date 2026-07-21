from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from users import views as user_views
from listings import views as listing_views

from favorites import views as fav_views

urlpatterns = [
    # Template-based (HTML) URLs
    path("", listing_views.listing_list, name="home"),
    path("listings/<int:pk>/", listing_views.listing_detail, name="listing_detail"),
    path("listings/new/", listing_views.create_listing, name="create_listing"),
    path("login/", user_views.login_view, name="login"),
    path("register/", user_views.register_view, name="register"),
    path("logout/", user_views.logout_view, name="logout"),
    path("profile/", user_views.profile_view, name="profile"),
    path("profile/<int:pk>/", user_views.public_profile_view, name="public_profile"),
    path("password-reset/", user_views.password_reset_view, name="password_reset"),
    path("auth/google/", user_views.google_login_view, name="google_login"),
    path("auth/google/callback/", user_views.google_callback_view, name="google_callback"),
    path("favorites/<int:listing_id>/toggle/", fav_views.toggle_favorite, name="toggle_favorite"),

    # API URLs
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/", include("listings.urls")),
    path("api/", include("favorites.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]