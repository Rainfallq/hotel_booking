from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(max_length=20)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data: dict) -> User:
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")
