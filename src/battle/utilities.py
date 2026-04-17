from poke_env.battle.move_category import MoveCategory
from poke_env.battle.move import DynamaxMove
from poke_env.data.gen_data import GenData
from math import floor

import battle.buffs as buffs
import battle.debuffs as debuffs
import battle.habilities as habilities

TYPE_CHART = GenData.from_gen(9).type_chart


# Safely read a stat from a dict and fall back to a default value when missing.
def safe_stat(stat_dict, stat_name, default=0):
    """Safely get a stat value, returning default if None or missing."""
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


# Estimate move damage with a simplified damage formula and partial information.
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


# Estimate actual expected damage after accuracy and ability modifiers.
def estimate_damage_output(move, attacker, defender, battle, is_bot_turn):
    if move.category == MoveCategory.STATUS:
        return 0

    damage = calculate_damage(
        move,
        attacker,
        defender,
        pessimistic=False,
        is_bot_turn=is_bot_turn,
    )
    damage *= move.accuracy
    damage *= get_offensive_ability_multiplier(attacker, defender, move, battle)
    damage *= get_defensive_ability_multiplier(defender, move)
    return damage


# Return the known ability or, if still hidden, the most likely ability candidate.
def get_pokemon_ability(pokemon):
    if pokemon.ability:
        return pokemon.ability
    if pokemon.possible_abilities:
        return pokemon.possible_abilities[0]
    return None


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


# Convert remaining HP into a compact score for the heuristic.
def get_hp_score(pokemon):
    return pokemon.current_hp_fraction * 2.5


# Estimate the opponent's remaining HP in raw points from the known HP fraction.
def estimate_remaining_hp(pokemon, is_dynamaxed=False):
    # We reconstruct approximate remaining HP from total HP and the visible fraction
    # because Showdown often exposes percentages before exact HP values are fully known.
    total_hp = calculate_total_HP(pokemon, is_dynamaxed)
    return max(1, total_hp * pokemon.current_hp_fraction)


# Estimate our remaining HP in raw points from known HP data.
def estimate_current_hp(pokemon):
    # For our side we usually know HP better, but we keep the same estimation path
    # so all later heuristics compare HP using the same scale.
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

    tempo_buffs = buffs.ABILITY_SPEED_TEMPO_BUFFS.get(ability, {})
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
    return base_speed * get_stage_multiplier(boost_stage) * get_speed_ability_multiplier(
        pokemon, battle
    )


# Apply offensive ability modifiers that can increase the value of an attacking move.
def get_offensive_ability_multiplier(attacker, defender, move, battle):
    ability = get_pokemon_ability(attacker)
    if not ability:
        return 1.0

    multiplier = 1.0

    type_multiplier_data = habilities.ABILITY_ATTACK_TYPE_MULTIPLIERS.get(ability)
    if type_multiplier_data:
        move_type = move.type.name.lower()
        if move_type in type_multiplier_data:
            hp_threshold = type_multiplier_data.get("hp_below")
            if hp_threshold is None or attacker.current_hp_fraction <= hp_threshold:
                multiplier *= type_multiplier_data[move_type]

    move_multiplier_data = habilities.ABILITY_ATTACK_MOVE_MULTIPLIERS.get(ability)
    if move_multiplier_data:
        if ability == "adaptability" and (
            move.type == attacker.type_1 or move.type == attacker.type_2
        ):
            multiplier *= 4 / 3
        elif move_multiplier_data.get("base_power_at_most") is not None:
            if move.base_power <= move_multiplier_data["base_power_at_most"]:
                multiplier *= move_multiplier_data.get("multiplier", 1.0)
        elif ability == "analytic" and move_multiplier_data.get("when_moving_last"):
            if get_effective_speed(attacker, battle) < get_effective_speed(defender, battle):
                multiplier *= move_multiplier_data.get("multiplier", 1.0)

    stat_modifier_data = habilities.ABILITY_STAT_MODIFIERS.get(ability)
    if stat_modifier_data:
        if ability == "guts" and attacker.status is not None and move.category == MoveCategory.PHYSICAL:
            multiplier *= stat_modifier_data.get("atk", 1.0)
        elif ability == "flareboost" and attacker.status is not None and move.category == MoveCategory.SPECIAL:
            multiplier *= stat_modifier_data.get("spa", 1.0)
        elif ability == "toxicboost" and attacker.status is not None and move.category == MoveCategory.PHYSICAL:
            multiplier *= stat_modifier_data.get("atk", 1.0)
        elif ability == "solarpower" and is_weather_active(battle, "sunnyday") and move.category == MoveCategory.SPECIAL:
            multiplier *= stat_modifier_data.get("spa", 1.0)
        elif ability == "hustle" and move.category == MoveCategory.PHYSICAL:
            multiplier *= stat_modifier_data.get("atk", 1.0)
        elif ability == "supremeoverlord":
            multiplier *= 1.1
        elif ability == "gorillatactics" and move.category == MoveCategory.PHYSICAL:
            multiplier *= stat_modifier_data.get("atk", 1.0)

    return multiplier


