# =========================================================
# GEN 9 RANDOM BATTLE (SINGLES)
# ABILITIES FOR DEBUFFS / NEGATIVE EFFECTS / CONTROL
# =========================================================

# ---------------------------------------------------------
# 1) LOWERS OPPONENT STATS ON SWITCH-IN
# ---------------------------------------------------------
ABILITY_DEBUFF_ON_SWITCH_IN = {
    "intimidate": {
        "on_switch_in_lower_target": {"atk": -1}
    },  # Lowers opponent Attack on entry
    "gooey": {"contact": {"spe": -1}},  # Lowers attacker Speed on contact
    "tanglinghair": {"contact": {"spe": -1}},  # Lowers attacker Speed on contact
}

# ---------------------------------------------------------
# 2) LOWERS STATS WHEN HIT
# ---------------------------------------------------------
ABILITY_DEBUFF_WHEN_HIT = {
    "cottondown": {"on_hit_lower_foe": {"spe": -1}},  # Lowers opponent Speed when hit
}

# ---------------------------------------------------------
# 3) LOWERS STATS ON CONTACT
# ---------------------------------------------------------
ABILITY_CONTACT_DEBUFFS = {
    "gooey": {"lower_attacker_spe_on_contact": 1},  # Lowers Speed on contact
    "tanglinghair": {"lower_attacker_spe_on_contact": 1},  # Same as Gooey
}

# ---------------------------------------------------------
# 4) FORCES NEGATIVE STAT CHANGES (SELF OR FOE)
# ---------------------------------------------------------
ABILITY_FORCED_STAT_DROPS = {
    "weakarmor": {
        "self": {"def": -1},
        "after_hit": True,
    },  # Lowers own Defense after hit
    "moody": {"random_stat_drop": True},  # Randomly lowers a stat each turn
    "defeatist": {
        "atk": 0.5,
        "spa": 0.5,
        "hp_at_or_below": 0.5,
    },  # Halves stats at low HP
    "slowstart": {"atk": 0.5, "spe": 0.5, "turns": 5},  # Temporary stat reduction
}

# ---------------------------------------------------------
# 5) ABILITIES THAT CAUSE STATUS CONDITIONS
# ---------------------------------------------------------
ABILITY_STATUS_INFLICT = {
    "static": {"contact_status": "par"},  # May paralyze attacker
    "flamebody": {"contact_status": "brn"},  # May burn attacker
    "poisonpoint": {"contact_status": "psn"},  # May poison attacker
    "effectspore": {
        "contact_random_status": ["slp", "psn", "par"]
    },  # Random status on contact
    "cutecharm": {"contact_infatuation": True},  # May infatuate attacker
}

# ---------------------------------------------------------
# 6) ABILITIES THAT DISABLE OR LIMIT MOVES
# ---------------------------------------------------------
ABILITY_MOVE_CONTROL_DEBUFFS = {
    "cursedbody": {"chance_disable_attacker_move": True},  # May disable move used on it
    "pressure": {"double_pp_usage": True},  # Doubles PP usage of foe moves
    "truant": {"skip_every_other_turn": True},  # Can only act every other turn
    "stall": {"moves_last_in_priority_bracket": True},  # Always moves last in bracket
    "gorillatactics": {"choice_lock": True},  # Locks into one move
}

# ---------------------------------------------------------
# 7) ABILITIES THAT DAMAGE THE OPPONENT INDIRECTLY
# ---------------------------------------------------------
ABILITY_INDIRECT_DAMAGE = {
    "roughskin": {"contact_damage": 1 / 8},  # Damages attacker on contact
    "ironbarbs": {"contact_damage": 1 / 8},  # Same as Rough Skin
    "aftermath": {"explode_on_contact_ko": True},  # Damages foe on KO by contact
    "innardsout": {
        "damage_equal_to_hp_on_ko": True
    },  # Deals damage equal to remaining HP
}

# ---------------------------------------------------------
# 8) ABILITIES THAT REPLACE OR ALTER OPPONENT ABILITIES
# ---------------------------------------------------------
ABILITY_ABILITY_CONTROL = {
    "mummy": {
        "replace_attackers_ability_on_contact": True
    },  # Replaces attacker ability
    "lingeringaroma": {"replace_attackers_ability_on_contact": True},  # Same as Mummy
    "wanderingspirit": {
        "swap_abilities_on_contact": True
    },  # Swaps abilities on contact
    "neutralizinggas": {
        "suppress_all_other_abilities": True
    },  # Disables other abilities
}

