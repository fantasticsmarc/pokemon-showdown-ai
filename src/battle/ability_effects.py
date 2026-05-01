import battle.buffs as buffs
import battle.debuffs as debuffs
import battle.habilities as habilities

# Central registry for every strategic ability dictionary we maintain.
# poke_env tells us which ability a Pokemon has; these dictionaries explain how much that ability should matter to SmartBot's heuristic.
ABILITY_EFFECT_GROUPS = {
    "boosts_when_hit": (
        buffs.ABILITY_BOOSTS_WHEN_HIT,
        habilities.ABILITY_BOOSTS_WHEN_HIT,
    ),
    "boosts_on_ko": (buffs.ABILITY_BOOSTS_ON_KO,),
    "boosts_on_faint": (buffs.ABILITY_BOOSTS_ON_FAINT,),
    "end_turn_boosts": (buffs.ABILITY_END_TURN_BOOSTS,),
    "ally_faint_buffs": (buffs.ABILITY_ALLY_FAINT_BUFFS,),
    "weather_buffs": (buffs.ABILITY_WEATHER_BUFFS,),
    "terrain_buffs": (buffs.ABILITY_TERRAIN_BUFFS,),
    "special_field_buffs": (buffs.ABILITY_SPECIAL_FIELD_BUFFS,),
    "low_hp_buffs": (
        buffs.ABILITY_LOW_HP_BUFFS,
        habilities.ABILITY_ATTACK_TYPE_MULTIPLIERS,
    ),
    "status_buffs": (buffs.ABILITY_STATUS_BUFFS,),
    "item_triggered_buffs": (buffs.ABILITY_ITEM_TRIGGERED_BUFFS,),
    "offensive_buffs": (
        buffs.ABILITY_OFFENSIVE_BUFFS,
        habilities.ABILITY_ATTACK_MOVE_MULTIPLIERS,
    ),
    "move_type_change_buffs": (
        buffs.ABILITY_MOVE_TYPE_CHANGE_BUFFS,
        habilities.ABILITY_MOVE_TYPE_CHANGE,
    ),
    "crit_buffs": (
        buffs.ABILITY_CRIT_BUFFS,
        habilities.ABILITY_CRIT_INTERACTIONS,
    ),
    "accuracy_buffs": (buffs.ABILITY_ACCURACY_BUFFS,),
    "stat_change_buffs": (
        buffs.ABILITY_STAT_CHANGE_BUFFS,
        habilities.ABILITY_STATUS_TEMPO,
    ),
    "speed_tempo_buffs": (buffs.ABILITY_SPEED_TEMPO_BUFFS,),
    "survival_buffs": (buffs.ABILITY_SURVIVAL_BUFFS,),
    "utility_buffs": (buffs.ABILITY_UTILITY_BUFFS,),
    "type_immunities": (habilities.ABILITY_NEGATES,),
    "type_healing": (habilities.ABILITY_HEALS_FROM_TYPE,),
    "redirection": (habilities.ABILITY_REDIRECTS,),
    "attack_type_multipliers": (habilities.ABILITY_ATTACK_TYPE_MULTIPLIERS,),
    "attack_move_multipliers": (habilities.ABILITY_ATTACK_MOVE_MULTIPLIERS,),
    "defense_multipliers": (habilities.ABILITY_DEFENSE_MULTIPLIERS,),
    "reduce_super_effective": (habilities.ABILITY_REDUCE_SUPER_EFFECTIVE,),
    "full_hp_reduction": (habilities.ABILITY_FULL_HP_REDUCTION,),
    "bypass_defensive_abilities": (habilities.ABILITY_BYPASSES_DEFENSIVE_ABILITIES,),
    "stat_modifiers": (habilities.ABILITY_STAT_MODIFIERS,),
    "contact_and_indirect": (
        habilities.ABILITY_CONTACT_AND_INDIRECT,
        debuffs.ABILITY_INDIRECT_DAMAGE,
    ),
    "indirect_rules": (habilities.ABILITY_INDIRECT_RULES,),
    "debuff_on_switch_in": (debuffs.ABILITY_DEBUFF_ON_SWITCH_IN,),
    "debuff_when_hit": (debuffs.ABILITY_DEBUFF_WHEN_HIT,),
    "contact_debuffs": (debuffs.ABILITY_CONTACT_DEBUFFS,),
    "forced_stat_drops": (debuffs.ABILITY_FORCED_STAT_DROPS,),
    "status_inflict": (debuffs.ABILITY_STATUS_INFLICT,),
    "move_control_debuffs": (debuffs.ABILITY_MOVE_CONTROL_DEBUFFS,),
    "ability_control": (debuffs.ABILITY_ABILITY_CONTROL,),
    "debuff_reflection": (debuffs.ABILITY_DEBUFF_REFLECTION,),
    "ignore_boosts": (debuffs.ABILITY_IGNORE_BOOSTS,),
    "accuracy_debuffs": (debuffs.ABILITY_ACCURACY_DEBUFFS,),
    "self_damage": (debuffs.ABILITY_SELF_DAMAGE,),
    "action_limits": (debuffs.ABILITY_ACTION_LIMITS,),
    "damage_debuffs": (debuffs.ABILITY_DAMAGE_DEBUFFS,),
    "control_disruption": (debuffs.ABILITY_CONTROL_DISRUPTION,),
    "strategy_limiters": (debuffs.ABILITY_STRATEGY_LIMITERS,),
}


# Read the active ability known by poke_env, falling back to the most likely
# ability candidate when the opponent has not revealed it yet.
def get_known_ability(pokemon):
    if pokemon.ability:
        return pokemon.ability
    if pokemon.possible_abilities:
        return pokemon.possible_abilities[0]
    return None


# Return the first strategic entry found for an ability in one effect group.
def get_effect_data(group_name, ability, default=None):
    for effect_table in ABILITY_EFFECT_GROUPS.get(group_name, ()):
        if ability in effect_table:
            return effect_table[ability]
    return default


# Check if an ability belongs to a strategic effect group.
def has_effect(group_name, ability):
    return get_effect_data(group_name, ability) is not None


# Check whether an ability grants immunity to a specific attacking type.
def blocks_type(ability, type_name):
    blocked_types = get_effect_data("type_immunities", ability, [])
    return type_name in blocked_types


# Check whether an ability heals from a specific attacking type.
def heals_from_type(ability, type_name):
    healing_types = get_effect_data("type_healing", ability, [])
    return type_name in healing_types


# Return a compact matchup bonus/penalty from broad ability classes.
def get_matchup_modifier(own_ability, opponent_ability):
    modifier = 0.0

    # Negative score means our position is better; positive means more danger.
    if has_effect("damage_debuffs", own_ability):
        modifier -= 6
    if has_effect("survival_buffs", own_ability):
        modifier -= 6
    if has_effect("survival_buffs", opponent_ability):
        modifier += 8
    if has_effect("damage_debuffs", opponent_ability):
        modifier += 6

    return modifier
