"""
Unit tests untuk combat decision logic
"""
import pytest
from bot.strategy.brain import (
    calc_damage, get_weapon_bonus, get_weapon_range,
    _get_weapon_strategy, _select_weakest,
    WEAPONS, WEAPON_STRATEGIES
)

# Note: _should_engage_enemy and _should_flee_from_enemy were refactored into decide_action logic


class TestDamageCalculation:
    """Test suite untuk damage formula"""
    
    def test_calc_damage_basic(self):
        """Test basic damage calculation"""
        # ATK=15, bonus=20 (sword), DEF=10
        damage = calc_damage(15, 20, 10)
        # Base = 15 + 20 - 5 = 30
        assert damage == 30
        
    def test_calc_damage_minimum_one(self):
        """Damage minimum adalah 1"""
        damage = calc_damage(1, 0, 100)
        assert damage == 1
        
    def test_calc_damage_weather_penalty(self):
        """Test weather damage penalties"""
        base_damage = calc_damage(20, 20, 10, "clear")
        rain_damage = calc_damage(20, 20, 10, "rain")
        storm_damage = calc_damage(20, 20, 10, "storm")
        
        assert rain_damage < base_damage  # -5%
        assert storm_damage < rain_damage  # -15%
        
    @pytest.mark.parametrize("weapon_type,expected_bonus,expected_range", [
        ("fist", 0, 0),
        ("dagger", 10, 0),
        ("sword", 20, 0),
        ("katana", 35, 0),
        ("bow", 5, 1),
        ("pistol", 10, 1),
        ("sniper", 28, 2),
    ])
    def test_weapon_stats(self, weapon_type, expected_bonus, expected_range):
        """Test weapon stats dictionary"""
        assert WEAPONS[weapon_type]["bonus"] == expected_bonus
        assert WEAPONS[weapon_type]["range"] == expected_range


class TestWeaponStrategy:
    """Test suite untuk weapon-specific strategies"""
    
    @pytest.mark.parametrize("weapon_type", ["sniper", "katana", "sword", "dagger", "pistol", "bow", "fist"])
    def test_all_weapons_have_strategy(self, weapon_type):
        """All weapons must have strategy config"""
        strategy = _get_weapon_strategy({"typeId": weapon_type})
        assert strategy is not None
        assert "style" in strategy
        assert "min_hp_threshold" in strategy
        
    def test_sniper_aggressive(self):
        """Sniper should have aggressive strategy"""
        strategy = _get_weapon_strategy({"typeId": "sniper"})
        assert strategy["style"] == "ranged_aggressive"
        assert strategy["range"] == 2
        assert strategy["flee_threshold"] == 0.1  # Low flee chance
        
    def test_katana_melee(self):
        """Katana should have melee aggressive"""
        strategy = _get_weapon_strategy({"typeId": "katana"})
        assert strategy["style"] == "melee_aggressive"
        assert strategy["range"] == 0
        assert strategy["engagement_range"] == 0
        
    def test_fist_defensive(self):
        """Fist should be very defensive"""
        strategy = _get_weapon_strategy({"typeId": "fist"})
        assert strategy["style"] == "melee_defensive"
        assert strategy["min_hp_threshold"] == 80
        assert strategy["flee_threshold"] == 0.8  # High flee chance
        
    def test_null_weapon_returns_fist(self):
        """None weapon should return fist strategy"""
        strategy = _get_weapon_strategy(None)
        assert strategy == WEAPON_STRATEGIES["fist"]
        
    def test_weapon_bonus_extraction(self):
        """Test getting bonus from equipped weapon"""
        assert get_weapon_bonus({"typeId": "katana"}) == 35
        assert get_weapon_bonus({"typeId": "sniper"}) == 28
        assert get_weapon_bonus(None) == 0
        
    def test_weapon_range_extraction(self):
        """Test getting range from equipped weapon"""
        assert get_weapon_range({"typeId": "sniper"}) == 2
        assert get_weapon_range({"typeId": "sword"}) == 0
        assert get_weapon_range(None) == 0


class TestTargetSelection:
    """Test suite untuk target selection"""
    
    def test_select_weakest(self):
        """Should select enemy dengan HP terendah"""
        enemies = [
            {"id": "e1", "hp": 80, "isAlive": True},
            {"id": "e2", "hp": 30, "isAlive": True},
            {"id": "e3", "hp": 50, "isAlive": True},
        ]
        weakest = _select_weakest(enemies)
        assert weakest["id"] == "e2"
        assert weakest["hp"] == 30
        
    def test_select_weakest_empty(self):
        """Should return None untuk empty list"""
        assert _select_weakest([]) is None
        
    def test_select_weakest_prioritizes_low_hp(self):
        """Should correctly identify lowest HP"""
        enemies = [
            {"id": "e1", "hp": 10, "isAlive": True},
            {"id": "e2", "hp": 100, "isAlive": True},
            {"id": "e3", "hp": 11, "isAlive": True},
        ]
        weakest = _select_weakest(enemies)
        assert weakest["id"] == "e1"


class TestCombatDecision:
    """Test suite untuk engage/flee decisions - REFACTORED
    
    Note: _should_engage_enemy and _should_flee_from_enemy functions were
    integrated into the main decide_action function. These tests are kept
    as documentation but marked to be updated with integration tests.
    """
    
    @pytest.mark.skip(reason="Function refactored into decide_action - needs integration test")
    def test_should_engage_weaker_enemy(self, sample_enemy_agent):
        """Should engage enemy yang lebih lemah"""
        pass
        
    @pytest.mark.skip(reason="Function refactored into decide_action - needs integration test")
    def test_should_flee_stronger_enemy(self, sample_enemy_agent):
        """Should flee dari enemy kuat dengan HP rendah"""
        pass
        
    @pytest.mark.skip(reason="Function refactored into decide_action - needs integration test")
    def test_should_engage_finisher(self):
        """Should engage enemy dengan very low HP (finisher)"""
        pass


class TestWeaponPriorities:
    """Test suite untuk weapon priority system"""
    
    def test_weapon_priority_order(self):
        """Weapon priority list should be in correct order"""
        from bot.strategy.brain import WEAPON_PRIORITY
        
        expected = ["katana", "sniper", "sword", "pistol", "dagger", "bow", "fist"]
        assert WEAPON_PRIORITY == expected
        
    def test_katana_highest_priority(self):
        """Katana should be highest priority"""
        assert WEAPON_PRIORITY[0] == "katana"
        
    def test_sniper_second_priority(self):
        """Sniper should be second priority"""
        assert WEAPON_PRIORITY[1] == "sniper"
