from poke_env.battle.move_category import MoveCategory
from poke_env.battle.move import DynamaxMove
from poke_env.battle.effect import Effect
from poke_env.battle.pokemon_type import PokemonType
from poke_env.battle.side_condition import SideCondition
from poke_env.data.gen_data import GenData
from math import floor

import battle.ability_effects as ability_effects
import battle.move_effects as move_effects

TYPE_CHART = GenData.from_gen(9).type_chart


# Safely read a stat from a dict and fall back to a default value when missing.
def safe_stat(stat_dict, stat_name, default=0):
    # Safely get a stat value, returning default if None or missing.
    value = stat_dict.get(stat_name)
    return value if value is not None else default


# Estimate an opponent stat when Showdown has not revealed the exact value yet.
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


# Estimate the physical attack/defense ratio used later in damage calculations.
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


# Estimate the special attack/defense ratio used later in damage calculations.
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


# Decide if the opponent is likely to move first based on estimated speed.
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


# Compute a Pokemon's total HP, including the Dynamax HP boost when relevant.
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


# Estimate the worst likely defensive type matchup against the opponent's STABs.
def get_defensive_type_multiplier(my_pokemon, opponent_pokemon):
    # Get the defensive type multiplier (how much damage my Pokémon will take from opponent_pokemon's attacks). Returns the higher multiplier (worse case scenario) for pessimistic calculation.

    if opponent_pokemon.type_2 is None:
        return my_pokemon.damage_multiplier(opponent_pokemon.type_1)

    multiplier1 = my_pokemon.damage_multiplier(opponent_pokemon.type_1)
    multiplier2 = my_pokemon.damage_multiplier(opponent_pokemon.type_2)

    return max(multiplier1, multiplier2)


# Read the Pokemon's current defensive types, including Tera and temporary type changes.
def get_current_types(pokemon):
    return (
        [pokemon.type_1] if pokemon.type_2 is None else [pokemon.type_1, pokemon.type_2]
    )


# Safely compute a move/type multiplier into a Pokemon's current typing.
def get_current_type_multiplier(target_pokemon, type_or_move):
    try:
        return target_pokemon.damage_multiplier(type_or_move)
    except Exception:
        return 1.0


# Read a move property defensively because forced moves like Recharge may have sparse data.
def safe_move_attr(move, attr_name, default=None):
    try:
        return getattr(move, attr_name)
    except (KeyError, AttributeError, TypeError):
        return default


# Return the category of a move, defaulting to status for sparse forced actions.
def get_move_category(move):
    return safe_move_attr(move, "category", MoveCategory.STATUS)


# Return the priority of a move without crashing on sparse forced actions.
def get_move_priority(move):
    return safe_move_attr(move, "priority", 0)


# Estimate move damage with a simplified damage formula and partial information.
def calculate_damage(move, attacker, defender, pessimistic, is_bot_turn):
    # Calculate damage of a move using the official Pokemon damage formula and handles estimation for unknown opponent stats.
    move_category = get_move_category(move)
    move_type = safe_move_attr(move, "type")

    # Status moves don't do damage
    if move_category == MoveCategory.STATUS or move_type is None:
        return 0

    # Start with base power
    damage = safe_move_attr(move, "base_power", 0)

    # Apply attack/defense ratio based on move category
    if move_category == MoveCategory.PHYSICAL:
        ratio = calculate_physical_ratio(attacker, defender, is_bot_turn)
    elif move_category == MoveCategory.SPECIAL:
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
    if move_type == attacker.type_1 or move_type == attacker.type_2:
        damage *= 1.5

    # Apply type effectiveness
    type_multiplier = get_current_type_multiplier(defender, move)
    damage *= type_multiplier

    # Ensure minimum damage of 1
    return max(1, int(damage))


# Estimate actual expected damage after accuracy and ability modifiers.
def estimate_damage_output(move, attacker, defender, battle, is_bot_turn):
    move_category = get_move_category(move)
    move_type = safe_move_attr(move, "type")

    if move_category == MoveCategory.STATUS or move_type is None:
        return 0

    # We intentionally use a simplified damage score instead of pretending to know the exact HP damage. The previous "realistic" formula was far too unstable with partial information and produced absurd values.
    damage_score = safe_move_attr(move, "base_power", 0) * safe_move_attr(move, "accuracy", 1.0) / 2

    if move_type == attacker.type_1 or move_type == attacker.type_2:
        damage_score *= 1.5
    if attacker.is_terastallized and attacker.tera_type == move_type:
        damage_score *= 1.3

    damage_score *= get_current_type_multiplier(defender, move)

    if move_category == MoveCategory.PHYSICAL:
        attack_stage = attacker.boosts.get("atk", 0)
        defense_stage = defender.boosts.get("def", 0)
    elif move_category == MoveCategory.SPECIAL:
        attack_stage = attacker.boosts.get("spa", 0)
        defense_stage = defender.boosts.get("spd", 0)
    else:
        attack_stage = 0
        defense_stage = 0

    damage_score *= get_stage_multiplier(attack_stage) / max(
        get_stage_multiplier(defense_stage),
        0.5,
    )
    damage_score *= get_offensive_ability_multiplier(attacker, defender, move, battle)
    damage_score *= get_defensive_ability_multiplier(defender, move)
    damage_score *= safe_move_attr(move, "expected_hits", 1)
    return max(damage_score, 0)


# Express expected damage on a stable 0-100 scale using the defender's total HP.
def estimate_damage_percent(move, attacker, defender, battle, is_bot_turn):
    damage = estimate_damage_output(move, attacker, defender, battle, is_bot_turn)
    return min(damage, 200)


# Return the known ability or, if still hidden, the most likely ability candidate.
def get_pokemon_ability(pokemon):
    return ability_effects.get_known_ability(pokemon)


# Convert stat stages into their numeric multiplier equivalent.
def get_stage_multiplier(stage):
    if stage >= 0:
        return (2 + stage) / 2
    return 2 / (2 - stage)


# Summarize current boosts into a single score used in the matchup heuristic.
def get_boost_score(pokemon):
    weights = {
        "atk": 1.0,
        "def": 0.9,
        "spa": 1.0,
        "spd": 0.9,
        "spe": 1.1,
        "accuracy": 0.4,
        "evasion": 0.4,
    }

    score = 0
    for stat, stage in pokemon.boosts.items():
        score += weights.get(stat, 0.2) * stage
    return score


