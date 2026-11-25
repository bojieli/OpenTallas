# QC-STAV2-F436 (owner slw_st_a_v2__clf4365a62; parent QC-ALLFIX)
Base C1o v13 aa3a14fb7484 (epyc12 QC-C1O-COMPOSE/c1o_v13/plan_c1o.json, sidecar a142fe516f24). Row = C1p key-patch on this one type.
Work dir: epyc12 /srv/opentallas-scratch2/claude/QC-STAV2-F436/  (local scratch f436/ for analysis only)

## Kit / attempt census (11-25 06:5x)
| kit | plan | host | stage | numbers | live | class |
|---|---|---|---|---|---|---|
| ABSTRACT-EXACT probe_qc (OT_PROBE_THROUGH, goal place) | s29q103S4Q9N46R6V4 (kw43 V4 private QC-STA-PROBE) | epyc12 .../abstract-exact/probe_qc/gen/slw_st_a_v2__clf4365a62 | place done; renders 12:15 FAILED, 13:30 + 14:00 SMELL-STRUCTURAL | GP WNS -571/TNS -260ns; DP -181/-205ns; ideal top-50 -343; drv slew 27317 cap 38 | no | STRUCTURAL (floorplan) |
| VIS-REOWN census kit (11-24 19:07) | pre-C1n | epyc2 | sign-off read | TT -124.89, DRC 72, pair skew 336/279; NOT SIGNED | no | clock skew + floorplan |
| W5 placed_scan (QC-FEV1FLAT-RE) | dm2 64729ba8d8bb | epyc12 | placed_scan | lpad_rs_s1 479um; lob_x_fe_o 611um; bin_x_hc1 4b 608um | no | reach/station residue |
| C1o v13 | aa3a14fb7484 | - | HELD (C1p SINKBINS + FEV1-FLAT) | v13 strict bind DIED rc1 (HARD_CORE_PARAM_WRAP, tree class, COMPOSE re-bind ETA 08:45) | - | - |

## 11 problems (STAGE-PLATEAU 06:27, place-gp-1125-1400) -> cause -> fix -> owner
| # | problem | cause | planned fix (C1p row keys, this type) | owner |
|---|---|---|---|---|
| 1 | W third (x<230) + NE quadrant empty, fill .205 | macros packed E; outline = plan slot | keep outline (die seams/pin windows unchanged: outline cut = die re-floor, slower); move region column W onto one x, btab SRAMs inboard into freed middle; NE gets btab/x_st_b logic | QC-STAV2-F436 |
| 2 | E wall: 4 SRAM + 3 cland y17-842, 20um to E pins, RUDY 91 | SRAM stack between E pins and logic | hard_cores: SRAM stack moved inboard (W of x450, beside region column), >=60um clear corridor behind E face north of the clands | QC-STAV2-F436 |
| 3 | cland abutment hw_ctl/tw_data/x_ctl_fw (0/4um) | stacked, no channel | hard_cores: >=20um channels between the 3 E clands (within pin-window tolerance) | QC-STAV2-F436 |
| 4 | SRAM pockets (30um gaps fill with cells) | gaps too narrow | SRAMs abutted in 2 back-to-back pairs + one wide channel; placement blockage in residual gaps | QC-STAV2-F436 |
| 5 | W-face trunk x~220 y350-1100 | one bus runs column height to every region W face | regions on one column with W third used: per-region registered entry from nearest edge (relay_sites re-derived for moved cores) | QC-STAV2-F436 |
| 6 | staggered region column x 233/233/242/268 | hand offsets | one x for u_r0..r3, uniform pitch | QC-STAV2-F436 |
| 7 | bottom pinch: r0 8um above S cland row | region on S cland row | lift r0 >=40um above rs_s0/rs_s1/x_fw_ctl clands | QC-STAV2-F436 |
| 8 | no macro halo (regions/clands) | halo unset | halo_um 4.32 on every hard core (regions + clands), as on SRAMs | QC-STAV2-F436 |
| 9 | pin clustering (top pins x0-480, bottom bar) | pins packed by bus | die-level pin windows are seam contracts: NOT moved in this row; internal: region/cland placement opposite each bus window instead | QC-STAV2-F436 |
| 10 | run_in/rst_in 1 flop -> ~700 srl/rrl, 2685um, -106ps | single-source pin entry | reset.pin_root_copies signals [reset,start], max_loads 48, one copy site per load group (0 cycles, reset_tree.py existing key) | QC-STAV2-F436 |
| 11 | u_bin_x_hc1_i q[0..3] -> INVx1 886ps -> pd8 tap flops (-343) | one bin flop drives the whole x_hc1 4-bit pad-tail trunk fan-out | same 4-bit x_hc1 pad-tail trunk as FEV1FLAT-RE bin_x_hc1 pd7 t_9 seats: trunk seats + per-group bin copies in the land_pad_tail_split generator row | QC-FEV1FLAT-RE (generator row); F436 composes + checks no key overlap |

Key-conflict rule with QC-FEV1FLAT-RE: F436 touches hard_cores, halos, reset.pin_root_copies and the relay_sites / internal_stations / ft regs re-derived for moved cores; FEV1FLAT-RE touches x_hc1 trunk seats (u_pd*_x_hc1_i_*) + x_fe_o stations. Overlap check by key diff before ROW-READY.
Compose order with QC-SINKBINS: SINKBINS (sb_row.py) moves clock sink bins / taps and re-taps reset by position, so it must see the moved macros. Order: F436 row first on this type, then QC-SINKBINS re-runs sb_row.py on F436's output for clf4365a62 only (no shared hand keys).

## Log
- 06:3x CENSUS posted.
