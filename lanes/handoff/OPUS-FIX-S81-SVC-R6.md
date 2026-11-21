# OPUS-FIX-S81-SVC-R6 handoff (started 2026-11-21 05:0x PST; newest first). Succeeds OPUS-FIX-S81-SVC-R5 (read its STOOD DOWN block).
Nothing signed or exported. Pushed to main: d32d1a542d (type_split sidecar tree check), afc6f085e3 (type_split part_region), 625a0f6f0e (ATT land bench).


## STOOD DOWN 11-21 08:3x PST (context ~318k). Successor: OPUS-FIX-S81-SVC-R7. READ THIS + the STATE block below.
RUNNING (leave; re-arm waiters at once, Bash run_in_background loops):
- chain10h epyc10 PID 1746572 (bind_hi4x/chain10h.sh, log chain10h.log, out chain10h.out). Now: split -> elab -> strict bind -> LATCHECK -> STATE.
  W1: R=/srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/bind_hi4x; loop: ssh epyc10 "cat $R/STATE; kill -0 1746572 && echo chain_live" every 300 s
  until STATE has rc=|_BAD (or chain gone). Green = "rc=0 BIND_RC=0 LATCHECK_RC=0" -> the chain itself runs prep.py (config.mk diff gate vs wave kit) ->
  place -> route of svc_hi_dsdv_svc_rs__t4_att on epyc10; re-arm on $R/KSTATE (match "route rc=|_BAD|place rc=[1-9]").
  Red: read bind_out3/bind_report.json errors (classify by prefix), diff inputs first; previous four failures were all setup class.
  To re-run: mv STATE/split/elab3/bind3 logs + bind_out3 aside (suffix), copy chainNN.sh -> next with sed (see chain10h.sh line 2), nohup start.
- chain_rest8 epyc8 PID 833298 (same path on epyc8 bind_hi4x/chain_rest8.sh, log rest8.log): polls epyc10 STATE every 300 s; green -> rsync
  tree + bind_out3 -> prep_rest.py (copies epyc10 prep.py incl. the cfg diff gate) -> place -> route on epyc8. Result KSTATE_REST.
  If STATE goes red it exits (NOBIND); after a re-run, mv KSTATE_REST aside and restart it (nohup, it waits for the new STATE).
OPEN: if HARD_CORE_PARAM_ALL persists for legacy gunit l0r/l3/qbank_N, find how the J6 tree (s81-j6/candC1n_pf, gate.sh) resolves them (ref_tile specs
  copied already). Never set OT_HCPARAM_ALL=0.
AFTER ROUTE: sign-off read of both parts (DRC 0 route, TT setup >= -42, FF hold >= 0, LEC; final-stage reports only), then export both (benches PASS).
J7: only hi4 rows handed (lanes/handoff/OPUS-FIX-S81-SVC-R6-J7-rows.json); watch S81-J6-ASSEMBLY-R3 / COORD replies on the 15 blocked types.
Workers' dirs: epyc10 opus-fix-s81-svc-r6/j7rows/package, epyc8 opus-fix-s81-svc-r6/att-bench, lane clone epyc10 opus-fix-s81-svc-r6/lc.

## 11-21 08:2x PST STATE
LIVE (leave running; waiters needed):
- chain10h epyc10 PID 1746572: opus-fix-s81-svc-r5/bind_hi4x/chain10h.sh: split (spec plan = band-test plan_svc_hi4_x_epoch_ua.json, manifest
  tree/asbuilt_svc_r5_hi4_split_map_ua.json) -> elab -> strict bind --all-gaps -> LATCHECK -> STATE -> on green prep.py att kit -> place -> route (KSTATE).
  prep.py has the COORD config.mk diff gate vs wave kit (wave_ref/, kit-wave 224567138ab): any flow-knob diff = PREP_FAIL CFGDIFF, report cfgdiff_<type>.tsv.
- chain_rest8 epyc8 PID 833298 (same paths on epyc8): waits epyc10 STATE green -> rsync tree+bind_out3 -> prep_rest.py rest part svc_hi_dsdv_svc_rs__t4
  -> place -> route on epyc8. KSTATE_REST, rest8.log.
BIND HISTORY (all setup class, fixed): split tree check (10d), manifest relative base (10e), part_region (10f), 10g 263 errors:
  ATTCUT wrapper adds u_att.u_a level -> plan paths renamed in hi4 type (112 dotted + 72 flat physical_inst), gid strap regex + declared_ties paths
  accept (\.u_a)?, declared_ties types += __t4_att, new land SRAM ties (w_mask_in all-ones, wd_in[255:144]=0, proof = land bench),
  HARD_CORE_PARAM_ALL (13 non-svc modules: spec.json/config.mk copied from s81-j6/candC1n_pf physical/ref_tile; legacy gunit l0r/l3 may remain -> if so
  compare with how J6 binds them; OT_HCPARAM_ALL is NOT to be switched off).
BENCHES: ATT land bench NON-VACUOUS PASS 6/6 (epyc8 att-bench rowx0/rowx1); prog 2412579 PASS (ATTCUT only, no land coverage). Export allowed after sign-off.
J7 ROWS: posted lanes/handoff/OPUS-FIX-S81-SVC-R6-J7-rows.json to S81-J6-ASSEMBLY-R3: only hi4 composes; 15 types blocked (port windows on seam,
  lo rest-part overflow, hi t1/t6 FT corridor) -> assembly / COORD decision. svc_* hold stays.
NEXT: on STATE green -> watch KSTATE / KSTATE_REST; sign-off read (DRC 0, TT >= -42, FF hold >= 0, LEC; post-hook CTS reports); export both parts.
