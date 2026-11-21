# TAP-GRID-R2 handoff (successor of TAP-GRID-2130; started 11-21 06:4x UTC / 22:4x PST)
Read lanes/handoff/TAP-GRID-2130.md for the method (tap grid plan key clock.tap_grid, OT_TAP_CONVERGE, post-hook read).

## Tasks
1. KV pv v8c r2: epyc7 oth-ubuntu-3155521-1795241969 (v8c_conv/kv3_pv_v8), in CTS hooks at 06:41 UTC (baseline hooks 6.6 h). Target tap spread < 100 ps before D27 pv volume. Post -> KV-PLAN-R3.
2. leaf t60_conv / t60_convR: epyc10, both queued on memory (admits 0 GB) at 06:41 UTC; ot-heavy waiters pid 2321660 / 2339672.
3. Lever-3 real proof: one S81 kit regenerated with clock.tap_grid on (pitch <=300, bank taps >1000 sinks), private bind, to CTS. Not started.
4. Audit kits generated in 054ac247c4 -> 47295f4adc for OT_TAP_CORE_DIRECT=1 without the CORE-DIRECT block -> FABLE-FIX-KV-HGI. Not started.

## Status
- 06:4x UTC: lane up; LANE-STATUS row TAP-GRID-2130 -> TAP-GRID-R2.

## Lever-3 proof: S81 leaf t39 (11-21 07:xx UTC)
- Work: intel1 /srv/opentallas-scratch2/claude/tap-grid-r2/t39 (hub copy of spec in intel2 same path /wave/spec.json).
- regs: epyc9 tap-grid-r2/t39/regs/t39_regs.json = tap_resolve --dump of J5 t39 a3 3_place.odb (44,253 registers, 27 macros).
- Plan: J5 plan_h2_2249.json (sha 913a7026) + t39 tap_resolve.apply_density(span 300, target 1000): added_taps 39 -> 82 (taps 55 -> 98), max load 1000, 0 over span;
  clock.tap_span_um 300, clock.tap_grid {pitch_um 300, bank_sinks 1000, pair_um 200} (no regs key: taps already in the table, so bind sees the ports). delta: t39/tap_grid_delta.json.
- Tree: t39/src2 = hardlink copy of kw45 src_s81_pin_3c913dbdfb23_d8j5_1117_work, tools + common_flow from rt f3db2d0e628f (= main tools), plan replaced by rename (S untouched, sha checked).
  (t39/src = symlink tree, abandoned: bind dead-input proof path check resolves symlinks.)
- Bind: t39/bind.sh (strict --all-gaps + LATCHECK), out t39/bind, log t39/bind.log; try1 failed on the symlink tree (bind_try1.log).
- Next: kit via kit_wave.py run-item wave/spec.json (copy of the J5 a3 spec: private src/plan/bind/work, kit_snap off, no future_lec, rt f3db), then tg_cts-style CTS, read post-hook vs baseline.
- Baseline J5 t39 a3 (epyc7 ot-jobs/ot_s81sl_leaf__t39-route-loved-redfish-1218124-1795237605): OT_CTS_POST_TIMING setup -73.73 / TNS -1278.1, hold -75.14 / -89488.2; 79 taps; clk_t6 6,092 sinks skew 62.3.
- CORE-DIRECT audit: intel1/intel2/epyc7/epyc8/epyc9 0 bad (config.mk newer than 11-21 04:00 UTC with OT_TAP_CORE_DIRECT=1 and tap_balance.tcl without tb_cdirect); epyc2/epyc10 rescanning.

## 07:4x UTC
- t39 chain unattended: intel2 systemd user unit tgr2-t39-chain runs /srv/opentallas-scratch2/claude/tap-grid-r2/t39/chain.sh (log chain.log there):
  wait bind (intel1 oth-ubuntu-1025678-1795244779) -> kit_wave.py run-item wave/spec.json (log wave/run_item.log) -> DO_NOT_COUNT + tg_cts.sh CTS on intel1 (kit otrun_cts.log) -> greps.
  Posts on bind / place failure. Read 4_1_cts.log OT_CTS_POST_TIMING + OT_TAP_INSERTION vs the J5 a3 baseline above.
