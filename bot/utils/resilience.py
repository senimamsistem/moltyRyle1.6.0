"""
Error resilience, retry logic, dan circuit breaker patterns
untuk meningkatkan reliability bot
"""
import asyncio
import time
import random
from functools import wraps
from typing import Callable, TypeVar, Optional, Any
from dataclasses import dataclass
from enum import Enum
from bot.utils.logger import get_logger

log = get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration untuk retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    on_retry: Optional[Callable] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration untuk circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreaker:
    """Circuit breaker pattern untuk mencegah cascade failures"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
        
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function dengan circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    log.info(f"🔓 Circuit {self.name}: Moving to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
                    
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpen(f"Circuit {self.name} HALF_OPEN limit reached")
                self.half_open_calls += 1
                
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
            
    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    log.info(f"✅ Circuit {self.name}: Closing (recovered)")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.half_open_calls = 0
            else:
                self.failure_count = max(0, self.failure_count - 1)
                
    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                log.warning(f"❌ Circuit {self.name}: Opened again (test failed)")
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.config.failure_threshold:
                log.warning(f"🔒 Circuit {self.name}: Opening (threshold reached)")
                self.state = CircuitState.OPEN
                
    def get_state(self) -> dict:
        """Get current circuit state info"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
        }


class CircuitBreakerOpen(Exception):
    """Exception when circuit breaker is open"""
    pass


class ResilientClient:
    """Base class untuk resilient API/WebSocket clients"""
    
    def __init__(self):
        self.circuit_breakers = {}
        self._operation_counters = {}
        
    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get atau create circuit breaker"""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]
        
    async def with_retry(
        self,
        operation: Callable[..., T],
        config: RetryConfig = None,
        operation_name: str = "operation"
    ) -> T:
        """Execute operation dengan retry logic"""
        config = config or RetryConfig()
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                return await operation()
            except config.retryable_exceptions as e:
                last_exception = e
                
                if attempt == config.max_attempts:
                    log.error(f"❌ {operation_name} failed after {attempt} attempts: {e}")
                    raise
                    
                # Calculate delay dengan exponential backoff
                delay = min(
                    config.base_delay * (config.exponential_base ** (attempt - 1)),
                    config.max_delay
                )
                
                # Add jitter untuk menghindari thundering herd
                if config.jitter:
                    delay = delay * (0.5 + random.random())
                    
                log.warning(f"⚠️ {operation_name} attempt {attempt}/{config.max_attempts} failed: {e}. Retrying in {delay:.1f}s...")
                
                if config.on_retry:
                    config.on_retry(attempt, e, delay)
                    
                await asyncio.sleep(delay)
                
        raise last_exception


# Global circuit breakers
_api_circuit_breaker = CircuitBreaker("api_calls", CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=60.0
))

_ws_circuit_breaker = CircuitBreaker("websocket", CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=30.0
))


def with_resilience(
    max_retries: int = 3,
    base_delay: float = 1.0,
    circuit_breaker: str = None,
    retryable_exceptions: tuple = (Exception,)
):
    """Decorator untuk menambahkan resilience ke functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_retries,
                base_delay=base_delay,
                retryable_exceptions=retryable_exceptions
            )
            
            resilient_client = ResilientClient()
            
            async def operation():
                # Jika circuit breaker specified, wrap dengan itu
                if circuit_breaker:
                    cb = resilient_client.get_circuit_breaker(circuit_breaker)
                    return await cb.call(func, *args, **kwargs)
                return await func(*args, **kwargs)
                
            return await resilient_client.with_retry(
                operation,
                config=config,
                operation_name=func.__name__
            )
            
        return wrapper
    return decorator


class GracefulDegradation:
    """Handle partial failures dengan graceful degradation"""
    
    @staticmethod
    async def with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        fallback_on: tuple = (Exception,),
        timeout: float = 30.0
    ):
        """Try primary, fall back ke secondary jika fails"""
        try:
            return await asyncio.wait_for(primary_func(), timeout=timeout)
        except fallback_on as e:
            log.warning(f"⚠️ Primary failed ({e}), using fallback")
            return await fallback_func()
        except asyncio.TimeoutError:
            log.warning(f"⏱️ Primary timeout, using fallback")
            return await fallback_func()
            
    @staticmethod
    async def with_partial(
        func: Callable,
        partial_result: Any,
        acceptable_exceptions: tuple = (Exception,),
        timeout: float = 10.0
    ):
        """Return partial result jika full result fails"""
        try:
            return await asyncio.wait_for(func(), timeout=timeout)
        except acceptable_exceptions as e:
            log.warning(f"⚠️ Using partial result due to: {e}")
            return partial_result


class StateRecovery:
    """Recover state setelah crashes atau disconnections"""
    
    def __init__(self):
        self._checkpoints = {}
        self._last_checkpoint_time = 0
        
    def checkpoint(self, name: str, state: dict):
        """Save state checkpoint"""
        self._checkpoints[name] = {
            "state": state.copy(),
            "timestamp": time.time()
        }
        self._last_checkpoint_time = time.time()
        
    def recover(self, name: str, max_age: float = 300.0) -> Optional[dict]:
        """Recover state dari checkpoint jika masih valid"""
        if name not in self._checkpoints:
            return None
            
        checkpoint = self._checkpoints[name]
        age = time.time() - checkpoint["timestamp"]
        
        if age > max_age:
            log.warning(f"⚠️ Checkpoint {name} too old ({age:.0f}s), discarding")
            del self._checkpoints[name]
            return None
            
        log.info(f"🔄 Recovered state from checkpoint {name} (age: {age:.0f}s)")
        return checkpoint["state"].copy()
        
    def clear_checkpoint(self, name: str):
        """Clear specific checkpoint"""
        if name in self._checkpoints:
            del self._checkpoints[name]


# Export singleton instances
api_circuit_breaker = _api_circuit_breaker
ws_circuit_breaker = _ws_circuit_breaker
state_recovery = StateRecovery()
