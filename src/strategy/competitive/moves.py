from dataclasses import dataclass, field

from poke_env.battle.move_category import MoveCategory
from poke_env.battle.target import Target

import battle.core as core
import strategy.data.move_effects as move_effects


# Moves that remove hazards or field pressure from our side.
HAZARD_REMOVAL_MOVES = {"rapidspin", "defog", "tidyup", "mortalspin"}

# Pivot moves are valuable because they deal damage or support while keeping momentum.
PIVOT_MOVES = {
    "uturn",
    "voltswitch",
    "flipturn",
    "partingshot",
    "chillyreception",
    "batonpass",
    "teleport",
}

# Phazing forces the opponent out, which is strong against boosted sweepers.
FORCE_SWITCH_MOVES = {"roar", "whirlwind", "dragontail", "circlethrow"}

# Trapping moves help turn defensive advantages into guaranteed progress.
TRAPPING_MOVES = {
    "anchorshot",
    "block",
    "jawlock",
    "meanlook",
    "spiderweb",
    "spiritshackle",
    "thousandwaves",
}

# Screens make setup and bulky positioning safer for several turns.
SCREEN_MOVES = {"reflect", "lightscreen", "auroraveil"}

# Cleric moves repair team status or trade one Pokemon to revive momentum.
CLERIC_MOVES = {"aromatherapy", "healbell", "healingwish", "lunardance"}

# Item control is one of the most reliable ways to make permanent progress.
ITEM_CONTROL_MOVES = {"knockoff", "trick", "switcheroo", "corrosivegas"}

# Scout moves are useful to block damage, burn turns, or protect a Substitute.
SCOUT_MOVES = {
    "banefulbunker",
    "detect",
    "kingsshield",
    "obstruct",
    "protect",
    "silktrap",
    "spikyshield",
    "substitute",
}

# Priority attacks can revenge kill faster weakened threats.
PRIORITY_ATTACK_MOVES = {
    "aquajet",
    "bulletpunch",
    "extremespeed",
    "fakeout",
    "firstimpression",
    "iceshard",
    "machpunch",
    "quickattack",
    "shadowsneak",
    "suckerpunch",
    "vacuumwave",
}

# Big recharge attacks can win a last turn, but they often donate a free turn
# after the KO. Score them as high-risk unless they are closing the game.
RECHARGE_MOVES = {
    "blastburn",
    "eternabeam",
    "frenzyplant",
    "gigaimpact",
    "hydrocannon",
    "hyperbeam",
    "meteorassault",
    "prismaticlaser",
    "rockwrecker",
    "roaroftime",
}

# Anti-setup moves stop the opponent from snowballing instead of racing damage.
ANTI_SETUP_MOVES = {
    "clearsmog",
    "encore",
    "haze",
    "taunt",
    "topsyturvy",
    "trick",
    "switcheroo",
}

# High-impact status moves are often worth using even without direct damage.
HIGH_VALUE_STATUS_MOVES = {
    "glare",
    "nuzzle",
    "sleeppowder",
    "spore",
    "thunderwave",
    "toxic",
    "willowisp",
}

STATUS_PROGRESS_MOVES = {
    "confuseray",
    "curse",
    "disable",
    "leechseed",
    "perishsong",
    "strengthsap",
    "torment",
    "yawn",
}

CONTEXTUAL_SETUP_BOOSTS = {
    "curse": {"atk": 1, "def": 1},
}

SLEEP_TALK_MOVES = {"sleeptalk"}

# Tactical action groups used by the competitive decision layer.
EMERGENCY_TACTICAL_KINDS = {
    "attack",
    "switch",
    "heal",
    "hazard_removal",
    "disruption",
    "item_control",
    "phazing",
    "anti_setup",
    "scout",
    "sleep_talk",
}

REPEAT_SENSITIVE_KINDS = {
    "anti_setup",
    "cleric",
    "disruption",
    "heal",
    "hazard",
    "scout",
    "screen",
    "setup",
}

STRATEGIC_OVERRIDE_MARGIN = 12

