"""
Death Zone Predictive Avoidance System

Features:
1. Track DZ history dan patterns
2. Predict DZ shrink direction (center bias)
3. Identify safe zones dan danger zones
4. Recommend optimal positioning untuk avoid future DZ
5. Early warning system untuk DZ approach
"""
import json
import os
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from bot.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class DZSnapshot:
    """Snapshot of death zone state pada specific turn"""
    turn: int
    alive_count: int
    active_dz: Set[str] = field(default_factory=set)
    pending_dz: Set[str] = field(default_factory=set)
    safe_regions: Set[str] = field(default_factory=set)
    timestamp: float = 0.0


@dataclass
class RegionSafety:
    """Safety analysis untuk specific region"""
    region_id: str
    current_safe: bool
    turns_until_danger: int  # -1 if unknown, 0 if already danger, >0 if will be danger
    distance_to_center: int  # Estimated distance dari map center
    escape_routes: int  # Number of safe escape routes
    safety_score: float  # 0-1 scale, 1 = very safe, 0 = very dangerous
    is_center: bool = False  # Whether this is a center region
    is_edge: bool = False  # Whether this is an edge region


class DZPredictor:
    """
    Death Zone Predictive Avoidance System
    
    Analyzes DZ patterns dan predicts future DZ shrink untuk strategic positioning.
    """
    
    # History tracking
    _dz_history: List[DZSnapshot] = []
    _max_history_size: int = 20  # Keep last 20 snapshots
    
    # Pattern analysis
    _region_dz_history: Dict[str, List[int]] = defaultdict(list)  # region -> turns where DZ
    _center_regions: Set[str] = set()  # Regions identified sebagai map center
    _edge_regions: Set[str] = set()  # Regions identified sebagai map edge
    
    # Prediction state
    _last_prediction_turn: int = 0
    _predicted_next_dz: Set[str] = set()
    _safe_corridors: Set[str] = set()  # Regions likely to remain safe
    
    def __init__(self):
        self._dz_history: List[DZSnapshot] = []
        self._region_dz_history: Dict[str, List[int]] = defaultdict(list)
        self._center_regions: Set[str] = set()
        self._edge_regions: Set[str] = set()
        self._predicted_next_dz: Set[str] = set()
        self._safe_corridors: Set[str] = set()
    
    def record_dz_state(
        self,
        turn: int,
        alive_count: int,
        active_dz: List[str],
        pending_dz: List[str],
        all_regions: List[str],
        timestamp: float = 0.0
    ):
        """Record current DZ state untuk pattern analysis"""
        active_set = set(active_dz)
        pending_set = set(pending_dz)
        
        # Calculate safe regions
        safe_regions = set(all_regions) - active_set - pending_set
        
        snapshot = DZSnapshot(
            turn=turn,
            alive_count=alive_count,
            active_dz=active_set,
            pending_dz=pending_set,
            safe_regions=safe_regions,
            timestamp=timestamp
        )
        
        self._dz_history.append(snapshot)
        
        # Update region DZ history
        for region in active_dz:
            self._region_dz_history[region].append(turn)
        for region in pending_dz:
            # Track that this region was pending (about to become DZ)
            if turn not in self._region_dz_history[region]:
                self._region_dz_history[region].append(turn)
        
        # Maintain history size
        if len(self._dz_history) > self._max_history_size:
            self._dz_history.pop(0)
        
        # Update center/edge classification jika we have enough data
        if len(self._dz_history) >= 5:
            self._update_center_edge_classification()
        
        self._last_prediction_turn = turn
        log.debug("DZ_PREDICTOR: Recorded turn %d | Active=%d | Pending=%d | Safe=%d",
                  turn, len(active_set), len(pending_set), len(safe_regions))
    
    def _update_center_edge_classification(self):
        """
        Classify regions sebagai center atau edge based on DZ history.
        Center regions = less likely to become DZ early
        Edge regions = more likely to become DZ early
        """
        if not self._dz_history:
            return
        
        # Count how often each region became DZ across history
        dz_frequency: Dict[str, int] = defaultdict(int)
        total_turns = len(self._dz_history)
        
        for snapshot in self._dz_history:
            for region in snapshot.active_dz:
                dz_frequency[region] += 1
            for region in snapshot.pending_dz:
                dz_frequency[region] += 0.5  # Pending counts as half
        
        # Classify: high frequency = edge, low frequency = center
        for region, count in dz_frequency.items():
            frequency = count / total_turns if total_turns > 0 else 0
            
            if frequency >= 0.7:  # Became DZ in 70%+ of turns
                self._edge_regions.add(region)
                if region in self._center_regions:
                    self._center_regions.remove(region)
            elif frequency <= 0.2:  # Became DZ in 20% or less of turns
                self._center_regions.add(region)
                if region in self._edge_regions:
                    self._edge_regions.remove(region)
    
    def predict_next_dz(self, current_pending: List[str], turn: int) -> Set[str]:
        """
        Predict which regions will become DZ next.
        Returns set of predicted region IDs.
        """
        predicted = set(current_pending)  # Pending regions will definitely become DZ
        
        if len(self._dz_history) < 3:
            # Not enough history untuk meaningful prediction
            self._predicted_next_dz = predicted
            return predicted
        
        # Get current safe regions adjacent to pending/active DZ
        current_snapshot = self._dz_history[-1] if self._dz_history else None
        if not current_snapshot:
            self._predicted_next_dz = predicted
            return predicted
        
        # Predict: regions adjacent to current DZ are at risk
        # This is a simplified model - real DZ shrinks inward from edges
        
        # Add edge regions yang belum DZ sebagai high risk
        for region in self._edge_regions:
            if (region not in current_snapshot.active_dz and 
                region not in current_snapshot.pending_dz and
                region in current_snapshot.safe_regions):
                # Check if this edge region is adjacent to current DZ
                if self._is_adjacent_to_dz(region, current_snapshot):
                    predicted.add(region)
        
        self._predicted_next_dz = predicted
        return predicted
    
    def _is_adjacent_to_dz(self, region: str, snapshot: DZSnapshot) -> bool:
        """Check if region is adjacent to active/pending DZ"""
        # This would need actual map topology - simplified version
        # Assume regions with similar IDs are adjacent
        # In real implementation, this would check actual connections
        return True  # Simplified - treat all edge regions sebagai adjacent
    
    def calculate_region_safety(
        self,
        region_id: str,
        active_dz: List[str],
        pending_dz: List[str],
        turn: int,
        connections: List[str]
    ) -> RegionSafety:
        """
        Calculate comprehensive safety analysis untuk region.
        """
        is_active_dz = region_id in active_dz
        is_pending_dz = region_id in pending_dz
        is_center_region = region_id in self._center_regions
        is_edge_region = region_id in self._edge_regions
        is_safe = not is_active_dz and not is_pending_dz  # Both active and pending are not "safe"
        
        # Calculate turns until danger
        if is_active_dz:
            turns_until_danger = 0  # Already dangerous
        elif is_pending_dz:
            turns_until_danger = 1  # Will be dangerous next turn
        elif region_id in self._predicted_next_dz:
            turns_until_danger = 2  # Predicted to be dangerous soon
        elif is_edge_region:
            turns_until_danger = 3  # Edge region, at risk
        elif is_center_region:
            turns_until_danger = -1  # Center region, likely safe longer
        else:
            turns_until_danger = -1  # Unknown
        
        # Estimate distance to center (simplified)
        distance_to_center = self._estimate_distance_to_center(region_id)
        
        # Count safe escape routes
        safe_exits = sum(1 for conn in connections if conn not in active_dz and conn not in pending_dz)
        
        # Calculate safety score (0-1)
        safety_score = self._calculate_safety_score(
            is_safe=is_safe and not is_pending_dz,  # Pending DZ gets 0 score
            turns_until_danger=turns_until_danger,
            distance_to_center=distance_to_center,
            safe_exits=safe_exits,
            is_center=is_center_region,
            is_edge=is_edge_region
        )
        
        return RegionSafety(
            region_id=region_id,
            current_safe=is_safe,
            turns_until_danger=turns_until_danger,
            distance_to_center=distance_to_center,
            escape_routes=safe_exits,
            safety_score=safety_score,
            is_center=is_center_region,
            is_edge=is_edge_region
        )
    
    def _estimate_distance_to_center(self, region_id: str) -> int:
        """Estimate distance dari region to map center"""
        if region_id in self._center_regions:
            return 0
        elif region_id in self._edge_regions:
            return 3  # Assume edge is 3 steps from center
        else:
            return 1  # Unknown, assume close
    
    def _calculate_safety_score(
        self,
        is_safe: bool,
        turns_until_danger: int,
        distance_to_center: int,
        safe_exits: int,
        is_center: bool,
        is_edge: bool
    ) -> float:
        """Calculate 0-1 safety score untuk region"""
        if not is_safe:
            return 0.0  # Already DZ or pending
        
        score = 1.0
        
        # Deduct for imminent danger
        if turns_until_danger == 1:
            score -= 0.4
        elif turns_until_danger == 2:
            score -= 0.25
        elif turns_until_danger == 3:
            score -= 0.15
        
        # Bonus for center proximity
        score += (3 - min(distance_to_center, 3)) * 0.1
        
        # Bonus for escape routes
        score += min(safe_exits, 3) * 0.05
        
        # Classification bonus/penalty
        if is_center:
            score += 0.1
        if is_edge:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def get_safe_positioning_recommendation(
        self,
        current_region: str,
        available_regions: List[str],
        active_dz: List[str],
        pending_dz: List[str],
        turn: int,
        our_hp: int,
        has_weapon: bool
    ) -> Tuple[str, float, str]:
        """
        Recommend safest region untuk positioning.
        
        Returns: (recommended_region, safety_score, reason)
        """
        if not available_regions:
            return current_region, 0.0, "No available regions"
        
        # Calculate safety untuk each region
        region_safety = {}
        for region in available_regions:
            # Get connections for this region (simplified - would need actual data)
            safety = self.calculate_region_safety(
                region_id=region,
                active_dz=active_dz,
                pending_dz=pending_dz,
                turn=turn,
                connections=[]  # Would need actual connections
            )
            region_safety[region] = safety
        
        # Find safest region
        safest_region = max(region_safety.keys(), key=lambda r: region_safety[r].safety_score)
        safest_data = region_safety[safest_region]
        
        # Generate reason
        reason_parts = []
        if safest_data.is_center or safest_region in self._center_regions:
            reason_parts.append("center region (long-term safety)")
        if safest_data.turns_until_danger == -1:
            reason_parts.append("no DZ threat predicted")
        elif safest_data.turns_until_danger >= 3:
            reason_parts.append(f"{safest_data.turns_until_danger} turns until danger")
        if safest_data.escape_routes >= 2:
            reason_parts.append(f"{safest_data.escape_routes} escape routes")
        
        reason = " | ".join(reason_parts) if reason_parts else "highest safety score"
        
        return safest_region, safest_data.safety_score, reason
    
    def get_dz_early_warning(
        self,
        region_id: str,
        active_dz: List[str],
        pending_dz: List[str],
        turn: int,
        turns_ahead: int = 3
    ) -> Dict:
        """
        Get early warning tentang DZ approach untuk specific region.
        
        Returns dict dengan:
        - warning_level: 'none', 'low', 'medium', 'high', 'critical'
        - turns_until_danger: int
        - recommended_action: str
        """
        is_active = region_id in active_dz
        is_pending = region_id in pending_dz
        
        if is_active:
            return {
                "warning_level": "critical",
                "turns_until_danger": 0,
                "recommended_action": "ESCAPE IMMEDIATELY - Already in Death Zone!"
            }
        
        if is_pending:
            return {
                "warning_level": "critical",
                "turns_until_danger": 1,
                "recommended_action": "ESCAPE NOW - Will become Death Zone next turn!"
            }
        
        # Check if in predicted next DZ
        if region_id in self._predicted_next_dz:
            return {
                "warning_level": "high",
                "turns_until_danger": 2,
                "recommended_action": "Move to safer position - Predicted Death Zone soon"
            }
        
        # Check if edge region (higher risk)
        if region_id in self._edge_regions:
            return {
                "warning_level": "medium",
                "turns_until_danger": 3,
                "recommended_action": "Caution - Edge region, monitor DZ spread"
            }
        
        # Check if center region (lower risk)
        if region_id in self._center_regions:
            return {
                "warning_level": "low",
                "turns_until_danger": -1,
                "recommended_action": "Safe position - Center region, low DZ risk"
            }
        
        # Unknown risk
        return {
            "warning_level": "low",
            "turns_until_danger": -1,
            "recommended_action": "Monitor DZ - Unknown region risk level"
        }
    
    def get_center_bias_recommendation(
        self,
        current_region: str,
        available_regions: List[str],
        alive_count: int
    ) -> Tuple[str, str]:
        """
        Recommend moving toward center untuk late game safety.
        
        Returns: (recommended_region, reason)
        """
        if alive_count > 50:
            # Early game - don't force center yet
            return current_region, "Early game - no center bias needed"
        
        # Find center-most region dari available
        center_candidates = [r for r in available_regions if r in self._center_regions]
        
        if center_candidates:
            # Prefer center regions
            return center_candidates[0], "Late game - prioritize center region for safety"
        
        # No center region available, move away dari edge
        edge_avoided = [r for r in available_regions if r not in self._edge_regions]
        
        if edge_avoided:
            return edge_avoided[0], "Late game - avoid edge regions"
        
        return current_region, "No better options available"
    
    def get_summary(self) -> Dict:
        """Get summary of DZ predictor state"""
        return {
            "history_size": len(self._dz_history),
            "center_regions_count": len(self._center_regions),
            "edge_regions_count": len(self._edge_regions),
            "predicted_next_dz_count": len(self._predicted_next_dz),
            "last_prediction_turn": self._last_prediction_turn,
            "center_regions": list(self._center_regions)[:10],  # Sample
            "edge_regions": list(self._edge_regions)[:10],  # Sample
        }


