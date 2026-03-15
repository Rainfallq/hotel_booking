from django.urls import path

from .views import BookingListCreateView, BookingDetailView


urlpatterns = [
    path("bookings/", BookingListCreateView.as_view(), name="booking_list"),
    path("bookings/<int:pk>/", BookingDetailView.as_view(), name="booking_detail"),
]

