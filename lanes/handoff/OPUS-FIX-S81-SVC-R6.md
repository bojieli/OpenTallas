# OPUS-FIX-S81-SVC-R6 handoff (started 2026-11-21 05:0x PST; newest first). Succeeds OPUS-FIX-S81-SVC-R5 (read its STOOD DOWN block).
Nothing signed or exported. Pushed to main: d32d1a542d (type_split sidecar tree check), afc6f085e3 (type_split part_region), 625a0f6f0e (ATT land bench).

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
