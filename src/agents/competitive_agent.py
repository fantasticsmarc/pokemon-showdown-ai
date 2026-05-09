# CompetitiveBot uses a separate competitive heuristic layer. The agent itself stays small: it reads the battle, asks for a plan-aware action, then sends the corresponding Showdown order.

import battle.utilities as utilities
import strategy.competitive.heuristics as competitive
from poke_env import Player
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from config.accounts import get_account_configuration

LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)


class CompetitiveBot(Player):
    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER
    debug_enabled = True

    # Build the competitive bot with the selected account and server configuration.
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
            start_timer_on_battle_start=True,
        )
        self.last_switch_from = None
        self.last_switch_to = None
        self.previous_opponent = None
        self.opponent_change_count = 0
        self.last_debug_team_signature = None
        self.current_battle_tag = None
        self.recent_actions = []
        self.previous_active = None
        self.active_action_count = 0
        self.active_first_turn = True

    # Track opponent active changes for debug only. This includes KOs and forced switches, so it should not be treated as a reliable voluntary-switch read.
    def update_battle_memory(self, battle):
        battle_tag = getattr(battle, "battle_tag", None)
        if battle_tag != self.current_battle_tag:
            # Each battle needs fresh memory. Otherwise a 50-battle benchmark
            # makes opponent_change_count grow forever and pollute debug.
            self.current_battle_tag = battle_tag
            self.last_switch_from = None
            self.last_switch_to = None
            self.previous_opponent = None
            self.opponent_change_count = 0
            self.last_debug_team_signature = None
            self.recent_actions = []
            self.previous_active = None
            self.active_action_count = 0
            self.active_first_turn = True

        current_active = battle.active_pokemon
        if current_active != self.previous_active:
            self.previous_active = current_active
            self.active_action_count = 0
        self.active_first_turn = self.active_action_count == 0

        current_opponent = battle.opponent_active_pokemon
        if (
            self.previous_opponent is not None
            and current_opponent != self.previous_opponent
        ):
            self.opponent_change_count += 1
        self.previous_opponent = current_opponent

    # Apply Tera, Dynamax, Mega or Z-Move when the shared mechanic heuristic says it is worth spending.
    def create_competitive_move_order(self, battle, action, context):
        move = action.move
        special_mechanic = utilities.choose_special_mechanic(
            battle,
            move,
            action.value,
            context.matchup_score,
        )

        if self.debug_enabled:
            print(
                "Competitive mechanic: "
                f"selected={special_mechanic} | move={move} "
                f"| action={action.kind} | value={action.value:.2f}"
            )

        if special_mechanic == "terastallize":
            return self.create_order(move, terastallize=True)
        if special_mechanic == "dynamax":
            return self.create_order(move, dynamax=True)
        if special_mechanic == "mega_evolve":
            return self.create_order(move, mega_evolve=True)
        if special_mechanic == "z_move":
            return self.create_order(move, z_move=True)
        return self.create_order(move)

    def remember_action(self, action):
        self.recent_actions.append(competitive.get_action_memory_entry(action))
        self.recent_actions = self.recent_actions[-6:]
        if action.kind != "switch":
            self.active_action_count += 1

    # Print the plan-level context so testing shows why the bot chose a move.
    def debug_context(self, battle, context, action):
        active_profile = context.plan.profiles.get(battle.active_pokemon)
        active_roles = sorted(active_profile.roles) if active_profile else []
        team_signature = competitive.get_team_debug_signature(context.plan)
        actions = competitive.build_competitive_actions(
            battle,
            context,
            self.last_switch_from,
            self.recent_actions,
        )

        if team_signature != self.last_debug_team_signature:
            print(competitive.format_team_plan_debug(context.plan))
            self.last_debug_team_signature = team_signature

        print(
            "Competitive plan: "
            f"style={context.plan.style} | phase={context.phase} "
            f"| style_reason={context.plan.style_reason} "
            f"| active_roles={active_roles} "
            f"| matchup={context.matchup_score:.2f} "
            f"| threat={context.opponent_threat:.2f} "
            f"| safe_turn={context.safe_turn} "
            f"| active_importance={context.active_importance:.2f} "
            f"| best_attack_damage={context.best_attack_damage:.2f} "
            f"| opponent_hp={context.opponent_hp_percent:.2f} "
            f"| opponent_changes={self.opponent_change_count} "
            f"| expected_switch={context.expected_opponent_switch} "
            f"| expected_switch_reason={context.expected_switch_reason} "
            f"| active_first_turn={context.active_first_turn}"
        )
        print(
            "Competitive action: "
            f"kind={action.kind} | move={action.move} | switch={action.switch} "
            f"| value={action.value:.2f} | reason={action.reason}"
        )
        print(competitive.format_action_debug(actions))

    # Main decision function: choose a plan-aware competitive action.
    def choose_move(self, battle):
        self.update_battle_memory(battle)
        context = competitive.build_turn_context(battle, self.active_first_turn)

        if not battle.available_moves:
            switch = competitive.choose_forced_switch(battle, context)
            if switch is None:
                return self.choose_random_move(battle)
            self.last_switch_from = battle.active_pokemon
            self.last_switch_to = switch
            self.remember_action(
                competitive.CompetitiveAction("switch", 0, switch=switch)
            )
            return self.create_order(switch)

        action = competitive.choose_competitive_action(
            battle,
            context,
            self.last_switch_from,
            self.recent_actions,
        )

        if self.debug_enabled:
            self.debug_context(battle, context, action)

        if action.kind == "switch" and action.switch is not None:
            self.last_switch_from = battle.active_pokemon
            self.last_switch_to = action.switch
            self.remember_action(action)
            return self.create_order(action.switch)

        if action.move is not None:
            self.remember_action(action)
            return self.create_competitive_move_order(battle, action, context)

        return self.choose_random_move(battle)


# Choose between the local Showdown server and the public ladder server.
def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Competitive Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(
            f"Competitive Bot / Using ladder server configuration: {config.websocket_url}"
        )
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


# Create a ready-to-use competitive bot with the correct server and account settings.
def create_competitive_bot(play_format: int) -> "CompetitiveBot":
    chosen_server_configuration = get_server_configuration(play_format)
    account_configuration = get_account_configuration(play_format, "CompetitiveBot")
    return CompetitiveBot(
        account_configuration=account_configuration,
        server_configuration=chosen_server_configuration,
    )
