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
            "id", "title", "description", "price", "city", "address",
            "listing_type", "source", "source_url", "owner", "owner_username",
            "is_active", "created_at", "updated_at", "images",
        ]
        read_only_fields = ["id", "source", "source_url", "owner", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        is_staff = request and request.user.is_staff
        if not is_staff:
            data.pop("source", None)
            data.pop("source_url", None)
        return data


class ListingCreateSerializer(serializers.ModelSerializer):
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = Listing
        fields = ["title", "description", "price", "city", "address", "listing_type", "uploaded_images"]

    def validate_city(self, value):
        valid = [c[0] for c in Listing.CITY_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(f"Invalid city. Choose from: {valid}")
        return value

    def validate_listing_type(self, value):
        valid = [t[0] for t in Listing.LISTING_TYPE_CHOICES]
        if value not in valid:
            raise serializers.ValidationError("Must be 'for_sale' or 'for_rent'.")
        return value

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