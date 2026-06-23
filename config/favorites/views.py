from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Favorite
from .serializers import FavoriteSerializer


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related("listing")

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only remove your own favorites.")
        instance.delete()

    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request):
        """Add if not favorited, remove if already favorited."""
        listing_id = request.data.get("listing")
        if not listing_id:
            return Response({"detail": "listing is required."}, status=400)

        existing = Favorite.objects.filter(user=request.user, listing_id=listing_id).first()
        if existing:
            existing.delete()
            return Response({"status": "removed"}, status=200)
        else:
            serializer = self.get_serializer(data={"listing": listing_id})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"status": "added"}, status=201)