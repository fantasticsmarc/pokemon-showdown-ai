from dataclasses import dataclass, field
import math

import battle.core as core
import battle.utilities as utilities
import strategy.competitive.moves as competitive_moves


@dataclass
class PokemonProfile:
    roles: set = field(default_factory=set)
    role_reasons: dict = field(default_factory=dict)
    move_roles: dict = field(default_factory=dict)
    speed: float = 0.0
    bulk: float = 0.0
    offense: float = 0.0
    hazard_count: int = 0
    setup_count: int = 0
    recovery_count: int = 0
    disruption_count: int = 0
    priority_count: int = 0
    pivot_count: int = 0
    removal_count: int = 0
    screen_count: int = 0
    cleric_count: int = 0
    item_control_count: int = 0
    phazing_count: int = 0
    trapping_count: int = 0
    scout_count: int = 0
    anti_setup_count: int = 0
    best_damage_value: float = 0.0


@dataclass
class TeamPlan:
    style: str
    style_reason: str
    profiles: dict
    win_conditions: set
    hazard_setters: set
    defensive_pivots: set
    revenge_killers: set
    screen_setters: set
    anti_setup_users: set
    progress_makers: set


@dataclass
class TurnContext:
    phase: str
    plan: TeamPlan
    matchup_score: float
    opponent_threat: float
    safe_turn: bool
    active_importance: float
    opponent_remaining: int
    own_remaining: int
    best_attack_value: float = 0.0
    best_attack_damage: float = 0.0
    opponent_hp_percent: float = 0.0
    expected_opponent_switch: bool = False
    expected_switch_reason: str = "none"
    emergency: bool = False
    active_first_turn: bool = True


@dataclass
class CompetitiveAction:
    kind: str
    value: float
    move: object = None
    switch: object = None
    reason: str = ""


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

STRATEGIC_OVERRIDE_MARGIN = 18
ATTACK_CONDITIONAL_MOVES = {"suckerpunch"}


def get_move_accuracy(move):
    accuracy = core.safe_move_attr(move, "accuracy", 1.0)
    if accuracy is True or accuracy is None:
        return 1.0
    if accuracy is False:
        return 1.0
    if accuracy > 1:
        return accuracy / 100
    return accuracy


def get_secondary_entries(move):
    secondary = core.safe_move_attr(move, "secondary", [])
    if secondary is None:
        return []
    if isinstance(secondary, dict):
        return [secondary]
    return secondary


def get_secondary_effect_value(move, active, opponent, battle):
    value = 0.0
    for secondary in get_secondary_entries(move):
        chance = secondary.get("chance", 100) / 100
        boosts = secondary.get("boosts")
        if boosts:
            value += utilities.get_target_debuff_value(
                boosts,
                active,
                opponent,
                battle,
                chance,
            )
        if secondary.get("status") is not None:
            value += utilities.get_status_infliction_value(
                secondary.get("status"),
                active,
                opponent,
                battle,
                chance,
            )
        if secondary.get("volatileStatus") is not None:
            value += 10 * chance
    return value


def get_direct_disruption_value(move, active, opponent, battle):
    value = 0.0
    boosts = core.safe_move_attr(move, "boosts")
    status = core.safe_move_attr(move, "status")
    if boosts:
        value += utilities.get_target_debuff_value(boosts, active, opponent, battle)
    if status is not None and opponent.status is None:
        value += utilities.get_status_infliction_value(status, active, opponent, battle)
    return value


def pokemon_has_type(pokemon, type_name):
    return any(
        pokemon_type is not None and pokemon_type.name.lower() == type_name
        for pokemon_type in (pokemon.type_1, pokemon.type_2)
    )


def is_status_move_blocked(move, opponent):
    if core.safe_move_attr(move, "status") is None:
        return False
    if utilities.opponent_has_substitute(opponent):
        return True

    move_id = move.id
    if move_id == "thunderwave":
        return pokemon_has_type(opponent, "ground") or pokemon_has_type(opponent, "electric")
    if move_id == "willowisp":
        return pokemon_has_type(opponent, "fire")
    if move_id == "toxic":
        return pokemon_has_type(opponent, "poison") or pokemon_has_type(opponent, "steel")
    if move_id in {"sleeppowder", "stunspore", "spore"}:
        return pokemon_has_type(opponent, "grass")
    return False


def get_attack_risk_penalty(move, damage_percent, opponent_hp_percent):
    accuracy = get_move_accuracy(move)
    penalty = 0.0
    if accuracy < 0.9:
        penalty += (0.9 - accuracy) * 80
        if damage_percent >= opponent_hp_percent:
            penalty += (1 - accuracy) * 28
    elif accuracy < 1.0 and damage_percent >= opponent_hp_percent:
        penalty += (1 - accuracy) * 12
    return penalty


def is_reliable_finisher(battle, move, context, damage_percent):
    opponent_hp = battle.opponent_active_pokemon.current_hp_fraction * 100
    accuracy = get_move_accuracy(move)
    if move.id in ATTACK_CONDITIONAL_MOVES and context.expected_opponent_switch:
        return False
    if accuracy < 0.9 and opponent_hp > 12:
        return False
    margin = 1.08 if opponent_hp <= 35 else 1.15
    return damage_percent >= opponent_hp * margin


def opponent_has_snowball_route(opponent):
    for move in get_moves(opponent):
        if is_setup_move(move):
            return True
        if move.id in {"storedpower", "powertrip", "bodypress"}:
            return True
    return False


def finalize_selected_action(actions, selected):
    if selected is None:
        return get_best_action(actions)
    best_action = get_best_action(actions)
    if best_action is None or not math.isfinite(best_action.value):
        return selected
    if selected.value < 0 < best_action.value:
        best_action.reason = f"{best_action.reason}, override_floor"
        return best_action
    if selected.value + STRATEGIC_OVERRIDE_MARGIN <= best_action.value:
        best_action.reason = f"{best_action.reason}, override_floor"
        return best_action
    return selected


