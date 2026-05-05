"""
Unit tests untuk error resilience dan recovery systems
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from bot.utils.resilience import (
    CircuitBreaker, CircuitBreakerOpen, CircuitState,
    RetryConfig, ResilientClient, GracefulDegradation,
    StateRecovery, with_resilience
)


class TestCircuitBreaker:
    """Test suite untuk circuit breaker pattern"""
    
    @pytest.fixture
    def circuit(self):
        from bot.utils.resilience import CircuitBreakerConfig
        return CircuitBreaker("test_circuit", CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.1
        ))
        
    @pytest.mark.asyncio
    async def test_initial_state_closed(self, circuit):
        """Circuit should start in CLOSED state"""
        assert circuit.state == CircuitState.CLOSED
        
    @pytest.mark.asyncio
    async def test_successful_calls_decrement_failure(self, circuit):
        """Successful calls should reduce failure count"""
        circuit.failure_count = 2
        
        async def success_func():
            return "success"
            
        await circuit.call(success_func)
        assert circuit.failure_count == 1
        
    @pytest.mark.asyncio
    async def test_repeated_failures_open_circuit(self, circuit):
        """Repeated failures should open the circuit"""
        async def fail_func():
            raise ValueError("Test error")
            
        # Fail 3 times
        for _ in range(3):
            try:
                await circuit.call(fail_func)
            except ValueError:
                pass
                
        assert circuit.state == CircuitState.OPEN
        
    @pytest.mark.asyncio
    async def test_open_circuit_raises_exception(self, circuit):
        """Calling open circuit should raise CircuitBreakerOpen"""
        circuit.state = CircuitState.OPEN
        circuit.last_failure_time = asyncio.get_event_loop().time()
        
        async def any_func():
            return "result"
            
        with pytest.raises(CircuitBreakerOpen):
            await circuit.call(any_func)
            
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, circuit):
        """Circuit should move to HALF_OPEN after timeout"""
        circuit.state = CircuitState.OPEN
        circuit.last_failure_time = asyncio.get_event_loop().time() - 0.2
        
        async def success_func():
            return "success"
            
        await circuit.call(success_func)
        assert circuit.state == CircuitState.CLOSED
        
    @pytest.mark.asyncio
    async def test_half_open_fails_reopens(self, circuit):
        """Failure in HALF_OPEN should reopen circuit"""
        circuit.state = CircuitState.OPEN
        circuit.last_failure_time = asyncio.get_event_loop().time() - 0.2
        
        async def fail_func():
            raise ValueError("Test error")
            
        try:
            await circuit.call(fail_func)
        except ValueError:
            pass
            
        assert circuit.state == CircuitState.OPEN


class TestRetryLogic:
    """Test suite untuk retry mechanisms"""
    
    @pytest.fixture
    def resilient_client(self):
        return ResilientClient()
        
    @pytest.mark.asyncio
    async def test_success_no_retry(self, resilient_client):
        """Successful operation should not retry"""
        mock_func = AsyncMock(return_value="success")
        mock_func.__name__ = "test_func"
        
        config = RetryConfig(max_attempts=3)
        result = await resilient_client.with_retry(mock_func, config, "test")
        
        assert result == "success"
        assert mock_func.call_count == 1
        
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, resilient_client):
        """Should retry on failure"""
        mock_func = AsyncMock(side_effect=[ValueError("fail1"), ValueError("fail2"), "success"])
        mock_func.__name__ = "test_func"
        
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = await resilient_client.with_retry(mock_func, config, "test")
        
        assert result == "success"
        assert mock_func.call_count == 3
        
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, resilient_client):
        """Should raise exception when max retries exceeded"""
        mock_func = AsyncMock(side_effect=ValueError("always fails"))
        mock_func.__name__ = "test_func"
        
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        
        with pytest.raises(ValueError):
            await resilient_client.with_retry(mock_func, config, "test")
            
        assert mock_func.call_count == 3
        
    @pytest.mark.asyncio
    async def test_retry_with_jitter(self, resilient_client):
        """Retry delays should have jitter applied"""
        delays = []
        
        def on_retry(attempt, error, delay):
            delays.append(delay)
            
        mock_func = AsyncMock(side_effect=[ValueError("fail1"), "success"])
        mock_func.__name__ = "test_func"
        
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True,
            on_retry=on_retry
        )
        
        await resilient_client.with_retry(mock_func, config, "test")
        
        # With jitter, delay should be between 0.5x and 1.5x expected
        assert len(delays) == 1
        assert 0.5 <= delays[0] <= 1.5


class TestGracefulDegradation:
    """Test suite untuk graceful degradation"""
    
    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Should use fallback when primary fails"""
        primary = AsyncMock(side_effect=ValueError("Primary failed"))
        fallback = AsyncMock(return_value="fallback_result")
        
        result = await GracefulDegradation.with_fallback(
            primary, fallback, fallback_on=(ValueError,)
        )
        
        assert result == "fallback_result"
        primary.assert_called_once()
        fallback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self):
        """Should not use fallback when primary succeeds"""
        primary = AsyncMock(return_value="primary_result")
        fallback = AsyncMock(return_value="fallback_result")
        
        result = await GracefulDegradation.with_fallback(
            primary, fallback, fallback_on=(ValueError,)
        )
        
        assert result == "primary_result"
        primary.assert_called_once()
        fallback.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self):
        """Should use fallback on timeout"""
        async def slow_func():
            await asyncio.sleep(10)
            return "slow_result"
            
        fallback = AsyncMock(return_value="fallback_result")
        
        result = await GracefulDegradation.with_fallback(
            slow_func, fallback, timeout=0.01
        )
        
        assert result == "fallback_result"
        fallback.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_partial_result_on_failure(self):
        """Should return partial result on failure"""
        async def fail_func():
            raise ValueError("Full failure")
            
        result = await GracefulDegradation.with_partial(
            fail_func,
            partial_result={"data": "partial"},
            acceptable_exceptions=(ValueError,),
            timeout=1.0
        )
        
        assert result == {"data": "partial"}


