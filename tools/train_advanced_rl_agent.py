import argparse
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from poke_env import AccountConfiguration
from poke_env.environment import SingleAgentWrapper
from poke_env.player.baselines import MaxBasePowerPlayer, RandomPlayer, SimpleHeuristicsPlayer
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

from agents.advanced_rl_agent import (
    DEFAULT_ADVANCED_MODEL_PATH,
    LOCAL_SERVER,
    AdvancedPokemonRLEnv,
)
from agents.competitive_agent import CompetitiveBot


OPPONENTS = {
    "random": RandomPlayer,
    "max": MaxBasePowerPlayer,
    "simple": SimpleHeuristicsPlayer,
    "competitive": CompetitiveBot,
}


def build_opponent(name: str, username: str):
    opponent_class = OPPONENTS[name]
    account_configuration = AccountConfiguration(username=username, password=None)
    if opponent_class is CompetitiveBot:
        opponent = opponent_class(
            account_configuration=account_configuration,
            server_configuration=LOCAL_SERVER,
        )
    else:
        opponent = opponent_class(
            account_configuration=account_configuration,
            battle_format="gen9randombattle",
            server_configuration=LOCAL_SERVER,
        )
    if hasattr(opponent, "debug_enabled"):
        opponent.debug_enabled = False
    return opponent


def build_training_env(opponent_name: str):
    suffix = uuid.uuid4().hex[:8]
    base_env = AdvancedPokemonRLEnv(
        account_configuration1=AccountConfiguration(
            username=f"AdvRL{suffix}",
            password=None,
        ),
        account_configuration2=AccountConfiguration(
            username=f"AdvEnv{suffix}",
            password=None,
        ),
    )
    opponent = build_opponent(opponent_name, f"AdvOpp{suffix}")
    return Monitor(SingleAgentWrapper(base_env, opponent))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument(
        "--opponent",
        choices=sorted(OPPONENTS),
        default="max",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_ADVANCED_MODEL_PATH)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = build_training_env(args.opponent)

    if args.input:
        model = PPO.load(args.input, env=env)
    else:
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            n_steps=2048,
            batch_size=128,
            gamma=0.995,
            ent_coef=0.01,
        )

    model.learn(total_timesteps=args.timesteps)
    model.save(args.output)
    env.close()

    print(f"Saved advanced model to {args.output}")


if __name__ == "__main__":
    main()
