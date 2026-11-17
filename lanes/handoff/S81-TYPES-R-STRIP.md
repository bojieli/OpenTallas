# S81-TYPES-R strip fork (strip leaves, bg_bare, t34 model, t43); started 11-16 17:1x PST

Parent lane S81-TYPES-R (columns + IFN0 are NOT here). Predecessor FABLE-FIX-S81-CONG.md (read its Codex handback section).

## bg_bare (DONE)
- Branch claude/s81-types-r-bgbare-1116 @11bfca8d9c9 (clone epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/lane). +9 lines in tools/die_plan/kit_bus_bitgroups.py, test_kit_bus_bare_alias.py (6 tests), fixture kit_bus_t34_current819.sv.gz.
- GATE main=34781ed8bbc pass=3/3 GREEN. READY posted (FABLE-FIX-S81-CONG post 266cbf08). COORD approval pending.
- leaf34 current819: IN 68/595 (VS 559..593, VN 0..32; soft VP captures 33..558 unresolved by design), OUT 667/668. t43 unchanged (IN 69, OUT 410 unprepared).
- Next immutable profile: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/code_2ef_11bfca8 (read-only; code_profile.json f0bd94f035a3, BG d13183d3083d, 24 tests pass). code_2ef_ac601 and the running constructor untouched.
- NOTE: on PREPARED bound RTL out_bit_owners resolves 0 for leafup_o0 (u_bout .d is the inserted u_ist station q). Owners must be taken on the unprepared text or traced through u_ist; not fixed here.

## Eight-leaf constructor (RUNNING at 17:4x)
- intel2 client 3945840, E10 unit oth-ubuntu-1354323-1794875694, log ~/fable-fix-s81-cong/gen_countable_f2s4tapfix1_eight.log, out E10 fable-fix-s81-cong/countable_F2s4tapfix1_eight. All eight preps done 01:36 UTC; shared gen.py phys started 01:37 UTC (t28 first).
- STALE-CORE-VIEW will not recur: D3 signed table has ot_s81sl_vsw _tt.lib cbc77fd548ba and the D3 ref_tile lib has that sha.
- TODO when GEN ends: look at every kit image (Read) + verdict, stage kits off E10 (ot-run --stage), launch to sign-off; t75/t72 diagnostic only.

## t34 VQ +43.2 Y (GEN RUNNING)
- Rows: epyc10 fable-fix-s81-cong/t34_vq_current/{t34vq_rows.json,t34vq_report.json,resite_t34_vq.py,t34vq_review*.png}. VQ origin 527.04 -> 570.24, 21 VQ station rows rebuilt at the SAME depth (0 FF, 0 cycles), max per-bit hop 394.8 um, 0 station / FT / tap collisions. Image LOOKED PASS-COND (VQ.u -> VS station sits above VS at (248,625); wire overflies VSW M5).
- Kit GEN: intel2 client 283901, E10 unit oth-ubuntu-2192800-1794878457, log intel2 ~/s81-types-r/gen_t34vq.log, script E10 fable-fix-s81-cong/gen_t34vq.sh, out fable-fix-s81-cong/t34vq_F2s4tapfix1 (private plan 7c84f6d385b5 = 819 + t34 rows; profile code_2ef_11bfca8; --max-wire-um 405 instead of the 100 um advisory pitch).
- TODO: review kit image, stage off E10, run to GRT (run_kit.sh ... grt), read GRT overflow + reloaded-GRT TT setup / FF hold, post typed row to S81-DIE-R. The 256-FF / 336-clone packing is NOT forced in this kit (placer decides); if the x_qd / VQ input class still fails at GRT, add the pack as a placement seed.

### t34 attempt 1 FAILED at GEN (17:3x), cause measured
- gen phys: "physical collector_tree differs from captured bound reset identity". Bound reset relay u_rrl_117 (kind wire, depth 3) sits at (574.32, 669.32) = under the new VQ footprint (y 570.24..699.84). The row is therefore NOT RTL-neutral: the reset tree re-solved on the private plan has 263 relays (bound 267), n_tree 130 (128), 162 relay edges renumbered, depth 6 = 6 (reset latency unchanged). Diff: epyc10 fable-fix-s81-cong/t34_vq_current/t34vq_reset_resolve_diff.json.
- So VQ +43.2 = 0 data FF / 0 cycles, but -4 reset relay FF and a new reset RTL emission: it needs a bind (S81-DIE-R event), not a row-only carry. No receipt was edited, no gen patch.
- Attempt 2 (r2, RUNNING): kit-rtl + prepare-stations on the PRIVATE plan (type-local emission with the re-solved tree), then gen. intel2 log ~/s81-types-r/gen_t34vq_r2.log, E10 unit oth-ubuntu-2447808-1794879298, out fable-fix-s81-cong/t34vq_F2s4tapfix1_r2, script gen_t34vq_r2.sh. If kit-rtl refuses a plan that differs from the bind, the proof kit must wait for the DIE-R bind.

## t43 (ROWS POSTED 17:4x, post 59ad5785)
- Full-width result: both buses need MAX2 (VS.g L1 1003.5..1015.1, VS.e 965.9..999.7): +1265 FF, dn +1, up +1. 15 typed rows, hop bound max 390.1 um, 0 M7 hits. No core moves.
- Files epyc7 + epyc10 fable-fix-s81-cong/t43v_current/t43_fullwidth_{rows,report}.json, t43_fullwidth_review.png, t43_rows_audit.py. Old drafts with mission_cycle_delta 0 superseded.
- Open: S81-DIE-R must regenerate source at MAX2 and bind. Zero-cycle alternative = VS/VE re-floor (not built).
