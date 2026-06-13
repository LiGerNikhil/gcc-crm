from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, UserProfile

User = get_user_model()


# ------------------------------------------------------------------ #
#  ROLE
# ------------------------------------------------------------------ #
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "role_code", "name", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


# ------------------------------------------------------------------ #
#  USER PROFILE
# ------------------------------------------------------------------ #
class UserProfileSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.role_code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id", "role", "role_code", "role_name",
            "department", "manager", "manager_name",
            "phone", "profile_image", "bio", "is_active",
        ]
        read_only_fields = ["id"]

    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.user.get_full_name() or obj.manager.user.username
        return None


class UserProfileDetailSerializer(UserProfileSerializer):
    subordinates_count = serializers.SerializerMethodField()

    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + ["subordinates_count", "created_at", "updated_at"]

    def get_subordinates_count(self, obj):
        return obj.subordinates.count()


# ------------------------------------------------------------------ #
#  USER
# ------------------------------------------------------------------ #
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_code = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "phone", "full_name",
            "first_name", "last_name", "is_active",
            "role_code", "role_name", "profile",
            "last_login", "last_activity_at", "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_role_code(self, obj):
        try:
            return obj.profile.role.role_code
        except Exception:
            return None

    def get_role_name(self, obj):
        try:
            return obj.profile.role.name
        except Exception:
            return None


class UserDetailSerializer(UserSerializer):
    profile = UserProfileDetailSerializer(read_only=True)
    assigned_leads_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["assigned_leads_count", "created_at", "updated_at"]

    def get_assigned_leads_count(self, obj):
        return obj.assigned_leads.filter(is_deleted=False).count()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})
    role = serializers.UUIDField(write_only=True)
    department = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "username", "email", "password", "password_confirm",
            "first_name", "last_name", "phone", "is_active",
            "role", "department",
        ]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        role_id = validated_data.pop("role")
        department = validated_data.pop("department", "")
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        from .models import UserProfile, Role
        role = Role.objects.get(id=role_id)
        UserProfile.objects.create(user=user, role=role, department=department)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    role = serializers.UUIDField(write_only=True, required=False)
    department = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "phone",
            "is_active", "role", "department",
        ]

    def update(self, instance, validated_data):
        role_id = validated_data.pop("role", None)
        department = validated_data.pop("department", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if role_id or department is not None:
            profile = getattr(instance, "profile", None)
            if profile:
                if role_id:
                    from .models import Role
                    profile.role = Role.objects.get(id=role_id)
                if department is not None:
                    profile.department = department
                profile.save()
        return instance


# ------------------------------------------------------------------ #
#  CHANGE PASSWORD
# ------------------------------------------------------------------ #
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(style={"input_type": "password"})
    new_password = serializers.CharField(style={"input_type": "password"})
    new_password_confirm = serializers.CharField(style={"input_type": "password"})

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return data
