# FAM-S81-COL-R2 handoff (11-21 03:4x PST) - STAND-DOWN, successor needed (Sonnet/Opus)
## Done / superseded
- cfg7 RD_EXTRA re-harden: Codex signed + exported it (main 00a9cc7750a, TT +350, FF 0, DRC/ANT 0, LEC EQUIVALENT; boundary FF -52.86). My own epyc7 rdxkit run (oth-ubuntu-3851512-1795252969) failed at CTS (kit corners) and is superseded; do not rerun. Recipe committed claude/fam-s81-col-rdx f3f038393f.
- FLEET-MIX-2340: stopped col_h10_r2 pv0c1de895 (intel2) and pvf1512c16 (epyc2) by exact unit.
- Recipe posted: private kit refused at src_manifest -> set "src_manifest":"off" in private wave/spec.json, rerun run-item.
## Proofs A and B (J5 col_h10_r0_p1 pvb095fa2f): BOTH FAILED at place (not at src_manifest)
- Bind+LATCHECK pass. Place failed in global_place hook OT_HOOK_COVERAGE relay_mid: 15 of 121 (A) / of 142 (B) station groups on old fallback, hop > 405 um: lpl_11_r.u_y_q, lpl_12_r.u_y_q, es_p0, rr_1, so_1, so_3, xo0..xo3. Same 15 in the baseline plan, so it is NOT caused by the ROM rows; it is the shared col relay-depth class.
- Codex diagnosis: lanes handoff/codex_fam_col_relay_mid_20261121.md (hub ~/coord/handoff). Needed extra stages: lpl_11 +2, lpl_12 +1, es_p0 +1 (or t0 shift 17.28 um left), rr_1 +1, so_1 +1, so_3 +1, xo0 +1, xo1 +1(+split), xo2 +2, xo3 +2; plus 7 adjacent chains need joint seats (29 seats, worst 403.8 um). Artifacts intel1 fam-s81-col/relay-mid-*-1121.
## Next steps
1. Fold those relay_depth D additions + joint seats into the J7 col rows (delta_c3c_rdx + Codex v3 nine-row FT delta epyc10 s81-j6/reviews_codex_1121/j7_coll_ft_order_delta_v3.json + rows/j7_cfg7 donors) and add FABLE lever-7 rows (N-strip ft window, xo_i pad) and ROM pval output rows.
2. Rebuild proof A' (rows above + signed RD_EXTRA view) via mkplan2.py + chainR2.sh pattern; pass = TT >= -42, no ROM-face/s*.q path in worst list. Codex private col unit 2930371 (E8) is a parallel corrected run: take its result first.
3. After J6 applies (C1n pack in progress, not C3g/C3i): lanefix.py + strict bind of delta; derive t4.xai/t5.xbi rows with relay_depth.py; hand to S81-J6-ASSEMBLY-R2.
4. J6-R2 tok/s answer still pending (asked 01:1x).
