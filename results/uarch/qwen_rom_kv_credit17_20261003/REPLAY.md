One 17-credit composition — failed admission

The only completed successor uses17/group,136global,68pending/PC and85words/pool with8return groups,4column paths/stack and7global fills unchanged. Full36 conditional calendar:358.6013us,25.267966667us above3k budget; gain0.688787% versus361.0713us, below1% gate. No production or physical admission. Prior failures and pinned originals remain unchanged. Added two return and two reverse validation edges are proposed and priced, not physically measured. Mutable storage protection, loaded routing/clock/CDC costs, sustained PHY and production journal remain unbound.

The completed calendar is model-r2.json. model-r3.json adds the source-pinned route/collector composition without changing that calendar. model-r1.json and functional-failure-r1.json preserve the initial serialization assertion failure. focused-tests-r1.log records six functional cases. The evidence verifier replays composition/pricing and chains historical pin verification; it does not claim an independent second full calendar replay.

Run from the repository root after applying this commit on parent c8d or a descendant containing af7 and its prerequisites:

```bash
python3 -m unittest discover -s tests -p 'test_qwen_rom_kv_credit17.py' -v
python3 tools/verify_qwen_kv_credit17_evidence.py
replay_dir=$(mktemp -d /tmp/qrom-credit17-replay.XXXXXX)
python3 tools/uarch_model_qwen_kv_credit17.py --result "$replay_dir/calendar.json"
cmp "$replay_dir/calendar.json" results/uarch/qwen_rom_kv_credit17_20261003/model-r2.json
python3 tools/qwen_rom_kv_credit17_compose.py --result "$replay_dir/composed.json"
cmp "$replay_dir/composed.json" results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json
```

No new RTL/P&R, parameter sweep or numerical run. Full replay uses one local CPU and measured host headroom; no arbitrary deadline. Exact addressed dependencies are in peer-contract-receipt-r1.json. send_input was unavailable; parent relay is required. Parent owns merge/push.
