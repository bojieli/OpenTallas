# RSEL (g1 rr_fifo registered one-hot read select) proof results, HBM-CORES-C 11-12

1. yosys equiv (eq_rsel.ys, W=288 AW=2, gold RSEL=0 vs gate RSEL=1): equiv_simple/equiv_induct -seq 4, 1795 cells proven, 0 unproven.
   Negative control (rsel_oh loaded from rbin, one edge late): 1507 proven, 288 unproven (all rdata bits), assert fails.
   NOTE: a first run at the default W=32 was vacuous (NS=W/72=0 -> no write path, mutant also "proven"); do not use W=32.
2. Lock-step bench tb_rsel_lockstep.sv (RSEL 0 vs 1, two clocks, 40000 rclk, 19405 reads): 0 errors; late-load mutant 19405 errors.
   Simulation-only invariant in the RTL (`RSEL_INV_FAIL`): rsel_oh == onehot(rbin) at every rclk edge. Random mid-run async reset pulses
   in both domains (tb with resets): 0 errors, no invariant message.
3. WBQ-QUAL bench, run_qual_rsel.py (job ids rr / rr_rsel, g1 RR + RPIPE, GREG=0): 42 jobs, 0 not OK. rr_rsel: fault, clean, K-slow and
   quadrant modes on 8 clock ratios, and the credit sweep on 3 ratios, all PASS. Credit sweep copy-duration new-old delta
   rr 0.27-0.34 %, rr_rsel 0.15-0.43 % (same order, different random seeds), writes new-old = 0.
   RSEL_INV_FAIL appears in 18 rr_rsel logs, always 84 lines at ONE timestamp (t=638000 ps, 6 slices x 14 FIFOs): the first rclk edge
   after the power-up reset release, where Verilator's random initial values (+verilator+rand+reset+2) have not been reset by any clock edge
   or negedge yet (rbin of the original FIFO is equally random then). No violation at any later time. This is a bench start-up artifact,
   not a design violation; it is stated here, not hidden.
