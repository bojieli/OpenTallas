# Area-constrained roofline: n5_vs_b200-qwen3-8b-1m

> CANDIDATE MODEL under n5_vs_b200: Qwen3-8B at 1,000,000 tokens. Mask-ROM silicon at TSMC N5 against NVIDIA B200 at 4NP, compared at equal silicon area. Blackwell is a two-die package, so B200 is counted per package at 1,600 mm2 of silicon. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 188x (ROM-N5-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 41x (b200_sxm-x3729-pipeline, 3,729 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 61 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Qwen3-8B takes 2 x 46,225 mm2 (92,450 mm2, wafer, KV in SRAM) at 5,035 tok/s per user and 54 tok/s per 1,000 mm2, holding 1 session, against 58 copies of one unified HBM die at the same silicon: 5.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Qwen3-8B on 138,675 mm2 of ROM silicon at 4,544 tok/s per user against 139,200 mm2 of b200_sxm-x87-nvl72-hybrid at 754 tok/s: **6.0x**, ROM binding on `link_latency` and the GPU on `layer_fixed_latency`. It holds 1 resident session against the GPU cluster's 95. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 23.56x to it.** At 554,700 mm2 on Qwen3-8B the pipeline-only GPU delivers 38.00 tok/s and the same silicon running hybrid delivers 895 tok/s.
7. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 794 us over NVLink, capping per-user decode at 1,259 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 154.6 us and cap it at 6,469 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
8. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 1 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 1 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
9. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 268 of 762 feasible points.
10. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N5.
11. **The cooling limit binds, and not where a uniform correction said it would.** 139 of 762 feasible points (18.2%) are power-limited now that leakage, clock distribution and a measured clocked-idle floor are charged per mm2 per second rather than per byte moved. The worst is `Qwen3-8B/b200_sxm-x3729-pipeline` at batch 4096 on 5,966,400 mm2, throttled 1.03x from 36 to 35 tok/s per user. **No wafer is throttled anywhere in this study**: a ROM sweep is a fixed cost spread over far more silicon, so wafer-scale is power-sparse. And HBM KV is what melts the arrays -- the worst point's dynamic energy is 91% kv read against 8.5% weight read. The ROM sweep is not what melts it.


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

**Recommended: `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill`** -- 2 x 46,225 mm2 wafers, 92,450 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `rom`.

- **5,035.0 tok/s per user** (0.20 ms/token), binding on `link_latency`
- **54.5 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 5,035 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 7,966 W at 0.086 W/mm2, 1,582.1 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 58 copies of one unified HBM die -- `b200_sxm-x58-nvl72-tensor`, 92,800 mm2, area ratio 0.9962 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 92,450 | 92,800 | 0.9962 |
| user tok/s | 5,035.0 | 849.5 | 5.93x |
| aggregate tok/s | 5,035 | 849 | 2.28x |
| resident sessions | 1 | 63 | -- |
| J/token | 1.5821 | 41.0221 | 25.9x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 63 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `b200_sxm-x347-nvl72-hybrid` at 555,200 mm2 and 895.3 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 54.5 | 1 | 5.93x |
| rank on per-user rate alone | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 54.5 | 1 | 5.93x |
| smallest feasible machine | `ROM-N5-native-SRAMKV-array-hw-hybrid-x71-romfill` | 57,865 | 1,495.1 | 25.8 | 1 | 2.16x |
| **after -- this report's rule** | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 54.5 | 1 | 5.93x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` **<-- recommended** | 92,450 | 2 | 5,035.0 | 5,035 | 54.5 | 1 | `link_latency` | 7,966 | 1,582.1 | `b200_sxm-x58-nvl72-tensor` | 5.93x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 126 | densest | `ROM-N5-native-SRAMKV-array-hw-tensor-x90` | 73,350 | 3,346.1 | 45.6 | 1 |
| array | 126 | fastest | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 146,700 | 3,799.1 | 25.9 | 1 |
| array | 126 | smallest | `ROM-N5-native-SRAMKV-array-hw-hybrid-x71-romfill` | 57,865 | 1,495.1 | 25.8 | 1 |
| wafer | 36 | densest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 54.5 | 1 |
| wafer | 36 | fastest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 54.5 | 1 |
| wafer | 36 | smallest | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 54.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N5-native-SRAMKV-array-hw-tensor-x180` | 146,700 | 3,799.1 | 3,799 | 1 | 17,825 | 4,691.8 | `layer_fixed_latency` | `b200_sxm-x92-nvl72-hybrid` | 772.6 | 100 | 58,823.1 | 0.997 | 4.92x | 12.5x |
| 1 | wafer | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | 5,035 | 1 | 7,966 | 1,582.1 | `link_latency` | `b200_sxm-x58-nvl72-tensor` | 849.5 | 63 | 41,022.1 | 0.996 | 5.93x | 25.9x |
| 1 | array @ wafer area | `ROM-N5-native-SRAMKV-array-hw-tensor-x113` | 92,095 | 3,258.6 | 3,259 | 1 | 9,676 | 2,969.4 | `layer_fixed_latency` | `b200_sxm-x58-nvl72-tensor` | 849.5 | 63 | 41,022.1 | 0.992 | 3.84x | 13.8x |
| 1 | wafer reference | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | 5,035.0 | -- | 1 | -- | 1,582.1 | -- | -- | -- | -- | -- | 0.996 | 1.55x wafer/array | -- |
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
| 1 | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 92,450 | wafer | SRAM | 1 |
| 2-4096 | *no feasible design* | -- | -- | -- | -- |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Qwen3-8B | SRAM | rom | 71, 75, 90, 93, 113, 120, 170, 180, 227, 240, 340 |
| Qwen3-8B | SRAM | sram | 72, 75, 90, 113, 120, 170, 180, 227, 240, 340 |

A wafer chosen over the array class is now compared against an array sampled at the wafer's own area and at four rungs above the array's floor; the `array @ wafer area` rows in the iso-area table above are that comparison. The curve BETWEEN rungs is still not evidence and must not be read as any.

## Serial latency and collectives

The serial part of every step is the longest path of one token's operator
dependency graph (`src/opentallas/critical_path.py`): the dependent-operator
chain priced with measured RTL depths (ROM) or a published CUDA-graph launch gap
per dependent kernel (GPU), every collective the weight split needs with its
latency and real payload, and every pipeline hop. A hybrid layout's tensor
group and every collective's reduction algorithm are searched per point.
`legacy` is the flat per-layer floor plus two all-reduces per layer this
replaced.

| Model | Design | Batch | Group | Coll./layer | Algorithms | Chain (us) | Comm. (us) | Sweep (us) | Legacy serial (us) | tok/s/user |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Qwen3-8B | `ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 1 | 32 | 2.03 | one_shot, rec_doubling | 67.84 | 93.46 | 41.22 | 106.12 | 5,035.0 |
| Qwen3-8B | `b200_sxm-x58-nvl72-tensor` | 1 | 58 | 2.03 | measured_floor | 566.80 | 177.78 | 432.61 | 181.55 | 849.5 |

## The overlap and serialisation rule

```
t_memory  = t_weight + t_kv        weights and KV share one memory system
t_memory  = max(t_weight, t_kv)    weights and KV are separate arrays
t_service = max(t_memory, t_compute)      on the AGGREGATE machine
S         = token_slots * t_service / stage_balance      the sweep a token waits for
t_user    = max(S, longest path of the token's operator graph with S spread
                over its operators by bytes, + every pipeline hop)
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
`token_slots` is 1, and the price is every collective the weight split needs,
charged on the token's operator graph (see *Serial latency and collectives*).

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 10,802.5 tok/s | 0.64x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 77.8 W | 0.31x | within 2x | FAIL |

HC1 binds on `layer_fixed_latency`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 59.54 us.

The model **under**-predicts the shipping part by 1.57x. Rather than tune the densities until the anchor
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
(5.563e+11 B/s/mm2).

### The serial-latency band, and why the gate is not fitted

The serial part of the step is the dependent-operator chain of the
Llama-3.1-8B decode graph (`src/opentallas/critical_path.py`), priced
with this repository's measured RTL depths
(`serial_latency.rom_datapath`). Nothing in it is fitted to this
anchor. Its few assumed inputs -- the clock the RTL is applied at,
the stream-unit share of the compute area, the select units, the
row-access latency -- carry ranges, and the gate is evaluated at both
ends. The flat per-layer floor this chain replaced is shown beside it.

| Serial chain | Per layer | Per token | Legacy floor per token | Modelled tok/s | Ratio | Binds on |
|---|---:|---:|---:|---:|---:|---|
| range low | 1,368.9 ns/layer | 43.81 us | 6.06 us | 13,014.5 | 0.77x | layer_fixed_latency |
| range stated | 1,860.6 ns/layer | 59.54 us | 6.06 us | 10,802.5 | 0.64x | layer_fixed_latency |
| range high | 3,206.3 ns/layer | 102.60 us | 6.06 us | 7,497.8 | 0.44x | layer_fixed_latency |

The per-layer serial cost that would land the model exactly on the
published figure is **810.3 ns/layer**. It is reported so the distance between the measured chain and the one the shipping part implies is visible. It is never used as an input: a chain longer than it means the hardwired datapath modelled here is serially slower than HC1's.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 10,783.7 | 0.64x | layer_fixed_latency |
| 3.5 | 10,802.5 | 0.64x | layer_fixed_latency |
| 4.0 | 10,783.7 | 0.64x | layer_fixed_latency |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 11,698.3 | 0.69x | layer_fixed_latency |
| 1,536 | 11,242.9 | 0.66x | layer_fixed_latency |
| 2,048 | 10,802.5 | 0.64x | layer_fixed_latency |

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
| Taalas HC1 card power | 200.0-250.0 W | 77.8 W | 0.31x | FAIL |

**Where the watts come from.**

| Term | A100 at TDP | Taalas HC1 |
|---|---:|---:|
| memory / array traffic (weights) | 213.9 W | 2.8 W |
| KV traffic | n/a: one saturating HBM stream | 7.5 W |
| operand delivery | 0.5 W | 8.8 W |
| arithmetic | 103.0 W | 6.3 W |
| static: leakage | 31.4 W | 20.6 W |
| static: clock distribution | 99.0 W | 31.6 W |
| static: memory-interface idle | 14.0 W | 0.0 W |
| **static charged** (max of the enumeration and the measured clocked-idle floor) | 144.4 W | 52.2 W |
| **total** | 461.7 W | 77.8 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 57.0 W | 0.23x | 0.28x |
| stated | 461.7 W | 1.15x | 77.8 W | 0.31x | 0.39x |
| high | 698.3 W | 1.75x | 339.3 W | 1.36x | 1.70x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.31x of the top of its published band, **3.21x low**, against 2.57x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | 0.007199 J/token | 77.8 | 10,802.5 |
| A100 80GB, weight-bound gate, same model and batch | 1.537721 J/token | 336.2 | 218.6 |

That is a factor of 214 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

**The thermal limit binds here, and this is the first version of this
study in which it could.**
Static power is charged per mm2 per second whether or not a byte moves,
so the coolable step time solves
`t >= E_dynamic / (cooling_limit - P_static)` rather than dividing the
total energy by the total limit. Under the old rule stretching a step
always reduced modelled power, so every design was coolable at some speed
and `thermal_scale` was exactly 1.0 at all 11,747 feasible points across
both studies.

- **139 of 762 feasible points (18.2%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).
- By family: gpu 139.
- By area class: wafer (>=40,000 mm2) 139.
- By KV store: hbm 139.
- By batch: B=1 18, B=2 18, B=4 18, B=8 18, B=16 18, B=32 29, B=64 14, B=256 2, B=1024 1, B=4096 3.

The cooling limit binds, and it binds where a uniform multiplier on the old traffic-proportional model said it would NOT. It is not the wafers: wafer-scale ROM silicon is power-sparse, because a ROM sweep is a fixed cost spread over far more silicon, and the busiest one here reaches 28% of its budget. It is the SMALL, DENSE ARRAYS, and specifically the ones that put KV in HBM: the worst point's dynamic energy is dominated by KV traffic and not by the ROM sweep at all. The batch dependence the earlier uniform-multiplier analysis predicted does NOT survive -- static power does not scale with traffic, so batch 1 throttles too, and the worst point here is at batch 4096.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 540 | 139 | 85.0% | 100.0% | 0.625 | 41% |
| rom | wafer (>=40,000 mm2) | 222 | 0 | 15.6% | 27.6% | 0.138 | 95% |

### The points that cannot be cooled at full speed

| Design | Model | B | mm2 | KV | Throttle | Power / budget | Static share | tok/s | tok/s unthrottled |
|---|---|---:|---:|---|---:|---|---:|---:|---:|
| `Qwen3-8B/b200_sxm-x3729-pipeline` | Qwen3-8B | 4096 | 5,966,400 | hbm | 1.026x | 3,729,000.0 / 3,729,000.0 W | 35% | 34.9 | 35.8 |
| `Qwen3-8B/b200_sxm-x61-pipeline` | Qwen3-8B | 64 | 97,600 | hbm | 1.025x | 61,000.0 / 61,000.0 W | 35% | 36.4 | 37.3 |
| `Qwen3-8B/b200_sxm-x29-pipeline` | Qwen3-8B | 1 | 46,400 | hbm | 1.024x | 29,000.0 / 29,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x29-pipeline` | Qwen3-8B | 2 | 46,400 | hbm | 1.024x | 29,000.0 / 29,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x29-pipeline` | Qwen3-8B | 4 | 46,400 | hbm | 1.024x | 29,000.0 / 29,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x29-pipeline` | Qwen3-8B | 8 | 46,400 | hbm | 1.024x | 29,000.0 / 29,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x29-pipeline` | Qwen3-8B | 16 | 46,400 | hbm | 1.024x | 29,000.0 / 29,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x36-pipeline` | Qwen3-8B | 1 | 57,600 | hbm | 1.024x | 36,000.0 / 36,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x36-pipeline` | Qwen3-8B | 2 | 57,600 | hbm | 1.024x | 36,000.0 / 36,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x36-pipeline` | Qwen3-8B | 4 | 57,600 | hbm | 1.024x | 36,000.0 / 36,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x36-pipeline` | Qwen3-8B | 8 | 57,600 | hbm | 1.024x | 36,000.0 / 36,000.0 W | 35% | 38.0 | 38.9 |
| `Qwen3-8B/b200_sxm-x36-pipeline` | Qwen3-8B | 16 | 57,600 | hbm | 1.024x | 36,000.0 / 36,000.0 W | 35% | 38.0 | 38.9 |

The worst point's dynamic energy is kv read 91.2%, weight read 8.5%, operand delivery 0.2%, arithmetic 0.0%. **The ROM sweep is not what melts it.** A mask-ROM array
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
| Qwen3-8B | 1 | 92,450 | `Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill` | 1.582140 | 7,966.1 | link_latency | `Qwen3-8B/b200_sxm-x58-nvl72-tensor` | 41.022108 | 34,847.5 | layer_fixed_latency | 25.93x |

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
| ROM capacity density | 9.380 MB/mm2 | derived |
| ROM read bandwidth density | 362.9 GB/s/mm2 | derived |
| SRAM read bandwidth density | 556.3 GB/s/mm2 | derived |
| Compute density, bf16 | 0.680 Tops/s/mm2 | derived |
| Compute density, fp8 | 1.360 Tops/s/mm2 | derived |
| Compute density, w4a8 | 1.923 Tops/s/mm2 | derived |
| Compute density, fp4 | 2.720 Tops/s/mm2 | derived |
| Compute density, fp32 | 0.042 Tops/s/mm2 | derived |
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
| Qwen3-8B | 2 | 92,450 | 6,163.6 | wafer-pipeline | 5,035.0 | wafer-hybrid | 1.22x | 932.3 | pipeline | 849.5 | tensor | 1.10x | 6.61x | 5.93x | 0.90x |
| Qwen3-8B | 3 | 138,675 | 6,163.6 | wafer-pipeline | 4,544.3 | wafer-hybrid | 1.36x | 1,081.1 | pipeline | 754.4 | hybrid | 1.43x | 5.70x | 6.02x | 1.06x |
| Qwen3-8B | 4 | 184,900 | 7,785.9 | wafer-pipeline | 4,194.2 | wafer-hybrid | 1.86x | 1,174.9 | pipeline | 846.4 | hybrid | 1.39x | 6.63x | 4.96x | 0.75x |
| Qwen3-8B | 6 | 277,350 | 7,785.9 | wafer-pipeline | 3,854.1 | wafer-hybrid | 2.02x | 1,285.0 | pipeline | 843.1 | hybrid | 1.52x | 6.06x | 4.57x | 0.75x |
| Qwen3-8B | 8 | 369,800 | 7,785.9 | wafer-pipeline | 3,578.1 | wafer-hybrid | 2.18x | 1,349.7 | pipeline | 842.0 | hybrid | 1.60x | 5.77x | 4.25x | 0.74x |
| Qwen3-8B | 12 | 554,700 | 7,785.9 | wafer-pipeline | 3,113.2 | wafer-hybrid | 2.50x | 1,421.0 | pipeline | 895.3 | hybrid | 1.59x | 5.48x | 3.48x | 0.63x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.63x to 1.06x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Qwen3-8B | 1 | fastest | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill | 92,450 | 5,035.0 | 5,035.0 | link_latency | Qwen3-8B/b200_sxm-x58-nvl72-tensor | 92,800 | 1.00x | tensor | 177.78 | 849.5 | 849.5 | layer_fixed_latency | 5.93x | 2.28x | 132.51x | 5.93x |
| Qwen3-8B | 1 | smallest silicon | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x71-romfill | 57,865 | 1,495.1 | 1,495.1 | layer_fixed_latency | Qwen3-8B/b200_sxm-x36-nvl72-tensor | 57,600 | 1.00x | tensor | 177.75 | 693.7 | 693.7 | kv_read | 2.16x | 1.09x | 39.35x | 2.16x |
| Qwen3-8B | 2 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-nvl72-tensor | 59,200 | 0.99x | tensor | 180.30 | 490.1 | 980.3 | kv_read | — | — | — | — |
| Qwen3-8B | 4 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-nvl72-tensor | 59,200 | 0.99x | tensor | 185.40 | 305.3 | 1,221.2 | kv_read | — | — | — | — |
| Qwen3-8B | 8 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-nvl72-tensor | 59,200 | 0.99x | tensor | 195.60 | 174.0 | 1,392.4 | kv_read | — | — | — | — |
| Qwen3-8B | 16 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-nvl72-tensor | 59,200 | 0.99x | tensor | 216.01 | 93.6 | 1,497.3 | kv_read | — | — | — | — |
| Qwen3-8B | 32 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-nvl72-tensor | 59,200 | 0.99x | tensor | 256.82 | 48.3 | 1,545.2 | thermal | — | — | — | — |
| Qwen3-8B | 64 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-pipeline | 59,200 | 0.99x | pipeline | 48.97 | infeasible | — | capacity_or_format | — | — | — | — |
| Qwen3-8B | 256 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-pipeline | 59,200 | 0.99x | pipeline | 53.84 | infeasible | — | capacity_or_format | — | — | — | — |
| Qwen3-8B | 1024 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-pipeline | 59,200 | 0.99x | pipeline | 73.30 | infeasible | — | capacity_or_format | — | — | — | — |
| Qwen3-8B | 4096 | no feasible ROM design | Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | 58,680 | infeasible | — | capacity_or_format | Qwen3-8B/b200_sxm-x37-pipeline | 59,200 | 0.99x | pipeline | 151.15 | infeasible | — | capacity_or_format | — | — | — | — |

## The NVLink domain is a published number, and there are two of them

This study prices an SXM module on a baseboard whose NVLink domain is 72 GPUs, which is what the vendor publishes for that part. The
same vendor also ships a 72-GPU single-tier NVLink domain in a rack-scale product built
from a different module. Borrowing the larger domain for this part would be
choosing an input by its answer, so it is reported here instead. Batch 1,
best topology at each cluster size.

| Model | GPUs | mm2 | Link us at domain 72 | Link us at domain 72 | tok/s at 72 | tok/s at 72 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-8B | 29 | 46,400 | 177.73 | 174.70 | 621.2 | 622.4 |
| Qwen3-8B | 36 | 57,600 | 177.75 | 174.71 | 693.7 | 695.2 |
| Qwen3-8B | 37 | 59,200 | 177.75 | 174.71 | 702.9 | 704.4 |
| Qwen3-8B | 38 | 60,800 | 177.75 | 174.71 | 711.8 | 713.4 |
| Qwen3-8B | 39 | 62,400 | 177.75 | 174.72 | 720.5 | 722.1 |
| Qwen3-8B | 40 | 64,000 | 177.76 | 174.72 | 728.9 | 730.6 |
| Qwen3-8B | 46 | 73,600 | 177.76 | 174.72 | 775.2 | 777.0 |
| Qwen3-8B | 47 | 75,200 | 177.77 | 174.72 | 782.2 | 784.1 |
| Qwen3-8B | 58 | 92,800 | 177.78 | 174.73 | 849.5 | 851.7 |
| Qwen3-8B | 61 | 97,600 | 177.78 | 174.73 | 865.1 | 867.4 |
| Qwen3-8B | 87 | 139,200 | 182.00 | 176.93 | 754.4 | 757.3 |
| Qwen3-8B | 92 | 147,200 | 182.00 | 176.93 | 772.6 | 775.7 |
| Qwen3-8B | 116 | 185,600 | 182.00 | 176.93 | 846.4 | 850.1 |
| Qwen3-8B | 122 | 195,200 | 182.00 | 176.93 | 862.0 | 865.7 |
| Qwen3-8B | 173 | 276,800 | 184.20 | 179.13 | 843.1 | 846.7 |
| Qwen3-8B | 231 | 369,600 | 186.39 | 181.32 | 842.0 | 845.6 |
| Qwen3-8B | 347 | 555,200 | 188.59 | 183.51 | 895.3 | 899.4 |
| Qwen3-8B | 3,729 | 5,966,400 | 256.60 | 251.52 | 852.3 | 856.0 |

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
| Qwen3-8B | 29 | 46,400 | 38.0 | 621.2 | 336.2 | tensor | 177.73 | 11.0% | kv_read |
| Qwen3-8B | 36 | 57,600 | 38.0 | 693.7 | 377.5 | tensor | 177.75 | 12.3% | kv_read |
| Qwen3-8B | 37 | 59,200 | 38.0 | 702.9 | 382.9 | tensor | 177.75 | 12.5% | layer_fixed_latency |
| Qwen3-8B | 38 | 60,800 | 38.0 | 711.8 | 388.2 | tensor | 177.75 | 12.7% | layer_fixed_latency |
| Qwen3-8B | 39 | 62,400 | 38.0 | 720.5 | 393.4 | tensor | 177.75 | 12.8% | layer_fixed_latency |
| Qwen3-8B | 40 | 64,000 | 38.0 | 728.9 | 398.4 | tensor | 177.76 | 13.0% | layer_fixed_latency |
| Qwen3-8B | 46 | 73,600 | 38.0 | 775.2 | 426.2 | tensor | 177.76 | 13.8% | layer_fixed_latency |
| Qwen3-8B | 47 | 75,200 | 38.0 | 782.2 | 430.5 | tensor | 177.77 | 13.9% | layer_fixed_latency |
| Qwen3-8B | 58 | 92,800 | 38.0 | 849.5 | 471.6 | tensor | 177.78 | 15.1% | layer_fixed_latency |
| Qwen3-8B | 61 | 97,600 | 38.0 | 865.1 | 481.2 | tensor | 177.78 | 15.4% | layer_fixed_latency |
| Qwen3-8B | 87 | 139,200 | 38.0 | 654.3 | 754.4 | hybrid | 182.00 | 13.7% | layer_fixed_latency |
| Qwen3-8B | 92 | 147,200 | 38.0 | 661.1 | 772.6 | hybrid | 182.00 | 14.1% | layer_fixed_latency |
| Qwen3-8B | 116 | 185,600 | 38.0 | 686.7 | 846.4 | hybrid | 182.00 | 15.4% | layer_fixed_latency |
| Qwen3-8B | 122 | 195,200 | 38.0 | 691.7 | 862.0 | hybrid | 182.00 | 15.7% | layer_fixed_latency |
| Qwen3-8B | 173 | 276,800 | 38.0 | 718.0 | 843.1 | hybrid | 184.20 | 15.5% | layer_fixed_latency |
| Qwen3-8B | 231 | 369,600 | 38.0 | 735.1 | 842.0 | hybrid | 186.39 | 15.7% | layer_fixed_latency |
| Qwen3-8B | 347 | 555,200 | 38.0 | 753.9 | 895.3 | hybrid | 188.59 | 16.9% | layer_fixed_latency |
| Qwen3-8B | 3729 | 5,966,400 | 38.0 | 787.8 | 852.3 | hybrid | 256.60 | 21.9% | layer_fixed_latency |

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
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72 | Qwen3-8B | 72 | pipeline | rom_package_ucie | rom_board_serdes | 35 | 1.16 us | 86,080.4 tok/s | 860,803.8 tok/s | 27 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.33 us; 8 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 0.84 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x72 | Qwen3-8B | 72 | tensor | rom_package_ucie | rom_board_serdes | 144 | 66.06 us | 1,513.8 tok/s | 15,137.7 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 72 x all_reduce span 18 on rom_board_serdes (traversals 8.8) = 64.29 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x72 | Qwen3-8B | 72 | hybrid | rom_package_ucie | rom_board_serdes | 89 | 3.55 us | 28,175.8 tok/s | 281,758.0 tok/s | 72 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 1.77 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.78 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x72 | Qwen3-8B | 72 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x2 | Qwen3-8B | 2 | pipeline | on_wafer_n5 | rom_wafer_serdes | 35 | 4.38 us | 22,857.1 tok/s | 228,570.9 tok/s | 35 x point_to_point span 2 on on_wafer_n5 (traversals 1.0) = 4.38 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x72 | Qwen3-8B | 72 | tensor | nvlink5 | infiniband_ndr | 144 | 498.30 us | 200.7 tok/s | 2,006.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 9 on infiniband_ndr (traversals 2.0) = 323.78 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-tensor-x2 | Qwen3-8B | 2 | tensor | on_wafer_n5 | rom_wafer_serdes | 144 | 154.59 us | 646.9 tok/s | 6,468.8 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 72 x all_reduce span 2 on rom_wafer_serdes (traversals 2.2) = 15.99 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-array-hybrid-x72 | Qwen3-8B | 72 | hybrid | nvlink5 | infiniband_ndr | 80 | 192.07 us | 520.6 tok/s | 5,206.4 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 8 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 17.55 us |
| Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | Qwen3-8B | 2 | hybrid | on_wafer_n5 | rom_wafer_serdes | 73 | 138.70 us | 721.0 tok/s | 7,209.7 tok/s | 72 x all_reduce span 57 on on_wafer_n5 (traversals 15.4) = 138.60 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Qwen3-8B/b200_sxm-x29-pipeline | Qwen3-8B | 29 | pipeline | nvlink5 | infiniband_ndr | 28 | 36.81 us | 2,716.7 tok/s | 27,167.2 tok/s | 25 x point_to_point span 2 on nvlink5 (traversals 1.0) = 30.23 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-tensor | Qwen3-8B | 29 | tensor | nvlink5 | infiniband_ndr | 144 | 493.38 us | 202.7 tok/s | 2,026.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x29-hybrid | Qwen3-8B | 29 | hybrid | nvlink5 | infiniband_ndr | 75 | 181.10 us | 552.2 tok/s | 5,521.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x29-nvl72-tensor | Qwen3-8B | 29 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.70 us | 572.4 tok/s | 5,724.2 tok/s | 72 x all_reduce span 29 on nvlink5_nvl72 (traversals 2.0) = 174.70 us |
| Qwen3-8B/b200_sxm-x36-pipeline | Qwen3-8B | 36 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x36-tensor | Qwen3-8B | 36 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x36-hybrid | Qwen3-8B | 36 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x36-nvl72-tensor | Qwen3-8B | 36 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.71 us | 572.4 tok/s | 5,723.7 tok/s | 72 x all_reduce span 36 on nvlink5_nvl72 (traversals 2.0) = 174.71 us |
| Qwen3-8B/b200_sxm-x37-pipeline | Qwen3-8B | 37 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x37-tensor | Qwen3-8B | 37 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x37-hybrid | Qwen3-8B | 37 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x37-nvl72-tensor | Qwen3-8B | 37 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.71 us | 572.4 tok/s | 5,723.7 tok/s | 72 x all_reduce span 37 on nvlink5_nvl72 (traversals 2.0) = 174.71 us |
| Qwen3-8B/b200_sxm-x38-pipeline | Qwen3-8B | 38 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x38-tensor | Qwen3-8B | 38 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x38-hybrid | Qwen3-8B | 38 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x38-nvl72-tensor | Qwen3-8B | 38 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.71 us | 572.4 tok/s | 5,723.6 tok/s | 72 x all_reduce span 38 on nvlink5_nvl72 (traversals 2.0) = 174.71 us |
| Qwen3-8B/b200_sxm-x39-pipeline | Qwen3-8B | 39 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x39-tensor | Qwen3-8B | 39 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x39-hybrid | Qwen3-8B | 39 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x39-nvl72-tensor | Qwen3-8B | 39 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.72 us | 572.4 tok/s | 5,723.6 tok/s | 72 x all_reduce span 39 on nvlink5_nvl72 (traversals 2.0) = 174.72 us |
| Qwen3-8B/b200_sxm-x40-pipeline | Qwen3-8B | 40 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x40-tensor | Qwen3-8B | 40 | tensor | nvlink5 | infiniband_ndr | 144 | 495.15 us | 202.0 tok/s | 2,019.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x40-hybrid | Qwen3-8B | 40 | hybrid | nvlink5 | infiniband_ndr | 76 | 183.30 us | 545.6 tok/s | 5,455.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x40-nvl72-tensor | Qwen3-8B | 40 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.72 us | 572.4 tok/s | 5,723.5 tok/s | 72 x all_reduce span 40 on nvlink5_nvl72 (traversals 2.0) = 174.72 us |
| Qwen3-8B/b200_sxm-x46-pipeline | Qwen3-8B | 46 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x46-tensor | Qwen3-8B | 46 | tensor | nvlink5 | infiniband_ndr | 144 | 496.33 us | 201.5 tok/s | 2,014.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 321.81 us |
| Qwen3-8B/b200_sxm-x46-hybrid | Qwen3-8B | 46 | hybrid | nvlink5 | infiniband_ndr | 77 | 185.49 us | 539.1 tok/s | 5,391.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| Qwen3-8B/b200_sxm-x46-nvl72-tensor | Qwen3-8B | 46 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.72 us | 572.3 tok/s | 5,723.3 tok/s | 72 x all_reduce span 46 on nvlink5_nvl72 (traversals 2.0) = 174.72 us |
| Qwen3-8B/b200_sxm-x47-pipeline | Qwen3-8B | 47 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x47-tensor | Qwen3-8B | 47 | tensor | nvlink5 | infiniband_ndr | 144 | 496.33 us | 201.5 tok/s | 2,014.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 6 on infiniband_ndr (traversals 2.0) = 321.81 us |
| Qwen3-8B/b200_sxm-x47-hybrid | Qwen3-8B | 47 | hybrid | nvlink5 | infiniband_ndr | 77 | 185.49 us | 539.1 tok/s | 5,391.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 5 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 10.97 us |
| Qwen3-8B/b200_sxm-x47-nvl72-tensor | Qwen3-8B | 47 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.72 us | 572.3 tok/s | 5,723.3 tok/s | 72 x all_reduce span 47 on nvlink5_nvl72 (traversals 2.0) = 174.72 us |
| Qwen3-8B/b200_sxm-x58-pipeline | Qwen3-8B | 58 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x58-tensor | Qwen3-8B | 58 | tensor | nvlink5 | infiniband_ndr | 144 | 497.81 us | 200.9 tok/s | 2,008.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 323.29 us |
| Qwen3-8B/b200_sxm-x58-hybrid | Qwen3-8B | 58 | hybrid | nvlink5 | infiniband_ndr | 79 | 189.88 us | 526.7 tok/s | 5,266.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| Qwen3-8B/b200_sxm-x58-nvl72-tensor | Qwen3-8B | 58 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.0 tok/s | 72 x all_reduce span 58 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x61-pipeline | Qwen3-8B | 61 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x61-tensor | Qwen3-8B | 61 | tensor | nvlink5 | infiniband_ndr | 144 | 497.81 us | 200.9 tok/s | 2,008.8 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 8 on infiniband_ndr (traversals 2.0) = 323.29 us |
| Qwen3-8B/b200_sxm-x61-hybrid | Qwen3-8B | 61 | hybrid | nvlink5 | infiniband_ndr | 79 | 189.88 us | 526.7 tok/s | 5,266.6 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 7 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 15.36 us |
| Qwen3-8B/b200_sxm-x61-nvl72-tensor | Qwen3-8B | 61 | tensor | nvlink5_nvl72 | infiniband_ndr | 72 | 174.73 us | 572.3 tok/s | 5,723.0 tok/s | 72 x all_reduce span 61 on nvlink5_nvl72 (traversals 2.0) = 174.73 us |
| Qwen3-8B/b200_sxm-x87-pipeline | Qwen3-8B | 87 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x87-tensor | Qwen3-8B | 87 | tensor | nvlink5 | infiniband_ndr | 144 | 499.01 us | 200.4 tok/s | 2,004.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 11 on infiniband_ndr (traversals 2.0) = 324.49 us |
| Qwen3-8B/b200_sxm-x87-hybrid | Qwen3-8B | 87 | hybrid | nvlink5 | infiniband_ndr | 82 | 196.46 us | 509.0 tok/s | 5,090.1 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 10 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 21.94 us |
| Qwen3-8B/b200_sxm-x87-nvl72-tensor | Qwen3-8B | 87 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x87-nvl72-hybrid | Qwen3-8B | 87 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x92-pipeline | Qwen3-8B | 92 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x92-tensor | Qwen3-8B | 92 | tensor | nvlink5 | infiniband_ndr | 144 | 499.28 us | 200.3 tok/s | 2,002.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 12 on infiniband_ndr (traversals 2.0) = 324.76 us |
| Qwen3-8B/b200_sxm-x92-hybrid | Qwen3-8B | 92 | hybrid | nvlink5 | infiniband_ndr | 83 | 198.65 us | 503.4 tok/s | 5,033.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 11 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 24.13 us |
| Qwen3-8B/b200_sxm-x92-nvl72-tensor | Qwen3-8B | 92 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x92-nvl72-hybrid | Qwen3-8B | 92 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x116-pipeline | Qwen3-8B | 116 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x116-tensor | Qwen3-8B | 116 | tensor | nvlink5 | infiniband_ndr | 144 | 499.87 us | 200.1 tok/s | 2,000.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 15 on infiniband_ndr (traversals 2.0) = 325.35 us |
| Qwen3-8B/b200_sxm-x116-hybrid | Qwen3-8B | 116 | hybrid | nvlink5 | infiniband_ndr | 86 | 205.23 us | 487.2 tok/s | 4,872.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 14 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 30.71 us |
| Qwen3-8B/b200_sxm-x116-nvl72-tensor | Qwen3-8B | 116 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x116-nvl72-hybrid | Qwen3-8B | 116 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x122-pipeline | Qwen3-8B | 122 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x122-tensor | Qwen3-8B | 122 | tensor | nvlink5 | infiniband_ndr | 144 | 500.02 us | 200.0 tok/s | 1,999.9 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 16 on infiniband_ndr (traversals 2.0) = 325.50 us |
| Qwen3-8B/b200_sxm-x122-hybrid | Qwen3-8B | 122 | hybrid | nvlink5 | infiniband_ndr | 87 | 207.43 us | 482.1 tok/s | 4,821.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 15 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 32.91 us |
| Qwen3-8B/b200_sxm-x122-nvl72-tensor | Qwen3-8B | 122 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 484.75 us | 206.3 tok/s | 2,062.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 2 on infiniband_ndr (traversals 2.0) = 310.01 us |
| Qwen3-8B/b200_sxm-x122-nvl72-hybrid | Qwen3-8B | 122 | hybrid | nvlink5_nvl72 | infiniband_ndr | 73 | 176.93 us | 565.2 tok/s | 5,651.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 1 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 2.19 us |
| Qwen3-8B/b200_sxm-x173-pipeline | Qwen3-8B | 173 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x173-tensor | Qwen3-8B | 173 | tensor | nvlink5 | infiniband_ndr | 144 | 500.62 us | 199.8 tok/s | 1,997.5 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 22 on infiniband_ndr (traversals 2.0) = 326.10 us |
| Qwen3-8B/b200_sxm-x173-hybrid | Qwen3-8B | 173 | hybrid | nvlink5 | infiniband_ndr | 93 | 220.59 us | 453.3 tok/s | 4,533.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 21 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 46.07 us |
| Qwen3-8B/b200_sxm-x173-nvl72-tensor | Qwen3-8B | 173 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 490.65 us | 203.8 tok/s | 2,038.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 3 on infiniband_ndr (traversals 2.0) = 315.91 us |
| Qwen3-8B/b200_sxm-x173-nvl72-hybrid | Qwen3-8B | 173 | hybrid | nvlink5_nvl72 | infiniband_ndr | 74 | 179.13 us | 558.3 tok/s | 5,582.6 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 2 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 4.39 us |
| Qwen3-8B/b200_sxm-x231-pipeline | Qwen3-8B | 231 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x231-tensor | Qwen3-8B | 231 | tensor | nvlink5 | infiniband_ndr | 144 | 501.01 us | 199.6 tok/s | 1,996.0 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 29 on infiniband_ndr (traversals 2.0) = 326.49 us |
| Qwen3-8B/b200_sxm-x231-hybrid | Qwen3-8B | 231 | hybrid | nvlink5 | infiniband_ndr | 100 | 235.95 us | 423.8 tok/s | 4,238.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 28 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 61.43 us |
| Qwen3-8B/b200_sxm-x231-nvl72-tensor | Qwen3-8B | 231 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 493.60 us | 202.6 tok/s | 2,025.9 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 4 on infiniband_ndr (traversals 2.0) = 318.86 us |
| Qwen3-8B/b200_sxm-x231-nvl72-hybrid | Qwen3-8B | 231 | hybrid | nvlink5_nvl72 | infiniband_ndr | 75 | 181.32 us | 551.5 tok/s | 5,515.1 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 3 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 6.58 us |
| Qwen3-8B/b200_sxm-x347-pipeline | Qwen3-8B | 347 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x347-tensor | Qwen3-8B | 347 | tensor | nvlink5 | infiniband_ndr | 144 | 501.43 us | 199.4 tok/s | 1,994.3 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 44 on infiniband_ndr (traversals 2.0) = 326.91 us |
| Qwen3-8B/b200_sxm-x347-hybrid | Qwen3-8B | 347 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| Qwen3-8B/b200_sxm-x347-nvl72-tensor | Qwen3-8B | 347 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 495.37 us | 201.9 tok/s | 2,018.7 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 5 on infiniband_ndr (traversals 2.0) = 320.63 us |
| Qwen3-8B/b200_sxm-x347-nvl72-hybrid | Qwen3-8B | 347 | hybrid | nvlink5_nvl72 | infiniband_ndr | 76 | 183.51 us | 544.9 tok/s | 5,449.2 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x3729-pipeline | Qwen3-8B | 3729 | pipeline | nvlink5 | infiniband_ndr | 35 | 46.26 us | 2,161.8 tok/s | 21,618.1 tok/s | 31 x point_to_point span 2 on nvlink5 (traversals 1.0) = 37.48 us; 4 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 8.78 us |
| Qwen3-8B/b200_sxm-x3729-tensor | Qwen3-8B | 3729 | tensor | nvlink5 | infiniband_ndr | 144 | 794.47 us | 125.9 tok/s | 1,258.7 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 72 x all_reduce span 467 on infiniband_ndr (traversals 4.0) = 619.95 us |
| Qwen3-8B/b200_sxm-x3729-hybrid | Qwen3-8B | 3729 | hybrid | nvlink5 | infiniband_ndr | 107 | 251.30 us | 397.9 tok/s | 3,979.2 tok/s | 72 x all_reduce span 8 on nvlink5 (traversals 2.0) = 174.52 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |
| Qwen3-8B/b200_sxm-x3729-nvl72-tensor | Qwen3-8B | 3729 | tensor | nvlink5_nvl72 | infiniband_ndr | 144 | 501.77 us | 199.3 tok/s | 1,993.0 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 72 x all_reduce span 52 on infiniband_ndr (traversals 2.0) = 327.03 us |
| Qwen3-8B/b200_sxm-x3729-nvl72-hybrid | Qwen3-8B | 3729 | hybrid | nvlink5_nvl72 | infiniband_ndr | 107 | 251.52 us | 397.6 tok/s | 3,975.8 tok/s | 72 x all_reduce span 72 on nvlink5_nvl72 (traversals 2.0) = 174.74 us; 35 x point_to_point span 2 on infiniband_ndr (traversals 1.0) = 76.78 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Qwen3-8B | 1 | wafer | wafer | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill | 92,450 | 5,035.0 | 0.054 | 3,799.1 (146,700) | 5,035.0 (92,450) | 1.33x | link_latency |
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

This probe requests 3.51 GB of weights at 3.5 bits per parameter on the same 815 mm2. The ROM-plus-MAC floorplan holds the requested weights; the compute-in-ROM floorplan holds only 100.0% and is infeasible at this area. The failed floorplan is retained so the capacity cost of the larger cell remains visible.

| | ROM + MAC array | compute-in-ROM |
|---|---:|---:|
| cell area vs a storage-only bit | 1.0x | 1.6x |
| ROM array | 374.6 mm2 | 199.8 mm2 |
| weight capacity | 3.51 GB (100.0%) | 3.51 GB (100.0%) |
| capacity-feasible | yes | **no** |
| compute block | 293.7 mm2 | 146.7 mm2 (pre-compute only) |
| SRAM | 0.0 mm2 | 321.8 mm2 |
| sustained fp8 compute roof | 2.197e+14 ops/s | the array sweep itself |
| weight bytes/s the roof wants | 1.098e+14 | n/a |
| weight bytes/s the array supplies | 1.019e+14 | 1.019e+14 |
| **can the compute block be fed?** | **0.93x** | there is nothing to feed |
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

The ROM-plus-MAC machine is bandwidth-starved: its array supplies
only 0.93x of the bytes its MAC roof wants,
so some compute capacity cannot be exercised.

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
| Qwen3-8B | 1 | sram | 3,829.7 | 3,733.6 | 3,733.6 | 1.03x | 1.00x | link_latency | link_latency | link_latency |
| Qwen3-8B | 2 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 4 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 8 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 16 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 32 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 64 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 256 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 1024 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 4096 | sram | — | — | — | — | — | — | — | — |
| Qwen3-8B | 1 | rom | 5,035.0 | 4,985.4 | 4,985.4 | 1.01x | 1.00x | link_latency | link_latency | link_latency |
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
| Qwen3-8B | 1 | batched | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2 | 92,450 | 1.00 | 1.00 | 3,829.7 | 0.041 | link_latency | 1.00x |
| Qwen3-8B | 1 | batched | rom | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-romfill | 92,450 | 12.49 | 1.00 | 5,035.0 | 0.054 | link_latency | 1.31x |
| Qwen3-8B | 1 | per_stream | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perstream | 92,450 | 1.00 | 1.00 | 3,733.6 | 0.040 | link_latency | 0.97x |
| Qwen3-8B | 1 | per_stream | rom | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perstream-romfill | 92,450 | 30.14 | 1.00 | 4,985.4 | 0.054 | link_latency | 1.30x |
| Qwen3-8B | 1 | per_region | sram | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion | 92,450 | 1.00 | 1.00 | 3,733.6 | 0.040 | link_latency | 0.97x |
| Qwen3-8B | 1 | per_region | rom | Qwen3-8B/ROM-N5-native-SRAMKV-wafer-hybrid-x2-perregion-romfill | 92,450 | 30.14 | 1.00 | 4,985.4 | 0.054 | link_latency | 1.30x |

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
| Qwen3-8B | 1 | 75 | 1.00 | 1.000 | 1.000 | 1.00x |

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
| gpu | Qwen3-8B | 1 | 566.80 | 50.7% |
| rom | Qwen3-8B | 1 | 67.84 | 34.2% |

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
| Qwen3-8B | 1 | 75 | 99.19% | 689.91 | 9.27 |

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
| gpu | infeasible | 260 |
| gpu | kv_read | 260 |
| gpu | layer_fixed_latency | 33 |
| gpu | link_latency | 108 |
| gpu | thermal | 139 |
| rom | infeasible | 1998 |
| rom | kv_read | 8 |
| rom | layer_fixed_latency | 102 |
| rom | link_latency | 91 |
| rom | weight_read | 21 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 260 |
| rom | CAPACITY | 1998 |

## Mechanical consistency audit

**FAIL** over 31,546 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x72', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x75', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x90', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x120', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x180', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x240', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x72', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x75', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x90', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x120', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x180', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x240', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-tensor-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x72', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x75', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x90', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x120', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x180', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x240', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-hw-hybrid-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x72', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x75', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x90', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x113', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x120', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x170', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x180', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x227', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x240', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-pipeline-x340', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x2', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x3', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x4', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x6', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x8', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-wafer-pipeline-x12', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x72', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x75', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x90', 'Qwen3-8B', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Qwen3-8B/ROM-N5-native-SRAMKV-array-tensor-x113', 'Qwen3-8B', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 48 |
| assumed | 77 |

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
- `serial_latency.hardware_links.rom_board_serdes`
- `serial_latency.hardware_links.rom_package_ucie`
- `serial_latency.hardware_links.rom_wafer_serdes`
- `serial_latency.rom_datapath.hbm_random_row_latency_s`
- `serial_latency.rom_datapath.rom_row_access_s`
- `serial_latency.rom_datapath.select_units_per_die`
- `serial_latency.rom_datapath.stream_area_fraction`
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
  2.6-3.2x low on the other.** Leakage, clock distribution, operand
  delivery and a measured clocked-idle floor are charged per mm2 per
  second whether or not a byte moves, and the HBM traffic energy is a
  measured SC 2025 figure rather than an HBM2-era model. The A100 lands
  at 1.15x of its published TDP under a saturating load; the Taalas HC1
  lands at 0.31x of its published card power. **The second one FAILS its
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
