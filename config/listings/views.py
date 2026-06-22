from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly , SAFE_METHODS , BasePermission
from django_filters.rest_framework import DjangoFilterBackend
from .models import Listing
from .serializers import ListingSerializer, ListingCreateSerializer


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.owner == request.user


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["source"]
    search_fields = ["title", "description", "address"]

    def get_serializer_class(self):
        if self.action == "create":
            return ListingCreateSerializer
        return ListingSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()