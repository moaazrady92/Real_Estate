import django_filters
from .models import Listing


class ListingFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name="city", lookup_expr="exact")
    listing_type = django_filters.CharFilter(field_name="listing_type", lookup_expr="exact")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    source = django_filters.CharFilter(field_name="source", lookup_expr="exact")

    class Meta:
        model = Listing
        fields = ["city", "listing_type", "min_price", "max_price", "source"]