# Store the reason beside each role so debug output explains the plan instead
# of only showing labels like "breaker" or "wall".
def add_role(profile, role, reason):
    profile.roles.add(role)
    profile.role_reasons[role] = reason


# Return all known moves without exposing poke_env recursion issues to this module.
def get_moves(pokemon):
    return utilities.get_known_moves_safely(pokemon)


# Keep short aliases here so the strategy code reads like a battle plan while
# the detailed move taxonomy lives in competitive_moves.py.
is_attacking_move = competitive_moves.is_attacking_move
is_hazard_move = competitive_moves.is_hazard_move
is_hazard_removal_move = competitive_moves.is_hazard_removal_move
is_healing_move = competitive_moves.is_healing_move
is_setup_move = competitive_moves.is_setup_move
is_disruption_move = competitive_moves.is_disruption_move
is_pivot_move = competitive_moves.is_pivot_move


# Estimate broad offensive pressure from the visible moveset.
def estimate_best_damage_value(pokemon, battle):
    if battle is None or battle.opponent_active_pokemon is None:
        attacking_moves = [move for move in get_moves(pokemon) if is_attacking_move(move)]
        if not attacking_moves:
            return 0.0
        return max(core.safe_move_attr(move, "base_power", 0) for move in attacking_moves)

    return utilities.get_best_move_value(
        pokemon,
        battle.opponent_active_pokemon,
        battle,
        True,
        respect_turn_restrictions=False,
    )


# Build a role profile from stats, item, ability and moves.
def analyze_pokemon_profile(pokemon, battle=None):
    moves = get_moves(pokemon)
    speed = utilities.safe_stat(pokemon.stats, "spe")
    attack = utilities.safe_stat(pokemon.stats, "atk")
    special_attack = utilities.safe_stat(pokemon.stats, "spa")
    defense = utilities.safe_stat(pokemon.stats, "def")
    special_defense = utilities.safe_stat(pokemon.stats, "spd")

    profile = PokemonProfile(
        speed=speed,
        bulk=defense + special_defense + pokemon.current_hp_fraction * 100,
        offense=max(attack, special_attack),
        hazard_count=sum(1 for move in moves if is_hazard_move(move)),
        setup_count=sum(1 for move in moves if is_setup_move(move)),
        recovery_count=sum(1 for move in moves if is_healing_move(move)),
        disruption_count=sum(1 for move in moves if is_disruption_move(move)),
        priority_count=sum(1 for move in moves if competitive_moves.is_priority_move(move)),
        pivot_count=sum(1 for move in moves if is_pivot_move(move)),
        removal_count=sum(1 for move in moves if is_hazard_removal_move(move)),
        screen_count=sum(1 for move in moves if competitive_moves.is_screen_move(move)),
        cleric_count=sum(1 for move in moves if competitive_moves.is_cleric_move(move)),
        item_control_count=sum(
            1 for move in moves if competitive_moves.is_item_control_move(move)
        ),
        phazing_count=sum(1 for move in moves if competitive_moves.is_phazing_move(move)),
        trapping_count=sum(1 for move in moves if competitive_moves.is_trapping_move(move)),
        scout_count=sum(1 for move in moves if competitive_moves.is_scout_move(move)),
        anti_setup_count=sum(
            1 for move in moves if competitive_moves.is_anti_setup_move(move)
        ),
        best_damage_value=estimate_best_damage_value(pokemon, battle),
    )
    # Keep the move evidence for debug: this shows which concrete moves made a
    # Pokemon count as hazard setter, pivot, anti-setup user, etc.
    for move in moves:
        move_roles = sorted(competitive_moves.get_move_profile(move).roles)
        if move_roles:
            profile.move_roles[move.id] = move_roles

    if profile.hazard_count:
        add_role(profile, "hazard_setter", f"{profile.hazard_count} hazard move(s)")
    if profile.removal_count:
        add_role(profile, "hazard_control", f"{profile.removal_count} removal move(s)")
    if profile.recovery_count and profile.bulk >= 430:
        add_role(profile, "wall", f"bulk={profile.bulk:.0f} with recovery")
    if profile.pivot_count:
        add_role(profile, "pivot", f"{profile.pivot_count} pivot move(s)")
    if profile.disruption_count:
        add_role(profile, "support", f"{profile.disruption_count} disruption move(s)")
    if profile.priority_count or profile.speed >= 210:
        reason = (
            f"{profile.priority_count} priority attack(s)"
            if profile.priority_count
            else f"speed={profile.speed:.0f}"
        )
        add_role(profile, "revenge_killer", reason)
    if profile.screen_count:
        add_role(profile, "screen_support", f"{profile.screen_count} screen move(s)")
    if profile.cleric_count:
        add_role(profile, "cleric", f"{profile.cleric_count} cleric move(s)")
    if profile.item_control_count or profile.trapping_count:
        add_role(
            profile,
            "progress_maker",
            f"item_control={profile.item_control_count}, trapping={profile.trapping_count}",
        )
    if profile.phazing_count:
        add_role(profile, "phazer", f"{profile.phazing_count} phazing move(s)")
    if profile.scout_count and profile.bulk >= 390:
        add_role(profile, "scout_wall", f"bulk={profile.bulk:.0f} with scout move")
    if profile.anti_setup_count:
        add_role(profile, "anti_setup", f"{profile.anti_setup_count} anti-setup move(s)")
    if profile.offense >= 220 or profile.best_damage_value >= 80:
        add_role(
            profile,
            "breaker",
            f"offense={profile.offense:.0f}, best_damage_value={profile.best_damage_value:.1f}",
        )
    if profile.setup_count and (profile.offense >= 185 or profile.recovery_count):
        add_role(profile, "win_condition", f"{profile.setup_count} setup move(s)")
    if profile.setup_count and profile.speed >= 185:
        add_role(profile, "cleaner", f"speed={profile.speed:.0f} with setup")

    return profile


