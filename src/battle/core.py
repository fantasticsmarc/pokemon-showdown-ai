from poke_env.battle.move_category import MoveCategory


# Safely compute a move/type multiplier into a Pokemon's current typing.
def get_current_type_multiplier(target_pokemon, type_or_move):
    try:
        return target_pokemon.damage_multiplier(type_or_move)
    except Exception:
        return 1.0


# Read the Pokemon's current defensive types, including Tera and temporary type changes.
def get_current_types(pokemon):
    return (
        [pokemon.type_1] if pokemon.type_2 is None else [pokemon.type_1, pokemon.type_2]
    )


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
