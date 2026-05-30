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
    "painsplit": 0.35,
    "strengthsap": 0.5,
}


# Moves with delayed or risky recovery should be valued lower than immediate healing.
DELAYED_HEALING_MOVES = {"wish"}
SELF_SLEEP_HEALING_MOVES = {"rest"}


# Attacks whose success depends on a specific turn context rather than only on
# accuracy, typing and damage.
ATTACK_CONDITIONAL_MOVES = {"suckerpunch", "thunderclap"}
PRIORITY_TARGET_REQUIRED_ATTACKS = {"upperhand"}
INTERRUPTIBLE_ATTACK_MOVES = {"focuspunch"}
REACTIVE_DAMAGE_ATTACKS = {
    "bide",
    "comeuppance",
    "counter",
    "metalburst",
    "mirrorcoat",
    "shelltrap",
}


# Attacks that fail unless the target/user/field has a required state.
TARGET_STATUS_REQUIRED_ATTACKS = {
    "dreameater": {"slp"},
}
USER_STATUS_REQUIRED_ATTACKS = {
    "snore": {"slp"},
}
FIELD_REQUIRED_ATTACKS = {
    "steelroller": {"electricterrain", "grassyterrain", "mistyterrain", "psychicterrain"},
}
TARGET_ITEM_REQUIRED_ATTACKS = {"poltergeist"}
USER_ITEM_REQUIRED_ATTACKS = {"fling", "naturalgift"}
USER_HISTORY_REQUIRED_ATTACKS = {"belch", "lastresort"}


# Two-turn attacks are not unusable, but should not be treated as immediate
# damage unless weather or an item removes the charge turn.
TWO_TURN_ATTACKS = {
    "bounce",
    "dig",
    "dive",
    "electroshot",
    "fly",
    "freezeshock",
    "iceburn",
    "meteorbeam",
    "phantomforce",
    "razorwind",
    "shadowforce",
    "skullbash",
    "skyattack",
    "skydrop",
    "solarbeam",
    "solarblade",
}
SUN_SKIP_CHARGE_ATTACKS = {"solarbeam", "solarblade"}
RAIN_SKIP_CHARGE_ATTACKS = {"electroshot"}


# Attacks that consume the user or a large chunk of its HP need a different
# risk model from ordinary recoil.
SELF_DESTRUCT_ATTACKS = {"explosion", "finalgambit", "mistyexplosion", "selfdestruct"}
HIGH_SELF_DAMAGE_ATTACKS = {"chloroblast", "mindblown", "steelbeam"}


# Moves exposed with basePower 0 whose damage is determined dynamically.
SPEED_RATIO_ATTACKS = {"electroball", "gyroball"}
LOW_HP_POWER_ATTACKS = {"flail", "reversal"}
TARGET_HP_POWER_ATTACKS = {"crushgrip", "hardpress", "wringout"}
BOOST_POWER_ATTACKS = {"powertrip", "storedpower"}
HALF_CURRENT_HP_ATTACKS = {
    "guardianofalola",
    "naturesmadness",
    "ruination",
    "superfang",
}
USER_HP_DAMAGE_ATTACKS = {"finalgambit"}
HP_EQUALIZER_ATTACKS = {"endeavor"}
RANDOM_POWER_ATTACKS = {"magnitude", "present"}
OHKO_ATTACKS = {"fissure", "guillotine", "horndrill", "sheercold"}
