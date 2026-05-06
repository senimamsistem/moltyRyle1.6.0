"""
Unit tests untuk Movement Prediction System
"""
import pytest
import time
from bot.learning.movement_predictor import (
    MovementPattern, MovementPredictor,
    movement_predictor, get_movement_prediction, get_escape_recommendations
)


class TestMovementPattern:
    """Test MovementPattern dataclass"""
    
    def test_initialization(self):
        pattern = MovementPattern(player_id="player123")
        assert pattern.player_id == "player123"
        assert pattern.region_sequence == []
        assert pattern.total_moves == 0
        assert pattern.last_seen_region == ""
    
    def test_record_movement(self):
        pattern = MovementPattern(player_id="player123")
        
        # Record first move
        pattern.record_movement("region_a", "region_b", "early", time.time())
        assert pattern.total_moves == 1
        assert pattern.last_seen_region == "region_b"
        assert "region_b" in pattern.early_game_regions
        
        # Record second move
        time.sleep(0.01)
        pattern.record_movement("region_b", "region_c", "mid", time.time())
        assert pattern.total_moves == 2
        assert pattern.last_seen_region == "region_c"
        assert "region_c" in pattern.mid_game_regions
    
    def test_transition_probability(self):
        pattern = MovementPattern(player_id="player123")
        
        # No transitions yet
        assert pattern.get_transition_probability("region_a", "region_b") == 0.0
        
        # Record some transitions
        now = time.time()
        pattern.record_movement("region_a", "region_b", "early", now)
        pattern.record_movement("region_a", "region_b", "early", now + 1)
        pattern.record_movement("region_a", "region_c", "early", now + 2)
        
        # Check probabilities
        prob_ab = pattern.get_transition_probability("region_a", "region_b")
        prob_ac = pattern.get_transition_probability("region_a", "region_c")
        
        assert prob_ab == 2/3  # 2 out of 3 transitions
        assert prob_ac == 1/3  # 1 out of 3 transitions
    
    def test_predict_next_regions(self):
        pattern = MovementPattern(player_id="player123")
        
        # Setup: player moves region_a -> region_b twice, region_a -> region_c once
        now = time.time()
        pattern.record_movement("region_a", "region_b", "early", now)
        pattern.record_movement("region_a", "region_b", "mid", now + 1)
        pattern.record_movement("region_a", "region_c", "late", now + 2)
        
        # Predict from region_a in early game
        predictions = pattern.predict_next_regions("region_a", "early", ["region_b", "region_c", "region_d"])
        
        assert len(predictions) == 3
        # region_b should have highest probability (familiarity + transitions)
        assert predictions[0][0] == "region_b"
        assert predictions[0][1] > predictions[1][1]
        
        # All probabilities should sum to ~1
        total_prob = sum(p for _, p in predictions)
        assert 0.99 <= total_prob <= 1.01


