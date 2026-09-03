# What the weight-to-KV ratio and the KV capacity decide

> **CORRECTION, 2026-08-30.** Every DeepSeek row of this document was wrong, in
> the same direction, by the same cause. The KV model's `entry_bytes` and
> `index_entry_bytes` constants were retracted (583 → 1,024 and 68 → 256), and
> an index-scan threshold at 8,001 tokens was retracted as an instrumentation
> artifact. DeepSeek KV read/token rose ~3.2× and KV/user ~2.0×, so every
> weight-to-KV ratio in §2 fell by ~3.2× and every DeepSeek area in §3–§4 roughly
> doubled. **The figure §7 nominated as "the project's actual finding" — 260:1
> for Pro at 200,000 tokens — is 3.10× too high and is now 83.8:1.** The three
> Qwen rows never moved and are correct as published.
>
> Separately, the FP8 rows of §5 are **retracted**: the study no longer prices a
> re-encoding of a released checkpoint on either side, and the ROM density they
> used (19.7 MB/mm²) is not the density the model derives.
>
> **The document's reasoning survives its numbers.** Sparsity plus long context
> is still the ROM-favourable regime; the margin is smaller and §4's qualitative
> split narrows from 3.8× to 2.1×. The claims that depended on the *magnitude*
> are rewritten in §7.

The previous version of this document opened by saying *"Every figure comes from
`configs/models/*.json` through `opentallas.workload`"*. That was not a
provenance claim a reader could act on: `src/opentallas/workload.py` has **no
`main`, no CLI and no argparse**, and no artifact in this repository emitted this
table. Naming a module is not naming a command. Here is the command, and every
table below states which of its columns it produces:

```sh
PYTHONPATH=src python3 -c '
from opentallas import workload as W
from opentallas.schema import ModelProfile
for name, ctxs in [("qwen3-8b",[1024,8192,32768]),
                   ("deepseek-v4-flash-0731",[200000,1000000]),
                   ("deepseek-v4-pro-0813",[200000,1000000])]:
    m = ModelProfile.load(f"configs/models/{name}.json")
    wt = W.weight_traffic(m, 1); wb = wt.dense_bytes + wt.routed_bytes
    for c in ctxs:
        kv = W.kv_traffic(m, c)
        print(f"{name:24} ctx={c:>9,} W={wb/1e9:8.3f} GB KVread={kv.read_bytes/1e9:7.4f} GB "
              f"KV/user={kv.storage_bytes_per_user/1e9:7.4f} GB W:KV={wb/kv.read_bytes:7.2f}")'
```

Three rows are independently confirmed by generated artifacts, and one is
confirmed by an **execution** of the released DeepSeek implementation; those are
marked in place. Nothing here is an assumed hardware number except where §3 and
§5 name a density, and those are cited to the study that derives them.

## 1. The two quantities

**Weight bytes read per token** is fixed by the checkpoint (for a dense model)
or by the experts one token activates (for an MoE). It does not grow with
context.

**KV bytes read per token** grows **linearly with context**. Sparse attention
lowers the constant; it does not change the growth. And **KV storage** grows
linearly with context *and* with batch, and sparsity does not reduce it at all —
a sparsely-attended cache is still a full cache.

Those are different constraints and they push in different directions. The first
sets how much a ROM weight path is worth. The second sets whether the KV can
live on-die. That reasoning is unchanged by the correction; only the constants
moved.

## 2. The weight-to-KV read ratio

