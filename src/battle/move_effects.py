# =========================================================
# GEN 9 RANDOM BATTLE (SINGLES)
# Protect/Hazard conditions and move with special effects
# =========================================================

from poke_env.battle.effect import Effect
from poke_env.battle.side_condition import SideCondition

# Effects that mean the target is protected from most direct attacks this turn.
PROTECT_LIKE_EFFECTS = {
    Effect.PROTECT,
    Effect.BANEFUL_BUNKER,
    Effect.KINGS_SHIELD,
    Effect.OBSTRUCT,
    Effect.SILK_TRAP,
    Effect.SPIKY_SHIELD,
}


# Entry hazards that damage or disrupt opponents when they switch in.
HAZARD_SIDE_CONDITIONS = {
    SideCondition.STEALTH_ROCK,
    SideCondition.SPIKES,
    SideCondition.TOXIC_SPIKES,
    SideCondition.STICKY_WEB,
}


# Stat groups used to understand whether setup boosts fit the current moveset.
SETUP_ATTACK_STATS = {"atk", "spa", "spe"}
SETUP_DEFENSE_STATS = {"def", "spd", "evasion"}


# How valuable it usually is to lower each target stat.
TARGET_DEBUFF_STAT_VALUES = {
    "atk": 22,
    "spa": 22,
    "spe": 20,
    "def": 18,
    "spd": 18,
    "accuracy": 16,
    "evasion": 14,
}


# Baseline value for inflicting each major status condition.
STATUS_INFLICTION_VALUES = {
    "brn": 34,
    "par": 36,
    "slp": 52,
    "frz": 48,
    "psn": 26,
    "tox": 42,
}


# Fallback healing data for moves whose recovery is dynamic or not exposed by poke_env.
HEALING_MOVE_FALLBACKS = {
    "milkdrink": 0.5,
    "moonlight": 0.5,
    "morningsun": 0.5,
    "shoreup": 0.5,
    "slackoff": 0.5,
    "softboiled": 0.5,
    "synthesis": 0.5,
    "wish": 0.5,
    "rest": 1.0,
}


# Moves with delayed or risky recovery should be valued lower than immediate healing.
DELAYED_HEALING_MOVES = {"wish"}
SELF_SLEEP_HEALING_MOVES = {"rest"}
