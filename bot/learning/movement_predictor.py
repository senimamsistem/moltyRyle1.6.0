"""
Movement Prediction System - Advanced enemy movement prediction
Extends enemy_profiler dengan sophisticated movement modeling
"""
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple, Counter as CounterType
from collections import defaultdict, Counter
from datetime import datetime
from bot.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class MovementPattern:
    """Track movement patterns untuk single enemy"""
    player_id: str
    
    # Movement history
    region_sequence: List[Tuple[str, float]] = field(default_factory=list)  # (region_id, timestamp)
    transition_counts: Dict[str, CounterType[str]] = field(default_factory=lambda: defaultdict(Counter))
    
    # Pattern analysis
    avg_time_per_region: float = 0.0  # Average turns spent in a region
    movement_frequency: float = 0.0  # Moves per turn
    preferred_connections: Dict[str, List[str]] = field(default_factory=dict)  # region -> [next_regions]
    
    # Game phase patterns
    early_game_regions: Set[str] = field(default_factory=set)
    mid_game_regions: Set[str] = field(default_factory=set)
    late_game_regions: Set[str] = field(default_factory=set)
    
    # Meta patterns
    last_seen_region: str = ""
    last_move_timestamp: float = 0.0
    total_moves: int = 0
    
    def record_movement(self, from_region: str, to_region: str, game_phase: str, timestamp: float):
        """Record a movement dari one region to another"""
        # Update transition count
        self.transition_counts[from_region][to_region] += 1
        
        # Track region sequence
        self.region_sequence.append((to_region, timestamp))
        
        # Update game phase region tracking
        if game_phase == "early":
            self.early_game_regions.add(to_region)
        elif game_phase == "mid":
            self.mid_game_regions.add(to_region)
        else:  # late
            self.late_game_regions.add(to_region)
        
        # Update timing
        if self.last_move_timestamp > 0:
            time_spent = timestamp - self.last_move_timestamp
            # Update rolling average
            self.avg_time_per_region = (self.avg_time_per_region * self.total_moves + time_spent) / (self.total_moves + 1)
        
        self.last_seen_region = to_region
        self.last_move_timestamp = timestamp
        self.total_moves += 1
        
        # Update movement frequency
        if len(self.region_sequence) >= 2:
            self.movement_frequency = self.total_moves / len(self.region_sequence)
    
    def get_transition_probability(self, from_region: str, to_region: str) -> float:
        """Get probability of moving dari from_region ke to_region"""
        if from_region not in self.transition_counts:
            return 0.0
        
        transitions = self.transition_counts[from_region]
        total = sum(transitions.values())
        
        if total == 0:
            return 0.0
        
        return transitions[to_region] / total
    
    def predict_next_regions(self, current_region: str, game_phase: str, 
                            available_connections: List[str]) -> List[Tuple[str, float]]:
        """
        Predict likely next regions dengan weighted scoring
        Returns: List of (region, probability) sorted by probability
        """
        predictions = []
        
        for region in available_connections:
            score = 0.0
            
            # 1. Transition probability (40% weight)
            transition_prob = self.get_transition_probability(current_region, region)
            score += transition_prob * 0.4
            
            # 2. Game phase preference (30% weight)
            phase_score = 0.0
            if game_phase == "early" and region in self.early_game_regions:
                phase_score = 0.3
            elif game_phase == "mid" and region in self.mid_game_regions:
                phase_score = 0.3
            elif game_phase == "late" and region in self.late_game_regions:
                phase_score = 0.3
            score += phase_score
            
            # 3. Familiarity bonus (20% weight)
            if region in [r for r, _ in self.region_sequence]:
                # Been there before
                visit_count = sum(1 for r, _ in self.region_sequence if r == region)
                score += min(0.2, visit_count * 0.05)  # Cap at 0.2
            
            # 4. Recency penalty (10% weight) - less likely to go back immediately
            if len(self.region_sequence) >= 2:
                last_region = self.region_sequence[-2][0] if len(self.region_sequence) >= 2 else ""
                if region == last_region:
                    score -= 0.1  # Penalty for backtracking
            
            predictions.append((region, max(0.01, score)))  # Minimum 1% probability
        
        # Normalize probabilities
        total_score = sum(score for _, score in predictions)
        if total_score > 0:
            predictions = [(r, s / total_score) for r, s in predictions]
        else:
            # Equal probability if no data
            prob = 1.0 / len(available_connections) if available_connections else 0
            predictions = [(r, prob) for r in available_connections]
        
        # Sort by probability descending
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions
    
    def get_favored_approach_regions(self, target_region: str, all_regions: Dict) -> List[str]:
        """
        Get regions that this player commonly approaches target_region from
        Useful untuk predicting ambush locations
        """
        approach_regions = []
        
        for from_region, transitions in self.transition_counts.items():
            if target_region in transitions:
                count = transitions[target_region]
                approach_regions.append((from_region, count))
        
        # Sort by frequency
        approach_regions.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in approach_regions[:3]]  # Top 3