# Protect-like moves lose most of their value when we expect the opponent to
# switch, because they spend our free turn without creating board progress.
PROTECT_EXPECTED_SWITCH_PENALTY = 64
PROTECT_EXPECTED_SWITCH_CAP = -8

# Conditional or context-sensitive attacks can fail based on the turn state.
ATTACK_CONDITIONAL_MOVES = move_effects.ATTACK_CONDITIONAL_MOVES
PRIORITY_TARGET_REQUIRED_ATTACKS = move_effects.PRIORITY_TARGET_REQUIRED_ATTACKS
INTERRUPTIBLE_ATTACK_MOVES = move_effects.INTERRUPTIBLE_ATTACK_MOVES
REACTIVE_DAMAGE_ATTACKS = move_effects.REACTIVE_DAMAGE_ATTACKS
TARGET_STATUS_REQUIRED_ATTACKS = move_effects.TARGET_STATUS_REQUIRED_ATTACKS
USER_STATUS_REQUIRED_ATTACKS = move_effects.USER_STATUS_REQUIRED_ATTACKS
FIELD_REQUIRED_ATTACKS = move_effects.FIELD_REQUIRED_ATTACKS
TARGET_ITEM_REQUIRED_ATTACKS = move_effects.TARGET_ITEM_REQUIRED_ATTACKS
USER_ITEM_REQUIRED_ATTACKS = move_effects.USER_ITEM_REQUIRED_ATTACKS
USER_HISTORY_REQUIRED_ATTACKS = move_effects.USER_HISTORY_REQUIRED_ATTACKS
TWO_TURN_ATTACKS = move_effects.TWO_TURN_ATTACKS
SELF_DESTRUCT_ATTACKS = move_effects.SELF_DESTRUCT_ATTACKS
HIGH_SELF_DAMAGE_ATTACKS = move_effects.HIGH_SELF_DAMAGE_ATTACKS


@dataclass
class MoveProfile:
    roles: set = field(default_factory=set)
    is_attack: bool = False
    is_hazard: bool = False
    is_hazard_removal: bool = False
    is_healing: bool = False
    is_setup: bool = False
    is_disruption: bool = False
    is_pivot: bool = False
    is_phazing: bool = False
    is_trapping: bool = False
    is_screen: bool = False
    is_cleric: bool = False
    is_item_control: bool = False
    is_scout: bool = False
    is_priority: bool = False
    is_anti_setup: bool = False


# Direct attacks are every non-status move according to poke_env.
def is_attacking_move(move):
    return core.get_move_category(move) != MoveCategory.STATUS


# Hazards are detected through poke_env SideCondition data when available.
def is_hazard_move(move):
    return core.safe_move_attr(move, "side_condition") in move_effects.HAZARD_SIDE_CONDITIONS


# Hazard removal is mostly name-based because poke_env exposes these inconsistently.
def is_hazard_removal_move(move):
    return move.id in HAZARD_REMOVAL_MOVES


# Healing is mixed: static poke_env heal data plus fallback lists for dynamic moves.
def is_healing_move(move):
    return bool(
        core.safe_move_attr(move, "heal", 0)
        or move.id in move_effects.HEALING_MOVE_FALLBACKS
    )


# Setup means the move boosts the user directly.
def is_setup_move(move):
    return bool(get_setup_boosts(move))


# Return only positive self-boosts. This avoids treating Close Combat as setup
# while still valuing Dragon Dance, Calm Mind, Victory Dance, etc.
def get_setup_boosts(move):
    if move.id in CONTEXTUAL_SETUP_BOOSTS:
        return CONTEXTUAL_SETUP_BOOSTS[move.id]

    self_boost = core.safe_move_attr(move, "self_boost")
    if self_boost:
        return {
            stat: stage
            for stat, stage in self_boost.items()
            if stage > 0
        }

    boosts = core.safe_move_attr(move, "boosts")
    if (
        core.get_move_category(move) == MoveCategory.STATUS
        and core.safe_move_attr(move, "target") == Target.SELF
        and boosts
    ):
        return {
            stat: stage
            for stat, stage in boosts.items()
            if stage > 0
        }
    return {}


