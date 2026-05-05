"""
Strategy Constants - Shared definitions untuk avoid circular imports
"""

# Weapon stats from combat-items.md
WEAPONS = {
    "fist": {"bonus": 0, "range": 0},
    "dagger": {"bonus": 10, "range": 0},
    "sword": {"bonus": 20, "range": 0},
    "katana": {"bonus": 35, "range": 0},
    "bow": {"bonus": 5, "range": 1},
    "pistol": {"bonus": 10, "range": 1},
    "sniper": {"bonus": 28, "range": 2},
}

WEAPON_PRIORITY = ["katana", "sniper", "sword", "pistol", "dagger", "bow", "fist"]

# Recovery items
RECOVERY_ITEMS = {
    "medkit": 50, "bandage": 30, "emergency_food": 20,
    "energy_drink": 0,
}

# Weather combat penalty per game-systems.md
WEATHER_COMBAT_PENALTY = {
    "clear": 0.0,
    "rain": 0.05,
    "fog": 0.10,
    "storm": 0.15,
}

# Weapon-Specific Strategy Configurations
WEAPON_STRATEGIES = {
    "sniper": {
        "range": 2,
        "damage": 30,
        "style": "ranged_aggressive",
        "engagement_range": 2,
        "min_hp_threshold": 20,
        "flee_threshold": 0.1,
        "finisher_threshold": 40,
        "priority_targets": "any",
        "movement_style": "kiting",
        "combat_preference": "offensive",
    },
    "katana": {
        "range": 0,
        "damage": 25,
        "style": "melee_aggressive",
        "engagement_range": 0,
        "min_hp_threshold": 40,
        "flee_threshold": 0.3,
        "finisher_threshold": 35,
        "priority_targets": "weaker",
        "movement_style": "closing",
        "combat_preference": "aggressive",
    },
    "sword": {
        "range": 0,
        "damage": 20,
        "style": "melee_balanced",
        "engagement_range": 0,
        "min_hp_threshold": 50,
        "flee_threshold": 0.4,
        "finisher_threshold": 45,
        "priority_targets": "balanced",
        "movement_style": "tactical",
        "combat_preference": "balanced",
    },
    "dagger": {
        "range": 0,
        "damage": 15,
        "style": "melee_fast",
        "engagement_range": 0,
        "min_hp_threshold": 60,
        "flee_threshold": 0.6,
        "finisher_threshold": 55,
        "priority_targets": "finishers",
        "movement_style": "hit_and_run",
        "combat_preference": "opportunistic",
    },
    "pistol": {
        "range": 1,
        "damage": 18,
        "style": "ranged_balanced",
        "engagement_range": 1,
        "min_hp_threshold": 45,
        "flee_threshold": 0.4,
        "finisher_threshold": 50,
        "priority_targets": "balanced",
        "movement_style": "positioning",
        "combat_preference": "tactical",
    },
    "bow": {
        "range": 1,
        "damage": 12,
        "style": "ranged_defensive",
        "engagement_range": 1,
        "min_hp_threshold": 55,
        "flee_threshold": 0.5,
        "finisher_threshold": 60,
        "priority_targets": "finishers",
        "movement_style": "kiting",
        "combat_preference": "defensive",
    },
    "fist": {
        "range": 0,
        "damage": 5,
        "style": "melee_defensive",
        "engagement_range": 0,
        "min_hp_threshold": 80,
        "flee_threshold": 0.8,
        "finisher_threshold": 70,
        "priority_targets": "finishers",
        "movement_style": "evasive",
        "combat_preference": "defensive",
    }
}

# Item priority for pickup
ITEM_PRIORITY = {
    "rewards": 300,
    "katana": 120, "sniper": 115, "sword": 110, "pistol": 105,
    "dagger": 100, "bow": 95,
    "medkit": 70, "bandage": 65, "emergency_food": 60, "energy_drink": 58,
    "binoculars": 55,
    "map": 52,
    "megaphone": 0,
    "moltz": 10,
}
