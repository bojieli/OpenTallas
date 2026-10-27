# TOK-QK-KVL 10-27: the per-layer KV attention phase of the B48 KV die (COORD ASK2)

The release gate (owner 10-18) requires per-layer RTL sims on the current dies, with the static schedule and the
compute<->KV traffic. QC compute already covers 36/36 layers (TOK-QK, `results/token_pass/qk_1027`).
This lane adds the KV half. The B48 KV die is the native `tb_kvslice` vehicle, built hierarchically from the B48 bound
top. It runs one compiled 8K token, which is 36 layers on the B48 static calendar (`D2D_TOKEN_PERIOD` 293,376 edges,
`token_cycles_through_L35` 290,059). The far end of the UCIe link is the compute die's own real link-end RTL
(`kvs_compute_end.sv`):

- `qfd_d2d_static` PR1 with TXDP_C;
- `ot_qwen_d2d_cal_seq` AUTO;
- `qkd_native_attention_record` with KV_SIDE 0;
- `qfd_kvn_static_transport`.

Only the PHY is modelled. Each layer has its own operands.

## What is new

| file | change |
|---|---|
| `tools/qwen_layerbench/kv_dieslice/kvs_compute_end.sv` | `+VECL=<dir>`: per-layer `L<n>/{q,gold,kvn}.hex`, selected by the calendar's running layer (CMD / Q / KVN) and by the RESULT record's layer field (check). `FAR_LAYER` / `FAR_LAYER_SUMMARY` give per-layer ok/bad, cal_start and first/last RESULT cycle. Mutant m4 `+MUT_QSWAP` feeds layer n the q of layer n^1. Without `+VECL` the behaviour is unchanged. |
| `tools/qwen_layerbench/kv_dieslice/kv_preload.py` | `--as-layer N`, for the per-layer preload and mutant m5. |
| `tools/qwen_layerbench/kv_dieslice/run_kvl.sh` | The per-layer runner. It builds the 36 per-layer HBM histories (`--skip-last`, so row T-1 must arrive over KVN and be written by the die), runs boot then token, and reports `layers PASS n/36`. |
| `tools/qwen_layerbench/kvl_history.py` | The declared deterministic FP8 K/V history (see below). |
| `tools/qwen_layerbench/kv_attn_vectors.py` | `--fx declared --history-manifest`: the fixture-identity check is recorded as not applicable, and the history sha is recorded instead. |

## Operands (no reference substitution)

`gold.sh` produces the operands in three steps:

1. **History.** `kvl_history.py` builds a declared history for rows 0..8190, using a safe-finite E4M3 code law. The seed is
   distinct per layer, die and head, the same law that `qwen_tp8_native_layer_oracle.py` uses for its prior cache.
   No 36-layer real-prefill history exists on the fleet or in the archive.
2. **Gold.** `kv_attn_gold.py` → `qwen_hbmacc_position_oracle_gpu.py --run --device cpu --kv-history`. This is the
   history-seeded TP4 ISA golden with the real checkpoint weights (`prep/tp4`). It uses the real prompt token at
   position 8191 and chains x from layer to layer. It took 111 s on intel2.
3. **Vectors.** `kv_attn_vectors.py` splits the result into the 8 KV heads × 36 layers, giving the KV die's TP8 view:
   - q: 4 heads × 128;
   - K/V: rows 0..8191;
   - gold: the reference at the KV die's TP8 splits.

The check is independent. For all 288/288 (layer, head) pairs, the reference at the ISA splits equals the ISA golden
bit for bit (`isa_ref_eq_isa` 0). `vec_record.json` verdict PASS. CHECKED.

## Runs

- **Build.** `build.sh` re-verilates only the top. The 75 B48 hier libs are symlinked read-only from
  codex-kv-boot-2005. The first try at `--mem 160` was killed by MEMCG-OOM at 160 GiB; it was relaunched at `--mem 360`.
- **Sims.** `launch_all.sh` starts:
  - 8 nominal runs (heads d0..3 × g0..1), each covering all 36 layers;
  - 4 negative controls on d0_g0, L0..L2: m1 CMD late, m3 K-row swap in phy_WS_0, m4 q of layer n^1, m5 HBM history of
    layers 0 and 1 swapped. m5 must give L0 and L1 FAIL and L2 PASS.
- **Smoke.** `smoke_old.sh` runs layer 0 only on the r4 B48 binary, which carries the unchanged far end.

**The 36 layers are not 36 independent sims.** The calendar runs L0..L35 back to back inside one token. A sim that
checks layer L must still replay the boot (~38k cycles) and every earlier layer, and nothing restarts the calendar at
layer L. The parallel axis is therefore the 8 TP8 KV heads × the mutants. Each nominal run covers 36 layers, so the
whole set covers 288 layer-head pairs.

Results: see the lane line in `~/coord/lanes/TOK-QK.md` (filled in when the units finish).

## Real prefill history (COORD 10-27): the final verdict uses it

The verdict vectors are `vec_real`. They are built from the real 36-layer prefill K/V history, not the declared FP8 pattern (`kvl_history.py`, now smoke/debug only).

**Caveat (record in the receipt):** the history is NOT bit-exact chip arithmetic.
- The prefill of tokens 0..8190 uses HF BF16 CPU arithmetic (`kvl_prefill_hist.py`, `qwen3_deployment_quality.Qwen3(..., "gpu", "w8", "fp8", fold=True)`).
- The weights are the chip's norm-folded W8 ROM codes, prep-checked against fx/tp4.
- The K/V rounding is golden FP8.
- Only the decode at P8191 is the bit-exact TP4 ISA golden (`qwen_hbmacc_position_oracle_gpu --kv-history hist_real`).
- A bit-exact golden prefill would take ~76 h, over the 48 h rule.
- `kvl_hist_check.py` compares rows 0..15 against the golden's own 16-position prefill (`hist_check.json`). This checks layout and head/die mapping and gives an agreement figure.

Chain: `real_post.sh` on epyc2 (`/srv/opentallas-scratch2/claude/tok-qk-kvh`, log `post.log`).
- Steps: prefill container `kvh-prefill` -> `hist_real/` -> check -> `gold_real` -> `vec_real` (kv.hex, the format `kv_preload.py --as-layer` reads) -> rsync to `intel2:/srv/opentallas-scratch2/claude/tok-qk-kvl/vec_real` (+`.done`/`.failed`).
- `chain.sh` launches the 12 sims on `vec_real` once the build and `vec_real/.done` both exist.