# Convert a status condition into a positive or negative heuristic score.
def get_status_score(pokemon):
    if pokemon.status is None:
        return 0

    status_name = pokemon.status.name.lower()
    ability = get_pokemon_ability(pokemon)

    if status_name == "brn":
        if ability == "guts":
            return 1.0
        if ability == "flareboost":
            return 0.8
        return -1.2

    if status_name == "psn":
        if ability == "poisonheal":
            return 0.8
        if ability == "toxicboost":
            return 1.0
        return -1.0

    if status_name == "tox":
        if ability == "poisonheal":
            return 0.6
        if ability == "toxicboost":
            return 0.8
        return -1.3

    if status_name == "par":
        if ability == "quickfeet":
            return 0.4
        return -1.4

    if status_name == "slp":
        return -1.8

    if status_name == "frz":
        return -1.8

    return -0.5


# Estimate how useful it is to heal right now.
def get_healing_value(move, attacker, battle, setup_safety=1.0, immediate=False):
    # poke_env exposes direct recovery through move.heal; for dynamic recovery
    # moves we use a small fallback table in move_effects.py.
    heal_fraction = safe_move_attr(
        move,
        "heal",
        0,
    ) or move_effects.HEALING_MOVE_FALLBACKS.get(move.id, 0)
    if not heal_fraction:
        return 0.0

    missing_hp = 1 - attacker.current_hp_fraction
    if missing_hp <= 0.08:
        return -8.0

    value = heal_fraction * missing_hp * 135

    # Healing is most urgent when low, but risky healing should still respect
    # whether the current turn is safe enough to spend on recovery.
    if attacker.current_hp_fraction <= 0.28:
        value += 26
    elif attacker.current_hp_fraction <= 0.45:
        value += 14

    if move.id in move_effects.DELAYED_HEALING_MOVES:
        value *= 0.65
    if move.id in move_effects.SELF_SLEEP_HEALING_MOVES:
        value *= 0.75
        if attacker.status is not None:
            value += 14

    if immediate:
        value *= 0.55
    else:
        value *= setup_safety

    return value


# Estimate the value of inflicting a major status condition on the opponent.
def get_status_infliction_value(status, attacker, defender, battle, chance=1.0):
    if status is None or defender.status is not None:
        return 0.0

    # poke_env returns Status objects for move.status, but secondary effects in
    # the move database store raw strings like "brn" or "par".
    status_name = status if isinstance(status, str) else status.name
    status_name = status_name.lower()
    value = move_effects.STATUS_INFLICTION_VALUES.get(status_name, 28)

    # Burn is especially strong into physical attackers, paralysis into faster
    # targets, and poison/toxic into bulky targets that may stay around.
    if status_name == "brn" and safe_stat(defender.stats, "atk") >= safe_stat(
        defender.stats,
        "spa",
    ):
        value += 12
    if status_name == "par" and get_effective_speed(
        defender,
        battle,
    ) > get_effective_speed(attacker, battle):
        value += 14
    if status_name in {"psn", "tox"} and defender.current_hp_fraction >= 0.55:
        value += 10

    return value * chance


# Estimate how useful it is to lower the opponent's stats.
def get_target_debuff_value(boosts, attacker, defender, battle, chance=1.0):
    if not boosts:
        return 0.0

    defender_ability = get_pokemon_ability(defender)
    if defender_ability == "contrary":
        return -24.0 * chance
    if defender_ability in {"mirrorarmor", "magicbounce"}:
        return -18.0 * chance
    if defender_ability == "defiant" and any(stage < 0 for stage in boosts.values()):
        return -28.0 * chance
    if defender_ability == "competitive" and any(stage < 0 for stage in boosts.values()):
        return -28.0 * chance

    value = 0.0
    for stat, stage in boosts.items():
        current_stage = defender.boosts.get(stat, 0)
        stat_weight = move_effects.TARGET_DEBUFF_STAT_VALUES.get(stat, 12)

        if stage < 0:
            # Stat drops lose value once the target is already heavily debuffed.
            remaining_drop_room = max(0, current_stage + 6)
            useful_stage_change = min(abs(stage), remaining_drop_room)
            value += useful_stage_change * stat_weight
        elif stage > 0:
            value -= stage * stat_weight

    if get_effective_speed(defender, battle) > get_effective_speed(attacker, battle):
        value *= 1.08

    return value * chance


# Convert known secondary effects into extra move value.
def get_secondary_utility_value(move, attacker, defender, battle):
    secondary_value = 0.0

    for secondary in safe_move_attr(move, "secondary", []):
        chance = secondary.get("chance", 100) / 100

        # Debuffs on the target matter a lot because they affect the next turn immediately.
        if "boosts" in secondary and secondary["boosts"]:
            secondary_value += get_target_debuff_value(
                secondary["boosts"],
                attacker,
                defender,
                battle,
                chance,
            )

        # Status from an attacking move is strong tempo, especially if the target is not already statused.
        if secondary.get("status") is not None:
            secondary_value += get_status_infliction_value(
                secondary.get("status"),
                attacker,
                defender,
                battle,
                chance,
            )

        if secondary.get("volatileStatus") is not None:
            secondary_value += 12 * chance

        if secondary.get("self") and secondary["self"].get("boosts"):
            stage_value = sum(secondary["self"]["boosts"].values())
            secondary_value += stage_value * 14 * chance

    return secondary_value


# Score setup stats by how immediately useful they are for the user's current set.
def get_setup_stat_value(boosts, attacker):
    if not boosts:
        return 0.0

    known_moves = get_known_moves_safely(attacker)
    has_physical_move = any(
        get_move_category(move) == MoveCategory.PHYSICAL for move in known_moves
    )
    has_special_move = any(
        get_move_category(move) == MoveCategory.SPECIAL for move in known_moves
    )
    value = 0.0

    for stat, stage in boosts.items():
        if stage <= 0:
            continue
        if stat == "atk" and has_physical_move:
            value += stage * 24
        elif stat == "spa" and has_special_move:
            value += stage * 24
        elif stat == "spe":
            value += stage * 22
        elif stat in move_effects.SETUP_DEFENSE_STATS:
            value += stage * 16
        elif stat == "accuracy":
            value += stage * 9
        else:
            value += stage * 10

    return value


# Count how many opponent Pokemon are still alive so hazard value scales with future switch opportunities.
def count_remaining_opponent_pokemon(battle):
    return sum(1 for pokemon in battle.opponent_team.values() if not pokemon.fainted)


