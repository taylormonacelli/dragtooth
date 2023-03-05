import datetime
import logging
import os
import re
import sys

import bs4
import requests
import requests.exceptions

from . import model

_logger = logging.getLogger(__name__)

pat = re.compile(
    r"Session pair has been generated\(dec\)"
    r" (?P<dec>\$[^:]+)\s+:\s+(?P<enc>\$[^:]+) \(enc\)"
)

CONNECT_TIMEOUT_SEC = 2

# use requests's session auto manage cookies
curSession = requests.Session()


def get_credentials_from_env() -> model.Credentials:
    def validate_login(login):
        msg_login = (
            "WEBUI_LOGIN is incorrect, try: export "
            "WEBUI_LOGIN=username WEBUI_PASSWORD=password"
        )

        if not login:
            _logger.critical(msg_login)
            sys.exit(-1)

    def validate_password(login):
        msg_password = (
            "WEBUI_PASSWORD is incorrect, try: export "
            "WEBUI_LOGIN=username WEBUI_PASSWORD=password"
        )

        if not password:
            _logger.critical(msg_password)
            sys.exit(-1)

    login = os.getenv("WEBUI_LOGIN", None)
    validate_login(login)

    password = os.getenv("WEBUI_PASSWORD", None)
    validate_login(password)

    return model.Credentials(login, password)


def generate_request_session(credentials: model.Credentials) -> None:
    # all cookies received will be stored in the session object

    payload = {"login": credentials.login, "password": credentials.password}
    url = "http://tl3.streambox.com/light/light_status.php"

    try:
        _logger.debug(f"feching {url}")
        response = requests.get(url, timeout=CONNECT_TIMEOUT_SEC)
        response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xxx

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.critical(f"can't reach {url}")
        sys.exit(-1)

    except requests.exceptions.HTTPError:
        _logger.critical("4xx, 5xx")
        sys.exit(-1)

    else:
        _logger.debug(f"Great!  I'm able to reach {url}")

    _logger.debug(f"submitting post request to {url} with {payload=}")
    response = curSession.post(url, data=payload, timeout=CONNECT_TIMEOUT_SEC)


def html_to_text(html: str):
    soup = bs4.BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    _logger.debug(f"parse_it: parsed as {text}")

    return text


def post_session_create_request(port: int, lifetime: datetime.timedelta) -> str:
    url = "http://tl3.streambox.com/light/sreq.php"

    payload = {
        "port1": port,
        "port2": port,
        "lifetime": lifetime.total_seconds() / 3600,
        "request": "Request",
    }

    try:
        response = curSession.post(url, data=payload, timeout=5)
        _logger.debug(f"response from post request to {url} is {response.text}")

        # Raises a HTTPError if the status is 4xx, 5xxx
        response.raise_for_status()

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.critical(f"can't reach {url}")
        sys.exit(-1)

    except requests.exceptions.HTTPError:
        _logger.critical("4xx, 5xx")
        sys.exit(-1)

    else:
        _logger.debug(f"Great!  I'm able to reach {url}")

    return response.text


def post_session_delete_request(session: model.LightSession) -> str:
    payload = {
        "action": 3,
        "idd1": session.encoder,
        "idd2": session.decoder,
    }

    url = "http://tl3.streambox.com/light/sreq.php"
    response = curSession.post(url, data=payload, timeout=5)
    _logger.debug(f"response from post request to {url} is {response.text}")

    return response.text


def generate_session_from_text(text: str, port: int) -> model.LightSession:
    text = text.strip()
    for line in text.splitlines():
        mo = pat.search(line)
        if mo:
            dec = mo.group("dec").strip()
            enc = mo.group("enc").strip()
            return model.LightSession(encoder=enc, decoder=dec, port=port)

    return model.LightSession(encoder="", deocder="", port=port)


def main(args):
    creds = get_credentials_from_env()
    generate_request_session(credentials=creds)
    session_count = args.session_count
    session_lifetime = datetime.timedelta(hours=args.session_lifetime_hours)
    starting_port = 2000
    msg = (
        f"request to create {session_count} "
        f"sessions, starting at port {starting_port}"
    )
    _logger.info(msg)

    for offset in range(session_count):
        port = starting_port + offset
        _logger.debug(f"{port=}, {offset=}")
        html = post_session_create_request(port=port, lifetime=session_lifetime)
        text = html_to_text(html)
        session = generate_session_from_text(text, port=port)
        msg = (
            "session pair generated or re-fetched for "
            f"{port=} {session=}, {session_count-offset:,} remaining"
        )
        _logger.info(msg)
