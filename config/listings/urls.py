from rest_framework.routers import DefaultRouter
from .views import ListingViewSet

router = DefaultRouter()
router.register("listings", ListingViewSet, basename="listing")
router.register("listings_types", ListingViewSet, basename="listings_type")

urlpatterns = router.urls