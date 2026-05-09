import argparse
import asyncio
import contextlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agents.competitive_agent import create_competitive_bot
from agents.smart_agent import create_smart_bot


async def run_battles(battles: int, smart_debug: bool) -> None:
    competitive = create_competitive_bot(1)
    smart = create_smart_bot(1)
    competitive.debug_enabled = True
    smart.debug_enabled = smart_debug

    await smart.battle_against(competitive, n_battles=battles)

    print(f"Completed {battles} battles")
    print(f"Player SmartBot victories: {smart.n_won_battles}")
    print(f"Player CompetitiveBot victories: {competitive.n_won_battles}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--battles", type=int, default=20)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--smart-debug", action="store_true")
    args = parser.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("w", encoding="utf-8") as log_file:
        with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            asyncio.run(run_battles(args.battles, args.smart_debug))

    print(args.log)


if __name__ == "__main__":
    main()
