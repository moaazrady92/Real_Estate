from rest_framework import serializers
from .models import Listing, ListingImage


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image", "image_url", "is_primary"]


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id", "title", "description", "price", "address","city",
            "source", "source_url", "owner", "owner_username",
            "is_active", "created_at", "updated_at", "images",
        ]
        read_only_fields = ["id", "source", "source_url", "owner", "created_at", "updated_at"]


class ListingCreateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = Listing
        fields = ["title", "description", "price","city","address", "uploaded_images"]

    def create(self, validated_data):
        images = validated_data.pop("uploaded_images", [])
        request = self.context["request"]
        listing = Listing.objects.create(
            owner=request.user,
            source="manual",
            **validated_data,
        )
        for img in images:
            ListingImage.objects.create(listing=listing, image=img)
        return listing