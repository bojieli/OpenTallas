# OPUS-FIX-KV-PV-R6 handoff (KV pv family owner; successor of OPUS-FIX-KV-PV-R5) -> OPUS-FIX-KV-PV-R7

Written 2026-11-21 ~21:xx PST. Posts lanes/posts/OPUS-FIX-KV-PV-R6.md. Logs intel2 ~/tmp/okpvr6/. Work dir epyc8
/srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/split28 (tree5 = private tree). No job of mine is running.

## A. All-16 one-event split (lever 3): compose_all16.py + run_all16.sh (ot-run --plan-job g0 on epyc8, ~2 min)
Composer fixes made this session (each previous version saved as compose_all16.r5_run4.py / .r6_run5.py / .r6_run6.py):
1. R2 leaf rows (start moved to the leaf anchor) are re-stationed: same reg count (no unpriced cycles), shortest legal L/Z
   polyline, grid-path fallback for same-half rows; no reg in a final core box or within 0.5 um of x 1080; same-half rows stay in
   their half, crossing rows cross once. Fixed run 4 (v1 o_vport_E_N_vqN e,w,e). Max hops in rows_all16.json R2HOPS (v12 vqN 396 um, < 405).
2. spec cut_pins_per_um = "type" (type_split option: the type's own G2 face budget x0.9) instead of flat 8/um. Run 5: 13 of 16
   types were over/fragmented at 7.2/um. With "type" every type except v1n places its cut windows.
3. clock.added_taps dropped on the 8 types that have them (pv, v1, v12, v2, v5n, v6n, v7, v8): the core swap changes the density tap
   count, so taps.density_taps' name check fails on the WHOLE type before the split. TAP-GRID-R5 must give per-half tap rows.
4. Ring review (v1 cl_i_slg_E_N_rsp_d1): a straddling ring whose bus feeds one station row ('landing ring <bus>' -> leaf) goes to
   that consumer's half, its window follows, and the ring row's start moves with the ring + regs re-stationed. v1: ring now e
   (1520.64, 276.48) not w (933.12, 535.68); window L2114_3 local 1169.6-1287.1; row i_slg_E_N_rsp_d1 1 reg, max hop 284 um.
   Run 5's w site sent all 1,056 bits up a 50-um channel and back across the cut to u_vport_E (e). x=1080 abutting site was
   blocked by the ring's own tap + collector relays u_rrl_266/289-291 (they stay at ~1102,331 in e).
5. kv3_pv_v1n HELD (HELD dict, rows_all16.json "held"): cut demand 16,267 pins, does not fit even at 12.96/um (v1n budget raised
   9.5 -> 14.4 in FACE_BUDGET, still "cut face full"): six vo forwards (o_vport_E/W_N_vo, _d1, _d2; 6 x 1,350 pins) cross x 1080
   and all want the top ~250 um of the cut face; vport half variants do not help (dbg_var/var_cut.json: WwEe 16168, WeEw 17277,
   WeEe 16491). Needs a structural row (move the vo rings/forwards off the cut or a different cut for v1n) -> KV-PLAN-R6.
Run 7 (15 types) FAIL: "kv3_pv_v12e: collector source ft10_i has no tap relay within 405.0 um (1364.1)" (type_split.py:3332,
collector tree after the split; TAP-GRID / reset-relay reselect class, FABLE-PD-KV-2000 item 7). Next: fix that (relay rows for
the v12 e half or TAP-GRID-R5 input), rerun. Failed dirs por_all16_{input,composed}.fail1-7 in tree5/.../qwen_kvsys (ot-delete later).
Diagnostics: dbg_cut_r6.py, var_cut_r6.py (per-type split, CPU=type DV=<dir>), dbg_all16_out/ (785 MB copy, ot-delete later).

## B. kv3_pv_v3 representative, bind 11 (split28/bindgate_11)
- R8_STALE is NOT an off-by-one at a source: the table equals bind 9/10's bound depths exactly (vport_ES_0/1/3.out_t bound
  40/59/71); bind 11's plan (R5 carry 472f8f912964, R3 cycles priced) moved them to 41/64/72. The table is one plan behind.
  COORD approved a second refresh: do it from the bind of the FINAL plan (after the first-hop fix, which adds cycles again),
  i.e. plan fix -> bind 12 -> r8_refresh (chain14.sh line 25 form) from bind-12 bus_groups -> bind 13.
- EMIT x3 / R8_STRAP_PAD x5 / TYPE_SPLIT x3 are all kv3_pc_v1/v3 strap pads from the stale R8 depths (pad > strap capacity -> bind
  splits pc into variants -> variant emit 'raw Q rst_rl_247: exactly one same-clk plain relay'). Expect them to clear with the refresh;
  if not, they are a pc-family bind issue (FAM-KV-IOPC). PARAM_REGEN pair image = KV-PLAN-R6 D28 apply step (run_mu833.sh).
- First hop > 405: v3 427 bits (o_astk_E..response_data 140 b at 1345 um, o_vport_W_N_vo 287 b at 639 um), v3e 396 (o_astk_E 128 b
  843 um, o_vport_E_N_vo_d4 128 b 824, _d3 140 b 468). These are FORWARD rows (bus in -> face out) whose lane passes the leaf anchor
  mid-way (R3), but the bound RTL feeds the leaf bits into station 0 (regs[0], at the input-port end). Re-siting cannot fix it
  (port-to-anchor > 800 um). Fix = leaf bits join the lane at the station at the anchor: either a separate leaf-launched row for
  the leaf bits (from the anchor) if the bind maps rows by source, or bind/emitter support (bind_intra_stations OUT-BUS covers only
  u_bout buses, all bits one latency). Needs the bind owner's call; leaf bits would carry fewer cycles than forwarded bits.
## C. Not done: pv_v3 split representative build (bind not clean). STOP list unchanged.
