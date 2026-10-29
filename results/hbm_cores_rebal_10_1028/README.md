# HBM-CORES-REBAL-10 (2026-10-28): lanes__canon MLAT5/WCOPY1 re-place -- WCOPY copies kept + guided beside their SRAMs

Branch `claude/hbm-cores-rebal-10-1028` (base REBAL-9b 48957e0967). Everything new is opt-in; defaults are unchanged.

## 1. Root cause of the REBAL-9 post-CTS wd_in miss (-124.3 ps, 903 endpoints) -- CHECKED
* **The column copies did not exist.** yosys `opt_merge` folded the READERS identical WCOPY registers (same D, same clock)
  into one flop per bank. The REBAL-9 4_cts netlist has copy flops under only 1-2 columns per bank: 168 copy flops
  instead of 1008 (4 banks x 6 columns x 42). The surviving copy then broadcast to all 6 SRAMs again, up to **809 um** from
  an SRAM it writes (rend_mrg.py on REBAL-9 canon_post/cts.csv). Example: the -124.3 ps path starts at
  `u_bank2...g_read[2].g_wcopy.wd_q[2]` and ends at `g_read[4].u_m/wd_in`, through 13 buffers (695 ps).
* **The write relays sat at the pins.** The pinned-bank write registers (wd_pin/wa_pin/w_pin) were placed at the south
  write pins (wa_pin y = 5.4 um). The copy hop therefore spanned the whole die height.
* The bank2 columns are spread across the core by the plan-fixed macro table (mp3_lanes__canon, REBAL-4): x 35-726 um,
  y 99-617 um.

## 2. Structural fix (opt-in)
* **RTL** `ot_hbm_su_static_data_store.sv`: `(* keep *)` on the g_wcopy registers. The ORFS ot_keep_regs.tcl hook then
  keeps every copy flop, as FLOW-FIX-0410 intended for declared copies.
  - yosys check (ORFS image, hook sourced): WCOPY=1 replicated bank has 270 DFF = 6 x (3 ks + 42 copy), vs 60 before.
    After `rename -wire` the names are g_read[k].g_wcopy.{wv,wa,wd}_q.
  - WCOPY=0 (default) elaboration is RTLIL-identical apart from the source-line numbers in auto names (CHECKED).
* **Generator** `gen_core_kit_hbm.py` (default off; with the flag off, the kit is byte-identical to REBAL-9 _m5w1g except
  the RTL copy, CHECKED by diff -r):
  - `--macro-reg-guide SCOPE [--macro-reg-guide-um 15]`: one INCLUSIVE GPL guide region per static macro `<P>.u_m`,
    holding the instances under `<P>.SCOPE.` (the column's own copy flops). The box is the macro bbox grown 15 um and
    clipped to the core. Overlapping boxes are cut at mid-gap, so all guides are disjoint.
  - `--relay-reg-guide FILE`: a guide box for each relay register group, centred on the plan point that minimises the
    longer of the pin->relay and relay->macro hops (L1, 5-um grid, clear of every macro guide).
    results/.../relay_lanes_canon.json lists 12 groups (wd_pin / wa_pin / w_pin x 4 banks): data, address and valid
    pins sit at different x in the plan.
  - macro_reg_guide.tcl (PRE_GLOBAL_PLACE, at the end of face_flops.tcl) creates the regions and fails closed when a
    guide has no member or a fill >= 0.80. macro_reg_guide_release.tcl (PRE_DETAIL_PLACE) removes them before DPL.
    This is the PATH-KV-ASTK2 zone_fence form. macro_reg_guide.json records the spec in the kit.
  - Tests: test_macro_reg_guide.py (3) + the hbm_arch_cores suite (25 PASS).

## 3. Estimate before build (UNCHECKED analytic)
Repeated wire 1.0-1.15 ps/um (REBAL-9 chain: 695 ps over the bank2 broadcast). Hop overhead = clk->q 66 + setup ~25 +
uncertainty 60 = ~151 ps, which leaves ~680 ps for wire, a reach of 590-680 um.

| hop | longest (um) | estimated slack (ps) |
|---|---|---|
| copy -> own SRAM (wd_in on both macro edges, <= 95 + 41 um) | ~140 | >= +300 (incl. 87 ps macro clock lead seen in REBAL-9) |
| relay -> copies, bank0/1/3 | 370-500 | +105..+310 |
| relay -> copies, bank2 (sink minimax bound) | 538 | +63..+144 |
| write_v pin -> w_pin relay, bank3 (pin at the SW corner) | 575 | +21..+107 |
| without relay guide, wd_pin at the pins (REBAL-9 form) | up to 791-911 | negative |

Verdict: the estimate passes, so build. bank3 write_v is the thinnest hop; its pin position is a die-plan item.

## 4. Builds (intel2, ot-run --mem 32, GOAL cts)
* `_c20ek2m_m5w1gr` = keep + copy guides + relay guides (**candidate**), KIT_PREFLIGHT PASS 0.
* `_c20ek2m_m5w1gk` = keep + copy guides only (A/B arm: shows the relay effect), KIT_PREFLIGHT PASS 0.
* chain_r10.sh collects 3_place (TT ideal-clock STA + render) and 4_cts (propagated TT STA + render), writing
  post_{gr,gk}/status, sta_*.log, *.png. sta_r10.tcl reports per hop: relay_D / copy_D / sram_wd / sram_waddr / sram_wce.
* Synth CHECKED (both kits, 1_synth.v): 42 copy flops under every one of the 24 columns = 1008 (REBAL-9: 168).
  Next stages in the kit chain: face_guard/port_bind, LEC (~66 min), floorplan, place, CTS, post-CTS hold gate.

## 5. Successor steps
1. post_gr/status shows 3_place: VIEW post_gr/3_place.png. Copy flops should sit inside their dashed boxes, and the
   relay groups at their points. Read sta_3_place.log HOP lines. Post a GEOM REQ [HBM-CORES-REBAL-10 lanes__canon m5w1gr]
   with the render.
2. 4_cts: sta_4_cts.log (WNS/TNS/NEG, CLS, HOP, MULALL, reset) and hold_gate.log. Compare with gk (relay A/B) and
   REBAL-9 (-124.3 / 903).
3. Enqueue the finish (intel2 enqueue.py --die hbm --type ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77
   --kit intel2:<gr kit> --src claude/hbm-cores-rebal-10-1028@<sha> --geom REQ --geom-ref "<GEOM REQ tag>" --mem 32
   --cells 330000 --lane HBM-CORES-REBAL --goal finish --mode trial). Do this ONLY after the hand CTS run has ended,
   so the autopilot never runs it twice. The autopilot route then gives signoff.py + routed LEC; export the view with
   export_view.py (provenance.json, pin file plan_pins.json).
4. READY ROOT-MERGE for this branch: RTL keep + opt-in generator guides.