# Analyze the whole team and choose the broad plan CompetitiveBot should follow.
def analyze_team_plan(battle):
    profiles = {
        pokemon: analyze_pokemon_profile(pokemon, battle)
        for pokemon in battle.team.values()
        if not pokemon.fainted
    }
    hazard_setters = {
        pokemon for pokemon, profile in profiles.items() if "hazard_setter" in profile.roles
    }
    win_conditions = {
        pokemon for pokemon, profile in profiles.items() if "win_condition" in profile.roles
    }
    defensive_pivots = {
        pokemon
        for pokemon, profile in profiles.items()
        if "wall" in profile.roles or "pivot" in profile.roles
    }
    revenge_killers = {
        pokemon
        for pokemon, profile in profiles.items()
        if "revenge_killer" in profile.roles
    }
    screen_setters = {
        pokemon for pokemon, profile in profiles.items() if "screen_support" in profile.roles
    }
    anti_setup_users = {
        pokemon for pokemon, profile in profiles.items() if "anti_setup" in profile.roles
    }
    progress_makers = {
        pokemon for pokemon, profile in profiles.items() if "progress_maker" in profile.roles
    }
    breakers = {
        pokemon for pokemon, profile in profiles.items() if "breaker" in profile.roles
    }
    phazers = {pokemon for pokemon, profile in profiles.items() if "phazer" in profile.roles}

    if screen_setters and win_conditions:
        style = "screens_offense"
        style_reason = "team has screens plus setup win conditions"
    elif len(hazard_setters) >= 2 or (
        hazard_setters and (len(defensive_pivots) >= 2 or phazers)
    ):
        style = "hazard_stack"
        style_reason = "team can set hazards and has pivots/phazing to exploit chip"
    elif win_conditions and len(breakers) >= 2:
        style = "setup_sweep"
        style_reason = "team has setup win conditions supported by breakers"
    elif progress_makers and len(breakers) >= 2:
        style = "progress_offense"
        style_reason = "team has item/trapping progress plus breakers"
    elif len(revenge_killers) >= 3 and len(breakers) >= 2:
        style = "offense"
        style_reason = "team has multiple fast/priority attackers and breakers"
    elif len(defensive_pivots) >= 2:
        style = "balance"
        style_reason = "team has multiple walls or pivots"
    else:
        style = "adaptive"
        style_reason = "no single strategy is dominant, so play the board"

    return TeamPlan(
        style=style,
        style_reason=style_reason,
        profiles=profiles,
        win_conditions=win_conditions,
        hazard_setters=hazard_setters,
        defensive_pivots=defensive_pivots,
        revenge_killers=revenge_killers,
        screen_setters=screen_setters,
        anti_setup_users=anti_setup_users,
        progress_makers=progress_makers,
    )


# Create a compact signature so the agent only prints the full role map when it
# changes, instead of flooding the console every single turn.
def get_team_debug_signature(team_plan):
    parts = []
    for pokemon, profile in team_plan.profiles.items():
        roles = ",".join(sorted(profile.roles))
        hp = f"{pokemon.current_hp_fraction:.2f}"
        parts.append(f"{get_pokemon_label(pokemon)}:{hp}:{roles}")
    return "|".join(sorted(parts))


# Return a readable Pokemon name without assuming every poke_env object exposes
# the same label attribute in every battle state.
def get_pokemon_label(pokemon):
    return getattr(pokemon, "species", None) or getattr(pokemon, "name", None) or str(pokemon)


# Format every alive Pokemon with the roles and move evidence that created them.
def format_team_plan_debug(team_plan):
    lines = [
        "Competitive team roles:",
        f"  style={team_plan.style} | reason={team_plan.style_reason}",
    ]
    for pokemon, profile in team_plan.profiles.items():
        role_chunks = [
            f"{role}({profile.role_reasons.get(role, 'detected')})"
            for role in sorted(profile.roles)
        ]
        move_chunks = [
            f"{move_id}={','.join(roles)}"
            for move_id, roles in sorted(profile.move_roles.items())
        ]
        item_id = utilities.get_known_item_id(pokemon) or "unknown"
        lines.append(
            "  "
            f"{get_pokemon_label(pokemon)}: "
            f"roles=[{'; '.join(role_chunks) or 'none'}] | "
            f"stats=spe {profile.speed:.0f}, bulk {profile.bulk:.0f}, "
            f"offense {profile.offense:.0f}, best_damage {profile.best_damage_value:.1f}, "
            f"item {item_id} | "
            f"moves=[{'; '.join(move_chunks) or 'unknown'}]"
        )
    return "\n".join(lines)


# Decide battle phase from remaining Pokemon count.
def get_battle_phase(battle):
    opponent_alive = sum(
        1 for pokemon in battle.opponent_team.values() if not pokemon.fainted
    )
    own_alive = sum(1 for pokemon in battle.team.values() if not pokemon.fainted)
    remaining = max(opponent_alive, own_alive)

    if remaining >= 5:
        return "early"
    if remaining >= 3:
        return "mid"
    return "late"


# Score how important it is to preserve a Pokemon for the chosen team plan.
def get_pokemon_importance(pokemon, team_plan):
    profile = team_plan.profiles.get(pokemon)
    if profile is None:
        return 0.0

    importance = pokemon.current_hp_fraction * 16
    if pokemon in team_plan.win_conditions:
        importance += 28
    if pokemon in team_plan.revenge_killers:
        importance += 16
    if pokemon in team_plan.defensive_pivots:
        importance += 14
    if pokemon in team_plan.hazard_setters and team_plan.style == "hazard_stack":
        importance += 10
    if pokemon in team_plan.screen_setters and team_plan.style == "screens_offense":
        importance += 10
    if pokemon in team_plan.anti_setup_users:
        importance += 8
    if pokemon in team_plan.progress_makers:
        importance += 8
    if "breaker" in profile.roles:
        importance += 12

    return importance


