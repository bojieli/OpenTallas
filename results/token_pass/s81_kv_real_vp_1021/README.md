# S81 real VP / KV consumer component

R3 passes the production D512 KV bank and native adapter from
`codex/s81-kvq-bind-1021@286841a838132f393f3b387f2ecce0e20111c73b`
connected to the real `ot_s81sl_vp` and both 512x128 SRAM models. The component
uses the baseline gate's seeded, independent D512 golden vectors. Inputs enter
through the VP native write port; commands traverse VP's SU forwarding seam;
outputs are checked through actual VP extension readback. No behavioral memory
response replaces the active production path.

Gold2 unit `oth-ubuntu-2450205-1792604500` completed with exit 0. The explicit
installed NBA scan checked 4,384 loops with zero findings and no missing source
files. R3 positive exits 0; the exponent-write suppression control exits 1 and
detects eight incorrect 32-bit exponent words. Shared baseline source hashes,
all added source hashes, vector hashes, build argv, full logs and vectors are
preserved here.

| Measurement | R3 result |
| --- | ---: |
| Native extension response latency | 4 edges for all 190 requests |
| KV output write events / distinct spine addresses | 26 / 25 |
| Native output pair writes | 52 |
| Positive scoreboard mismatches / VP faults / KV faults | 0 / 0 / 0 |
| First / last bank result, adapter age | 266 / 285 |
| Fixed drain start / drain duration | 1024 / 104 edges |
| Gain / KV finish, adapter age | 1025 / 1130 |
| Gain / KV command-to-done benchmark elapsed | 1028 / 1133 |

The final elapsed row uses the benchmark's negedge command setup before the
next VP capture edge, counting following posedges through done observation.
Adapter ages are `dut.age` sampled at negedge. These conventions are explicit;
the values are not absolute programme issue or capture dates. The prior
one-edge-memory-model result ages 263..282 are superseded for the connected VP
consumer by measured ages 266..285. The existing fixed drain remains valid.

`r1` preserves the initial missing-reset-relay source-inventory build failure.
`r2` preserves the next run's source/argv record and external termination
record. Its original `result.json` says RUNNING because the scope was killed
before the runner could seal it; `termination.json` and `host_scope_journal.txt`
supersede that status. The journal proves a 16 GiB cgroup OOM killed compiler
processes, then systemd stopped the scope. No simulation ran in R1 or R2. R3
resumed R2's complete generated model and existing objects using make with two
compiler jobs under a 48 GiB memory cap; it did not rerun Verilator or change RTL.

This is a consumer component receipt. XS/frame/CAP production, distributed and
interrank transport, actual layer coefficient/data ownership, absolute static
issue dates, SO handoff, whole-layer exactness and whole-token throughput remain
open. Fixture preload and completion observation belong to the test boundary;
the production result drain remains the immutable fixed-age source mechanism.

Reproduction uses `tools/s81_dv/kv_vp_1021/gate.py` with the baseline production
bank gate's passing output as `--baseline`, and a new output directory. The
fleet source root and original runs remain at
`gold2:/srv/opentallas-scratch/claude/codex-s81-kv-vp-1021`.

The source reconciliation against folded publication `c8bb7cf5e` is sealed in
`source_reconciliation.json`. All 64 production RTL/SRAM files match candidate
`286841a838132f393f3b387f2ecce0e20111c73b` exactly. At publication `c8bb7cf5e`,
62 match, none differ, and two are absent: `ot_s81sl_kv_bank.sv` and
`ot_s81sl_kv_leaf.sv`. Publication of this evidence and the compiler row contract
therefore does not establish that main contains the candidate bank/adapter or
their full source binding. The PASS remains scoped to the pinned candidate.
