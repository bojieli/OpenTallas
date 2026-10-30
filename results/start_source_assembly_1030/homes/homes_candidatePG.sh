#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-start-source-assembly-1030
cd "$r"
PYTHONPATH=/srv/opentallas-scratch2/claude/codex-flow-s81phy-1030/exactA/tool_snapshot/tools/die_plan python3 -B src/tools/die_plan/start_source_homes.py --assembly source/source_assembly.json --inventory attempt_833/source_inventory_with_caps.json --library library_all.json --old-meta old_meta.json --new-contract new_contract.json --plan candidate_pg_exclusion_plan_MODEL_ONLY.json --out source_homes_candidatePG.json >homes_candidatePG.log 2>homes_candidatePG.err
