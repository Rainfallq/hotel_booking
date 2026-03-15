from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveIntegerField()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
    
