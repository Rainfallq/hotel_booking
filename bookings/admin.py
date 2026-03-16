from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "room",
        "check_in",
        "check_out",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email", "room__name")
    ordering = ("-created_at",)
    fields = ("user", "room", "check_in", "check_out", "status")
