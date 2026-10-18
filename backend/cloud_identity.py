"""Verify Firebase/Identity Platform ID tokens on the server."""
import hashlib

from fastapi import HTTPException


def verifier(project):
    import firebase_admin
    from firebase_admin import auth
    name = 'dose-timer-cloud'
    try:
        app = firebase_admin.get_app(name)
    except ValueError:
        app = firebase_admin.initialize_app(options={'projectId': project}, name=name)

    def verify(value):
        if not value.startswith('Bearer '):
            raise HTTPException(401, 'Sign in to the demo first.')
        try:
            claims = auth.verify_id_token(value[7:], app=app)
            uid = claims['uid']
            if not uid:
                raise ValueError()
            return hashlib.sha256(uid.encode()).hexdigest()
        except Exception:
            raise HTTPException(401, 'Your demo session expired. Refresh and try again.') from None

    return verify
