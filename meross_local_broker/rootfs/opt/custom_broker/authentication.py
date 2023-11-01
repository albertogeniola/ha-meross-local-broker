from hashlib import md5
import uuid
from _sha256 import sha256
from typing import Tuple, Optional

from meross_iot.http_api import ErrorCodes
from meross_iot.model.http.exception import HttpApiError

from db_helper import dbhelper
from model.enums import EventType
from model.db_models import User, UserToken
from utilities import _hash_password


def verify_token(token) -> Optional[User]:
    """
    Returns the user's id for a given token.
    """
    return dbhelper.get_user_by_token(token)


def _user_logout(token: str) -> None:
    # Retrieve the user from the token for logging reasons
    user = dbhelper.get_user_by_token(token=token)
    dbhelper.remove_user_token(token=token)
    dbhelper.store_event(EventType.USER_LOGOUT, details=f"User {user.email} has failed to log in via Local Meross API: wrong or unexisting email specified.", user_id=user.user_id);


def _attempt_password_upgrade(email, password) -> bool:
    # Attempt password upgrade from non-hashed to hashed form
    user = dbhelper.get_user_by_email(email=email)
    if user is None:
        dbhelper.store_event(EventType.USER_LOGIN_FAILURE, details=f"User {email} has failed to log in via Local Meross API: wrong or unexisting email specified.");
        return False
    # Only upgrade the password if user hasn't done it yet and if the old password still is valid
    old_password = _hash_password(salt=user.salt, password=password, pre_apply_md5=False)
    if not user.password_upgraded and user.password == old_password:
        new_pass = md5(password.encode("utf8")).hexdigest()
        dbhelper.add_update_user(email=user.email, password=new_pass, user_key=None)
        dbhelper.store_event(EventType.USER_PASSWORD_UPGRADE, details=f"User's password has been upgraded for {email}.");
        return True
    return False


def _user_login(email: str, password: str, providing_pre_hashed_password: bool) -> Tuple[User, UserToken]:
    # Check user-password creds
    # email, userid, salt, password, mqtt_key
    user = dbhelper.get_user_by_email(email=email)
    if user is None:
        dbhelper.store_event(EventType.USER_LOGIN_FAILURE, details=f"User {email} has failed to log in via Local Meross API: wrong or unexisting email specified.");
        raise HttpApiError(ErrorCodes.CODE_UNEXISTING_ACCOUNT)

    # If not provided with a pre-md5-hashed password, we compute it via _hash_password.
    computed_hashed_password = _hash_password(salt=user.salt, password=password, pre_apply_md5 = not providing_pre_hashed_password)

    if computed_hashed_password != user.password:
        dbhelper.store_event(EventType.USER_LOGIN_FAILURE, details=f"User {email} has failed to log in via Local Meross API: wrong password.");
        raise HttpApiError(ErrorCodes.CODE_WRONG_CREDENTIALS)

    # If ok, generate an HTTP_TOKEN
    hash = sha256()
    hash.update(uuid.uuid4().bytes)
    token = hash.hexdigest()

    # Store the new token
    token = dbhelper.store_new_user_token(user.user_id, token)
    dbhelper.store_event(EventType.USER_LOGIN_SUCCESS, details=f"User {email} has successfully logged in via Local Meross API.");
    return user, token


