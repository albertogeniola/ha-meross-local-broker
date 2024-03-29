from hashlib import md5
from uuid import uuid4
from meross_iot.model.credentials import MerossCloudCreds

from logger import get_logger
import argparse
from constants import DEFAULT_USER_ID
from database import init_db
from db_helper import dbhelper
from model.db_models import User
from model.enums import EventType


from meross_iot.http_api import MerossHttpClient

l = get_logger("setup")


def get_meross_credentials(email: str, password: str) -> MerossCloudCreds:
    import asyncio

    async def get_creds(email: str = email, password: str = password) -> MerossCloudCreds:
        creds = await MerossHttpClient.async_login(api_base_url="https://iotx-us.meross.com", email=email, password=password)
        return creds
    return asyncio.run(get_creds(email=email, password=password))


def setup_account(email: str, password: str, enable_meross_link: bool) -> User:
    user_key = str(md5(uuid4().bytes).hexdigest().lower())
    user_id = DEFAULT_USER_ID
    if enable_meross_link:
        l.info("Trying to federate against Meross Cloud for user %s...", email)
        creds = get_meross_credentials(email=email, password=password)
        l.debug("Retrieved credentials from Meross: %s", str(creds.to_json()))
        user_id = int(creds.user_id)
        user_key = creds.key

    # The new version of Meross API uses a hashed password as clear password (md5)
    #  We do the same to maintain compatibility with low-level MerossIot API
    hashed_pass = md5(password.encode("utf8")).hexdigest()
    user = dbhelper.add_update_user(user_id=user_id, email=email, password=hashed_pass, user_key=user_key)
    dbhelper.add_update_configuration(enable_meross_link=enable_meross_link, local_user_id=user.user_id)
    l.info(f"User: %s, mqtt_key: %s", user.email, user.mqtt_key)
    dbhelper.store_event(event_type=EventType.CONFIGURATION_CHANGE, details=f"Login username/password has been changed.")
    return user


def main():
    init_db()
   

if __name__ == '__main__':
    main()