# Global instance
dz_predictor = DZPredictor()


def record_dz_state(
    turn: int,
    alive_count: int,
    active_dz: List[str],
    pending_dz: List[str],
    all_regions: List[str],
    timestamp: float = 0.0
):
    """Convenience function untuk record DZ state"""
    dz_predictor.record_dz_state(turn, alive_count, active_dz, pending_dz, all_regions, timestamp)


def get_region_safety(
    region_id: str,
    active_dz: List[str],
    pending_dz: List[str],
    turn: int,
    connections: List[str]
) -> RegionSafety:
    """Convenience function untuk get region safety"""
    return dz_predictor.calculate_region_safety(region_id, active_dz, pending_dz, turn, connections)


def get_dz_warning(
    region_id: str,
    active_dz: List[str],
    pending_dz: List[str],
    turn: int
) -> Dict:
    """Convenience function untuk get DZ warning"""
    return dz_predictor.get_dz_early_warning(region_id, active_dz, pending_dz, turn)


def recommend_safe_position(
    current_region: str,
    available_regions: List[str],
    active_dz: List[str],
    pending_dz: List[str],
    turn: int,
    our_hp: int,
    has_weapon: bool
) -> Tuple[str, float, str]:
    """Convenience function untuk get safe positioning"""
    return dz_predictor.get_safe_positioning_recommendation(
        current_region, available_regions, active_dz, pending_dz, turn, our_hp, has_weapon
    )


def get_center_recommendation(
    current_region: str,
    available_regions: List[str],
    alive_count: int
) -> Tuple[str, str]:
    """Convenience function untuk get center bias recommendation"""
    return dz_predictor.get_center_bias_recommendation(current_region, available_regions, alive_count)
