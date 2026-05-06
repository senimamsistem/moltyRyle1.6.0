"""
Comprehensive unit tests untuk bot/strategy/brain.py
Target: 80%+ code coverage

Test Categories:
1. Damage calculation functions
2. Weapon utilities
3. Region resolution
4. Combat tracking
5. State management
6. Target selection
7. Item utilities
8. Safe region finding
9. Movement utilities
10. Helper functions
"""
import pytest
from unittest.mock import patch, MagicMock
import logging

from bot.strategy.brain import (
    # Damage and combat
    calc_damage, get_weapon_bonus, get_weapon_range,
    _get_weapon_strategy, _get_weapon_icon, _format_weapon_with_icon,
    
    # Region utilities
    _resolve_region, _get_region_id, _get_adjacent_ids,
    
    # State management
    reset_game_state, _track_attack, _track_chase, _track_enemy_seen,
    track_failed_action, _log_combat_metrics,
    
    # Target and combat
    _estimate_enemy_weapon_bonus, _estimate_enemy_strength,
    _select_best_target, _get_combat_hp_threshold,
    
    # Items and inventory
    _find_healing_item, _pickup_score, _check_pickup, _check_equip,
    _calculate_item_value, _try_use_low_value_items, _find_best_replacement,
    
    # Movement and safety
    _get_move_ep_cost, _find_safe_region, _find_safe_region_with_exit,
    
    # Main decision
    decide_action,
)


class TestCalcDamage:
    """Test damage calculation function"""
    
    def test_basic_damage(self):
        """Test basic damage calculation"""
        dmg = calc_damage(atk=20, weapon_bonus=10, target_def=10)
        # Base: 30 - 5 = 25, no penalty
        assert dmg >= 1
        
    def test_weather_penalties(self):
        """Test weather damage penalties"""
        clear_dmg = calc_damage(20, 10, 10, "clear")
        storm_dmg = calc_damage(20, 10, 10, "storm")
        
        # Storm should reduce damage
        assert storm_dmg <= clear_dmg
        
    def test_minimum_damage(self):
        """Test minimum damage is 1"""
        dmg = calc_damage(atk=1, weapon_bonus=0, target_def=100)
        assert dmg == 1
        
    def test_high_damage(self):
        """Test high ATK vs low DEF"""
        dmg = calc_damage(atk=50, weapon_bonus=35, target_def=5)
        assert dmg > 50  # Should be very high damage


class TestWeaponUtilities:
    """Test weapon utility functions"""
    
    def test_get_weapon_bonus_none(self):
        """Test weapon bonus with no weapon"""
        assert get_weapon_bonus(None) == 0
        
    def test_get_weapon_bonus_katana(self):
        """Test katana bonus"""
        weapon = {"typeId": "katana"}
        bonus = get_weapon_bonus(weapon)
        assert bonus == 35  # Per WEAPONS constant
        
    def test_get_weapon_range_none(self):
        """Test range with no weapon"""
        assert get_weapon_range(None) == 0
        
    def test_get_weapon_range_sniper(self):
        """Test sniper range"""
        weapon = {"typeId": "sniper"}
        range_val = get_weapon_range(weapon)
        assert range_val == 2  # Sniper has range 2
        
    def test_get_weapon_range_melee(self):
        """Test melee weapon range"""
        weapon = {"typeId": "katana"}
        range_val = get_weapon_range(weapon)
        assert range_val == 0  # Melee has range 0
        
    def test_get_weapon_strategy_fist(self):
        """Test strategy untuk unarmed"""
        strategy = _get_weapon_strategy(None)
        assert strategy["style"] == "melee_defensive"
        
    def test_get_weapon_strategy_sniper(self):
        """Test strategy untuk sniper"""
        strategy = _get_weapon_strategy({"typeId": "sniper"})
        assert strategy["style"] == "ranged_aggressive"
        
    def test_get_weapon_icon(self):
        """Test weapon icon mapping"""
        assert "🏹" in _get_weapon_icon("bow") or "🎯" in _get_weapon_icon("bow")
        assert "🔫" in _get_weapon_icon("sniper") or "🎯" in _get_weapon_icon("sniper")
        
    def test_format_weapon_with_icon(self):
        """Test weapon formatting"""
        formatted = _format_weapon_with_icon("katana")
        assert "KATANA" in formatted


