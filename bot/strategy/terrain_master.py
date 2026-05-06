"""
Terrain Mastery System - Calculate terrain advantages untuk combat positioning

Features:
1. Weapon vs terrain combat bonus matrix
2. Optimal positioning recommendations per weapon type
3. Terrain-based defensive bonuses
4. High ground / choke point detection
"""
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from bot.utils.logger import get_logger

log = get_logger(__name__)


# Weapon effectiveness matrix per terrain
# Format: terrain -> weapon_type -> {attack_bonus, defense_bonus, accuracy_bonus, description}
TERRAIN_WEAPON_MATRIX = {
    "forest": {
        "katana": {"attack": 1.15, "defense": 1.0, "accuracy": 1.0, "desc": "Katana excels di forest - close quarters combat advantage"},
        "sword": {"attack": 1.10, "defense": 1.0, "accuracy": 1.0, "desc": "Sword effective di forest"},
        "dagger": {"attack": 1.20, "defense": 1.05, "accuracy": 1.05, "desc": "Dagger superior di forest - stealth advantage"},
        "bow": {"attack": 0.80, "defense": 1.0, "accuracy": 0.70, "desc": "Bow hindered di forest - visibility reduced"},
        "sniper": {"attack": 0.60, "defense": 1.0, "accuracy": 0.50, "desc": "Sniper severely hindered di forest - no line of sight"},
        "pistol": {"attack": 0.85, "defense": 1.0, "accuracy": 0.75, "desc": "Pistol slightly hindered di forest"},
        "fist": {"attack": 1.0, "defense": 1.0, "accuracy": 1.0, "desc": "Fist combat normal di forest"},
    },
    "plains": {
        "katana": {"attack": 1.0, "defense": 1.0, "accuracy": 1.0, "desc": "Katana normal di plains"},
        "sword": {"attack": 1.0, "defense": 1.0, "accuracy": 1.0, "desc": "Sword normal di plains"},
        "dagger": {"attack": 0.90, "defense": 0.95, "accuracy": 1.0, "desc": "Dagger slightly hindered - no cover"},
        "bow": {"attack": 1.10, "defense": 1.0, "accuracy": 1.15, "desc": "Bow excellent di plains - clear line of sight"},
        "sniper": {"attack": 1.20, "defense": 1.0, "accuracy": 1.25, "desc": "Sniper dominant di plains - maximum range advantage"},
        "pistol": {"attack": 1.05, "defense": 1.0, "accuracy": 1.10, "desc": "Pistol effective di plains"},
        "fist": {"attack": 1.0, "defense": 1.0, "accuracy": 1.0, "desc": "Fist combat normal di plains"},
    },
    "mountain": {
        "katana": {"attack": 0.90, "defense": 1.10, "accuracy": 0.95, "desc": "Katana slightly hindered di mountain - uneven ground"},
        "sword": {"attack": 0.95, "defense": 1.05, "accuracy": 1.0, "desc": "Sword slightly hindered di mountain"},
        "dagger": {"attack": 0.85, "defense": 1.0, "accuracy": 0.90, "desc": "Dagger hindered di mountain - unstable footing"},
        "bow": {"attack": 1.15, "defense": 1.10, "accuracy": 1.10, "desc": "Bow excellent di mountain - high ground advantage"},
        "sniper": {"attack": 1.30, "defense": 1.15, "accuracy": 1.30, "desc": "Sniper supreme di mountain - high ground + visibility"},
        "pistol": {"attack": 1.10, "defense": 1.05, "accuracy": 1.15, "desc": "Pistol effective di mountain"},
        "fist": {"attack": 0.95, "defense": 1.0, "accuracy": 0.95, "desc": "Fist combat slightly hindered di mountain"},
    },
    "water": {
        "katana": {"attack": 0.85, "defense": 0.90, "accuracy": 0.85, "desc": "Katana hindered di water - movement restricted"},
        "sword": {"attack": 0.90, "defense": 0.95, "accuracy": 0.90, "desc": "Sword slightly hindered di water"},
        "dagger": {"attack": 0.70, "defense": 0.85, "accuracy": 0.80, "desc": "Dagger severely hindered di water"},
        "bow": {"attack": 0.60, "defense": 0.90, "accuracy": 0.50, "desc": "Bow severely hindered di water - wet equipment"},
        "sniper": {"attack": 0.40, "defense": 0.85, "accuracy": 0.30, "desc": "Sniper extremely hindered di water"},
        "pistol": {"attack": 0.75, "defense": 0.90, "accuracy": 0.70, "desc": "Pistol hindered di water - wet equipment"},
        "fist": {"attack": 0.90, "defense": 0.95, "accuracy": 0.90, "desc": "Fist combat hindered di water"},
    },
    "urban": {
        "katana": {"attack": 1.10, "defense": 1.05, "accuracy": 1.0, "desc": "Katana effective di urban - close quarters"},
        "sword": {"attack": 1.05, "defense": 1.0, "accuracy": 1.0, "desc": "Sword effective di urban"},
        "dagger": {"attack": 1.15, "defense": 1.10, "accuracy": 1.0, "desc": "Dagger superior di urban - ambush opportunities"},
        "bow": {"attack": 0.90, "defense": 1.0, "accuracy": 0.85, "desc": "Bow hindered di urban - obstacles"},
        "sniper": {"attack": 0.95, "defense": 1.0, "accuracy": 0.90, "desc": "Sniper slightly hindered di urban - line of sight issues"},
        "pistol": {"attack": 1.15, "defense": 1.0, "accuracy": 1.10, "desc": "Pistol superior di urban - close range effectiveness"},
        "fist": {"attack": 1.0, "defense": 1.0, "accuracy": 1.0, "desc": "Fist combat normal di urban"},
    },
    "desert": {
        "katana": {"attack": 1.0, "defense": 0.95, "accuracy": 0.95, "desc": "Katana normal di desert - heat fatigue"},
        "sword": {"attack": 1.0, "defense": 0.95, "accuracy": 1.0, "desc": "Sword normal di desert"},
        "dagger": {"attack": 0.95, "defense": 0.95, "accuracy": 1.0, "desc": "Dagger normal di desert"},
        "bow": {"attack": 0.90, "defense": 0.95, "accuracy": 0.85, "desc": "Bow hindered di desert - heat shimmer, sand"},
        "sniper": {"attack": 0.85, "defense": 0.95, "accuracy": 0.80, "desc": "Sniper hindered di desert - heat shimmer"},
        "pistol": {"attack": 1.0, "defense": 0.95, "accuracy": 0.95, "desc": "Pistol normal di desert - sand can jam"},
        "fist": {"attack": 0.95, "defense": 0.95, "accuracy": 0.95, "desc": "Fist combat hindered di desert - heat fatigue"},
    },
}

