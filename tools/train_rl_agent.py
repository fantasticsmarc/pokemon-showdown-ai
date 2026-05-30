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

from agents.rl_agent import DEFAULT_MODEL_PATH, LOCAL_SERVER, MiniPokemonRLEnv


OPPONENTS = {
    "random": RandomPlayer,
    "max": MaxBasePowerPlayer,
    "simple": SimpleHeuristicsPlayer,
}


def build_opponent(name: str, username: str):
    opponent_class = OPPONENTS[name]
    return opponent_class(
        account_configuration=AccountConfiguration(username=username, password=None),
        battle_format="gen9randombattle",
        server_configuration=LOCAL_SERVER,
    )


def build_training_env(opponent_name: str):
    suffix = uuid.uuid4().hex[:8]
    base_env = MiniPokemonRLEnv(
        account_configuration1=AccountConfiguration(
            username=f"MiniRL{suffix}",
            password=None,
        ),
        account_configuration2=AccountConfiguration(
            username=f"EnvOpp{suffix}",
            password=None,
        ),
    )
    opponent = build_opponent(opponent_name, f"BrainOpp{suffix}")
    return Monitor(SingleAgentWrapper(base_env, opponent))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=20_000)
    parser.add_argument(
        "--opponent",
        choices=sorted(OPPONENTS),
        default="random",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_PATH,
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = build_training_env(args.opponent)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=1024,
        batch_size=64,
        gamma=0.99,
    )
    model.learn(total_timesteps=args.timesteps)
    model.save(args.output)
    env.close()

    print(f"Saved model to {args.output}")


if __name__ == "__main__":
    main()
