"""
Enemy Behavior Profiling System - Track dan predict enemy player patterns
Partial implementation untuk Sprint 2
"""
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime
from bot.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class EnemyProfile:
    """Profile untuk enemy player"""
    player_id: str
    name: str
    first_seen: float
    last_seen: float
    encounter_count: int = 0
    
    # Behavior patterns
    avg_aggression: float = 0.0  # 0.0 (defensive) to 1.0 (aggressive)
    avg_hp_at_encounter: float = 100.0
    preferred_weapons: List[str] = None
    
    # Combat stats
    wins_against_us: int = 0
    losses_against_us: int = 0
    damage_dealt_to_us: int = 0
    damage_taken_from_us: int = 0
    
    # Movement patterns
    regions_visited: Set[str] = None
    avg_movement_per_turn: float = 0.0
    preferred_terrains: List[str] = None
    
    # Meta patterns
    avg_game_placement: float = 50.0
    avg_kills_per_game: float = 0.0
    survival_time_avg: float = 0.0
    
    def __post_init__(self):
        if self.preferred_weapons is None:
            self.preferred_weapons = []
        if self.regions_visited is None:
            self.regions_visited = set()
        if self.preferred_terrains is None:
            self.preferred_terrains = []


@dataclass
class EncounterRecord:
    """Single encounter dengan enemy"""
    timestamp: float
    our_hp: int
    our_weapon: str
    enemy_hp: int
    enemy_weapon: str
    terrain: str
    weather: str
    outcome: str  # "won", "lost", "escaped", "disengaged"
    damage_dealt: int = 0
    damage_taken: int = 0
    turns_engaged: int = 0


