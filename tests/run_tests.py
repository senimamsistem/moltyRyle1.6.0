"""
Test runner untuk Molty Royale AI Agent
Usage: python tests/run_tests.py [options]
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(args):
    """Execute test suite dengan pytest"""
    
    # Base pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
    ]
    
    # Add options
    if args.coverage:
        cmd.extend([
            "--cov=bot",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_html",
            "--cov-report=xml:coverage.xml",
        ])
        
    if args.unit_only:
        cmd.append("tests/unit/")
        
    if args.integration_only:
        cmd.append("tests/integration/")
        
    if args.failfast:
        cmd.append("-x")
        
    if args.filter:
        cmd.extend(["-k", args.filter])
        
    if args.markers:
        for marker in args.markers:
            cmd.extend(["-m", marker])
    
    print("=" * 60)
    print("🧪 MOLTY ROYALE AI AGENT - TEST RUNNER")
    print("=" * 60)
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    
    print("=" * 60)
    if result.returncode == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ TESTS FAILED (exit code: {result.returncode})")
    print("=" * 60)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run Molty Royale AI Agent tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_tests.py                    # Run all tests
  python tests/run_tests.py --coverage         # Run with coverage report
  python tests/run_tests.py --unit-only        # Unit tests only
  python tests/run_tests.py -k "test_damage"   # Filter by test name
  python tests/run_tests.py -x               # Stop on first failure
        """
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--unit-only", "-u",
        action="store_true",
        help="Run only unit tests"
    )
    
    parser.add_argument(
        "--integration-only", "-i",
        action="store_true",
        help="Run only integration tests"
    )
    
    parser.add_argument(
        "--failfast", "-x",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--filter", "-k",
        type=str,
        help="Filter tests by name (pytest -k)"
    )
    
    parser.add_argument(
        "--markers", "-m",
        nargs="+",
        help="Run tests with specific markers"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tests"
    )
    
    args = parser.parse_args()
    
    if args.list:
        # List all tests
        cmd = [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"]
        subprocess.run(cmd)
        return 0
    
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
