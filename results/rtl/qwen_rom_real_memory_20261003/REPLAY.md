# Qwen3-8B ROM TP4 runtime on real memory services (REAL_MEM), 2026-10-03

## What was run

These runs use the default-off REAL_MEM configuration of the W12 TP4 die (G = 6,144, SW = 64, LV 7, MEM_EXTRA 1, collective LAT 339). The retained runtime is untouched.

In this configuration no memory is served by the C++ host on demand. The host only preloads contents between stages: ROM via masks, the HBM model's per-layer KV history and the embedding row. It also wires the tile fabric and the collective.

Readiness signals:

| Signal | Driven by |
|---|---|
| `kv_ok` | the KV fill service (`rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv`): all fill sectors retired and every slice write landed |
| `kv_write_drained` | the same service: every token K/V sector acknowledged by a tagged, generation-checked HBM write-done (`rtl/hdc/kv/ot_qwen_hbm_model_ack.sv`, WR_ACK=1) |
| `me_mem_ok` | the ready signals of the scale-ROM macro banks (core `ME_STALL`=1) |
| `w_ok`, `emb_ok` | the ROM services' ready signals; driven, but not consulted, because `W_HBM`=0 |

Memories:

- **Tiles.** Each is the hardened `ot_qwen_rom_tile_w12`: code ROM in `ot_rom_4096x266_m8` macros, and the KV slice in 2 × `ot_sram_1r1w_128x256` macros with `KV_LOCAL`=1.
- **Die memories.**
  - Scale ROM: 48 ports, each with 13 `ot_rom_4096x266_m8`.
  - Embedding ROM: array storage with the one-cycle macro read contract.
  - Program, descriptors, constants and vector memory: RTL arrays.
- **HBM.** One stack per die: 32 pseudo-channels at 833 ps, with refresh and FR-FCFS.

Stages:

- **E.** The INT8 embedding through the core's `INT8_EMBED` path (`tools/qwen_rom_embed_stage_w12.py`).
- **L0, L1, L2.** Decoder layers.

Golden reference: `tools/qwen_rom_position_oracle_w12.py`, the ISA golden of `tools/hdc_golden.py` and `tools/hdc_program.py`.

- The prompt is the Qwen3-8B model card, tokenised.
- Positions below P are the golden prefill, run as sequential decode. They populate each layer's KV.
- The dense kernel is vectorised in the same order, and is checked bit-equal to the reference kernel.
- The tool reproduces the retained `oracle_tp4` X for L0, L1 and L2 at token 0, position 0.

## Reproduce

All runs use `ot-epyc1tb:/srv/opentallas-scratch/claude/realmem`.

1. Standalone service benches:
   ```
   python3 tools/run_qwen_rt_realmem_standalone.py --work W --result standalone/standalone_services.json
   ```
2. Golden:
   ```
   QWEN_O4_GROUPS=6144 QWEN_O4_TP=4 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 \
     python3 tools/qwen_rom_position_oracle_w12.py --layer-dirs "<img_tp4>/L{layer}-d{die}" --layers 3 \
     --tokens prompt_tokens.txt --positions 255,1023,2047 --snapshot <Qwen3-8B b968826d> --out gold/prompt
   ```
   Add `--check-token0-preload` with token 0 for the position-0 run.
3. Embedding stage:
   ```
   HDC_SU_WIDTH=64 python3 tools/qwen_rom_embed_stage_w12.py --out stages/E
   ```
4. Runtime:
   ```
   python3 tools/qwen_rom_rt_token_w12_rm.py --real-mem --workdir runs/<n> --build-dir build \
     --stages stages_E_L0_L2.txt --oracle gold/prompt/P255 --pos 255 --token 6280 --result runs/<n>.json
   ```
   Add `[--kv-ideal]`. Its defaults are the retained TP4 design point.
5. Collect:
   ```
   python3 tools/qwen_rom_realmem_collect.py --run name=runs/<n>.json:runs/<n>/token.log ...
   ```

`--kv-ideal` is the A/B reference: the same die and binary, with the KV service's HBM bypassed and the slices preloaded with exactly what the fill writes. The difference between a REAL run and its `--kv-ideal` twin is the cost of the real KV memory.
