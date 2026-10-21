# qfd_tt_ctlm_dv_safe8u -- QW-TTC8 10-20: safe8t + region dissolve before DPL (structural fix of the safe8t DPL FAIL)

Netlist, RTL, pins, macros, outline, regions and clocks are byte-identical to safe8t (candidate8 r7 lp8_np, lockstep
PASS 186,922 / mutants FAIL 9,838 / 4,748 at 780d83de9). No new cycle, no price change. Not on critical_tiles.txt.

## safe8t failure, read from the actual run (agidock ref_gate/qfd_tt_ctlm_dv_safe8t-20261020-0936*/cts.log; failed ODB was in the container, not kept)
- GPL converged (TD off); OT_LCR regions core / hr std util 9.9 % / 4.4 % (bt 11.7 / 5.2 %): NOT a capacity problem.
- 3_4 repair_design: 7,750 slew + 625 cap violations -> inserted 12,828 (bt 11,633) buffers. OpenROAD does not put
  repair-created cells in the driver's dbGroup; OpenDP forbids un-grouped cells inside a region, so every buffer placed
  next to its cone deep inside ot_lcr_core / ot_lcr_hr had to move to the 43.2 um pin bands (Y movement 1.79e9 DBU).
- DPL negotiation: 27,582 illegal cells -> 15,992 stuck -> 9,806 edge-spacing / 226 padding / 13,686 overlaps, then
  improve_placement crashed (detail_place.tcl:42 bad optional access = consequence). clock_rule FAIL = no CTS ran.

## Fix (pre_dpl_extra lcr_dissolve_after_gpl.tcl)
GPL places every owned cell inside its region (the core/hr partition, i.e. the per-root clock locality, lives in the
placement). After the pin-cell release the hook counts un-grouped cells inside each region box (log OT_LCD), then
destroys the two ot_lcr groups / regions, so DPL legalises locally and CTS / GRT repair cells also have a legal home.
Main safe8u = 777.6 x 648 (40.5 um SRAM row channels); parallel fallback safe8bu = 777.6 x 604.8 (20.6 um channels).

## SAFE checklist (unchanged from safe8t unless noted)
1 Pins PASS (lp landings + cf pin register; 2-stage regional reset) | 2 Reach: gate wire_reach | 3 Fanout PASS (census
max 32) | 4 Depth 686.8 ps / 23 lv WARN (>600; named start-range cone, CTLM9 RTL round; textbook in-flow 711.8) |
5 Storage PASS (6 SRAM + 3 ROM) | 6 Floorplan PASS (lattice, channels >= 20 um, fill 46.6 / 50.0 %, aspect 1.2/1.29) +
FIXED: region membership no longer blocks repair cells | 7 Clock: regional ck_core / ck_hr (11,199 / 4,626 flops) with
landed crossings; gate measures spread per root | 8 Schedule static, no new edge.
Pre-gate native census: candidate8 r7 strict PASS max 32 / 0 violations (gate native_census PASS max=32 on safe8t).
