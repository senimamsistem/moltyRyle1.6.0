"""
Integration tests untuk WebSocket flow dan game engine
"""
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock

from bot.game.websocket_engine import WebSocketEngine
from bot.game.action_sender import ActionSender
from tests.mocks.mock_api import MockWebSocket


class TestWebSocketConnection:
    """Test WebSocket connection handling"""
    
    @pytest.mark.asyncio
    async def test_connection_initialization(self):
        """Test successful connection setup"""
        engine = WebSocketEngine("game-123", "agent-456")
        
        mock_ws = MockWebSocket()
        mock_ws.add_message("connected", {"gameId": "game-123", "agentId": "agent-456"})
        
        with patch('websockets.connect', return_value=mock_ws):
            # Should connect and authenticate
            await engine._connect()
            assert engine.connected is True
            
    @pytest.mark.asyncio
    async def test_reconnection_on_failure(self):
        """Test automatic reconnection"""
        engine = WebSocketEngine("game-123", "agent-456")
        engine.max_reconnect_attempts = 3
        engine.reconnect_delay = 0.1
        
        # Mock failed then success connection
        call_count = 0
        async def mock_connect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            mock_ws = MockWebSocket()
            mock_ws.add_message("connected", {})
            return mock_ws
            
        with patch('websockets.connect', side_effect=mock_connect):
            with patch.object(engine, '_handle_message', new_callable=AsyncMock):
                await engine.run()
                assert call_count == 3  # Should retry until success


class TestMessageHandling:
    """Test message parsing dan action handling"""
    
    @pytest.mark.asyncio
    async def test_agent_view_processing(self):
        """Test agent_view message triggers decision"""
        engine = WebSocketEngine("game-123", "agent-456")
        
        view_data = {
            "self": {
                "id": "agent-456",
                "hp": 100,
                "ep": 10,
                "isAlive": True,
                "inventory": [],
                "equippedWeapon": None
            },
            "currentRegion": {"id": "r1", "name": "Test", "isDeathZone": False},
            "aliveCount": 100,
            "visibleAgents": [],
            "visibleItems": []
        }
        
        mock_ws = MockWebSocket()
        mock_ws.add_agent_view(view_data)
        
        with patch('bot.strategy.brain.decide_action', return_value={
            "action": "rest",
            "data": {},
            "reason": "Test"
        }) as mock_decide:
            with patch.object(engine, '_send', new_callable=AsyncMock) as mock_send:
                await engine._on_agent_view(view_data)
                mock_decide.assert_called_once()


class TestActionSender:
    """Test action envelope building"""
    
    def test_cooldown_action_tracking(self):
        """Test cooldown state updates correctly"""
        sender = ActionSender()
        
        # Initial state
        assert sender.can_act is True
        
        # Update from cooldown result
        sender.update_from_result({
            "canAct": False,
            "cooldownRemainingMs": 50000
        })
        
        assert sender.can_act is False
        assert sender.cooldown_remaining_ms == 50000
        
    def test_can_send_cooldown_action(self):
        """Test cooldown action permissions"""
        sender = ActionSender()
        
        # Should allow when can_act is True
        assert sender.can_send_cooldown_action() is True
        
        # Should deny when can_act is False
        sender.can_act = False
        assert sender.can_send_cooldown_action() is False
        
    def test_action_envelope_format(self):
        """Test action envelope structure"""
        sender = ActionSender()
        
        action = sender.build_action(
            action_type="move",
            data={"regionId": "region-123"},
            reasoning="Test movement",
            planned_action="Move to safe region"
        )
        
        assert action["type"] == "action"
        assert action["data"]["type"] == "move"
        assert action["data"]["regionId"] == "region-123"
        assert "thought" in action
        assert "reasoning" in action["thought"]
        assert "plannedAction" in action["thought"]


class TestGameStateManagement:
    """Test game state tracking"""
    
    @pytest.mark.asyncio
    async def test_game_end_detection(self):
        """Test game ended message handling"""
        engine = WebSocketEngine("game-123", "agent-456")
        
        result_data = {
            "placement": 5,
            "kills": 2,
            "damageDealt": 150,
            "damageTaken": 80,
            "moltz": 50
        }
        
        mock_ws = MockWebSocket()
        mock_ws.add_game_ended(result_data)
        
        msg = {"type": "game_ended", "result": result_data}
        result = await engine._handle_message(json.dumps(msg))
        
        assert result is not None
        assert result.get("type") == "game_ended"


class TestErrorHandling:
    """Test error handling dalam WebSocket flow"""
    
    @pytest.mark.asyncio
    async def test_invalid_message_handling(self):
        """Test graceful handling invalid messages"""
        engine = WebSocketEngine("game-123", "agent-456")
        
        # Invalid JSON
        result = await engine._handle_message("not valid json {{{")
        assert result is None  # Should not crash
        
        # Unknown message type
        result = await engine._handle_message(json.dumps({"type": "unknown_type"}))
        assert result is None  # Should handle gracefully
        
    @pytest.mark.asyncio
    async def test_connection_error_recovery(self):
        """Test recovery dari connection errors"""
        engine = WebSocketEngine("game-123", "agent-456")
        
        error_count = 0
        async def failing_connect(*args, **kwargs):
            nonlocal error_count
            error_count += 1
            if error_count < 2:
                raise ConnectionRefusedError("Server refused")
            mock_ws = MockWebSocket()
            mock_ws.add_message("connected", {})
            return mock_ws
            
        with patch('websockets.connect', side_effect=failing_connect):
            with patch.object(engine, '_handle_message', new_callable=AsyncMock):
                await engine.run()
                assert error_count >= 2
