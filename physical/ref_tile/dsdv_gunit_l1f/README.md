# dsdv_gunit_l1f N32 (DRIVE-S81-GUNIT, 10-20, tree S81.STA.PAR.3)

Router select front of dsdv_gunit (hardened once, 4 instances beside the stack leaf L1). Fallback kit with the same RTL:
`dsdv_gunit_l1f_b` (302.4 x 345.6). Bind the first one to close.

## Why this successor
The 10-18 RTL never closed: its gates failed trial GRT (259.2^2 GRT out of memory; 259.2 x 302.4 overflow 176 above
the SRAM stack, W pins packed into the upper third of the face). The pre-gate native census of that RTL
(probe e5122895e, ep9 ref_gate/dsdv_gunit_l1f-20261020-212633) FAILED with 1,046 drivers above 32 loads (max 2,110):

| class | loads | fix (0 edges) |
|---|---|---|
| wq write enables | 2,110 | 9 kept copies (8 entry groups + the beat-0 forward) |
| beat number cbn | 1,030 | 19 kept copies, one per 27-bit read slice |
| reset relay | 639 | valid/enable-only reset, 13 kept relay regions (<= 28 loads) |
| gq2 reply select | 431 | 9 kept copies |
| SC data ad/bd | 64 | 4 kept copies at the pins |
| f12 LAT-5 adder cut regs | 56-69 | ve-local NATIVE-32 adder `ot_s81sl_ve_qadd` LAT 4 behind a kept twin operand register (= LAT 5, bit-exact f12) |
| adder y | 33 | key bits 0..15 from y, 16..31 from the kept copy y2 |
| cfw | 33 | 2 kept copies |
| 420 comb sort/merge/decode selects | 33-200 | `dsdv_gunit_sel_n32`: 4 kept compare copies per exchange, one per record-bit slice; per-entry/half-word kept write decode `dsdv_l1f_wdec`; 4 kept gather-request copies |

## GUNIT2 (10-20 ~23:20): census of the N32 RTL and its fix
The N32 gates (ref_gate 20261020-214042, A and B) were refused at floorplan: PRE_GATE_NATIVE_CENSUS FAIL, 488 drivers
> 32 (max 276). Codex's row-decode localisation (a65070b5f) measured 590 / max 394. Root causes (synthesis, not plan):
- the kept copies were UNPACKED ARRAYS (`reg [13:0] wqc [0:8]`): yosys makes memories, `ot_keep_regs.tcl` never sees a keep
  wire and opt_merge folded each copy set into one flop (wq 276, cbc 60, gq2 56);
- the kept modules were PARAMETERISED (`dsdv_l1f_wdec #(I,H)`, `dsdv_seln_gt #(W)`) and got flattened (`$paramod` misses
  SYNTH_KEEP_MODULES), so ABC merged the compare copies (72) and pushed the shared row decode into the data AND-ORs (238);
- the census counts leaf pins THROUGH buffers/inverters and hierarchy, so a select reaches ~2 pins per muxed bit and
  a comparator input ~3 pins per compare.
Fix (same ports / function / edges): packed keep vectors; unparameterised kept fan-out fences (`dsdv_l1f_wdec8` with
`dsdv_l1f_term8` + two `dsdv_l1f_or8` byte enables, `dsdv_l1f_dec64` row one-hot per copy, `dsdv_l1f_dec7` beat one-hot x 32
copies of 16 read bits, `dsdv_l1f_mux8` forward byte select; select network: `dsdv_seln_gt40` = 10 kept `dsdv_seln_cmp4`,
S = 8 compare copies, kept `dsdv_seln_mux1` record muxes, key / sort-stage / merge registers kept twice (A feeds the select
compares, B the candidate compares and data)); ND 5, NQ 18, 4 cfw copies.
Pre-gate census (ORFS synth of this RTL, ep7 drives81-gunit2): **PASS, max 32, 0 violations, 192,363 roots**; synth area
36,915 um^2 (was 33,200). Receipt `results/rtl/drives81_gunit_l1f_1020/gunit2/native_census.json` (top 200 drivers).
Benches (Verilator 5.050, ep7): gunit exact 8 PASS (router_lat 38, hc_lat 748 = 10-18), MUT1 FAIL 40; witnesses
`results/rtl/drives81_gunit_l1f_1020/gunit2/`.

## SAFE checklist
1. Pins: every input lands in a flop, every output is a flop (pin_regs off: source-registered); reset via ot_rst_relay 2 sync + 1 relay. PASS
2. Reach: tile < 405 um across. PASS
3. Fanout: GUNIT2 census PASS max 32 (0 drivers > 32, reset included). fixed
4. Depth: unchanged stage structure (one compare deep a select stage; adder f12 cuts). PASS (gate path classes decide)
5. Storage: SC store 112 x 32 b = 3,584 b stays in flops (written sparse by beat, read by one-hot beat select and the gather; an SRAM would add read edges on the select path). Waived under the 10-20 RULE FREEZE; bias table is in 2 SRAM macros.
6. Floorplan: 2 SRAM macros on the 43.2 lattice, one std-cell band, W pins spread over the full face; A 259.2 x 302.4 (~47% of std area 36.9k), B 302.4 x 345.6 (~36%). PASS
7. Clock: single region (< 1 mm); pin-flop spread <= 80 TT/FF measured by the --cts gate; io_hold_margin 0.03. gate
8. Schedule: 0 edges added (same calendar: adders E+6, key E+7, sort E+10, merge E+12). PASS

Benches: `run_gunit_bench.sh` (whole dsdv_gunit, split-L1 lineage) exact 8 cases + MUT1 (bias not added) on Verilator 5.050.
