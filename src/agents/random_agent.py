from poke_env import RandomPlayer, AccountConfiguration
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
import json

with open("pokemon-showdown-ai/config.json", "r") as f:
    config = json.load(f)

password = config["password"]

LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class _RandomBot(RandomPlayer):
    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER
    account_configuration = AccountConfiguration(
        username="RandomBot", password=password
    )


def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Random Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(f"Random Bot / Using ladder server configuration: {config.websocket_url}")
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


def create_random_bot(play_format: int) -> "_RandomBot":
    # We set `server_configuration` as a *class attribute* for poke_env.
    chosen_server_configuration = get_server_configuration(play_format)

    class RandomBot(_RandomBot):
        server_configuration = chosen_server_configuration

    return RandomBot()