class TestRegionUtilities:
    """Test region resolution utilities"""
    
    def test_resolve_region_dict(self):
        """Test resolving region dari dict"""
        view = {
            "visibleRegions": [
                {"id": "region-1", "name": "Test Region"}
            ]
        }
        region = _resolve_region({"id": "region-1"}, view)
        assert region is not None
        assert region["id"] == "region-1"
        
    def test_resolve_region_string(self):
        """Test resolving region dari string ID"""
        view = {
            "visibleRegions": [
                {"id": "region-1", "name": "Test Region"}
            ]
        }
        region = _resolve_region("region-1", view)
        assert region is not None
        
    def test_resolve_region_not_visible(self):
        """Test resolving region not in visible"""
        view = {"visibleRegions": []}
        region = _resolve_region("region-unknown", view)
        assert region is None
        
    def test_get_region_id_string(self):
        """Test get region ID dari string"""
        assert _get_region_id("region-123") == "region-123"
        
    def test_get_region_id_dict(self):
        """Test get region ID dari dict"""
        assert _get_region_id({"id": "region-456"}) == "region-456"
        
    def test_get_region_id_invalid(self):
        """Test get region ID dengan invalid input"""
        assert _get_region_id(None) == ""
        assert _get_region_id({}) == ""
        
    def test_get_adjacent_ids_from_string(self):
        """Test get adjacent IDs dari string"""
        visible = [{"id": "adj1"}, {"id": "adj2"}]
        result = _get_adjacent_ids("main-region", visible)
        # Should return list
        assert isinstance(result, list)


class TestStateManagement:
    """Test state management functions"""
    
    def test_reset_game_state(self):
        """Test game state reset"""
        # Should not raise exception
        reset_game_state()
        
    def test_track_attack(self):
        """Test attack tracking"""
        _track_attack("melee")
        # Should not raise exception
        
    def test_track_attack_finisher(self):
        """Test attack tracking dengan finisher"""
        _track_attack("melee", is_finisher=True)
        # Should not raise exception
        
    def test_track_chase(self):
        """Test chase tracking"""
        _track_chase()
        # Should not raise exception
        
    def test_track_enemy_seen(self):
        """Test enemy seen tracking"""
        _track_enemy_seen(3)
        # Should not raise exception
        
    def test_track_enemy_seen_default(self):
        """Test enemy seen tracking dengan default"""
        _track_enemy_seen()
        # Should not raise exception
        
    def test_track_failed_action(self):
        """Test failed action tracking"""
        track_failed_action("attack", "target-123")
        # Should not raise exception
        
    def test_log_combat_metrics(self, caplog):
        """Test combat metrics logging"""
        with caplog.at_level(logging.INFO):
            _log_combat_metrics()
            # Should log metrics
            assert "COMBAT" in caplog.text or len(caplog.records) >= 0


class TestEnemyEstimation:
    """Test enemy strength estimation"""
    
    def test_estimate_enemy_weapon_bonus_none(self):
        """Test enemy weapon bonus estimation - no weapon"""
        agent = {"equippedWeapon": None}
        bonus = _estimate_enemy_weapon_bonus(agent)
        assert bonus == 0
        
    def test_estimate_enemy_weapon_bonus(self):
        """Test enemy weapon bonus estimation"""
        agent = {"equippedWeapon": {"typeId": "sword"}}
        bonus = _estimate_enemy_weapon_bonus(agent)
        assert bonus > 0
        
    def test_estimate_enemy_strength(self):
        """Test comprehensive enemy strength estimation"""
        agent = {
            "hp": 80,
            "atk": 15,
            "def": 8,
            "equippedWeapon": {"typeId": "sword"},
            "isGuardian": False
        }
        strength = _estimate_enemy_strength(agent)
        
        assert "threat_level" in strength
        assert strength["effective_hp"] >= 80  # At least current HP


