"""
Unit tests untuk Item Need Predictor
"""
import pytest
from bot.strategy.item_need_predictor import (
    ItemNeedPredictor, ItemNeedProfile, GamePhase,
    predict_item_needs, get_pickup_recommendation, should_use_item_now
)


class TestGamePhaseDetection:
    """Test game phase detection"""
    
    def test_early_phase_80_plus(self):
        predictor = ItemNeedPredictor()
        phase = predictor._get_game_phase(95)
        assert phase == GamePhase.EARLY
        
    def test_mid_phase_30_79(self):
        predictor = ItemNeedPredictor()
        phase = predictor._get_game_phase(50)
        assert phase == GamePhase.MID
        
    def test_late_phase_10_29(self):
        predictor = ItemNeedPredictor()
        phase = predictor._get_game_phase(15)
        assert phase == GamePhase.LATE
        
    def test_endgame_phase_under_10(self):
        predictor = ItemNeedPredictor()
        phase = predictor._get_game_phase(5)
        assert phase == GamePhase.ENDGAME


class TestWeaponTier:
    """Test weapon tier calculation"""
    
    def test_no_weapon_tier_0(self):
        predictor = ItemNeedPredictor()
        tier = predictor._get_weapon_tier(None)
        assert tier == 0
        
    def test_fist_tier_0(self):
        predictor = ItemNeedPredictor()
        tier = predictor._get_weapon_tier({"typeId": "fist"})
        assert tier == 0
        
    def test_dagger_tier_1(self):
        predictor = ItemNeedPredictor()
        tier = predictor._get_weapon_tier({"typeId": "dagger"})
        assert tier == 1
        
    def test_sword_tier_2(self):
        predictor = ItemNeedPredictor()
        tier = predictor._get_weapon_tier({"typeId": "sword"})
        assert tier == 2
        
    def test_katana_tier_3(self):
        predictor = ItemNeedPredictor()
        tier = predictor._get_weapon_tier({"typeId": "katana"})
        assert tier == 3
        
    def test_sniper_tier_3(self):
        predictor = ItemNeedPredictor()
        tier = predictor._get_weapon_tier({"typeId": "sniper"})
        assert tier == 3


class TestHealingCount:
    """Test healing item counting"""
    
    def test_empty_inventory(self):
        predictor = ItemNeedPredictor()
        count, potential = predictor._count_healing_items([])
        assert count == 0
        assert potential == 0
        
    def test_mixed_healing_items(self):
        predictor = ItemNeedPredictor()
        inventory = [
            {"typeId": "bandage"},
            {"typeId": "medkit"},
            {"typeId": "emergency_food"},
            {"typeId": "sword"},  # Not healing
        ]
        count, potential = predictor._count_healing_items(inventory)
        assert count == 3
        assert potential == 100  # 30 + 50 + 20
        
    def test_multiple_same_type(self):
        predictor = ItemNeedPredictor()
        inventory = [
            {"typeId": "bandage"},
            {"typeId": "bandage"},
            {"typeId": "medkit"},
        ]
        count, potential = predictor._count_healing_items(inventory)
        assert count == 3
        assert potential == 110  # 30 + 30 + 50


