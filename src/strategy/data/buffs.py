# =========================================================
# GEN 9 RANDOM BATTLE (SINGLES)
# ABILITIES FOR BUFFS / BOOSTS / TEMPO
# =========================================================

# ---------------------------------------------------------
# 1) BOOSTS WHEN HIT BY A SPECIFIC TYPE OR CONDITION
# ---------------------------------------------------------
ABILITY_BOOSTS_WHEN_HIT = {
    "motordrive": {
        "types": ["electric"],
        "boost": {"spe": 1},
    },  # Boosts Speed when hit by Electric
    "lightningrod": {
        "types": ["electric"],
        "boost": {"spa": 1},
    },  # Boosts SpA when hit by Electric
    "stormdrain": {
        "types": ["water"],
        "boost": {"spa": 1},
    },  # Boosts SpA when hit by Water
    "sapsipper": {
        "types": ["grass"],
        "boost": {"atk": 1},
    },  # Boosts Attack when hit by Grass
    "wellbakedbody": {
        "types": ["fire"],
        "boost": {"def": 2},
    },  # Sharply boosts Defense when hit by Fire
    "thermalexchange": {
        "types": ["fire"],
        "boost": {"atk": 1},
    },  # Boosts Attack when hit by Fire
    "steamengine": {
        "types": ["fire", "water"],
        "boost": {"spe": 6},
    },  # Maximizes Speed when hit by Fire or Water
    "weakarmor": {
        "trigger": "physical",
        "boost": {"spe": 2, "def": -1},
    },  # Boosts Speed but lowers Defense after physical hit
    "justified": {
        "types": ["dark"],
        "boost": {"atk": 1},
    },  # Boosts Attack when hit by Dark
    "rattled": {
        "types": ["bug", "dark", "ghost"],
        "boost": {"spe": 1},
    },  # Boosts Speed when hit by Bug/Dark/Ghost
    "berserk": {
        "trigger": "hp_below_half_after_hit",
        "boost": {"spa": 1},
    },  # Boosts SpA when HP drops below half
    "angerpoint": {
        "trigger": "crit",
        "boost": {"atk": 12},
    },  # Maximizes Attack after a critical hit
    "stamina": {"trigger": "hit", "boost": {"def": 1}},  # Boosts Defense when hit
    "cottondown": {
        "trigger": "hit",
        "effect": {"foe_spe": -1},
    },  # Lowers foe Speed when hit
}

# ---------------------------------------------------------
# 2) BOOSTS AFTER GETTING A KO
# ---------------------------------------------------------
ABILITY_BOOSTS_ON_KO = {
    "moxie": {"on_knockout": {"atk": 1}},  # Boosts Attack after KO
    "beastboost": {"on_knockout_best_stat": 1},  # Boosts highest stat after KO
    "chillingneigh": {"on_knockout": {"atk": 1}},  # Boosts Attack after KO
    "grimneigh": {"on_knockout": {"spa": 1}},  # Boosts SpA after KO
    "asoneglastrier": {"on_knockout": {"atk": 1}},  # Boosts Attack after KO
    "asonespectrier": {"on_knockout": {"spa": 1}},  # Boosts SpA after KO
}

# ---------------------------------------------------------
# 3) BOOSTS WHEN ANY POKEMON FAINTS
# ---------------------------------------------------------
ABILITY_BOOSTS_ON_FAINT = {
    "soulheart": {
        "on_other_faint": {"spa": 1}
    },  # Boosts SpA when another Pokemon faints
}

# ---------------------------------------------------------
# 4) END OF TURN BUFFS
# ---------------------------------------------------------
ABILITY_END_TURN_BOOSTS = {
    "speedboost": {"end_turn": {"spe": 1}},  # Boosts Speed every turn
    "moody": {
        "end_turn_random_boost": True
    },  # Randomly boosts one stat and lowers another
}

# ---------------------------------------------------------
# 5) BUILDS POWER FROM FAINTED ALLIES
# ---------------------------------------------------------
ABILITY_ALLY_FAINT_BUFFS = {
    "supremeoverlord": {
        "per_fainted_ally": 0.1,
        "max_multiplier": 1.5,
    },  # Increases power for each fainted ally
}

