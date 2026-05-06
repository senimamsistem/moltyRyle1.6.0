"""
Unit tests untuk Terrain Mastery System
"""
import pytest
from bot.strategy.terrain_master import (
    TerrainMaster, TerrainBonus,
    get_terrain_advantage, recommend_terrain_for_weapon,
    should_change_terrain, get_weapon_terrain_summary
)


class TestTerrainBonus:
    """Test TerrainBonus dataclass"""
    
    def test_creation(self):
        bonus = TerrainBonus(
            terrain="forest",
            weapon_type="katana",
            attack_multiplier=1.15,
            defense_multiplier=1.0,
            accuracy_multiplier=1.0,
            description="Katana excels di forest"
        )
        
        assert bonus.terrain == "forest"
        assert bonus.weapon_type == "katana"
        assert bonus.attack_multiplier == 1.15


class TestTerrainMaster:
    """Test TerrainMaster class"""
    
    def test_initialization(self):
        master = TerrainMaster()
        assert master.matrix is not None
        assert "forest" in master.matrix
        assert "katana" in master.matrix["forest"]
    
    def test_get_terrain_bonus_known(self):
        master = TerrainMaster()
        
        # Test known terrain dan weapon
        bonus = master.get_terrain_bonus("forest", "katana")
        assert bonus.terrain == "forest"
        assert bonus.weapon_type == "katana"
        assert bonus.attack_multiplier == 1.15  # Katana bonus di forest
        assert "excels" in bonus.description.lower()
    
    def test_get_terrain_bonus_unknown_terrain(self):
        master = TerrainMaster()
        
        # Test unknown terrain - should return default
        bonus = master.get_terrain_bonus("unknown_terrain", "katana")
        assert bonus.attack_multiplier == 1.0  # Default
        assert bonus.defense_multiplier == 1.0
        assert bonus.accuracy_multiplier == 1.0
    
    def test_get_terrain_bonus_unknown_weapon(self):
        master = TerrainMaster()
        
        # Test unknown weapon - should return default
        bonus = master.get_terrain_bonus("forest", "unknown_weapon")
        assert bonus.attack_multiplier == 1.0  # Default
    
    def test_calculate_combat_advantage_katana_vs_sniper_forest(self):
        master = TerrainMaster()
        
        # Katana should have advantage vs sniper di forest
        result = master.calculate_combat_advantage(
            our_weapon="katana",
            enemy_weapon="sniper",
            terrain="forest",
            our_hp=100,
            enemy_hp=100
        )
        
        # Katana should have positive advantage di forest
        assert result["our_advantage"] > 0
        assert result["recommendation"] == "fight"
        assert result["our_bonus"]["attack"] == 1.15
        assert result["enemy_bonus"]["attack"] == 0.60  # Sniper hindered di forest
    
    def test_calculate_combat_advantage_sniper_vs_katana_plains(self):
        master = TerrainMaster()
        
        # Sniper should have advantage vs katana di plains
        result = master.calculate_combat_advantage(
            our_weapon="sniper",
            enemy_weapon="katana",
            terrain="plains",
            our_hp=100,
            enemy_hp=100
        )
        
        assert result["our_advantage"] > 0
        assert result["recommendation"] == "fight"
        assert result["our_bonus"]["attack"] == 1.20  # Sniper bonus di plains
    
    def test_calculate_combat_advantage_sniper_disadvantage_forest(self):
        master = TerrainMaster()
        
        # Sniper should have disadvantage vs katana di forest
        result = master.calculate_combat_advantage(
            our_weapon="sniper",
            enemy_weapon="katana",
            terrain="forest",
            our_hp=100,
            enemy_hp=100
        )
        
        assert result["our_advantage"] < 0
        assert result["recommendation"] == "avoid"
    
    def test_recommend_optimal_terrain_sniper(self):
        master = TerrainMaster()
        
        # Sniper should prefer plains dan mountain
        terrains = ["forest", "plains", "mountain", "water", "urban"]
        recommendations = master.recommend_optimal_terrain("sniper", terrains)
        
        # Should return sorted list
        assert len(recommendations) == 5
        
        # Plains atau mountain should be top
        top_terrain = recommendations[0][0]
        assert top_terrain in ["plains", "mountain"]
        
        # Water should be near bottom
        water_score = next(score for terrain, score in recommendations if terrain == "water")
        assert water_score < 0.7  # Severe penalty di water
    
    def test_recommend_optimal_terrain_katana(self):
        master = TerrainMaster()
        
        # Katana should prefer forest dan urban
        terrains = ["forest", "plains", "mountain", "water", "urban"]
        recommendations = master.recommend_optimal_terrain("katana", terrains)
        
        # Forest atau urban should be top
        top_terrain = recommendations[0][0]
        assert top_terrain in ["forest", "urban"]
    
    def test_get_favorable_terrains_sniper(self):
        master = TerrainMaster()
        
        favorable = master.get_favorable_terrains("sniper")
        
        # Sniper should find plains dan mountain favorable
        assert "plains" in favorable
        assert "mountain" in favorable
        
        # Forest dan water should NOT be favorable
        assert "forest" not in favorable
        assert "water" not in favorable
    
    def test_get_unfavorable_terrains_sniper(self):
        master = TerrainMaster()
        
        unfavorable = master.get_unfavorable_terrains("sniper")
        
        # Sniper should find forest dan water unfavorable
        assert "forest" in unfavorable
        assert "water" in unfavorable
    
    def test_should_seek_terrain_change_advantage_available(self):
        master = TerrainMaster()
        
        # Sniper di forest (bad) with plains available (good)
        should_move, recommended, gain = master.should_seek_terrain_change(
            our_weapon="sniper",
            enemy_weapon="katana",
            current_terrain="forest",
            available_terrains=["forest", "plains", "mountain"]
        )
        
        assert should_move is True
        assert recommended in ["plains", "mountain"]  # Better terrains untuk sniper
        assert gain > 0.1
    
    def test_should_seek_terrain_change_already_optimal(self):
        master = TerrainMaster()
        
        # Sniper di plains (good), no better option
        should_move, recommended, gain = master.should_seek_terrain_change(
            our_weapon="sniper",
            enemy_weapon="katana",
            current_terrain="plains",
            available_terrains=["plains", "water", "forest"]
        )
        
        # Should NOT recommend move (already in good terrain, others are worse)
        assert should_move is False or gain < 0.1
    
    def test_get_terrain_summary_sniper(self):
        master = TerrainMaster()
        
        summary = master.get_terrain_summary("sniper")
        
        assert summary["weapon"] == "sniper"
        assert "plains" in summary["favorable_terrains"]
        assert "mountain" in summary["favorable_terrains"]
        assert "forest" in summary["unfavorable_terrains"]
        assert "water" in summary["unfavorable_terrains"]


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_terrain_advantage(self):
        result = get_terrain_advantage("katana", "sniper", "forest")
        
        assert "our_advantage" in result
        assert "recommendation" in result
        assert result["our_advantage"] > 0  # Katana advantage di forest
    
    def test_recommend_terrain_for_weapon(self):
        recommendations = recommend_terrain_for_weapon("sniper", ["forest", "plains", "mountain"])
        
        assert len(recommendations) == 3
        # Plains atau mountain should be top untuk sniper
        assert recommendations[0][0] in ["plains", "mountain"]
    
    def test_should_change_terrain(self):
        should_move, recommended, gain = should_change_terrain(
            "sniper", "katana", "forest", ["forest", "plains"]
        )
        
        assert isinstance(should_move, bool)
        assert isinstance(recommended, str)
        assert isinstance(gain, float)
    
    def test_get_weapon_terrain_summary(self):
        summary = get_weapon_terrain_summary("dagger")
        
        assert summary["weapon"] == "dagger"
        assert "favorable_terrains" in summary
        assert "unfavorable_terrains" in summary
        # Dagger should favor forest dan urban
        assert "forest" in summary["favorable_terrains"] or "urban" in summary["favorable_terrains"]


class TestTerrainEdgeCases:
    """Test edge cases"""
    
    def test_empty_weapon_string(self):
        master = TerrainMaster()
        bonus = master.get_terrain_bonus("forest", "")
        # Empty string weapon defaults to "fist"
        assert bonus.weapon_type == "fist"
        assert bonus.attack_multiplier == 1.0  # Default fist bonus di forest
    
    def test_none_terrain(self):
        master = TerrainMaster()
        bonus = master.get_terrain_bonus(None, "katana")
        # None terrain defaults to "plains"
        assert bonus.terrain == "plains"
        assert bonus.attack_multiplier == 1.0  # Katana normal di plains
    
    def test_case_insensitive(self):
        master = TerrainMaster()
        
        # Should be case insensitive
        bonus1 = master.get_terrain_bonus("FOREST", "KATANA")
        bonus2 = master.get_terrain_bonus("forest", "katana")
        
        assert bonus1.attack_multiplier == bonus2.attack_multiplier


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
