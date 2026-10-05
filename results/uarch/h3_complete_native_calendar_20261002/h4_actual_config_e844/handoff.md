H4 actual-configuration finite model and C0 service milestone

Inputs: Sagan e844837ed H1 992c14a70, unified-model fd722 source SHA 2da5b6d..., retained Qwen execution 8020d8af and DS ordered PC127 ea1da4ec. Parent H4 intake8c9fae preserves the same source audit. Only the three authorized paths changed.

Run from the calendar worktree (or parent after intake):

```sh
python3 tools/h3_complete_native_calendar.py --h4-cost-join results/uarch/h3_complete_native_calendar_20261002/h4_actual_config_e844/inputs --out results/uarch/h3_complete_native_calendar_20261002/h4_actual_config_e844/run_r3 --verify
python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
```

To regenerate use a new nonexistent --out directory and omit --verify. Cost join is under2sec/<300MiB; tests budget35sec/<1.5GiB (reduced functional controls). No wholeprogram arithmetic/provider replay, RTL build, original producer mutation or r22 augmentation is performed. Historical manifests retain their original consumer pins. run_r1/r2 are superseded positive intermediate captures; no failed verdict was overwritten.

Qwen: existing two reduced36layer fixtures,3474 PC intervals/66342 native batches; producer shared128B counts become12456 actual64B scratch transactions. Positive provisional8 ticks per64B transaction plus22 C0 ticks per native batch. Total88339452 ->89848800 software ticks. Source-provider/RF/codec service prices retained once. Future executable bounded runs now default to actual64B counts. This reprice adds C0 reservation demand; it is not an executed H1 micro-op trace.

DS: retained actual PC127 rank0 native3999 stages/1189792 batches; added26175424 C0 ticks, ordered fetch/decode/home/admit before source phases and completion/reverse retirement after visible commit. Relative page peak3670528 bytes is not the producer complete6790664-byte footprint. Physical base/lease unresolved. Explicit UNKNOWN shared movement count; no false mapping of32MiB workspace into64KiB scratch. Existing all2213 bounded macro reservation remains intermediate.

Model: calls exact source-pinned unified sm_area/sm_op_cycles/mma_drain_cycles algorithms with DSLEV4/group_slotFalse and QwenLEV5, actual RF256KiB logical/512KiB physical/128 macros perSM,32SM/rank. Models RF physical ACK credit1 and512entry C0 scoreboard, actual4096b RF ports,512b scratch,1024b matrix ingress and32-way command mux/demux/fanout. DS mode rates are mutually exclusive: H1 BF16 peak512MAC/issue-clock; modeled FP8/FP4 candidates1024/2048, no summed-mode issue rate. Unit-sum RF/C0 area estimates and routing demands are committed; missing endpoint area/channel/slot-fit explicitly block admission. Streaming1.2GHz and serial0.9GHz are policy targets, not measured software tick conversion or clock qualification.

Executable C0VersionScoreboard controls concrete rank/SM/version/generation/home references; fullRF credit through ACK, future-reader leases, rank-global HBM aliases, completion/visibility/reverse retirement and finite capacity exhaustion. Sagan owns extracting commands and the actual opcode/consumer bridge. C0_Sagan_interface.json is the direct integration artifact; direct agent messaging is unavailable. All3950PC/51family source-audit bindings are covered; zero complete H1 native-family bridges are hardware-qualified. No trained checkpoint/full-token output was numerically executed by this join. Existing Qwen producer/output snapshot comparisons and DS prior synthetic-family tests do not supply that credit.
