import pytest
import factory
from datetime import date, timedelta
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


# ─── Factories ────────────────────────────────────────────────────────────────

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rooms.Room"

    name = factory.Sequence(lambda n: f"Room {n}")
    price_per_day = factory.Faker(
        "pydecimal", left_digits=3, right_digits=2, positive=True
    )
    capacity = factory.Faker("random_int", min=1, max=5)


class BookingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "bookings.Booking"

    user = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
    check_in = factory.LazyFunction(lambda: date.today() + timedelta(days=1))
    check_out = factory.LazyFunction(lambda: date.today() + timedelta(days=3))
    status = "active"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def another_user(db):
    return UserFactory()


@pytest.fixture
def room(db):
    return RoomFactory()


@pytest.fixture
def auth_client(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def another_auth_client(db, another_user):
    client = APIClient()
    client.force_authenticate(user=another_user)
    return client, another_user