# Build all context values needed by the competitive decision layer.
def build_turn_context(battle, active_first_turn=None):
    plan = analyze_team_plan(battle)
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    if active_first_turn is None:
        active_first_turn = getattr(active, "first_turn", False)
    opponent_threat = utilities.get_opponent_threat_value(opponent, active, battle)
    active_hp = utilities.estimate_current_hp(active)
    best_attack = get_best_available_attack(battle, active_first_turn)
    best_attack_value = (
        score_attack_action_without_context(battle, best_attack, active_first_turn)
        if best_attack is not None
        else 0.0
    )
    best_attack_damage = (
        utilities.estimate_damage_percent(best_attack, active, opponent, battle, True)
        if best_attack is not None
        else 0.0
    )
    emergency = opponent_threat >= active_hp * 0.62
    expected_opponent_switch, expected_switch_reason = get_expected_switch_read(
        battle,
        best_attack,
        best_attack_damage,
    )

    return TurnContext(
        phase=get_battle_phase(battle),
        plan=plan,
        matchup_score=utilities.evaluate_pokemon_matchup(active, opponent, battle),
        opponent_threat=opponent_threat,
        safe_turn=opponent_threat < active_hp * 0.42,
        active_importance=get_pokemon_importance(active, plan),
        opponent_remaining=sum(
            1 for pokemon in battle.opponent_team.values() if not pokemon.fainted
        ),
        own_remaining=sum(1 for pokemon in battle.team.values() if not pokemon.fainted),
        best_attack_value=best_attack_value,
        best_attack_damage=best_attack_damage,
        opponent_hp_percent=opponent.current_hp_fraction * 100,
        expected_opponent_switch=expected_opponent_switch,
        expected_switch_reason=expected_switch_reason,
        emergency=emergency,
        active_first_turn=active_first_turn,
    )


# Find the best attacking move available this turn.
def get_best_available_attack(battle, active_first_turn=None):
    attacks = [move for move in battle.available_moves if is_attacking_move(move)]
    if not attacks:
        return None
    return max(
        attacks,
        key=lambda move: utilities.daniela(
            move,
            battle.active_pokemon,
            battle.opponent_active_pokemon,
            battle,
            True,
            first_turn_override=active_first_turn,
        ),
    )


# Score attacks before TurnContext exists.
def score_attack_action_without_context(battle, move, active_first_turn=None):
    if move is None:
        return 0.0
    return utilities.daniela(
        move,
        battle.active_pokemon,
        battle.opponent_active_pokemon,
        battle,
        True,
        first_turn_override=active_first_turn,
    )


# Estimate if the opponent is likely to switch because their active Pokemon is pressured.
def get_expected_switch_read(battle, best_attack, best_attack_damage):
    opponent = battle.opponent_active_pokemon
    active = battle.active_pokemon
    matchup_score = utilities.evaluate_pokemon_matchup(opponent, active, battle)
    attack_accuracy = get_move_accuracy(best_attack) if best_attack is not None else 1.0

    if (
        opponent.current_hp_fraction <= 0.28
        and best_attack_damage >= 35
        and attack_accuracy >= 0.8
    ):
        return True, "low_hp_and_attack_pressure"
    if not math.isfinite(matchup_score):
        return True, "bad_matchup_score=very_bad"
    if matchup_score >= 28 and battle.opponent_team:
        return True, f"bad_matchup_score={matchup_score:.2f}"
    if (
        best_attack_damage >= opponent.current_hp_fraction * 100 * 1.05
        and attack_accuracy >= 0.9
    ):
        return True, "near_ko_pressure"
    return False, "none"


# Score one move as an attacking action.
def score_attack_action(battle, move, context):
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    damage_percent = utilities.estimate_damage_percent(move, active, opponent, battle, True)
    value = utilities.daniela(
        move,
        active,
        opponent,
        battle,
        True,
        first_turn_override=context.active_first_turn,
    )

    if is_reliable_finisher(battle, move, context, damage_percent):
        value += 42
    if context.phase == "late":
        value += damage_percent * 0.35
    if context.plan.style == "offense":
        value += damage_percent * 0.18
    if core.get_current_type_multiplier(opponent, move) > 1:
        value += 12
    if context.emergency and damage_percent < 35:
        value -= 10
    if move.id in ATTACK_CONDITIONAL_MOVES:
        if context.expected_opponent_switch:
            value -= 70
            value = min(value, 22 if context.emergency else 18)
        elif context.safe_turn and context.opponent_threat < 35:
            value -= 24
    value -= get_attack_risk_penalty(
        move,
        damage_percent,
        opponent.current_hp_fraction * 100,
    )
    if competitive_moves.is_recharge_move(move):
        closes_game = (
            context.opponent_remaining <= 1
            and is_reliable_finisher(battle, move, context, damage_percent)
        )
        if not closes_game:
            value -= 40
            if damage_percent < opponent.current_hp_fraction * 100:
                value -= 15

    return value


# Score a healing action with preservation and role context.
def score_heal_action(battle, move, context):
    active = battle.active_pokemon
    active_hp = active.current_hp_fraction
    value = utilities.get_healing_value(
        move,
        active,
        battle,
        1.0 if context.safe_turn else 0.45,
    )
    if active_hp >= 0.72:
        value -= 36
    elif active_hp >= 0.58 and not context.emergency:
        value -= 18
    if move.id == "rest" and active_hp >= 0.45 and not context.emergency:
        value -= 25
    if context.active_importance >= 30:
        value += 12
    if context.safe_turn:
        value += 8
    if context.phase == "late":
        value += 6
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 35
    if context.emergency and context.opponent_threat >= utilities.estimate_current_hp(active) * 0.9:
        value -= 30
    return value


# Score a hazard action based on team plan and game phase.
def score_hazard_action(battle, move, context):
    value = utilities.get_hazard_setup_value(move, battle)
    if context.plan.style == "hazard_stack":
        value += 18
    if context.phase == "early":
        value += 14
    elif context.phase == "mid":
        value += 4
    else:
        value -= 24
    if not context.safe_turn:
        value -= 18
    if context.expected_opponent_switch:
        value += 12
    if battle.opponent_active_pokemon.current_hp_fraction <= 0.35:
        value -= 16
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 45
    if context.plan.win_conditions and context.phase == "mid":
        value -= 6
    return value


