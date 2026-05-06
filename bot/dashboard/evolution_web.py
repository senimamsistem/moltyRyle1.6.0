"""
Railway Evolution Dashboard
Monitor bot evolution via web interface - no terminal needed
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Add bot to path
sys.path.insert(0, '.')
from bot.learning.strategy_dna import StrategyDNA, DNA_FILE, MATCH_HISTORY_FILE
from bot.memory.agent_memory import AgentMemory, MEMORY_FILE

app = FastAPI(title="Bot Evolution Dashboard")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main evolution dashboard"""
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Bot Evolution Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { text-align: center; color: #333; }
        .status { display: flex; justify-content: space-between; flex-wrap: wrap; }
        .status-item { text-align: center; padding: 10px; }
        .status-value { font-size: 2em; font-weight: bold; color: #4CAF50; }
        .evolved { color: #ff9800; }
        .declining { color: #f44336; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .change-positive { color: #4CAF50; }
        .change-negative { color: #f44336; }
        .refresh-btn { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #45a049; }
        .alert { padding: 15px; margin: 10px 0; border-radius: 4px; }
        .alert-success { background-color: #d4edda; border: 1px solid #c3e6cb; }
        .alert-info { background-color: #d1ecf1; border: 1px solid #bee5eb; }
        .alert-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Bot Evolution Dashboard</h1>
            <p>Monitor bot learning progress and parameter evolution</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>

        <div id="status-card" class="card">
            <h2>📊 Evolution Status</h2>
            <div class="status">
                <div class="status-item">
                    <div class="status-value" id="generation">-</div>
                    <div>Generation</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="matches">-</div>
                    <div>Matches</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="fitness">-</div>
                    <div>Last Fitness</div>
                </div>
                <div class="status-item">
                    <div class="status-value" id="last-evolution">-</div>
                    <div>Last Evolution</div>
                </div>
            </div>
        </div>

        <div id="evolution-events" class="card">
            <h2>🚨 Evolution Events</h2>
            <div id="events-content">Loading...</div>
        </div>

        <div id="dna-comparison" class="card">
            <h2>🧬 DNA Parameter Evolution</h2>
            <table id="dna-table">
                <thead>
                    <tr>
                        <th>Parameter</th>
                        <th>Default</th>
                        <th>Current</th>
                        <th>Change</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="dna-tbody">
                    <tr><td colspan="5">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <div id="learning-progress" class="card">
            <h2>📈 Learning Progress</h2>
            <div id="progress-content">Loading...</div>
        </div>

        <div id="memory-status" class="card">
            <h2>🧠 Agent Memory</h2>
            <div id="memory-content">Loading...</div>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setInterval(() => {
            location.reload();
        }, 30000);

        // Load data on page load
        window.onload = function() {
            loadEvolutionData();
        };

        async function loadEvolutionData() {
            try {
                const response = await fetch('/api/evolution-data');
                const data = await response.json();
                
                updateStatus(data);
                updateEvents(data);
                updateDNA(data);
                updateProgress(data);
                updateMemory(data);
            } catch (error) {
                console.error('Error loading evolution data:', error);
            }
        }

        function updateStatus(data) {
            document.getElementById('generation').textContent = data.generation || '0';
            document.getElementById('matches').textContent = data.match_count || '0';
            document.getElementById('fitness').textContent = data.last_fitness ? data.last_fitness.toFixed(1) : '-';
            document.getElementById('last-evolution').textContent = data.last_evolution || 'Never';
        }

        function updateEvents(data) {
            const eventsDiv = document.getElementById('events-content');
            if (data.evolution_events && data.evolution_events.length > 0) {
                eventsDiv.innerHTML = data.evolution_events.map(event => 
                    `<div class="alert alert-info">🔔 ${event}</div>`
                ).join('');
            } else {
                eventsDiv.innerHTML = '<div class="alert alert-warning">⚠️ No evolution events yet. Play more matches!</div>';
            }
        }

        function updateDNA(data) {
            const tbody = document.getElementById('dna-tbody');
            if (data.dna_comparison) {
                tbody.innerHTML = data.dna_comparison.map(param => {
                    const changeClass = param.significant_change ? 'change-positive' : '';
                    const status = param.significant_change ? '🔥 Evolved' : 'Stable';
                    return `
                        <tr>
                            <td>${param.parameter}</td>
                            <td>${param.default}</td>
                            <td>${param.current}</td>
                            <td class="${changeClass}">${param.change}</td>
                            <td>${status}</td>
                        </tr>
                    `;
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="5">No DNA data available</td></tr>';
            }
        }

        function updateProgress(data) {
            const progressDiv = document.getElementById('progress-content');
            if (data.learning_progress) {
                const progress = data.learning_progress;
                let html = `
                    <div class="status">
                        <div class="status-item">
                            <div class="status-value">${progress.total_matches}</div>
                            <div>Total Matches</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value ${progress.fitness_trend > 0 ? 'evolved' : progress.fitness_trend < 0 ? 'declining' : ''}">${progress.fitness_trend > 0 ? '+' : ''}${progress.fitness_trend.toFixed(1)}</div>
                            <div>Fitness Trend</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">${progress.avg_placement.toFixed(1)}</div>
                            <div>Avg Placement</div>
                        </div>
                    </div>
                `;
                
                if (progress.recent_matches && progress.recent_matches.length > 0) {
                    html += '<h3>Recent Matches (Last 10)</h3>';
                    html += '<table><thead><tr><th>Match</th><th>Placement</th><th>Kills</th><th>Fitness</th></tr></thead><tbody>';
                    html += progress.recent_matches.map(match => 
                        `<tr>
                            <td>#${match.match}</td>
                            <td>${match.placement}</td>
                            <td>${match.kills}</td>
                            <td>${match.fitness.toFixed(1)}</td>
                        </tr>`
                    ).join('');
                    html += '</tbody></table>';
                }
                
                progressDiv.innerHTML = html;
            } else {
                progressDiv.innerHTML = '<div class="alert alert-warning">⚠️ No learning progress data yet</div>';
            }
        }

        function updateMemory(data) {
            const memoryDiv = document.getElementById('memory-content');
            if (data.memory_status) {
                const memory = data.memory_status;
                memoryDiv.innerHTML = `
                    <div class="status">
                        <div class="status-item">
                            <div class="status-value">${memory.total_games}</div>
                            <div>Total Games</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">${memory.wins}</div>
                            <div>Wins</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">${memory.avg_kills.toFixed(1)}</div>
                            <div>Avg Kills</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value">${memory.lessons}</div>
                            <div>Lessons</div>
                        </div>
                    </div>
                `;
            } else {
                memoryDiv.innerHTML = '<div class="alert alert-warning">⚠️ No memory data available</div>';
            }
        }
    </script>
</body>
</html>
    """)

@app.get("/api/evolution-data")
async def get_evolution_data():
    """Get evolution data as JSON"""
    try:
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
