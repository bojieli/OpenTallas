# Attention record-overlap validation: QUALIFIED

Source: `045a720dc` on `claude/el1011-hbm-attn-tput`. PIPE=3; DS production geometry H4/D512/NL4, KV8 fmt7, KVL17, RIF128, KLAT104. Four QK then four PV records per case; no simulator repricing.

Positive DS run (ot-epyc4, `o_pos`): HGI_ATT_TPUT PASS on 3 shards, 0 wrong words (2560/4608/2560 checked; `run.log`), ATT_TPUT_GATE PASS (`gate.txt`, `bench_report.json`).

| case | T | price | steady-state service (cycles/record) | ratio | gate 1.10x |
|---|---|---|---|---|---|
| ds_L0 QK / PV | 128 | 147.1 | 146 / 146 | 0.992x | 161.9 |
| ds_L20 QK / PV | 640 | 339.1 | 274 / 274 | 0.808x | 373.0 |
| ring_wrap QK / PV | 128 | 147.1 | 146 / 146 | 0.992x | 161.9 |

Dispatch-to-retirement latency (not gated): T128 204 (QK) / 223 (PV), T640 332 / 351. The 104-cycle KV latency is hidden by record overlap at T128 already, so the one-record-ahead KV issue stage is not needed.

Completed evidence:

- `qwen_d128.log`: reduced D128 Qwen T512/T1024 overlap and multi-job merge functional check PASS (two shards).
- `mut_ovl.log`: stale overlap snapshot mutant detected, 2048/2304/2048 incorrect words.
- `mut_w3.log`: premature closing-row score write detected, 64/320/64 incorrect words.
- `mut_ring.log`: ring-wrap addressing mutant detected, 2560 incorrect words in the wrap case; ordinary cases unchanged.

The simulator exits zero even for a printed functional FAIL; mutation detection is established by the explicit mismatch counts and FAIL markers, not its process return code. Steady-state same-op service is reported separately from per-record dispatch-to-retirement latency; only the former is the existing throughput gate.
