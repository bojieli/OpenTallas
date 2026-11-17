# S81-TYPES-R strip fork (strip leaves, bg_bare, t34 model, t43); started 11-16 17:1x PST

Parent lane S81-TYPES-R (columns + IFN0 are NOT here). Predecessor FABLE-FIX-S81-CONG.md (read its Codex handback section).

## bg_bare (DONE)
- Branch claude/s81-types-r-bgbare-1116 @11bfca8d9c9 (clone epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/lane). +9 lines in tools/die_plan/kit_bus_bitgroups.py, test_kit_bus_bare_alias.py (6 tests), fixture kit_bus_t34_current819.sv.gz.
- GATE main=34781ed8bbc pass=3/3 GREEN. READY posted (FABLE-FIX-S81-CONG post 266cbf08). COORD approval pending.
- leaf34 current819: IN 68/595 (VS 559..593, VN 0..32; soft VP captures 33..558 unresolved by design), OUT 667/668. t43 unchanged (IN 69, OUT 410 unprepared).
- Next immutable profile: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/code_2ef_11bfca8 (read-only; code_profile.json f0bd94f035a3, BG d13183d3083d, 24 tests pass). code_2ef_ac601 and the running constructor untouched.
- NOTE: on PREPARED bound RTL out_bit_owners resolves 0 for leafup_o0 (u_bout .d is the inserted u_ist station q). Owners must be taken on the unprepared text or traced through u_ist; not fixed here.

## Eight-leaf constructor (DONE 02:07 UTC, exit 0) + launches
- GEN_ONLY_OK x8 at E10 fable-fix-s81-cong/countable_F2s4tapfix1_eight/gen (run_kit.sh + flow_tag there). Replicated (rsync, 204 MB) to the same path on epyc7 / epyc8 / epyc9 / intel1.
- Images: intel2 ~/s81-types-r/review_eight/<t>.png (renderer kit_view.py + fetch.sh there). All LOOKED. 0 macro overlaps in all eight.
- Verdicts: t28, t34, t47, t62 PASS-COND (launched to sign-off); t75, t72 PASS-COND diagnostic (launched); t8 HOLD; t43 HOLD. Post fda8a225.
- t8 HOLD: plan edge_clocks fclk_in_ft0_i / fclk_in_ft1_i / fclk_in_cland_dn_1 tap_um x=1440.736 not moved with the 1598.40 outline (+155.52): taps inside vp_g_ln_4/11/13, 14 ring-on-macro overlaps. Needs the DIE-R row fix + regenerate; do NOT launch the current t8 kit.
- t43 HOLD: MAX1 bus cannot reach VS (rows posted); do NOT launch the current t43 kit.
- Launch form: intel2 `ot-run --mem 64 --threads 16 --disk 40 --hosts epyc7,epyc8,epyc9,intel1 --dir $G -- bash $G/run_kit.sh $G/<type> route 64 16` (G = the gen dir; --dir must be the gen dir, a kit --dir is REFUSED by ISOLATION step 3). Logs intel2 ~/s81-types-r/run_eight_<t>.log.
- SUPERSEDED by the 18:3x block below. Live at 18:2x PST: t28 client 850976 unit oth-ubuntu-2091121-1794881515, t34 client 853411 unit oth-ubuntu-2093685-1794881530, t47 client 856591 unit oth-ubuntu-2097861-1794881544, all on intel1 (floorplan). t62 client 857885, t75 client 861073, t72 client 865910 = queued waiters on intel1 (thread cap 108+16 > 112); they start by themselves.
- TODO: per kit read 4_1_cts.log taps, GRT overflow, reloaded-GRT TT setup / FF hold, then DRC / signoff.json; export SIGNED to AGIdock /archive/opentallas-signed-1114 + rtx-pro; classify failures (t34 expected class = VQ core-input, see below; t47 = START writer class).

## t34 VQ +43.2 Y (BLOCKED on bind, post 0e32d614)
- Rows: epyc10 fable-fix-s81-cong/t34_vq_current/{t34vq_rows.json,t34vq_report.json,resite_t34_vq.py,t34vq_review*.png}. VQ origin 527.04 -> 570.24, 21 VQ station rows rebuilt at the SAME depth (0 FF, 0 cycles), max per-bit hop 394.8 um, 0 station / FT / tap collisions. Image LOOKED PASS-COND (VQ.u -> VS station sits above VS at (248,625); wire overflies VSW M5).
- Kit GEN: intel2 client 283901, E10 unit oth-ubuntu-2192800-1794878457, log intel2 ~/s81-types-r/gen_t34vq.log, script E10 fable-fix-s81-cong/gen_t34vq.sh, out fable-fix-s81-cong/t34vq_F2s4tapfix1 (private plan 7c84f6d385b5 = 819 + t34 rows; profile code_2ef_11bfca8; --max-wire-um 405 instead of the 100 um advisory pitch).
- TODO: review kit image, stage off E10, run to GRT (run_kit.sh ... grt), read GRT overflow + reloaded-GRT TT setup / FF hold, post typed row to S81-DIE-R. The 256-FF / 336-clone packing is NOT forced in this kit (placer decides); if the x_qd / VQ input class still fails at GRT, add the pack as a placement seed.

