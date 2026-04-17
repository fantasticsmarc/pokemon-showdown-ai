from poke_env import Player
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from config.accounts import get_account_configuration

# node pokemon-showdown start --no-security
LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class MaxDamageBot(Player):
    # Build the max-damage bot with the selected account and server configuration.
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

    # Pick the move with the highest raw base power and use battle gimmicks if available.
    def choose_move(self, battle):
        if battle.available_moves:
            best_move = max(battle.available_moves, key=lambda move: move.base_power)

            if battle.can_tera:
                return self.create_order(best_move, terastallize=True)
            if battle.can_dynamax:
                return self.create_order(best_move, dynamax=True)
            if battle.can_mega_evolve:
                return self.create_order(best_move, mega_evolve=True)
            if battle.can_z_move:
                return self.create_order(best_move, z_move=True)

            return self.create_order(best_move)

        else:
            return self.choose_random_move(battle)

    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER


# Choose between the local Showdown server and the public ladder server.
def get_server_configuration(play_format: int):
    if play_format == 1:
        print("MaxDamage Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(
            f"MaxDamage Bot / Using ladder server configuration: {config.websocket_url}"
        )
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


# Create a ready-to-use max-damage bot with the correct server and account settings.
def create_max_damage_bot(play_format: int) -> "MaxDamageBot":
    chosen_server_configuration = get_server_configuration(play_format)
    account_configuration = get_account_configuration(play_format, "MaxDamageBot")
    return MaxDamageBot(
        account_configuration=account_configuration,
        server_configuration=chosen_server_configuration,
    )