# Default terrain bonus jika terrain tidak dikenali
DEFAULT_TERRAIN_BONUS = {"attack": 1.0, "defense": 1.0, "accuracy": 1.0, "desc": "Normal combat conditions"}


@dataclass
class TerrainBonus:
    """Terrain combat bonus untuk specific weapon"""
    terrain: str
    weapon_type: str
    attack_multiplier: float
    defense_multiplier: float
    accuracy_multiplier: float
    description: str


class TerrainMaster:
    """
    Terrain Mastery System
    
    Features:
    - Calculate weapon effectiveness per terrain
    - Recommend optimal terrain untuk specific weapons
    - Evaluate terrain advantages untuk combat decisions
    """
    
    def __init__(self):
        self.matrix = TERRAIN_WEAPON_MATRIX
    
    def get_terrain_bonus(self, terrain: str, weapon_type: str) -> TerrainBonus:
        """
        Get combat bonus untuk weapon di specific terrain
        
        Returns TerrainBonus dengan multipliers:
        - attack_multiplier: damage multiplier
        - defense_multiplier: defense effectiveness
        - accuracy_multiplier: hit chance multiplier
        """
        # Handle edge cases
        if terrain is None:
            terrain = "plains"
        elif not isinstance(terrain, str):
            terrain = str(terrain).lower()
        else:
            terrain = terrain.lower()
        
        if weapon_type is None or weapon_type == "":
            weapon_type = "fist"
        elif not isinstance(weapon_type, str):
            weapon_type = str(weapon_type).lower()
        else:
            weapon_type = weapon_type.lower()
        
        # Get bonus dari matrix atau default
        if terrain in self.matrix and weapon_type in self.matrix[terrain]:
            bonus_data = self.matrix[terrain][weapon_type]
        else:
            bonus_data = DEFAULT_TERRAIN_BONUS
        
        return TerrainBonus(
            terrain=terrain,
            weapon_type=weapon_type,
            attack_multiplier=bonus_data["attack"],
            defense_multiplier=bonus_data["defense"],
            accuracy_multiplier=bonus_data["accuracy"],
            description=bonus_data["desc"]
        )
    
    def calculate_combat_advantage(
        self,
        our_weapon: str,
        enemy_weapon: str,
        terrain: str,
        our_hp: int,
        enemy_hp: int
    ) -> Dict:
        """
        Calculate overall combat advantage berdasarkan terrain dan weapons
        
        Returns dict dengan:
        - our_advantage: float (positive = advantage, negative = disadvantage)
        - recommendation: str (fight, avoid, or neutral)
        - details: dict dengan breakdown
        """
        our_bonus = self.get_terrain_bonus(terrain, our_weapon)
        enemy_bonus = self.get_terrain_bonus(terrain, enemy_weapon)
        
        # Calculate advantage score
        # Consider: attack power, defense effectiveness, accuracy
        our_score = (
            our_bonus.attack_multiplier * 0.5 +
            our_bonus.defense_multiplier * 0.3 +
            our_bonus.accuracy_multiplier * 0.2
        )
        
        enemy_score = (
            enemy_bonus.attack_multiplier * 0.5 +
            enemy_bonus.defense_multiplier * 0.3 +
            enemy_bonus.accuracy_multiplier * 0.2
        )
        
        advantage = our_score - enemy_score
        
        # Generate recommendation
        if advantage >= 0.15:
            recommendation = "fight"
            confidence = "high"
        elif advantage >= 0.05:
            recommendation = "fight"
            confidence = "medium"
        elif advantage <= -0.15:
            recommendation = "avoid"
            confidence = "high"
        elif advantage <= -0.05:
            recommendation = "avoid"
            confidence = "medium"
        else:
            recommendation = "neutral"
            confidence = "low"
        
        return {
            "our_advantage": round(advantage, 3),
            "recommendation": recommendation,
            "confidence": confidence,
            "our_bonus": {
                "attack": our_bonus.attack_multiplier,
                "defense": our_bonus.defense_multiplier,
                "accuracy": our_bonus.accuracy_multiplier,
                "description": our_bonus.description
            },
            "enemy_bonus": {
                "attack": enemy_bonus.attack_multiplier,
                "defense": enemy_bonus.defense_multiplier,
                "accuracy": enemy_bonus.accuracy_multiplier,
                "description": enemy_bonus.description
            }
        }
    
    def recommend_optimal_terrain(
        self,
        weapon_type: str,
        available_terrains: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Recommend optimal terrains untuk specific weapon
        Returns: List of (terrain, score) sorted by score descending
        """
        scores = []
        
        for terrain in available_terrains:
            bonus = self.get_terrain_bonus(terrain, weapon_type)
            
            # Calculate overall effectiveness score
            score = (
                bonus.attack_multiplier * 0.4 +
                bonus.defense_multiplier * 0.3 +
                bonus.accuracy_multiplier * 0.3
            )
            
            scores.append((terrain, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
    
    def get_favorable_terrains(self, weapon_type: str) -> List[str]:
        """
        Get list of favorable terrains untuk weapon
        Returns terrains where weapon has advantage (score > 1.0)
        """
        favorable = []
        
        for terrain in self.matrix.keys():
            bonus = self.get_terrain_bonus(terrain, weapon_type)
            avg_bonus = (bonus.attack_multiplier + bonus.defense_multiplier + bonus.accuracy_multiplier) / 3
            
            if avg_bonus > 1.0:
                favorable.append(terrain)
        
        return favorable
    
    def get_unfavorable_terrains(self, weapon_type: str) -> List[str]:
        """
        Get list of unfavorable terrains untuk weapon
        Returns terrains where weapon has disadvantage (score < 1.0)
        """
        unfavorable = []
        
        for terrain in self.matrix.keys():
            bonus = self.get_terrain_bonus(terrain, weapon_type)
            avg_bonus = (bonus.attack_multiplier + bonus.defense_multiplier + bonus.accuracy_multiplier) / 3
            
            if avg_bonus < 1.0:
                unfavorable.append(terrain)
        
        return unfavorable
    
    def should_seek_terrain_change(
        self,
        our_weapon: str,
        enemy_weapon: str,
        current_terrain: str,
        available_terrains: List[str]
    ) -> Tuple[bool, str, float]:
        """
        Determine if we should move to different terrain untuk combat advantage
        
        Returns: (should_move, recommended_terrain, advantage_gain)
        """
        # Current advantage
        current_analysis = self.calculate_combat_advantage(
            our_weapon, enemy_weapon, current_terrain, 100, 100
        )
        current_advantage = current_analysis["our_advantage"]
        
        # Find best alternative terrain
        best_terrain = current_terrain
        best_advantage = current_advantage
        
        for terrain in available_terrains:
            if terrain == current_terrain:
                continue
            
            analysis = self.calculate_combat_advantage(
                our_weapon, enemy_weapon, terrain, 100, 100
            )
            
            if analysis["our_advantage"] > best_advantage:
                best_advantage = analysis["our_advantage"]
                best_terrain = terrain
        
        advantage_gain = best_advantage - current_advantage
        
        # Only recommend move if significant advantage gain (>0.1)
        should_move = advantage_gain >= 0.1
        
        return should_move, best_terrain, advantage_gain
    
    def get_terrain_summary(self, weapon_type: str) -> Dict:
        """Get summary of terrain effectiveness untuk weapon"""
        favorable = self.get_favorable_terrains(weapon_type)
        unfavorable = self.get_unfavorable_terrains(weapon_type)
        
        return {
            "weapon": weapon_type,
            "favorable_terrains": favorable,
            "unfavorable_terrains": unfavorable,
            "favorable_count": len(favorable),
            "unfavorable_count": len(unfavorable),
            "summary": f"{weapon_type}: Good in {', '.join(favorable) or 'none'} | Bad in {', '.join(unfavorable) or 'none'}"
        }


# Global instance
terrain_master = TerrainMaster()


def get_terrain_advantage(
    our_weapon: str,
    enemy_weapon: str,
    terrain: str,
    our_hp: int = 100,
    enemy_hp: int = 100
) -> Dict:
    """Convenience function untuk get combat advantage analysis"""
    return terrain_master.calculate_combat_advantage(
        our_weapon, enemy_weapon, terrain, our_hp, enemy_hp
    )


def recommend_terrain_for_weapon(weapon_type: str, available_terrains: List[str]) -> List[Tuple[str, float]]:
    """Convenience function untuk get terrain recommendations"""
    return terrain_master.recommend_optimal_terrain(weapon_type, available_terrains)


def should_change_terrain(
    our_weapon: str,
    enemy_weapon: str,
    current_terrain: str,
    available_terrains: List[str]
) -> Tuple[bool, str, float]:
    """Convenience function untuk determine if terrain change recommended"""
    return terrain_master.should_seek_terrain_change(
        our_weapon, enemy_weapon, current_terrain, available_terrains
    )


def get_weapon_terrain_summary(weapon_type: str) -> Dict:
    """Convenience function untuk get terrain summary"""
    return terrain_master.get_terrain_summary(weapon_type)
