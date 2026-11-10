#!/usr/bin/env bash
# Live Gemini smoke tests only (uses real API quota). Results are saved to docs/live_test_results.txt.
set -o pipefail
cd "$(dirname "$0")/.."
python -m pytest -m live -v -rs 2>&1 | tee docs/live_test_results.txt
