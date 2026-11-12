# TOK-VERIFY-3 lane handoff (2026-11-12 12:46 PST)
## 1 Scope
Post-train token checks on main d3f85cdf01a0 (train 9): S81 strict-bind compile + tok/s, Qwen (QC+KV) lane price, r12ng FSA go_tag confirmation. Successor of TOK-VERIFY-2 (read its handoff for scripts).
## 2 Worktrees
- intel1 /srv/opentallas-scratch2/claude/wt/tok-verify-2 detached @d3f85cdf01a0.
- epyc9 /srv/opentallas-scratch2/claude/wt/tok-verify-3-main detached @d3f85cdf01a0 (git worktree of wt/tok-verify-2-gear clone).
## 3 Running jobs
None.
## 4 Results (posted in COORD-REVIEW-QUEUE)
- S81 main d3f85cdf PASS: CC rc 0 x5, prog json differing 0 x4, AR 769.6 / MTP 2700.0. Run dir intel1 .../tok-verify-2/main_d3f85cdf. Command: TOK-VERIFY-2 handoff 6.3 with name main_d3f85cdf.
- QW: no RTL recipe; method = tools/token_pass/reform_rebaseline.py --die kv --base OLD plan_c.json --batch NEW plan_c.json (script epyc9 .../tok-verify-2/qw.sh). d767 -> d3f85cdf: 195 lanes, +579 cyc, max +3, BOUND 4403.2 -> 4401.46 tok/s (-0.04 %).
- FSA r12ng without workaround: rc 0 x3, no go_tag KeyError (epyc9 .../tok-verify-2/fsa3_r12ng). Compile then fails qualify_frame_source (GBQ record lacks r12ng ages [0]); needs an r12ng GB provider qualification record. Command: s81tok_v3.sh fsa3_r12ng $W $LAT with MAN=$T/asbuilt_f_s87r12.json BIND=$T/out_r12ng SRCBS=$T/bsrc4_r12ng.
## 5 Next
Re-run S81 per train when rtl/ or tools/s81* change; for r12ng A/B, wait for DIE-S81-88 GBQ for r12ng ages, then rerun gear arms with GBQ pointing at it.
## 6 Gotchas
- S81 default inputs (type-safe-5/cand, main_d767/cc) only on intel1; epyc9 has r12ng inputs only. ot-run lives at intel2 ~/.local/bin/ot-run (not on PATH).
- worktree add of the 57 GB tree on epyc9 took ~10 min.