# Estimate the strategic value of setting a specific hazard right now.
def get_hazard_setup_value(move, battle):
    side_condition = safe_move_attr(move, "side_condition")
    if side_condition not in move_effects.HAZARD_SIDE_CONDITIONS:
        return 0.0

    existing_condition = battle.opponent_side_conditions.get(side_condition, 0)
    remaining_targets = count_remaining_opponent_pokemon(battle)
    value = max(remaining_targets - 1, 0) * 10
    opponent = battle.opponent_active_pokemon

    # If the current target is already close to being removed, immediate damage
    # is usually a better tempo play than spending the turn on long-term chip.
    if opponent.current_hp_fraction <= 0.35:
        value *= 0.45

    # Hazards are best early or mid game. With few targets left, the value drops
    # sharply unless the layer is especially impactful.
    if remaining_targets <= 2:
        value *= 0.55

    # First hazard layer is usually the most impactful, extra layers still help
    # but should not endlessly dominate the heuristic.
    if side_condition == SideCondition.STEALTH_ROCK:
        if side_condition in battle.opponent_side_conditions:
            return 0.0
        return value + 18

    if side_condition == SideCondition.SPIKES:
        if existing_condition >= 3:
            return 0.0
        return value + 12 - existing_condition * 2

    if side_condition == SideCondition.TOXIC_SPIKES:
        if existing_condition >= 2:
            return 0.0
        return value + 10 - existing_condition * 2

    if side_condition == SideCondition.STICKY_WEB:
        if side_condition in battle.opponent_side_conditions:
            return 0.0
        return value + 14

    return 0.0


# Detect if the target is currently behind a protect-like effect this turn.
def opponent_is_protected(pokemon):
    return any(effect in move_effects.PROTECT_LIKE_EFFECTS for effect in pokemon.effects)


# Detect if the target is currently behind a substitute.
def opponent_has_substitute(pokemon):
    return Effect.SUBSTITUTE in pokemon.effects


# Detect whether a move is one of the common protect-like actions.
def is_protect_like_move(move):
    if safe_move_attr(move, "is_protect_move", False):
        return True
    return move.id in {
        "protect",
        "detect",
        "kingsshield",
        "spikyshield",
        "banefulbunker",
        "obstruct",
        "silktrap",
    }


# Detect whether a move is Substitute.
def is_substitute_move(move):
    return move.id == "substitute" or safe_move_attr(move, "volatile_status") == Effect.SUBSTITUTE


# Convert remaining HP into a compact score for the heuristic.
def get_hp_score(pokemon):
    return pokemon.current_hp_fraction * 2.5


# Estimate the opponent's remaining HP in raw points from the known HP fraction.
def estimate_remaining_hp(pokemon, is_dynamaxed=False):
    # We reconstruct approximate remaining HP from total HP and the visible fraction because Showdown often exposes percentages before exact HP values are fully known.
    total_hp = calculate_total_HP(pokemon, is_dynamaxed)
    return max(1, total_hp * pokemon.current_hp_fraction)


# Estimate our remaining HP in raw points from known HP data.
def estimate_current_hp(pokemon):
    # For our side we usually know HP better, but we keep the same estimation path so all later heuristics compare HP using the same scale.
    total_hp = calculate_total_HP(pokemon, pokemon.is_dynamaxed)
    return max(1, total_hp * pokemon.current_hp_fraction)


# Check whether a specific weather is currently active in battle.
def is_weather_active(battle, weather_name):
    return any(weather.name.lower() == weather_name for weather in battle.weather)


# Check whether a specific terrain or field effect is currently active.
def is_field_active(battle, field_name):
    return any(field.name.lower() == field_name for field in battle.fields)


# Apply speed-related ability effects such as Swift Swim or Chlorophyll.
def get_speed_ability_multiplier(pokemon, battle):
    ability = get_pokemon_ability(pokemon)
    if not ability:
        return 1.0

    tempo_buffs = ability_effects.get_effect_data("speed_tempo_buffs", ability, {})
    if ability == "swiftswim" and is_weather_active(battle, "raindance"):
        return tempo_buffs.get("spe", 1.0)
    if ability == "chlorophyll" and is_weather_active(battle, "sunnyday"):
        return tempo_buffs.get("spe", 1.0)
    if ability == "sandrush" and is_weather_active(battle, "sandstorm"):
        return tempo_buffs.get("spe", 1.0)
    if ability == "slushrush" and is_weather_active(battle, "snow"):
        return tempo_buffs.get("spe", 1.0)
    if ability == "surgesurfer" and is_field_active(battle, "electricterrain"):
        return tempo_buffs.get("spe", 1.0)
    if ability == "quickfeet" and pokemon.status is not None:
        return tempo_buffs.get("spe", 1.0)
    if ability == "unburden" and pokemon.item is None:
        return 2.0
    if ability == "slowstart":
        return 0.5
    return 1.0


# Estimate the real turn-order speed after boosts and ability effects.
def get_effective_speed(pokemon, battle):
    base_speed = safe_stat(pokemon.stats, "spe")
    if not base_speed:
        base_speed = estimate_opponent_stat(
            pokemon, "spe", assume_max_ivs_evs=False, beneficial_nature=False
        )

    boost_stage = pokemon.boosts.get("spe", 0)
    return (
        base_speed
        * get_stage_multiplier(boost_stage)
        * get_speed_ability_multiplier(pokemon, battle)
    )


# Apply offensive ability modifiers that can increase the value of an attacking move.
def get_offensive_ability_multiplier(attacker, defender, move, battle):
    ability = get_pokemon_ability(attacker)
    if not ability:
        return 1.0

    multiplier = 1.0
    move_category = get_move_category(move)
    move_type = safe_move_attr(move, "type")
    move_base_power = safe_move_attr(move, "base_power", 0)

    type_multiplier_data = ability_effects.get_effect_data(
        "attack_type_multipliers",
        ability,
    )
    if type_multiplier_data and move_type is not None:
        move_type_name = move_type.name.lower()
        if move_type_name in type_multiplier_data:
            hp_threshold = type_multiplier_data.get("hp_below")
            if hp_threshold is None or attacker.current_hp_fraction <= hp_threshold:
                multiplier *= type_multiplier_data[move_type_name]

    move_multiplier_data = ability_effects.get_effect_data(
        "attack_move_multipliers",
        ability,
    )
    if move_multiplier_data:
        if ability == "adaptability" and (
            move_type == attacker.type_1 or move_type == attacker.type_2
        ):
            multiplier *= 4 / 3
        elif move_multiplier_data.get("base_power_at_most") is not None:
            if move_base_power <= move_multiplier_data["base_power_at_most"]:
                multiplier *= move_multiplier_data.get("multiplier", 1.0)
        elif ability == "analytic" and move_multiplier_data.get("when_moving_last"):
            if get_effective_speed(attacker, battle) < get_effective_speed(
                defender, battle
            ):
                multiplier *= move_multiplier_data.get("multiplier", 1.0)

    stat_modifier_data = ability_effects.get_effect_data("stat_modifiers", ability)
    if stat_modifier_data:
        if (
            ability == "guts"
            and attacker.status is not None
            and move_category == MoveCategory.PHYSICAL
        ):
            multiplier *= stat_modifier_data.get("atk", 1.0)
        elif (
            ability == "flareboost"
            and attacker.status is not None
            and move_category == MoveCategory.SPECIAL
        ):
            multiplier *= stat_modifier_data.get("spa", 1.0)
        elif (
            ability == "toxicboost"
            and attacker.status is not None
            and move_category == MoveCategory.PHYSICAL
        ):
            multiplier *= stat_modifier_data.get("atk", 1.0)
        elif (
            ability == "solarpower"
            and is_weather_active(battle, "sunnyday")
            and move_category == MoveCategory.SPECIAL
        ):
            multiplier *= stat_modifier_data.get("spa", 1.0)
        elif ability == "hustle" and move_category == MoveCategory.PHYSICAL:
            multiplier *= stat_modifier_data.get("atk", 1.0)
        elif ability == "supremeoverlord":
            multiplier *= 1.1
        elif ability == "gorillatactics" and move_category == MoveCategory.PHYSICAL:
            multiplier *= stat_modifier_data.get("atk", 1.0)

    return multiplier


