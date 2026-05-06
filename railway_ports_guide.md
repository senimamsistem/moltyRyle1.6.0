# Railway Port Configuration Guide

## Problem: WebSocket 403 Forbidden Error

### Issue:
- Railway FastAPI dashboard intercepting WebSocket connections
- Molty Royale WebSocket connections getting 403 Forbidden
- Dashboard and bot trying to use same port

### Solution: Separate Ports

#### Port Configuration:
```python
# bot/config.py
BOT_PORT = int(os.getenv("PORT", "8080"))      # Bot WebSocket port
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8081"))  # Dashboard web port
```

#### Railway Environment Variables:
1. **PORT**: 8080 (Bot WebSocket - Railway default)
2. **DASHBOARD_PORT**: 8081 (Dashboard web interface)
3. **DASHBOARD_PORT**: Expose port 8081 in Railway settings

### Access Points:
- **Bot WebSocket**: `https://your-app.railway.app/` (port 8080)
- **Dashboard**: `https://your-app.railway.app:8081/` (port 8081)

### Railway Setup Steps:
1. Set `DASHBOARD_PORT=8081` in Railway Variables
2. Expose port 8081 in Railway Service Settings
3. Deploy - bot runs on 8080, dashboard on 8081
4. Access dashboard via port 8081

### Benefits:
- ✅ No WebSocket conflicts
- ✅ Bot connects to Molty Royale server
- ✅ Dashboard accessible separately
- ✅ Clean separation of concerns
