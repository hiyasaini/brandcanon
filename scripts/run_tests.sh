#!/usr/bin/env bash
# Runs the mocked test suite (no network, no API quota) and records the real output in docs/test_results.txt.
# Live Gemini smoke tests are separate: scripts/run_live_tests.sh
cd "$(dirname "$0")/.." || exit 1
{ echo "BrandCanon test run — $(date)"; python -m pytest -v --tb=short 2>&1; } | tee docs/test_results.txt
