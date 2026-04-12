from poke_env.battle.move_category import MoveCategory
from math import floor


def safe_stat(stat_dict, stat_name, default=0):
    """Safely get a stat value, returning default if None or missing."""
    value = stat_dict.get(stat_name)
    return value if value is not None else default


def estimate_opponent_stat(
    pokemon, stat_name, assume_max_ivs_evs=False, beneficial_nature=False
):
    # Estimate an opponent's stat when we don't have full information (IVs/EVs/nature unknown).

    base_stat = pokemon.base_stats[stat_name]
    level = pokemon.level

    if assume_max_ivs_evs:
        iv = 31  # Maximum IVs
        ev = 252  # Maximum EVs
    else:
        iv = 15.5  # Average IVs
        ev = 126  # Average EVs (reasonable assumption)

    nature_modifier = 1.1 if beneficial_nature else 1.0

    if stat_name == "hp":
        estimated = (((2 * base_stat + iv + floor(ev / 4)) * level) / 100) + level + 10
    else:
        estimated = (((2 * base_stat + iv + floor(ev / 4)) * level) / 100) + 5
        estimated *= nature_modifier

    return floor(estimated)


def calculate_physical_ratio(attacker, defender, is_bot_turn):
    # Calculate the physical attack/defense ratio. Estimate stats for opponent's Pokémon if we don't have full information.

    if is_bot_turn:
        attack_stat = safe_stat(attacker.stats, "atk")
        defense_stat = safe_stat(defender.stats, "def")
    else:
        attack_stat = safe_stat(attacker.stats, "atk")
        defense_stat = safe_stat(defender.stats, "def")

    # If we're estimating opponent's defense and don't have actual stats
    if not is_bot_turn and defense_stat == 0:
        defense_stat = estimate_opponent_stat(defender, "def", assume_max_ivs_evs=True)
    # If we're estimating our own stats (shouldn't happen in practice, but safe)
    elif is_bot_turn and attack_stat == 0:
        attack_stat = estimate_opponent_stat(attacker, "atk", assume_max_ivs_evs=False)

    # Avoid division by zero
    if defense_stat == 0:
        defense_stat = 1

    return attack_stat / defense_stat


def calculate_special_ratio(attacker, defender, is_bot_turn):
    # Calculate the special attack/defense ratio. Estimate stats for opponent's Pokémon if we don't have full information.

    if is_bot_turn:
        spattack_stat = safe_stat(attacker.stats, "spa")
        spdefense_stat = safe_stat(defender.stats, "spd")
    else:
        spattack_stat = safe_stat(attacker.stats, "spa")
        spdefense_stat = safe_stat(defender.stats, "spd")

    # If we're estimating opponent's special defense and don't have actual stats
    if not is_bot_turn and spdefense_stat == 0:
        spdefense_stat = estimate_opponent_stat(
            defender, "spd", assume_max_ivs_evs=True
        )
    # If we're estimating our own stats
    elif is_bot_turn and spattack_stat == 0:
        spattack_stat = estimate_opponent_stat(
            attacker, "spa", assume_max_ivs_evs=False
        )

    # Avoid division by zero
    if spdefense_stat == 0:
        spdefense_stat = 1

    return spattack_stat / spdefense_stat


def opponent_can_outspeed(my_pokemon, opponent_pokemon):
    # Determine if opponent can outspeed your Pokémon. Estimate opponent's speed if we don't have full information.

    # Our speed: we know this exactly from our team configuration
    my_speed = safe_stat(my_pokemon.stats, "spe")

    # Fallback estimation if our stats aren't populated yet (early battle)
    if my_speed is None:
        my_speed = estimate_opponent_stat(
            my_pokemon, "spe", assume_max_ivs_evs=False, beneficial_nature=False
        )

    # We must estimate opponent's speed. To be pessimistic about whether they can outspeed us, assume favorable conditions for them.
    opponent_speed = estimate_opponent_stat(
        opponent_pokemon,
        "spe",
        assume_max_ivs_evs=True,  # Assume max IVs (31) and EVs (252) in speed
        beneficial_nature=True,  # Assume beneficial nature (+10% speed)
    )

    # Safety checks
    if my_speed is None or my_speed == 0:
        print(
            "Warning: My Pokémon's speed is unknown or zero, defaulting to 1 to avoid division issues."
        )
        my_speed = 1

    return opponent_speed > my_speed


def calculate_total_HP(pokemon, is_dynamaxed):
    # Calculate total HP of a Pokémon. For my Pokémon uses actual stats and for opponent's Pokémon estimates if needed
    hp = safe_stat(pokemon.stats, "hp")

    # If we don't have actual HP (opponent or early battle), estimate it
    if hp == 0:
        hp = estimate_opponent_stat(
            pokemon, "hp", assume_max_ivs_evs=False, beneficial_nature=False
        )

    if is_dynamaxed:
        hp *= 2

    return hp


def get_defensive_type_multiplier(my_pokemon, opponent_pokemon):
    # Get the defensive type multiplier (how much damage my Pokémon will take from opponent_pokemon's attacks). Returns the higher multiplier (worse case scenario) for pessimistic calculation.

    if opponent_pokemon.type_2 is None:
        return my_pokemon.damage_multiplier(opponent_pokemon.type_1)

    multiplier1 = my_pokemon.damage_multiplier(opponent_pokemon.type_1)
    multiplier2 = my_pokemon.damage_multiplier(opponent_pokemon.type_2)

    return max(multiplier1, multiplier2)


def calculate_damage(move, attacker, defender, pessimistic, is_bot_turn):
    # Calculate damage of a move using the official Pokemon damage formula and handles estimation for unknown opponent stats.

    # Status moves don't do damage
    if move.category == MoveCategory.STATUS:
        return 0

    # Start with base power
    damage = move.base_power

    # Apply attack/defense ratio based on move category
    if move.category == MoveCategory.PHYSICAL:
        ratio = calculate_physical_ratio(attacker, defender, is_bot_turn)
    elif move.category == MoveCategory.SPECIAL:
        ratio = calculate_special_ratio(attacker, defender, is_bot_turn)
    else:
        ratio = 1  # Shouldn't happen for non-status moves

    damage *= ratio

    # Apply level multiplier
    level_multiplier = (2 * attacker.level) / 5 + 2
    damage *= level_multiplier

    # Apply division by 50 and add 2
    damage = (damage / 50) + 2

    # Apply random factor
    if pessimistic:
        damage *= 0.85  # Minimum damage roll
    else:
        damage *= 0.925  # Average damage roll

    # Apply STAB
    if move.type == attacker.type_1 or move.type == attacker.type_2:
        damage *= 1.5

    # Apply type effectiveness
    type_multiplier = defender.damage_multiplier(move)
    damage *= type_multiplier

    # Ensure minimum damage of 1
    return max(1, int(damage))
