# Comparison fairness audit

Six dimensions -- area accounting, memory hierarchy, efficiency derates, search
space, executed lanes, anchors and gates -- were audited independently and every
finding was independently verified. This document ranks what survived by **how
much it moves the headline**, not by how interesting it is.

**The headline under audit:** the iso-area ROM-to-GPU per-user speed ratio at
**8.63x**, DeepSeek-V4-Pro-0813 at 1,000,000 tokens, batch 1, 554,700 mm2
(`results/roofline/n6_vs_a100/analytical.json`, `latency_correction_ladder`,
`ratio_after = 8.628003684494233`; rendered at `REPORT.md:371`).

Every number below was recomputed from the two points' own published
`component_times_s`. The reconstruction is exact -- ROM step 489.732 us and GPU
step 4,225.408 us against published values identical to the microsecond -- so
each perturbation below is a real re-evaluation of the published pair, not an
estimate.

---

## The headline, decomposed. Read this first; it reorders everything.

| | ROM: `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x12-romfill` | GPU: `DSV4-Pro/a100_sxm_80gb-x672-tensor` |
|---|---:|---:|
| Step time | 489.73 us | 4,225.41 us |
| **link_latency** | **243.93 us (49.8%)** | **2,784.68 us (65.9%)** |
| service (memory/compute, /0.9) | 232.05 us (47.4%) | 1,426.98 us (33.8%) |
| layer_fixed_latency | 13.75 us (2.8%) | 13.75 us (0.3%) |
| per-user | 2,041.9 tok/s | 236.7 tok/s |
| binds on | `link_latency` | `link_latency` |

**Both sides bind on `link_latency`.** 58% of the combined step mass of the
headline is collective latency. The ROM pays 122 on-wafer all-reduces across 57
reticle regions (187.88 us) plus 11 inter-wafer point-to-point hops (56.05 us);
the GPU pays 122 NVLink-3 all-reduces across 8 (381.30 us) plus 122 InfiniBand
all-reduces across 84 nodes (2,403.38 us). That is **1.54 us per 57-region
on-wafer all-reduce against 22.83 us per 672-way two-tier GPU all-reduce**.

Weight bandwidth -- the entire subject of the ROM thesis -- is 47% of the ROM
step and 30% of the GPU step. It is no longer what the headline is about.

Three consequences that reorder the audit:

1. Every finding about compute derates, KV capacity, KV bandwidth, HBM
   beachfront and GPU L2 is **worth zero or near-zero at this headline**,
   however large it is elsewhere. The headline ROM winner holds its KV in SRAM
   and carries **zero HBM stacks**; its compute term (24.95 us) sits under its
   weight term (208.85 us); the GPU's KV term is 1.90 us of 4,225 us.
2. **The headline row is nobody's best machine.** The ROM's own fastest
   batch-1 machine for this model is 2 wafers at 2,653.6 tok/s (92,450 mm2);
   the GPU's is 280 A100s at 312.1 tok/s (231,280 mm2). The comparison is read
   at 554,700 mm2, where both sides are past their own optimum. This is not a
   detail -- it is the mechanism behind the two largest items below.
3. The largest single lever on the headline is **one assumed constant**:
   `links.on_wafer.hop_latency_s`.

---

## Ranked summary

Ratio change is multiplicative on 8.628x. "Cut" marks where headline effect
reaches zero; items below the cut are ranked by severity elsewhere and are still
required fixes.

| # | What is unequal | Favours | Headline | Kind |
|---:|---|---|---:|---|
| A1 | On-wafer hop latency assumed (16.7x sweep) vs GPU's measured (1.54x); band published joint-only | ROM | **0.33x – 1.51x** | artefact of disclosure over a legitimate evidence gap |
| B1 | "Silicon area" = logic die only; HBM DRAM/base/interposer and off-package silicon uncounted | GPU | **0.77x – 0.81x** (sign flips under A2) | legitimate convention, undisclosed |
| B2 | Winner is a `-romfill` per-workload floorplan with R replicated weight copies | ROM | **2.61x** as published; **1.00x** under A2 | legitimate physics, undisclosed |
| A2 | Data-parallel replication offered to neither side; ROM has an in-model substitute | ROM | 0.985x directly; **precondition for B1 and B2** | artefact |
| A3 | `stage_balance` 1/0.9 charged to a tensor group with one stage | ROM | 0.966x | artefact |
| A4 | No redundancy/repair area on an unrepairable mask-ROM array | ROM | 0.92x – 0.99x | artefact |
| B3 | `hbm_bandwidth` 0.85, ungated, GPU's only bandwidth derate | GPU | 0.96x – 1.07x | legitimate, ungated |
| B4 | `rom_read_bandwidth`/`sram_read_bandwidth` 0.75 against HBM's 0.85 | GPU | costs ROM 0.13x | legitimate counterweight |
| A5 | HBM KV round trip charged at SRAM access time (2 ns) | ROM | 1.005x | artefact |
| — | **cut: zero at this headline** | | | |
| A6 | `max_resident_users` floor-divides to 0; guard tests truthiness | ROM | 0 here; **up to 681x** on aggregate rows | artefact (most severe code bug found) |
| A7 | HBM beachfront 0.60 imported from a B200 package into an A100 study | ROM | 0 here; −10% on the batch-256 headline | artefact |
| A8 | Aggregate ratio uses a per-user-selected GPU comparator | ROM | 0 here; up to 102x on aggregate rows | artefact |
| A9 | A100 throughput gate is an arithmetic identity that cannot fail | ROM | 0; 100% of GPU throughput validation | artefact |
| A10 | ABI3 executed lanes: 512- vs 8192-token program block | ROM | 0 here; +6.94% read traffic on the HBM lane | artefact |
| A11 | iso-node ROM-only efficiency envelope, GPU pinned | ROM | 0 here; 13x span in that study | artefact |
| A12 | HC1 config asserted batch-independence | ROM | 0; falsified a robustness claim | **resolved after audit:** batch is published and the stale sweep was removed |
| A13 | SRAM KV capacity carries no allocator/workspace derate | ROM | 0.999x | artefact |
| A14 | `n5_vs_b200` prints `n6_vs_a100`'s gates; neither of its parts is gated | ROM | 0 | artefact |
| A15 | Array-kind candidate sets differ per area rung (`counts_by_kind` scope) | GPU | 0 here | artefact |
| A16 | `balanced_area_split` hard-codes `fp8` for MAC sizing | ROM (mildly) | ~0 | artefact |
| A17 | HC1 compute shortfall was rendered as a false “within” claim | ROM | 0 | **resolved after audit** |
| B5 | GPU credited with zero on-die SRAM (no L2 capacity, no L2 bandwidth) | ROM | ~0 here; up to 1.7x on Qwen rows | legitimate for decode, undisclosed |
| B6 | N6 vs N7 logic density 1.18x; native w4a8 vs BF16 emulation 3.3x | ROM | ~0 here | legitimate, disclose |
| B7 | ROM array leakage was charged at zero | ROM | 0 on speed; tokens/J was an upper bound | **resolved after audit:** nonzero term charged and reported |
| B8 | Wafer gross-die utilisation (65% vs ~75%) not charged | ROM | 0 on any rate | legitimate, disclose |
| B9 | No gate covers the multi-device, multi-slot or wafer regime | neither | 0 | legitimate evidence limit |
| B10 | The two products in the comparison do not carry the same RTL standing: the Qwen deployments are co-simulated against the golden model, the wafer one is covered only when the campaign says so | ROM | 0 on any rate | legitimate evidence limit, disclose |

---

# Part A — Artefacts, ranked. These must be fixed.

