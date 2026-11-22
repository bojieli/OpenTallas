# OPUS-FIX-KV-HGI-R6 handoff (updated 11-22 10:4xZ)

Owner of kv3_hg* / kv3_hgi*. Work dir: epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r6 (ana/, gen/, chain_*.sh, gates_*.sh).

## State
- D28 rows HANDED to KV-PLAN-R6 (COORD ruling 11-22): ana/d28_hg_hgi_pkg.json f69be8e48755 -> plan_r6h.json 64ec19c3d027 (19 types, type-local keys).
  Proof: fresh27h (empty out dir, rt fda4eaad0e94) G0 PASS, RC_BIND 0, 0 EMIT, LATCHECK 0, LANDREMAP 0. R8 32-unequal + BPC 1 inherited (non-blocking per COORD).
- Plan lineage: R6c e81c383a201c (regen + lockup_regions + HGI sync tails) -> R6d (ectl landing re-site, 17 rows) -> R6e (+hg krsp re-site, 8 rows)
  -> R6f b2dc2d5b1a2d (+10 band-follows-core rows, v8 y 1167.48) -> R6g ae551048b4ad (landing_remap) -> R6h 64ec19c3d027 (+16 port-pad relay ref rewrites, gen/padremap.py).
- HOLD: no hg/hgi kit until a real bind shows lockup regions. lockup_regions is INERT in real binds ("rest" 40 loads on every hg/hgi type);
  a 04:48 debug-wrapper bind gave 18. A/B debug binds running (tmp/lockab_home vs tmp/lockab_nohome; intel2 ~/tmp/opusfixkvhgir6/lockab_*.log).
- Open: LANDREMAP port-pad chain (landing_remap skips pad relays) -> FLOW-OPS-R2 (top). Inherited hgi_v4 ft20_i band under head2_e1 68% (warn-only).

## Next
1. Read A/B result; root-cause lockup (env / wrapper / tools); if a bind tool bug: fix on main + test, tell FLOW-OPS-R2 + KV-PLAN-R6 the sha.
2. After lockup is effective in D28 bound text: private-spec kv3_hgi_v2__cle0015330 on epyc8 (wave env, rt >= fda4), kit_pin_site_check, sign-off.
3. Relaunch claimed hg rows (kv3_hg, v1p3..v1p6, hg_v3) on D28.

## Lessons
- Every core-move row needs landing_remap + pad-relay rewrite + band-follows-core + KITFIT grid snap check BEFORE bind.
- Run plan_gate_pre --baseline-plan <last clean plan> (LANDREMAP) and landing_band_core before any bind.
