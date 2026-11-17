# FABLE-FIX-S81-GUNIT (S81 dsdv_gunit_l1f_bf), started 2026-11-16 17:4x PST

## Diagnosis (neither count-mapping nor missing record: PLAN/VIEW MISMATCH)
- Signed record EXISTS, both stores, sha equal: AGIdock /archive/opentallas-signed-1114/s81/dsdv_gunit_l1f_bf and
  rtx-pro /home/ubuntu/signed-export-1114/s81/dsdv_gunit_l1f_bf (6_final.odb 5a662c50..., signoff.json 6944512c...).
  eco_gf1115c: SIGNED minimal, DRC 0, ant 0, TT -16.44 (4 ep), internal FF >= 0 (port-start -44.9 advisory), LEC EQUIVALENT,
  FWPIPE (bind must carry OT_GUNIT_BF_FWPIPE, RT_LAT 66/64). No rebuild or hold ECO needed.
- Counter: signed_cores credits it (63) and the archive gate passes; signed_designs (62/64) rejects it in design_unmatched:
  "pins match no plan design: outline (432000, 216000) nm vs plan (432000, 172800) nm". The counter is right.
- Adopted plan 819037bbe371 (B6gF2s4tapfix1) gunit__t1, 4 instances of bf: outline 432x172.8, pins_file
  inputs/core_pins/nrev_1113/lanes/dsdv_gunit_l1f_bf.json (DIE-S81-89 11-13 N-face lane reverse).
  Signed g3f was built 11-14 on 432x216 (Fable: 172.8 cannot route, g1 dead GRT-0116) from the PRE-nrev pin table
  inputs/core_pins/dsdv_gunit_l1f_bf.json (sha 859101cf, canon 9f39dae5).
- Pin diff signed vs plan (2689 names equal): S face (s0a/s0b/sv_lo/vf_lo/ctl_lo/sf0, 953 pins) identical;
  N face +43.2 y, and s1a/s1b (656) differ in x (lane order); W/E faces (786) same x, +21.6 y.
- Seam check: plan stacks ba0 / 21.6 gap / bf / ba1 with bf N ABUTTING ba1 S (gap 0). RTL dsdv_gunit_l1f.sv:904
  wires ba1.qa[i] -> bf.s1a[i]. The SIGNED bf has s1a[i]/s1b[i] at the x of plan ba1 qa[i]/qb[i] (656/656 same index);
  the plan nrev table puts them at a different index (656/656 crossed at a zero-gap seam).
- Room: growing bf to 216 needs ba1 x4 moved +43.2 y. Tops become 557.28 (inst 0, next core at 682.56) and 1222.56
  (inst 1-3, type height 1226.88: 4.32 left). ba1 has no N-face pins (S + W only).

## Proposed fix = one gunit__t1 plan event (no core rebuild)
bf outline 432x172.8 -> 432x216 (origin kept), pins/LEF = signed view (epyc7
/srv/opentallas-scratch2/claude/type-gunit-l1f/signed_view_1116/dsdv_gunit_l1f_bf, pins.json canon 9f39dae5; LEF also in
both archives), ba1 x4 origin y +43.2, W/E landings +21.6. Then bind + LATCHECK (FWPIPE, RT_LAT 66/64) + G0; the count
then matches by pins and S81 cores go 63/64. Alternative (not recommended): rebuild bf at 216 with nrev pins plus the
mirrored ba1 (new sign-off of two cores).

## Done
- rtx-pro INDEX.tsv was missing the 2 rows AGIdock has (native_w re-sign row, gunit_l1f_bf): appended byte-identical
  under flock; indexes now in sync (498 lines).
## Not done / next
- Plan delta not written or bound (needs die-owner / COORD go, S81 819/D3 just adopted). No job launched, nothing deleted.
- Evidence: rtx-pro scratchpad .../scratchpad/gunit (plan_pins.json, plan.lef, pins.json, ba1_pins.json, agi_INDEX.tsv).

## 2026-11-16 18:0x PST: COORD GO (no rebuild) -> rows written for S81-DIE-R, NOT bound
Dir: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-gunit (W). Script W/gunit_bf_compose.py (inputs W/in, asserts inside).
- W/rows/gunit_bf_signed1116_rows.json (sha af0eb56c..., schema opentallas.typed_future_delta.v1, same form as t51e rows;
  base raw 819037bb): 40 patches, all in gunit__t1: bf x4 outline_um 432x172.8 -> 432x216, pins_file ->
  inputs/core_pins/dsdv_gunit_l1f_bf_signed1116.json, lef -> cores/views/dsdv_gunit_l1f_bf_signed_1116/dsdv_gunit_l1f_bf.lef, note;
  ba1 x4 origin y +43.2; clock taps: u_f.clk xy +21.6 y (= signed clk pin), insertion 360/293.4 ESTIMATE -> 412.99/339.27
  measured, budget_owner; u_ahi.clk xy +43.2 y.
- W/rows/overlay (11 files): signed LEF, tt/ff lib, signoff.json, pins.json, core.json, gates.json, provenance.json,
  insertion.json, view.json, and the plan pin table (2689 pins, from the signed LEF, == kit pins.json 0 mismatch).
- W/rows/plan_819_plus_gunit_bf.json = candidate (sha e81bc507...), W/rows/gunit_bf_signed1116_report.json = checks.
- W/E landings: the plan has no separate landing rows for these cores; they follow the pin table (786 W/E pins, same x, +21.6 y).
Checks (all asserted): only type gunit__t1 changes (keys hard_cores + clock; no top-level key, type outline unchanged, die
unchanged); 4 cores resized (bf), 4 moved (ba1), no other core touched; 0 core overlaps, 0 outside the type, all on the 4.32
lattice; nothing (station, tap, sink site) in the strips ba1 moves into; room above ba1: 125.28 (g0), 4.32 (g1-g3).
Seam bf N / ba1 S per instance: 950/950 straight, s1a/s1b 656/656, gap 0. Seam bf S / ba0 N: 953/953 straight (unchanged).
NREV = PLAN ERROR, proven: plan 819 nrev table at the same zero-gap seam: s1a/s1b 0/656 straight, 656 crossed, span up to
340.272 um, peak 656 nets over one x = 25.7 um of M4+M6 channel by stage_gunit_bf_nrev.py's own estimate (0.7 util); the
plan has 0. The stage docstring says mode "lanes" needs that parent channel (or mode "mirror" + ba1 MY); 11-13 source note:
"parent N seam/gutters and plan adoption separate". DIE-S81-90 adopted the lanes table alone. The pre-nrev table on the same
geometry is 656/656 straight. Inheritance: none. gunit__t1 is the only gunit type (1 die instance), the only user of the
nrev table and of the l1f bands (12 cores).
For S81-DIE-R: bind needs OT_GUNIT_BF_FWPIPE, lane RT_LAT 66/64; plan core entries carry no lib field (libs sit beside the
LEF in the view dir); cells estimate untouched. Next: S81-DIE-R composes + binds + LATCHECK/G0, Fable review in parallel;
after adoption check signed_designs credits bf (63/64).
