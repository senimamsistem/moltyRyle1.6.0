"""
Unit tests untuk Death Zone Predictor System
"""
import pytest
import time
from bot.strategy.dz_predictor import (
    DZSnapshot, RegionSafety, DZPredictor,
    dz_predictor, get_region_safety, get_dz_warning,
    recommend_safe_position, get_center_recommendation
)


class TestDZSnapshot:
    """Test DZSnapshot dataclass"""
    
    def test_creation(self):
        snapshot = DZSnapshot(
            turn=10,
            alive_count=50,
            active_dz={"region_a", "region_b"},
            pending_dz={"region_c"},
            safe_regions={"region_d", "region_e"},
            timestamp=time.time()
        )
        
        assert snapshot.turn == 10
        assert snapshot.alive_count == 50
        assert "region_a" in snapshot.active_dz
        assert "region_c" in snapshot.pending_dz


class TestRegionSafety:
    """Test RegionSafety dataclass"""
    
    def test_creation(self):
        safety = RegionSafety(
            region_id="region_test",
            current_safe=True,
            turns_until_danger=-1,
            distance_to_center=1,
            escape_routes=3,
            safety_score=0.85
        )
        
        assert safety.region_id == "region_test"
        assert safety.safety_score == 0.85
        assert safety.current_safe is True