# Apply defensive ability effects such as immunities or damage reduction.
def get_defensive_ability_multiplier(defender, move):
    ability = get_pokemon_ability(defender)
    if not ability:
        return 1.0

    move_category = get_move_category(move)
    move_type = safe_move_attr(move, "type")
    if move_type is None:
        return 1.0

    move_type_name = move_type.name.lower()

    if ability_effects.blocks_type(ability, move_type_name):
        return 0.0

    if ability_effects.heals_from_type(ability, move_type_name):
        return 0.0

    multiplier = 1.0

    defense_multiplier_data = ability_effects.get_effect_data(
        "defense_multipliers",
        ability,
    )
    if defense_multiplier_data:
        if move_type_name in defense_multiplier_data:
            multiplier *= defense_multiplier_data[move_type_name]
        if (
            move_category == MoveCategory.PHYSICAL
            and "physical" in defense_multiplier_data
        ):
            multiplier *= defense_multiplier_data["physical"]
        if (
            move_category == MoveCategory.SPECIAL
            and "special" in defense_multiplier_data
        ):
            multiplier *= defense_multiplier_data["special"]

    if defender.current_hp_fraction == 1.0:
        multiplier *= ability_effects.get_effect_data(
            "full_hp_reduction",
            ability,
            1.0,
        )

    if get_current_type_multiplier(defender, move) > 1:
        multiplier *= ability_effects.get_effect_data(
            "reduce_super_effective",
            ability,
            1.0,
        )

    return multiplier


# Estimate the overall usefulness of a move, not just its raw damage. Estimate move value
def daniela(
    move,
    attacker,
    defender,
    battle,
    is_bot_turn,
    include_setup_safety=True,
):
    current_pp = safe_move_attr(move, "current_pp", 1)
    move_category = get_move_category(move)

    if current_pp == 0:
        return float("-inf")

    if move_category == MoveCategory.STATUS:
        # Status moves are scored by the utility they create this turn, such as boosting, healing or inflicting a new status.
        # When this function is called inside broader matchup estimates we avoid recursively asking for setup safety again, otherwise status-move evaluation can loop through threat estimation forever.
        setup_safety = (
            get_setup_safety_score(attacker, defender, battle)
            if include_setup_safety
            else 1.0
        )
        value = 0.0
        self_boost = safe_move_attr(move, "self_boost")
        boosts = safe_move_attr(move, "boosts")
        status = safe_move_attr(move, "status")
        heal = safe_move_attr(move, "heal", 0)
        side_condition = safe_move_attr(move, "side_condition")

        if self_boost:
            # Self boosts are strongest in calm turns where we can expect to stay on the field long enough to cash them in.
            value += get_setup_stat_value(self_boost, attacker) * setup_safety
        if boosts:
            # Target debuffs matter immediately, so they stay valuable even when setup is slightly risky.
            value += get_target_debuff_value(boosts, attacker, defender, battle)
        if status is not None:
            value += get_status_infliction_value(status, attacker, defender, battle)
        if heal or move.id in move_effects.HEALING_MOVE_FALLBACKS:
            value += get_healing_value(move, attacker, battle, setup_safety)
        if side_condition:
            # Hazards scale with how many opposing Pokemon are still available to
            # be chipped by future switches.
            value += get_hazard_setup_value(move, battle)
        if safe_move_attr(move, "weather") is not None:
            value += 12
        if safe_move_attr(move, "terrain") is not None:
            value += 12
        if safe_move_attr(move, "volatile_status") is not None and not (
            is_substitute_move(move) or is_protect_like_move(move)
        ):
            value += 16
        if get_move_priority(move) > 0:
            value += get_move_priority(move) * 10
        if safe_move_attr(move, "self_switch"):
            value += 10
        if is_substitute_move(move):
            if (
                Effect.SUBSTITUTE not in attacker.effects
                and attacker.current_hp_fraction >= 0.55
                and setup_safety >= 0.8
            ):
                value += 42 * setup_safety
            else:
                value -= 20
        if is_protect_like_move(move):
            # Protect-like moves are mainly useful for stalling a threatening turn,
            # scouting, or squeezing recovery/status turns.
            if include_setup_safety:
                opponent_threat = get_opponent_threat_value(defender, attacker, battle)
                if opponent_threat >= estimate_current_hp(attacker) * 0.45:
                    value += 28
            if attacker.current_hp_fraction <= 0.35:
                value += 12
            if attacker.item == "leftovers":
                value += 8
            if defender.status is not None:
                value += 8
            if attacker.protect_counter > 0:
                value -= 18 * attacker.protect_counter
        if safe_move_attr(move, "force_switch", False):
            value += 20 if count_remaining_opponent_pokemon(battle) > 2 else 8

        # Calm setup turns deserve a small baseline bonus so the bot does not
        # always default to chip damage in good boosting positions.
        if self_boost and setup_safety >= 0.95:
            value += 14

        # If the rival is pressing us too hard, setup and utility moves lose value so the bot stops over-greeding in dangerous positions.
        if setup_safety < 0.6:
            value *= setup_safety
        return value

    # Damaging moves start from expected damage and then get adjusted by useful side effects like drain, boosts or priority.
    damage = estimate_damage_output(move, attacker, defender, battle, is_bot_turn)
    damage_percent = estimate_damage_percent(
        move,
        attacker,
        defender,
        battle,
        is_bot_turn,
    )

    # We score attacking moves by percent of the defender's HP instead of raw damage numbers so heuristics remain comparable across different stats.
    value = damage_percent

    # If the opponent is currently protected, attacking into it is usually bad unless the chosen move is specifically meant to break that protection.
    if opponent_is_protected(defender) and not safe_move_attr(move, "breaks_protect", False):
        value *= 0.15

    # Give a clear boost to super effective hits and penalize resisted ones so the bot behaves more like "find the strong effective attack" again.
    effectiveness = get_current_type_multiplier(defender, move)
    if effectiveness == 0:
        return float("-inf")
    if effectiveness > 1:
        value += 18 * effectiveness
    elif effectiveness < 1:
        value -= 14 * (1 / max(effectiveness, 0.25))

    # Damaging attacks into Substitute lose a lot of utility if they are mainly
    # trying to inflict status or drops rather than simply breaking the doll.
    if opponent_has_substitute(defender):
        value *= 0.75
        if safe_move_attr(move, "status") is not None:
            value *= 0.5

    drain = safe_move_attr(move, "drain", 0)
    heal = safe_move_attr(move, "heal", 0)
    self_boost = safe_move_attr(move, "self_boost")
    boosts = safe_move_attr(move, "boosts")
    status = safe_move_attr(move, "status")
    recoil = safe_move_attr(move, "recoil", 0)
    secondary = safe_move_attr(move, "secondary", [])

    if drain:
        value += damage_percent * drain * 0.35
    if heal:
        value += get_healing_value(move, attacker, battle, immediate=True)
    if self_boost:
        value += get_setup_stat_value(self_boost, attacker) * 0.45
    if boosts:
        value += get_target_debuff_value(boosts, attacker, defender, battle) * 0.65
    if status is not None:
        value += get_status_infliction_value(status, attacker, defender, battle) * 0.7
    if get_move_priority(move) > 0:
        value += get_move_priority(move) * 8
    if recoil:
        value -= damage_percent * recoil * 0.3
    if secondary:
        secondary_value = get_secondary_utility_value(move, attacker, defender, battle)
        value += 4 + secondary_value

    return value


