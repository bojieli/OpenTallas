#!/bin/bash
# Full core A2P: only SE/NE SM-side hardware and four physical SerDes peers are removed.
# d4c reset geometry is deliberately not reused; rebuild against the d4f placement.
# Relay layer (H-NETLIST/D4F-RELAY 10-17): F1 forwarded-clock stations from the H-DIE routed station list at reach 405 and
# the DIE-CLOCK region map, built against the LAYER=none contract:
#   relay_layer_d4f.py --stations S --contract <LAYER=none contract> --manifest <case manifest> --root-sites R --region-map M
#     --out tools/hbm_die_v15/v16_relays/relays_d4f.json.gz --report <OUT>/relays_d4f_report.json ; LAYER=none for the base.
set -euo pipefail
cd "$(dirname "$0")/../.."
LAYER=${LAYER:-tools/hbm_die_v15/v16_relays/relays_d4f_r8b.json.gz} IDSTRAPS=1 PCH8=1 PCH9B=1 SOFT_IDX=${SOFT_IDX-results/arch/hbm_idx_soft_parent_1016/netmap_nq2_tp192.json} DROPSM=SE,NE \
DROPI=ep_S2,lk_S2,ep_S4,lk_S4,ep_N1,lk_N1,ep_N3,lk_N3 \
EXTRA_LAYERS="tools/hbm_die_v15/v16_layers/xql_d4f_bfqg.json tools/hbm_die_v15/v16_layers/sfu_split3_d4f.json tools/hbm_die_v15/v16_layers/vm_q2merge_d4f.json tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json tools/hbm_die_v15/v16_layers/coll_hardv7_d4f.json tools/hbm_die_v15/v16_layers/su_rflocal_d4f.json tools/hbm_die_v15/v16_layers/vm_kshare_krl1_d4f.json tools/hbm_die_v15/v16_layers/wrq_lanes_d4f.json tools/hbm_die_v15/v16_layers/slots_r6_d4f.json tools/hbm_die_v15/v16_layers/xq_pegress_x6_clocks_d4f.json tools/hbm_die_v15/v16_layers/sfu_r14_d4f.json tools/hbm_die_v15/v16_layers/su_prog_part_d4f.json tools/hbm_die_v15/v16_layers/r8b_d4f.json" \
bash tools/hbm_die_v15/run_v16_d4b.sh "${1:-results/arch/hbm_die_v16_d4f}"
# H-DIE-R8b 10-17: + r8b_d4f layer (LG tap fold, cij rg, sfup r10), relay layer relays_d4f_r8b (run8 stations), die.v from the contract.
# H-DIE-R8 10-17: + sfu_r14 (SFU LG chains R14, LG_PATH 15), su_prog_part (su_pgr root + pgp_<q> r4 slices), HBM-FAULT + cp_rx post-layers.
# H-DIE-R7b 10-17 (coordinator 0da+): HBM-TIE layer (bc32a2e45) on the generated contract + die.v: top-k K from col_idx.prm,
# 2 ot_hbm_pc_refresh_cfg (refcfg_SW/NW, PC reset held until loaded), xl_<q>_ctl -> ctlx. TIE=0 skips it.
OUTD="${1:-results/arch/hbm_die_v16_d4f}"
if [ "${TIE:-1}" = 1 ]; then
  T=$(mktemp -d)
  # H-DIE-R8b: LGFOLD=1 (r8b layer folds the LG taps): the fault tree reads the folds' faults.  die.v is written FROM the
  # final contract (tools/hbm_die_v16/contract_die_v.py; equal to the textual die-mode chain on run8, check mode).
  zcat "$OUTD/contract.json.gz" > $T/c.json && python3 tools/hbm_die_v15/hbm_tie_1017.py contract $T/c.json $T/ct.json \
    && LGFOLD=${LGFOLD:-1} python3 tools/hbm_die_v16/hbm_fault_1017.py contract $T/ct.json $T/cf.json && python3 tools/hbm_die_v15/hbm_host_r8_1017.py contract $T/cf.json $T/ct.json \
    && python3 tools/hbm_die_v16/contract_die_v.py emit $T/ct.json $T/dt.v && gzip -c $T/ct.json > "$OUTD/contract.json.gz" && gzip -c $T/dt.v > "$OUTD/die.v.gz" \
    || { echo "POST_LAYERS FAIL"; exit 5; }
  python3 -c "import json; c=json.load(open('$T/ct.json')); json.dump(dict(straps=sorted({(s['master'], s['port']) for s in c['straps']})), open('$OUTD/straps_tie.json','w'), indent=1)"
  rm -rf $T; echo "HBM_TIE_LAYER APPLIED (+ H-DIE-R8: HBM-FAULT tree / status_join_fa, host cp_rx fold)"
fi
# H-NETLIST 2330 (fail-closed source inventory): every module the contract instantiates must resolve to a committed file.
# In a git checkout this runs here; a non-git fleet copy must be checked from the checkout before the contract commit.
OUTD="${1:-results/arch/hbm_die_v16_d4f}"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  python3 tools/hbm_die_v15/check_contract_modules.py --contract "$OUTD/contract.json.gz" --rev HEAD --json "$OUTD/contract_modules_check.json" || { echo "CONTRACT_MODULES_CHECK FAIL"; exit 3; }
else
  echo "CONTRACT_MODULES_CHECK DEFERRED (no git here): run tools/hbm_die_v15/check_contract_modules.py in the checkout before committing"
fi