- CORE-DIRECT audit DONE: 7 hosts, 1,420 recent kits, 0 missing the block (posted to FABLE-FIX-KV-HGI).
- Reader units (intel2 user systemd, logs /srv/opentallas-scratch2/claude/tap-grid-r2/<unit>.log): tgr2-read-v8c (epyc7 oth-ubuntu-3155521-1795241969),
  tgr2-read-t60 (epyc10 ot-run pid 2320712), tgr2-read-t60R (epyc10 pid 2338565). Each ot-waits, then posts the raw OT_CTS_POST_TIMING / OT_TAP_CONVERGE /
  OT_TAP_INSERTION lines to lanes/posts/TAP-GRID-R2.md. The verdict vs baseline and the rows (KV-PLAN-R3 pv spread < 100 ps; J6 before 11-21 13:00 PST else J7; QC-PLAN-R8 V2) are still lane work.
- ETA: v8c ~13:00 UTC (baseline hooks 6.6 h); t39 bind ~10:00 UTC, then gen + place + CTS: likely after 16:00 UTC, so J6 (13:00 PST = 21:00 UTC) is tight.

## COORD 11-21 (successor names + scope)
- Rows go to: KV-PLAN-R4 (not R3), S81-J6-ASSEMBLY-R2 (J6 only if before 11-21 13:00 PST, else J7), QC-PLAN-R8 (V2), and the t39 result also to FABLE-FIX-S81-LEAF-R2.
- pv tap result applies to the D28 split halves, not v8: the v8c r2 read is evidence for the D28 halves; post it to KV-PLAN-R4 framed that way.
- Lane keeps a run_in_background waiter on t39/chain.log (CHAIN_DONE / BIND_FAIL / NO_PLACE / cts rc=).

## 11-21 09:xx UTC
- t39: private strict bind PASS (errors 0, LATCHECK 0; bind try2 on the hardlink tree). Chain2 (unit tgr2-t39-chain2, src_manifest off in spec) is at place; kit RTL carries the new ports (clk_t97). CTS next.
- FABLE-VISUAL-0030 cause 5 (COORD ask): main 17960d767b = clock_taps.tcl CT_CASCADE ejection chains (OT_TAP_CAP_CASCADE), CAPACITY WARN, tap_grid caps at bank_sinks + turns cascade on,
  clock.tap_cap_cascade; test_tap_cap_cascade.py; mock repair of test_clock_taps_cap_recheck/groups (ord::get_db). Posted to FAM-S81-COL-R2 + FAM-KV-IOPC with rows
  (col: tap_grid or tap_max_sinks 1000 + cascade; pc_v3: tap_grid regs = bank taps, 67,193 sinks on 39 x 1,200 cannot fit).
  The t39 proof kit was generated on rt f3db2d0e628f (before 17960d767b): no cascade in it (its plan cap is 1000 already).

## CODEX notes 11-21 02:24 PST

- t60 and raise100 both failed the inherited rollout comparison on FF hold. Control TT/FF -222.55/-57.22 ps, r2 -207.06/-68.54, raise100 -206.83/-93.09. No volume rows. 
- t39 current placement is actually running on intel2 in sealed job ot_s81sl_leaf__t39-place-tolerant-swine-775262-1795253535, with output copy-back to intel1, and the inherited chain follows to CTS. Placement checkpoint review rendered and examined, PASS-COND for this isolated proof; see results/geom_review/tap-grid-r2-t39-1121.md.

