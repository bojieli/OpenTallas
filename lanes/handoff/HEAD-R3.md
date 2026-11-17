# HEAD-R3 handoff (Fable), successor of HEAD-DIE-R / HEAD-TYPES-R2 / FABLE-FIX-HEAD-CTL / FABLE-FIX-HEAD-SERDES
Started 2026-11-17 05:28 PST. Client logs: intel2 ~/head-r3-logs/. Nothing deleted, no kills.

## Live jobs (collect; R-MINIMAL = DRC 0, routed TT >= -42, internal reg-to-reg FF hold >= 0)
- hd_ctl HEI: Codex hei1 route (E7 unit3887706) FAILED DRT-0206: unchanged net cland_fwd_fclk_out_b7_tx_o "1 pin not
  visited" (legacy pin-contact class, same as n3_turn route_contact_r2). Failure kept at E7 mchk_local/hei1.
  Successor hei1r2 = same hei_insert.odb (23 HB4) + that net added to the re-routed set (private
  hold_eco_internal_route_extra.tcl, OT_HEI_EXTRA_NETS). E7 was disk-refused, so kit+inputs were copied to E9 same path
  /srv/opentallas-scratch2/claude/head-types-r2/mchk_local/{kit_hd_ctl,hei1,hei1r2}. E9 unit oth-ubuntu-3558344-1794922883,
  log ~/head-r3-logs/ctl_hei1r2.log; route -> fill/finish -> signoff.py -> hei1r2/kit_hd_ctl/signoff_hei/signoff.json.
  ROUTE_ATTEMPTED guards a repeat. If SIGNED: LOOK final render, export with rtx-pro ~/head-spe-export/ffht_export_v2.sh
  epyc9 hd_ctl__nf15d2_mchk_local_hei1r2_1117 <base> <signoff.json> "<note>".
- hd_st_n3_turn 192-pad recovery: hei1 (E8 unit2826139) NOT SIGNED, DRC 0, TT +43.85, one new internal end
  u_ft_u1_s5/q[366] FF -1.035. Codex hei2 (1 HB4) E8 unit oth-ubuntu-3532638-1794921683, log ~/hdr/fclk_hei2_route_codex.log,
  out E8 head-die-r/fclk_recovery_u1/hei2/signoff/signoff.json. Custom base (run_route_signoff.sh) -> export from hei2/run/results/...
- BUF64 coupon: route E7 unit104774 exit 0, validate_route.py DRC 0 (130 nets). export/run_export.sh FAILED (script bug:
  libs.txt names /work/macros/*.lib, kit not mounted). Successor export_r2/run_export_r2.sh (kit mounted ro, then
  pair TT/FF into buf4_64/pair_routed_r2) queued on E7, log ~/head-r3-logs/buf64_export_pair_r2.log. Coupon only: no type sign-off.
- hd_serdes sd9f: E7 unit3729170 DRT 2nd iteration, 11,565 violations at 06:02 (from 69,638). sd9e (E10) fallback untouched.
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
- BUF64 coupon: export_r2 alias PASS (E7 buf4_64/export_r2/6_final.*), routed pair tE1o0->tE0b1 hold TT +386.45 / FF +106.09,
  2 endpoints, 0 negative (buf4_64/pair_routed_r2). Model said 171 TT / 115 FF margin. Coupon only; phase contract owner decides.

## Not done (next owner)
1. Geometry event NF15f: apply +181.44 to LEP type (2 upper cores, N-face pins, clock taps/reservations, plw_s2), parent
   die (6 north hd_serdes + PHY domains + die outline 17737.92, IO/bumps/PG/M8 guide), place the relay anchors at the
   witness columns, rerun alloc_r4 on the composed plan, then fresh clock GEN (GEN3/graft method) and reset census.
2. Reset seams (714/530) and BUF4 hold model: untouched by this lane. Mesh finite PG (141 -> 7 with localtracks f3ee5447): untouched.
3. Pending merges listed by Codex (HEAD localtracks f3ee5447, BUFdelay 55fb36df) were not touched.
