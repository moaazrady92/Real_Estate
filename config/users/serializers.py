from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class BuyerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email",
            "phone_number", "password", "password_confirm",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data, role="buyer")
        user.set_password(password)
        user.save()
        return user


class SellerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "phone_number",
            "national_id", "password", "password_confirm",
        ]

    def validate_national_id(self, value):
        if not value:
            raise serializers.ValidationError("National ID is required for sellers.")
        if not value.isdigit() or len(value) != 14:
            raise serializers.ValidationError("National ID must be exactly 14 digits.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data, role="seller")
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    listings = serializers.SerializerMethodField()
    favorites = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "display_name",
            "bio", "profile_picture", "email", "phone_number",
            "role", "national_id", "listings", "favorites",
        ]
        read_only_fields = ["id", "email", "role", "national_id"]

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return obj.profile_picture.url

    def get_listings(self, obj):
        if obj.role != "seller":
            return []
        from listings.serializers import ListingSerializer
        qs = obj.listings.filter(is_active=True)
        return ListingSerializer(qs, many=True, context=self.context).data

    def get_favorites(self, obj):
        if obj.role != "buyer":
            return []
        from favorites.serializers import FavoriteSerializer
        qs = obj.favorites.select_related("listing").all()
        return FavoriteSerializer(qs, many=True, context=self.context).data


class PublicProfileSerializer(serializers.ModelSerializer):
    """For viewing another user's profile — limited fields only."""
    listings = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "display_name",
            "bio", "profile_picture", "role", "listings",
        ]

    def get_profile_picture(self, obj):
        if not obj.profile_picture:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return obj.profile_picture.url

    def get_listings(self, obj):
        if obj.role != "seller":
            return []
        from listings.serializers import ListingSerializer
        qs = obj.listings.filter(is_active=True)
        return ListingSerializer(qs, many=True, context=self.context).data