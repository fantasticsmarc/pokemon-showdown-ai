# =========================================================
# GEN 9 RANDOM BATTLE (SINGLES)
# ABILITIES FOR DAMAGE / RESISTANCES / TEMPO
# =========================================================

# ---------------------------------------------------------
# 1) FULL IMMUNITY TO MOVE TYPE
# ---------------------------------------------------------
ABILITY_NEGATES = {
    "voltabsorb": ["electric"],  # Absorbs electric moves
    "motordrive": ["electric"],  # Immune to electric, boosts Speed
    "lightningrod": ["electric"],  # Redirects and absorbs electric moves
    "sapsipper": ["grass"],  # Immune to grass, boosts Attack
    "stormdrain": ["water"],  # Redirects and absorbs water moves
    "waterabsorb": ["water"],  # Absorbs water moves
    "dryskin": ["water"],  # Absorbs water, harmed by fire
    "flashfire": ["fire"],  # Absorbs fire, boosts fire moves
    "wellbakedbody": ["fire"],  # Immune to fire, boosts Defense
    "levitate": ["ground"],  # Immune to ground moves
    "eartheater": ["ground"],  # Absorbs ground, heals
}

# ---------------------------------------------------------
# 2) HEALS WHEN HIT BY TYPE
# ---------------------------------------------------------
ABILITY_HEALS_FROM_TYPE = {
    "voltabsorb": ["electric"],  # Heals from electric moves
    "waterabsorb": ["water"],  # Heals from water moves
    "dryskin": ["water"],  # Heals from water
    "eartheater": ["ground"],  # Heals from ground moves
}

# ---------------------------------------------------------
# 3) BOOSTS WHEN HIT
# ---------------------------------------------------------
ABILITY_BOOSTS_WHEN_HIT = {
    "motordrive": {
        "types": ["electric"],
        "boost": {"spe": 1},
    },  # Speed boost from electric
    "lightningrod": {
        "types": ["electric"],
        "boost": {"spa": 1},
    },  # SpA boost from electric
    "stormdrain": {"types": ["water"], "boost": {"spa": 1}},  # SpA boost from water
    "sapsipper": {"types": ["grass"], "boost": {"atk": 1}},  # Attack boost from grass
    "wellbakedbody": {
        "types": ["fire"],
        "boost": {"def": 2},
    },  # Big Defense boost from fire
    "thermalexchange": {
        "types": ["fire"],
        "boost": {"atk": 1},
    },  # Attack boost from fire
    "steamengine": {
        "types": ["fire", "water"],
        "boost": {"spe": 6},
    },  # Huge Speed boost
    "weakarmor": {
        "trigger": "physical",
        "boost": {"spe": 2, "def": -1},
    },  # Speed up, Defense down
    "justified": {"types": ["dark"], "boost": {"atk": 1}},  # Attack boost from dark
    "rattled": {"types": ["bug", "dark", "ghost"], "boost": {"spe": 1}},  # Speed boost
    "berserk": {
        "trigger": "hp_below_half_after_hit",
        "boost": {"spa": 1},
    },  # SpA boost below 50%
    "angerpoint": {"trigger": "crit", "boost": {"atk": 12}},  # Max Attack on crit
}

# ---------------------------------------------------------
# 4) REDIRECTION (SINGLES = ABSORB EFFECT)
# ---------------------------------------------------------
ABILITY_REDIRECTS = {
    "lightningrod": ["electric"],  # Redirects electric moves
    "stormdrain": ["water"],  # Redirects water moves
}

# ---------------------------------------------------------
# 5) OFFENSIVE TYPE MULTIPLIERS
# ---------------------------------------------------------
ABILITY_ATTACK_TYPE_MULTIPLIERS = {
    "swarm": {"bug": 1.5, "hp_below": 1 / 3},  # Boost bug at low HP
    "blaze": {"fire": 1.5, "hp_below": 1 / 3},  # Boost fire at low HP
    "torrent": {"water": 1.5, "hp_below": 1 / 3},  # Boost water at low HP
    "overgrow": {"grass": 1.5, "hp_below": 1 / 3},  # Boost grass at low HP
    "dragonsmaw": {"dragon": 1.5},  # Boost dragon moves
    "transistor": {"electric": 1.3},  # Boost electric moves
    "rockypayload": {"rock": 1.5},  # Boost rock moves
    "steelworker": {"steel": 1.5},  # Boost steel moves
    "waterbubble": {"water": 2.0},  # Double water damage
    "flashfire": {"fire": 1.5, "requires_activation": True},  # Boost fire after absorb
}