class TestDZPredictor:
    """Test DZPredictor class"""
    
    def test_initialization(self):
        predictor = DZPredictor()
        assert len(predictor._dz_history) == 0
        assert len(predictor._center_regions) == 0
        assert len(predictor._edge_regions) == 0
    
    def test_record_dz_state(self):
        predictor = DZPredictor()
        
        predictor.record_dz_state(
            turn=1,
            alive_count=100,
            active_dz=["region_edge1"],
            pending_dz=["region_edge2"],
            all_regions=["region_center", "region_edge1", "region_edge2", "region_edge3"],
            timestamp=time.time()
        )
        
        assert len(predictor._dz_history) == 1
        assert "region_edge1" in predictor._region_dz_history
    
    def test_update_center_edge_classification(self):
        predictor = DZPredictor()
        
        # Simulate multiple turns dengan consistent DZ pattern
        for turn in range(1, 11):
            predictor.record_dz_state(
                turn=turn,
                alive_count=100 - turn,
                active_dz=["region_edge1", "region_edge2"],  # Always DZ
                pending_dz=["region_edge3"],
                all_regions=["region_center", "region_edge1", "region_edge2", "region_edge3", "region_edge4"],
                timestamp=time.time()
            )
        
        # Update classification
        predictor._update_center_edge_classification()
        
        # Regions that are always DZ should be classified as edge
        assert "region_edge1" in predictor._edge_regions
        assert "region_edge2" in predictor._edge_regions
    
    def test_calculate_safety_score_safe(self):
        predictor = DZPredictor()
        
        score = predictor._calculate_safety_score(
            is_safe=True,
            turns_until_danger=-1,
            distance_to_center=0,
            safe_exits=3,
            is_center=True,
            is_edge=False
        )
        
        assert score > 0.8  # High safety score untuk center region
    
    def test_calculate_safety_score_danger(self):
        predictor = DZPredictor()
        
        score = predictor._calculate_safety_score(
            is_safe=False,
            turns_until_danger=0,
            distance_to_center=3,
            safe_exits=1,
            is_center=False,
            is_edge=True
        )
        
        assert score == 0.0  # Zero safety untuk active DZ
    
    def test_calculate_safety_score_imminent(self):
        predictor = DZPredictor()
        
        score = predictor._calculate_safety_score(
            is_safe=True,
            turns_until_danger=1,
            distance_to_center=1,
            safe_exits=2,
            is_center=False,
            is_edge=False
        )
        
        # Score should be less than perfect due to imminent danger
        # With center proximity bonus and exit bonus, can still be relatively high
        assert score < 1.0  # Less than perfect
    
    def test_calculate_region_safety_active_dz(self):
        predictor = DZPredictor()
        
        safety = predictor.calculate_region_safety(
            region_id="region_a",
            active_dz=["region_a"],
            pending_dz=["region_b"],
            turn=10,
            connections=["region_b", "region_c"]
        )
        
        assert safety.current_safe is False
        assert safety.turns_until_danger == 0
        assert safety.safety_score == 0.0
    
    def test_calculate_region_safety_pending_dz(self):
        predictor = DZPredictor()
        
        safety = predictor.calculate_region_safety(
            region_id="region_a",
            active_dz=["region_c"],
            pending_dz=["region_a"],
            turn=10,
            connections=["region_b", "region_d"]
        )
        
        # Pending DZ is NOT considered safe (will be danger next turn)
        assert safety.current_safe is False  # Will be danger next turn
        assert safety.turns_until_danger == 1  # Will be danger next turn
        assert safety.safety_score == 0.0  # Score is 0 for pending DZ
    
    def test_get_dz_early_warning_critical(self):
        predictor = DZPredictor()
        
        warning = predictor.get_dz_early_warning(
            region_id="region_a",
            active_dz=["region_a"],
            pending_dz=[],
            turn=10,
            turns_ahead=3
        )
        
        assert warning["warning_level"] == "critical"
        assert warning["turns_until_danger"] == 0
        assert "ESCAPE IMMEDIATELY" in warning["recommended_action"]
    
    def test_get_dz_early_warning_pending(self):
        predictor = DZPredictor()
        
        warning = predictor.get_dz_early_warning(
            region_id="region_a",
            active_dz=[],
            pending_dz=["region_a"],
            turn=10,
            turns_ahead=3
        )
        
        assert warning["warning_level"] == "critical"
        assert warning["turns_until_danger"] == 1
    
    def test_get_dz_early_warning_center(self):
        predictor = DZPredictor()
        
        # First classify a region as center
        predictor._center_regions.add("region_center")
        
        warning = predictor.get_dz_early_warning(
            region_id="region_center",
            active_dz=["region_edge"],
            pending_dz=["region_edge2"],
            turn=10,
            turns_ahead=3
        )
        
        assert warning["warning_level"] == "low"
        assert warning["turns_until_danger"] == -1  # Center = safe
    
    def test_get_center_bias_recommendation_late_game(self):
        predictor = DZPredictor()
        
        # Add center classification
        predictor._center_regions.add("region_center")
        
        rec, reason = predictor.get_center_bias_recommendation(
            current_region="region_edge",
            available_regions=["region_center", "region_edge2"],
            alive_count=20  # Late game
        )
        
        assert rec == "region_center"
        assert "center" in reason.lower()
    
    def test_get_center_bias_recommendation_early_game(self):
        predictor = DZPredictor()
        
        rec, reason = predictor.get_center_bias_recommendation(
            current_region="region_edge",
            available_regions=["region_center", "region_edge2"],
            alive_count=90  # Early game
        )
        
        # Early game: no center bias
        assert rec == "region_edge"
    
    def test_get_summary(self):
        predictor = DZPredictor()
        
        # Add some data
        predictor.record_dz_state(
            turn=1,
            alive_count=50,
            active_dz=["region_a"],
            pending_dz=["region_b"],
            all_regions=["region_a", "region_b", "region_c"]
        )
        
        predictor._center_regions.add("region_c")
        predictor._edge_regions.add("region_a")
        
        summary = predictor.get_summary()
        
        assert summary["history_size"] == 1
        assert summary["center_regions_count"] == 1
        assert summary["edge_regions_count"] == 1


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_region_safety(self):
        safety = get_region_safety(
            region_id="region_test",
            active_dz=[],
            pending_dz=[],
            turn=10,
            connections=["conn1", "conn2"]
        )
        
        assert isinstance(safety, RegionSafety)
        assert safety.current_safe is True
    
    def test_get_dz_warning(self):
        warning = get_dz_warning(
            region_id="region_test",
            active_dz=[],
            pending_dz=["region_test"],
            turn=10
        )
        
        assert "warning_level" in warning
        assert warning["warning_level"] == "critical"
    
    def test_recommend_safe_position(self):
        rec, score, reason = recommend_safe_position(
            current_region="region_a",
            available_regions=["region_b", "region_c"],
            active_dz=["region_d"],
            pending_dz=[],
            turn=10,
            our_hp=80,
            has_weapon=True
        )
        
        assert rec in ["region_b", "region_c"]
        assert 0 <= score <= 1
        assert isinstance(reason, str)
    
    def test_get_center_recommendation(self):
        rec, reason = get_center_recommendation(
            current_region="region_a",
            available_regions=["region_b", "region_c"],
            alive_count=50
        )
        
        assert isinstance(rec, str)
        assert isinstance(reason, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