# Safely collect a Pokemon's known moves without crashing on rare Mimic/Transform edge cases.
def get_known_moves_safely(pokemon):
    try:
        return list(pokemon.moves.values())
    except RecursionError:
        # poke_env can recurse forever while resolving copied move sets in some transformed or mimic-like states. Returning no known moves is saferthan crashing the whole battle loop.
        return []


# Get the highest estimated move value a Pokemon can produce against a target.
def get_best_move_value(attacker, defender, battle, is_bot_turn):
    known_moves = get_known_moves_safely(attacker)
    if not known_moves:
        return 0
    return max(
        daniela(
            move,
            attacker,
            defender,
            battle,
            is_bot_turn,
            include_setup_safety=False,
        )
        for move in known_moves
    )


# Estimate generic STAB pressure when the opponent has not revealed enough attacks yet.
def estimate_unrevealed_stab_pressure(attacker, defender, battle):
    attacking_types = [attacker.type_1]
    if attacker.type_2 is not None and attacker.type_2 != attacker.type_1:
        attacking_types.append(attacker.type_2)

    if not attacking_types:
        return 0

    # We approximate hidden pressure with a medium-strong STAB attack so the bot respects dangerous typings before every move is revealed.
    best_multiplier = max(
        get_current_type_multiplier(defender, attacking_type)
        for attacking_type in attacking_types
    )
    atk_pressure = safe_stat(attacker.stats, "atk") or estimate_opponent_stat(
        attacker, "atk", assume_max_ivs_evs=True, beneficial_nature=True
    )
    spa_pressure = safe_stat(attacker.stats, "spa") or estimate_opponent_stat(
        attacker, "spa", assume_max_ivs_evs=True, beneficial_nature=True
    )
    def_pressure = safe_stat(defender.stats, "def") or estimate_opponent_stat(
        defender, "def", assume_max_ivs_evs=False
    )
    spd_pressure = safe_stat(defender.stats, "spd") or estimate_opponent_stat(
        defender, "spd", assume_max_ivs_evs=False
    )

    physical_value = 80 * max(1, atk_pressure / max(1, def_pressure))
    special_value = 80 * max(1, spa_pressure / max(1, spd_pressure))
    pressure = max(physical_value, special_value) * best_multiplier * 0.7

    if get_effective_speed(attacker, battle) > get_effective_speed(defender, battle):
        pressure += 12
    return pressure


# Return how threatening the opponent looks right now, even with partial move information.
def get_opponent_threat_value(opponent_pokemon, my_pokemon, battle):
    known_attack_value = get_best_move_value(
        opponent_pokemon, my_pokemon, battle, False
    )
    hidden_stab_value = estimate_unrevealed_stab_pressure(
        opponent_pokemon,
        my_pokemon,
        battle,
    )

    # We keep the higher value because revealed damage and inferred STAB danger are both useful signals, and we want the bot to respect the worst case.
    return max(known_attack_value, hidden_stab_value)


# Detect whether the opponent has already revealed a super effective attack into us.
def opponent_has_known_super_effective_move(opponent_pokemon, my_pokemon):
    for move in get_known_moves_safely(opponent_pokemon):
        if get_move_category(move) == MoveCategory.STATUS:
            continue
        if get_current_type_multiplier(my_pokemon, move) > 1:
            return True
    return False


# Detect whether the opponent's typing alone suggests a risky STAB matchup.
def opponent_has_super_effective_stab(opponent_pokemon, my_pokemon):
    for attacking_type in [opponent_pokemon.type_1, opponent_pokemon.type_2]:
        if attacking_type is None:
            continue
        if get_current_type_multiplier(my_pokemon, attacking_type) > 1:
            return True
    return False


# Estimate how safe it is to spend the turn on setup instead of direct damage.
def get_setup_safety_score(attacker, defender, battle):
    opponent_threat = get_opponent_threat_value(defender, attacker, battle)
    attacker_hp = estimate_current_hp(attacker)
    defender_speed = get_effective_speed(defender, battle)
    attacker_speed = get_effective_speed(attacker, battle)
    safety = 1.0

    # Setup becomes more realistic when we move first and when the rival does not appear able to remove us or chunk us immediately.
    if attacker_speed > defender_speed:
        safety += 0.2
    else:
        safety -= 0.15

    if opponent_threat >= attacker_hp * 0.8:
        safety -= 0.45
    elif opponent_threat >= attacker_hp * 0.5:
        safety -= 0.25
    else:
        safety += 0.15

    if opponent_has_known_super_effective_move(defender, attacker):
        safety -= 0.3
    elif opponent_has_super_effective_stab(defender, attacker):
        safety -= 0.15

    if attacker.current_hp_fraction >= 0.7:
        safety += 0.1
    elif attacker.current_hp_fraction <= 0.35:
        safety -= 0.15

    return max(0.25, safety)


