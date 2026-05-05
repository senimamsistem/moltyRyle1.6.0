"""
Combat Prediction Engine - Probability-based combat decisions
Replaces threshold-based logic dengan ML-informed win probability estimation
"""
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from bot.strategy.constants import WEAPONS, WEAPON_STRATEGIES, WEATHER_COMBAT_PENALTY
from bot.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class CombatFactors:
    """All factors influencing combat outcome"""
    # Our stats
    hp: int
    max_hp: int
    ep: int
    atk: int
    defense: int
    weapon_bonus: int
    weapon_range: int
    weapon_type: str
    healing_items: int
    
    # Enemy stats
    enemy_hp: int
    enemy_max_hp: int
    enemy_atk: int
    enemy_def: int
    enemy_weapon_bonus: int
    enemy_weapon_type: str
    
    # Environmental
    terrain: str
    weather: str
    is_surrounded: bool
    escape_routes: int
    
    # Game phase
    alive_count: int
    game_phase: str  # early, mid, late
    
    # Historical (from learning)
    enemy_historical_wins: int = 0
    enemy_historical_losses: int = 0
    enemy_avg_damage_dealt: float = 0.0


@dataclass
class CombatPrediction:
    """Combat outcome prediction"""
    win_probability: float  # 0.0 to 1.0
    expected_damage_dealt: float
    expected_damage_taken: float
    expected_turns: int
    risk_level: str  # low, medium, high, extreme
    recommended_action: str  # attack, flee, wait
    confidence: float  # prediction confidence


