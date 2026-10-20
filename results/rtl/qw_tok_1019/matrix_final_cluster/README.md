# Private recorded matrix final-cluster replay

This packet uses the existing N12/MUT0 NU1 and NU4 binaries to replay the recorded TP8 die-0 L0/L1 QKV and GU matrices at their **completed cluster input boundary**. Four explicit `kc=1` keywords are applied only inside a new private source snapshot; `stn_ages.json` is the exact historical overlay blob. No public lowering helper, RTL, default, production programme, binary, timing metadata, build option, or release binding changes.

**Terminal verdict:** eight positive cases PASS (15,360/15,360 ISA words), ten controls CAUSAL_FAIL, nine complete NU1/NU4 stimulus and raw-RTL trace pairs byte-identical. Classifier unit `oth-ubuntu-118586-1792445195` ran exit 0. Every one of 41,472 observed words has its expected/observed address, bits and edge retained; all 5,184 visible readback packet edges match the measured pilot template. Eight positives have zero aggregate fault/busy and no missing, duplicate or extra output address. `replay_raw.tar.gz` holds every raw case artifact; `raw/` exposes short bench receipts directly. All own fleet jobs are terminal.

| Actual recorded cut (each NU) | ISA words | STN command entries | Cluster input edges | Table setup events/edges | Readback command entries | Visible readback outputs |
| --- | ---: | --- | --- | --- | --- | --- |
| L0/L1 QKV | 768 | 134..156 | 148..169 | 36 / 46..81 | 369..2659 | 395..2740 |
| L0/L1 GU | 3,072 | 170..192 | 184..205 | 72 / 46..117 | 405..5465 | 431..5566 |

The command-first to cluster-last span is 35 edges for each cut, including the configured command-chain arrival schedule; the visible command-first to final readback spans are 2,606/5,396 edges and include bench observation. Neither is actual command-to-last-station-result latency, which remains NULL.

| Control (same outcome in each NU) | Wrong ISA words | Aggregate | Actual causal witness |
| --- | ---: | --- | --- |
| GU sbase+1 | 3,051/3,072 | `0x000` | First row `0xbc7f590d` vs `0xbc9d3436` |
| GU kc=2 | 3,072/3,072 | `0x200` | All expected-region readback words zero; station busy at end |
| GU near block +1 edge | 256/3,072 | `0x320` | S0 STN fault plus busy; first row `0xbc36538c` vs `0xbc9d3436` |
| GU next STN before drain | 256/3,072 | `0x200` | Actual second STN entry206, destination128; stale/zero expected-region data and busy |
| L1 QKV scale before tree | 442/768 | `0x000` | Actual recorded rounding witness, e.g. row21 `0xbb4d292b` vs `0xbb4d292a` |

ROOT's scoped grant followed model `18db17025`. The model's base/overlay declarations are checked against the complete 19,731-file repaired-vector manifest and its 40 compiled/runtime ancestry records from `28ebdeac7`. One model pin was wrong: the actual staged `dv_bench.py` is byte-identical to base `0d4c9808f`, not overlay `416cd1a11`. Initial stage unit `oth-ubuntu-103655-1792444695` refused before arithmetic or RTL. Its failed snapshot/driver remain intact, and `stage_failure_1.txt` records the refusal. The corrected private manifest explicitly pins the actual base file; it substitutes no arithmetic source. Fresh snapshot `matrix_final_cluster_1019_v2` passes the source checks.

`replay.py independent()` separately implements BF16 RNE input conversion, contiguous K chunks, separate FP32 multiply/add rounding from canonical +0, each 64-way cluster tree, the upper pairwise tree and final row-scale multiplication. It does not call DUT or existing golden arithmetic. All four complete matrices match untouched NPZ `gold_y`: 7,680/7,680 ISA words. Their independently computed completed cluster bits also match the existing bench's source-level calculation before RTL admission. Fixtures, parent manifests, source changes and exact executable hashes are pinned. Preflight unit `oth-ubuntu-104055-1792444731` ran exit 0.

The two unchanged executable SHA256 values are:

- NU1: `7ba89595a8c4d2e77ba02e76479b2703237c426caf994cc8f2911ec698b8ce86`.
- NU4: `2b1db9ca2ff412ea081c66d66d135278960ed3044157e2af8cac96e295d073e1`.

Every case rejects rebuild fallback, requires the actual binary hash immediately before execution, emits `RTL_EXEC_BEGIN`, and retains complete nonempty stimulus and RTL traces. All output directories are new. The first full L0 GU NU1 case was admitted through unpinned `ot-run --mem 16 --threads 1`; unit `oth-ubuntu-104648-1792444749` ran exit 0. It passed all 3,072 output words and terminal idle/fault checks. GNU time measured 78.79 seconds wall time and 316,628 KB peak RSS; primary stimulus/log/edge ledger were 97,999/77,514/96,882 bytes. These are software-run resource measurements, not hardware latency. Subsequent replay uses four isolated processes with an 8 GB admission reservation, over six times their combined pilot peak; there is no process address, CPU-time, wall-time or file-size limit. Inventory unit `oth-ubuntu-108020-1792444850` reuses the same two binaries.

The bounded inventory contains eight positives (four recorded matrices × two configurations), eight real command controls (sbase+1, kc=2, one-edge near-block shift, and a noncolliding second STN before prior drain on L0 GU × two configurations), and two actual recorded rounding controls (L1 QKV scale before upper tree × two configurations). The kc control asserts that only command bits [66:59] change. The pairing control changes eight actual near-port events by one edge. The second-STN control preserves the original schedule and inserts a new command at first-far+8, changing the same station's destination while results are outstanding. None is an RTL mutation build. Lowering/import failures cannot count as causal failures.

Independent preflight found scale-before-tree differences in 288/1,250/442/1,155 rows for L0 QKV/GU and L1 QKV/GU. L1 QKV is the recorded rounding witness. Sequential cluster reduction is noncausal for both GU cuts and L0 QKV (zero differing rows); those zeros remain in the preflight record. It differs in 338 L1 QKV rows but is not an additional RTL control in this bounded inventory.

`classify.py` reconstructs every output address, eight-lane mask and FP32 word against the untouched ISA fixture, rejects duplicate/missing/extra addresses, checks all visible output edges and final faults/busy, and compares complete NU1/NU4 stimulus and raw traces. `word_address_comparisons.json` retains every expected/observed word, address and edge; `terminal_status.json` and `output_edges.json` retain the full status/event observations. `schedule_breakdown.json` separates actual STN entries, completed-cluster inputs, table setup, readback command entries and visible readback outputs. Readback edges use the pilot's measured observation `entry + 26 + 4*slice + packet`; they are a regression check against that measured pilot, not a native clock-phase contract.

**Visibility limit:** station results write internal VM and are not logged by these fixed binaries. Actual command-to-last-station-result latency is therefore **NULL**, and no operation latency or throughput qualification follows from late readback. Historical `stn_ages.json` is not relabelled as a new measurement. Complete visible readback edges and exact output words remain useful evidence under the no-rebuild grant.

**Scope:** all commands use user 0. NU1/NU4 agreement qualifies configuration invariance of these cuts, not four independent request lifetimes. The injected stream has one completed cluster block; native kc8/kc32 accumulator streams, actual production tile issue, source reset/configuration lifetime, programme delivery (the bench uses kind-2/kind-3 `st_wi`, idle in the old die), native clock phase, routed timing, full token and independent four-user gold remain HOLD. No OD fixture or MUT14/MUT15 RTL mutation is claimed.