# Score hazard removal by how much our team is being taxed by switching.
def score_hazard_removal_action(battle, move, context):
    if not battle.side_conditions:
        return -20.0

    value = 18 + len(battle.side_conditions) * 12
    active = battle.active_pokemon
    if utilities.get_switch_hazard_penalty(active, battle) >= 18:
        value += 12
    if context.plan.style in {"balance", "screens_offense", "setup_sweep"}:
        value += 8
    if context.safe_turn:
        value += 8
    else:
        value -= 16
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 38
    return value


# Score a setup action as a possible win-condition enabler.
def score_setup_action(battle, move, context):
    active = battle.active_pokemon
    profile = context.plan.profiles.get(active)
    boosts = competitive_moves.get_setup_boosts(move)
    value = utilities.get_setup_stat_value(boosts, active)

    if active in context.plan.win_conditions:
        value += 24
    if context.plan.style == "setup_sweep":
        value += 14
    if context.safe_turn:
        value += 16
    else:
        value -= 24
    if context.opponent_threat >= utilities.estimate_current_hp(active) * 0.55:
        value -= 14
    if context.phase == "late" and profile and "cleaner" not in profile.roles:
        value -= 20
    if active.current_hp_fraction <= 0.45:
        value -= 12
    if context.expected_opponent_switch:
        value += 10
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 38
    for stat, stage in boosts.items():
        current_stage = active.boosts.get(stat, 0)
        if current_stage >= 4:
            value -= 28
        elif current_stage >= 2:
            value -= 14
        if current_stage + stage > 6:
            value -= 18
    return value


# Score status and debuff actions as support for the broader plan.
def score_disruption_action(battle, move, context):
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    if is_attacking_move(move):
        if utilities.get_current_type_multiplier(opponent, move) == 0:
            return float("-inf")
        damage_percent = utilities.estimate_damage_percent(
            move,
            active,
            opponent,
            battle,
            True,
        )
        effect_value = (
            get_direct_disruption_value(move, active, opponent, battle)
            + get_secondary_effect_value(move, active, opponent, battle)
        )
        value = damage_percent * 0.35 + effect_value
        value -= get_attack_risk_penalty(
            move,
            damage_percent,
            opponent.current_hp_fraction * 100,
        ) * 0.5
    else:
        value = utilities.daniela(move, active, opponent, battle, True)
        effect_value = value

    if context.plan.style in {"hazard_stack", "balance"}:
        value += 8
    if utilities.get_effective_speed(opponent, battle) > utilities.get_effective_speed(
        active,
        battle,
    ):
        value += 6
    if context.phase == "late" and opponent.current_hp_fraction <= 0.4:
        value -= 12
    if move.id in competitive_moves.HIGH_VALUE_STATUS_MOVES and opponent.status is None:
        value += 10
    if core.safe_move_attr(move, "status") is not None:
        if opponent.status is not None:
            value -= 48
        if is_status_move_blocked(move, opponent):
            value -= 72
    if context.best_attack_damage >= opponent.current_hp_fraction * 100:
        value -= 32
    if is_attacking_move(move) and effect_value <= 0:
        value -= 16
    return value


# Score screens as team support, not as a selfish single-turn play.
def score_screen_action(battle, move, context):
    value = 28
    if context.plan.style == "screens_offense":
        value += 24
    if context.phase == "early":
        value += 14
    elif context.phase == "mid":
        value += 6
    else:
        value -= 24
    if context.safe_turn:
        value += 10
    else:
        value -= 12
    if context.plan.win_conditions:
        value += 8
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 40
    return value


# Score item control because removing Boots, Leftovers or Choice items creates progress.
def score_item_control_action(battle, move, context):
    value = utilities.daniela(move, battle.active_pokemon, battle.opponent_active_pokemon, battle, True)
    item_value = utilities.get_item_control_value(battle.opponent_active_pokemon)
    value += item_value
    if context.phase in {"early", "mid"}:
        value += 14
    if context.plan.style in {"progress_offense", "balance", "hazard_stack"}:
        value += 10
    if context.expected_opponent_switch:
        value += 8
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 35
    if item_value <= 0 and context.phase == "late":
        value -= 12
    return value


# Score phazing mostly as an answer to setup or as hazard-stack chip.
def score_phazing_action(battle, move, context):
    opponent_boosts = utilities.get_boost_score(battle.opponent_active_pokemon)
    value = utilities.daniela(move, battle.active_pokemon, battle.opponent_active_pokemon, battle, True)
    if opponent_boosts >= 2:
        value += 34
    elif opponent_boosts <= 0:
        value -= 24
    if context.plan.style == "hazard_stack" and battle.opponent_side_conditions:
        value += 12
    if context.phase == "late" and context.opponent_remaining <= 2:
        value -= 20
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 38
    return value


# Score anti-setup moves when the opponent is boosted or likely to snowball.
def score_anti_setup_action(battle, move, context):
    opponent_boosts = utilities.get_boost_score(battle.opponent_active_pokemon)
    opponent_can_snowball = opponent_has_snowball_route(battle.opponent_active_pokemon)
    value = utilities.daniela(move, battle.active_pokemon, battle.opponent_active_pokemon, battle, True)
    if opponent_boosts <= 0 and move.id in {"encore", "haze", "taunt", "topsyturvy"}:
        value -= 30 if not opponent_can_snowball else 14
    if opponent_boosts >= 2:
        value += 42
    elif context.emergency and opponent_can_snowball:
        value += 12
    if move.id in {"taunt", "encore"} and context.safe_turn:
        value += 8
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 34
    return value


