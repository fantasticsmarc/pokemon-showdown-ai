from poke_env import Player, AccountConfiguration
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
import json

with open("pokemon-showdown-ai/config.json", "r") as f:
    config = json.load(f)

password = config["password"]

# node pokemon-showdown start --no-security
LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class _MaxDamageBot(Player):

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
    account_configuration = AccountConfiguration(
        username="MaxDamageBot",
        password=password,
    )


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


def create_max_damage_bot(play_format: int) -> "_MaxDamageBot":
    # We set `server_configuration` as a *class attribute* for poke_env.
    chosen_server_configuration = get_server_configuration(play_format)

    class MaxDamageBot(_MaxDamageBot):
        server_configuration = chosen_server_configuration

    return MaxDamageBot()
