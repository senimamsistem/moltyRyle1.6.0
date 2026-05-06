"""
Dashboard web server — serves the UI and real-time WebSocket updates.
Uses FastAPI for uvicorn compatibility.
"""
import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from bot.dashboard.state import dashboard_state
from bot.learning.strategy_dna import DEFAULT_DNA, StrategyDNA, DNA_FILE, MATCH_HISTORY_FILE, sanitize_dna
from bot.utils.logger import get_logger, setup_dashboard_logging

log = get_logger(__name__)

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(DASHBOARD_DIR, "static")

# Connected WebSocket clients for real-time push
_ws_clients: set = set()


def create_app():
    """Create and configure the FastAPI app."""
    app = FastAPI(title="Molty Royale Dashboard")
    
    # Setup dashboard logging - redirect all terminal logs to dashboard
    setup_dashboard_logging(dashboard_state)
    log.info("🌐 Dashboard logging initialized - terminal logs will appear in dashboard")
    
    # Mount static files
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    
    # Add all routes
    app.include_router(app)
    
    # Add startup event to start push loop safely
    @app.on_event("startup")
    async def startup_event():
        """Start background tasks after app is fully initialized."""
        asyncio.create_task(_push_loop(app))
    
    return app


# FastAPI app
app = create_app()

@app.get("/health")
async def health_check():
    """Railway health check endpoint."""
    return {"status": "healthy", "service": "molty-royale-dashboard"}

