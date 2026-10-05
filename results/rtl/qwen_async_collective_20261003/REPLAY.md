# Qwen3-8B ROM TP4: the asynchronous collective (replay)

Dataflow level 5 (collective fusion). It is opt-in and default-off. The design and pricing come from `claude/qwen-body-wire-latency-20261003` @ `0faf74e24`, `study.json` L5pkg: a model saving of 286 cycles a layer.

## Verdict
- **Measured on the TP4 runtime, L0 and L1:** 3,930 cycles a layer becomes **3,652**.
  - That saves 278 cycles a layer, or 7.07%.
  - Every die's X is bit-exact against the retained terminal (L0 `7631b189`, L1 `bd905163`).
- **Projected token** (36 layers × 278): 144,522 cycles becomes 134,514, which is **+7.4% per-user rate**. The full token was not run.
- **Gates passed:** the ≥1% priced gain, and the ≥1% RTL-measured gain.
- **Still open before adoption:**
  - SS/FF closure of the sequencer in context;
  - the hub routing-layer check of the ME-write observation tap;
  - integration into `claude/qwen-rom-system-rtl-20261003`.

| run | images | L0 | L1 | saved per layer |
|---|---|---|---|---|
| A | one-stream `img256` (no cut bit), the baseline | 3,931 | 3,930 | – |
| B | fused epilogue | 3,801 | 3,800 | 130 |
| C | cut-through bit only | 3,783 | 3,782 | 148 |
| D | fused + cut-through | **3,653** | **3,652** | **278** |

- All four runs use ONE binary (`77bc37d2…`, `ASYNC_COLL=1`, `ENABLE_AR256=1`, coll DEPTH 256).
- Run E repeats D on L0 with `RT_ITRACE`. The collective starts sending at cycle 1,238, while the O matvec is still writing; it ends at 1,276.

## What changed
**New files only.** These stay byte-identical: `ot_qwen_tp_seq_w12`, `ot_qwen_rom_rt_die_w12`, `qwen_rom_rt_token_w12.py`, the program generators, every pinned image and every pinned record.

- **`rtl/rom/ot_qwen_tp_seq_async_w12.sv`:** the TP sequencer with `ASYNC_COLL` (default 0, which gives identical behaviour).
  - Descriptor bit 20 marks a cut-through all-reduce.
  - The sequencer watches the die's ME result writes, `vw_me_*`, and keeps one bit per region word. A bit is set by a full-mask write in this segment.
  - It sends words in order as soon as each is written, or once END arrives. It accepts receives while the core is still running, and advances the segment only when both the core and the receive are done.
  - The fold, tags and `last` checks are unchanged.
  - An image without the bit runs the legacy path, cycle-identical (gate).
- **`rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_async_w12.sv`:** the same die ports as before, plus the observation tap.
- **`tools/qwen_rom_rt_token_async_w12.py`:** the runtime driver for that die, with `--async-coll`.
- **`tools/qwen_rom_async_coll.py`:** the stage-image transform, which derives from one-stream images.
  - **`--fuse`:** replaces the pair (post-TP scale `MC_C`, then residual `AD_C` + sum of squares) with ONE stream-unit op. The op is `MA_AB` with b = the constant-ROM scale, then `AD_C` with c = X, with the same reducer. This gives X' = fl(fl(T1·s) + X): the golden's two roundings, with no FMA.
  - **`--cut`:** sets bit 20 only under a checked contract:
    - the segment ends [.., ME, barrier END];
    - that ME writes every region element exactly once;
    - no other ME op writes into the region;
    - any stream-unit write into the region is followed by a barrier.
  - **`--self-check`** runs it on the W12 generator for 4 dies. Each die has 2 fused pairs, both all-reduces are cut, the identity round trip passes, and the fused words are ISA-equivalent in `hdc_program.Machine`.
  - T1 keeps the unscaled sum. The tool checks that nothing reads T1 before the engine rewrites it.

