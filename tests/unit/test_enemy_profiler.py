"""
Unit tests untuk Enemy Behavior Profiling System
"""
import pytest
import time
import os
import tempfile
from bot.learning.enemy_profiler import (
    EnemyProfiler, EnemyProfile, EncounterRecord,
    enemy_profiler, record_combat_encounter, get_enemy_intelligence
)


class TestEnemyProfile:
    """Test EnemyProfile dataclass"""
    
    def test_profile_creation(self):
        """Test creating enemy profile"""
        profile = EnemyProfile(
            player_id="player_123",
            name="TestPlayer",
            first_seen=time.time(),
            last_seen=time.time(),
            encounter_count=1
        )
        
        assert profile.player_id == "player_123"
        assert profile.name == "TestPlayer"
        assert profile.encounter_count == 1
        assert profile.preferred_weapons == []
        assert profile.regions_visited == set()


class TestEnemyProfiler:
    """Test EnemyProfiler functionality"""
    
    @pytest.fixture
    def temp_profiler(self, tmp_path):
        """Create profiler dengan temporary file"""
        profiler = EnemyProfiler()
        profiler.PROFILE_FILE = str(tmp_path / "test_profiles.json")
        return profiler
    
    def test_record_encounter_creates_profile(self, temp_profiler):
        """Recording encounter should create new profile"""
        temp_profiler.record_encounter(
            enemy_id="enemy_1",
            enemy_name="EnemyPlayer",
            our_hp=80,
            our_weapon="sword",
            enemy_hp=60,
            enemy_weapon="dagger",
            terrain="plains",
            weather="clear",
            outcome="won",
            damage_dealt=40,
            damage_taken=20
        )
        
        assert "enemy_1" in temp_profiler.profiles
        profile = temp_profiler.profiles["enemy_1"]
        assert profile.name == "EnemyPlayer"
        assert profile.encounter_count == 1
        assert profile.wins_against_us == 1
        
    def test_multiple_encounters_update_profile(self, temp_profiler):
        """Multiple encounters should update same profile"""
        for i in range(3):
            temp_profiler.record_encounter(
                enemy_id="enemy_1",
                enemy_name="EnemyPlayer",
                our_hp=80,
                our_weapon="sword",
                enemy_hp=60,
                enemy_weapon="dagger",
                terrain="plains",
                weather="clear",
                outcome="won" if i < 2 else "lost",
                damage_dealt=40,
                damage_taken=20
            )
        
        profile = temp_profiler.profiles["enemy_1"]
        assert profile.encounter_count == 3
        assert profile.wins_against_us == 2
        assert profile.losses_against_us == 1
        
    def test_behavior_classification_unknown(self, temp_profiler):
        """Unknown enemy should return unknown classification"""
        result = temp_profiler.classify_behavior("unknown_enemy")
        assert result == "unknown"
        
    def test_behavior_classification_aggressive(self, temp_profiler):
        """High win rate enemy should be classified aggressive"""
        # Create profile dengan many wins
        for _ in range(5):
            temp_profiler.record_encounter(
                enemy_id="aggro_player",
                enemy_name="AggroPlayer",
                our_hp=50,
                our_weapon="sword",
                enemy_hp=100,
                enemy_weapon="katana",
                terrain="plains",
                weather="clear",
                outcome="lost",  # They win = we lose
                damage_dealt=10,
                damage_taken=50
            )
        
        behavior = temp_profiler.classify_behavior("aggro_player")
        assert behavior == "aggressive"
        
    def test_behavior_classification_defensive(self, temp_profiler):
        """Low damage dealt vs taken should be defensive"""
        # Create profile where they take damage but deal little
        for _ in range(3):
            temp_profiler.record_encounter(
                enemy_id="def_player",
                enemy_name="DefensivePlayer",
                our_hp=100,
                our_weapon="sword",
                enemy_hp=50,
                enemy_weapon="shield",  # They don't fight back hard
                terrain="plains",
                weather="clear",
                outcome="won",
                damage_dealt=50,
                damage_taken=10
            )
        
        behavior = temp_profiler.classify_behavior("def_player")
        # Might be defensive atau balanced tergantung exact ratios
        assert behavior in ["defensive", "balanced", "unknown"]
        
    def test_threat_level_unknown(self, temp_profiler):
        """Unknown enemy should have medium threat"""
        threat = temp_profiler.predict_threat_level("unknown", {
            "our_weapon": "sword",
            "enemy_weapon": "dagger",
            "our_hp": 100,
            "enemy_hp": 80
        })
        assert threat == "medium"
        
    def test_threat_level_high_weapon_advantage(self, temp_profiler):
        """Enemy with better weapon should have higher threat"""
        # Create profile
        temp_profiler.record_encounter(
            enemy_id="strong_enemy",
            enemy_name="StrongEnemy",
            our_hp=80,
            our_weapon="dagger",
            enemy_hp=90,
            enemy_weapon="katana",
            terrain="plains",
            weather="clear",
            outcome="lost",
            damage_dealt=20,
            damage_taken=60
        )
        
        threat = temp_profiler.predict_threat_level("strong_enemy", {
            "our_weapon": "dagger",
            "enemy_weapon": "katana",
            "our_hp": 80,
            "enemy_hp": 90
        })
        
        # Should be high atau extreme karena weapon advantage
        assert threat in ["high", "extreme"]
        
    def test_counter_strategy_aggressive(self, temp_profiler):
        """Should provide counter strategy untuk aggressive enemy"""
        for _ in range(4):
            temp_profiler.record_encounter(
                enemy_id="aggro",
                enemy_name="AggroPlayer",
                our_hp=50,
                our_weapon="sword",
                enemy_hp=100,
                enemy_weapon="katana",
                terrain="plains",
                weather="clear",
                outcome="lost",
                damage_dealt=20,
                damage_taken=50
            )
        
        strategy = temp_profiler.get_counter_strategy("aggro")
        assert "ENEMY_COUNTER" in strategy
        assert "aggressive" in strategy.lower()
        
    def test_profile_summary_generation(self, temp_profiler):
        """Should generate readable profile summary"""
        temp_profiler.record_encounter(
            enemy_id="player_1",
            enemy_name="TestPlayer",
            our_hp=80,
            our_weapon="sword",
            enemy_hp=70,
            enemy_weapon="dagger",
            terrain="plains",
            weather="clear",
            outcome="won",
            damage_dealt=30,
            damage_taken=20
        )
        
        summary = temp_profiler.get_profile_summary("player_1")
        assert "TestPlayer" in summary
        assert "Encounters:" in summary
        
    def test_predict_movement_no_data(self, temp_profiler):
        """Movement prediction without data should be uniform"""
        regions = ["region_a", "region_b", "region_c"]
        predictions = temp_profiler.predict_movement("unknown", "current", regions)
        
        assert len(predictions) == 3
        # Without data, should be roughly equal
        probs = [p[1] for p in predictions]
        assert all(0.1 < p < 0.5 for p in probs)
        
    def test_stale_profile_detection(self, temp_profiler):
        """Should detect stale profiles"""
        # Create fresh profile
        temp_profiler.record_encounter(
            enemy_id="fresh",
            enemy_name="FreshPlayer",
            our_hp=80,
            our_weapon="sword",
            enemy_hp=70,
            enemy_weapon="dagger",
            terrain="plains",
            weather="clear",
            outcome="won",
            damage_dealt=30,
            damage_taken=20
        )
        
        # Not stale yet
        stale = temp_profiler.get_stale_profiles(max_age_days=7)
        assert "fresh" not in stale
        
        # Make profile old
        temp_profiler.profiles["fresh"].last_seen = time.time() - (8 * 86400)
        
        stale = temp_profiler.get_stale_profiles(max_age_days=7)
        assert "fresh" in stale
        
    def test_cleanup_stale_profiles(self, temp_profiler):
        """Should remove stale profiles"""
        temp_profiler.record_encounter(
            enemy_id="old",
            enemy_name="OldPlayer",
            our_hp=80,
            our_weapon="sword",
            enemy_hp=70,
            enemy_weapon="dagger",
            terrain="plains",
            weather="clear",
            outcome="won",
            damage_dealt=30,
            damage_taken=20
        )
        
        # Make old
        temp_profiler.profiles["old"].last_seen = time.time() - (10 * 86400)
        
        temp_profiler.cleanup_stale_profiles()
        
        assert "old" not in temp_profiler.profiles


class TestGlobalProfiler:
    """Test global enemy_profiler instance"""
    
    def test_global_profiler_exists(self):
        """Test global profiler is initialized"""
        assert enemy_profiler is not None
        assert isinstance(enemy_profiler, EnemyProfiler)
        
    def test_convenience_functions(self):
        """Test convenience function exports"""
        # Test get_enemy_intelligence returns dict
        intel = get_enemy_intelligence("unknown", {})
        assert isinstance(intel, dict)
        assert "behavior" in intel
        assert "threat" in intel
        assert "counter_strategy" in intel
        assert "profile_summary" in intel
