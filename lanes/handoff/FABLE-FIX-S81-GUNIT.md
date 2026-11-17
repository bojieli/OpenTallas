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
