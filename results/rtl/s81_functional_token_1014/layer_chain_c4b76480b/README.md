# S81 full-token layer chain, layer vehicle (s81-functional-token, 2026-10-14)

All 40 layers of the DeepSeek-V4.1 1M token (position 1,048,575) on `tb_s81_die_layer` at production shape (NG 256,
hierarchical HC slab, DPI fp, `--coef-split`, nominal links), each layer from its golden entry h (fixtures
`tools/s81_ctrl/die_layer_chain.py`, built from the released checkpoint subset + the 1M shard, every internal assert true;
L0 / L2 from the pinned su_cases pickle). Chain: the shard's h_out(L) == h_in(L+1) and pre_out == pre_in for every L
(`chain_continuity.txt` PASS), and each layer's H_STORE rows are bit-exact against its golden h_out, so the 40 exact layers
chain into the token's final h. Result: **40 / 40 PASS** (norm rows 330/330, H_STORE 640/640 each), **16 / 16 mutants FAIL**
(mut_hc + mut_coll on L0, L5, L10, L15, L20, L25, L30, L35). `record.json` has every layer; sum of layer cycles 414,964.

| layer type | layers | result | layer cycles |
|---|---|---|---|
| sliding | 0 | PASS | 8,823 |
| engram + sliding | 1 | PASS | 9,941 |
| ratio2 + compressor + indexer | 2, 8 | PASS | 17,737-17,750 |
| ratio2 | 3-7, 9-13, 15-19 | PASS | 8,743 |
| engram + ratio2 + compressor + indexer | 14 | PASS | 18,861 |
| ratio1 + compressor + indexer + candidates | 20 | PASS | 34,410 |
| ratio1 | 21-23, 25-27, 29-31, 33-35, 37-39 | PASS | 8,743 |
| ratio1 + indexer | 24, 28, 32, 36 | PASS | 11,264-11,296 |
| head (+ argmax, token 21946) | - | NOT IN THIS VEHICLE | - |
| MTP draft layers (DSpark) | - | NOT IN THIS VEHICLE (no shard) | - |

Every layer is MoE (top-6 of 384): the model has no dense layer. RTL computes: control plane, gather + capture field
phases (golden root partials injected), HC slab NORM / POST / H_STORE, the 4-die collective with real link endpoints. NOT
computed by RTL here: the field matvec, SU / svc / select / col / hcx / Engram engines (behavioural, golden durations), so
attention and MoE arithmetic enter as golden y. Vehicle fix: `die_layer_stim.py` had no L20 `attn.cand.merge` (KeyError).