| model | context | weight read/token | KV read/token | **W:KV** | was | evidence |
|---|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1,024 | 15.137 GB | 0.1510 GB | **100.3** | 100 | derived |
| Qwen3-8B | 8,192 | 15.137 GB | 1.2080 GB | **12.5** | 12.5 | derived ✓ artifact | <!-- figure: 1.2080 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=Qwen3-8B].kv_read_bytes_per_user_token" scale="1e-9" name="Qwen KV read/token at 8K, GB" --> <!-- figure: 12.5 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=Qwen3-8B].weight_to_kv_read_ratio_b1" name="Qwen W:KV at 8K" -->
| Qwen3-8B | 32,768 | 15.137 GB | 4.8318 GB | **3.1** | 3.1 | derived |
| DeepSeek-V4-Flash | 200,000 | 11.218 GB | **0.3175 GB** | **35.3** | ~~113~~ | **executed** | <!-- figure: 11.218 src="results/model-traffic/sweep.csv#active_weight_read_bytes_per_step" where="model=DeepSeek-V4-Flash-0731;context_tokens=200000;batch_size=1" scale="1e-9" name="Flash weight read/token, GB" --> <!-- figure: 0.3175 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].kv_read_bytes_per_user_token" scale="1e-9" name="Flash KV read/token at 200K, GB" --> <!-- figure: 35.3 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].weight_to_kv_read_ratio_b1" name="Flash W:KV at 200K" -->
| DeepSeek-V4-Flash | 1,000,000 | 11.218 GB | **1.5207 GB** | **7.4** | ~~24.5~~ | derived |
| DeepSeek-V4-Pro | 200,000 | 39.667 GB | **0.4731 GB** | **83.8** | ~~260~~ | derived |
| DeepSeek-V4-Pro | 1,000,000 | 39.667 GB | **2.2075 GB** | **18.0** | ~~59~~ | derived ✓ artifact | <!-- figure: 39.667 src="results/model-traffic/sweep.csv#active_weight_read_bytes_per_step" where="model=DeepSeek-V4-Pro-0813;context_tokens=1000000;batch_size=1" scale="1e-9" name="Pro weight read/token, GB" --> <!-- figure: 2.2075 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].kv_read_bytes_per_user_token" scale="1e-9" name="Pro KV read/token at 1M, GB" --> <!-- figure: 18.0 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].weight_to_kv_read_ratio_b1" name="Pro W:KV at 1M" -->

Every row: the command above.
Artifact confirmation for the two ticked rows:
[`results/roofline/n6_vs_a100/REPORT.md`](../results/roofline/n6_vs_a100/REPORT.md)
→ "Models and their work", columns `KV read/token` and `W:KV at B=1`
(Qwen @8,192 = 1.208 GB / 12.5; Pro @1M = 2.207 GB / 18.0). Regenerate with
`make roofline`.

**The Flash @200,000 row is executed, not derived**, and it is the strongest
evidence in this document.
[`results/abi3/deepseek_v4_reference_oracle_context_ladder.json`](../results/abi3/deepseek_v4_reference_oracle_context_ladder.json)
→ `context_ladder_summary.rungs[4]` ran the released implementation at 200,000
tokens and measured `measured_kv_bytes_per_decode_step = 317,435,904` against a
profile prediction of `317,461,760` — agreement to 0.008% — and reports
`weight_to_kv_read_ratio_at_this_context = 35.335`. The same file's
`context_ladder_summary.executed` lists all five rungs
`[1000, 8000, 32000, 128000, 200000]` as run. It also gives the ratio's whole
executed curve: **894.1 → 390.9 → 173.1 → 53.6 → 35.3** at 1K / 8K / 32K / 128K
/ 200K.

The independently generated hardware-free sweep agrees:
[`results/model-traffic/sweep.csv`](../results/model-traffic/sweep.csv), row
`DeepSeek-V4-Flash-0731, 200000, 1`, `weight_to_kv_read_ratio = 35.33578981`,
`kv_read_bytes_per_user_token = 317,456,384`, `active_weight_read_bytes_per_step
= 11,217,572,060`. Regenerate with `make model-traffic`.

**The result is still the opposite of the intuition that long context erodes the
ROM case, and the retraction did not change its direction.** Sparse attention
keeps DeepSeek's KV read small: at 200,000 tokens Flash reads 317 MB of KV
against 11.2 GB of weights. The models that need wafer-scale are precisely the
ones where the weight path dominates *most*. What changed is the size of the
gap: 113:1 was wrong, 35:1 is right, and 35:1 is still an order of magnitude.

Dense attention behaves the other way. Qwen3-8B falls from 100:1 at 1K to 3.1:1
at 32K, because it rereads the whole cache every token. A dense 8B model's ROM
advantage is a **short-context** advantage. Those three rows are unchanged.

## 3. KV capacity, and where SRAM stops working

On-die SRAM area to hold the KV cache. The previous version used a hand-entered
0.024 µm²/bit at 60% array efficiency. The model derives the density instead:
**3.009 MB/mm² at N6**, from a 0.027 µm² 6T HD bitcell (`configs/hardware/technology.json` <!-- figure: 3.009 src="results/roofline/n6_vs_a100/REPORT.md#Value" table="Derived technology at N6" where="Quantity=SRAM capacity density" name="SRAM capacity density at N6" -->
→ `nodes.N6.sram_hd_bitcell_um2`, `derived` from the published N7 cell) at 65%
array efficiency (`sram.array_efficiency`, `assumed`, swept 0.55–0.75), and the
result is reported at
[`results/roofline/n6_vs_a100/REPORT.md`](../results/roofline/n6_vs_a100/REPORT.md)
→ "Derived technology at N6". One reticle die is **815 mm²** <!-- figure: 815 src="configs/hardware/technology.json#reticle.area_mm2.value" name="reticle area" -->
(`configs/hardware/technology.json` → `reticle.area_mm2`, the published Taalas
HC1 die area). Bytes are decimal SI throughout (`technology.json` → `units`).