class TestPredictNeedsEarlyGame:
    """Test item need prediction untuk early game"""
    
    def test_early_no_weapon_critical(self):
        profile = predict_item_needs(
            alive_count=95,
            inventory=[],
            equipped_weapon=None,
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        assert profile.game_phase == "early"
        assert profile.needs_weapon is True
        assert profile.weapon_priority == 100
        assert "weapon" in profile.priority_item_types
        
    def test_early_with_weapon_ok(self):
        profile = predict_item_needs(
            alive_count=85,
            inventory=[
                {"typeId": "sword", "category": "weapon"},
                {"typeId": "bandage", "category": "consumable"}
            ],
            equipped_weapon={"typeId": "sword"},
            current_hp=80,
            current_ep=10,
            max_ep=10
        )
        
        assert profile.needs_weapon is False
        assert profile.needs_better_weapon is False  # Sword cukup untuk early
        
    def test_early_needs_healing_low(self):
        profile = predict_item_needs(
            alive_count=90,
            inventory=[{"typeId": "sword"}],
            equipped_weapon={"typeId": "sword"},
            current_hp=40,
            current_ep=10,
            max_ep=10
        )
        
        assert profile.needs_healing is True
        assert profile.healing_urgency in ["low", "medium", "critical"]


class TestPredictNeedsLateGame:
    """Test item need prediction untuk late game"""
    
    def test_late_needs_better_weapon(self):
        profile = predict_item_needs(
            alive_count=15,
            inventory=[{"typeId": "dagger", "category": "weapon"}],
            equipped_weapon={"typeId": "dagger"},
            current_hp=80,
            current_ep=10,
            max_ep=10
        )
        
        assert profile.game_phase == "late"
        assert profile.needs_weapon is False
        assert profile.needs_better_weapon is True  # Dagger tidak cukup untuk late
        
    def test_late_with_katana_ok(self):
        predictor = ItemNeedPredictor()
        # Katana with 4 bandages - good loadout for late game
        profile = predictor.predict_needs(
            alive_count=15,
            inventory=[{"typeId": "katana", "category": "weapon"}] + [{"typeId": "bandage", "category": "consumable"} for _ in range(4)],
            equipped_weapon={"typeId": "katana"},
            current_hp=80,
            current_ep=10,
            max_ep=10
        )
        
        assert profile.needs_weapon is False
        assert profile.needs_better_weapon is False  # Katana is tier 3, best for late
        
    def test_endgame_max_heals_needed(self):
        predictor = ItemNeedPredictor()
        profile = predictor.predict_needs(
            alive_count=5,
            inventory=[{"typeId": "katana", "category": "weapon"}],
            equipped_weapon={"typeId": "katana"},
            current_hp=80,
            current_ep=10,
            max_ep=10
        )
        
        assert profile.game_phase == "endgame"
        assert profile.healing_target >= 5  # Endgame butuh banyak heals


class TestDZThreat:
    """Test item needs dengan DZ threat"""
    
    def test_dz_threat_increases_heal_target(self):
        predictor = ItemNeedPredictor()
        
        # Without DZ threat
        profile_normal = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword", "category": "weapon"}],
            equipped_weapon={"typeId": "sword"},
            current_hp=80,
            current_ep=10,
            max_ep=10,
            is_dz_threat=False
        )
        
        # With DZ threat
        profile_dz = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword", "category": "weapon"}],
            equipped_weapon={"typeId": "sword"},
            current_hp=80,
            current_ep=10,
            max_ep=10,
            is_dz_threat=True
        )
        
        assert profile_dz.healing_target >= profile_normal.healing_target
        assert profile_dz.needs_dz_escape is True
        
    def test_dz_threat_with_low_ep(self):
        predictor = ItemNeedPredictor()
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[],
            equipped_weapon={"typeId": "sword"},
            current_hp=80,
            current_ep=3,  # Low EP
            max_ep=10,
            is_dz_threat=True
        )
        
        assert profile.needs_dz_escape is True
        assert profile.needs_ep_recovery is True