class CombatPredictor:
    """
    Advanced combat prediction using:
    1. Statistical modeling dari weapon matchups
    2. Historical performance tracking
    3. Environmental factor analysis
    4. Risk-adjusted expected value calculation
    """
    
    # Weapon matchup advantages (empirical dari game data)
    WEAPON_MATCHUP_MATRIX = {
        # Attacker -> Defender advantage score
        # Positive = attacker advantage, Negative = defender advantage
        ("katana", "sniper"): 0.15,   # Katana can close distance fast
        ("katana", "bow"): 0.20,     # Bow has trouble at close range
        ("sniper", "katana"): -0.10, # Sniper needs to keep distance
        ("sniper", "bow"): 0.25,     # Sniper outranges bow
        ("sword", "dagger"): 0.10,   # Sword > dagger
        ("sword", "fist"): 0.30,     # Weapon vs fist big advantage
        ("pistol", "fist"): 0.25,
        ("pistol", "katana"): -0.15, # Katana closes on pistol
        ("dagger", "sniper"): 0.20,  # Can ambush sniper
        ("bow", "pistol"): -0.10,    # Pistol more reliable
    }
    
    # Terrain combat modifiers
    TERRAIN_MODIFIERS = {
        "hills": {"ranged_bonus": 0.15, "melee_penalty": 0.05},
        "forest": {"ranged_penalty": 0.10, "melee_bonus": 0.10},
        "ruins": {"ranged_penalty": 0.05, "melee_bonus": 0.15},
        "plains": {},  # Neutral
        "water": {"all_penalty": 0.20},  # Combat harder in water
    }
    
    def __init__(self):
        self._historical_performance: Dict[str, Dict] = {}
        self._prediction_cache: Dict[str, CombatPrediction] = {}
        
    def calculate_win_probability(self, factors: CombatFactors) -> CombatPrediction:
        """
        Calculate comprehensive combat win probability
        
        Formula components:
        1. Base power comparison (HP, ATK, weapon)
        2. Weapon matchup advantage
        3. Environmental factors (terrain, weather)
        4. Resource advantage (healing items, EP)
        5. Historical performance (if available)
        """
        
        # 1. Base power calculation
        our_power = self._calculate_power(
            factors.hp, factors.atk, factors.weapon_bonus, 
            factors.defense, factors.healing_items
        )
        enemy_power = self._calculate_power(
            factors.enemy_hp, factors.enemy_atk, factors.enemy_weapon_bonus,
            factors.enemy_def, 0  # Assume enemy might have heals
        )
        
        # Base win probability dari power comparison
        if our_power + enemy_power == 0:
            base_prob = 0.5
        else:
            base_prob = our_power / (our_power + enemy_power)
        
        # 2. Weapon matchup modifier
        matchup_modifier = self._get_weapon_matchup_modifier(
            factors.weapon_type, factors.enemy_weapon_type
        )
        
        # 3. Environmental modifiers
        env_modifier = self._get_environmental_modifier(factors)
        
        # 4. Resource evaluation
        resource_modifier = self._get_resource_modifier(factors)
        
        # 5. Historical performance (if we know this enemy)
        historical_modifier = self._get_historical_modifier(factors)
        
        # Combine all factors
        # Use logistic function untuk smooth probability curve
        total_modifier = matchup_modifier + env_modifier + resource_modifier + historical_modifier
        adjusted_prob = self._apply_logistic_curve(base_prob, total_modifier)
        
        # Clamp to valid range
        win_prob = max(0.05, min(0.95, adjusted_prob))
        
        # Calculate expected outcomes
        expected_damage = self._estimate_damage_exchange(factors)
        expected_turns = self._estimate_combat_duration(factors)
        
        # Determine risk level
        risk_level = self._classify_risk(win_prob, factors)
        
        # Generate recommendation
        recommended_action = self._generate_recommendation(win_prob, risk_level, factors)
        
        # Calculate confidence (lower jika many unknown factors)
        confidence = self._calculate_confidence(factors)
        
        prediction = CombatPrediction(
            win_probability=win_prob,
            expected_damage_dealt=expected_damage["dealt"],
            expected_damage_taken=expected_damage["taken"],
            expected_turns=expected_turns,
            risk_level=risk_level,
            recommended_action=recommended_action,
            confidence=confidence
        )
        
        # Cache prediction
        cache_key = self._make_cache_key(factors)
        self._prediction_cache[cache_key] = prediction
        
        return prediction
    
    def _calculate_power(self, hp: int, atk: int, weapon_bonus: int, 
                        defense: int, healing_items: int) -> float:
        """Calculate effective combat power"""
        # HP weight: current HP + some factor of max (survivability)
        hp_factor = hp * 1.5 + (hp / 100) * 20  # Bonus untuk high HP%
        
        # Offensive power
        offense = atk + weapon_bonus
        
        # Defense contribution (diminishing returns)
        defense_factor = defense * 0.3
        
        # Healing buffer (each heal ~25 HP effective)
        healing_factor = healing_items * 25
        
        return hp_factor + offense + defense_factor + healing_factor
    
    def _get_weapon_matchup_modifier(self, our_weapon: str, enemy_weapon: str) -> float:
        """Get weapon matchup advantage/disadvantage"""
        key = (our_weapon, enemy_weapon)
        if key in self.WEAPON_MATCHUP_MATRIX:
            return self.WEAPON_MATCHUP_MATRIX[key]
        
        # Reverse lookup (negative of the reverse matchup)
        reverse_key = (enemy_weapon, our_weapon)
        if reverse_key in self.WEAPON_MATCHUP_MATRIX:
            return -self.WEAPON_MATCHUP_MATRIX[reverse_key]
        
        return 0.0  # No known matchup
    
    def _get_environmental_modifier(self, factors: CombatFactors) -> float:
        """Calculate environmental impact on combat"""
        modifier = 0.0
        
        # Weather penalty
        weather_penalty = WEATHER_COMBAT_PENALTY.get(factors.weather, 0.0)
        modifier -= weather_penalty * 0.5  # Affects both equally, slight random factor
        
        # Terrain effects
        terrain = self.TERRAIN_MODIFIERS.get(factors.terrain, {})
        our_weapon_style = WEAPON_STRATEGIES.get(factors.weapon_type, {}).get("style", "")
        
        if "ranged" in our_weapon_style:
            modifier += terrain.get("ranged_bonus", 0)
            modifier -= terrain.get("ranged_penalty", 0)
        elif "melee" in our_weapon_style:
            modifier += terrain.get("melee_bonus", 0)
            modifier -= terrain.get("melee_penalty", 0)
            
        # General penalty applies to all
        modifier -= terrain.get("all_penalty", 0)
        
        # Surrounded penalty (can't retreat easily)
        if factors.is_surrounded:
            modifier -= 0.15
            
        return modifier
    
    def _get_resource_modifier(self, factors: CombatFactors) -> float:
        """Calculate resource advantage/disadvantage"""
        modifier = 0.0
        
        # EP advantage (more actions available)
        if factors.ep >= 8:
            modifier += 0.05
        elif factors.ep <= 3:
            modifier -= 0.10  # Low EP = vulnerable
            
        # Healing advantage
        if factors.healing_items >= 3:
            modifier += 0.08
        elif factors.healing_items == 0:
            modifier -= 0.05
            
        # Escape routes (retreat option value)
        if factors.escape_routes == 0:
            modifier -= 0.10  # Trapped!
        elif factors.escape_routes >= 3:
            modifier += 0.03  # Can disengage
            
        return modifier
    
    def _get_historical_modifier(self, factors: CombatFactors) -> float:
        """Apply historical performance data if available"""
        total_games = factors.enemy_historical_wins + factors.enemy_historical_losses
        if total_games < 3:
            return 0.0  # Not enough data
            
        enemy_win_rate = factors.enemy_historical_wins / total_games
        
        # If enemy has high win rate, reduce our win probability
        if enemy_win_rate > 0.6:
            return -0.10
        elif enemy_win_rate < 0.4:
            return 0.10
            
        return 0.0
    
    def _apply_logistic_curve(self, base_prob: float, modifier: float) -> float:
        """Apply modifier menggunakan logistic function untuk smooth curve"""
        # Convert base prob ke log-odds
        if base_prob <= 0:
            base_prob = 0.001
        if base_prob >= 1:
            base_prob = 0.999
            
        log_odds = math.log(base_prob / (1 - base_prob))
        
        # Apply modifier (scaled)
        adjusted_log_odds = log_odds + (modifier * 2)
        
        # Convert back to probability
        return 1 / (1 + math.exp(-adjusted_log_odds))
    
    def _estimate_damage_exchange(self, factors: CombatFactors) -> Dict[str, float]:
        """Estimate damage exchange dalam combat"""
        our_weapon = WEAPONS.get(factors.weapon_type, {"bonus": 0})
        enemy_weapon = WEAPONS.get(factors.enemy_weapon_type, {"bonus": 0})
        
        # Base damage calculation
        our_damage = factors.atk + our_weapon["bonus"] - (factors.enemy_def * 0.5)
        enemy_damage = factors.enemy_atk + enemy_weapon["bonus"] - (factors.defense * 0.5)
        
        # Weather penalty
        weather_penalty = WEATHER_COMBAT_PENALTY.get(factors.weather, 0.0)
        our_damage *= (1 - weather_penalty)
        enemy_damage *= (1 - weather_penalty)
        
        # Estimate total exchange before someone dies
        our_ttk = factors.enemy_hp / max(1, our_damage)  # Turns to kill enemy
        enemy_ttk = factors.hp / max(1, enemy_damage)    # Turns for enemy to kill us
        
        expected_turns = min(our_ttk, enemy_ttk)
        
        return {
            "dealt": our_damage * expected_turns,
            "taken": enemy_damage * expected_turns
        }
    
    def _estimate_combat_duration(self, factors: CombatFactors) -> int:
        """Estimate berapa turns combat akan berlangsung"""
        damage = self._estimate_damage_exchange(factors)
        
        if damage["dealt"] <= 0:
            return 10  # Unknown, assume long
            
        turns_to_kill = factors.enemy_hp / damage["dealt"]
        return max(1, min(10, int(turns_to_kill)))
    
    def _classify_risk(self, win_prob: float, factors: CombatFactors) -> str:
        """Classify combat risk level"""
        if win_prob >= 0.75:
            return "low"
        elif win_prob >= 0.55:
            return "medium"
        elif win_prob >= 0.40:
            return "high"
        else:
            return "extreme"
    
    def _generate_recommendation(self, win_prob: float, risk: str, 
                                  factors: CombatFactors) -> str:
        """Generate action recommendation"""
        # High win probability = attack
        if win_prob >= 0.70:
            return "attack"
            
        # Medium dengan good resources = attack
        if win_prob >= 0.55 and factors.healing_items >= 1 and factors.ep >= 5:
            return "attack"
            
        # High risk tapi trapped = must fight
        if risk == "high" and factors.escape_routes == 0:
            return "attack"
            
        # Extreme risk with escape option = flee
        if risk == "extreme" and factors.escape_routes > 0:
            return "flee"
            
        # Default: wait for better opportunity
        return "wait"
    
    def _calculate_confidence(self, factors: CombatFactors) -> float:
        """Calculate prediction confidence"""
        confidence = 0.8  # Base confidence
        
        # Reduce confidence jika missing data
        if factors.enemy_historical_wins + factors.enemy_historical_losses < 3:
            confidence -= 0.1
            
        # Unknown terrain/weather reduces confidence
        if factors.terrain not in self.TERRAIN_MODIFIERS:
            confidence -= 0.05
            
        # High EP gives more tactical options = higher confidence
        if factors.ep < 5:
            confidence -= 0.1
            
        return max(0.3, min(1.0, confidence))
    
    def _make_cache_key(self, factors: CombatFactors) -> str:
        """Create cache key untuk prediction"""
        return (
            f"{factors.weapon_type}_{factors.hp}_{factors.enemy_weapon_type}_{factors.enemy_hp}_"
            f"{factors.terrain}_{factors.weather}"
        )
    
    def record_outcome(self, factors: CombatFactors, won: bool, 
                       damage_dealt: int, damage_taken: int):
        """Record actual outcome untuk improve future predictions"""
        enemy_id = f"enemy_{factors.enemy_weapon_type}_{factors.enemy_atk}"
        
        if enemy_id not in self._historical_performance:
            self._historical_performance[enemy_id] = {
                "wins": 0, "losses": 0, "damage_dealt": [], "damage_taken": []
            }
            
        record = self._historical_performance[enemy_id]
        if won:
            record["wins"] += 1
        else:
            record["losses"] += 1
            
        record["damage_dealt"].append(damage_dealt)
        record["damage_taken"].append(damage_taken)
        
        # Keep only last 20 records
        record["damage_dealt"] = record["damage_dealt"][-20:]
        record["damage_taken"] = record["damage_taken"][-20:]
    
    def get_prediction_for_display(self, factors: CombatFactors) -> str:
        """Get human-readable prediction summary"""
        pred = self.calculate_win_probability(factors)
        
        return (
            f"Win: {pred.win_probability:.1%} | "
            f"Risk: {pred.risk_level.upper()} | "
            f"DMG: ±{pred.expected_damage_dealt:.0f}/-{pred.expected_damage_taken:.0f} | "
            f"Action: {pred.recommended_action.upper()}"
        )