Area = `KV/user × batch / 3.009 MB/mm²`; dies = `area / 815 mm²`.

| model | context | KV/user | B=1 | B=8 | B=64 | was (B=1 / B=8 / B=64) |
|---|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1,024 | 0.1510 GB | 50 mm² | 401 mm² | 3.9 dies | 48 / 387 mm² / 4 dies |
| Qwen3-8B | 8,192 | 1.2080 GB | **401 mm²** | 3.9 dies | 31.5 dies | 387 mm² / 4 / 30 dies | <!-- figure: 1.2080 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=Qwen3-8B].kv_storage_bytes_per_user" scale="1e-9" name="Qwen KV/user at 8K, GB" -->
| Qwen3-8B | 32,768 | 4.8318 GB | 2.0 dies | 15.8 dies | 126.1 dies | 2 / 15 / 121 dies |
| DeepSeek-V4-Flash | 200,000 | **1.3816 GB** | **459 mm²** | **4.5 dies** | **36.1 dies** | ~~226 mm² / 2 / 18 dies~~ | <!-- figure: 1.3816 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].kv_storage_bytes_per_user" scale="1e-9" name="Flash KV/user at 200K, GB" -->
| DeepSeek-V4-Pro | 1,000,000 | **9.8560 GB** | **4.0 dies** | **32.2 dies** | **257.2 dies** | ~~2 / 16 / 126 dies~~ | <!-- figure: 9.8560 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].kv_storage_bytes_per_user" scale="1e-9" name="Pro KV/user at 1M, GB" -->

The Qwen rows move only by the density change (19.7→16.2 for ROM, 0.024 µm²/60%
→ 0.027 µm²/65% for SRAM); the DeepSeek rows move by that *and* by the ~2× KV
storage correction. `kv_traffic(...).storage_bytes_per_user` is the field;
1.382 GB and 9.856 GB are also printed in `n6_vs_a100/REPORT.md` → "Models and
their work", column `KV/user`.

SRAM holds the KV only for a small model, at short context, at low batch. That
is exactly the Taalas HC1 regime, and it is why its published figure is quoted
**per user**. That conclusion is unaffected; it got stronger, because the
DeepSeek caches are twice as large as this document used to say.

## 4. Bandwidth versus capacity: they bind different machines

HBM3E is taken at 24 GB and ~1.2 TB/s per stack. Demand columns are
`kv_traffic(...).read_bytes × rate` and
`kv_traffic(...).storage_bytes_per_user × 64` from the command in the header.

| target | KV bandwidth demand | stacks for BW | KV capacity at B=64 | stacks for capacity | binds on |
|---|---:|---:|---:|---:|---|
| Qwen3-8B @8K, 10,000 tok/s | **12.08 TB/s** | **10.1** | 77.3 GB | 3.2 | **bandwidth**, 3.2× |
| DeepSeek-Flash @200K, 6,600 tok/s | ~~0.65~~ **2.10 TB/s** | 1.7 | ~~45~~ **88.4 GB** | **3.7** | **capacity**, 2.1× |
| DeepSeek-Pro @1M, 3,000 tok/s | ~~2.02~~ **6.62 TB/s** | 5.5 | ~~322~~ **630.8 GB** | **26.3** | **capacity**, 4.8× |

**Dense Qwen is KV-bandwidth-bound; sparse DeepSeek is KV-capacity-bound.** That
distinction survives and still determines the memory technology. Its margin for
Flash narrows from **3.8× to 2.1×** — capacity still binds, but it is now within
a factor of two of bandwidth rather than a factor of four, so the conclusion is
weaker than it was stated to be:

- Qwen at 8K needs 12.08 TB/s of KV bandwidth. Ten HBM stacks would supply it; a
  few hundred mm² of SRAM supplies it trivially. **SRAM is chosen for
  bandwidth**, and the capacity limit is what caps context and batch.
- DeepSeek at 200K needs 2.10 TB/s and tens to hundreds of GB. **HBM is chosen
  for capacity**, and its bandwidth is not the constraint — but at 1.7 stacks
  against 3.7 it is no longer negligible either.

