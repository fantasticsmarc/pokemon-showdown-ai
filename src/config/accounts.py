import json
from pathlib import Path

from poke_env import AccountConfiguration

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    config = json.load(f)


# Build a clear error message when the shared ladder account is missing from config.
def _build_missing_ladder_account_message(base_username: str) -> str:
    return (
        f"Missing ladder credentials for {base_username} in {CONFIG_PATH}. "
        "Expected config format:\n"
        '{\n'
        '  "ladder_account": {\n'
        '    "username": "YourShowdownUsername",\n'
        '    "password": "YourShowdownPassword"\n'
        "  }\n"
        "}"
    )


# Return the account to use for local play or for the shared ladder login.
def get_account_configuration(play_format: int, base_username: str) -> AccountConfiguration:
    if play_format == 1:
        # Local play does not require authentication, so each bot can simply
        # use its visible name as the account name.
        return AccountConfiguration(username=base_username, password=None)

    # Ladder play uses one shared account from config.json because only one
    # ladder bot is created at a time in main.py.
    ladder_account = config.get("ladder_account", {})
    ladder_username = ladder_account.get("username")
    ladder_password = ladder_account.get("password")

    if ladder_username and ladder_password:
        print(f"{base_username} / Using shared ladder account: {ladder_username}")
        return AccountConfiguration(username=ladder_username, password=ladder_password)

    raise ValueError(_build_missing_ladder_account_message(base_username))
