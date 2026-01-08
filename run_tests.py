#!/usr/bin/env python3
"""
Test Runner for Multi-Agent System
==================================

This script runs the unit tests for the multi-agent voice assistant.
"""

import sys
import subprocess
import os
from pathlib import Path

def install_test_dependencies():
    """Install test dependencies if not already installed."""
    try:
        import pytest
        import pytest_cov
        print("✓ Test dependencies already installed")
    except ImportError:
        print("Installing test dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "test-requirements.txt"
        ])
        print("✓ Test dependencies installed")

def run_tests(test_path=None, coverage=True, verbose=True):
    """Run the test suite."""
    cmd = [sys.executable, "-m", "pytest"]

    if test_path:
        cmd.append(test_path)

    if coverage:
        cmd.extend(["--cov=src/agents", "--cov-report=term-missing"])

    if verbose:
        cmd.append("-v")

    # Add pytest.ini configuration
    cmd.extend(["--tb=short", "--strict-markers"])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    return result.returncode == 0

def run_specific_test(test_file):
    """Run a specific test file."""
    test_path = f"tests/{test_file}"
    if not Path(test_path).exists():
        print(f"❌ Test file {test_path} not found")
        return False

    print(f"Running specific test: {test_file}")
    return run_tests(test_path)

def main():
    """Main test runner function."""
    print("🚀 Multi-Agent System Test Runner")
    print("=" * 40)

    # Check if we're in the right directory
    if not Path("src/agents").exists():
        print("❌ Please run this script from the farmer-poc-rag-lambda directory")
        sys.exit(1)

    # Install dependencies
    install_test_dependencies()

    # Parse command line arguments
    if len(sys.argv) > 1:
        test_target = sys.argv[1]
        if test_target.endswith(".py"):
            # Run specific test file
            success = run_specific_test(test_target)
        else:
            # Run tests for specific agent
            test_file = f"test_{test_target}_agent.py"
            success = run_specific_test(test_file)
    else:
        # Run all tests
        print("Running all agent tests...")
        success = run_tests()

    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()