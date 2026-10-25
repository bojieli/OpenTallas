#!/usr/bin/env bash
# TOK-SCHED 2026-10-25 (sub-agent of lane TOK-SCHED): r25gq (HBM die, ds_ar + qwen_ar) ledger rows for the three
# COORD-approved cycle changes (COORD 12:07 10-25 RE PATH-HBM). Replayable on any merged ledger:
#   bash results/token_pass/toksched_1025/hbm_ledger_cmds.sh
# Pricing record (each change alone, bracketed, combined in one schedule): results/token_pass/toksched_1025/hbm_price.json
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/../../.." && pwd); cd "$ROOT"
AC="python3 tools/throughput/accepted_cost.py"
UA='COLL.ARGMAX_MERGE q3 ARG publication +1 edge (ot_hgi_coll_argmax_m_tp192_pr, PATH-HBM/Q3)'
UB='SM BF16 path xs3n -> tcl/tct 2nd relay stage +1 edge (PATH-HBM/SM cluster)'
UC='COLL.TOPK_MERGE tkx transport q_hub_nw W end of NW_hub <-> TKM root (26 + 26 stations)'

# (a) +1 a COLL.ARGMAX_MERGE record: publication flush+6 -> flush+7; argmax_rows.py --arg-pr-source moves capture_arg,
#     the SU sink and del_obase +1 (II32 unchanged). Price 6 / measured 7 = the publication edges.
$AC propose r25gq --unit "$UA" --group COLL.ARG_PR_PUBLISH --op COLL.ARGMAX_MERGE --op-delta 1 --price 6 --measured 7 \
  --evidence results/token_pass/path_hbm_1309/arg_pr/compiler_receipt.json \
  --note "q3 hub edge binds ot_hgi_coll_argmax_m_tp192_pr (rtl/.../p2p/ot_hgi_coll_edge_pr.sv; ot_hfd_coll_q3_hard_v8x_s, main a63baaa9a): ARG publication +1 edge. Compiler: tools/hbm_coll_static/argmax_rows.py --arg-pr-source (Codex 2999de1eaa): capture_arg / SU sink / del_obase +1, II32, halt +1, rows +2 (VM_RT81 P8 226->228 of 256). Calendar check results/token_pass/toksched_1025/hbm_arg_pr_slot_check_P8_vmrt81.json PASS. +1 cycle a record, S2 schedule fully exposed (1 record a token both workloads)."
$AC accept r25gq "$UA" --note "COORD 2026-10-25 12:07 (q3 +1 edge argmax publish -> TOK-HBM); priced TOK-SCHED 2026-10-25"

# (b) +1 a record on the SM BF16 tc columns: SM.MATVEC with B BF16 (wo_a, router gate, compressor, LM head) or INT8
#     (fmt3 runs on the BF16 lanes: ot_hbm_accel_smh.sv op_bf = fmt 0 | fmt 3), and ATT.QK / ATT.PV (attention native
#     column = tcl halves + tct). FP8 / FP4 block-dot (bdc) records do not use the path.
$AC propose r25gq --unit "$UB" --group SM.BF16_XS3N_TC --op 'SM.MATVEC|ATT.QK|ATT.PV' --op-fmt 'SM.MATVEC:B=BF16/INT8' \
  --op-delta 1 --price 1 --measured 2 --evidence results/token_pass/toksched_1025/hbm_price.json \
  --note "COORD 12:07 (3): BF16 operands xs3n W/E -> tcl/tct 437-561 um per hop get a 2nd relay stage (no room beside xs3n, lanes/PATH-HBM.md 10:52): +1 edge a record on every op that runs on the tc columns. Structural register count, priced in the S2 schedule; lower bound BF16 weights only ds_ar 0.0147 %, upper bound every SM/ATT record ds_ar 0.0764 % (hbm_price.json sensitivity). Compiler offset +1 on the tc operand path still to land with the SM cluster plan rev."
$AC accept r25gq "$UB" --note "COORD 2026-10-25 12:07 (3) APPROVED; priced TOK-SCHED 2026-10-25"

# (c) +52 a COLL.TOPK_MERGE record: the TKM root is reached through the q_hub_nw W-end placement, 26 stations out (L74_o)
#     + 26 back (L13_i into u_hb_coll_Q_*), one critical round trip a merge (streamed words keep II8; tkx_cost_ledger_ft21).
#     Unpriced transport (price 0): the priced schedule had the TKM local to the COLL quadrant.
$AC propose r25gq --unit "$UC" --group COLL.TKX_Q_HUB_NW --op COLL.TOPK_MERGE --op-delta 52 --price 0 --measured 52 \
  --evidence results/token_pass/toksched_1025/hbm_tkx_measure.json \
  --note "COORD 12:07 (1): q_hub_nw at the W end of NW_hub ACCEPTED on condition the tkx cost is measured; revisit with an E-side relay if e2e loss > 2 %. Measured round trip 52 edges from the plan (epyc1 path-hbm/plan_delta/q_hub_nw die_plan.json sha 3044f0bc3fc6). ds_ar 9 merges a token (8 x '96 x 512 index merge' + 1 candidate merge), all exposed: +468 cycles, 0.081 %; bracket +40/+50/+60 = 0.062/0.078/0.094 %; upper bound incl. all 40 IDX.TOPK at +60 = 0.507 %. qwen_ar has no TOPK_MERGE (0). Far below the 2 % revisit line. E-end alternative saves 39 edges a merge (0.061 %)."
$AC accept r25gq "$UC" --note "COORD 2026-10-25 12:07 (1) ACCEPTED with condition; measured e2e 0.081 % < 2 %: no E-side relay revisit"

$AC check
$AC table | grep -E '^\| (design|r25gq)' | head -60