# ---------------------------------------------------------
# 6) WEATHER-BASED BUFFS
# ---------------------------------------------------------
ABILITY_WEATHER_BUFFS = {
    "swiftswim": {"spe": 2.0, "rain_only": True},  # Doubles Speed in rain
    "raindish": {"heal_in_rain": 1 / 16},  # Heals each turn in rain
    "dryskin": {
        "heal_in_rain": 1 / 8,
        "lose_in_sun": 1 / 8,
    },  # Heals in rain, loses HP in sun
    "chlorophyll": {"spe": 2.0, "sun_only": True},  # Doubles Speed in sun
    "solarpower": {"spa": 1.5, "sun_only": True},  # Boosts SpA in sun
    "harvest": {"berry_regen_in_sun": True},  # Restores berry more often in sun
    "leafguard": {"status_protection_in_sun": True},  # Prevents status in sun
    "sandrush": {"spe": 2.0, "sand_only": True},  # Doubles Speed in sand
    "sandforce": {
        "rock_ground_steel": 1.3,
        "sand_only": True,
    },  # Boosts Rock/Ground/Steel in sand
    "sandveil": {"evasion": 1.25, "sand_only": True},  # Boosts evasion in sand
    "slushrush": {"spe": 2.0, "snow_only": True},  # Doubles Speed in snow
    "snowcloak": {"evasion": 1.25, "snow_only": True},  # Boosts evasion in snow
    "icebody": {"heal_in_snow": 1 / 16},  # Heals each turn in snow
}

# ---------------------------------------------------------
# 7) TERRAIN-BASED BUFFS
# ---------------------------------------------------------
ABILITY_TERRAIN_BUFFS = {
    "surgesurfer": {
        "spe": 2.0,
        "electric_terrain_only": True,
    },  # Doubles Speed in Electric Terrain
    "grasspelt": {
        "def": 1.5,
        "grassy_terrain_only": True,
    },  # Boosts Defense in Grassy Terrain
    "quarkdrive": {
        "boost_best_stat_in_electric_terrain_or_booster": True
    },  # Boosts best stat in Electric Terrain
    "hadronengine": {
        "spa": 4 / 3,
        "electric_terrain_only_or_sets": True,
    },  # Boosts SpA in Electric Terrain
}

# ---------------------------------------------------------
# 8) SUN / PROTOSYNTHESIS STYLE BUFFS
# ---------------------------------------------------------
ABILITY_SPECIAL_FIELD_BUFFS = {
    "protosynthesis": {
        "boost_best_stat_in_sun_or_booster": True
    },  # Boosts best stat in sun or with Booster Energy
    "quarkdrive": {
        "boost_best_stat_in_electric_terrain_or_booster": True
    },  # Boosts best stat in Electric Terrain or with Booster Energy
    "orichalcumpulse": {
        "atk": 4 / 3,
        "sun_only_or_sets_sun": True,
    },  # Boosts Attack and sets sun
    "hadronengine": {
        "spa": 4 / 3,
        "electric_terrain_only_or_sets": True,
    },  # Boosts SpA and sets Electric Terrain
}

# ---------------------------------------------------------
# 9) LOW HP POWER BUFFS
# ---------------------------------------------------------
ABILITY_LOW_HP_BUFFS = {
    "swarm": {"bug": 1.5, "hp_below": 1 / 3},  # Boosts Bug moves at low HP
    "blaze": {"fire": 1.5, "hp_below": 1 / 3},  # Boosts Fire moves at low HP
    "torrent": {"water": 1.5, "hp_below": 1 / 3},  # Boosts Water moves at low HP
    "overgrow": {"grass": 1.5, "hp_below": 1 / 3},  # Boosts Grass moves at low HP
}

# ---------------------------------------------------------
# 10) STATUS-BASED BUFFS
# ---------------------------------------------------------
ABILITY_STATUS_BUFFS = {
    "guts": {"atk": 1.5, "status_only": True},  # Boosts Attack when statused
    "quickfeet": {"spe": 1.5, "status_only": True},  # Boosts Speed when statused
    "marvelscale": {"def": 1.5, "status_only": True},  # Boosts Defense when statused
    "flareboost": {"spa": 1.5, "burned_only": True},  # Boosts SpA when burned
    "toxicboost": {"atk": 1.5, "poisoned_only": True},  # Boosts Attack when poisoned
    "poisonheal": {"heal_if_poisoned": 1 / 8},  # Heals when poisoned
}

