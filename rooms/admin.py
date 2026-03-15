from django.contrib import admin

from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "price_per_day", "capacity")
    search_fields = ("name",)
    ordering = ("name",)
    