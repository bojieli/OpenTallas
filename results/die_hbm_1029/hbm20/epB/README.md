# DIE-HBM-20-EPB (2026-10-29): hfd_ep_static variant (b) WIDER SLOT (COORD 13:38, parallel to the tx/rx split)

Same RTL, same synthesized netlist (ep_my kit's synth reused: no RTL change), no M6 (kit layers M2-M5). Diagnostic
core probes on epyc2 `/srv/opentallas-scratch2/claude/die-hbm-20/epB/kitB{1..4}` (floorplan + place, docker
openroad/orfs:asap7lock, 24 GB cap) + AUTO-GEOM `tools/autopilot/geom_check.sh` (GRT 50 it, M2-M5, adj 0.25) in
`rev/B{1..4}`. Plan candidates on intel1 `/srv/opentallas-scratch2/claude/die-hbm-20/plan/epB{1,3,4}`
(cp -al of d16k_q2L 0b7b966cbaf2 + epb_plan.py), checks `.../chk/g0{,c}_epB*`. Numbers CHECKED from the named files
unless marked; area/track estimates are arithmetic (UNCHECKED).

## Estimate (before build)
- SRAM ot_sram_1r1w_64x512_m1_r2c2 171.288 x 77.784, OBS M1-M4, M4 pins on BOTH vertical edges: W (LEF frame)
  rd_out 512 + wd_in 266 + clk/ce/addr 15 = 793 "heavy"; E wd_in 246 + w_mask_in 512 + rr_/cr_ 34 = 792. In the
  synthesized netlist w_mask_in / rr_* / cr_* are ALL one tie net (_17943_) -> the E side carries only wd_in 246 +
  ties (CHECKED, 1_synth.v).
- Root cause of the current 241.92 x 397.44 failure (GEOM-61): one SRAM column, heavy+light edges both need logic
  but only M5 (vertical) crosses a macro -> two disconnected 31-um strips; the whole tx path (613+613+512 regs) lives
  in the W strip.
- 2x2 arrangement: column A MY, column B R0 -> both heavy edges face one mid channel (read mux + output regs between
  the two banks of a bit slice: row0 = mem[0] of block 0/1, row1 = mem[1]); light edges face thin outer channels;
  logic band S. Pins: sd_tx / sd_rx / sd_st + controls on S (SerDes u_lk below the EP in all 5 types), tx_frame W,
  rx_pin_flit E (unchanged faces -> no new core_faces risk), 13 status pins N.
- Vertical demand is free over the macros (M5 not obstructed); the binding resource is horizontal escape from the
  mid channel (M2/M4 only between macros) -> row gap and the mid-channel mouth into the S band.
- AUTO-GEOM limits that size the slot: macro share >= 50 % (else fill >= 0.15 / empty <= 0.5 FAIL: std area only
  ~5.2k um2 -> a 2x2 slot cannot reach 15 % fill), partial_face (< 4 pins/um -> W/E pin pitch 0.288), clock_reach
  <= 220 (leaf islands in the outer channels + mid channel).

## Probe results (AUTO-GEOM, CHECKED rev/B*/auto_geom.json, renders VIEWED)
| shape | outline | macro % | GRT ov (50 it) | FAIL rules |
|---|---|---|---|---|
| ep_my (current, KITS-18) | 241.92 x 397.44 | 55.4 | 255,546 | r2r 539.9/59, channel_h/v, col_v 2.03, grt |
| B1 2x2, S band 116 um, mid 42 um | 432.00 x 319.68 | 38.6 | **0** | fill 0.057, empty 0.77, partial_face 2 (0.192 pitch), channel_v 1.23, col_v 1.18, clock_reach 256.8 |
| B2 2x2, mid 29 um (uninformed parallel) | 414.72 x 302.40 | 42.5 | **0** | fill, empty, partial_face 2, channel_h 1.09, channel_v 1.28, col_v 1.15, clock_reach 248.4 |
| B3 macro>=50 %, S band 43, mid 50.5, outer 21.6, W/E 0.288 | 444.96 x 237.60 | 50.4 | **0** | channel_h 1.736 (est.) at the 13-um row gap, x 252 |
| **B4** = B3 + row gap 21.6, outer 12.96 | **427.68 x 246.24** | 50.6 | **0** | channel_h 1.081 (est., hard 1.0) at the mid-channel mouth (y 40-47, x 242) |
B4 passes r2r 362.7 / r2r_count 0, pin_reg_max 10.4, partial_face 0, pin_density 3.5, clock_reach 168.2, fill/empty
INFO (macro-dominated), channel_v 0.714 / col_v 0.687 WARN (GRT 0). Remaining FAIL is the placement-estimate
channel_h (1.081 vs hard 1.0) with GRT overflow 0; next informed step (not built): S band +4.32 um or the mid-channel
mouth widened (B column +4.32 E), keeping macro share >= 50 %.

## Plan delta (epb_plan.py, opt-in candidate, not adopted)
6 hfd_ep_static instances in 5 types: outline, pins_file (new per-shape table = the probe kit's plan pins), contents
outline, NW_io/NE_io u_ep_N0/N2 origin x -> 112.32 (B1/B4) / 103.68 (B3) on the 8.64 lattice (432-um core inside
the 648-um partition), clock_entries.json + clock taps xy (centre entry = probe island 0), internal stations of the
u_lk <-> u_ep links (EP end -> S-face port centroid, Z route, hops <= 360), core_macros.json entry.
- G0 PASS (B1, B3, B4); G0C 8 ERRORs = inherited d16k_q2L q_hub set exactly, 0 new; EP core_faces 2 -> 0
  (q_spb0 / q_spb0__physical_v1 u_ep_S0 sd_tx W-face error gone; also the 3 EP sd_rx perpendicular WARNs gone).
  Only remaining EP findings = inherited core_pg WARNs (CHECKED chk/g0{,c}_epB*/g0_report.json).
- Cost: core area 96,150 -> 105,312 um2 (+9.5 %) for B4 (UNCHECKED arithmetic); width 241.92 -> 427.68.

Files: mk_epb.py (kit reshaper), epb_plan.py (plan delta), run_place.sh, auto_geom_B{1..4}.json, B{1..4}_auto_geom.png.
