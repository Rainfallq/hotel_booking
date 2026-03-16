from rest_framework import generics, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import QuerySet
from datetime import date

from .models import Room
from .filters import RoomFilter
from .serializers import RoomSerializer
from bookings.models import Booking


class RoomListView(generics.ListAPIView):
    serializer_class = RoomSerializer
    permission_classes = (permissions.AllowAny,)
    filterset_class = RoomFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["price_per_day", "capacity"]
    ordering = ["name"]

    @extend_schema(
        parameters=[
            OpenApiParameter("check_in", str, description="Check-in date (YYYY-MM-DD)"),
            OpenApiParameter(
                "check_out", str, description="Check-out date (YYYY-MM-DD)"
            ),
            OpenApiParameter("min_price", float, description="Minimum price per day"),
            OpenApiParameter("max_price", float, description="Maximum price per day"),
            OpenApiParameter("capacity", int, description="Exact capacity"),
            OpenApiParameter("min_capacity", int, description="Minimum capacity"),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by: price_per_day, capacity (use - for descending)",
            ),
        ]
    )
    def get_queryset(self) -> QuerySet:
        queryset = Room.objects.all()
        check_in = self.request.query_params.get("check_in")
        check_out = self.request.query_params.get("check_out")

        if check_in and check_out:
            try:
                check_in_date = date.fromisoformat("check_in")
                check_out_date = date.fromisoformat("check_out")
            except ValueError:
                return queryset

            booker_room_ids = Booking.objects.filter(
                status=Booking.Status.ACTIVE,
                check_in__lt=check_out_date,
                check_out__gt=check_in_date,
            ).values_list("room_id", flat=True)

            queryset = queryset.exclude(id__in=booker_room_ids)

        return queryset


class RoomDetailView(generics.RetrieveAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = (permissions.AllowAny,)