# ---------------------------------------------------------
# 6) OFFENSIVE MOVE CLASS MULTIPLIERS
# ---------------------------------------------------------
ABILITY_ATTACK_MOVE_MULTIPLIERS = {
    "adaptability": {"stab": 2.0},  # Stronger STAB
    "technician": {"base_power_at_most": 60, "multiplier": 1.5},  # Boost weak moves
    "analytic": {"multiplier": 1.3, "when_moving_last": True},  # Boost when slower
    "sheerforce": {
        "multiplier": 1.3,
        "secondary_effect_moves_only": True,
    },  # Boost no-effect moves
    "toughclaws": {
        "multiplier": 1.3,
        "contact_moves_only": True,
    },  # Boost contact moves
    "ironfist": {"multiplier": 1.2, "punch_moves_only": True},  # Boost punch moves
    "strongjaw": {"multiplier": 1.5, "bite_moves_only": True},  # Boost bite moves
    "megalauncher": {"multiplier": 1.5, "pulse_moves_only": True},  # Boost pulse moves
    "reckless": {
        "multiplier": 1.2,
        "recoil_or_crash_moves_only": True,
    },  # Boost recoil moves
    "sharpsness": {
        "multiplier": 1.5,
        "slicing_moves_only": True,
    },  # Boost slicing moves
    "punkrock": {"multiplier": 1.3, "sound_moves_only": True},  # Boost sound moves
    "stakeout": {"multiplier": 2.0, "target_switching_in": True},  # Double vs switch-in
    "rivalry": {"same_gender": 1.25, "opposite_gender": 0.75},  # Gender-based boost
    "infiltrator": {
        "ignore_screens_and_substitute_for_damage": True
    },  # Ignores screens
}

# ---------------------------------------------------------
# 7) MOVE TYPE CHANGES
# ---------------------------------------------------------
ABILITY_MOVE_TYPE_CHANGE = {
    "aerilate": {"normal_to": "flying", "multiplier": 1.2},  # Normal -> Flying
    "pixilate": {"normal_to": "fairy", "multiplier": 1.2},  # Normal -> Fairy
    "refrigerate": {"normal_to": "ice", "multiplier": 1.2},  # Normal -> Ice
    "galvanize": {"normal_to": "electric", "multiplier": 1.2},  # Normal -> Electric
    "normalize": {"all_to": "normal", "multiplier": 1.2},  # All moves Normal
    "liquidvoice": {"sound_to": "water"},  # Sound -> Water
}

# ---------------------------------------------------------
# 8) DEFENSIVE MULTIPLIERS
# ---------------------------------------------------------
ABILITY_DEFENSE_MULTIPLIERS = {
    "thickfat": {"fire": 0.5, "ice": 0.5},  # Reduces fire/ice damage
    "heatproof": {"fire": 0.5},  # Reduces fire damage
    "dryskin": {"fire": 1.25},  # Takes more fire damage
    "waterbubble": {"fire": 0.5},  # Reduces fire damage
    "fluffy": {"contact": 0.5, "fire": 2.0},  # Less contact, more fire damage
    "punkrock": {"sound": 0.5},  # Reduces sound damage
    "icescales": {"special": 0.5},  # Halves special damage
    "furcoat": {"physical": 0.5},  # Halves physical damage
    "marvelscale": {
        "physical": 2 / 3,
        "status_only": True,
    },  # Boost defense when statused
}

# ---------------------------------------------------------
# 9) REDUCE SUPER EFFECTIVE DAMAGE
# ---------------------------------------------------------
ABILITY_REDUCE_SUPER_EFFECTIVE = {
    "filter": 0.75,  # Reduces super effective damage
    "solidrock": 0.75,  # Same as filter
    "prismarmor": 0.75,  # Same as filter
}

# ---------------------------------------------------------
# 10) FULL HP DAMAGE REDUCTION
# ---------------------------------------------------------
ABILITY_FULL_HP_REDUCTION = {
    "multiscale": 0.5,  # Halves damage at full HP
    "shadowshield": 0.5,  # Same as multiscale
}

