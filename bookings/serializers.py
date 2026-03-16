from rest_framework import serializers
from datetime import date

from rooms.serializers import RoomSerializer
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    room_detail = RoomSerializer(source="room", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "room",
            "room_detail",
            "check_in",
            "check_out",
            "status",
            "created_at",
        )
        read_only_fields = ("status", "created_at")

    def validate(self, attrs: dict) -> dict:
        check_in: date = attrs["check_in"]
        check_out: date = attrs["check_out"]

        if check_in >= check_out:
            raise serializers.ValidationError("Check out must be later than check in")

        if check_in <= date.today():
            raise serializers.ValidationError("Check in cannot be in the past")

        conflict_bookings = Booking.objects.filter(
            room=attrs["room"],
            status=Booking.Status.ACTIVE,
            check_in__lt=check_in,
            check_out__gt=check_out,
        )

        # if booking already exists
        if self.instance:
            conflict_bookings = conflict_bookings.exclude(
                pk=self.instance.pk
            )  # for put/patch operations

        if conflict_bookings.exists():
            raise serializers.ValidationError("This booking is already taken")

        return attrs

    def create(self, validated_data: dict) -> Booking:
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BookingAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ("id", "user", "room", "check_in", "check_out", "status", "created_at")
        read_only_fields = ("created_at",)
