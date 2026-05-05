"""
Unit tests untuk Combat Prediction Engine
"""
import pytest
from bot.strategy.combat_predictor import (
    CombatPredictor, CombatFactors, CombatPrediction,
    combat_predictor, should_engange_with_prediction
)


class TestCombatPrediction:
    """Test suite untuk combat prediction calculations"""
    
    @pytest.fixture
    def predictor(self):
        return CombatPredictor()
    
    @pytest.fixture
    def sample_factors(self):
        return CombatFactors(
            hp=80, max_hp=100, ep=8, atk=15, defense=8,
            weapon_bonus=20, weapon_range=0, weapon_type="sword",
            healing_items=2,
            enemy_hp=60, enemy_max_hp=100, enemy_atk=12, enemy_def=5,
            enemy_weapon_bonus=10, enemy_weapon_type="dagger",
            terrain="plains", weather="clear",
            is_surrounded=False, escape_routes=3,
            alive_count=50, game_phase="mid"
        )
    
    def test_win_probability_calculation(self, predictor, sample_factors):
        """Test win probability calculation returns valid range"""
        prediction = predictor.calculate_win_probability(sample_factors)
        
        assert isinstance(prediction, CombatPrediction)
        assert 0.0 <= prediction.win_probability <= 1.0
        assert prediction.confidence > 0
        assert prediction.risk_level in ["low", "medium", "high", "extreme"]
        
    def test_advantageous_combat_high_probability(self, predictor):
        """When we have clear advantage, win prob should be high"""
        factors = CombatFactors(
            hp=100, max_hp=100, ep=10, atk=20, defense=10,
            weapon_bonus=35, weapon_range=0, weapon_type="katana",
            healing_items=3,
            enemy_hp=40, enemy_max_hp=100, enemy_atk=10, enemy_def=3,
            enemy_weapon_bonus=0, enemy_weapon_type="fist",
            terrain="plains", weather="clear",
            is_surrounded=False, escape_routes=4,
            alive_count=30, game_phase="late"
        )
        
        prediction = predictor.calculate_win_probability(factors)
        assert prediction.win_probability >= 0.7
        assert prediction.risk_level == "low"
        
    def test_disadvantageous_combat_low_probability(self, predictor):
        """When at disadvantage, win prob should be low"""
        factors = CombatFactors(
            hp=30, max_hp=100, ep=3, atk=10, defense=3,
            weapon_bonus=0, weapon_range=0, weapon_type="fist",
            healing_items=0,
            enemy_hp=100, enemy_max_hp=100, enemy_atk=20, enemy_def=10,
            enemy_weapon_bonus=35, enemy_weapon_type="katana",
            terrain="plains", weather="clear",
            is_surrounded=True, escape_routes=1,
            alive_count=10, game_phase="late"
        )
        
        prediction = predictor.calculate_win_probability(factors)
        assert prediction.win_probability <= 0.4
        assert prediction.risk_level in ["high", "extreme"]
        
    def test_weapon_matchup_modifier(self, predictor):
        """Test weapon matchup calculations"""
        # Katana vs Bow should have advantage
        katana_vs_bow = predictor._get_weapon_matchup_modifier("katana", "bow")
        assert katana_vs_bow > 0
        
        # Sniper vs Katana should have disadvantage (katana can close)
        sniper_vs_katana = predictor._get_weapon_matchup_modifier("sniper", "katana")
        assert sniper_vs_katana < 0
        
        # Same weapon = no advantage
        same = predictor._get_weapon_matchup_modifier("sword", "sword")
        assert same == 0.0
        
    def test_terrain_modifiers(self, predictor, sample_factors):
        """Test terrain affects prediction"""
        # Hills favor ranged
        sample_factors.terrain = "hills"
        sample_factors.weapon_type = "sniper"
        
        modifier = predictor._get_environmental_modifier(sample_factors)
        assert modifier > 0  # Should give bonus untuk ranged di hills
        
    def test_weather_penalty(self, predictor, sample_factors):
        """Test weather reduces effectiveness"""
        sample_factors.weather = "storm"
        
        modifier = predictor._get_environmental_modifier(sample_factors)
        assert modifier < 0  # Storm should give penalty
        
    def test_surrounded_penalty(self, predictor, sample_factors):
        """Being surrounded should increase risk"""
        sample_factors.is_surrounded = True
        
        modifier = predictor._get_resource_modifier(sample_factors)
        assert modifier < 0  # Should have escape penalty
        
    def test_healing_advantage(self, predictor, sample_factors):
        """Having healing items should help"""
        sample_factors.healing_items = 5
        
        modifier = predictor._get_resource_modifier(sample_factors)
        assert modifier > 0  # Healing advantage
        
    def test_logistic_curve(self, predictor):
        """Test logistic curve applies modifiers smoothly"""
        base = 0.5
        
        # Positive modifier increases probability
        higher = predictor._apply_logistic_curve(base, 0.5)
        assert higher > base
        
        # Negative modifier decreases probability
        lower = predictor._apply_logistic_curve(base, -0.5)
        assert lower < base
        
        # Large positive shouldn't exceed 0.95
        very_high = predictor._apply_logistic_curve(base, 2.0)
        assert very_high <= 0.95
        
        # Large negative shouldn't go below 0.05
        very_low = predictor._apply_logistic_curve(base, -2.0)
        assert very_low >= 0.05
        
    def test_prediction_recommendation_attack(self, predictor):
        """High win probability should recommend attack"""
        factors = CombatFactors(
            hp=90, max_hp=100, ep=10, atk=20, defense=10,
            weapon_bonus=35, weapon_range=0, weapon_type="katana",
            healing_items=3,
            enemy_hp=50, enemy_max_hp=100, enemy_atk=10, enemy_def=5,
            enemy_weapon_bonus=10, enemy_weapon_type="dagger",
            terrain="plains", weather="clear",
            is_surrounded=False, escape_routes=3,
            alive_count=30, game_phase="mid"
        )
        
        prediction = predictor.calculate_win_probability(factors)
        assert prediction.recommended_action == "attack"
        
    def test_prediction_recommendation_flee(self, predictor):
        """Extreme risk should recommend flee"""
        factors = CombatFactors(
            hp=20, max_hp=100, ep=3, atk=10, defense=3,
            weapon_bonus=0, weapon_range=0, weapon_type="fist",
            healing_items=0,
            enemy_hp=100, enemy_max_hp=100, enemy_atk=20, enemy_def=10,
            enemy_weapon_bonus=35, enemy_weapon_type="katana",
            terrain="plains", weather="clear",
            is_surrounded=True, escape_routes=2,
            alive_count=10, game_phase="late"
        )
        
        prediction = predictor.calculate_win_probability(factors)
        assert prediction.recommended_action == "flee"
        
    def test_damage_exchange_estimation(self, predictor, sample_factors):
        """Test damage exchange estimation"""
        damage = predictor._estimate_damage_exchange(sample_factors)
        
        assert "dealt" in damage
        assert "taken" in damage
        assert damage["dealt"] > 0
        assert damage["taken"] >= 0
        
    def test_combat_duration_estimation(self, predictor, sample_factors):
        """Test combat duration estimation"""
        turns = predictor._estimate_combat_duration(sample_factors)
        
        assert 1 <= turns <= 10  # Should be reasonable range
        
    def test_risk_classification(self, predictor):
        """Test risk level classification"""
        assert predictor._classify_risk(0.8, sample_factors) == "low"
        assert predictor._classify_risk(0.6, sample_factors) == "medium"
        assert predictor._classify_risk(0.45, sample_factors) == "high"
        assert predictor._classify_risk(0.3, sample_factors) == "extreme"
        
    def test_prediction_caching(self, predictor, sample_factors):
        """Test predictions are cached"""
        pred1 = predictor.calculate_win_probability(sample_factors)
        pred2 = predictor.calculate_win_probability(sample_factors)
        
        # Should return same cached result
        cache_key = predictor._make_cache_key(sample_factors)
        assert cache_key in predictor._prediction_cache
        
    def test_historical_modifier(self, predictor, sample_factors):
        """Test historical performance affects prediction"""
        # With good enemy history (many wins)
        sample_factors.enemy_historical_wins = 10
        sample_factors.enemy_historical_losses = 2
        
        modifier = predictor._get_historical_modifier(sample_factors)
        assert modifier < 0  # Should reduce our win probability (they're good)
        
        # Reset untuk avoid affecting other tests
        sample_factors.enemy_historical_wins = 0
        sample_factors.enemy_historical_losses = 0
        
    def test_finisher_override(self):
        """Very low HP enemy should trigger finisher attack"""
        enemy = {"id": "e1", "hp": 15, "name": "WeakEnemy"}
        
        should_attack, reason, prediction = should_engange_with_prediction(
            enemy=enemy,
            hp=50,
            ep=5,
            equipped={"typeId": "sword"},
            inventory=[],
            terrain="plains",
            weather="clear",
            alive_count=50,
            connections=[],
            aggression="balanced"
        )
        
        assert should_attack is True
        assert "FINISHER" in reason


class TestCombatFactors:
    """Test CombatFactors dataclass"""
    
    def test_factors_creation(self):
        """Test creating CombatFactors"""
        factors = CombatFactors(
            hp=100, max_hp=100, ep=10, atk=15, defense=5,
            weapon_bonus=20, weapon_range=0, weapon_type="sword",
            healing_items=2,
            enemy_hp=80, enemy_max_hp=100, enemy_atk=12, enemy_def=4,
            enemy_weapon_bonus=10, enemy_weapon_type="dagger",
            terrain="plains", weather="clear",
            is_surrounded=False, escape_routes=3,
            alive_count=50, game_phase="mid"
        )
        
        assert factors.hp == 100
        assert factors.weapon_type == "sword"
        assert factors.game_phase == "mid"


class TestGlobalPredictor:
    """Test global combat_predictor instance"""
    
    def test_global_predictor_exists(self):
        """Test global predictor is initialized"""
        assert combat_predictor is not None
        assert isinstance(combat_predictor, CombatPredictor)