### t34 attempt 1 FAILED at GEN (17:3x), cause measured
- gen phys: "physical collector_tree differs from captured bound reset identity". Bound reset relay u_rrl_117 (kind wire, depth 3) sits at (574.32, 669.32) = under the new VQ footprint (y 570.24..699.84). The row is therefore NOT RTL-neutral: the reset tree re-solved on the private plan has 263 relays (bound 267), n_tree 130 (128), 162 relay edges renumbered, depth 6 = 6 (reset latency unchanged). Diff: epyc10 fable-fix-s81-cong/t34_vq_current/t34vq_reset_resolve_diff.json.
- So VQ +43.2 = 0 data FF / 0 cycles, but -4 reset relay FF and a new reset RTL emission: it needs a bind (S81-DIE-R event), not a row-only carry. No receipt was edited, no gen patch.
- Attempt 2 (r2, FAILED exit 4 KIT_TOPOLOGY_BIND_STALE; kit-rtl still carried the bound 267-relay tree): kit-rtl + prepare-stations on the PRIVATE plan (type-local emission with the re-solved tree), then gen. intel2 log ~/s81-types-r/gen_t34vq_r2.log, E10 unit oth-ubuntu-2447808-1794879298, out fable-fix-s81-cong/t34vq_F2s4tapfix1_r2, script gen_t34vq_r2.sh. If kit-rtl refuses a plan that differs from the bind, the proof kit must wait for the DIE-R bind.

## t43 (ROWS POSTED 17:4x, post 59ad5785)
- Full-width result: both buses need MAX2 (VS.g L1 1003.5..1015.1, VS.e 965.9..999.7): +1265 FF, dn +1, up +1. 15 typed rows, hop bound max 390.1 um, 0 M7 hits. No core moves.
- Files epyc7 + epyc10 fable-fix-s81-cong/t43v_current/t43_fullwidth_{rows,report}.json, t43_fullwidth_review.png, t43_rows_audit.py. Old drafts with mission_cycle_delta 0 superseded.
- Open: S81-DIE-R must regenerate source at MAX2 and bind. Zero-cycle alternative = VS/VE re-floor (not built).

## 18:3x PST after COORD ruling (bgbare approved r392; DIE-R folds t34 + t43 rows; t8 must be fixed; follow six leaves)
- Six leaves RUNNING (ot-run 64 GB / 16 thr, goal route = to sign-off), logs intel2 ~/s81-types-r/run_eight_<t>.log:
  - intel1: t28 client 850976 unit oth-ubuntu-2091121-1794881515; t34 client 853411 unit oth-ubuntu-2093685-1794881530; t47 client 856591 unit oth-ubuntu-2097861-1794881544.
  - epyc7: t62 client 941066 unit oth-ubuntu-920741-1794881978; t75 client 944226 unit oth-ubuntu-927383-1794882003; t72 client 948373 unit oth-ubuntu-932069-1794882028 (the three queued intel1 clients 857885 / 861073 / 865910 were stopped unadmitted after a PID + cmdline check and relaunched on epyc7,epyc8,epyc9).
  - Watcher: intel2 ~/s81-types-r/leafwatch.sh (prints stage changes / FAIL / exit). Read helper for CTS / GRT: epyc7 fable-fix-s81-coltap/an/stage_sta.sh KIT OUT cts|grt (+ stage_ffh.sh).
  - Per leaf TODO: place image LOOK, relay_mid check (grep OT_HOOK_COVERAGE hook=relay_mid in the place log: default OT_RELAY_MID_RE misses underscore-joined relay names), CTS read, GRT read (TT >= -42 reloaded GRT DB, overflow 0), route DRC 0 / TT >= -42 / internal FF hold >= 0, export.
- t8 fix ROW posted (post ad8c8cd9): 3 edge-clock taps + 23 landing pins x 1440.736 -> 1596.256, bands ft0_i / ft1_i / monitor_1 = one legal rect each in the east strip. Files E10 fable-fix-s81-cong/t8_tapfix/. Proof-kit GEN (private plan + private sidecar, profile code_2ef_11bfca8): intel2 log ~/s81-types-r/gen_t8fix.log, E10 unit oth-ubuntu-3290180-1794882228, out fable-fix-s81-cong/t8fix_F2s4tapfix1. If GEN passes: image review (kit_view.py), replicate, launch; it is evidence until DIE-R binds the row.
- t34 / t43: wait for the DIE-R event bind, then regenerate both on it with profile code_2ef_11bfca8 (t34 with --max-wire-um 405) and prove t34 to GRT.
