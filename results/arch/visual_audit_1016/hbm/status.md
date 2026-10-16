# HBM visual-audit status: P0/P1 closure-blocking findings
Updated 2026-10-16 02:00 PT by VIS-HBM. Sources: closure-loop verdicts, owner logs and replies. Details are in findings.json.

States:
- **fixed-routed**: the fix is routed and the cited metric improved.
- **fix-in-gate**: the fix is in a gate, route or regenerated case, with no verdict yet.
- **fix-planned**: the owner accepted it, but no kit exists yet.
- **not-started**: no geometry change exists.
- **refuted**: owner evidence shows the finding, or its fix, was wrong.

| id | sev | finding | owner | state | evidence |
|---|---|---|---|---|---|
| D1 | P0 | d2 die clock buffers placed inside SM outlines (15,671 of 53,087); 31.6 ns model insertion from one root | H-DIE | **fix-in-gate** | Root cause confirmed by H-DIE (die_case carved the SM reserved channels out of the clock obstacles while the SYNTH SM views block the whole outline). d2 KILLED. Fix: full-outline obstacles, grid 20 -> 10 um, span 420 -> 200 um; case being regenerated in /tmp/claude-1000/hdie0030/d3clk before d3 uses it |
| D2 | P0 | 124.8 mm2 empty: ~33 mm2 corner voids beside the LK/EP column, 4 x 240-um band slivers | H-DIE | **fix-planned (partial)** | sfucore_<q> slots of 763.56 x 1936.44 granted in the band gap (main 818f005b6); SU bank slot 390.96 -> 369.36 (-1.67 mm2). The corner voids beside the EP column are still unused |
| D3 | P1 | SM_HBM relays up to 15.3 mm / 31 stages; put SMs next to their PC row | H-DIE | **refuted (as proposed)** | H-DIE measured: (a) svc groups in the band middle 117k vs 50k bit-mm -> reject; (b) v8 columns remove the SM_HBM stages but VM_RING 11 -> 15.5 and COLL_EP 13.8 -> 20.8, and need M8/M9 or 727-817 mm2. v5 kept unless die GRT shows SM<->PC congestion |
| T1 | P0 | xload ctl: pin-bound 12% fill, 10,786 pins, diagonal worst path (TT -92.5, DRC 4) | H-SM | **not-started (geometry)** | cl2e RTL lookahead for lane_en -> bsel; no cl2e gate or route yet; the 4 DRCs (corner pins) went to ROOT |
| T2 | P0 | bdring: clk on W face, logic and pins E | H-SM | **not-started (geometry)** | cl2e removes an output inverter; a clock-face move only if cl2e native fails |
| T3 | P0 | strap q0-q3: centred SRAM stack, ring logic, paths wrap the stack | H-SM | **not-started (geometry); RTL-only fix REFUTED on q0** | strap5 q0 (2c0df5054) NEEDS_RTL TT -114.94 / FF +2.29, worse than strap4hookfix q0 -62.49; q2/q3 strap5 in ECO. q1 strap4hookfix CLOSED +18.72 |
| T4 | P1 | VM calendar: centred SRAM splits logic, clock wraps under the macro | H-HARDEN | **fixed-routed** | xcap cce3264d2 CLOSED TT +45.93 / FF +24.17 / DRC 0. Routed native PASS (main results/rtl/hbm_harden_0030/calendar_x_native.json, checked): L 222.0 -> 179.0, C 206.2 -> 133.0, spread 92.8 -> 37.2 ps |
| T5 | P1 | COLL vmwrite: clk at the N end of a 389-um strip | H-HARDEN | **fix-in-gate** | v5 midclk (mid0030-8e0909ea1) RUNNING |
| T6 | P0 | SM tile rp3: W/E 3,705 pins each in 203 um (18.2 pins/um) | H-SM | **not-started** | rp3 route RUNNING on the old pin plan; owner noted it for rp4 |
| T8 | P1 | pc_ctrl_cfg (x128): centred SRAMs, C-shaped logic, empty E strip | H-PCCTRL | **fix-in-gate (partial)** | H3 d47e7b45c: outline 185.76 -> 164.16 square (util 0.52), but the macros are still centred (20.6-um channel); its real blocker is TT setup -37.9 on the ref_c -> write-ACT path; CTS gate running |
| T9 | P1 | SU bank6 / reduce: low fill | H-SU | **fixed-routed (bank); refuted for reduce** | bank r12 369.36 x 151.2 CLOSED TT +111.89 / FF +10.49 / DRC 0, routed native PASS L180.2 / C119.6 / spread 56.7 (main native_audit_r12.json): -5.5% = -1.672 mm2 over 512 banks (my ~20% estimate was too high). Reduce: 4 per die, 0.036 mm2 -> no action |
| T12 | P1 | LK EP: SRAM pins face inward across a 47-um channel (route 2: 12 overflow edges) | H-LKEP | **fix-in-gate** | route 3 (e4e436536, 21.6-um row channel) passed trial GRT with overflow 0 and is RUNNING. The compact variant cmp1 (91b2723d4, 434.72 x 224.64, my height cut) hit EARLY_FAIL_CONGESTION GRT-0116 again -> my compact suggestion is not confirmed |
| R2-1 | P1 | LK EP route-3 kit clock insertion 444.9 / spread 109.6 | H-LKEP | **refuted** | (1) The 300/80 limit applies only above 15k sinks (7,194 here). (2) Native launch/capture are O-R / S+R with R = boundary mean insertion (native_pin_audit.py), so high but uniform insertion is not a native fail |
| T7 | P1 | smh_bdc d62 one-sided IO | H-SM | withdrawn | d62 leaf re-harden dropped |

Totals:
- fixed-routed: 2 (T4, T9 bank)
- fix-in-gate: 4 (D1, T5, T8, T12)
- fix-planned: 1 (D2)
- not-started: 4 (T1, T2, T3, T6)
- refuted: 3 (D3 as proposed, T9 reduce, R2-1)
- withdrawn: 1 (T7)

The P0 blockers left without a geometry fix are all H-SM: T1, T2, T3 and T6. T3's RTL-only route has now failed on q0 (-114.94 ps).
