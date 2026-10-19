# hcoll_gq_issue_1018: COLL gather master issue leaf (ot_hgi_coll_gq_issue)

The d4g plan (b) per-quadrant COLL gather master, issue leaf. It holds the F20 target, the descriptor calendar, the
static two-ring gather schedule, the VM reads, two flat quantisers (ot_hgi_coll_aq13), the payload P, and the ring
commands. The RTL is `rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv`. The bench is
`run_coll_gq_bench.sh`; the compiler model is `tools/hgi_sim/collq_gather_1018.py`.

## History

| Run | Result | Cause |
|---|---|---|
| r1 `5d045cb87` | NEEDS_RTL | stale job.json mutant count |
| r2 `a481cc848` | NEEDS_RTL, TT -98.19 / FF -27.71 | TT: held-state select fan-out into the ld_p_d / aq_x muxes. FF: gated quantiser-line banks were early. |
| r3 gate (1c5b70cbb) | FAIL reset_landing | The worktree had a stale `ot_pin_regs.tcl` without OT_RST_LAND, so the port reached 3 relay flops. The gate also warned: wp 3,073 loads; 37,053 flops on one root; s3->s4 630 ps; util 45 %. |

## r4: SAFE-DESIGN checklist (owner 10-19; redesign after two failed routes)

r4 moves no edges. The gather schedule, the quantiser latency (13), and every pin's edge are unchanged, and the bench
is bit-exact.

| # | Item | Result |
|---|---|---|
| 1 | Pins | **PASS.** Every input is captured by a flop at the pin, and every output is a flop Q in the RTL (gather stage table). The pin_regs opt-out stands, with its reason in spec.json. Reset lands at the face in 2 registered stages: `reset_landing` with main's `ot_pin_regs.tcl` (OT_RST_LAND); r3 ran a stale copy. After landing, ot_rst_relay REGIONS 6 drives one kept copy per region: calendar, event/valid pipes, VM request, ring/merge, and quantiser 0/1. Each copy has ≤ ~200 async loads (r3: one relay flop had 1,154). |
| 2 | Reach | **PASS.** The tile is 224.64 um square (gate reach 57 um), so no wire exceeds 405 um. |
| 3 | Fanout | **Fixed.** Kept copies (`(* keep *)`, turned into kept flop cells by `ot_keep_regs.tcl`, attribute-based, so paramod renaming does not matter) replace the high-fanout drivers. Quantiser line pointer: 64 reset-free, self-correcting one-hot copies per instance (`ot_hdc_delay_hc` WG 16), 32 loads per bit (r3: 3,073). Quantiser-feed bank one-hots: 8 per 256-b word, 32 loads (r3: 256). P raw/code/exp-lo/exp-hi one-hots: 8 per word, 32 loads (r3: 256). Calendar row read cur one-hot: 4 copies, ~26 loads (r3: 101). Exponent bytes: 2 per ring, 32 lanes (r3: 64). Quantiser S8/S10 e and fp4: 4 copies, 8 elements each. The exponent-word clear moved to the kept fire_q (+0 schedule edges: no exponent flit merges within 24 edges of a fire), which takes 512 loads off the calendar compare. g_src (the SAFE-AUDIT 5,899 loads were the r2 netlist) is read only by the one-edge-ahead pre-stages since r3; the r3 netlist's top fan-out list holds only wp. **Check at gate:** the kept-copy counts must survive synthesis (textbook high_fanout_top). |
| 4 | Depth | **Fixed.** The scale multiply's stage 4 now uses pre-decoded alignment (`ot_hgi_coll_aq_scale13r`): a one-hot shift over 23..48 plus a sticky thermometer, registered at s2/s3 from the exponent-only decision. Stage 4 is then an AND-OR + increment, where r3 had a per-bit 12-b add, range compare and 48:1 decode (630 ps / 17 levels). Same 5 edges. It is exact against the closed `ot_hbm_xp_aq_scale13` (tb_aq_scale13r_eq: every a exponent field x 4,096 significands x 2 signs x both coefficients) and against tree13 (tb_aq_tree13). No in->out combinational path. |
| 5 | Storage | **PASS.** The 1,024 x 9-edge element line is a ring buffer: 8 load-enabled banks, a statically rotating one-hot pointer, and a one-hot read (the checklist's delay-line form). It is never data-indexed. The calendar rf is 16 x 101 b (1.6 kb < 2 kb). The SRAM alternative (2 x `ot_sram_1r1w2c_16x546` per quantiser, half the rows unused) was considered and not taken: 4 macros in a 225 um pin-bound tile. |
| 6 | Floorplan | **PASS.** No macros. The outline comes from synthesis area (std_area_um2 25,000, util 0.52), giving 224.64 x 224.64 (1:1) with a full std-cell band. The densest face is E at ~1,150 pins / 224.6 um = 5.1 pins/um, under 6. |
| 7 | Clock | **PASS (clock rule).** There is one root of ~39k sinks. The r3 CTS gate measured pin-flop spread TT 17.1 / FF 15.8 ps (<= 80). By the owner's 10-17 rule the sink count alone is not a split reason; the parent compensates the boundary insertion (TT 335 / FF 270). Regional roots were not built: no hard children, 225 um tile. The bank/read registers share one ungated tree (GATED 0, as in r3). io_hold_margin is 0.03. |
| 8 | Schedule | **PASS.** Static: no credits or backpressure. No edge was added, so nothing goes to the GQ calendar / HBM-REPRICE. |
