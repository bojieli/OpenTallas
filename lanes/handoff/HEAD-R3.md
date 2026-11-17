# HEAD-R3 handoff (Fable), successor of HEAD-DIE-R / HEAD-TYPES-R2 / FABLE-FIX-HEAD-CTL / FABLE-FIX-HEAD-SERDES
Started 2026-11-17 05:28 PST. Client logs: intel2 ~/head-r3-logs/. Nothing deleted, no kills.

## Live jobs (collect; R-MINIMAL = DRC 0, routed TT >= -42, internal reg-to-reg FF hold >= 0)
- hd_ctl: DONE, SIGNED + exported (see Collected). Codex hei1 route (E7 unit3887706) had FAILED DRT-0206 on the unchanged net
  cland_fwd_fclk_out_b7_tx_o (legacy pin-contact class); failure kept at E7 mchk_local/hei1. Successor hei1r2 on E9 (same
  path; E7 was disk-refused) re-routed that net with the 23 HB4 nets (hold_eco_internal_route_extra.tcl, OT_HEI_EXTRA_NETS).
- hd_st_n3_turn 192-pad recovery: hei1 (E8 unit2826139) NOT SIGNED, DRC 0, TT +43.85, one new internal end
  u_ft_u1_s5/q[366] FF -1.035. Codex hei2 (1 HB4) E8 unit oth-ubuntu-3532638-1794921683, log ~/hdr/fclk_hei2_route_codex.log,
  out E8 head-die-r/fclk_recovery_u1/hei2/signoff/signoff.json. Custom base (run_route_signoff.sh) -> export from hei2/run/results/...
