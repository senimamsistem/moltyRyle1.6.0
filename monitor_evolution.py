#!/usr/bin/env python3
"""
Bot Evolution Monitor
Track and visualize bot learning progress and parameter changes
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add bot to path
sys.path.insert(0, '.')
from bot.learning.strategy_dna import StrategyDNA, DNA_FILE, MATCH_HISTORY_FILE
from bot.memory.agent_memory import AgentMemory, MEMORY_FILE
from bot.utils.logger import get_logger

log = get_logger(__name__)

class EvolutionMonitor:
    """Monitor bot evolution and learning progress"""
    
    def __init__(self):
        self.dna_system = StrategyDNA()
        self.memory = AgentMemory()
        
    def check_evolution_status(self) -> Dict[str, Any]:
        """Check current evolution status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "dna_loaded": DNA_FILE.exists(),
            "history_loaded": MATCH_HISTORY_FILE.exists(),
            "memory_loaded": MEMORY_FILE.exists(),
            "generation": self.dna_system.generation,
            "match_count": len(self.dna_system.match_history),
            "current_dna": self.dna_system.dna.copy()
        }
        return status
    
    def show_dna_comparison(self) -> None:
        """Compare current DNA with default"""
        from bot.learning.strategy_dna import DEFAULT_DNA
        
        print("\n🧬 DNA EVOLUTION COMPARISON")
        print("=" * 60)
        
        current = self.dna_system.dna
        default = DEFAULT_DNA
        
        print(f"{'Parameter':<25} {'Default':<12} {'Current':<12} {'Change':<10}")
        print("-" * 60)
        
        for key in sorted(current.keys()):
            default_val = default.get(key, "N/A")
            current_val = current.get(key, "N/A")
            
            if isinstance(default_val, float):
                default_str = f"{default_val:.3f}"
                current_str = f"{current_val:.3f}"
                change = current_val - default_val
                change_str = f"{change:+.3f}"
            else:
                default_str = str(default_val)
                current_str = str(current_val)
                if isinstance(default_val, (int, float)):
                    change = current_val - default_val
                    change_str = f"{change:+}"
                else:
                    change_str = "N/A"
            
            # Highlight significant changes
            if isinstance(change, (int, float)) and abs(change) > 0.1:
                change_str = f"🔥{change_str}"
            
            print(f"{key:<25} {default_str:<12} {current_str:<12} {change_str:<10}")
    
    def show_learning_progress(self) -> None:
        """Show learning progress over time"""
        history = self.dna_system.match_history
        
        if not history:
            print("\n❌ No match history found - play some matches first!")
            return
        
        print(f"\n📈 LEARNING PROGRESS ({len(history)} matches)")
        print("=" * 60)
        
        print(f"{'Match':<6} {'Placement':<10} {'Kills':<7} {'Fitness':<8} {'Generation':<10}")
        print("-" * 60)
        
        # Show last 10 matches
        recent_matches = history[-10:]
        for i, match in enumerate(recent_matches):
            placement = match.get('placement', 'N/A')
            kills = match.get('kills', 0)
            fitness = match.get('fitness', 0)
            generation = match.get('generation', 0)
            
            print(f"#{i+1:<5} {placement:<10} {kills:<7} {fitness:<8.1f} {generation:<10}")
        
        # Calculate trends
        if len(history) >= 5:
            early_avg = sum(m.get('fitness', 0) for m in history[:5]) / 5
            recent_avg = sum(m.get('fitness', 0) for m in history[-5:]) / 5
            
            print(f"\n📊 FITNESS TREND:")
            print(f"   Early (first 5): {early_avg:.1f}")
            print(f"   Recent (last 5): {recent_avg:.1f}")
            improvement = recent_avg - early_avg
            trend = "🔥 IMPROVING" if improvement > 10 else "➡️ STABLE" if improvement > -10 else "📉 DECLINING"
            print(f"   Change: {improvement:+.1f} ({trend})")
    
    def show_memory_status(self) -> None:
        """Show agent memory status"""
        print(f"\n🧠 AGENT MEMORY STATUS")
        print("=" * 40)
        
        overall = self.memory.data.get("overall", {})
        history = overall.get("history", {})
        
        print(f"Total Games: {history.get('totalGames', 0)}")
        print(f"Wins: {history.get('wins', 0)}")
        print(f"Avg Kills: {history.get('avgKills', 0):.1f}")
        print(f"Lessons Learned: {len(history.get('lessons', []))}")
        
        # Show recent lessons
        lessons = history.get('lessons', [])
        if lessons:
            print(f"\n📚 RECENT LESSONS:")
            for lesson in lessons[-3:]:
                print(f"   • {lesson}")
    
    def detect_evolution_events(self) -> List[str]:
        """Detect recent evolution events"""
        events = []
        
        # Check for DNA backups (indicates evolution)
        data_dir = Path("data")
        if data_dir.exists():
            backup_files = list(data_dir.glob("strategy_dna.json.*.autobackup"))
            if backup_files:
                latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
                events.append(f"🔄 DNA Evolution: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check for generation changes
        if self.dna_system.generation > 0:
            events.append(f"🧬 Current Generation: {self.dna_system.generation}")
        
        # Check for significant parameter changes
        from bot.learning.strategy_dna import DEFAULT_DNA
        significant_changes = []
        
        for key, current_val in self.dna_system.dna.items():
            default_val = DEFAULT_DNA.get(key)
            if default_val and isinstance(default_val, (int, float)):
                change = abs(current_val - default_val)
                if change > 0.1:  # Significant change threshold
                    significant_changes.append(f"{key}: {default_val} → {current_val}")
        
        if significant_changes:
            events.append("🔥 Significant Parameter Changes:")
            for change in significant_changes[:3]:  # Show top 3
                events.append(f"   • {change}")
        
        return events
    
    def run_full_check(self) -> None:
        """Run complete evolution check"""
        print("🔍 BOT EVOLUTION MONITOR")
        print("=" * 60)
        
        # Basic status
        status = self.check_evolution_status()
        print(f"📅 Check Time: {status['timestamp']}")
        print(f"🧬 DNA File: {'✅ Loaded' if status['dna_loaded'] else '❌ Missing'}")
        print(f"📊 History: {'✅ Loaded' if status['history_loaded'] else '❌ Missing'}")
        print(f"🧠 Memory: {'✅ Loaded' if status['memory_loaded'] else '❌ Missing'}")
        print(f"🎯 Generation: {status['generation']}")
        print(f"🎮 Matches Played: {status['match_count']}")
        
        # Evolution events
        events = self.detect_evolution_events()
        if events:
            print(f"\n🚨 EVOLUTION EVENTS:")
            for event in events:
                print(f"   {event}")
        
        # Detailed analysis
        self.show_dna_comparison()
        self.show_learning_progress()
        self.show_memory_status()
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if status['match_count'] < 5:
            print("   • Play more matches to trigger evolution (need 5+ matches)")
        if status['match_count'] >= 5 and status['generation'] == 0:
            print("   • Evolution should trigger soon - check back after next match")
        if status['generation'] > 0:
            print("   • Bot is evolving! Monitor fitness trends for improvement")
        
        print(f"\n✅ Evolution check complete!")

if __name__ == "__main__":
    monitor = EvolutionMonitor()
    monitor.run_full_check()
