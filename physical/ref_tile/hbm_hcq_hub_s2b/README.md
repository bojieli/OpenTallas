# hbm_hcq_hub_s2b (PARALLEL variant of hbm_hcq_hub_s2): safe successor of the d4g HC quarter hub (hbm_hcq_hub_1017)

Lane HBM-ELEMOWN3/QHUB, 2026-10-19. Branch `claude/hcq-hub-s1-1019`. Spec source: `physical/hbm_hc_hub/specs/hbm_hcq_hub_s2b.json`.
THIS kit is the PARALLEL variant: the same RTL as `hbm_hcq_hub_s2`, but a wider band (432.0 um at 151.2..583.2, PD 0.45; face pin <= ~302 um from the band).
Bind whichever closes first and cancel the other.

## Why a structural redesign

The 1017 `--cts` gate (10-19 03:42) failed. CTS and the trial GRT were both killed (rc137) after 4 h each, with the
post-CTS repair stuck at WNS -155 ps and TNS -93 ns. The design point was:

- one clock root for 48.7k flops over the 734.4 um square at ~10 % utilisation, with the pin flops anchored on all four faces;
- 2,049 s_i bits feeding the level-1 adders' decode logic straight from the port; io_flop_at_pins then dragged those adder cut registers to the W face (1,600 input endpoints with more than 3 levels);
- reset nets of 2,193, 1,063 and 299 loads;
- a runtime part-select;
- calendar -> gather.issue_sector at ~678 ps / 17 levels.

The P3 attempt (`hnx_hcq_hub_safe_1019`, central band) fixed the placement. It then stalled in CTS repair at WNS -49.9 ps,
because it had absorbed the s_i register into a LAT-6 level-1 adder. Its kept-module beat copies were also folded by
yosys, and its reset split never matched (the wrong relay names). This kit keeps the band and fixes the other three.

## s2 delta (10-19 ~23:00, from the s1 / s1b gate textbook on ot-agidock128)

The s1 synthesis showed no reset net over 32 loads, so the split worked. Two findings remained:

- `u_q.gather.return_sector[2]` had 3,088 loads: it was the select of the 768-b 8:1 return mux. It is now 24 kept copies of `return_sector[2:0]` (RSC). Each copy drives the decoded one-hot AND-OR of one 32-b chunk, and the copies load the same values on the same edges.
- `captured -> gb` was ~688 ps / 19 levels. It is now an exact shallow form: n1 = npos - 1 in 0..7, three masked shifted addends, a 19-b sum, last < 32768 <=> last[18:15] == 0.

Benches for the RTL at @0abb3677c (iverilog, ot-epyc5):

- hcq SAFE 1 with GSTR 43 (the return sectors cross banks, so every copy is exercised): MUT 0 PASS, 1/7 FAIL;
- GSTR 40: 0 PASS, 1-4/7 FAIL;
- SAFE 0 with GSTR 40/43: 0 PASS, 1-4 FAIL.

Logs: `results/rtl/hbm_hcq_hub_s2/`. The ring is unchanged (qcen untouched), so the s1 ring witnesses hold.

## SAFE-DESIGN checklist (owner 10-19, 8 items)

| # | item | result |
|---|---|---|
| 1 | Pins registered; 2-stage reset landing | **fixed**. s_i now lands in a pin register (qcen SAFE 1); every other port was already registered. rst_n uses the 2-stage `reset_landing`. |
| 2 | Reach <= 405 um per cycle | **fixed** by placement. Every cell is in the central band (194.4..540.0), so a face pin is at most ~384 um from the band (perpendicular + along the face). xb_v*/xb_beat* leave their OWN per-face kept copy (x_face_*: W, N, E, S + a centre copy for the rx), so no register is tied to pins on two faces (P3 n1 / safe gate wire_reach). |
| 3 | Fanout <= ~32 | **fixed**. Reset loads: the q relay has 96 kept copies, the centre 32 (u_rst_relay), the F20 target body 40 (`__ot_rlv`). `reset_relay_split` max_loads 32 with an explicit `re` that matches these names, spread by physical/common_flow/ot_rst_copies.tcl. The x_wave capture enable is 64 kept copies (32 bits each). The calendar's gather_phase bit no longer gates 2 x 2,056 data bits: only the 8 sector valid bits are steered. Copies are kept registers, not keep_modules. |
| 4 | Depth <= ~600 ps / 20 levels | **fixed**. The gathered-reader launch bounds are precomputed one register earlier from the programme word (ot_hbm_hc_qcal_static `gb`, same value, 0 edges). Every tree adder keeps LAT 7. Assembly writes are decoded constant-index slices, with no runtime part-select. |
| 5 | Storage > 2 kb in SRAM | PASS. The programme is a 1024x256 SRAM. rr_q/result_q/s_q are single captures. done_cal (152 b), order (12x23) and installed (1 kb) are under 2 kb. |
| 6 | Floorplan | **fixed / waived**. The SRAM is at (259.2, 302.4) on the 43.2 lattice with a 5.4 halo, and there is one contiguous band, aspect 1:1. Tile utilisation stays ~9 % (fill_reason.pin_bound): 9,903 literal face pins sit in the 734.4 hole of the bank ring. Band utilisation is ~40 %. |
| 7 | Clock | **fixed** structurally. There is one root, but its sinks are a compact 345.6 um register mass, not four faces 734 um apart. io_hold_margin is 0.03. The `--cts` gate measures TT/FF spread (limit 80). |
| 8 | Static schedule, cycles priced | **+1 edge**. The s_i pin register delays the quarter subtree, so ps_v/ps/ps_f leave 1 edge later. The root takes this as QCHX 12 (= 11 CPR + 1) and the programme as RAW0 179 (165 + 11 CPR + 2 DRLY + 1); bench form = the closed ring the kits encode (HC_XRLY 0, the U relay is the die lead's open choice). Bench: HC_QSI=1. Ledger: hc_tree 41 -> 42 edges, under 0.1 % of the HC mix and well under 1 % end to end. Everything else adds 0 edges. |

## Benches (fleet, @ca6cb0c03)

- hcq (iverilog, ot-epyc5):
  - SAFE 0 regression: MUT 0 PASS, 1-4 FAIL.
  - SAFE 1: MUT 0 PASS, 1/2/3/4/7 FAIL. The face-copy equality is checked on every edge.
  - Logs: `results/rtl/hbm_hcq_hub_s1/hcq_*.log`.
- Ring lockstep, Verilator 5.050: `HC_XDEF='+define+HC_DRLY=2 +define+HC_XRLY=0 +define+HC_QSI=1'`.
  - MUT 0 **PASS**: HC_ENG PASS, mixbad 0, outbad 0, HC_MIX_CYCLES 1010 (RAW0 179). Log: `results/rtl/hbm_hcq_hub_s1/ring_m0.log`.
  - MUT 6 (s_i register without the valid delay) **FAIL**: HC_ENG_FAULT ps=1 at t=2181, rc 1.
  - Witness: `results/rtl/hbm_hcq_hub_s1/ring_mut6.log`.

## Gate acceptance

- `--cts --remote auto`;
- GRT overflow 0;
- pin-flop spread <= 80 at TT and FF;
- the gpl log shows `HC_HUB_BAND gpl region`;
- textbook high_fanout shows no reset over 32;
- the PNG shows the band and the SRAM on the lattice.

Not a critical tile, so submit with submit_exact (reroute_reason: the 1017 gate failure).
The die contract needs root QCHX 12 when this hub binds: a NOTICE goes to HBM-HCRING / the root kit.
