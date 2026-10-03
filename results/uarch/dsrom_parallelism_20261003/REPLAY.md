# DeepSeek-V4.1 ROM array: choosing the parallelism mapping

This is analytical model work only. No RTL or P&R was run, nothing is adopted, and `tools/uarch_model.py` and every pinned record are untouched.

For a weight-stationary ROM, a parallelism is two choices: where each weight byte lives, and which activations move. Each candidate is priced by re-timing the unified model's S58 graph (`cons_v41_rom`, run with the S58 selection's own settings) through two opt-in extensions:

- `tools/uarch_model_parallelism.py`, from this study;
- `tools/uarch_model_par2_boundary.py`, the PAR2 term from `claude/dsrom-par2-boundary-20261003` at aafbe3a75.

Pricing is done on physical NP2048 dies, 8 per stage.

## Replay

```
python3 tools/dsrom_parallelism.py          # rewrites model.json; refuses if the bytes differ (~10 min)
python3 -m pytest -q tests/test_dsrom_parallelism.py
```

The run checks two baselines before writing anything:

- the pinned S58 model: AR/MTP 2563.7/3809.4 tok/s at 1M and 2680.6/4176.7 at 200K;
- the PAR2 record (C1): 2347.4/3539.3 at 1M and 2445.0/3854.2 at 200K.

## Results

- AR and MTP are in tok/s.
- The path columns are µs on the 1M AR critical path.
- The power column is the hottest physical die at saturation; the cooling limit is 474.6 W.

| id | AR 1M | MTP 1M | AR 200K | MTP 200K | ΔAR/ΔMTP 1M vs C1 | dies/pkgs/stacks | field | chain | kv | TP coll | EP | CP | hops | PAR2 | max/mean | W | exact |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| M0 model, no PAR2 term (proxy) | 2563.7 | 3809.4 | 2680.6 | 4176.7 | +9.2 / +7.6 | 508/254/960 | 116.0 | 162.0 | 21.5 | 65.2 | 0 | 2.2 | 23.2 | 0 | 5.2 | 133 | no (K-split MoE) |
| **C1** PP58·TP4·PAR2 rows (current) | 2347.4 | 3539.3 | 2445.0 | 3854.2 | 0 / 0 | 508/254/960 | 116.0 | 162.0 | 21.5 | 68.5 | 0 | 2.2 | 24.6 | 31.3 | 5.2 | 133 | if MoE row split |
| C1x C1 + exact two-gather MoE | 2349.1 | 3517.4 | 2446.9 | 3828.2 | +0.1 / −0.6 | 508/254/960 | 116.0 | 162.0 | 21.5 | 68.1 | 0 | 2.2 | 24.6 | 31.3 | 5.2 | 133 | yes |
| **C2** PP + EP8, dense whole on a hub die | 1353.0 | 1123.3 | 1489.6 | 1253.1 | −42 / −68 | 566/283/264 | 424.4 | 168.3 | 94.5 | 0.2 | 28.5 | 0 | 23.2 | 0 | 5.0 | hub 190 | yes |
| **C3** PP + TP8 Megatron (aligned K split) | 2357.1 | 3142.2 | 2434.9 | 3323.2 | +0.4 / −11 | 508/254/960 | 123.7 | 158.4 | 21.5 | 95.0 | 0 | 2.5 | 23.2 | 0 | 4.3 | 122 | yes, imbalanced |
| **C4** C2 + CP8 index keys | 1482.4 | 1254.9 | 1512.8 | 1282.8 | −37 / −65 | 566/283/1076 | 424.4 | 139.4 | 56.4 | 0.2 | 28.5 | 2.5 | 23.2 | 0 | 2.3 | hub 228 | yes |
| C4b TP8 symmetric + EP8 + CP8 | 2232.5 | 2760.6 | 2302.2 | 2899.3 | −4.9 / −22 | 508/254/960 | 180.2 | 158.4 | 21.5 | 31.4 | 30.7 | 2.5 | 23.2 | 0 | 3.4 | 111 | yes |
| C5r hybrid, small matrices replicated | 2391.1 | 2948.3 | 2471.3 | 3107.1 | +1.9 / −17 | 508/254/960 | 158.8 | 158.4 | 21.5 | 53.9 | 0 | 2.5 | 23.2 | 0 | 3.7 | 115 | yes |
| C5 hybrid, TP8 per operator | 2536.8 | 3710.8 | 2627.1 | 3965.9 | +8.1 / +4.9 | 508/254/960 | 116.3 | 158.4 | 21.5 | 72.3 | 0 | 2.5 | 23.2 | 0 | 4.5 | 124 | yes |
| C5h + lm_head 8-way | 2576.9 | 3857.0 | 2670.2 | 4133.3 | +9.8 / +9.0 | 508/254/960 | 110.2 | 158.4 | 21.5 | 72.3 | 0 | 2.5 | 23.2 | 0 | 4.5 | 142 | yes |
| **C5hc + chase (RECOMMENDED)** | **2606.6** | **3968.6** | **2677.1** | **4159.9** | **+11.0 / +12.1** | 508/254/960 | 110.2 | 154.0 | 21.5 | 72.3 | 0 | 2.5 | 23.2 | 0 | 4.5 | 142 | yes |
| C5hc4 (4 stacks per die, sensitivity) | 2650.4 | 4086.7 | 2682.9 | 4185.8 | +12.9 / +15.5 | 508/254/1888 | 110.2 | 154.0 | 15.2 | 72.3 | 0 | 2.5 | 23.2 | 0 | 3.5 | 149 | yes |

