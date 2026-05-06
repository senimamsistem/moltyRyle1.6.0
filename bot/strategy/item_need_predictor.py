"""
Item Need Prediction System
Predicts item needs based on game phase, current loadout, and threats
Integrates with Strategy DNA for learning and auto-tuning item priorities
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from enum import Enum
from bot.utils.logger import get_logger

log = get_logger(__name__)


class GamePhase(Enum):
    EARLY = "early"      # 80+ alive
    MID = "mid"          # 30-79 alive
    LATE = "late"        # 10-29 alive
    ENDGAME = "endgame"  # <10 alive


@dataclass
class ItemNeedProfile:
    """Profile of predicted item needs"""
    game_phase: str
    alive_count: int
    
    # Weapon needs
    needs_weapon: bool
    needs_better_weapon: bool
    weapon_priority: int  # 0-100
    
    # Healing needs
    needs_healing: bool
    healing_urgency: str  # "none", "low", "medium", "critical"
    healing_target: int   # Target number of heals
    healing_deficit: int  # How many heals needed
    
    # Utility needs
    needs_binoculars: bool
    needs_map: bool
    needs_energy_drink: bool
    
    # Special situation needs
    needs_dz_escape: bool      # Need items untuk DZ escape
    needs_ep_recovery: bool    # Need EP items
    needs_finisher_setup: bool # Need items untuk finish fights
    
    # Overall assessment
    priority_item_types: List[str] = field(default_factory=list)
    shopping_list: List[Dict] = field(default_factory=list)  # What to look for
    can_drop_low_value: bool = False


class ItemNeedPredictor:
    """
    Predicts item needs based on current situation and game phase.
    Learns from match history untuk optimize predictions.
    """
    
    # Base healing targets per phase
    HEAL_TARGETS = {
        GamePhase.EARLY: 2,     # 2 heals cukup di early
        GamePhase.MID: 4,       # 4 heals untuk sustained combat
        GamePhase.LATE: 5,      # 5 heals untuk intense endgame
        GamePhase.ENDGAME: 6,   # Max heals untuk survival
    }
    
    # Weapon quality tiers
    WEAPON_TIERS = {
        "fist": 0,
        "dagger": 1,
        "bow": 1,
        "pistol": 2,
        "sword": 2,
        "katana": 3,
        "sniper": 3,
    }
    
    def __init__(self, dna_file: str = "data/strategy_dna.json"):
        self.dna_file = Path(dna_file)
        self._dna = self._load_dna()
        
    def _load_dna(self) -> Dict:
        """Load Strategy DNA untuk item priorities"""
        if self.dna_file.exists():
            try:
                with open(self.dna_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log.warning("📦 ITEM_NEED: Could not load DNA: %s", e)
        
        # Default DNA values
        return {
            "heal_stockpile_target": 4,
            "weapon_priority_boost": 100,
            "currency_priority": 300,
        }
    
    def _get_game_phase(self, alive_count: int) -> GamePhase:
        """Determine game phase dari alive count"""
        if alive_count >= 80:
            return GamePhase.EARLY
        elif alive_count >= 30:
            return GamePhase.MID
        elif alive_count >= 10:
            return GamePhase.LATE
        else:
            return GamePhase.ENDGAME
    
    def _get_weapon_tier(self, weapon: Optional[Dict]) -> int:
        """Get weapon quality tier"""
        if not weapon:
            return 0
        type_id = weapon.get("typeId", "fist").lower()
        return self.WEAPON_TIERS.get(type_id, 0)
    
    def _count_healing_items(self, inventory: List[Dict]) -> Tuple[int, int]:
        """Count healing items dan total healing potential"""
        heal_items = ["bandage", "medkit", "emergency_food"]
        count = 0
        total_heal_potential = 0
        
        for item in inventory:
            type_id = item.get("typeId", "").lower()
            if type_id == "bandage":
                count += 1
                total_heal_potential += 30
            elif type_id == "medkit":
                count += 1
                total_heal_potential += 50
            elif type_id == "emergency_food":
                count += 1
                total_heal_potential += 20
        
        return count, total_heal_potential
    
    def predict_needs(
        self,
        alive_count: int,
        inventory: List[Dict],
        equipped_weapon: Optional[Dict],
        current_hp: int,
        current_ep: int,
        max_ep: int,
        is_dz_threat: bool = False,
        recent_damage: int = 0,
        enemies_nearby: int = 0,
        has_binoculars: bool = False,
        has_map: bool = False
    ) -> ItemNeedProfile:
        """
        Predict item needs based on current situation.
        
        Returns ItemNeedProfile dengan detailed needs assessment.
        """
        phase = self._get_game_phase(alive_count)
        heal_count, heal_potential = self._count_healing_items(inventory)
        weapon_tier = self._get_weapon_tier(equipped_weapon)
        
        # Determine weapon needs
        needs_weapon = weapon_tier == 0
        needs_better_weapon = weapon_tier < 2 and phase in [GamePhase.MID, GamePhase.LATE]
        
        # Weapon priority calculation
        weapon_priority = 0
        if needs_weapon:
            weapon_priority = 100  # Critical - no weapon!
        elif needs_better_weapon:
            weapon_priority = 70 if phase == GamePhase.MID else 50
        
        # Healing needs assessment
        heal_target = self.HEAL_TARGETS.get(phase, 3)
        dna_target = self._dna.get("heal_stockpile_target", 4)
        
        # Adjust target based on situation
        if is_dz_threat:
            heal_target = max(heal_target, 4)  # Need heals untuk DZ
        if enemies_nearby > 0:
            heal_target = max(heal_target, 3)  # Need heals untuk combat
        if recent_damage > 30:
            heal_target += 1  # Taking damage - need more heals
            
        # Use DNA target jika lebih tinggi
        heal_target = max(heal_target, dna_target)
        
        healing_deficit = max(0, heal_target - heal_count)
        
        # Determine healing urgency
        if current_hp <= 30 or (healing_deficit >= 3 and current_hp < 50):
            healing_urgency = "critical"
        elif healing_deficit >= 2 or current_hp < 50:
            healing_urgency = "medium"
        elif healing_deficit >= 1:
            healing_urgency = "low"
        else:
            healing_urgency = "none"
            
        needs_healing = healing_urgency in ["medium", "critical"] or healing_deficit > 0
        
        # Utility needs
        needs_binoculars = not has_binoculars and phase in [GamePhase.MID, GamePhase.LATE]
        needs_map = not has_map and phase == GamePhase.EARLY
        needs_energy_drink = current_ep < max_ep * 0.5 and any(
            item.get("typeId", "").lower() == "energy_drink"
            for item in inventory
        ) == False
        
        # Special situation needs
        needs_dz_escape = is_dz_threat and (current_ep < 6 or heal_count < 2)
        needs_ep_recovery = current_ep < 4
        needs_finisher_setup = phase in [GamePhase.LATE, GamePhase.ENDGAME] and weapon_tier >= 2
        
        # Build priority list
        priority_items = []
        shopping_list = []
        can_drop_low = False
        
        # Priority 1: Weapon (if none)
        if needs_weapon:
            priority_items.append("weapon")
            shopping_list.append({
                "type": "weapon",
                "priority": "critical",
                "reason": "UNARMED - immediate danger",
                "acceptable_weapons": ["dagger", "sword", "katana", "bow", "pistol", "sniper"]
            })
        
        # Priority 2: Critical healing
        if healing_urgency == "critical":
            priority_items.append("healing_critical")
            shopping_list.append({
                "type": "healing",
                "priority": "critical",
                "reason": f"HP {current_hp} low atau heals deficit {healing_deficit}",
                "preferred": ["medkit", "bandage", "emergency_food"]
            })
        
        # Priority 3: Better weapon untuk late game
        if needs_better_weapon and phase in [GamePhase.LATE, GamePhase.ENDGAME]:
            priority_items.append("better_weapon")
            shopping_list.append({
                "type": "weapon",
                "priority": "high" if phase == GamePhase.LATE else "medium",
                "reason": f"Current {equipped_weapon.get('typeId', 'fist')} tier {weapon_tier} < ideal untuk {phase.value}",
                "acceptable_weapons": ["katana", "sniper", "sword", "pistol"]
            })
        
        # Priority 4: Medium healing
        if healing_urgency == "medium":
            priority_items.append("healing_medium")
            shopping_list.append({
                "type": "healing",
                "priority": "medium",
                "reason": f"Need {healing_deficit} more heals untuk target {heal_target}",
                "preferred": ["bandage", "emergency_food", "medkit"]
            })
        
        # Priority 5: EP recovery
        if needs_ep_recovery:
            priority_items.append("ep_recovery")
            shopping_list.append({
                "type": "ep_item",
                "priority": "high" if current_ep < 3 else "medium",
                "reason": f"EP {current_ep}/{max_ep} dangerously low",
                "preferred": ["energy_drink"]
            })
        
        # Priority 6: Utility items
        if needs_binoculars:
            priority_items.append("binoculars")
            shopping_list.append({
                "type": "utility",
                "priority": "low",
                "reason": "Vision advantage untuk scouting"
            })
        
        # Can drop low value items?
        can_drop_low = len(inventory) >= 8 and not needs_weapon and healing_urgency != "critical"
        
        profile = ItemNeedProfile(
            game_phase=phase.value,
            alive_count=alive_count,
            needs_weapon=needs_weapon,
            needs_better_weapon=needs_better_weapon,
            weapon_priority=weapon_priority,
            needs_healing=needs_healing,
            healing_urgency=healing_urgency,
            healing_target=heal_target,
            healing_deficit=healing_deficit,
            needs_binoculars=needs_binoculars,
            needs_map=needs_map,
            needs_energy_drink=needs_energy_drink,
            needs_dz_escape=needs_dz_escape,
            needs_ep_recovery=needs_ep_recovery,
            needs_finisher_setup=needs_finisher_setup,
            priority_item_types=priority_items,
            shopping_list=shopping_list,
            can_drop_low_value=can_drop_low
        )
        
        self._log_profile(profile)
        return profile
    
    def _log_profile(self, profile: ItemNeedProfile):
        """Log the need profile"""
        # Build status emoji
        if profile.needs_weapon:
            status = "🚨 NEED WEAPON CRITICAL"
        elif profile.healing_urgency == "critical":
            status = "🚨 NEED HEALING CRITICAL"
        elif profile.needs_better_weapon and profile.game_phase in ["late", "endgame"]:
            status = "⚔️ SEEK UPGRADE"
        elif profile.needs_healing:
            status = "🏥 NEED HEALS"
        elif profile.priority_item_types:
            status = "🛒 SHOPPING MODE"
        else:
            status = "✅ WELL EQUIPPED"
        
        log.info(
            "📦 ITEM_NEED [%s] %s: heals=%d/%d, weapon=%s, shopping=%s",
            profile.game_phase.upper(),
            status,
            profile.healing_target - profile.healing_deficit,
            profile.healing_target,
            "NEED" if profile.needs_weapon else ("UPGRADE" if profile.needs_better_weapon else "OK"),
            len(profile.shopping_list)
        )
        
        # Log detailed shopping list if any
        for item in profile.shopping_list[:3]:  # Top 3 only
            log.info(
                "   🛒 [%s] %s: %s",
                item["priority"].upper(),
                item["type"],
                item["reason"]
            )
    
    def get_pickup_recommendation(
        self,
        ground_item: Dict,
        profile: ItemNeedProfile,
        current_inventory: List[Dict]
    ) -> Dict:
        """
        Get recommendation untuk whether to pickup an item.
        
        Returns dict dengan:
        - should_pickup: bool
        - priority_score: int (0-100)
        - reason: str
        - drop_suggestion: Optional[str] - item to drop jika inventory full
        """
        item_type = ground_item.get("typeId", "").lower()
        category = ground_item.get("category", "").lower()
        
        # Check against shopping list
        for need in profile.shopping_list:
            need_type = need["type"]
            
            # Weapon match
            if need_type == "weapon" and category == "weapon":
                acceptable = need.get("acceptable_weapons", [])
                if not acceptable or item_type in acceptable:
                    return {
                        "should_pickup": True,
                        "priority_score": 100 if need["priority"] == "critical" else 80,
                        "reason": f"NEEDED: {need['reason']}",
                        "drop_suggestion": self._suggest_drop(current_inventory, profile)
                    }
            
            # Healing match
            if need_type == "healing" and item_type in ["bandage", "medkit", "emergency_food"]:
                return {
                    "should_pickup": True,
                    "priority_score": 90 if need["priority"] == "critical" else 70,
                    "reason": f"NEEDED: {need['reason']}",
                    "drop_suggestion": self._suggest_drop(current_inventory, profile)
                }
            
            # EP item match
            if need_type == "ep_item" and item_type == "energy_drink":
                return {
                    "should_pickup": True,
                    "priority_score": 75,
                    "reason": f"NEEDED: {need['reason']}",
                    "drop_suggestion": None
                }
        
        # Default: not needed
        return {
            "should_pickup": False,
            "priority_score": 0,
            "reason": "Not in current shopping list",
            "drop_suggestion": None
        }
    
    def _suggest_drop(
        self,
        inventory: List[Dict],
        profile: ItemNeedProfile
    ) -> Optional[str]:
        """Suggest an item to drop jika inventory full"""
        if len(inventory) < 10:
            return None
        
        # Priority untuk drop (lowest value first)
        drop_candidates = []
        
        for item in inventory:
            type_id = item.get("typeId", "").lower()
            
            # Energy drink - lowest priority
            if type_id == "energy_drink":
                drop_candidates.append((item["id"], 10, "energy_drink"))
            # Map - low priority jika sudah explored
            elif type_id == "map":
                drop_candidates.append((item["id"], 20, "map"))
            # Excess healing
            elif type_id in ["bandage", "emergency_food"]:
                if not profile.needs_healing:
                    drop_candidates.append((item["id"], 30, type_id))
            # Low tier weapon jika have better
            elif type_id == "dagger" and not profile.needs_weapon:
                drop_candidates.append((item["id"], 40, "dagger"))
        
        if drop_candidates:
            # Sort by priority (lowest first)
            drop_candidates.sort(key=lambda x: x[1])
            return drop_candidates[0][0]  # Return item ID
        
        return None
    
    def should_use_item_now(
        self,
        item: Dict,
        profile: ItemNeedProfile,
        current_hp: int,
        current_ep: int,
        max_ep: int
    ) -> bool:
        """
        Determine if an item should be used immediately.
        Used untuk "use low value items to make space" logic.
        """
        type_id = item.get("typeId", "").lower()
        
        # Energy drink - use jika EP low dan need space
        if type_id == "energy_drink":
            return current_ep < max_ep * 0.7 and profile.can_drop_low_value
        
        # Emergency food - use jika have excess heals
        if type_id == "emergency_food":
            return profile.healing_urgency == "none" and profile.healing_deficit < 0
        
        # Map - use immediately untuk reveal, frees space
        if type_id == "map":
            return True  # Always use map immediately
        
        return False


# Global predictor instance
_item_need_predictor: Optional[ItemNeedPredictor] = None


def get_predictor() -> ItemNeedPredictor:
    """Get global item need predictor instance"""
    global _item_need_predictor
    if _item_need_predictor is None:
        _item_need_predictor = ItemNeedPredictor()
    return _item_need_predictor


def predict_item_needs(
    alive_count: int,
    inventory: List[Dict],
    equipped_weapon: Optional[Dict],
    current_hp: int,
    current_ep: int,
    max_ep: int,
    **kwargs
) -> ItemNeedProfile:
    """Convenience function untuk predict item needs"""
    predictor = get_predictor()
    return predictor.predict_needs(
        alive_count=alive_count,
        inventory=inventory,
        equipped_weapon=equipped_weapon,
        current_hp=current_hp,
        current_ep=current_ep,
        max_ep=max_ep,
        **kwargs
    )


def get_pickup_recommendation(
    ground_item: Dict,
    profile: ItemNeedProfile,
    current_inventory: List[Dict]
) -> Dict:
    """Convenience function untuk get pickup recommendation"""
    predictor = get_predictor()
    return predictor.get_pickup_recommendation(ground_item, profile, current_inventory)


def should_use_item_now(
    item: Dict,
    profile: ItemNeedProfile,
    current_hp: int,
    current_ep: int,
    max_ep: int
) -> bool:
    """Convenience function untuk check if item should be used now"""
    predictor = get_predictor()
    return predictor.should_use_item_now(item, profile, current_hp, current_ep, max_ep)
