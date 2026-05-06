"""
Molty Royale AI Agent — Entry Point v2.0.
Run: python -m bot.main
Dashboard + Bot run concurrently.
"""
import asyncio
import signal
import sys
import os
from pathlib import Path

from bot.utils.logger import get_logger
from bot.config import DASHBOARD_PORT
from bot.dashboard.state import dashboard_state
from bot.game.websocket_engine import WebSocketEngine
from bot.credentials import get_api_key
from bot.memory.agent_memory import AgentMemory
from bot.dashboard.evolution_web import app as evolution_app
from bot.autonomous_integration import autonomous_manager
from bot.heartbeat import Heartbeat

log = get_logger(__name__)


async def start_evolution_dashboard():
    """Start evolution dashboard server"""
    try:
        import uvicorn
    except ImportError:
        log.warning("⚠️ uvicorn not available - dashboard disabled")
        return
    
    log.info("🌐 Starting Evolution Dashboard on port %s", DASHBOARD_PORT)
    
    # Configure uvicorn for Railway
    config = uvicorn.Config(
        evolution_app,
        host="0.0.0.0",
        port=DASHBOARD_PORT,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Entry point for the bot with autonomous AI integration."""
    log.info("Molty Royale AI Agent v1.6.0")
    log.info("By Eryck Juliant")
    log.info("🤖 Autonomous AI System: Initializing...")
    
    # Initialize autonomous AI system
    await autonomous_manager.initialize_autonomous_system()
    
    log.info("Press Ctrl+C to stop")

    heartbeat = Heartbeat()

    async def run_all():
        # Start evolution dashboard server (non-blocking)
        dashboard_task = asyncio.create_task(start_evolution_dashboard())
        
        # Give dashboard a moment to start
        await asyncio.sleep(1)
        
        # Run heartbeat (main bot loop — runs forever)
        await heartbeat.run()

    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        await run_all()
    except KeyboardInterrupt:
        log.info("Shutdown complete.")

def main_sync():
    """Synchronous entry point for backwards compatibility."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