# ---------------------------------------------------------
# 9) ABILITIES THAT REFLECT OR REVERSE EFFECTS (DEBUFF CONTROL)
# ---------------------------------------------------------
ABILITY_DEBUFF_REFLECTION = {
    "mirrorarmor": {"reflect_stat_drops": True},  # Reflects stat drops back
    "magicbounce": {"reflect_status_moves": True},  # Reflects status moves
    "synchronize": {"reflect_status_back": True},  # Sends status back to attacker
}

# ---------------------------------------------------------
# 10) ABILITIES THAT IGNORE BOOSTS (EFFECTIVE DEBUFF)
# ---------------------------------------------------------
ABILITY_IGNORE_BOOSTS = {
    "unaware": {
        "ignore_target_stat_boosts_in_calc": True
    },  # Ignores opponent stat boosts
}

# ---------------------------------------------------------
# 11) ABILITIES THAT FORCE WORSE ACCURACY / HIT CONDITIONS
# ---------------------------------------------------------
ABILITY_ACCURACY_DEBUFFS = {
    "sandveil": {"evasion": 1.25, "sand_only": True},  # Makes opponent less accurate
    "snowcloak": {"evasion": 1.25, "snow_only": True},  # Same in snow
}

# ---------------------------------------------------------
# 12) ABILITIES THAT CAUSE SELF DAMAGE / DRAWBACKS
# ---------------------------------------------------------
ABILITY_SELF_DAMAGE = {
    "solarpower": {"lose_in_sun": 1 / 8},  # Loses HP each turn in sun
    "dryskin": {
        "lose_in_sun": 1 / 8,
        "fire_damage": 1.25,
    },  # Loses HP in sun, takes more fire damage
    "aftermath": {"self_destruct_effect": True},  # Causes damage after faint
}

# ---------------------------------------------------------
# 13) ABILITIES THAT PREVENT ACTION OR LIMIT OPTIONS
# ---------------------------------------------------------
ABILITY_ACTION_LIMITS = {
    "truant": {"skip_every_other_turn": True},  # Cannot act every other turn
    "stall": {"always_moves_last": True},  # Always moves last
}

# ---------------------------------------------------------
# 14) ABILITIES THAT REDUCE OPPONENT DAMAGE OUTPUT
# ---------------------------------------------------------
ABILITY_DAMAGE_DEBUFFS = {
    "intimidate": {"lower_attack": 1},  # Reduces opponent Attack
    "tabletsofruin": {"lower_foe_atk": 0.75},  # Reduces foe Attack globally
    "vesselofruin": {"lower_foe_spa": 0.75},  # Reduces foe SpA globally
    "beadsofruin": {"lower_foe_spd": 0.75},  # Reduces foe SpD (indirect damage boost)
    "swordofruin": {"lower_foe_def": 0.75},  # Reduces foe Defense
}

# ---------------------------------------------------------
# 15) ABILITIES THAT DISRUPT STATUS OR FIELD CONTROL
# ---------------------------------------------------------
ABILITY_CONTROL_DISRUPTION = {
    "goodasgold": {"immune_to_status_moves": True},  # Blocks status moves
    "overcoat": {"ignore_powder": True},  # Blocks powder moves
    "soundproof": {"immune_to_sound_moves": True},  # Blocks sound moves
    "bulletproof": {"immune_to_ball_bomb_moves": True},  # Blocks bomb/ball moves
}

# ---------------------------------------------------------
# 16) ABILITIES THAT NEGATE OR LIMIT STRATEGY OPTIONS
# ---------------------------------------------------------
ABILITY_STRATEGY_LIMITERS = {
    "neutralizinggas": {"disable_abilities": True},  # Turns off all abilities
    "moldbreaker": {"ignore_defensive_abilities": True},  # Ignores opponent abilities
    "turboblaze": {"ignore_defensive_abilities": True},  # Same effect
    "teravolt": {"ignore_defensive_abilities": True},  # Same effect
}
