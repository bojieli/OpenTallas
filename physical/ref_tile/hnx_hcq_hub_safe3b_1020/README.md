# hnx_hcq_hub_safe3b_1020: SAFE3 successor (432 band) of the HC quarter hub (hnx_hcq_hub_safe2_1020)

Lane HNX-UNITS, 2026-10-20. Branch `claude/hnx-hub-safe2-1020`. Spec `physical/hbm_next/hc/specs/hnx_hcq_hub_safe3b_1020.json`.
PARALLEL variant of `hnx_hcq_hub_safe3_1020` (same RTL, 388.8 band there). Bind whichever closes first under the checklist; cancel the other.
Geometry, clock (km32 regional roots), band and pins are the safe2 kit's unchanged; this step is RTL fan-out only.

## Why (safe2 pre-gate native census, 10-20 07:01, evidence d3f9aeda9)

native_census REFUSED 984 drivers > 32 (max 136); no --cts gate was launched. Classified (trace of the mapped netlist):
- qcen fp32 tree adders: 565 named cut-stage registers + 263 of the 275 anonymous nets (all inside `ot_hdc_fp32_add_lat`).
- hc_q: calendar fields c[24] 90, c[1] 70, c[0] 53 (launch-time bound multipliers and launch enables); residual vc_c 64 x 64,
  valid[21] 66, active 39, rbase[1] 35; gather resp_c 22 x 64, issue_sector[0] 48, launch accept (start) 121, output
  enables 39-55, rs_c[0] 33; calendar gp_r 37, word_ok 47, start accept 42; programme target reset_live 55, we_n 42,
  descriptor accept 55 / 74, scan_start 37, io_n 33; qcen iv_q 96; reset copies 33-41 (qcen relay c1/c2, rstb_w/e, rl1).

## The structure (one added edge, priced)

1. qcen `FAN32 1`: all 63 tree adders are main's qualified native `ot_hdc_fp32_add_lat_fan32 #(.LAT(7),.DRST(0),.SAFE_DIST(1))`
   (520dbea3a: SAT-proved equal to the released LAT 7 / DRST 0 adder; <= 32 loads on every driver incl. inputs / reset).
   There is no LAT-6 native, so with the s_i pin register (SIREG 1) level 1 stays at LAT 7: ps_v / ps / ps_f leave
   ONE edge later. The root takes it as `QXL 1` (SYS_LAT + 1) and the compiler constant RAW0 is 168 (was 167).
   PRICE: +1 edge (0.83 ns) per quarter subtree sum = per HC_MIX reduction; at <= 4 HC reductions a layer x 61 layers
   that is <= 244 edges = 0.20 us per token against ~513 us (1,950 tok/s AR): <= 0.04 % AR, below the 1 % lever floor
   and inside the accepted closure-cost ledger. Handed to HNEXT.CMTP / HNEXT.DIE: root `QXL 1`, RAW0 168.
   Kept copies: 32 leaf-valid copies (one per level-1 adder), 3 ingest-event copies; relay REGIONS 32.
2. hc_q, zero added edges, bit-identical outputs on every legal programme:
   - calendar: valid1 x3 (gate per consumer group), start_v_q x3 (start accept per register group), running copy for
     the 32-b issued counter, gp_c 16 copies (address / valid selects), launch copies lc_c (residual x2, gather x4);
   - residual reader: the launch check (fault only; the run started regardless before too) runs one edge later from
     registered operands; act_o copy for request valid / read; the request sector adder is shared (s = rbase + 8 rslot,
     + b); 128 beat-valid copies (16-b groups) from 4 pre-copies, a word / beat enable copy;
   - gather reader: launch accept per register group (4 launch + 4 active copies; the bound uses the 3-b npos - 1, which
     is exact whenever bounds_ok can be true); response copies registered one edge ahead (48 landing + 4 control, from 2
     kept phase copies); 2 streaming copies; issue sectors registered (q_j = next issue sector + j); request ADDRESS
     bits are no longer zeroed while the request valid is 0 (don't-care; the valid bits are exact); a 9th rsel copy;
   - result store: the store-slot check runs one edge later from registered operands (fault only);
   - programme target: reset_live = 4-copy kept family (ot_rst_split), cfg_v x2 / desc_v x3 copies (row-half write
     strobe and image clear, descriptor accept per group), program_cfg_addr / program_start_* payload load every edge
     (read only with their strobes, which keep their exact edges), scan column copy per 2 rows; relay REGIONS 24.
3. Kit: reset landing last stage x4 copies (OT_RST_LAND_COPIES rst_n=4).

Fault timing: the three deferred checks raise the sticky fault one edge later on the same illegal programmes.

## SAFE-DESIGN checklist (owner 10-19)

| # | item | result |
|---|---|---|
| 1 | pins registered, 2-stage reset landing | PASS (safe2 unchanged; landing x4 copies) |
| 2 | reach <= 405 um | PASS (safe2: kept xbrep copies, every register in the central band, face pin <= 346 um) |
| 3 | fanout <= 32 | fixed above; the pre-gate census below is the witness |
| 4 | depth <= 600 ps | native adder 288 ps / 9 levels a stage (standalone); hc_q paths one AND-OR level from kept registers |
| 5 | storage > 2 kb in SRAM | PASS (programme 1024x256 SRAM; bitmap 1 kb) |
| 6 | lattice, band, util, aspect | PASS (safe2 geometry) |
| 7 | clock | km32 regional roots, io_hold_margin 0.03; the --cts gate measures TT/FF pin-flop spread |
| 8 | static schedule | +1 edge on the quarter subtree sum (priced above, handed to CMTP/DIE); 0 elsewhere |

## Benches (Verilator 5.050, fleet; tools/hbm_next/hnx_hc_bench.sh)

- q: q_n4s + q_d4g PASS required; q_m7 / m8 / m9 FAIL witnesses; eng4 lint.
- ring f0 (FAN32 + SIREG, QXL 1, RAW0 168): N 1,2,3,4,6,8 PASS; f5 (MUT 5) and fq (RAW0 167, the unpriced schedule) FAIL.

## Pre-gate census

Native census (tools/ref_tile/native_census.py, limit 32, no waivers, in the floorplan step), evidence
results/arch/hbm_next_1019/units/hc/census_safe3/ (native_census + trace per round):

| round | commit | drivers > 32 | max | what was left |
|---|---|---|---|---|
| safe2 | a8b354d73 | 984 | 136 | qcen adders 828, hc_q 156 |
| r1 | d46478db7 | 32 | 79 | deferred-check multipliers, scan copies per 2 rows, ingest copies, merged relay synchronisers |
| r2 | 4d6c23d83 | 6 | 45 | s0 cone, descriptor accept, q_n mux, row walk, streaming copies |
| r3 | d7b1740d9 | 3 | 45 | q_n mux replicated per j, launch group 3, captured folded into cap_k |
| r4 | b33e577b5 | 3 | 36 | header-cone position bits, gather active |
| r5 | 13f93e333 | **0 (PASS)** | 32 | - |

The r5 synthesis gate then stopped in timing-driven GPL: RSZ-3006 (a native-adder net whose load cell is dont_touch).
The native graph marks its cells keep + dont_touch for synthesis; the kit now clears that flag before GPL
(OT_NATIVE_UNTOUCH ".u_native.", physical/hbm_next/hc/hub_band_gpl.tcl): sizing / buffering keep the function, the
<= 32-load structure is fixed once mapped.
