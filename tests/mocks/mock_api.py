"""
Mock API responses untuk testing tanpa hit real endpoints
"""


class MockMoltyAPI:
    """Mock API client untuk testing"""
    
    def __init__(self, api_key="test-key"):
        self.api_key = api_key
        self.call_count = 0
        self.responses = {}
        
    def set_response(self, endpoint, data):
        """Set mock response untuk endpoint"""
        self.responses[endpoint] = data
        
    async def get_accounts_me(self):
        """Mock account info"""
        self.call_count += 1
        return self.responses.get("/accounts/me", {
            "agentId": "test-agent-123",
            "agentName": "TestAgent",
            "balance": 1000,
            "isAlive": True,
            "currentGameId": None,
            "whitelistStatus": "approved",
            "hasERC8004Identity": True
        })
    
    async def join_free_game(self):
        """Mock free game join"""
        self.call_count += 1
        return ("game-abc-123", "agent-456")
    
    async def join_paid_game(self):
        """Mock paid game join"""
        self.call_count += 1
        return ("game-def-456", "agent-789")
    
    async def close(self):
        """Mock cleanup"""
        pass


class MockWebSocket:
    """Mock WebSocket untuk testing WebSocket engine"""
    
    def __init__(self):
        self.messages = []
        self.outgoing = []
        self.connected = True
        self.closed = False
        
    async def send(self, message):
        """Mock send message"""
        self.outgoing.append(message)
        
    async def recv(self):
        """Mock receive message"""
        if self.messages:
            return self.messages.pop(0)
        # Return default heartbeat jika no messages
        return json.dumps({"type": "heartbeat"})
        
    async def close(self):
        """Mock close connection"""
        self.closed = True
        self.connected = False
        
    def add_message(self, msg_type, data=None):
        """Add mock message untuk receive"""
        msg = {"type": msg_type}
        if data:
            msg.update(data)
        self.messages.append(json.dumps(msg))
        
    def add_agent_view(self, view_data):
        """Add agent_view message"""
        self.add_message("agent_view", {"view": view_data})
        
    def add_turn_advanced(self, turn_data):
        """Add turn_advanced message"""
        self.add_message("turn_advanced", {"data": turn_data})
        
    def add_game_ended(self, result_data):
        """Add game_ended message"""
        self.add_message("game_ended", {"result": result_data})


import json
