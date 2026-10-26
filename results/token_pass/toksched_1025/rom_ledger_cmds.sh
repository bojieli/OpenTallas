#!/bin/bash
# TOK-SCHED 10-25 (sub-agent of lane TOK-SCHED): exact commands run for the ROM cycle-change rows.  Run from the repo
# root of a checkout of this branch (or main after merge).  Light python except step (b), which builds a ~214 MB engine
# snapshot: run (b) on a fleet host scratch dir (epyc1 /srv/opentallas-scratch2/...), never on a root disk.
set -euo pipefail
REPO=${REPO:-$(git rev-parse --show-toplevel)}
H=results/token_pass/toksched_1025
SCR=${SCR:-/srv/opentallas-scratch2/claude/toksched-rom-1025}

# (a) S81 vsw LR=1 -- Codex 841db2c43 is already on main (c967be25c); cherry-pick was empty.  Re-run its checks:
python3 tools/s81_dv/tokfunc/compose_tok_ds.py --out "$SCR/vsw_new"            # AR map 1528917.6 / MTP 1815279.6, calendars PASS
cp "$SCR/vsw_new/compose_1u.json" "$SCR/vsw_new/calendar_mu.json" $H/vsw_recheck/
python3 $H/vsw_l14_check.py "$REPO"                                               # L14 span 28081.9 (LR 0) -> 28082.9 (LR 1)
python3 tools/throughput/accepted_cost.py compute s81 --unit S81.VSW_LR1 \
  --match 'ffn\.(shared_)?swiglu(\.r\d+)?$' --price 0 --measured 1 --node-delta 1  # ledger DAG cross-check AR +40 / MTP +48

# (b) QC MIF=1 -- toksim_compose bound_current with SU-derived ages +1/+2/+3 (Codex qwen_s8_crom_price_1025 recipe)
mkdir -p "$SCR"
python3 $H/qc_mif_price.py "$REPO" "$SCR/mif"                                     # 286726 / +433 / +866 / +1299 (= Codex CROM 288025)
cp "$SCR"/mif/{bound_current,bound_su_plus1,bound_su_plus2,bound_su_plus3,mif_summary_raw}.json $H/qc_mif/

# (c) KV v3.9r lane-cycle table + L663
git show origin/claude/path-kv-rebase-1025:results/arch/kv_plan_0719/rebase1025/lane_cycle_delta_vs_main.json \
  > $H/kv_v39r/lane_cycle_delta_vs_main.json                                     # branch @3832299dfb
python3 $H/kv_v39r_price.py $H/kv_v39r/lane_cycle_delta_vs_main.json $H/kv_v39r/kv_v39r_price.json

# ledger rows (propose + accept, COORD-approved), then the table / check
python3 $H/rom_ledger_rows.py                                                     # --ledger PATH for a merged ledger
python3 tools/throughput/accepted_cost.py table | grep -E 'VSW_LR1|SRAM_MIF1|V39R_LANES|^s81:|^qwen_rom:'
python3 tools/throughput/accepted_cost.py check   # only the pre-existing r25gq COLL quadrant row violation (also on main)

# 2026-10-25 TOK-SCHED merge: KV.PLAN_V39R_LANES, QC.SRAM_MIF1, COLL.TOPK_MERGE tkx and SM BF16 rows were DEMOTED to proposed/interim_log
# (model/plan-count evidence, no measured run). Do not replay their accept steps; only S81.VSW_LR1 and COLL.ARGMAX_MERGE stay accepted.
