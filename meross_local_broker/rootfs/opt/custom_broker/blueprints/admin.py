from logger import get_logger
from typing import Dict, List

from flask import jsonify, request
from flask import Blueprint
from db_helper import dbhelper
from model.enums import EventType
from model.db_models import Device
from model.exception import BadRequestError
from constants import DEFAULT_USER_ID
from s6 import service_manager
from setup import setup_account
from datetime import datetime
from meross_iot.model.http.exception import BadLoginException


admin_blueprint = Blueprint('admin', __name__)
_LOGGER = get_logger(__name__)


# TODO: check super-admin role...
@admin_blueprint.route('/devices', methods=['GET'])
def list_devices() -> List[Dict]:
    """ List all devices """
    devices = dbhelper.get_all_devices()
    return jsonify(Device.serialize_list(devices))


# TODO: check super-admin role...
@admin_blueprint.route('/devices/<uuid>', methods=['PUT'])
def update_device(uuid: str) -> Dict:
    """ Update the given device """
    device_patch = request.get_json(force=True)

    # Check if the given device exists
    device = dbhelper.get_device_by_uuid(device_uuid=uuid)
    if device is None:
        _LOGGER.warning("Device with UUID %s does not exist", uuid)
        raise BadRequestError(msg=f"Device with UUID {uuid} does not exist")

    # Path supported methods: device name
    name = device_patch.get("dev_name")
    if name is not None:
        device.dev_name = name
        del device_patch["dev_name"]

    # Raise an error if the user has tried to update any other attribute
    if len(device_patch.keys()) > 0:
        _LOGGER.warning("Unsupported patch arguments: %s", ",".join(device_patch.keys()))
        raise BadRequestError("Unsupported patch arguments: %s" % ",".join(device_patch.keys()))

    dbhelper.update_device(device)

    return jsonify(Device.serialize(device))


# TODO: check super-admin role...
@admin_blueprint.route('/subdevices', methods=['GET'])
def list_subdevices() -> List[Dict]:
    """ List all subdevices """
    subdevices = dbhelper.get_all_subdevices()
    return jsonify(Device.serialize_list(subdevices))


# TODO: check super-admin role...
@admin_blueprint.route('/services', methods=['GET'])
def list_services() -> List[Dict]:
    """ List services """
    services = service_manager.get_services_info()
    return jsonify([s.serialize() for s in services])


# TODO: check super-admin role...
@admin_blueprint.route('/services/<service_name>/execute/<command>', methods=['POST'])
def execute_service_command(service_name: str, command: str):
    """ Executes a command on a service """
    cmd = command.lower()
    if cmd == "start": 
        return_code, stdout = service_manager.start_service(service_name)
    elif cmd == "stop":
        return_code, stdout = service_manager.stop_service(service_name)
    elif command == "restart":
        return_code, stdout = service_manager.restart_service(service_name)
    else:
        raise BadRequestError(msg="Invalid command specified.")
    return jsonify({
        "return_code": return_code,
        "output": stdout
    })


# TODO: check super-admin role...
@admin_blueprint.route('/services/<service_name>/log', methods=['GET'])
def get_service_log(service_name: str):
    """ Returns the log of the given service """
    return jsonify(service_manager.get_log(service_name))


# TODO: check super-admin role...
@admin_blueprint.route('/configuration', methods=['GET'])
def get_account():
    """ Returns the configured account """
    # Get the configured account
    configuration = dbhelper.get_configuration()
    if configuration is None:
        _LOGGER.warning("Invalid/Missing userid %s in the DB. Please set it again.", DEFAULT_USER_ID)
        return jsonify(None)
    return jsonify(configuration.serialize())


# TODO: check super-admin role...
@admin_blueprint.route('/configuration', methods=['PUT'])
def set_account():
    """ Configures the Meross Account to be use as authentication method """
    # Arg checks
    payload = request.get_json(force=True)
    if payload is None:
        raise BadRequestError(msg=f"Missing json payload.")
    email: str = payload.get('email')
    password: str = payload.get('password')
    meross_link: bool = payload.get('enableMerossLink', False)
    if email is None:
        raise BadRequestError(msg=f"Missing or invalid email.")
    if password is None:
        raise BadRequestError(msg=f"Missing or invalid password.")
    if meross_link is None:
        raise BadRequestError(msg=f"Missing or invalid enableMerossLink option.")
    
    # Setup Account
    try:
        user = setup_account(email=email, password=password, enable_meross_link=meross_link)
    except BadLoginException as e:
        raise BadRequestError(msg=f"Invalid credentials.")
    
    dbhelper.add_update_configuration(enable_meross_link=meross_link, local_user_id=user.user_id)

    # As soon as the Account is set, we need to restart the mosquitto and the broker services
    _LOGGER.warn("Restarting broker & MQTT services (due to account configuration changes)")
    service_manager.restart_service("Local Agent")
    service_manager.restart_service("MQTT Service")

    # TODO: Restart/Reload broker?
    return jsonify(user.serialize())


# TODO: check super-admin role...
@admin_blueprint.route('/events', methods=['GET'])
def get_events():
    """ Returns the latest events """
    # Arg checks
    
    args = request.args
    limit = args.get('limit')
    if limit is not None:
        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError()
        except ValueError as e:
            raise BadRequestError(msg="Invalid limit parameter specified. Limit must be a positive integer or null.")

    event_type = args.get('eventType')
    if event_type is not None:
        try:
            event_type = EventType(event_type)
        except ValueError as e:
            raise BadRequestError(msg=f"Invalid eventType parameter specified: {event_type}.")

    from_timestamp = args.get('fromTimestamp')
    if from_timestamp is not None:
        try:
            from_timestamp = datetime.fromtimestamp(float(from_timestamp))
        except (ValueError,TypeError) as e:
            raise BadRequestError(msg=f"Invalid fromTimestamp parameter specified: {from_timestamp}.")

    to_timestamp = args.get('toTimestamp')
    if to_timestamp is not None:
        try:
            to_timestamp = datetime.fromtimestamp(float(to_timestamp))
        except (ValueError,TypeError) as e:
            raise BadRequestError(msg=f"Invalid toTimestamp parameter specified: {from_timestamp}.")

    device_uuid = args.get('deviceUuid')
    sub_device_id = args.get('subDeviceId')
    user_id = args.get('userId')

    events = dbhelper.get_events(limit=limit, event_type=event_type, device_uuid=device_uuid, sub_device_id=sub_device_id, user_id=user_id, from_timestamp=from_timestamp, to_timestamp=to_timestamp)
    
    # TODO: Restart/Reload broker?
    return jsonify([e.serialize() for e in events])