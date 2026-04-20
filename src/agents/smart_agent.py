# SmartBot combines move value, matchup danger, setup safety and special mechanics to choose between attacking, switching and spending battle resources.
"""
Current position: active=chienpao (pokemon object) [Active: True, Status: PSN] | opponent=lugia (pokemon object) [Active: True, Status: None] | matchup=25.57 | best_move=sacredsword (Move object) | best_move_value=-44.75 | immediate_threat=False | likely_ko_now=False | bot_moves_first=True | expected_damage=11.25 | damage_percent=11.25 | remaining_hp=96.00 | effectiveness=0.25
Switch candidate: toucannon (pokemon object) [Active: False, Status: None] | matchup=84.65 | hazards=0.00 | final=84.65
Switch candidate: braviaryhisui (pokemon object) [Active: False, Status: None] | matchup=104.27 | hazards=0.00 | final=104.27
Switch candidate: golurk (pokemon object) [Active: False, Status: PSN] | matchup=29.40 | hazards=12.50 | final=41.90
Switch decision summary: current=25.57 | best_switch=golurk (pokemon object) [Active: False, Status: PSN] | switch_score=41.90 | adjusted_switch=53.90 | best_move=-44.75 | immediate_threat=False | choose_switch=False
Best move: sacredsword (Move object), move value: -44.75, matchup score: 25.57, immediate threat: False
"""

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
    debug_enabled = True

    # Build the smart bot with the selected account and server configuration.
    def __init__(
        self,
        *,
        account_configuration,
        server_configuration: ServerConfiguration,
        start_timer_on_battle_start=True,
    ):
        super().__init__(
            account_configuration=account_configuration,
            battle_format=self.battle_format,
            server_configuration=server_configuration,
            start_timer_on_battle_start=True,
        )

    # Evaluate how favorable a Pokemon is against the current opponent.
    def get_matchup_score(self, my_pokemon, opponent_pokemon):
        # Lower scores are better. This now considers offensive pressure, defensive safety, abilities, boosts, debuffs and status.
        return utilities.evaluate_pokemon_matchup(
            my_pokemon, opponent_pokemon, self.current_battle
        )

    # Find the best available switch and only return it if it clearly improves the matchup.
    def choose_best_switch(self, battle, current_matchup_score=None):
        if not battle.available_switches:
            return None

        best_score = float("inf")
        best_switch = None
        best_move_value = None

        for switch in battle.available_switches:
            # Each switch is evaluated as a full board-state option, not just by typing, so hazards on our side can make an otherwise good pivot bad.
            matchup_score = utilities.evaluate_pokemon_matchup(
                switch, battle.opponent_active_pokemon, battle
            )
            hazard_penalty = utilities.get_switch_hazard_penalty(switch, battle)
            score = matchup_score + hazard_penalty

            if self.debug_enabled:
                print(
                    "Switch candidate: "
                    f"{switch} | matchup={matchup_score:.2f} "
                    f"| hazards={hazard_penalty:.2f} | final={score:.2f}"
                )
            if score < best_score:
                best_score = score
                best_switch = switch

        if current_matchup_score is None:
            return best_switch

        # Compare the best switch not only against the current matchup, but also against the best move we can fire immediately from the current Pokemon.
        if battle.available_moves:
            best_move_value = utilities.daniela(
                self.choose_best_move(battle),
                battle.active_pokemon,
                battle.opponent_active_pokemon,
                battle,
                True,
            )
        else:
            best_move_value = 0

        # If the current active Pokemon is under immediate threat, we lower the improvement threshold so the bot actually escapes bad positions.
        switch_margin = self.switch_margin
        immediate_threat = utilities.is_immediate_switch_threat(
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            battle,
        )
        if immediate_threat:
            switch_margin = 4

        # The switch only happens if it beats both the current board position and the value of simply attacking right now.
        adjusted_switch_score = best_score + switch_margin
        should_switch = utilities.should_switch_over_best_move(
            current_matchup_score,
            adjusted_switch_score,
            best_move_value,
            immediate_threat,
        )

        if self.debug_enabled and best_switch is not None:
            print(
                "Switch decision summary: "
                f"current={current_matchup_score:.2f} | best_switch={best_switch} "
                f"| switch_score={best_score:.2f} | adjusted_switch={adjusted_switch_score:.2f} "
                f"| best_move={best_move_value:.2f} | immediate_threat={immediate_threat} "
                f"| choose_switch={should_switch}"
            )

        if best_switch and should_switch:
            return best_switch
        return None

    # Pick the move with the highest estimated overall value in the current turn.
    def choose_best_move(self, battle):
        return max(
            battle.available_moves,
            key=lambda move: utilities.daniela(
                move,
                battle.active_pokemon,
                battle.opponent_active_pokemon,
                battle,
                True,
            ),
        )

    # Main decision function: compare switching against staying in and then choose the best action.
    def choose_move(self, battle):
        # Save the battle reference so helper methods can evaluate the current state without threading battle through every call manually.
        self.current_battle = battle
        self.currentOpponent = battle.opponent_active_pokemon

        # Reset our simple opponent-tracking state whenever the rival active Pokemon changes, so later heuristics are based on the current board.
        if self.currentOpponent != self.previousOpponent:
            self.currentDamagePercent = 100
            self.previousOpponent = self.currentOpponent
            print(f"New opponent: {self.currentOpponent}")
        else:
            self.currentDamagePercent = battle.opponent_active_pokemon.current_hp

        # Keep these values updated because older parts of the bot still use them as turn-to-turn memory.
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
        current_best_move = self.choose_best_move(battle)
        current_best_move_value = utilities.daniela(
            current_best_move,
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            battle,
            True,
        )
        immediate_threat = utilities.is_immediate_switch_threat(
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            battle,
        )
        likely_ko_now = utilities.is_best_move_likely_to_ko(
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            current_best_move,
            battle,
        )
        ko_debug_data = utilities.get_ko_debug_data(
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            current_best_move,
            battle,
        )
        bot_moves_first = (
            current_best_move.priority > 0
            or utilities.get_effective_speed(
                battle.active_pokemon,
                battle,
            )
            >= utilities.get_effective_speed(
                battle.opponent_active_pokemon,
                battle,
            )
        )

        if self.debug_enabled:
            print(
                "Current position: "
                f"active={battle.active_pokemon} | opponent={battle.opponent_active_pokemon} "
                f"| matchup={current_matchup_score:.2f} | best_move={current_best_move} "
                f"| best_move_value={current_best_move_value:.2f} "
                f"| immediate_threat={immediate_threat} | likely_ko_now={likely_ko_now} "
                f"| bot_moves_first={bot_moves_first} "
                f"| expected_damage={ko_debug_data['expected_damage']:.2f} "
                f"| damage_percent={ko_debug_data['damage_percent']:.2f} "
                f"| remaining_hp={ko_debug_data['remaining_hp']:.2f} "
                f"| effectiveness={ko_debug_data['effectiveness']}"
            )

        # If we can probably remove the opponent right now, attacking is usually better than pivoting into a future position and risking a bad double switch.
        if likely_ko_now and bot_moves_first:
            if self.debug_enabled:
                print(
                    "Finishing rule: attack now because the opponent is in likely KO range "
                    "and we do not expect to lose the turn order."
                )
            best_move = current_best_move
            best_move_value = current_best_move_value
            special_mechanic = utilities.choose_special_mechanic(
                battle,
                best_move,
                best_move_value,
                current_matchup_score,
            )
            if self.debug_enabled:
                print(
                    "Special mechanic decision: "
                    f"selected={special_mechanic} | can_tera={battle.can_tera} "
                    f"| can_dynamax={battle.can_dynamax} | can_mega={battle.can_mega_evolve} "
                    f"| can_z={battle.can_z_move}"
                )
            if special_mechanic == "terastallize":
                print(f"Using special mechanic: {special_mechanic}")
                return self.create_order(best_move, terastallize=True)
            if special_mechanic == "dynamax":
                print(f"Using special mechanic: {special_mechanic}")
                return self.create_order(best_move, dynamax=True)
            if special_mechanic == "mega_evolve":
                print(f"Using special mechanic: {special_mechanic}")
                return self.create_order(best_move, mega_evolve=True)
            if special_mechanic == "z_move":
                print(f"Using special mechanic: {special_mechanic}")
                return self.create_order(best_move, z_move=True)
            return self.create_order(best_move)

        # Only switch if the best available teammate is clearly better than staying in with the current active Pokemon.
        best_switch = self.choose_best_switch(battle, current_matchup_score)
        if best_switch is not None:
            print(
                f"Switching from {battle.active_pokemon} to {best_switch} "
                f"(score {current_matchup_score:.2f})"
            )
            return self.create_order(best_switch)

        self.usedMovePreviously = True

        # If staying in is better, choose the move with the highest estimated value after damage, boosts, status and utility are considered.
        best_move = current_best_move
        best_move_value = current_best_move_value
        print(
            f"Best move: {best_move}, "
            f"move value: {best_move_value:.2f}, "
            f"matchup score: {current_matchup_score:.2f}, "
            f"immediate threat: {immediate_threat}"
        )

        # Ask the mechanic selector whether this is the right turn to specially use Mega, Z-Move, Tera or Dynamax, and if so which one wins the comparison.
        special_mechanic = utilities.choose_special_mechanic(
            battle,
            best_move,
            best_move_value,
            current_matchup_score,
        )
        if self.debug_enabled:
            print(
                "Special mechanic decision: "
                f"selected={special_mechanic} | can_tera={battle.can_tera} "
                f"| can_dynamax={battle.can_dynamax} | can_mega={battle.can_mega_evolve} "
                f"| can_z={battle.can_z_move}"
            )
        if special_mechanic == "terastallize":
            print(f"Using special mechanic: {special_mechanic}")
            return self.create_order(best_move, terastallize=True)
        if special_mechanic == "dynamax":
            print(f"Using special mechanic: {special_mechanic}")
            return self.create_order(best_move, dynamax=True)
        if special_mechanic == "mega_evolve":
            print(f"Using special mechanic: {special_mechanic}")
            return self.create_order(best_move, mega_evolve=True)
        if special_mechanic == "z_move":
            print(f"Using special mechanic: {special_mechanic}")
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