# ---------------------------------------------------------
# 11) ITEM-LOSS OR ITEM-BASED BUFFS
# ---------------------------------------------------------
ABILITY_ITEM_TRIGGERED_BUFFS = {
    "unburden": {
        "double_speed_when_item_lost": True
    },  # Doubles Speed after losing item
    "stakeout": {
        "multiplier": 2.0,
        "target_switching_in": True,
    },  # Doubles damage on switch-in target
    "gorillatactics": {
        "atk": 1.5,
        "choice_lock": True,
    },  # Boosts Attack but locks move choice
    "harvest": {"berry_regen": True},  # Can restore used berry
    "pickup": {"item_gain": "end_turn"},  # May gain item at end of turn
}

# ---------------------------------------------------------
# 12) RAW OFFENSIVE POWER BUFFS
# ---------------------------------------------------------
ABILITY_OFFENSIVE_BUFFS = {
    "adaptability": {"stab": 2.0},  # Stronger STAB bonus
    "hustle": {"atk": 1.5, "accuracy": 0.8},  # Boosts Attack, lowers accuracy
    "dragonsmaw": {"dragon": 1.5},  # Boosts Dragon moves
    "transistor": {"electric": 1.3},  # Boosts Electric moves
    "rockypayload": {"rock": 1.5},  # Boosts Rock moves
    "steelworker": {"steel": 1.5},  # Boosts Steel moves
    "waterbubble": {"water": 2.0},  # Doubles Water move power
    "technician": {"base_power_at_most": 60, "multiplier": 1.5},  # Boosts weaker moves
    "analytic": {
        "multiplier": 1.3,
        "when_moving_last": True,
    },  # Boosts attacks when moving last
    "sheerforce": {
        "multiplier": 1.3,
        "secondary_effect_moves_only": True,
    },  # Boosts moves with secondary effects
    "toughclaws": {
        "multiplier": 1.3,
        "contact_moves_only": True,
    },  # Boosts contact moves
    "ironfist": {"multiplier": 1.2, "punch_moves_only": True},  # Boosts punch moves
    "strongjaw": {"multiplier": 1.5, "bite_moves_only": True},  # Boosts bite moves
    "megalauncher": {"multiplier": 1.5, "pulse_moves_only": True},  # Boosts pulse moves
    "reckless": {
        "multiplier": 1.2,
        "recoil_or_crash_moves_only": True,
    },  # Boosts recoil/crash moves
    "sharpsness": {
        "multiplier": 1.5,
        "slicing_moves_only": True,
    },  # Boosts slicing moves
    "punkrock": {"multiplier": 1.3, "sound_moves_only": True},  # Boosts sound moves
    "rivalry": {
        "same_gender": 1.25,
        "opposite_gender": 0.75,
    },  # Changes power based on gender
    "flashfire": {
        "fire": 1.5,
        "requires_activation": True,
    },  # Boosts Fire after activation
}

# ---------------------------------------------------------
# 13) MOVE TYPE CONVERSION BUFFS
# ---------------------------------------------------------
ABILITY_MOVE_TYPE_CHANGE_BUFFS = {
    "aerilate": {
        "normal_to": "flying",
        "multiplier": 1.2,
    },  # Converts Normal to Flying and boosts it
    "pixilate": {
        "normal_to": "fairy",
        "multiplier": 1.2,
    },  # Converts Normal to Fairy and boosts it
    "refrigerate": {
        "normal_to": "ice",
        "multiplier": 1.2,
    },  # Converts Normal to Ice and boosts it
    "galvanize": {
        "normal_to": "electric",
        "multiplier": 1.2,
    },  # Converts Normal to Electric and boosts it
    "normalize": {
        "all_to": "normal",
        "multiplier": 1.2,
    },  # Converts all moves to Normal
    "liquidvoice": {"sound_to": "water"},  # Converts sound moves to Water
}

# ---------------------------------------------------------
# 14) CRITICAL HIT BUFFS
# ---------------------------------------------------------
ABILITY_CRIT_BUFFS = {
    "superluck": {"crit_stage": 1},  # Raises critical hit rate
    "sniper": {"crit_multiplier_bonus": True},  # Makes critical hits stronger
    "merciless": {"always_crit_vs_poisoned": True},  # Always crits poisoned targets
}

