import asyncio

import integrations.poke_env.login_patch
from poke_env import cross_evaluate
from tabulate import tabulate

from agents.maxdamage_agent import create_max_damage_bot
from agents.random_agent import create_random_bot
from agents.smart_agent import create_smart_bot
from agents.simpleheurstics_agent import create_simple_heuristics_bot

LOCAL_PLAY_FORMAT = 1
LADDER_PLAY_FORMAT = 2
TABLE_RESULTS = 1
PRINT_RESULTS = 2

PLAYER_FACTORIES = {
    1: ("MaxDamageBot", create_max_damage_bot),
    2: ("RandomBot", create_random_bot),
    3: ("SmartBot", create_smart_bot),
    4: ("SimpleHeuristicsBot", create_simple_heuristics_bot),
}


# Read a numeric option from the console and convert it to int.
def prompt_int(message: str) -> int:
    return int(input(message))


# Build the three local players for simulations on the local server.
def create_all_players(play_format: int) -> list:
    return [factory(play_format) for _, factory in PLAYER_FACTORIES.values()]


# Create the text shown when the user has to choose between loaded players.
def get_player_selection_prompt(players: list, prompt_text: str) -> str:
    player_options = " / ".join(
        f"{index}. {player.username}" for index, player in enumerate(players, start=1)
    )
    return f"{player_options} \n {prompt_text}"


# Return the chosen local player object or None if the index is invalid.
def select_local_player(players: list, prompt_text: str):
    selected_index = prompt_int(get_player_selection_prompt(players, prompt_text))
    if 1 <= selected_index <= len(players):
        return players[selected_index - 1]
    return None


# Convert cross-evaluation results into a table ready for tabulate.
def build_cross_evaluation_table(players: list, cross_evaluation: dict) -> list:
    table = [["-"] + [player.username for player in players]]
    for player_name, row in cross_evaluation.items():
        table.append(
            [player_name]
            + [cross_evaluation[player_name][opponent] for opponent in row]
        )
    return table


# Run local battles between two chosen players and print the win counts.
async def run_local_print_mode(players: list, battles: int):
    while True:
        first_player = select_local_player(players, "Choose first player: ")
        second_player = select_local_player(players, "Choose second player: ")

        if not first_player or not second_player:
            continue

        if first_player == second_player:
            print("The two players cannot be the same. Please try again.")
            continue

        await first_player.battle_against(second_player, n_battles=battles)
        print(f"Completed {battles} battles")
        print(f"Player {first_player.username} victories: {first_player.n_won_battles}")
        print(
            f"Player {second_player.username} victories: {second_player.n_won_battles}"
        )
        return


# Run a round-robin local evaluation and print the resulting table.
async def run_local_table_mode(players: list, battles: int):
    cross_evaluation = await cross_evaluate(players, n_challenges=battles)
    table = build_cross_evaluation_table(players, cross_evaluation)
    print(f"Completed {battles} battles")
    print(tabulate(table))


# Handle the full local-server flow, including result mode selection.
async def run_local_mode():
    players = create_all_players(LOCAL_PLAY_FORMAT)
    battles = prompt_int("Choose a number of battles to be played: ")

    while True:
        results_mode = prompt_int(
            "Choose way to show results: \n 1. Table / 2. Print \n"
        )

        if results_mode == TABLE_RESULTS:
            await run_local_table_mode(players, battles)
            return

        if results_mode == PRINT_RESULTS:
            await run_local_print_mode(players, battles)
            return

        print("Choose a correct answer")


# Create the menu text used to choose which bot will play on ladder.
def get_ladder_selection_prompt() -> str:
    player_options = " / ".join(
        f"{index}. {player_name}"
        for index, (player_name, _) in PLAYER_FACTORIES.items()
    )
    return f"Choose what agent is going to play: \n {player_options} \n"


# Handle the ladder flow by creating only the selected bot and sending it to ladder.
async def run_ladder_mode():
    battles = prompt_int("Choose a number of battles to be played: ")

    while True:
        selected_player = prompt_int(get_ladder_selection_prompt())
        ladder_player = PLAYER_FACTORIES.get(selected_player)

        if not ladder_player:
            print("Choose a correct answer")
            continue

        player_name, player_factory = ladder_player
        player_instance = player_factory(LADDER_PLAY_FORMAT)
        print(f"{player_name} is playing as {player_instance.username}...")
        await player_instance.ladder(battles)

        for battle in player_instance.battles.values():
            print(battle.rating, battle.opponent_rating)
        return


# Entry point that routes the program to local mode or ladder mode.
async def main():
    play_format = prompt_int("Are you playing in local server (1) or ladder (2): ")

    if play_format == LOCAL_PLAY_FORMAT:
        await run_local_mode()
        return

    if play_format == LADDER_PLAY_FORMAT:
        await run_ladder_mode()
        return

    print("Choose a correct answer")


if __name__ == "__main__":
    asyncio.run(main())
