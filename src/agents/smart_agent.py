# TODO Mejorar lógica utilizando habilidades (habilities.py) y solucionar casos como el de Cresselia
import battle.utilities as utilities
from poke_env import Player
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from config.accounts import get_account_configuration

LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class SmartBot(Player):
    prevDamagePercent = 100
    currentdamagePercent = 100
    usedMovePreviously = False
    currentOpponent = None
    previousOpponent = None
    switch_margin = 12

    # Build the smart bot with the selected account and server configuration.
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

    # Evaluate how favorable a Pokemon is against the current opponent.
    def get_matchup_score(self, my_pokemon, opponent_pokemon):
        # Lower scores are better. This now considers offensive pressure,
        # defensive safety, abilities, boosts, debuffs and status.
        return utilities.evaluate_pokemon_matchup(
            my_pokemon, opponent_pokemon, self.current_battle
        )

    # Find the best available switch and only return it if it clearly improves the matchup.
    def choose_best_switch(self, battle, current_matchup_score=None):
        if not battle.available_switches:
            return None

        best_score = float("inf")
        best_switch = None

        for switch in battle.available_switches:
            score = utilities.evaluate_pokemon_matchup(
                switch, battle.opponent_active_pokemon, battle
            )
            if score < best_score:
                best_score = score
                best_switch = switch

        if current_matchup_score is None:
            return best_switch

        if best_switch and best_score + self.switch_margin < current_matchup_score:
            return best_switch
        return None

    # Pick the move with the highest estimated overall value in the current turn.
    def choose_best_move(self, battle):
        return max(
            battle.available_moves,
            key=lambda move: utilities.estimate_move_value(
                move,
                battle.active_pokemon,
                battle.opponent_active_pokemon,
                battle,
                True,
            ),
        )

    # Main decision function: compare switching against staying in and then choose the best action.
    def choose_move(self, battle):
        # Save the battle reference so helper methods can evaluate the current
        # state without threading battle through every call manually.
        self.current_battle = battle
        self.currentOpponent = battle.opponent_active_pokemon

        # Reset our simple opponent-tracking state whenever the rival active
        # Pokemon changes, so later heuristics are based on the current board.
        if self.currentOpponent != self.previousOpponent:
            self.currentDamagePercent = 100
            self.previousOpponent = self.currentOpponent
            print(f"New opponent: {self.currentOpponent}")
        else:
            self.currentDamagePercent = battle.opponent_active_pokemon.current_hp

        # Keep these values updated because older parts of the bot still use
        # them as turn-to-turn memory.
        self.prevDamagePercent = self.currentDamagePercent
        self.usedMovePreviously = False
        self.previousOpponent = self.currentOpponent

        if not battle.available_moves:
            # If we cannot attack, the turn is forced into a switch decision.
            best_switch = self.choose_best_switch(battle)
            if best_switch is None:
                return self.choose_random_move(battle)
            return self.create_order(best_switch)

        # Score the current active Pokemon before considering a switch.
        current_matchup_score = utilities.evaluate_pokemon_matchup(
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            battle,
        )

        # Only switch if the best available teammate is clearly better than
        # staying in with the current active Pokemon.
        best_switch = self.choose_best_switch(battle, current_matchup_score)
        if best_switch is not None:
            print(
                f"Switching from {battle.active_pokemon} to {best_switch} "
                f"(score {current_matchup_score:.2f})"
            )
            return self.create_order(best_switch)

        self.usedMovePreviously = True

        # If staying in is better, choose the move with the highest estimated
        # value after damage, boosts, status and utility are considered.
        best_move = self.choose_best_move(battle)
        best_move_value = utilities.estimate_move_value(
            best_move,
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            battle,
            True,
        )
        print(
            f"Best move: {best_move}, "
            f"move value: {best_move_value:.2f}, "
            f"matchup score: {current_matchup_score:.2f}"
        )

        # Ask the mechanic selector whether this is the right turn to spend
        # Mega, Z-Move, Tera or Dynamax, and if so which one wins the comparison.
        special_mechanic = utilities.choose_special_mechanic(
            battle,
            best_move,
            best_move_value,
            current_matchup_score,
        )
        if special_mechanic == "terastallize":
            return self.create_order(best_move, terastallize=True)
        if special_mechanic == "dynamax":
            return self.create_order(best_move, dynamax=True)
        if special_mechanic == "mega_evolve":
            return self.create_order(best_move, mega_evolve=True)
        if special_mechanic == "z_move":
            return self.create_order(best_move, z_move=True)

        return self.create_order(best_move)

    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER


# Choose between the local Showdown server and the public ladder server.
def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Smart Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(f"Smart Bot / Using ladder server configuration: {config.websocket_url}")
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


# Create a ready-to-use smart bot with the correct server and account settings.
def create_smart_bot(play_format: int) -> "SmartBot":
    chosen_server_configuration = get_server_configuration(play_format)
    account_configuration = get_account_configuration(play_format, "SmartBot")
    return SmartBot(
        account_configuration=account_configuration,
        server_configuration=chosen_server_configuration,
    )
