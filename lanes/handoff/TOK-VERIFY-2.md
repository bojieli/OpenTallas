# TOK-VERIFY-2 lane handoff (refreshed 2026-11-12 ~08:5x PST)

## 1 Scope
Functional token verification of RTL that lands or is about to land:
(a) ds_native bc62f30f4e: DONE (on main via ROOT-MERGE-59 train Z).
(b) BUS-GEAR-2 S81 x feed 2:1: gear TOK-VERIFY (A/B geared vs ungeared twin, same r12ng base) + COORD-approved compiler x cadence knob.
(c) S81 token check on main after every merge train touching RTL.

## 2 Worktrees / branch
- intel1:/srv/opentallas-scratch2/claude/wt/tok-verify-2 : detached main checks (now adf10c2724821). Git dir intel1 .../tok-verify-1/repo.
- intel1:/srv/opentallas-scratch2/claude/wt/tok-verify-2-xcad : branch claude/tok-verify-2-xcad2-1112 @5460102b71 (PUSHED to hub; off main 8eeefa4716dd).
  edc97692b6 = OT_XS_X_CADENCE knob (xs_calendar.py, xs_field_calendar.py, xs_wqb_die.py, test_xs_x_cadence.py); 5460102b71 = OT_XS_X_CADENCE_FLOOR bound|expected.
- epyc9:/srv/opentallas-scratch2/claude/wt/tok-verify-2-gear : local clone @096abb5649 = xcad2 5460102b71 + merge of claude/bus-gear-1-xint-1112@877cfc14f1 (NOT pushed; test tree only).
- epyc8:/srv/opentallas-scratch2/claude/wt/tok-verify-2-pt : sparse clone of the branch for pytest (intel1 has no pytest).
No uncommitted files.

## 3 Running jobs (ot-run; check with `ssh intel2 'tail ~/tok-verify-2-logs/<name>.otrun.log'`, DONE line = finished)
- main_adf10c27 (intel1): S81 check on main adf10c2724821. run dir intel1:/srv/opentallas-scratch2/claude/tok-verify-2/main_adf10c27.
- gear_twin_s (epyc9): ungeared twin, s87bind asbuilt_f_s87r12 / out_r12ng / bsrc4_r12ng, cadence 1, schedules reused (SCHED=v1/sched_main_d767/sched). run dir epyc9:/srv/opentallas-scratch2/claude/tok-verify-2/gear_twin_s.

## 4 Scripts (no watchers)
- intel1 .../tok-verify-2/s81tok.sh, s81tok_v2.sh (TS5 defaults; env MAN BIND SRCBS PLANREL REFCC).
- epyc9 .../tok-verify-2/s81tok_v3.sh (host independent: VREF=.../tok-verify-2/v1 GBQ=.../v1/gb_provider_qualification.json REFCC=.. SCHED=..(skip FSA) MAN BIND SRCBS; args <name> <code tree> <lat>).
- queue post helper (localhost scratch post.sh): append to ~/coord/lanes/COORD-REVIEW-QUEUE.md + coord-commit.sh.

## 5 Results (all posted)
- main d767dc851b PASS (compose AR 769.6 / MTP 2700.0 = reference). main 8eeefa4716dd PASS (0 prog json differ).
- Gate 1 PASS: cadence 1 on edc97692b6 = 0 prog json differ vs main_d767 (xcad_c1).
- Cadence 2 BOUND (xcad_c2): periods gu 145->216, down 127->190, wo_b 128->192, wq_b 127->190, wo_a/router 234->298; field end +8558 (L0) / +9262 (L2/L14/L20); AR 615.4 (-20.0%) mean / 613.0 max; MTP 2219.9 / 2212.3.
- Cadence 2 EXPECTED (xcad_c2e): COMPILE FAULT on L0/L2/L14/L20, shared calendar pack base 4424 > 4096 ROM rows.
- r12ng trees: frame_schedule_asb KeyError 'go_tag' (both arms) -> workaround SCHED reuse.
- Tests: test_xs_x_cadence 9/9; with test_xs_calendar_pack + test_bf_col_form + test_station_depth 27 pass (epyc8, edc976); xs_field_calendar selftest 23/23 at c1 and c2.

## 6 Next steps
1. main_adf10c27 DONE -> PASS if CC all rc 0 and "prog json files differing: 0" x4 vs main_d767 -> post RESULT (sha adf10c2724821).
2. BUS-GEAR-2 posts that r12ng/out_bind re-bind is done (out_bind/rtl exists) -> launch from intel2:
   B=/srv/opentallas-scratch2/claude; L=$B/tok-verify-2; W=$B/wt/tok-verify-2-gear; G=$B/bus-gear-2/r12ng; T=$B/s87bind
   ot-run --mem 96 --threads 16 --hosts epyc9 --dir $L --stage $L --stage $W --stage $G --stage $T -- env VREF=$L/v1 GBQ=$L/v1/gb_provider_qualification.json REFCC=$L/gear_twin_s/cc SCHED=$L/v1/sched_main_d767/sched MAN=$G/asbuilt_xg.json BIND=$G/out_bind SRCBS=$G/bsrc_xg OT_XS_X_CADENCE=2 OT_XS_X_CADENCE_FLOOR=bound bash $L/s81tok_v3.sh gear_xg_s2 $W $G/lat/s81_latency.json
   (if BUS-GEAR-2 changed the TX again: `git -C $W fetch origin claude/bus-gear-1-xint-1112 && git -C $W merge FETCH_HEAD` first.)
   PASS rule: CC all rc 0 with the same op/status counts as gear_twin_s; only prog/xs calendar files differ; field-end delta per layer -> price x43 AR / x44 MTP on 769.6 / 2700.0, plus the declared +1 word edge per geared x hop. Post RESULT cc BUS-GEAR-2, DIE-S81-88.
3. Post READY for claude/tok-verify-2-xcad2-1112@5460102b71 -> COORD + ROOT-MERGE-60 (files: tools/s81_dv/layer_prog/{xs_calendar,xs_field_calendar,xs_wqb_die}.py + test_xs_x_cadence.py; tests above; gate 1 PASS; default cadence 1 byte-identical).
4. KV vN (52a724781a52) and later trains: when main moves with RTL/compiler changes, `git -C intel1:wt/tok-verify-2 checkout --detach <sha>` and run s81tok_v2.sh main_<sha8> with REFCC=main_d767/cc (see 2026-11-12 queue posts for the exact ot-run line).
5. STATE every 60 min.

## 7 Open
- ASK -> BUS-GEAR-2 (08:4x): tell me when r12ng/out_bind re-bind is done and which TX sha.
- Design input -> COORD/BUS-GEAR-2: the bound rule (-20%) is the only cadence-2 form that compiles; cheaper needs the frame-bench P sweep + a pack that fits 4096 rows, a bigger calendar ROM, or gearing down/wo_b/wo_a only.
- S81-FRAME-FIX-1 / DIE-S81-88: frame_schedule_asb go_tag KeyError on r12ng trees.

## 8 Gotchas
- ot-run refuses paths in the command outside --dir unless --stage'd.
- Frame roots use cp -al of 35-48 GB trees; frame_root unlinks before writing (safe for the source trees). Never edit DIE-S81-88's bsrc4_* trees.
- compose_tok_ds ignores cadence/word_cycles; the per-sha signal = compile rc/op counts + cdiff calendars; price = field-window end delta x layers.
- pytest missing on intel1; use epyc8 sparse clone (sparse-checkout add paths that tests read).
- coord-commit.sh prints a long git status when another lane commits at the same time; it is still on origin (check the count line).
