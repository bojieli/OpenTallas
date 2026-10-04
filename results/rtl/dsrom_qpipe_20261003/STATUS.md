# dsrom-qpipe STATUS (DS-V4.1 ROM q-pair element, SS 1.2 GHz pipelining) - HANDED OVER TO CODEX 2026-10-03

Branch claude/dsrom-qelem-pipeline-20261003 (pushed). Frozen RTL SHA 281bde911. Pinned worktree on ot-epyc1tb:
/srv/opentallas-scratch/claude/dsrom-qpipe/wt-281bde911.

## Stages added (QPIPE=1, default 0; rtl/v41rom/ot_v41_rom_elem_qp_w10.sv, wrapper ot_v41_rom_elem_q_qp_w10.sv)
- +1 boundary: go/go_bf/cfg registered on free clk, rst_n local synchroniser (async assert, sync deassert), x beats
  registered on gclk (QP_XS=1). go/rst_n no longer reach the ICG. With QP_XS=0 the spine issues go/cfg/rst one cycle
  early and the cycle is hidden (exact-gated as xs0, L=1).
- +1 lane P1 split (ot_v41_bterm3_w10 P1S=1: decode | 4x4 product); QP_CSAM=10 rebalances CSA levels (0 cycles).
- optional +1 QP_CAP: registered capture select before lanes (R_cap1 only).
- 0-cycle: segtree3 slot-local decisions, per-macro issue-control copies, x-match pair offset precompute, FP8 half
  select retimed, walker last-unit lookahead register, QK-delayed output tables, registered busy/fault, ICG held QK longer.
- Not touched: chain adder loop (fwd5/fwd6 -> fadd stage 0, -93..-120 ps at post-CTS before) - pricing says a cycle
  inside the chunk-8 recurrence costs -0.65% AR / -1.66% MTP; fill cycles cost -0.044% AR / -0.023% MTP each.
Total added latency: L=2 (R_cap0) or L=3 (R_cap1) per q-op; L=1 if the spine issues control early (QP_XS=0).

## Exactness
PASS at 281bde911 (results/rtl/dsrom_qpipe_20261003/exact.json, commit d69e8d520): 27.5M compared cycles vs the pinned
ot_v41_rom_elem_q_w10, outputs cycle-shifted by exactly L, builds L=2/3/1/0, mutants dp/tree/half/shadow/lu caught.
Gate: tools/dsrom_qpipe_exact.py (needs committed sources).

## Running on ot-epyc1tb (detached, OT_ORFS_NUM_CORES=20) - leave alone
- run_chain.sh R_cap0 0 / R_cap1 1 -> /home/ubuntu/otjobs/dsrom_qpipe_20261003/R_cap{0,1} (launch.log, receipt,
  macro_gate.json PASS; launch.rc + launch.done on exit). Frame C, SS WC 0.833 ns, 60/25 ps, ADDER_MAP off, full route.
- post_sta.sh (chained): sta/<run>/cts_SS.{log,ends,paths} after CTS; final_SS / final_FF with SPEF after route
  (OT_WNS / OT_TNS lines). post.done when finished.
- R_cap*_aborted_threads128: first attempt, stopped at floorplan (thread cap), no results.

## Next steps (Codex)
1. Read cts_SS: if residual violators, categorise (.ends) - expected candidates: chain fwd5/fwd6 -> fadd u_c0
   (fanout of forward selects; try duplication before adding a cycle), walker nA/nB/wA enables.
2. After route: signoff = SS setup WNS >= 0 and FF hold WNS >= 0, DRC clean. Write verdict JSON under
   results/rtl/dsrom_qpipe_20261003/ (never overwrite failures); pick minimum L that closes.
3. Report added cycles to the model (pricing record results/uarch/dsrom_qelem_pipeline_pricing_20261003.json).
