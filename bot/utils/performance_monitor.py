"""
Performance Monitor - Track decision latency dan operational metrics

Features:
1. Decision latency measurement (<100ms target)
2. Action execution tracking
3. Performance statistics dan reporting
4. Latency alerts untuk slow decisions
5. Historical performance data
"""
import time
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from bot.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class DecisionMetrics:
    """Metrics untuk single decision"""
    timestamp: float
    latency_ms: float
    action_type: str
    game_phase: str
    alive_count: int
    success: bool
    error: Optional[str] = None


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance statistics"""
    timestamp: float
    total_decisions: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    slow_decisions_count: int  # >100ms
    target_compliance_rate: float  # % under 100ms


class PerformanceMonitor:
    """
    Performance Monitor untuk track decision latency dan operational metrics.
    
    Target: <100ms decision latency
    """
    
    # Target latency dalam milliseconds
    TARGET_LATENCY_MS = 100
    WARNING_LATENCY_MS = 150
    CRITICAL_LATENCY_MS = 250
    
    # Keep last N decisions untuk rolling statistics
    MAX_HISTORY_SIZE = 1000
    
    def __init__(self):
        self._decision_history: deque = deque(maxlen=self.MAX_HISTORY_SIZE)
        self._action_history: deque = deque(maxlen=500)
        self._last_report_time: float = 0.0
        self._report_interval: float = 60.0  # Generate report every 60 seconds
        self._slow_decision_count: int = 0
        self._total_decision_count: int = 0
        
        # Track latency by game phase
        self._phase_latencies: Dict[str, List[float]] = {
            "early": [],
            "mid": [],
            "late": [],
            "endgame": []
        }
        
        # Track latency by action type
        self._action_latencies: Dict[str, List[float]] = {
            "move": [],
            "attack": [],
            "use_item": [],
            "rest": [],
            "interact": [],
            "wait": []
        }
    
    def record_decision_start(self) -> float:
        """
        Record start of decision process.
        Returns start timestamp untuk use dengan record_decision_end.
        """
        return time.perf_counter()
    
    def record_decision_end(
        self,
        start_time: float,
        action_type: str,
        game_phase: str,
        alive_count: int,
        success: bool = True,
        error: Optional[str] = None
    ) -> DecisionMetrics:
        """
        Record end of decision process dan calculate latency.
        
        Returns DecisionMetrics dengan latency information.
        """
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        
        metrics = DecisionMetrics(
            timestamp=time.time(),
            latency_ms=latency_ms,
            action_type=action_type,
            game_phase=game_phase,
            alive_count=alive_count,
            success=success,
            error=error
        )
        
        # Store in history
        self._decision_history.append(metrics)
        self._total_decision_count += 1
        
        # Track slow decisions
        if latency_ms > self.TARGET_LATENCY_MS:
            self._slow_decision_count += 1
            
            # Log warning untuk slow decisions
            if latency_ms > self.CRITICAL_LATENCY_MS:
                log.error("⏱️ LATENCY_CRITICAL: Decision took %.1fms (target: %dms) | Action: %s | Phase: %s",
                          latency_ms, self.TARGET_LATENCY_MS, action_type, game_phase)
            elif latency_ms > self.WARNING_LATENCY_MS:
                log.warning("⏱️ LATENCY_WARNING: Decision took %.1fms (target: %dms) | Action: %s | Phase: %s",
                            latency_ms, self.TARGET_LATENCY_MS, action_type, game_phase)
            else:
                log.info("⏱️ LATENCY_SLOW: Decision took %.1fms (target: %dms) | Action: %s",
                         latency_ms, self.TARGET_LATENCY_MS, action_type)
        else:
            # Fast decision - debug level only
            log.debug("⏱️ LATENCY_OK: Decision took %.1fms | Action: %s", latency_ms, action_type)
        
        # Track by phase
        if game_phase in self._phase_latencies:
            self._phase_latencies[game_phase].append(latency_ms)
            # Keep only last 100 per phase
            if len(self._phase_latencies[game_phase]) > 100:
                self._phase_latencies[game_phase].pop(0)
        
        # Track by action type
        if action_type in self._action_latencies:
            self._action_latencies[action_type].append(latency_ms)
            # Keep only last 100 per action
            if len(self._action_latencies[action_type]) > 100:
                self._action_latencies[action_type].pop(0)
        
        return metrics
    
    def record_action_executed(self, action_type: str, success: bool = True, error: str = None):
        """Record that an action was executed"""
        self._action_history.append({
            "timestamp": time.time(),
            "action_type": action_type,
            "success": success,
            "error": error
        })
    
    def get_current_statistics(self) -> Dict:
        """Get current performance statistics"""
        if not self._decision_history:
            return {
                "status": "no_data",
                "message": "No decisions recorded yet"
            }
        
        latencies = [m.latency_ms for m in self._decision_history]
        
        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)
        p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
        p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]
        
        # Count slow decisions in recent history
        recent_slow = sum(1 for l in latencies if l > self.TARGET_LATENCY_MS)
        compliance_rate = ((len(latencies) - recent_slow) / len(latencies)) * 100
        
        return {
            "status": "ok",
            "total_decisions": self._total_decision_count,
            "sample_size": len(latencies),
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "p99_latency_ms": round(p99_latency, 2),
            "slow_decisions": recent_slow,
            "target_compliance_rate": round(compliance_rate, 1),
            "target_met": avg_latency <= self.TARGET_LATENCY_MS,
            "performance_grade": self._calculate_grade(avg_latency, compliance_rate)
        }
    
    def _calculate_grade(self, avg_latency: float, compliance_rate: float) -> str:
        """Calculate performance grade"""
        if avg_latency <= 50 and compliance_rate >= 99:
            return "S"  # Excellent
        elif avg_latency <= 80 and compliance_rate >= 95:
            return "A"  # Great
        elif avg_latency <= 100 and compliance_rate >= 90:
            return "B"  # Good
        elif avg_latency <= 150 and compliance_rate >= 80:
            return "C"  # Acceptable
        elif avg_latency <= 200 and compliance_rate >= 70:
            return "D"  # Poor
        else:
            return "F"  # Failing
    
    def get_phase_statistics(self) -> Dict:
        """Get latency statistics by game phase"""
        stats = {}
        for phase, latencies in self._phase_latencies.items():
            if latencies:
                stats[phase] = {
                    "count": len(latencies),
                    "avg_ms": round(sum(latencies) / len(latencies), 2),
                    "max_ms": round(max(latencies), 2),
                    "slow_count": sum(1 for l in latencies if l > self.TARGET_LATENCY_MS)
                }
        return stats
    
    def get_action_statistics(self) -> Dict:
        """Get latency statistics by action type"""
        stats = {}
        for action, latencies in self._action_latencies.items():
            if latencies:
                stats[action] = {
                    "count": len(latencies),
                    "avg_ms": round(sum(latencies) / len(latencies), 2),
                    "max_ms": round(max(latencies), 2)
                }
        return stats
    
    def check_and_report(self) -> Optional[PerformanceSnapshot]:
        """
        Check if it's time to generate report dan generate if needed.
        Returns PerformanceSnapshot jika report generated, None otherwise.
        """
        current_time = time.time()
        if current_time - self._last_report_time < self._report_interval:
            return None
        
        self._last_report_time = current_time
        
        stats = self.get_current_statistics()
        if stats.get("status") != "ok":
            return None
        
        # Generate snapshot
        latencies = [m.latency_ms for m in self._decision_history]
        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)
        
        snapshot = PerformanceSnapshot(
            timestamp=current_time,
            total_decisions=self._total_decision_count,
            avg_latency_ms=stats["avg_latency_ms"],
            min_latency_ms=stats["min_latency_ms"],
            max_latency_ms=stats["max_latency_ms"],
            p95_latency_ms=sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)],
            p99_latency_ms=sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)],
            slow_decisions_count=stats["slow_decisions"],
            target_compliance_rate=stats["target_compliance_rate"]
        )
        
        # Log performance report
        log.info("=" * 60)
        log.info("⏱️ PERFORMANCE REPORT (Last %d decisions)", len(latencies))
        log.info("=" * 60)
        log.info("Average Latency: %.2fms (Target: %dms)", 
                 stats["avg_latency_ms"], self.TARGET_LATENCY_MS)
        log.info("Min/Max: %.2fms / %.2fms", 
                 stats["min_latency_ms"], stats["max_latency_ms"])
        log.info("P95/P99: %.2fms / %.2fms", 
                 stats["p95_latency_ms"], stats["p99_latency_ms"])
        log.info("Slow Decisions (>100ms): %d (%.1f%%)", 
                 stats["slow_decisions"], 100 - stats["target_compliance_rate"])
        log.info("Target Compliance: %.1f%%", stats["target_compliance_rate"])
        log.info("Performance Grade: %s", stats["performance_grade"])
        
        # Log phase breakdown
        phase_stats = self.get_phase_statistics()
        if phase_stats:
            log.info("-" * 40)
            log.info("By Game Phase:")
            for phase, data in phase_stats.items():
                log.info("  %s: avg=%.1fms, max=%.1fms, slow=%d", 
                        phase.upper(), data["avg_ms"], data["max_ms"], data["slow_count"])
        
        # Log action breakdown
        action_stats = self.get_action_statistics()
        if action_stats:
            log.info("-" * 40)
            log.info("By Action Type:")
            for action, data in action_stats.items():
                log.info("  %s: avg=%.1fms, max=%.1fms", 
                        action, data["avg_ms"], data["max_ms"])
        
        log.info("=" * 60)
        
        return snapshot
    
    def reset_statistics(self):
        """Reset all performance statistics"""
        self._decision_history.clear()
        self._action_history.clear()
        self._slow_decision_count = 0
        self._total_decision_count = 0
        for phase in self._phase_latencies:
            self._phase_latencies[phase].clear()
        for action in self._action_latencies:
            self._action_latencies[action].clear()
        log.info("⏱️ Performance statistics reset")
    
    def get_summary(self) -> Dict:
        """Get summary of performance monitor state"""
        return {
            "total_decisions": self._total_decision_count,
            "slow_decisions": self._slow_decision_count,
            "target_latency_ms": self.TARGET_LATENCY_MS,
            "history_size": len(self._decision_history),
            "last_report": self._last_report_time,
            "current_stats": self.get_current_statistics()
        }


# Global instance
performance_monitor = PerformanceMonitor()


def start_decision_timing() -> float:
    """Convenience function untuk start timing"""
    return performance_monitor.record_decision_start()


def end_decision_timing(
    start_time: float,
    action_type: str,
    game_phase: str,
    alive_count: int,
    success: bool = True,
    error: str = None
) -> DecisionMetrics:
    """Convenience function untuk end timing"""
    return performance_monitor.record_decision_end(
        start_time, action_type, game_phase, alive_count, success, error
    )


def record_action(action_type: str, success: bool = True, error: str = None):
    """Convenience function untuk record action"""
    performance_monitor.record_action_executed(action_type, success, error)


def get_performance_report() -> Dict:
    """Convenience function untuk get report"""
    return performance_monitor.get_current_statistics()


def check_performance() -> Optional[PerformanceSnapshot]:
    """Convenience function untuk check dan report"""
    return performance_monitor.check_and_report()