class EnemyProfiler:
    """
    Enemy behavior profiling system
    
    Capabilities:
    1. Track encounter history dengan enemy players
    2. Classify behavior patterns (aggressive/defensive/explorer)
    3. Predict enemy movements
    4. Suggest counter-strategies
    """
    
    PROFILE_FILE = "data/enemy_profiles.json"
    MAX_PROFILE_AGE_DAYS = 7  # Profiles older than this considered stale
    
    def __init__(self):
        self.profiles: Dict[str, EnemyProfile] = {}
        self.recent_encounters: List[EncounterRecord] = []
        self._load_profiles()
        
    def _load_profiles(self):
        """Load existing profiles dari disk"""
        if not os.path.exists(self.PROFILE_FILE):
            return
            
        try:
            with open(self.PROFILE_FILE, 'r') as f:
                data = json.load(f)
                
            for pid, pdata in data.items():
                # Convert sets back from lists
                if "regions_visited" in pdata:
                    pdata["regions_visited"] = set(pdata["regions_visited"])
                if "preferred_weapons" in pdata:
                    pdata["preferred_weapons"] = list(pdata.get("preferred_weapons", []))
                if "preferred_terrains" in pdata:
                    pdata["preferred_terrains"] = list(pdata.get("preferred_terrains", []))
                    
                self.profiles[pid] = EnemyProfile(**pdata)
                
            log.info("📊 Loaded %d enemy profiles", len(self.profiles))
        except Exception as e:
            log.warning("⚠️ Failed to load enemy profiles: %s", e)
    
    def _save_profiles(self):
        """Save profiles ke disk"""
        try:
            os.makedirs(os.path.dirname(self.PROFILE_FILE), exist_ok=True)
            
            # Convert sets to lists untuk JSON serialization
            data = {}
            for pid, profile in self.profiles.items():
                pdict = asdict(profile)
                pdict["regions_visited"] = list(pdict["regions_visited"])
                data[pid] = pdict
                
            with open(self.PROFILE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            log.error("❌ Failed to save enemy profiles: %s", e)
    
    def record_encounter(
        self,
        enemy_id: str,
        enemy_name: str,
        our_hp: int,
        our_weapon: str,
        enemy_hp: int,
        enemy_weapon: str,
        terrain: str,
        weather: str,
        outcome: str,
        damage_dealt: int = 0,
        damage_taken: int = 0
    ):
        """Record encounter dengan enemy"""
        now = time.time()
        
        # Create encounter record
        encounter = EncounterRecord(
            timestamp=now,
            our_hp=our_hp,
            our_weapon=our_weapon,
            enemy_hp=enemy_hp,
            enemy_weapon=enemy_weapon,
            terrain=terrain,
            weather=weather,
            outcome=outcome,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken
        )
        
        self.recent_encounters.append(encounter)
        
        # Update profile
        if enemy_id not in self.profiles:
            self.profiles[enemy_id] = EnemyProfile(
                player_id=enemy_id,
                name=enemy_name,
                first_seen=now,
                last_seen=now,
                encounter_count=1,
                preferred_weapons=[enemy_weapon] if enemy_weapon else [],
                regions_visited=set()
            )
        else:
            profile = self.profiles[enemy_id]
            profile.last_seen = now
            profile.encounter_count += 1
            
            # Track preferred weapons
            if enemy_weapon and enemy_weapon not in profile.preferred_weapons:
                profile.preferred_weapons.append(enemy_weapon)
                
            # Update combat stats
            if outcome == "won":
                profile.wins_against_us += 1
            elif outcome == "lost":
                profile.losses_against_us += 1
                
            profile.damage_dealt_to_us += damage_taken
            profile.damage_taken_from_us += damage_dealt
            
        # Save profiles periodically
        if len(self.recent_encounters) % 5 == 0:
            self._save_profiles()
            
        log.info("👤 Enemy profile updated: %s (encounter #%d)", 
                 enemy_name, self.profiles[enemy_id].encounter_count)
    
    def classify_behavior(self, enemy_id: str) -> str:
        """
        Classify enemy behavior pattern
        Returns: "aggressive", "defensive", "explorer", "balanced", or "unknown"
        """
        if enemy_id not in self.profiles:
            return "unknown"
            
        profile = self.profiles[enemy_id]
        
        if profile.encounter_count < 3:
            return "unknown"  # Not enough data
        
        # Calculate aggression score
        win_rate = profile.wins_against_us / max(1, profile.encounter_count)
        avg_damage_ratio = profile.damage_dealt_to_us / max(1, profile.damage_taken_from_us)
        
        # Aggressive: high win rate, high damage dealt vs taken
        if win_rate > 0.6 and avg_damage_ratio > 1.2:
            return "aggressive"
            
        # Defensive: low win rate for us (they survive), low damage ratio
        if win_rate < 0.4 and avg_damage_ratio < 0.8:
            return "defensive"
            
        # Explorer: many regions, lower combat frequency
        if len(profile.regions_visited) > 10 and profile.encounter_count < 5:
            return "explorer"
            
        return "balanced"
    
    def predict_threat_level(self, enemy_id: str, current_context: dict) -> str:
        """
        Predict threat level dari enemy dalam current context
        Returns: "low", "medium", "high", "extreme"
        """
        if enemy_id not in self.profiles:
            return "medium"  # Unknown = assume medium threat
            
        profile = self.profiles[enemy_id]
        threat_score = 0.0
        
        # Base threat dari historical performance
        total_fights = profile.wins_against_us + profile.losses_against_us
        if total_fights > 0:
            win_rate = profile.wins_against_us / total_fights
            threat_score += win_rate * 3  # Up to 3 points untuk high win rate
            
        # Weapon matchup
        enemy_weapon = current_context.get("enemy_weapon", "fist")
        our_weapon = current_context.get("our_weapon", "fist")
        
        # Simplified weapon advantage (TODO: expand)
        weapon_advantages = {
            "katana": 2.0,
            "sniper": 1.8,
            "sword": 1.2,
            "pistol": 1.0,
            "dagger": 0.8,
            "bow": 0.7,
            "fist": 0.3
        }
        
        enemy_weapon_power = weapon_advantages.get(enemy_weapon, 1.0)
        our_weapon_power = weapon_advantages.get(our_weapon, 1.0)
        
        if enemy_weapon_power > our_weapon_power:
            threat_score += 1.0
        elif enemy_weapon_power < our_weapon_power:
            threat_score -= 0.5
            
        # HP advantage
        enemy_hp = current_context.get("enemy_hp", 100)
        our_hp = current_context.get("our_hp", 100)
        
        if enemy_hp > our_hp * 1.3:
            threat_score += 1.5
        elif enemy_hp < our_hp * 0.7:
            threat_score -= 1.0
            
        # Convert score to threat level
        if threat_score >= 3.5:
            return "extreme"
        elif threat_score >= 2.0:
            return "high"
        elif threat_score >= 1.0:
            return "medium"
        else:
            return "low"
    
    def get_counter_strategy(self, enemy_id: str) -> str:
        """Suggest counter-strategy untuk enemy"""
        behavior = self.classify_behavior(enemy_id)
        
        strategies = {
            "aggressive": (
                "ENEMY_COUNTER: Aggressive player detected. "
                "Strategy: Bait into unfavorable fights, maintain HP buffer, "
                "use terrain advantage, avoid fighting when they have weapon advantage."
            ),
            "defensive": (
                "ENEMY_COUNTER: Defensive player detected. "
                "Strategy: Force engagements, don't let them heal/setup, "
                "chase when they flee, use range advantage."
            ),
            "explorer": (
                "ENEMY_COUNTER: Explorer type detected. "
                "Strategy: Predict movement patterns, ambush at loot locations, "
                "cut off escape routes, they may be under-geared."
            ),
            "balanced": (
                "ENEMY_COUNTER: Balanced player. "
                "Strategy: Play standard, watch untuk pattern changes, "
                "adapt based on their current loadout."
            ),
            "unknown": (
                "ENEMY_COUNTER: Unknown player. "
                "Strategy: Assume medium threat, gather intel, play safe initial encounter."
            )
        }
        
        return strategies.get(behavior, strategies["unknown"])
    
    def predict_movement(self, enemy_id: str, current_region: str, 
                         available_regions: List[str]) -> List[Tuple[str, float]]:
        """
        Predict enemy's likely next movements
        Returns: List of (region, probability)
        """
        if enemy_id not in self.profiles:
            # No data - assume equal probability
            prob = 1.0 / len(available_regions) if available_regions else 0
            return [(r, prob) for r in available_regions]
        
        profile = self.profiles[enemy_id]
        predictions = []
        
        for region in available_regions:
            prob = 0.2  # Base probability
            
            # Bonus if they've been there before
            if region in profile.regions_visited:
                prob += 0.3
                
            # If defensive, prefer regions dengan cover/resources
            behavior = self.classify_behavior(enemy_id)
            if behavior == "defensive":
                # Defensive players tend to retreat ke familiar ground
                if profile.encounter_count > 0:
                    prob += 0.1
                    
            predictions.append((region, prob))
        
        # Normalize probabilities
        total = sum(p for _, p in predictions)
        if total > 0:
            predictions = [(r, p/total) for r, p in predictions]
        
        # Sort by probability
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions
    
    def get_profile_summary(self, enemy_id: str) -> str:
        """Get human-readable summary dari enemy profile"""
        if enemy_id not in self.profiles:
            return f"No profile for enemy {enemy_id[:8]}..."
        
        p = self.profiles[enemy_id]
        behavior = self.classify_behavior(enemy_id)
        
        total_fights = p.wins_against_us + p.losses_against_us
        win_rate = (p.wins_against_us / total_fights * 100) if total_fights > 0 else 0
        
        return (
            f"👤 {p.name}: {behavior.upper()} | "
            f"Encounters: {p.encounter_count} | "
            f"Our win rate vs them: {win_rate:.0f}% | "
            f"Weapons: {', '.join(p.preferred_weapons) or 'unknown'} | "
            f"Regions visited: {len(p.regions_visited)}"
        )
    
    def get_all_known_enemies(self) -> List[str]:
        """Get list of all enemy IDs we've profiled"""
        return list(self.profiles.keys())
    
    def get_stale_profiles(self, max_age_days: int = None) -> List[str]:
        """Get profiles yang haven't been seen recently"""
        max_age = max_age_days or self.MAX_PROFILE_AGE_DAYS
        cutoff = time.time() - (max_age * 86400)
        
        stale = []
        for pid, profile in self.profiles.items():
            if profile.last_seen < cutoff:
                stale.append(pid)
                
        return stale
    
    def cleanup_stale_profiles(self):
        """Remove stale profiles"""
        stale = self.get_stale_profiles()
        for pid in stale:
            del self.profiles[pid]
            log.info("🗑️ Removed stale profile: %s", pid[:8])
            
        if stale:
            self._save_profiles()


# Global profiler instance
enemy_profiler = EnemyProfiler()


def record_combat_encounter(
    enemy_id: str,
    enemy_name: str,
    our_hp: int,
    our_weapon: str,
    enemy_hp: int,
    enemy_weapon: str,
    terrain: str,
    weather: str,
    outcome: str,
    damage_dealt: int = 0,
    damage_taken: int = 0
):
    """Convenience function untuk record encounter"""
    enemy_profiler.record_encounter(
        enemy_id=enemy_id,
        enemy_name=enemy_name,
        our_hp=our_hp,
        our_weapon=our_weapon,
        enemy_hp=enemy_hp,
        enemy_weapon=enemy_weapon,
        terrain=terrain,
        weather=weather,
        outcome=outcome,
        damage_dealt=damage_dealt,
        damage_taken=damage_taken
    )


def get_enemy_intelligence(enemy_id: str, current_context: dict) -> dict:
    """
    Get comprehensive intelligence report untuk enemy
    
    Returns dict dengan:
    - behavior_classification
    - threat_level
    - counter_strategy
    - predicted_movements
    - historical_stats
    """
    return {
        "behavior": enemy_profiler.classify_behavior(enemy_id),
        "threat": enemy_profiler.predict_threat_level(enemy_id, current_context),
        "counter_strategy": enemy_profiler.get_counter_strategy(enemy_id),
        "profile_summary": enemy_profiler.get_profile_summary(enemy_id)
    }