## A1. The on-wafer hop latency is assumed with a 16.7x sweep while the GPU's dominant hop is measured with a 1.54x sweep, and the published band moves both sides together, which conceals it

> **RESOLVED 2026-08-31.** Both halves of this artefact are fixed and the
> finding below is left as written, as the record of what was found. What
> changed: `links.on_wafer.hop_latency_s` is now **125 ns, graded `derived`,
> swept 75-250 ns (2.1x)** -- composed from Cerebras' published one-cycle
> core-to-core hop, published per-die core grid and published clock, corroborated
> by two measured whole-wafer collectives and by Tesla's published 100 ns
> reticle-die crossing. `links.nvlink3.hop_latency_s` is now **2.5 us, graded
> `derived`, swept 1.0-10.3 us** -- half the best measured 8x A100 small-message
> all-reduce, with stock NCCL's measured 20.6 us at the top of the band; the
> claim in its old note that "NVIDIA publishes no NVLink or NVSwitch latency
> figure in any form" is withdrawn, because NCCL's shipping source carries one.
> And the reports now emit **three** bands rather than one -- wafer fabric alone,
> cluster fabric alone, both together -- which is the presentation fix this
> finding asked for. The headline moved 8.63x -> **8.33x**; the one-sided ROM
> band moved 13.48x-3.26x -> **11.21x-5.41x**, and the GPU side's own band is now
> 6.92x-12.96x, so the two are comparable in width for the first time. See
> `docs/WAFER_VERSUS_ARRAY_LATENCY.md` §1 and §6.


**What is unequal.** The single largest term in the headline is collective
latency, and the two sides' dominant constants have completely different
evidential standing:

| Constant | Grade | Value | Sweep | Share of that side's link term |
|---|---|---:|---|---:|
| `links.on_wafer.hop_latency_s` | **assumed** | 100 ns | 30–500 ns (**16.7x**) | 77% (97% on the hull machine) |
| `links.inter_wafer.hop_latency_s` | **assumed** | 5.0 us | 1–10 us (10x) | 23% |
| `links.nvlink3.hop_latency_s` | **assumed** | 1.5 us | 1.0–5.5 us (5.5x) | 14% |
| `links.infiniband_hdr.hop_latency_s` | **published** (De Sensi et al., SC24) | 4.5 us | 3.7–5.7 us (**1.54x**) | 86% |

**Favours ROM**, as a matter of which side's number can move.

**Evidence.** `configs/hardware/technology.json` `links.*.hop_latency_s`. The
on-wafer note says in its own words "Not measured"; the InfiniBand note cites
GPU-buffer-to-GPU-buffer measurements across five production supercomputers.
Sweeping each side alone on the headline pair, the other held at its stated
value:

| Sweep | Headline |
|---|---|
| ROM `on_wafer` alone, 30 ns → 500 ns | **11.80x → 3.40x** |
| ROM both hops at their own low/high ends | **13.48x → 3.26x** |
| GPU both hops at their own low/high ends | 7.50x → 12.01x |
| Published joint band (`REPORT.md:467`) | 11.82x → 4.46x |

The one-sided ROM band (13.48x–3.26x, a **4.1x** span) is **wider than the
published joint band** (11.82x–4.46x, 2.6x). Moving both sides together
partially cancels, so the report's own band table understates the ROM-side
uncertainty and hides that essentially all of the width comes from one side's
unmeasured constant. The report's justification -- "a ratio is only tested by
moving both ends of it together" (`REPORT.md:467`) -- is the wrong test here:
moving both together checks robustness to a *common-mode* error, and there is
no common mode when one constant is measured and the other is not.

**Legitimate or artefact.** The constant being unmeasured is a legitimate
evidence limit -- no wafer-scale ROM part exists. The **joint-only presentation
is the artefact**, and it is fixable tonight without any new physics.

**Fix.** In `tools/run_roofline_studies.py`, emit `link_latency_sensitivity`
per-constant and one-sided as well as jointly, and render a per-constant column
in `REPORT.md`'s band section. Label each row with the constant's grade, so a
reader sees `on_wafer: assumed` beside `infiniband_hdr: published`. State the
adversarial corners explicitly (ROM hops low + GPU hops high = 18.77x; ROM hops
high + GPU hops low = 2.83x) rather than only the correlated ones.

---

## A2. Data-parallel replication is offered to neither side, which forces both past their own optimum -- and the ROM has an in-model substitute for it while the GPU has none

**What is unequal.** Both families can always build *k* independent replicas of
their best cluster at *k* times the area, so per-user latency is monotone
non-decreasing in area on both sides as a matter of physics. The study forces
all iso-area silicon into one machine. Both curves therefore fall past their
peak, and the headline is read at 554,700 mm2 where neither side is at its
optimum. The ROM has an in-model substitute -- `spare_area_policy='rom'` plus a
per-plan sizing sweep -- and the GPU has none.

**Favours ROM.**

**Evidence.** `tools/run_roofline_studies.py:1563` selects the comparator as
`max(feasible_at_area, key=per_user_tokens_s)` at one pinned area; there is no
replication construction anywhere. The DSV4-Pro batch-1 GPU curve is plainly
non-monotone: 263.96 (48 GPUs) rising to **312.13 (280 GPUs)** and then
collapsing to 233.64 (336) / 235.14 (448) / 236.66 (672) at the InfiniBand tier
boundary. The ROM curve peaks at **2,653.64 (2 wafers, 92,450 mm2)** and falls
to 2,041.93 at 12 wafers.

**Effect on the headline.** Under a symmetric hull -- best feasible design at
area <= budget, replicated -- ROM takes 6 replicas of its 2-wafer machine and
the GPU takes 2 replicas of its 280-GPU cluster: **8.628x → 8.502x (0.985x)**.
Directly, this is small.

**Its real importance is structural.** It is the precondition for reading B1 and
B2 correctly:

* Under the hull, the ROM's own best batch-1 machine is `ROM-N6-native-SRAMKV-wafer-hybrid-x2`, which is **not** a romfill design. The romfill axis, worth 2.61x on the published headline, is worth **exactly 1.00x** at batch 1 once replication is allowed (verified: best romfill and best non-romfill at area <= budget are both 2,653.6 tok/s).
* Under the pinned rule the total-silicon boundary (B1) *lowers* the headline; under the hull it *raises* it. The sign of B1 depends on fixing A2 first.

**Legitimate or artefact.** Artefact -- a modelling rule, not physics.

**Fix.** `tools/run_roofline_studies.py:1556-1566`. Report both sides under a
replication hull as an additional column of the iso-area table: best feasible
design at area <= A for per-user, times `floor(A / that design's area)` replicas
for aggregate. State that per-user latency under replication is flat in area on
both sides. Separately, split the comparator selection in two --
`iso_latency` by `per_user_tokens_s` and `iso_throughput` by
`aggregate_tokens_s` -- which also fixes A8.

---

## A3. `stage_balance` is charged to a tensor group that has one stage

**What is unequal.** `efficiencies.stage_balance` = 0.9 -- "penalty applied to a
multi-device pipeline for imperfect layer balance across devices" -- is applied
whenever `parallelism != "none"`, so a pure tensor group pays it despite having
one stage and no layer partition to balance. The headline GPU is
`tensor`/`pipeline_stages=1` and pays 1/0.9; the headline ROM is `hybrid` with
12 real pipeline stages and pays it legitimately.

**Favours ROM.**

**Evidence.** `src/opentallas/roofline.py:2890-2893`:

```
balance = technology.efficiency("stage_balance").value
apply_balance = devices > 1 and budget.topology.parallelism != "none"
if apply_balance:
    service_time /= balance
```

