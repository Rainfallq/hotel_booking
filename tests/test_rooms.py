import pytest
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from tests.conftest import UserFactory, RoomFactory, BookingFactory

ROOMS_URL = "/api/rooms/"


def room_detail_url(pk):
    return f"/api/rooms/{pk}/"


def future(days):
    return str(date.today() + timedelta(days=days))


@pytest.mark.django_db
class TestRoomList:
    """Basic room listing – no auth required."""

    def setup_method(self):
        self.client = APIClient()

    def test_room_list_returns_200_without_auth(self, db):
        """Rooms endpoint is public – no token needed."""
        RoomFactory.create_batch(3)
        r = self.client.get(ROOMS_URL)
        assert r.status_code == 200
        assert len(r.data) == 3

    def test_room_detail_returns_200_without_auth(self, db):
        """Room detail is public – no token needed."""
        room = RoomFactory()
        r = self.client.get(room_detail_url(room.pk))
        assert r.status_code == 200
        assert r.data["id"] == room.pk

    def test_room_detail_nonexistent_returns_404(self, db):
        """Non-existent room ID must return 404."""
        r = self.client.get(room_detail_url(99999))
        assert r.status_code == 404

    def test_room_fields_present(self, db):
        """Room response must contain id, name, price_per_day, capacity."""
        room = RoomFactory(
            name="Suite 101", price_per_day=Decimal("150.00"), capacity=2
        )
        r = self.client.get(room_detail_url(room.pk))
        assert "id" in r.data
        assert "name" in r.data
        assert "price_per_day" in r.data
        assert "capacity" in r.data


@pytest.mark.django_db
class TestRoomAvailabilityFilter:
    """TC20 – TC21: date-based availability filtering."""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_rooms(self, db):
        self.user = UserFactory()
        self.booked_room = RoomFactory(name="Booked Room")
        self.free_room = RoomFactory(name="Free Room")
        # Create an active booking on booked_room for days 2-6
        BookingFactory(
            user=self.user,
            room=self.booked_room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=6),
        )

    def test_date_filter_excludes_booked_room(self):
        """TC20 – Booked room must not appear in availability results."""
        r = self.client.get(
            ROOMS_URL,
            {"check_in": future(3), "check_out": future(5)},
        )
        assert r.status_code == 200
        ids = [room["id"] for room in r.data]
        assert self.booked_room.pk not in ids
        assert self.free_room.pk in ids

    def test_date_filter_includes_free_room(self):
        """TC20 ext – Free room must appear in availability results."""
        r = self.client.get(
            ROOMS_URL,
            {"check_in": future(7), "check_out": future(10)},
        )
        assert r.status_code == 200
        ids = [room["id"] for room in r.data]
        assert self.free_room.pk in ids
        assert self.booked_room.pk in ids  # not booked on these dates

    def test_cancelled_booking_does_not_block_room(self):
        """Extra – Cancelled booking must not exclude room from results."""
        cancelled_room = RoomFactory(name="Cancelled Booking Room")
        BookingFactory(
            user=self.user,
            room=cancelled_room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=6),
            status="cancelled",
        )
        r = self.client.get(
            ROOMS_URL,
            {"check_in": future(3), "check_out": future(5)},
        )
        ids = [room["id"] for room in r.data]
        assert cancelled_room.pk in ids

    def test_malformed_date_param_returns_full_list(self):
        """TC21 – Malformed date param should not crash; returns all rooms."""
        r = self.client.get(
            ROOMS_URL,
            {"check_in": "not-a-date", "check_out": future(5)},
        )
        assert r.status_code == 200

    def test_only_check_in_provided_returns_full_list(self):
        """TC21 ext – Partial date params (only check_in) returns all rooms."""
        r = self.client.get(ROOMS_URL, {"check_in": future(2)})
        assert r.status_code == 200


