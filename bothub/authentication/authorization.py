import logging

from django.utils.translation import ugettext_lazy as _
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header

from bothub.common.models import (
    RepositoryTranslator,
    Repository,
    RepositoryAuthorization,
)

LOGGER = logging.getLogger("weni_django_oidc")


class TranslatorAuthentication(TokenAuthentication):
    keyword = "Translator"
    model = RepositoryTranslator

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.get(pk=key)
        except RepositoryTranslator.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        repository = Repository.objects.get(
            pk=token.repository_version_language.repository_version.repository.pk
        )
        authorization = repository.get_user_authorization(token.created_by)

        if not authorization.can_translate:
            raise exceptions.PermissionDenied()

        return (token.created_by, token)


class NLPAuthentication(TokenAuthentication):
    keyword = "Bearer"
    model = RepositoryAuthorization

    def authenticate(self, request):
        from bothub.api.v2.nlp.views import RepositoryAuthorizationParseViewSet

        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _("Invalid token header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _("Invalid token header. Token string should not contain spaces.")
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _(
                "Invalid token header. Token string should not contain invalid characters."
            )
            raise exceptions.AuthenticationFailed(msg)

        if isinstance(
            request.parser_context.get("view"), RepositoryAuthorizationParseViewSet
        ):
            return self.authenticate_credentials(token, validation=False)

        return self.authenticate_credentials(token, validation=True)

    def authenticate_credentials(self, key, **kwargs):
        model = self.get_model()
        try:
            authorization = model.objects.get(uuid=key)
            if not authorization.can_translate and kwargs.get("validation"):
                raise exceptions.PermissionDenied()

            return (authorization.user, authorization)
        except RepositoryAuthorization.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))


class WeniOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def verify_claims(self, claims):
        # validação de permissão
        verified = super(WeniOIDCAuthenticationBackend, self).verify_claims(claims)
        # is_admin = "admin" in claims.get("roles", [])
        return (
            verified
        )  # and is_admin # not checking for user roles from keycloak at this time

    def get_username(self, claims):
        username = claims.get("preferred_username")
        if username:
            return username
        return super(WeniOIDCAuthenticationBackend, self).get_username(claims=claims)

    def create_user(self, claims):
        # Override existing create_user method in OIDCAuthenticationBackend
        email = claims.get("email")
        username = self.get_username(claims)[:16]
        user = self.UserModel.objects.create_user(email, username)

        user.name = claims.get("name", "")
        user.save()

        return user

    def update_user(self, user, claims):
        user.name = claims.get("name", "")
        user.email = claims.get("email", "")
        user.save()

        return user
