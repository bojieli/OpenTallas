# FABLE-PD-HEAD-1115: hd_spn (s81_head) repeat DRT-0255 -- PD review

Reviewer FABLE-PD-HEAD-1115, read-only. Kit read: epyc10
/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF6/items/hd_spn/attempt_3/gen/hd_spn
(job 25a0f9b7dd12, plan head_rp21z20NF6). DB query copy + outputs: epyc10 /srv/opentallas-scratch2/claude/fable-pd-head-1115
(q.tcl, q.out, 5_1_grt.odb copy 528 MB -- deletable). Every number is tagged MEASURED or INFERENCE.

## 0 Answers

1. CAUSE (MEASURED): the M7 boundary pins of hd_spn sit UNDER the tile's own M7 PG straps. The pin generator keeps M7 pins
   out of a band at 4.32 +- 0.48 mod 8.64 (schema.py PART_PG_BANDS "M7": (8.64, 4.32, 0.48)), but the kit pdn.tcl draws the
   M7 pair at 0 mod 8.64 in the type frame (offset 4.128 counted from the CORE edge 4.32: VSS 181.104-181.392, VDD
   181.488-181.776, pair centre 181.44 = 21 x 8.64). CORE_MARGIN 4.32 = half the M7 pitch, so the band table and the straps
   are exactly half a pitch apart: the generator protects 0.96 um where no strap is and allows pins where the strap is.
   M5 and M6 (pitch 4.32 = the margin) are not affected: 0 pins under their straps.
   b_i[67] = M7 pin x 181.648-181.680, y 0-0.192, inside the VDD strap x-range; the strap starts at y 4.311. Its GRT guide
   runs M7 0 -> 17.1 um in gcell column x 181.26-181.83, which has 0 DRT-legal M7 tracks above y 4.311. DRT leaves the
   guide, and in the 1st iteration the boundary pin left at (182.400, 7.980) has no legal grid edge -> DRT-0255.
   Not pin density, not off-grid, not a keepout: pins are on track (M7 0.032 + 0.064 k), 971 M7 pins on 587.52 um.
2. Setup -108.51 is NOT this family (MEASURED from the 11-14 04:57 HEAD-99 line): one endpoint, output export
   rst_start_raw_42 through a 12-buffer chain, on the old plan rp21z4 attempt_2, which routed DRC 0. On NF6 attempt_3
   GRT-stage TT setup WNS is +26.32 ps, 0 violators (MEASURED, grt_policy.json); routed timing on NF6 is UNMEASURED.
3. Fix = turn on the existing OT_PG_DIE_PHASE=1 (+ OT_PG_TRACK_TRUTH=1) for hd_spn and the other HEAD types with M7 face
   pins; no pin move, so no plan event. Rows, stop list and owners in sections 2 and 3.

## 1 Measured

- Failing worker (maze.log of attempt_3, 181,519 grid nodes, box (182.400, 6.840)-(186.390, 10.830)): source AP
  (182.624, 10.830) M7 reaches 180,729 nodes; 790 unreachable = 3 off-track M8 lines (y 7.968, 7.980, 10.272) + one M7
  node (182.400, 7.980). The only via on those lines is at (182.400, 7.980) M7<->M8. y 7.980 = 2 x 3.990 = an iteration-0
  box edge; x 182.400 = the iteration-1 box edge. So iteration 0 left b_i[67] metal on a box-boundary line, 0.57-0.96 um
  right of its guide. MEASURED. That the iteration-0 wire ran on M8 along y 7.980 is INFERENCE (no routed DB is written
  on DRT-0255).
- GRT DB window x 180-187, y 0-19 (openroad read via ot-run, unit oth-ubuntu-1544559-1794770933): PG M7 VSS
  181.104-181.392, VDD 181.488-181.776, y 4.311-2069.289; PG M5 VSS 183.444-183.564, VDD 183.636-183.756; PG M6 pairs at
  y 6.144/6.528, 10.464/10.848, 14.784/15.168; obstructions other than M8: 0 (7,680 M8 grant rows). b_i[67]: no NDR,
  one sink hold75154 (HB4xp67) at (181.44-181.82, 19.71-19.98). Guides: b_i[67] M7 (181.26, 0)-(181.83, 17.10);
  b_i[65] M7 (180.69, 0)-(181.26, 10.83) (pin 181.136-181.168, inside the VSS strap). MEASURED.
- Pins (io.tcl, 6,158 signal pins): bottom 976 M5 + 971 M7, top the same, left/right 566 M4 + 566 M6 each. M7 pins on the
  N/S faces under an M7 strap: 65 overlap + 21 within spacing per face = 172 of 1,942 (8.9 %); M5 under M5 straps 0;
  M6 (E/W) under M6 straps 0. Overlap is MEASURED; "within spacing" uses M7 spacing 0.032 = INFERENCE. By the generator's
  own +-0.48 band: 218 M7 face pins lie within 0.48 of 0 mod 8.64 and 0 within 0.48 of 4.32. MEASURED.
- Generator (epyc7 /srv/opentallas-scratch2/claude/kw45/src_head_rp21z_pgcaplec_c327/tools/die_plan): schema.py:2785
  PART_PG_BANDS M7 (8.64, 4.32, 0.48); schema.py:2932 uses pg_blocked(ln, c) with no core-margin term for port bit
  spreading. gen_phys.py:987/1018 test both origins (0 and 4.32) but only for snap / face tracks. gen_phys.py:1889
  pdn_die_phase (OT_PG_DIE_PHASE=1) re-offsets the stripes to the type frame: M7 offset 4.128 -> strap pair at
  3.984-4.656 mod 8.64 = inside the band. M5/M6 unchanged by it (4.32 is their pitch). MEASURED from code; the DIE_PHASE
  result on this kit is INFERENCE (not built).
