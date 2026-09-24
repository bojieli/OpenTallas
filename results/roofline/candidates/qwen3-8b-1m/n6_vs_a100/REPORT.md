# Area-constrained roofline: n6_vs_a100-qwen3-8b-1m

> CANDIDATE MODEL under n6_vs_a100: Qwen3-8B at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 518x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 92 devices. On the GPU side the correction reaches 927x (a100_sxm_80gb-x8389-pipeline, 8,389 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 304 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 92 x 815 mm2 (74,980 mm2, array, KV in SRAM) at 11,799 tok/s per user and 157 tok/s per 1,000 mm2, holding 1 session, against 91 copies of one unified HBM die at the same silicon: 21.4x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 76,610 mm2 of ROM silicon at 11,961 tok/s per user against 76,818 mm2 of a100_sxm_80gb-x93-tensor at 559 tok/s: **21.4x**, ROM binding on `link_latency` and the GPU on `kv_read`. It holds 1 resident session against the GPU cluster's 45. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 93.22x to it.** At 251,020 mm2 on Qwen3-8B the pipeline-only GPU delivers 10.15 tok/s and the same silicon running tensor delivers 946 tok/s.
7. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 1,021 us over NVLink, capping per-user decode at 980 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 154.6 us and cap it at 6,469 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
8. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 1; on tokens per second per square millimetre the same points go 1 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
9. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 480 of 711 feasible points.
10. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
11. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 79% of its cooling budget. The companion study at the other node does have power-limited points.


## The recommended design per model, and the rule that picks it

**The metric, stated here because a recommendation without its rule is an
opinion.**

> Among the ROM designs feasible for this model at this batch, keep every design that no other feasible design of the same model and batch beats on BOTH per-user tokens/s and tokens/s per 1,000 mm2. That non-dominated set is the reported frontier, and it is published in full. Order it by silicon area, start at the smallest feasible machine, and accept each larger rung only while the per-user tokens/s it adds per added mm2 is strictly greater than the tokens/s per mm2 the incumbent already returns on average; ties go to the smaller machine. The rung the walk stops on is the recommended design. Equivalently: maximise per-user tokens/s per mm2 over the feasible set. The two statements are the same rule -- accepting when (r - r0) / (a - a0) >= r0 / a0 is exactly r / a >= r0 / a0 -- and the marginal form is the one to read, because it is the engineering question: does the next slab of silicon work at least as hard as the slab you have?

Why this rule and not another: Ranking on per-user tokens/s alone hands an 8B model a 46,225 mm2 wafer, because a per-user rate has no area in it and a wafer is always at least as fast as anything cut out of it -- on Qwen3-8B that is 2.33x the rate of the three 815 mm2 reticles that hold the same checkpoint, bought with 18.9x the silicon and an eighth of the throughput density. Ranking on silicon area alone picks the smallest machine that physically holds the checkpoint, whatever it delivers. A 5%-of-peak tolerance does not fix the first: it is a tie-break among near-peak designs and is orthogonal to area, so it shrinks the machine only in the cases nobody was worried about. The domination filter plus the marginal-return walk fixes both, needs no latency target to be stated, and -- because the filter is on (per-user rate, rate per mm2) -- makes it structurally impossible to recommend a design that another feasible design of the same model beats on both axes at once.

The bar is `1` -- parity. The frontier is
taken over the `batched` machine, which is what the
main tables show. **The recommendation is not a single number and must not be
quoted as one:** every row below carries per-user rate, aggregate rate,
resident sessions, throughput density, power, energy per token and the
binding constraint together, because a per-user rate published without the
resident-session count beside it is how a one-session latency device gets
read as a server.

The GPU comparator at each ROM area is N copies of one unified HBM die, N chosen so the silicon matches, and the cluster is allowed to pick its own parallelism. The comparison is read at the ROM side's CHOSEN area, not at a fixed rung of the area ladder where both sides are past their own optimum.

### Qwen3-8B at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill`** -- 92 x 815 mm2 reticle dies, 74,980 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `rom`.

- **11,799.1 tok/s per user** (0.08 ms/token), binding on `link_latency`
- **157.4 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 11,799 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 9,638 W at 0.129 W/mm2, 816.8 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 91 copies of one unified HBM die -- `a100_sxm_80gb-x91-tensor`, 75,166 mm2, area ratio 0.9975 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 74,980 | 75,166 | 0.9975 |
| user tok/s | 11,799.1 | 552.2 | 21.37x |
| aggregate tok/s | 11,799 | 552 | 13.16x |
| resident sessions | 1 | 44 | -- |
| J/token | 0.8168 | 40.8899 | 50.1x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 44 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x8389-tensor` at 6,929,314 mm2 and 962.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` | 74,980 | 11,799.1 | 157.4 | 1 | 21.37x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill` | 77,425 | 12,019.7 | 155.2 | 1 | 21.35x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x79` | 64,385 | 8,535.0 | 132.6 | 1 | 16.99x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` | 74,980 | 11,799.1 | 157.4 | 1 | 21.37x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` | 74,980 | 11,799.1 | 157.4 | -- | 157.4 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x94-romfill` | 76,610 | 11,960.7 | 156.1 | 99.2 | 157.4 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill` | 77,425 | 12,019.7 | 155.2 | 90.2 | 157.4 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` **<-- recommended** | 74,980 | 92 | 11,799.1 | 11,799 | 157.4 | 1 | `link_latency` | 9,638 | 816.8 | `a100_sxm_80gb-x91-tensor` | 21.37x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x94-romfill` | 76,610 | 94 | 11,960.7 | 11,961 | 156.1 | 1 | `link_latency` | 9,807 | 819.9 | `a100_sxm_80gb-x93-tensor` | 21.38x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill` | 77,425 | 95 | 12,019.7 | 12,020 | 155.2 | 1 | `link_latency` | 9,882 | 822.2 | `a100_sxm_80gb-x94-tensor` | 21.35x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 144 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` | 74,980 | 11,799.1 | 157.4 | 1 |
| array | 144 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill` | 77,425 | 12,019.7 | 155.2 | 1 |
| array | 144 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x79` | 64,385 | 8,535.0 | 132.6 | 1 |
| wafer | 36 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 6,019.5 | 65.1 | 1 |
| wafer | 36 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 6,019.5 | 65.1 | 1 |
| wafer | 36 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 6,019.5 | 65.1 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill` | 77,425 | 12,019.7 | 12,020 | 1 | 9,882 | 822.2 | `link_latency` | `a100_sxm_80gb-x94-tensor` | 562.9 | 45 | 41,205.7 | 0.997 | 21.35x | 50.1x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 6,019.5 | 6,019 | 1 | 7,934 | 1,318.0 | `link_latency` | `a100_sxm_80gb-x112-tensor` | 621.5 | 54 | 43,114.4 | 0.999 | 9.69x | 32.7x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-tensor-x113-romfill` | 92,095 | 10,096.6 | 10,097 | 1 | 9,961 | 986.6 | `link_latency` | `a100_sxm_80gb-x111-tensor` | 618.5 | 54 | 43,009.0 | 1.004 | 16.33x | 43.6x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 6,019.5 | -- | 1 | -- | 1,318.0 | -- | -- | -- | -- | -- | 0.996 | 0.60x wafer/array | -- |
| 2 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 4 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 8 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 16 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 32 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 64 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 256 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 1024 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |
| 4096 | -- | *no feasible ROM design* | | | | | | | | | | | | | | |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` | 74,980 | array | SRAM | 1 |
| 2-4096 | *no feasible design* | -- | -- | -- | -- |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | SRAM | rom | 82, 92, 94, 95, 97, 113, 116, 154, 170, 227, 231, 308, 340 |
| Qwen3-8B | SRAM | sram | 79, 80, 97, 113, 116, 154, 170, 227, 231, 308, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 24,675.2 tok/s | 1.45x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 110.6 W | 0.44x | within 2x | FAIL |

HC1 binds on `weight_read`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 6.06 us.

The model **under**-predicts the shipping part by 0.69x. Rather than tune the densities until the anchor
is hit, the gate back-derives what each input would have to be for the
model to land exactly on 17,000 tok/s:

| Derived input | This model | Required by the shipping part | Shortfall |
|---|---:|---:|---:|
| ROM read bandwidth density (B/s/mm2) | 5.292e+11 | 3.093e+11 | 0.58x |
| Compute density (ops/s/mm2) | 1.261e+12 | 3.155e+12 | 2.50x |

The gate fails before either rate density can bind: the corrected
ROM capacity density and compute-in-ROM floorplan cannot fit the
published model in 815 mm2. The rate diagnostics remain useful --
ROM read density is 0.58x and
compute density is 2.50x
the value implied by the shipping rate -- but neither can rescue a
capacity failure. The required ROM read density remains below the SRAM
read-bandwidth density derived from Cerebras WSE-2
(4.327e+11 B/s/mm2).

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
| range low | 70.0 ns/layer | 2.24 us | 27,243.5 | 1.61x | weight_read |
| range stated | 189.4 ns/layer | 6.06 us | 24,675.2 | 1.45x | weight_read |
| range high | 894.8 ns/layer | 28.63 us | 15,847.9 | 0.93x | weight_read |

The per-layer cost that would land the model exactly on the
published figure is **765.5 ns/layer**. It is reported so the distance between the derived value and the fitted one is visible. It is never used as an input.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 24,675.2 | 1.45x | weight_read |
| 3.5 | 24,675.2 | 1.45x | weight_read |
| 4.0 | 24,675.2 | 1.45x | weight_read |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 24,675.2 | 1.45x | weight_read |
| 1,536 | 24,675.2 | 1.45x | weight_read |
| 2,048 | 24,675.2 | 1.45x | weight_read |

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
| A100 at TDP, saturating | 400.0 W | 461.7 W | 1.15x | PASS |
| Taalas HC1 card power | 200.0-250.0 W | 110.6 W | 0.44x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 6.5 W |
| KV traffic | n/a: one saturating HBM stream | 17.2 W |
| operand delivery | 0.5 W | 20.2 W |
| arithmetic | 103.0 W | 14.4 W |
| static: leakage | 31.4 W | 20.6 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.2 W |
| **total** | 461.7 W | 110.6 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 78.8 W | 0.32x | 0.39x |
| stated | 461.7 W | 1.15x | 110.6 W | 0.44x | 0.55x |
| high | 698.3 W | 1.75x | 407.5 W | 1.63x | 2.04x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.44x of the top of its published band, **2.26x low**, against 1.81x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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

**Energy accounting at the two anchors.** Both parts serve the same workload -- Llama-3.1-8B at batch 1 -- so this is the cleanest statement the model can make about the ROM argument, and it could not be made at all until the power terms existed:

| Part | Energy | W | tok/s |
|---|---:|---:|---:|
| Taalas HC1 (modelled reconstruction) | 0.004480 J/token | 110.6 | 24,675.2 |
| A100 80GB, weight-bound gate, same model and batch | 1.465768 J/token | 359.6 | 245.3 |

That is a factor of 327 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 1.8-2.3x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

**Where the remaining HC1 shortfall could live, none of it fitted.**
The ROM array is charged its stated leakage density: 1.7 W at the point
and 6.7 W at the
top of its range. The point charge moves the enumerated static
estimate just above the measured clocked-idle floor and is therefore
included in the charged static total. `energy.rom_read_j_per_byte`
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

- **0 of 711 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 79% of its cooling budget, and the busiest wafer-scale ROM design 27%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 471 | 0 | 67.4% | 79.0% | 0.383 | 54% |
| rom | wafer (>=40,000 mm2) | 240 | 0 | 15.9% | 27.3% | 0.137 | 93% |

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
| Qwen3-8B | 1 | 74,980 | `Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill` | 0.816850 | 9,638.1 | link_latency | `Qwen3-8B/a100_sxm_80gb-x91-tensor` | 40.889891 | 22,578.5 | kv_read | 50.06x |

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
| ROM capacity density | 7.295 MB/mm2 | derived |
| ROM read bandwidth density | 282.2 GB/s/mm2 | derived |
| SRAM read bandwidth density | 432.7 GB/s/mm2 | derived |
| Compute density, bf16 | 0.446 Tops/s/mm2 | derived |
| Compute density, fp8 | 0.891 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.261 Tops/s/mm2 | derived |
| Compute density, fp4 | 1.783 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.028 Tops/s/mm2 | derived |
| ROM full-array sweep time | 34.5 us | derived |
| ROM per-token ceiling from that sweep | 29,015 tok/s | derived |
| ROM per-token ceiling before the read derate | 38,686 tok/s | derived |

The ROM full-array sweep time is rom_capacity_density divided by rom_read_bandwidth_density. Both scale with the same published bitcell-area ratio under this derivation, so the sweep time -- and hence the ROM path's hard per-token ceiling -- is the SAME at every node. Process scaling buys a ROM design capacity, not per-token speed. No clock-frequency bonus is credited, which makes this the conservative reading.

## Models and their work

| Model | Context | Params | Checkpoint | Native bits/param | KV read/token | KV/user | W:KV at B=1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 1,000,000 | 8 B | 16.4 GB | 16.00 | 147.456 GB | 147.456 GB | 0.1 |

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
| Qwen3-8B | 2 | 92,450 | 46,516.5 | wafer-pipeline | 6,019.5 | wafer-hybrid | 7.73x | 1,027.1 | pipeline | 621.5 | tensor | 1.65x | 45.29x | 9.69x | 0.21x |
| Qwen3-8B | 3 | 138,675 | 46,516.5 | wafer-pipeline | 5,822.1 | wafer-tensor | 7.99x | 1,469.3 | pipeline | 758.9 | tensor | 1.94x | 31.66x | 7.67x | 0.24x |
| Qwen3-8B | 4 | 184,900 | 46,516.5 | wafer-pipeline | 5,821.3 | wafer-tensor | 7.99x | 1,872.3 | pipeline | 853.2 | tensor | 2.19x | 24.84x | 6.82x | 0.27x |
| Qwen3-8B | 6 | 277,350 | 46,516.5 | wafer-pipeline | 5,329.1 | wafer-tensor | 8.73x | 2,580.0 | pipeline | 758.3 | tensor | 3.40x | 18.03x | 7.03x | 0.39x |
| Qwen3-8B | 8 | 369,800 | 46,516.5 | wafer-pipeline | 5,328.8 | wafer-tensor | 8.73x | 3,181.2 | pipeline | 802.6 | tensor | 3.96x | 14.62x | 6.64x | 0.45x |
| Qwen3-8B | 12 | 554,700 | 46,516.5 | wafer-pipeline | 4,913.7 | wafer-tensor | 9.47x | 4,147.8 | pipeline | 852.5 | tensor | 4.87x | 11.21x | 5.76x | 0.51x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.21x to 0.51x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill | 77,425 | 12,019.7 | 12,019.7 | link_latency | Qwen3-8B/a100_sxm_80gb-x94-tensor | 77,644 | 1.00x | tensor | 722.36 | 562.9 | 562.9 | kv_read | 21.35x | 12.99x | 1184.43x | 21.35x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x79 | 64,385 | 8,535.0 | 8,535.0 | link_latency | Qwen3-8B/a100_sxm_80gb-x78-tensor | 64,428 | 1.00x | tensor | 721.18 | 502.5 | 502.5 | kv_read | 16.99x | 11.11x | 841.05x | 16.99x |
| Qwen3-8B | 2 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-tensor | 64,428 | 1.00x | tensor | 790.04 | 312.1 | 624.3 | kv_read | — | — | — | — |
| Qwen3-8B | 4 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-tensor | 64,428 | 1.00x | tensor | 927.77 | 177.6 | 710.4 | kv_read | — | — | — | — |
| Qwen3-8B | 8 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-tensor | 64,428 | 1.00x | tensor | 1,203.22 | 95.4 | 763.0 | kv_read | — | — | — | — |
| Qwen3-8B | 16 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 391.25 | 50.3 | 804.5 | kv_read | — | — | — | — |
| Qwen3-8B | 32 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-hybrid | 64,428 | 1.00x | hybrid | 404.22 | 26.2 | 837.4 | kv_read | — | — | — | — |
| Qwen3-8B | 64 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 87.78 | infeasible | — | capacity_or_format | — | — | — | — |
| Qwen3-8B | 256 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 92.70 | infeasible | — | capacity_or_format | — | — | — | — |
| Qwen3-8B | 1024 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 113.94 | infeasible | — | capacity_or_format | — | — | — | — |
| Qwen3-8B | 4096 | no feasible ROM design | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79 | 64,385 | infeasible | — | capacity_or_format | Qwen3-8B/a100_sxm_80gb-x78-pipeline | 64,428 | 1.00x | pipeline | 198.90 | infeasible | — | capacity_or_format | — | — | — | — |

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
| Qwen3-8B | 56 | 46,256 | 10.1 | 402.7 | 78.8 | tensor | 718.15 | 28.9% | kv_read |
| Qwen3-8B | 78 | 64,428 | 10.1 | 502.5 | 76.8 | tensor | 721.18 | 36.2% | kv_read |
| Qwen3-8B | 79 | 65,254 | 10.1 | 506.5 | 77.8 | tensor | 721.18 | 36.5% | kv_read |
| Qwen3-8B | 81 | 66,906 | 10.1 | 514.4 | 72.6 | tensor | 721.83 | 37.1% | kv_read |
| Qwen3-8B | 91 | 75,166 | 10.1 | 552.2 | 74.7 | tensor | 722.36 | 39.9% | kv_read |
| Qwen3-8B | 93 | 76,818 | 10.1 | 559.4 | 76.3 | tensor | 722.36 | 40.4% | kv_read |
| Qwen3-8B | 94 | 77,644 | 10.1 | 562.9 | 77.1 | tensor | 722.36 | 40.7% | kv_read |
| Qwen3-8B | 95 | 78,470 | 10.1 | 566.4 | 77.9 | tensor | 722.36 | 40.9% | kv_read |
| Qwen3-8B | 96 | 79,296 | 10.1 | 569.9 | 78.7 | tensor | 722.36 | 41.2% | kv_read |
| Qwen3-8B | 99 | 81,774 | 10.1 | 580.0 | 75.0 | tensor | 722.82 | 41.9% | kv_read |
| Qwen3-8B | 100 | 82,600 | 10.1 | 583.4 | 75.8 | tensor | 722.82 | 42.2% | kv_read |
| Qwen3-8B | 111 | 91,686 | 10.1 | 618.5 | 78.0 | tensor | 723.20 | 44.7% | kv_read |
| Qwen3-8B | 112 | 92,512 | 10.1 | 621.5 | 78.7 | tensor | 723.20 | 44.9% | link_latency |
| Qwen3-8B | 114 | 94,164 | 10.1 | 627.4 | 74.9 | tensor | 723.54 | 45.4% | link_latency |
| Qwen3-8B | 152 | 125,552 | 10.1 | 725.1 | 78.6 | tensor | 724.53 | 52.5% | link_latency |
| Qwen3-8B | 168 | 138,768 | 10.1 | 758.9 | 78.6 | tensor | 724.89 | 55.0% | link_latency |
| Qwen3-8B | 224 | 185,024 | 10.1 | 853.2 | 78.5 | tensor | 725.73 | 61.9% | link_latency |
| Qwen3-8B | 228 | 188,328 | 10.1 | 858.8 | 77.2 | tensor | 725.82 | 62.3% | link_latency |
| Qwen3-8B | 304 | 251,104 | 10.1 | 946.0 | 78.4 | tensor | 726.40 | 68.7% | link_latency |
| Qwen3-8B | 335 | 276,710 | 10.1 | 757.8 | 78.1 | tensor | 1,018.89 | 77.2% | link_latency |
| Qwen3-8B | 336 | 277,536 | 10.1 | 758.3 | 78.4 | tensor | 1,018.89 | 77.3% | link_latency |
| Qwen3-8B | 448 | 370,048 | 10.1 | 802.6 | 78.4 | tensor | 1,019.32 | 81.8% | link_latency |
| Qwen3-8B | 672 | 555,072 | 10.1 | 852.5 | 78.4 | tensor | 1,019.74 | 86.9% | link_latency |
| Qwen3-8B | 8389 | 6,929,314 | 10.1 | 962.4 | 78.3 | tensor | 1,020.51 | 98.2% | link_latency |

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
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x80 | Qwen3-8B | 80 | pipeline | rom_package_ucie | rom_board_serdes | 35 | 1.16 us | 86,080.4 tok/s | 860,803.8 tok/s | 27 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.33 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x80 | Qwen3-8B | 80 | tensor | rom_package_ucie | rom_board_serdes | 144 | 66.07 us | 1,513.6 tok/s | 15,136.5 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 20 on rom_board_serdes (traversals 8.8) = 64.29 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x80 | Qwen3-8B | 80 | hybrid | rom_package_ucie | rom_board_serdes | 91 | 3.76 us | 26,608.1 tok/s | 266,081.5 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 19 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.99 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x80 | Qwen3-8B | 80 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x2 | Qwen3-8B | 2 | pipeline | on_wafer | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-tensor-x79 | Qwen3-8B | 79 | tensor | nvlink3 | infiniband_hdr | 144 | 721.18 us | 138.7 tok/s | 1,386.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 356.02 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-tensor-x2 | Qwen3-8B | 2 | tensor | on_wafer | rom_wafer_serdes | 144 | 154.59 us | 646.9 tok/s | 6,468.8 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 72 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 15.99 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-array-hybrid-x80 | Qwen3-8B | 80 | hybrid | nvlink3 | infiniband_hdr | 81 | 386.38 us | 258.8 tok/s | 2,588.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| Qwen3-8B/ROM-N6-native-SRAMKV-wafer-hybrid-x2 | Qwen3-8B | 2 | hybrid | on_wafer | rom_wafer_serdes | 73 | 138.70 us | 721.0 tok/s | 7,209.7 tok/s | 72 x all_reduce span 57 on on_wafer (traversals 15.4) = 138.60 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/a100_sxm_80gb-x56-pipeline | Qwen3-8B | 56 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x56-tensor | Qwen3-8B | 56 | tensor | nvlink3 | infiniband_hdr | 144 | 718.15 us | 139.2 tok/s | 1,392.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 352.99 us |
| Qwen3-8B/a100_sxm_80gb-x56-hybrid | Qwen3-8B | 56 | hybrid | nvlink3 | infiniband_hdr | 78 | 379.31 us | 263.6 tok/s | 2,636.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 14.15 us |
| Qwen3-8B/a100_sxm_80gb-x78-pipeline | Qwen3-8B | 78 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x78-tensor | Qwen3-8B | 78 | tensor | nvlink3 | infiniband_hdr | 144 | 721.18 us | 138.7 tok/s | 1,386.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 356.02 us |
| Qwen3-8B/a100_sxm_80gb-x78-hybrid | Qwen3-8B | 78 | hybrid | nvlink3 | infiniband_hdr | 81 | 386.38 us | 258.8 tok/s | 2,588.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| Qwen3-8B/a100_sxm_80gb-x79-pipeline | Qwen3-8B | 79 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x79-tensor | Qwen3-8B | 79 | tensor | nvlink3 | infiniband_hdr | 144 | 721.18 us | 138.7 tok/s | 1,386.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 10 on infiniband_hdr (traversals 2.0) = 356.02 us |
| Qwen3-8B/a100_sxm_80gb-x79-hybrid | Qwen3-8B | 79 | hybrid | nvlink3 | infiniband_hdr | 81 | 386.38 us | 258.8 tok/s | 2,588.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 9 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 21.22 us |
| Qwen3-8B/a100_sxm_80gb-x81-pipeline | Qwen3-8B | 81 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x81-tensor | Qwen3-8B | 81 | tensor | nvlink3 | infiniband_hdr | 144 | 721.83 us | 138.5 tok/s | 1,385.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 356.66 us |
| Qwen3-8B/a100_sxm_80gb-x81-hybrid | Qwen3-8B | 81 | hybrid | nvlink3 | infiniband_hdr | 82 | 388.74 us | 257.2 tok/s | 2,572.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 23.58 us |
| Qwen3-8B/a100_sxm_80gb-x91-pipeline | Qwen3-8B | 91 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x91-tensor | Qwen3-8B | 91 | tensor | nvlink3 | infiniband_hdr | 144 | 722.36 us | 138.4 tok/s | 1,384.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 357.20 us |
| Qwen3-8B/a100_sxm_80gb-x91-hybrid | Qwen3-8B | 91 | hybrid | nvlink3 | infiniband_hdr | 83 | 391.10 us | 255.7 tok/s | 2,556.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| Qwen3-8B/a100_sxm_80gb-x93-pipeline | Qwen3-8B | 93 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x93-tensor | Qwen3-8B | 93 | tensor | nvlink3 | infiniband_hdr | 144 | 722.36 us | 138.4 tok/s | 1,384.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 357.20 us |
| Qwen3-8B/a100_sxm_80gb-x93-hybrid | Qwen3-8B | 93 | hybrid | nvlink3 | infiniband_hdr | 83 | 391.10 us | 255.7 tok/s | 2,556.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| Qwen3-8B/a100_sxm_80gb-x94-pipeline | Qwen3-8B | 94 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x94-tensor | Qwen3-8B | 94 | tensor | nvlink3 | infiniband_hdr | 144 | 722.36 us | 138.4 tok/s | 1,384.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 357.20 us |
| Qwen3-8B/a100_sxm_80gb-x94-hybrid | Qwen3-8B | 94 | hybrid | nvlink3 | infiniband_hdr | 83 | 391.10 us | 255.7 tok/s | 2,556.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| Qwen3-8B/a100_sxm_80gb-x95-pipeline | Qwen3-8B | 95 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x95-tensor | Qwen3-8B | 95 | tensor | nvlink3 | infiniband_hdr | 144 | 722.36 us | 138.4 tok/s | 1,384.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 357.20 us |
| Qwen3-8B/a100_sxm_80gb-x95-hybrid | Qwen3-8B | 95 | hybrid | nvlink3 | infiniband_hdr | 83 | 391.10 us | 255.7 tok/s | 2,556.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| Qwen3-8B/a100_sxm_80gb-x96-pipeline | Qwen3-8B | 96 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x96-tensor | Qwen3-8B | 96 | tensor | nvlink3 | infiniband_hdr | 144 | 722.36 us | 138.4 tok/s | 1,384.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 12 on infiniband_hdr (traversals 2.0) = 357.20 us |
| Qwen3-8B/a100_sxm_80gb-x96-hybrid | Qwen3-8B | 96 | hybrid | nvlink3 | infiniband_hdr | 83 | 391.10 us | 255.7 tok/s | 2,556.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.93 us |
| Qwen3-8B/a100_sxm_80gb-x99-pipeline | Qwen3-8B | 99 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x99-tensor | Qwen3-8B | 99 | tensor | nvlink3 | infiniband_hdr | 144 | 722.82 us | 138.3 tok/s | 1,383.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 357.65 us |
| Qwen3-8B/a100_sxm_80gb-x99-hybrid | Qwen3-8B | 99 | hybrid | nvlink3 | infiniband_hdr | 84 | 393.45 us | 254.2 tok/s | 2,541.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| Qwen3-8B/a100_sxm_80gb-x100-pipeline | Qwen3-8B | 100 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x100-tensor | Qwen3-8B | 100 | tensor | nvlink3 | infiniband_hdr | 144 | 722.82 us | 138.3 tok/s | 1,383.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 357.65 us |
| Qwen3-8B/a100_sxm_80gb-x100-hybrid | Qwen3-8B | 100 | hybrid | nvlink3 | infiniband_hdr | 84 | 393.45 us | 254.2 tok/s | 2,541.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.29 us |
| Qwen3-8B/a100_sxm_80gb-x111-pipeline | Qwen3-8B | 111 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x111-tensor | Qwen3-8B | 111 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x111-hybrid | Qwen3-8B | 111 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x112-pipeline | Qwen3-8B | 112 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x112-tensor | Qwen3-8B | 112 | tensor | nvlink3 | infiniband_hdr | 144 | 723.20 us | 138.3 tok/s | 1,382.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 358.04 us |
| Qwen3-8B/a100_sxm_80gb-x112-hybrid | Qwen3-8B | 112 | hybrid | nvlink3 | infiniband_hdr | 85 | 395.81 us | 252.6 tok/s | 2,526.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.65 us |
| Qwen3-8B/a100_sxm_80gb-x114-pipeline | Qwen3-8B | 114 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x114-tensor | Qwen3-8B | 114 | tensor | nvlink3 | infiniband_hdr | 144 | 723.54 us | 138.2 tok/s | 1,382.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 358.38 us |
| Qwen3-8B/a100_sxm_80gb-x114-hybrid | Qwen3-8B | 114 | hybrid | nvlink3 | infiniband_hdr | 86 | 398.17 us | 251.1 tok/s | 2,511.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.01 us |
| Qwen3-8B/a100_sxm_80gb-x152-pipeline | Qwen3-8B | 152 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x152-tensor | Qwen3-8B | 152 | tensor | nvlink3 | infiniband_hdr | 144 | 724.53 us | 138.0 tok/s | 1,380.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 359.37 us |
| Qwen3-8B/a100_sxm_80gb-x152-hybrid | Qwen3-8B | 152 | hybrid | nvlink3 | infiniband_hdr | 90 | 407.60 us | 245.3 tok/s | 2,453.4 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.44 us |
| Qwen3-8B/a100_sxm_80gb-x168-pipeline | Qwen3-8B | 168 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x168-tensor | Qwen3-8B | 168 | tensor | nvlink3 | infiniband_hdr | 144 | 724.89 us | 138.0 tok/s | 1,379.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 359.73 us |
| Qwen3-8B/a100_sxm_80gb-x168-hybrid | Qwen3-8B | 168 | hybrid | nvlink3 | infiniband_hdr | 92 | 412.31 us | 242.5 tok/s | 2,425.3 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.15 us |
| Qwen3-8B/a100_sxm_80gb-x224-pipeline | Qwen3-8B | 224 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x224-tensor | Qwen3-8B | 224 | tensor | nvlink3 | infiniband_hdr | 144 | 725.73 us | 137.8 tok/s | 1,377.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 360.57 us |
| Qwen3-8B/a100_sxm_80gb-x224-hybrid | Qwen3-8B | 224 | hybrid | nvlink3 | infiniband_hdr | 99 | 428.82 us | 233.2 tok/s | 2,332.0 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.66 us |
| Qwen3-8B/a100_sxm_80gb-x228-pipeline | Qwen3-8B | 228 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x228-tensor | Qwen3-8B | 228 | tensor | nvlink3 | infiniband_hdr | 144 | 725.82 us | 137.8 tok/s | 1,377.8 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 360.66 us |
| Qwen3-8B/a100_sxm_80gb-x228-hybrid | Qwen3-8B | 228 | hybrid | nvlink3 | infiniband_hdr | 100 | 431.18 us | 231.9 tok/s | 2,319.2 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 66.02 us |
| Qwen3-8B/a100_sxm_80gb-x304-pipeline | Qwen3-8B | 304 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x304-tensor | Qwen3-8B | 304 | tensor | nvlink3 | infiniband_hdr | 144 | 726.40 us | 137.7 tok/s | 1,376.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 38 on infiniband_hdr (traversals 2.0) = 361.24 us |
| Qwen3-8B/a100_sxm_80gb-x304-hybrid | Qwen3-8B | 304 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x335-pipeline | Qwen3-8B | 335 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x335-tensor | Qwen3-8B | 335 | tensor | nvlink3 | infiniband_hdr | 144 | 1,018.89 us | 98.1 tok/s | 981.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 653.73 us |
| Qwen3-8B/a100_sxm_80gb-x335-hybrid | Qwen3-8B | 335 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x336-pipeline | Qwen3-8B | 336 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x336-tensor | Qwen3-8B | 336 | tensor | nvlink3 | infiniband_hdr | 144 | 1,018.89 us | 98.1 tok/s | 981.5 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 653.73 us |
| Qwen3-8B/a100_sxm_80gb-x336-hybrid | Qwen3-8B | 336 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x448-pipeline | Qwen3-8B | 448 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x448-tensor | Qwen3-8B | 448 | tensor | nvlink3 | infiniband_hdr | 144 | 1,019.32 us | 98.1 tok/s | 981.1 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 654.15 us |
| Qwen3-8B/a100_sxm_80gb-x448-hybrid | Qwen3-8B | 448 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x672-pipeline | Qwen3-8B | 672 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x672-tensor | Qwen3-8B | 672 | tensor | nvlink3 | infiniband_hdr | 144 | 1,019.74 us | 98.1 tok/s | 980.6 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 654.58 us |
| Qwen3-8B/a100_sxm_80gb-x672-hybrid | Qwen3-8B | 672 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |
| Qwen3-8B/a100_sxm_80gb-x8389-pipeline | Qwen3-8B | 8389 | pipeline | nvlink3 | infiniband_hdr | 35 | 87.78 us | 1,139.2 tok/s | 11,392.5 tok/s | 31 x point_to_point span 2 on nvlink3 (traversals 1.0) = 78.35 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 9.43 us |
| Qwen3-8B/a100_sxm_80gb-x8389-tensor | Qwen3-8B | 8389 | tensor | nvlink3 | infiniband_hdr | 144 | 1,020.51 us | 98.0 tok/s | 979.9 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 72 x all_reduce span 1049 on infiniband_hdr (traversals 4.0) = 655.35 us |
| Qwen3-8B/a100_sxm_80gb-x8389-hybrid | Qwen3-8B | 8389 | hybrid | nvlink3 | infiniband_hdr | 107 | 447.68 us | 223.4 tok/s | 2,233.7 tok/s | 72 x all_reduce span 8 on nvlink3 (traversals 2.0) = 365.16 us; 35 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 82.52 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | array | array | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x92-romfill | 74,980 | 11,799.1 | 0.157 | 11,799.1 (74,980) | 6,019.5 (92,450) | 0.51x | link_latency |
| Qwen3-8B | 2 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 4 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 8 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 16 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 32 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 64 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 256 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 1024 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |
| Qwen3-8B | 4096 | no feasible ROM design | — | — | — | — | — | — (—) | — (—) | — | — |

## The two ROM floorplans on one die

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. Both machines hold the requested weights. They are different floorplans, not one floorplan with two arithmetics.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 481.6 mm2 | 256.8 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.51 GB (100.0%) |
| capacity-feasible | yes | yes |
| compute block | 186.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 264.8 mm2 |
| sustained fp8 compute roof | 9.154e+13 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 4.577e+13 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 1.019e+14 |
| **can the compute block be fed?** | **2.23x** | there is nothing to feed |
| full-array sweep | 34.47 us | 34.47 us |

**The sweep is identical.** Both the capacity density and the
read-bandwidth density scale as one over bitcell area, so a larger
compute-in-ROM cell holds proportionally fewer bits AND delivers
proportionally fewer bytes per second: the cell size cancels in
their ratio. What the larger cell costs is capacity -- the same
weights need a bigger array, and that silicon comes out of the SRAM
beside it. An earlier version of this model applied the multiplier
to area alone and credited the result with the storage cell's
bandwidth density, which handed compute-in-ROM a free 1.6x on throughput.

The ROM-plus-MAC machine is not bandwidth-starved at this point:
its array supplies 2.23x the bytes its MAC
roof demands, so the fp8 compute block can be fully fed and the
remaining array bandwidth is unused.

## The batch-amortisation fork, reported rather than resolved

`docs/ANALYTICAL_REPORT.md` names an open
high-batch question the anchor cannot settle. If a ROM cell both stores its bits
and performs the multiply for them -- compute-in-ROM, as Taalas
describes HC1 -- then a second concurrent stream needs a second pass
through the fabric, and **aggregate per-die throughput equals per-user
throughput at every batch**. If instead the ROM is storage feeding a
separate MAC array, one sweep serves the whole batch exactly as one HBM
fetch does on a GPU. Their sweep counts coincide at batch 1, but
their cell size and pre-compute reservation give them different
floorplans; the current compute-in-ROM anchor reconstruction is
capacity-infeasible. A batch-1 rate therefore cannot validate the
distinct high-batch scaling laws.

Every other table in this report uses the batched (ROM-as-storage)
machine; `-perstream` is compute-in-ROM with a global activation broadcast and `-perregion` gives each expert region its own port
variant.

The third column set is the per-region machine, which is the whole
subject of `docs/ANALYTICAL_REPORT.md`: its sweep depth
is the load of the **busiest** expert region, computed from the routing
distribution rather than from the mean engaged region.

| Model | B | Spare silicon | Batched aggregate | Per-stream aggregate | Per-region aggregate | Per-stream penalty | Per-region over broadcast | Batched binds on | Per-stream binds on | Per-region binds on |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|
| Qwen3-8B | 1 | sram | 9,236.2 | 8,993.8 | 8,993.8 | 1.03x | 1.00x | link_latency | link_latency | link_latency |
| Qwen3-8B | 2 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 4 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 8 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 16 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 32 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 64 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 256 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 1024 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 4096 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 1 | rom | 12,019.7 | 11,935.7 | 11,935.7 | 1.01x | 1.00x | link_latency | link_latency | link_latency |
| Qwen3-8B | 2 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 4 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 8 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 16 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 32 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 64 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 256 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 1024 | rom | — | — | — | — | — | — | — | — |
| Qwen3-8B | 4096 | rom | — | — | — | — | — | — | — | — |

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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x80 | 65,200 | 1.00 | 1.00 | 9,236.2 | 0.142 | link_latency | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x95-romfill | 77,425 | 3.46 | 1.00 | 12,019.7 | 0.155 | link_latency | 1.30x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x96-perstream | 78,240 | 1.00 | 1.00 | 8,993.8 | 0.115 | link_latency | 0.97x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x100-perstream-romfill | 81,500 | 3.52 | 1.00 | 11,935.7 | 0.146 | link_latency | 1.29x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x96-perregion | 78,240 | 1.00 | 1.00 | 8,993.8 | 0.115 | link_latency | 0.97x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x100-perregion-romfill | 81,500 | 3.52 | 1.00 | 11,935.7 | 0.146 | link_latency | 1.29x |

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
| Qwen3-8B | 1 | 96 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|

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
| gpu | Qwen3-8B | 1 | 6.82 | 0.7% |
| rom | Qwen3-8B | 1 | 6.82 | 8.2% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Qwen3-8B | sram | interleaved | 128 B | 1.00x |
| Qwen3-8B | hbm | interleaved | 32 B | 1.00x |

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
| Qwen3-8B | 1 | 96 | 99.64% | 887.10 | 9.27 |

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

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 249 |
| gpu | kv_read | 436 |
| gpu | link_latency | 35 |
| rom | compute | 7 |
| rom | infeasible | 2160 |
| rom | kv_read | 44 |
| rom | link_latency | 113 |
| rom | weight_read | 76 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 249 |
| rom | CAPACITY | 2160 |

## Mechanical consistency audit

**FAIL** over 30,937 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x79', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x80', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x97', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x116', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x154', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x231', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x308', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x79', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x80', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x97', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x116', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x154', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x231', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x308', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x79', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x80', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x97', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x116', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x154', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x231', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x308', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x79', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x80', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x97', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x116', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x154', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x231', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x308', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-array-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x2', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'Qwen3-8B', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 71 |
| derived | 47 |
| assumed | 70 |

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
- `kv.access_granularity_bytes.sram`
- `kv.index_layout`
- `latency.array_pass_boundaries_per_layer`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4-Flash-0731`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4-Pro-0813`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-hbm`
- `latency.array_pass_boundaries_per_layer_by_model.DeepSeek-V4.1-Flash-engram-host`
- `latency.array_pass_boundaries_per_layer_by_model.Kimi-K3`
- `latency.array_pass_boundaries_per_layer_by_model.MiMo-V2.6-Flash`
- `latency.array_pass_boundaries_per_layer_by_model.MiMo-V2.6-Pro`
- `latency.array_pass_boundaries_per_layer_by_model.Qwen3-8B`
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
- `links.inter_wafer.hop_latency_s`
- `links.nvlink.hop_latency_s`
- `links.on_package.fabric`
- `links.on_package.hop_latency_s`
- `links.rom_board_serdes.fabric`
- `links.rom_board_serdes.hop_latency_s`
- `links.rom_package_ucie.domain_size`
- `links.rom_package_ucie.fabric`
- `links.rom_wafer_serdes.fabric`
- `links.rom_wafer_serdes.hop_latency_s`
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
- `reference_parts.taalas_hc1.weight_amortization`
- `reference_parts.taalas_hc1.weight_bits_per_parameter`
- `rom.cim_cell_area_multiplier`
- `rom.cim_precompute_area_fraction`
- `rom.expert_bank_pooling`
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
- **Power is now enumerated, and it is close on one published part and
  1.8-2.3x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.44x of its published card power. **The second one FAILS its
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
