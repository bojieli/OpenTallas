# TOK-HBM-11 (2026-10-29, sub-lane of DIE-HBM-22): TOK prices for EP_S1 hop lane, hub-coll q0 drop, HBM-039 fix options

Model: the SAME ds S2 schedule model as DIE-HBM-10 `tok_rerun_c22.py` / DIE-HBM-20 `tok_pgp_cmd.py` (accepted_cost g25
rank0, NativeCost, T.schedule; no fork). Added cycles are charged serially per record (BOUND form, no overlap).
Base 576,702.4 cycles = 1906 tok/s. NUMBER-CHECK: the DIE-HBM-20 row SU +10 is reproduced at 1.702 % (CHECKED).
Model trap found: in a sparse checkout without `results/rtl/dshbm_1m_allmeasured_20261004/{collectives,local}.json`,
`ds_hgi` runs silently with another COLL/local price (base 557,152, SU+10 1.805 %). Check base 576,702.4 before trusting a run.

## (A) plan d21h EP_S1 hop lane (+17 cyc TX, +17 cyc RX)
- What ep_S1 carries (CHECKED from die_r18h5.v): `hfd_ep_static ep_S1` is lane 1 of the hub collective's 2-lane SerDes
  (`hb_coll_SW.tx_pin_flit[1223:612]` -> ep_S1.tx_frame; ep_S1.rx_pin_flit -> `hb_coll_SW.rx_pin_flit` lane 1; epcal
  payload -> rx_arm/release/slot). So it is the off-die collective path, on EVERY per-layer collective (642 COLL
  records/token: 584 ALL_GATHER, 40 GROUP_REDUCE_MCAST, 9 TOPK_MERGE, 8 ROW_GATHER, 1 ARGMAX_MERGE), not a side path.
- Price: a crossing pays TX +17 on the sender and RX +17 on the receiver (+34); crossings per op as perf.coll_cycles
  (2 for reduce-multicast, else 1); the striped transfer waits for the slower lane.

| case | cost | tok/s |
|---|---|---|
| A estimate of record (34 x crossings) | 3.195 % | 1847.0 |
| A low (one direction only) | 1.531 % | 1877.3 |
| A bound (34 x 2 on every COLL) | 6.205 % | 1794.6 |
The bind-8 README's ~0.3 % (UNCHECKED, 60 layers x 1 round trip) undercounts: there are ~16 collectives per layer.

## (B) HBM-BIND-7 hub collective q0 drop (NE <= +12, NW <= +15 per stage)
| case | cost | tok/s |
|---|---|---|
| B estimate of record, op-aware (merge/reduce ops: NW reduce 15 + body 11 + ring 6 = 32; gathers: body + ring = 17; x crossings) | 1.765 % | 1872.9 |
| B every COLL 32 x crossings | 2.992 % | 1850.6 |
| B NE stage maxima (27 x crossings) | 2.484 % | 1859.8 |
| B bound (3 x 15 x 2 on every COLL) | 8.314 % | 1759.7 |
| A + B estimates combined (34 + op-aware B) | 5.163 % | 1812.4 |
Each change alone is < 5 % on its estimate of record. Together they are 5.16 % (> 5 %), and both land on the same
collective path -> OWNER? item for the die owner (proposed default: keep both, recover the EP_S1 lane by an
ep_S1 slot next to the hub/root edge in the next re-plan event, so A drops to ~0).

## (C) HBM-039 hfd_hgi_vms_glue_nw_t (GEOM-65 FAIL STRUCTURAL): fix estimate (no RTL written, no kit)
RTL read: `ot_vms_slice_static_glue` (NC 0, sid 2) = u_hub `ot_vms_hub_static` + u_cw/u_ccw `ot_vms_rstop_static` +
u_replay + u_status.
- `u_status.sum_valid[0]` (2515 far captures) cannot be status logic: it only drives sum_valid[1]. Its D = 1'b1 with
  async reset 0, the same as `me[1] <= sid[1]` (sid = 2'b10) in u_hub/u_cw/u_ccw/u_replay and `dr <= dir` (u_ccw).
  Yosys opt_merge folds them into one flop (hypothesis, UNCHECKED: confirm on the kit netlist), so the ring stops'
  `own = in_q[2223] && in_q[2217+me]` -> `xq <= in_q[2207:0]` (2208-bit bank-face regs) hangs on it.
  Fix C1: use the tied sid/dir directly (me/dr are constant after reset; all their users are gated by in_q /
  enable_q, which are 0 in the first cycle after reset) -> constant-propagated, 0 flops, 0 cycles. Exact at the
  outputs (sequentially equivalent; not a combinational LEC match at me/dr -> needs a declared constant / sim proof).
- `u_cw/u_ccw.source_q` + enable_q (3293) select the 2224-bit flit mux into `l_out` (a face-wide pin bus);
  `u_hub.br[2125]` (bank-7 pr valid, 1293), `be[0..7]`/`bc` (~277 each), `replay.select_q` (289): per-cycle controls
  fanned to 2208-bit buses on other faces.
  Fix C2, per-region replication (exact, equivalent every cycle; needs (* keep *) / no-merge, else Yosys re-merges):
  ~4 copies per 1.6-mm face of: source_q 3 + enable_q 1 per stop x2, the in_q control/valid bits [2223:2208] per stop,
  br valid bits 8, be 8, bc 8, select_q 1 -> about 150-200 flops (UNCHECKED). 0 cycles ONLY if the D sources are
  local; they are not: tx_source/tx_enable/bank_enable/bank_client are single input pins and in_q/br come from one
  face, so a copy 1.6 mm away moves the long wire to pin->reg (GEOM pin_reg). It needs per-region duplicate pins
  driven by the die (the die relay already exists; more pins, 0 cycles) - a plan pin delta.
  Fix C3, one pipeline stage on the fan-out (local input reg -> per-region copies, data delayed to match):
  +1 cycle per ring-stop pass / hub turn. If the compiler issues the scheduled controls (tx_source, bank_enable)
  one cycle earlier, the data path does not grow; else price:

| case | cost | tok/s |
|---|---|---|
| C3 +1 on SU records (estimate) | 0.154 % | 1903.1 |
| C3 +1 on SU + SM records | 0.217 % | 1901.9 |
| C3 +1 on every non-CTL record (bound) | 0.357 % | 1899.2 |
| C3 +2 (request + response) on every non-CTL record | 0.714 % | 1892.5 |
- N-face status pins (b3/b5/b7_status, 1.58-1.76 mm to u_status.pair_sum at the S face): plan pin delta to the S face,
  0 cycles; vmstat is observation-only, so a declared +1 hop stage would cost 0 tok/s too.
- Recommendation: C1 (0 flops, 0 cycles) + C3 on the remaining controls (<= 0.36 %, far below 5 %) + S-face status
  pins; then AUTO-GEOM. RTL NOT written (budget): opt-in parameter, default byte-identical, plus Verilator
  output-equivalence on ot_vms_rstop_static/ot_vms_status_static is the next step.

Files: tok_hbm11.py / .json / .log (A, B, check), tok_hbm11_c.py / _c.json / _c.log (C). Run at repo root with
PYTHONPATH=src (~4 min and ~2 min, intel1). All cycle inputs are plan arithmetic from the bind-7/bind-8 READMEs;
model runs CHECKED, mapping of cycles to records = ESTIMATE.