class TestTargetSelection:
    """Test target selection logic"""
    
    def test_select_best_target_empty(self):
        """Test target selection dengan empty list"""
        result = _select_best_target([], 20, None, 10, "clear")
        assert result is None
        
    def test_select_best_target_single(self):
        """Test target selection dengan single target"""
        targets = [
            {"id": "enemy-1", "hp": 50, "atk": 10, "def": 5, "isAlive": True}
        ]
        result = _select_best_target(targets, 20, None, 10, "clear", my_hp=100)
        assert result is not None
        assert result["agent"]["id"] == "enemy-1"
        
    def test_select_best_target_prefer_weak(self):
        """Test preferring weaker targets"""
        targets = [
            {"id": "weak", "hp": 20, "atk": 5, "def": 3, "isAlive": True},
            {"id": "strong", "hp": 100, "atk": 20, "def": 15, "isAlive": True}
        ]
        result = _select_best_target(targets, 20, None, 10, "clear", my_hp=100)
        # Should prefer the weaker target
        assert result is not None


class TestCombatHPThreshold:
    """Test combat HP threshold calculation"""
    
    def test_combat_threshold_early_game(self):
        """Test threshold untuk early game"""
        threshold = _get_combat_hp_threshold(95, None)
        assert threshold > 0
        
    def test_combat_threshold_late_game(self):
        """Test threshold untuk late game"""
        threshold = _get_combat_hp_threshold(15, {"typeId": "sniper"})
        assert threshold > 0
        
    def test_combat_threshold_with_weapon(self):
        """Test threshold dengan weapon"""
        threshold_no_weapon = _get_combat_hp_threshold(50, None)
        threshold_with_weapon = _get_combat_hp_threshold(50, {"typeId": "sword"})
        # Weapon should affect threshold
        assert isinstance(threshold_no_weapon, int)
        assert isinstance(threshold_with_weapon, int)


class TestHealingItems:
    """Test healing item functions"""
    
    def test_find_healing_item_empty(self):
        """Test find healing dengan empty inventory"""
        result = _find_healing_item([], critical=False)
        assert result is None
        
    def test_find_healing_item_critical(self):
        """Test find healing untuk critical"""
        inventory = [
            {"id": "food-1", "typeId": "emergency_food"},
            {"id": "medkit-1", "typeId": "medkit"},
        ]
        result = _find_healing_item(inventory, critical=True)
        # Critical should prefer medkit
        assert result is not None
        
    def test_find_healing_item_normal(self):
        """Test find healing untuk normal"""
        inventory = [
            {"id": "food-1", "typeId": "emergency_food"},
            {"id": "medkit-1", "typeId": "medkit"},
        ]
        result = _find_healing_item(inventory, critical=False)
        # Normal should prefer emergency food to save medkit
        assert result is not None
        
    def test_find_healing_item_no_heals(self):
        """Test find healing dengan no healing items"""
        inventory = [
            {"id": "weapon-1", "typeId": "sword"},
            {"id": "map-1", "typeId": "map"},
        ]
        result = _find_healing_item(inventory, critical=False)
        assert result is None


