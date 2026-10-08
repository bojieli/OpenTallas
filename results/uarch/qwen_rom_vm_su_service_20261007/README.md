# SU bank service obligations and opaque replay

Prerequisite: `results/rtl/qwen_rom_vm_su_control_20261007`, produced by the native SU control patch. This additive model creates no RTL and claims no bank timing or numerical exactness.

The runner checks the captured source hashes and pins both the finite-VM historical top and current `ot_qwen_rom_rt_die_w12_vprm_stream4.sv`. Their nonblocking memory reads observe pre-edge values; SU writes execute in ascending lane order and reducer writes follow. This is the SU/reducer subset of the full priority: later collective writes still follow in the parent source. All other families remain excluded from this trace.

| Captured obligation | Both mappings |
| --- | ---: |
| Maximum scalar reads / edge | 192 |
| Maximum distinct read scalars / edge | 129 |
| Maximum same-scalar response fanout | 128 |
| Maximum distinct 512-bit read words / edge | 9 |
| Maximum same-word response fanout | 128 |
| Maximum scalar writes / edge | 64 |
| Maximum distinct write words / edge | 4 |

The maxima are independent and do not necessarily share an edge. Native enables include arithmetic-unused operand reads. The 128-fold mapping uses bank=(word XOR (word>>7))&127, row=word>>7; 256-fold uses shift8 and mask255. Both are bijective mappings with word=scalar>>4.

| Service obligation | Fold128 | Fold256 |
| --- | ---: | ---: |
| Frames with multiple read rows in a bank | 140 | 133 |
| Maximum read service quanta / frame | 3 | 2 |
| Maximum write service quanta / frame | 1 | 1 |
| Maximum read-barrier-write quanta / frame | 4 | 3 |
| Sum over 738 active frames | 1139 | 1130 |

These are abstract transaction waves, **not clock cycles or token latency**. Doubling bank count leaves actual SU conflicts. A conservative source-held implementation would cost `capture + Nread*read_service + scatter + Nwrite*write_service + release`, where each wave waits for every participating bank response or write completion. Read service, SRAM protection, write verification/ACK, actual bank concurrency, broadcast muxes, registered scatter, hold/resume and clock conversion require implementation and measurement. The summed quanta exclude inactive source edges and do not establish a speedup.

`plan()` deduplicates equal read words, retains every source/lane response target, dispatches one row per bank per read wave, then permits writes only after all reads have completed. Per-bank write batches preserve source order, merge only adjacent same-word writes in that bank's sequence, retain partial masks and give the last source its scalar value. Cross-bank writes commute; source-frame release requires the whole write phase. `replay()` uses independent scalar golden state and folded word storage with opaque source-tagged write payloads, checks every response and final written scalar, and verifies untouched lanes in each partially written word.

Both mappings pass 119645 scalar response/write checks plus whole-written-word mask preservation. Actual same-edge read/write alias occurs at PC18 cycle26 and PC26 cycle26, scalar0. A write-before-read mutation is rejected on captured traffic. No simultaneous SU/reducer write or duplicate scalar writer occurs in these independently reset traces. A clearly synthetic directed case exercises SU lane0, SU lane63 and reducer writing the same scalar: the reducer wins, old reads remain unchanged, and reversed write priority is rejected. This directed case establishes a replay obligation, not an observed runtime frequency.

A straightforward complete SU-frame capture would require at least 14649 bits for 192 read response payloads, 65 scalar write payloads and 257 enabled 24-bit address seats. This positive storage term excludes ownership tags, SRAM/control protection, row/bank dispatch metadata, intermediate registers, reply tracking, control and every non-SU family. It is not a full area/slot model or authorization for bank RTL.

The existing `ot_qwen_checked_vm_bank.sv` implements a protected four-bank aligned-window service, not either folded per-bank mapping. Its timing is not borrowed here. The source-hold bridge, folded provider, finite queues, owner/protection contract, full source-family overlap and capacity remain prerequisites.

Reproduce:

```sh
python3 tools/qwen_rom_vm_su_bank_service.py --root . --trace results/rtl/qwen_rom_vm_su_control_20261007 --out /tmp/qwen-su-service
```

`edge_service.json` records every active frame's demand and abstract cost. `witness_plans.json` makes representative read scatter destinations and source-ordered masked writes reviewable. The pinned native events plus executable planner reproduce every other edge schedule.