**Throughput.** At 1M, saturated AR rises from 80,834 tok/s (head-bound) to 102,870 tok/s with C5h's 8-way head. At 200K it reaches 160,772 tok/s.

## Why each candidate lands where it does

The underlying ROM fact is that read time equals the bytes on the busiest die divided by that die's macros. Dense weights are about 60% of the active bytes per token. That fact decides each candidate below.

**C2 and C4: whole dense matrices on one die.** These lose 37–42% of AR.

- They push 8× more words through each macro, so field time on the path goes from 116 to 424 µs.
- The worst case is wo_a on the scarce BF16 pairs.

**EP: whole experts per die.** This concentrates E[kmax] = 2.18 of the 6 experts on the busiest die. Balanced TP puts 0.75 of an expert there.

- The expert read is therefore ×2.9.
- The combine payload grows 6× (each expert's FP32 output must arrive whole, because the golden sums experts in id order).
- Under MTP the union of about 35 experts makes this worse (C4b: −22% MTP).

**C3: Megatron row-parallel down.** This is exact only on golden chunk boundaries.

- FF = 2304 is 9 chunks, so the TP-8 shares are [2,2,2,2,1,0,0,0], an imbalance of 1.78×.
- Each expert's partial must be tree-reduced separately: a 143 KB all-reduce.

**C5r: replicating a_proj and router.** This removes two all-gathers (about 18 µs) but costs 29 µs on the BF16 router alone. It is rejected.

**C1: PAR2's owner hub.** It pays 6 × 2 UCIe crossings per layer, 31.3 µs in total.

**C5: symmetric TP-8 peers.** Each die runs the bit-identical hub chain, which removes the PAR2 crossings. In exchange, collectives span 4 packages, adding about 7 µs. The MoE becomes the exact two-gather.

**CP for attention softmax is rejected.** There are 640 rows whatever the context, and a partial-softmax combine breaks the golden order. CP applies only to the index-key scan; see `cp_attention` in model.json.

## Exactness basis

The golden references are in `tools/hdc_golden_v41.py`:

- `csum` chunk8 (lines 189–206): every K reduction is contiguous 8-term chunks plus a padded pairwise tree.
- `moe` (lines 980–990): whole experts summed in id order, then the shared expert.
- `topk_lowest_index`: the tie order for top-k.

What C5 needs to stay exact:

- **Head and o-group splits** cut no reduction.
- **wo_b's 8-way K split** gives each die an aligned 4-chunk subtree of the 32-chunk tree. The combine must be the fixed pairwise tree, not a ring.
- **Expert output rows** keep full K, so the id-order sum is local.
- **CP merge** concatenates in position order into one `tselect_final`.
- **Replicated chains** are bit-identical.

## Must be measured in RTL before adoption

These are listed in model.json under `recommendation.measure_first_in_rtl`:

- 8-die, 4-package all-gather and fixed-tree all-reduce latency at the 64-B flit, including blocking and backpressure. C7 found overlap worse than modelled.
- The MoE two-gather schedule against the full-shape golden.
- The wo_b aligned 8-way reduce, bit-exact.
- Lockstep check that the replicated hub chains are bit-identical.
- The CP-8 key writer/scanner and its position-ordered merge.
- The chase.
- The lm_head 8-way argmax merge.

## Records and tools to regenerate

These are listed in model.json under `recommendation.regenerate`:

- `uarch_model` TP-8 physical-die mode;
- native_shard_choices;
- the model-r4 PAR2 boundary/return ledger;
- partition_token_options;
- the par2_boundary and stage_balance records;
- the HBM placement at 2 stacks per die;
- the no-ECC model, macro inventory and physical contracts;
- v41_tp_exact_reprice at TP-8;
- the C7 exposure campaign at 8 dies.

## Approximations, all stated in the code

These choices are conservative:

- No overlap credit for new collective bytes.
- TP-8 t_ret not credited.

These are estimates rather than measurements:

- The fixed part of a new collective is the graph's calibrated median.
- Hops are unchanged; each die forwards to its counterpart.
- Physical-die power is the rank die's static plus half of its dynamic.
- The C2 and C4 hub power assumes an 88% non-expert dynamic share.
- KV capacity scales with layer HBM stacks.
