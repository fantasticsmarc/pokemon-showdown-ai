import asyncio
import json

import requests
from poke_env.ps_client.ps_client import PSClient

LOGIN_CONNECT_TIMEOUT_SECONDS = 10
LOGIN_READ_TIMEOUT_SECONDS = 30
LOGIN_MAX_ATTEMPTS = 3
LOGIN_RETRY_DELAY_SECONDS = 2


# Parse the Showdown login server response and convert it to a Python dict.
def _extract_login_payload(response_text: str) -> dict:
    trimmed_response = response_text.lstrip("]")
    try:
        return json.loads(trimmed_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Pokemon Showdown returned a non-JSON login response: "
            f"{response_text[:200]}"
        ) from exc


# Request the login assertion token with retries in case the login server is slow.
async def _request_login_assertion(self: PSClient, split_message: list[str]) -> str:
    last_exception = None

    for attempt in range(1, LOGIN_MAX_ATTEMPTS + 1):
        try:
            log_in_request = requests.post(
                self.server_configuration.authentication_url,
                data={
                    "act": "login",
                    "name": self.account_configuration.username,
                    "pass": self.account_configuration.password,
                    "challengekeyid": split_message[2],
                    "challenge": split_message[3],
                },
                timeout=(
                    LOGIN_CONNECT_TIMEOUT_SECONDS,
                    LOGIN_READ_TIMEOUT_SECONDS,
                ),
            )
            log_in_request.raise_for_status()
            payload = _extract_login_payload(log_in_request.text)
            assertion = payload.get("assertion")

            if assertion:
                return assertion

            server_message = payload.get("message") or payload.get("actionsuccess")
            raise ValueError(
                "Pokemon Showdown did not return an assertion token. "
                f"Server response: {server_message!r}. Full payload: {payload}"
            )
        except requests.exceptions.Timeout as exc:
            last_exception = exc
            self.logger.warning(
                "Showdown login request timed out (attempt %d/%d). Retrying in %ds.",
                attempt,
                LOGIN_MAX_ATTEMPTS,
                LOGIN_RETRY_DELAY_SECONDS,
            )
            if attempt < LOGIN_MAX_ATTEMPTS:
                await asyncio.sleep(LOGIN_RETRY_DELAY_SECONDS)
                continue
        except requests.exceptions.RequestException as exc:
            last_exception = exc
            self.logger.warning(
                "Showdown login request failed (attempt %d/%d): %s",
                attempt,
                LOGIN_MAX_ATTEMPTS,
                exc,
            )
            if attempt < LOGIN_MAX_ATTEMPTS:
                await asyncio.sleep(LOGIN_RETRY_DELAY_SECONDS)
                continue
        else:
            last_exception = None

        break

    raise ConnectionError(
        "Pokemon Showdown login server did not respond successfully after "
        f"{LOGIN_MAX_ATTEMPTS} attempts."
    ) from last_exception


# Replace poke_env's login flow so it uses the current Showdown login format.
async def _patched_log_in(self: PSClient, split_message: list[str]):
    # Compatibility patch for newer Showdown login servers.

    # Recent Showdown login flows expect the challstr parts to be sent as `challengekeyid` and `challenge` instead of the legacy combined `challstr`.

    if self.account_configuration.password:
        self.logger.info("Sending authentication request")
        assertion = await _request_login_assertion(self, split_message)
    else:
        self.logger.info("Bypassing authentication request")
        assertion = ""

    await self.send_message(f"/trn {self.username},0,{assertion}")
    await self.change_avatar(self._avatar)


# Apply the custom login patch only once to avoid patching PSClient repeatedly.
def apply_poke_env_login_patch():
    if getattr(PSClient.log_in, "__name__", "") == "_patched_log_in":
        return
    PSClient.log_in = _patched_log_in


apply_poke_env_login_patch()
