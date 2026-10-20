# hnx_hcq_hub_safe2_1020: SAFE2 successor of the HC quarter hub (hnx_hcq_hub_safe_1019)

Lane HNEXT-LEAD/HNX-UNITS, 2026-10-20. Branch `claude/hnx-hub-safe2-1020`. Spec `physical/hbm_next/hc/specs/hnx_hcq_hub_safe2_1020.json`.
PARALLEL variant (same RTL, 432 band): `hnx_hcq_hub_safe2b_1020`. Bind whichever closes first under the checklist; cancel the other.

## Why (safe1019 gates s1 / b389, 10-19, both FAIL; evidence 48d4a1d9d on claude/hnx-hub-safe-1019)

- CTS: one root over 47,484 sinks in the 345.6 band. Input pin-flop arrival 621.7..758.3 ps TT (spread 136.6) and
  512.8..641.1 FF (128.3). The hold repair then crawled 4.9 h (42.7k hold buffers, WNS stuck at -49.87 on a qcen level-1
  adder register) until the gate killed it (CTS rc 137).
- keep_modules: `ot_hnx_hc_xbrep` matched no module after flattening. The four per-face beat copies folded into one
  register that drove the N and E face pins (wire_reach 540-560 um).
- Native census of the synthesised netlist (textbook_lint hf 32): 909 drivers > 32 loads. hc_q: residual.valid[22] 4,129,
  c[21] (gather_phase) 3,524, store reset 2,193, gather.return_sector[2:0] 1,098-2,067, target.reset_live 1,059,
  target.scan_row[0] 1,032, ~300 anonymous decode nets of 470-800 (store crossbar, gather muxes). qcen: 566 drivers of
  33-219 inside the ot_hdc_fp32_add_lat cut stages.
- GPL in the 345.6 band: routing congestion 1.15 (2.4 % overflowed gcells).

## The structure (0 added schedule edges)

1. Clock: 32 regional roots by k-means over the placed sinks (`physical/common_flow/clock_split_km.tcl`, OT_CKKM_K 32), with
   one external root and CTS balancing the roots. This is the closed XS ring fix: km16 measured 125.6 ps, km32 39.6 ps.
2. hc_q fanout rebuild:
   - The store bank routing is decoded on the calendar edge by the hc calendar copy `ot_hnx_hc_cal`, from its capture
     register, as kept one-hot copies (one per 32-b lane group). local_wq is then one AND-OR level, bit-identical.
   - gather: the issue and return bank selects are kept one-hot copies loaded with the next sector. The response copies
     are registered one edge ahead. The 23-row stream leaves a shift register instead of the next_row mux.
   - residual: 64 kept capture-valid copies, one per 32-b lane group of the 2,048-b beat register.
   - gather_phase gates only the 8 return-valid bits per reader, through kept copies `gp_c`.
   - The data registers are reset-free: store data/address 2,248 bits, and lg_rq addresses.
3. Programme target copy `ot_hnx_prog_target`:
   - The 1,024-row bitmap is 32 x 32 with kept per-row write / clear / row / column copies.
   - The bitmap has no reset. `img_v` marks the first image, and the first write clears it, as before.
   - The scan reads the bitmap in two registered stages. This is initialization only: configured rises 2 edges later,
     and the host waits for configured.
4. `ot_hnx_hc_xbrep`: the copies are `(* keep *)` registers (ot_keep_regs.tcl). The module-name keep is dropped.
5. The reset relays are named `u_rst_relay` (REGIONS 16 in hc_q and qcen), so the ot_rst_copies.py synthesis pass
   splits the reset loads over the copies (<= 32).
6. The standard-cell band is 388.8 um here and 432 in the b variant (safe1019 345.6 was congested). The face pin to band
   reach is <= 2 x 172.8 = 346 um (<= 2 x 151.2 in b).

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|---|---|
| 1 | pins registered, 2-stage reset landing | PASS (unchanged from safe1019: SIREG 1, hc_q/qcen pin flops, kit reset_landing 2) |
| 2 | reach <= 405 um | fixed: xbrep copies are kept again (n1 fix restored); every register sits in the central band, and a face pin is <= 346 um (b: 302) away |
| 3 | fanout <= ~32 | fixed in hc_q (above). Waived with reason: qcen ot_hdc_fp32_add_lat internal cut-stage datapath fanout (<= 136 non-reset, alignment / normalise selects of the closed arithmetic primitive), bounded per stage by logic_depth + TT setup. The pre-gate census numbers are below. |
| 4 | depth <= 600 ps | gather/store/residual paths are now 1 AND-OR level from kept registers. safe1019 lint: one 712 ps estimate (c[23] -> gather.next_row, removed by the shift stream) |
| 5 | storage > 2 kb in SRAM | PASS: programme 1024x256 SRAM. The bitmap is 1 kb (no runtime-indexed read wider than 32:1 per stage); the landing is 736 b, shifted not indexed |
| 6 | lattice, band, util, aspect | SRAM (259.2, 302.4) on the 43.2 lattice; one contiguous band; aspect 1:1; tile util pin-bound (fill_reason) |
| 7 | clock | fixed: km32 regional roots, one external root, io_hold_margin 0.03; the --cts gate measures TT/FF pin-flop spread |
| 8 | static schedule | PASS: 0 added edges on every schedule path. Only the F20 programme scan (initialization) takes +2 edges before configured |

## Benches (Verilator 5.050, fleet)

- q stage (tb_hnx_hc_q with the new leaves): q_n4s + q_d4g PASS required; q_m7/m8/m9 FAIL witnesses refreshed.
  Bundle b_b72f6e65f: see pending_results.
- The ring lockstep s0/s5/e1 (qcen + bank ring) touches qcen only through the relay rename: the safe1019 witnesses stand.

## Pre-gate census (10-20 07:01, synthesis gate @a8b354d73 on ot-epyc9; results/arch/hbm_next_1019/units/hc/census_safe2/)

The floorplan native census (tools/ref_tile/native_census.py, limit 32, no waivers) REFUSED: 984 drivers > 32, max 136.
hc_q went from 4,129 max to 90. The --cts gates were NOT launched.

Remaining violations (next RTL step):

- **qcen fp32 adders: 565 drivers.** Cut-stage registers u_ca rd (189, max 136), u_cd (155, 61), u_cc (126, 59), u_cb (95, 63).
  Fix: main's qualified `ot_hdc_fp32_add_lat_fan32 #(.SAFE_DIST(1))` (520dbea3a). It covers LAT 7 / DRST 0 only, so the
  SIREG level-1 LAT 6 adder needs either a LAT-6 native or SIREG level 1 at LAT 7. The second option is +1 edge on ps,
  which must be priced to the root / compiler.
- **qcen iv_q: 96.** Kept copies.
- **hc_q:**
  - c[24] 90 and c[1] 70: the npos fields feed the launch-time bound multipliers. Register the launch check one edge
    later (fault only).
  - residual.valid[21] 66: drives the 64 vc_c copies. Use two pre-copies.
  - vc_c 64 and gather rs_c 64: a 32-b enable maps to about 2 loads a bit. Use 16-b groups (128 / 16 copies).
  - programme 37.
  - Reset copies 33-55 (ot_rrs_* split copies; target reset_live 55): raise REGIONS.
  - Anonymous nets 121 and 74.
- **runtime_partselect WARN:** residual BEATS1 assembly (not instantiated at BEATS 4).