# ---------------------------------------------------------
# 11) CRITICAL HIT INTERACTIONS
# ---------------------------------------------------------
ABILITY_CRIT_INTERACTIONS = {
    "battlearmor": {"prevent_critical_hits": True},  # No crits
    "shellarmor": {"prevent_critical_hits": True},  # No crits
    "sniper": {"crit_multiplier_bonus": True},  # Stronger crits
    "merciless": {"always_crit_vs_poisoned": True},  # Always crit poisoned
    "superluck": {"crit_stage": 1},  # Higher crit chance
}

# ---------------------------------------------------------
# 12) BYPASS DEFENSIVE ABILITIES
# ---------------------------------------------------------
ABILITY_BYPASSES_DEFENSIVE_ABILITIES = {
    "moldbreaker": True,  # Ignores abilities
    "turboblaze": True,  # Same as mold breaker
    "teravolt": True,  # Same as mold breaker
}

# ---------------------------------------------------------
# 13) STAT MODIFIERS (TEMPO IMPORTANT)
# ---------------------------------------------------------
ABILITY_STAT_MODIFIERS = {
    "hustle": {"atk": 1.5},  # Boost attack, lowers accuracy
    "guts": {"atk": 1.5, "status_only": True},  # Boost attack if statused
    "flareboost": {"spa": 1.5, "burned_only": True},  # Boost SpA if burned
    "toxicboost": {"atk": 1.5, "poisoned_only": True},  # Boost attack if poisoned
    "solarpower": {"spa": 1.5, "sun_only": True},  # Boost SpA in sun
    "defeatist": {"atk": 0.5, "spa": 0.5, "hp_at_or_below": 0.5},  # Halves stats low HP
    "slowstart": {"atk": 0.5, "spe": 0.5, "turns": 5},  # Slow start penalty
    "supremeoverlord": {
        "per_fainted_ally": 0.1,
        "max_multiplier": 1.5,
    },  # Boost from allies
    "gorillatactics": {"atk": 1.5, "choice_lock": True},  # Boost but locked move
}

# ---------------------------------------------------------
# 14) STATUS / TEMPO ABILITIES
# ---------------------------------------------------------
ABILITY_STATUS_TEMPO = {
    "speedboost": {"end_turn": {"spe": 1}},  # Speed each turn
    "moxie": {"on_knockout": {"atk": 1}},  # Attack after KO
    "beastboost": {"on_knockout_best_stat": 1},  # Boost best stat
    "intimidate": {"on_switch_in_lower_target": {"atk": -1}},  # Lower enemy attack
    "unburden": {"double_speed_when_item_lost": True},  # Double speed no item
    "prankster": {"status_move_priority": 1},  # Priority status moves
    "magicbounce": {"reflect_status_moves": True},  # Reflect status
    "goodasgold": {"immune_to_status_moves": True},  # Immune to status
    "unaware": {"ignore_target_stat_boosts_in_calc": True},  # Ignore stat boosts
    "simple": {"double_stat_stage_changes": True},  # Double stat changes
    "contrary": {"invert_stat_stage_changes": True},  # Reverse stat changes
    "defiant": {"on_stat_drop": {"atk": 2}},  # Boost attack on drop
    "competitive": {"on_stat_drop": {"spa": 2}},  # Boost SpA on drop
}

# ---------------------------------------------------------
# 15) CONTACT / INDIRECT DAMAGE
# ---------------------------------------------------------
ABILITY_CONTACT_AND_INDIRECT = {
    "roughskin": {"contact_damage": 1 / 8},  # Damages attacker on contact
    "ironbarbs": {"contact_damage": 1 / 8},  # Same as rough skin
    "static": {"contact_status": "par"},  # Can paralyze attacker
    "flamebody": {"contact_status": "brn"},  # Can burn attacker
    "poisonpoint": {"contact_status": "psn"},  # Can poison attacker
    "gooey": {"lower_attacker_spe_on_contact": 1},  # Lowers speed on contact
    "aftermath": {"explode_on_contact_ko": True},  # Damages on KO
}

# ---------------------------------------------------------
# 16) INDIRECT DAMAGE / SPECIAL RULES
# ---------------------------------------------------------
ABILITY_INDIRECT_RULES = {
    "magicguard": {"ignore_indirect_damage": True},  # No indirect damage
    "rockhead": {"ignore_recoil": True},  # No recoil damage
    "overcoat": {
        "ignore_powder": True,
        "ignore_weather_damage": True,
    },  # Weather immunity
    "soundproof": {"immune_to_sound_moves": True},  # Immune to sound
    "bulletproof": {"immune_to_ball_bomb_moves": True},  # Immune to bomb moves
}
