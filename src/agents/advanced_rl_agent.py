from pathlib import Path

import numpy as np
from gymnasium.spaces import Box, Discrete
from poke_env import Player
from poke_env.environment import SinglesEnv
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from poke_env.player.battle_order import BattleOrder
from stable_baselines3 import PPO

import battle.core as core
import battle.utilities as utilities
import strategy.competitive.heuristics as competitive
import strategy.competitive.moves as competitive_moves
from config.accounts import get_account_configuration


LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADVANCED_MODEL_PATH = ROOT / "models" / "advanced_rl_agent.zip"

MOVE_SLOTS = 4
SWITCH_SLOTS = 6
ACTION_SIZE = MOVE_SLOTS + SWITCH_SLOTS
MOVE_FEATURES = 14
SWITCH_FEATURES = 8
CONTEXT_FEATURES = 17
OBSERVATION_SIZE = CONTEXT_FEATURES + MOVE_SLOTS * MOVE_FEATURES + SWITCH_SLOTS * SWITCH_FEATURES


def _clip(value: float, low: float = -5.0, high: float = 5.0) -> float:
    if not np.isfinite(value):
        return 0.0
    return float(np.clip(value, low, high))


def _fraction(value: float, scale: float = 100.0) -> float:
    return _clip(value / scale)


def _hp_fraction(pokemon, default: float = 0.0) -> float:
    if pokemon is None:
        return default
    hp = getattr(pokemon, "current_hp_fraction", default)
    return default if hp is None else float(hp)


def _remaining_fraction(team: dict, team_size: int) -> float:
    if team_size <= 0:
        return 0.0
    remaining = sum(1 for pokemon in team.values() if not pokemon.fainted)
    return remaining / team_size


def _status_flag(pokemon) -> float:
    return float(pokemon is not None and getattr(pokemon, "status", None) is not None)


def _safe_context(battle, active_first_turn: bool | None = None):
    try:
        return competitive.build_turn_context(battle, active_first_turn)
    except Exception:
        return None


def _safe_competitive_actions(battle, context):
    if context is None:
        return []
    try:
        return competitive.build_competitive_actions(battle, context)
    except Exception:
        return []


def _best_move_action_value(actions, move) -> float:
    values = [
        action.value
        for action in actions
        if action.move is not None and getattr(action.move, "id", None) == move.id
    ]
    return max(values) if values else 0.0


def _best_switch_action_value(actions, switch) -> float:
    values = [
        action.value
        for action in actions
        if action.switch is not None
        and getattr(action.switch, "base_species", None) == switch.base_species
    ]
    return max(values) if values else 0.0


def _phase_features(phase: str) -> list[float]:
    return [
        float(phase == "early"),
        float(phase == "mid"),
        float(phase == "late"),
    ]


def _speed_advantage(my_pokemon, opponent, battle) -> float:
    try:
        return float(
            utilities.get_effective_speed(my_pokemon, battle)
            >= utilities.get_effective_speed(opponent, battle)
        )
    except Exception:
        return 0.0


def _move_features(battle, move, context, actions) -> list[float]:
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    if move is None or active is None or opponent is None:
        return [0.0] * MOVE_FEATURES

    try:
        damage = utilities.estimate_damage_percent(move, active, opponent, battle, True)
    except Exception:
        damage = 0.0
    try:
        multiplier = utilities.get_effective_type_multiplier(opponent, move, active)
    except Exception:
        multiplier = 1.0

    profile = competitive_moves.get_move_profile(move)
    return [
        1.0,
        _fraction(utilities.get_effective_base_power(move, active, opponent)),
        _fraction(damage),
        _clip(multiplier / 4.0, 0.0, 1.0),
        _clip(competitive.get_move_accuracy(move), 0.0, 1.0),
        _clip(core.get_move_priority(move) / 5.0),
        float(profile.is_attack),
        float(profile.is_setup),
        float(profile.is_healing),
        float(profile.is_hazard),
        float(profile.is_hazard_removal),
        float(profile.is_disruption),
        float(profile.is_priority),
        _fraction(_best_move_action_value(actions, move)),
    ]


def _switch_features(battle, switch, context, actions) -> list[float]:
    opponent = battle.opponent_active_pokemon
    if switch is None or opponent is None:
        return [0.0] * SWITCH_FEATURES

    try:
        matchup = utilities.evaluate_pokemon_matchup(switch, opponent, battle)
    except Exception:
        matchup = 0.0
    try:
        hazard_penalty = utilities.get_switch_hazard_penalty(switch, battle)
    except Exception:
        hazard_penalty = 0.0

    return [
        float(switch in battle.available_switches),
        _hp_fraction(switch),
        float(switch.fainted),
        _status_flag(switch),
        _fraction(matchup),
        _fraction(hazard_penalty),
        _speed_advantage(switch, opponent, battle),
        _fraction(_best_switch_action_value(actions, switch)),
    ]


