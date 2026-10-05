# PAR2 intra-rank boundary: DS4096-TP4-S58-PAR2-NP2048

This is analytical model work only. No RTL or P&R was run, and nothing here is adopted.

`tools/uarch_model.py` and every pinned record are untouched. The term lives in the opt-in extension `tools/uarch_model_par2_boundary.py`, and `par2=None` is the unchanged baseline call.

## Replay

```
python3 tools/dsrom_par2_boundary.py      # rewrites model.json; refuses if the bytes differ
python3 -m pytest -q tests/test_dsrom_par2_boundary.py
```

- The baseline reproduces the pinned S58 figures exactly before anything is written: AR/MTP 2563.7/3809.4 at 1M and 2680.6/4176.7 at 200K.
- Pricing uses the S58 selection's own `cons_v41_rom` settings, taken from `tools/dsrom_4096_partition_token_options.py`.

## What crosses the boundary

The source is `dsrom_parallel_owner_binding_20261002/r1/native_shard_choices.jsonl.gz`.

PAR2 is a row (return-region) split, R128 → 2 × R64.
- It cuts no reduction: 0 cut regions and 0 cross-shard K reductions.
- So no partial sums, Sinkhorn/mHC, index/top-k, attention partials or collectives cross. The hub and the KV stay on shard 0.
- Only field weight calls with rows on shard 1 cross. Each one needs its activation sent out and its remote rows sent back.

Per rank per token there are 1,149 calls:
- 1,050 cross. Per layer that is 18 selected-expert calls (exp w1/w3/w2), plus wq_a, wq_b, wo_a ×2, wo_b, and shared w1/w3/w2. There are also 8 indexer wq_b calls and 2 Engram wkv calls.
- 99 stay local: wkv, gate, indexer weights_proj/wk, compressor.

Remote results are 69 bits per row: 8.8 kbit (wq_a) up to 283 kbit (wq_b) per call.

Calls inside one model step are independent, so dataflow level 4 overlaps them. The exposed count is crossing steps on the critical path: 6 per layer (a_proj, wq_b, wo_a, wo_b, experts_gu, down), 240 per token at both 1M and 200K.

## Link

The PAR2 pair shares a 2-die package over UCIe. One-way crossing cost, L1 = 65.2 ns:
- VM → UCIe PHY: 34 stages (W18b measured), paid on both dies, at 504 µm per stage (0.833 ns, 1.2 GHz SS).
- UCIe core: 8.5 ns. This is technology.json's 10 ns minus its 1.5 ns on-die routing. It includes the die-to-die synchroniser.
- No slow↔fast clock-domain crossing beyond the one the local path already pays.

Bandwidth:
- Need: 0.91 TB/s (4,416-bit return port plus 1,681-bit activation, every cycle).
- Available: 4.2 TB/s, so 4.6× headroom and no serialisation.

## Key rows (AR / MTP tok/s)

| variant | 1M | 200K |
|---|---|---|
| base S58 (no term) | 2563.7 / 3809.4 | 2680.6 / 4176.7 |
| owner (as designed), fc4 quad | 2347.4 / 3539.3 (−8.4%) | 2445.0 / 3854.2 |
| owner, board mesh | 2195.4 / 3510.4 (−14.4%) | 2280.5 / 3820.0 |
| owner, shards across packages | 2047.2 / 3378.5 (−20.2%) | 2121.1 / 3664.2 |
| mirror_full (KV ×2), fc4 | 2414.6 / 3592.8 | 2518.0 / 3917.7 |
| layer split S116, fc4 | 2227.5 / 2737.0 | 2315.2 / 2921.6 |
| **expert split, fc4** (conservative) | **2500.4 / 3657.2 (−2.5% / −4.0%)** | **2611.4 / 3994.4** |
| expert split, fc4, collective overlap credited | 2537.2 / 3790.6 (−1.0% / −0.5%) | 2651.6 / 4154.0 |

Link sensitivity (UCIe core 3 or 20 ns) moves the owner row by ±1% and the expert-split row by 0.2% or less.