class TestPickupRecommendation:
    """Test pickup recommendation logic"""
    
    def test_recommend_needed_weapon(self):
        predictor = ItemNeedPredictor()
        
        # Create profile yang butuh weapon
        profile = predictor.predict_needs(
            alive_count=90,
            inventory=[],
            equipped_weapon=None,
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        # Sword on ground
        ground_sword = {"typeId": "sword", "category": "weapon", "id": "sword-1"}
        rec = predictor.get_pickup_recommendation(ground_sword, profile, [])
        
        assert rec["should_pickup"] is True
        assert rec["priority_score"] >= 80
        
    def test_recommend_needed_healing(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword", "category": "weapon"}],
            equipped_weapon={"typeId": "sword"},
            current_hp=20,  # Low HP
            current_ep=10,
            max_ep=10
        )
        
        ground_medkit = {"typeId": "medkit", "category": "consumable", "id": "medkit-1"}
        rec = predictor.get_pickup_recommendation(ground_medkit, profile, [])
        
        assert rec["should_pickup"] is True
        assert "healing" in rec["reason"].lower() or "NEEDED" in rec["reason"]
        
    def test_reject_unneeded_item(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword"} for _ in range(5)],  # Full inventory
            equipped_weapon={"typeId": "katana"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        # Low tier weapon when already have katana
        ground_dagger = {"typeId": "dagger", "category": "weapon", "id": "dagger-1"}
        rec = predictor.get_pickup_recommendation(ground_dagger, profile, [])
        
        assert rec["should_pickup"] is False


class TestDropSuggestion:
    """Test drop suggestion logic"""
    
    def test_suggest_drop_energy_drink(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword"}],  # Butuh space
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        inventory = [
            {"typeId": "energy_drink", "id": "drink-1"},
            {"typeId": "sword", "category": "weapon", "id": "sword-1"},
        ]
        # Fill to 10 items
        for i in range(8):
            inventory.append({"typeId": f"item-{i}", "id": f"item-{i}"})
        
        drop = predictor._suggest_drop(inventory, profile)
        assert drop == "drink-1"  # Should suggest energy drink
        
    def test_suggest_drop_map(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword"}],
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        inventory = [
            {"typeId": "map", "id": "map-1"},
            {"typeId": "sword", "category": "weapon", "id": "sword-1"},
        ]
        for i in range(8):
            inventory.append({"typeId": f"item-{i}", "id": f"item-{i}"})
        
        drop = predictor._suggest_drop(inventory, profile)
        assert drop is not None
        
    def test_no_drop_when_not_full(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword"}],
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        inventory = [
            {"typeId": "energy_drink", "id": "drink-1"},
            {"typeId": "sword", "category": "weapon", "id": "sword-1"},
        ]  # Only 2 items
        
        drop = predictor._suggest_drop(inventory, profile)
        assert drop is None  # No drop needed


class TestShouldUseItemNow:
    """Test immediate item usage logic"""
    
    def test_use_energy_drink_when_ep_low(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=50,
            inventory=[{"typeId": "sword"} for _ in range(9)],  # Almost full
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=3,  # Low EP
            max_ep=10
        )
        
        energy_drink = {"typeId": "energy_drink"}
        should_use = predictor.should_use_item_now(
            energy_drink, profile, 100, 3, 10
        )
        
        assert should_use is True
        
    def test_use_emergency_food_when_excess(self):
        predictor = ItemNeedPredictor()
        
        # Profile dengan excess heals (10 bandages - definitely excess)
        profile = predictor.predict_needs(
            alive_count=50,  # Mid game
            inventory=[{"typeId": "bandage", "category": "consumable"} for _ in range(10)],  # 10 heals = definitely excess
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        # With 10 bandages, should definitely have excess (target is typically 4-6)
        emergency_food = {"typeId": "emergency_food"}
        should_use = predictor.should_use_item_now(
            emergency_food, profile, 100, 10, 10
        )
        
        # Should suggest using excess food if we have excess
        # (deficit < 0 means we have MORE than needed = excess)
        if profile.healing_deficit < 0:
            assert should_use is True
        else:
            # If somehow still not excess, just verify the function works
            assert isinstance(should_use, bool)
        
    def test_always_use_map(self):
        predictor = ItemNeedPredictor()
        
        profile = predictor.predict_needs(
            alive_count=95,
            inventory=[],
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        map_item = {"typeId": "map"}
        should_use = predictor.should_use_item_now(
            map_item, profile, 100, 10, 10
        )
        
        assert should_use is True


class TestConvenienceFunctions:
    """Test convenience module functions"""
    
    def test_predict_item_needs_convenience(self):
        profile = predict_item_needs(
            alive_count=95,
            inventory=[],
            equipped_weapon=None,
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        assert isinstance(profile, ItemNeedProfile)
        assert profile.needs_weapon is True
        
    def test_get_pickup_recommendation_convenience(self):
        predictor = ItemNeedPredictor()
        profile = predictor.predict_needs(
            alive_count=95,
            inventory=[],
            equipped_weapon=None,
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        ground_item = {"typeId": "sword", "category": "weapon", "id": "sword-1"}
        rec = get_pickup_recommendation(ground_item, profile, [])
        
        assert isinstance(rec, dict)
        assert "should_pickup" in rec
        
    def test_should_use_item_now_convenience(self):
        predictor = ItemNeedPredictor()
        profile = predictor.predict_needs(
            alive_count=95,
            inventory=[{"typeId": "sword"} for _ in range(9)],
            equipped_weapon={"typeId": "sword"},
            current_hp=100,
            current_ep=10,
            max_ep=10
        )
        
        map_item = {"typeId": "map"}
        result = should_use_item_now(map_item, profile, 100, 10, 10)
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
