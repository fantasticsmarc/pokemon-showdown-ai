import argparse
import asyncio
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from poke_env import AccountConfiguration
from tabulate import tabulate

from agents.maxdamage_agent import MaxDamageBot
from agents.random_agent import RandomBot
from agents.rl_agent import DEFAULT_MODEL_PATH, LOCAL_SERVER, MiniRLBot
from agents.simpleheurstics_agent import SHeuristicsBot


def _account(username: str) -> AccountConfiguration:
    return AccountConfiguration(username=username, password=None)


def _suffix() -> str:
    return uuid.uuid4().hex[:6]


def create_random_opponent(username: str) -> RandomBot:
    return RandomBot(
        account_configuration=_account(username),
        server_configuration=LOCAL_SERVER,
    )


def create_max_damage_opponent(username: str) -> MaxDamageBot:
    return MaxDamageBot(
        account_configuration=_account(username),
        server_configuration=LOCAL_SERVER,
    )


def create_simple_heuristics_opponent(username: str) -> SHeuristicsBot:
    return SHeuristicsBot(
        account_configuration=_account(username),
        server_configuration=LOCAL_SERVER,
    )


OPPONENTS = {
    "random": ("RandomBot", create_random_opponent),
    "max": ("MaxDamageBot", create_max_damage_opponent),
    "simple": ("SimpleHeuristicsBot", create_simple_heuristics_opponent),
}


async def evaluate_once(opponent_key: str, battles: int, model_path: Path) -> list:
    opponent_name, opponent_factory = OPPONENTS[opponent_key]
    suffix = _suffix()
    rl_player = MiniRLBot(
        account_configuration=_account(f"MiniRL{suffix}"),
        server_configuration=LOCAL_SERVER,
        model_path=model_path,
    )
    opponent = opponent_factory(f"Opp{suffix}")

    await rl_player.battle_against(opponent, n_battles=battles)

    rl_wins = rl_player.n_won_battles
    opponent_wins = opponent.n_won_battles
    ties = rl_player.n_finished_battles - rl_wins - opponent_wins
    win_rate = rl_wins / battles if battles else 0.0

    return [
        opponent_name,
        battles,
        rl_wins,
        opponent_wins,
        ties,
        f"{win_rate:.1%}",
    ]


async def evaluate(opponents: list[str], battles: int, model_path: Path) -> None:
    rows = []
    for opponent in opponents:
        print(f"Evaluating MiniRLBot vs {OPPONENTS[opponent][0]}...")
        rows.append(await evaluate_once(opponent, battles, model_path))

    print(
        tabulate(
            rows,
            headers=["Opponent", "Battles", "RL wins", "Opponent wins", "Ties", "Win rate"],
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--battles", type=int, default=50)
    parser.add_argument(
        "--opponents",
        nargs="+",
        choices=sorted(OPPONENTS),
        default=["random", "max", "simple"],
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args()

    if not args.model.exists():
        raise FileNotFoundError(
            f"Model not found at {args.model}. Train it with tools/train_rl_agent.py first."
        )

    asyncio.run(evaluate(args.opponents, args.battles, args.model))


if __name__ == "__main__":
    main()