class MovementPredictor:
    """
    Advanced movement prediction system
    
    Features:
    1. Transition probability matrix per enemy
    2. Game phase-based movement patterns
    3. Multi-step prediction (predict 2-3 moves ahead)
    4. Hot zone detection (areas dengan high enemy traffic)
    """
    
    PATTERNS_FILE = "data/movement_patterns.json"
    
    def __init__(self):
        self.patterns: Dict[str, MovementPattern] = {}
        self.global_hot_zones: CounterType[str] = Counter()  # region -> visit count across all enemies
        self.global_transitions: Dict[str, CounterType[str]] = defaultdict(Counter)
        self._load_patterns()
    
    def _load_patterns(self):
        """Load movement patterns dari disk"""
        if not os.path.exists(self.PATTERNS_FILE):
            return
        
        try:
            with open(self.PATTERNS_FILE, 'r') as f:
                data = json.load(f)
            
            for pid, pdata in data.get("patterns", {}).items():
                # Convert sets back from lists
                pdata["early_game_regions"] = set(pdata.get("early_game_regions", []))
                pdata["mid_game_regions"] = set(pdata.get("mid_game_regions", []))
                pdata["late_game_regions"] = set(pdata.get("late_game_regions", []))
                
                # Convert transition_counts
                if "transition_counts" in pdata:
                    pdata["transition_counts"] = {
                        k: Counter(v) for k, v in pdata["transition_counts"].items()
                    }
                
                self.patterns[pid] = MovementPattern(**pdata)
            
            self.global_hot_zones = Counter(data.get("global_hot_zones", {}))
            self.global_transitions = defaultdict(Counter, {
                k: Counter(v) for k, v in data.get("global_transitions", {}).items()
            })
            
            log.info("🗺️ Loaded movement patterns for %d enemies", len(self.patterns))
        except Exception as e:
            log.warning("⚠️ Failed to load movement patterns: %s", e)
    
    def _save_patterns(self):
        """Save movement patterns ke disk"""
        try:
            os.makedirs(os.path.dirname(self.PATTERNS_FILE), exist_ok=True)
            
            # Convert dataclasses to dicts
            patterns_data = {}
            for pid, pattern in self.patterns.items():
                pdata = asdict(pattern)
                pdata["early_game_regions"] = list(pdata["early_game_regions"])
                pdata["mid_game_regions"] = list(pdata["mid_game_regions"])
                pdata["late_game_regions"] = list(pdata["late_game_regions"])
                pdata["transition_counts"] = {
                    k: dict(v) for k, v in pdata["transition_counts"].items()
                }
                patterns_data[pid] = pdata
            
            data = {
                "patterns": patterns_data,
                "global_hot_zones": dict(self.global_hot_zones),
                "global_transitions": {k: dict(v) for k, v in self.global_transitions.items()},
                "last_saved": time.time()
            }
            
            with open(self.PATTERNS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            log.error("❌ Failed to save movement patterns: %s", e)
    
    def record_observation(self, enemy_id: str, region: str, game_phase: str,
                         alive_count: int, timestamp: float = None):
        """
        Record enemy observation (sighting) - tracks presence tanpa movement
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Get or create pattern
        if enemy_id not in self.patterns:
            self.patterns[enemy_id] = MovementPattern(player_id=enemy_id)
        
        pattern = self.patterns[enemy_id]
        
        # Record first sighting if new
        if not pattern.region_sequence:
            pattern.region_sequence.append((region, timestamp))
            pattern.last_seen_region = region
            pattern.last_move_timestamp = timestamp
        
        # Update hot zone
        self.global_hot_zones[region] += 1
    
    def record_movement(self, enemy_id: str, from_region: str, to_region: str,
                       game_phase: str, alive_count: int):
        """
        Record enemy movement dari one region to another
        """
        timestamp = time.time()
        
        # Get or create pattern
        if enemy_id not in self.patterns:
            self.patterns[enemy_id] = MovementPattern(player_id=enemy_id)
        
        pattern = self.patterns[enemy_id]
        pattern.record_movement(from_region, to_region, game_phase, timestamp)
        
        # Update global patterns
        self.global_transitions[from_region][to_region] += 1
        self.global_hot_zones[to_region] += 1
        
        # Save periodically
        if pattern.total_moves % 3 == 0:
            self._save_patterns()
    
    def predict_next_region(self, enemy_id: str, current_region: str,
                           available_connections: List[str],
                           game_phase: str = "mid") -> List[Tuple[str, float]]:
        """
        Predict enemy's most likely next regions
        Returns: List of (region, probability) sorted by probability
        """
        if enemy_id not in self.patterns:
            # No data - use global patterns if available
            return self._predict_from_global(current_region, available_connections)
        
        pattern = self.patterns[enemy_id]
        return pattern.predict_next_regions(current_region, game_phase, available_connections)
    
    def _predict_from_global(self, current_region: str, 
                            available_connections: List[str]) -> List[Tuple[str, float]]:
        """Predict using global movement patterns when individual data unavailable"""
        predictions = []
        
        for region in available_connections:
            prob = 0.1  # Base probability
            
            # Global transition preference
            if current_region in self.global_transitions:
                transitions = self.global_transitions[current_region]
                total = sum(transitions.values())
                if total > 0 and region in transitions:
                    prob += (transitions[region] / total) * 0.6
            
            # Hot zone bonus
            hot_score = self.global_hot_zones.get(region, 0)
            if hot_score > 0:
                prob += min(0.3, hot_score * 0.01)
            
            predictions.append((region, prob))
        
        # Normalize
        total = sum(p for _, p in predictions)
        if total > 0:
            predictions = [(r, p / total) for r, p in predictions]
        else:
            prob = 1.0 / len(available_connections) if available_connections else 0
            predictions = [(r, prob) for r in available_connections]
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions
    
    def predict_multi_step(self, enemy_id: str, current_region: str,
                          region_connections: Dict[str, List[str]],
                          game_phase: str, steps: int = 2) -> Dict[str, float]:
        """
        Predict enemy location probability distribution N steps ahead
        Returns: Dict of region -> probability
        """
        if steps < 1:
            return {current_region: 1.0}
        
        # Get step 1 predictions
        step1_preds = self.predict_next_region(
            enemy_id, current_region, 
            region_connections.get(current_region, []), 
            game_phase
        )
        
        if steps == 1:
            return {r: p for r, p in step1_preds}
        
        # For step 2, calculate probability of each path
        final_probs = defaultdict(float)
        
        for region1, prob1 in step1_preds:
            if prob1 < 0.05:  # Skip low probability paths
                continue
            
            # Get predictions from region1
            step2_preds = self.predict_next_region(
                enemy_id, region1,
                region_connections.get(region1, []),
                game_phase
            )
            
            for region2, prob2 in step2_preds:
                # Combined probability
                final_probs[region2] += prob1 * prob2
        
        # Normalize
        total = sum(final_probs.values())
        if total > 0:
            final_probs = {k: v / total for k, v in final_probs.items()}
        
        return dict(final_probs)
    
    def get_hot_zones(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """Get most frequented regions across all enemies"""
        return self.global_hot_zones.most_common(top_n)
    
    def get_danger_zones(self, our_region: str, enemy_regions: List[str],
                        region_connections: Dict[str, List[str]],
                        steps: int = 2) -> List[Tuple[str, float]]:
        """
        Identify dangerous zones where enemies are likely to converge
        Returns: List of (region, danger_score)
        """
        danger_scores = defaultdict(float)
        
        for enemy_id in enemy_regions:
            predictions = self.predict_multi_step(
                enemy_id, our_region,
                region_connections, "mid", steps
            )
            
            for region, prob in predictions.items():
                danger_scores[region] += prob
        
        # Sort by danger score
        sorted_danger = sorted(danger_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_danger
    
    def should_avoid_region(self, enemy_id: str, region: str,
                           current_region: str, game_phase: str,
                           available_connections: List[str],
                           threshold: float = 0.6) -> Tuple[bool, float]:
        """
        Determine if we should avoid a region due to high enemy prediction probability
        Returns: (should_avoid, probability)
        """
        predictions = self.predict_next_region(
            enemy_id, current_region, available_connections, game_phase
        )
        
        for pred_region, prob in predictions:
            if pred_region == region and prob >= threshold:
                return True, prob
        
        return False, 0.0
    
    def get_escape_routes(self, enemy_id: str, our_region: str,
                         available_connections: List[str],
                         game_phase: str) -> List[Tuple[str, float]]:
        """
        Get recommended escape routes (low enemy prediction probability)
        Returns: List of (region, safety_score) sorted by safety
        """
        predictions = self.predict_next_region(
            enemy_id, our_region, available_connections, game_phase
        )
        
        # Invert probabilities untuk safety score
        escape_routes = []
        for region, prob in predictions:
            safety = 1.0 - prob
            escape_routes.append((region, safety))
        
        # Sort by safety (highest first)
        escape_routes.sort(key=lambda x: x[1], reverse=True)
        return escape_routes
    
    def get_ambush_opportunities(self, enemy_id: str, enemy_region: str,
                                 region_connections: Dict[str, List[str]],
                                 our_weapon: str, game_phase: str) -> List[Tuple[str, float]]:
        """
        Find good ambush locations based on predicted enemy movement
        Returns: List of (region, ambush_score)
        """
        if enemy_id not in self.patterns:
            return []
        
        pattern = self.patterns[enemy_id]
        
        # Get regions enemy is likely to move to dari their current position
        predictions = self.predict_next_region(
            enemy_id, enemy_region,
            region_connections.get(enemy_region, []),
            game_phase
        )
        
        ambush_scores = []
        for region, prob in predictions:
            if prob < 0.2:  # Skip low probability targets
                continue
            
            score = prob
            
            # Bonus if enemy has visited this region frequently before
            visit_count = sum(1 for r, _ in pattern.region_sequence if r == region)
            score += min(0.3, visit_count * 0.05)
            
            # Bonus for high ground (sniper) or choke points (melee)
            # This would integrate dengan terrain data
            
            ambush_scores.append((region, score))
        
        ambush_scores.sort(key=lambda x: x[1], reverse=True)
        return ambush_scores[:3]  # Top 3 opportunities
    
    def get_movement_analysis(self, enemy_id: str) -> dict:
        """Get detailed movement analysis untuk an enemy"""
        if enemy_id not in self.patterns:
            return {"error": "No movement data available"}
        
        pattern = self.patterns[enemy_id]
        
        # Calculate movement stats
        if pattern.total_moves < 2:
            return {"error": "Insufficient movement data"}
        
        # Most common transitions
        top_transitions = []
        for from_region, transitions in pattern.transition_counts.items():
            for to_region, count in transitions.most_common(2):
                top_transitions.append({
                    "from": from_region,
                    "to": to_region,
                    "count": count
                })
        
        top_transitions.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total_moves": pattern.total_moves,
            "avg_time_per_region": round(pattern.avg_time_per_region, 2),
            "movement_frequency": round(pattern.movement_frequency, 3),
            "regions_visited": len(set(r for r, _ in pattern.region_sequence)),
            "last_seen_region": pattern.last_seen_region,
            "early_game_regions": len(pattern.early_game_regions),
            "mid_game_regions": len(pattern.mid_game_regions),
            "late_game_regions": len(pattern.late_game_regions),
            "top_transitions": top_transitions[:5]
        }


# Global instance
movement_predictor = MovementPredictor()


def record_enemy_sighting(enemy_id: str, region: str, alive_count: int):
    """Convenience function untuk record enemy sighting"""
    game_phase = "early" if alive_count >= 80 else "mid" if alive_count >= 30 else "late"
    movement_predictor.record_observation(enemy_id, region, game_phase, alive_count)


def record_enemy_movement(enemy_id: str, from_region: str, to_region: str, alive_count: int):
    """Convenience function untuk record enemy movement"""
    game_phase = "early" if alive_count >= 80 else "mid" if alive_count >= 30 else "late"
    movement_predictor.record_movement(enemy_id, from_region, to_region, game_phase, alive_count)


def get_movement_prediction(enemy_id: str, current_region: str,
                           connections: List[str], alive_count: int) -> List[Tuple[str, float]]:
    """Convenience function untuk get movement prediction"""
    game_phase = "early" if alive_count >= 80 else "mid" if alive_count >= 30 else "late"
    return movement_predictor.predict_next_region(enemy_id, current_region, connections, game_phase)


def get_escape_recommendations(enemy_id: str, our_region: str,
                               connections: List[str], alive_count: int) -> List[Tuple[str, float]]:
    """Get escape route recommendations"""
    game_phase = "early" if alive_count >= 80 else "mid" if alive_count >= 30 else "late"
    return movement_predictor.get_escape_routes(enemy_id, our_region, connections, game_phase)
