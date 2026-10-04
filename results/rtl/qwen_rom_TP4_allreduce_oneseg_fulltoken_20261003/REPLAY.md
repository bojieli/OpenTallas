# Qwen3-8B ROM TP4 one-stream all-reduce: full token, layer-parallel (2026-10-03)

This is the full-token measurement for the opt-in one-stream all-reduce, branch
`claude/qwen-allreduce-oneseg-20261003` at `7d736e8e6`. It was run with
`tools/qwen_rom_layer_parallel_sim.py`; the method is in
`results/rtl/qwen_rom_layer_parallel_20261003/REPLAY.md`.

## Result

- **Every stage is bit-exact against the retained TP4 terminal.**
  - L0..L35 exit x match on all four dies (`retained_terminal_crosscheck.json`, by sha256).
  - The head gives token **50994** with logit bits **419c72b5**.
- **Cycles per stage.**
  - Layers: 3,931 isolated each, which is 3,930 chained (L0 3,931, since it is entered by the wrapper start).
  - Head: 2,999 isolated, which is 2,998 chained.
  - The retained split-segment run took 4,668 per layer.
- **Composed total: 144,522 cycles**, against 171,090 retained, saving 26,568 (−15.5%). This equals
  the branch's projection of 144,522.
- **Entry-state composition.** The only pre-stage read that hits a word an earlier stage wrote is
  vector-memory word 0.
  - It is read on the stream unit's B port at cycle 19 in every stage and die (`DEPSITE ... addr=0 port=1 cyc=19`).
  - That is instruction 0, the RMS sum-of-squares, with `ma`/`ad`/`md` all bypass, so B is fetched but unused.
  - The AR256 image transform leaves the instructions byte-identical.
  - The baseline poisoned-entry run (`results/rtl/qwen_rom_layer_parallel_20261003/poison/`) preloads
    every non-x word with NaN `7fbadbad`, and stays bit-exact.
  - `verdict.json` here keeps `entry_state_composition_ok=false` as computed. No AR256 poison run was made.
- **Wall time:** 3,963–4,417 s per job, and 8,770 s first start to last end.
  - The large VM was shared with another agent's ORFS/simulation load (load 70–130 on 64 cores), so
    the 37 jobs launched in memory- and CPU-gated waves.

## Replay

```bash
# images: one-stream stage images from the pinned TP4 SW64 list (paths rewritten to the large VM copy)
python3 src-7d736e8e6/tools/qwen_rom_ar256_stage_images.py --stages stages-agi.txt --out img256
# build (models through the unchanged driver, then the audited host) -- build.sh
python3 tools/qwen_rom_layer_parallel_sim.py --build --workdir build-ar256-7d736e8e6 --source-root src-7d736e8e6 -- \
  --tp 4 --groups 6144 --count-width 18 --su-width 64 --lv 7 --smin 7 --smax 11 --tcut 7 --bd 41 --xvm 1 \
  --nws 5 --tws 38 --ord 7 --mem-extra 1 --scale-local 0 --code-banks 5 --coll-lat 339 --coll-depth 256 --enable-ar256
python3 tools/qwen_rom_layer_parallel_sim.py --plan --plan-dir PLAN --stages stages.txt --oracle oracle_tp4 \
  --preload preload.hex --fleet fleet.json        # no --reference: cycles are meant to change
python3 tools/qwen_rom_layer_parallel_sim.py --launch --fill --plan-dir PLAN   # repeat until all launched
python3 tools/qwen_rom_layer_parallel_sim.py --collect --plan-dir PLAN && python3 tools/qwen_rom_layer_parallel_sim.py --verify --plan-dir PLAN
```

- **Inputs.**
  - Oracle: `oracle_tp4`, sha256 `7babf695…`, the same one as the retained terminal.
  - Preload: sha256 `11f5ae1f…`.
  - One-stream image pins: `ar256_images.json`.
- **Build record.** `lp_build.json` holds the pinned source commit and the binary sha256. It records
  `ENABLE_AR256=1` and collective `DEPTH=256`, and the re-linked pinned host is byte-identical to the
  driver's binary.