# Score cleric moves only when enough team value is actually statused.
def score_cleric_action(battle, move, context):
    statused_allies = [
        pokemon
        for pokemon in battle.team.values()
        if not pokemon.fainted and pokemon.status is not None
    ]
    if not statused_allies:
        return -48

    value = len(statused_allies) * 18
    if any(pokemon in context.plan.win_conditions for pokemon in statused_allies):
        value += 16
    if context.safe_turn:
        value += 8
    else:
        value -= 18
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 36
    return value


# Score scouting/protection when blocking damage or buying recovery is useful.
def score_scout_action(battle, move, context):
    active = battle.active_pokemon
    value = utilities.daniela(move, active, battle.opponent_active_pokemon, battle, True)
    if context.emergency and context.active_importance >= 24:
        value += 14
    if active.current_hp_fraction <= 0.45 and context.opponent_threat > 0:
        value += 8
    if context.phase == "late":
        value -= 8
    if context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        value -= 34
    return value


def get_action_memory_entry(action):
    target = action.move or action.switch
    move_id = getattr(action.move, "id", None)
    switch_id = get_pokemon_label(action.switch) if action.switch is not None else None
    return {
        "kind": action.kind,
        "move_id": move_id,
        "switch_id": switch_id,
        "target": move_id or switch_id or str(target),
    }


def get_recent_action_penalty(action, recent_actions):
    if not recent_actions or action.kind not in REPEAT_SENSITIVE_KINDS:
        return 0.0

    move_id = getattr(action.move, "id", None)
    if move_id is None:
        return 0.0

    last = recent_actions[-1]
    same_as_last = last.get("move_id") == move_id
    same_kind_as_last = last.get("kind") == action.kind
    recent_same_move = sum(1 for item in recent_actions[-5:] if item.get("move_id") == move_id)
    recent_same_kind = sum(1 for item in recent_actions[-4:] if item.get("kind") == action.kind)

    penalty = 0.0
    if action.kind == "scout":
        if same_as_last or same_kind_as_last:
            penalty += 70
        elif recent_same_kind:
            penalty += 35
    elif action.kind == "screen":
        if same_as_last:
            penalty += 60
        elif recent_same_move:
            penalty += 45
    elif action.kind == "heal":
        if same_as_last or same_kind_as_last:
            penalty += 24
        if recent_same_kind >= 2:
            penalty += 18
    elif action.kind == "setup":
        if same_as_last:
            penalty += 34
        elif same_kind_as_last:
            penalty += 18
        if recent_same_move >= 2:
            penalty += 20
    elif action.kind == "anti_setup":
        if same_as_last:
            penalty += 22
        if recent_same_move >= 2:
            penalty += 18
    elif action.kind == "disruption":
        if same_as_last:
            penalty += 18
        if recent_same_move >= 2:
            penalty += 14
    elif action.kind == "cleric":
        if same_kind_as_last:
            penalty += 28
        elif recent_same_move:
            penalty += 20
        if recent_same_move >= 2:
            penalty += 18
    elif action.kind == "hazard":
        if same_as_last and move_id not in {"spikes", "toxicspikes"}:
            penalty += 24

    return penalty


def apply_recent_action_penalties(actions, recent_actions):
    if not recent_actions:
        return actions

    for action in actions:
        if not math.isfinite(action.value):
            continue
        penalty = get_recent_action_penalty(action, recent_actions)
        if penalty <= 0:
            continue
        action.value -= penalty
        action.reason = f"{action.reason}, repeat_penalty={penalty:.0f}"
    return actions


# Score switching as either preservation, revenge killing or defensive pivoting.
def score_switch_action(battle, switch, context, last_switch_from=None):
    active = battle.active_pokemon
    opponent = battle.opponent_active_pokemon
    switch_profile = context.plan.profiles.get(switch) or analyze_pokemon_profile(
        switch,
        battle,
    )
    current_attack_value = utilities.get_best_move_value(
        active,
        opponent,
        battle,
        True,
        first_turn_override=context.active_first_turn,
    )
    switch_matchup = utilities.evaluate_switch_option(switch, battle)
    switch_attack_value = utilities.get_best_move_value(
        switch,
        opponent,
        battle,
        True,
        respect_turn_restrictions=False,
    )
    value = -switch_matchup + switch_attack_value * 0.35

    if context.emergency:
        value += 28
    if context.active_importance >= 30:
        value += 12
    if "revenge_killer" in switch_profile.roles and switch_attack_value >= 50:
        value += 16
    if can_revenge_kill(battle, switch):
        value += 22
    if "wall" in switch_profile.roles and context.plan.style in {"balance", "hazard_stack"}:
        value += 8
    if switch == last_switch_from:
        value -= 24
    if current_attack_value >= 65 and context.safe_turn:
        value -= 28
    if context.best_attack_damage >= opponent.current_hp_fraction * 100:
        value -= 45
    if not context.emergency and switch_attack_value < current_attack_value + 18:
        value -= 12

    return value


# Decide if the active Pokemon is expendable enough to stay in for chip.
def active_can_be_sacrificed(battle, context):
    active = battle.active_pokemon
    profile = context.plan.profiles.get(active)
    if active.current_hp_fraction > 0.28:
        return False
    if context.active_importance >= 24:
        return False
    if profile and {"win_condition", "revenge_killer", "wall"} & profile.roles:
        return False
    return True


# Detect whether a switch can immediately revenge kill the current opponent.
def can_revenge_kill(battle, switch):
    opponent = battle.opponent_active_pokemon
    switch_speed = utilities.get_effective_speed(switch, battle)
    opponent_speed = utilities.get_effective_speed(opponent, battle)
    best_value = utilities.get_best_move_value(
        switch,
        opponent,
        battle,
        True,
        respect_turn_restrictions=False,
    )
    has_priority = any(competitive_moves.is_priority_move(move) for move in get_moves(switch))

    return (switch_speed >= opponent_speed or has_priority) and best_value >= max(
        45,
        opponent.current_hp_fraction * 100,
    )