class TestStateRecovery:
    """Test suite untuk state recovery"""
    
    @pytest.fixture
    def recovery(self):
        return StateRecovery()
        
    def test_checkpoint_save_and_recover(self, recovery):
        """Should save and recover state"""
        state = {"kills": 5, "hp": 80}
        recovery.checkpoint("game_123", state)
        
        recovered = recovery.recover("game_123")
        assert recovered == state
        
    def test_old_checkpoint_discarded(self, recovery):
        """Should discard old checkpoints"""
        import time
        
        state = {"kills": 5}
        recovery.checkpoint("game_123", state)
        
        # Simulate time passing
        recovery._checkpoints["game_123"]["timestamp"] = time.time() - 400
        
        recovered = recovery.recover("game_123", max_age=300)
        assert recovered is None
        
    def test_unknown_checkpoint_returns_none(self, recovery):
        """Should return None untuk unknown checkpoints"""
        recovered = recovery.recover("unknown_game")
        assert recovered is None
        
    def test_clear_checkpoint(self, recovery):
        """Should clear specific checkpoint"""
        recovery.checkpoint("game_123", {"kills": 5})
        recovery.clear_checkpoint("game_123")
        
        recovered = recovery.recover("game_123")
        assert recovered is None


class TestResilienceDecorator:
    """Test suite untuk @with_resilience decorator"""
    
    @pytest.mark.asyncio
    async def test_decorator_adds_resilience(self):
        """Decorator should add retry logic"""
        call_count = 0
        
        @with_resilience(max_retries=3, base_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"
            
        result = await flaky_function()
        assert result == "success"
        assert call_count == 3
        
    @pytest.mark.asyncio
    async def test_decorator_respects_circuit_breaker(self):
        """Decorator should use circuit breaker when specified"""
        call_count = 0
        
        @with_resilience(
            max_retries=2,
            base_delay=0.01,
            circuit_breaker="test_decorator"
        )
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Attempt {call_count}")
            
        # First calls to fail
        for _ in range(2):
            try:
                await always_fails()
            except ValueError:
                pass
                
        # Subsequent calls should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerOpen):
            await always_fails()


class TestCircuitBreakerMetrics:
    """Test circuit breaker metrics dan state reporting"""
    
    @pytest.fixture
    def circuit_with_metrics(self):
        from bot.utils.resilience import CircuitBreakerConfig
        return CircuitBreaker("metrics_test", CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0
        ))
        
    def test_get_state_report(self, circuit_with_metrics):
        """Should provide state information"""
        state = circuit_with_metrics.get_state()
        
        assert state["name"] == "metrics_test"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert "last_failure" in state