- BUF64 coupon: route E7 unit104774 exit 0, validate_route.py DRC 0 (130 nets). export/run_export.sh FAILED (script bug:
  libs.txt names /work/macros/*.lib, kit not mounted). Successor export_r2/run_export_r2.sh (kit mounted ro, then
  pair TT/FF into buf4_64/pair_routed_r2) queued on E7, log ~/head-r3-logs/buf64_export_pair_r2.log. Coupon only: no type sign-off.
- hd_serdes sd9f: E7 unit3729170 DRT ended 06:45 PST at 64 iterations with 28 DRC (19 Short + 9 Metal Spacing), ALL on M2
  against macro/cell obstructions, mostly clk_t*_tb0_n2 clock-tap nets and u_rrl_*/_1_ (same class as he12h drc2: HEAD-HE12H-DRC.md).
  Report E7 fable-fix-head-serdes/sd9f_lane/sd9f/gen/hd_serdes/run/reports/asap7/dp_hd_serdes/base/5_route_drc.rpt. The kit
  continues to finish + sign-off by itself (will be NOT SIGNED on DRC); routed TT not yet read (GRT TT -22.17).
  NEXT: read signoff TT/internal FF; if timing passes, one targeted M2 obstruction ECO on the 28 markers (he12h drc2 recipe),
  re-sign, export. sd9e (E10, TT -53.04 fallback) untouched.
- E7 scratch2 hit 0.4 GB free at 05:55 (ALERT posted); 100+ GB again at 06:00.

## NF15e corridor decision (model, numbers)  -> "NF15f"
Evidence E10 /srv/opentallas-scratch2/claude/head-die-r/nf15e_e10/hr3/ (alloc_r4.py sha f4cce221, w_*.json; inputs unchanged:
plan 7dc26079 = corridor +120.96, 46,192 bit edges, 40,670 driver hypernets; band y 490..790.96; 405 um full-rectangle reach).
Root cause is NOT raw track count: worst cut x=980 holds 8,627 tracks vs 5,710 mandatory (66%) / 8,561 full-rect (99.2%).
The trunks fail because stage hops span 300-389 um in x, which leaves a 9-45 um legal y window per net under the 405 um
reach, and thousands of nets share the same window.
| option | unassigned trunks | worst cut (full-rect / mandatory) |
| corridor +120.96 as is | 6,281 | 99.2% / 66.2% |
| more tracks only: +60.48 growth | 6,281 | 78.8% / 52.5% |
| hop halving only (relay rank, +1 cycle per relayed hop) | 1,617 | 99.2% / 66.2% |
| hop halving + all M8 granted (no growth) | 0 | 77.6% / 51.8% |
| hop halving + growth +34.56 | 79-452 | 86.4% / 57.7% |
| **hop halving + growth +60.48 (10 word classes)** | **0 of 40,670** | **78.75% / 52.5%** |
| same, 8 existing-knob classes only | 74 (one g_kl word) | 78.75% / 52.5% |
DECISION: both levers, neither alone closes. (1) Hop halving with cycles through the existing LEP stage knobs:
PIN 4->6, POUT 4->8, TXI 16'h1221->16'h2442, KTX 16'h0000->16'h1111, KRX 16'h1330->16'h2660 (15,031 relay FF);
the RX head -> MLWD/RID word (2,208 FF) needs one head register rank in u_lep or a re-site of the KRX tail anchor (74 bits
left without it). (2) Corridor growth +60.48 more: upper pair cores +181.44 total vs final52, type 1892.16 x 1408.32,
die height 17556.48 -> 17737.92 (+1.03% area). No core reshaped. M8 grant widening rejected (takes 2,400 die M8 tracks
over LEP, breaks the locked grant c5011c83). Time-multiplexing rejected (new RTL protocol; stage knobs already exist).
Relay sites per word class: relay_hops in hr3/w_final_knobF_g60.json (sha d8418d79), e.g. PIN s1->s2 column x=1649
y 513..780, POUT s0->s1 x=1354, KRX1 x=537.5/822.5, KRX2 x=560/880, TXI1 x=774.5, TXI2 x=752.
Scope: horizontal trunk witness only; vertical branches, vias, pin access, clock re-reservation not qualified. No route credit.

## NF15f functional compose + gates: PASS (06:20 PST)
E10 hr3/compose_f1.py + run_f1.sh: stage/prep_f1 = copy of gated prep_r2 (final75r2, b112d9ad) + the stage tuple
PIN6 POUT8 TXI 16'h2442 KTX 16'h1111 KRX 16'h2660; 34 new stage groups are FUNCTIONAL PLACEHOLDERS on existing anchors
(same tag/rect). Plan sha 3210bf1f1390a8c3a1aab968de8c7bd7e6ff452f3783be2ae3d2f336f90b60f9, +16,413 state bits.
E10 unit oth-ubuntu-1494505-1794924335 exit 0, gates_f1/: receipt rc 0, kit RTL PASS, HEAD_DIE_PORTBIND PASS
(module_missing 0, tie_audit PASS), cohort 26/26, LANE_ASBUILT 329/329 delta {}, G0 0 errors / 206 warnings.
Leg prices stage/prep_f1/native_provider_calendar_nf15f.json (PIN +2, POUT +4, TXI +1/+2/+2/+1, KTX +1 each, KRX +0/+3/+3/+1,
forward and credit). The token/compiler calendar for this tuple is NOT regenerated. This proves the cycle tuple only.

## Collected 06:1x-06:3x PST
- hd_st_n3_turn hei2: SIGNED R-MINIMAL, DRC 0, TT +43.88, internal FF hold 0 (138 output-port ends -12.85 on d1_o /
  rst_start_raw_* advisory, parent). Exported BOTH s81_head/hd_st_n3_turn__nf15_fclk192_hei2_1117, ODB sha
  0765cc9e970cf7df77f4ee9ce94d353b9f877a2475e3768014061372cbd57541; INDEX rows on rtx-pro + AGIdock. Final render not re-looked
  (1 HB4 after the reviewed hei1 image). NEXT: swap into die STA (E7 head-die-r/nf15c_real4/run_nf15c4.sh), remeasure ring hold.
- hd_ctl hei1r2 (E9 unit3558344): SIGNED R-MINIMAL, DRC 0, ANT 0, TT -4.82 (14 ends, achieved 837.82 ps), internal FF hold 0
  (complete census; 308 port ends -11.40 advisory, parent h_rx_i/lepk_i0). final_placement LOOKED. Exported BOTH
  s81_head/hd_ctl__nf15d2_mchk_local_hei1r2_1117, ODB sha 835ee68007cbd7c4ca8ab3bddd95d9014421e03aa2caa11598c8c6ed3856e068.
  NEXT: stand-in swap in die STA. E9 copy of kit_hd_ctl + hei1r2 can go after the die STA swap (ot-delete only).
- BUF64 coupon: export_r2 alias PASS (E7 buf4_64/export_r2/6_final.*), routed pair tE1o0->tE0b1 hold TT +386.45 / FF +106.09,
  2 endpoints, 0 negative (buf4_64/pair_routed_r2). Model said 171 TT / 115 FF margin. Coupon only; phase contract owner decides.

## Not done (next owner)
1. Geometry event NF15f: apply +181.44 to LEP type (2 upper cores, N-face pins, clock taps/reservations, plw_s2), parent
   die (6 north hd_serdes + PHY domains + die outline 17737.92, IO/bumps/PG/M8 guide), place the relay anchors at the
   witness columns, rerun alloc_r4 on the composed plan, then fresh clock GEN (GEN3/graft method) and reset census.
2. Reset seams (714/530) and BUF4 hold model: untouched by this lane. Mesh finite PG (141 -> 7 with localtracks f3ee5447): untouched.
3. Pending merges listed by Codex (HEAD localtracks f3ee5447, BUFdelay 55fb36df) were not touched.
