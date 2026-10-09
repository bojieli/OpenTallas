# Qwen3-8B ROM: ROM die (r22k) + KV die (stream kv-die, 2026-10-09)

**Owner decision (2026-10-09 ~04:00 PT).** The Qwen3-8B ROM design becomes a TP4 ROM die + KV die pair per package (option 1a). KV never crosses the link.

**Status.** Every number here is a priced candidate or a generator floorplan, not a closed rate.

## Results

| | ROM die r22k | KV die |
|---|---:|---:|
| Die | 23,095.6 × 32,801.8 µm = **757.6 mm²** (reticle margin 100.4 mm²; r21c 846.8) | 7,082.2 × 24,328.1 µm = **172.3 mm²** |
| UCIe-A x64 macro | 0.605 mm², 777.6 µm of the S edge, bottom of spine column M | 0.605 mm², 777.6 µm of the N edge |
| Legality | 0 overlaps / 0 outside, 12,910 instances | 0 / 0, 1,142 instances; OpenROAD real case OT_LEGAL 0 / 0, OT_ASSERT PASS |
| die_top_lint | connectivity 0, missing pins 0, unbound real pins 0 | connectivity 0, missing pins 0; strict ports (bound masters) OK |
| Relay margin lint (data buses, SS reach 504 µm) | 55 reach / 64 far-side, all on inherited r21c spine chains (r21c itself: 53 / 55); 0 on the new crossing buses | PASS (0 / 0) |
| Area by kind | tiles 529.6, spine 36.4, IO 17.6, relays 16.4, stations 8.4 mm² | PHY 40.0, row engines 21.0, aggregators 24.9 (ASSUMED frame), controllers 12.0, landings 8.4, CDC 4.3, SerDes host PHY 3.6, relays 1.8, centre blocks 2.1 mm² |

**Link bench.** One attention layer step crosses the link end to end, in `bench.json`:
1. the ROM faces send CTL, KVN and Q;
2. r22k relay stages (27 to 29);
3. the ROM end;
4. the UCIe macro pair;
5. the KV end;
6. `qkd_seq`;
7. the near-HBM attention (R = 8, the `_p` successors) at the KV-die stage counts, with the KV merge;
8. RES returns to the VM.

All of the following are bit-exact against `tools/hdc_golden.py`:
- contexts 1, 129, 2048, 4097, 8191 and 8192 (four kinds), with the VM stalled (stall 1) and not stalled (stall 0);
- the 65 embedding words in each direction;
- the host words and the token word;
- the 4 posted KV rows.

The HBM model poisons the rows at t = T-1, so a result can only be exact if the KV merge used the K/V that crossed the link. The mutants are in `bench.json`:
- extra link credit;
- merge off;
- dropped flit;
- early credit;
- Q beats swapped;
- plus the credit-stress base, which must stay exact.

**Re-price (`reprice.json`).** The ctx 8192 layer step through the link takes **1,879 cycles** (best 1,869, worst 1,883). It replaces the 1,756 cycles of tile attention plus softmax_norm.

| | Cycles | tok/s |
|---|---:|---:|
| Layer | 6,077 (TP4 5,954) | |
| Embedding fetch | 287 (worst 614) | |
| L0 cold KV-prefetch penalty | 0 (TP4: 762) | |
| **Token** | **222,418** | **5,395.2** |

The token is **−1.77 %** against TP4's 5,492.7 tok/s (range 5,383.8–5,404.1). It is −1.3 % against the option-1a model (5,466.4). That model assumed the tile attention stays and only 2 × 14 crossing cycles are added. Putting attention where the KV lives means near-HBM attention, and its step is the cost.

## Files

| Path | What |
|---|---|
| `CONTRACT.md` / `CONTRACT.json` | The interface contract: classes, formats, credits, clocking, latency, review-0327 decisions |
| `bench.json` | Layer-step bench through the link (best / typical / worst PHY latency), mutants |
| `reprice.json` | Token re-price |
| `token_path/qwen_kvdie.json` | Token-path view (`tools/token_path_export.py --only qwen_kvdie`) |
| `rom_r22k.json`, `rom_r22k_insts.json` | r22k record (`tools/qwen_kv_die/rom_record.py`): size, area by kind, crossing-bus relay stages, margin lint. Block rectangles for the explorer |
| `rom_r22k_check.json` | `tools/qwen_r21b_check.py r22k`. Its `ok` is false only because of pin-region cfgs unrelated to r22k (qfd_crom48 empty regions, qfd_emb_far92 / strip_bus92 regex) |
| `rom_r22k_lint.json` | `die_top_lint --die qwen_rom --qwen-recipe r22k`. Its `margin_lint` was computed before the clock-trunk filter (clock relay rows counted as data chains); the data-bus lint is in `rom_r22k.json` |
| `kv_die/plan.json`, `kv_die/lint.json` | KV-die generator record (`tools/qwen_kv_die/kv_die.py plan`) and `die_top_lint --die qwen_kv` |

**Explorer.** `site/chip_explorer` has the two-die view (Qwen design, "ROM + KV die"), with geometry key `qwen_kvdie` in `inputs/geo.json`.

## Reproduce

```
python3 tools/qwen_kv_die/contract.py --out results/arch/qwen_kv_die_20261009/CONTRACT.json
python3 tools/qwen_kv_die/phy_gen.py --out physical/qwen_kv_die_phy
python3 tools/qwen_kv_die/rom_record.py --out results/arch/qwen_kv_die_20261009/rom_r22k.json     # ~7 min (scipy)
python3 tools/qwen_kv_die/kv_die.py plan --out results/arch/qwen_kv_die_20261009/kv_die
python3 tools/die_top_lint.py lint --die qwen_kv --out DIR ; python3 tools/die_top_lint.py lint --die qwen_rom --qwen-recipe r22k --out DIR
rtl/test/qwen_kv_die/bench_run.sh SRC OUT 28 1 7 5 29 28 34      # ROM_ST KV_ST LINK PHY_LAT QX RX KVL (typical); 3 / 9 best / worst
python3 tools/qwen_kv_die/collect_bench.py ... ; python3 tools/qwen_kv_die/reprice.py ...
python3 tools/qwen_kv_die/explorer_geo.py --rom results/arch/qwen_kv_die_20261009/rom_r22k_insts.json && python3 tools/chip_explorer_build.py
```

**Die evidence.** The GRT and STA chains are `tools/qwen_kv_die/chain/die_chain.sh` (case, PDN, GRT, STA TT/FF). They are running on EPYC1 in `/srv/opentallas-scratch/claude/kv-die/die_{kv,r22k}`; see the COLLECT section of `kv-die.log`.
