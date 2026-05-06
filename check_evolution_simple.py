#!/usr/bin/env python3
"""
Simple Evolution Checker
Quick way to check if bot is evolving
"""
import json
from pathlib import Path
from datetime import datetime

def quick_evolution_check():
    """Quick check for evolution status"""
    print("🔍 QUICK EVOLUTION CHECK")
    print("=" * 40)
    
    # Check DNA file
    dna_file = Path("data/strategy_dna.json")
    if dna_file.exists():
        with open(dna_file, 'r') as f:
            dna = json.load(f)
        print("✅ DNA File: Found")
        
        # Show key evolved parameters
        key_params = {
            "aggression_early": dna.get("aggression_early", "N/A"),
            "combat_hp_threshold": dna.get("combat_hp_threshold", "N/A"),
            "weapon_priority_boost": dna.get("weapon_priority_boost", "N/A"),
            "hunting_weight": dna.get("hunting_weight", "N/A")
        }
        
        print("\n🧬 KEY PARAMETERS:")
        for param, value in key_params.items():
            print(f"   {param}: {value}")
    else:
        print("❌ DNA File: Not found (no evolution yet)")
    
    # Check match history
    history_file = Path("data/match_history.json")
    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)
        print(f"\n📊 Match History: {len(history)} matches")
        
        if history:
            latest = history[-1]
            print(f"   Latest Placement: {latest.get('placement', 'N/A')}")
            print(f"   Latest Fitness: {latest.get('fitness', 'N/A'):.1f}")
            print(f"   Generation: {latest.get('generation', 'N/A')}")
    else:
        print("❌ Match History: Not found")
    
    # Check for evolution backups
    data_dir = Path("data")
    if data_dir.exists():
        backups = list(data_dir.glob("strategy_dna.json.*.autobackup"))
        if backups:
            latest_backup = max(backups, key=lambda f: f.stat().st_mtime)
            backup_time = datetime.fromtimestamp(latest_backup.stat().st_mtime)
            print(f"\n🔄 Last Evolution: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n🔄 No evolution backups found")
    
    print("\n💡 HOW TO CHECK EVOLUTION:")
    print("   1. Run this script after playing matches")
    print("   2. Look for parameter changes vs defaults")
    print("   3. Check generation number increases")
    print("   4. Monitor fitness trends over time")

if __name__ == "__main__":
    quick_evolution_check()
