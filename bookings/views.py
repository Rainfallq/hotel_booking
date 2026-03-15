from django.shortcuts import render
from rest_framework import generics, permissions, status

from .models import Booking
from .serializers import BookingSerializer


class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("room")


class BookingDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = BookingSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("room")
    
    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()

        if booking.status == Booking.Status.CANCELLED:
            return Response(
                {"detail": "This Booking is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)
