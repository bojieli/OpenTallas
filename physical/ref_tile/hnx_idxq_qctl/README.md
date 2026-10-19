# hnx_idxq_qctl: IDXQ quadrant calendar copy (`ot_hnx_idxq_qctl`, CW=2)

This tile is the IDXN N-row issuer copy for one quadrant: 8 pipelined row streams over one frame SRAM (256x256), with per-class routing. Any collision raises a fault.

## Behaviour evidence
- **Quad lockstep** at 859b27b6b (`results/arch/hbm_next_1019/units/idxq/lockstep_859b27b6b`):
  - N = 1/2/4/6 rows are bit-exact against the IDXN stack and the exact oracle.
  - All 7 mutants FAIL as intended (`SUMMARY unexpected=0`).
- **Calendar CW bench** (`tools/hbm_next/hnx_idxn_cw_bench.sh`), run as the closure-loop benches:
  - `pos`: CW1 / CW2 equal CW0 on every edge.
  - `m4`, `m5`, `m6`: each fails. The fail witnesses are in `results/.../idxq/cw/witness`.
  - Verified on the fleet at 7493a0033: pos rc 0, m4 rc 1.

## Gate 6 (10-19 ~11:50, `--cts`, ot-epyc8): WARN 0 fail
- Geometry: 241.92 x 88.56. The frame SRAM sits at (43.2, 43.2) **on the 43.2 lattice**; gate 5 had it off-lattice at 25.92, 54.
- Utilisation: std 5,179 um2, std density 49.4%, total fill 61%.
- Clock: 7,082 sinks. TT insertion 225.0 ps, FF 185.3 ps. Pin-flop spread **32.7 TT / 32.0 FF**.
- Timing: setup WNS +12 ps (macro->reg) and hold +40 ps at placement, TT. No cross-clock violation.
- Trial GRT overflow 0 (M2 50.7%).

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|---|---|
| 1 | pins | PASS: every input lands in a kept pin flop and every output leaves a flop (RTL). `rst_n` goes through `ot_rst_relay` (2 sync stages). |
| 2 | reach | PASS: the tile is 242 um; there is no wire > 405 um. |
| 3 | fanout | PASS for data. The reset relay output drives 398 flops (WARN, guidance; reset only, not a data path). |
| 4 | depth | PASS: 371.7 ps max at synthesis. CW=2 has no SRAM-output bypass; the SRAM output feeds only the ring registers. |
| 5 | storage | PASS: the frame programme is in an SRAM macro. CW=2 compact windows hold 6,656 flops (shared head rows + 3-row ring), down from 9,216. |
| 6 | floorplan | **fixed**: the macro is on the 43.2 lattice on the pin-free N face, with one full-width std band. Inputs are on W, outputs on S. Util 49%. **Waived:** aspect 2.7:1, because the macro is 172.8 um wide plus lattice channels and util 40-60% forces the height; every dimension is < 405 um. |
| 7 | clock | PASS: clk is at the S centre beside the register mass. Spread is 32.7 / 32.0 ps. `io_hold_margin` is 0.03. The SRAM clock is a separate entry (`clk_program_mem`, same PLL phase). |
| 8 | schedule | PASS: static calendar, collisions fault, no credits. |

If the pin-registered key buffer (kb2, quad `KBP = 2`) is adopted, this tile takes `G2MIN = 25` and must be regated.