# Apply defensive ability effects such as immunities or damage reduction.
def get_defensive_ability_multiplier(defender, move):
    ability = get_pokemon_ability(defender)
    if not ability:
        return 1.0

    move_type = move.type.name.lower()

    if ability in habilities.ABILITY_NEGATES:
        if move_type in habilities.ABILITY_NEGATES[ability]:
            return 0.0

    if ability in habilities.ABILITY_HEALS_FROM_TYPE:
        if move_type in habilities.ABILITY_HEALS_FROM_TYPE[ability]:
            return 0.0

    multiplier = 1.0

    defense_multiplier_data = habilities.ABILITY_DEFENSE_MULTIPLIERS.get(ability)
    if defense_multiplier_data:
        if move_type in defense_multiplier_data:
            multiplier *= defense_multiplier_data[move_type]
        if move.category == MoveCategory.PHYSICAL and "physical" in defense_multiplier_data:
            multiplier *= defense_multiplier_data["physical"]
        if move.category == MoveCategory.SPECIAL and "special" in defense_multiplier_data:
            multiplier *= defense_multiplier_data["special"]

    if defender.current_hp_fraction == 1.0:
        multiplier *= habilities.ABILITY_FULL_HP_REDUCTION.get(ability, 1.0)

    if defender.damage_multiplier(move) > 1:
        multiplier *= habilities.ABILITY_REDUCE_SUPER_EFFECTIVE.get(ability, 1.0)

    return multiplier


# Estimate the overall usefulness of a move, not just its raw damage.
def estimate_move_value(move, attacker, defender, battle, is_bot_turn):
    if move.current_pp == 0:
        return float("-inf")

    if move.category == MoveCategory.STATUS:
        # Status moves are scored by the utility they create this turn,
        # such as boosting, healing or inflicting a new status.
        value = 0.0
        if move.self_boost:
            value += sum(move.self_boost.values()) * 20
        if move.boosts:
            value += sum(-stage for stage in move.boosts.values()) * 18
        if move.status is not None and defender.status is None:
            value += 35
        if move.heal:
            missing_hp = 1 - attacker.current_hp_fraction
            value += move.heal * missing_hp * 120
        if move.priority > 0:
            value += move.priority * 10
        return value

    # Damaging moves start from expected damage and then get adjusted
    # by useful side effects like drain, boosts or priority.
    damage = estimate_damage_output(move, attacker, defender, battle, is_bot_turn)

    value = damage
    if move.drain:
        value += damage * move.drain * 0.35
    if move.heal:
        missing_hp = 1 - attacker.current_hp_fraction
        value += move.heal * missing_hp * 60
    if move.self_boost:
        value += sum(move.self_boost.values()) * 10
    if move.boosts:
        value += sum(-stage for stage in move.boosts.values()) * 8
    if move.status is not None and defender.status is None:
        value += 20
    if move.priority > 0:
        value += move.priority * 8
    if move.recoil:
        value -= damage * move.recoil * 0.3
    if move.secondary:
        value += 8

    return value


# Get the highest estimated move value a Pokemon can produce against a target.
def get_best_move_value(attacker, defender, battle, is_bot_turn):
    known_moves = list(attacker.moves.values())
    if not known_moves:
        return 0
    return max(
        estimate_move_value(move, attacker, defender, battle, is_bot_turn)
        for move in known_moves
    )


# Estimate how dangerous the opponent's known attacks are into a specific type.
def get_known_move_defensive_multiplier(target_type, opponent_pokemon):
    attacking_moves = [
        move for move in opponent_pokemon.moves.values() if move.category != MoveCategory.STATUS
    ]

    if not attacking_moves:
        return None

    # We only care about the scariest known move because switching decisions
    # should be robust against the worst immediate punish we have seen so far.
    return max(
        move.type.damage_multiplier(target_type, type_chart=TYPE_CHART)
        for move in attacking_moves
    )