- PG flags: attempt_3 and attempt_4 config.mk carry no OT_PG_* line; 5_1_grt.log has no OT_PG_TRACK_TRUTH /
  OT_PG_CELL_KEEPOUT print. kit_wave.json s81_head die_gen_env has none of the 4 flags and OT_RFLOW=0; item_env hd_spn =
  OT_IO_HOLD, OT_GEN_M8_GRANT, OT_PLACE_MAX_FANOUT only. COORD's 11-15 00:2x order named hd_spn, but the 00:25 revert
  kept the flags on 10 QC/S81 kits only. MEASURED.
- attempt_4 (kw-s81hea-hdspn-4-69523): config.mk and io.tcl byte-identical to attempt_3 (diff empty, cmp equal).
  MEASURED: an unchanged relaunch.
- DRT iteration 0 of attempt_3: 23,560 violations; wire length 5.33 M um of which M3 4.50 M um (84 %), M5 0.106, M7 0.017;
  GRT M3 usage 18.7 %, M4-M8 each < 0.7 %, 0 overflow. MEASURED.
- Earlier hd_spn DRT-0255: 11-13 u_spo.g_c[0].x_q[61] box (38.76, 1870.17), 11-15 01:23 u_spo.i[366] box (70.68, 1878.15)
  with source AP (74.670, 1881.720) M8, also in the 1st iteration. Internal nets near y 1875, not face pins. MEASURED
  from logs. w3u_i[427] is hd_ctl_n, not hd_spn.

## 2 Fix / levers

| # | Change | Numbers | Owner |
|---|--------|---------|-------|
| F1 | item_env hd_spn: OT_PG_DIE_PHASE=1, OT_PG_TRACK_TRUTH=1, OT_PG_CELL_KEEPOUT=1, OT_PG_PIN_CHECK=warn; regenerate the kit fresh (stage_resume_off already lists hd_spn) | M7 straps move 4.32 um; 172 pins under straps -> 0 expected (INFERENCE); pins unchanged, so no plan event and no neighbour change | KIT-OPS-5 |
| F2 | Accept check before route: in the new kit, pdn.tcl M7 line must read -offset 8.448 (= (4.128 - 4.32) mod 8.64 from the core edge; pair at 3.984-4.656 mod 8.64 in the type frame) and the PIN_CHECK print must report 0 bad M7 pins | gate = 0 of 1,942 | KIT-OPS-5, HEAD-100 reads |
| F3 | Same flags for the other unsigned HEAD types with M7 N/S or M6/M7 face pins (hd_spn_end first: same b/au/ad face coordinates by abutment) | 17 eligible types | KIT-OPS-5, list from HEAD-100 |
| F4 | Die decision: M7 strap phase across abutment. A die-phase hd_spn has M7 straps 4.32 um off the straps of core-phase neighbours (9 signed types). PG continuity is advisory under the academic profile; record it on the open list, do not hold F1 for it | 4.32 um offset, 68 pairs per 587.52 um | HEAD-100 |
| F5 | Generator: schema.py:2932 should test both origins like gen_phys.py:987, or the band table should come from the kit PDN text, so a core-phase kit can never put pins under M7 straps again | 1 line | HEAD-100 -> a Sonnet fix lane, via merge queue |
| F6 | -108.51 ps: no action here; closed class on the old plan (reset export reach). Recheck routed TT on the first NF6 route | -- | HEAD-100 |

If F1 routes DRC 0, set OT_PG_PIN_CHECK=1 (hard) for HEAD. If DRT-0255 returns on an internal net with F1 on, that is a
different cause: send the maze.log and 5_1_grt.odb back for review rather than relaunching.

## 3 Stop list (must not relaunch unchanged)

- hd_spn attempt_4 kw-s81hea-hdspn-4-69523 (epyc10 .../head_rp21z20NF6/items/hd_spn/attempt_4): identical kit, same 172
  pins under straps. Cancel by exact unit / kit dir (KIT-OPS-5) and replace with the F1 kit. No kill by pattern.
- Any hd_spn or hd_spn_end kit whose config.mk has no OT_PG_DIE_PHASE = 1 line.
- No retry of 5_2_route from the attempt_3 5_1_grt.odb: its guides sit on 0-legal M7 columns.
- No knob-only forms (droute iterations, density, M8 grant changes): none of them moves a strap or a pin.

## 4 Not checked

- No build with OT_PG_DIE_PHASE=1 was run; the 172 -> 0 result and the DRT-0255 cure are INFERENCE until F2 and one route.
- The two earlier DRT-0255 on internal nets (y ~1875) were not traced: no maze.log kept for them. Whether they share this
  cause (guides in PG-illegal columns, the pg_track_truth class) is open.
- The exact iteration-0 wire of b_i[67] (layer, why it ran on a box edge) is not visible: no routed DB.
- Die-level M7 PG: whether die straps run over the tile seam above these M7 pins (a short at die level), and what the
  signed HEAD types did, was not read.
- M7 min spacing to a 0.288 wide strap (wide-metal rule) not read from the tech LEF; 0.032 assumed for the 21 + 21
  "within spacing" pins.
- Routed setup on NF6 and the 84 % M3 share (2 mm feed-through hops on the thinnest vertical layer) were not analysed.
- hd_spn_end and the shims were not measured; F3 is by shared face coordinates only.
