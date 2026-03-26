import asyncio
from agents.random_agent import RandomBot
from poke_env.ps_client import ShowdownServerConfiguration


async def main():
    player1 = RandomBot(
        battle_format="gen9randombattle",
        server_configuration=ShowdownServerConfiguration,
    )
    player2 = RandomBot(
        battle_format="gen9randombattle",
        server_configuration=ShowdownServerConfiguration,
    )

    await player1.battle_against(player2, n_battles=5)

    print("Completed 5 battles")
    print(f"Player 1 victories: {player1.n_won_battles}")
    print(f"Player 2 victories: {player2.n_won_battles}")


if __name__ == "__main__":
    asyncio.run(main())