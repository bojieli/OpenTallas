# Attention record-overlap validation (in progress)

Source: `045a720dc` on `claude/el1011-hbm-attn-tput`. PIPE=3; DS production geometry H4/D512/NL4, KV8 fmt7, KVL17, RIF128, KLAT104. Four QK then four PV records per case; no simulator repricing.

The positive DS run is still compiling on ot-epyc4 at `/srv/opentallas-scratch/claude/att3/045a720dc/o_pos`. No positive DS exactness or throughput qualification is claimed yet.

Completed evidence:

- `qwen_d128.log`: reduced D128 Qwen T512/T1024 overlap and multi-job merge functional check PASS (two shards).
- `mut_ovl.log`: stale overlap snapshot mutant detected, 2048/2304/2048 incorrect words.
- `mut_w3.log`: premature closing-row score write detected, 64/320/64 incorrect words.
- `mut_ring.log`: ring-wrap addressing mutant detected, 2560 incorrect words in the wrap case; ordinary cases unchanged.

The simulator exits zero even for a printed functional FAIL; mutation detection is established by the explicit mismatch counts and FAIL markers, not its process return code. Steady-state same-op service is reported separately from per-record dispatch-to-retirement latency; only the former is the existing throughput gate.