class TestMovementPredictor:
    """Test MovementPredictor class"""
    
    def test_record_observation(self):
        predictor = MovementPredictor()
        
        # Record an observation
        predictor.record_observation("enemy1", "region_a", "early", 90)
        
        # Check pattern was created
        assert "enemy1" in predictor.patterns
        assert predictor.global_hot_zones["region_a"] == 1
    
    def test_record_movement(self):
        predictor = MovementPredictor()
        
        # Record movement
        predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        
        # Check pattern updated
        pattern = predictor.patterns["enemy1"]
        assert pattern.total_moves == 1
        assert pattern.transition_counts["region_a"]["region_b"] == 1
        assert predictor.global_hot_zones["region_b"] == 1
    
    def test_predict_next_region_no_data(self):
        predictor = MovementPredictor()
        
        # Predict without any data - should return equal probabilities
        predictions = predictor.predict_next_region(
            "unknown_enemy", "region_a", ["region_b", "region_c"], "mid"
        )
        
        assert len(predictions) == 2
        assert predictions[0][1] == 0.5
        assert predictions[1][1] == 0.5
    
    def test_predict_next_region_with_data(self):
        predictor = MovementPredictor()
        
        # Setup: enemy prefers region_b when in region_a
        predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        predictor.record_movement("enemy1", "region_a", "region_c", "mid", 50)
        
        # Predict
        predictions = predictor.predict_next_region(
            "enemy1", "region_a", ["region_b", "region_c"], "mid"
        )
        
        # region_b should be more likely
        region_b_prob = next(p for r, p in predictions if r == "region_b")
        region_c_prob = next(p for r, p in predictions if r == "region_c")
        assert region_b_prob > region_c_prob
    
    def test_predict_multi_step(self):
        predictor = MovementPredictor()
        
        # Setup transition chain: a -> b -> c
        predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        predictor.record_movement("enemy1", "region_b", "region_c", "mid", 50)
        
        # Get region connections
        connections = {
            "region_a": ["region_b"],
            "region_b": ["region_c", "region_a"]
        }
        
        # Predict 2 steps ahead from region_a
        predictions = predictor.predict_multi_step(
            "enemy1", "region_a", connections, "mid", steps=2
        )
        
        # Should have region_c as likely destination
        assert "region_c" in predictions
    
    def test_get_hot_zones(self):
        predictor = MovementPredictor()
        
        # Record multiple movements to create hot zones
        for i in range(5):
            predictor.record_movement(f"enemy{i}", "region_a", "region_b", "mid", 50)
        
        for i in range(3):
            predictor.record_movement(f"enemy{i}", "region_c", "region_d", "mid", 50)
        
        hot_zones = predictor.get_hot_zones(top_n=3)
        
        # region_b should be most visited (5 times)
        assert hot_zones[0][0] == "region_b"
        assert hot_zones[0][1] == 5
    
    def test_get_escape_routes(self):
        predictor = MovementPredictor()
        
        # Setup: enemy in region_a usually goes to region_b
        predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        predictor.record_movement("enemy1", "region_a", "region_c", "mid", 50)
        
        # Get escape routes dari enemy's predicted movement
        escape_routes = predictor.get_escape_routes(
            "enemy1", "region_a", ["region_b", "region_c"], "mid"
        )
        
        # region_c should be safer (lower probability enemy goes there)
        region_c_safety = next(s for r, s in escape_routes if r == "region_c")
        region_b_safety = next(s for r, s in escape_routes if r == "region_b")
        assert region_c_safety > region_b_safety
    
    def test_should_avoid_region(self):
        predictor = MovementPredictor()
        
        # Setup: enemy almost always goes to region_b from region_a
        for _ in range(10):
            predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        
        # Should avoid region_b when enemy is in region_a
        should_avoid, prob = predictor.should_avoid_region(
            "enemy1", "region_b", "region_a", "mid", ["region_b", "region_c"], threshold=0.6
        )
        
        assert should_avoid is True
        assert prob >= 0.6
    
    def test_get_ambush_opportunities(self):
        predictor = MovementPredictor()
        
        # Setup: enemy often moves region_a -> region_b
        for _ in range(5):
            predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        
        # Get region connections
        connections = {
            "region_a": ["region_b", "region_c"]
        }
        
        # Get ambush opportunities
        opportunities = predictor.get_ambush_opportunities(
            "enemy1", "region_a", connections, "sniper", "mid"
        )
        
        # region_b should be top opportunity
        assert len(opportunities) > 0
        assert opportunities[0][0] == "region_b"
    
    def test_get_movement_analysis(self):
        predictor = MovementPredictor()
        
        # Record some movements
        predictor.record_movement("enemy1", "region_a", "region_b", "early", 90)
        predictor.record_movement("enemy1", "region_b", "region_c", "mid", 50)
        predictor.record_movement("enemy1", "region_c", "region_d", "late", 20)
        
        analysis = predictor.get_movement_analysis("enemy1")
        
        assert analysis["total_moves"] == 3
        assert analysis["early_game_regions"] == 1  # region_b
        assert analysis["mid_game_regions"] == 1    # region_c
        assert analysis["late_game_regions"] == 1     # region_d
        assert len(analysis["top_transitions"]) > 0
    
    def test_no_data_error(self):
        predictor = MovementPredictor()
        
        analysis = predictor.get_movement_analysis("unknown_enemy")
        
        assert "error" in analysis


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_movement_prediction(self):
        # First record some data
        movement_predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        
        # Get prediction
        predictions = get_movement_prediction("enemy1", "region_a", ["region_b", "region_c"], 50)
        
        assert len(predictions) > 0
        assert abs(sum(p for _, p in predictions) - 1.0) < 0.01
    
    def test_get_escape_recommendations(self):
        # Setup
        movement_predictor.record_movement("enemy1", "region_a", "region_b", "mid", 50)
        
        # Get recommendations
        recommendations = get_escape_recommendations("enemy1", "region_a", ["region_b", "region_c"], 50)
        
        assert len(recommendations) > 0
        # All safety scores should be between 0 and 1
        for _, safety in recommendations:
            assert 0 <= safety <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
