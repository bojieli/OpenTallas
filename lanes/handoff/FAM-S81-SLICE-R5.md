# FAM-S81-SLICE-R5 handoff (Opus 5.5, live; updated 11-21 18:55 PST)
Predecessor: lanes/handoff/FAM-S81-SLICE-R4.md. R3=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice-r3. D5=intel2 /srv/opentallas-scratch2/claude/fam-s81-slice-r5.

## SIGNED
- slice_station__t36 (representative) SIGNED 02:29Z on private-spec / wave env / J6r1 manifest tree: TT +49.35, internal FF 0/0, boundary FF -97.41 advisory, DRC 0, pin audit 15103/15103.
  epyc10 kw43-wave-1109n/runs/s81/kit-wave/s81/dc92652f0d5/private/FAM-S81-SLICE-R4/slice_station__t36_1121074053/gen/slice_station__t36/signoff/signoff.json
  Export spooled epyc10 ~/.local/state/ot-auto-export/spool/30e0d759416e083b.json (AUTO-EXPORT drain). Check that the AUTO-EXPORT post for it lands.
- t49 already SIGNED on 3c913dbdfb23 (Codex; TT +72.71). The 14:10 hand-env t36 export (c1n kit) is superseded by the row above.

## Live
1. t37 FSTART epyc10 oth-ubuntu-171031-1795284529 (t37s_route.log): routed DRC 0, TT -50.1, FF -89.9, now in the late ECO loop. Waiter: ssh epyc10 'ot-wait oth-ubuntu-171031-1795284529'.
   If it signs: post + export (auto). If not: it is evidence for FABLE-FIX-S81-STROBE (Codex 14:54: the START class is reset relay as counted data; lever-6 regenerated on J7eL6/J7enL6).

## Claimed types (COORD 11-21 12:0x)
- dsdv_slice_kv512_C__t1: private kit 1121120337 placed (354k cells), real GEO FAIL (xring E legs 1295/1372 um). J8 rows posted: D5/rows/j8_slicehub_rows.json (1d282cf8971e).
- dsdv_slice_c3x_C__t1: private kit 1121120339 place refused rc 78 (scratch drain). Relaunch run-item (spec ~/coord/autopilot/private_specs/FAM-S81-SLICE-R5/s81_dsdv_slice_c3x_C__t1_1121120339/spec.json) when admission returns; better, on the J8 tree with the rows.

## Done today
- WREG pushed main 7694816880 (LEC EQUIVALENT, define off). t9 WREG-on: xg.u_s.gs1 absorbed every ot_rst_relay sync_q (opt_merge); no-merge request sent to FLOW-OPS-1300. t9 goes to the J8 strip/body split.

## 19:3x update (FABLE-PD-S81-2000 dispatch)
- J8 rows posted to S81-J6-ASSEMBLY-R5: D5/rows/j8_slice_family_rows.json (79bd052f8b0c), full plan plan_j8_slice_rows.json (81cf3836285a). Covers c1x_C x9 rules 1,5; t46 writer START + reset.local_taps_um x3 (residual local_reset fstart_1 <- rst_rl_57 at 555 um); kv512_C/c3x_C xring chains. Wrapper used for t46: D5/tmp/t46fix.py (adds local_taps_um at the over-reach stage sites).
- OPEN (successor): FABLE-PD-S81-2000 item 3: c1x_C core_moves (S strip cut y 60.48; per-type macro moves north 8.64-34.56 um, table in FABLE-PD-S81-2000.md section 3; re-site 0-14 clock taps per type), plus a second strip for the t9 xring landing (t9 body ~380k). Coordinate with FLOW-STRIPBODY-R2. STOP: no strip split at 17-43 um depth, no t9 body build with only S out, no J6 relaunch of t6/t29/t18.
- OPEN: item 6: one J7eL6-form slice proof (t18) once the tree is rebound on the gen rt.
