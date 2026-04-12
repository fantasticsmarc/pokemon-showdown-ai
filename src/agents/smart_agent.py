from poke_env import Player, AccountConfiguration
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from poke_env.battle.move_category import MoveCategory
import json
import battle.utilities as utilities

with open("pokemon-showdown-ai/config.json", "r") as f:
    config = json.load(f)

password = config["password"]

LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class _SmartBot(Player):
    prevDamagePercent = 100
    currentdamagePercent = 100
    usedMovePreviously = False
    currentOpponent = None
    previousOpponent = None

    def get_matchup_score(self, my_pokemon, opponent_pokemon):
        # Gets a number that determines how well the Pokemon matches up with opponent. Lower scores are better

        score = 0
        defensive_multiplier = utilities.get_defensive_type_multiplier(
            my_pokemon, opponent_pokemon
        )

        # We add points for weaknesses and subtract points for resistances. We also add points if opponent can outspeed us.
        if defensive_multiplier == 4:
            score += 1
        elif defensive_multiplier == 2:
            score += 0.5
        elif defensive_multiplier == 0.5:
            score -= 0.5
        elif defensive_multiplier == 0.25:
            score -= 1
        if utilities.opponent_can_outspeed(my_pokemon, opponent_pokemon):
            score += 0.5

        return score

    def choose_best_switch(self, battle):
        # Go through each Pokemon that can be switched to, and choose one with the best type matchup score against opponent's active Pokemon.

        # If there are no Pokemon to switch to, you can't choose a best switch
        if not battle.available_switches:
            return None

        best_score = float("inf")
        best_switch = None

        for switch in battle.available_switches:
            score = self.get_matchup_score(switch, battle.opponent_active_pokemon)
            if score < best_score:
                best_score = score
                best_switch = switch
        return best_switch

    def choose_move(self, battle):
        self.currentOpponent = battle.opponent_active_pokemon
        if self.currentOpponent != self.previousOpponent:
            self.currentDamagePercent = 100
            self.previousOpponent = self.currentOpponent
            print(f"New opponent: {self.currentOpponent}")
        else:
            self.currentDamagePercent = battle.opponent_active_pokemon.current_hp

        self.prevDamagePercent = self.currentDamagePercent
        self.usedMovePreviously = False
        self.previousOpponent = self.currentOpponent

        if not battle.available_moves:
            best_switch = self.choose_best_switch(battle)
            if best_switch is None:
                return self.choose_random_move(battle)
            return self.create_order(best_switch)

        # Use matchup score to determine who to switch to
        matchup_score = self.get_matchup_score(
            battle.active_pokemon, battle.opponent_active_pokemon
        )
        # If negative situation (bad matchup), try switching to a better Pokemon
        if matchup_score >= 1:
            best_switch = self.choose_best_switch(battle)
            if best_switch is not None:
                return self.create_order(best_switch)

        self.usedMovePreviously = True
        best_move = max(
            battle.available_moves,
            key=lambda move: utilities.calculate_damage(
                move, battle.active_pokemon, battle.opponent_active_pokemon, True, True
            ),
        )
        print(f"Best move: {best_move}, Matchup score: {matchup_score}")

        return self.create_order(best_move)

    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER
    account_configuration = AccountConfiguration(
        username="SmartBot",
        password=password,
    )


def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Smart Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(f"Smart Bot / Using ladder server configuration: {config.websocket_url}")
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


def create_smart_bot(play_format: int) -> "_SmartBot":
    # We set `server_configuration` as a *class attribute* for poke_env.
    chosen_server_configuration = get_server_configuration(play_format)

    class SmartBot(_SmartBot):
        server_configuration = chosen_server_configuration

    return SmartBot()