# Estimate how dangerous the opponent's known attacks are into a specific type.
def get_known_move_defensive_multiplier(target_type, opponent_pokemon):
    attacking_moves = [
        move
        for move in get_known_moves_safely(opponent_pokemon)
        if get_move_category(move) != MoveCategory.STATUS
        and safe_move_attr(move, "type") is not None
    ]

    if not attacking_moves:
        return None

    # We only care about the scariest known move because switching decisions should be robust against the worst immediate punish we have seen so far.
    return max(
        safe_move_attr(move, "type").damage_multiplier(target_type, type_chart=TYPE_CHART)
        for move in attacking_moves
    )


# Check whether the current best move is likely to finish the target immediately.
def is_best_move_likely_to_ko(attacker, defender, move, battle):
    if move is None or get_move_category(move) == MoveCategory.STATUS:
        return False

    expected_damage = estimate_damage_percent(move, attacker, defender, battle, True)
    defender_remaining_percent = defender.current_hp_fraction * 100
    effectiveness = get_current_type_multiplier(defender, move)

    # We keep this rule intentionally conservative because a false positive here is costly: the bot stays in and attacks when it should have switched.
    if defender.current_hp_fraction > 0.35:
        return False
    if effectiveness < 1 and defender.current_hp_fraction > 0.1:
        return False
    if safe_move_attr(move, "base_power", 0) < 45 and defender.current_hp_fraction > 0.1:
        return False
    if safe_move_attr(move, "accuracy", 1.0) < 0.9 and defender.current_hp_fraction > 0.12:
        return False
    if expected_damage < 18:
        return False

    return expected_damage >= defender_remaining_percent * 1.2


# Expose the KO-rule inputs so SmartBot can print exactly why the finisher rule did or did not trigger.
def get_ko_debug_data(attacker, defender, move, battle):
    if move is None or get_move_category(move) == MoveCategory.STATUS:
        return {
            "expected_damage": 0,
            "damage_percent": 0,
            "remaining_hp": defender.current_hp_fraction * 100,
            "effectiveness": 0,
        }

    return {
        "expected_damage": estimate_damage_percent(
            move, attacker, defender, battle, True
        ),
        "damage_percent": estimate_damage_percent(
            move, attacker, defender, battle, True
        ),
        "remaining_hp": defender.current_hp_fraction * 100,
        "effectiveness": get_current_type_multiplier(defender, move),
    }


# Estimate how much a Tera type would improve or worsen the defensive matchup.
def get_tera_defensive_bonus(attacker, defender):
    if attacker.tera_type is None or attacker.is_terastallized:
        return 0

    # Start with the generic fallback based on the opponent's own types.
    current_multiplier = get_defensive_type_multiplier(attacker, defender)
    tera_multiplier = 1.0

    # If we know any of the opponent's real attacking moves, prefer those over the cruder "opponent type = likely attack type" approximation.
    known_move_multiplier = get_known_move_defensive_multiplier(
        attacker.tera_type, defender
    )
    if known_move_multiplier is not None:
        tera_multiplier = known_move_multiplier

    if known_move_multiplier is None and defender.type_1 is not None:
        tera_multiplier = max(
            tera_multiplier,
            defender.type_1.damage_multiplier(
                attacker.tera_type, type_chart=TYPE_CHART
            ),
        )
    if known_move_multiplier is None and defender.type_2 is not None:
        tera_multiplier = max(
            tera_multiplier,
            defender.type_2.damage_multiplier(
                attacker.tera_type, type_chart=TYPE_CHART
            ),
        )

    return (current_multiplier - tera_multiplier) * 22


# Check if Terastallization improves the current move through stronger or cleaner STAB.
def tera_improves_offense(attacker, move):
    if attacker.tera_type is None:
        return False

    move_type = safe_move_attr(move, "type")
    if move_type is None:
        return False

    tera_type_name = attacker.tera_type.name.lower()
    move_type_name = move_type.name.lower()
    current_types = {
        attacker.type_1.name.lower() if attacker.type_1 else None,
        attacker.type_2.name.lower() if attacker.type_2 else None,
    }

    if tera_type_name != move_type_name:
        return False

    # Tera is especially valuable when it turns a non-STAB move into STAB or when it reinforces a same-type attack on a crucial turn.
    return move_type_name not in current_types or safe_move_attr(move, "base_power", 0) >= 80


# Estimate how much extra offensive value Tera adds to the selected move.
def get_tera_offensive_bonus(attacker, defender, move, battle):
    if attacker.tera_type is None or attacker.is_terastallized:
        return 0.0

    move_type = safe_move_attr(move, "type")
    if move_type is None or attacker.tera_type != move_type:
        return 0.0

    base_damage = estimate_damage_percent(move, attacker, defender, battle, True)
    current_stab = 1.5 if move_type in get_current_types(attacker) else 1.0
    tera_stab = 2.0 if move_type in attacker.original_types else 1.5
    stab_gain = max(tera_stab / current_stab - 1, 0)

    return base_damage * stab_gain + (8 if tera_improves_offense(attacker, move) else 0)


# Estimate the turn value of using Tera on the chosen move.
def estimate_tera_move_value(battle, move, move_value):
    attacker = battle.active_pokemon
    defender = battle.opponent_active_pokemon

    if attacker.tera_type is None or attacker.is_terastallized:
        return float("-inf")

    # We start from the normal move value and then add only the extra value created by Tera, so we can compare fairly against the non-Tera option.
    tera_value = move_value
    tera_value += get_tera_offensive_bonus(attacker, defender, move, battle)

    # Reward Tera a bit more when it helps convert a neutral turn into a clearly
    # stronger offensive one.
    if get_current_type_multiplier(defender, move) > 1:
        tera_value += 10
    tera_value += get_tera_defensive_bonus(attacker, defender)
    return tera_value


# Use Mega Evolution aggressively because it is usually a pure upgrade with no timing downside.
def should_use_mega_evolution(move_value, current_matchup_score):
    return move_value >= 30 or current_matchup_score >= 4


# Estimate the turn value of Mega Evolution as a general stat upgrade.
def estimate_mega_move_value(move_value, current_matchup_score):
    if not should_use_mega_evolution(move_value, current_matchup_score):
        return float("-inf")
    # Mega evolution is treated as a stable all-around upgrade, so we add a flat bonus plus a bit more when the current position is shaky.
    return move_value + 18 + max(0, current_matchup_score * 0.15)


