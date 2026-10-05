# Qwen3 ROM full-system RTL: replay

**Branch:** `claude/qwen-rom-system-rtl-20261003`.

**Integrated branches:**
- qwen-allreduce-oneseg @ 7d736e8e6
- qwen-nearhbm-attn @ 0c43e10dd
- qwen-hbm-sustained-bw @ 52ce3e9c1
- two-clock-rtl @ 27d86cfe4
- macro-alignment-fix @ 53487e07b
- qwen-real-memory-runtime @ fa3e4b320

`campaign.json` names the commit it ran from (`git_head`). Every source it depends on is pinned by sha256 in that file.

## What runs

The system top is `rtl/qwen_sys/ot_qwen_rom_sys_top.sv`: 4 dies, link layers, KV services, the host interface, the package controller, the reset sequencer and the CSRs. The bench is `rtl/test/qwen_sys/tb_qwen_rom_sys.sv`. Around the DUT the bench provides:

- a register-level host: rings in host memory, doorbells, IRQ/MSI;
- the die-to-die channels: in-package latency 8 cycles, board latency 40 cycles, with optional bit errors;
- one HBM model per die: `ot_qwen_hbm_model_ack`, with WR_ACK.

The host submits a GENERATE request per user:
- prompt of 16 tokens;
- 3 new tokens.

The system then:
- runs positions 0..17;
- writes every KV row into HBM through the KV services;
- re-reads every KV row from HBM at every token, because the staging SRAM is invalidated at each token start;
- emits tokens 1073 / 382 / 93 at positions 15 / 16 / 17.

The checks are bit-exact against `tools/hdc_program.py --tp 4`, which itself is bit-exact with `tools/hdc_golden.py` at every step. Each run checks:
- every step's {token, logit} on all 4 dies;
- every completion entry;
- every die's HBM KV image;
- every die's vector memory.

Variants, given as (`-GME_CDC`, `-GKV_PREFETCH`):

- **c0p0**: one 0.9 GHz clock.
- **c1p0**: matrix engines at 1.2 GHz (fclk), everything else at 0.9 GHz (sclk), 3:4 from one PLL. Run at every fclk phase.
- **c0p1 / c1p1**: the same two, plus the token-start KV prefetch notice.

## Replay

The commands run on ot-epyc1tb with Verilator 5.050 from `~/.local/opentallas-tools`:

```bash
git checkout <git_head from campaign.json>
# images (needs build/models/qwen3-reduced-v1 and torch for the oracle; HDC_SU_WIDTH=1 is set by the tools)
HDC_SU_WIDTH=1 python3 tools/hdc_program.py --tp 4 --ngen 3 --out IMG
# everything (unit benches, 4 system variants x run matrix, fault injections, AR256 sequencer equivalence)
python3 tools/qwen_rom_sys_campaign.py --work WORK --out OUT --img IMG --jobs 32
# one run by hand
cd WORK/obj_sys_c1p1 && ./Vtb_qwen_rom_sys +DIR=IMG +CLK=split +USERS=2 +FLIP=97     # ... PASS
```

Bench switches:

| Switch | Effect |
|---|---|
| `+USERS=n` | number of users, 1..4 |
| `+FLIP=p` | inverts one bit in every p-th flit on every channel |
| `+HBM_TAG_FLIP=n` | flips the generation bit of die 2's n-th response after ready |
| `+BREAK=cycle` | corrupts every flit of the die 0 → die 3 channel from that cycle |
| `+EXPECT_FAULT=bit+1` | the run must end in an error completion with that FAULT_STATUS bit set |

## Files

- `campaign.json`: the verdict, with per-run summaries, log sha256 and source sha256.
- `*.log`: the logs.
- `INVENTORY.md`: the system inventory.

## This record

`campaign.json` comes from a `git archive` of commit **0a0baeb66** on ot-epyc1tb, so its `git_head` field is empty. Its `source_sha256` pins every input file. Verilator 5.050 was used.

- **Status:** pass on 40 of 40 runs.
- **AR256 sequencer equivalence:** pass. The successor at its defaults produces stdout identical to W12, and TAG_FULL passes.
- **Static readiness check:** pass. No readiness port in the system sources is tied high.

All system runs below decode the same token sequence. In each run:
- the token at position 15 is 1073, then 382 and 93;
- every step and die, every completion, and every die's HBM KV and VM image are bit-exact.

| Variant (1 user, 18 steps) | Cycles at 0.9 GHz | Die 0 kv_ok wait | First token (pos 15) at cycle |
|---|---|---|---|
| c0p0 (single clock) | 257,472 | 23,414 | 229,264 |
| c1p0 (ME at 1.2 GHz) | 238,653 (-7.3%) | 21,822 | 212,133 |
| c0p1 (prefetch notice) | 243,094 (-5.6%) | 0 | 216,073 |
| c1p1 (both) | 225,918 (-12.3%) | 0 | 200,919 |

The c1p1 run with 4 users and a bit error every 97 flits also passed:
- 72 steps, all exact;
- 114,613 CRC errors detected and 12,073 replays, with no mismatch.

Two injected faults each ended in an error completion with the failing source named in FAULT_STATUS:
- a corrupted HBM tag (FAULT_STATUS bit 13: die 2, KV service);
- a broken board link (bit 4: die 0, link).
