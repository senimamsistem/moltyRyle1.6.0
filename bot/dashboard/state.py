"""
Dashboard shared state — bridge between bot engine and web dashboard.
Bot writes → Dashboard reads. Thread-safe via asyncio lock.
"""
import time
import json
from collections import deque
from pathlib import Path
from typing import Dict, List, Any
from bot.utils.logger import get_logger

log = get_logger(__name__)

# Maximum log entries kept in memory
MAX_LOGS = 500


class DashboardState:
    """Singleton shared state between bot and dashboard."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ── Agent state ────────────────────────────────────────
        self.agents: dict[str, dict] = {}  # {agent_id: {name, status, hp, ep, ...}}

        # ── Global stats ───────────────────────────────────────
        self.total_wins = 0
        self.total_moltz = 0
        self.total_smoltz = 0
        self.total_cross = 0.0
        self.bots_running = 0

        # ── Logs ───────────────────────────────────────────────
        self.global_logs: deque = deque(maxlen=MAX_LOGS)
        self.agent_logs: dict[str, deque] = {}  # {agent_id: deque}

        # ── Accounts ───────────────────────────────────────────
        self.accounts: list[dict] = []

        # ── Timestamps ─────────────────────────────────────────
        self.started_at = time.time()
        self.last_update = time.time()
        
        # ── Turn Timer ─────────────────────────────────────────
        self.turn_duration = 60  # seconds per game loop.md
        self.last_action_time = 0
        self.cooldown_end_time = 0

    # ── Bot writes ─────────────────────────────────────────────

    def update_agent(self, agent_id: str, data: dict):
        """Update agent state from bot engine."""
        if agent_id not in self.agents:
            self.agents[agent_id] = {}
            self.agent_logs[agent_id] = deque(maxlen=MAX_LOGS)
        self.agents[agent_id].update(data)
        self.agents[agent_id]["last_update"] = time.time()
        self.last_update = time.time()

    def add_log(self, message: str, level: str = "info", agent_id: str = None):
        """Add log entry."""
        entry = {
            "ts": time.time(),
            "msg": message,
            "level": level,
            "agent": agent_id,
        }
        self.global_logs.append(entry)
        if agent_id and agent_id in self.agent_logs:
            self.agent_logs[agent_id].append(entry)

    def set_account(self, account_data: dict):
        """Add or update account."""
        api_key = account_data.get("api_key", "")
        for i, acc in enumerate(self.accounts):
            if acc.get("api_key") == api_key:
                self.accounts[i] = account_data
                return
        self.accounts.append(account_data)

    def get_evolution_data(self) -> dict:
        """Get evolution data for dashboard."""
        try:
            # Import here to avoid circular imports
            import sys
            sys.path.insert(0, '.')
            from bot.learning.strategy_dna import StrategyDNA, DNA_FILE, MATCH_HISTORY_FILE
            from bot.memory.agent_memory import AgentMemory, MEMORY_FILE
            
            dna_system = StrategyDNA()
            memory = AgentMemory()
            
            # Basic status
            status = {
                "generation": dna_system.generation,
                "match_count": len(dna_system.match_history),
                "last_fitness": None,
                "last_evolution": None
            }
            
            # Get last fitness
            if dna_system.match_history:
                last_match = dna_system.match_history[-1]
                status["last_fitness"] = last_match.get("fitness", 0)
            
            # Check evolution events
            evolution_events = []
            data_dir = Path("data")
            if data_dir.exists():
                backup_files = list(data_dir.glob("strategy_dna.json.*.autobackup"))
                if backup_files:
                    from datetime import datetime
                    latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                    backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
                    evolution_events.append(f"DNA Evolution: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if status["generation"] > 0:
                evolution_events.append(f"Current Generation: {status['generation']}")
            
            # DNA comparison
            dna_comparison = []
            from bot.learning.strategy_dna import DEFAULT_DNA
            
            for key, current_val in dna_system.dna.items():
                default_val = DEFAULT_DNA.get(key)
                if default_val and isinstance(default_val, (int, float)):
                    change = current_val - default_val
                    significant_change = abs(change) > 0.1
                    
                    dna_comparison.append({
                        "parameter": key,
                        "default": default_val,
                        "current": current_val,
                        "change": f"{change:+.3f}" if isinstance(change, float) else f"{change:+}",
                        "significant_change": significant_change
                    })
            
            # Learning progress
            learning_progress = None
            if dna_system.match_history:
                recent_matches = dna_system.match_history[-10:]
                fitness_trend = 0
                
                if len(dna_system.match_history) >= 10:
                    early_avg = sum(m.get('fitness', 0) for m in dna_system.match_history[:5]) / 5
                    recent_avg = sum(m.get('fitness', 0) for m in dna_system.match_history[-5:]) / 5
                    fitness_trend = recent_avg - early_avg
                
                avg_placement = sum(m.get('placement', 100) for m in dna_system.match_history) / len(dna_system.match_history)
                
                learning_progress = {
                    "total_matches": len(dna_system.match_history),
                    "fitness_trend": fitness_trend,
                    "avg_placement": avg_placement,
                    "recent_matches": [
                        {
                            "match": i + 1,
                            "placement": m.get('placement', 100),
                            "kills": m.get('kills', 0),
                            "fitness": m.get('fitness', 0)
                        }
                        for i, m in enumerate(recent_matches)
                    ]
                }
            
            # Memory status
            memory_status = None
            overall = memory.data.get("overall", {})
            history = overall.get("history", {})
            
            memory_status = {
                "total_games": history.get("totalGames", 0),
                "wins": history.get("wins", 0),
                "avg_kills": history.get("avgKills", 0),
                "lessons": len(history.get("lessons", []))
            }
            
            return {
                **status,
                "evolution_events": evolution_events,
                "dna_comparison": dna_comparison,
                "learning_progress": learning_progress,
                "memory_status": memory_status
            }
            
        except Exception as e:
            log.error(f"Error getting evolution data: {e}")
            return {
                "generation": 0,
                "match_count": 0,
                "evolution_events": ["Error loading evolution data"],
                "dna_comparison": [],
                "learning_progress": None,
                "memory_status": None
            }

    # ── Dashboard reads ────────────────────────────────────────

    def get_snapshot(self) -> dict:
        """Full state snapshot for dashboard API."""
        now = time.time()
        # Calculate countdown timer
        remaining = max(0, self.cooldown_end_time - now)
        can_act = remaining <= 0
        
        return {
            "agents": dict(self.agents),
            "stats": {
                "total_wins": self.total_wins,
                "total_moltz": self.total_moltz,
                "total_smoltz": self.total_smoltz,
                "total_cross": self.total_cross,
                "bots_running": self.bots_running,
                "agents_active": sum(1 for a in self.agents.values()
                                     if a.get("status") == "playing"),
                "agents_idle": sum(1 for a in self.agents.values()
                                   if a.get("status") in ("idle", "queuing")),
                "agents_dead": sum(1 for a in self.agents.values()
                                   if a.get("status") == "dead"),
                "agents_error": sum(1 for a in self.agents.values()
                                    if a.get("status") == "error"),
                "uptime": now - self.started_at,
                # Turn timer info
                "turn_duration": self.turn_duration,
                "cooldown_remaining": int(remaining),
                "can_act": can_act,
                "next_turn_in": int(remaining) if remaining > 0 else 0,
            },
            "accounts": self.accounts,
            "logs": list(self.global_logs)[-200:],
            "agent_logs": {k: list(v)[-100:] for k, v in self.agent_logs.items()},
        }


# Global singleton
dashboard_state = DashboardState()

# Add app property for compatibility with main.py
from bot.dashboard.server import create_app
dashboard_state.app = create_app()