# Use a Z-Move mainly to secure a KO or break through a bad matchup.
def should_use_z_move(
    battle,
    move,
    move_value,
    current_matchup_score,
    estimated_damage,
    defender_remaining_hp,
):
    likely_ko = estimated_damage >= defender_remaining_hp
    close_to_ko = (
        defender_remaining_hp > 0 and estimated_damage >= defender_remaining_hp * 0.65
    )
    return (
        likely_ko or (current_matchup_score >= 12 and close_to_ko) or move_value >= 95
    )


# Estimate the turn value of converting the move into its Z-Move version.
def estimate_z_move_value(battle, move, move_value, current_matchup_score):
    attacker = battle.active_pokemon
    defender = battle.opponent_active_pokemon

    if move not in attacker.available_z_moves:
        return float("-inf")

    if get_move_category(move) == MoveCategory.STATUS:
        # Status Z-Moves often provide special boosts or effects.
        z_value = move_value
        z_move_boost = safe_move_attr(move, "z_move_boost")
        if z_move_boost:
            z_value += sum(z_move_boost.values()) * 18
        if safe_move_attr(move, "z_move_effect") is not None:
            z_value += 22
        return z_value

    base_damage = estimate_damage_output(move, attacker, defender, battle, True)
    base_power = safe_move_attr(move, "base_power", 0)
    z_move_power = safe_move_attr(move, "z_move_power", 0)
    if base_power <= 0 or z_move_power <= 0:
        return float("-inf")

    # Approximate Z damage by scaling the normal move's expected damage to the Z-Move base power. It is not perfect but is much closer than using the regular move value directly.
    z_damage = base_damage * (z_move_power / base_power)
    z_value = move_value + (z_damage - base_damage)
    if z_damage >= defender.current_hp_fraction * 100:
        z_value += 18
    if current_matchup_score >= 18:
        z_value += 10
    return z_value


# Use Dynamax in more defensive or swingy turns where extra HP and power matter.
def should_use_dynamax(
    battle,
    move,
    move_value,
    current_matchup_score,
    estimated_damage,
    defender_remaining_hp,
):
    attacker = battle.active_pokemon
    likely_ko = estimated_damage >= defender_remaining_hp
    attacker_low_hp = attacker.current_hp_fraction <= 0.4
    losing_position = current_matchup_score >= 14
    return (
        (losing_position and attacker_low_hp)
        or (losing_position and move_value >= 70)
        or (likely_ko and attacker.current_hp_fraction <= 0.6)
    )


# Estimate the turn value of Dynamax by looking at Max Move effects and survival value.
def estimate_dynamax_move_value(battle, move, move_value, current_matchup_score):
    if get_move_category(move) == MoveCategory.STATUS:
        return float("-inf")

    attacker = battle.active_pokemon
    max_move = DynamaxMove(move)
    # First score the Max Move as if it were the action we are taking this turn.
    dynamax_value = daniela(
        max_move,
        attacker,
        battle.opponent_active_pokemon,
        battle,
        True,
    )

    # Dynamax also gives extra HP immediately, so it becomes more attractive the lower our current HP is.
    dynamax_value += (1 - attacker.current_hp_fraction) * 35

    # Max Moves can set weather/terrain or apply boosts/drops, so reward that utility explicitly instead of relying only on raw damage.
    max_move_self_boost = safe_move_attr(max_move, "self_boost")
    max_move_boosts = safe_move_attr(max_move, "boosts")
    if max_move_self_boost:
        dynamax_value += sum(max_move_self_boost.values()) * 12
    if max_move_boosts:
        dynamax_value += sum(-stage for stage in max_move_boosts.values()) * 10
    if safe_move_attr(max_move, "weather") is not None:
        dynamax_value += 10
    if safe_move_attr(max_move, "terrain") is not None:
        dynamax_value += 10

    if current_matchup_score >= 18:
        dynamax_value += 15
    return dynamax_value


# Use Tera when the Tera type helps this move a lot or when it can save a bad matchup.
def should_use_tera(
    battle,
    move,
    move_value,
    current_matchup_score,
    estimated_damage,
    defender_remaining_hp,
):
    attacker = battle.active_pokemon
    defender_remaining_percent = (
        battle.opponent_active_pokemon.current_hp_fraction * 100
    )
    likely_ko = estimated_damage >= defender_remaining_percent
    better_offense = tera_improves_offense(attacker, move)
    offensive_bonus = get_tera_offensive_bonus(
        attacker,
        battle.opponent_active_pokemon,
        move,
        battle,
    )
    dangerous_matchup = current_matchup_score >= 10

    if better_offense and (likely_ko or move_value >= 52 or offensive_bonus >= 14):
        return True
    if better_offense and dangerous_matchup:
        return True
    if get_tera_defensive_bonus(attacker, battle.opponent_active_pokemon) >= 6:
        return True
    return False


# Choose which special mechanic to spend this turn, if any.
def choose_special_mechanic(battle, move, move_value, current_matchup_score):
    attacker = battle.active_pokemon
    defender = battle.opponent_active_pokemon

    # Compute shared context once so all mechanic-specific heuristics compare against the same expected turn.
    estimated_damage = estimate_damage_percent(move, attacker, defender, battle, True)
    defender_remaining_hp = defender.current_hp_fraction * 100
    candidate_scores = {}

    if battle.can_mega_evolve:
        candidate_scores["mega_evolve"] = estimate_mega_move_value(
            move_value,
            current_matchup_score,
        )

    if battle.can_z_move and should_use_z_move(
        battle,
        move,
        move_value,
        current_matchup_score,
        estimated_damage,
        defender_remaining_hp,
    ):
        candidate_scores["z_move"] = estimate_z_move_value(
            battle,
            move,
            move_value,
            current_matchup_score,
        )

    if battle.can_tera and should_use_tera(
        battle,
        move,
        move_value,
        current_matchup_score,
        estimated_damage,
        defender_remaining_hp,
    ):
        candidate_scores["terastallize"] = estimate_tera_move_value(
            battle,
            move,
            move_value,
        )

    if battle.can_dynamax and should_use_dynamax(
        battle,
        move,
        move_value,
        current_matchup_score,
        estimated_damage,
        defender_remaining_hp,
    ):
        candidate_scores["dynamax"] = estimate_dynamax_move_value(
            battle,
            move,
            move_value,
            current_matchup_score,
        )

    if not candidate_scores:
        return None

    # Pick the mechanic with the highest estimated value, but only if it is meaningfully better than preserving the resource for a later turn.
    best_mechanic, best_value = max(candidate_scores.items(), key=lambda item: item[1])
    if best_value <= move_value + 3:
        return None
    return best_mechanic


