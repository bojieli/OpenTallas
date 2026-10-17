#!/bin/bash
# Full core A2P: only SE/NE SM-side hardware and four physical SerDes peers are removed.
# d4c reset geometry is deliberately not reused; rebuild against the d4f placement.
set -euo pipefail
cd "$(dirname "$0")/../.."
LAYER=none IDSTRAPS=1 PCH8=1 PCH9B=1 SOFT_IDX=${SOFT_IDX-results/arch/hbm_idx_soft_parent_1016/netmap_nq2_tp192.json} DROPSM=SE,NE \
DROPI=ep_S2,lk_S2,ep_S4,lk_S4,ep_N1,lk_N1,ep_N3,lk_N3 \
EXTRA_LAYERS="tools/hbm_die_v15/v16_layers/xql_d4f_bfqg.json tools/hbm_die_v15/v16_layers/sfu_split2_d4f.json tools/hbm_die_v15/v16_layers/vm_q2merge_d4f.json tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json tools/hbm_die_v15/v16_layers/coll_hardv7_d4f.json tools/hbm_die_v15/v16_layers/su_rflocal_d4f.json tools/hbm_die_v15/v16_layers/vm_kshare_krl1_d4f.json" \
bash tools/hbm_die_v15/run_v16_d4b.sh "${1:-results/arch/hbm_die_v16_d4f}"
# H-NETLIST 2330 (fail-closed source inventory): every module the contract instantiates must resolve to a committed file.
# In a git checkout this runs here; a non-git fleet copy must be checked from the checkout before the contract commit.
OUTD="${1:-results/arch/hbm_die_v16_d4f}"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  python3 tools/hbm_die_v15/check_contract_modules.py --contract "$OUTD/contract.json.gz" --rev HEAD --json "$OUTD/contract_modules_check.json" || { echo "CONTRACT_MODULES_CHECK FAIL"; exit 3; }
else
  echo "CONTRACT_MODULES_CHECK DEFERRED (no git here): run tools/hbm_die_v15/check_contract_modules.py in the checkout before committing"
fi
