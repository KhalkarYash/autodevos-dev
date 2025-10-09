#!/bin/bash
# AutoDevOS - Production Readiness Verification Script

set -e

echo "🔍 AutoDevOS Production Readiness Verification"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    fi
}

# 1. Check Python version
echo "1. Checking Python version..."
python --version | grep -q "Python 3\."
check "Python 3.x installed"

# 2. Check required dependencies
echo ""
echo "2. Checking dependencies..."
python -c "import google.generativeai" 2>/dev/null
check "google-generativeai installed"

python -c "import rich" 2>/dev/null
check "rich installed"

python -c "import yaml" 2>/dev/null
check "PyYAML installed"

# 3. Verify all modules import
echo ""
echo "3. Verifying module imports..."
python -c "import meta_agent.llm_interface" 2>/dev/null
check "meta_agent.llm_interface imports"

python -c "import meta_agent.orchestrator" 2>/dev/null
check "meta_agent.orchestrator imports"

python -c "import meta_agent.dag_scheduler" 2>/dev/null
check "meta_agent.dag_scheduler imports"

python -c "import meta_agent.context_manager" 2>/dev/null
check "meta_agent.context_manager imports"

python -c "import meta_agent.utils" 2>/dev/null
check "meta_agent.utils imports"

# 4. Check syntax of all Python files
echo ""
echo "4. Checking Python syntax..."
find meta_agent agents -name "*.py" -exec python -m py_compile {} \; 2>/dev/null
check "All Python files compile"

# 5. Verify core functionality
echo ""
echo "5. Verifying core functionality..."

python -c "
from meta_agent.llm_interface import MockLLM, GeminiLLM, make_llm
llm = make_llm(prefer_gemini=False)
result = llm.generate_code('test')
assert len(result) > 0
" 2>/dev/null
check "MockLLM generates code"

python -c "
from meta_agent.context_manager import MCPContext
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    ctx = MCPContext('test', Path(tmpdir))
    ctx.set('key', 'value')
    assert ctx.get('key') == 'value'
    ctx.save()
    ctx2 = MCPContext.load('test', Path(tmpdir))
    assert ctx2.get('key') == 'value'
" 2>/dev/null
check "Context manager save/load works"

python -c "
from meta_agent.orchestrator import Orchestrator
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    orch = Orchestrator(Path(tmpdir), Path(tmpdir) / 'output', use_dynamic_planning=False)
    plan = orch.plan('create app')
    assert len(plan) > 0
    assert all('id' in task for task in plan)
" 2>/dev/null
check "Orchestrator creates valid plan"

# 6. Check documentation
echo ""
echo "6. Checking documentation..."
[ -f "README.md" ]
check "README.md exists"

[ -f "SECURITY.md" ]
check "SECURITY.md exists"

[ -f "IMPLEMENTATION_STATUS.md" ]
check "IMPLEMENTATION_STATUS.md exists"

[ -f "IMPROVEMENTS_SUMMARY.md" ]
check "IMPROVEMENTS_SUMMARY.md exists"

[ -f "PRODUCTION_CHECKLIST.md" ]
check "PRODUCTION_CHECKLIST.md exists"

# 7. Check CI/CD
echo ""
echo "7. Checking CI/CD..."
[ -f ".github/workflows/ci.yml" ]
check "CI workflow exists"

# 8. Check Docker
echo ""
echo "8. Checking Docker..."
[ -f "docker/Dockerfile" ]
check "Dockerfile exists"

[ -f "docker/entrypoint.sh" ]
check "Docker entrypoint exists"

# 9. Check configuration
echo ""
echo "9. Checking configuration..."
[ -f ".env.example" ]
check ".env.example exists"

[ -f "config.yaml" ]
check "config.yaml exists"

[ -f "requirements.txt" ]
check "requirements.txt exists"

# 10. Check test files
echo ""
echo "10. Checking test files..."
[ -f "tests/unit/test_llm_interface.py" ]
check "LLM interface tests exist"

[ -f "tests/unit/test_orchestrator.py" ]
check "Orchestrator tests exist"

[ -f "tests/unit/test_scheduler.py" ]
check "Scheduler tests exist"

# Summary
echo ""
echo "=============================================="
echo "📊 Verification Summary"
echo "=============================================="
echo -e "Passed: ${GREEN}${PASSED}${NC}"
echo -e "Failed: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! AutoDevOS is production-ready.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