# Global predictor instance
combat_predictor = CombatPredictor()


def should_engange_with_prediction(
    enemy: dict,
    hp: int,
    ep: int,
    equipped: dict,
    inventory: list,
    terrain: str,
    weather: str,
    alive_count: int,
    connections: list,
    aggression: str = "balanced"
) -> Tuple[bool, str, CombatPrediction]:
    """
    Enhanced combat decision menggunakan prediction engine
    
    Returns: (should_attack, reason, prediction)
    """
    # Build combat factors
    our_weapon_type = equipped.get("typeId", "fist") if equipped else "fist"
    our_weapon = WEAPONS.get(our_weapon_type, {"bonus": 0, "range": 0})
    
    healing_count = len([
        i for i in inventory 
        if isinstance(i, dict) and i.get("typeId", "").lower() in ("medkit", "bandage", "emergency_food")
    ])
    
    # Determine game phase
    if alive_count >= 80:
        game_phase = "early"
    elif alive_count >= 30:
        game_phase = "mid"
    else:
        game_phase = "late"
    
    factors = CombatFactors(
        hp=hp,
        max_hp=100,  # Default
        ep=ep,
        atk=10,  # Will be from self_data
        defense=5,
        weapon_bonus=our_weapon["bonus"],
        weapon_range=our_weapon["range"],
        weapon_type=our_weapon_type,
        healing_items=healing_count,
        
        enemy_hp=enemy.get("hp", 100),
        enemy_max_hp=100,
        enemy_atk=enemy.get("atk", 10),
        enemy_def=enemy.get("def", 5),
        enemy_weapon_bonus=WEAPONS.get(
            (enemy.get("equippedWeapon") or {}).get("typeId", "fist"),
            {"bonus": 0}
        )["bonus"],
        enemy_weapon_type=(enemy.get("equippedWeapon") or {}).get("typeId", "fist"),
        
        terrain=terrain.lower(),
        weather=weather.lower(),
        is_surrounded=False,  # Will calculate
        escape_routes=len(connections),
        
        alive_count=alive_count,
        game_phase=game_phase
    )
    
    # Get prediction
    prediction = combat_predictor.calculate_win_probability(factors)
    
    # Aggression adjustments
    aggression_threshold = {
        "aggressive": 0.45,
        "balanced": 0.55,
        "passive": 0.65
    }.get(aggression, 0.55)
    
    # Override recommendation based on aggression
    if prediction.win_probability >= aggression_threshold:
        should_attack = True
        reason = f"COMBAT_PRED: {prediction.win_probability:.0%} win probability ({prediction.risk_level} risk)"
    elif prediction.recommended_action == "flee":
        should_attack = False
        reason = f"COMBAT_PRED: Recommend flee - {prediction.win_probability:.0%} win prob too low"
    else:
        # Wait untuk better opportunity
        should_attack = False
        reason = f"COMBAT_PRED: Wait for better opportunity ({prediction.win_probability:.0%} win prob)"
    
    # Special case: finisher (low HP enemy)
    if enemy.get("hp", 100) <= 25:
        should_attack = True
        reason = f"COMBAT_PRED: FINISHER - enemy HP critical ({enemy.get('hp')}%)"
    
    return should_attack, reason, prediction
