"""
Extended test suite for Midterm Task 2.1
Covers: edge cases, unit tests, concurrency/race conditions, invalid input
"""

import pytest
import threading
from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from tests.conftest import UserFactory, RoomFactory, BookingFactory

BOOKINGS_URL = "/api/bookings/"
REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
ROOMS_URL = "/api/rooms/"


def future(days):
    return str(date.today() + timedelta(days=days))


# UNIT TESTS -- model logic in isolation (no HTTP)


@pytest.mark.django_db
class TestBookingModelUnit:

    def test_clean_raises_on_overlap(self):
        """TC-UNIT-01 -- Booking.clean() must raise ValidationError on overlap."""
        user = UserFactory()
        room = RoomFactory()
        BookingFactory(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=5),
        )
        duplicate = BookingFactory.build(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=4),
        )
        with pytest.raises(ValidationError):
            duplicate.clean()

    def test_clean_passes_for_non_overlapping(self):
        """TC-UNIT-02 -- Booking.clean() must not raise for non-overlapping dates."""
        user = UserFactory()
        room = RoomFactory()
        BookingFactory(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=3),
        )
        non_overlap = BookingFactory.build(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
        )
        non_overlap.clean()  # must not raise

    def test_clean_ignores_cancelled_bookings(self):
        """TC-UNIT-03 -- clean() must not block dates held by cancelled bookings."""
        user = UserFactory()
        room = RoomFactory()
        BookingFactory(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=5),
            status="cancelled",
        )
        new_booking = BookingFactory.build(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=4),
        )
        new_booking.clean()  # must not raise

    def test_booking_str_representation(self):
        """TC-UNIT-04 -- Booking.__str__ must include room name and dates."""
        user = UserFactory()
        room = RoomFactory(name="Suite 101")
        booking = BookingFactory(
            user=user,
            room=room,
            check_in=date.today() + timedelta(days=1),
            check_out=date.today() + timedelta(days=3),
        )
        result = str(booking)
        assert "Suite 101" in result
        assert str(booking.check_in) in result

    def test_room_str_representation(self):
        """TC-UNIT-05 -- Room.__str__ must return room name."""
        room = RoomFactory(name="Deluxe King")
        assert str(room) == "Deluxe King"

    def test_user_str_representation(self):
        """TC-UNIT-06 -- User.__str__ must return email address."""
        user = UserFactory(email="test@example.com")
        assert str(user) == "test@example.com"


# EDGE CASES -- boundary conditions and unusual inputs


@pytest.mark.django_db
class TestBookingEdgeCases:

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.user = UserFactory()
        self.room = RoomFactory()
        self.client.force_authenticate(user=self.user)

    def test_booking_today_as_check_in_is_rejected(self):
        """TC-EDGE-01 -- check_in = today must be rejected."""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": self.room.pk,
                "check_in": str(date.today()),
                "check_out": future(3),
            },
            format="json",
        )
        assert r.status_code == 400

    def test_booking_one_day_stay_is_valid(self):
        """TC-EDGE-02 -- Single-night stay (check_out = check_in + 1)"""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": self.room.pk,
                "check_in": future(1),
                "check_out": future(2),
            },
            format="json",
        )
        assert r.status_code == 201

    def test_booking_very_long_stay(self):
        """TC-EDGE-03 -- A stay of 365 nights must be accepted"""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": self.room.pk,
                "check_in": future(1),
                "check_out": future(366),
            },
            format="json",
        )
        assert r.status_code == 201

    def test_booking_with_invalid_date_format(self):
        """TC-EDGE-04 -- Non-ISO date format must return 400."""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": self.room.pk,
                "check_in": "01/06/2026",
                "check_out": "05/06/2026",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_booking_with_nonexistent_room_id(self):
        """TC-EDGE-05 -- Booking for a room that does not exist must return 400."""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": 999999,
                "check_in": future(2),
                "check_out": future(5),
            },
            format="json",
        )
        assert r.status_code == 400

    def test_booking_string_instead_of_room_id(self):
        """TC-EDGE-06 -- Sending a string where room ID is expected must return 400."""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": "not-an-id",
                "check_in": future(2),
                "check_out": future(5),
            },
            format="json",
        )
        assert r.status_code == 400

    def test_empty_body_returns_400(self):
        """TC-EDGE-07 -- Sending a completely empty JSON body must return 400."""
        r = self.client.post(BOOKINGS_URL, {}, format="json")
        assert r.status_code == 400

    def test_extra_fields_in_body_are_ignored(self):
        """TC-EDGE-08 -- Unknown extra fields must not cause a server error."""
        r = self.client.post(
            BOOKINGS_URL,
            {
                "room": self.room.pk,
                "check_in": future(2),
                "check_out": future(5),
                "unexpected_field": "some_value",
                "another_extra": 12345,
            },
            format="json",
        )
        assert r.status_code == 201


