# KV-TOK (epyc2) — branch claude/kv-tok-1024 (= tokj-kvslice-1023 + main), worktree localhost ~/wt/kv-tok, epyc2 ~/wt/kv-tok
## Status 2026-10-24 07:00 PDT
- Recovered old ot-gold1 scratch (tokj-1023/kvslice: staged kv41 src, img41 boot frames, 79 built hier-block libs, build.log)
  to intel1:~/ot-scratch/kv-tok/recovered/ (+ kv-p7-1023 from intel1/intel2); streaming to epyc2:/srv/opentallas-scratch/claude/tokj-1023/kvslice.
- ROOT CAUSE of the 10-23 top blow-up (853 MB root header, 11,900 top .cpp, still emitting at host death): every partition
  instance with #(...) overrides (hg/hgi/pv/pc*_0/hub_C/...) was NOT matched to its hier block (built with defaults) and was
  inlined into the top. All 2,582 overrides equal the module defaults -> strip #() from the top (exact) -> all 79 types hier.
## Next
- top-only verilation against the recovered libs; boot run nominal + mutant; then PV W request-lane pads (kv-p7), token tests.
## OWNER?
(none)
