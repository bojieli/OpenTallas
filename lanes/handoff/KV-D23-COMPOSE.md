# KV-D23-COMPOSE handoff (helper of KV-HG-OPUS; started 2026-11-18 06:0x PST)

Work dir epyc7 /srv/opentallas-scratch2/claude/kv-d23-compose (lane clone wt/ = sparse main worktree). Hub logs intel2 ~/tmp/kvd23c.

## Status 2026-11-20 09:30Z (OWNER #2 daily cadence; read this first)
- KV DAILY CUT = 04:00Z. Rows posted by the cut, each with path + sha (and a kv_regen frame dry run for any K/depth row), go into that day's event.
  - Schedule: compose + PRE/G0 04-05Z, private-copy strict bind ~05-08:30Z, apply ~09Z.
- Today's event: KV-D25e3, strict bind running (W8/d25e3bindgate, ETA ~11:45Z). Apply per the 08:45Z section (post_bind_d25e3.sh, then apply_d25.sh).
- The D25f2 parallel chain is STOPPED (owner #2). Its sealed tree kw45/..._hg13_26fa4732_t315cc72_d25f2 is the starting point for KV-D26.
- KV-D26 queue (cut 2026-11-21 04:00Z), on main tools at cut time. Tools must be >= 77553520681 (guard fix); this also brings owner #6 generator defaults (registered SRAM/ROM reads +1 cycle, 300-um placed-hop cap).
  1. D25f2 content: rls 15 types, hub_Wi SRAM, pv form C (rows_C), pc core-tap v2. Core-tap v2 ships only paired with the v3 die tree (DIE-CORETAP-1119 must confirm on the D26 plan).
  2. Guard: clock.pregrt_hold_guard_ps. kv3_pv stays at the 5 ps base until form C is in its kits; hg/hgi/pc keep the default 45 (FABLE-CBC-QK-0130 §1).
  3. kv3_hub_Eo: all 61 station rows from KV-HUB-0005 placed_scan_rows.json (+cycles pre-approved), plus regions, plus a per-region reset relay leaf (<=32 loads, <=405 um). Re-bind needed (FABLE-CBC-QK-0130 §5).
  4. qkd_hr_ingest_eng: early tap 106/78 ps + core-input lockup latches, no re-CTS (KV-HUB-0005 / DIE-CORETAP-1119, §6).
  5. kv3_pc: form B is DISPROVED (0 of 688 core PG pins connect). Form A re-harden is owned by KV-PC-PG-2330; take its new pcc/pcf/h_head_p views when posted, plus the lattice row (§2).
  6. Hub core-tap rows when posted.
- KV-D26 item 7, superset forms (COORD 09:5xZ; FABLE-SUPERSET-0415-classes.json sha c6b142d032c7, on the D25f2 plan, 56 -> 24 builds). New step TYPEMERGE-KV in build_d26: rep = widest member; partition_types[rep].superset (SUPERSET-1 e00be6bb60); members re-pointed with the class orient; keep per-member added_taps; re-key rows to rep; kv_regen dry run; latency unchanged. hg v1..v1p6 -> 1 (needs FABLE-FIX-KV-HG-0000 netlist-superset confirm); hgi 11 -> 1-3 (KV-PC-HGI-1119). Ask posted 1bf4075a805.
- KV-D26 items 8-10 (posts 11-20 02:07-02:16 PST):
  8. CBC-ALL-0200: build the D26 tree from main >= 595df01cf9d (reset hop cap 300 = aced0fb210) and run PRECHECK; quote the cbc_score.tsv per-die PASS counts in the event post. rt/current sync is blocked (hub disk): use a main clone for TOOLS.
  9. kv3_pv raw branches: re-run kv_start_corridor_event.py raw (tools >= aced0fb210) on the D26 start plan. 15 of 16 pv types have hops > 300 in D25f2 (audit lanes/handoff/CBC-R4/kv_pv_rawbranch_audit_d25f2.json ac25321b3b06).
  10. hgi_v1 k12 rows (wns +14.2 TT post-CTS): section N of lanes/handoff/FABLE-FIX-KV-HG-rows-d24.json (6e210594fbd): reg_leaf_split, tN/eN internal_stations D=3, 2 polylines, 2 relay_sites, eN +2 / tN +2 cycles, one hst3 move. Order: apply k12 rows to hgi_v1 BEFORE the hgi superset merge, so the representative carries them.
  11. (COORD 10:3xZ) Re-emit the type SDCs from main >= 76ea03e4ae9 (new seam budget default). Also re-run the raw-branch AND reset generators from aced0fb210 (300 um) on ALL kv3_pv types, not only the 15 flagged. Item 10 (section N) plus the OPUS-FIX-KV-HG proposal-3 tools are taken only once k13 proves out; otherwise they wait for the next cut.
  12. (COORD 10:4xZ, revises item 7) Superset unify spec lanes/handoff/FABLE-SUPERSET-0415-unify.json (2ae9ece21c46, on kv_d25f2). Three largest classes, in this order:
      - kv3_hg: rep v1p6, 8 members, 7833 bits.
      - kv3_hgi: rep v8, 11 members, cland_missing ends.
      - kv3_pv: rep v12, 16 members.
      Form: members KEEP their type names (no re-point, no outline change). Each member gets its bus_missing, bus_narrow, cland_missing and ft rows, copied from the rep plan bus and ft_slot defs (face, window, layers), plus partition_types[T].superset=true (SUPERSET-1 e00be6bb60 gives the spare pins).
      Acceptance: tools/fleet/netlist_inherit.py summary shows 1 hash group per class, then a per-member proof against the signed rep.
      Step UNIFY-KV in build_d26 (to write) runs after the per-type rows.
- Not in D26 unless reposted: M2 (k11), HST3FB (stop list), depth-16 rows.

## Status 2026-11-20 08:45Z (read this first; supersedes 07:05Z)
- D25e3: plan 983443ee7b6d, G0 PASS (0 errors / 2464 warnings), sealed 5705fa378e1c, replicated and hosts check OK to epyc9/10, intel1, epyc2.
  - Strict bind on private copy kw45/bindcopy_kv_d25e3 started 08:38:55Z (W8/d25e3bindgate; chain log W8/run_d25e3.out; ETA ~11:45Z).
- When green:
  1. On epyc8: `bash W8/post_bind_d25e3.sh`. It seals and replicates the bind dest, rsyncs every referenced bindcopy path to epyc7/9/10, intel1 and epyc2, and checks 0 missing per host. Wait for READY_TO_APPLY in W8/post_bind_d25e3.out.
  2. On intel2: `RT=$(readlink -f rt/current) TOOLS=a2fb7e625dd89d4961fa633e35977e1e4a3577f5 HOSTS=epyc8,epyc9,epyc10,intel1,epyc2 BGH=epyc8 BIND_DEST=<dest> LIVE=<d25e tree> LIVE_EV=KV-D25e BC=d25e3 SKIP_SEAL=1 NOTE_TXT=... bash ~/tmp/kvd23c/apply_d25.sh d25e3 KV-D25e3`.
  3. NEVER delete bindcopy_kv_d25e3.
- D25f2 (lever 5 + FABLE-PD-KV-2300 §A) staged on D25e3: tree kw45/src_kv_pin_eb1e73448bd0_hg13_26fa4732_t315cc72_d25f2, plan 26fa4732ff8e, tools main 315cc72.
  - Steps: RLS 15 types, HUBWI SRAM at (1058.4,1566.0), ROWSC (rows_C 2c57439f7acf: lockup seg 8, station 405), COREEARLY (die-coretap kv_d25e_mean rows 112360ab8ca5: 48 pc core taps). HST3FB dropped (FABLE stop list).
  - G0 PASS. Chain W8/run_d25f2.sh (seal, private bindcopy, strict bind) is running.
  - PAIRING: COREEARLY ships only if DIE-CORETAP-1119 confirms the v3 tree is built on plan 26fa4732ff8e (asked 08:0xZ). Otherwise rebuild without it: SKIP_COREEARLY=1 W8/build_d25f.py.
- Out of D25f2: M2 (k11 not ready), depth-16 rows (other form), kv3_pc PG views (KV-PC-PG).
- Scrap: old D25f tree kw45/src_kv_pin_eb1e73448bd0_hg13_ba572267_t99007dc_d25f plus its replicas on epyc9/10, intel1, epyc2; ot-delete when idle.
  - Deleted: kw45/bindcopy_kv_d25e2, kw45/bindsrc_kv_d25e2, kw45/bindcopy_kv_d25f (guard).

## Status 2026-11-20 07:05Z (read this first; supersedes 05:30Z for D25e2)
- D25e2 strict bind FAILED with exactly one error: PARAM_REGEN kv_regen 'ECTL: K round trips differ per frame [25, 26]'.
  - Cause: the 28 fall rows moved 28 ECTL rq lanes down one cycle; the 4 hg->pc pairs without a fall row (WN_1/WN_3/WS_3/WS_6) stayed at RT 26.
  - Rest of the gate: R8_RECHECK changed 0, LATCHECK 0.
  - KV-CROSSING posted ROWS-KV-ECTL-RT-FIX.json (W8/d25e2_in, 4b55c5b15800): 4 rq rows K-1/sched_lat-1.
- D25e3 = D25e2 + those 4 rows (W8/build_d25e3.py, tools a2fb7e6 unchanged).
  - Chain W8/run_d25e3.sh (log W8/run_d25e3.out): build -> PRE+G0 -> seal/replicate -> PRIVATE cp -a bindcopy kw45/bindcopy_kv_d25e3 -> strict bind (W8/d25e3bindgate).
  - When green: seal the bind dest (W8/seal_bind_dest.sh d25e3 <tree>, REPL_HOSTS="epyc9 epyc10 intel1 epyc2"), then apply_d25.sh d25e3 KV-D25e3 (TOOLS=a2fb7e625dd8..., LIVE=d25e tree, LIVE_EV=KV-D25e, BC=d25e3).
  - KEEP kw45/bindcopy_kv_d25e3 after apply.
- D25f (lever 5, gen-only) staged on D25e2: plan ba57226730de, G0 PASS, sealed.
  - Must be REBASED on D25e3: rerun W8/build_d25f.py on the D25e3 tree, then W8/fix_hubwi_d25f.py is no longer needed (the hubwi row script has the tap-clear site).
  - Old D25f tree kw45/src_kv_pin_eb1e73448bd0_hg13_ba572267_t99007dc_d25f and its replicas are scrap.
  - kw45/bindcopy_kv_d25f is an empty guard dir; rmdir it once seal_bind_d25f.sh has exited.

## Status 2026-11-20 05:30Z (read this first; corrects 04:50Z)
- RULE (learned the hard way): a bind dest reads ABSOLUTE paths inside kw45/bindcopy_kv_<ev> (bind.f, asbuilt.ys, kit_rtl.json). The bindcopy of an applied or bound event is a live kit input on every gen host; NEVER delete it. The 04:50Z note "then ot-delete kw45/bindcopy_kv_d25e2" is WRONG: keep it and replicate it with the dest.
  - Deleting bindcopy_kv_d25e caused KIT_INPUT_MISSING for KV-D25e on all hosts.
  - Rebuilt 05:1xZ as a sparse private copy of the 183 referenced paths (W8/mk_sparse_bc.py: bind_of_record from the sealed dest, everything else from the tree) on epyc7, epyc8, epyc9, epyc10, intel1 and epyc2.
- D25e2 tree: resealed unshared, SRC_MANIFEST OK 619dc622ee98, RC_VERIFY 0, replicated to epyc9, epyc10, intel1 and epyc2. Strict bind running on epyc8 (W8/d25e2bindgate).
- kv3_hub_Wi ORD-2013: u_bound.u_kvs_emb.u_rowtx.u_row = ot_sram_1r1w_64x512_m1_r2c2 has no plan view.
  - Row: W8/hubwi_macro_row.py, a physical_parts leaf on content kvs_emb at origin (1097.28,1587.6) R0. KITFIT clean.
  - The other hub types have no gap (static walk W8/hubmacros3.py).
- D25f (on D25e2 after it applies; COORD lever 5):
  - rls rows for the 15 types without a split (lanes/handoff/FABLE-FIX-KV-HG-rls-rows-all.json 470ed6c0684d; keep D25e2's section-M rows on hgi_v1 x2);
  - the hst3 polyline swapped to the k10 fallback [[200,950],[650,950],[650,618]], or M2 if k11 holds (tN/eN D=3, +1 cycle each);
  - DIE-CORETAP pc v3 offsets + pv DME (final after the snake runs; no DME on hg/hgi);
  - FABLE-FIX-KV-PV budgets.r_dly_spread_station_um {kv3_pv: 405} + lockup rows (after the v8f read);
  - the hub_Wi macro row.

## Status 2026-11-20 04:50Z (read this first; supersedes 02:45Z)
LIVE = KV-D25e, applied bind-first at 04:41Z.
- Commits and receipt: kit_wave 5d887cfc3e5; receipt lanes/handoff/qwen_kvsys_atomic_apply_1795149669406572244.json.
- Tree: kw45/src_kv_pin_eb1e73448bd0_hg11_a5a8c6b9_tdcd5636_d25e (manifest dc58066d4f79, plan a5a8c6b96e5f).
- Bind of record: kw45/..._d25e_bind_1120042203, on epyc8/9/10, intel1 and epyc2.
- bound_trees = KV-D25d (bind 1119143244) + KV-D24.
- Driver: intel2 ~/tmp/kvd23c/apply_d25.sh. New env: TOOLS, LF, NOTE_TXT. RT = the resolved rt/current (rt dirs get pruned).
- Apply-time fix: the tree check on epyc10 refused inodes shared with a cp -al copy. Fix = delete your own copy, or replace the tree-side files with private copies (src_manifest.py links TREE lists them).

D25e2: G0 PASS (0 errors / 2464 warnings), PRE 0.
- Tree: kw45/src_kv_pin_eb1e73448bd0_hg12_d96baf37_ta2fb7e6_d25e2, plan d96baf37b98c, tools main a2fb7e625dd8. a2fb7e625dd8 contains 6e2f4ee27af8, 1b95661b75, 8b1909473d6/a2fb7e625dd and 8f981deeaa1.
- Contents vs D25e (report W8/d25e2/build_report.json):
  - hgi_v1 x2 section L+M:
    - reg_leaf_split hst2 at x 40 and hst3 at x 650;
    - polylines;
    - tN station (200,950) +1;
    - eN pad 2 via R8, with eN fixed staying 6 under the native_istations rule;
    - 64 eN pd2 sites plus the eq key.
  - KTALIAS: 1904 x 19 alias keys dropped.
  - FALL: 32 sidecar ports (30 K-1, 2 K+1).
  - PV: +500 route-priced set (compose_rows --cycles-405) with the tables from the bind head:
    - r8_ev repinned;
    - pv_col/v pads MINPAD 10 / EMINPAD 10;
    - r8 scripts from main.
  - R: 16 pv tail_clear sync rows.
  - Latency: 172 lanes, +484.
- Strict bind: started 03:53Z on epyc8, W8/d25e2bindgate, copy kw45/bindcopy_kv_d25e2.
  - The bind head beforehand (W8/d25e2head2) gave head_r8_errors 0 and stale 0.
- Seal: done, but verify refused because the bind copy shared the inodes. W8/reseal_unshare_d25e2.sh moves the sealed tree to kw45/bindsrc_kv_d25e2 (the bind copy's inode source), copies it back with cp -a, then verifies and replicates to epyc9/10, intel1 and epyc2 (W8/seal_rep_d25e2.out).
- Next, when the bind is green:
  1. On epyc8: `REPL_HOSTS="epyc9 epyc10 intel1 epyc2" bash W8/seal_bind_dest.sh d25e2 <tree>`.
  2. On intel2: `RT=$(readlink -f rt/current) TOOLS=a2fb7e625dd89d4961fa633e35977e1e4a3577f5 HOSTS=epyc8,epyc9,epyc10,intel1,epyc2 BGH=epyc8 BIND_DEST=<dest> LIVE=<d25e tree> LIVE_EV=KV-D25e BC=d25e2 SKIP_SEAL=1 NOTE_TXT=... apply_d25.sh d25e2 KV-D25e2`.
  3. Then ot-delete kw45/bindsrc_kv_d25e2 and kw45/bindcopy_kv_d25e2.
- Watch the bind for two error classes QC hit (KV-CROSSING is checking): K-1 shifting one collective seam group unevenly, and pads past the 15-cycle strap. If they appear, ask KV-CROSSING for corrected rows; do not drop the fall rows.
- Next event: 17-type rls rows (FABLE-FIX-KV-HG-rls-rows-all.json), together with the core-tap v2 + pcsink v2 tree pair (DIE-CORETAP).

## Status 2026-11-20 02:45Z (read this first; supersedes 11-19 21:30Z)
LIVE = KV-D25d (d25d4). D25e (plan a5a8c6b96e5f, sealed manifest dc58066d4f79) is in its strict bind on epyc10 W/d25ebindgate (bindcopy kw45/bindcopy_kv_d25e, started 01:48Z).
- When it is green: on epyc10 run `REPL_HOSTS="epyc8 epyc9 intel1 epyc2" bash seal_bind_dest.sh d25e <d25e tree>`, then on intel2 run `RT=rt/dcd56363d450 HOSTS=epyc8,epyc9,epyc10,intel1,epyc2 BGH=epyc10 BIND_DEST=<dest> LIVE=<d25d4> LIVE_EV=KV-D25d BC=d25e SKIP_SEAL=1 apply_d25.sh d25e KV-D25e`. COORD: ship as is, even though it carries the TRUNK-CHAIN defect from older tools.

D25e2: STAGED (unsealed). Tree kw45/src_kv_pin_eb1e73448bd0_hg12_9939c1eb_t0a56e37_d25e2, plan 9939c1eb044e, tools main 0a56e37ba7f1 (contains 1b95661b75, 8f981deeaa1, e9ad080d925).
- Steps, from W8/build_d25e2.py and then W8/build_d25e2_more.py; report W8/d25e2/build_report.json:
  - LS: hgi_v1 x2 reg_leaf_split u_hst2_t2 a/b/c at x 40. A dry run on the d25d4 RTL gives 1575 -> 807/1063/807.
  - POLY: u_hst2_g polyline [(40,1080),(40,618)].
  - K6: eN lanes +1 (pad 1->2, 64 u_pd2 sites) and tN lanes +1 with a station at (60,1080): 24 lanes, +24.
  - KTALIAS: 1904 kst alias keys dropped on each of the 19 hg/hgi types.
  - FALL: ROWS-KV-SIDECAR-FALL.json bab36e6bd90c, 32 ports (30 K-1/sched-1, 2 K+1/sched+1), net -28.
  - PV: compose_rows --cycles-405, 128 lanes +500.
  - Total vs D25e: 184 lanes, +496.
- Running now on epyc8:
  - W8/d25e2g0pre: early G0/PRE against D25e.
  - W8/d25e2head: elab + r8-prepass on kw45/bindcopy_kv_d25e2_head, with OT_BIND_PLAN_PACKAGE off.
- Next:
  1. `L_TREE=<d25e tree> K=<d25e2 tree> MINPAD=10 EMINPAD=10 bash W8/tables_d25e2.sh W8/d25e2head W8/d25e2tables install` installs r8_ev, the pv pad tables and asbuilt land_r8_extra.
  2. G0 again.
  3. Seal and replicate.
  4. Strict bind on epyc10 (gate_bind_d25.sh). Check that R8_RECHECK changed 0 and REACH short == 0 for pv.
  5. Apply as KV-D25e2.
- After the D25e2 bind, DIE-LEVEL times the bound sidecar in fall form; any further fails go into the next event.

## Status 2026-11-19 21:30Z (read this first; supersedes 15:15Z)
LIVE = KV-D25d = d25d4, applied bind-first 20:39Z. Receipt: lanes/handoff/qwen_kvsys_atomic_apply_1795120745379255041.json.
- Bind of record: kw45/src_kv_pin_eb1e73448bd0_hg10_a1e1d4d0_tb3c4d97_d25d4_bind_1119194238. It is sealed and on epyc7/8/9/10, intel1 and epyc2.
- gen_hosts: epyc8, epyc9, epyc10, intel1, epyc2 (commit 932697f4bae; COORD dropped epyc7).
- bound_trees = [KV-D24 D24c]. The stray KV-D25c entry, which paired the D25c plan with the D24c bind, was removed (110b93ab684).
- Driver: intel2 ~/tmp/kvd23c/apply_d25.sh (env HOSTS, BGH, BIND_DEST, RT; rt/0017 is gone, use rt/dcd56363d450).

D25e: STAGED, G0 running (W8/d25eg0gate, baseline d25d4).
- Tree kw45/src_kv_pin_eb1e73448bd0_hg11_a5a8c6b9_tdcd5636_d25e, plan a5a8c6b96e5f, tools main dcd56363d450 (includes 041f1eefb09 and 83494dde2c1).
- Builder: W8/build_d25e.py, run with SKIP_BINS=1 CT_PC_FROM=W8/d25e_in/coretap_pc/rows.json RD_REPORT=W8/d25e_in/relay_depth/report.json. Log W8/build_d25e.log; report W8/d25e/build_report.json.
- Contents:
  - E2: lef/lib of the signed pc masters on 48 kv3_pc* rows (views installed under kv_pcsplit_views_1119).
  - CORETAP: 140 core taps CHANGE, re-derived on d25d4.
    - The 48 pc rows come from DIE-CORETAP's record rows, i.e. the signed-DB 318/320/196/193 values that the pcsink_fix tree delivers.
    - The E2 liberty mean (pcc 279.5) is not used.
  - RD: relay_depth 285 rows / +330 stages on 15 pv types.
    - The other 258 rows of the 543-row recount (19 hg/hgi types, kt paths) are already carried by KST2 on d25d4.
  - RAWB: hgi_v1 raw branches re-selected with landing_remap resel: rst_rl_124 and rst_rl_117.
  - TAPWIN: KV-CROSSING kv_tile_window_pcsink.json, 4284 rows raise-only, cap 130; 358 ports remain unmet.
  - Latency: 0 lanes moved.
- Not in D25e:
  - BINS: landing_remap has no tap successor for clk_t1 / clk_t19 within 200 um; COORD did not list sink bins.
  - P4 crossing rows: they need a START-TREE-1 sidecar for root pc_WS_2. KV-CROSSING is building it, and COORD said to keep the d25d4 sidecar for now.
  - pv +500 rows: waiting for FABLE-FIX-KV-PV.
- Next: G0 green -> seal + replicate (SEAL_G0=1 seal_rep_d24.sh d25e d24c) -> bind copy on epyc10 -> gate_bind_d25.sh -> R8 refresh if R8_STALE -> sealed bind dest -> apply_d25.sh d25e KV-D25e (LIVE = d25d4, LIVE_EV = KV-D25d).

## Status 2026-11-19 15:15Z (supersedes 14:10Z)
LIVE = KV-D25c, still with no bind of record.
- Wave unblocked (commits 48493e9a566 and 5baac307032): bound_trees = [D24c entry], and kit_rtl.bind_out = the D24c bind_of_record.
  - Before the switch every gen host was SRC-INCOMPLETE. The 07:07 PST tick passes them.
  - Remove this when the d25d4 apply sets the new bind_out.
- Trees d25d4 (manifest ee98d9f486c9) and d25c2 (manifest c81c3c85fa5c) are sealed, replicated and verified on epyc7, epyc8, epyc9 and epyc10.
  - G0 gates: W8/d25d4g0gate (0 errors / 2456 warnings) and W8/d25c2g0gate (0 / 2446).
- Strict binds run on epyc10 kv-d23-compose8/{d25d4,d25c2}bindgate, on the copies kw45/bindcopy_kv_{d25d4,d25c2}. They started 14:57:43Z.
  - The first try failed at elab because the sealed tree was read-only. mk_bindcopy.sh now does chmod u+w on the directories.
- Apply when d25d4 is green:
  - On epyc10: REPL_HOSTS="epyc7 epyc8 epyc9" bash seal_bind_dest.sh d25d4 <d25d4 tree>. This prints BIND_DEST.
  - On intel2: BGH=epyc10 BIND_DEST=<dest> LIVE=<D25c tree> LIVE_EV=KV-D25c BC=d25d4 SKIP_SEAL=1 bash ~/tmp/kvd23c/apply_d25.sh d25d4 KV-D25d
  - BGH records the bind-gate host in binding_proof. Apply d25c2 as KV-D25c2 only if d25d4 is red.
- D25e inputs, all composed onto the applied d25d4:
  - hgi_v1 raw branches regenerated from the d25d4 bound RTL.
  - FABLE-FIX-KV-PV pv rows: compose_rows.py TREE --zero-cycle, plus the ROUTE-PRICED cycle set (128 status lanes +500, astk lanes 0 with distance in the pe2 pad).
    COORD lever 7 (07:50 PST): do NOT use the kv_pv_p2p +464 set (tree4 a04c96f9ee3a), which leaves 32 hops over 405 um.
  - COORD lever 7: d25d4 becomes the bind of record as soon as it is green (bind-first apply), or D25d-prime if that lands first.
  - FABLE H: the t2 split and west-channel chain. The k6 form is a bound-RTL hand edit (fable-fix-kv-hg3/k6/split_t2.py). land_pad_tail_split does not cover the qkh_head_gather_stage, so this needs generator code plus a proof on a d25d4-bound kit.
  - sink bins (W8/d25e_in/sink_bins) and K6.
  - COORD lever 2 (FABLE-PD-KV-0845): E2 pc view rows (epyc7 fable-fix-kv-pv-1119/rows/E2, rows.py apply + --install; lef/lib for 48 kv3_pc hard_cores rows). Purpose: die STA hold measured on the signed pc views.
  - COORD lever 1: KV-PC-HGI-1119 type hold-window rows, taken when they post.
- Open finding (FABLE-FIX-KV-PV, 05:38 PST): pv_v_pads_7p in the live plan is stale by +5 on 488 members, which is likely a lane defect. It is fixed with the pv rows.

## Status 2026-11-19 14:10Z (supersedes 10:50Z)
LIVE = KV-D25c (tree ..._4a40f1db_tb3c4d97_d25c). It still has NO usable bind, and the wave has 0 KV-D25c rows.
- Both strict binds are RED, so do not adopt either.
  - W8/d25cbindgate fails with 2 EMIT errors: kv3_hgi_v1__cl141fc26e raw Q rst_rl_127 and kv3_hgi_v1__cl42bc8b12 raw Q rst_rl_120.
    The bind re-solves the hgi_v1 reset tree around the W1-moved core (258 -> 251 relays), but clock.landing_raw_branches still name D24c relays.
  - W8/d25dbindgate fails with the same 2 EMIT errors plus 30 R8_STALE. Section B moved ectl e*/t1 from bound 5 to 11, and the r8_ev table was not refreshed.
- Fix trees (build_d25.py options NORAWB=1, R8_FROM=<table>):
  - d25c2 = D25c + NORAWB, plan 0b16e17d8005. This is the fallback bind for live.
  - d25d4 = d25d3 + NORAWB + R8_FROM d25in/r8_ev_d25d_sectionB.json, plan a1e1d4d07494. The table changes 168 members, all hg ectl t1/e2/e3 sources, +6.
- Pipeline for each tree:
  1. G0 on its final path (W8/<tag>g0gate).
  2. Seal and replicate.
  3. Strict bind in a hardlink copy on epyc10 (less loaded). Scripts are staged in epyc10 kv-d23-compose8/.
  4. seal_bind_dest.sh BC TREE writes <tree>_bind_<stamp> and replicates it.
  5. On intel2: BIND_DEST=... LIVE=<D25c tree> LIVE_EV=KV-D25c BC=<tag> SKIP_SEAL=1 bash ~/tmp/kvd23c/apply_d25.sh <tag> <EVENT>.
     Step 5 uses rt/0017e104f93a publish_apply. bind_matches runs, then tree and bind_out switch in one commit.
  - Do not use 0017's own bind-first runner: its run.sh lacks OT_KV_HEAD_KST=2 and OT_HCPARAM_ALL=1, and it caps the job at 4 h.
- Next event (D25e):
  - Regenerate the hgi_v1 raw branches from the d25d4 bound RTL (qc_raw_branches_gen.py).
  - Add the t2 split and the west-channel chain (FABLE rows section H), replacing W3 x340.
  - Also: sink bins, PV tap split, K6.
- d25d, d25d2 and d25d3 are superseded: do not apply them. Bind copies kw45/bindcopy_kv_d25c and bindcopy_kv_d25d are red; delete them after use.

## Status 2026-11-19 10:50Z ( supersedes 09:55Z)
LIVE = KV-D25c (unchanged; see 09:55Z). D25d is now rebuilt as tag d25d3. d25d and d25d2 are superseded: do not apply them.
- d25d3 = D25d (K1 342 + K8 + W2 + K2 + section B 56 lanes +6) + PROVFIX, without K5. Base D24c, main b3c4d97, built by build_d25.py with D25D=1.
  - PROVFIX (KV-HUBPV 11-19): kvd23_hr_views_1118/<view>/provenance.json no longer carries any absolute original-kit path.
    - A receipt with sha == export.signoff_sha256 is copied to <view>/receipt/signoff/signoff.json. Only qkd_hr_cdc_hi and phy_pad have one.
    - Every other path is kept as "orig-kit:srv/...", with a provenance_fix note.
    - kit_store.view_refs(kv3_hub_Wi): 22 present / 14 missing on d25d, 0 / 0 on d25d2.
  - K5 (relay_polylines x 310) is DROPPED (COORD / FABLE-FIX-KV-HG k6: middle-channel overload). It is opt-in with D25D_K5=1.
    It is read only by gen_phys, never by bind, R8 or LATCHECK, so the strict bind on bindcopy_kv_d25d (K5 plan 2030743e) stands as the bind proof.
- Next steps:
  1. G0 on the d25d3 final path (W8/d25d3g0gate).
  2. SKIP_SEAL=0 LIVE=<D25c tree> LIVE_EV=KV-D25c BC=d25d bash ~/tmp/kvd23c/apply_d25.sh d25d3 KV-D25d (intel2), after the private hgi_v1 kit.
- D25e: W3 x 340 + K5 are replaced by the west-channel form (FABLE rows section H), plus sink bins, PV tap split and K6.

## Status 2026-11-19 09:55Z (supersedes 07:30Z)
LIVE = KV-D25c, applied on G0 per r712 at 09:50Z. Tree kw45/src_kv_pin_eb1e73448bd0_hg10_4a40f1db_tb3c4d97_d25c, manifest a42f7c77f43b,
plan 4a40f1dbe86d, tools b3c4d97 (rt/current). Receipt lanes/handoff/qwen_kvsys_atomic_apply_1795081781159010419.json.
Gate of record: W8/d25cg0gate, G0 0 errors / 2446 warnings. Candidate W8/cand_d25c.json (mk_candidate_g0.py), driver intel2 ~/tmp/kvd23c/apply_d25.sh TAG EVENT.
- Live bind_of_record is EMPTY. Post-apply bind runs on the linked copy kw45/bindcopy_kv_d25c (.link-base = live tree; mk_bindcopy.sh).
  Gate W8/d25cbindgate (gate_bind_d25.sh): fresh bind.py elab, because the kst2 netlist makes the cached bind9 elab wrong (first try:
  CompositionError missing exact member). Started 09:53Z, about 3 h.
  When green: make a linked child tree (cp -al live + bind files in bind_of_record, .link-base = live), seal, replicate, apply as the
  bind-carrying event, then relaunch the KV kits.
- D25d: sealed, not applied. kw45/src_kv_pin_eb1e73448bd0_hg10_2030743e_tb3c4d97_d25d, manifest f348a8425747, plan 2030743e51da.
  G0 PASS, 0 errors / 2456 warnings. Bind on kw45/bindcopy_kv_d25d (gate W8/d25dbindgate).
  Next: private hgi_v1 kit to GRT TT via kit_wave item_inputs {kv3_hgi_v1__cl141fc26e: src, src_manifest_hash, plan,
  kit_rtl{bind_out = bindcopy bind_of_record, asbuilt}} + item_env OT_KV_HEAD_KST=2 (kit_wave_edit.py).
- 10:15Z: fresh elab PASSED on both copies (RC_ELAB 0); strict binds running, ETA about 12:30Z.
- D25e inputs: sink_bins DONE for 24 KV types (W8/d25e_in/sink_bins/ + REPORT.json; scripts epyc8 /srv/opentallas-scratch2/claude/kv-d23-compose8-bins/),
  FABLE-FIX-KV-PV tap split rows, K6 (hgi i_ectl +1 stage; pad names from the D25d bind).
- Leftovers to delete once older than live (ot-delete): kw45/broken_* and kw45/bindcopy_kv_* after use.

## Status 2026-11-19 07:30Z (read this first; supersedes 05:05Z)
LIVE = KV-D24 (d24c, manifest b951ed387f8c, plan 2862ed5a71bc). W8 = epyc8 /srv/opentallas-scratch2/claude/kv-d23-compose8.
- D25b red at PRE: SCHEMA-UNKNOWN-KEY. I had added note keys to relay_polylines and relay_sites_note. Not a design finding.
- D25c, first build: mis-staged. The foreground ssh died mid-build, and the rerun copied the base INTO the leftover staging dir, so
  the tree had a nested d24c and no tools/s81_head. PRE caught it (TOOLS-SKEW). I cancelled the gate and moved the tree to
  kw45/broken_d25c_nested_0702 (ot-delete refuses: newer than live).
- D25c rebuilt clean (same plan 937d2422ed53): kw45/src_kv_pin_eb1e73448bd0_hg10_937d2422_td6a5a52_d25c. Gate W8/d25cgate
  (ot-run plan bind, started 07:23Z). PRECHECK 1 = TOOLSTALE only.
- D25d build (W8/build_d25.py with D25D=1, MAIN d43ef10787 incl. aae3f7b5ec6) adds on top of D25c:
  K5 W3b polyline x 310 (all hgi_v1 west band types); K8 hgi_v8 cl_i_ectl_Q_N_tN +172.8 (band rects + tap follow);
  W2 lane-pad station off head2_e6 on the other 8 hgi types; K2 relay_sites for the kst parent cells at the 14 kt row
  sites (u_head<h>_g_t_<t>_u_kst<k>.{kp_o[b],kpv_o,gf_o} plus the g_r.r[b] form; unmatched keys are report-only);
  section B on the 7 hg variants (v1, v1p2..p6, v3): eN 6 stations (y 1270 street, E channel x 1235, face pins at (1279,22)) and
  tN 6 stations (y 1270). Lanes eN 0->6 and tN 1->7, so eN stays 1 cycle ahead of tN as built: the hgi pd1 and R8 pads do not move.
  K1/F2 start_stage_raw_resite.py runs on the base bind trees; gen.py latency --inplace (asserts exactly 56 lanes +6).
- K6 is NOT in D25d. The extra hgi stage needs the pad name and order. The binder lands landing pads (u_pd1) after the ring, and
  receiver pads as u_bin_*_pad. Read them from the D25d private hgi_v1 kit, then site the stage in D25e.
- r712: apply on G0. The apply candidate needs bind_out, so the kits wait BIND-STALE until the bind exists.

## Status 2026-11-19 05:05Z (read this first; supersedes 03:25Z)
LIVE = KV-D24 (applied 04:5xZ): kw45/src_kv_pin_eb1e73448bd0_hg9_2862ed5a_tb3e667d_d24c, manifest b951ed387f8c, plan 2862ed5a71bc
(receipt lanes/handoff/qwen_kvsys_atomic_apply_1795064629906020025.json). D24n (no PVFIN) is green too and is not needed.
D25b gate running on epyc8 (ot-run plan bind, about 2.5 h): tree kw45/src_kv_pin_eb1e73448bd0_hg10_7402c516_td6a5a52_d25b, plan 7402c516a256,
gate W8/d25bgate (gate_d25.sh: baseline KV-D24, OT_KV_HEAD_KST=2). D25a (plan 5801ea964612) was killed before its bind (FABLE-PD-STRUCT K2/K3).
D25b = KV-KT-E0 (kst2 netlist/map/compose, HXK 15, kv_head_kst asbuilt record, 16 sited kt rows a type KEPT, relay regex unchanged)
+ kv3_hgi_v1 x2 W1 (core + 2 band rects + tap), W2, W3, W5 (relay_sites). NOT in it: F2 (K1), which waits on FABLE-FIX-KV-HG's writer-start emitter rule on main -> D25c.
When green: seal_rep_d24.sh d25b <d24c basename> (seal_d24.py now enters every bind file; bind_sinks.json may need cp -p + mv
unshare, see d24c), guard_d23.py, mk_candidate_d24.py cand_d24c.json <d24c tree> KV-D24 ..., publish_apply --expect-event KV-D24.
Stop list (COORD): count no hg/hgi kit before e0 and ECTLK q0-q3 are signed off; write no pc rows from HG6-era kits.

## Status 2026-11-19 03:25Z (read this first)
LIVE = KV-D23H: kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h2 (manifest dd671e408127, plan aa3f08ac4159).
D24b NOT applied: strict bind EMIT land_intra_stations dst pvfin_lo has 0 bound leaves (pvfin_lo/hi are inside ONE bound leaf u_pvfin).
In flight on epyc8 (W8 = /srv/opentallas-scratch2/claude/kv-d23-compose8), gates are ot-run plan binds started 01:57Z, about 2.5 h each:
- D24c kw45/src_kv_pin_eb1e73448bd0_hg9_2862ed5a_tb3e667d_d24c = D24 + PVFIN in bound-leaf form (3 nets ahub.fr_* -> pvfin.*, 2 stages
  at shared-fork sites d24in/pvfin/pvfin_fork_sites.json, FR_LEAD hook = 2). Gate W8/d24cgate.
- D24n kw45/src_kv_pin_eb1e73448bd0_hg9_fcea2f4a_tb3e667d_d24n = D24 without PVFIN (NO_PVFIN=1). Gate W8/d24ngate.
- PRECHECK 1 on both = TOOLSTALE kit_common_files.py only (my main 62723dbbdd; the wave runs tools from rt/current). Not a design finding.
Apply when green (prefer D24c): seal_rep_d24.sh TAG src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h2 (seal_d24.py classifies the manifest drift);
intel2 ~/tmp/kvd23c/guard_d23.py TREE HASH epyc7,epyc8,epyc9,epyc10 MAIN; mk_candidate_d24.py cand_d23h2.json <d23h2 tree> KV-D23H TREE KV-D24 GATE ...;
publish_apply apply --expect-source <d23h2 tree> --expect-event KV-D23H.
Cell cap (FABLE-FLOW G): fixed on main 62723dbbdd (kit_common_files.stage writes KIT/CELL_WAIVER from the gen env); rt/current carries it.
D25 (COORD 11-19): W8/build_d25.py BASE EVENT MAIN TAG on the applied D24 = KV-KT-E0 (kst2 netlist/map/compose, HXK 15, relay regex,
kt DEMAND rows dropped, asbuilt kv_head_kst; OT_KV_HEAD_KST=2 needed by the boot-image compiler) + kv3_hgi_v1 W1/W2/W3/W5
(W5 = plan relay_sites on the 32 u_pd1_i_ectl_Q_N_eN_<b>.q, an existing generator form; sites obstacle-clear). Inputs W8/d25in.

## Candidates (all built from the live D22 tree, manifest d988db9486e2, plan 23c87c42a4e9; tools/common_flow + rtl/lib/ot_dp_efault.sv from main eefb7e36eb6)
- D23  kw45/src_kv_pin_eb1e73448bd0_hg8_add04d1e_teefb7e3_d23  plan add04d1e8a2d asbuilt da56e1cd818c; gate d23gate/
  = tail split types kv3_pv.* (only under-matching ^-string in plan+asbuilt) + KV-D23-PC composer re-run on D22 (pc/ : 68/72/72 taps,
    fclk edge splits, reset/collector re-solve, sidecar 9704beb258d4) + efault EQ_PIPE_V 10 rows (plan_cell_conns_v36) + hub_Wo 11 cores.
- D23b kw45/src_kv_pin_eb1e73448bd0_hg8_2cc1cff4_teefb7e3_d23b plan 2cc1cff49074; gate d23bgate/ = D23 + 59 PV raw-stage band rows
  (band/band_rows.py, flags 3/3 KV-HG6 literal-local-reset CLAND failures; D22 left v4 TNQN_b stage 2 at y 1516.32).
- D23c = D23b + KV-D23-REACH rows (rows_proof.json: reset_replicate rsync on 36 types, reset sink_stages, tail split pipes:true);
  needs the reach code on main (my squash of claude/kv-core-reach-1118, conflicts with BIN-COPY resolved by hand; ot-push-main).
## Scripts
build_d23.py MAIN TAG (in/plan_TAG.json, in/asbuilt_extra_TAG.json), gate_d23.sh TREE OUT, seal_d23.py TAG, seal_rep_d23.sh TAG,
mk_candidate.py (from the KV-D22 candidate); intel2 ~/tmp/kvd23c/{guard_d23.py, launch_gate_when_staged.sh}.
Apply: python3 -I rt/current/tools/autopilot/publish_apply.py apply --candidate C --expect-source LIVE --expect-event EV --lane KV-D23-COMPOSE
## D24 (next): hub_C split (KV-D23-HUBC), die clock node re-site, pvfin stations, hub_Wi host rows (KV-HUBWI-HOST-rows-d23.json,
writer main 04df4c77f065), pc core RTL for qkd_kvs_pcc/pcf(+_h_head_p) (portbind/LEC gap; bind + kits not affected), light ring key.
## Status 15:15Z
D23 + D23b strict binds running on epyc7 (ot-run plan bind). ot-push-main of reach squash (wt branch kvd23-reach 440bf7477b6) running tests (push3.log).
D23c staged inputs: in/plan_d23c.json (band + reach + ring2 lite/narrow keys on hub C/Wi/Wo/Ei/Eo), in/asbuilt_extra_d23c.json.
Apply order (KV-HG-OPUS): D23 when green -> D23b -> D23c. Rider rows (kv-pv-rider) not yet in any candidate.
## Status 16:45Z (after D23/D23b FAIL)
BASE FOR MIRRORS (live, applied): /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg7_23c87c42_t5144e08_d22
  manifest d988db9486e2, plan 23c87c42a4e9, asbuilt efad37e95d45, r8 57bb66595819 (event KV-D22). Updated here when D23e/f/g applies.
D23/D23b FAIL: 1 EMIT kv3_hub_Wo raw Q rst_rl_214 (hub_Wo cores change the solved reset tree; lane KV-HUBWO-RESET).
In flight (epyc7, no hub_Wo, NO_WO=1 build_d23.py): D23e (D23 minus hub_Wo, tools eefb7e3), D23f (band + rider), D23g (band + rider + reach + ring2 keys, main e8731b01bcf).
D24 prep on main: 05f7de74d0c (hard RSTREP rings keep reach reader START), db1854527ce (clksite_resite.py; hub_C S 68.31 um).
hub_C pre-proof gate: epyc7 kv-d23-compose/hubc/gate_c (rows4 = KV-D23-HUBC rows3 + resite, D22 mirror, tools main e8731b01bcf).
## Status 18:00Z
Gates (epyc7, all PRE PASS, strict binds running, ot-run --crit since 17:07Z): d23egate, d23fgate, d23ggate, d23hgate (D23h = D23g + FABLE-FIX-KV-HG
relay_mid keys on 17 hg/hgi types, main 0c3fb152c30, tree kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h plan aa3f08ac4159), hubc/gate_c.
Apply rule: most complete green of g > f > e first (expect-source D22, expect-event KV-D22), then D23h on top (expect-source = applied tree).
pvfin (RULING KV-HG-OPUS 18:0x): NO pvfin station rows from this lane. ahub fr_rz -> pvfin rz is 0 kept stages, per-bit 1,084 / 1,176 um
(lo / hi, needs k=2 at 405 um), but pvfin faults on an rz off its calendar slot (qkd_pv_fin_s8 l.144) and pvfin sits in the u_kvs_attn
static loop (pvfst D45 -> pvfin -> fin D46, RETIRE_STATIC). Lane KV-PVFIN-CAL moves the attn_root calendar R slot +2 + 2 rz stations and
writes ~/coord/lanes/handoff/KV-PVFIN-CAL-d24.json; it drops into D24 last. Fallback re-floor next to ahub: 0 free sites <= 500 um today
(blocked by taps / internal station regs / collector relays; epyc7 kv-d23-compose/hubc/pvsite*.py).
pc RTL (D24): sources already in every tree (results/kv_host_regen_1/rtl_rf3/<m>/<m>.sv, on main); the gap is only asbuilt portbind_files.
Proof: epyc8 /srv/opentallas-scratch2/claude/kv-d23-compose8/pcpb (strict portbind on D22 + 4 pc tops in portbind_files; ot-run from intel2).
D24 recipe (base = applied D23 tree): hub_C rows (re-run kv-d23-hubc/d23_hubc_rows.py on the applied plan + tools/die_plan/clksite_resite.py)
+ hub_C clock.landing_ring_lite/narrow (KV-RING2-LIGHT-keys-d24.json; hard rings are wide, LITE only <= 4 bits, NARROW keeps hard params)
+ hub_Wi host rows (KV-HUBWI-HOST-rows-d23.json apply_recipe, writer main 04df4c77f065, views epyc9 kv-d23-hubwi/views_src)
+ 4 pc portbind_files + hub_Wo (KV-HUBWO-RESET-d23.json when green) + pvfin (KV-PVFIN-CAL-d24.json) last.
HUBC leftovers now mine: 6 exported ring/dly masters, kv_dly_w512_d46_b4fbd in GRT (KV-D23-HUBC dead).
## Status 19:05Z -- KV-D23 APPLIED (D23f)
LIVE BASE (for mirrors / D24): /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg8_e21a54ae_teefb7e3_d23f
  manifest ec75f13b9d2b, plan e21a54aebe16, asbuilt da56e1cd818c, event KV-D23, hosts epyc7/epyc9/epyc10 (epyc8 disk floor, not replicated).
  receipt lanes/handoff/qwen_kvsys_atomic_apply_1795034096412178751.json.
Next on top (expect-source = D23f tree, expect-event KV-D23): D23h2 (= D23g2 + FABLE-FIX-KV-HG relay_mid keys on 17 hg/hgi types;
  tree kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h2, gate epyc7 d23h2gate) or D23g2 if h2 fails.
  D23g/D23h: NOT to apply (ring RTL without LITE; D23g bind BIND_PARAM_UNKNOWN). build_d23.py EXTRA_PATHS adds the ring RTL.
D24: epyc8 kv-d23-compose8/build_d24.py BASE EVENT MAIN TAG (inputs d24in/); needs the HCPARAM entry (main 61164324139e) in tools.
pc portbind proof: epyc9 kv-d23-compose8/pcpb (epyc8 below disk floor). d46 dly rebuild: epyc10 kv-d23-compose/dly_h1.
BOUND-PARAM-1 (main 60fe7ab5499): run tools/die_plan/bound_param_check.py --tree T --rtl-dir T/.../bind_of_record/rtl after each gate.
After the first D23 hub/pv kits: post native hub_Wo cell count (hub_Wo split held, so from D24) and NEED-STATION counts on pv v2/v6 kits.

## Status 21:50Z -- KV-D23H APPLIED (D23h2 on D23f)
LIVE BASE: /srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0_hg8_aa3f08ac_t0c3fb15_d23h2  manifest dd671e408127, plan aa3f08ac4159,
  tools 0c3fb152c30a, event KV-D23H, hosts epyc7/8/9/10 (tree_check full_ok), receipt lanes/handoff/qwen_kvsys_atomic_apply_1795037429350356690.json.
  Content: D23f + reach rows (reset_replicate rsync copy_depth 3 = FABLE fix #3) + ring-lite keys + FABLE fix #1 relay_mid keys (17 hg/hgi).
  D23f (KV-D23) re-replicated to epyc8, tree_check full_ok 4 hosts. Candidate maker for stacked events: epyc7 W/mk_candidate_stack.py.
  Seal lesson: seal_rep_d23.sh continues after RC_VERIFY 1 (it replicated anyway); h2 bind_sinks.json had nlink 2 from outside -> cp -p + mv.
D24 (building epyc8 kv-d23-compose8/build_d24a.log, TAG d24a, base D23h2, main 795a5223111):
  1 hub_C split  2 hub_Wi host  3 pc portbind_files (+ portbind_prefer mu_qwen_20261018 collected_mu: pc proof AMBIGUOUS fix, rerun epyc9 pcpb)
  4 PVFIN-CAL: asbuilt.land_intra_stations 6 nets ahub.fr_* -> pvfin_{lo,hi} k=2 (bind_intra_stations.py; plan core rows get NO RTL on KV),
    sites d24in/pvfin/pvfin_intra_sites_d24.json (2 stages re-sited off pvfin_hi / pll, hops <= 398.7), FR_LEAD derived by
    r8/kv_pv_col_regen_d24.py (declare qkd_kvs_attn_fl FR_LEAD 0). RTL qkd_kvs_attn_fl_r17 + qkd_kvs_attn_r17 from main.
  D_RL caveat: real boot image boot_v36/boot_ages_asbuilt.json D_RL 93 / D_QK 57 / F_DLY 55 / FIA 113 (lane scanned 235/3/95/255): KV-PVFIN-CAL re-scan asked.
  Next: gate D24 (bind_fast precheck -> strict bind -> LATCHECK -> G0 + bound_param_check + bind_intra_stations.json / param_regen FR_LEAD 2 read-back).
Not in D24: FABLE fix #2 (28x2 parent kt + 2 e0-local + astk calendar +2): NEEDS-LANE KV-KT-E0 (head RTL ot_qkh_head_native_r4 kst D=2 x16
  lanes, astk cal +2 + sim, e0 re-harden 216x216, bind_intra_stations bit-slice net form); hub_Wo split (KV-HUBWO-RESET).
d46 dly (epyc10 dly_h1): still NOT SIGNED, FF hold -5.75 ps even with margins 30/25.

## Codex takeover 2026-11-20 03:38 PST

- D25e3 plan 983443ee7b6d, manifest 5705fa378e1c: G0 0, BIND 0, LATCHECK 2404/2404, BPC 0 (67 modules, 570 params), R8 unchanged from D16. Exact ECTL die-scale geometry looked, results/geom_review/kv-d25e3.md. Bind of record `..._d25e3_bind_1120113734`, 183/183 referenced inputs on E8/E9/E10/I1/E2. Guarded apply intel2 PID 4043825, `~/tmp/kvd23c/apply_d25e3.out`; it expects KV-D25e. Keep bindcopy_kv_d25e3. v6 route stop on D25e and D25e3 exact keys 7ee05d920649 and 57680a9ac020.
- KV-D26 pv_v6: E8 `kv-d23-compose8/d26_raw`. Coalesce exact placed reset chains, 83→70 branches and busiest literal stage site 8→1 on old geometry. Phase/role proof 83/83 for v6 and v6n; negative control rejected. 300 µm raw replay must rederive reset first. Fresh v6 depth 12, internal max 275 µm, local arst_n→tap release clocks 10→13, zero datapath cycles. Initial 83/83 replay reached minimum 301.752/300.324 µm actual final pin hops for ft5/ft6 because core inset was unpriced. Terminal-budget candidate fixes that; focused replay 300.0 µm on both; all-role replay queued (intel2 form_pv6_raw_terminal.log). Private source patch kv_d26_raw_replay.patch d7cfa63d1e08. No D26 route launched. Recompute whole-die boot schedule when all 16 types replay; 14 require longer reset depth than the old plan from lower bounds.
- D26 v1n is a separate Form C proof representative (168103 unlatched bits on old census). Actual bound v1/v1n/v8 candidate census queued, intel2 pv_form_c_census.log. v8j 4_1 CTS on E10, CpuShares 10240; restoration watcher intel2 PID 3406901. v8h DPL. v8k uses exact unchain + 25 ps repair target and its existing E7 chain.
- HG: kR E9 GRT 3581 at iter5, 1223 iter10, 195 iter20, iter24 running. k13i/k13ci (proposal 3/control) Intel2 3_3, h1/h2 (fixed/moved krsp) 2_1. h2 routing-only next requires fresh die clock and pin review. D26 section N + proposal 3 remains conditional on k13 proof.
- PC: Form A four cores queued E7, signed-parent pilot after fresh views. D25e3 plan macro sites already oriented-lattice aligned (kvpc2 x552.960); measured x552.576 is an actual placement issue. Use M7 top PG publish to die-level M8 via PG-CORECONN-3 under methodology 12.1a; no new tile M8. The old HG6 pc attempt on E10 TT -1731.61 was a route triage failure; existing new D25e attempts continue. hub_Wi SRAM row remains in D26. v6 stop is physical, while pcc/pcf and cland invalid synthesized kit_rtl rows were fixed by the partition-type filter. pvfin WAIT-CHILD has its two view rows in D25e3.
- R11 kv3_sys_SD selective TX write-select reset D-term pilot E10 `kvsysc-1119-lane/fdi_tx_wsel_r11`: 916 lockstep checks, 16 asynchronous flushes, negative control rejected at check 16, no cycles. Sized STA dump and real reviewed route proof still pending. R11 io_ft_v1 +1 station item remains pending sized E9 receipt.

## 2026-11-20 05:00 PST KV-D25e3 live

Applied with publisher df1b461e4b13, RC_APPLY 0. Receipt qwen_kvsys_atomic_apply_1795179529808598494.json. Active plan 983443ee7b6d and source manifest 5705fa378e1c. Explicit bind `..._d25e3_bind_1120113734` passed 56/56 and identical digest fb3856e31bdb over 60 files. All six verified gen hosts remain active. epyc7 joined live D25e during preparation, so the apply replicated source there and we copied the exact selected bind plus all 183 references. The live config points directly to the sealed selected bind. The earlier mkdir refusal is retained at intel2 ~/tmp/kvd23c/apply_d25e3.out.refused-native-bind. The E8 private preseal fallback passed and stayed private.

Full exact geometry render reviewed in results/geom_review/kv-d25e3-exact.png, sha 6b98a5c790d6. The live type cache has 56 types. Hub C no longer has a provisional dependency on pvfin because the signed core view is present. The two former false cland partition types appear as signed cores only. pv_v6 remains stopped on failed geometry block 57680a9ac020, pending D26.

D26 preview inputs on E8 are in d26_raw. The first package d26_pv_raw_previews_verified_roles.json covers six exact types and 388 distinct roles with zero data cycles. Further previews v3n/v4/v4n passed. Both base pv and v1n retry through actual ring geometry and constrained-role-first placement. Their physical reroute and rate change require the next daily exact bind and boot model. The v8j/v8h live CTS results exposed a remaining shared east astk pad-trunk timing problem. The exact location probe is queued on epyc10 under the existing fable-fix-kv-pv-2140 lane.