## 5. Why the big models need a wafer — and it is the weights, not the KV

ROM array area at the **released packing only**. ROM capacity density is derived,
not entered: **7.295 MB/mm² at N6** and **9.380 MB/mm² at N5**, from the same <!-- figure: 7.295 src="results/roofline/n6_vs_a100/REPORT.md#Value" table="Derived technology at N6" where="Quantity=ROM capacity density" name="ROM capacity density at N6" --> <!-- figure: 9.380 src="results/roofline/n5_vs_b200/REPORT.md#Value" table="Derived technology at N5" where="Quantity=ROM capacity density" name="ROM capacity density at N5" -->
6T HD bitcell scaled by the current 0.33 ROM-to-SRAM cell-area ratio at 52%
array efficiency (`configs/hardware/technology.json` →
`rom.cell_to_sram_cell_area_ratio`, `rom.array_efficiency`; both `derived`, both
swept). Reported at
`n6_vs_a100/REPORT.md` and `n5_vs_b200/REPORT.md` → "Derived technology at N6/N5".
Checkpoint bytes and bits/parameter are `n6_vs_a100/REPORT.md` → "Models and
their work". Wafer = 46,225 mm², reticle = 815 mm² <!-- figure: 46,225 src="configs/hardware/technology.json#wafer.area_mm2.value" name="wafer area (input echo)" -->
(`technology.json` → `wafer.area_mm2`, `reticle.area_mm2`).

| model | representation | checkpoint | bits/param | ROM array @N6 | @N5 | reticles @N5 | wafer @N5 |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | released BF16 | 16.4 GB | 16.00 | 2,246 mm² | 1,747 mm² | **2.1** | 3.8% | <!-- figure: 16.4 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=Qwen3-8B].checkpoint_bytes" scale="1e-9" name="Qwen checkpoint, GB" --> <!-- figure: 16.00 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=Qwen3-8B].native_bits_per_parameter" name="Qwen bits/param" -->
| DeepSeek-V4-Flash | released MXFP4+FP8 | 166.9 GB | 4.70 | 22,875 mm² | 17,792 mm² | **21.8** | 38.5% | <!-- figure: 166.9 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].checkpoint_bytes" scale="1e-9" name="Flash checkpoint, GB" --> <!-- figure: 4.70 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Flash-0731].native_bits_per_parameter" name="Flash bits/param" -->
| DeepSeek-V4-Pro | released MXFP4+FP8 | 892.7 GB | 4.46 | 122,372 mm² | 95,178 mm² | **116.8** | **205.9%** | <!-- figure: 892.7 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].checkpoint_bytes" scale="1e-9" name="Pro checkpoint, GB" --> <!-- figure: 4.46 src="results/roofline/n6_vs_a100/analytical.json#model_summaries[model=DeepSeek-V4-Pro-0813].native_bits_per_parameter" name="Pro bits/param" -->

> **The FP8 rows are retracted.** The previous version of this table offered
> every model a hypothetical FP8 re-encoding — Qwen at 416 mm², Flash at
> 14,416 mm², Pro at 81,218 mm² — and used the Qwen row to claim a
> single-half-reticle part. The study has since removed that option
> (`4c24730 fix(roofline): price every design at the release's own packing,
> nothing else`) for three compounding reasons: it was offered to the ROM side
> only, so an 8-bit ROM machine competed against a 16-bit GPU; no executed lane
> validates it, since `rom_qwen3` declares BF16 contracts and no FP8 contract at
> all, and the oracle-identical tokens this program rests on were produced at
> BF16; and re-encoding BF16 to FP8 is a *quantisation*, not a repacking, so it
> would produce different tokens by an unmeasured amount. Half of every feasible
> Qwen comparison was being won by such a design, the best at **30.79×**; with
> the option removed and the corrected physical inputs applied, the Qwen
> batch-1 `smallest silicon` iso-area ratio is **5.00×** <!-- figure: 5.00 src="results/roofline/n6_vs_a100/REPORT.md#Per-user ratio" table="Iso-area comparison" where="Model=Qwen3-8B;B=1;Pick=smallest silicon" name="best Qwen batch-1 iso-area ratio" -->
> (`n6_vs_a100/REPORT.md`, iso-area table, row `Qwen3-8B | 1 | smallest silicon`).
> The rule is pinned by
> `tests/test_roofline.py::test_no_design_stores_weights_at_a_precision_the_release_does_not_have`.
> Only Qwen3-8B was affected; Flash and Pro ship at 4.70 and 4.46 bits and were
> already below the 8.5-bit threshold.

