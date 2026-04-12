# Ability effect mappings - abilities that negate or heal from certain move types
ABILITY_NEGATES = {
    "voltabsorb": ["electric"],
    "waterabsorb": ["water"],
    "lightningrod": ["electric"],  # Redirects but effectively nullifies for damage calc
    "stormdrain": ["water"],  # Redirects but effectively nullifies for damage calc
    "flashfire": ["fire"],
    "levitate": ["ground"],
    "sapsipper": ["grass"],
    "motordrive": ["electric"],
    "dryskin": ["fire"],  # Actually does 1.25x damage, but we'll handle specially
    "wellbakedbody": ["fire"],  # Nullifies and raises Defense
    "purifyingsalt": ["water"],  # Reduces damage by 50% (we'll treat as resist)
    "thermalexchange": ["fire"],  # Nullifies and raises Attack
    "eartheater": ["ground"],  # Nullifies ground moves and heals
    "lightning rod": ["electric"],
    "storm drain": ["water"],
}

ABILITY_HEALS = {
    "voltabsorb": ["electric"],
    "waterabsorb": ["water"],
    "flashfire": ["fire"],  # Actually just nullifies, but some interpret as heal effect
    "dryskin": ["water"],  # Heals from water moves
    "eartheater": ["ground"],  # Heals from ground moves
    "raindish": ["water"],  # Heals in rain (situational)
    "icebody": ["ice"],  # Heals in hail (situational)
}

ABILITY_BOOSTS = {
    "flareboost": ["fire"],  # Boosts Fire power when burned
    "toxikboost": ["poison"],  # Boosts Poison power when poisoned
    "guts": ["normal"],  # Boosts Attack when statused (not type-specific but relevant)
    "harvest": ["berry"],  # Can reuse berries (item interaction)
}
