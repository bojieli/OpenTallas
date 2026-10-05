# H3 native SOFTWARE finite calendar handoff

Compiler: `tools/h3_complete_native_calendar.py`; tests: `tests/test_h3_complete_native_calendar.py`.
Base: f5b776a5991ba5522b88882b0baab5ca0604289e; isolated branch codex/h3-native-calendar-20261002.

Consumes actual Popper Qwen recipes and Peirce DeepSeek SSA templates, each source PC and operand version checked against archived H3 graphs. Native primitive issue/read/execute/write-ACK/consume/retire calendars preserve iteration-major FOR order and array128-lane batches. The compiler does shape inference only. No source handler, golden macro callback, or CPU numerical timing supplies calendar cycles.

Concrete Kepler R17 homes replace Qwen inline spill refusal: provider references, physical spill bases, allocation lookup, input/output refs, publication state and release/reuse edges are joined. Each sector pays two owner lookups (12 explicit provisional ticks each), held acceptance, CDC, consumer completion, reverse validation and retirement. Global/rank collective source rendezvous precedes native consumption; ordered output delivery precedes retirement. Atomic admission and independent interval proofs reject missing dependencies, capacity overrequests, slot conflicts, aliases and premature home reuse. Persistent generations cannot overwrite outstanding future readers.

Native temporary storage is deliberately conservative: materialized, double-buffered logical scratch with 8-byte slots preserving I64 and padding F32/U32. Each transfer is costed. Finite arena demands are reported by rank, alignment, minimum address width and nonalias constraints rather than preventing software calendars. This is not an optimized hardware implementation or a latency claim. The provisional endpoint cycle table is explicit, positive, editable with --cycles, and independent of the measured provider/SSFF and numerical execution gates.

Tests include positive finite parallel/serial controls, exact native pipeline replay, primitive-dependent latency changes, actual R17 home/reuse controls and negative deadlock, capacity, alias, stale dependency, scratch and provenance controls. Earlier failed and intermediate verdicts are retained.

Generate/replay DeepSeek input from captured immutable compiler snapshot:

```
python results/uarch/h3_complete_native_calendar_20261002/inputs/compile_deepseek_snapshot.py
```

Compile complete calendars (new output directory required):

```
python tools/h3_complete_native_calendar.py --out results/uarch/h3_complete_native_calendar_20261002/native_r3 --native-lowering results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_native.json.gz --native-lowering results/uarch/h3_complete_native_calendar_20261002/inputs/DeepSeek_native.json.gz --qwen-providers results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_provider_binding.json.gz
```

Replay uses the same command with --verify. Full expanded calendars and the large reproducible DeepSeek input are local generated artifacts, intentionally excluded from this bounded code handoff. The committed manifest records their content hashes, complete coverage, resource proof and finite extent demands. The small exact Qwen and R17 inputs and immutable producer snapshots are included.

Calendar replay is source-pin replay of the consumed native packages. Captured Qwen producer-emitter replay exposed live producer drift (preserved separately); its snapshot is supporting WIP evidence, not authority for regenerating the supplied Qwen package. The exact Qwen package itself is committed and hash-pinned. Parent integration owns current producer-package/numerical coverage and model admission. No RTL, physical run, routing-layer change or adoption is performed here.
