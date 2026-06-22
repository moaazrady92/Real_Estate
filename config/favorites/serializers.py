from rest_framework import serializers
from .models import Favorite
from listings.serializers import ListingSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    listing_detail = ListingSerializer(source="listing", read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "listing", "listing_detail", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)