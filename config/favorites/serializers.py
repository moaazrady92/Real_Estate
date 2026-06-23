from rest_framework import serializers
from .models import Favorite
from listings.serializers import ListingSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    listing_detail = ListingSerializer(source="listing", read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "listing", "listing_detail", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        listing = attrs["listing"]
        if Favorite.objects.filter(user=user, listing=listing).exists():
            raise serializers.ValidationError("You already favorited this listing.")
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)