# Detect turns where staying in is dangerous enough that switching should be favored.
def is_immediate_switch_threat(my_pokemon, opponent_pokemon, battle):
    opponent_threat = get_opponent_threat_value(opponent_pokemon, my_pokemon, battle)
    my_remaining_hp = estimate_current_hp(my_pokemon)
    faster_opponent = get_effective_speed(
        opponent_pokemon, battle
    ) > get_effective_speed(my_pokemon, battle)
    known_super_effective = opponent_has_known_super_effective_move(
        opponent_pokemon,
        my_pokemon,
    )
    likely_super_effective = opponent_has_super_effective_stab(
        opponent_pokemon, my_pokemon
    )

    # We only force a defensive reaction when the opponent looks able to punish right now, not just when the position is generically a bit awkward.
    if faster_opponent and opponent_threat >= my_remaining_hp * 0.7:
        return True
    if known_super_effective and opponent_threat >= my_remaining_hp * 0.55:
        return True
    if (
        likely_super_effective
        and faster_opponent
        and opponent_threat >= my_remaining_hp * 0.6
    ):
        return True
    return False


# Check whether hazards that only affect grounded Pokemon should apply on switch-in.
def is_grounded_for_entry_hazards(pokemon):
    if pokemon.type_1 is not None and pokemon.type_1.name.lower() == "flying":
        return False
    if pokemon.type_2 is not None and pokemon.type_2.name.lower() == "flying":
        return False
    if get_pokemon_ability(pokemon) == "levitate":
        return False
    return True


# Estimate the HP fraction a Pokemon would lose immediately when switching into hazards.
def estimate_hazard_damage_fraction_on_switch(pokemon, battle):
    damage_fraction = 0.0
    side_conditions = battle.side_conditions

    # Stealth Rock damage depends on Rock effectiveness against the incoming Pokemon.
    if SideCondition.STEALTH_ROCK in side_conditions:
        damage_fraction += 0.125 * pokemon.damage_multiplier(PokemonType.ROCK)

    # Spikes only affects grounded Pokemon and scales with the number of layers.
    spikes_layers = side_conditions.get(SideCondition.SPIKES, 0)
    if spikes_layers and is_grounded_for_entry_hazards(pokemon):
        if spikes_layers == 1:
            damage_fraction += 0.125
        elif spikes_layers == 2:
            damage_fraction += 1 / 6
        else:
            damage_fraction += 0.25

    return min(damage_fraction, 0.95)


# Convert switch-in hazards into the same score scale used by matchup evaluation.
def get_switch_hazard_penalty(pokemon, battle):
    try:
        damage_fraction = estimate_hazard_damage_fraction_on_switch(pokemon, battle)
    except Exception:
        # Hazards are only a secondary heuristic, so if something unexpected
        # happens here we prefer to ignore the penalty rather than crash the bot.
        damage_fraction = 0.0
    status_penalty = 0.0
    side_conditions = battle.side_conditions

    # Toxic Spikes are punished separately because poison on entry can matter even when the raw damage from hazards is not huge.
    if (
        SideCondition.TOXIC_SPIKES in side_conditions
        and pokemon.type_1.name.lower() != "poison"
        and (pokemon.type_2 is None or pokemon.type_2.name.lower() != "poison")
        and is_grounded_for_entry_hazards(pokemon)
        and pokemon.status is None
    ):
        toxic_layers = side_conditions[SideCondition.TOXIC_SPIKES]
        status_penalty += 12 if toxic_layers >= 2 else 8

    # Sticky Web mainly matters for grounded Pokemon that care about moving first.
    if SideCondition.STICKY_WEB in side_conditions and is_grounded_for_entry_hazards(
        pokemon
    ):
        status_penalty += 8

    # The damage fraction is scaled into a penalty that is large enough to stop reckless switches into hazards but not so large that it blocks all pivots.
    return damage_fraction * 100 + status_penalty


# Estimate how rewarding an immediate switch is after hazards and board state are considered.
def evaluate_switch_option(switch_pokemon, battle):
    matchup_score = evaluate_pokemon_matchup(
        switch_pokemon,
        battle.opponent_active_pokemon,
        battle,
    )
    hazard_penalty = get_switch_hazard_penalty(switch_pokemon, battle)

    # Lower is better, so hazards make the switch less attractive by increasing the final score of that option.
    return matchup_score + hazard_penalty


# Compare switching now versus using the current best move right away.
def should_switch_over_best_move(
    current_matchup_score,
    best_switch_score,
    best_move_value,
    immediate_threat,
):
    # Attacking this turn has real value, so switching should only happen if the future position clearly beats the immediate payoff of the best move.
    move_pressure_discount = min(best_move_value * 0.18, 18)
    effective_current_score = current_matchup_score - move_pressure_discount

    if immediate_threat:
        # When we are in danger, we allow smaller improvements because saving the active Pokemon is often worth more than one attack.
        effective_current_score += 8

    return best_switch_score < effective_current_score


# Combine offense, defense, tempo and board state into one matchup score.
def evaluate_pokemon_matchup(my_pokemon, opponent_pokemon, battle):
    defensive_multiplier = get_defensive_type_multiplier(my_pokemon, opponent_pokemon)
    my_best_move_value = get_best_move_value(my_pokemon, opponent_pokemon, battle, True)
    opponent_best_move_value = get_opponent_threat_value(
        opponent_pokemon,
        my_pokemon,
        battle,
    )

    score = 0.0
    score += defensive_multiplier * 35
    score += opponent_best_move_value * 0.6
    score -= my_best_move_value * 0.55
    score -= get_boost_score(my_pokemon) * 12
    score += get_boost_score(opponent_pokemon) * 10
    score -= get_status_score(my_pokemon) * 10
    score += get_status_score(opponent_pokemon) * 8
    score -= get_hp_score(my_pokemon) * 6
    score += get_hp_score(opponent_pokemon) * 4

    if get_effective_speed(opponent_pokemon, battle) > get_effective_speed(
        my_pokemon, battle
    ):
        score += 10
    else:
        score -= 6

    # A revealed super effective move is stronger evidence than a vague bad typing read, so we score those two cases separately.
    if opponent_has_known_super_effective_move(opponent_pokemon, my_pokemon):
        score += 16
    elif opponent_has_super_effective_stab(opponent_pokemon, my_pokemon):
        score += 8

    my_ability = get_pokemon_ability(my_pokemon)
    opponent_ability = get_pokemon_ability(opponent_pokemon)
    score += ability_effects.get_matchup_modifier(my_ability, opponent_ability)
    if battle.side_conditions:
        score += 4 * len(battle.side_conditions)
    if battle.opponent_side_conditions:
        score -= 3 * len(battle.opponent_side_conditions)

    return score
