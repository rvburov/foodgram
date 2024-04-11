from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешение для проверки авторства или только чтения."""

    def has_permission(self, request, view):
        """Проверяет разрешение на выполнение действия."""
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        """Проверяет разрешение на выполнение действия над объектом."""
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )
