# qfd_tt_ctlm_dv_safe4 — QW-CTLM4 (LEAD2-QW 10-19), parallel variant next to safe3 / safe3n

Base: safe3 (claude/qw-ctlm3-1019 @7e683685c: landing_reset_lead lp RTL, D2/K1 rings, no data multicycle, native_ret E recut),
regions kept (lp_cone_regions.tcl). Fallback without regions: qfd_tt_ctlm_dv_safe4n (identical otherwise).
Gate tools = origin/main + the QW-CTLM3 branch deltas (clock_entry_constraints no_data_multicycle, lp.py), as safe3.

It fixes the three open risks safe3 carried:

1. **ck_hr pin-flop spread (safe2n 176 / 166 ps TT / FF).** The hr register mass is two pin bands (N: pw/dh/obs at x475-775,
   S: hr/cmd/ss5/ag5 at x581-729) plus the E native strip (y78-188); the root was a S-face port at x655, so the N band sat
   ~430 um (around h16c) from the root while the S flops were next to it (soft boundary 568-797 ps). Now **ck_hr is an E-face
   port at y264.012 (M4)**, centre-fed between the two bands with the E channel (x734-775, beside h16c's E face) as the
   trunk: ~280 um to each band, ~80-190 um to the natives. The hr cells stay in their own region boxes (h16c box + the band
   above the OPROM row), so the hr tree is built over a compact, own-root region. Die GEN must deliver ck_hr on the E face.
2. **u_cal tcount -> fire_q ~745 ps / 20 levels.** FIREDQ in rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv: the relative head time
   dq = tcount + 1 - ht_q is a register kept by induction (start 2, reset 1, non-frozen edge dq + run_q - (nh_v ? dd : 0));
   fire_n compares the dq register with dd. The 20-bit incrementer + subtractor are gone from the fire_q cone. **Zero added
   edges**: edge-identical calendar (lockstep with qfd_dv_cmd_cal and the compiled NU4 timeline PASS), so nothing goes to
   the schedule / lanes/QW-GEN2.md for this item. Mutant MUT 34 (start loads dq one short) FAILS.
3. **SRAM face density 10.2 pins/um.** The six 64x512 SRAMs bind the QW-SRAM3 successor ot_sram_1r1w_64x512_m1_r2c2_p192_mir
   (W/E pins at 0.192 um = **5.21 pins/um**, 171.288 x 153.912, same ports / behaviour / read latency; kit shim
   rtl/lib/sram_p192_1019/ot_sram_1r1w_64x512_m1_r2c2__p192.sv, zero RTL edits). Pins sit only on W/E faces, so each column is
   an abutted 3-stack (QW-SRAM3 head_p192 recipe, 153.936 pitch on the 0.048 grid) at x43.2 / x259.2 with the 44.7 um
   pin-face channel between them. **Outline 777.6x432 -> 777.6x561.6** (fill from synthesis area: 53.4%); h16c, OPROM row,
   the E natives and every N/S pin x unchanged.

## Benches / witnesses (Verilator 5.050, fleet)
- bench_witness/ctlm4_v5050: mu_seq_bench MUT0 PASS / MUT34 FAIL (26,836 lockstep mismatches) / MUT1 FAIL; tile
  ctlm_abi_m0 PASS, ctlm_cal_m0 PASS 62/62, ctlm_cal_m1/m2/m3 FAIL 2/2/60 (re-witnessed on the FIREDQ RTL).
- bench_witness/lp_v5050: QW-CTLM3 lp lockstep (landed RTL unchanged): MUT0 PASS; MUT1/2/4/5 FAIL (regex "LP_LOCKSTEP FAIL").
- SRAM shim equivalence: QW-SRAM3 results/arch/qw_sram3_1019/p192_shim_equiv_verilator5050.log (all PASS, mask mutants FAIL).

## Safe-design checklist (owner 10-19)
| # | Item | Result |
|---|------|--------|
| 1 | Pins registered, reset landed 2 stages | PASS (inherited PINREG / OT_KEEP_PIN_REGS=1; lp regional reset runs). |
| 2 | Reach <= 405 um per cycle | PASS by plan: native_ret recut kept; N hr pin band -> h16c N face ~250-300 um; ring -> read crossings as safe3. Gate lint decides. |
| 3 | Fanout <= 32, kept copies | inherited lp_reset_copies + same_edge_reset_copies (max 32), kept CALPIPE selectors. |
| 4 | Depth <= ~600 ps | fixed: FIREDQ removes the 20-b inc+sub from tcount -> fire_q (dd mux -> 12-b compare remains). |
| 5 | Storage > 2 kb in SRAM | PASS (unchanged: CALPIPE FIFOs / store in SRAM rings; landing rings 1,904 b). |
| 6 | Floorplan | fixed: SRAM pin faces 5.21/um (p192), macros on the 43.2 lattice in x (abutted y stack on the 0.048 grid), outline from synthesis area at 53%, aspect 1.38, full-width N/S std bands. |
| 7 | Clock | fixed: ck_hr centre-fed on the E face beside the hr register mass, own region, landed crossings, io_hold 30 ps. Gate measures TT/FF spread. |
| 8 | Schedule | static; FIREDQ adds no edge. Slot change (height 561.6, ck_hr E face) -> GEN re-slot (lanes/QW-GEN2.md). |

Gate: pre_route_gate --remote auto --cts. Not critical. Submit only if a gate PASSes (coordinate with safe3/safe3n via lanes/QW-CTLM3.md).
