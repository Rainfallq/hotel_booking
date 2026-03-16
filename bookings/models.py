from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Booking(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    check_in = models.DateField()
    check_out = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Для админки, чтобы не создавать не правильные букинги
        overlapping = Booking.objects.filter(
            room=self.room,
            status=Booking.Status.ACTIVE,
            check_in__lt=self.check_out,
            check_out__gt=self.check_in,
        )
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError("Эта комната уже занята на выбранные даты.")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Booking #{self.pk} - {self.room} ({self.check_in} -> {self.check_out})"
