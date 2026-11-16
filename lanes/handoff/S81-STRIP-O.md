# S81-STRIP-O handoff (Opus successor of FABLE-FIX-S81-STRIP; Fable weekly limit to 11-21)

Updated 2026-11-16 02:40 PST.

## Scope
- Leaf t43 / t47 / t75 / t28 / t8 (STRIP boxed types; DIE-S81-92 G4 core-move gave 0 rows), t72 (ff key only).
- FABLE-PD-S81-0117 levers 5-7: t62 STRIP row (ft0/ft1 stations in the S strip vs ft7_i/ft4_o windows), t34 one kit with y-slot + STRIP rows, re-judge leaf rows only on ring_place ff kits.

## Proof kits (running)
- Plan epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/fx0.json (7688d13b2b37) = B6gE composed + ring_place carried from B6gE_pre on 988 bands (lever-2 form, private). t34 = kitplan_strip row (strip+y-slot), t62 = kitplan_ys row.
- Kits: epyc7 fable-fix-s81-strip/kit/b_<t>/kit/gen/ot_s81sl_leaf__<t>, replicated to epyc8/9/10; running on epyc8 under ot-run (run_kit.sh grt 64 16), OT_GRT_EARLY_STOP=0, OT_GRT_CONGESTED_FAIL=0. All ring tags +ff/+ffr, preflight PASS.
- Launch logs intel2 ~/fable-fix-s81-strip/run_b_<t>_grt.log; recipe epyc7 fable-fix-s81-strip/kit_fx.sh, intel2 ~/fable-fix-s81-strip/launch.sh.
- run_kit PIDs on epyc8: t34 45921, t72 52346, t8 59563, t62 78778, t28 4102339, t43 4107187, t47 4113938, t75 4148613.
- Status script: epyc8 run `bash -s < st.sh` (copy in this lane's notes); split scripts epyc8 /tmp/s81o_cong.py KIT [it], /tmp/s81o_ft.py KIT [it] (copies of Fable 0117 cong/ft).

## Tools for rows (epyc7 /srv/opentallas-scratch2/claude/s81-leaf-plan/evg/)
- strip_push2.py (sequential push, far-face growth fallback), push_diag.py (why push_ok refuses), band_ca_floor.py (band floor rule; t72 not needed with ff).
- sp2/types.json 528df95851f8: t28 push vn_b +65.88 y, ve_s +53.46 y (along 2.6 -> 0.90); t8 vn_b +57.78 (1.89 -> 1.46); t43/t47/t75 refused (ft station banks would be covered).

## Decisions so far
- None yet: no structural row before the ff kit reads GRT (0117 stop list: no core move / growth answer to band-caused overflow).

## Next
1. Read each kit's GRT overflow per iteration + ft/cland split when GRT ends.
2. Per type: 0 overflow -> no row (READY as "no row needed"); ft-strip overflow -> core push / station bank move / outline growth row.
3. READY-ROWS to DIE-S81-92 for the event after F2s.
