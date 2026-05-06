"""
Unit tests untuk Performance Monitor System
"""
import pytest
import time
from bot.utils.performance_monitor import (
    DecisionMetrics, PerformanceSnapshot, PerformanceMonitor,
    performance_monitor, start_decision_timing, end_decision_timing,
    record_action, get_performance_report, check_performance
)


class TestDecisionMetrics:
    """Test DecisionMetrics dataclass"""
    
    def test_creation(self):
        metrics = DecisionMetrics(
            timestamp=time.time(),
            latency_ms=50.0,
            action_type="attack",
            game_phase="mid",
            alive_count=50,
            success=True,
            error=None
        )
        
        assert metrics.latency_ms == 50.0
        assert metrics.action_type == "attack"
        assert metrics.success is True


class TestPerformanceSnapshot:
    """Test PerformanceSnapshot dataclass"""
    
    def test_creation(self):
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            total_decisions=100,
            avg_latency_ms=75.0,
            min_latency_ms=20.0,
            max_latency_ms=150.0,
            p95_latency_ms=120.0,
            p99_latency_ms=140.0,
            slow_decisions_count=5,
            target_compliance_rate=95.0
        )
        
        assert snapshot.avg_latency_ms == 75.0
        assert snapshot.target_compliance_rate == 95.0


class TestPerformanceMonitor:
    """Test PerformanceMonitor class"""
    
    def test_initialization(self):
        monitor = PerformanceMonitor()
        assert len(monitor._decision_history) == 0
        assert monitor.TARGET_LATENCY_MS == 100
        assert monitor._total_decision_count == 0
    
    def test_record_decision_start(self):
        monitor = PerformanceMonitor()
        start_time = monitor.record_decision_start()
        assert isinstance(start_time, float)
        assert start_time > 0
    
    def test_record_decision_end_fast(self):
        monitor = PerformanceMonitor()
        start_time = monitor.record_decision_start()
        time.sleep(0.01)  # 10ms
        
        metrics = monitor.record_decision_end(
            start_time=start_time,
            action_type="attack",
            game_phase="mid",
            alive_count=50,
            success=True
        )
        
        assert isinstance(metrics, DecisionMetrics)
        assert metrics.latency_ms >= 10  # At least 10ms
        assert metrics.latency_ms < 100  # Should be under target
        assert metrics.action_type == "attack"
        assert monitor._total_decision_count == 1
    
    def test_record_decision_end_slow(self):
        monitor = PerformanceMonitor()
        start_time = monitor.record_decision_start()
        time.sleep(0.15)  # 150ms - slow
        
        metrics = monitor.record_decision_end(
            start_time=start_time,
            action_type="move",
            game_phase="late",
            alive_count=20,
            success=True
        )
        
        assert metrics.latency_ms >= 150
        assert monitor._slow_decision_count == 1
    
    def test_get_current_statistics_empty(self):
        monitor = PerformanceMonitor()
        stats = monitor.get_current_statistics()
        
        assert stats["status"] == "no_data"
    
    def test_get_current_statistics_with_data(self):
        monitor = PerformanceMonitor()
        
        # Record multiple decisions
        for i in range(10):
            start = monitor.record_decision_start()
            time.sleep(0.01)  # 10ms each
            monitor.record_decision_end(start, "attack", "mid", 50, True)
        
        stats = monitor.get_current_statistics()
        
        assert stats["status"] == "ok"
        assert stats["total_decisions"] == 10
        assert stats["avg_latency_ms"] >= 10
        assert stats["target_met"] is True  # All under 100ms
        assert stats["performance_grade"] in ["S", "A", "B"]
    
    def test_calculate_grade_s(self):
        monitor = PerformanceMonitor()
        grade = monitor._calculate_grade(avg_latency=45, compliance_rate=99.5)
        assert grade == "S"
    
    def test_calculate_grade_a(self):
        monitor = PerformanceMonitor()
        grade = monitor._calculate_grade(avg_latency=75, compliance_rate=96)
        assert grade == "A"
    
    def test_calculate_grade_b(self):
        monitor = PerformanceMonitor()
        grade = monitor._calculate_grade(avg_latency=95, compliance_rate=92)
        assert grade == "B"
    
    def test_calculate_grade_f(self):
        monitor = PerformanceMonitor()
        grade = monitor._calculate_grade(avg_latency=300, compliance_rate=50)
        assert grade == "F"
    
    def test_get_phase_statistics(self):
        monitor = PerformanceMonitor()
        
        # Add data untuk different phases
        for phase in ["early", "mid", "late"]:
            for _ in range(5):
                start = monitor.record_decision_start()
                time.sleep(0.01)
                monitor.record_decision_end(start, "attack", phase, 50, True)
        
        stats = monitor.get_phase_statistics()
        
        assert "early" in stats
        assert "mid" in stats
        assert "late" in stats
        assert stats["early"]["count"] == 5
    
    def test_get_action_statistics(self):
        monitor = PerformanceMonitor()
        
        # Add data untuk different actions
        for action in ["attack", "move", "rest"]:
            for _ in range(3):
                start = monitor.record_decision_start()
                time.sleep(0.01)
                monitor.record_decision_end(start, action, "mid", 50, True)
        
        stats = monitor.get_action_statistics()
        
        assert "attack" in stats
        assert "move" in stats
        assert "rest" in stats
    
    def test_reset_statistics(self):
        monitor = PerformanceMonitor()
        
        # Add some data
        start = monitor.record_decision_start()
        time.sleep(0.01)
        monitor.record_decision_end(start, "attack", "mid", 50, True)
        
        assert monitor._total_decision_count == 1
        
        # Reset
        monitor.reset_statistics()
        
        assert monitor._total_decision_count == 0
        assert len(monitor._decision_history) == 0
    
    def test_get_summary(self):
        monitor = PerformanceMonitor()
        
        # Add some data
        start = monitor.record_decision_start()
        time.sleep(0.01)
        monitor.record_decision_end(start, "attack", "mid", 50, True)
        
        summary = monitor.get_summary()
        
        assert summary["total_decisions"] == 1
        assert summary["target_latency_ms"] == 100
        assert "current_stats" in summary


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_start_decision_timing(self):
        start_time = start_decision_timing()
        assert isinstance(start_time, float)
        assert start_time > 0
    
    def test_end_decision_timing(self):
        start_time = start_decision_timing()
        time.sleep(0.01)
        
        metrics = end_decision_timing(
            start_time=start_time,
            action_type="attack",
            game_phase="mid",
            alive_count=50,
            success=True
        )
        
        assert isinstance(metrics, DecisionMetrics)
        assert metrics.action_type == "attack"
    
    def test_record_action(self):
        record_action("attack", success=True)
        # Should not raise error
    
    def test_get_performance_report(self):
        report = get_performance_report()
        assert isinstance(report, dict)
    
    def test_check_performance_no_report_yet(self):
        # Should return None if report interval not met
        result = check_performance()
        # Will be None initially since not enough time passed
        assert result is None or isinstance(result, PerformanceSnapshot)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
