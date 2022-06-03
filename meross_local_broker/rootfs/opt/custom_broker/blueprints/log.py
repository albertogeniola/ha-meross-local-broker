from meross_iot.model.http.exception import HttpApiError

from logger import get_logger
from typing import Dict

from flask import Blueprint

from authentication import _user_login
from decorator import meross_http_api
from messaging import make_api_response


log_blueprint = Blueprint('log', __name__)
_LOGGER = get_logger(__name__)


@log_blueprint.route('/user', methods=['POST'])
@meross_http_api(login_required=True)
def log_user(api_payload: Dict, *args, **kwargs):
    # This api is implemented only for compatibility reasons.
    # We simply do nothing
    data = None
    return make_api_response(data=data)