# Pick the best move for each strategic action type.
def build_move_actions(battle, context):
    actions = []
    for move in battle.available_moves:
        if is_attacking_move(move):
            actions.append(
                CompetitiveAction(
                    "attack",
                    score_attack_action(battle, move, context),
                    move=move,
                    reason="damage_or_ko",
                )
            )
        if is_healing_move(move):
            actions.append(
                CompetitiveAction(
                    "heal",
                    score_heal_action(battle, move, context),
                    move=move,
                    reason="preserve_key_pokemon",
                )
            )
        if is_hazard_move(move):
            actions.append(
                CompetitiveAction(
                    "hazard",
                    score_hazard_action(battle, move, context),
                    move=move,
                    reason="long_term_chip",
                )
            )
        if is_hazard_removal_move(move):
            actions.append(
                CompetitiveAction(
                    "hazard_removal",
                    score_hazard_removal_action(battle, move, context),
                    move=move,
                    reason="clear_our_field",
                )
            )
        if is_setup_move(move):
            actions.append(
                CompetitiveAction(
                    "setup",
                    score_setup_action(battle, move, context),
                    move=move,
                    reason="enable_win_condition",
                )
            )
        if (
            is_disruption_move(move)
            and not competitive_moves.is_anti_setup_move(move)
            and not competitive_moves.is_phazing_move(move)
        ):
            actions.append(
                CompetitiveAction(
                    "disruption",
                    score_disruption_action(battle, move, context),
                    move=move,
                    reason="status_or_debuff",
                )
            )
        if competitive_moves.is_screen_move(move):
            actions.append(
                CompetitiveAction(
                    "screen",
                    score_screen_action(battle, move, context),
                    move=move,
                    reason="team_protection",
                )
            )
        if competitive_moves.is_item_control_move(move):
            item_id = utilities.get_known_item_id(battle.opponent_active_pokemon)
            reason = "permanent_progress"
            if item_id is not None:
                reason = f"{reason}, target_item={item_id}"
            actions.append(
                CompetitiveAction(
                    "item_control",
                    score_item_control_action(battle, move, context),
                    move=move,
                    reason=reason,
                )
            )
        if competitive_moves.is_phazing_move(move):
            actions.append(
                CompetitiveAction(
                    "phazing",
                    score_phazing_action(battle, move, context),
                    move=move,
                    reason="stop_setup_or_stack_chip",
                )
            )
        if competitive_moves.is_anti_setup_move(move):
            actions.append(
                CompetitiveAction(
                    "anti_setup",
                    score_anti_setup_action(battle, move, context),
                    move=move,
                    reason="deny_snowball",
                )
            )
        if competitive_moves.is_cleric_move(move):
            actions.append(
                CompetitiveAction(
                    "cleric",
                    score_cleric_action(battle, move, context),
                    move=move,
                    reason="repair_team_status",
                )
            )
        if competitive_moves.is_scout_move(move):
            actions.append(
                CompetitiveAction(
                    "scout",
                    score_scout_action(battle, move, context),
                    move=move,
                    reason="block_or_scout",
                )
            )

    return actions


# Build possible switch actions for the current turn.
def build_switch_actions(battle, context, last_switch_from=None):
    return [
        CompetitiveAction(
            "switch",
            score_switch_action(battle, switch, context, last_switch_from),
            switch=switch,
            reason="preserve_or_revenge",
        )
        for switch in battle.available_switches
    ]


# Build all legal actions in one place so decision making and debug rankings use
# exactly the same scores.
def build_competitive_actions(battle, context, last_switch_from=None, recent_actions=None):
    actions = build_move_actions(battle, context)
    actions.extend(build_switch_actions(battle, context, last_switch_from))
    return apply_recent_action_penalties(actions, recent_actions)


# Return the strongest action per kind, useful both for logic and readable debug.
def get_best_actions_by_kind(actions):
    best_by_kind = {}
    for action in actions:
        if action.kind not in best_by_kind or action.value > best_by_kind[action.kind].value:
            best_by_kind[action.kind] = action
    return best_by_kind


def get_best_action(actions):
    candidates = [action for action in actions if action is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda action: action.value)


# Format the top candidate actions so bad choices can be diagnosed from logs.
def format_action_debug(actions, limit=8):
    if not actions:
        return "Competitive action ranking: no legal actions"

    lines = ["Competitive action ranking:"]
    for action in sorted(actions, key=lambda item: item.value, reverse=True)[:limit]:
        target = action.move or action.switch
        lines.append(
            "  "
            f"{action.kind}: target={target} | value={action.value:.2f} "
            f"| reason={action.reason}"
        )
    return "\n".join(lines)


# Choose the best forced switch when no move is available.
def choose_forced_switch(battle, context):
    if not battle.available_switches:
        return None
    return max(
        build_switch_actions(battle, context),
        key=lambda action: action.value,
    ).switch