## Gates
- **`fused_epilogue_gate.json`:** the production `ot_hdc_vstream` (SW 64, LV 7) under Verilator, two-op against fused against `hdc_golden` (add(X, mul(T1, s)), lane_sum of squares).
  - Uniform, wide and adversarial sets: cancellation to +0, signed zeros, subnormals, round-to-even ties, near-overflow.
  - X and the reducer are bit-identical. On the non-finite set, the fault and NaN behaviour agree.
  - Busy cycles: 240 for the two ops against 153 for the fused op.
  - Two earlier verdicts are kept as `FAILED_`: `wide_overflow` (the wide set overflowed the sum of squares; both RTL programs agree, the golden is inf; fixed by bounding the wide set) and `nonfinite_ieee` (inf/NaN operands fault in this RTL with identical bits in both programs, but were compared against numpy IEEE specials; non-finite cases are now judged by identical bits + identical fault). Every finite set passed in both.
- **`async_coll_verilator_gate.json`:** four sequencers, the real collective (LAT 339, DEPTH 256), and a stub core writing the region on schedules over stale data.
  - Schedules: O-like rounds, down-like rounds, reverse order, and half masks.
  - Legacy against async0 against async1: write logs identical, bit-exact against `hdc_golden.fold`, and legacy equals async0 in cycles.
  - Saved per all-reduce: O-like 68, down-like 132, reverse 31, half-mask 0. A word written in half masks waits for END, which is by design.
  - Overflow faults identically in every mode, and a bad `last` faults all four sequencers.
  - `SUPERSEDED_…lanemask_574fc96.json` is the earlier lane-mask scoreboard. It passed, but did not synthesise: see below.

## Physical (pathfinding only)
Screen: ASAP7 TT, pre-layout, synth+sta, 0.833 ns, NP 48 ports.

| `ot_qwen_tp_seq_async_w12` | area (µm²) | cells | fmax pre-layout |
|---|---|---|---|
| `ASYNC_COLL=0` | 1,634 | 10,930 | 295 MHz |
| `ASYNC_COLL=1` | 3,821 | 30,011 | 297 MHz |

- `ASYNC_COLL=1` adds +2,187 µm² (48 port decoders and a 256-bit OR) with no new critical path.
- The sequencer already misses 1.2 GHz pre-layout in both settings, a pre-existing issue.
- The first scoreboard (256 × 16 lane masks, 48 read-modify-write ports) did not finish Yosys in 2 h (`FAILED_seq_lanemask_…json`). It was replaced by full-word bits: the engine's masks are full except past an op's output count.
- SS/FF closure in context was not run.

## Replay
```
# gates (Verilator 5.050)
python3 tools/qwen_tp4_async_coll_verilator_gate.py --work W/vg --result W/vg.json --seeds 2
python3 tools/qwen_fused_epilogue_gate.py --work W/fe --result W/fe.json --seeds 3
python3 tools/qwen_rom_async_coll.py --self-check
# images: pinned TP4 SW64 L0/L1 (ot-pve1:/home/ubuntu/w12/st_tp4_sw64/sw) -> one-stream -> fused / cut / both
python3 tools/qwen_rom_ar256_stage_images.py --stages BASE --out img256
python3 tools/qwen_rom_async_coll.py --stages img256/stages.txt --out imgF --fuse      # and --cut, --fuse --cut
# runtime: runtime/chain.sh (one ASYNC_COLL=1 build; A/B/C/D/E)
A="--tp 4 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --code-banks 5 --mem-extra 1 --bd 41 --xvm 1 --nws 5 \
   --tws 38 --ord 7 --coll-lat 339 --coll-depth 256 --enable-ar256 --async-coll"
python3 tools/qwen_rom_rt_token_async_w12.py --workdir W --stages IMG/stages.txt --token-oracle ORACLE_TP4 --preload VM_X $A
```
- The runs used ot-epyc1tb `/srv/opentallas-scratch/claude/qwen-async-coll`, with source `de1d9348d` (git archive of rtl, tools and configs). See `runtime/MANIFEST.txt` and `runtime/chain.log`.
- Image L1-d0 program sha256 values:
  - `img256`: `23e52eb4`, the measured 3,930 one-stream image;
  - `imgF` and `imgFC`: `6f05f5e0`.

## Not done (claim boundary)
- **The core does not issue across the collective.** It still restarts per segment from a descriptor. "The core keeps running" is realised as the fused epilogue (L5b1) plus the cut-through send (L5c). A non-blocking core-issued collective would need a core change, and the model prices the residual at a few cycles of restart.
- **L5b2 (the receive-path epilogue) is not built.** It needs new fp32 arithmetic to close at SS.
