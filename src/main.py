import asyncio
from tabulate import tabulate
from poke_env import cross_evaluate
from agents.random_agent import create_random_bot
from agents.maxdamage_agent import create_max_damage_bot
from agents.smart_agent import create_smart_bot


async def main():
    play_format = int(input("Are you playing in local server (1) or ladder (2): "))
    player1 = create_max_damage_bot(play_format)
    player2 = create_random_bot(play_format)
    player3 = create_smart_bot(play_format)
    players = [player1, player2, player3]

    if play_format == 1:
        battles = int(input("Choose a number of battles to be played: "))
        while True:
            results = int(
                input("Choose way to show results: \n 1. Table / 2. Print \n")
            )
            if results == 2:
                player_1 = None
                player_2 = None
                while not player_1 or not player_2:
                    player_1 = int(
                        input(
                            f"1. {player1.username} / 2. {player2.username} / 3. {player3.username} \n Choose first player: "
                        )
                    )
                    player_2 = int(
                        input(
                            f"1. {player1.username} / 2. {player2.username} / 3. {player3.username} \n Choose second player: "
                        )
                    )
                    if player_1 == 1:
                        player_1 = player1
                    elif player_1 == 2:
                        player_1 = player2
                    elif player_1 == 3:
                        player_1 = player3
                    if player_2 == 1:
                        player_2 = player1
                    elif player_2 == 2:
                        player_2 = player2
                    elif player_2 == 3:
                        player_2 = player3

                    if player_1 == player_2:
                        print("The two players cannot be the same. Please try again.")
                    else:
                        await player_1.battle_against(player_2, n_battles=battles)
                        print(f"Completed {battles} battles")
                        print(
                            f"Player {player_1.username} victories: {player_1.n_won_battles}"
                        )
                        print(
                            f"Player {player_2.username} victories: {player_2.n_won_battles}"
                        )
                        break
                break
            elif results == 1:
                cross_evaluation = await cross_evaluate(players, n_challenges=battles)
                table = [["-"] + [p.username for p in players]]
                for p_1, row in cross_evaluation.items():
                    table.append([p_1] + [cross_evaluation[p_1][p_2] for p_2 in row])
                print(f"Completed {battles} battles")
                print(tabulate(table))
                break
            else:
                print("Choose a correct answer")

    elif play_format == 2:
        battles = int(input("Choose a number of battles to be played: "))
        while True:
            player = int(
                input(
                    f"Choose what agent is going to play: \n 1. {player1.username} / 2. {player2.username} / 3. {player3.username} \n"
                )
            )
            if player == 1:
                print(f"{player1.username} is playing...")
                await player1.ladder(battles)
                for battle in player1.battles.values():
                    print(battle.rating, battle.opponent_rating)
                break
            elif player == 2:
                print(f"{player2.username} is playing...")
                await player2.ladder(battles)
                for battle in player2.battles.values():
                    print(battle.rating, battle.opponent_rating)
                break
            elif player == 3:
                print(f"{player3.username} is playing...")
                await player3.ladder(battles)
                for battle in player3.battles.values():
                    print(battle.rating, battle.opponent_rating)
                break
            else:
                print("Choose a correct answer")
    else:
        print("Choose a correct answer")


if __name__ == "__main__":
    asyncio.run(main())