# Estimate how much a Tera type would improve or worsen the defensive matchup.
def get_tera_defensive_bonus(attacker, defender):
    if attacker.tera_type is None or attacker.is_terastallized:
        return 0

    # Start with the generic fallback based on the opponent's own types.
    current_multiplier = get_defensive_type_multiplier(attacker, defender)
    tera_multiplier = 1.0

    # If we know any of the opponent's real attacking moves, prefer those over
    # the cruder "opponent type = likely attack type" approximation.
    known_move_multiplier = get_known_move_defensive_multiplier(attacker.tera_type, defender)
    if known_move_multiplier is not None:
        tera_multiplier = known_move_multiplier

    if known_move_multiplier is None and defender.type_1 is not None:
        tera_multiplier = max(
            tera_multiplier,
            defender.type_1.damage_multiplier(attacker.tera_type, type_chart=TYPE_CHART),
        )
    if known_move_multiplier is None and defender.type_2 is not None:
        tera_multiplier = max(
            tera_multiplier,
            defender.type_2.damage_multiplier(attacker.tera_type, type_chart=TYPE_CHART),
        )

    return (current_multiplier - tera_multiplier) * 22


# Check if Terastallization improves the current move through stronger or cleaner STAB.
def tera_improves_offense(attacker, move):
    if attacker.tera_type is None:
        return False

    tera_type_name = attacker.tera_type.name.lower()
    move_type_name = move.type.name.lower()
    current_types = {
        attacker.type_1.name.lower() if attacker.type_1 else None,
        attacker.type_2.name.lower() if attacker.type_2 else None,
    }

    if tera_type_name != move_type_name:
        return False

    # Tera is especially valuable when it turns a non-STAB move into STAB
    # or when it reinforces a same-type attack on a crucial turn.
    return move_type_name not in current_types or move.base_power >= 80


# Estimate the turn value of using Tera on the chosen move.
def estimate_tera_move_value(battle, move, move_value):
    attacker = battle.active_pokemon
    defender = battle.opponent_active_pokemon

    if attacker.tera_type is None or attacker.is_terastallized:
        return float("-inf")

    # We start from the normal move value and then add only the extra value
    # created by Tera, so we can compare fairly against the non-Tera option.
    tera_value = move_value
    if tera_improves_offense(attacker, move):
        tera_value += estimate_damage_output(move, attacker, defender, battle, True) * 0.35
    tera_value += get_tera_defensive_bonus(attacker, defender)
    return tera_value


# Use Mega Evolution aggressively because it is usually a pure upgrade with no timing downside.
def should_use_mega_evolution(move_value, current_matchup_score):
    return move_value >= 45 or current_matchup_score >= 8


# Estimate the turn value of Mega Evolution as a general stat upgrade.
def estimate_mega_move_value(move_value, current_matchup_score):
    if not should_use_mega_evolution(move_value, current_matchup_score):
        return float("-inf")
    # Mega evolution is treated as a stable all-around upgrade,
    # so we add a flat bonus plus a bit more when the current position is shaky.
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
    close_to_ko = defender_remaining_hp > 0 and estimated_damage >= defender_remaining_hp * 0.65
    return likely_ko or (current_matchup_score >= 18 and close_to_ko) or move_value >= 120


# Estimate the turn value of converting the move into its Z-Move version.
def estimate_z_move_value(battle, move, move_value, current_matchup_score):
    attacker = battle.active_pokemon
    defender = battle.opponent_active_pokemon

    if move not in attacker.available_z_moves:
        return float("-inf")

    if move.category == MoveCategory.STATUS:
        # Status Z-Moves often provide special boosts or effects.
        z_value = move_value
        if move.z_move_boost:
            z_value += sum(move.z_move_boost.values()) * 18
        if move.z_move_effect is not None:
            z_value += 22
        return z_value

    base_damage = estimate_damage_output(move, attacker, defender, battle, True)
    if move.base_power <= 0 or move.z_move_power <= 0:
        return float("-inf")

    # Approximate Z damage by scaling the normal move's expected damage
    # to the Z-Move base power. It is not perfect but is much closer than
    # using the regular move value directly.
    z_damage = base_damage * (move.z_move_power / move.base_power)
    z_value = move_value + (z_damage - base_damage)
    if z_damage >= estimate_remaining_hp(defender):
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
    losing_position = current_matchup_score >= 18
    return (
        (losing_position and attacker_low_hp)
        or (losing_position and move_value >= 85)
        or (likely_ko and attacker.current_hp_fraction <= 0.6)
    )