# Phazing can be a direct flag or a known move id depending on the move.
def is_phazing_move(move):
    return bool(core.safe_move_attr(move, "force_switch")) or move.id in FORCE_SWITCH_MOVES


# Disruption includes status, debuffs, phazing, anti-setup and secondary effects.
def is_disruption_move(move):
    if move.id in STATUS_PROGRESS_MOVES:
        return True
    if core.safe_move_attr(move, "status") is not None:
        return True

    boosts = core.safe_move_attr(move, "boosts")
    target = core.safe_move_attr(move, "target")
    if boosts and target != Target.SELF:
        return True
    if is_phazing_move(move) or is_anti_setup_move(move):
        return True

    for secondary in core.safe_move_attr(move, "secondary", []):
        if (
            secondary.get("status") is not None
            or secondary.get("boosts")
            or secondary.get("volatileStatus") is not None
        ):
            return True
    return False


# Pivoting uses poke_env self_switch first, then a curated fallback list.
def is_pivot_move(move):
    return bool(core.safe_move_attr(move, "self_switch")) or move.id in PIVOT_MOVES


# These checks are intentionally small wrappers so the heuristic code reads clearly.
def is_trapping_move(move):
    return move.id in TRAPPING_MOVES


def is_screen_move(move):
    return move.id in SCREEN_MOVES


def is_cleric_move(move):
    return move.id in CLERIC_MOVES


def is_item_control_move(move):
    return move.id in ITEM_CONTROL_MOVES


def is_scout_move(move):
    return bool(core.safe_move_attr(move, "is_protect_move", False)) or move.id in SCOUT_MOVES


def is_priority_move(move):
    return is_attacking_move(move) and (
        core.get_move_priority(move) > 0 or move.id in PRIORITY_ATTACK_MOVES
    )


def is_recharge_move(move):
    return move.id in RECHARGE_MOVES or bool(core.safe_move_attr(move, "must_recharge"))


def is_anti_setup_move(move):
    return move.id in ANTI_SETUP_MOVES


# Build a reusable role summary for a move so strategy code can stay high level.
def get_move_profile(move):
    profile = MoveProfile(
        is_attack=is_attacking_move(move),
        is_hazard=is_hazard_move(move),
        is_hazard_removal=is_hazard_removal_move(move),
        is_healing=is_healing_move(move),
        is_setup=is_setup_move(move),
        is_disruption=is_disruption_move(move),
        is_pivot=is_pivot_move(move),
        is_phazing=is_phazing_move(move),
        is_trapping=is_trapping_move(move),
        is_screen=is_screen_move(move),
        is_cleric=is_cleric_move(move),
        is_item_control=is_item_control_move(move),
        is_scout=is_scout_move(move),
        is_priority=is_priority_move(move),
        is_anti_setup=is_anti_setup_move(move),
    )

    # Role names are used by team analysis to infer the intended game plan.
    if profile.is_attack:
        profile.roles.add("attack")
    if profile.is_hazard:
        profile.roles.add("hazard")
    if profile.is_hazard_removal:
        profile.roles.add("hazard_removal")
    if profile.is_healing:
        profile.roles.add("healing")
    if profile.is_setup:
        profile.roles.add("setup")
    if profile.is_disruption:
        profile.roles.add("disruption")
    if profile.is_pivot:
        profile.roles.add("pivot")
    if profile.is_phazing:
        profile.roles.add("phazing")
    if profile.is_trapping:
        profile.roles.add("trapping")
    if profile.is_screen:
        profile.roles.add("screen")
    if profile.is_cleric:
        profile.roles.add("cleric")
    if profile.is_item_control:
        profile.roles.add("item_control")
    if profile.is_scout:
        profile.roles.add("scout")
    if profile.is_priority:
        profile.roles.add("priority")
    if profile.is_anti_setup:
        profile.roles.add("anti_setup")

    return profile
