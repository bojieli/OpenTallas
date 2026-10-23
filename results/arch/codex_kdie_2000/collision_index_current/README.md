Source: actual failed b21799aae / codexN6 model captured at 22:13:38 PDT on Gold1. Original pickle remains at /home/ubuntu/ot-scratch/claude/codex-kdie-2000/fail_codexN6.json.pkl; its SHA256 is recorded in both files.

The replay uses 18,133 actual obstacle rectangles and 983 accepted repair candidates plus their eight adjacent lattice positions. It retains the captured staged/committed ordering and the original floating-point collision predicate. All 8,847 comparisons agree, including 3,662 overlaps. Accepted candidate coordinates have zero collisions. Lookup-only timings are in equivalence.json and do not predict full GEN speed. Candidate enumeration, geometry, progress tests, clock selection and guards are unchanged.

Replay: python3 tools/qwen_kv_die/replay_collision_index.py results/arch/codex_kdie_2000/collision_index_current/N6_capture.json.gz
