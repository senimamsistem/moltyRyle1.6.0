# Molty Royale AI Agent - Optimization Roadmap

## Overview
Strategic optimization plan untuk meningkatkan performance bot dari current state ke competitive-ready.

---

## Phase 1: Testing Infrastructure (Foundation)
**Priority: HIGH** | **Duration: 1-2 hari**

### Goals
- Prevent regression bugs
- Enable confident refactoring
- Validate strategy changes

### Tasks
- [x] Create `tests/` directory structure
- [x] Unit tests untuk core decision logic
- [x] Integration tests untuk WebSocket flow
- [x] Mock data generators untuk game states
- [x] CI-ready test runner
- [ ] Run tests dan fix failures (in progress)

### Success Criteria
- [ ] 80%+ code coverage untuk `brain.py`
- [ ] All tests pass before any PR
- [ ] < 30s test execution time

**Files Created:**
- `tests/conftest.py` - Fixtures dan mock data
- `tests/unit/test_combat_logic.py` - Combat tests
- `tests/unit/test_decision_engine.py` - Decision engine tests
- `tests/unit/test_resilience.py` - Resilience system tests
- `tests/integration/test_websocket_flow.py` - WebSocket tests
- `tests/mocks/mock_api.py` - Mock API client
- `tests/run_tests.py` - Test runner
- `pytest.ini` - Pytest configuration
- Updated `requirements.txt` dengan testing deps

---

## Phase 2: Error Resilience & Recovery
**Priority: HIGH** | **Duration: 1 hari**

### Goals
- Reduce downtime dari network failures
- Handle edge cases gracefully
- Auto-recovery tanpa manual intervention

### Tasks
- [x] Enhanced retry dengan circuit breaker pattern
- [x] WebSocket reconnection exponential backoff
- [x] API failure fallback strategies
- [x] State recovery setelah crash
- [x] Graceful degradation untuk partial failures
- [ ] Integration testing dengan real failures

**Files Created:**
- `bot/utils/resilience.py` - Core resilience module
- Enhanced `bot/api_client.py` dengan retry decorators
- Enhanced `bot/game/websocket_engine.py` dengan state recovery

### Success Criteria
- [ ] < 1% downtime dari network issues
- [ ] Auto-recovery dalam < 10s
- [ ] No manual restart required untuk transient errors

---

## Phase 3: Combat Prediction Enhancement
**Priority: MEDIUM** | **Duration: 2-3 hari**

### Goals
- Move dari threshold-based ke probability-based combat decisions
- Better risk assessment
- Higher kill/death ratio

### Tasks
- [x] Win probability calculator (based on HP, weapon, terrain, weather)
- [x] Enemy strength estimation dari historical data
- [x] Expected value (EV) calculation untuk combat actions
- [x] Dynamic risk tolerance adjustment
- [x] Combat outcome prediction logging untuk training data
- [x] Integration dengan brain.py combat logic

### Success Criteria
- [ ] +15% combat success rate
- [ ] +10% K/D ratio improvement
- [ ] < 20% "unnecessary" deaths

**Files Created:**
- `bot/strategy/combat_predictor.py` - Complete prediction engine
- `tests/unit/test_combat_predictor.py` - Comprehensive test suite
- Enhanced `bot/strategy/brain.py` dengan prediction integration

**Features:**
- `CombatPredictor` class dengan probability-based calculations
- `CombatFactors` dataclass untuk semua combat variables
- Weapon matchup matrix (katana vs sniper, dll)
- Terrain & weather modifiers
- Historical performance integration
- Risk classification (low/medium/high/extreme)
- Action recommendations (attack/flee/wait)

---

## Phase 4: Enemy Behavior Profiling
**Priority: MEDIUM** | **Duration: 3-4 hari**

### Goals
- Recognize player patterns
- Counter-strategy adaptation
- Predict enemy movements

### Tasks (Sprint 2 - Partial)
- [x] Enemy player tracking system
- [x] Behavior pattern classification (aggressive/defensive/explorer)
- [x] Counter-strategy selector
- [x] Profile storage dan persistence
- [ ] Predictive movement model (NEXT)
- [ ] Enhanced profile sharing antar games (NEXT)

