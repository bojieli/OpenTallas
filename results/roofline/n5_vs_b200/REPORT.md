# Area-constrained roofline: n5_vs_b200

> Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 608x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `tensor` on 1 device. On the GPU side the correction reaches 268x (b200_sxm-x347-pipeline, 347 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `hybrid` on 29 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **6x**. The GPU binds on `weight_read` and the ROM part on `link_latency`.
4. **A token cannot cross more stage boundaries than the model has layers, and charging it as though it could was most of the reported advantage at scale.** At 554,700 mm2 on Qwen3-8B at batch 1, the iso-area GPU cluster is 347 devices. Cut as one serial pipeline that is 44 stages and 375 us of link latency per token; but the model has 36 layers, so at most 36 of those boundaries can exist and the rest of the silicon is replication, which adds bandwidth and no serial event: 338 us. The iso-area per-user ratio at that point falls from 3.0x to 2.9x. The same cap is applied to the ROM side, where it is worth more still because a twelve-wafer machine spans 681 reticle fields.
5. **Letting the GPU choose its own parallelism is worth up to 69.36x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 7.63 tok/s and the same silicon running tensor delivers 529 tok/s.
6. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.04x (Qwen3-8B, ROM binding on `weight_read`) to 18.08x (DeepSeek-V4-Flash-0731, ROM binding on `link_latency`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
7. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 35.7% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 810 to 11,593 tok/s, and its rate with every slot occupied from 11,340 to 11,593. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 14 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
8. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,498 us over NVLink, capping per-user decode at 667 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,478.2 us and cap it at 677 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 1.3x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
9. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 12 to the array and 12 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
10. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 224 of 3016 feasible points.
11. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 27.2x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
12. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 8.98x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 3.02x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 44 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
13. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
14. **The cooling limit binds, and not where a uniform correction said it would.** 105 of 3,016 feasible points (3.5%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` at batch 8 on 3,260 mm2, throttled 1.35x from 1,560 to 1,151 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 97% kv read against 0.5% weight read. The ROM sweep is not what melts it.

## The overlap and serialisation rule

```
t_memory  = t_weight + t_kv        weights and KV share one memory system
t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays
t_service = max(t_memory, t_compute)      on the AGGREGATE machine
t_user    = token_slots * t_service / stage_balance + t_link
t_user   *= thermal_scale

per_user_tokens_s  = 1 / t_user
aggregate_tokens_s = fill_users / t_user      fill_users = max(batch, slots)
delivered_tokens_s = batch / t_user
```

Compute overlaps memory. Weight and KV traffic **add** on a GPU because they
contend for the same HBM channels, and **overlap** on a ROM part because the
mask ROM and the KV store are physically separate arrays -- that single rule
is most of the architectural difference and it is stated rather than hidden
in an efficiency factor. Hop and collective latency is **added** to the
critical path at every batch size, because decode is sequential across
layers.

`t_service` is computed on the machine's **aggregate** resources: all of the
array bandwidth, all of the compute roof. That denominator is correct only
for partitions that are working on the same token at the same instant, which
is what tensor parallelism is. `token_slots = partitions / tensor_group` is
how many independent groups the machine is cut into, and a token is served by
exactly one of them at a time, so its latency is `token_slots` service times
long. **Under pipeline parallelism the two factors cancel exactly** -- each of
N stages holds 1/N of the weights and reads them with 1/N of the bandwidth --
so adding devices buys aggregate throughput and buys one user nothing.
Tensor parallelism is different in kind: every partition is on the same token,
`token_slots` is 1, and the price is two all-reduces per layer, charged in
`t_link`.

**`aggregate = batch x per-user rate` no longer holds and its removal is the
point.** The aggregate rate is the machine's rate with every slot occupied,
which needs `token_slots` concurrent users; below that the surplus slots idle
and the machine delivers `delivered_tokens_s` instead. The fill is capped by
the users whose KV the machine can hold, reported per point as
`pipeline_fill_limited_by`. Fill and drain are not charged: decode is a
continuous stream of steps and the pipeline is taken to be in steady state,
which flatters a deep pipeline by at most one traversal per request.

Every point also carries `per_user_tokens_s_throughput_view`: the single
number this study reported for both quantities before they were separated, so
the size of this correction is separable from every other one.

## Validation gates

| Gate | Published | Modelled | Ratio | Tolerance | Result |
|---|---:|---:|---:|---:|---|
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 12,232.4 tok/s | 0.72x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 389.9 W | 0.97x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 70.2 W | 0.28x | within 2x | FAIL |

HC1 binds on `weight_read`. Its component times are weight_read 76.55 us, kv_read 2.71 us, compute 76.55 us, link_latency 0.00 us, layer_fixed_latency 5.20 us.

The model **under**-predicts the shipping part by 1.39x. Rather than tune the densities until the anchor
is hit, the gate back-derives what each input would have to be for the
model to land exactly on 17,000 tok/s:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 1.764e+11 | 2.290e+11 | 1.30x |
| Compute density (ops/s/mm2) | 1.261e+12 | 2.840e+13 | 22.52x |

The compute density derived from A100's published dense roofs and die
area is within 2152.4% of what the shipping part must have. The ROM read-bandwidth density derived from a
28 nm simulated ROM-CIM macro is the input that is short, and the
required value is still below the SRAM read-bandwidth density derived
from Cerebras WSE-2 (5.563e+11 B/s/mm2), so it is physically unremarkable. That is a falsifiable
statement about one technology input, which is what a gate is for.

### The per-layer latency band, and why the gate is not fitted

Every term in the per-layer latency block is `assumed` and carries
a stated range. Reporting the gate at one point inside a wide band
would invite the point to be read as measured, which is how a gate
becomes a one-parameter curve fit. The terms are derived from
primitives independent of this anchor -- SRAM access time,
sequencer issue and decode, pipeline fill and drain across a
dependent array-pass boundary, the layer barrier, and an on-die
wire delay over a distance taken from the floorplan -- and the gate
is evaluated at both ends.

| Per-layer latency | Value | Per token | Modelled tok/s | Ratio | Binds on |
|---|---:|---:|---:|---:|---|
| range low | 65.4 ns/layer | 2.09 us | 12,715.1 | 0.75x | weight_read |
| range stated | 162.4 ns/layer | 5.20 us | 12,232.4 | 0.72x | weight_read |
| range high | 726.8 ns/layer | 23.26 us | 10,018.9 | 0.59x | weight_read |

The per-layer cost that would land the model exactly on the
published figure is **-549.7 ns/layer**. It is negative, which means the model is already slower than the shipping part before any fixed cost is charged: no value of this term could have closed the gap, and the residual lies in the ROM read-bandwidth density instead.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 12,232.4 | 0.72x | weight_read |
| 3.5 | 12,232.4 | 0.72x | weight_read |
| 4.0 | 12,232.4 | 0.72x | weight_read |
| 5.0 | 12,232.4 | 0.72x | weight_read |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 12,232.4 | 0.72x | weight_read |
| 1,536 | 12,232.4 | 0.72x | weight_read |
| 2,048 | 12,232.4 | 0.72x | weight_read |

### The two power gates, and the residual they leave

Two gates in the shape of the two above, added because every watt this
program reported was 7-9x low against both published parts and because
`thermal_scale` was exactly 1.0 at every feasible point, so no rate
depended on the energy model at all. **Nothing was tuned to close
either of them.** Six power terms were derived from primitives and
adversarially verified; every one was sent back with a correction, and
the corrections are what is applied. Two of them move power up and two
move it down.

The A100 gate is evaluated at a **saturating** operating point --
2.039 TB/s of published HBM
bandwidth and 312 T ops/s of published
dense roof at 1,410 MHz, both at
once -- because a TDP is what a part is built to shed under load, not
what a decode step draws. The HC1 gate is evaluated at exactly the point
its throughput gate already uses, read off that gate's own step so the
two cannot drift apart.

| Gate | Published | Modelled | Ratio | Result |
|---|---:|---:|---:|---|
| A100 at TDP, saturating | 400.0 W | 389.9 W | 0.97x | PASS |
| Taalas HC1 card power | 200.0-250.0 W | 70.2 W | 0.28x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 3.2 W |
| KV traffic | n/a: one saturating HBM stream | 3.3 W |
| operand delivery | 0.5 W | 10.0 W |
| arithmetic | 31.2 W | 3.7 W |
| static: leakage | 31.4 W | 11.3 W |
| static: clock distribution | 99.0 W | 22.2 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 50.0 W |
| **total** | 389.9 W | 70.2 W |

On HC1 the enumerated static power is 33.5 W and the measured clocked-idle floor is 50.0 W, so **the floor binds**: the bottom-up enumeration of this part's leakage and clock tree is below what a shipping clocked device is measured to draw, and the floor is charged instead. The two are combined with `max` and never added, because a measured clocked-idle reading IS mostly leakage and clock tree.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 267.1 W | 0.67x | 54.3 W | 0.22x | 0.27x |
| stated | 389.9 W | 0.97x | 70.2 W | 0.28x | 0.35x |
| high | 626.6 W | 1.57x | 267.1 W | 1.07x | 1.34x |

**The outcome, stated as an outcome.** The A100 gate lands at 0.97x of its published TDP. The HC1 gate lands at 0.28x of the top of its published band, **3.56x low**, against 2.85x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

**Why the A100 gate is the weaker of the two, and must not be quoted
as independent.** `power.clock_energy_j_per_mm2_per_cycle` was
calibrated as 20-45% of a shipping GPU's published TDP density. It is
a different GPU -- P100 and GV100 at 16FF+/12FFN, not this part -- but
it is still a GPU TDP, so adding that term to the others and comparing
the sum with a GPU's TDP is partly checking an input against its own
family. What the gate does test is that the traffic terms, the
arithmetic and the static terms are mutually consistent in size, and
it would fail loudly if any were an order of magnitude out. The HC1
gate has no such circularity: nothing on the ROM side was calibrated
on a Taalas figure, because Taalas publishes no microarchitecture and
no energy at all. **It is the stronger gate and it is the one that
fails.**

**Energy per token at the two anchors.** Both parts serve the same workload -- Llama-3.1-8B at batch 1 -- so this is the cleanest statement the model can make about the ROM argument, and it could not be made at all until the power terms existed:

| Part | J/token | W | tok/s |
|---|---:|---:|---:|
| Taalas HC1 (modelled reconstruction) | 0.005736 | 70.2 | 12,232.4 |
| A100 80GB, weight-bound gate, same model and batch | 1.462191 | 358.8 | 245.4 |

That is a factor of 255 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.9-3.6x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged **zero** leakage, because the companion term
for it was refuted as underived; at the top of its reconstructed
bracket it would add 10.4 W,
which does not close the gate either. `energy.rom_read_j_per_byte`
moved from 0.5 to 0.08 pJ/B on the evidence, which made this gate
**worse by about 4x on that term alone** and was adopted anyway. The
honest reading is that a compute-in-ROM part's energy has never been
published at any node, and this model's ROM side is built from macros
that are mostly simulated, at 28-130 nm, with boundaries that do not
match the term they are being asked to supply.


## Power, dark silicon and energy per token

**The thermal limit binds here, and this is the first version of this
study in which it could.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **105 of 3,016 feasible points (3.5%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 1, rom 104.
- By area class: large array (5,000-40,000 mm2) 33, small array (1,600-5,000 mm2) 72.
- By KV store: hbm 105.
- By batch: B=1 9, B=2 9, B=4 9, B=8 10, B=16 13, B=32 18, B=64 18, B=256 19.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 47% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 8.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 168 | 0 | 65.6% | 100.0% | 0.625 | 54% |
| gpu | small array (1,600-5,000 mm2) | 30 | 1 | 99.2% | 100.0% | 0.625 | 36% |
| gpu | wafer (>=40,000 mm2) | 696 | 0 | 45.7% | 98.8% | 0.618 | 77% |
| rom | large array (5,000-40,000 mm2) | 330 | 33 | 17.8% | 100.0% | 0.500 | 73% |
| rom | small array (1,600-5,000 mm2) | 112 | 71 | 100.0% | 100.0% | 0.500 | 21% |
| rom | wafer (>=40,000 mm2) | 1,680 | 0 | 20.6% | 47.1% | 0.235 | 87% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` | Qwen3-8B | 8 | 3,260 | hbm | 1.354x | 1,630.0 / 1,630.0 W | 26% | 1,151.5 | 1,559.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` | Qwen3-8B | 16 | 3,260 | hbm | 1.352x | 1,630.0 / 1,630.0 W | 26% | 580.9 | 785.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` | Qwen3-8B | 32 | 3,260 | hbm | 1.351x | 1,630.0 / 1,630.0 W | 26% | 291.8 | 394.3 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` | Qwen3-8B | 64 | 3,260 | hbm | 1.351x | 1,630.0 / 1,630.0 W | 26% | 146.2 | 197.5 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` | Qwen3-8B | 256 | 3,260 | hbm | 1.350x | 1,630.0 / 1,630.0 W | 26% | 36.6 | 49.4 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4` | Qwen3-8B | 256 | 3,260 | hbm | 1.314x | 1,630.0 / 1,630.0 W | 26% | 36.6 | 48.1 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4` | Qwen3-8B | 64 | 3,260 | hbm | 1.282x | 1,630.0 / 1,630.0 W | 26% | 146.5 | 187.7 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill` | Qwen3-8B | 1 | 3,260 | hbm | 1.269x | 1,630.0 / 1,630.0 W | 21% | 2,422.5 | 3,073.9 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill` | Qwen3-8B | 2 | 3,260 | hbm | 1.269x | 1,630.0 / 1,630.0 W | 21% | 2,422.5 | 3,073.9 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill` | Qwen3-8B | 4 | 3,260 | hbm | 1.269x | 1,630.0 / 1,630.0 W | 21% | 2,422.5 | 3,073.9 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill` | Qwen3-8B | 8 | 3,260 | hbm | 1.265x | 1,630.0 / 1,630.0 W | 21% | 1,233.0 | 1,559.6 |
| `Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4` | Qwen3-8B | 1 | 3,260 | hbm | 1.264x | 1,630.0 / 1,630.0 W | 26% | 2,262.3 | 2,859.5 |

The worst point's dynamic energy is kv read 96.8%, operand delivery 1.5%, arithmetic 1.2%, weight read 0.5%. **The ROM sweep is not what melts it.** A mask-ROM array
reads its weights for almost nothing; what it still pays for, at
the same rate a GPU does, is KV traffic to DRAM. That is an
argument for keeping KV on die, and it is visible here only
because the power model now distinguishes the two.

### Energy per token, both sides, at equal area

**This number has been unpublishable until now.** Not paying DRAM
access energy for weights is much of the ROM argument, and the
model could not state it while every watt in it was 7-9x low. The
figures below include the static share amortised over the tokens
the step actually produces, so a machine that is fast and leaky is
not flattered against one that is slow and cool.

One row per (model, batch). The ROM design is the smallest silicon within 5% of the fastest per-user rate -- the same rule the report uses everywhere it says 'best' -- and the GPU beside it is the iso-area comparator that comparison already chose. Listing every comparison instead buries the answer under wafers serving one user.

| Model | B | mm2 | ROM design | ROM J/token | ROM W | ROM binds | iso-area GPU | GPU J/token | GPU W | GPU binds | ROM tokens/joule |
|---|---:|---:|---|---:|---:|---|---|---:|---:|---|---:|
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 0.774530 | 3,807.2 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 3.601531 | 15,328.8 | weight_read | 4.65x |
| DeepSeek-V4-Flash-0731 | 2 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.439023 | 4,314.9 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 3.601531 | 15,328.8 | weight_read | 8.20x |
| DeepSeek-V4-Flash-0731 | 4 | 46,225 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill` | 0.243617 | 4,641.0 | link_latency | `DSV4-Flash/b200_sxm-x29-hybrid` | 3.601531 | 15,328.8 | weight_read | 14.78x |
| DeepSeek-V4-Flash-0731 | 8 | 92,450 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.252594 | 9,225.1 | link_latency | `DSV4-Flash/b200_sxm-x58-hybrid` | 4.648310 | 27,508.6 | weight_read | 18.40x |
| DeepSeek-V4-Flash-0731 | 16 | 138,675 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.211807 | 14,282.2 | link_latency | `DSV4-Flash/b200_sxm-x87-hybrid` | 4.377940 | 39,013.5 | weight_read | 20.67x |
| DeepSeek-V4-Flash-0731 | 32 | 277,350 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.223577 | 28,261.0 | link_latency | `DSV4-Flash/b200_sxm-x173-tensor` | 5.505881 | 64,333.6 | link_latency | 24.63x |
| DeepSeek-V4-Flash-0731 | 64 | 369,800 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.179284 | 39,498.3 | link_latency | `DSV4-Flash/b200_sxm-x231-hybrid` | 5.865949 | 93,039.4 | weight_read | 32.72x |
| DeepSeek-V4-Flash-0731 | 256 | 554,700 | `DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.118583 | 67,617.8 | link_latency | `DSV4-Flash/b200_sxm-x347-hybrid` | 4.372659 | 137,933.7 | weight_read | 36.87x |
| DeepSeek-V4-Pro-0813 | 1 | 92,450 | `DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2` | 3.163115 | 7,463.5 | link_latency | `DSV4-Pro/b200_sxm-x58-tensor` | 45.282234 | 22,518.0 | link_latency | 14.32x |
| DeepSeek-V4-Pro-0813 | 2 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 1.938221 | 13,622.8 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 36.501923 | 33,207.2 | link_latency | 18.83x |
| DeepSeek-V4-Pro-0813 | 4 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 1.514336 | 14,189.2 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 22.214219 | 33,946.6 | link_latency | 14.67x |
| DeepSeek-V4-Pro-0813 | 8 | 138,675 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.894662 | 16,338.5 | link_latency | `DSV4-Pro/b200_sxm-x87-tensor` | 14.481683 | 35,010.1 | link_latency | 16.19x |
| DeepSeek-V4-Pro-0813 | 16 | 277,350 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.918041 | 32,366.1 | link_latency | `DSV4-Pro/b200_sxm-x173-tensor` | 17.754271 | 66,707.5 | link_latency | 19.34x |
| DeepSeek-V4-Pro-0813 | 32 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.964797 | 63,609.8 | link_latency | `DSV4-Pro/b200_sxm-x347-tensor` | 24.395929 | 128,986.3 | link_latency | 25.29x |
| DeepSeek-V4-Pro-0813 | 64 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.738046 | 70,804.4 | kv_read | `DSV4-Pro/b200_sxm-x347-tensor` | 19.798338 | 129,038.5 | link_latency | 26.83x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12` | 0.765029 | 111,423.7 | kv_read | `DSV4-Pro/b200_sxm-x347-hybrid` | 16.003424 | 139,212.2 | weight_read | 20.92x |
| Qwen3-8B | 1 | 46,225 | `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill` | 0.589593 | 3,835.5 | link_latency | `Qwen3-8B/b200_sxm-x29-hybrid` | 3.149267 | 22,385.4 | weight_read | 5.34x |
| Qwen3-8B | 2 | 92,450 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill` | 0.869640 | 9,339.5 | link_latency | `Qwen3-8B/b200_sxm-x58-hybrid` | 3.196664 | 43,986.4 | weight_read | 3.68x |
| Qwen3-8B | 4 | 138,675 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill` | 0.735763 | 14,457.9 | link_latency | `Qwen3-8B/b200_sxm-x87-hybrid` | 3.284644 | 63,984.5 | weight_read | 4.46x |
| Qwen3-8B | 8 | 277,350 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill` | 0.780900 | 28,554.8 | link_latency | `Qwen3-8B/b200_sxm-x173-hybrid` | 3.422403 | 121,845.1 | weight_read | 4.38x |
| Qwen3-8B | 16 | 369,800 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill` | 0.632409 | 39,889.6 | link_latency | `Qwen3-8B/b200_sxm-x231-hybrid` | 3.523471 | 158,115.2 | link_latency | 5.57x |
| Qwen3-8B | 32 | 554,700 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.573642 | 61,396.1 | link_latency | `Qwen3-8B/b200_sxm-x347-hybrid` | 3.605072 | 232,498.6 | link_latency | 6.28x |
| Qwen3-8B | 64 | 554,700 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.424876 | 68,231.9 | link_latency | `Qwen3-8B/b200_sxm-x347-hybrid` | 2.546699 | 233,836.4 | link_latency | 5.99x |
| Qwen3-8B | 256 | 554,700 | `Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill` | 0.313301 | 80,547.0 | kv_read | `Qwen3-8B/b200_sxm-x347-hybrid` | 0.800384 | 244,282.4 | link_latency | 2.55x |

**Read this with the power gates beside it.** The ROM side's energy
rests on `energy.rom_read_j_per_byte`, which is `assumed` over a
17x-wide bracket, and on an operand-delivery scalar that is the
tile-local floor with no long-path ladder in it. The HC1 power gate
says the ROM side's total is several times below a shipping part's
published card power, so **every ROM joule-per-token here is a
lower bound and should be quoted as one.** The GPU side rests on
a measured, peer-reviewed HBM figure and on a gate that lands
within a few percent of a published TDP, so the two sides are not
equally well founded and the ratio inherits the weaker of them.

**A dense model gives the energy advantage back as batch rises and
a sparse one does not.** A GPU amortises one weight read over the
whole batch, so its joules per token fall roughly as 1/batch until
KV takes over; the ROM part's weight read was already nearly free,
so it has nothing to amortise. On a sparse model the GPU cannot
amortise -- batching engages more experts -- so the ROM advantage
grows instead. Quoting a dense model's batch-1 number without its
batch-256 number beside it is quoting the best case as the case.


## Derived technology at N5

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.869 MB/mm2 | assumed |
| ROM capacity density | 20.833 MB/mm2 | assumed |
| ROM read bandwidth density | 362.9 GB/s/mm2 | derived |
| SRAM read bandwidth density | 556.3 GB/s/mm2 | derived |
| Compute density, bf16 | 0.680 Tops/s/mm2 | derived |
| Compute density, fp8 | 1.360 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.923 Tops/s/mm2 | derived |
| Compute density, fp4 | 2.720 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.042 Tops/s/mm2 | derived |
| ROM full-array sweep time | 76.6 us | derived |
| ROM per-token ceiling from that sweep | 13,063 tok/s | derived |
| ROM per-token ceiling before the read derate | 17,417 tok/s | derived |

The ROM full-array sweep time is rom_capacity_density divided by rom_read_bandwidth_density. Both scale with the same published bitcell-area ratio under this derivation, so the sweep time -- and hence the ROM path's hard per-token ceiling -- is the SAME at every node. Process scaling buys a ROM design capacity, not per-token speed. No clock-frequency bonus is credited, which makes this the conservative reading.

## Models and their work

| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | KV/user | W:KV at B=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 8,192 | 8 B | 16.4 GB | 16.00 | 1.208 GB | 1.208 GB | 12.5 |
| DeepSeek-V4-Flash-0731 | 200,000 | 284 B | 166.9 GB | 4.70 | 0.317 GB | 1.382 GB | 35.3 |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 1,600 B | 892.7 GB | 4.46 | 2.207 GB | 9.856 GB | 18.0 |

## The latency separation, before and after, at batch 1

Per-user latency and aggregate throughput used to be one number in
this study. The service time was computed on the machine's
**aggregate** resources -- the throughput view -- and the hops were
added on the single-token path, which is the latency view. A token
under pipeline parallelism is served by one stage's silicon at a time
and has to visit every stage, so its latency is that service time
multiplied by the slot count, not divided by anything.

**Before** is not a memory of an earlier run. Every point carries
`per_user_tokens_s_throughput_view`, the number the old rule produced,
and each side is ranked by it -- so the before column reproduces the
previous topology choice as well as the previous rate, and the two
corrections stay separable. Both sides are read at the same seven
rungs of silicon.

| Model | Wafer-eq | mm2 | ROM before | topo | ROM after | topo | ROM /x | GPU before | topo | GPU after | topo | GPU /x | Ratio before | Ratio after | Ratio change |
|---|---:|---:|---:|---|---:|---|---:|---:|---|---:|---|---:|---:|---:|---:|
| Qwen3-8B | 1 | 46,225 | 51,291.3 | wafer-pipeline | 6,505.3 | wafer-tensor | 7.88x | 7,034.3 | pipeline | 1,777.0 | hybrid | 3.96x | 7.29x | 3.66x | 0.50x |
| Qwen3-8B | 2 | 92,450 | 48,716.3 | wafer-pipeline | 5,878.5 | wafer-hybrid | 8.29x | 9,256.6 | pipeline | 1,720.0 | hybrid | 5.38x | 5.26x | 3.42x | 0.65x |
| Qwen3-8B | 3 | 138,675 | 48,716.3 | wafer-pipeline | 5,391.7 | wafer-hybrid | 9.04x | 10,789.5 | pipeline | 1,770.9 | hybrid | 6.09x | 4.52x | 3.04x | 0.67x |
| Qwen3-8B | 4 | 184,900 | 51,537.5 | wafer-pipeline | 5,093.3 | wafer-hybrid | 10.12x | 11,763.6 | pipeline | 1,692.0 | hybrid | 6.95x | 4.38x | 3.01x | 0.69x |
| Qwen3-8B | 6 | 277,350 | 61,188.9 | wafer-pipeline | 4,843.9 | wafer-hybrid | 12.63x | 12,916.2 | pipeline | 1,618.3 | hybrid | 7.98x | 4.74x | 2.99x | 0.63x |
| Qwen3-8B | 8 | 369,800 | 67,510.2 | wafer-pipeline | 4,617.8 | wafer-hybrid | 14.62x | 13,596.9 | pipeline | 1,547.4 | hybrid | 8.79x | 4.97x | 2.98x | 0.60x |
| Qwen3-8B | 12 | 554,700 | 75,288.0 | wafer-pipeline | 4,223.4 | wafer-hybrid | 17.83x | 14,351.1 | pipeline | 1,465.7 | hybrid | 9.79x | 5.25x | 2.88x | 0.55x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 23,181.2 | wafer-pipeline | 4,915.5 | wafer-tensor | 4.72x | 4,332.5 | pipeline | 1,064.0 | hybrid | 4.07x | 5.35x | 4.62x | 0.86x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 32,761.7 | wafer-pipeline | 4,728.6 | wafer-hybrid | 6.93x | 4,643.4 | pipeline | 857.1 | tensor | 5.42x | 7.06x | 5.52x | 0.78x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 39,515.6 | wafer-pipeline | 4,619.2 | wafer-hybrid | 8.55x | 4,966.6 | pipeline | 866.4 | tensor | 5.73x | 7.96x | 5.33x | 0.67x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 44,044.8 | wafer-pipeline | 4,514.4 | wafer-hybrid | 9.76x | 5,151.5 | pipeline | 871.1 | tensor | 5.91x | 8.55x | 5.18x | 0.61x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 49,736.6 | wafer-pipeline | 4,317.8 | wafer-hybrid | 11.52x | 5,352.7 | pipeline | 876.0 | tensor | 6.11x | 9.29x | 4.93x | 0.53x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 53,167.9 | wafer-pipeline | 4,137.4 | wafer-hybrid | 12.85x | 5,463.6 | pipeline | 878.5 | tensor | 6.22x | 9.73x | 4.71x | 0.48x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 57,104.4 | wafer-pipeline | 3,818.2 | wafer-hybrid | 14.96x | 5,580.4 | pipeline | 881.1 | tensor | 6.33x | 10.23x | 4.33x | 0.42x |
| DeepSeek-V4-Pro-0813 | 2 | 92,450 | 8,986.6 | wafer-pipeline | 2,359.5 | wafer-hybrid | 3.81x | 1,619.4 | pipeline | 497.3 | tensor | 3.26x | 5.55x | 4.74x | 0.86x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 12,160.6 | wafer-pipeline | 2,342.8 | wafer-hybrid | 5.19x | 1,754.4 | pipeline | 509.3 | tensor | 3.44x | 6.93x | 4.60x | 0.66x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 14,656.5 | wafer-pipeline | 2,315.2 | wafer-hybrid | 6.33x | 1,839.6 | pipeline | 515.6 | tensor | 3.57x | 7.97x | 4.49x | 0.56x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 18,443.0 | wafer-pipeline | 2,262.0 | wafer-hybrid | 8.15x | 1,934.5 | pipeline | 522.2 | tensor | 3.70x | 9.53x | 4.33x | 0.45x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 21,204.0 | wafer-pipeline | 2,213.3 | wafer-hybrid | 9.58x | 1,987.9 | pipeline | 525.7 | tensor | 3.78x | 10.67x | 4.21x | 0.39x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 24,912.4 | wafer-pipeline | 2,119.9 | wafer-hybrid | 11.75x | 2,044.8 | pipeline | 529.2 | tensor | 3.86x | 12.18x | 4.01x | 0.33x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.33x to 0.86x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


## Iso-area comparison

Two ROM designs per operating point -- the **fastest** and the
**smallest silicon that serves the point at all** -- each against the GPU
cluster of the closest equal silicon area. **The area is stated on both
sides.** Where one row appears, the two coincide.

**Both sides choose their own parallelism.** The GPU cluster is
evaluated under pipeline, tensor and hybrid and the best is reported,
exactly as the ROM side is. `PP-only ratio` is what the same comparison
says when the GPU is allowed pipeline and nothing else.

`Ratio without the layer cap` is what the comparison says when a token
is allowed to cross more stage boundaries than the model has layers --
which is what this study charged before. That column, not the topology
sweep, is where the previously published ratios came from.

**`user tok/s` and `aggregate tok/s` are different quantities and no
longer differ by the batch.** `user tok/s` is one user's token rate on
the full serial path through the machine. `aggregate tok/s` is the
machine's total rate with a user in every slot, which needs
`token_slots` concurrent users; where the batch is smaller than that,
the surplus slots idle and what the machine actually delivers at the
stated batch is `batch x user tok/s`, carried per point as
`delivered_tokens_s`. Read the per-user ratio for a latency claim and
the aggregate ratio for a throughput claim; reading either as the other
is the error this study made.

| Model | B | Pick | ROM design | ROM mm2 | ROM user tok/s | ROM aggregate tok/s | ROM binds on | GPU | GPU mm2 | Area ratio | GPU parallelism | GPU link us | GPU user tok/s | GPU aggregate tok/s | GPU binds on | Per-user ratio | Aggregate ratio | PP-only ratio | Ratio without the layer cap |
|---|---:|---|---|---:|---:|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,505.3 | 6,505.3 | link_latency | Qwen3-8B/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 188.51 | 1,777.0 | 7,108.1 | weight_read | 3.66x | 0.92x | 17.70x | 3.66x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3 | 2,445 | 3,795.9 | 3,795.9 | weight_read | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 0.76x | tensor | 173.78 | 660.1 | 660.1 | weight_read | 5.75x | 5.75x | 10.16x | 5.75x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,369.8 | 10,739.5 | link_latency | Qwen3-8B/b200_sxm-x58-hybrid | 92,800 | 1.00x | hybrid | 207.17 | 1,720.0 | 13,760.1 | weight_read | 3.12x | 0.78x | 14.67x | 3.12x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | 3,260 | 2,945.3 | 5,890.7 | link_latency | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 174.77 | 619.3 | 1,238.6 | weight_read | 4.76x | 4.76x | 7.89x | 4.76x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 5,093.3 | 20,373.1 | link_latency | Qwen3-8B/b200_sxm-x116-hybrid | 185,600 | 1.00x | hybrid | 239.81 | 1,692.0 | 25,380.1 | weight_read | 3.01x | 0.80x | 13.92x | 3.01x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill | 3,260 | 2,422.5 | 9,690.0 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 176.73 | 551.3 | 2,205.0 | weight_read | 4.39x | 4.39x | 6.97x | 4.39x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 4,617.8 | 36,942.1 | link_latency | Qwen3-8B/b200_sxm-x231-hybrid | 369,600 | 1.00x | hybrid | 305.11 | 1,547.4 | 44,874.8 | link_latency | 2.98x | 0.82x | 12.62x | 2.98x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4-romfill | 3,260 | 1,233.0 | 9,863.7 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 180.66 | 451.9 | 3,615.3 | weight_read | 2.73x | 2.73x | 4.03x | 2.73x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4,012.6 | 64,201.3 | link_latency | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 337.75 | 1,465.7 | 64,492.1 | link_latency | 2.74x | 1.00x | 10.97x | 2.89x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4-romfill | 3,260 | 626.3 | 10,021.0 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 188.53 | 332.2 | 5,315.1 | kv_read | 1.89x | 1.89x | 2.54x | 1.89x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,344.6 | 107,028.6 | link_latency | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 337.75 | 1,465.7 | 64,492.1 | link_latency | 2.28x | 1.66x | 9.14x | 2.41x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4-romfill | 3,260 | 313.5 | 10,032.4 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 204.26 | 217.1 | 6,948.6 | kv_read | 1.44x | 1.44x | 1.77x | 1.44x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,509.3 | 160,592.6 | link_latency | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 341.14 | 1,434.7 | 91,819.4 | link_latency | 1.75x | 1.75x | 6.86x | 1.84x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4-romfill | 3,260 | 156.8 | 10,038.1 | thermal | Qwen3-8B/b200_sxm-x2-tensor | 3,200 | 1.02x | tensor | 235.71 | 128.3 | 8,210.3 | kv_read | 1.22x | 1.22x | 1.38x | 1.22x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,004.3 | 257,091.2 | kv_read | Qwen3-8B/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 373.67 | 1,192.2 | 305,206.6 | link_latency | 0.84x | 0.84x | 2.74x | 0.89x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4-romfill | 3,260 | 39.2 | 10,042.4 | thermal | Qwen3-8B/b200_sxm-x2-pipeline | 3,200 | 1.02x | pipeline | 2.37 | infeasible | — | capacity_or_format | — | — | — | — |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,915.5 | 4,915.5 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 222.45 | 1,064.0 | 4,256.2 | weight_read | 4.62x | 1.15x | 25.49x | 4.62x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x14 | 11,410 | 2,545.1 | 5,090.3 | link_latency | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 208.41 | 1,656.8 | 1,656.8 | weight_read | 1.54x | 3.07x | 6.91x | 1.54x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,914.2 | 9,828.3 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 222.45 | 1,064.0 | 4,256.2 | weight_read | 4.62x | 2.31x | 25.48x | 4.62x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | 11,410 | 2,531.4 | 5,062.8 | link_latency | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 210.43 | 1,356.4 | 2,712.8 | weight_read | 1.87x | 1.87x | 6.87x | 1.87x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,762.6 | 19,050.4 | link_latency | DSV4-Flash/b200_sxm-x29-hybrid | 46,400 | 1.00x | hybrid | 222.45 | 1,064.0 | 4,256.2 | weight_read | 4.48x | 4.48x | 24.69x | 4.48x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | 11,410 | 1,755.9 | 7,023.6 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 214.45 | 1,031.0 | 4,124.0 | weight_read | 1.70x | 1.70x | 4.77x | 1.70x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,609.9 | 36,878.9 | link_latency | DSV4-Flash/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,304.26 | 624.0 | 4,992.1 | link_latency | 7.39x | 7.39x | 49.94x | 7.39x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | 11,410 | 1,088.8 | 8,710.3 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 222.50 | 728.3 | 5,826.6 | weight_read | 1.49x | 1.49x | 3.11x | 1.49x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,357.6 | 69,721.1 | link_latency | DSV4-Flash/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 1,644.52 | 499.0 | 7,983.3 | link_latency | 8.73x | 8.73x | 59.17x | 8.73x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 710.8 | 11,372.6 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 238.61 | 489.2 | 7,827.3 | weight_read | 1.45x | 1.45x | 2.76x | 1.45x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,994.3 | 127,816.1 | link_latency | DSV4-Flash/b200_sxm-x231-tensor | 369,600 | 1.00x | tensor | 2,352.17 | 368.8 | 11,802.6 | link_latency | 10.83x | 10.83x | 97.47x | 10.83x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 359.0 | 11,489.3 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 270.81 | 327.2 | 10,469.1 | weight_read | 1.10x | 1.10x | 2.03x | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,510.0 | 224,636.9 | link_latency | DSV4-Flash/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 3,755.75 | 242.1 | 15,495.8 | link_latency | 14.50x | 14.50x | 123.86x | 14.50x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 180.4 | 11,548.5 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 335.23 | 231.3 | 14,802.5 | weight_read | 0.78x | 0.78x | 1.57x | 0.78x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,227.4 | 570,217.3 | link_latency | DSV4-Flash/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 447.39 | 123.2 | 31,544.6 | weight_read | 18.08x | 18.08x | 78.60x | 18.09x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | 11,410 | 45.3 | 11,593.4 | compute | DSV4-Flash/b200_sxm-x7-tensor | 11,200 | 1.02x | tensor | 721.70 | 143.7 | 36,780.6 | weight_read | 0.32x | 0.32x | 0.95x | 0.32x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,359.5 | 2,359.5 | link_latency | DSV4-Pro/b200_sxm-x58-tensor | 92,800 | 1.00x | tensor | 1,487.72 | 497.3 | 497.3 | link_latency | 4.74x | 4.74x | 69.98x | 4.74x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x72 | 58,680 | 715.0 | 715.0 | compute | DSV4-Pro/b200_sxm-x37-tensor | 59,200 | 0.99x | tensor | 1,479.85 | 479.4 | 479.4 | link_latency | 1.49x | 1.49x | 15.72x | 1.49x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,342.8 | 7,028.5 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,591.80 | 454.9 | 909.7 | link_latency | 5.15x | 7.73x | 93.67x | 5.15x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 691.5 | 6,915.4 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 1,568.91 | 420.3 | 840.6 | link_latency | 1.65x | 8.23x | 15.46x | 1.65x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,342.5 | 9,369.9 | link_latency | DSV4-Pro/b200_sxm-x87-tensor | 139,200 | 1.00x | tensor | 1,792.80 | 382.0 | 1,528.1 | link_latency | 6.13x | 6.13x | 93.66x | 6.13x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 691.5 | 6,915.4 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 1,747.01 | 349.7 | 1,398.9 | link_latency | 1.98x | 4.94x | 15.46x | 1.98x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 2,313.7 | 18,509.3 | link_latency | DSV4-Pro/b200_sxm-x116-tensor | 185,600 | 1.00x | tensor | 2,215.16 | 311.0 | 2,488.0 | link_latency | 7.44x | 7.44x | 116.17x | 7.44x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 691.5 | 6,915.4 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 2,103.22 | 270.5 | 2,163.8 | link_latency | 2.56x | 3.20x | 15.46x | 2.56x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 2,207.6 | 35,321.6 | link_latency | DSV4-Pro/b200_sxm-x231-tensor | 369,600 | 1.00x | tensor | 3,093.55 | 240.2 | 3,842.7 | link_latency | 9.19x | 9.19x | 199.82x | 9.19x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 475.0 | 7,599.4 | compute | DSV4-Pro/b200_sxm-x38-tensor | 60,800 | 0.99x | tensor | 2,815.65 | 193.6 | 3,097.8 | link_latency | 2.45x | 2.45x | 10.62x | 2.45x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,060.3 | 65,930.8 | link_latency | DSV4-Pro/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 4,835.78 | 165.2 | 5,287.2 | link_latency | 12.47x | 12.47x | 270.02x | 12.47x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 258.8 | 8,281.9 | compute | DSV4-Pro/b200_sxm-x38-hybrid | 60,800 | 0.99x | hybrid | 350.79 | 135.6 | 4,339.9 | weight_read | 1.91x | 1.91x | 5.79x | 1.91x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,499.0 | 95,935.0 | kv_read | DSV4-Pro/b200_sxm-x347-tensor | 555,200 | 1.00x | tensor | 8,280.77 | 101.8 | 6,517.6 | link_latency | 14.72x | 14.72x | 196.45x | 14.72x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x74 | 60,310 | 135.5 | 8,671.4 | compute | DSV4-Pro/b200_sxm-x38-hybrid | 60,800 | 0.99x | hybrid | 390.78 | 93.6 | 5,992.0 | weight_read | 1.45x | 1.45x | 3.79x | 1.45x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 568.9 | 145,646.4 | kv_read | DSV4-Pro/b200_sxm-x347-hybrid | 555,200 | 1.00x | hybrid | 587.71 | 34.0 | 8,698.9 | weight_read | 16.74x | 16.74x | 74.56x | 16.74x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x74 | 60,310 | 35.6 | 9,124.5 | compute | DSV4-Pro/b200_sxm-x38-hybrid | 60,800 | 0.99x | hybrid | 630.70 | 43.3 | 11,087.1 | weight_read | 0.82x | 0.82x | 1.95x | 0.82x |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer_n5`, `inter_wafer`), which no GPU design touches; the
**cluster fabric** alone (`nvlink5`, `infiniband_ndr`), which is charged to both families; and
both together.

**Why three and not one.** This study used to publish the joint band only. Moving
both sides at once is the right test for a *common-mode* error, and the wrong one
for asking how much of the uncertainty is ours: the two sides partly cancel, so the
joint band comes out narrower than the wafer side's own band and the reader cannot
see that most of the width sits on the side with the weaker evidence. Reading the
cells: a **low** wafer hop makes the ROM machine faster and the ratio larger, and a
**low** cluster hop makes the GPU faster and the ratio smaller, so the two columns
run in opposite directions by construction.

| Model | ROM mm2 | Ratio stated | Wafer fabric low → high | Cluster fabric low → high | Both together | Widest one-sided span |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 11,410 | 1.54x | 1.54x → 1.54x | 1.69x → 1.18x | 1.69x → 1.18x | 1.4x |
| DeepSeek-V4-Flash-0731 | 46,225 | 4.62x | 6.85x → 2.55x | 4.19x → 8.27x | 6.20x → 4.56x | 2.7x |
| DeepSeek-V4-Flash-0731 | 92,450 | 5.52x | 8.26x → 3.05x | 4.46x → 9.93x | 6.68x → 5.50x | 2.7x |
| DeepSeek-V4-Flash-0731 | 138,675 | 5.33x | 8.11x → 2.94x | 4.30x → 9.70x | 6.54x → 5.36x | 2.8x |
| DeepSeek-V4-Flash-0731 | 184,900 | 5.18x | 8.01x → 2.86x | 4.17x → 9.45x | 6.45x → 5.21x | 2.8x |
| DeepSeek-V4-Flash-0731 | 277,350 | 4.93x | 7.85x → 2.70x | 3.96x → 9.01x | 6.31x → 4.95x | 2.9x |
| DeepSeek-V4-Flash-0731 | 369,800 | 4.71x | 7.72x → 2.57x | 3.78x → 8.62x | 6.20x → 4.71x | 3.0x |
| DeepSeek-V4-Flash-0731 | 554,700 | 4.33x | 7.48x → 2.35x | 3.48x → 7.95x | 6.01x → 4.31x | 3.2x |
| DeepSeek-V4-Pro-0813 | 58,680 | 1.49x | 1.49x → 1.49x | — | — | 1.0x |
| DeepSeek-V4-Pro-0813 | 60,310 | 1.73x | 1.73x → 1.73x | 1.64x → 1.51x | 1.64x → 1.51x | 1.1x |
| DeepSeek-V4-Pro-0813 | 61,940 | 1.72x | 1.72x → 1.72x | 1.63x → 1.51x | 1.63x → 1.51x | 1.1x |
| DeepSeek-V4-Pro-0813 | 92,450 | 4.74x | 6.17x → 3.03x | 4.00x → 7.91x | 5.20x → 5.05x | 2.0x |
| DeepSeek-V4-Pro-0813 | 138,675 | 4.60x | 6.04x → 2.92x | 3.86x → 7.74x | 5.07x → 4.92x | 2.1x |
| DeepSeek-V4-Pro-0813 | 184,900 | 4.49x | 5.95x → 2.84x | 3.76x → 7.60x | 4.98x → 4.81x | 2.1x |
| DeepSeek-V4-Pro-0813 | 277,350 | 4.33x | 5.84x → 2.73x | 3.61x → 7.37x | 4.87x → 4.64x | 2.1x |
| DeepSeek-V4-Pro-0813 | 369,800 | 4.21x | 5.77x → 2.64x | 3.51x → 7.18x | 4.81x → 4.50x | 2.2x |
| DeepSeek-V4-Pro-0813 | 554,700 | 4.01x | 5.66x → 2.48x | 3.33x → 6.85x | 4.71x → 4.24x | 2.3x |
| Qwen3-8B | 2,445 | 5.75x | 5.75x → 5.75x | 7.48x → 9.63x | 7.48x → 9.63x | 1.3x |
| Qwen3-8B | 3,260 | 5.85x | 5.85x → 5.85x | 7.71x → 5.17x | 7.71x → 5.17x | 1.5x |
| Qwen3-8B | 4,075 | 5.31x | 5.31x → 5.31x | — | — | 1.0x |
| Qwen3-8B | 5,705 | 4.27x | 4.27x → 4.27x | — | — | 1.0x |
| Qwen3-8B | 6,520 | 3.86x | 3.86x → 3.86x | — | — | 1.0x |
| Qwen3-8B | 46,225 | 3.66x | 5.73x → 1.93x | 3.18x → 7.71x | 4.97x → 4.06x | 3.0x |
| Qwen3-8B | 92,450 | 3.42x | 5.25x → 1.85x | 2.96x → 7.11x | 4.55x → 3.85x | 2.8x |
| Qwen3-8B | 138,675 | 3.04x | 4.63x → 1.69x | 2.61x → 6.45x | 3.97x → 3.58x | 2.7x |
| Qwen3-8B | 184,900 | 3.01x | 4.59x → 1.69x | 2.59x → 6.25x | 3.94x → 3.51x | 2.7x |
| Qwen3-8B | 277,350 | 2.99x | 4.72x → 1.67x | 2.56x → 6.11x | 4.04x → 3.41x | 2.8x |
| Qwen3-8B | 369,800 | 2.98x | 4.85x → 1.66x | 2.55x → 6.00x | 4.15x → 3.33x | 2.9x |
| Qwen3-8B | 554,700 | 2.88x | 4.97x → 1.59x | 2.46x → 5.67x | 4.24x → 3.12x | 3.1x |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 8 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 8 | Link us at domain 72 | tok/s at 8 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 4 | 6,400 | 208.16 | 208.16 | 1,261.5 | 1,261.5 |
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 208.41 | 208.41 | 1,656.8 | 1,656.8 |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 213.12 | 208.53 | 1,245.8 | 1,253.0 |
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 213.12 | 208.55 | 1,292.1 | 1,299.8 |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 217.78 | 208.62 | 1,145.6 | 1,157.7 |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 217.78 | 208.63 | 1,167.2 | 1,179.8 |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 222.45 | 208.67 | 1,064.0 | 1,079.9 |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 1,019.44 | 208.71 | 857.1 | 2,808.9 |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 1,020.88 | 1,003.85 | 866.4 | 879.4 |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 1,021.91 | 1,003.85 | 871.1 | 885.0 |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 1,022.80 | 1,010.90 | 876.0 | 885.2 |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 1,023.27 | 1,014.42 | 878.5 | 885.4 |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 1,023.76 | 1,016.53 | 881.1 | 886.8 |
| DeepSeek-V4-Pro-0813 | 22 | 35,200 | 1,465.86 | 298.36 | 450.9 | 952.3 |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 1,474.61 | 298.43 | 467.1 | 1,036.4 |
| DeepSeek-V4-Pro-0813 | 37 | 59,200 | 1,479.85 | 298.47 | 479.4 | 1,105.4 |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 1,479.85 | 298.48 | 480.7 | 1,112.6 |
| DeepSeek-V4-Pro-0813 | 39 | 62,400 | 1,479.85 | 298.48 | 482.0 | 1,119.6 |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 1,485.85 | 298.53 | 496.4 | 1,209.0 |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 1,487.72 | 298.53 | 497.3 | 1,216.9 |
| DeepSeek-V4-Pro-0813 | 60 | 96,000 | 1,487.72 | 298.53 | 498.5 | 1,224.4 |
| DeepSeek-V4-Pro-0813 | 68 | 108,800 | 1,489.18 | 298.54 | 502.5 | 1,250.9 |
| DeepSeek-V4-Pro-0813 | 84 | 134,400 | 1,491.30 | 1,449.02 | 508.4 | 519.5 |
| DeepSeek-V4-Pro-0813 | 86 | 137,600 | 1,491.30 | 1,449.02 | 509.0 | 520.2 |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 1,491.30 | 1,449.02 | 509.3 | 520.5 |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 1,493.84 | 1,449.02 | 515.6 | 527.8 |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 1,496.07 | 1,466.51 | 522.2 | 530.4 |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 1,497.22 | 1,475.25 | 525.7 | 531.8 |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 1,498.46 | 1,480.50 | 529.2 | 534.3 |
| Qwen3-8B | 2 | 3,200 | 173.78 | 173.78 | 660.1 | 660.1 |
| Qwen3-8B | 3 | 4,800 | 174.11 | 174.11 | 934.4 | 934.4 |
| Qwen3-8B | 4 | 6,400 | 174.27 | 174.27 | 1,179.5 | 1,179.5 |
| Qwen3-8B | 29 | 46,400 | 188.51 | 174.70 | 1,777.0 | 1,821.7 |
| Qwen3-8B | 58 | 92,800 | 207.17 | 174.73 | 1,720.0 | 1,821.6 |
| Qwen3-8B | 87 | 139,200 | 221.16 | 179.40 | 1,770.9 | 1,912.3 |
| Qwen3-8B | 116 | 185,600 | 239.81 | 179.40 | 1,692.0 | 1,884.6 |
| Qwen3-8B | 173 | 276,800 | 272.46 | 184.07 | 1,618.3 | 1,888.4 |
| Qwen3-8B | 231 | 369,600 | 305.11 | 188.73 | 1,547.4 | 1,887.3 |
| Qwen3-8B | 347 | 555,200 | 337.75 | 193.39 | 1,465.7 | 1,859.1 |

## The GPU's own topology choice, at batch 1

Every cluster size in the study, under each parallelism it can
actually run, at **per-user** rate. `pipeline` is what this study
charged the GPU before, at every size; `hybrid` is tensor-parallel
inside the NVLink domain and pipeline-parallel across it, which is
what a real deployment of this size runs. A blank cell is a topology
that collapses onto another at that size and is not emitted twice.

**This table is where the latency separation shows up most
plainly.** A pipeline column is now a machine cut into as many slots
as it has GPUs, and a token visits every one of them; the whole
cluster's HBM bandwidth is on that token's path only under `tensor`,
which is why a 672-GPU pipeline reads as fractions of a token per
second while the same silicon tensor-parallel reads in the hundreds.

| Model | GPUs | mm2 | Pipeline tok/s | Tensor tok/s | Hybrid tok/s | Best | Best link us | Link share | Binds on |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| DeepSeek-V4-Flash-0731 | 4 | 6,400 | 432.4 | 1,261.5 | — | tensor | 208.16 | 26.3% | weight_read |
| DeepSeek-V4-Flash-0731 | 7 | 11,200 | 368.3 | 1,656.8 | — | tensor | 208.41 | 34.5% | weight_read |
| DeepSeek-V4-Flash-0731 | 11 | 17,600 | 311.1 | 767.3 | 1,245.8 | hybrid | 213.12 | 26.6% | weight_read |
| DeepSeek-V4-Flash-0731 | 12 | 19,200 | 300.0 | 775.9 | 1,292.1 | hybrid | 213.12 | 27.5% | weight_read |
| DeepSeek-V4-Flash-0731 | 19 | 30,400 | 242.3 | 809.4 | 1,145.6 | hybrid | 217.78 | 24.9% | weight_read |
| DeepSeek-V4-Flash-0731 | 20 | 32,000 | 236.1 | 813.0 | 1,167.2 | hybrid | 217.78 | 25.4% | weight_read |
| DeepSeek-V4-Flash-0731 | 29 | 46,400 | 192.9 | 832.8 | 1,064.0 | hybrid | 222.45 | 23.7% | weight_read |
| DeepSeek-V4-Flash-0731 | 58 | 92,800 | 124.1 | 857.1 | 739.7 | tensor | 1,019.44 | 87.4% | link_latency |
| DeepSeek-V4-Flash-0731 | 87 | 139,200 | 92.3 | 866.4 | 615.6 | tensor | 1,020.88 | 88.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 116 | 185,600 | 73.6 | 871.1 | 492.8 | tensor | 1,021.91 | 89.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 173 | 276,800 | 52.8 | 876.0 | 368.2 | tensor | 1,022.80 | 89.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 231 | 369,600 | 41.0 | 878.5 | 293.9 | tensor | 1,023.27 | 89.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 347 | 555,200 | 28.3 | 881.1 | 205.0 | tensor | 1,023.76 | 90.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 22 | 35,200 | 61.4 | 450.9 | 394.5 | tensor | 1,465.86 | 66.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 29 | 46,400 | 52.7 | 467.1 | 340.5 | tensor | 1,474.61 | 68.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 37 | 59,200 | 45.5 | 479.4 | 303.7 | tensor | 1,479.85 | 70.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 38 | 60,800 | 44.7 | 480.7 | 306.4 | tensor | 1,479.85 | 71.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 39 | 62,400 | 44.0 | 482.0 | 309.1 | tensor | 1,479.85 | 71.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 89,600 | 34.6 | 496.4 | 253.5 | tensor | 1,485.85 | 73.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 58 | 92,800 | 33.7 | 497.3 | 226.2 | tensor | 1,487.72 | 74.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 60 | 96,000 | 32.9 | 498.5 | 228.3 | tensor | 1,487.72 | 74.2% | link_latency |
| DeepSeek-V4-Pro-0813 | 68 | 108,800 | 30.1 | 502.5 | 211.2 | tensor | 1,489.18 | 74.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 84 | 134,400 | 25.7 | 508.4 | 183.8 | tensor | 1,491.30 | 75.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 86 | 137,600 | 25.2 | 509.0 | 184.7 | tensor | 1,491.30 | 75.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 87 | 139,200 | 25.0 | 509.3 | 185.2 | tensor | 1,491.30 | 76.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 116 | 185,600 | 19.9 | 515.6 | 145.8 | tensor | 1,493.84 | 77.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 173 | 276,800 | 14.2 | 522.2 | 107.2 | tensor | 1,496.07 | 78.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 231 | 369,600 | 11.0 | 525.7 | 84.8 | tensor | 1,497.22 | 78.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 347 | 555,200 | 7.6 | 529.2 | 58.4 | tensor | 1,498.46 | 79.3% | link_latency |
| Qwen3-8B | 2 | 3,200 | 373.4 | 660.1 | — | tensor | 173.78 | 11.5% | weight_read |
| Qwen3-8B | 3 | 4,800 | 373.3 | 934.4 | — | tensor | 174.11 | 16.3% | weight_read |
| Qwen3-8B | 4 | 6,400 | 373.1 | 1,179.5 | — | tensor | 174.27 | 20.6% | weight_read |
| Qwen3-8B | 29 | 46,400 | 367.5 | 1,056.0 | 1,777.0 | hybrid | 188.51 | 33.5% | weight_read |
| Qwen3-8B | 58 | 92,800 | 365.9 | 1,104.5 | 1,720.0 | hybrid | 207.17 | 35.6% | weight_read |
| Qwen3-8B | 87 | 139,200 | 365.9 | 1,122.0 | 1,770.9 | hybrid | 221.16 | 39.2% | weight_read |
| Qwen3-8B | 116 | 185,600 | 365.9 | 1,130.7 | 1,692.0 | hybrid | 239.81 | 40.6% | weight_read |
| Qwen3-8B | 173 | 276,800 | 365.9 | 1,139.5 | 1,618.3 | hybrid | 272.46 | 44.1% | weight_read |
| Qwen3-8B | 231 | 369,600 | 365.9 | 1,144.0 | 1,547.4 | hybrid | 305.11 | 47.2% | link_latency |
| Qwen3-8B | 347 | 555,200 | 365.9 | 1,148.6 | 1,465.7 | hybrid | 337.75 | 49.5% | link_latency |

## Array or wafer: the crossover, reported rather than assumed

`Array viable to` is the per-user rate at which the topology's hops alone
consume 10% of the token budget; `hard ceiling` is the rate at which they
consume all of it. Below the first number the interconnect is a design
cost; above the second the topology cannot deliver the rate at all.

Each event is priced on the link it actually crosses and, for a
collective, on how many partitions it spans: an all-reduce costs
`traversals x hop latency` plus `(p-1)/p` of the payload each way, where
`traversals` is `2 lg p` in the fabric's own switch radix (Thakur,
Rabenseifner & Gropp 2005) or 1.1x the mesh diameter on a stitched
fabric (Rocki et al., SC20). `Events` spells the breakdown out.

| Design | Model | Devices | Parallelism | Intra link | Inter link | Hops/token | Link latency/token | Viable to (10% budget) | Hard ceiling | Events |
|---|---|---:|---|---|---|---:|---:|---:|---:|---|
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x3 | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 2.42 us | 41,353.0 tok/s | 413,530.0 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 2.42 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x3 | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 174.11 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-pipeline-x4 | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer_n5 | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 174.27 us |
| Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer_n5 | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us |
| Qwen3-8B/b200_sxm-x2-pipeline | Qwen3-8B | 2 | pipeline | nvlink5 | infiniband_ndr | 1 | 1.21 us | 82,706.0 tok/s | 827,059.9 tok/s | 1 x point_to_point span 2 on nvlink5 (traversals 1.0) = 1.21 us |
| Qwen3-8B/b200_sxm-x2-tensor | Qwen3-8B | 2 | tensor | nvlink5 | infiniband_ndr | 72 | 173.78 us | 575.4 tok/s | 5,754.3 tok/s | 72 x all_reduce span 2 on nvlink5 (traversals 2.0) = 173.78 us |
| Qwen3-8B/b200_sxm-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink5 | infiniband_ndr | 2 | 2.42 us | 41,353.0 tok/s | 413,530.0 tok/s | 2 x point_to_point span 2 on nvlink5 (traversals 1.0) = 2.42 us |
| Qwen3-8B/b200_sxm-x3-tensor | Qwen3-8B | 3 | tensor | nvlink5 | infiniband_ndr | 72 | 174.11 us | 574.3 tok/s | 5,743.5 tok/s | 72 x all_reduce span 3 on nvlink5 (traversals 2.0) = 174.11 us |
| Qwen3-8B/b200_sxm-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| Qwen3-8B/b200_sxm-x4-tensor | Qwen3-8B | 4 | tensor | nvlink5 | infiniband_ndr | 72 | 174.27 us | 573.8 tok/s | 5,738.1 tok/s | 72 x all_reduce span 4 on nvlink5 (traversals 2.0) = 174.27 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 44.22 us | 2,261.5 tok/s | 22,614.7 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 849.06 us | 117.8 tok/s | 1,177.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 674.54 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 188.51 us | 530.5 tok/s | 5,304.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 56.14 us | 1,781.3 tok/s | 17,813.4 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 853.49 us | 117.2 tok/s | 1,171.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 678.97 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 207.17 us | 482.7 tok/s | 4,827.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.65 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 56.14 us | 1,781.3 tok/s | 17,813.4 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 854.69 us | 117.0 tok/s | 1,170.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 680.17 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 221.16 us | 452.2 tok/s | 4,521.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.64 us |
| Qwen3-8B/b200_sxm-x116-pipeline | Qwen3-8B | 116 | pipeline | nvlink5 | infiniband_ndr | 35 | 56.14 us | 1,781.3 tok/s | 17,813.4 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x116-tensor | Qwen3-8B | 116 | tensor | nvlink5 | infiniband_ndr | 144 | 855.55 us | 116.9 tok/s | 1,168.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 681.03 us |
| Qwen3-8B/b200_sxm-x116-hybrid | Qwen3-8B | 116 | hybrid | nvlink5 | infiniband_ndr | 86 | 239.81 us | 417.0 tok/s | 4,169.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 65.29 us |
| Qwen3-8B/b200_sxm-x173-pipeline | Qwen3-8B | 173 | pipeline | nvlink5 | infiniband_ndr | 35 | 56.14 us | 1,781.3 tok/s | 17,813.4 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x173-tensor | Qwen3-8B | 173 | tensor | nvlink5 | infiniband_ndr | 144 | 856.30 us | 116.8 tok/s | 1,167.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 681.78 us |
| Qwen3-8B/b200_sxm-x173-hybrid | Qwen3-8B | 173 | hybrid | nvlink5 | infiniband_ndr | 93 | 272.46 us | 367.0 tok/s | 3,670.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 97.94 us |
| Qwen3-8B/b200_sxm-x231-pipeline | Qwen3-8B | 231 | pipeline | nvlink5 | infiniband_ndr | 35 | 56.14 us | 1,781.3 tok/s | 17,813.4 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x231-tensor | Qwen3-8B | 231 | tensor | nvlink5 | infiniband_ndr | 144 | 856.69 us | 116.7 tok/s | 1,167.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 682.17 us |
| Qwen3-8B/b200_sxm-x231-hybrid | Qwen3-8B | 231 | hybrid | nvlink5 | infiniband_ndr | 100 | 305.11 us | 327.8 tok/s | 3,277.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 130.59 us |
| Qwen3-8B/b200_sxm-x347-pipeline | Qwen3-8B | 347 | pipeline | nvlink5 | infiniband_ndr | 35 | 56.14 us | 1,781.3 tok/s | 17,813.4 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 18.66 us |
| Qwen3-8B/b200_sxm-x347-tensor | Qwen3-8B | 347 | tensor | nvlink5 | infiniband_ndr | 144 | 857.11 us | 116.7 tok/s | 1,166.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 682.59 us |
| Qwen3-8B/b200_sxm-x347-hybrid | Qwen3-8B | 347 | hybrid | nvlink5 | infiniband_ndr | 107 | 337.75 us | 296.1 tok/s | 2,960.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 163.23 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-pipeline-x14 | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 19.17 us | 5,215.6 tok/s | 52,156.5 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.51 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-tensor-x14 | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5 | infiniband_ndr | 172 | 1,003.59 us | 99.6 tok/s | 996.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-SRAMKV-array-hybrid-x14 | DeepSeek-V4-Flash-0731 | 14 | hybrid | nvlink5 | infiniband_ndr | 87 | 213.12 us | 469.2 tok/s | 4,692.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x14 | DeepSeek-V4-Flash-0731 | 14 | pipeline | nvlink5 | infiniband_ndr | 13 | 19.17 us | 5,215.6 tok/s | 52,156.5 tok/s | 12 x point_to_point span 2 on nvlink5 (traversals 1.0) = 14.51 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer_n5 | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-tensor-x14 | DeepSeek-V4-Flash-0731 | 14 | tensor | nvlink5 | infiniband_ndr | 172 | 1,003.59 us | 99.6 tok/s | 996.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer_n5 | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x14 | DeepSeek-V4-Flash-0731 | 14 | hybrid | nvlink5 | infiniband_ndr | 87 | 213.12 us | 469.2 tok/s | 4,692.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x4-pipeline | DeepSeek-V4-Flash-0731 | 4 | pipeline | nvlink5 | infiniband_ndr | 3 | 3.63 us | 27,568.7 tok/s | 275,686.6 tok/s | 3 x point_to_point span 2 on nvlink5 (traversals 1.0) = 3.63 us |
| DSV4-Flash/b200_sxm-x4-tensor | DeepSeek-V4-Flash-0731 | 4 | tensor | nvlink5 | infiniband_ndr | 86 | 208.16 us | 480.4 tok/s | 4,804.0 tok/s | 86 x all_reduce span 4 on nvlink5 (traversals 2.0) = 208.16 us |
| DSV4-Flash/b200_sxm-x7-pipeline | DeepSeek-V4-Flash-0731 | 7 | pipeline | nvlink5 | infiniband_ndr | 6 | 7.25 us | 13,784.3 tok/s | 137,843.3 tok/s | 6 x point_to_point span 2 on nvlink5 (traversals 1.0) = 7.25 us |
| DSV4-Flash/b200_sxm-x7-tensor | DeepSeek-V4-Flash-0731 | 7 | tensor | nvlink5 | infiniband_ndr | 86 | 208.41 us | 479.8 tok/s | 4,798.2 tok/s | 86 x all_reduce span 7 on nvlink5 (traversals 2.0) = 208.41 us |
| DSV4-Flash/b200_sxm-x11-pipeline | DeepSeek-V4-Flash-0731 | 11 | pipeline | nvlink5 | infiniband_ndr | 10 | 15.55 us | 6,432.6 tok/s | 64,326.2 tok/s | 9 x point_to_point span 2 on nvlink5 (traversals 1.0) = 10.88 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x11-tensor | DeepSeek-V4-Flash-0731 | 11 | tensor | nvlink5 | infiniband_ndr | 172 | 1,003.59 us | 99.6 tok/s | 996.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/b200_sxm-x11-hybrid | DeepSeek-V4-Flash-0731 | 11 | hybrid | nvlink5 | infiniband_ndr | 87 | 213.12 us | 469.2 tok/s | 4,692.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x12-pipeline | DeepSeek-V4-Flash-0731 | 12 | pipeline | nvlink5 | infiniband_ndr | 11 | 16.75 us | 5,968.4 tok/s | 59,684.2 tok/s | 10 x point_to_point span 2 on nvlink5 (traversals 1.0) = 12.09 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x12-tensor | DeepSeek-V4-Flash-0731 | 12 | tensor | nvlink5 | infiniband_ndr | 172 | 1,003.59 us | 99.6 tok/s | 996.4 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 795.14 us |
| DSV4-Flash/b200_sxm-x12-hybrid | DeepSeek-V4-Flash-0731 | 12 | hybrid | nvlink5 | infiniband_ndr | 87 | 213.12 us | 469.2 tok/s | 4,692.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.66 us |
| DSV4-Flash/b200_sxm-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink5 | infiniband_ndr | 18 | 28.67 us | 3,487.6 tok/s | 34,875.6 tok/s | 16 x point_to_point span 2 on nvlink5 (traversals 1.0) = 19.35 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink5 | infiniband_ndr | 172 | 1,010.64 us | 98.9 tok/s | 989.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 802.18 us |
| DSV4-Flash/b200_sxm-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink5 | infiniband_ndr | 88 | 217.78 us | 459.2 tok/s | 4,591.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x20-pipeline | DeepSeek-V4-Flash-0731 | 20 | pipeline | nvlink5 | infiniband_ndr | 19 | 29.88 us | 3,346.4 tok/s | 33,464.5 tok/s | 17 x point_to_point span 2 on nvlink5 (traversals 1.0) = 20.55 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x20-tensor | DeepSeek-V4-Flash-0731 | 20 | tensor | nvlink5 | infiniband_ndr | 172 | 1,010.64 us | 98.9 tok/s | 989.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 802.18 us |
| DSV4-Flash/b200_sxm-x20-hybrid | DeepSeek-V4-Flash-0731 | 20 | hybrid | nvlink5 | infiniband_ndr | 88 | 217.78 us | 459.2 tok/s | 4,591.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.33 us |
| DSV4-Flash/b200_sxm-x29-pipeline | DeepSeek-V4-Flash-0731 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 44.22 us | 2,261.5 tok/s | 22,614.7 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| DSV4-Flash/b200_sxm-x29-tensor | DeepSeek-V4-Flash-0731 | 29 | tensor | nvlink5 | infiniband_ndr | 172 | 1,014.16 us | 98.6 tok/s | 986.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 805.70 us |
| DSV4-Flash/b200_sxm-x29-hybrid | DeepSeek-V4-Flash-0731 | 29 | hybrid | nvlink5 | infiniband_ndr | 89 | 222.45 us | 449.5 tok/s | 4,495.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 13.99 us |
| DSV4-Flash/b200_sxm-x58-pipeline | DeepSeek-V4-Flash-0731 | 58 | pipeline | nvlink5 | infiniband_ndr | 42 | 68.06 us | 1,469.4 tok/s | 14,693.8 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x58-tensor | DeepSeek-V4-Flash-0731 | 58 | tensor | nvlink5 | infiniband_ndr | 172 | 1,019.44 us | 98.1 tok/s | 980.9 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 810.99 us |
| DSV4-Flash/b200_sxm-x58-hybrid | DeepSeek-V4-Flash-0731 | 58 | hybrid | nvlink5 | infiniband_ndr | 93 | 241.10 us | 414.8 tok/s | 4,147.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.65 us |
| DSV4-Flash/b200_sxm-x87-pipeline | DeepSeek-V4-Flash-0731 | 87 | pipeline | nvlink5 | infiniband_ndr | 42 | 68.06 us | 1,469.4 tok/s | 14,693.8 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x87-tensor | DeepSeek-V4-Flash-0731 | 87 | tensor | nvlink5 | infiniband_ndr | 172 | 1,020.88 us | 98.0 tok/s | 979.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 812.43 us |
| DSV4-Flash/b200_sxm-x87-hybrid | DeepSeek-V4-Flash-0731 | 87 | hybrid | nvlink5 | infiniband_ndr | 96 | 255.09 us | 392.0 tok/s | 3,920.1 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.64 us |
| DSV4-Flash/b200_sxm-x116-pipeline | DeepSeek-V4-Flash-0731 | 116 | pipeline | nvlink5 | infiniband_ndr | 42 | 68.06 us | 1,469.4 tok/s | 14,693.8 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x116-tensor | DeepSeek-V4-Flash-0731 | 116 | tensor | nvlink5 | infiniband_ndr | 172 | 1,021.91 us | 97.9 tok/s | 978.6 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 813.45 us |
| DSV4-Flash/b200_sxm-x116-hybrid | DeepSeek-V4-Flash-0731 | 116 | hybrid | nvlink5 | infiniband_ndr | 100 | 273.75 us | 365.3 tok/s | 3,653.0 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 65.29 us |
| DSV4-Flash/b200_sxm-x173-pipeline | DeepSeek-V4-Flash-0731 | 173 | pipeline | nvlink5 | infiniband_ndr | 42 | 68.06 us | 1,469.4 tok/s | 14,693.8 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x173-tensor | DeepSeek-V4-Flash-0731 | 173 | tensor | nvlink5 | infiniband_ndr | 172 | 1,022.80 us | 97.8 tok/s | 977.7 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 814.35 us |
| DSV4-Flash/b200_sxm-x173-hybrid | DeepSeek-V4-Flash-0731 | 173 | hybrid | nvlink5 | infiniband_ndr | 107 | 306.40 us | 326.4 tok/s | 3,263.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 97.94 us |
| DSV4-Flash/b200_sxm-x231-pipeline | DeepSeek-V4-Flash-0731 | 231 | pipeline | nvlink5 | infiniband_ndr | 42 | 68.06 us | 1,469.4 tok/s | 14,693.8 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x231-tensor | DeepSeek-V4-Flash-0731 | 231 | tensor | nvlink5 | infiniband_ndr | 172 | 1,023.27 us | 97.7 tok/s | 977.3 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 814.81 us |
| DSV4-Flash/b200_sxm-x231-hybrid | DeepSeek-V4-Flash-0731 | 231 | hybrid | nvlink5 | infiniband_ndr | 114 | 339.04 us | 294.9 tok/s | 2,949.5 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 130.59 us |
| DSV4-Flash/b200_sxm-x347-pipeline | DeepSeek-V4-Flash-0731 | 347 | pipeline | nvlink5 | infiniband_ndr | 42 | 68.06 us | 1,469.4 tok/s | 14,693.8 tok/s | 37 x point_to_point span 2 on nvlink5 (traversals 1.0) = 44.74 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 23.32 us |
| DSV4-Flash/b200_sxm-x347-tensor | DeepSeek-V4-Flash-0731 | 347 | tensor | nvlink5 | infiniband_ndr | 172 | 1,023.76 us | 97.7 tok/s | 976.8 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 86 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 815.31 us |
| DSV4-Flash/b200_sxm-x347-hybrid | DeepSeek-V4-Flash-0731 | 347 | hybrid | nvlink5 | infiniband_ndr | 128 | 404.34 us | 247.3 tok/s | 2,473.2 tok/s | 86 x all_reduce span 8 on nvlink5 (traversals 2.0) = 208.45 us; 42 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 195.88 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-pipeline-x74 | DeepSeek-V4-Pro-0813 | 74 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer_n5 | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-tensor-x72 | DeepSeek-V4-Pro-0813 | 72 | tensor | nvlink5 | infiniband_ndr | 244 | 1,489.18 us | 67.2 tok/s | 671.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 1,191.28 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer_n5 | inter_wafer | 244 | 1,472.34 us | 67.9 tok/s | 679.2 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 2 on inter_wafer (traversals 2.0) = 1,237.49 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-array-hybrid-x74 | DeepSeek-V4-Pro-0813 | 74 | hybrid | nvlink5 | infiniband_ndr | 131 | 340.98 us | 293.3 tok/s | 2,932.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 43.08 us |
| DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Pro-0813 | 2 | hybrid | on_wafer_n5 | inter_wafer | 123 | 239.95 us | 416.8 tok/s | 4,167.6 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-pipeline-x76 | DeepSeek-V4-Pro-0813 | 76 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3 | DeepSeek-V4-Pro-0813 | 3 | pipeline | on_wafer_n5 | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-tensor-x74 | DeepSeek-V4-Pro-0813 | 74 | tensor | nvlink5 | infiniband_ndr | 244 | 1,490.35 us | 67.1 tok/s | 671.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 10 on infiniband_ndr (traversals 2.0) = 1,192.45 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-tensor-x3 | DeepSeek-V4-Pro-0813 | 3 | tensor | on_wafer_n5 | inter_wafer | 244 | 1,478.17 us | 67.7 tok/s | 676.5 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 122 x all_reduce span 3 on inter_wafer (traversals 2.0) = 1,243.32 us |
| DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x76 | DeepSeek-V4-Pro-0813 | 76 | hybrid | nvlink5 | infiniband_ndr | 131 | 340.98 us | 293.3 tok/s | 2,932.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 9 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 43.08 us |
| DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | DeepSeek-V4-Pro-0813 | 3 | hybrid | on_wafer_n5 | inter_wafer | 124 | 245.04 us | 408.1 tok/s | 4,080.9 tok/s | 122 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 234.85 us; 2 x point_to_point span 2 on inter_wafer (traversals 1.0) = 10.19 us |
| DSV4-Pro/b200_sxm-x22-pipeline | DeepSeek-V4-Pro-0813 | 22 | pipeline | nvlink5 | infiniband_ndr | 21 | 32.68 us | 3,060.3 tok/s | 30,603.4 tok/s | 19 x point_to_point span 2 on nvlink5 (traversals 1.0) = 23.10 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.57 us |
| DSV4-Pro/b200_sxm-x22-tensor | DeepSeek-V4-Pro-0813 | 22 | tensor | nvlink5 | infiniband_ndr | 244 | 1,465.86 us | 68.2 tok/s | 682.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 1,167.96 us |
| DSV4-Pro/b200_sxm-x22-hybrid | DeepSeek-V4-Pro-0813 | 22 | hybrid | nvlink5 | infiniband_ndr | 124 | 307.47 us | 325.2 tok/s | 3,252.3 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 9.57 us |
| DSV4-Pro/b200_sxm-x29-pipeline | DeepSeek-V4-Pro-0813 | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 44.76 us | 2,234.2 tok/s | 22,342.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.40 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 14.36 us |
| DSV4-Pro/b200_sxm-x29-tensor | DeepSeek-V4-Pro-0813 | 29 | tensor | nvlink5 | infiniband_ndr | 244 | 1,474.61 us | 67.8 tok/s | 678.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 1,176.70 us |
| DSV4-Pro/b200_sxm-x29-hybrid | DeepSeek-V4-Pro-0813 | 29 | hybrid | nvlink5 | infiniband_ndr | 125 | 312.26 us | 320.2 tok/s | 3,202.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 14.36 us |
| DSV4-Pro/b200_sxm-x37-pipeline | DeepSeek-V4-Pro-0813 | 37 | pipeline | nvlink5 | infiniband_ndr | 36 | 58.06 us | 1,722.5 tok/s | 17,224.6 tok/s | 32 x point_to_point span 2 on nvlink5 (traversals 1.0) = 38.91 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x37-tensor | DeepSeek-V4-Pro-0813 | 37 | tensor | nvlink5 | infiniband_ndr | 244 | 1,479.85 us | 67.6 tok/s | 675.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 1,181.95 us |
| DSV4-Pro/b200_sxm-x37-hybrid | DeepSeek-V4-Pro-0813 | 37 | hybrid | nvlink5 | infiniband_ndr | 126 | 317.05 us | 315.4 tok/s | 3,154.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x38-pipeline | DeepSeek-V4-Pro-0813 | 38 | pipeline | nvlink5 | infiniband_ndr | 37 | 59.27 us | 1,687.1 tok/s | 16,871.2 tok/s | 33 x point_to_point span 2 on nvlink5 (traversals 1.0) = 40.13 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x38-tensor | DeepSeek-V4-Pro-0813 | 38 | tensor | nvlink5 | infiniband_ndr | 244 | 1,479.85 us | 67.6 tok/s | 675.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 1,181.95 us |
| DSV4-Pro/b200_sxm-x38-hybrid | DeepSeek-V4-Pro-0813 | 38 | hybrid | nvlink5 | infiniband_ndr | 126 | 317.05 us | 315.4 tok/s | 3,154.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x39-pipeline | DeepSeek-V4-Pro-0813 | 39 | pipeline | nvlink5 | infiniband_ndr | 38 | 60.49 us | 1,653.2 tok/s | 16,532.1 tok/s | 34 x point_to_point span 2 on nvlink5 (traversals 1.0) = 41.34 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x39-tensor | DeepSeek-V4-Pro-0813 | 39 | tensor | nvlink5 | infiniband_ndr | 244 | 1,479.85 us | 67.6 tok/s | 675.7 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 1,181.95 us |
| DSV4-Pro/b200_sxm-x39-hybrid | DeepSeek-V4-Pro-0813 | 39 | hybrid | nvlink5 | infiniband_ndr | 126 | 317.05 us | 315.4 tok/s | 3,154.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 19.15 us |
| DSV4-Pro/b200_sxm-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink5 | infiniband_ndr | 55 | 88.30 us | 1,132.5 tok/s | 11,324.9 tok/s | 49 x point_to_point span 2 on nvlink5 (traversals 1.0) = 59.58 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 28.72 us |
| DSV4-Pro/b200_sxm-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink5 | infiniband_ndr | 244 | 1,485.85 us | 67.3 tok/s | 673.0 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 7 on infiniband_ndr (traversals 2.0) = 1,187.95 us |
| DSV4-Pro/b200_sxm-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink5 | infiniband_ndr | 128 | 326.62 us | 306.2 tok/s | 3,061.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 6 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 28.72 us |
| DSV4-Pro/b200_sxm-x58-pipeline | DeepSeek-V4-Pro-0813 | 58 | pipeline | nvlink5 | infiniband_ndr | 57 | 94.30 us | 1,060.4 tok/s | 10,604.1 tok/s | 50 x point_to_point span 2 on nvlink5 (traversals 1.0) = 60.80 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x58-tensor | DeepSeek-V4-Pro-0813 | 58 | tensor | nvlink5 | infiniband_ndr | 244 | 1,487.72 us | 67.2 tok/s | 672.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 1,189.82 us |
| DSV4-Pro/b200_sxm-x58-hybrid | DeepSeek-V4-Pro-0813 | 58 | hybrid | nvlink5 | infiniband_ndr | 129 | 331.41 us | 301.7 tok/s | 3,017.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x60-pipeline | DeepSeek-V4-Pro-0813 | 60 | pipeline | nvlink5 | infiniband_ndr | 59 | 96.74 us | 1,033.7 tok/s | 10,337.5 tok/s | 52 x point_to_point span 2 on nvlink5 (traversals 1.0) = 63.23 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x60-tensor | DeepSeek-V4-Pro-0813 | 60 | tensor | nvlink5 | infiniband_ndr | 244 | 1,487.72 us | 67.2 tok/s | 672.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 1,189.82 us |
| DSV4-Pro/b200_sxm-x60-hybrid | DeepSeek-V4-Pro-0813 | 60 | hybrid | nvlink5 | infiniband_ndr | 129 | 331.41 us | 301.7 tok/s | 3,017.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x68-pipeline | DeepSeek-V4-Pro-0813 | 68 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x68-tensor | DeepSeek-V4-Pro-0813 | 68 | tensor | nvlink5 | infiniband_ndr | 244 | 1,489.18 us | 67.2 tok/s | 671.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 1,191.28 us |
| DSV4-Pro/b200_sxm-x68-hybrid | DeepSeek-V4-Pro-0813 | 68 | hybrid | nvlink5 | infiniband_ndr | 130 | 336.19 us | 297.4 tok/s | 2,974.5 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 38.29 us |
| DSV4-Pro/b200_sxm-x84-pipeline | DeepSeek-V4-Pro-0813 | 84 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x84-tensor | DeepSeek-V4-Pro-0813 | 84 | tensor | nvlink5 | infiniband_ndr | 244 | 1,491.30 us | 67.1 tok/s | 670.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 1,193.40 us |
| DSV4-Pro/b200_sxm-x84-hybrid | DeepSeek-V4-Pro-0813 | 84 | hybrid | nvlink5 | infiniband_ndr | 132 | 345.77 us | 289.2 tok/s | 2,892.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.87 us |
| DSV4-Pro/b200_sxm-x86-pipeline | DeepSeek-V4-Pro-0813 | 86 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x86-tensor | DeepSeek-V4-Pro-0813 | 86 | tensor | nvlink5 | infiniband_ndr | 244 | 1,491.30 us | 67.1 tok/s | 670.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 1,193.40 us |
| DSV4-Pro/b200_sxm-x86-hybrid | DeepSeek-V4-Pro-0813 | 86 | hybrid | nvlink5 | infiniband_ndr | 132 | 345.77 us | 289.2 tok/s | 2,892.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.87 us |
| DSV4-Pro/b200_sxm-x87-pipeline | DeepSeek-V4-Pro-0813 | 87 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x87-tensor | DeepSeek-V4-Pro-0813 | 87 | tensor | nvlink5 | infiniband_ndr | 244 | 1,491.30 us | 67.1 tok/s | 670.6 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 1,193.40 us |
| DSV4-Pro/b200_sxm-x87-hybrid | DeepSeek-V4-Pro-0813 | 87 | hybrid | nvlink5 | infiniband_ndr | 132 | 345.77 us | 289.2 tok/s | 2,892.1 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 47.87 us |
| DSV4-Pro/b200_sxm-x116-pipeline | DeepSeek-V4-Pro-0813 | 116 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x116-tensor | DeepSeek-V4-Pro-0813 | 116 | tensor | nvlink5 | infiniband_ndr | 244 | 1,493.84 us | 66.9 tok/s | 669.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 1,195.94 us |
| DSV4-Pro/b200_sxm-x116-hybrid | DeepSeek-V4-Pro-0813 | 116 | hybrid | nvlink5 | infiniband_ndr | 136 | 364.92 us | 274.0 tok/s | 2,740.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 67.01 us |
| DSV4-Pro/b200_sxm-x173-pipeline | DeepSeek-V4-Pro-0813 | 173 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x173-tensor | DeepSeek-V4-Pro-0813 | 173 | tensor | nvlink5 | infiniband_ndr | 244 | 1,496.07 us | 66.8 tok/s | 668.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 1,198.17 us |
| DSV4-Pro/b200_sxm-x173-hybrid | DeepSeek-V4-Pro-0813 | 173 | hybrid | nvlink5 | infiniband_ndr | 143 | 398.42 us | 251.0 tok/s | 2,509.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 100.52 us |
| DSV4-Pro/b200_sxm-x231-pipeline | DeepSeek-V4-Pro-0813 | 231 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x231-tensor | DeepSeek-V4-Pro-0813 | 231 | tensor | nvlink5 | infiniband_ndr | 244 | 1,497.22 us | 66.8 tok/s | 667.9 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 1,199.32 us |
| DSV4-Pro/b200_sxm-x231-hybrid | DeepSeek-V4-Pro-0813 | 231 | hybrid | nvlink5 | infiniband_ndr | 150 | 431.93 us | 231.5 tok/s | 2,315.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 134.03 us |
| DSV4-Pro/b200_sxm-x347-pipeline | DeepSeek-V4-Pro-0813 | 347 | pipeline | nvlink5 | infiniband_ndr | 60 | 97.95 us | 1,020.9 tok/s | 10,209.2 tok/s | 53 x point_to_point span 2 on nvlink5 (traversals 1.0) = 64.44 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 33.51 us |
| DSV4-Pro/b200_sxm-x347-tensor | DeepSeek-V4-Pro-0813 | 347 | tensor | nvlink5 | infiniband_ndr | 244 | 1,498.46 us | 66.7 tok/s | 667.4 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 122 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 1,200.55 us |
| DSV4-Pro/b200_sxm-x347-hybrid | DeepSeek-V4-Pro-0813 | 347 | hybrid | nvlink5 | infiniband_ndr | 165 | 503.73 us | 198.5 tok/s | 1,985.2 tok/s | 122 x all_reduce span 8 on nvlink5 (traversals 2.0) = 297.90 us; 43 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 205.83 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,505.3 | 0.141 | 4,964.8 (4,075) | 6,505.3 (46,225) | 1.31x | link_latency |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 5,369.8 | 0.058 | 3,830.7 (6,520) | 5,369.8 (92,450) | 1.40x | link_latency |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,912.5 | 0.035 | 2,911.6 (6,520) | 4,912.5 (138,675) | 1.69x | link_latency |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 4,570.8 | 0.016 | 2,422.5 (6,520) | 4,570.8 (277,350) | 1.89x | link_latency |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,942.2 | 0.011 | 1,233.0 (6,520) | 3,942.2 (369,800) | 3.20x | link_latency |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,344.6 | 0.006 | 627.0 (6,520) | 3,344.6 (554,700) | 5.33x | link_latency |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,509.3 | 0.005 | 313.7 (6,520) | 2,509.3 (554,700) | 8.00x | link_latency |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,004.3 | 0.002 | 78.5 (6,520) | 1,004.3 (554,700) | 12.80x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | array | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 4,915.5 | 0.106 | 2,545.1 (11,410) | 4,915.5 (46,225) | 1.93x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,914.2 | 0.106 | 2,531.4 (11,410) | 4,914.2 (46,225) | 1.94x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,762.6 | 0.103 | 1,755.9 (11,410) | 4,762.6 (46,225) | 2.71x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | array | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,565.2 | 0.049 | 1,088.8 (11,410) | 4,565.2 (92,450) | 4.19x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,214.4 | 0.030 | 710.8 (11,410) | 4,214.4 (138,675) | 5.93x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,950.1 | 0.014 | 359.0 (11,410) | 3,950.1 (277,350) | 11.00x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,442.4 | 0.009 | 180.4 (11,410) | 3,442.4 (369,800) | 19.08x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | wafer | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,227.4 | 0.004 | 45.3 (11,410) | 2,227.4 (554,700) | 49.18x | link_latency |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,359.5 | 0.026 | 829.7 (60,310) | 2,359.5 (92,450) | 2.84x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,342.8 | 0.017 | 829.7 (61,940) | 2,342.8 (138,675) | 2.82x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,342.5 | 0.017 | 829.7 (61,940) | 2,342.5 (138,675) | 2.82x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 2,282.8 | 0.016 | 829.7 (61,940) | 2,282.8 (138,675) | 2.75x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 2,203.5 | 0.008 | 631.4 (61,940) | 2,203.5 (277,350) | 3.49x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,060.3 | 0.004 | 354.5 (61,940) | 2,060.3 (554,700) | 5.81x | link_latency |
| DeepSeek-V4-Pro-0813 | 64 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,499.0 | 0.003 | 188.9 (61,940) | 1,499.0 (554,700) | 7.94x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | wafer | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 568.9 | 0.001 | 50.7 (61,940) | 568.9 (554,700) | 11.21x | kv_read |

## The two ROM floorplans on one die

Both machines hold the same 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 168.6 mm2 | 269.8 mm2 |
| compute block | 499.7 mm2 | 16.3 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 382.2 mm2 |
| sustained fp8 compute roof | 3.737e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.868e+14 | n/a |
| weight bytes/s the array supplies | 4.589e+13 | 4.589e+13 |
| **can the compute block be fed?** | **0.25x** | there is nothing to feed |
| full-array sweep | 76.55 us | 76.55 us |

**The sweep is identical.** Both the capacity density and the
read-bandwidth density scale as one over bitcell area, so a larger
compute-in-ROM cell holds proportionally fewer bits AND delivers
proportionally fewer bytes per second: the cell size cancels in
their ratio. What the larger cell costs is capacity -- the same
weights need a bigger array, and that silicon comes out of the SRAM
beside it. An earlier version of this model applied the multiplier
to area alone and credited the result with the storage cell's
bandwidth density, which handed compute-in-ROM a free 1.6x on throughput.

What compute-in-ROM does buy on this die is that it has no MAC
array to starve: the storage machine's 500 mm2 of MAC array can be fed at only 0.25x of what it
wants at one weight byte per multiply-accumulate, so more than half
the die runs at a fraction of its duty and the step is weight-bound
anyway.

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 44.2 mm2 | 0.88 mm2 (2.0%) | 11,303 mm2 | 226 mm2 | 12,816 mm2 = 15.7 reticles |
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 164.4 mm2 | 3.29 mm2 (2.0%) | 63,134 mm2 | 1,263 mm2 | 68,561 mm2 = 84.1 reticles |

## The batch-amortisation fork, reported rather than resolved

`docs/ISO_AREA_COMPARISON_AND_THE_TAALAS_ANCHOR.md` names an open
question the anchor cannot settle. If a ROM cell both stores its bits
and performs the multiply for them -- compute-in-ROM, as Taalas
describes HC1 -- then a second concurrent stream needs a second pass
through the fabric, and **aggregate per-die throughput equals per-user
throughput at every batch**. If instead the ROM is storage feeding a
separate MAC array, one sweep serves the whole batch exactly as one HBM
fetch does on a GPU. The two are *identical at batch 1*, which is
precisely why the published 16,960 tok/s figure cannot distinguish
them, and why it must not be used to justify a high-batch claim.

Every other table in this report uses the batched (ROM-as-storage)
machine; `-perstream` is compute-in-ROM with a global activation broadcast and `-perregion` gives each expert region its own port
variant.

The third column set is the per-region machine, which is the whole
subject of `docs/PER_REGION_COMPUTE_IN_ROM_DESIGN.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| Qwen3-8B | 1 | sram | 13,032.3 | 13,032.3 | 13,032.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 13,032.3 | 13,032.3 | 13,032.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 14,458.1 | 13,032.3 | 13,032.3 | 1.11x | 1.00x | link_latency | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 25,017.0 | 13,032.3 | 13,032.3 | 1.92x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 39,004.8 | 13,032.3 | 13,032.3 | 2.99x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 63,873.1 | 13,032.3 | 13,032.3 | 4.90x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 93,743.6 | 13,035.7 | 13,035.7 | 7.19x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 207,628.8 | 13,056.0 | 13,056.0 | 15.90x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 1 | rom | 325,147.9 | 30,090.7 | 30,090.7 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 325,147.9 | 30,090.7 | 30,090.7 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 325,147.9 | 30,090.7 | 30,090.7 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 325,147.9 | 30,090.7 | 30,090.7 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 325,147.9 | 30,090.7 | 30,090.7 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 325,147.9 | 30,090.7 | 30,090.7 | 10.81x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 325,147.9 | 30,108.5 | 30,108.5 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 325,147.9 | 30,217.4 | 30,217.4 | 10.76x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 13,018.3 | 13,018.3 | 13,018.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 13,018.3 | 13,018.3 | 13,018.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 15,887.2 | 13,018.3 | 13,533.3 | 1.22x | 1.04x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | sram | 31,774.4 | 13,018.3 | 23,630.2 | 2.44x | 1.82x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 50,920.7 | 13,018.3 | 40,408.9 | 3.91x | 3.10x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 91,112.4 | 13,018.3 | 66,193.5 | 7.00x | 5.08x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 144,557.7 | 13,023.2 | 102,958.0 | 11.10x | 7.91x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 354,458.4 | 13,052.9 | 117,176.6 | 27.16x | 8.98x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 378,837.5 | 36,893.4 | 36,893.4 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 378,837.5 | 36,893.4 | 36,893.4 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 378,837.5 | 36,893.4 | 36,893.4 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 378,837.5 | 36,893.4 | 36,893.4 | 10.27x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 378,837.5 | 36,893.4 | 50,920.7 | 10.27x | 1.38x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | rom | 378,837.5 | 36,893.4 | 70,608.1 | 10.27x | 1.91x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 378,837.5 | 36,932.4 | 87,528.5 | 10.26x | 2.37x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 570,217.3 | 37,172.5 | 166,276.1 | 15.34x | 4.47x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 11,751.3 | 11,735.4 | 11,735.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 11,751.3 | 11,735.4 | 11,735.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 11,751.3 | 11,735.4 | 11,735.4 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 15,555.6 | 11,735.4 | 14,197.3 | 1.33x | 1.21x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 26,447.2 | 11,735.4 | 23,382.3 | 2.25x | 1.99x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 40,686.6 | 11,735.4 | 32,771.3 | 3.47x | 2.79x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 66,018.8 | 11,735.4 | 37,773.0 | 5.63x | 3.22x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 145,646.4 | 11,742.4 | 66,116.9 | 12.40x | 5.63x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 71,213.5 | 24,997.2 | 24,997.2 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 71,213.5 | 24,997.2 | 24,997.2 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 71,213.5 | 24,997.2 | 24,997.2 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 71,213.5 | 24,997.2 | 24,997.2 | 2.85x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 71,213.5 | 24,997.2 | 30,008.7 | 2.85x | 1.20x | weight_read | weight_read | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | rom | 71,213.5 | 24,997.2 | 39,862.4 | 2.85x | 1.59x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 95,935.0 | 24,997.2 | 47,692.6 | 3.84x | 1.91x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 145,646.4 | 25,005.4 | 78,076.6 | 5.82x | 3.12x | kv_read | weight_read | weight_read |

## The floorplan sweep: where the recovered silicon goes

Compute-in-ROM has no MAC array, so it recovers that silicon.
What it is spent on decides the comparison, so it is swept
rather than assumed, and **the same sweep is offered to the
amortising machine** -- offering it to one side only would move
the artefact rather than remove it.

* `sram` sizes the array to the stored bytes. Compute-in-ROM's
  spare silicon becomes KV store, which is the split Taalas
  describes; the amortising machine's becomes MAC array.
* `rom` grows the array into that silicon as **replicated copies
  of the same weights**. R copies carry R sets of bitlines and
  sense amps, so R disjoint slices of the weight set are read at
  once and the sweep time falls by R. On the amortising machine
  the MAC array is then sized to consume exactly what the array
  can read, at one weight byte per multiply-accumulate -- a
  derived split, not a swept one.

`R` is the replication factor the design ended up with, which is
`weight_capacity / stored`. **Areas differ down this table**, so
read `tok/s/mm2` and not only aggregate: a design is allowed to
buy throughput with silicon here, and the iso-area table above is
where that is controlled for.

| Model | B | Amortisation | Spare | Design | mm2 | R | Sweeps | Aggregate | tok/s/mm2 | Binds on | vs ROM+MAC/sram |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---:|
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 24.95x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 24.95x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.00x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 2.31x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 14,458.1 | 0.313 | link_latency | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 22.49x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.90x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 2.08x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.90x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 2.08x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 25,017.0 | 0.271 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 13.00x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.52x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 1.20x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.52x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 1.20x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 39,004.8 | 0.281 | weight_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 8.34x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.33x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 0.77x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.33x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 0.77x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 63,873.1 | 0.345 | weight_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 5.09x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.20x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 0.47x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.20x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.00 | 30,090.7 | 0.651 | kv_read | 0.47x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 93,743.6 | 0.338 | weight_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 3.47x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,035.7 | 0.282 | weight_read | 0.14x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 1.12 | 30,108.5 | 0.651 | kv_read | 0.32x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 13,035.7 | 0.282 | weight_read | 0.14x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 1.12 | 30,108.5 | 0.651 | kv_read | 0.32x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 207,628.8 | 0.374 | weight_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 331.01 | 1.00 | 325,147.9 | 0.586 | kv_read | 1.57x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,056.0 | 0.282 | weight_read | 0.06x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 29.05 | 4.49 | 30,217.4 | 0.654 | kv_read | 0.15x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.49 | 13,056.0 | 0.282 | weight_read | 0.06x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 29.05 | 4.49 | 30,217.4 | 0.654 | kv_read | 0.15x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 29.10x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 2.83x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 2.83x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 29.10x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 2.83x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 2.83x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 15,887.2 | 0.344 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 23.85x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.82x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 2.32x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 1.57 | 13,533.3 | 0.293 | link_latency | 0.85x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 2.32x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 31,774.4 | 0.687 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 11.92x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.41x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 1.16x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 23,630.2 | 0.511 | link_latency | 0.74x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 1.16x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 50,920.7 | 1.102 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 7.44x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.26x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 0.72x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 40,408.9 | 0.874 | weight_read | 0.79x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 2.88 | 50,920.7 | 1.102 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 91,112.4 | 0.986 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 4.16x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.14x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.00 | 36,893.4 | 0.798 | weight_read | 0.40x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.03 | 66,193.5 | 1.432 | weight_read | 0.73x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 4.03 | 70,608.1 | 1.527 | kv_read | 0.77x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 144,557.7 | 1.042 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 32.49 | 1.00 | 378,837.5 | 0.683 | weight_read | 2.62x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,023.2 | 0.282 | weight_read | 0.09x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 1.12 | 36,932.4 | 0.799 | weight_read | 0.26x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N5-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 5.83 | 102,958.0 | 2.227 | weight_read | 0.71x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.85 | 5.83 | 87,528.5 | 1.894 | kv_read | 0.61x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 354,458.4 | 1.278 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 32.49 | 1.00 | 570,217.3 | 1.028 | link_latency | 1.61x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,052.9 | 0.282 | weight_read | 0.04x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N5-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.85 | 4.49 | 37,172.5 | 0.804 | weight_read | 0.10x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x22-perregion | 17,930 | 1.00 | 6.88 | 117,176.6 | 6.535 | weight_read | 0.33x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N5-native-HBMKV-array-hybrid-x40-perregion-romfill | 32,600 | 1.88 | 5.15 | 166,276.1 | 5.100 | weight_read | 0.47x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,213.5 | 0.128 | weight_read | 6.06x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,213.5 | 0.128 | weight_read | 6.06x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,213.5 | 0.128 | weight_read | 6.06x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perregion | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 2.13x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 15,555.6 | 0.112 | link_latency | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,213.5 | 0.128 | weight_read | 4.58x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 0.75x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 1.61x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.19 | 14,197.3 | 0.102 | weight_read | 0.91x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 1.61x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 26,447.2 | 0.143 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,213.5 | 0.128 | weight_read | 2.69x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 0.44x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 0.95x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 1.66 | 23,382.3 | 0.169 | weight_read | 0.88x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 2.13 | 1.43 | 30,008.7 | 0.162 | link_latency | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 40,686.6 | 0.147 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 6.07 | 1.00 | 71,213.5 | 0.128 | weight_read | 1.75x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 0.29x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 0.61x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.18 | 32,771.3 | 0.236 | kv_read | 0.81x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 2.13 | 1.99 | 39,862.4 | 0.216 | kv_read | 0.98x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 66,018.8 | 0.179 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6.07 | 1.00 | 95,935.0 | 0.173 | kv_read | 1.45x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.00 | 11,735.4 | 0.085 | weight_read | 0.18x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.00 | 24,997.2 | 0.135 | weight_read | 0.38x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x3-perregion | 138,675 | 1.00 | 2.93 | 37,773.0 | 0.272 | kv_read | 0.57x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x4-perregion-romfill | 184,900 | 2.13 | 2.54 | 47,692.6 | 0.258 | kv_read | 0.72x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 145,646.4 | 0.263 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 6.07 | 1.00 | 145,646.4 | 0.263 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x3-perstream | 138,675 | 1.00 | 1.50 | 11,742.4 | 0.085 | weight_read | 0.08x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N5-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 2.13 | 1.13 | 25,005.4 | 0.135 | weight_read | 0.17x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x114-perregion | 92,910 | 1.00 | 2.62 | 66,116.9 | 0.712 | weight_read | 0.45x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N5-native-HBMKV-array-hybrid-x168-perregion-romfill | 136,920 | 1.48 | 2.27 | 78,076.6 | 0.570 | weight_read | 0.54x |

## What the completeness corrections cost

Four terms the model priced wrongly or not at all. Each row is
computed from the evaluated points, not restated from prose.

### 1. Per-region sweep depth: the busiest region, not the mean

The compute-in-ROM per-region machine used to charge `batch * k /
(N * coverage)` -- the load of the AVERAGE engaged region -- and then
divide it by a flat 0.85 whose own note said the depth is set by the
busiest region. The busiest region is now computed from the routing
distribution. The correction is not a constant: it is a function of
how many users one array pass actually serves.

**Read the `Users per slot` column, not the batch.** Since per-user
latency was separated from aggregate throughput, a machine cut into
`token_slots` slots spreads its batch across them, and the region
collisions this correction is about happen inside **one** slot. Where
the design the sweep chose has more slots than the batch has users, one
pass serves one user, no two tokens can collide on a region, and the
correction is 1.00x by construction rather than by accident. The
statistic itself is unchanged and is checked against a Monte Carlo of
the routing in `tests/test_roofline.py`; what moved is which point on it
these designs sit at.

| Model | B | Slots | Users per slot | Mean engaged region | Busiest region | Correction |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 | 3 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 3 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 4 | 64.00 | 64.000 | 64.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 57 | 1.12 | 1.001 | 1.014 | 1.01x |
| DeepSeek-V4-Flash-0731 | 256 | 22 | 11.64 | 1.131 | 2.460 | 2.18x |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 114 | 2.25 | 1.010 | 1.128 | 1.12x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 4 | 3.29 | 2.30 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 4 | 3.87 | 2.62 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 4 | 3.99 | 2.91 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 4 | 4.00 | 3.15 | 1.27x |
| DeepSeek-V4-Flash-0731 | 64 | 4 | 4.00 | 3.33 | 1.20x |
| DeepSeek-V4-Flash-0731 | 256 | 4 | 4.00 | 3.55 | 1.13x |
| DeepSeek-V4-Flash-0731 | 1 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 7 | 4.22 | 2.86 | 1.47x |
| DeepSeek-V4-Flash-0731 | 8 | 7 | 4.56 | 2.98 | 1.53x |
| DeepSeek-V4-Flash-0731 | 16 | 7 | 6.13 | 3.59 | 1.71x |
| DeepSeek-V4-Flash-0731 | 32 | 7 | 6.88 | 4.18 | 1.65x |
| DeepSeek-V4-Flash-0731 | 64 | 7 | 7.00 | 4.71 | 1.48x |
| DeepSeek-V4-Flash-0731 | 256 | 7 | 7.00 | 5.48 | 1.28x |
| DeepSeek-V4-Flash-0731 | 1 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 2 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 4 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 8 | 11 | 4.79 | 3.32 | 1.44x |
| DeepSeek-V4-Flash-0731 | 16 | 11 | 6.19 | 3.78 | 1.64x |
| DeepSeek-V4-Flash-0731 | 32 | 11 | 8.84 | 4.72 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 11 | 10.53 | 5.67 | 1.86x |
| DeepSeek-V4-Flash-0731 | 256 | 11 | 11.00 | 7.32 | 1.50x |
| DeepSeek-V4-Flash-0731 | 1 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 2 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 4 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 8 | 12 | 4.88 | 3.41 | 1.43x |
| DeepSeek-V4-Flash-0731 | 16 | 12 | 6.00 | 3.78 | 1.59x |
| DeepSeek-V4-Flash-0731 | 32 | 12 | 8.94 | 4.77 | 1.87x |
| DeepSeek-V4-Flash-0731 | 64 | 12 | 11.15 | 5.81 | 1.92x |
| DeepSeek-V4-Flash-0731 | 256 | 12 | 12.00 | 7.67 | 1.56x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 7.95 | 4.78 | 1.66x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 12.44 | 6.24 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 18.57 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 2 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 4 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 8 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 16 | 20 | 5.30 | 3.92 | 1.35x |
| DeepSeek-V4-Flash-0731 | 32 | 20 | 7.73 | 4.75 | 1.63x |
| DeepSeek-V4-Flash-0731 | 64 | 20 | 12.34 | 6.25 | 1.97x |
| DeepSeek-V4-Flash-0731 | 256 | 20 | 19.36 | 9.54 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Flash-0731 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Flash-0731 | 64 | 29 | 10.66 | 6.08 | 1.75x |
| DeepSeek-V4-Flash-0731 | 256 | 29 | 23.69 | 10.39 | 2.28x |
| DeepSeek-V4-Flash-0731 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Flash-0731 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Flash-0731 | 256 | 58 | 20.74 | 10.34 | 2.01x |
| DeepSeek-V4-Flash-0731 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Flash-0731 | 256 | 87 | 15.73 | 9.34 | 1.68x |
| DeepSeek-V4-Flash-0731 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Flash-0731 | 256 | 116 | 12.40 | 8.75 | 1.42x |
| DeepSeek-V4-Flash-0731 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Flash-0731 | 256 | 173 | 8.63 | 7.48 | 1.15x |
| DeepSeek-V4-Flash-0731 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Flash-0731 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 2 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 4 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 8 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 16 | 22 | 5.36 | 4.02 | 1.33x |
| DeepSeek-V4-Pro-0813 | 32 | 22 | 7.32 | 4.70 | 1.56x |
| DeepSeek-V4-Pro-0813 | 64 | 22 | 12.11 | 6.27 | 1.93x |
| DeepSeek-V4-Pro-0813 | 256 | 22 | 20.89 | 9.93 | 2.10x |
| DeepSeek-V4-Pro-0813 | 1 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 2 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 4 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 8 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 16 | 29 | 5.51 | 4.29 | 1.28x |
| DeepSeek-V4-Pro-0813 | 32 | 29 | 6.01 | 4.50 | 1.34x |
| DeepSeek-V4-Pro-0813 | 64 | 29 | 10.70 | 6.10 | 1.75x |
| DeepSeek-V4-Pro-0813 | 256 | 29 | 23.96 | 10.50 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 8 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 16 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 32 | 37 | 5.61 | 4.52 | 1.24x |
| DeepSeek-V4-Pro-0813 | 64 | 37 | 9.11 | 5.85 | 1.56x |
| DeepSeek-V4-Pro-0813 | 256 | 37 | 24.51 | 10.72 | 2.29x |
| DeepSeek-V4-Pro-0813 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 2 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 4 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 8 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 16 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 32 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Pro-0813 | 64 | 38 | 8.93 | 5.82 | 1.53x |
| DeepSeek-V4-Pro-0813 | 256 | 38 | 24.44 | 10.72 | 2.28x |
| DeepSeek-V4-Pro-0813 | 1 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 2 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 4 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 8 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 16 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 32 | 39 | 5.63 | 4.57 | 1.23x |
| DeepSeek-V4-Pro-0813 | 64 | 39 | 8.76 | 5.80 | 1.51x |
| DeepSeek-V4-Pro-0813 | 256 | 39 | 24.36 | 10.72 | 2.27x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4-Pro-0813 | 1 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 16 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 32 | 58 | 5.75 | 4.91 | 1.17x |
| DeepSeek-V4-Pro-0813 | 64 | 58 | 6.30 | 5.21 | 1.21x |
| DeepSeek-V4-Pro-0813 | 256 | 58 | 20.96 | 10.41 | 2.01x |
| DeepSeek-V4-Pro-0813 | 1 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 2 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 4 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 8 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 16 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 32 | 60 | 5.76 | 4.93 | 1.17x |
| DeepSeek-V4-Pro-0813 | 64 | 60 | 6.12 | 5.13 | 1.19x |
| DeepSeek-V4-Pro-0813 | 256 | 60 | 20.55 | 10.34 | 1.99x |
| DeepSeek-V4-Pro-0813 | 1 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 2 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 4 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 8 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 16 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 32 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 64 | 68 | 5.78 | 5.03 | 1.15x |
| DeepSeek-V4-Pro-0813 | 256 | 68 | 18.99 | 10.03 | 1.89x |
| DeepSeek-V4-Pro-0813 | 1 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 2 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 4 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 8 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 16 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 32 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 64 | 84 | 5.82 | 5.18 | 1.13x |
| DeepSeek-V4-Pro-0813 | 256 | 84 | 16.29 | 9.46 | 1.72x |
| DeepSeek-V4-Pro-0813 | 1 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 86 | 5.83 | 5.19 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 86 | 15.99 | 9.40 | 1.70x |
| DeepSeek-V4-Pro-0813 | 1 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 2 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 4 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 8 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 16 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 32 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | 87 | 5.83 | 5.20 | 1.12x |
| DeepSeek-V4-Pro-0813 | 256 | 87 | 15.84 | 9.37 | 1.69x |
| DeepSeek-V4-Pro-0813 | 1 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 2 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 4 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 8 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 16 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 32 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 64 | 116 | 5.87 | 5.37 | 1.09x |
| DeepSeek-V4-Pro-0813 | 256 | 116 | 12.45 | 8.77 | 1.42x |
| DeepSeek-V4-Pro-0813 | 1 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 2 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 4 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 8 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 16 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 32 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 64 | 173 | 5.91 | 5.56 | 1.06x |
| DeepSeek-V4-Pro-0813 | 256 | 173 | 8.65 | 7.49 | 1.15x |
| DeepSeek-V4-Pro-0813 | 1 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 231 | 5.94 | 5.66 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 231 | 6.56 | 6.17 | 1.06x |
| DeepSeek-V4-Pro-0813 | 1 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 347 | 5.96 | 5.77 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 347 | 5.96 | 5.77 | 1.03x |

### 3. The per-layer serial cost, and who pays it

Before this term the only latency in the model was
`links.*.hop_latency_s`, charged at inter-partition boundaries -- so
a `single_chip` design had a decode step with no fixed cost at all.
**The asymmetry is the finding and it runs against the ROM thesis:**
a ROM step is tens of microseconds over 32-61 layers while a GPU step
for the same model is milliseconds, so the same per-layer floor is a
large fraction of one and a rounding error on the other.

| Family | Model | B | Fixed latency (us) | Share of the fastest step |
|---|---|---:|---:|---:|
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 1.6% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 0.7% |
| gpu | Qwen3-8B | 1 | 5.85 | 1.0% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 4.8% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 3.3% |
| rom | Qwen3-8B | 1 | 5.85 | 3.8% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Flash-0731 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Flash-0731 | hbm | interleaved | 32 B | 1.00x |
| DeepSeek-V4-Pro-0813 | sram | interleaved | 128 B | 1.00x |
| DeepSeek-V4-Pro-0813 | hbm | interleaved | 32 B | 1.00x |

### 5. The SRAM KV path, which is still never exercised

A reported bound rather than a correction. The step credits ONE user
with the whole array's read bandwidth. That is defensible for KV in a
way it is not for ROM -- KV is written at run time and can be striped
across every bank, whereas an expert's weights live where they were
masked -- but it holds only if the design really stripes, and nothing
in the model checks. The bound below is what the same read costs if a
user can draw only the banks its own footprint occupies.

| Model | B | Devices | Bank occupancy | KV read as charged (us) | Under bank locality (us) |
|---|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 | 3 | 44.74% | 12.45 | 9.27 |
| Qwen3-8B | 2 | 3 | 44.74% | 12.45 | 9.27 |
| Qwen3-8B | 4 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 8 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 16 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 32 | 1 | 0.87% | 4.62 | 9.27 |
| Qwen3-8B | 64 | 1 | 0.98% | 5.19 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 21 | 40.78% | 18.25 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 21 | 40.78% | 18.25 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 1.48% | 1.80 | 2.13 |
| DeepSeek-V4-Flash-0731 | 64 | 1 | 1.66% | 2.02 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 110 | 80.65% | 184.27 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 2 | 47.19% | 111.73 | 2.08 |

## Sparse-MoE engagement on a ROM machine

Expected distinct experts touched by a batch is `1 - (1 - k/N)^B`, so the
bytes a step engages grow with batch while the ROM full-array sweep time
does not: an unselected expert's read ports cannot be borrowed, and a
selected one is read once however many batch members chose it. **MoE
sparsity on a ROM machine therefore converts into aggregate throughput,
not into lower per-token latency** -- which is the opposite of what it does
on an HBM machine, where bandwidth is global and sparsity directly
reduces the bytes fetched.

| Model | B | Expert coverage | Engaged weight bytes | Engaged fraction | Effective ROM read | Peak ROM read | Per-user tok/s | Aggregate tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,262.3 | 9,049.4 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,262.3 | 9,049.4 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 2,262.3 | 9,049.4 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,151.5 | 9,211.7 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 580.9 | 9,295.0 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 291.8 | 9,337.2 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 146.2 | 9,358.5 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 36.6 | 9,374.5 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 810.0 | 11,339.7 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 810.0 | 11,339.7 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 810.0 | 11,339.7 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 810.0 | 11,339.7 |
| DeepSeek-V4-Flash-0731 | 16 | 2.67% | 11.7 GB | 7.01% | 152.88 TB/s | 2,179.91 TB/s | 710.8 | 11,372.6 |
| DeepSeek-V4-Flash-0731 | 32 | 5.28% | 15.5 GB | 9.31% | 202.92 TB/s | 2,179.91 TB/s | 359.0 | 11,489.3 |
| DeepSeek-V4-Flash-0731 | 64 | 10.27% | 22.9 GB | 13.72% | 299.00 TB/s | 2,179.91 TB/s | 180.4 | 11,548.5 |
| DeepSeek-V4-Flash-0731 | 256 | 35.19% | 59.6 GB | 35.69% | 777.94 TB/s | 2,179.91 TB/s | 45.3 | 11,593.4 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 122.1 | 9,038.3 |
| DeepSeek-V4-Pro-0813 | 256 | 5.30% | 70.4 GB | 7.89% | 919.76 TB/s | 11,661.57 TB/s | 35.6 | 9,124.5 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 2 |
| gpu | kv_read | 21 |
| gpu | link_latency | 287 |
| gpu | thermal | 1 |
| gpu | weight_read | 585 |
| rom | compute | 80 |
| rom | infeasible | 1574 |
| rom | kv_read | 203 |
| rom | link_latency | 805 |
| rom | thermal | 104 |
| rom | weight_read | 930 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 2 |
| rom | CAPACITY | 1574 |

## Mechanical consistency audit

**PASS** over 95,508 checks.

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 2 |
| published | 69 |
| derived | 36 |
| assumed | 60 |

Every `assumed` input, in full, because an ungraded assumption is the
failure mode this program exists to prevent:

- `efficiencies.compute`
- `efficiencies.expert_router_imbalance`
- `efficiencies.hbm_bandwidth`
- `efficiencies.hbm_capacity`
- `efficiencies.rom_read_bandwidth`
- `efficiencies.sram_read_bandwidth`
- `efficiencies.stage_balance`
- `energy.mac_energy_j_per_op.bf16`
- `energy.mac_energy_j_per_op.fp32`
- `energy.mac_energy_j_per_op.fp4`
- `energy.mac_energy_j_per_op.fp8`
- `energy.mac_energy_j_per_op.w4a8`
- `energy.operand_delivery_j_per_byte`
- `energy.rom_read_j_per_byte`
- `energy.sram_read_j_per_byte`
- `floorplan.interconnect_area_fraction`
- `floorplan.overhead_area_fraction`
- `hbm.hbm2e.phy_area_mm2_per_stack`
- `hbm.hbm2e.stack_beachfront_mm`
- `hbm.hbm3e.phy_area_mm2_per_stack`
- `hbm.hbm3e.stack_beachfront_mm`
- `kv.access_granularity_bytes.hbm`
- `kv.access_granularity_bytes.sram`
- `kv.index_layout`
- `latency.array_pass_boundaries_per_layer`
- `latency.global_wire_delay_s_per_mm`
- `latency.layer_barrier_s`
- `latency.pipeline_fill_drain_s`
- `latency.sequencer_issue_decode_s`
- `latency.sparse_index_dependency_s`
- `latency.sram_access_s`
- `links.ethernet.bytes_s`
- `links.ethernet.fabric`
- `links.ethernet.hop_latency_s`
- `links.ethernet.switch_radix`
- `links.inter_wafer.domain_size`
- `links.inter_wafer.fabric`
- `links.inter_wafer.hop_latency_s`
- `links.inter_wafer.switch_radix`
- `links.nvlink.hop_latency_s`
- `links.on_package.fabric`
- `links.on_package.hop_latency_s`
- `power.clock_energy_j_per_mm2_per_cycle`
- `power.clock_region_multiplier.rom_array`
- `power.clock_region_multiplier.sram_array`
- `power.fabric_clock_hz`
- `power.gpu_logic_area_fraction`
- `power.memory_interface_idle_w_per_stack`
- `power.static_leakage_w_per_mm2.logic`
- `power.static_leakage_w_per_mm2.rom_array`
- `power.static_leakage_w_per_mm2.sram_array`
- `reference_parts.b200_sxm.clock_frequency_hz`
- `reference_parts.taalas_hc1.batch_size`
- `reference_parts.taalas_hc1.weight_amortization`
- `reference_parts.taalas_hc1.weight_bits_per_parameter`
- `rom.array_efficiency`
- `rom.cell_to_sram_cell_area_ratio`
- `rom.cim_cell_area_multiplier`
- `rom.cim_precompute_area_fraction`
- `sram.array_efficiency`

## Interpretation boundary

- No mask-ROM macro has been fabricated at a leading node for this
  program. The ROM capacity density rests on an assumed cell-area ratio
  against a published SRAM bitcell, and the ROM read bandwidth density on
  a *simulated* 28 nm ROM-CIM macro scaled by published bitcell areas.
  Both are named in the evidence ledger above.
- Compute density is charged at a published GPU's whole-die roof per mm2,
  applied to a modelled design's compute-only area. Newer parts are
  denser than the A100 anchor, so this understates a 2026 design.
- Hop latencies are floors. They ignore switch contention, per-hop
  payload queueing beyond the modelled serialisation, and pipeline fill
  at batch 1. Each of those makes an array worse, never better, so the
  reported array crossovers are upper bounds.
- **Power is now enumerated, and it is right on one published part and
  2.9-3.6x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 0.97x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.28x of its published card power. **The second one FAILS its
  gate and the failure is reported rather than tuned away.** The A100
  gate is also the weaker of the two, because the clock term inside it
  was calibrated as a fraction of a shipping GPU's TDP density -- read
  the power-gate section before quoting it. Every ROM watt and every ROM
  joule-per-token here is a LOWER BOUND by roughly the HC1 gate's
  shortfall.
- **`thermal_scale` now binds, which it never did before.** Static power
  does not fall when a step is stretched, so the coolable step time
  solves `t >= E_dynamic / (cooling_limit - P_static)` rather than
  dividing total energy by the total limit. Some designs are power-
  limited and their rates are reduced accordingly; the power-and-energy
  section names every one of them. Rates on unthrottled points are
  unchanged, so the two validation gates above are untouched by this.
- **Aggregate throughput is reported at steady state with every slot
  occupied, and fill and drain are not charged.** A request that is short
  compared with the slot count pays up to one extra traversal that this
  model does not bill, which flatters a deep pipeline. The delivered rate
  at the requested concurrency is reported separately and is not affected.
- **The weight replication a deep pipeline implies is not charged against
  capacity.** Beyond the layer count the surplus partitions hold replicas
  of a stage, and each replica needs its own copy of that stage's weights;
  the capacity check credits the machine with holding the model once. This
  favours the deepest pipelines, which are on the GPU side of this
  comparison, so correcting it would widen the ROM ratios rather than
  narrow them.
- Prefill, speculative decoding and cost are out of scope for this model.