`Topology.token_slots` and `pipeline_stages` are both 1 for a tensor group. The
verification pass found that across 1,230 live rows a tensor-only exemption
moves 1,066, of which **931 fall and 135 rise** -- the GPU picks tensor in 996
of 1,230 comparisons while the ROM picks pipeline or hybrid in 796, so the
parameter is nominally shared and its effect is not.

**Effect on the headline.** GPU service 1,426.98 → 1,284.28 us; step 4,225.41 →
4,082.71 us. **8.628x → 8.337x (0.966x).** Under the hull, 8.502x → 8.102x.

**Legitimate or artefact.** Artefact. The model charges a penalty for a
partition structure the topology does not have.

**Fix.** `src/opentallas/roofline.py:2891` -- change the guard to
`budget.topology.pipeline_stages > 1`. If a tensor-shard imbalance penalty is
wanted, add `efficiencies.tensor_shard_balance` as a separately named and
justified parameter. **Related, and free to fix at the same time:**
`apply_balance` tests `devices > 1` where the physics is `partitions > 1`, so a
single-wafer design running 57 on-wafer pipeline stages pays nothing. That
exemption does not touch this headline (the winner is 12 wafers) but it is worth
up to 1.111x on 72 live rows and it makes two ROM machines with identical
partition structure pay differently purely by package count.

---

## A4. There is no redundancy, repair or spare-area line item on an array that cannot be repaired after fabrication