# ---------------------------------------------------------
# 15) ACCURACY / HIT RELIABILITY BUFFS
# ---------------------------------------------------------
ABILITY_ACCURACY_BUFFS = {
    "compoundeyes": {"accuracy": 1.3},  # Boosts move accuracy
    "noguard": {"all_moves_hit": True},  # All moves always hit
    "victorystar": {"accuracy": 1.1},  # Slightly boosts accuracy
}

# ---------------------------------------------------------
# 16) STAT CHANGE INTERACTION BUFFS
# ---------------------------------------------------------
ABILITY_STAT_CHANGE_BUFFS = {
    "simple": {"double_stat_stage_changes": True},  # Doubles stat changes
    "contrary": {"invert_stat_stage_changes": True},  # Reverses stat changes
    "defiant": {"on_stat_drop": {"atk": 2}},  # Boosts Attack when stats are lowered
    "competitive": {"on_stat_drop": {"spa": 2}},  # Boosts SpA when stats are lowered
    "opportunist": {"copy_foe_stat_boosts": True},  # Copies foe stat boosts
    "mirrorarmor": {"reflect_stat_drops": True},  # Reflects stat drops back
}

# ---------------------------------------------------------
# 17) SPEED / TURN ORDER BUFFS
# ---------------------------------------------------------
ABILITY_SPEED_TEMPO_BUFFS = {
    "speedboost": {"end_turn": {"spe": 1}},  # Boosts Speed every turn
    "swiftswim": {"spe": 2.0, "rain_only": True},  # Doubles Speed in rain
    "chlorophyll": {"spe": 2.0, "sun_only": True},  # Doubles Speed in sun
    "sandrush": {"spe": 2.0, "sand_only": True},  # Doubles Speed in sand
    "slushrush": {"spe": 2.0, "snow_only": True},  # Doubles Speed in snow
    "surgesurfer": {
        "spe": 2.0,
        "electric_terrain_only": True,
    },  # Doubles Speed in Electric Terrain
    "quickfeet": {"spe": 1.5, "status_only": True},  # Boosts Speed when statused
    "unburden": {
        "double_speed_when_item_lost": True
    },  # Doubles Speed after losing item
    "stall": {"moves_last_in_priority_bracket": True},  # Always moves last in bracket
    "prankster": {"status_move_priority": 1},  # Gives priority to status moves
    "triage": {"healing_move_priority": 3},  # Gives priority to healing moves
}

# ---------------------------------------------------------
# 18) DEFENSIVE / SURVIVAL BUFFS
# ---------------------------------------------------------
ABILITY_SURVIVAL_BUFFS = {
    "multiscale": {"damage_taken_at_full_hp": 0.5},  # Halves damage at full HP
    "shadowshield": {"damage_taken_at_full_hp": 0.5},  # Halves damage at full HP
    "filter": {"super_effective_damage": 0.75},  # Reduces super effective damage
    "solidrock": {"super_effective_damage": 0.75},  # Reduces super effective damage
    "prismarmor": {"super_effective_damage": 0.75},  # Reduces super effective damage
    "furcoat": {"physical_damage": 0.5},  # Halves physical damage
    "icescales": {"special_damage": 0.5},  # Halves special damage
    "thickfat": {"fire": 0.5, "ice": 0.5},  # Reduces Fire and Ice damage
    "waterbubble": {"fire": 0.5},  # Reduces Fire damage
    "heatproof": {"fire": 0.5},  # Reduces Fire damage
    "fluffy": {"contact": 0.5, "fire": 2.0},  # Reduces contact damage, weak to Fire
}

# ---------------------------------------------------------
# 19) ABILITIES THAT IMPROVE POSITIONAL / DECISION VALUE
# ---------------------------------------------------------
ABILITY_UTILITY_BUFFS = {
    "magicbounce": {"reflect_status_moves": True},  # Reflects status moves
    "goodasgold": {"immune_to_status_moves": True},  # Immune to status moves
    "unaware": {
        "ignore_target_stat_boosts_in_calc": True
    },  # Ignores foe boosts in damage calc
    "infiltrator": {
        "ignore_screens_and_substitute_for_damage": True
    },  # Ignores screens and Substitute
    "moldbreaker": {
        "ignore_defensive_abilities": True
    },  # Ignores target defensive abilities
    "turboblaze": {"ignore_defensive_abilities": True},  # Same as Mold Breaker
    "teravolt": {"ignore_defensive_abilities": True},  # Same as Mold Breaker
}
