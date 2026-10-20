#!/bin/bash
set -euo pipefail
M=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git
R=${OT_SCRATCH:-/srv/opentallas-scratch}/claude/codex-kv-gen9-t3-tests-390ad0bbf
W=$R/source
mkdir -p "$R"
git -C "$M" fetch -q https://github.com/bojieli/OpenTallas codex/kv-gen9-takeover3-1019
if [ ! -d "$W" ]; then
 git -C "$M" worktree add --no-checkout --detach "$W" 390ad0bbf
 git -C "$W" sparse-checkout set tools rtl/qwen_sys results/arch/qwen_kv_domsplit_1019 results/arch/qwen_kv_kits_b_1018
 git -C "$W" checkout --quiet
fi
cd "$W"
python3 tools/qwen_kv_die/kv_grp_safe2.py --check | tee "$R/generated_source_check.log"
python3 -m pip -q install --target "$R/testdeps" pytest
PYTHONPATH="$R/testdeps${PYTHONPATH:+:$PYTHONPATH}" python3 -m pytest -q tools/qwen_kv_die/test_kv_grp_safe2_plan.py tools/qwen_kv_die/test_kv_domsplit.py tools/qwen_kv_die/test_kv_relays.py > "$R/tests_isolated_deps.log" 2>&1
cat "$R/tests_isolated_deps.log"