# Choose a competitive action by comparing plan-aware moves and switches.
def choose_competitive_action(battle, context, last_switch_from=None, recent_actions=None):
    actions = build_competitive_actions(
        battle,
        context,
        last_switch_from,
        recent_actions,
    )

    if not actions:
        return CompetitiveAction("random", float("-inf"), reason="no_legal_action")

    best_by_kind = get_best_actions_by_kind(actions)

    best_attack = best_by_kind.get("attack")
    best_switch = best_by_kind.get("switch")
    best_heal = best_by_kind.get("heal")
    best_hazard = best_by_kind.get("hazard")
    best_hazard_removal = best_by_kind.get("hazard_removal")
    best_setup = best_by_kind.get("setup")
    best_disruption = best_by_kind.get("disruption")
    best_screen = best_by_kind.get("screen")
    best_item_control = best_by_kind.get("item_control")
    best_phazing = best_by_kind.get("phazing")
    best_anti_setup = best_by_kind.get("anti_setup")
    best_cleric = best_by_kind.get("cleric")
    best_scout = best_by_kind.get("scout")

    # Tactical guardrail: if we have a strong immediate attack, do not let a
    # long-term plan steal the turn unless it is clearly better.
    if best_attack and context.best_attack_damage >= battle.opponent_active_pokemon.current_hp_fraction * 100:
        best_attack.reason = (
            f"secure_ko damage={context.best_attack_damage:.1f} "
            f"hp={context.opponent_hp_percent:.1f}"
        )
        if is_reliable_finisher(battle, best_attack.move, context, context.best_attack_damage):
            return finalize_selected_action(actions, best_attack)

    # Emergency turns should either switch, revenge kill, or accept a sacrifice
    # for chip. This prevents greedy hazards/setup when the active is about to drop.
    if context.emergency:
        best_attack_or_switch = get_best_action([best_attack, best_switch])
        best_tactical = get_best_action(
            [action for action in actions if action.kind in EMERGENCY_TACTICAL_KINDS]
        )

        opponent_boosts = utilities.get_boost_score(battle.opponent_active_pokemon)
        if (
            best_anti_setup
            and opponent_boosts >= 2
            and best_anti_setup.value >= (best_attack.value if best_attack else 0) + 4
        ):
            best_anti_setup.reason = "emergency_deny_setup"
            return finalize_selected_action(actions, best_anti_setup)
        if best_phazing and best_phazing.value >= (best_attack.value if best_attack else 0) + 4:
            best_phazing.reason = "emergency_force_out_booster"
            return finalize_selected_action(actions, best_phazing)
        if (
            best_tactical
            and best_attack_or_switch
            and best_tactical.kind not in {"attack", "switch"}
            and best_tactical.value >= best_attack_or_switch.value + 8
        ):
            best_tactical.reason = f"emergency_best_{best_tactical.kind}"
            return finalize_selected_action(actions, best_tactical)
        if (
            best_tactical
            and best_attack
            and best_tactical.kind not in {"attack", "switch"}
            and best_attack.value <= 10
            and best_tactical.value > best_attack.value
        ):
            best_tactical.reason = f"emergency_best_{best_tactical.kind}"
            return finalize_selected_action(actions, best_tactical)
        if best_switch and best_switch.value >= (best_attack.value if best_attack else 0) + 10:
            best_switch.reason = "emergency_preserve_or_revenge"
            return finalize_selected_action(actions, best_switch)
        if best_attack and active_can_be_sacrificed(battle, context):
            best_attack.reason = "sacrifice_for_chip"
            return finalize_selected_action(actions, best_attack)
        if best_attack and (
            best_switch is None or best_attack.value >= best_switch.value + 12
        ):
            best_attack.reason = "emergency_no_good_switch"
            return finalize_selected_action(actions, best_attack)
        if best_scout and best_scout.value >= (best_attack.value if best_attack else 0) + 8:
            best_scout.reason = "emergency_scout"
            return finalize_selected_action(actions, best_scout)
        if best_switch and (
            best_attack is None or best_switch.value >= best_attack.value + 4
        ):
            best_switch.reason = "emergency_switch"
            return finalize_selected_action(actions, best_switch)
        if best_attack:
            best_attack.reason = "emergency_best_attack"
            return finalize_selected_action(actions, best_attack)

    # Endgame is mostly about closing KO routes, not investing in delayed value.
    if context.phase == "late":
        endgame_candidates = [
            action
            for action in [
                best_attack,
                best_heal,
                best_setup,
                best_disruption,
                best_item_control,
                best_phazing,
                best_anti_setup,
                best_scout,
                best_hazard_removal,
                best_switch,
            ]
            if action is not None
        ]
        return finalize_selected_action(
            actions,
            max(endgame_candidates, key=lambda action: action.value),
        )

    if best_heal and best_attack and best_heal.value >= best_attack.value + 12:
        return finalize_selected_action(actions, best_heal)

    if (
        best_hazard_removal
        and best_hazard_removal.value >= (best_attack.value if best_attack else 0) + 8
    ):
        return finalize_selected_action(actions, best_hazard_removal)

    if best_cleric and best_cleric.value >= (best_attack.value if best_attack else 0) + 10:
        return finalize_selected_action(actions, best_cleric)

    if (
        best_screen
        and context.safe_turn
        and context.plan.style == "screens_offense"
        and best_screen.value >= (best_attack.value if best_attack else 0) + 8
    ):
        return finalize_selected_action(actions, best_screen)

    if (
        best_setup
        and context.safe_turn
        and best_setup.value >= (best_attack.value if best_attack else 0) + 10
    ):
        return finalize_selected_action(actions, best_setup)

    if (
        best_hazard
        and context.safe_turn
        and context.phase == "early"
        and best_hazard.value >= (best_attack.value if best_attack else 0) + 8
    ):
        return finalize_selected_action(actions, best_hazard)

    if best_anti_setup and best_anti_setup.value >= (best_attack.value if best_attack else 0) + 8:
        return finalize_selected_action(actions, best_anti_setup)

    if best_phazing and best_phazing.value >= (best_attack.value if best_attack else 0) + 8:
        return finalize_selected_action(actions, best_phazing)

    if (
        best_item_control
        and context.phase in {"early", "mid"}
        and best_item_control.value >= (best_attack.value if best_attack else 0) + 8
    ):
        return finalize_selected_action(actions, best_item_control)

    if best_scout and best_scout.value >= (best_attack.value if best_attack else 0) + 12:
        return finalize_selected_action(actions, best_scout)

    if best_disruption and best_disruption.value >= (best_attack.value if best_attack else 0) + 8:
        return finalize_selected_action(actions, best_disruption)

    if best_switch and best_switch.value >= (best_attack.value if best_attack else 0) + 14:
        return finalize_selected_action(actions, best_switch)

    best_action = max(actions, key=lambda action: action.value)

    # Avoid low-value switches when staying in has a useful attack.
    if best_action.kind == "switch":
        if best_attack and best_attack.value >= best_action.value - 6:
            return finalize_selected_action(actions, best_attack)

    return finalize_selected_action(actions, best_action)
