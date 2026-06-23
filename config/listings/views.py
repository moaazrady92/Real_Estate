from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Listing, ListingImage
from .serializers import ListingSerializer, ListingCreateSerializer
from .filters import ListingFilter


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsSellerOrReadOnly(permissions.BasePermission):
    """Only sellers can create listings."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == "seller"


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.filter(is_active=True)
    permission_classes = [IsSellerOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ListingFilter
    search_fields = ["title", "description", "address", "city"]

    def get_serializer_class(self):
        if self.action == "create":
            return ListingCreateSerializer
        return ListingSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_listings(self, request):
        listings = Listing.objects.filter(owner=request.user, is_active=True)
        serializer = self.get_serializer(listings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def cities(self, request):
        return Response([
            {"value": value, "label": label}
            for value, label in Listing.CITY_CHOICES
        ])