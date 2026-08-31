# Area-constrained roofline: n6_vs_a100

> Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 76.6 us, or 13,063 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 608x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `tensor` on 1 device. On the GPU side the correction reaches 595x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate -- runs `tensor` on 112 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **11x**. The GPU binds on `weight_read` and the ROM part on `compute`.
4. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
5. **Letting the GPU choose its own parallelism is worth up to 214.59x to it.** At 554,700 mm2 on DeepSeek-V4-Pro-0813 the pipeline-only GPU delivers 1.04 tok/s and the same silicon running tensor delivers 224 tok/s.
6. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 256 the aggregate ratio at equal area spans 0.10x (Qwen3-8B, ROM binding on `weight_read`) to 35.13x (DeepSeek-V4-Flash-0731, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
7. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** DeepSeek-V4-Flash-0731 engages 6.7% of its ROM array at batch 1 and 29.9% at batch 256, while the weight-read time is identical at both. What the machine delivers rises from 527 to 9,760 tok/s, and its rate with every slot occupied from 9,491 to 9,760. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 18 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
8. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 3,029 us over NVLink, capping per-user decode at 330 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 1,482.8 us and cap it at 674 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least 2.6x cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
9. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 24 of 24 operating points and an array 0; on tokens per second per square millimetre the same points go 18 to the array and 6 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
10. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 477 of 3092 feasible points.
11. **The largest open question is not in this model's inputs but in the architecture, and the anchor cannot settle it.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 256 that costs up to 20.0x of aggregate throughput (DeepSeek-V4-Flash-0731). The machines are identical at batch 1, which is where the published anchor sits, so no amount of validation against it resolves the fork.
12. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 6.78x, on DeepSeek-V4-Flash-0731 at batch 256, where the busiest region carries 3.04x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 42 of 48 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
13. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
14. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 77% of its cooling budget. The companion study at the other node does have power-limited points.

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
from Cerebras WSE-2 (4.327e+11 B/s/mm2), so it is physically unremarkable. That is a falsifiable
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

**The thermal limit can bind now, and this is the first version of this
study in which it could -- in this one it does not, and the companion
study at the other node is where it does.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **0 of 3,092 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 77% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 240 | 0 | 50.8% | 77.4% | 0.375 | 71% |
| gpu | small array (1,600-5,000 mm2) | 60 | 0 | 77.0% | 77.5% | 0.375 | 47% |
| gpu | wafer (>=40,000 mm2) | 720 | 0 | 40.5% | 76.9% | 0.372 | 89% |
| rom | large array (5,000-40,000 mm2) | 420 | 0 | 16.7% | 69.3% | 0.346 | 77% |
| rom | small array (1,600-5,000 mm2) | 114 | 0 | 54.2% | 67.2% | 0.336 | 34% |
| rom | wafer (>=40,000 mm2) | 1,538 | 0 | 20.1% | 36.0% | 0.180 | 90% |

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
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill` | 0.930621 | 4,340.1 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 16.075415 | 8,745.9 | link_latency | 17.27x |
| DeepSeek-V4-Flash-0731 | 2 | 46,225 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill` | 0.490110 | 4,500.0 | link_latency | `DSV4-Flash/a100_sxm_80gb-x56-tensor` | 9.271642 | 8,850.4 | link_latency | 18.92x |
| DeepSeek-V4-Flash-0731 | 4 | 92,450 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 0.510600 | 8,970.9 | link_latency | `DSV4-Flash/a100_sxm_80gb-x112-tensor` | 10.045490 | 17,177.9 | link_latency | 19.67x |
| DeepSeek-V4-Flash-0731 | 8 | 138,675 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill` | 0.424532 | 13,659.9 | link_latency | `DSV4-Flash/a100_sxm_80gb-x168-tensor` | 8.994009 | 25,596.8 | link_latency | 21.19x |
| DeepSeek-V4-Flash-0731 | 16 | 277,350 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill` | 0.448634 | 27,183.0 | link_latency | `DSV4-Flash/a100_sxm_80gb-x336-tensor` | 13.595028 | 49,949.7 | link_latency | 30.30x |
| DeepSeek-V4-Flash-0731 | 32 | 369,800 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 0.354979 | 37,070.3 | link_latency | `DSV4-Flash/a100_sxm_80gb-x448-tensor` | 12.337839 | 66,391.5 | link_latency | 34.76x |
| DeepSeek-V4-Flash-0731 | 64 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.316632 | 56,343.4 | link_latency | `DSV4-Flash/a100_sxm_80gb-x672-tensor` | 13.708066 | 98,727.1 | link_latency | 43.29x |
| DeepSeek-V4-Flash-0731 | 256 | 554,700 | `DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.181335 | 62,063.5 | kv_read | `DSV4-Flash/a100_sxm_80gb-x672-tensor` | 10.057423 | 97,982.5 | link_latency | 55.46x |
| DeepSeek-V4-Pro-0813 | 1 | 92,450 | `DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2` | 2.437649 | 5,751.7 | link_latency | `DSV4-Pro/a100_sxm_80gb-x112-tensor` | 63.234327 | 17,383.0 | link_latency | 25.94x |
| DeepSeek-V4-Pro-0813 | 2 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill` | 2.340342 | 23,309.9 | link_latency | `DSV4-Pro/a100_sxm_80gb-x280-tensor` | 81.541094 | 41,965.7 | link_latency | 34.84x |
| DeepSeek-V4-Pro-0813 | 4 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill` | 2.340342 | 23,309.9 | link_latency | `DSV4-Pro/a100_sxm_80gb-x280-tensor` | 51.736781 | 42,276.8 | link_latency | 22.11x |
| DeepSeek-V4-Pro-0813 | 8 | 231,125 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill` | 1.632808 | 24,530.0 | link_latency | `DSV4-Pro/a100_sxm_80gb-x280-tensor` | 34.665122 | 42,733.3 | link_latency | 21.23x |
| DeepSeek-V4-Pro-0813 | 16 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.928211 | 57,341.9 | link_latency | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 58.855356 | 99,769.8 | link_latency | 30.52x |
| DeepSeek-V4-Pro-0813 | 32 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.408555 | 60,482.6 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 43.152067 | 100,271.1 | link_latency | 30.64x |
| DeepSeek-V4-Pro-0813 | 64 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.169914 | 63,085.5 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 34.150177 | 100,379.6 | link_latency | 29.19x |
| DeepSeek-V4-Pro-0813 | 256 | 554,700 | `DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 1.359671 | 90,722.6 | kv_read | `DSV4-Pro/a100_sxm_80gb-x672-tensor` | 25.563103 | 99,286.8 | link_latency | 18.80x |
| Qwen3-8B | 1 | 46,225 | `Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill` | 0.621029 | 4,040.0 | link_latency | `Qwen3-8B/a100_sxm_80gb-x56-tensor` | 11.962200 | 9,442.9 | link_latency | 19.26x |
| Qwen3-8B | 2 | 92,450 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill` | 1.130584 | 9,438.8 | link_latency | `Qwen3-8B/a100_sxm_80gb-x112-tensor` | 11.080137 | 17,642.3 | link_latency | 9.80x |
| Qwen3-8B | 4 | 184,900 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill` | 1.172673 | 18,787.6 | link_latency | `Qwen3-8B/a100_sxm_80gb-x224-tensor` | 11.560125 | 33,884.6 | link_latency | 9.86x |
| Qwen3-8B | 8 | 369,800 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill` | 1.256852 | 37,255.4 | link_latency | `Qwen3-8B/a100_sxm_80gb-x448-hybrid` | 3.856186 | 116,740.2 | weight_read | 3.07x |
| Qwen3-8B | 16 | 554,700 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 1.132261 | 56,555.3 | link_latency | `Qwen3-8B/a100_sxm_80gb-x672-hybrid` | 3.856186 | 175,110.3 | weight_read | 3.41x |
| Qwen3-8B | 32 | 554,700 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.819108 | 59,408.5 | kv_read | `Qwen3-8B/a100_sxm_80gb-x672-hybrid` | 3.856186 | 175,110.3 | weight_read | 4.71x |
| Qwen3-8B | 64 | 554,700 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill` | 0.662531 | 62,085.0 | kv_read | `Qwen3-8B/a100_sxm_80gb-x672-hybrid` | 3.856186 | 175,110.3 | weight_read | 5.82x |
| Qwen3-8B | 256 | 554,700 | `Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12` | 0.809968 | 97,187.3 | kv_read | `Qwen3-8B/a100_sxm_80gb-x672-hybrid` | 1.439685 | 177,013.9 | weight_read | 1.78x |

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


## Derived technology at N6

These are outputs of the graded primitives, not inputs.

| Quantity | Value | Grade |
|---|---:|---|
| SRAM capacity density | 3.009 MB/mm2 | assumed |
| ROM capacity density | 16.204 MB/mm2 | assumed |
| ROM read bandwidth density | 282.2 GB/s/mm2 | derived |
| SRAM read bandwidth density | 432.7 GB/s/mm2 | derived |
| Compute density, bf16 | 0.446 Tops/s/mm2 | derived |
| Compute density, fp8 | 0.891 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.261 Tops/s/mm2 | derived |
| Compute density, fp4 | 1.783 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.028 Tops/s/mm2 | derived |
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
| Qwen3-8B | 1 | 46,225 | 51,291.3 | wafer-pipeline | 6,505.3 | wafer-tensor | 7.88x | 3,440.9 | pipeline | 789.4 | tensor | 4.36x | 14.91x | 8.24x | 0.55x |
| Qwen3-8B | 2 | 92,450 | 48,716.3 | wafer-pipeline | 5,878.5 | wafer-hybrid | 8.29x | 5,074.5 | pipeline | 848.7 | tensor | 5.98x | 9.60x | 6.93x | 0.72x |
| Qwen3-8B | 3 | 138,675 | 48,716.3 | wafer-pipeline | 5,391.7 | wafer-hybrid | 9.04x | 6,028.6 | pipeline | 870.5 | tensor | 6.93x | 8.08x | 6.19x | 0.77x |
| Qwen3-8B | 4 | 184,900 | 48,716.3 | wafer-pipeline | 4,979.3 | wafer-hybrid | 9.78x | 6,654.1 | pipeline | 881.8 | tensor | 7.55x | 7.32x | 5.65x | 0.77x |
| Qwen3-8B | 6 | 277,350 | 48,716.3 | wafer-pipeline | 4,318.7 | wafer-hybrid | 11.28x | 7,424.4 | pipeline | 565.8 | tensor | 13.12x | 6.56x | 7.63x | 1.16x |
| Qwen3-8B | 8 | 369,800 | 48,716.3 | wafer-pipeline | 3,812.9 | wafer-hybrid | 12.78x | 7,880.6 | pipeline | 568.2 | tensor | 13.87x | 6.18x | 6.71x | 1.09x |
| Qwen3-8B | 12 | 554,700 | 56,411.9 | wafer-pipeline | 3,447.0 | wafer-hybrid | 16.37x | 8,396.5 | pipeline | 570.6 | tensor | 14.72x | 6.72x | 6.04x | 0.90x |
| DeepSeek-V4-Flash-0731 | 1 | 46,225 | 18,475.6 | wafer-pipeline | 4,663.6 | wafer-tensor | 3.96x | 1,485.7 | pipeline | 544.1 | tensor | 2.73x | 12.44x | 8.57x | 0.69x |
| DeepSeek-V4-Flash-0731 | 2 | 92,450 | 27,333.1 | wafer-pipeline | 4,472.2 | wafer-hybrid | 6.11x | 1,703.4 | pipeline | 568.8 | tensor | 2.99x | 16.05x | 7.86x | 0.49x |
| DeepSeek-V4-Flash-0731 | 3 | 138,675 | 34,088.9 | wafer-pipeline | 4,375.0 | wafer-hybrid | 7.79x | 1,795.0 | pipeline | 578.0 | tensor | 3.11x | 18.99x | 7.57x | 0.40x |
| DeepSeek-V4-Flash-0731 | 4 | 184,900 | 38,879.0 | wafer-pipeline | 4,281.2 | wafer-hybrid | 9.08x | 1,845.5 | pipeline | 582.8 | tensor | 3.17x | 21.07x | 7.35x | 0.35x |
| DeepSeek-V4-Flash-0731 | 6 | 277,350 | 45,220.6 | wafer-pipeline | 4,104.3 | wafer-hybrid | 11.02x | 1,899.6 | pipeline | 404.0 | tensor | 4.70x | 23.81x | 10.16x | 0.43x |
| DeepSeek-V4-Flash-0731 | 8 | 369,800 | 49,229.4 | wafer-pipeline | 3,941.1 | wafer-hybrid | 12.49x | 1,928.1 | pipeline | 405.2 | tensor | 4.76x | 25.53x | 9.73x | 0.38x |
| DeepSeek-V4-Flash-0731 | 12 | 554,700 | 54,012.8 | wafer-pipeline | 3,650.5 | wafer-hybrid | 14.80x | 1,957.7 | pipeline | 406.4 | tensor | 4.82x | 27.59x | 8.98x | 0.33x |
| DeepSeek-V4-Pro-0813 | 2 | 92,450 | 8,986.6 | wafer-pipeline | 2,359.5 | wafer-hybrid | 3.81x | 529.1 | pipeline | 274.9 | tensor | 1.92x | 16.99x | 8.58x | 0.51x |
| DeepSeek-V4-Pro-0813 | 3 | 138,675 | 9,497.6 | wafer-pipeline | 2,016.1 | wafer-hybrid | 4.71x | 561.6 | pipeline | 283.0 | tensor | 1.98x | 16.91x | 7.12x | 0.42x |
| DeepSeek-V4-Pro-0813 | 4 | 184,900 | 11,753.0 | wafer-pipeline | 2,002.6 | wafer-hybrid | 5.87x | 579.7 | pipeline | 287.4 | tensor | 2.02x | 20.27x | 6.97x | 0.34x |
| DeepSeek-V4-Pro-0813 | 6 | 277,350 | 15,371.5 | wafer-pipeline | 1,972.0 | wafer-hybrid | 7.79x | 599.4 | pipeline | 221.0 | tensor | 2.71x | 25.65x | 8.92x | 0.35x |
| DeepSeek-V4-Pro-0813 | 8 | 369,800 | 18,073.4 | wafer-pipeline | 1,933.6 | wafer-hybrid | 9.35x | 609.8 | pipeline | 222.4 | tensor | 2.74x | 29.64x | 8.70x | 0.29x |
| DeepSeek-V4-Pro-0813 | 12 | 554,700 | 21,951.3 | wafer-pipeline | 1,863.2 | wafer-hybrid | 11.78x | 620.6 | pipeline | 223.7 | tensor | 2.77x | 35.37x | 8.33x | 0.24x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.24x to 1.16x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,505.3 | 6,505.3 | link_latency | Qwen3-8B/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,073.83 | 789.4 | 789.4 | link_latency | 8.24x | 8.24x | 68.84x | 8.24x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x3 | 2,445 | 2,791.2 | 8,373.5 | compute | Qwen3-8B/a100_sxm_80gb-x3-tensor | 2,478 | 0.99x | tensor | 363.93 | 258.9 | 258.9 | weight_read | 10.78x | 32.34x | 29.28x | 10.78x |
| Qwen3-8B | 2 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,174.3 | 8,348.6 | link_latency | Qwen3-8B/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,149.77 | 796.1 | 1,592.2 | link_latency | 5.24x | 5.24x | 44.17x | 5.24x |
| Qwen3-8B | 2 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x5 | 4,075 | 1,459.7 | 2,919.3 | link_latency | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 369.44 | 380.8 | 761.6 | weight_read | 3.83x | 3.83x | 15.32x | 3.83x |
| Qwen3-8B | 4 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,005.3 | 16,021.2 | link_latency | Qwen3-8B/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,301.65 | 732.8 | 2,931.2 | link_latency | 5.47x | 5.47x | 42.38x | 5.47x |
| Qwen3-8B | 4 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 1,265.1 | 6,325.4 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 378.87 | 339.5 | 1,358.2 | weight_read | 3.73x | 4.66x | 13.28x | 3.73x |
| Qwen3-8B | 8 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,705.2 | 29,641.9 | link_latency | Qwen3-8B/a100_sxm_80gb-x448-hybrid | 370,048 | 1.00x | hybrid | 534.13 | 540.6 | 30,273.5 | weight_read | 6.85x | 0.98x | 39.21x | 7.21x |
| Qwen3-8B | 8 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 796.7 | 6,373.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 397.75 | 279.0 | 2,232.4 | weight_read | 2.85x | 2.85x | 8.73x | 2.85x |
| Qwen3-8B | 16 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,121.8 | 49,949.0 | link_latency | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 534.13 | 540.6 | 45,410.2 | weight_read | 5.77x | 1.10x | 33.04x | 6.50x |
| Qwen3-8B | 16 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 400.9 | 6,413.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 435.50 | 205.7 | 3,291.8 | kv_read | 1.95x | 1.95x | 4.89x | 1.95x |
| Qwen3-8B | 32 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,266.5 | 72,528.3 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 534.13 | 540.6 | 45,410.2 | weight_read | 4.19x | 1.60x | 23.98x | 4.72x |
| Qwen3-8B | 32 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 201.1 | 6,434.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 510.99 | 134.9 | 4,315.9 | kv_read | 1.49x | 1.49x | 2.95x | 1.49x |
| Qwen3-8B | 64 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,464.2 | 93,708.8 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 534.13 | 540.6 | 45,410.2 | weight_read | 2.71x | 2.06x | 15.49x | 3.05x |
| Qwen3-8B | 64 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 100.7 | 6,444.5 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 661.99 | 79.9 | 5,110.8 | kv_read | 1.26x | 1.26x | 1.98x | 1.26x |
| Qwen3-8B | 256 | fastest | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 468.7 | 119,989.1 | kv_read | Qwen3-8B/a100_sxm_80gb-x672-hybrid | 555,072 | 1.00x | hybrid | 568.18 | 480.3 | 122,953.2 | weight_read | 0.98x | 0.98x | 4.96x | 1.10x |
| Qwen3-8B | 256 | smallest silicon | Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | 4,075 | 25.2 | 6,452.2 | kv_read | Qwen3-8B/a100_sxm_80gb-x5-tensor | 4,130 | 0.99x | tensor | 1,567.96 | 23.2 | 5,930.1 | kv_read | 1.09x | 1.09x | 1.24x | 1.09x |
| DeepSeek-V4-Flash-0731 | 1 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,663.6 | 4,663.6 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,282.63 | 544.1 | 544.1 | link_latency | 8.57x | 8.57x | 143.13x | 8.57x |
| DeepSeek-V4-Flash-0731 | 1 | smallest silicon | DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x18 | 14,670 | 1,407.1 | 1,407.1 | link_latency | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,266.53 | 466.5 | 466.5 | link_latency | 3.02x | 3.02x | 22.05x | 3.02x |
| DeepSeek-V4-Flash-0731 | 2 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,590.8 | 9,181.7 | link_latency | DSV4-Flash/a100_sxm_80gb-x56-tensor | 46,256 | 1.00x | tensor | 1,361.26 | 477.3 | 954.6 | link_latency | 9.62x | 9.62x | 140.89x | 9.62x |
| DeepSeek-V4-Flash-0731 | 2 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x18 | 14,670 | 1,312.3 | 3,936.8 | link_latency | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,329.05 | 398.9 | 797.8 | link_latency | 3.29x | 4.93x | 20.57x | 3.29x |
| DeepSeek-V4-Flash-0731 | 4 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,392.3 | 17,569.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,542.67 | 427.5 | 1,710.0 | link_latency | 10.27x | 10.27x | 226.72x | 10.27x |
| DeepSeek-V4-Flash-0731 | 4 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x18 | 14,670 | 1,154.1 | 4,616.3 | link_latency | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,454.10 | 322.0 | 1,288.1 | link_latency | 3.58x | 3.58x | 18.09x | 3.58x |
| DeepSeek-V4-Flash-0731 | 8 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,203.7 | 33,629.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x224-tensor | 185,024 | 1.00x | tensor | 1,905.49 | 363.0 | 2,904.3 | link_latency | 11.58x | 11.58x | 390.88x | 11.58x |
| DeepSeek-V4-Flash-0731 | 8 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x18 | 14,670 | 778.6 | 6,229.0 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 1,704.20 | 242.6 | 1,940.6 | weight_read | 3.21x | 3.21x | 12.20x | 3.21x |
| DeepSeek-V4-Flash-0731 | 16 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,871.1 | 61,937.7 | link_latency | DSV4-Flash/a100_sxm_80gb-x448-tensor | 370,048 | 1.00x | tensor | 3,405.14 | 233.1 | 3,729.5 | link_latency | 16.61x | 16.61x | 679.14x | 16.61x |
| DeepSeek-V4-Flash-0731 | 16 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 527.3 | 9,491.1 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 2,204.41 | 171.6 | 2,745.4 | weight_read | 3.07x | 3.46x | 8.26x | 3.07x |
| DeepSeek-V4-Flash-0731 | 32 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,390.5 | 108,496.4 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 4,848.38 | 171.6 | 5,491.3 | link_latency | 19.76x | 19.76x | 874.16x | 19.76x |
| DeepSeek-V4-Flash-0731 | 32 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 300.5 | 9,615.7 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 3,204.81 | 116.9 | 3,739.4 | weight_read | 2.57x | 2.57x | 6.01x | 2.57x |
| DeepSeek-V4-Flash-0731 | 64 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,780.4 | 177,945.9 | link_latency | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 7,718.77 | 112.5 | 7,202.1 | link_latency | 24.71x | 24.71x | 716.86x | 24.71x |
| DeepSeek-V4-Flash-0731 | 64 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 151.5 | 9,697.5 | compute | DSV4-Flash/a100_sxm_80gb-x18-tensor | 14,868 | 0.99x | tensor | 5,205.63 | 79.3 | 5,076.3 | weight_read | 1.91x | 1.91x | 4.22x | 1.91x |
| DeepSeek-V4-Flash-0731 | 256 | fastest | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,336.9 | 342,257.8 | kv_read | DSV4-Flash/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 24,941.07 | 38.1 | 9,742.3 | link_latency | 35.13x | 35.13x | 344.70x | 35.13x |
| DeepSeek-V4-Flash-0731 | 256 | smallest silicon | DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x18 | 14,670 | 38.1 | 9,759.8 | compute | DSV4-Flash/a100_sxm_80gb-x18-hybrid | 14,868 | 0.99x | hybrid | 1,020.96 | 39.0 | 9,978.3 | weight_read | 0.98x | 0.98x | 2.32x | 0.98x |
| DeepSeek-V4-Pro-0813 | 1 | fastest | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,359.5 | 2,359.5 | link_latency | DSV4-Pro/a100_sxm_80gb-x112-tensor | 92,512 | 1.00x | tensor | 1,918.19 | 274.9 | 274.9 | link_latency | 8.58x | 8.58x | 451.22x | 8.58x |
| DeepSeek-V4-Pro-0813 | 1 | smallest silicon | DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x94 | 76,610 | 500.5 | 500.5 | compute | DSV4-Pro/a100_sxm_80gb-x93-tensor | 76,818 | 1.00x | tensor | 1,915.69 | 270.2 | 270.2 | link_latency | 1.85x | 1.85x | 82.56x | 1.85x |
| DeepSeek-V4-Pro-0813 | 2 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 1,992.0 | 9,960.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 2,146.37 | 257.3 | 514.7 | link_latency | 7.74x | 19.35x | 840.81x | 7.74x |
| DeepSeek-V4-Pro-0813 | 2 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 486.5 | 5,838.2 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 2,123.39 | 227.3 | 454.6 | link_latency | 2.14x | 12.84x | 81.60x | 2.14x |
| DeepSeek-V4-Pro-0813 | 4 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 1,992.0 | 9,960.1 | link_latency | DSV4-Pro/a100_sxm_80gb-x280-tensor | 231,280 | 1.00x | tensor | 2,584.74 | 204.3 | 817.2 | link_latency | 9.75x | 12.19x | 840.81x | 9.75x |
| DeepSeek-V4-Pro-0813 | 4 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 486.5 | 5,838.2 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 2,538.77 | 176.9 | 707.7 | weight_read | 2.75x | 8.25x | 81.60x | 2.75x |
| DeepSeek-V4-Pro-0813 | 8 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 1,971.4 | 15,771.0 | link_latency | DSV4-Pro/a100_sxm_80gb-x336-tensor | 277,536 | 1.00x | tensor | 4,567.48 | 133.6 | 1,069.1 | link_latency | 14.75x | 14.75x | 983.44x | 14.75x |
| DeepSeek-V4-Pro-0813 | 8 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 486.5 | 5,838.2 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 3,369.54 | 132.4 | 1,058.8 | weight_read | 3.68x | 5.51x | 81.60x | 3.68x |
| DeepSeek-V4-Pro-0813 | 16 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,858.7 | 29,738.4 | link_latency | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 6,368.95 | 105.9 | 1,695.2 | link_latency | 17.54x | 17.54x | 1782.65x | 17.54x |
| DeepSeek-V4-Pro-0813 | 16 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 397.4 | 6,358.9 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 5,031.08 | 92.1 | 1,474.4 | link_latency | 4.31x | 4.31x | 66.66x | 4.31x |
| DeepSeek-V4-Pro-0813 | 32 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,341.9 | 42,939.5 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 9,931.89 | 72.6 | 2,323.7 | link_latency | 18.48x | 18.48x | 1286.99x | 18.48x |
| DeepSeek-V4-Pro-0813 | 32 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 229.4 | 7,341.0 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 8,354.17 | 60.6 | 1,939.3 | link_latency | 3.79x | 3.79x | 38.48x | 3.79x |
| DeepSeek-V4-Pro-0813 | 64 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 842.5 | 53,923.2 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 17,057.79 | 45.9 | 2,939.4 | link_latency | 18.35x | 18.35x | 808.10x | 18.35x |
| DeepSeek-V4-Pro-0813 | 64 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x96 | 78,240 | 124.3 | 7,955.4 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 15,000.34 | 38.3 | 2,449.2 | link_latency | 3.25x | 3.25x | 20.85x | 3.25x |
| DeepSeek-V4-Pro-0813 | 256 | fastest | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 260.6 | 66,724.0 | kv_read | DSV4-Pro/a100_sxm_80gb-x672-tensor | 555,072 | 1.00x | tensor | 59,813.14 | 15.2 | 3,884.0 | link_latency | 17.18x | 17.18x | 249.98x | 17.18x |
| DeepSeek-V4-Pro-0813 | 256 | smallest silicon | DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x96 | 78,240 | 34.2 | 8,760.9 | compute | DSV4-Pro/a100_sxm_80gb-x95-tensor | 78,470 | 1.00x | tensor | 54,877.36 | 13.9 | 3,548.1 | link_latency | 2.47x | 2.47x | 8.48x | 2.47x |

## The headline is a band, and each side's share of it is reported apart

Every hop latency in this model states a range, and the ratio moves inside it.
This table re-runs the whole study at both ends of those ranges three ways:
the **wafer fabric** alone (`on_wafer`, `inter_wafer`), which no GPU design touches; the
**cluster fabric** alone (`nvlink3`, `infiniband_hdr`), which is charged to both families; and
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
| DeepSeek-V4-Flash-0731 | 14,670 | 3.02x | 3.02x → 3.02x | 3.88x → 2.16x | 3.88x → 2.16x | 1.8x |
| DeepSeek-V4-Flash-0731 | 15,485 | 2.98x | 2.98x → 2.98x | 3.82x → 2.03x | 3.82x → 2.03x | 1.9x |
| DeepSeek-V4-Flash-0731 | 46,225 | 8.57x | 12.40x → 4.84x | 6.73x → 15.79x | 9.73x → 8.91x | 2.6x |
| DeepSeek-V4-Flash-0731 | 92,450 | 7.86x | 11.46x → 4.46x | 6.09x → 14.79x | 8.88x → 8.39x | 2.6x |
| DeepSeek-V4-Flash-0731 | 138,675 | 7.57x | 11.21x → 4.28x | 5.84x → 14.34x | 8.65x → 8.11x | 2.6x |
| DeepSeek-V4-Flash-0731 | 184,900 | 7.35x | 11.04x → 4.14x | 5.65x → 13.97x | 8.50x → 7.88x | 2.7x |
| DeepSeek-V4-Flash-0731 | 277,350 | 10.16x | 15.72x → 5.70x | 7.97x → 17.36x | 12.34x → 9.74x | 2.8x |
| DeepSeek-V4-Flash-0731 | 369,800 | 9.73x | 15.47x → 5.43x | 7.63x → 16.64x | 12.13x → 9.30x | 2.8x |
| DeepSeek-V4-Flash-0731 | 554,700 | 8.98x | 15.03x → 4.98x | 7.04x → 15.39x | 11.77x → 8.52x | 3.0x |
| DeepSeek-V4-Pro-0813 | 76,610 | 1.85x | 1.85x → 1.85x | 2.13x → 1.38x | 2.13x → 1.38x | 1.5x |
| DeepSeek-V4-Pro-0813 | 78,240 | 2.15x | 2.15x → 2.15x | 2.34x → 1.62x | 2.34x → 1.62x | 1.4x |
| DeepSeek-V4-Pro-0813 | 80,685 | 2.04x | 2.04x → 2.04x | 2.18x → 1.58x | 2.18x → 1.58x | 1.4x |
| DeepSeek-V4-Pro-0813 | 92,450 | 8.58x | 11.16x → 5.48x | 7.26x → 13.76x | 9.44x → 8.79x | 2.0x |
| DeepSeek-V4-Pro-0813 | 138,675 | 7.12x | 8.97x → 4.77x | 5.99x → 11.55x | 7.54x → 7.73x | 1.9x |
| DeepSeek-V4-Pro-0813 | 184,900 | 6.97x | 8.85x → 4.64x | 5.85x → 11.37x | 7.42x → 7.58x | 1.9x |
| DeepSeek-V4-Pro-0813 | 231,125 | 6.87x | 8.79x → 4.56x | 5.75x → 11.24x | 7.36x → 7.46x | 2.0x |
| DeepSeek-V4-Pro-0813 | 277,350 | 8.92x | 11.51x → 5.90x | 7.43x → 13.83x | 9.58x → 9.14x | 2.0x |
| DeepSeek-V4-Pro-0813 | 369,800 | 8.70x | 11.38x → 5.71x | 7.23x → 13.51x | 9.46x → 8.88x | 2.0x |
| DeepSeek-V4-Pro-0813 | 554,700 | 8.33x | 11.21x → 5.41x | 6.92x → 12.96x | 9.31x → 8.42x | 2.1x |
| Qwen3-8B | 2,445 | 10.78x | 10.78x → 10.78x | 13.53x → 13.34x | 13.53x → 13.34x | 1.0x |
| Qwen3-8B | 3,260 | 8.45x | 8.45x → 8.45x | 11.59x → 12.90x | 11.59x → 12.90x | 1.1x |
| Qwen3-8B | 4,075 | 4.69x | 4.69x → 4.69x | 7.27x → 11.23x | 7.27x → 11.23x | 1.5x |
| Qwen3-8B | 4,890 | 7.43x | 7.43x → 7.43x | — | — | 1.0x |
| Qwen3-8B | 5,705 | 6.59x | 6.59x → 6.59x | — | — | 1.0x |
| Qwen3-8B | 6,520 | 3.59x | 3.59x → 3.59x | — | — | 1.0x |
| Qwen3-8B | 46,225 | 8.24x | 12.89x → 4.33x | 6.09x → 16.67x | 9.52x → 8.77x | 3.0x |
| Qwen3-8B | 92,450 | 6.93x | 10.65x → 3.76x | 4.98x → 14.55x | 7.65x → 7.89x | 2.9x |
| Qwen3-8B | 138,675 | 6.19x | 9.41x → 3.44x | 4.41x → 13.18x | 6.70x → 7.32x | 3.0x |
| Qwen3-8B | 184,900 | 5.65x | 8.50x → 3.20x | 4.00x → 12.10x | 6.02x → 6.86x | 3.0x |
| Qwen3-8B | 277,350 | 7.63x | 11.32x → 4.47x | 5.70x → 13.02x | 8.46x → 7.63x | 2.5x |
| Qwen3-8B | 369,800 | 6.71x | 9.84x → 4.04x | 5.01x → 11.50x | 7.35x → 6.92x | 2.4x |
| Qwen3-8B | 554,700 | 6.04x | 9.19x → 3.62x | 4.50x → 10.39x | 6.85x → 6.23x | 2.5x |

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
| DeepSeek-V4-Flash-0731 | 8 | 6,608 | 90.0 | 546.1 | — | tensor | 436.16 | 23.8% | weight_read |
| DeepSeek-V4-Flash-0731 | 18 | 14,868 | 63.8 | 466.5 | 327.0 | tensor | 1,266.53 | 59.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 19 | 15,694 | 62.1 | 471.6 | 334.7 | tensor | 1,266.53 | 59.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 26 | 21,476 | 52.6 | 497.2 | 296.6 | tensor | 1,273.57 | 63.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 28 | 23,128 | 50.5 | 503.0 | 305.0 | tensor | 1,273.57 | 64.1% | link_latency |
| DeepSeek-V4-Flash-0731 | 31 | 25,606 | 47.6 | 510.7 | 316.4 | tensor | 1,273.57 | 65.0% | link_latency |
| DeepSeek-V4-Flash-0731 | 38 | 31,388 | 42.0 | 523.5 | 279.4 | tensor | 1,277.80 | 66.9% | link_latency |
| DeepSeek-V4-Flash-0731 | 42 | 34,692 | 39.5 | 528.9 | 245.5 | tensor | 1,280.62 | 67.7% | link_latency |
| DeepSeek-V4-Flash-0731 | 56 | 46,256 | 32.6 | 544.1 | 232.8 | tensor | 1,282.63 | 69.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 112 | 92,512 | 19.4 | 568.8 | 144.0 | tensor | 1,288.67 | 73.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 168 | 138,768 | 13.8 | 578.0 | 104.5 | tensor | 1,290.68 | 74.6% | link_latency |
| DeepSeek-V4-Flash-0731 | 224 | 185,024 | 10.8 | 582.8 | 82.1 | tensor | 1,291.69 | 75.3% | link_latency |
| DeepSeek-V4-Flash-0731 | 336 | 277,536 | 7.5 | 404.0 | 57.5 | tensor | 2,066.69 | 83.5% | link_latency |
| DeepSeek-V4-Flash-0731 | 448 | 370,048 | 5.7 | 405.2 | 44.3 | tensor | 2,067.20 | 83.8% | link_latency |
| DeepSeek-V4-Flash-0731 | 672 | 555,072 | 3.9 | 406.4 | 30.4 | tensor | 2,067.70 | 84.0% | link_latency |
| DeepSeek-V4-Pro-0813 | 48 | 39,648 | 9.8 | 248.0 | 74.7 | tensor | 1,898.20 | 47.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 56 | 46,256 | 8.8 | 254.0 | 67.5 | tensor | 1,903.20 | 48.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 93 | 76,818 | 6.1 | 270.2 | 45.5 | tensor | 1,915.69 | 51.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 95 | 78,470 | 6.0 | 270.8 | 45.8 | tensor | 1,915.69 | 51.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 98 | 80,948 | 5.8 | 271.5 | 42.6 | tensor | 1,917.04 | 52.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 112 | 92,512 | 5.2 | 274.9 | 40.7 | tensor | 1,918.19 | 52.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 139 | 114,814 | 4.4 | 279.5 | 33.0 | tensor | 1,921.52 | 53.7% | link_latency |
| DeepSeek-V4-Pro-0813 | 144 | 118,944 | 4.2 | 280.2 | 33.2 | tensor | 1,921.52 | 53.8% | link_latency |
| DeepSeek-V4-Pro-0813 | 145 | 119,770 | 4.2 | 280.3 | 31.5 | tensor | 1,922.14 | 53.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 146 | 120,596 | 4.2 | 280.5 | 31.6 | tensor | 1,922.14 | 53.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 154 | 127,204 | 4.0 | 281.5 | 30.2 | tensor | 1,922.69 | 54.1% | link_latency |
| DeepSeek-V4-Pro-0813 | 168 | 138,768 | 3.7 | 283.0 | 29.2 | tensor | 1,923.19 | 54.4% | link_latency |
| DeepSeek-V4-Pro-0813 | 224 | 185,024 | 2.9 | 287.4 | 22.8 | tensor | 1,925.69 | 55.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 280 | 231,280 | 2.4 | 290.0 | 18.7 | tensor | 1,927.19 | 55.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 336 | 277,536 | 2.0 | 221.0 | 15.8 | tensor | 3,026.19 | 66.9% | link_latency |
| DeepSeek-V4-Pro-0813 | 448 | 370,048 | 1.5 | 222.4 | 12.1 | tensor | 3,027.43 | 67.3% | link_latency |
| DeepSeek-V4-Pro-0813 | 672 | 555,072 | 1.0 | 223.7 | 8.3 | tensor | 3,028.68 | 67.8% | link_latency |
| Qwen3-8B | 3 | 2,478 | 95.3 | 258.9 | — | tensor | 363.93 | 9.4% | weight_read |
| Qwen3-8B | 4 | 3,304 | 95.3 | 334.5 | — | tensor | 364.42 | 12.2% | weight_read |
| Qwen3-8B | 5 | 4,130 | 95.3 | 405.5 | — | tensor | 364.72 | 14.8% | weight_read |
| Qwen3-8B | 6 | 4,956 | 95.3 | 472.3 | — | tensor | 364.92 | 17.2% | weight_read |
| Qwen3-8B | 7 | 5,782 | 95.2 | 535.4 | — | tensor | 365.06 | 19.5% | weight_read |
| Qwen3-8B | 8 | 6,608 | 95.2 | 594.9 | — | tensor | 365.16 | 21.7% | weight_read |
| Qwen3-8B | 56 | 46,256 | 94.5 | 789.4 | 584.9 | tensor | 1,073.83 | 84.8% | link_latency |
| Qwen3-8B | 112 | 92,512 | 94.5 | 848.7 | 573.5 | tensor | 1,078.88 | 91.6% | link_latency |
| Qwen3-8B | 168 | 138,768 | 94.5 | 870.5 | 562.6 | tensor | 1,080.57 | 94.1% | link_latency |
| Qwen3-8B | 224 | 185,024 | 94.5 | 881.8 | 552.1 | tensor | 1,081.41 | 95.4% | link_latency |
| Qwen3-8B | 336 | 277,536 | 94.5 | 565.8 | 540.6 | tensor | 1,730.25 | 97.9% | link_latency |
| Qwen3-8B | 448 | 370,048 | 94.5 | 568.2 | 540.6 | tensor | 1,730.68 | 98.3% | link_latency |
| Qwen3-8B | 672 | 555,072 | 94.5 | 570.6 | 540.6 | tensor | 1,731.10 | 98.8% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x3 | Qwen3-8B | 3 | pipeline | nvlink3 | infiniband_hdr | 2 | 5.05 us | 19,783.9 tok/s | 197,839.1 tok/s | 2 x point_to_point span 2 on nvlink3 (traversals 1.0) = 5.05 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x4 | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 364.42 us | 274.4 tok/s | 2,744.1 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 364.42 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-pipeline-x5 | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 10.11 us | 9,892.0 tok/s | 98,919.5 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.11 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | Qwen3-8B | 1 | pipeline | on_wafer | inter_wafer | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-HBMKV-array-tensor-x8 | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 365.16 us | 273.9 tok/s | 2,738.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us |
| Qwen3-8B/ROM-N6-native-HBMKV-wafer-tensor-x1 | Qwen3-8B | 1 | tensor | on_wafer | inter_wafer | 72 | 138.60 us | 721.5 tok/s | 7,215.0 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us |
| Qwen3-8B/a100_sxm_80gb-x3-pipeline | Qwen3-8B | 3 | pipeline | nvlink3 | infiniband_hdr | 2 | 5.05 us | 19,783.9 tok/s | 197,839.1 tok/s | 2 x point_to_point span 2 on nvlink3 (traversals 1.0) = 5.05 us |
| Qwen3-8B/a100_sxm_80gb-x3-tensor | Qwen3-8B | 3 | tensor | nvlink3 | infiniband_hdr | 72 | 363.93 us | 274.8 tok/s | 2,747.8 tok/s | 72 x all_reduce span 3 on nvlink3 (traversals 2.0) = 363.93 us |
| Qwen3-8B/a100_sxm_80gb-x4-pipeline | Qwen3-8B | 4 | pipeline | nvlink3 | infiniband_hdr | 3 | 7.58 us | 13,189.3 tok/s | 131,892.7 tok/s | 3 x point_to_point span 2 on nvlink3 (traversals 1.0) = 7.58 us |
| Qwen3-8B/a100_sxm_80gb-x4-tensor | Qwen3-8B | 4 | tensor | nvlink3 | infiniband_hdr | 72 | 364.42 us | 274.4 tok/s | 2,744.1 tok/s | 72 x all_reduce span 4 on nvlink3 (traversals 2.0) = 364.42 us |
| Qwen3-8B/a100_sxm_80gb-x5-pipeline | Qwen3-8B | 5 | pipeline | nvlink3 | infiniband_hdr | 4 | 10.11 us | 9,892.0 tok/s | 98,919.5 tok/s | 4 x point_to_point span 2 on nvlink3 (traversals 1.0) = 10.11 us |
| Qwen3-8B/a100_sxm_80gb-x5-tensor | Qwen3-8B | 5 | tensor | nvlink3 | infiniband_hdr | 72 | 364.72 us | 274.2 tok/s | 2,741.8 tok/s | 72 x all_reduce span 5 on nvlink3 (traversals 2.0) = 364.72 us |
| Qwen3-8B/a100_sxm_80gb-x6-pipeline | Qwen3-8B | 6 | pipeline | nvlink3 | infiniband_hdr | 5 | 12.64 us | 7,913.6 tok/s | 79,135.6 tok/s | 5 x point_to_point span 2 on nvlink3 (traversals 1.0) = 12.64 us |
| Qwen3-8B/a100_sxm_80gb-x6-tensor | Qwen3-8B | 6 | tensor | nvlink3 | infiniband_hdr | 72 | 364.92 us | 274.0 tok/s | 2,740.4 tok/s | 72 x all_reduce span 6 on nvlink3 (traversals 2.0) = 364.92 us |
| Qwen3-8B/a100_sxm_80gb-x7-pipeline | Qwen3-8B | 7 | pipeline | nvlink3 | infiniband_hdr | 6 | 15.16 us | 6,594.6 tok/s | 65,946.4 tok/s | 6 x point_to_point span 2 on nvlink3 (traversals 1.0) = 15.16 us |
| Qwen3-8B/a100_sxm_80gb-x7-tensor | Qwen3-8B | 7 | tensor | nvlink3 | infiniband_hdr | 72 | 365.06 us | 273.9 tok/s | 2,739.3 tok/s | 72 x all_reduce span 7 on nvlink3 (traversals 2.0) = 365.06 us |
| Qwen3-8B/a100_sxm_80gb-x8-pipeline | Qwen3-8B | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.69 us | 5,652.5 tok/s | 56,525.4 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.69 us |
| Qwen3-8B/a100_sxm_80gb-x8-tensor | Qwen3-8B | 8 | tensor | nvlink3 | infiniband_hdr | 72 | 365.16 us | 273.9 tok/s | 2,738.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us |
| Qwen3-8B/a100_sxm_80gb-x56-pipeline | Qwen3-8B | 56 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x56-tensor | Qwen3-8B | 56 | tensor | nvlink3 | infiniband_hdr | 144 | 1,073.83 us | 93.1 tok/s | 931.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 708.67 us |
| Qwen3-8B/a100_sxm_80gb-x56-hybrid | Qwen3-8B | 56 | hybrid | nvlink3 | infiniband_hdr | 78 | 394.13 us | 253.7 tok/s | 2,537.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.97 us |
| Qwen3-8B/a100_sxm_80gb-x112-pipeline | Qwen3-8B | 112 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x112-tensor | Qwen3-8B | 112 | tensor | nvlink3 | infiniband_hdr | 144 | 1,078.88 us | 92.7 tok/s | 926.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 713.72 us |
| Qwen3-8B/a100_sxm_80gb-x112-hybrid | Qwen3-8B | 112 | hybrid | nvlink3 | infiniband_hdr | 85 | 427.92 us | 233.7 tok/s | 2,336.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.76 us |
| Qwen3-8B/a100_sxm_80gb-x168-pipeline | Qwen3-8B | 168 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x168-tensor | Qwen3-8B | 168 | tensor | nvlink3 | infiniband_hdr | 144 | 1,080.57 us | 92.5 tok/s | 925.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 715.41 us |
| Qwen3-8B/a100_sxm_80gb-x168-hybrid | Qwen3-8B | 168 | hybrid | nvlink3 | infiniband_hdr | 92 | 461.71 us | 216.6 tok/s | 2,165.8 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.55 us |
| Qwen3-8B/a100_sxm_80gb-x224-pipeline | Qwen3-8B | 224 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x224-tensor | Qwen3-8B | 224 | tensor | nvlink3 | infiniband_hdr | 144 | 1,081.41 us | 92.5 tok/s | 924.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 716.25 us |
| Qwen3-8B/a100_sxm_80gb-x224-hybrid | Qwen3-8B | 224 | hybrid | nvlink3 | infiniband_hdr | 99 | 495.51 us | 201.8 tok/s | 2,018.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 130.35 us |
| Qwen3-8B/a100_sxm_80gb-x336-pipeline | Qwen3-8B | 336 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x336-tensor | Qwen3-8B | 336 | tensor | nvlink3 | infiniband_hdr | 144 | 1,730.25 us | 57.8 tok/s | 577.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,365.09 us |
| Qwen3-8B/a100_sxm_80gb-x336-hybrid | Qwen3-8B | 336 | hybrid | nvlink3 | infiniband_hdr | 107 | 534.13 us | 187.2 tok/s | 1,872.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.97 us |
| Qwen3-8B/a100_sxm_80gb-x448-pipeline | Qwen3-8B | 448 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x448-tensor | Qwen3-8B | 448 | tensor | nvlink3 | infiniband_hdr | 144 | 1,730.68 us | 57.8 tok/s | 577.8 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,365.51 us |
| Qwen3-8B/a100_sxm_80gb-x448-hybrid | Qwen3-8B | 448 | hybrid | nvlink3 | infiniband_hdr | 107 | 534.13 us | 187.2 tok/s | 1,872.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.97 us |
| Qwen3-8B/a100_sxm_80gb-x672-pipeline | Qwen3-8B | 672 | pipeline | nvlink3 | infiniband_hdr | 35 | 97.66 us | 1,024.0 tok/s | 10,239.9 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| Qwen3-8B/a100_sxm_80gb-x672-tensor | Qwen3-8B | 672 | tensor | nvlink3 | infiniband_hdr | 144 | 1,731.10 us | 57.8 tok/s | 577.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,365.94 us |
| Qwen3-8B/a100_sxm_80gb-x672-hybrid | Qwen3-8B | 672 | hybrid | nvlink3 | infiniband_hdr | 107 | 534.13 us | 187.2 tok/s | 1,872.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 168.97 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-pipeline-x18 | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 47.56 us | 2,102.4 tok/s | 21,023.9 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 37.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-tensor-x18 | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 1,266.53 us | 79.0 tok/s | 789.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-SRAMKV-array-hybrid-x18 | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 445.82 us | 224.3 tok/s | 2,243.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-pipeline-x19 | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 50.09 us | 1,996.3 tok/s | 19,963.2 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | DeepSeek-V4-Flash-0731 | 1 | pipeline | on_wafer | inter_wafer | 42 | 5.25 us | 19,047.6 tok/s | 190,475.7 tok/s | 42 x point_to_point span 2 on on_wafer (traversals 1.0) = 5.25 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-tensor-x18 | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 1,266.53 us | 79.0 tok/s | 789.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | DeepSeek-V4-Flash-0731 | 1 | tensor | on_wafer | inter_wafer | 86 | 165.55 us | 604.0 tok/s | 6,040.5 tok/s | 86 x all_reduce span 57 on on_wafer (traversals 15.4) = 165.55 us |
| DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x19 | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 445.82 us | 224.3 tok/s | 2,243.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x8-pipeline | DeepSeek-V4-Flash-0731 | 8 | pipeline | nvlink3 | infiniband_hdr | 7 | 17.69 us | 5,652.5 tok/s | 56,525.4 tok/s | 7 x point_to_point span 2 on nvlink3 (traversals 1.0) = 17.69 us |
| DSV4-Flash/a100_sxm_80gb-x8-tensor | DeepSeek-V4-Flash-0731 | 8 | tensor | nvlink3 | infiniband_hdr | 86 | 436.16 us | 229.3 tok/s | 2,292.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us |
| DSV4-Flash/a100_sxm_80gb-x18-pipeline | DeepSeek-V4-Flash-0731 | 18 | pipeline | nvlink3 | infiniband_hdr | 17 | 47.56 us | 2,102.4 tok/s | 21,023.9 tok/s | 15 x point_to_point span 2 on nvlink3 (traversals 1.0) = 37.91 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x18-tensor | DeepSeek-V4-Flash-0731 | 18 | tensor | nvlink3 | infiniband_hdr | 172 | 1,266.53 us | 79.0 tok/s | 789.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/a100_sxm_80gb-x18-hybrid | DeepSeek-V4-Flash-0731 | 18 | hybrid | nvlink3 | infiniband_hdr | 88 | 445.82 us | 224.3 tok/s | 2,243.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x19-pipeline | DeepSeek-V4-Flash-0731 | 19 | pipeline | nvlink3 | infiniband_hdr | 18 | 50.09 us | 1,996.3 tok/s | 19,963.2 tok/s | 16 x point_to_point span 2 on nvlink3 (traversals 1.0) = 40.44 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x19-tensor | DeepSeek-V4-Flash-0731 | 19 | tensor | nvlink3 | infiniband_hdr | 172 | 1,266.53 us | 79.0 tok/s | 789.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 3 on infiniband_hdr (traversals 2.0) = 830.36 us |
| DSV4-Flash/a100_sxm_80gb-x19-hybrid | DeepSeek-V4-Flash-0731 | 19 | hybrid | nvlink3 | infiniband_hdr | 88 | 445.82 us | 224.3 tok/s | 2,243.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 2 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.66 us |
| DSV4-Flash/a100_sxm_80gb-x26-pipeline | DeepSeek-V4-Flash-0731 | 26 | pipeline | nvlink3 | infiniband_hdr | 25 | 70.08 us | 1,426.9 tok/s | 14,268.6 tok/s | 22 x point_to_point span 2 on nvlink3 (traversals 1.0) = 55.60 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x26-tensor | DeepSeek-V4-Flash-0731 | 26 | tensor | nvlink3 | infiniband_hdr | 172 | 1,273.57 us | 78.5 tok/s | 785.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x26-hybrid | DeepSeek-V4-Flash-0731 | 26 | hybrid | nvlink3 | infiniband_hdr | 89 | 450.65 us | 221.9 tok/s | 2,219.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x28-pipeline | DeepSeek-V4-Flash-0731 | 28 | pipeline | nvlink3 | infiniband_hdr | 27 | 75.14 us | 1,330.9 tok/s | 13,308.8 tok/s | 24 x point_to_point span 2 on nvlink3 (traversals 1.0) = 60.66 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x28-tensor | DeepSeek-V4-Flash-0731 | 28 | tensor | nvlink3 | infiniband_hdr | 172 | 1,273.57 us | 78.5 tok/s | 785.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x28-hybrid | DeepSeek-V4-Flash-0731 | 28 | hybrid | nvlink3 | infiniband_hdr | 89 | 450.65 us | 221.9 tok/s | 2,219.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x31-pipeline | DeepSeek-V4-Flash-0731 | 31 | pipeline | nvlink3 | infiniband_hdr | 30 | 82.72 us | 1,208.9 tok/s | 12,088.9 tok/s | 27 x point_to_point span 2 on nvlink3 (traversals 1.0) = 68.24 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x31-tensor | DeepSeek-V4-Flash-0731 | 31 | tensor | nvlink3 | infiniband_hdr | 172 | 1,273.57 us | 78.5 tok/s | 785.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 4 on infiniband_hdr (traversals 2.0) = 837.41 us |
| DSV4-Flash/a100_sxm_80gb-x31-hybrid | DeepSeek-V4-Flash-0731 | 31 | hybrid | nvlink3 | infiniband_hdr | 89 | 450.65 us | 221.9 tok/s | 2,219.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 3 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.48 us |
| DSV4-Flash/a100_sxm_80gb-x38-pipeline | DeepSeek-V4-Flash-0731 | 38 | pipeline | nvlink3 | infiniband_hdr | 37 | 102.71 us | 973.6 tok/s | 9,736.0 tok/s | 33 x point_to_point span 2 on nvlink3 (traversals 1.0) = 83.40 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| DSV4-Flash/a100_sxm_80gb-x38-tensor | DeepSeek-V4-Flash-0731 | 38 | tensor | nvlink3 | infiniband_hdr | 172 | 1,277.80 us | 78.3 tok/s | 782.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 841.63 us |
| DSV4-Flash/a100_sxm_80gb-x38-hybrid | DeepSeek-V4-Flash-0731 | 38 | hybrid | nvlink3 | infiniband_hdr | 90 | 455.48 us | 219.6 tok/s | 2,195.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 19.31 us |
| DSV4-Flash/a100_sxm_80gb-x42-pipeline | DeepSeek-V4-Flash-0731 | 42 | pipeline | nvlink3 | infiniband_hdr | 41 | 115.12 us | 868.6 tok/s | 8,686.5 tok/s | 36 x point_to_point span 2 on nvlink3 (traversals 1.0) = 90.98 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x42-tensor | DeepSeek-V4-Flash-0731 | 42 | tensor | nvlink3 | infiniband_hdr | 172 | 1,280.62 us | 78.1 tok/s | 780.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 844.45 us |
| DSV4-Flash/a100_sxm_80gb-x42-hybrid | DeepSeek-V4-Flash-0731 | 42 | hybrid | nvlink3 | infiniband_hdr | 91 | 460.30 us | 217.2 tok/s | 2,172.5 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Flash-0731 | 56 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Flash-0731 | 56 | tensor | nvlink3 | infiniband_hdr | 172 | 1,282.63 us | 78.0 tok/s | 779.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 846.46 us |
| DSV4-Flash/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Flash-0731 | 56 | hybrid | nvlink3 | infiniband_hdr | 92 | 465.13 us | 215.0 tok/s | 2,149.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.97 us |
| DSV4-Flash/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Flash-0731 | 112 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Flash-0731 | 112 | tensor | nvlink3 | infiniband_hdr | 172 | 1,288.67 us | 77.6 tok/s | 776.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 852.50 us |
| DSV4-Flash/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Flash-0731 | 112 | hybrid | nvlink3 | infiniband_hdr | 99 | 498.92 us | 200.4 tok/s | 2,004.3 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 62.76 us |
| DSV4-Flash/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Flash-0731 | 168 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Flash-0731 | 168 | tensor | nvlink3 | infiniband_hdr | 172 | 1,290.68 us | 77.5 tok/s | 774.8 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 854.52 us |
| DSV4-Flash/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Flash-0731 | 168 | hybrid | nvlink3 | infiniband_hdr | 106 | 532.72 us | 187.7 tok/s | 1,877.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.55 us |
| DSV4-Flash/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Flash-0731 | 224 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Flash-0731 | 224 | tensor | nvlink3 | infiniband_hdr | 172 | 1,291.69 us | 77.4 tok/s | 774.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 855.52 us |
| DSV4-Flash/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Flash-0731 | 224 | hybrid | nvlink3 | infiniband_hdr | 113 | 566.51 us | 176.5 tok/s | 1,765.2 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 130.35 us |
| DSV4-Flash/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Flash-0731 | 336 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Flash-0731 | 336 | tensor | nvlink3 | infiniband_hdr | 172 | 2,066.69 us | 48.4 tok/s | 483.9 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,630.53 us |
| DSV4-Flash/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Flash-0731 | 336 | hybrid | nvlink3 | infiniband_hdr | 127 | 634.10 us | 157.7 tok/s | 1,577.0 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.93 us |
| DSV4-Flash/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Flash-0731 | 448 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Flash-0731 | 448 | tensor | nvlink3 | infiniband_hdr | 172 | 2,067.20 us | 48.4 tok/s | 483.7 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,631.03 us |
| DSV4-Flash/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Flash-0731 | 448 | hybrid | nvlink3 | infiniband_hdr | 128 | 638.93 us | 156.5 tok/s | 1,565.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.76 us |
| DSV4-Flash/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Flash-0731 | 672 | pipeline | nvlink3 | infiniband_hdr | 42 | 117.65 us | 850.0 tok/s | 8,499.9 tok/s | 37 x point_to_point span 2 on nvlink3 (traversals 1.0) = 93.51 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 24.14 us |
| DSV4-Flash/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Flash-0731 | 672 | tensor | nvlink3 | infiniband_hdr | 172 | 2,067.70 us | 48.4 tok/s | 483.6 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 86 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,631.53 us |
| DSV4-Flash/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Flash-0731 | 672 | hybrid | nvlink3 | infiniband_hdr | 128 | 638.93 us | 156.5 tok/s | 1,565.1 tok/s | 86 x all_reduce span 8 on nvlink3 (traversals 2.0) = 436.16 us; 42 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 202.76 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-pipeline-x96 | DeepSeek-V4-Pro-0813 | 96 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | DeepSeek-V4-Pro-0813 | 2 | pipeline | on_wafer | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-tensor-x94 | DeepSeek-V4-Pro-0813 | 94 | tensor | nvlink3 | infiniband_hdr | 244 | 1,915.69 us | 52.2 tok/s | 522.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x2 | DeepSeek-V4-Pro-0813 | 2 | tensor | on_wafer | inter_wafer | 244 | 1,472.34 us | 67.9 tok/s | 679.2 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 2 on inter_wafer (traversals 2.0) = 1,237.49 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-array-hybrid-x96 | DeepSeek-V4-Pro-0813 | 96 | hybrid | nvlink3 | infiniband_hdr | 133 | 681.11 us | 146.8 tok/s | 1,468.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | DeepSeek-V4-Pro-0813 | 2 | hybrid | on_wafer | inter_wafer | 123 | 239.95 us | 416.8 tok/s | 4,167.6 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-pipeline-x99 | DeepSeek-V4-Pro-0813 | 99 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5 | DeepSeek-V4-Pro-0813 | 5 | pipeline | on_wafer | inter_wafer | 60 | 12.47 us | 8,018.9 tok/s | 80,188.6 tok/s | 59 x point_to_point span 2 on on_wafer (traversals 1.0) = 7.38 us; 1 x point_to_point span 2 on inter_wafer (traversals 1.0) = 5.10 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-tensor-x96 | DeepSeek-V4-Pro-0813 | 96 | tensor | nvlink3 | infiniband_hdr | 244 | 1,915.69 us | 52.2 tok/s | 522.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-tensor-x5 | DeepSeek-V4-Pro-0813 | 5 | tensor | on_wafer | inter_wafer | 244 | 1,482.83 us | 67.4 tok/s | 674.4 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 122 x all_reduce span 5 on inter_wafer (traversals 2.0) = 1,247.98 us |
| DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x99 | DeepSeek-V4-Pro-0813 | 99 | hybrid | nvlink3 | infiniband_hdr | 134 | 686.18 us | 145.7 tok/s | 1,457.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.88 us |
| DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5 | DeepSeek-V4-Pro-0813 | 5 | hybrid | on_wafer | inter_wafer | 126 | 255.23 us | 391.8 tok/s | 3,918.0 tok/s | 122 x all_reduce span 57 on on_wafer (traversals 15.4) = 234.85 us; 4 x point_to_point span 2 on inter_wafer (traversals 1.0) = 20.38 us |
| DSV4-Pro/a100_sxm_80gb-x48-pipeline | DeepSeek-V4-Pro-0813 | 48 | pipeline | nvlink3 | infiniband_hdr | 47 | 132.37 us | 755.4 tok/s | 7,554.3 tok/s | 42 x point_to_point span 2 on nvlink3 (traversals 1.0) = 107.01 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.37 us |
| DSV4-Pro/a100_sxm_80gb-x48-tensor | DeepSeek-V4-Pro-0813 | 48 | tensor | nvlink3 | infiniband_hdr | 244 | 1,898.20 us | 52.7 tok/s | 526.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 6 on infiniband_hdr (traversals 2.0) = 1,272.90 us |
| DSV4-Pro/a100_sxm_80gb-x48-hybrid | DeepSeek-V4-Pro-0813 | 48 | hybrid | nvlink3 | infiniband_hdr | 127 | 650.67 us | 153.7 tok/s | 1,536.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 5 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.37 us |
| DSV4-Pro/a100_sxm_80gb-x56-pipeline | DeepSeek-V4-Pro-0813 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 155.28 us | 644.0 tok/s | 6,439.9 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.44 us |
| DSV4-Pro/a100_sxm_80gb-x56-tensor | DeepSeek-V4-Pro-0813 | 56 | tensor | nvlink3 | infiniband_hdr | 244 | 1,903.20 us | 52.5 tok/s | 525.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 1,277.90 us |
| DSV4-Pro/a100_sxm_80gb-x56-hybrid | DeepSeek-V4-Pro-0813 | 56 | hybrid | nvlink3 | infiniband_hdr | 128 | 655.74 us | 152.5 tok/s | 1,525.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.44 us |
| DSV4-Pro/a100_sxm_80gb-x93-pipeline | DeepSeek-V4-Pro-0813 | 93 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x93-tensor | DeepSeek-V4-Pro-0813 | 93 | tensor | nvlink3 | infiniband_hdr | 244 | 1,915.69 us | 52.2 tok/s | 522.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/a100_sxm_80gb-x93-hybrid | DeepSeek-V4-Pro-0813 | 93 | hybrid | nvlink3 | infiniband_hdr | 133 | 681.11 us | 146.8 tok/s | 1,468.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/a100_sxm_80gb-x95-pipeline | DeepSeek-V4-Pro-0813 | 95 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x95-tensor | DeepSeek-V4-Pro-0813 | 95 | tensor | nvlink3 | infiniband_hdr | 244 | 1,915.69 us | 52.2 tok/s | 522.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 1,290.39 us |
| DSV4-Pro/a100_sxm_80gb-x95-hybrid | DeepSeek-V4-Pro-0813 | 95 | hybrid | nvlink3 | infiniband_hdr | 133 | 681.11 us | 146.8 tok/s | 1,468.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.81 us |
| DSV4-Pro/a100_sxm_80gb-x98-pipeline | DeepSeek-V4-Pro-0813 | 98 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x98-tensor | DeepSeek-V4-Pro-0813 | 98 | tensor | nvlink3 | infiniband_hdr | 244 | 1,917.04 us | 52.2 tok/s | 521.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 1,291.73 us |
| DSV4-Pro/a100_sxm_80gb-x98-hybrid | DeepSeek-V4-Pro-0813 | 98 | hybrid | nvlink3 | infiniband_hdr | 134 | 686.18 us | 145.7 tok/s | 1,457.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 60.88 us |
| DSV4-Pro/a100_sxm_80gb-x112-pipeline | DeepSeek-V4-Pro-0813 | 112 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x112-tensor | DeepSeek-V4-Pro-0813 | 112 | tensor | nvlink3 | infiniband_hdr | 244 | 1,918.19 us | 52.1 tok/s | 521.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 1,292.89 us |
| DSV4-Pro/a100_sxm_80gb-x112-hybrid | DeepSeek-V4-Pro-0813 | 112 | hybrid | nvlink3 | infiniband_hdr | 135 | 691.26 us | 144.7 tok/s | 1,446.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.95 us |
| DSV4-Pro/a100_sxm_80gb-x139-pipeline | DeepSeek-V4-Pro-0813 | 139 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x139-tensor | DeepSeek-V4-Pro-0813 | 139 | tensor | nvlink3 | infiniband_hdr | 244 | 1,921.52 us | 52.0 tok/s | 520.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 1,296.22 us |
| DSV4-Pro/a100_sxm_80gb-x139-hybrid | DeepSeek-V4-Pro-0813 | 139 | hybrid | nvlink3 | infiniband_hdr | 139 | 711.55 us | 140.5 tok/s | 1,405.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 86.25 us |
| DSV4-Pro/a100_sxm_80gb-x144-pipeline | DeepSeek-V4-Pro-0813 | 144 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x144-tensor | DeepSeek-V4-Pro-0813 | 144 | tensor | nvlink3 | infiniband_hdr | 244 | 1,921.52 us | 52.0 tok/s | 520.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 1,296.22 us |
| DSV4-Pro/a100_sxm_80gb-x144-hybrid | DeepSeek-V4-Pro-0813 | 144 | hybrid | nvlink3 | infiniband_hdr | 139 | 711.55 us | 140.5 tok/s | 1,405.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 86.25 us |
| DSV4-Pro/a100_sxm_80gb-x145-pipeline | DeepSeek-V4-Pro-0813 | 145 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x145-tensor | DeepSeek-V4-Pro-0813 | 145 | tensor | nvlink3 | infiniband_hdr | 244 | 1,922.14 us | 52.0 tok/s | 520.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 1,296.83 us |
| DSV4-Pro/a100_sxm_80gb-x145-hybrid | DeepSeek-V4-Pro-0813 | 145 | hybrid | nvlink3 | infiniband_hdr | 140 | 716.63 us | 139.5 tok/s | 1,395.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.32 us |
| DSV4-Pro/a100_sxm_80gb-x146-pipeline | DeepSeek-V4-Pro-0813 | 146 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x146-tensor | DeepSeek-V4-Pro-0813 | 146 | tensor | nvlink3 | infiniband_hdr | 244 | 1,922.14 us | 52.0 tok/s | 520.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 1,296.83 us |
| DSV4-Pro/a100_sxm_80gb-x146-hybrid | DeepSeek-V4-Pro-0813 | 146 | hybrid | nvlink3 | infiniband_hdr | 140 | 716.63 us | 139.5 tok/s | 1,395.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 91.32 us |
| DSV4-Pro/a100_sxm_80gb-x154-pipeline | DeepSeek-V4-Pro-0813 | 154 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x154-tensor | DeepSeek-V4-Pro-0813 | 154 | tensor | nvlink3 | infiniband_hdr | 244 | 1,922.69 us | 52.0 tok/s | 520.1 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 1,297.39 us |
| DSV4-Pro/a100_sxm_80gb-x154-hybrid | DeepSeek-V4-Pro-0813 | 154 | hybrid | nvlink3 | infiniband_hdr | 141 | 721.70 us | 138.6 tok/s | 1,385.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 96.40 us |
| DSV4-Pro/a100_sxm_80gb-x168-pipeline | DeepSeek-V4-Pro-0813 | 168 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x168-tensor | DeepSeek-V4-Pro-0813 | 168 | tensor | nvlink3 | infiniband_hdr | 244 | 1,923.19 us | 52.0 tok/s | 520.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 1,297.88 us |
| DSV4-Pro/a100_sxm_80gb-x168-hybrid | DeepSeek-V4-Pro-0813 | 168 | hybrid | nvlink3 | infiniband_hdr | 142 | 726.77 us | 137.6 tok/s | 1,375.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 101.47 us |
| DSV4-Pro/a100_sxm_80gb-x224-pipeline | DeepSeek-V4-Pro-0813 | 224 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x224-tensor | DeepSeek-V4-Pro-0813 | 224 | tensor | nvlink3 | infiniband_hdr | 244 | 1,925.69 us | 51.9 tok/s | 519.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 1,300.38 us |
| DSV4-Pro/a100_sxm_80gb-x224-hybrid | DeepSeek-V4-Pro-0813 | 224 | hybrid | nvlink3 | infiniband_hdr | 149 | 762.29 us | 131.2 tok/s | 1,311.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 136.98 us |
| DSV4-Pro/a100_sxm_80gb-x280-pipeline | DeepSeek-V4-Pro-0813 | 280 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x280-tensor | DeepSeek-V4-Pro-0813 | 280 | tensor | nvlink3 | infiniband_hdr | 244 | 1,927.19 us | 51.9 tok/s | 518.9 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 1,301.88 us |
| DSV4-Pro/a100_sxm_80gb-x280-hybrid | DeepSeek-V4-Pro-0813 | 280 | hybrid | nvlink3 | infiniband_hdr | 156 | 797.80 us | 125.3 tok/s | 1,253.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 172.50 us |
| DSV4-Pro/a100_sxm_80gb-x336-pipeline | DeepSeek-V4-Pro-0813 | 336 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x336-tensor | DeepSeek-V4-Pro-0813 | 336 | tensor | nvlink3 | infiniband_hdr | 244 | 3,026.19 us | 33.0 tok/s | 330.4 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 2,400.88 us |
| DSV4-Pro/a100_sxm_80gb-x336-hybrid | DeepSeek-V4-Pro-0813 | 336 | hybrid | nvlink3 | infiniband_hdr | 163 | 833.31 us | 120.0 tok/s | 1,200.0 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 208.01 us |
| DSV4-Pro/a100_sxm_80gb-x448-pipeline | DeepSeek-V4-Pro-0813 | 448 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x448-tensor | DeepSeek-V4-Pro-0813 | 448 | tensor | nvlink3 | infiniband_hdr | 244 | 3,027.43 us | 33.0 tok/s | 330.3 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 2,402.13 us |
| DSV4-Pro/a100_sxm_80gb-x448-hybrid | DeepSeek-V4-Pro-0813 | 448 | hybrid | nvlink3 | infiniband_hdr | 177 | 904.34 us | 110.6 tok/s | 1,105.8 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 279.04 us |
| DSV4-Pro/a100_sxm_80gb-x672-pipeline | DeepSeek-V4-Pro-0813 | 672 | pipeline | nvlink3 | infiniband_hdr | 60 | 170.55 us | 586.3 tok/s | 5,863.5 tok/s | 53 x point_to_point span 2 on nvlink3 (traversals 1.0) = 135.03 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.51 us |
| DSV4-Pro/a100_sxm_80gb-x672-tensor | DeepSeek-V4-Pro-0813 | 672 | tensor | nvlink3 | infiniband_hdr | 244 | 3,028.68 us | 33.0 tok/s | 330.2 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 122 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 2,403.38 us |
| DSV4-Pro/a100_sxm_80gb-x672-hybrid | DeepSeek-V4-Pro-0813 | 672 | hybrid | nvlink3 | infiniband_hdr | 182 | 929.71 us | 107.6 tok/s | 1,075.6 tok/s | 122 x all_reduce span 8 on nvlink3 (traversals 2.0) = 625.30 us; 60 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 304.41 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | array | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x1-romfill | 46,225 | 6,505.3 | 0.141 | 3,509.6 (4,890) | 6,505.3 (46,225) | 1.85x | link_latency |
| Qwen3-8B | 2 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,174.3 | 0.045 | 1,755.0 (6,520) | 4,174.3 (92,450) | 2.38x | link_latency |
| Qwen3-8B | 4 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4-romfill | 184,900 | 4,005.3 | 0.022 | 1,265.1 (4,075) | 4,005.3 (184,900) | 3.17x | link_latency |
| Qwen3-8B | 8 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,705.2 | 0.010 | 1,253.1 (6,520) | 3,705.2 (369,800) | 2.96x | link_latency |
| Qwen3-8B | 16 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 3,121.8 | 0.006 | 635.8 (6,520) | 3,121.8 (554,700) | 4.91x | link_latency |
| Qwen3-8B | 32 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,266.5 | 0.004 | 320.3 (6,520) | 2,266.5 (554,700) | 7.08x | kv_read |
| Qwen3-8B | 64 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,464.2 | 0.003 | 160.7 (6,520) | 1,464.2 (554,700) | 9.11x | kv_read |
| Qwen3-8B | 256 | wafer | array | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 468.7 | 0.001 | 40.3 (6,520) | 468.7 (554,700) | 11.63x | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,663.6 | 0.101 | 1,407.1 (14,670) | 4,663.6 (46,225) | 3.31x | link_latency |
| DeepSeek-V4-Flash-0731 | 2 | wafer | wafer | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-romfill | 46,225 | 4,590.8 | 0.099 | 1,407.1 (15,485) | 4,590.8 (46,225) | 3.26x | link_latency |
| DeepSeek-V4-Flash-0731 | 4 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2-romfill | 92,450 | 4,392.3 | 0.048 | 1,402.6 (15,485) | 4,392.3 (92,450) | 3.13x | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3-romfill | 138,675 | 4,022.0 | 0.029 | 1,069.0 (15,485) | 4,022.0 (138,675) | 3.76x | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x6-romfill | 277,350 | 3,786.9 | 0.014 | 703.1 (15,485) | 3,786.9 (277,350) | 5.39x | link_latency |
| DeepSeek-V4-Flash-0731 | 32 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8-romfill | 369,800 | 3,263.4 | 0.009 | 516.8 (15,485) | 3,263.4 (369,800) | 6.31x | link_latency |
| DeepSeek-V4-Flash-0731 | 64 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 2,780.4 | 0.005 | 262.4 (15,485) | 2,780.4 (554,700) | 10.60x | link_latency |
| DeepSeek-V4-Flash-0731 | 256 | wafer | array | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,336.9 | 0.002 | 66.4 (15,485) | 1,336.9 (554,700) | 20.15x | kv_read |
| DeepSeek-V4-Pro-0813 | 1 | wafer | wafer | DSV4-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 2,359.5 | 0.026 | 582.9 (78,240) | 2,359.5 (92,450) | 4.05x | link_latency |
| DeepSeek-V4-Pro-0813 | 2 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 1,992.0 | 0.009 | 553.8 (80,685) | 1,992.0 (231,125) | 3.60x | link_latency |
| DeepSeek-V4-Pro-0813 | 4 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 1,992.0 | 0.009 | 553.8 (80,685) | 1,992.0 (231,125) | 3.60x | link_latency |
| DeepSeek-V4-Pro-0813 | 8 | wafer | wafer | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-romfill | 231,125 | 1,877.9 | 0.008 | 553.8 (80,685) | 1,877.9 (231,125) | 3.39x | link_latency |
| DeepSeek-V4-Pro-0813 | 16 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,858.7 | 0.003 | 507.8 (80,685) | 1,858.7 (554,700) | 3.66x | link_latency |
| DeepSeek-V4-Pro-0813 | 32 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 1,341.9 | 0.002 | 306.7 (80,685) | 1,341.9 (554,700) | 4.38x | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 842.5 | 0.002 | 171.1 (80,685) | 842.5 (554,700) | 4.92x | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | wafer | array | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 260.6 | 0.000 | 49.0 (80,685) | 260.6 (554,700) | 5.32x | kv_read |

## The two ROM floorplans on one die

Both machines hold the same 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 216.8 mm2 | 346.9 mm2 |
| compute block | 451.5 mm2 | 16.3 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 305.1 mm2 |
| sustained fp8 compute roof | 2.214e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.107e+14 | n/a |
| weight bytes/s the array supplies | 4.589e+13 | 4.589e+13 |
| **can the compute block be fed?** | **0.41x** | there is nothing to feed |
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
array to starve: the storage machine's 451 mm2 of MAC array can be fed at only 0.41x of what it
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
| DeepSeek-V4-Flash-0731 | 256 | 574.9 MB | 56.8 mm2 | 1.14 mm2 (2.0%) | 14,532 mm2 | 291 mm2 | 16,478 mm2 = 20.2 reticles |
| DeepSeek-V4-Pro-0813 | 384 | 2,140.8 MB | 211.4 mm2 | 4.23 mm2 (2.0%) | 81,172 mm2 | 1,623 mm2 | 88,150 mm2 = 108.2 reticles |

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
| Qwen3-8B | 1 | sram | 12,310.3 | 13,032.3 | 13,032.3 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 2 | sram | 12,310.3 | 13,032.3 | 13,032.3 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 4 | sram | 12,310.3 | 13,032.3 | 13,032.3 | 0.94x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 8 | sram | 19,516.3 | 13,032.3 | 13,032.3 | 1.50x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 16 | sram | 30,749.2 | 13,032.3 | 13,032.3 | 2.36x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 32 | sram | 46,972.0 | 13,032.3 | 13,032.3 | 3.60x | 1.00x | weight_read | weight_read | weight_read |
| Qwen3-8B | 64 | sram | 70,876.5 | 13,035.7 | 13,035.7 | 5.44x | 1.00x | kv_read | weight_read | weight_read |
| Qwen3-8B | 256 | sram | 119,989.1 | 12,331.5 | 12,331.5 | 9.73x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 1 | rom | 132,979.7 | 12,310.3 | 12,310.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 2 | rom | 132,979.7 | 12,310.3 | 12,310.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 4 | rom | 132,979.7 | 12,310.3 | 12,310.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 8 | rom | 132,979.7 | 12,310.3 | 12,310.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 16 | rom | 132,979.7 | 12,310.3 | 12,310.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 32 | rom | 132,979.7 | 12,310.3 | 12,310.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 64 | rom | 132,979.7 | 12,313.3 | 12,313.3 | 10.80x | 1.00x | kv_read | kv_read | kv_read |
| Qwen3-8B | 256 | rom | 132,979.7 | 12,331.5 | 12,331.5 | 10.78x | 1.00x | kv_read | kv_read | kv_read |
| DeepSeek-V4-Flash-0731 | 1 | sram | 13,018.3 | 13,018.3 | 13,018.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | sram | 13,018.3 | 13,018.3 | 13,018.3 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | sram | 15,359.2 | 13,018.3 | 13,533.3 | 1.18x | 1.04x | link_latency | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 8 | sram | 23,145.6 | 13,018.3 | 23,630.2 | 1.78x | 1.82x | kv_read | weight_read | link_latency |
| DeepSeek-V4-Flash-0731 | 16 | sram | 43,242.1 | 13,018.3 | 40,408.9 | 3.32x | 3.10x | link_latency | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 32 | sram | 72,469.7 | 13,018.3 | 66,193.5 | 5.57x | 5.08x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 64 | sram | 111,977.1 | 13,023.2 | 41,597.6 | 8.60x | 3.19x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 256 | sram | 261,261.9 | 13,052.9 | 88,442.0 | 20.02x | 6.78x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 1 | rom | 273,830.7 | 28,756.6 | 28,756.6 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 2 | rom | 273,830.7 | 28,756.6 | 28,756.6 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 4 | rom | 273,830.7 | 28,756.6 | 28,756.6 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 8 | rom | 273,830.7 | 28,756.6 | 28,756.6 | 9.52x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 16 | rom | 273,830.7 | 28,756.6 | 31,004.5 | 9.52x | 1.08x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 32 | rom | 273,830.7 | 28,756.6 | 37,344.5 | 9.52x | 1.30x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Flash-0731 | 64 | rom | 273,830.7 | 28,780.3 | 48,683.8 | 9.51x | 1.69x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Flash-0731 | 256 | rom | 342,257.8 | 28,925.9 | 110,735.9 | 11.83x | 3.83x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | sram | 11,751.3 | 11,743.8 | 11,743.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | sram | 11,751.3 | 11,743.8 | 11,743.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | sram | 11,751.3 | 11,743.8 | 11,743.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | sram | 11,751.3 | 11,743.8 | 11,743.8 | 1.00x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | sram | 20,376.3 | 11,743.8 | 19,635.9 | 1.74x | 1.67x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | sram | 33,100.8 | 11,743.8 | 24,164.7 | 2.82x | 2.06x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 64 | sram | 48,123.5 | 11,743.8 | 26,891.9 | 4.10x | 2.29x | weight_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | sram | 66,724.0 | 11,743.8 | 52,670.7 | 5.68x | 4.48x | kv_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 1 | rom | 51,394.5 | 24,318.5 | 24,318.5 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 2 | rom | 51,394.5 | 24,318.5 | 24,318.5 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 4 | rom | 51,394.5 | 24,318.5 | 24,318.5 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 8 | rom | 51,394.5 | 24,318.5 | 24,318.5 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 16 | rom | 51,394.5 | 24,318.5 | 24,318.5 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 32 | rom | 51,394.5 | 24,318.5 | 24,318.5 | 2.11x | 1.00x | weight_read | weight_read | weight_read |
| DeepSeek-V4-Pro-0813 | 64 | rom | 53,923.2 | 24,318.5 | 26,891.9 | 2.22x | 1.11x | kv_read | weight_read | kv_read |
| DeepSeek-V4-Pro-0813 | 256 | rom | 66,724.0 | 24,318.5 | 53,112.6 | 2.74x | 2.18x | kv_read | weight_read | weight_read |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 10.80x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 2 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 2 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 10.80x |
| Qwen3-8B | 2 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 2 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 2 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 2 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 4 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 10.80x |
| Qwen3-8B | 4 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 4 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 4 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 1.06x |
| Qwen3-8B | 4 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 1.00x |
| Qwen3-8B | 8 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 19,516.3 | 0.141 | weight_read | 1.00x |
| Qwen3-8B | 8 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 6.81x |
| Qwen3-8B | 8 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.67x |
| Qwen3-8B | 8 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 0.63x |
| Qwen3-8B | 8 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.67x |
| Qwen3-8B | 8 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 0.63x |
| Qwen3-8B | 16 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 30,749.2 | 0.166 | kv_read | 1.00x |
| Qwen3-8B | 16 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 4.32x |
| Qwen3-8B | 16 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.42x |
| Qwen3-8B | 16 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 0.40x |
| Qwen3-8B | 16 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.42x |
| Qwen3-8B | 16 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 0.40x |
| Qwen3-8B | 32 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 46,972.0 | 0.169 | weight_read | 1.00x |
| Qwen3-8B | 32 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 2.83x |
| Qwen3-8B | 32 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.28x |
| Qwen3-8B | 32 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 0.26x |
| Qwen3-8B | 32 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,032.3 | 0.282 | weight_read | 0.28x |
| Qwen3-8B | 32 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.00 | 12,310.3 | 0.266 | kv_read | 0.26x |
| Qwen3-8B | 64 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 70,876.5 | 0.192 | kv_read | 1.00x |
| Qwen3-8B | 64 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 1.88x |
| Qwen3-8B | 64 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,035.7 | 0.282 | weight_read | 0.18x |
| Qwen3-8B | 64 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 1.12 | 12,313.3 | 0.266 | kv_read | 0.17x |
| Qwen3-8B | 64 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.12 | 13,035.7 | 0.282 | weight_read | 0.18x |
| Qwen3-8B | 64 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 1.12 | 12,313.3 | 0.266 | kv_read | 0.17x |
| Qwen3-8B | 256 | batched | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 119,989.1 | 0.216 | kv_read | 1.00x |
| Qwen3-8B | 256 | batched | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 238.71 | 1.00 | 132,979.7 | 0.240 | kv_read | 1.11x |
| Qwen3-8B | 256 | per_stream | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 12,331.5 | 0.267 | kv_read | 0.10x |
| Qwen3-8B | 256 | per_stream | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 22.60 | 4.49 | 12,331.5 | 0.267 | kv_read | 0.10x |
| Qwen3-8B | 256 | per_region | sram | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 4.49 | 12,331.5 | 0.267 | kv_read | 0.10x |
| Qwen3-8B | 256 | per_region | rom | Qwen3-8B/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 22.60 | 4.49 | 12,331.5 | 0.267 | kv_read | 0.10x |
| DeepSeek-V4-Flash-0731 | 1 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 21.03x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 2 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1 | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 21.03x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 2.21x |
| DeepSeek-V4-Flash-0731 | 4 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 15,359.2 | 0.332 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 17.83x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.85x |
| DeepSeek-V4-Flash-0731 | 4 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 1.87x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 1.57 | 13,533.3 | 0.293 | link_latency | 0.88x |
| DeepSeek-V4-Flash-0731 | 4 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 1.87x |
| DeepSeek-V4-Flash-0731 | 8 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1 | 46,225 | 1.00 | 1.00 | 23,145.6 | 0.501 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 11.83x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.56x |
| DeepSeek-V4-Flash-0731 | 8 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 1.24x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.13 | 23,630.2 | 0.511 | link_latency | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perregion-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 1.24x |
| DeepSeek-V4-Flash-0731 | 16 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 43,242.1 | 0.468 | link_latency | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 6.33x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.30x |
| DeepSeek-V4-Flash-0731 | 16 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 0.67x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 2.88 | 40,408.9 | 0.874 | weight_read | 0.93x |
| DeepSeek-V4-Flash-0731 | 16 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 2.88 | 31,004.5 | 0.671 | kv_read | 0.72x |
| DeepSeek-V4-Flash-0731 | 32 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x3 | 138,675 | 1.00 | 1.00 | 72,469.7 | 0.523 | weight_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 3.78x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.00 | 13,018.3 | 0.282 | weight_read | 0.18x |
| DeepSeek-V4-Flash-0731 | 32 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.00 | 28,756.6 | 0.622 | weight_read | 0.40x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | sram | DSV4-Flash/ROM-N6-native-SRAMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 4.03 | 66,193.5 | 1.432 | weight_read | 0.91x |
| DeepSeek-V4-Flash-0731 | 32 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion-romfill | 46,225 | 2.22 | 4.03 | 37,344.5 | 0.808 | kv_read | 0.52x |
| DeepSeek-V4-Flash-0731 | 64 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x4 | 184,900 | 1.00 | 1.00 | 111,977.1 | 0.606 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 23.43 | 1.00 | 273,830.7 | 0.494 | weight_read | 2.45x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 1.12 | 13,023.2 | 0.282 | weight_read | 0.12x |
| DeepSeek-V4-Flash-0731 | 64 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 1.12 | 28,780.3 | 0.623 | weight_read | 0.26x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-tensor-x1-perregion | 46,225 | 1.00 | 5.83 | 41,597.6 | 0.900 | kv_read | 0.37x |
| DeepSeek-V4-Flash-0731 | 64 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x43-perregion-romfill | 35,045 | 1.57 | 2.37 | 48,683.8 | 1.389 | weight_read | 0.43x |
| DeepSeek-V4-Flash-0731 | 256 | batched | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 261,261.9 | 0.706 | kv_read | 1.00x |
| DeepSeek-V4-Flash-0731 | 256 | batched | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 23.43 | 1.00 | 342,257.8 | 0.617 | kv_read | 1.31x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | sram | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream | 46,225 | 1.00 | 4.49 | 13,052.9 | 0.282 | weight_read | 0.05x |
| DeepSeek-V4-Flash-0731 | 256 | per_stream | rom | DSV4-Flash/ROM-N6-native-HBMKV-wafer-pipeline-x1-perstream-romfill | 46,225 | 2.22 | 4.49 | 28,925.9 | 0.626 | weight_read | 0.11x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | sram | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x28-perregion | 22,820 | 1.00 | 5.83 | 88,442.0 | 3.876 | weight_read | 0.34x |
| DeepSeek-V4-Flash-0731 | 256 | per_region | rom | DSV4-Flash/ROM-N6-native-HBMKV-array-hybrid-x43-perregion-romfill | 35,045 | 1.57 | 4.67 | 110,735.9 | 3.160 | weight_read | 0.42x |
| DeepSeek-V4-Pro-0813 | 1 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,394.5 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 1 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 2 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,394.5 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 4 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,394.5 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12 | 554,700 | 1.00 | 1.00 | 11,751.3 | 0.021 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,394.5 | 0.093 | weight_read | 4.37x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 2.07x |
| DeepSeek-V4-Pro-0813 | 16 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x6 | 277,350 | 1.00 | 1.00 | 20,376.3 | 0.073 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,394.5 | 0.093 | weight_read | 2.52x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 0.58x |
| DeepSeek-V4-Pro-0813 | 16 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 1.19x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 1.28 | 19,635.9 | 0.085 | weight_read | 0.96x |
| DeepSeek-V4-Pro-0813 | 16 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 1.19x |
| DeepSeek-V4-Pro-0813 | 32 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x8 | 369,800 | 1.00 | 1.00 | 33,100.8 | 0.090 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x12-romfill | 554,700 | 4.38 | 1.00 | 51,394.5 | 0.093 | weight_read | 1.55x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 0.35x |
| DeepSeek-V4-Pro-0813 | 32 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 0.73x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 1.82 | 24,164.7 | 0.105 | kv_read | 0.73x |
| DeepSeek-V4-Pro-0813 | 32 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perregion-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 0.73x |
| DeepSeek-V4-Pro-0813 | 64 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 48,123.5 | 0.087 | weight_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4.38 | 1.00 | 53,923.2 | 0.097 | kv_read | 1.12x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 0.24x |
| DeepSeek-V4-Pro-0813 | 64 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 0.51x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion | 231,125 | 1.00 | 2.31 | 26,891.9 | 0.116 | kv_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 64 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x5-perregion-romfill | 231,125 | 2.07 | 2.31 | 26,891.9 | 0.116 | kv_read | 0.56x |
| DeepSeek-V4-Pro-0813 | 256 | batched | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12 | 554,700 | 1.00 | 1.00 | 66,724.0 | 0.120 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | batched | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x12-romfill | 554,700 | 4.38 | 1.00 | 66,724.0 | 0.120 | kv_read | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | sram | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream | 231,125 | 1.00 | 1.00 | 11,743.8 | 0.051 | weight_read | 0.18x |
| DeepSeek-V4-Pro-0813 | 256 | per_stream | rom | DSV4-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x5-perstream-romfill | 231,125 | 2.07 | 1.00 | 24,318.5 | 0.105 | weight_read | 0.36x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | sram | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x147-perregion | 119,805 | 1.00 | 2.36 | 52,670.7 | 0.440 | weight_read | 0.79x |
| DeepSeek-V4-Pro-0813 | 256 | per_region | rom | DSV4-Pro/ROM-N6-native-HBMKV-array-hybrid-x148-perregion-romfill | 120,620 | 1.01 | 2.36 | 53,112.6 | 0.440 | weight_read | 0.80x |

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
| Qwen3-8B | 1 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 2 | 4 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| Qwen3-8B | 64 | 57 | 1.12 | 1.123 | 1.123 | 1.00x |
| Qwen3-8B | 256 | 5 | 51.20 | 51.200 | 51.200 | 1.00x |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 2 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 4 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 8 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 16 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 32 | 57 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 2.29 | 1.015 | 1.192 | 1.17x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 9.14 | 1.099 | 2.232 | 2.03x |
| DeepSeek-V4-Pro-0813 | 1 | 141 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 2 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 4 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 8 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 16 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 32 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 64 | 147 | 1.00 | 1.000 | 1.000 | 1.00x |
| DeepSeek-V4-Pro-0813 | 256 | 147 | 1.74 | 1.006 | 1.066 | 1.06x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 1 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 2 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 4 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 8 | 8 | 4.41 | 3.00 | 1.47x |
| DeepSeek-V4-Flash-0731 | 16 | 8 | 6.36 | 3.68 | 1.73x |
| DeepSeek-V4-Flash-0731 | 32 | 8 | 7.64 | 4.38 | 1.74x |
| DeepSeek-V4-Flash-0731 | 64 | 8 | 7.98 | 5.03 | 1.59x |
| DeepSeek-V4-Flash-0731 | 256 | 8 | 8.00 | 6.01 | 1.33x |
| DeepSeek-V4-Flash-0731 | 1 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 2 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 4 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 8 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 16 | 18 | 5.23 | 3.82 | 1.37x |
| DeepSeek-V4-Flash-0731 | 32 | 18 | 8.16 | 4.80 | 1.70x |
| DeepSeek-V4-Flash-0731 | 64 | 18 | 12.49 | 6.22 | 2.01x |
| DeepSeek-V4-Flash-0731 | 256 | 18 | 17.73 | 9.20 | 1.93x |
| DeepSeek-V4-Flash-0731 | 1 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 2 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 4 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 8 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 16 | 19 | 5.26 | 3.87 | 1.36x |
| DeepSeek-V4-Flash-0731 | 32 | 19 | 7.95 | 4.78 | 1.66x |
| DeepSeek-V4-Flash-0731 | 64 | 19 | 12.44 | 6.24 | 1.99x |
| DeepSeek-V4-Flash-0731 | 256 | 19 | 18.57 | 9.38 | 1.98x |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 2 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 4 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 8 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 16 | 26 | 5.45 | 4.18 | 1.30x |
| DeepSeek-V4-Flash-0731 | 32 | 26 | 6.52 | 4.59 | 1.42x |
| DeepSeek-V4-Flash-0731 | 64 | 26 | 11.29 | 6.18 | 1.83x |
| DeepSeek-V4-Flash-0731 | 256 | 26 | 22.79 | 10.20 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 2 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 4 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 8 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 16 | 28 | 5.49 | 4.26 | 1.29x |
| DeepSeek-V4-Flash-0731 | 32 | 28 | 6.17 | 4.53 | 1.36x |
| DeepSeek-V4-Flash-0731 | 64 | 28 | 10.87 | 6.12 | 1.78x |
| DeepSeek-V4-Flash-0731 | 256 | 28 | 23.44 | 10.33 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 2 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 4 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 8 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 16 | 31 | 5.54 | 4.35 | 1.27x |
| DeepSeek-V4-Flash-0731 | 32 | 31 | 5.70 | 4.42 | 1.29x |
| DeepSeek-V4-Flash-0731 | 64 | 31 | 10.24 | 6.02 | 1.70x |
| DeepSeek-V4-Flash-0731 | 256 | 31 | 24.03 | 10.48 | 2.29x |
| DeepSeek-V4-Flash-0731 | 1 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 2 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 4 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 8 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 16 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 32 | 38 | 5.62 | 4.55 | 1.24x |
| DeepSeek-V4-Flash-0731 | 64 | 38 | 8.91 | 5.82 | 1.53x |
| DeepSeek-V4-Flash-0731 | 256 | 38 | 24.13 | 10.62 | 2.27x |
| DeepSeek-V4-Flash-0731 | 1 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 2 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 4 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 8 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 16 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 32 | 42 | 5.65 | 4.64 | 1.22x |
| DeepSeek-V4-Flash-0731 | 64 | 42 | 8.26 | 5.71 | 1.45x |
| DeepSeek-V4-Flash-0731 | 256 | 42 | 23.69 | 10.62 | 2.23x |
| DeepSeek-V4-Flash-0731 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Flash-0731 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Flash-0731 | 256 | 56 | 21.14 | 10.40 | 2.03x |
| DeepSeek-V4-Flash-0731 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Flash-0731 | 256 | 112 | 12.78 | 8.82 | 1.45x |
| DeepSeek-V4-Flash-0731 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Flash-0731 | 256 | 168 | 8.87 | 7.61 | 1.17x |
| DeepSeek-V4-Flash-0731 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Flash-0731 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Flash-0731 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Flash-0731 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Flash-0731 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Flash-0731 | 256 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 2 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 4 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 8 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 16 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 32 | 48 | 5.70 | 4.75 | 1.20x |
| DeepSeek-V4-Pro-0813 | 64 | 48 | 7.42 | 5.55 | 1.34x |
| DeepSeek-V4-Pro-0813 | 256 | 48 | 22.97 | 10.64 | 2.16x |
| DeepSeek-V4-Pro-0813 | 1 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 2 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 4 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 8 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 16 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 32 | 56 | 5.74 | 4.88 | 1.18x |
| DeepSeek-V4-Pro-0813 | 64 | 56 | 6.50 | 5.28 | 1.23x |
| DeepSeek-V4-Pro-0813 | 256 | 56 | 21.37 | 10.48 | 2.04x |
| DeepSeek-V4-Pro-0813 | 1 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 93 | 5.84 | 5.24 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 93 | 15.02 | 9.23 | 1.63x |
| DeepSeek-V4-Pro-0813 | 1 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 95 | 5.84 | 5.25 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 95 | 14.76 | 9.18 | 1.61x |
| DeepSeek-V4-Pro-0813 | 1 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 2 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 4 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 8 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 16 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 32 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 64 | 98 | 5.85 | 5.27 | 1.11x |
| DeepSeek-V4-Pro-0813 | 256 | 98 | 14.38 | 9.12 | 1.58x |
| DeepSeek-V4-Pro-0813 | 1 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 2 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 4 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 8 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 16 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 32 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 64 | 112 | 5.87 | 5.35 | 1.10x |
| DeepSeek-V4-Pro-0813 | 256 | 112 | 12.84 | 8.85 | 1.45x |
| DeepSeek-V4-Pro-0813 | 1 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 139 | 5.89 | 5.46 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 139 | 10.59 | 8.30 | 1.28x |
| DeepSeek-V4-Pro-0813 | 1 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 144 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 144 | 10.26 | 8.18 | 1.25x |
| DeepSeek-V4-Pro-0813 | 1 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 145 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 145 | 10.19 | 8.16 | 1.25x |
| DeepSeek-V4-Pro-0813 | 1 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 2 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 4 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 8 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 16 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 32 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 64 | 146 | 5.90 | 5.48 | 1.08x |
| DeepSeek-V4-Pro-0813 | 256 | 146 | 10.13 | 8.14 | 1.24x |
| DeepSeek-V4-Pro-0813 | 1 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 154 | 5.90 | 5.51 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 154 | 9.64 | 7.95 | 1.21x |
| DeepSeek-V4-Pro-0813 | 1 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 2 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 4 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 8 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 16 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 32 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 64 | 168 | 5.91 | 5.54 | 1.07x |
| DeepSeek-V4-Pro-0813 | 256 | 168 | 8.89 | 7.62 | 1.17x |
| DeepSeek-V4-Pro-0813 | 1 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 2 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 4 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 8 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 16 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 32 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 64 | 224 | 5.93 | 5.65 | 1.05x |
| DeepSeek-V4-Pro-0813 | 256 | 224 | 6.76 | 6.32 | 1.07x |
| DeepSeek-V4-Pro-0813 | 1 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 2 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 4 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 8 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 16 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 32 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 64 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 256 | 280 | 5.95 | 5.72 | 1.04x |
| DeepSeek-V4-Pro-0813 | 1 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 2 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 4 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 8 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 16 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 32 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 64 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 256 | 336 | 5.96 | 5.76 | 1.03x |
| DeepSeek-V4-Pro-0813 | 1 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 448 | 5.97 | 5.82 | 1.02x |
| DeepSeek-V4-Pro-0813 | 1 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 2 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 4 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 8 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 16 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 32 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 64 | 672 | 5.98 | 5.88 | 1.02x |
| DeepSeek-V4-Pro-0813 | 256 | 672 | 5.98 | 5.88 | 1.02x |

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
| gpu | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 0.6% |
| gpu | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 0.4% |
| gpu | Qwen3-8B | 1 | 5.85 | 0.5% |
| rom | DeepSeek-V4-Flash-0731 | 1 | 9.67 | 4.6% |
| rom | DeepSeek-V4-Pro-0813 | 1 | 13.75 | 3.2% |
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
| Qwen3-8B | 1 | 4 | 40.53% | 15.04 | 9.27 |
| Qwen3-8B | 2 | 4 | 40.53% | 15.04 | 9.27 |
| Qwen3-8B | 4 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 8 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 16 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 32 | 1 | 1.14% | 6.00 | 9.27 |
| Qwen3-8B | 64 | 1 | 1.27% | 6.74 | 9.27 |
| DeepSeek-V4-Flash-0731 | 1 | 26 | 96.88% | 53.68 | 2.13 |
| DeepSeek-V4-Flash-0731 | 2 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 4 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 8 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 16 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Flash-0731 | 32 | 1 | 2.24% | 2.72 | 2.13 |
| DeepSeek-V4-Pro-0813 | 1 | 141 | 86.61% | 253.66 | 2.08 |
| DeepSeek-V4-Pro-0813 | 2 | 3 | 14.37% | 51.05 | 2.08 |
| DeepSeek-V4-Pro-0813 | 4 | 3 | 14.37% | 51.05 | 2.08 |

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
| Qwen3-8B | 1 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,265.1 | 6,325.4 |
| Qwen3-8B | 2 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,265.1 | 6,325.4 |
| Qwen3-8B | 4 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 1,265.1 | 6,325.4 |
| Qwen3-8B | 8 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 796.7 | 6,373.3 |
| Qwen3-8B | 16 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 400.9 | 6,413.8 |
| Qwen3-8B | 32 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 201.1 | 6,434.2 |
| Qwen3-8B | 64 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 100.7 | 6,444.5 |
| Qwen3-8B | 256 | 100.00% | 15.1 GB | 92.40% | 197.73 TB/s | 213.99 TB/s | 25.2 | 6,452.2 |
| DeepSeek-V4-Flash-0731 | 1 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 527.3 | 9,491.1 |
| DeepSeek-V4-Flash-0731 | 2 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 527.3 | 9,491.1 |
| DeepSeek-V4-Flash-0731 | 4 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 527.3 | 9,491.1 |
| DeepSeek-V4-Flash-0731 | 8 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 527.3 | 9,491.1 |
| DeepSeek-V4-Flash-0731 | 16 | 2.34% | 11.2 GB | 6.72% | 146.53 TB/s | 2,179.91 TB/s | 527.3 | 9,491.1 |
| DeepSeek-V4-Flash-0731 | 32 | 4.13% | 13.8 GB | 8.30% | 180.85 TB/s | 2,179.91 TB/s | 300.5 | 9,615.7 |
| DeepSeek-V4-Flash-0731 | 64 | 8.09% | 19.7 GB | 11.79% | 256.94 TB/s | 2,179.91 TB/s | 151.5 | 9,697.5 |
| DeepSeek-V4-Flash-0731 | 256 | 28.63% | 49.9 GB | 29.90% | 651.89 TB/s | 2,179.91 TB/s | 38.1 | 9,759.8 |
| DeepSeek-V4-Pro-0813 | 1 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 2 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 4 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 8 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 16 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 32 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 64 | 1.56% | 39.7 GB | 4.44% | 518.16 TB/s | 11,661.57 TB/s | 90.3 | 8,673.0 |
| DeepSeek-V4-Pro-0813 | 256 | 4.11% | 60.6 GB | 6.79% | 792.00 TB/s | 11,661.57 TB/s | 34.2 | 8,760.9 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 4 |
| gpu | kv_read | 31 |
| gpu | link_latency | 274 |
| gpu | weight_read | 715 |
| rom | compute | 91 |
| rom | infeasible | 1592 |
| rom | kv_read | 446 |
| rom | link_latency | 762 |
| rom | weight_read | 773 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 4 |
| rom | CAPACITY | 1592 |

## Mechanical consistency audit

**PASS** over 97,291 checks.

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
