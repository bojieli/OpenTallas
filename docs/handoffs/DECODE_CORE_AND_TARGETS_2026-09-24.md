# Decode core and target status — 2026-09-24

This follows the [architecture feasibility handoff](ARCHITECTURE_FEASIBILITY_2026-09-23.md).
The analytical position is unchanged ([the analytical report](../ANALYTICAL_REPORT.md)).
Since then the work has moved to implementation. All of it is on `main`.

## 1. The hardwired decode core (`rtl/hdc/`)

This is a model-specific, fully pipelined decode core for the ROM machine. The
[plan and iteration log](../TOKEN_PIPELINE_OPTIMIZATION_PLAN.md) records every
step and number.

- **Arithmetic specification.** A chain of four artifacts, each checked
  against the one before it:
  1. `tools/hdc_golden.py` defines the arithmetic, bit-exact;
  2. `tools/hdc_isa.py` defines the instruction format;
  3. `tools/hdc_program.py` writes the program and ROM images, and runs an
     ISA-level simulator that must match the golden;
  4. the RTL comes last.
- **Datapath.**
  - A 64-lane matrix engine. The sums circulate in the adder pipeline, narrow
    matrices use a K-split tree, and the BF16 lanes are exact.
  - A stream unit with exp, reciprocal, rsqrt and sigmoid pipelines.
  - No divider and no iteration anywhere.
- **Control.** A static program with barriers, plus element chaining on
  progress thresholds.
- **One token, one core.** 32,172 cycles in Verilator, bit-exact in every
  logit, the vector memory and the KV cache (`results/rtl/hdc_decode_campaign.json`).
  From an empty KV cache the core consumes the prompt and generates the torch
  oracle's 1073, 382, 93.
- **ROM array** (`rtl/test/tb_hdc_array.sv`, `results/rtl/hdc_array_campaign.json`).
  Decode cores are chained layer-per-package through `ot_rom_pkg_link`, with
  per-user KV slices. Every user generates the oracle's tokens.

  | Packages / users | Speed-up over one core |
  |---|---|
  | 4 / 4 | 2.2× |
  | 5 / 5 | 3.65× |
  | 6 / 6 (vocabulary-split lm_head) | 5.2× |
  | 10 / 10 (attention/MLP half-layer packages) | 7.0× |

- **ASAP7, routed** (`results/physical_abi3/asap7/hdc/`):

  | Block | Routed |
  |---|---|
  | stream unit | 1,111 MHz |
  | exp, reciprocal, rsqrt | 1.20–1.22 GHz |
  | rebalanced FP32 multiplier | 1,275 MHz |
  | FP32 adder | 1,447 MHz |

- **Open.**
  - The matrix-engine route: its internal paths close. Its first attempt hit
    routing congestion; the current attempt is limited by a 2,048-bit I/O
    budget at the block boundary.
  - The full-core route: at floorplan its worst path was −24 ps at a 0.9 ns
    target.
  - The vector memory is assumed external with 7R/6W ports; a real design needs
    it banked.

## 2. The other targets

This is a read-only survey of the committed artifacts, taken at `bb6ad96d`.
The token results are from the numpy runtime simulator unless marked RTL.

| Target | Deployment | Tokens | Performance | Main blocker |
|---|---|---|---|---|
| Qwen3-8B, HBM (ABI 3.0) | 21/21 checks | Shipped model matches the oracle: 3 tokens to EOS, and a chat run. The reduced model's token 1073 matches in RTL. | Exact-8K, batch 1: 172.4 M cycles (dated 09-04) | The shipped-program RTL faults at PC 32 `DMA.SCATTER`. The cycle numbers predate the 09-20 engine rewrites. |
| Qwen3-8B, ROM (ABI 3.0) | 63/63 checks | As HBM. The reduced 4-node array reaches EOS matching the oracle. | 148.1 M cycles (09-04) | As HBM. The decode core above is the fast replacement for the reduced model. |
| DeepSeek V4.1, HBM | Admits on an 8-node comparator at context 512 | Matches at 8–9 prompt tokens; disagrees at 12/16/32 | none (0 of 15 cycle cells) | Streamed index select has no query position (`POSITION_START` is 0 in prefill) |
| DeepSeek V4.1, ROM array (64) | Built and admitted | `[305,270,915,22105]`, wrong from index 0 | none | As HBM; no multi-node RTL |
| DeepSeek V4.1, ROM wafer (2) | Admitted | Same tokens as the array, wrong | none | As HBM |

The DeepSeek query-position fix is being worked in an isolated branch. It
needs the A18 view format to carry two request-dependent extents.

## 3. Stale documents found

- `docs/PROGRAM_STATUS.md` (09-12) does not cover V4.1.
- Checklist W14.4 and W14.5 say no V4.1 deployment or token exists; both now
  exist.
- `docs/FOUR_TARGET_PROGRESS_REPORT.md` (09-04) describes V4-Flash, not V4.1.

## 4. Workspace

- There are no concurrent sessions. An ORFS container without a live
  `docker run` client is a leftover from a dead session. Four such containers
  (G2 cluster, rms_norm) were killed on 09-24.
- Route from a pinned worktree (`/tmp/claude-1000/hdcwt`).
- Reproduce with `python3 tools/rtl_hdc_decode_campaign.py` (~3 min) and
  `python3 tools/rtl_hdc_array_campaign.py` (~8 min, 4 configurations in
  parallel).
