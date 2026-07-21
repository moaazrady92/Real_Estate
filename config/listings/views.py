from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.db.models.expressions import OrderBy
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


# ──────────────────────────────────────────────────
# Template-based views
# ──────────────────────────────────────────────────

def listing_list(request):
    listings = Listing.objects.filter(is_active=True).prefetch_related("images").annotate(
        image_count=Count("images")
    )

    listing_type = request.GET.get("listing_type", "for_sale")
    city = request.GET.get("city", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sources = request.GET.getlist("source", [])
    sort = request.GET.get("sort", "-created_at")

    if listing_type:
        listings = listings.filter(listing_type=listing_type)
    if city:
        listings = listings.filter(city__iexact=city)
    if min_price:
        listings = listings.filter(price__gte=min_price)
    if max_price:
        listings = listings.filter(price__lte=max_price)
    if sources:
        listings = listings.filter(source__in=sources)

    ordering = []
    if sort in ["price", "-price", "-created_at", "created_at"]:
        ordering.append(sort)
    ordered = listings.order_by(OrderBy(F("image_count"), descending=True), *ordering)

    paginator = Paginator(ordered, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    if request.user.is_authenticated:
        from favorites.models import Favorite
        fav_ids = set(Favorite.objects.filter(user=request.user).values_list("listing_id", flat=True))
        for listing in page_obj:
            listing.is_favorited = listing.pk in fav_ids

    all_cities = (
        Listing.objects.filter(is_active=True)
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    all_sources = ["manual", "aqarmap", "bayut", "nawy"]

    context = {
        "listings": page_obj,
        "page_obj": page_obj,
        "cities": [c for c in all_cities if c],
        "sources": all_sources,
        "selected_sources": sources if sources else all_sources,
        "title": "Properties for Rent" if listing_type == "for_rent" else "Properties for Sale",
    }
    return render(request, "listings/list.html", context)


def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.filter(is_active=True).prefetch_related("images").select_related("owner"),
        pk=pk,
    )

    if request.user.is_authenticated:
        from favorites.models import Favorite
        listing.is_favorited = Favorite.objects.filter(
            user=request.user, listing=listing
        ).exists()

    return render(request, "listings/detail.html", {"listing": listing})


@login_required
def create_listing(request):
    if request.user.role != "seller":
        messages.error(request, "Only sellers can post listings.")
        return redirect("home")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        price = request.POST.get("price", "").strip()
        listing_type = request.POST.get("listing_type", "for_sale")
        city = request.POST.get("city", "")
        address = request.POST.get("address", "").strip()
        bedrooms = request.POST.get("bedrooms", "")
        bathrooms = request.POST.get("bathrooms", "")
        area = request.POST.get("area", "")
        description = request.POST.get("description", "").strip()

        errors = {}
        if not title:
            errors["title"] = "Title is required."
        if not price:
            errors["price"] = "Price is required."
        if not city:
            errors["city"] = "City is required."

        if not errors:
            listing = Listing.objects.create(
                title=title,
                price=price,
                listing_type=listing_type,
                city=city,
                address=address,
                bedrooms=bedrooms or None,
                bathrooms=bathrooms or None,
                area=area or None,
                description=description,
                owner=request.user,
                source="manual",
            )

            images = request.FILES.getlist("images")
            for i, image_file in enumerate(images):
                ListingImage.objects.create(
                    listing=listing,
                    image=image_file,
                    is_primary=(i == 0),
                )

            messages.success(request, f"Property '{title}' posted successfully!")
            return redirect("listing_detail", pk=listing.pk)

        return render(request, "listings/create.html", {"errors": errors})

    return render(request, "listings/create.html")