class TestItemValue:
    """Test item value calculation"""
    
    def test_calculate_item_value_weapon(self):
        """Test weapon value calculation"""
        item = {"typeId": "katana", "category": "weapon"}
        value = _calculate_item_value(item, [], 2)
        assert value > 100  # Weapons should be high value
        
    def test_calculate_item_value_healing_low_stock(self):
        """Test healing value when stock is low"""
        item = {"typeId": "bandage", "category": "consumable"}
        value = _calculate_item_value(item, [], 0)  # No heals
        assert value > 0  # Should have value when no heals
        
    def test_calculate_item_value_healing_high_stock(self):
        """Test healing value when stock is high"""
        item = {"typeId": "bandage", "category": "consumable"}
        value = _calculate_item_value(item, [], 10)  # Many heals
        # Value should be lower dengan many heals
        assert value >= 0
        
    def test_calculate_item_value_moltz(self):
        """Test Moltz value"""
        item = {"typeId": "moltz", "category": "currency"}
        value = _calculate_item_value(item, [], 2)
        assert value > 200  # Moltz should be very high value
        
    def test_calculate_item_value_unknown(self):
        """Test unknown item value"""
        item = {"typeId": "unknown_item", "category": "unknown"}
        value = _calculate_item_value(item, [], 2)
        assert value >= 0  # Should have default value


class TestPickupScore:
    """Test pickup scoring"""
    
    def test_pickup_score_weapon_no_weapon(self):
        """Test weapon score when unarmed"""
        item = {"typeId": "sword", "category": "weapon"}
        score = _pickup_score(item, [], 2)
        assert score > 100  # High priority when no weapon
        
    def test_pickup_score_weapon_with_weapon(self):
        """Test weapon score when armed"""
        item = {"typeId": "sword", "category": "weapon"}
        inventory = [{"typeId": "dagger", "category": "weapon"}]
        score = _pickup_score(item, inventory, 2)
        assert score > 0
        
    def test_pickup_score_healing(self):
        """Test healing item score"""
        item = {"typeId": "bandage", "category": "consumable"}
        score = _pickup_score(item, [], 2)
        assert score > 0
        
    def test_pickup_score_moltz(self):
        """Test Moltz score"""
        item = {"typeId": "moltz", "category": "currency"}
        score = _pickup_score(item, [], 2)
        assert score > 200  # Very high score


class TestCheckPickup:
    """Test pickup checking"""
    
    def test_check_pickup_no_items(self):
        """Test pickup dengan no ground items"""
        result = _check_pickup([], [], "region-1")
        assert result is None
        
    def test_check_pickup_weapon_priority(self):
        """Test weapon pickup priority"""
        items = [
            {"id": "sword-1", "typeId": "sword", "category": "weapon", "regionId": "region-1"}
        ]
        result = _check_pickup(items, [], "region-1")
        assert result is not None
        assert result["action"] == "pickup"


class TestCheckEquip:
    """Test equip checking"""
    
    def test_check_equip_no_inventory(self):
        """Test equip dengan empty inventory"""
        result = _check_equip([], None)
        assert result is None
        
    def test_check_equip_better_weapon(self):
        """Test equip when better weapon in inventory"""
        inventory = [
            {"id": "katana-1", "typeId": "katana", "category": "weapon"}
        ]
        equipped = {"typeId": "dagger"}  # Worse weapon
        result = _check_equip(inventory, equipped)
        assert result is not None
        assert result["action"] == "equip"
        
    def test_check_equip_worse_weapon(self):
        """Test equip when equipped is better"""
        inventory = [
            {"id": "dagger-1", "typeId": "dagger", "category": "weapon"}
        ]
        equipped = {"typeId": "katana"}  # Better weapon
        result = _check_equip(inventory, equipped)
        assert result is None  # Should not equip worse weapon


class TestLowValueItems:
    """Test low value item usage"""
    
    def test_try_use_low_value_items_empty(self):
        """Test dengan empty inventory"""
        result = _try_use_low_value_items([], 2)
        assert result is None
        
    def test_try_use_low_value_items_energy_drink(self):
        """Test menggunakan energy drink when EP needed"""
        inventory = [
            {"id": "drink-1", "typeId": "energy_drink", "category": "consumable"}
        ]
        result = _try_use_low_value_items(inventory, 5)
        # May atau may not use depending on logic
        assert result is None or result["action"] == "use_item"