@pytest.mark.django_db
class TestRoomPriceFilter:
    """TC22: min_price / max_price filtering."""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_rooms(self, db):
        self.cheap = RoomFactory(
            name="Cheap", price_per_day=Decimal("50.00"), capacity=1
        )
        self.mid = RoomFactory(name="Mid", price_per_day=Decimal("150.00"), capacity=2)
        self.expensive = RoomFactory(
            name="Expensive", price_per_day=Decimal("300.00"), capacity=3
        )

    def test_min_price_filter(self):
        """TC22 – min_price excludes cheaper rooms."""
        r = self.client.get(ROOMS_URL, {"min_price": "100"})
        ids = [room["id"] for room in r.data]
        assert self.cheap.pk not in ids
        assert self.mid.pk in ids
        assert self.expensive.pk in ids

    def test_max_price_filter(self):
        """TC22 – max_price excludes expensive rooms."""
        r = self.client.get(ROOMS_URL, {"max_price": "200"})
        ids = [room["id"] for room in r.data]
        assert self.expensive.pk not in ids
        assert self.cheap.pk in ids
        assert self.mid.pk in ids

    def test_price_range_filter(self):
        """TC22 – Combined min+max returns only rooms in range."""
        r = self.client.get(ROOMS_URL, {"min_price": "100", "max_price": "200"})
        ids = [room["id"] for room in r.data]
        assert self.cheap.pk not in ids
        assert self.expensive.pk not in ids
        assert self.mid.pk in ids


@pytest.mark.django_db
class TestRoomCapacityFilter:
    """TC23: capacity filtering."""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_rooms(self, db):
        self.single = RoomFactory(
            name="Single", capacity=1, price_per_day=Decimal("80.00")
        )
        self.double = RoomFactory(
            name="Double", capacity=2, price_per_day=Decimal("120.00")
        )
        self.suite = RoomFactory(
            name="Suite", capacity=4, price_per_day=Decimal("250.00")
        )

    def test_exact_capacity_filter(self):
        """TC23 – capacity=2 returns only rooms with exactly 2 guests."""
        r = self.client.get(ROOMS_URL, {"capacity": "2"})
        ids = [room["id"] for room in r.data]
        assert self.double.pk in ids
        assert self.single.pk not in ids
        assert self.suite.pk not in ids

    def test_min_capacity_filter(self):
        """TC23 – min_capacity=2 returns rooms with 2 or more guests."""
        r = self.client.get(ROOMS_URL, {"min_capacity": "2"})
        ids = [room["id"] for room in r.data]
        assert self.single.pk not in ids
        assert self.double.pk in ids
        assert self.suite.pk in ids


@pytest.mark.django_db
class TestRoomOrdering:
    """TC24: ordering by price and capacity."""

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_rooms(self, db):
        self.r1 = RoomFactory(name="A", price_per_day=Decimal("300.00"), capacity=3)
        self.r2 = RoomFactory(name="B", price_per_day=Decimal("100.00"), capacity=1)
        self.r3 = RoomFactory(name="C", price_per_day=Decimal("200.00"), capacity=2)

    def test_ordering_price_ascending(self):
        """TC24 – ordering=price_per_day returns rooms sorted cheapest first."""
        r = self.client.get(ROOMS_URL, {"ordering": "price_per_day"})
        prices = [float(room["price_per_day"]) for room in r.data]
        assert prices == sorted(prices)

    def test_ordering_price_descending(self):
        """TC24 – ordering=-price_per_day returns rooms sorted most expensive first."""
        r = self.client.get(ROOMS_URL, {"ordering": "-price_per_day"})
        prices = [float(room["price_per_day"]) for room in r.data]
        assert prices == sorted(prices, reverse=True)

    def test_ordering_capacity_ascending(self):
        """TC24 – ordering=capacity returns rooms sorted by capacity ascending."""
        r = self.client.get(ROOMS_URL, {"ordering": "capacity"})
        capacities = [room["capacity"] for room in r.data]
        assert capacities == sorted(capacities)

    def test_ordering_capacity_descending(self):
        """TC24 – ordering=-capacity returns rooms sorted by capacity descending."""
        r = self.client.get(ROOMS_URL, {"ordering": "-capacity"})
        capacities = [room["capacity"] for room in r.data]
        assert capacities == sorted(capacities, reverse=True)