def embed_battle_advanced(battle, active_first_turn: bool | None = None) -> np.ndarray:
    context = _safe_context(battle, active_first_turn)
    actions = _safe_competitive_actions(battle, context)
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    team_size = getattr(battle, "team_size", 6) or 6

    if context is None:
        context_features = [0.0] * CONTEXT_FEATURES
    else:
        context_features = [
            _hp_fraction(active),
            _hp_fraction(opponent),
            _remaining_fraction(battle.team, team_size),
            _remaining_fraction(battle.opponent_team, team_size),
            _fraction(context.matchup_score),
            _fraction(context.opponent_threat),
            float(context.safe_turn),
            float(context.emergency),
            _fraction(context.active_importance),
            _fraction(context.best_attack_value),
            _fraction(context.best_attack_damage),
            _clip(context.opponent_hp_percent / 100.0, 0.0, 1.0),
            float(context.expected_opponent_switch),
            float(context.active_first_turn),
        ]
        context_features.extend(_phase_features(context.phase))

    moves = list(battle.available_moves)[:MOVE_SLOTS]
    moves.extend([None] * (MOVE_SLOTS - len(moves)))
    move_features = [
        value
        for move in moves
        for value in _move_features(battle, move, context, actions)
    ]

    team = list(battle.team.values())[:SWITCH_SLOTS]
    team.extend([None] * (SWITCH_SLOTS - len(team)))
    switch_features = [
        value
        for switch in team
        for value in _switch_features(battle, switch, context, actions)
    ]

    observation = np.array(context_features + move_features + switch_features, dtype=np.float32)
    if observation.shape != (OBSERVATION_SIZE,):
        return np.zeros(OBSERVATION_SIZE, dtype=np.float32)
    return observation


def _move_order_with_mechanic(battle, move):
    context = _safe_context(battle)
    move_value = 0.0
    matchup_score = 0.0
    if context is not None:
        actions = _safe_competitive_actions(battle, context)
        move_value = _best_move_action_value(actions, move)
        matchup_score = context.matchup_score

    mechanic = utilities.choose_special_mechanic(battle, move, move_value, matchup_score)
    if mechanic == "terastallize":
        return Player.create_order(move, terastallize=True)
    if mechanic == "dynamax":
        return Player.create_order(move, dynamax=True)
    if mechanic == "mega_evolve":
        return Player.create_order(move, mega=True)
    if mechanic == "z_move":
        return Player.create_order(move, z_move=True)
    return Player.create_order(move)


class AdvancedPokemonRLEnv(SinglesEnv):
    battle_format = "gen9randombattle"

    def __init__(self, **kwargs):
        kwargs.setdefault("battle_format", self.battle_format)
        kwargs.setdefault("server_configuration", LOCAL_SERVER)
        kwargs.setdefault("strict", False)
        super().__init__(**kwargs)

        self.action_spaces = {
            agent: Discrete(ACTION_SIZE) for agent in self.possible_agents
        }
        self.observation_spaces = {
            agent: Box(
                low=-5.0,
                high=5.0,
                shape=(OBSERVATION_SIZE,),
                dtype=np.float32,
            )
            for agent in self.possible_agents
        }

    @staticmethod
    def action_to_order(action, battle, fake: bool = False, strict: bool = True):
        action = int(np.asarray(action).item())

        if action < MOVE_SLOTS:
            moves = list(battle.available_moves)
            if action < len(moves):
                return _move_order_with_mechanic(battle, moves[action])
            return Player.choose_random_singles_move(battle)

        team_index = action - MOVE_SLOTS
        team = list(battle.team.values())
        if team_index < len(team) and team[team_index] in battle.available_switches:
            return Player.create_order(team[team_index])

        return Player.choose_random_singles_move(battle)

    @staticmethod
    def order_to_action(
        order: BattleOrder, battle, fake: bool = False, strict: bool = True
    ) -> np.int64:
        try:
            full_action = SinglesEnv.order_to_action(order, battle, fake, strict)
        except Exception:
            return np.int64(0)

        if 0 <= full_action <= 5:
            return np.int64(MOVE_SLOTS + full_action)
        if 6 <= full_action <= 25:
            return np.int64((full_action - 6) % MOVE_SLOTS)
        return np.int64(0)

    def embed_battle(self, battle) -> np.ndarray:
        return embed_battle_advanced(battle)

    def calc_reward(self, battle) -> float:
        return self.reward_computing_helper(
            battle,
            fainted_value=4.0,
            hp_value=2.0,
            status_value=0.4,
            victory_value=60.0,
        )


class AdvancedRLBot(Player):
    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER

    def __init__(
        self,
        *,
        account_configuration,
        server_configuration: ServerConfiguration,
        model_path: Path = DEFAULT_ADVANCED_MODEL_PATH,
    ):
        super().__init__(
            account_configuration=account_configuration,
            battle_format=self.battle_format,
            server_configuration=server_configuration,
            start_timer_on_battle_start=True,
        )
        if not model_path.exists():
            raise FileNotFoundError(
                f"Advanced RL model not found at {model_path}. "
                "Train it first with tools/train_advanced_rl_agent.py."
            )
        self.model = PPO.load(model_path)

    def choose_move(self, battle):
        observation = embed_battle_advanced(battle)
        action, _ = self.model.predict(observation, deterministic=True)
        return AdvancedPokemonRLEnv.action_to_order(action, battle, strict=False)


def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Advanced RL Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(f"Advanced RL Bot / Using ladder server configuration: {config.websocket_url}")
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


def create_advanced_rl_bot(play_format: int) -> "AdvancedRLBot":
    chosen_server_configuration = get_server_configuration(play_format)
    account_configuration = get_account_configuration(play_format, "AdvancedRLBot")
    return AdvancedRLBot(
        account_configuration=account_configuration,
        server_configuration=chosen_server_configuration,
    )