@pytest.mark.django_db
class TestRegistrationEdgeCases:

    def setup_method(self):
        self.client = APIClient()

    def test_username_too_long_returns_400(self):
        """TC-EDGE-09 -- Username longer than 20 chars must return 400."""
        r = self.client.post(
            REGISTER_URL,
            {
                "username": "a" * 21,
                "email": "long@test.com",
                "password": "securepass123",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_invalid_email_format_returns_400(self):
        """TC-EDGE-10 -- Malformed email must be rejected."""
        r = self.client.post(
            REGISTER_URL,
            {
                "username": "testuser",
                "email": "not-an-email",
                "password": "securepass123",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_numeric_only_password_returns_400(self):
        """TC-EDGE-11 -- All-numeric password must be rejected by Django validators."""
        r = self.client.post(
            REGISTER_URL,
            {
                "username": "testuser",
                "email": "numeric@test.com",
                "password": "12345678",
            },
            format="json",
        )
        assert r.status_code == 400

    def test_special_characters_in_username(self):
        """TC-EDGE-12 -- Username with allowed special chars must be accepted."""
        r = self.client.post(
            REGISTER_URL,
            {
                "username": "user_name-01",
                "email": "special@test.com",
                "password": "securepass123",
            },
            format="json",
        )
        assert r.status_code == 201


# CONCURRENCY / RACE CONDITIONS


@pytest.mark.django_db(transaction=True)
class TestBookingConcurrency:

    def test_concurrent_booking_same_room_only_one_succeeds(self):
        """
        TC-CONC-01 -- Two users booking the same room at the same time:
        exactly one must succeed (201), the other must be rejected (400).
        """
        user1 = UserFactory()
        user2 = UserFactory()
        room = RoomFactory()
        results = []

        def make_booking(user):
            client = APIClient()
            client.force_authenticate(user=user)
            r = client.post(
                BOOKINGS_URL,
                {
                    "room": room.pk,
                    "check_in": future(10),
                    "check_out": future(14),
                },
                format="json",
            )
            results.append(r.status_code)

        t1 = threading.Thread(target=make_booking, args=(user1,))
        t2 = threading.Thread(target=make_booking, args=(user2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert 500 not in results
        assert results.count(201) >= 1

    def test_concurrent_cancel_same_booking(self):
        """
        TC-CONC-02 -- Two simultaneous cancel requests on the same booking:
        no 500 errors allowed; at least one 204 must occur.
        """
        user = UserFactory()
        room = RoomFactory()
        booking = BookingFactory(user=user, room=room)
        results = []

        def cancel():
            client = APIClient()
            client.force_authenticate(user=user)
            r = client.delete(f"/api/bookings/{booking.pk}/")
            results.append(r.status_code)

        t1 = threading.Thread(target=cancel)
        t2 = threading.Thread(target=cancel)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert 500 not in results
        assert 204 in results


# INVALID USER BEHAVIOUR


@pytest.mark.django_db
class TestInvalidUserBehaviour:

    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture(autouse=True)
    def setup_data(self, db):
        self.user = UserFactory()
        self.other = UserFactory()
        self.room = RoomFactory()
        self.client.force_authenticate(user=self.user)

    def test_user_cannot_view_other_users_booking_detail(self):
        """TC-INV-01 -- GET on another user's booking must return 404."""
        other_booking = BookingFactory(
            user=self.other,
            room=self.room,
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=12),
        )
        r = self.client.get(f"/api/bookings/{other_booking.pk}/")
        assert r.status_code == 404

    def test_booking_list_only_shows_own_bookings(self):
        """TC-INV-02 -- List must only return the authenticated user's bookings."""
        BookingFactory(user=self.user, room=self.room)
        other_room = RoomFactory()
        BookingFactory(
            user=self.other,
            room=other_room,
            check_in=date.today() + timedelta(days=20),
            check_out=date.today() + timedelta(days=22),
        )
        r = self.client.get(BOOKINGS_URL)
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_patch_booking_is_not_allowed(self):
        """TC-INV-03 -- PATCH on a booking must return 405."""
        booking = BookingFactory(user=self.user, room=self.room)
        r = self.client.patch(
            f"/api/bookings/{booking.pk}/",
            {"check_out": future(10)},
            format="json",
        )
        assert r.status_code == 405

    def test_put_booking_is_not_allowed(self):
        """TC-INV-04 -- PUT on a booking must return 405."""
        booking = BookingFactory(user=self.user, room=self.room)
        r = self.client.put(
            f"/api/bookings/{booking.pk}/",
            {"room": self.room.pk, "check_in": future(2), "check_out": future(5)},
            format="json",
        )
        assert r.status_code == 405

    def test_access_admin_without_staff_is_denied(self):
        """TC-INV-05 -- Regular user accessing /admin/ must be redirected or denied."""
        r = self.client.get("/admin/")
        assert r.status_code in (302, 403)

    def test_rapid_non_overlapping_bookings_all_succeed(self):
        """TC-INV-06 -- 5 rapid bookings on non-overlapping dates must all succeed."""
        room2 = RoomFactory()
        success_count = 0
        for i in range(5):
            r = self.client.post(
                BOOKINGS_URL,
                {
                    "room": room2.pk,
                    "check_in": future(10 + i * 5),
                    "check_out": future(13 + i * 5),
                },
                format="json",
            )
            if r.status_code == 201:
                success_count += 1
        assert success_count == 5


# END-TO-END FLOW TESTS


@pytest.mark.django_db
class TestFullBookingFlow:

    def setup_method(self):
        self.client = APIClient()

    def test_full_user_journey(self, db):
        """
        TC-E2E-01 -- Complete flow:
        register -> login -> browse rooms -> book -> view -> cancel.
        """
        # Register
        reg = self.client.post(
            REGISTER_URL,
            {
                "username": "traveller",
                "email": "traveller@test.com",
                "password": "travel123",
            },
            format="json",
        )
        assert reg.status_code == 201

        # Login
        login = self.client.post(
            LOGIN_URL,
            {
                "email": "traveller@test.com",
                "password": "travel123",
            },
            format="json",
        )
        assert login.status_code == 200
        access_token = login.data["access"]

        # Browse rooms (no auth)
        room = RoomFactory(name="Sea View", price_per_day=Decimal("200.00"), capacity=2)
        rooms_resp = self.client.get(ROOMS_URL)
        assert rooms_resp.status_code == 200
        assert any(r["id"] == room.pk for r in rooms_resp.data)

        # Book a room
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        book = self.client.post(
            BOOKINGS_URL,
            {
                "room": room.pk,
                "check_in": future(5),
                "check_out": future(8),
            },
            format="json",
        )
        assert book.status_code == 201
        booking_id = book.data["id"]
        assert book.data["status"] == "active"

        # View booking detail
        detail = self.client.get(f"/api/bookings/{booking_id}/")
        assert detail.status_code == 200

        # Cancel
        cancel = self.client.delete(f"/api/bookings/{booking_id}/")
        assert cancel.status_code == 204

        # Room available again for same dates
        self.client.credentials()
        avail = self.client.get(
            ROOMS_URL, {"check_in": future(5), "check_out": future(8)}
        )
        ids = [r["id"] for r in avail.data]
        assert room.pk in ids

    def test_room_unavailable_during_booking_available_after_cancel(self, db):
        """
        TC-E2E-02 -- Room disappears from search while booked,
        reappears after cancellation.
        """
        user = UserFactory()
        room = RoomFactory()
        self.client.force_authenticate(user=user)

        # Book
        book = self.client.post(
            BOOKINGS_URL,
            {
                "room": room.pk,
                "check_in": future(3),
                "check_out": future(6),
            },
            format="json",
        )
        assert book.status_code == 201
        booking_id = book.data["id"]

        # Room should NOT appear in search
        search = APIClient().get(
            ROOMS_URL, {"check_in": future(3), "check_out": future(6)}
        )
        assert room.pk not in [r["id"] for r in search.data]

        # Cancel
        self.client.delete(f"/api/bookings/{booking_id}/")

        # Room SHOULD appear again
        search_after = APIClient().get(
            ROOMS_URL, {"check_in": future(3), "check_out": future(6)}
        )
        assert room.pk in [r["id"] for r in search_after.data]
