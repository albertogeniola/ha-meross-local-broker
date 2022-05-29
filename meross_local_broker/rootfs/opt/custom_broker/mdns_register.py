#!/usr/bin/python3
import sys
from pkg_resources import require
from dbus import SystemBus, Interface, DBusException
from argparse import ArgumentParser, Namespace


def _parse_args() -> Namespace:
    parser = ArgumentParser(description='DBUS-MDNS service manager')
    # Register parser
    subparsers = parser.add_subparsers(title="sub-commands", description="valid subcommands", dest="command")

    # Praser for the register command
    parser_register = subparsers.add_parser('register', help="Registers a service")
    parser_register.add_argument('service_name', help="Service name", type=str)
    parser_register.add_argument('service_name_template', help="Service name template")
    parser_register.add_argument('service_type', help="Service type, e.g. _myservice._tcp", type=str)
    parser_register.add_argument('service_port', help="Service port, e.g. 5000", type=int)
    parser_register.add_argument('--priority', help="Service priority, e.g. 1", required=False, default=1, type=int)
    parser_register.add_argument('--weight', help="Service weight, e.g. 1", required=False, default=1, type=int)
    parser_register.add_argument('--set', help="Add txt data record, in the form KEY=VALUE. Please do not put a space before the '=' sign. In case the value contains spaces, please enclose it with double quotes.", required=False, metavar="KEY=VALUE", nargs='+')
    parser_register.add_argument('--update-if-present', help="When set, this will ensure the service is updated in case it is already registered.", action='store_true', required=False)

    parser_unregister = subparsers.add_parser('unregister', help="Unegisters a service")
    parser_unregister.add_argument('service_name', help="Service name to unregister", type=str)
    
    return parser.parse_args()


def _register_service(service_name: str, service_name_template: str, service_type: str, service_port: int, service_priority: int, service_weight: int, data: list) -> str:
    bus = SystemBus()
    resolved = bus.get_object('org.freedesktop.resolve1', '/org/freedesktop/resolve1')
    manager = Interface(resolved,dbus_interface='org.freedesktop.resolve1.Manager')
    
    # Data should be converted in an array of dictionaries where the data is a list of chars (expressed as byte array)

    if data is None or len(data) == 0:
        txt_data = []
    else:
        txt_data = [ {keyvalue.split('=')[0]: bytearray(keyvalue.split('=')[1].encode('utf8'))} for keyvalue in data ]

    service_path = manager.RegisterService(service_name, service_name_template, service_type, service_port,service_priority,service_weight,txt_data)
    print(f"Service registered in {service_path}")
    return service_path
    
    
def register_service(service_name: str, service_name_template: str, service_type: str, service_port: int, service_priority: int, service_weight: int, data: list, update_if_present: bool) -> str:
    try:
        return _register_service(service_name=service_name, service_name_template=service_name_template, service_type=service_type, service_port=service_port, service_priority=service_priority, service_weight=service_weight, data=data)
    except DBusException as e:
        # Raise any error except "already registered service"
        if not e.get_dbus_name()=="org.freedesktop.resolve1.DnssdServiceExists":
            print(f"An unhandled exception occurred: {str(e)}")
            raise e
        
        # Handle already registered service
        print(f"Service '{service_name}' already exists.")
        if update_if_present:
            print("Unregistering it...")
            unregister_service(service_name)
            print("Attempting a new registration...")
            return _register_service(service_name=service_name, service_name_template=service_name_template, service_type=service_type, service_port=service_port, service_priority=service_priority, service_weight=service_weight, data=data)
        else:
            raise e


def unregister_service(service_name: str) -> None:
    bus = SystemBus()
    service_path = f"/org/freedesktop/resolve1/dnssd/{service_name}"
    print(f"Unregistering '{service_path}'")
    resolved = bus.get_object('org.freedesktop.resolve1', '/org/freedesktop/resolve1')
    manager = Interface(resolved,dbus_interface='org.freedesktop.resolve1.Manager')
    manager.UnregisterService(service_path)
    print(f"Service {service_name} unregistered.")
    

def main() -> int:
    args = _parse_args()
    if args.command == "register":
        print(f"Requested service registration for '{args.service_name}'")
        path = register_service(service_name=args.service_name, service_name_template=args.service_name_template, service_type=args.service_type, service_port=args.service_port, service_priority=args.priority, service_weight=args.weight, data=args.set, update_if_present=args.update_if_present)
        print(f"Registered to {path}")
        return 0
    elif args.command == "unregister":
        print(f"Requested service unregistration for '{args.service_name}'")
        unregister_service(args.service_name)
        return 0
    else:
        raise ValueError("Invalid invocation: please specify at least one between 'register' and 'unregister' options.")

    
if __name__ == '__main__':
    exit(main())
