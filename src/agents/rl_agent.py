from pathlib import Path

import numpy as np
from gymnasium.spaces import Box, Discrete
from poke_env import Player
from poke_env.environment import SinglesEnv
from poke_env.ps_client import ServerConfiguration, ShowdownServerConfiguration
from poke_env.player.battle_order import BattleOrder
from stable_baselines3 import PPO

from config.accounts import get_account_configuration


LOCAL_SERVER = ServerConfiguration(
    "ws://localhost:8000/showdown/websocket",
    "http://localhost:8000/action.php?",
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT / "models" / "mini_move_rl_agent.zip"
OBSERVATION_SIZE = 12
MOVE_ACTIONS = 4


def _safe_hp_fraction(pokemon, default: float) -> float:
    if pokemon is None:
        return default
    value = getattr(pokemon, "current_hp_fraction", default)
    if value is None:
        return default
    return float(value)


def _safe_damage_multiplier(move, opponent) -> float:
    if move is None or opponent is None:
        return 1.0
    try:
        return float(opponent.damage_multiplier(move))
    except Exception:
        return 1.0


def _fainted_fraction(team: dict, team_size: int) -> float:
    if team_size <= 0:
        return 0.0
    fainted = sum(1 for pokemon in team.values() if pokemon.fainted)
    return fainted / team_size


def embed_battle_minimal(battle) -> np.ndarray:
    """Convert a poke-env Battle into the tiny numeric state used by this lesson."""
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    team_size = getattr(battle, "team_size", 6) or 6

    features = [
        _safe_hp_fraction(active, 1.0),
        _safe_hp_fraction(opponent, 1.0),
    ]

    moves = list(battle.available_moves)[:4]
    while len(moves) < 4:
        moves.append(None)

    for move in moves:
        base_power = getattr(move, "base_power", 0) if move is not None else 0
        features.append(float(base_power or 0) / 100.0)

    for move in moves:
        features.append(_safe_damage_multiplier(move, opponent))

    features.extend(
        [
            _fainted_fraction(battle.team, team_size),
            _fainted_fraction(battle.opponent_team, team_size),
        ]
    )

    return np.array(features, dtype=np.float32)


class MiniPokemonRLEnv(SinglesEnv):
    """Small educational RL environment with four move-slot actions."""

    battle_format = "gen9randombattle"

    def __init__(self, **kwargs):
        kwargs.setdefault("battle_format", self.battle_format)
        kwargs.setdefault("server_configuration", LOCAL_SERVER)
        kwargs.setdefault("strict", False)
        super().__init__(**kwargs)

        self.action_spaces = {
            agent: Discrete(MOVE_ACTIONS) for agent in self.possible_agents
        }
        self.observation_spaces = {
            agent: Box(
                low=0.0,
                high=4.0,
                shape=(OBSERVATION_SIZE,),
                dtype=np.float32,
            )
            for agent in self.possible_agents
        }

    @staticmethod
    def action_to_order(action, battle, fake: bool = False, strict: bool = True):
        action = int(np.asarray(action).item())
        moves = list(battle.available_moves)

        if 0 <= action < len(moves):
            return Player.create_order(moves[action])

        return Player.choose_random_singles_move(battle)

    @staticmethod
    def order_to_action(
        order: BattleOrder, battle, fake: bool = False, strict: bool = True
    ) -> np.int64:
        try:
            full_action = SinglesEnv.order_to_action(order, battle, fake, strict)
        except Exception:
            return np.int64(0)

        if 6 <= full_action <= 9:
            return np.int64(full_action - 6)

        return np.int64(0)

    def embed_battle(self, battle) -> np.ndarray:
        return embed_battle_minimal(battle)

    def calc_reward(self, battle) -> float:
        return self.reward_computing_helper(
            battle,
            fainted_value=2.0,
            hp_value=1.0,
            status_value=0.3,
            victory_value=30.0,
        )


class MiniRLBot(Player):
    battle_format = "gen9randombattle"
    server_configuration = LOCAL_SERVER

    def __init__(
        self,
        *,
        account_configuration,
        server_configuration: ServerConfiguration,
        model_path: Path = DEFAULT_MODEL_PATH,
    ):
        super().__init__(
            account_configuration=account_configuration,
            battle_format=self.battle_format,
            server_configuration=server_configuration,
            start_timer_on_battle_start=True,
        )
        if not model_path.exists():
            raise FileNotFoundError(
                f"RL model not found at {model_path}. "
                "Train it first with tools/train_rl_agent.py."
            )
        self.model = PPO.load(model_path)

    def choose_move(self, battle):
        observation = embed_battle_minimal(battle)
        action, _ = self.model.predict(observation, deterministic=True)

        return MiniPokemonRLEnv.action_to_order(action, battle, strict=False)


def get_server_configuration(play_format: int):
    if play_format == 1:
        print("Mini RL Bot / Using local server configuration")
        return LOCAL_SERVER
    if play_format == 2:
        config = ShowdownServerConfiguration
        print(f"Mini RL Bot / Using ladder server configuration: {config.websocket_url}")
        return config
    raise ValueError("Choose a correct answer (1 local / 2 ladder).")


def create_mini_rl_bot(play_format: int) -> "MiniRLBot":
    chosen_server_configuration = get_server_configuration(play_format)
    account_configuration = get_account_configuration(play_format, "MiniRLBot")
    return MiniRLBot(
        account_configuration=account_configuration,
        server_configuration=chosen_server_configuration,
    )
