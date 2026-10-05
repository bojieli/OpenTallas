# Qwen3-8B ROM TP4 asynchronous collective at full shape (2026-10-04)

**Verdict: REJECT.** The hardware cannot close physically. The lever is exact and fast, but the sequencer as built misses SS setup at 1.2 GHz by 546 ps. Defaults stay `ASYNC_COLL=0`, and it is not adopted into the combined Qwen top.

## Full token, ideal memory, position 0 (layer-parallel, 37 jobs from golden checkpoints)

Both runs use one `ASYNC_COLL=1`, `ENABLE_AR256=1` binary (`layer_parallel/lp_build.json`).

| images | per layer (chained) | head | token cycles | tok/s/user @ 1.2 GHz |
|---|---|---|---|---|
| one-stream `img256` (no bit 20), the baseline | 3,930 | 2,998 | **144,522** | 8,303 |
| fused + cut-through `imgFC` | 3,652 | 2,998 | **134,514** | 8,921 (**+7.44%**) |

- **Exactness.** Every exit x is bit-exact. The head gives token 50994 with logit bits `419c72b5`.
- **Entry state.** It is discharged by the poisoned-entry plan (`verdict_fc-r2.with-poison.json`: `composed_full_token_exact=true`).
- **Legacy path.** The baseline equals the pinned AR256 full-token record, so images without the bit run cycle-identically on the async binary.

## Real memory (REAL_MEM HBM KV service), prefix E+L0..L2

| position | one-stream | async | prefix rate |
|---|---|---|---|
| P0 | 14,273 (4,222/4,970/4,973) | 12,240 (3,902/4,283/3,947) | +16.6% |
| P255 | 13,874 (4,337/4,776/4,653) | 12,687 (4,017/4,017/4,545) | +9.4% |

- **What ran.** The die is `rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_rm_async.sv`, with the driver `tools/qwen_rom_rt_token_w12_rm_async.py`.
- **Exactness.** Every layer X and the token K/V written to HBM are bit-exact against the frozen REAL_MEM goldens.
- **Uneven savings.** The saving per layer varies, because moving a layer's timing shifts its KV write-drain against HBM refresh.
- **Tap gating.** The tap is gated by `me_clk_en`, the committed write. Under `ME_STALL` the engine holds its write outputs while the vector memory does not commit. An ungated tap could send a word before it lands.

## Not done

- **Full token at a nonzero position.** It was not run. At launch no 36-layer P255 golden existed: the oracle is NumPy-only and CPU goldens are banned. A local-GPU full-36 P255 golden has since landed (`results/inputs/qwen_rom_full36_p255_20261003`). It was not used, because the lever is rejected physically and the owner rule allows no rescue runs.
- **P1023.** It was still running on EPYC at record time.

## Physical

Physical results are in `../physical_incontext_20261004/`.

| | `ASYNC_COLL=0` | `ASYNC_COLL=1` |
|---|---|---|
| SS setup (1.2 GHz) | +17.1 ps | **−546 ps** |
| FF hold | +6.2 ps | not reached |

- **Failing path.** It is logic depth in the scoreboard set: subtract, range compare, 256-way decode, then a 48-port OR tree.
- **Hub routing of the 48-port tap.** It passes, but needs a register stage.
- **What a successor would need.** A pipelined scoreboard would be a new lever, not part of this one.

## Replay

Run `chain.sh` and `chain2.sh` on ot-epyc1tb under `/srv/opentallas-scratch/claude/qwen-async-full`. The source is `src/SOURCE_COMMIT`.

`chain2.sh` exists because the first run of the `imgFC` jobs failed at file-open: a stage-list path was doubled. Those first-run plans (`fc`, `fc-poison`) are kept there.
