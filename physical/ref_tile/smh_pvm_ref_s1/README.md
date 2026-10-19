# smh_pvm_ref_s1 -- SAFE redesign of smh_pvm (ot_hbm_sm_pv_merge #(TAGW 16, LV 4, PUBLISH 1, TURNREG 1, SAFE 1))

HBM-PVM-SAFE 2026-10-19. Replaces smh_pvm_ref_r4 after route `smh_pvm_ref_r4-r3-f63e66b4c` ended NEEDS_RTL
(TT -125.42 / FF -17.57 ps, DRC 0). Several failed attempts on this tile, so this is a structural redesign.

## Failing path classes of r3 (routed result, TT / FF, `path_summary` at 2,000 endpoints)

| class | TT setup | paths | levels | cause | fix in s1 |
|---|---|---|---|---|---|
| u_stack/rd_out -> g_madd.u_ca (adder A1 decode/compare) | -125.4 | 456 | 14 | macro read -> operand mux -> 31-bit KS compare in one cycle; long rd_out wires (W face to the logic ring) | (a) operand registers |
| fd1 -> u_stack/wd_in | -48.6 | 463 | 18 | priority write mux with the select (fd1 / ev / turn state) on 512 bits | (c) 2:1 write mux on ev |
| ev pin reg -> g_madd.u_ca | -21.0 | 588 | 21 | ev -> turn decode -> operand mux -> adder A1 | (a) |
| FF hold: u_cb -> u_cd, s2_* -> u_cc, y -> vreg | -17.6 | 214 | 2-4 | adder pass-through stages with 40 ps leaf skew; 7k async-reset datapath flops | (b) DRST 0, (a) no vreg, (d) ring |
| FF hold: fw_a -> fw_a | -0.2 | 18 | 2 | 8-deep fold address delay line | (d) ring |

Reach was not a factor: the r4 outline (373.68 x 146.88) had no wire longer than 405 um. Its aspect ratio was 2.54:1, and the macro sat off the 43.2 lattice.

## RTL (SAFE 1; SAFE 0 = the r4 form unchanged)

- (a) Operand registers oa / ob / ov feed the 16 adders. The result register vreg is removed, and the adder's own y is read at the entry's next turn. A merge turn is still 8 cycles (1 + ALAT 7), so the merge stream is cycle-identical (bench: 599 cycles in both forms).
- (b) The adders are `ot_hdc_fp32_add_lat #(.LAT(7), .DRST(0))`: only the valid bits are reset. The textbook tool had flagged the 7,077-load rst tree, which this removes.
- (c) Stack write data = `ev ? sum : y`. This matches the 3-way priority mux on every schedule that does not fault.
- (d) The fold write-back tracker is an 8-slot ring on a free-running index, replacing the fw_a / fw_v delay lines.
- Schedule: a fold's sum is written ALAT + 3 cycles after the request (was + 2). A fold may name as b a node whose write-back lands in the request cycle. Publication of a folded node must come at least 1 cycle after its write-back, otherwise a sticky fault is raised. The Qwen h128 calendar change is publication of node 0 at F0 + 22 -> F0 + 23, i.e. +1 cycle per head block per column. This was handed to TW5-HBM-DIE and HBM-REPRICE3.

## Benches (Verilator 5.050, results/arch/hbm_pvm_safe_1019/bench)
exact PASS 240, tight-fold calendar PASS 192 (b written back in the request cycle; publication at the earliest legal cycle),
mut1 / mut4 / mut5 FAIL (negative controls), pubearly FAIL (publication 1 cycle early -> fault + stale data: schedule witness).
SAFE 0 regression: exact PASS 240, tight PASS 192.

## SAFE-DESIGN CHECKLIST (owner 10-19)
1. Pins: PASS. Pin registers on every data pin (recipe 4) and a 2-stage reset landing (OT_RST_LAND=1, stages 2).
2. Reach: PASS. The outline is 259.2 x 172.8, so no single-cycle wire exceeds 405 um.
3. Fanout: fixed. The datapath reset tree is gone (DRST 0). The write mux has one select (ev). The operand-mux selects drive register D pins only (the adder logic is now the next stage), and repair_design buffers them. The reset after landing is not timing-critical (audit R2).
4. Depth: fixed. Macro -> operand register, then operand register -> adder A1. There are no combinational in->out paths (pin registers).
5. Storage: PASS. The 32 kb stack is the 64x512 SRAM macro. The fold delay line is now a ring. The adder stage registers are a pipeline, not a delay line (each hop carries logic or a select).
6. Floorplan: fixed, with one waiver.
   - Fixed: the macro is at (43.2, 43.2) on the lattice. The outline comes from synthesis area (std ~11.4k um2 + macro 13.3k): 259.2 x 172.8 = 1.5:1, fill about 55 %. Full-width std-cell bands run N and S of the macro.
   - Waived: the macro's W / E pin faces carry about 780 pins each on 77.76 um (about 10 pins/um). This is fixed by the macro LEF, which is pin-limited. Mitigation: 43.2 / 44.7 um channels on those faces plus the 5.4 um halo.
7. Clock: PASS (gate numbers below). A single root, centre-fed (`-no_obstruction_aware` H-tree). Pin-flop spread must be <= 80 at TT and FF. io_hold_margin is 0.03.
8. Schedule: the design is static. The +1 fold write-back cycle was handed to TW5-HBM-DIE and HBM-REPRICE3.

## Gate
(filled in after the --cts gate)
