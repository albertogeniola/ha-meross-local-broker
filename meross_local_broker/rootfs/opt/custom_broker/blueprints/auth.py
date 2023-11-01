import re
from enum import Enum
from meross_iot.model.http.exception import HttpApiError

from logger import get_logger
from typing import Dict, Optional, Tuple

from flask import Blueprint, request

from authentication import _attempt_password_upgrade, _user_login
from decorator import meross_http_api
from messaging import make_api_response
from pep440_rs import Version


auth_blueprint = Blueprint('auth', __name__)
_LOGGER = get_logger(__name__)


@auth_blueprint.route('/signIn', methods=['POST'])
@meross_http_api(login_required=False)
def sign_in(api_payload: Dict, *args, **kwargs):
    email = api_payload.get("email")
    password = api_payload.get("password")
    encryption = api_payload.get("encryption", 0)

    if encryption == 1:
        providing_pre_hashed_password = True
    elif encryption == 0:
        providing_pre_hashed_password = False
    else:
        raise HttpApiError("Invalid or unsupported encryption flag. Only accepted value is 1.")
    
    if email is None:
        raise HttpApiError("Missing email parameter")
    if password is None:
        raise HttpApiError("Missing password parameter")

    user, token = _user_login(email, password, providing_pre_hashed_password)
    _LOGGER.info("User: %s successfully logged in" % email)
    data = {
        "token": str(token.token),
        "key": str(user.mqtt_key),
        "userid": str(user.user_id),
        "email": str(user.email),
        "domain": str(request.scheme + "://" + request.host),
        "mqttDomain": "",
        "mfaLockExpire": 0
    }
    return make_api_response(data=data)


@auth_blueprint.route('/Login', methods=['POST'])
@meross_http_api(login_required=False)
def login(api_payload: Dict, *args, **kwargs):
    """DEPRECATED METHOD. Left for backward compatibility"""
    email = api_payload.get("email")
    password = api_payload.get("password")
    
    if email is None:
        raise HttpApiError("Missing email parameter")
    if password is None:
        raise HttpApiError("Missing password parameter")

    # Attempt a password upgrade here if calling user-agent is < 1.2.10
    client_type, client_version = _parse_client_version(request.headers.get("User-Agent"))
    if client_type == ClientType.HA_LIBRARY and Version(client_version) < Version("0.4.6"):
        _LOGGER.warning("Detected login attempt from old client using non-hashed password.")
        if _attempt_password_upgrade(email, password):
            _LOGGER.warning("Password upgrade successful.")
        else:
            _LOGGER.error("Password upgrade failed.")

    user, token = _user_login(email, password, False)
    _LOGGER.info("User: %s successfully logged in" % email)
    data = {
        "token": str(token.token),
        "key": str(user.mqtt_key),
        "userid": str(user.user_id),
        "email": str(user.email)
    }
    return make_api_response(data=data)


def _parse_client_version(user_agent: str) -> Tuple[str, Optional[str]]:
    """Returns the client type and its version, if available"""
    if user_agent is None:
        return ClientType.UNKNOWN, None
    version = re.fullmatch("MerossIOT\/(.*)", user_agent)
    if version is not None:
        return ClientType.HA_LIBRARY, version.group(1)
    return ClientType.UNKNOWN, None


class ClientType(Enum):
    HA_LIBRARY="MerossIOT",
    UNKNOWN=""
