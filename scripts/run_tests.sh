#!/bin/bash
# Run all tests and summarize results
# Usage: ./scripts/run_tests.sh [options]
#   -v    Verbose output
#   -c    Include coverage report
#   -q    Quiet mode (summary only)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
VERBOSE=""
COVERAGE=""
QUIET=""

while getopts "vcq" opt; do
    case $opt in
        v) VERBOSE="-v" ;;
        c) COVERAGE="--cov=src --cov=config --cov-report=term-missing" ;;
        q) QUIET="true" ;;
    esac
done

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Vector AI Job Matching - Test Suite                 ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

# Check pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest pytest-cov --quiet
fi

echo -e "${BLUE}Running tests...${NC}"
echo ""

# Create temp file for results
RESULTS_FILE=$(mktemp)

# Run tests and capture output
START_TIME=$(date +%s)

if [ "$QUIET" = "true" ]; then
    python -m pytest tests/ $VERBOSE $COVERAGE --tb=short -q 2>&1 | tee "$RESULTS_FILE"
else
    python -m pytest tests/ $VERBOSE $COVERAGE --tb=short 2>&1 | tee "$RESULTS_FILE"
fi

EXIT_CODE=${PIPESTATUS[0]}
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                        TEST SUMMARY                          ${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo ""

# Extract results from output
PASSED=$(grep -oE '[0-9]+ passed' "$RESULTS_FILE" | head -1 | grep -oE '[0-9]+' || echo "0")
FAILED=$(grep -oE '[0-9]+ failed' "$RESULTS_FILE" | head -1 | grep -oE '[0-9]+' || echo "0")
WARNINGS=$(grep -oE '[0-9]+ warning' "$RESULTS_FILE" | head -1 | grep -oE '[0-9]+' || echo "0")
ERRORS=$(grep -oE '[0-9]+ error' "$RESULTS_FILE" | head -1 | grep -oE '[0-9]+' || echo "0")

TOTAL=$((PASSED + FAILED))

# Display summary
echo -e "  ${GREEN}✓ Passed:${NC}    $PASSED"
if [ "$FAILED" -gt 0 ]; then
    echo -e "  ${RED}✗ Failed:${NC}    $FAILED"
else
    echo -e "  ${GREEN}✗ Failed:${NC}    $FAILED"
fi
if [ "$WARNINGS" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠ Warnings:${NC}  $WARNINGS"
fi
if [ "$ERRORS" -gt 0 ]; then
    echo -e "  ${RED}⚠ Errors:${NC}    $ERRORS"
fi
echo ""
echo -e "  ${BLUE}Total:${NC}       $TOTAL tests"
echo -e "  ${BLUE}Duration:${NC}    ${DURATION}s"
echo ""

# Test breakdown by file
echo -e "${BLUE}Test Breakdown:${NC}"
echo "  ├── test_models.py    - Data models (Job, Candidate)"
echo "  ├── test_services.py  - Service layer (Job, Candidate, Matching)"
echo "  ├── test_api.py       - REST API endpoints"
echo "  └── test_agent.py     - ADK agent configuration"
echo ""

# Final status
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    ✓ ALL TESTS PASSED                        ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    ✗ SOME TESTS FAILED                       ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Run with -v flag for verbose output to see failure details${NC}"
fi

# Cleanup
rm -f "$RESULTS_FILE"

echo ""
exit $EXIT_CODE

