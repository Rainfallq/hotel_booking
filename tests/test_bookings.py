import pytest
from datetime import date, timedelta
from rest_framework.test import APIClient
from tests.conftest import UserFactory, RoomFactory, BookingFactory

BOOKINGS_URL = "/api/bookings/"


def booking_detail_url(pk):
    return f"/api/bookings/{pk}/"


def future(days):
    return str(date.today() + timedelta(days=days))


def past(days):
    return str(date.today() - timedelta(days=days))


@pytest.mark.django_db
class TestBookingCreate:
    """TC12 – TC16"""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.user = UserFactory()
        self.room = RoomFactory()
        self.client.force_authenticate(user=self.user)

    def _payload(self, check_in=None, check_out=None, room=None):
        return {
            "room": (room or self.room).pk,
            "check_in": check_in or future(2),
            "check_out": check_out or future(5),
        }

    def test_valid_booking_returns_201(self):
        """TC12 – Valid booking returns 201 with booking fields."""
        r = self.client.post(BOOKINGS_URL, self._payload(), format="json")
        assert r.status_code == 201
        assert r.data["room"] == self.room.pk
        assert r.data["status"] == "active"
        assert "id" in r.data

    def test_overlap_returns_400(self):
        """TC13 – Overlapping booking must be rejected with 400."""
        BookingFactory(
            user=self.user,
            room=self.room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=6),
        )
        # New booking overlaps with the existing one
        r = self.client.post(
            BOOKINGS_URL,
            self._payload(check_in=future(3), check_out=future(5)),
            format="json",
        )
        assert r.status_code == 400

    def test_adjacent_booking_is_allowed(self):
        """TC13 ext – Booking that starts exactly when another ends is valid."""
        BookingFactory(
            user=self.user,
            room=self.room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=4),
        )
        # Starts on the same day the first booking ends — no overlap
        r = self.client.post(
            BOOKINGS_URL,
            self._payload(check_in=future(4), check_out=future(7)),
            format="json",
        )
        assert r.status_code == 201

    def test_past_check_in_returns_400(self):
        """TC14 – check_in in the past must be rejected."""
        r = self.client.post(
            BOOKINGS_URL,
            self._payload(check_in=past(1), check_out=future(2)),
            format="json",
        )
        assert r.status_code == 400

    def test_check_in_equals_check_out_returns_400(self):
        """TC15 – check_in == check_out must be rejected (zero-length stay)."""
        r = self.client.post(
            BOOKINGS_URL,
            self._payload(check_in=future(2), check_out=future(2)),
            format="json",
        )
        assert r.status_code == 400

    def test_check_out_before_check_in_returns_400(self):
        """TC15 ext – check_out before check_in must also be rejected."""
        r = self.client.post(
            BOOKINGS_URL,
            self._payload(check_in=future(5), check_out=future(2)),
            format="json",
        )
        assert r.status_code == 400

    def test_unauthenticated_returns_401(self):
        """TC16 – Request without token must return 401."""
        unauthenticated = APIClient()
        r = unauthenticated.post(BOOKINGS_URL, self._payload(), format="json")
        assert r.status_code == 401

    def test_missing_room_returns_400(self):
        """Extra – Missing room field must return 400."""
        r = self.client.post(
            BOOKINGS_URL,
            {"check_in": future(2), "check_out": future(5)},
            format="json",
        )
        assert r.status_code == 400

    def test_missing_check_in_returns_400(self):
        """Extra – Missing check_in field must return 400."""
        r = self.client.post(
            BOOKINGS_URL,
            {"room": self.room.pk, "check_out": future(5)},
            format="json",
        )
        assert r.status_code == 400

    def test_cancelled_booking_does_not_block_new_booking(self):
        """Extra – A cancelled booking on the same dates should not cause"""
        BookingFactory(
            user=self.user,
            room=self.room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=5),
            status="cancelled",
        )
        r = self.client.post(
            BOOKINGS_URL,
            self._payload(check_in=future(1), check_out=future(5)),
            format="json",
        )
        assert r.status_code == 201


@pytest.mark.django_db
class TestBookingList:
    """User sees only their own bookings."""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.user = UserFactory()
        self.other = UserFactory()
        self.room = RoomFactory()
        self.client.force_authenticate(user=self.user)

    def test_user_sees_own_bookings_only(self):
        """User's booking list must not contain other users' bookings."""
        BookingFactory(user=self.user, room=self.room)
        BookingFactory(
            user=self.other,
            room=self.room,
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=12),
        )
        r = self.client.get(BOOKINGS_URL)
        assert r.status_code == 200
        assert len(r.data) == 1
        assert r.data[0]["room"] == self.room.pk

    def test_unauthenticated_list_returns_401(self):
        """Unauthenticated GET /bookings/ must return 401."""
        r = APIClient().get(BOOKINGS_URL)
        assert r.status_code == 401


@pytest.mark.django_db
class TestBookingCancel:
    """TC17 – TC19"""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.user = UserFactory()
        self.other = UserFactory()
        self.room = RoomFactory()
        self.client.force_authenticate(user=self.user)
        self.booking = BookingFactory(user=self.user, room=self.room)

    def test_cancel_own_active_booking_returns_204(self):
        """TC17 – DELETE on own active booking returns 204."""
        r = self.client.delete(booking_detail_url(self.booking.pk))
        assert r.status_code == 204

    def test_cancelled_booking_status_is_updated(self):
        """TC17 ext – After cancel, booking status must be 'cancelled'."""
        self.client.delete(booking_detail_url(self.booking.pk))
        self.booking.refresh_from_db()
        assert self.booking.status == "cancelled"

    def test_double_cancel_returns_400(self):
        """TC18 – Cancelling an already-cancelled booking must return 400."""
        self.client.delete(booking_detail_url(self.booking.pk))
        r = self.client.delete(booking_detail_url(self.booking.pk))
        assert r.status_code == 400

    def test_cancel_other_users_booking_returns_404(self):
        """TC19 – Cancelling another user's booking must return 404."""
        other_booking = BookingFactory(
            user=self.other,
            room=self.room,
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=12),
        )
        r = self.client.delete(booking_detail_url(other_booking.pk))
        assert r.status_code == 404

    def test_cancel_nonexistent_booking_returns_404(self):
        """Extra – DELETE on non-existent booking ID must return 404."""
        r = self.client.delete(booking_detail_url(99999))
        assert r.status_code == 404

    def test_unauthenticated_cancel_returns_401(self):
        """Extra – DELETE without token must return 401."""
        r = APIClient().delete(booking_detail_url(self.booking.pk))
        assert r.status_code == 401
