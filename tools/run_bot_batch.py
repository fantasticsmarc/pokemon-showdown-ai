import argparse
import asyncio
import contextlib
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from poke_env import AccountConfiguration

from agents.competitive_agent import CompetitiveBot, LOCAL_SERVER
from agents.smart_agent import SmartBot


async def run_battles(battles: int, smart_debug: bool) -> None:
    suffix = uuid.uuid4().hex[:8]
    competitive = CompetitiveBot(
        account_configuration=AccountConfiguration(
            username=f"CB{suffix}",
            password=None,
        ),
        server_configuration=LOCAL_SERVER,
    )
    smart = SmartBot(
        account_configuration=AccountConfiguration(
            username=f"SB{suffix}",
            password=None,
        ),
        server_configuration=LOCAL_SERVER,
    )
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