- t39 final detailed placement passed. Inspected the copy-back kit's final layout. The inherited kit's Tcl has the same missing tb_cdirect/tb_cdmax globals fixed by main 5294e088f553. A fresh cp -a replay adds only that declaration and is in CTS on intel1, oth-ubuntu-2231504-1795257312, t39/cts_fixed_5294/kit. The original kit and its geometry job were untouched.
- KV hroot D28 candidate consolidates 12 sparse west taps to 5, preserving 200 um planned reach on the old placed registers and reset preview depth. See results/geom_review/tap-grid-r2-kv-hroot-1121.md.
- CT_CASCADE correction landed e75e9f9ab9 at 02:46. Checks live span on both receiving taps before each paired move, including two runtime cases where the initial allowance admitted opposite extrema. Source 66aa62d1321; gate GREEN 25/25, five matched main baselines.
- Span-box incremental refresh source 2182d2a6928 on claude/tap-grid-r2, same normal GREEN 25/25. The exact span cache refreshes changed bins before the next pass. 36-tap/18,000-sink synthetic replay produced identical assignments/logs/teardown verdict, 9.31 to 7.20 seconds. Candidate READY.
- t39 actual 3_place prehook diagnostic readback, intel1 t39/new_sink_geom/clock_phase. Out-of-limit boxes 0 nearest -> 39 group/follow -> 71 cap/refollow -> 75 pair/final. Final tap t67 load 1,449, limit 1,000, W+H 538.1 um. Counterfactual restoring only reset clocks to nearest reduces over-span count 75 to 9 but has no STA qualification. Logic issue is outlying reset flops re-hung at their descendants, not the added tap geometry. Explicit terminal-only follower recipe probe in sibling terminal_followers limits regex to 122 unconsumed relay outputs of 737 and drops first-phase over-spans from 39 to 1; final physical timing TBD.
- Terminal-only t39 exact geometry replay finished with 8/98 final boxes >300 um vs 75/98, max 355.2 vs 670.95 um. No span violations before the short-pair pass. t67 remaining 1,447 sinks are all one VP write-bank group pinned to clk_t67 by /work/vpw_bank_clock.tcl (906 XR, 224 SLR, 317 other). Extra nearby taps cannot take members without changing the clock cohort design. Looked at terminal-vs-control physical assignment plot, then launched same-checkpoint private CTS-only comparison, intel1 oth-ubuntu-2825559-1795258453. Timing and bind qualification remain pending.

## 11-21 11:4x UTC (Claude resumed after Codex handback 03:32 PST)
- Codex landed (lane name TAP-GRID-R2): e75e9f9ab9, cf5df768462 (tap span / pass), claude/tap-grid-r2 @930a4abd798 merged (main 9c0d61b2258; pair-plan span boxes seeded from fixed sinks; t39 replay 0/98 over 300, max 299.970).
- t60 conv r2 / raise100: FAIL on FF hold (posted 02:18 PST); off J6/V2. KV v8c r2 still in CTS hooks (reader tgr2-read-v8c active).
- t39 CTS proofs running on intel1, each with a hub reader that posts raw post-hook lines:
  base new ports (chain2, attempt_1 kit) oth-ubuntu-2505215-1795257884 -> tgr2-read-t39base
  cts_fixed_5294/kit oth-ubuntu-2231504-1795257312 -> tgr2-read-t39fixed
  cts_terminal_followers/kit oth-ubuntu-2825559-1795258453 -> tgr2-read-t39follow
  cts_terminal_pair_span_seeded/kit oth-ubuntu-3880037-1795260472 -> tgr2-read-t39seeded (Codex's current form)
- t39 r3 submitted: src3 = src2 + clk_t98 (881.28, 635.04) for the t67 fixed VP writer overload (1465 / cap 1000; 541 other VP sinks within 145 um), tools rt 7ff721a00978 (cascade + span fixes).
  Unit tgr2-t39-chain3 (hub), log t39/chain3.log: bind3 (intel1, t39/bind3.sh) -> run-item wave3/spec.json -> CTS -> post.
- Baseline (J5 t39 a3 post-hook): setup -73.73 / TNS -1278.1, hold -75.14 / -89488.2. Rows only if a proof is no worse on setup and hold: S81-J6-ASSEMBLY-R2 before 13:00 PST else J7, FABLE-FIX-S81-LEAF-R2, QC-PLAN-R8 (V2), KV-PLAN-R4 (D28 halves).