Qwen3-8B needs **2.1 reticle fields of ROM at N5 and 2.8 at N6** — at least
three fields at either node, using the released BF16 packing rather than the
retracted FP8 half-die. Flash needs about 22 reticles at N5, so a wafer-scale
layout remains justified. Pro in its released representation consumes 206% of
a wafer in ROM alone at N5 and 265% at N6, leaving nothing for compute at
either node; a Pro machine is therefore at least three wafers, and pays an
inter-wafer link for it
(see [`docs/WAFER_VERSUS_ARRAY_LATENCY.md`](WAFER_VERSUS_ARRAY_LATENCY.md) §3).
**That is where the area balance genuinely binds.** The claim that the stored
representation is therefore a design variable is *still true of a mask ROM* —
but it is a claim about manufacturing, not a licence to price a re-encoding no
execution has validated, and this document made that mistake.

## 6. The architecture this forces

| | Qwen3-8B | DeepSeek-V4-Flash | DeepSeek-V4-Pro |
|---|---|---|---|
| part | three-reticle array at N5 | wafer | 3+ wafers |
| weights | ROM, 1,747 mm² @N5 | ROM, ~22 reticles | ROM, ~117 reticles |
| KV | **SRAM** (bandwidth) | **HBM** (capacity) | **HBM** (capacity) |
| binds at low batch | KV bandwidth | weight read | weight read |
| binds at high batch | KV capacity | KV capacity | KV capacity |

Each memory is chosen for the quantity that actually binds. Weights go to ROM in
every case, because W:KV is between **3.1 and 100** and never inverts.

Two qualifications the previous version did not carry. First, the old row
*"compared against **one** / ~56 / ~112 GPU dies"* is removed: it was a
device-count assertion with no producer, and the studies now report the GPU
cluster each design is actually compared against, at stated equal area, in their
iso-area tables. Second, the binding-constraint rows are the *model's* language
and the model reports them per point — the census is at `n5_vs_b200/REPORT.md`
→ "Binding constraint census".

## 7. What this means for the comparison

**RETRACTED:** *"The ROM advantage is largest exactly where W:KV is largest:
DeepSeek-V4-Pro at 200,000 tokens, at 260:1."* The ratio there is **83.8:1**.
And it is a **derived** figure, not an executed one — the executed context ladder
covers Flash, not Pro, and no Pro row in this repository is measured.

The corrected statement:

> The ROM advantage is largest where W:KV is largest — **DeepSeek-V4-Pro at
> 200,000 tokens, at 83.8:1 (derived)** and **DeepSeek-V4-Flash at 200,000
> tokens, at 35.3:1 (executed)**. It is smallest for a dense model at long
> context, where it falls to 3.1:1 and the machine becomes a KV engine that
> happens to have its weights on-die.

The previous version said this *"should be stated as the headline of any
write-up, because it is counter-intuitive and it is the project's actual
finding"*. The finding is intact and the headline is not: **sparsity plus long
context is the ROM-favourable regime, not the adverse one** remains true, and
the number attached to it was 3.1× too large for a year of write-ups. A W:KV
ratio is also not a speedup — the iso-area studies put the batch-1 advantage at
**5.90×** for Pro and **5.76×** for Flash at 554,700 mm² <!-- figure: 5.90 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after" table="latency separation" where="Model=DeepSeek-V4-Pro-0813;mm2=554700" name="Pro batch-1 iso-area ratio at 554,700 mm2" --> <!-- figure: 5.76 src="results/roofline/n6_vs_a100/REPORT.md#Ratio after" table="latency separation" where="Model=DeepSeek-V4-Flash-0731;mm2=554700" name="Flash batch-1 iso-area ratio at 554,700 mm2" -->
(`n6_vs_a100/REPORT.md`, "The latency separation, before and after, at batch 1",
`Ratio after` column), and every one of those is bounded by ROM service, KV
service, compute, collectives, capacity, power and cooling, none of which a
traffic ratio prices.

## What nothing produces

- **`weight_traffic` for Qwen returns 15.137 GB against a 16.381 GB checkpoint.**
  The difference is real and explicable (untied embeddings and resident-only
  tensors are not read per decode step), but no artifact states the
  reconciliation, and this document does not assert one.
- **No artifact emits the tables in this document.** The command in the header
  reproduces §2 and §4; §3 and §5 are my arithmetic on two densities and two
  byte counts that *are* cited. Until something writes this table to
  `results/`, it will go stale again the next time the KV model moves — which is
  precisely how it went stale this time.
