"""
Pytest configuration and shared fixtures
"""
import pytest
import json
from pathlib import Path

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_game_state():
    """Sample game state untuk testing"""
    return {
        "self": {
            "id": "agent-123",
            "name": "TestBot",
            "hp": 80,
            "ep": 10,
            "maxEp": 10,
            "atk": 15,
            "def": 8,
            "isAlive": True,
            "inventory": [],
            "equippedWeapon": None
        },
        "currentRegion": {
            "id": "region-abc",
            "name": "Test Region",
            "terrain": "plains",
            "weather": "clear",
            "isDeathZone": False,
            "connections": ["region-def", "region-ghi"],
            "interactables": []
        },
        "connectedRegions": ["region-def", "region-ghi"],
        "visibleRegions": [],
        "visibleAgents": [],
        "visibleMonsters": [],
        "visibleNPCs": [],
        "visibleItems": [],
        "pendingDeathzones": [],
        "recentLogs": [],
        "recentMessages": [],
        "aliveCount": 100
    }


@pytest.fixture
def sample_enemy_agent():
    """Sample enemy agent untuk combat testing"""
    return {
        "id": "enemy-456",
        "name": "EnemyPlayer",
        "hp": 50,
        "maxHp": 100,
        "ep": 8,
        "atk": 12,
        "def": 5,
        "isAlive": True,
        "isGuardian": False,
        "regionId": "region-abc",
        "equippedWeapon": {"typeId": "sword", "name": "Sword"}
    }


@pytest.fixture
def sample_weapon_item():
    """Sample weapon item untuk pickup testing"""
    return {
        "id": "weapon-789",
        "name": "Katana",
        "typeId": "katana",
        "category": "weapon",
        "regionId": "region-abc"
    }


@pytest.fixture
def sample_healing_item():
    """Sample healing item untuk inventory testing"""
    return {
        "id": "heal-101",
        "name": "Medkit",
        "typeId": "medkit",
        "category": "consumable",
        "regionId": "region-abc"
    }


@pytest.fixture
def mock_websocket_connection():
    """Mock WebSocket connection untuk integration tests"""
    class MockWS:
        def __init__(self):
            self.messages_sent = []
            self.messages_received = []
            self.closed = False
            
        async def send(self, message):
            self.messages_sent.append(message)
            
        async def recv(self):
            if self.messages_received:
                return self.messages_received.pop(0)
            return None
            
        async def close(self):
            self.closed = True
            
        def add_mock_message(self, msg):
            self.messages_received.append(msg)
            
    return MockWS()


@pytest.fixture
def all_weapons():
    """All weapon types untuk parameterized testing"""
    return [
        ("fist", 0, 0),
        ("dagger", 10, 0),
        ("sword", 20, 0),
        ("katana", 35, 0),
        ("bow", 5, 1),
        ("pistol", 10, 1),
        ("sniper", 28, 2),
    ]


@pytest.fixture
def game_phases():
    """Different game phases untuk phase-based strategy testing"""
    return [
        ("early", 95, "WEAPON_SEARCH"),
        ("mid", 45, "WEAPON_SPECIFIC"),
        ("high", 15, "COMBAT_DOMINANCE"),
    ]


@pytest.fixture
def reset_brain_state():
    """Reset brain global state sebelum test"""
    from bot.strategy import brain
    brain.reset_game_state()
    yield
    brain.reset_game_state()