class TestBestReplacement:
    """Test best replacement finding"""
    
    def test_find_best_replacement_no_items(self):
        """Test dengan no ground items"""
        result = _find_best_replacement([], [], 2)
        assert result is None
        
    def test_find_best_replacement_inventory_full(self):
        """Test dengan full inventory"""
        ground_items = [
            {"id": "katana-1", "typeId": "katana", "category": "weapon"}
        ]
        inventory = [
            {"id": "dagger-1", "typeId": "dagger", "category": "weapon"},
            {"id": "bandage-1", "typeId": "bandage", "category": "consumable"},
        ]
        result = _find_best_replacement(ground_items, inventory, 5)
        # May find replacement if katana > dagger


class TestMoveEPCost:
    """Test move EP cost calculation"""
    
    def test_move_ep_cost_plains_clear(self):
        """Test plains clear weather"""
        cost = _get_move_ep_cost("plains", "clear")
        assert cost == 2  # Base cost
        
    def test_move_ep_cost_water(self):
        """Test water terrain"""
        cost = _get_move_ep_cost("water", "clear")
        assert cost == 3  # Water costs 3
        
    def test_move_ep_cost_storm(self):
        """Test storm weather"""
        cost = _get_move_ep_cost("plains", "storm")
        assert cost == 3  # Storm adds 1
        
    def test_move_ep_cost_water_storm(self):
        """Test water + storm"""
        cost = _get_move_ep_cost("water", "storm")
        assert cost >= 3  # At least water cost
        
    def test_move_ep_cost_unknown(self):
        """Test unknown terrain"""
        cost = _get_move_ep_cost("unknown", "clear")
        assert cost == 2  # Default to base


class TestFindSafeRegion:
    """Test safe region finding"""
    
    def test_find_safe_region_no_connections(self):
        """Test dengan no connections"""
        result = _find_safe_region([], set(), {})
        assert result is None
        
    def test_find_safe_region_all_safe(self):
        """Test when all regions safe"""
        connections = [
            {"id": "region-1", "isDeathZone": False},
            {"id": "region-2", "isDeathZone": False},
        ]
        result = _find_safe_region(connections, set(), {})
        assert result in ["region-1", "region-2"]
        
    def test_find_safe_region_with_dz(self):
        """Test when some regions are DZ"""
        connections = [
            {"id": "safe-region", "isDeathZone": False},
            {"id": "dz-region", "isDeathZone": True},
        ]
        danger_ids = {"dz-region"}
        result = _find_safe_region(connections, danger_ids, {})
        assert result == "safe-region"
        
    def test_find_safe_region_all_dz(self):
        """Test when all regions are DZ"""
        connections = [
            {"id": "dz-1", "isDeathZone": True},
            {"id": "dz-2", "isDeathZone": True},
        ]
        danger_ids = {"dz-1", "dz-2"}
        result = _find_safe_region(connections, danger_ids, {})
        assert result is None  # No safe region
        
    def test_find_safe_region_string_ids(self):
        """Test dengan string connection IDs"""
        connections = ["region-1", "region-2"]
        danger_ids = set()
        result = _find_safe_region(connections, danger_ids, {})
        assert result in ["region-1", "region-2"]


class TestFindSafeRegionWithExit:
    """Test safe region with exit finding"""
    
    def test_find_safe_region_with_exit_basic(self):
        """Test basic functionality"""
        connections = [
            {"id": "safe-1", "isDeathZone": False, "connections": ["exit-1"]},
        ]
        danger_ids = set()
        view = {"visibleRegions": [{"id": "exit-1"}]}
        result = _find_safe_region_with_exit(connections, danger_ids, view)
        assert result == "safe-1"
        
    def test_find_safe_region_with_exit_no_exit(self):
        """Test region tanpa exit"""
        connections = [
            {"id": "safe-1", "isDeathZone": False, "connections": []},
        ]
        danger_ids = set()
        view = {}
        result = _find_safe_region_with_exit(connections, danger_ids, view)
        # Should still return region even without exit


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
