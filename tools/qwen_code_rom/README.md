# Actual TP8 code-ROM payloads

`build.py` checks the pinned released TP8 image hashes, layer/rank identity and checkpoint lock, then concatenates 36 × 512 layer words and 1,600 head words. This is a byte-preserving resident image of 20,032 words; the five 4,096-word banks explicitly pad the final 448 unused words with zero. No weights are requantized.

Each source word contains 3,072 groups × 16 INT8 lanes. Tile `t` owns groups `4t` through `4t+3`; column 0 holds the first 32 code bytes and column 1 the remaining 32. All 768 tiles × five banks × two columns receive actual native macro IDs `qtile_t{t}_b{b}_c{c}`. The manifest records every source image, stage base, mask hash, stored row count and exact payload identity. Independent physical-bitline readback checks every generated mask against its source bytes. All eight rank cohorts are generated separately.

The native static producer must relocate a layer-local code address by `512 × layer`, or 18,432 for the head. Each instantiated native tile must bind a constant `ROM_TILE` equal to its hardware `tile_id` strap; the actual element API checks this. A tree placement change must preserve that identity. Empty/default mask contents cannot qualify.

Run only through fleet admission after staging the source:

```bash
python3 tools/qwen_code_rom/build.py --banks /absolute/released/banks --out /absolute/fresh/masks --jobs 4
bash tools/qwen_code_rom/build_rtl.sh /absolute/fresh/rtl
python3 tools/qwen_code_rom/run_cases.py --binary /absolute/fresh/rtl/obj/Vtb_code_pair --images /absolute/fresh/masks --out /absolute/fresh/cases --workers 16
```

The actual hardened `ot_qwen_tile_rpair` contains two real 4,096×266 ROM macro models and its real INT8-to-BF16/capture/return pipeline. The minimum identical physical circuit is reused across all 30,720 rank/tile/bank cohorts. Each case supplies exact hash-checked aliases of its two immutable native mask payloads and checks every 4,096 stored word plus four masked tail slots at seven-edge latency. The observer's INT8-to-BF16 lookup comes independently from FP32 conversion; no expected code or BF16 result drives the DUT. The compressed per-case receipts record both actual target instance IDs and the compiled minimum-circuit aliases explicitly. A corrupted actual via bit must cause a numerical failure; a missing mask must fail initialization.

This establishes every released code payload on the actual hardened pair circuit. It is not a simultaneous 61,440-macro die elaboration or a full native token. The generated die still needs source-pinned ROM_TILE/strap bindings, actual native command and X/result paths, physical clocks/relays and full layer/token execution. These remaining requirements are retained in the proof report.