### Success Criteria
- [ ] 70%+ accuracy dalam predict enemy presence
- [ ] Adapts strategy dalam 3+ encounters dengan player yang sama
- [ ] Reduces surprise attacks by 30%

**Files Created:**
- `bot/learning/enemy_profiler.py` - Enemy profiling system
- `tests/unit/test_enemy_profiler.py` - Test suite
- Enhanced `bot/strategy/brain.py` dengan enemy intelligence integration

**Features:**
- `EnemyProfile` dataclass untuk track encounters
- `EnemyProfiler` class dengan pattern recognition
- Behavior classification: aggressive/defensive/explorer/balanced
- Threat level prediction
- Counter-strategy recommendations
- Profile persistence ke JSON
- Stale profile cleanup

---

## Phase 5: Terrain & Weather Mastery
**Priority: MEDIUM** | **Duration: 2 hari**

### Goals
- Leverage terrain advantages
- Optimal positioning strategy
- Weather-adaptive combat

### Tasks
- [ ] Terrain combat bonus calculator
- [ ] Optimal positioning untuk each weapon type
- [ ] Weather-based movement patterns
- [ ] Death zone avoidance dengan predictive positioning
- [ ] High ground / choke point recognition

### Success Criteria
- [ ] +20% combat win rate di favorable terrain
- [ ] 95%+ survival rate dari death zones
- [ ] Optimal positioning dalam 3 turns dari combat

---

## Phase 6: Advanced Inventory Optimization
**Priority: LOW** | **Duration: 1-2 hari**

### Goals
- Predictive item acquisition
- Long-term resource planning
- Situational item priority

### Tasks
- [ ] Future-phase item need prediction
- [ ] Item combination optimization
- [ ] Drop vs keep decision trees
- [ ] Trading efficiency (if applicable)
- [ ] Item scarcity awareness

### Success Criteria
- [ ] 90%+ inventory utilization efficiency
- [ ] Always have optimal items untuk current phase
- [ ] Reduce "wrong item at wrong time" scenarios

---

## Phase 7: Performance Analytics & Monitoring
**Priority: LOW** | **Duration: 1-2 hari**

### Goals
- Deep performance insights
- Bottleneck identification
- Strategy effectiveness measurement

### Tasks
- [ ] APM (Actions Per Minute) tracking
- [ ] Decision latency measurement
- [ ] Strategy effectiveness heatmaps
- [ ] Resource efficiency metrics
- [ ] Automated performance reports

### Success Criteria
- [ ] < 100ms average decision time
- [ ] Real-time performance dashboard
- [ ] Weekly automated optimization suggestions

---

## Quick Wins (Parallel Tasks) - COMPLETED ✅
Tasks yang bisa dikerjakan kapan saja tanpa blocking:

- [x] Health check endpoint untuk external monitoring (`/api/health`)
- [x] DNA backup before evolution (safety) - auto-backup + API
- [x] DNA manual backup/restore API endpoints
- [ ] Weapon drop rate tracking & analysis (NEXT)
- [ ] Kill/death heatmap generation (NEXT)
- [ ] Enhanced logging dengan structured format (JSON)
- [ ] Configuration validation strict mode

**API Endpoints Added:**
- `GET /api/health` - Health check dengan status dan metrics
- `POST /api/dna/backup` - Manual DNA backup
- `GET /api/dna/backups` - List available backups
- `POST /api/dna/restore` - Restore dari backup

---

## Current Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Testing | 🟡 In Progress | ~70% |
| Phase 2: Resilience | ✅ Complete | 100% |
| Phase 3: Combat Prediction | ✅ Complete | 100% |
| Phase 4: Enemy Profiling | � In Progress | ~60% |
| Phase 5: Terrain Mastery | 🔴 Not Started | 0% |
| Phase 6: Inventory | 🟡 Partial | ~40% (basic smart inventory done) |
| Phase 7: Analytics | 🟡 Partial | ~30% (basic metrics exist) |
| Quick Wins | 🟡 Ongoing | Variable |

---

## Execution Order Recommendation

