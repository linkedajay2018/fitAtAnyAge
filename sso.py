"""SSO / OAuth login. Each provider is independently optional — see
config.py's GOOGLE_CONFIGURED / FACEBOOK_CONFIGURED. Adding a new provider:
add its *_CLIENT_ID/*_CLIENT_SECRET to config.py, register it in
register_providers() below, and add it to PROVIDER_META."""

from authlib.integrations.flask_client import OAuth

import config

oauth = OAuth()

# Display metadata for templates — keyed by the same provider id used in
# oauth.register() below and in the /login/<provider> route.
PROVIDER_META = {
    "google": {"label": "Google"},
    "facebook": {"label": "Facebook"},
}


def register_providers(app):
    oauth.init_app(app)

    if config.GOOGLE_CONFIGURED:
        oauth.register(
            name="google",
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if config.FACEBOOK_CONFIGURED:
        oauth.register(
            name="facebook",
            client_id=config.FACEBOOK_CLIENT_ID,
            client_secret=config.FACEBOOK_CLIENT_SECRET,
            access_token_url="https://graph.facebook.com/oauth/access_token",
            authorize_url="https://www.facebook.com/dialog/oauth",
            api_base_url="https://graph.facebook.com/",
            client_kwargs={"scope": "email public_profile"},
        )


def get_configured_providers():
    providers = []
    if config.GOOGLE_CONFIGURED:
        providers.append("google")
    if config.FACEBOOK_CONFIGURED:
        providers.append("facebook")
    return providers


def fetch_sso_profile(provider, client, token):
    """Return (email, name) for the logged-in user from this provider's
    token, or (None, None) if no email was available (e.g. the user's
    Facebook account has no email on file)."""
    if provider == "google":
        userinfo = token.get("userinfo") or client.userinfo(token=token)
        return userinfo.get("email"), userinfo.get("name")

    if provider == "facebook":
        profile = client.get("me?fields=id,name,email", token=token).json()
        return profile.get("email"), profile.get("name")

    return None, None
