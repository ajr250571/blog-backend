from rest_framework import permissions
from django.conf import settings


class HasValidAPIKey(permissions.BasePermission):
    """
    Custom permission to only allow access to users with a valid API key.
    """

    def has_permission(self, request, view):
        api_key = request.headers.get('API-Key')
        return api_key in getattr(settings, 'VALID_API_KEYS', [])