### Sprint 1 (Completed) ✅
**Date**: 2026-05-05

#### Deliverables:
1. ✅ **Phase 1: Testing Infrastructure**
   - Test framework dengan pytest
   - Unit tests untuk combat logic, decisions, resilience
   - Integration tests untuk WebSocket flow
   - Mock data generators dan API mocks
   - Test runner dengan coverage support

2. ✅ **Phase 2: Error Resilience & Recovery**
   - Circuit breaker pattern untuk API/WebSocket
   - Exponential backoff dengan jitter
   - State recovery setelah crash/disconnect
   - Graceful degradation handlers
   - Enhanced API client dengan retry decorators

3. ✅ **Quick Wins**
   - Health check endpoint: `GET /api/health`
   - DNA auto-backup sebelum evolution
   - Manual DNA backup/restore API
   - Backup cleanup (keep last 5 auto-backups)

#### Files Created/Modified:
- `tests/` - Complete test suite
- `bot/utils/resilience.py` - Resilience module
- Enhanced `bot/api_client.py` dengan retry logic
- Enhanced `bot/game/websocket_engine.py` dengan state recovery
- Enhanced `bot/dashboard/server.py` dengan health check dan DNA backup API
- Enhanced `bot/learning/strategy_dna.py` dengan auto-backup

#### Next: Sprint 2
- Phase 3: Combat Prediction Enhancement
- Phase 4: Enemy Behavior Profiling (partial)

### Sprint 2 (Completed) ✅
**Date**: 2026-05-12

#### Deliverables:
1. ✅ **Phase 3: Combat Prediction Enhancement**
   - Complete probability-based combat prediction engine
   - Win probability calculator dengan multiple factors
   - Risk assessment dan action recommendations
   - Integration dengan existing combat logic

2. ✅ **Phase 4: Enemy Behavior Profiling (Partial)**
   - Enemy tracking dan profiling system
   - Behavior classification (aggressive/defensive/explorer)
   - Counter-strategy recommendations
   - Threat level prediction
   - Profile persistence ke disk

#### Files Created:
- `bot/strategy/combat_predictor.py`
- `bot/learning/enemy_profiler.py`
- `tests/unit/test_combat_predictor.py`
- `tests/unit/test_enemy_profiler.py`

#### Next: Sprint 3
- Phase 4 completion (movement prediction)
- Phase 5: Terrain Mastery
- Phase 6: Advanced Inventory

### Sprint 3 (Next Week - 2026-05-19)
1. Phase 4: Enemy Profiling completion (movement prediction)
2. Phase 5: Terrain Mastery
3. Phase 6: Advanced Inventory (partial)

### Sprint 4 (2026-05-26)
1. Phase 6: Advanced Inventory
2. Phase 7: Analytics

### Sprint 5 (2026-06-02)
1. Full system integration testing
2. Performance tuning dan optimization

---

## Definition of Done

- [ ] All tests passing
- [ ] No regression dalam win rate
- [ ] Performance metrics improved atau maintained
- [ ] Documentation updated
- [ ] Code review completed

---

## 🐛 Bug Fixes

### Circular Import Resolution (2026-05-06)
**Issue**: `ImportError: cannot import name 'WEAPONS' from partially initialized module 'bot.strategy.brain'`

**Root Cause**: `brain.py` imported dari `combat_predictor.py`, dan `combat_predictor.py` import dari `brain.py`

**Solution**: 
- Created `bot/strategy/constants.py` untuk shared constants
- Moved `WEAPONS`, `WEAPON_STRATEGIES`, `WEATHER_COMBAT_PENALTY`, `WEAPON_PRIORITY`, `ITEM_PRIORITY`, `RECOVERY_ITEMS`
- Both `brain.py` dan `combat_predictor.py` sekarang import dari `constants.py`

**Files Modified**:
- Created `bot/strategy/constants.py`
- Updated `bot/strategy/brain.py` - removed duplicate constant definitions
- Updated `bot/strategy/combat_predictor.py` - changed import source

---

**Created**: 2026-05-05  
**Last Updated**: 2026-05-06  
**Next Review**: Weekly atau setelah setiap sprint completion