# Estimate the turn value of Dynamax by looking at Max Move effects and survival value.
def estimate_dynamax_move_value(battle, move, move_value, current_matchup_score):
    if move.category == MoveCategory.STATUS:
        return float("-inf")

    attacker = battle.active_pokemon
    max_move = DynamaxMove(move)
    # First score the Max Move as if it were the action we are taking this turn.
    dynamax_value = estimate_move_value(
        max_move,
        attacker,
        battle.opponent_active_pokemon,
        battle,
        True,
    )

    # Dynamax also gives extra HP immediately, so it becomes more attractive
    # the lower our current HP is.
    dynamax_value += (1 - attacker.current_hp_fraction) * 35

    # Max Moves can set weather/terrain or apply boosts/drops, so reward that
    # utility explicitly instead of relying only on raw damage.
    if max_move.self_boost:
        dynamax_value += sum(max_move.self_boost.values()) * 12
    if max_move.boosts:
        dynamax_value += sum(-stage for stage in max_move.boosts.values()) * 10
    if getattr(max_move, "weather", None) is not None:
        dynamax_value += 10
    if getattr(max_move, "terrain", None) is not None:
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
    likely_ko = estimated_damage >= defender_remaining_hp
    better_offense = tera_improves_offense(attacker, move)
    dangerous_matchup = current_matchup_score >= 22

    if better_offense and (likely_ko or move_value >= 85):
        return True
    if better_offense and dangerous_matchup:
        return True
    if get_tera_defensive_bonus(attacker, battle.opponent_active_pokemon) >= 12:
        return True
    return False


# Choose which special mechanic to spend this turn, if any.
def choose_special_mechanic(battle, move, move_value, current_matchup_score):
    attacker = battle.active_pokemon
    defender = battle.opponent_active_pokemon

    # Compute shared context once so all mechanic-specific heuristics
    # compare against the same expected turn.
    estimated_damage = estimate_damage_output(move, attacker, defender, battle, True)
    defender_remaining_hp = estimate_remaining_hp(defender)
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

    # Pick the mechanic with the highest estimated value, but only if it is
    # meaningfully better than preserving the resource for a later turn.
    best_mechanic, best_value = max(candidate_scores.items(), key=lambda item: item[1])
    if best_value <= move_value + 8:
        return None
    return best_mechanic


# Combine offense, defense, tempo and board state into one matchup score.
def evaluate_pokemon_matchup(my_pokemon, opponent_pokemon, battle):
    defensive_multiplier = get_defensive_type_multiplier(my_pokemon, opponent_pokemon)
    my_best_move_value = get_best_move_value(my_pokemon, opponent_pokemon, battle, True)
    opponent_best_move_value = get_best_move_value(
        opponent_pokemon, my_pokemon, battle, False
    )

    score = 0.0
    score += defensive_multiplier * 35
    score += opponent_best_move_value * 0.45
    score -= my_best_move_value * 0.55
    score -= get_boost_score(my_pokemon) * 12
    score += get_boost_score(opponent_pokemon) * 10
    score -= get_status_score(my_pokemon) * 10
    score += get_status_score(opponent_pokemon) * 8
    score -= get_hp_score(my_pokemon) * 6
    score += get_hp_score(opponent_pokemon) * 4

    if get_effective_speed(opponent_pokemon, battle) > get_effective_speed(my_pokemon, battle):
        score += 10
    else:
        score -= 6

    my_ability = get_pokemon_ability(my_pokemon)
    opponent_ability = get_pokemon_ability(opponent_pokemon)

    if my_ability in debuffs.ABILITY_DAMAGE_DEBUFFS:
        score -= 6
    if my_ability in buffs.ABILITY_SURVIVAL_BUFFS:
        score -= 6
    if opponent_ability in buffs.ABILITY_SURVIVAL_BUFFS:
        score += 8
    if opponent_ability in debuffs.ABILITY_DAMAGE_DEBUFFS:
        score += 6
    if battle.side_conditions:
        score += 4 * len(battle.side_conditions)
    if battle.opponent_side_conditions:
        score -= 3 * len(battle.opponent_side_conditions)

    return score
