# Proposed doc corrections (not applied)

Codex owns `main` and `docs/`, so this branch edits no published doc and no pinned predecessor record. Each item below gives the location (checked at c5ae2f69d), what is wrong, and the replacement. The replacement figures come from the records in this directory. They are model-only and not adopted.

## 1. Headline identity: the published rate is for TP2 + DFlash, but the adopted design is TP4 AR

| Location | Now | Problem | Proposed |
|---|---|---|---|
| `docs/ARCHITECTURE_ATLAS.html:210, 238, 276-277, 1278, 1417` | 18,720 tok/s DFlash and 10,874 AR on "a two-reticle package ... tensor-parallel 2" | These describe the TP2 package with DFlash speculation (`results/arch/qwen3_budget.json`). The adopted design is option C, TP4, AR only (atlas :640). Its rates assume KV is perfectly overlapped at 7.2 TB/s. | Label these as the superseded TP2 + DFlash design point. Publish the option C AR rate with all 20 identity fields (`summary-r1.json:identity_fields`). The calibrated finite-calendar rate is **2,793 tok/s (357.99 us)** for the current fill path. The selected-for-build near-HBM model entry is **5,237 tok/s (190.97 us)**. |
| `docs/HEADLINE_BUNDLE.md:38` (`qwen.dflash` 18,720), `:63` (`qwen.rate_8k` 10,874) | TP2 package rows | Same identity mismatch. `speculation=dflash` and `design=TP2` cannot be compared with any TP4 AR record (`summary-r1.json:refused_comparisons.atlas_headline_TP2_DFlash`). | Mark as superseded TP2. Add a TP4 AR row whose identity is this record's. |
| `docs/MICROARCH_MODEL.md:341` | 10,874 (published, TP2) beside 9,851 (option C) in one row | Two designs presented as one comparison | Split the row, or state that the 10,874 figure is TP2 + DFlash-era. |

## 2. Mixed-position calibration: the 6,222 tok/s row

| Location | Now | Problem | Proposed |
|---|---|---|---|
| `docs/MICROARCH_MODEL.md:707, 923, 929`; `tools/uarch_model.py:5570-5636` | 6,222 tok/s "as built" = body x 1.0923 + 2 x 991 all-reduces | The body ratio is measured at **position 0** (`QWEN_L0_RTL`, ctx=1) but applied to the **ctx-8192** chain, so `position_basis` is mixed. The row also has no KV-delivery term: KV is treated as on core. `summary-r1.json:refused_comparisons.microarch_6222_mixed_position` refuses it. | Replace with the finite calendar at measured compute: **357.99 us = 2,793 tok/s**. The 8K attention (+1,220 cycles/layer, unmeasured) gives **359.71 us = 2,780 tok/s**. Label 6,222 and 8,460 as "compute chain only, KV delivery not modelled". |
| `docs/MICROARCH_MODEL.md:1003` | "KV read 41.9 us, binding: compute chain" | This assumes the KV fill runs at PHY rate. The 7 x 64 B fill network has a 281.4 us floor, and the command bus has a 308.16 us floor. | The binder is KV fill service. The compute chain is 142.6 us at position 0 and 179.2 us with the 8K attention. |
| `docs/CURRENT_WORK_HANDOFF_2026_10_03.md:118` | "150,847,488 KV bytes per token" | That figure is RD+WR command bytes (4,713,984 x 32 B). | KV off-chip read is **150,690,816 B/die/token**; write is 156,672 B. |

## 3. Stale BF16 KV statements (the adopted contract is FP8 E4M3, per element, unscaled)

- `tools/arch_budget_qwen3.py:62`: the comment "(a golden change: BF16 today)" is stale. The golden has been FP8 since 8a91421a3. Change it to "FP8 E4M3 per element, unscaled; golden tools/hdc_golden.py to_fp8".
- `tools/arch_budget_qwen3.py:1518`: `as_built="... BF16 KV only"` should say the TP4 RTL token uses KV_FP8(1).
- `results/quality/qwen3_8b_deployment_arithmetic.json`: the "main ... still keeps a BF16 KV cache" text is stale. It is pinned, so annotate it in a successor record rather than editing it.
- `rtl/hdc/kv/ot_hdc_kv_stream.sv:81`: `HBM_FP8 = 0` (SRAM BF16) is the default of the legacy streamer. Document it as legacy, not the adopted format.

## 4. Other identity defects found by the policy review

- `docs/ARCHITECTURE_ATLAS.html:778` promises a layer-ahead prefetch into a 19.3 MB ring. The calendar uses a cold per-layer lease. The cross-layer handoff variant is now REJECTED (`streaming-rejected-r1.json`, +0.857% at the 8K calibrated compute).
- `results/uarch/qwen_rom.json:335, 375`: the TP2 G4608 value 8460.12 is equal to the option C SS row. Annotate it in a successor.
- `results/rtl/qwen_rom_TP4_terminal_20261002/original_terminal.json:3`: the claim text says "G=5,120 TP-2", but `design_point` says tp=4, G=6144. Annotate it in a successor. The record is pinned.
- `me_lat_extra=55` in `tools/uarch_model_qwen_kv_credit17.py:131`, `uarch_model_qwen_kv_bank_groups.py` and `uarch_model_qwen_kv_rate_risk.py` replaces the 112 measured wire stages instead of adding to them. The correct total is 167.

After any `docs/` edit, AGENTS.md requires the prose-figure census to be regenerated and `make check-figures` to be run.
