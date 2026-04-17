from poke_env.player.baselines import SimpleHeuristicsPlayer
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from config.accounts import get_account_configuration

LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class SHeuristicsBot(SimpleHeuristicsPlayer):
    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER

    # Build the random bot with the selected account and server configuration.
    def __init__(
        self,
        *,
        account_configuration,
        server_configuration: ServerConfiguration,
    ):
        super().__init__(
            account_configuration=account_configuration,
            battle_format=self.battle_format,
            server_configuration=server_configuration,
        )


# Choose between the local Showdown server and the public ladder server.
def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Simple Heuristics Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(
            f"Simple Heuristics Bot / Using ladder server configuration: {config.websocket_url}"
        )
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


# Create a ready-to-use simple heuristics bot with the correct server and account settings.
def create_simple_heuristics_bot(play_format: int) -> "SHeuristicsBot":
    chosen_server_configuration = get_server_configuration(play_format)
    account_configuration = get_account_configuration(play_format, "SHeuristicsBot")
    return SHeuristicsBot(
        account_configuration=account_configuration,
        server_configuration=chosen_server_configuration,
    )