**What is unequal.** `floorplan` contains exactly two fractions --
`interconnect_area_fraction` 0.08 ("on-die network and the bank-to-compute
fabric") and `overhead_area_fraction` 0.10 ("host/PCIe PHY, clocking and PLLs,
power delivery, control, DFT and scan"). Neither names repair, redundancy, spare
rows/columns or ECC. `docs/METHODOLOGY.md:170` requires it: "Whole-wafer values
deduct ROM/SRAM array area, compute, NoC, PHY, control, **repair, and spare**
fractions." A 46,225 mm2 monolithic mask-ROM array gets no defect allowance at
all, while the GPU pays for its harvest inside a published, yielded part (GA100
ships 108 of 128 SMs, and the 312 TFLOPS roof every density in the study derives
from is the harvested part's).

Aggravating: `rom.array_efficiency` = 0.70 is set **above**
`sram.array_efficiency` = 0.65, and the SRAM note names redundancy among what
its 0.65 covers while the ROM note names only the absence of write drivers.

**Favours ROM.**

**Evidence.** `configs/hardware/technology.json` `floorplan` block; grep of the
whole file for `redundan|repair|spare|yield|harvest` returns only
`rom.cell_to_sram_cell_area_ratio`'s "no write redundancy" and
`sram.array_efficiency`'s note.

**Effect on the headline.** Deducting a redundancy fraction off the top of the
die re-solves the balanced split, shrinking `rom_mm2` and lengthening
`weight_read`, which is the ROM's binding service term here:

| Redundancy fraction | Headline |
|---:|---:|
| 0.02 | 8.526x (0.988x) |
| 0.05 | 8.369x (0.970x) |
| 0.12 | 7.975x (0.924x) |

**Legitimate or artefact.** Artefact -- a category the project's own methodology
requires and the comparator pays for.

**Fix.** Add `floorplan.redundancy_area_fraction`, graded `assumed`, swept
0.02–0.12, with a note that a mask ROM cannot be field-repaired.
**Do not** fold it into `rom.array_efficiency`: that field feeds only
`rom_bits_per_mm2` (`src/opentallas/roofline.py:481-491`), while
`rom_read_bytes_s_per_mm2` (`:557-577`) is anchored on macro throughput scaled
by bitcell area and never sees it. Folding it in would change capacity and
feasibility without changing read bandwidth, which is the opposite of the
intended charge.

---

## A5. The per-layer KV round trip is charged at SRAM access time to every architecture, including both HBM-KV families

**What is unequal.** `layer_fixed_latency(technology, model)` takes no budget
and charges `latency.sram_access_s` = 2 ns as the KV dependency for every
design, including the GPU and the ROM HBM-KV wafers whose KV is in DRAM.

**Favours ROM** *on this headline*, because the headline ROM winner holds its KV
in SRAM and is correctly priced while the GPU is not. (The verification pass
established the direction reverses where both sides are HBM-KV, since a shared
absolute constant added to both steps shrinks a ratio above 1.)

**Evidence.** `src/opentallas/roofline.py:1076`,
`kv_round_trip_s = sram_access.value + traversal_s`. The docstring's blanket
claim that charging the same budget to every architecture "is conservative for
the ROM side" is false on any row where the ROM is SRAM-KV and the GPU is not --
which includes this one.

**Effect on the headline.** DSV4-Pro has 61 layers at 225 ns each. Substituting
a 350 ns HBM round trip on the GPU only adds 21.2 us: step 4,225.41 → 4,246.6
us. **8.628x → 8.671x (1.005x).**

**Legitimate or artefact.** Artefact -- the primitive is named for the wrong
memory. One correction to the original finding: the justification "it cannot be
prefetched because layer n's query does not exist until layer n-1 retires" is
wrong for dense/window/compressed-dense attention, where the KV read's
*addresses* do not depend on the query. The genuinely unprefetchable case is the
sparse top-k gather, which the model already charges separately at
`latency.sparse_index_dependency_s` = 128 ns.

**Fix.** Pass `kv_store` into `layer_fixed_latency` and select between
`latency.sram_access_s` and a new `latency.hbm_access_s` (graded `assumed`,
200–500 ns). Retract the docstring's blanket conservatism claim.

---

## Below the cut — zero at this headline, still required fixes

Ranked by severity where they do bite.

### A6. `max_resident_users` floor-divides to 0 and the guard tests it for truthiness

The most severe code defect found anywhere in the audit, and it is worth zero
here only by luck. `src/opentallas/roofline.py:3070` computes
`max_resident_users = int(max(0.0, remaining) // kv.storage_bytes_per_user)`,
and `:3161` guards with `if max_resident_users and fill_users > max_resident_users:`.
Because `balanced_area_split:1655` sizes SRAM as `resident_kv_bytes / density`
and `rom_device_budget:2204` reads capacity back as `sram_mm2 * density`, the
round trip lands 2e-7 B **low** at the study's own geometry, the floor-division
returns 0, and 0 is falsy -- so the cap never runs. Reproduced independently at
3 devices x 815 mm2: `kv_capacity = 1207959551.9999998` against
`resident = 1207959552.0`, `mru = 0`, `fill = 3.0`. Strictly one-sided: all 44
`mru == 0` feasible points across both studies are `family=rom`,
`kv_store=sram`; a GPU's remaining HBM is always many users wide. Peak
distortion **681x** of aggregate throughput and tokens/J
(`Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x12-romfill`, reported aggregate
ratio 155.9x against a corrected 0.23x); 14 comparison rows in `n6_vs_a100` and
4 in `n5_vs_b200`. `tests/test_roofline.py:1544` asserts exactly this invariant
and passes only because its 64 x 3000 mm2 geometry lands on the safe side of the
float. **This headline is untouched only because its `mru` happens to be 1 and
its `token_slots` are capped to 1 anyway.** Fix: `math.floor(... + 1e-9)` (or
the `+1.0` slop the refusal check three lines up already uses) and change the
guard to `if kv.storage_bytes_per_user > 0 and ...`; add the study's own
geometry as a regression case.

### A7. HBM beachfront 0.60 imported from a B200 package into an A100-comparator study

`hbm.hbm2e.max_beachfront_utilization` = 0.60 is applied to modelled ROM parts
via `max_hbm_stacks_per_device` (`roofline.py:1531-1549`), which
`gpu_device_budget` never calls -- so the constant can only ever grant, never
bind. At 46,225 mm2 it yields **43 stacks per wafer** where the A100's own
achieved 52.2% yields 37: **+16% of KV bandwidth and capacity on every
wafer-scale HBM-KV design.** Zero here (the winner carries zero stacks) but it
lands on the batch-256 headline, taking DSV4-Flash 36.52x to roughly 33x. Two
corrections to the original finding survive verification: the hbm2e and hbm3e
notes are *not* identical (B200 genuinely achieves 0.60), so this is precedent
selection rather than a fabricated constant; and at reticle scale it is not a
grant at all (5 stacks on 815 mm2 is 52.5%, the A100's own). Fix: use the
comparator's own achieved utilisation for the hbm2e/A100 study, keep 0.60 for
hbm3e/B200, sweep 0.45–0.60, and print the wafer stack count next to the largest
shipping precedent (8). Note `tests/test_roofline.py:870-879` recomputes the
expression it is testing and can never fail on the constant.

### A8. The aggregate ratio divides by a comparator selected on per-user rate

`tools/run_roofline_studies.py:1560-1566` picks one `iso` GPU by
`per_user_tokens_s` and `:1698` uses it as the denominator for
`aggregate_speed_ratio`, `energy_per_token_ratio` and
`tokens_per_joule_advantage_x`. 338 of 1,230 rows are inflated more than 2x
against the GPU's own best-aggregate machine at the same area, peak **102.4x**;
280 rows inflate `tokens_per_joule_advantage_x` by more than 2x, peak 48.66x.
Scope qualification the original finding did not make: this is a defect in the
`comparisons` **fields**, not in `REPORT.md`'s tables, which select on per-user
rate on both sides. Fix is the two-comparator split named in A2.

### A9. The A100 throughput gate is an arithmetic identity that cannot fail

`a100_weight_bound_anchor` (`roofline.py:3746`) sets
`published_value = bandwidth / stored` and
`modelled_value = 1/step.component_times_s["weight_read"]`, where that time is
`stored/bandwidth` under `technology.ideal()` and
`weight_traffic_policy='full_checkpoint'`. It returns `ratio = 1.000000000 PASS`
under every mutation tried: HBM bandwidth x8 or halved, a die area of 1 mm2 that
voids the iso-area premise, an HBM capacity at which the model does not fit, a
cooling limit at which the part cannot run, the bandwidth derate at 0.05, and
stored widths from 2 to 100 bits per parameter. It is presented in
`METHODOLOGY §1a`, `README.md:188`, `SOURCES.md:234` and both gate tables as the
counterpart to the genuinely published HC1 gate, with a **tighter** tolerance
(1% vs 2x) that inverts the true ordering of evidential strength -- and its
"Published" value, 253.91 tok/s, is published nowhere; the gate computes it.
Three further asymmetries ride on the same row: the A100 gate runs on the ideal
roofline while HC1 runs derated (the derated A100 figure is 208.62 tok/s, 22%
below the printed 253.91); the "Modelled" column is the reciprocal of one
component on one row and the full step rate on the other; and the A100 gate uses
`weight_traffic_policy='full_checkpoint'` where the study uses
`decode_streamed`, worth 7.0% in ROM's favour. Fix: delete the row and disclose
that no GPU-side throughput gate exists, or anchor it to a measured decode rate
(see Part D).

### A10. ABI3 executed lanes: a 512-token program block against an 8,192-token one

`compiler/backends/hbm_sram/plan.py:242` hard-codes `TileConfig.block = 512`;
`compiler/backends/rom/common/program.py:955` leaves `token_block_rows = 0` and
`:2416` resolves it to the whole declared context, 8,192 rows. Two per-backend
compiler defaults, derived from no capability field, on two parts that declare
the identical 128 MiB of SRAM. At TA-QW-8K-1 this charges the HBM lane **+6.94%
read bytes (208,508,098,560 B), +7.81% state bytes, +7.42% loop iterations and
10.79x prefill retired instructions (2,105 vs 22,715)** for provably identical
arithmetic -- `tensor.multiplications`, `attention.context_positions`,
`attention.kv_bytes_read` and `vector.elements` are bit-identical and writes are
conserved to the byte. The isolation is clean: at TA-QW-CHAT-1 (117 positions,
one block on both lanes) reads and writes are conserved exactly. This is the real
cause behind both the 239-vs-218 descriptor gap and the index-137 divergence
that `docs/UNIFIED_EXECUTION_CHECKLIST.md:392-405` attributes to storage class.
Two companions in the same deliverable: `tools/build_comparison_report.py:load_record`
drops `implementation_identity`, so `check_comparable`'s guard
(`runtime/evidence.py:311-322`) skips on two empty dicts and a torch-vs-numpy
pair passes the gate that exists to refuse it; and the HBM backend declares
SRAM regions at `lower.py:616` and never routes a byte through them, which
`UNIFIED_EXECUTION_CHECKLIST.md:417` then publishes as a technology result
("the ROM target moves 437 MB / 61 MB through SRAM where the HBM target moves
none"). None of this touches the roofline headline; all of it is one-sided.

### A11. The iso-node study gives the ROM a three-point efficiency envelope and pins the GPU

`configs/hardware/technology_inputs.json` `runtime_and_cost_assumptions`: a100
fixed at `compute_efficiency` 0.45 / `load_balance_efficiency` 0.75;
`rom_by_envelope` at 0.45/0.60/0.70 and 0.75/0.85/0.92. Both parameters are
graded `assumed` on both sides with no measurement behind either, and only one
side is allowed to move. The compute-path derate product runs 0.325/0.497/0.632
against the GPU's fixed 0.428, and the study's median per-user ratio spans
**0.700x to 9.090x -- 13x on envelope choice alone** -- with the ROM losing only
at the single envelope where its two assumed derates equal the GPU's. The
artifact's `uncertainty_bands` block is ROM-only
(`rom_per_user_tokens_s_high`/`_low`, `scenario_count: 3`) and
`interpretation_boundary` never says which parameters the envelope moves that
the GPU's fixed profile does not, while `REPORT.md:63` headlines the central
case. Counterweight that does not overturn it: `weight_bandwidth_efficiency`
runs 0.50/0.65/0.75 for the ROM against the A100's 0.75, so on that parameter
the ROM is charged harder at two of three envelopes. `defect_repair_efficiency`
and `clock_efficiency` are legitimately asymmetric and correctly charged against
the ROM. Fix: give the GPU the same three-point envelope on the two parameters
assumed on both sides, and pair conservative-ROM with aggressive-GPU.

### A12. Resolved: the HC1 batch-independence assertion was removed

The audit baseline graded `reference_parts.taalas_hc1.batch_size` as `assumed`
and claimed the dense-model anchor was batch-independent. Its own sweep refuted
that claim. The launch-deck footnote now grades batch 1 as `published`, and the
register explains that each amortisation policy carries a different batch cost.
The intermediate 0.7213× batch-1 PASS is also superseded: the corrected ROM
density and compute-in-ROM floorplan make the anchor capacity-infeasible at the
published point, so the current gate reports zero and FAIL rather than using the
old sweep as a robustness claim.

### A13–A17, briefly

* **A13** `efficiencies.hbm_capacity` 0.90 covers "runtime workspace, allocator and safety reserve" for HBM on both families; a ROM design's on-die SRAM KV store gets no equivalent (`roofline.py:2204-2207`). KV is written at run time on both architectures. Worth 0.999x here (SRAM is 0.6% of this die) and about −2.7% on the Qwen headline. **Must land after A6**, or sizing at `resident/(density*0.9)` and crediting at `area*density*0.9` re-creates the exact float knife-edge. The ROM side also carries no activation/workspace line item of any kind: grep of `roofline.py` for `workspace|scratch|activation_buffer` returns nothing.
* **A14** `run_all` (`tools/run_roofline_studies.py:4823-4828`) computes anchors once and assigns them into every study, so `results/roofline/n5_vs_b200/REPORT.md` shows a four-row PASS table in which **neither of that study's two parts is gated** -- byte-identical to `n6_vs_a100`'s except one line. `b200_sxm` carries published roofs, HBM3e bandwidth, capacity, power *and* native fp8/fp4, so a real B200 gate is constructible where the A100's fp8 gate is not. The one line that differs is itself wrong: the n5 report checks a fixed N6 ROM read-density requirement against an **N5-scaled** WSE-2 SRAM density, flattering it by 1.29x.
* **A15** `counts_by_kind` is declared inside the `kv_store` and `(amortization, spare_area_policy)` loops (`tools/run_roofline_studies.py:1238`) and the fixed `ROM_AREA_LADDER` is added only for `plan.kind == 'wafer'` (`:1259`), so array-kind rungs are read off non-overlapping candidate sets. This makes the published ROM curve sawtooth (2927.7, 3212.0, 2621.5, 3687.7, 3782.6, 3088.1) where the full set is monotone (2927.7, 3418.0, 3557.9, 3687.7, 3782.6, 3854.9) -- a modelling artefact a reader would take for physics. Favours GPU; verified to move no published headline (DSV4-Pro's 76,610 mm2 row is unchanged).
* **A16** `balanced_area_split:1690-1694` hard-codes the literal `'fp8'` for `mac_density` and never receives the design's execution format. Verified largely harmless: the fp8/bf16 density ratio is exactly **2.0**, not 3.3x, and for bf16 the 2x density halving exactly cancels the 2x bytes-per-parameter, so the hard-code returns the format-correct answer. A residual mismatch exists on w4a8 designs and favours **ROM**, not the GPU. Thread `execution_format` through anyway.
* **A17 — resolved after audit.** The renderer now states that capacity fails
  before either rate density can bind and reports the ROM and compute
  diagnostics separately. The regression test is named for the ROM-read
  density it actually checks; it no longer implies that compute density passed
  a shipping-silicon gate.

---

# Part B — Legitimate asymmetries. Disclose these; do not remove them.

## B1. "Silicon area" means leading-node logic die area only

**What is unequal.** `gpu_device_budget` (`roofline.py:2410-2419`) builds
`AreaSplit(total_mm2=826, compute_mm2=826, rom=sram=hbm_phy=overhead=interconnect=0)`
and `_iso_area_gpu_counts` (`tools/run_roofline_studies.py:827`) derives the
comparator from `die_area_mm2` alone. HBM DRAM dies, base dies, interposer,
package, NVSwitch, NICs, InfiniBand switch ASICs and host CPUs are charged to
neither side. Meanwhile `balanced_area_split` charges the ROM side
`rom_mm2 = stored_weight_bytes / rom_density` for every stored weight byte.

**At this headline the asymmetry is total, not partial.** The ROM winner holds
its KV in on-die SRAM and carries **zero HBM stacks**; the 672-A100 comparator
carries **3,360 HBM2e stacks**, roughly 2.86e6 mm2 of uncounted DRAM and base
silicon against 554,700 mm2 of counted logic, plus ~300,000 mm2 of uncounted
NVSwitch, NIC, switch and host silicon (84 baseboards, 672 adapters, 168 CPU
packages).

**Effect on the headline -- and the sign is not what the audit assumed.**

| Convention | A100s that 554,700 mm2 buys | GPU tok/s | Headline |
|---|---:|---:|---:|
| Logic only (published) | 671 | 236.7 | 8.63x |
| DRAM mm2 at 0.25 | 293 | 293.9 | **6.95x** |
| DRAM mm2 at 0.5 | 187 | 305.7 | **6.68x** |
| DRAM mm2 at 1.0 | 109 | 293.8 | **6.95x** |

Under the **published pinned-area rule**, counting total silicon **lowers** the
headline by 19–23%, because the GPU's per-user curve is non-monotone and 672
devices is past its peak of 280 -- shrinking the cluster moves it *toward* its
optimum. The audit's own summary that "the published ratios are floors under a
total-silicon convention" is **false at this headline**. Under the replication
hull (A2), where the GPU is no longer being handed a cluster past its own
optimum, the sign reverses as expected: 8.502x → 8.73x (DRAM at 0.5) → 9.13x
(DRAM at 1.0).

**Legitimate.** A mm2 of 1y-nm DRAM is not a mm2 of N6 logic in cost, yield or
supply, and counting them 1:1 would be wrong in the other direction and would
make the ROM thesis trivially true. The **defect is that the single most
load-bearing convention in the deliverable is stated nowhere** --
`comparison_contract` is one sentence, "compared at equal silicon area with the
area stated on both sides", and grep for dram/interposer/package/base-die/
off-package across `REPORT.md` and `METHODOLOGY.md` returns nothing.

**The sentence that should appear beside the headline:**

> Silicon area here means **leading-node logic die area**. HBM DRAM dies, base
> dies, interposer, package, and off-package switch, NIC and host silicon are
> excluded on both sides. At this operating point that exclusion is one-sided in
> practice: the ROM design holds its KV on-die and carries zero HBM stacks,
> while the 672-GPU comparator carries 3,360 HBM2e stacks -- roughly 2.9 million
> mm2 of uncounted DRAM and base silicon against 554,700 mm2 of counted logic.
> Counting all silicon at parity would buy 109 A100s instead of 672, and because
> a GPU cluster's per-user rate peaks at 280 devices and falls thereafter, that
> would move this ratio to about **7x, not above 8.6x**.

**Also emit** a second column per iso-area row,
`total_silicon_including_dram_mm2`, on both sides, so the direction is visible
rather than reconstructed.

---

## B2. The winning ROM design is a per-workload floorplan with replicated weight copies; a GPU die is fixed

**What is unequal.** `spare_area_policy='rom'` (romfill) reallocates leftover
silicon into replicated copies of the weight array and re-derives the MAC array
to match, and the design also re-floorplans its KV SRAM to the batch it is
evaluated at. The headline ROM design carries **`rom_replication_factor` =
4.40** -- 4.4 addressable copies of the 892.7 GB checkpoint -- and sizes its KV
store (0.59% of the die) to exactly one 1M-token user. The GPU's die is fixed and
can do neither.

**Effect on the headline.** Removing the axis and taking the best non-romfill
design at the same area gives 782.2 tok/s: **8.628x → 3.305x**. The axis is
worth **2.61x**, the largest single contributor to the published number.

But under the replication hull (A2) it is worth **exactly 1.00x** at batch 1:
the ROM's best machine at any area <= budget is the 2-wafer
`ROM-N6-native-SRAMKV-wafer-hybrid-x2` at 2,653.6 tok/s, and the best romfill
design anywhere <= budget is the same 2,653.6. Romfill's headline value is
entirely a consequence of the pinned-area rule forcing the ROM to spend 554,700
mm2 in one machine. Two caveats on the counterfactual: the non-romfill
alternative at the pinned area spends 71.5% of its die on a MAC array that
batch-1 decode cannot use, so 2.61x overstates the honest value of the axis; and
the "smallest silicon" rows of the iso-area table are largely **not** romfill
designs (DSV4-Pro batch 1's is `ROM-N6-native-SRAMKV-array-hybrid-x94`).

**Legitimate.** A mask-ROM part *is* drawn for one model, so choosing its
ROM/MAC/SRAM split per model, per batch and per topology is exactly what such a
part is; the area for all R copies is charged; R disjoint slices really are read
at once; and the study honestly offers the same sweep to both amortisation
policies. The GPU genuinely cannot re-floorplan.

**The sentence that should appear beside the headline:**

> The winning ROM design is a floorplan chosen for this model, this batch and
> this topology: it spends its spare silicon on **4.4 addressable copies of the
> checkpoint** and sizes its KV store to exactly one user. A GPU's fixed die has
> no equivalent freedom. Removing that freedom at this pinned area takes the
> ratio from 8.6x to 3.3x; allowing both sides to replicate their best cluster
> instead takes it to 8.5x with the floorplan choice worth nothing.

**Also** print `rom_replication_factor` and `spare_area_policy` as columns of
the iso-area table, not only in the fork table ~490 lines below it.

---

## B3. `efficiencies.hbm_bandwidth` = 0.85 is the GPU's only bandwidth derate and no gate can test it

Graded `assumed`, sourced to "commonly measured STREAM-class fraction of HBM
peak". Real A100 numbers bracket it on both sides: BabelStream triad lands near
0.64–0.69, a pure large-block read kernel reaches 0.83–0.88, an end-to-end
batch-1 decode loop is below both. It is applied identically to any HBM in the
study, ROM or GPU, and the chosen value is generous to the GPU -- so it is
conservative for the claim. But `Technology.ideal()` forces it to 1.0 in the one
GPU-side gate (A9), so nothing can move it, and **`REPORT.md` prints no
efficiency value anywhere** -- the six keys appear at `REPORT.md:1537-1543` as
bare names with no values attached.

**Effect on the headline:** 0.70 → 9.25x, 0.75 → 9.02x, 0.80 → 8.81x, **0.85 →
8.63x**, 0.90 → 8.47x, 0.95 → 8.32x, 1.00 → 8.19x. About ±7% over the plausible
band -- smaller than on the Qwen headline (±20%) because here the GPU is
link-bound, not weight-bound.

**Sentence:** *"The GPU is credited with 85% of published HBM peak bandwidth,
an assumed value with no gate behind it; over the plausible 0.70–0.95 band this
headline runs 9.25x to 8.32x."* Report the GPU's weight-bound rate with the
derate at 1.0 beside the ROM's undated sweep ceiling, which `REPORT.md:318`
already prints.

## B4. The ROM and SRAM read derates (0.75) are harsher than HBM's (0.85), on more regular access patterns

`efficiencies.rom_read_bandwidth` and `sram_read_bandwidth` are 0.75 against
HBM's 0.85, and the config's own note concedes "a mask-ROM sweep is the most
regular access pattern available ... so 0.75 is a conservative charge and
0.90–1.00 is arguable." A mask-ROM sweep has no refresh, no bus turnaround, no
bank-conflict arbitration and no controller queueing. **On this headline it
costs the ROM 13%**: at 1.00 the ratio would be 9.79x, at 0.90 it would be
9.37x. Legitimate as a direction -- charging the unmeasured side harder than the
measured one is the defensible default -- and worth recording so nobody moves it
upward without noticing. Two further counterweights in the same family: the SRAM
read-bandwidth density is anchored on WSE-2's **whole-die** attribution and then
applied to array-only area, about **3.4x** conservative; and compute density is
a published GPU's whole-die roof applied to a modelled design's compute-only
area after an 18% floorplan deduction, about 1.5x conservative (already
disclosed in `REPORT.md`'s interpretation boundary and in
`compute.anchor_note`).

## B5. The GPU is credited with zero on-die SRAM

`gpu_device_budget` sets `sram_mm2 = 0` and routes every weight and KV byte to
HBM; there is no L2 or cache path anywhere in the model. This is correct physics
for decode -- a step streams every weight and every KV byte exactly once, so
there is no within-step reuse for a 40 MB L2 to capture against a 892.7 GB
sweep -- and it is worth ~0 at this headline, where per-device engaged weights
are 59 MB, above the A100's 40 MB L2. It is worth up to **1.7x** on the Qwen
rows, where `a100_sxm_80gb-x672-hybrid` binds `weight_read` with 22.5 MB of
weights per device, entirely L2-resident across decode steps, on the first
NVIDIA part with an explicit L2 persistence API. The model charges the GPU 330
mm2 of its die at SRAM leakage density in the power block while crediting it
zero bytes and zero bandwidth in the performance model -- consistent by intent,
but stated in `power.gpu_logic_area_fraction`'s source field and nowhere in
`METHODOLOGY.md` or `REPORT.md`.

**Sentence:** *"A published GPU's on-die L2 and register file are credited with
zero capacity and zero bandwidth in this model, while the ROM part's on-die
arrays are credited with both. For a decode step that reads each weight once
this is right, and at this operating point it is worth under 1%; on the smaller
Qwen clusters, where a device's whole weight slice fits in L2, it is worth up to
1.7x."*

## B6. Iso-area is neither iso-transistor nor iso-datapath

The ROM's compute area gets N6's 1.18x logic-density credit while the A100 sits
at N7 (and the ROM *array* correctly gets none, since N6 carries the N7 bitcell
unchanged); and for the DeepSeek profiles the ROM builds a native w4a8 datapath
at 1.26e12 ops/s/mm2 while the A100 must emulate in BF16 at 3.78e11 -- 3.3x more
ops per mm2 of compute, compounding to ~3.9x. Both legitimate and both visible
in the config's `native_formats`/`emulated_formats` table rather than buried in
an efficiency factor. Worth ~0 here (only 99 of 2,120 feasible ROM points bind
on compute, and no headline row does), but it would dominate the moment a
comparison landed in a compute-bound regime.

## B7. Resolved: ROM-array leakage is now charged and reported

The baseline audited here set
`power.static_leakage_w_per_mm2.rom_array = 0.0` and correctly called that an
under-charge. The current register derives 0.0067 W/mm², sweeps
0.0013–0.026 W/mm², and the power path applies it to the solved ROM area. On
the HC1 reconstruction that is 2.90 W at the point and 11.24 W at range high;
the artifact exposes both fields instead of hard-coding “0 W charged.” The
speed headline is unchanged. The broader evidence boundary remains: the HC1
card-power gate still fails, and a modelled tokens-per-joule ratio is not a
measurement of fabricated leading-node ROM silicon.

## B8. A wafer consumes more 300 mm wafer per usable mm2 than reticle dies do

A 215 x 215 mm square die occupies 46,225 mm2 of a 70,686 mm2 wafer (65%);
~826 mm2 rectangular dies reach ~72–76% gross-die utilisation. Worth ~10–15% in
wafer-consumed terms, 0 on any modelled rate, and it runs opposite to B1 so the
two partly cancel. Disclose only because the study says "silicon area" where the
quantity counted is die area, and a wafer-scale part is exactly where the two
diverge.

## B9. No gate covers the regime the headline is computed in

Both throughput gates construct `Topology(kind='single_chip', device_count=1,
parallelism='none')` at batch 1 with `token_slots = 1`. The entire span from a
single 815–826 mm2 die to a 554,700 mm2 twelve-wafer machine or a 672-GPU
cluster is ungated on both sides -- and that span is where the 54.2x → 35.4x →
8.6x corrections all landed. Legitimate as an evidence limit (no shipping
wafer-scale ROM part, no published per-user decode rate for a 672-GPU pipeline)
but it belongs under the gates table, which currently shows four PASS rows above
headline ratios computed on machines the table never touches.

**Sentence:** *"The validation gates cover a single die at batch 1 with one
token slot and no collectives. No gate covers the multi-device, multi-slot or
wafer regime in which every headline in this report is computed."*

## B10. The two products do not carry the same RTL standing, and the wafer one is the headline

This is an asymmetry **inside this repository**, between the two designs it
builds, rather than between ROM and GPU — and it lands on the side the headline
is computed on. `results/rtl/abi3_deployment_campaign.json` loads the shipped
deployment images into the ABI 3.0 microsequencer RTL and correlates every
retirement against `runtime.sim.device.Device`. Its `correlated_cases` field is
the list of deployments the RTL is known to reproduce; the two Qwen3-8B builds
are in it at whole-transaction depth, and the DeepSeek-V4-Flash ROM wafer
deployment enters it only when a campaign records it doing so. At commit
`518260f` it did not: the RTL trapped that deployment after eight retirements on
`A3_STATE_SLOTS`, a bound nothing expressed at admission.

It moves no rate, which is why it sits in Part B. It is worth disclosing anyway
for two reasons. First, the model this report prices is the **wafer** one, so
the product carrying the weaker implementation evidence is the product carrying
the headline. Second, it is easy to launder: this repository does have routed
ABI 3.0 blocks, and a sentence that puts "routed on an open PDK" next to
"DeepSeek-V4-Flash wafer" reads as an implementation claim about the wafer part
that no artifact supports. The rule that prevents it is stated once, at the head
of W9 in `docs/UNIFIED_EXECUTION_CHECKLIST.md`: **a number resting on this RTL
may name exactly the deployments `correlated_cases` records, and no others.**

None of this touches the analytical model. `src/opentallas/roofline.py` prices a
design from technology constants and never reads the RTL, so no ratio in this
report depends on the RTL at all — which is itself the disclosure, because a
reader who has seen the RTL work may reasonably assume otherwise.

**Sentence:** *"The ROM wafer design this report prices is not covered by the
RTL co-simulation that covers the Qwen designs, and no ratio here depends on
RTL: the roofline model reads technology constants only."*

---

# Part C — Refuted. Do not re-raise these.

**On area accounting**

1. *"The published ratios are floors under a total-silicon convention."* **False
   at this headline.** Under the pinned-area rule, counting total silicon moves
   8.63x to ~6.7–7.0x, because the GPU's per-user curve peaks at 280 devices and
   672 is past it. The sign only becomes positive after the replication hull
   (A2) is applied. Verified numerically in B1.
2. *"The hbm2e and hbm3e beachfront notes are identical and the justification is
   self-refuting."* They differ; the hbm3e note cites B200 at 8 x 12 mm on a
   160 mm perimeter = 60%, a real shipping precedent under the model's own
   `4*sqrt(A)` rule. The defect is precedent selection, not fabrication.
3. *"The beachfront constant over-grants at reticle scale (815 mm2 → 5 stacks vs
   4)."* Five stacks on 815 mm2 is 52.5% utilisation -- the A100's own 52.2%.
   The `0.522 → 4` result is a `floor()` artefact at 4.97. The finding is
   wafer-only.
4. *"A redundancy charge is a straight 2–12% haircut on the 849 weight_read-bound
   rows via `rom.array_efficiency`."* That field feeds only capacity;
   `rom_read_bytes_s_per_mm2` is anchored on macro throughput and never touches
   it. The fix must be a separate area fraction (see A4).
5. *"Every row of the iso-area table names a `-romfill` design."* The "fastest"
   rows do; the "smallest silicon" rows generally do not.
6. *"`balanced_area_split`'s fp8 hard-code undersizes a bf16 MAC array by 3.3x
   and the split cannot consume what its array reads."* The density ratio is
   exactly **2.0**, and for bf16 the 2x halving exactly cancels the 2x
   bytes-per-parameter, so the hard-code returns the format-correct answer
   (verified: Qwen effective MACs/s 2.130e15 against params/s 2.130e15,
   t_compute 3.553 us against t_weight 3.845 us). The residual mismatch is on
   w4a8 and favours **ROM**.

**On memory hierarchy**

7. *"KV access granularity (128 B SRAM vs 32 B HBM) penalises SRAM-KV designs by
   up to 1.33x."* Computed on a superseded model profile.
   `deepseek-v4-flash-0731.json` now carries `entry_bytes` 1024 and
   `index_entry_bytes` 256 -- exact multiples of both granules --
   and `kv_access_granularity_inflation` is exactly 1.0 at all 4,760 points in
   `n6_vs_a100` and all 4,592 in `n5_vs_b200`.
8. *"Charging the capacity refusal at `batch_size` while crediting throughput at
   `fill_users` is an independent asymmetry."* It is A6 restated; with the cap
   working the model is self-consistent by construction. The proposed fix
   (refuse at `fill_users`) would be **wrong** -- it would declare infeasible a
   design that can serve the requested batch merely because it cannot fill its
   surplus slots.
9. *"`METHODOLOGY §2`'s per-device / B x stages rule is unimplemented."*
   Sharding is uniform throughout: `B x stages` shards of `total/stages` each is
   identically `B x total`, so the aggregate check is algebraically the
   per-device check.
10. *"The on-die fabric is charged no area."* `roofline.py:1663` charges
    `interconnect_mm2 = 0.08 * total_mm2` and deducts it from compute -- 65.2 mm2
    of every 815 mm2 die. Residual defect: the config asks for a 0.05–0.15 sweep
    and nothing runs it.

**On efficiency derates**

11. *"`stage_balance` on tensor machines favours neither side."* It favours
    **ROM**: a tensor-only exemption moves 931 live rows down and 135 up, median
    0.980, and −3.4% on this headline.
12. *"The SRAM-KV capacity derate is worth 1.111x on 918 of 2,224 rows."* 994 of
    those rows are infeasible. The live exposure is 78 of 1,230 rows, and the
    mechanism is not a fill cut but an area displacement: the solver *sizes* the
    SRAM to the KV, so the honest counterfactual is ~−2.7%, not −11%.

**On search space**

13. *"Speculative decoding is not disclosed anywhere."* `REPORT.md:1648` and
    `n5_vs_b200/REPORT.md:1666`: "Prefill, speculative decoding and cost are out
    of scope for this model", in the very Interpretation-boundary section the
    claim names.
14. *"`fastest_feasible_gpu_*` is collected and dropped, so a reader cannot see
    the GPU's non-monotonicity."* The fields are unrendered, but the
    latency-separation table (`REPORT.md:330-372`) publishes the GPU's per-user
    rate at all seven rungs and shows the collapse plainly. Downgrade to a
    labelling gap.
15. *"TP group size is unswept and this favours ROM."* Mechanism confirmed --
    only `{1, domain, all}` is ever evaluated, on both sides -- but no direction
    is established, and at this headline TP=280 already **is** the best available
    point, so no intermediate group can raise the GPU. The value that looked
    like a TP knob is captured by the replication hull (A2).
16. *"The replication hull is the largest confirmed asymmetry that moves a
    published number."* It is worth 1.51x on the `n5_vs_b200` Flash headline and
    **0.985x on this one**. Its importance here is structural, not numeric.

**On anchors and gates**

17. *"The GPU side of the comparison has zero falsifiable validation."* The A100
    TDP power gate is falsifiable and does move (HBM bandwidth x8 → 4.73x FAIL).
    The correct statement is *zero falsifiable **throughput** validation*.
18. *"The A100 gate's FP8 stored width prices a machine that cannot exist."* The
    gate passes no execution format and never asserts FP8 arithmetic; 8-bit
    storage with BF16 dequantisation is a real deployment shape. The defect is
    that 8.0 is a bare Python default rather than a graded input, and not the
    released packing. `ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md:51` already
    prints both packings and both ratios.
19. *"`weight_traffic_policy` is recorded in no artifact."* It is at
    `validation_gates.<gate>.detail.step.metrics.weight_traffic_policy`. The
    residual defect is that it is not *rendered*.
20. *"The reports say nothing about the gates' scope."* Both carry an
    audit-scope block (`n6_vs_a100/REPORT.md:1518-1520`). It sits ~1,440 lines
    below the gates table, says "two" where the table shows four, and does not
    name the single-die/batch-1/no-collectives scope.
21. **Checked and cleared, worth recording as evidence against a fit:** the HC1
    gate is *not* fitted at the ROM-optimal edge. Sweeping
    `rom.cell_to_sram_cell_area_ratio` across its declared 1/6–1/4 bracket gives
    0.609 → 0.888; the value that would *close* the gate is 0.29–0.30, outside
    the bracket. The study takes 1/5, the midpoint. `rom.array_efficiency` is
    likewise at the midpoint of its declared 0.60–0.80 sweep. On both
    load-bearing axes of the ROM capacity chain the study sits at the declared
    midpoint, not at the gate-closing edge.

**On executed lanes**

22. *"The torch-vs-numpy pairing voids the entire W11.1 executed artifact."*
    Counters are produced by `runtime/sim/engine.py:_account_read/_account_write`
    as `array.size * dtype.itemsize` bucketed by storage class -- a path that
    never consults the numeric backend. Totals conserve to the byte across the
    two lanes (reads 366,294,894,160 on both sides; writes 686,411,872). Only
    the gate and the token-identity half are affected, and both 192-token lanes
    ran numpy/numpy.
23. *"The index-137 divergence is a coin flip."* It reproduces across two
    different linear-algebra implementations at the same `block=512` shape --
    same index, same token 1879, same tie multiplicity. "Neither lane is more
    correct" stands; "coin flip" does not. The reproducibility across libraries
    is itself evidence for the claim's own thesis, that the token block and not
    the storage class is the operative variable.
24. *"`prove_storage_class_equivalence.py` hides that the two backends emit
    different programs."* Disclosed at length in `README.md:101-107`,
    `docs/ABI3_PROGRAM_REPORT.md:73-80` and `:225-227`, in OI-19, and in the
    tool's own docstring. Residual defect: the artifact's 31/210 figures are
    stale against the executed lane's 75/239 and are quoted as current in four
    places.

---

# Part D — What would have to be measured

Every correction in this audit came from measuring something inside the
repository rather than arguing about it: re-running the model against mutated
configs, reconstructing steps from published component times, sweeping a
constant and watching a gate not move. The next correction cannot come from
inside the repository, and naming it is the most useful thing this document can
do.

**The headline is now a comparison between a measured collective and an assumed
one.**

Both sides bind on `link_latency`. The GPU's dominant link term rests on
`links.infiniband_hdr.hop_latency_s` = 4.5 us, graded **published**, cited to De
Sensi et al. (SC24) GPU-buffer-to-GPU-buffer measurements across five production
supercomputers, swept 3.7–5.7 us -- a **1.54x** band. The ROM's dominant link
term rests on `links.on_wafer.hop_latency_s` = 100 ns, graded **assumed**, whose
own note says "Not measured", swept 30–500 ns -- a **16.7x** band.

That one constant is 77% of the ROM link term on the published headline machine
and 97% on the machine the ROM would actually choose. Moving it alone across its
own declared sweep, with everything else held:

> **the headline runs from 3.40x to 11.80x.**

Every artefact in Part A together moves the headline from 8.63x to about 7.9x --
roughly 9%. One unmeasured number moves it by 3.5x. The ranking is not close.

## The measurements, in order

**1. A reticle-to-reticle hop latency, and a small-tensor all-reduce latency
across N reticle fields, on real wafer-scale silicon.** *(PARTLY ANSWERED
2026-08-31 -- the constant is now `derived` at 125 ns from published Cerebras
geometry and two measured whole-wafer collectives, swept 75-250 ns. What is still
missing is a direct measurement of the object itself: nobody has published a
latency for one reticle-field crossing, or a cycle cost for a stitched reticle
boundary.)*
This is the number. The model charges **1.54 us per 57-region on-wafer
all-reduce** (187.88 us / 122 events) at 100 ns per reticle crossing under a
mesh rule of ~1.1x diameter. The only shipping instance of the physics is a
Cerebras WSE. The measurement: run an all-reduce over a known number of tiles on
a CS-2 or CS-3, at message sizes matching a decode step's activation vector, and
back out nanoseconds per reticle crossing and traversals per collective. A
single published number for a ~57-region all-reduce would collapse the largest
band in the study. Nothing in this repository has it;
`docs/WAFER_VERSUS_ARRAY_LATENCY.md` is the assumption's only source, and it is
an argument rather than a measurement.

**2. An A100 NVLink/NVSwitch small-message all-reduce at TP=8.** *(ANSWERED
2026-08-31 -- four independent measurements of exactly this experiment exist and
are now the constant: 20.6 us stock NCCL, 5.0 us best kernel, on 8x A100 over
NVLink 3.0. The entry is `derived` at 2.5 us per traversal.)*
`links.nvlink3.hop_latency_s` = 1.5 us is *also* graded `assumed` -- NVIDIA
publishes no NVLink or NVSwitch latency figure in any form, and the note records
that six first-party pages were checked. It is swept 1.0–5.5 us, i.e. a 2.0 us
to 11.0 us in-domain all-reduce, bracketing a measured speed-of-light floor at
one end and stock NCCL's ring at the other, with the **stated value near the
optimistic end**. This one is cheap and immediate: one 8-GPU A100 node and
`nccl-tests all_reduce_perf -b 8 -e 1M -f 2 -g 8`. It is the GPU-side twin of
measurement 1, and measuring it is what makes measurement 1 a fair comparison
rather than a replacement of one assumption with another. Worth 14% of the GPU's
link term here, and far more on the smaller clusters.

**3. A wafer-to-wafer (SwarmX-class) hop latency.**
`links.inter_wafer.hop_latency_s` = 5.0 us, graded `assumed`, swept 1–10 us,
with the note "Cerebras publishes no SwarmX latency figure in any form" and "this
is the number that decides whether a twelve-wafer machine is one machine or
twelve". Only 23% of the ROM link term on the published headline machine and 3%
on the hull machine, so third priority -- but it is the constant that decides
whether the multi-wafer topologies exist at all.

**4. A single-user decode token rate for one of the three models on a real GPU
cluster.** This gates `efficiencies.hbm_bandwidth` = 0.85, the only bandwidth
derate on the GPU side, which no existing gate can test (A9). Worth ±7% here and
±20% on the Qwen headline. The repository already holds a measurement --
`results/gpu/local_rtx_pro_6000/20260828T102304Z/measurement.json`, 179–191 tok/s
at concurrency 1 on an RTX PRO 6000 Blackwell under vLLM -- and nothing in
`src/opentallas/roofline.py` or `tools/run_roofline_studies.py` reads it. It is
self-labelled "shared_contended service-level measurement; not a clean peak GPU
benchmark", so a clean single-user A100 or B200 decode measurement is preferable;
but wiring the existing one in as a second, honestly-caveated gate is strictly
better than the arithmetic identity currently occupying that slot.

## The question this audit could not answer

**Does a stitched wafer-scale mesh actually deliver a 57-region all-reduce in
1.5 us, and does a 672-GPU cluster actually deliver a two-tier all-reduce in
22.8 us?**

Those two numbers are 58% of the headline. One is extrapolated from a published
mesh-diameter rule and an assumed per-hop constant that has never been measured
at any scale; the other is built from one measured constant and one assumed one.
Until both are measured at the message sizes a decode step actually sends, the
8.6x is not a number. It is an interval roughly 3x to 12x wide, and every
asymmetry catalogued above -- including the ones worth fixing tonight -- sits
inside the width of that interval.