@app.get("/", response_class=HTMLResponse)
async def index_handler():
    """Serve the dashboard HTML (no cache to always get latest)."""
    html_path = os.path.join(STATIC_DIR, "index.html")
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return HTMLResponse(content, headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

@app.get("/api/state")
async def api_state():
    """Return full dashboard state snapshot."""
    return JSONResponse(dashboard_state.get_snapshot())


@app.get("/api/accounts")
async def api_accounts():
    """Return accounts list."""
    return JSONResponse({"accounts": dashboard_state.accounts})


@app.get("/api/export")
async def api_export():
    """Export all data as JSON download."""
    data = dashboard_state.get_snapshot()
    return JSONResponse(data, headers={
        "Content-Disposition": "attachment; filename=molty-export.json"
    })


@app.get("/api/evolution")
async def api_evolution():
    """Return evolution data for dashboard."""
    return JSONResponse(dashboard_state.get_evolution_data())


def _load_json_file(path: str, fallback):
    """Load JSON data for dashboard widgets."""
    try:
        if not os.path.exists(path):
            return fallback
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return fallback


def _num(value, default=0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _fitness(match: dict) -> float:
    return StrategyDNA().calculate_fitness({
        "placement": _num(match.get("placement", 100), 100),
        "kills": _num(match.get("kills", 0), 0),
        "survival_time": _num(match.get("survival_time", 0), 0),
        "damage_dealt": _num(match.get("damage_dealt", 0), 0),
    })


async def api_learning(request):
    """Return learning DNA + match history summary for the web dashboard."""
    history = _load_json_file(MATCH_HISTORY_FILE, [])
    if not isinstance(history, list):
        history = []

    raw_dna = _load_json_file(DNA_FILE, {})
    dna_saved = bool(raw_dna)
    dna = sanitize_dna(raw_dna or DEFAULT_DNA)

    placements = [_num(m.get("placement", 100), 100) for m in history]
    kills = [_num(m.get("kills", 0), 0) for m in history]
    survival = [_num(m.get("survival_time", 0), 0) for m in history]
    damage = [_num(m.get("damage_dealt", 0), 0) for m in history]

    total = len(history)
    wins = sum(1 for p in placements if int(p) == 1)
    top10 = sum(1 for p in placements if p <= 10)

    recent = []
    for match in list(reversed(history[-10:])):
        fitness = match.get("fitness")
        if fitness is None:
            fitness = _fitness(match)
        recent.append({
            "timestamp": str(match.get("timestamp", ""))[:16],
            "placement": int(_num(match.get("placement", 100), 100)),
            "kills": int(_num(match.get("kills", 0), 0)),
            "survival_time": int(_num(match.get("survival_time", 0), 0)),
            "damage_dealt": int(_num(match.get("damage_dealt", 0), 0)),
            "fitness": round(_num(fitness, 0), 1),
        })

    avg_kills = (sum(kills) / total) if total else 0
    avg_placement = (sum(placements) / total) if total else 0
    recommendations = []
    if total < 5:
        recommendations.append("Data masih sedikit. Kumpulkan minimal 5 match supaya evolusi DNA lebih masuk akal.")
    if total and avg_placement > 50:
        recommendations.append("Survival masih rendah. Pertahankan combat HP floor dan jangan terlalu cepat cari fight.")
    if total and avg_kills < 1:
        recommendations.append("Kill masih rendah. Naikkan agresi late game hanya kalau survival sudah membaik.")
    if total and avg_placement <= 10:
        recommendations.append("Placement bagus. Jaga balance survival dan combat seperti sekarang.")
    if not recommendations:
        recommendations.append("Learning siap. Lanjut kumpulkan match untuk melihat tren yang lebih jelas.")

    return web.json_response({
        "dna": dna,
        "dna_saved": dna_saved,
        "summary": {
            "total_matches": total,
            "wins": wins,
            "top10": top10,
            "avg_placement": round((sum(placements) / total) if total else 0, 1),
            "avg_kills": round(avg_kills, 1),
            "avg_survival": round((sum(survival) / total) if total else 0),
            "total_kills": int(sum(kills)),
            "total_damage": int(sum(damage)),
        },
        "recent": recent,
        "recommendations": recommendations,
    })


async def ws_handler(request):
    """WebSocket endpoint — client stays connected for push updates."""
    ws = web.WebSocketResponse(heartbeat=30)  # 30s ping/pong keepalive
    await ws.prepare(request)
    _ws_clients.add(ws)
    log.info("Dashboard WS client connected (%d total)", len(_ws_clients))

    try:
        # Send initial snapshot
        snapshot = dashboard_state.get_snapshot()
        await ws.send_json({"type": "snapshot", "data": snapshot})

        # Keep connection alive — listen for client messages
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                pass  # No client commands yet
            elif msg.type in (web.WSMsgType.ERROR, web.WSMsgType.CLOSE):
                break
    except Exception as e:
        log.debug("WS handler error: %s", e)
    finally:
        _ws_clients.discard(ws)
        log.info("Dashboard WS client disconnected (%d remaining)", len(_ws_clients))

    return ws


async def _push_loop(app):
    """Background task: push state snapshots to all WS clients every 1.5s."""
    global _ws_clients
    log.info("Dashboard push loop started")
    try:
        while True:
            await asyncio.sleep(1.5)
            if not _ws_clients:
                continue
            try:
                snapshot = dashboard_state.get_snapshot()
                msg = json.dumps({"type": "snapshot", "data": snapshot})
                dead = set()
                for ws in list(_ws_clients):  # Copy set to avoid mutation during iteration
                    try:
                        await ws.send_str(msg)
                    except Exception:
                        dead.add(ws)
                if dead:
                    _ws_clients -= dead
                    log.debug("Removed %d dead WS clients", len(dead))
            except Exception as e:
                log.warning("Dashboard push error: %s", e)
    except asyncio.CancelledError:
        log.info("Dashboard push loop stopped")


async def start_push_loop(app):
    """Start push loop as background task on app startup."""
    app['push_task'] = asyncio.create_task(_push_loop(app))


async def stop_push_loop(app):
    """Stop push loop on app shutdown."""
    task = app.get('push_task')
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.post("/api/accounts")
async def api_accounts_post(request_data: dict):
    """Save account from dashboard form."""
    try:
        dashboard_state.set_account(request_data)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/import")
async def api_import(request_data: dict):
    """Import data from JSON."""
    try:
        if "accounts" in request_data:
            for acc in request_data["accounts"]:
                dashboard_state.set_account(acc)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/health")
async def api_health():
    """Health check endpoint untuk monitoring."""
    import time
    from bot.learning.strategy_dna import StrategyDNA
    
    # Collect health metrics
    dna = StrategyDNA()
    history_count = len(dna.match_history)
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.6.0",
        "components": {
            "dashboard": "ok",
            "learning": "ok" if history_count > 0 else "no_data",
            "dna_ready": dna.dna is not None,
        },
        "metrics": {
            "matches_recorded": history_count,
            "dna_generation": dna.generation,
        }
    }
    
    # Determine overall status
    if health_status["components"]["learning"] == "no_data":
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(health_status, status_code=status_code)


@app.post("/api/dna/backup")
async def api_dna_backup():
    """Create manual DNA backup."""
    import shutil
    from datetime import datetime
    from bot.learning.strategy_dna import DNA_FILE
    
    try:
        if not os.path.exists(DNA_FILE):
            return JSONResponse(
                {"error": "No DNA file to backup"}, 
                status_code=404
            )
        
        # Create backup dengan timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{DNA_FILE}.{timestamp}.backup"
        
        shutil.copy2(DNA_FILE, backup_path)
        
        return JSONResponse({
            "ok": True,
            "backup_path": backup_path,
            "timestamp": timestamp,
            "message": f"DNA backed up to {backup_path}"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/dna/backups")
async def api_dna_list_backups():
    """List available DNA backups."""
    import glob
    from bot.learning.strategy_dna import DNA_FILE
    
    backup_pattern = f"{DNA_FILE}.*.backup"
    backups = glob.glob(backup_pattern)
    
    backup_info = []
    for backup in sorted(backups, reverse=True)[:10]:  # Last 10
        try:
            stat = os.stat(backup)
            backup_info.append({
                "path": backup,
                "created": stat.st_mtime,
                "size": stat.st_size
            })
        except OSError:
            pass
    
    return JSONResponse({
        "backups": backup_info,
        "count": len(backup_info)
    })


@app.post("/api/dna/restore")
async def api_dna_restore(request_data: dict):
    """Restore DNA from backup."""
    import shutil
    from bot.learning.strategy_dna import DNA_FILE
    
    try:
        backup_path = request_data.get("backup_path")
        
        if not backup_path or not os.path.exists(backup_path):
            return JSONResponse(
                {"error": "Backup not found"}, 
                status_code=404
            )
        
        # Create current backup sebelum restore
        if os.path.exists(DNA_FILE):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = f"{DNA_FILE}.{timestamp}.prerestore"
            shutil.copy2(DNA_FILE, pre_restore_backup)
        
        # Restore
        shutil.copy2(backup_path, DNA_FILE)
        
        return JSONResponse({
            "ok": True,
            "message": "DNA restored successfully",
            "restored_from": backup_path
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Add missing endpoints
@app.get("/api/learning")
async def api_learning():
    """Return learning data for dashboard."""
    try:
        from bot.learning.strategy_dna import StrategyDNA, DEFAULT_DNA
        dna = StrategyDNA()
        
        return JSONResponse({
            "dna": dna.dna,
            "default_dna": DEFAULT_DNA,
            "generation": dna.generation,
            "match_count": len(dna.match_history)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# Add WebSocket support
@app.websocket("/ws")
async def ws_handler(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)


# Mount static files
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
