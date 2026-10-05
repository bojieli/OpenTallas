Frozen handoff: one Ampere-joined per-word dispatch alternative

REJECT: model-r3.json composes full36 sequential layers at358.013133333us,24.6798us over3k budget,0.854205% conditional gain versus361.0713us. Keep8/4/7 transport,16/group128global64pending and56x80word pools. No tune, RTL, P&R, production headline or numerical run.

Ampere0fba48658 input is snapshotted under inputs/. Its169472FF/48496collectors/.1455818832mm2 and extra1predicate edge join once. Total added knownarea.84472939152mm2, service19.22629759632mm2, residual2.53831880482mm2 before unknown protection/loaded route/clock/hold/PG. Full old6613track deficit remains. ExistingKV/HBM debit replaced once; macros/PHY/fill roots not recharged.

model-r1.json and its layer journal preserve the completed pre-Ampere partial diagnostic; its exact implementation is inputs/pre-Ampere-diagnostic-r1.py. It was already progressing when the contract arrived. It is not the admitted or composed candidate. model-r2.json is the ONEjoined finite replay including the received predicate edge. model-r3.json adds scoped source-weighted read/write causal credit and historical traffic/port bounds without another calendar run. No parameter sweep. The compressed causal journal records all75024cohorts using exact source address recipes and dependency/event digests; it is derived conditional evidence, not Euclid observed production payload/state. Actual producer/reader/PHY/strictrefresh/physical joins remain open. No independent second full replay claimed.

Historical docs/MICROARCH_MODEL.md lines706/707 are snapshotted:8460 SS analytical row;6222 oldRTLbody and991cycle allreduces. Current conditional bytes150847488/token and fill281.4us/owner294.912us/column294.624us lower bounds prevent6222 even with infinitecredits/zero rootcompute. Necessary capacity equivalents at6222:13fill/15return/8column; at8460:18/21/11. At3k the causal relaxed group floor is6, old/new measuredlifetimes still require17; neither is a capacity sufficiency proof or an instruction to reopen rejected17. Morecredits cannot overcome fixedport deficit at historical rates. Actual resident/reuse policy may avoid transfers only after source state/residence/demand binding; no compulsorycoldrefill assumption.

Six functional cases pass. Verifier chains57sources/28originals and prior failure pins, independently reconstructs source cursor demand coverage of75024journal records, and replays pricing/composition. Failed17/coldnumerical originals unchanged. No documentation edits. Our localmodel jobs completed; no livePID/remotejob. Parent/Euclid fleet untouched. send_input unavailable; peer-contract-receipt-r1.json is for exact parent relay.

Minimum prerequisite is reviewed61c (plus its already integrated historical dependencies). This handoff adds only tools/tests/results. Parent owns merge/push.

Exact independent replay from repository root:

```bash
python3 -m unittest discover -s tests -p 'test_qwen_rom_kv_beat_retirement.py' -v
python3 tools/verify_qwen_kv_beat_retirement_evidence.py
replay_dir=$(mktemp -d /tmp/qrom-beat-retirement.XXXXXX)
python3 tools/uarch_model_qwen_kv_beat_retirement.py --result "$replay_dir/calendar.json" --journal "$replay_dir/layers.jsonl" --causal-journal "$replay_dir/causal.jsonl.gz"
cmp "$replay_dir/calendar.json" results/uarch/qwen_rom_kv_beat_retirement_20261003/model-r2.json
cmp "$replay_dir/layers.jsonl" results/uarch/qwen_rom_kv_beat_retirement_20261003/layer-journal-r2.jsonl
gzip -cd "$replay_dir/causal.jsonl.gz" > "$replay_dir/causal.jsonl"
gzip -cd results/uarch/qwen_rom_kv_beat_retirement_20261003/causal-journal-r2.jsonl.gz > "$replay_dir/expected-causal.jsonl"
cmp "$replay_dir/causal.jsonl" "$replay_dir/expected-causal.jsonl"
python3 tools/qwen_kv_beat_retirement_composition.py --result "$replay_dir/composed.json"
cmp "$replay_dir/composed.json" results/uarch/qwen_rom_kv_beat_retirement_20261003/model-r3.json
```

Compressed bytes include gzip time/name headers; compare decompressed exact records. Composition consumes the pinned completed calendar; the preceding compare proves the independent calendar matches it. Do not run duplicate live captures. The next required input is Euclid's terminal source-owned release/state/residence/reader/ACK lifecycle journal from its existingL0 capture, then an actual-policy transfer/debit reconciliation. This rejected dispatch lever is not tuned or built.
