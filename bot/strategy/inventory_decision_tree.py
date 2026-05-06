"""
Drop vs Keep Decision Trees
No-Drop Inventory Strategy untuk Molty Royale

Karena game tidak memiliki drop action, setiap pickup adalah permanent.
Sistem ini menggunakan decision trees untuk:
1. Pre-pickup impact analysis
2. Endgame slot preservation
3. Aggressive consumable usage untuk critical space
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict

from bot.utils.logger import get_logger
from bot.strategy.item_need_predictor import ItemNeedProfile, GamePhase

log = get_logger(__name__)


class SlotLockReason(Enum):
    """Reason why a slot is locked (can't be freed)"""
    CRITICAL_WEAPON = "critical_weapon"      # Best weapon we have
    ESSENTIAL_HEALS = "essential_heals"      # Minimum heals needed
    UTILITY_LOCKED = "utility_locked"        # Binoculars, etc
    VALUABLE_ITEM = "valuable_item"          # High value item
    CONSUMABLE_NOW = "consumable_now"        # Can use now to free
    JUNK = "junk"                            # Low value, can waste


@dataclass
class SlotAnalysis:
    """Analysis of a single inventory slot"""
    slot_index: int
    item_id: str
    item_type: str
    item_value: int
    can_free: bool                          # Can we free this slot?
    free_method: str                      # "use", "waste", "equip"
    lock_reason: SlotLockReason
    opportunity_cost: int                 # What we lose by keeping this


@dataclass
class PickupImpact:
    """Impact analysis of picking up an item"""
    should_pickup: bool
    item_id: str
    item_type: str
    item_value: int
    
    # Impact analysis
    slots_after: int                      # Slots remaining after pickup
    locked_slots: int                     # Slots that can't be freed
    flexible_slots: int                   # Slots that can be freed
    
    # Risk assessment
    future_risk: str                      # "low", "medium", "high", "critical"
    risk_reason: str
    
    # Recommended actions
    pre_pickup_actions: List[Dict]        # Actions to take before pickup
    post_pickup_flexibility: int          # How flexible inventory will be
    
    # Endgame impact
    endgame_readiness: int                # 0-100 score
    can_get_tier3_weapon: bool            # Will we have space for katana/sniper?


class InventoryDecisionTree:
    """
    Decision tree untuk no-drop inventory management.
    
    Core principle: Every pickup is permanent, so analyze before commit.
    """
    
    # Value thresholds
    TIER3_WEAPON_VALUE = 135              # Katana/sniper base value
    TIER2_WEAPON_VALUE = 120              # Sword/pistol base value
    TIER1_WEAPON_VALUE = 110              # Dagger/bow base value
    
    # Slot reservation for endgame
    ENDGAME_RESERVED_SLOTS = 3            # Save 3 slots untuk T3 weapon + 2 heals
    
    def __init__(self):
        self._analyze_history = []
    
    def analyze_slot(self, item: Dict, slot_index: int, game_phase: GamePhase,
                     current_hp: int, current_ep: int, max_ep: int,
                     equipped_weapon: Optional[Dict]) -> SlotAnalysis:
        """
        Analyze single inventory slot - can we free it if needed?
        """
        item_id = item.get("id", f"slot-{slot_index}")
        item_type = item.get("typeId", "").lower()
        category = item.get("category", "").lower()
        
        # Calculate base value
        item_value = self._calculate_item_value(
            item, current_hp, current_ep, max_ep, game_phase
        )
        
        # Determine if slot can be freed
        can_free = False
        free_method = "none"
        lock_reason = SlotLockReason.VALUABLE_ITEM
        opportunity_cost = 0
        
        # Map - can always use immediately
        if item_type == "map":
            can_free = True
            free_method = "use"
            lock_reason = SlotLockReason.CONSUMABLE_NOW
            opportunity_cost = 10
        
        # Energy drink - can use if EP not full
        elif item_type == "energy_drink":
            if current_ep < max_ep:
                can_free = True
                free_method = "use"
                lock_reason = SlotLockReason.CONSUMABLE_NOW
                opportunity_cost = 15
            else:
                can_free = True
                free_method = "waste"  # Use even if EP full untuk space
                lock_reason = SlotLockReason.JUNK
                opportunity_cost = 20
        
        # Healing items
        elif item_type in ["bandage", "emergency_food"]:
            # Can use if HP not full
            if current_hp < 100:
                can_free = True
                free_method = "use"
                lock_reason = SlotLockReason.CONSUMABLE_NOW
                opportunity_cost = 25
            else:
                # HP full - can waste untuk space if needed
                can_free = True
                free_method = "waste"
                lock_reason = SlotLockReason.JUNK
                opportunity_cost = 30
        
        elif item_type == "medkit":
            # Medkit too valuable to waste casually
            can_free = current_hp < 50  # Only use if actually needed
            free_method = "use" if can_free else "none"
            lock_reason = SlotLockReason.ESSENTIAL_HEALS if not can_free else SlotLockReason.CONSUMABLE_NOW
            opportunity_cost = 50 if not can_free else 40
        
        # Weapons
        elif category == "weapon":
            equipped_type = equipped_weapon.get("typeId", "").lower() if equipped_weapon else "fist"
            
            if item_type in ["katana", "sniper"]:
                # Tier 3 - never drop, equip if better
                can_free = False
                free_method = "none"
                lock_reason = SlotLockReason.CRITICAL_WEAPON
                opportunity_cost = 200
            
            elif item_type in ["sword", "pistol"]:
                # Tier 2 - keep unless have T3
                if equipped_type in ["katana", "sniper"]:
                    # Have better equipped, can waste if desperate
                    can_free = True
                    free_method = "waste"
                    lock_reason = SlotLockReason.JUNK
                    opportunity_cost = 60
                else:
                    can_free = False
                    lock_reason = SlotLockReason.CRITICAL_WEAPON
                    opportunity_cost = 150
            
            elif item_type in ["dagger", "bow"]:
                # Tier 1 - disposable if have T2+
                if equipped_type in ["sword", "pistol", "katana", "sniper"]:
                    can_free = True
                    free_method = "waste"
                    lock_reason = SlotLockReason.JUNK
                    opportunity_cost = 40
                else:
                    can_free = False
                    lock_reason = SlotLockReason.CRITICAL_WEAPON
                    opportunity_cost = 100
            
            else:  # Fist or unknown
                can_free = True
                free_method = "waste"
                lock_reason = SlotLockReason.JUNK
                opportunity_cost = 10
        
        # Currency - always valuable
        elif item_type in ["moltz", "rewards"]:
            can_free = False
            free_method = "none"
            lock_reason = SlotLockReason.VALUABLE_ITEM
            opportunity_cost = 300
        
        # Binoculars - utility, keep in mid/late
        elif item_type == "binoculars":
            if game_phase in [GamePhase.MID, GamePhase.LATE, GamePhase.ENDGAME]:
                can_free = False
                lock_reason = SlotLockReason.UTILITY_LOCKED
                opportunity_cost = 80
            else:
                can_free = True
                free_method = "waste"
                lock_reason = SlotLockReason.JUNK
                opportunity_cost = 30
        
        # Default
        else:
            can_free = True
            free_method = "waste"
            lock_reason = SlotLockReason.JUNK
            opportunity_cost = 20
        
        return SlotAnalysis(
            slot_index=slot_index,
            item_id=item_id,
            item_type=item_type,
            item_value=item_value,
            can_free=can_free,
            free_method=free_method,
            lock_reason=lock_reason,
            opportunity_cost=opportunity_cost
        )
    
    def analyze_inventory(self, inventory: List[Dict], game_phase: GamePhase,
                          current_hp: int, current_ep: int, max_ep: int,
                          equipped_weapon: Optional[Dict]) -> List[SlotAnalysis]:
        """
        Analyze entire inventory - classify each slot.
        """
        analysis = []
        for i, item in enumerate(inventory):
            if not isinstance(item, dict):
                continue
            slot_analysis = self.analyze_slot(
                item, i, game_phase, current_hp, current_ep, max_ep, equipped_weapon
            )
            analysis.append(slot_analysis)
        
        return analysis
    
    def evaluate_pickup_impact(self, ground_item: Dict, inventory: List[Dict],
                               item_need_profile: ItemNeedProfile,
                               current_hp: int, current_ep: int, max_ep: int,
                               equipped_weapon: Optional[Dict]) -> PickupImpact:
        """
        Evaluate impact of picking up an item.
        This is the main decision tree entry point.
        """
        item_id = ground_item.get("id", "unknown")
        item_type = ground_item.get("typeId", "").lower()
        category = ground_item.get("category", "").lower()
        
        # Current inventory state
        current_slots = len(inventory)
        max_slots = 10
        
        # Analyze current inventory
        game_phase = GamePhase(item_need_profile.game_phase)
        slot_analysis = self.analyze_inventory(
            inventory, game_phase, current_hp, current_ep, max_ep, equipped_weapon
        )
        
        # Count flexible vs locked slots
        locked_slots = sum(1 for s in slot_analysis if not s.can_free)
        flexible_slots = sum(1 for s in slot_analysis if s.can_free)
        
        # Calculate item value
        item_value = self._calculate_ground_item_value(
            ground_item, item_need_profile, game_phase
        )
        
        # Decision tree logic
        pre_pickup_actions = []
        should_pickup = False
        future_risk = "low"
        risk_reason = ""
        endgame_readiness = 100
        can_get_tier3 = True
        
        # Case 1: Inventory not full - easy decision
        if current_slots < max_slots:
            should_pickup = self._should_pickup_not_full(
                ground_item, item_need_profile, item_value
            )
            future_risk = "low"
            risk_reason = "Inventory has space"
        
        # Case 2: Inventory full - need complex analysis
        else:
            result = self._analyze_full_inventory_pickup(
                ground_item, slot_analysis, item_need_profile,
                current_hp, current_ep, max_ep, equipped_weapon
            )
            should_pickup = result["should_pickup"]
            pre_pickup_actions = result["pre_actions"]
            future_risk = result["future_risk"]
            risk_reason = result["risk_reason"]
            endgame_readiness = result["endgame_readiness"]
            can_get_tier3 = result["can_get_tier3"]
        
        # Calculate slots after pickup
        slots_after = max_slots - (current_slots + 1 - len(pre_pickup_actions))
        
        return PickupImpact(
            should_pickup=should_pickup,
            item_id=item_id,
            item_type=item_type,
            item_value=item_value,
            slots_after=slots_after,
            locked_slots=locked_slots,
            flexible_slots=flexible_slots - len(pre_pickup_actions),
            future_risk=future_risk,
            risk_reason=risk_reason,
            pre_pickup_actions=pre_pickup_actions,
            post_pickup_flexibility=flexible_slots - len(pre_pickup_actions),
            endgame_readiness=endgame_readiness,
            can_get_tier3_weapon=can_get_tier3
        )
    
    def _should_pickup_not_full(self, ground_item: Dict, 
                                item_need_profile: ItemNeedProfile,
                                item_value: int) -> bool:
        """Decision when inventory not full"""
        item_type = ground_item.get("typeId", "").lower()
        
        # Always pickup needed items
        if item_need_profile.needs_weapon and ground_item.get("category") == "weapon":
            return True
        
        if item_need_profile.needs_healing and item_type in ["bandage", "medkit", "emergency_food"]:
            return True
        
        # Always pickup high value
        if item_value >= 100:
            return True
        
        # Low value items - be selective
        if item_value < 30:
            # Only if really need it
            return item_type in [t for t in item_need_profile.priority_item_types]
        
        return True
    
    def _analyze_full_inventory_pickup(self, ground_item: Dict,
                                       slot_analysis: List[SlotAnalysis],
                                       item_need_profile: ItemNeedProfile,
                                       current_hp: int, current_ep: int, max_ep: int,
                                       equipped_weapon: Optional[Dict]) -> Dict:
        """
        Complex analysis when inventory full.
        Returns dict dengan should_pickup, pre_actions, risk, etc.
        """
        item_type = ground_item.get("typeId", "").lower()
        category = ground_item.get("category", "").lower()
        game_phase = GamePhase(item_need_profile.game_phase)
        
        result = {
            "should_pickup": False,
            "pre_actions": [],
            "future_risk": "high",
            "risk_reason": "",
            "endgame_readiness": 50,
            "can_get_tier3": False
        }
        
        # Find slots we can free (sorted by lowest opportunity cost first)
        freeable_slots = [s for s in slot_analysis if s.can_free]
        freeable_slots.sort(key=lambda s: s.opportunity_cost)
        
        # CRITICAL: Need weapon and see weapon on ground
        if item_need_profile.needs_weapon and category == "weapon":
            # AGGRESSIVE: Use ALL freeable consumables untuk space
            for slot in freeable_slots:
                if slot.free_method in ["use", "waste"]:
                    result["pre_actions"].append({
                        "action": "use_item" if slot.free_method == "use" else "use_waste",
                        "item_id": slot.item_id,
                        "item_type": slot.item_type,
                        "reason": f"Making space for CRITICAL weapon pickup"
                    })
                    if len(result["pre_actions"]) >= 1:  # Need at least 1 slot
                        break
            
            if result["pre_actions"]:
                result["should_pickup"] = True
                result["future_risk"] = "medium"
                result["risk_reason"] = "Used consumables untuk critical weapon"
                result["can_get_tier3"] = True
                log.warning("🚨 INVENTORY_CRISIS: Using %d items untuk WEAPON pickup!", 
                          len(result["pre_actions"]))
            else:
                result["risk_reason"] = "No freeable slots untuk weapon - STUCK!"
                result["future_risk"] = "critical"
        
        # HIGH: Late game + see T3 weapon
        elif (game_phase in [GamePhase.LATE, GamePhase.ENDGAME] and 
              item_type in ["katana", "sniper"]):
            
            # Check if current weapon is worse
            equipped_type = equipped_weapon.get("typeId", "").lower() if equipped_weapon else "fist"
            if equipped_type not in ["katana", "sniper"]:
                # UPGRADE OPPORTUNITY - be aggressive
                for slot in freeable_slots[:2]:  # Use up to 2 slots
                    result["pre_actions"].append({
                        "action": "use_waste" if slot.free_method == "waste" else "use_item",
                        "item_id": slot.item_id,
                        "item_type": slot.item_type,
                        "reason": f"Making space for T3 WEAPON upgrade!"
                    })
                
                if result["pre_actions"]:
                    result["should_pickup"] = True
                    result["future_risk"] = "low"
                    result["risk_reason"] = "T3 weapon upgrade - worth the cost"
                    result["can_get_tier3"] = True
                    result["endgame_readiness"] = 95
                    log.info("⚔️ UPGRADE_MODE: Using items untuk T3 weapon pickup")
        
        # MEDIUM: Healing critical
        elif item_need_profile.healing_urgency == "critical" and item_type in ["bandage", "medkit"]:
            # Use ONE freeable slot untuk healing
            if freeable_slots:
                slot = freeable_slots[0]
                result["pre_actions"].append({
                    "action": slot.free_method,
                    "item_id": slot.item_id,
                    "item_type": slot.item_type,
                    "reason": "Making space untuk CRITICAL healing"
                })
                result["should_pickup"] = True
                result["future_risk"] = "medium"
                result["risk_reason"] = "Critical healing needed"
        
        # LOW: Better weapon than current
        elif category == "weapon" and self._is_weapon_upgrade(ground_item, equipped_weapon):
            # Only if easy space available
            easy_slots = [s for s in freeable_slots if s.free_method == "use" and s.opportunity_cost < 30]
            if easy_slots:
                result["pre_actions"].append({
                    "action": "use_item",
                    "item_id": easy_slots[0].item_id,
                    "item_type": easy_slots[0].item_type,
                    "reason": "Making space untuk weapon upgrade"
                })
                result["should_pickup"] = True
                result["future_risk"] = "low"
                result["risk_reason"] = "Weapon upgrade dengan easy slot"
        
        # Calculate endgame readiness
        if result["should_pickup"]:
            remaining_freeable = len(freeable_slots) - len(result["pre_actions"])
            if remaining_freeable >= 2:
                result["can_get_tier3"] = True
                result["endgame_readiness"] = 90
            elif remaining_freeable >= 1:
                result["can_get_tier3"] = True
                result["endgame_readiness"] = 70
            else:
                result["can_get_tier3"] = False
                result["endgame_readiness"] = 40
        
        return result
    
    def _calculate_item_value(self, item: Dict, current_hp: int, current_ep: int,
                              max_ep: int, game_phase: GamePhase) -> int:
        """Calculate value of item in inventory"""
        item_type = item.get("typeId", "").lower()
        category = item.get("category", "").lower()
        
        # Currency - always max value
        if item_type in ["moltz", "rewards"]:
            return 300
        
        # Weapons
        if category == "weapon":
            if item_type == "katana":
                return 135
            elif item_type == "sniper":
                return 135
            elif item_type in ["sword", "pistol"]:
                return 120
            elif item_type in ["dagger", "bow"]:
                return 110
            else:
                return 100
        
        # Healing - dynamic based on need
        if item_type == "medkit":
            return 50 if current_hp < 50 else 35
        elif item_type == "bandage":
            # More valuable when low on heals
            if current_hp < 80:
                return 30
            else:
                return 20
        elif item_type == "emergency_food":
            return 20 if current_hp < 100 else 15
        
        # Utility
        if item_type == "binoculars":
            return 55 if game_phase in [GamePhase.MID, GamePhase.LATE] else 30
        
        if item_type == "map":
            return 30  # Can use immediately
        
        if item_type == "energy_drink":
            return 25 if current_ep < max_ep else 10
        
        return 10  # Default low value
    
    def _calculate_ground_item_value(self, item: Dict, item_need_profile: ItemNeedProfile,
                                     game_phase: GamePhase) -> int:
        """Calculate value of item on ground (with need bonus)"""
        base_value = self._calculate_item_value(
            item, 100, 10, 10, game_phase
        )
        
        item_type = item.get("typeId", "").lower()
        category = item.get("category", "").lower()
        
        # Bonus for needed items
        if item_need_profile.needs_weapon and category == "weapon":
            base_value += 200  # Critical bonus
        
        if item_need_profile.needs_healing and item_type in ["bandage", "medkit", "emergency_food"]:
            urgency_bonus = {"critical": 150, "medium": 80, "low": 40, "none": 0}
            base_value += urgency_bonus.get(item_need_profile.healing_urgency, 0)
        
        if item_need_profile.needs_binoculars and item_type == "binoculars":
            base_value += 50
        
        # Late game weapon bonus
        if game_phase in [GamePhase.LATE, GamePhase.ENDGAME] and item_type in ["katana", "sniper"]:
            base_value += 100
        
        return base_value
    
    def _is_weapon_upgrade(self, ground_weapon: Dict, equipped_weapon: Optional[Dict]) -> bool:
        """Check if ground weapon is upgrade dari equipped"""
        ground_type = ground_weapon.get("typeId", "").lower()
        equipped_type = equipped_weapon.get("typeId", "").lower() if equipped_weapon else "fist"
        
        tier_map = {
            "fist": 0, "dagger": 1, "bow": 1,
            "pistol": 2, "sword": 2,
            "katana": 3, "sniper": 3
        }
        
        ground_tier = tier_map.get(ground_type, 0)
        equipped_tier = tier_map.get(equipped_type, 0)
        
        return ground_tier > equipped_tier
    
    def get_space_creation_plan(self, inventory: List[Dict], slots_needed: int,
                                game_phase: GamePhase, current_hp: int, 
                                current_ep: int, max_ep: int,
                                equipped_weapon: Optional[Dict]) -> List[Dict]:
        """
        Generate plan untuk create N slots dengan using/wasting items.
        Returns list of actions to take.
        """
        if slots_needed <= 0:
            return []
        
        slot_analysis = self.analyze_inventory(
            inventory, game_phase, current_hp, current_ep, max_ep, equipped_weapon
        )
        
        # Sort by easiest to free (low opportunity cost first)
        freeable = [s for s in slot_analysis if s.can_free]
        freeable.sort(key=lambda s: (s.opportunity_cost, s.free_method != "use"))
        
        plan = []
        for slot in freeable[:slots_needed]:
            action = {
                "action": "use_item" if slot.free_method == "use" else "use_waste",
                "item_id": slot.item_id,
                "item_type": slot.item_type,
                "reason": f"Creating space ({slot.free_method}) - opportunity cost: {slot.opportunity_cost}"
            }
            plan.append(action)
        
        if len(plan) < slots_needed:
            log.warning("🚨 CANNOT_CREATE_SPACE: Need %d slots, can only free %d", 
                      slots_needed, len(plan))
        
        return plan
    
    def analyze_endgame_readiness(self, inventory: List[Dict], 
                                  equipped_weapon: Optional[Dict]) -> Dict:
        """
        Analyze if inventory ready untuk endgame (<10 players).
        Check if we have space untuk T3 weapon + minimum heals.
        """
        equipped_type = equipped_weapon.get("typeId", "").lower() if equipped_weapon else "fist"
        
        # Count items
        total_slots = len(inventory)
        free_slots = 10 - total_slots
        
        # Check equipped
        has_t3_equipped = equipped_type in ["katana", "sniper"]
        
        # Count heals
        heal_count = sum(1 for i in inventory 
                        if i.get("typeId", "").lower() in ["bandage", "medkit", "emergency_food"])
        
        # Check if T3 weapon in inventory
        has_t3_in_inv = any(i.get("typeId", "").lower() in ["katana", "sniper"] 
                           for i in inventory)
        
        # Calculate flexibility
        game_phase = GamePhase.ENDGAME
        slot_analysis = self.analyze_inventory(
            inventory, game_phase, 100, 10, 10, equipped_weapon
        )
        can_free = sum(1 for s in slot_analysis if s.can_free)
        
        # Endgame readiness
        readiness = 0
        issues = []
        
        if has_t3_equipped:
            readiness += 50
        elif has_t3_in_inv:
            readiness += 30
            issues.append("Have T3 weapon but not equipped")
        else:
            issues.append("No T3 weapon")
        
        if heal_count >= 4:
            readiness += 30
        elif heal_count >= 2:
            readiness += 15
            issues.append("Low heals for endgame")
        else:
            issues.append("CRITICAL: No heals!")
        
        if free_slots >= 2 or can_free >= 2:
            readiness += 20
        elif free_slots >= 1 or can_free >= 1:
            readiness += 10
        else:
            issues.append("Inventory locked - no flexibility")
        
        return {
            "readiness_score": min(100, readiness),
            "has_t3_weapon": has_t3_equipped or has_t3_in_inv,
            "heal_count": heal_count,
            "free_slots": free_slots,
            "can_free_slots": can_free,
            "issues": issues,
            "can_acquire_t3": free_slots >= 1 or can_free >= 1
        }


# Global instance
_inventory_decision_tree: Optional[InventoryDecisionTree] = None


def get_decision_tree() -> InventoryDecisionTree:
    """Get global decision tree instance"""
    global _inventory_decision_tree
    if _inventory_decision_tree is None:
        _inventory_decision_tree = InventoryDecisionTree()
    return _inventory_decision_tree


def evaluate_pickup(ground_item: Dict, inventory: List[Dict],
                   item_need_profile: ItemNeedProfile,
                   current_hp: int, current_ep: int, max_ep: int,
                   equipped_weapon: Optional[Dict]) -> PickupImpact:
    """Convenience function untuk evaluate pickup"""
    tree = get_decision_tree()
    return tree.evaluate_pickup_impact(
        ground_item, inventory, item_need_profile,
        current_hp, current_ep, max_ep, equipped_weapon
    )


def get_space_creation_plan(inventory: List[Dict], slots_needed: int,
                           game_phase: str, current_hp: int,
                           current_ep: int, max_ep: int,
                           equipped_weapon: Optional[Dict]) -> List[Dict]:
    """Convenience function untuk get space creation plan"""
    tree = get_decision_tree()
    phase = GamePhase(game_phase) if isinstance(game_phase, str) else game_phase
    return tree.get_space_creation_plan(
        inventory, slots_needed, phase,
        current_hp, current_ep, max_ep, equipped_weapon
    )


def analyze_endgame_readiness(inventory: List[Dict], 
                             equipped_weapon: Optional[Dict]) -> Dict:
    """Convenience function untuk analyze endgame readiness"""
    tree = get_decision_tree()
    return tree.analyze_endgame_readiness(inventory, equipped_weapon)
