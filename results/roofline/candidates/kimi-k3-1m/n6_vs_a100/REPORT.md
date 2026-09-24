# Area-constrained roofline: n6_vs_a100-kimi-k3-1m

> CANDIDATE MODEL under n6_vs_a100: Kimi-K3 at 1,000,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 2,663x (ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream, 5,389 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 174 devices. On the GPU side the correction reaches 329x (a100_sxm_80gb-x5316-pipeline, 5,316 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 211 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Kimi-K3 takes 399 x 815 mm2 (325,185 mm2, array, KV in SRAM) at 1,720 tok/s per user and 5 tok/s per 1,000 mm2, holding 1 session, against 394 copies of one unified HBM die at the same silicon: 5.2x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Kimi-K3 on 416,025 mm2 of ROM silicon at 1,860 tok/s per user against 416,304 mm2 of a100_sxm_80gb-x504-tensor at 335 tok/s: **5.6x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 2,433. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 32.57x to it.** At 4,391,375 mm2 on Kimi-K3 the pipeline-only GPU delivers 10.86 tok/s and the same silicon running tensor delivers 354 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.49x (Kimi-K3, ROM binding on `kv_read`) to 0.63x (Kimi-K3, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** Kimi-K3 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 17 to 69,614 tok/s, and its rate with every slot occupied from 70,039 to 70,039. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 5,389 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,783 us over NVLink, capping per-user decode at 359 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 727.6 us and cap it at 1,374 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 1 to the array and 9 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 97 of 1122 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 3.5x of aggregate throughput (Kimi-K3). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 3.49x, on Kimi-K3 at batch 4096, where the busiest region carries 3.45x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 8 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 91% of its cooling budget. The companion study at the other node does have power-limited points.


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

### Kimi-K3 at 1,000,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x399`** -- 399 x 815 mm2 reticle dies, 325,185 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **1,720.2 tok/s per user** (0.58 ms/token), binding on `link_latency`
- **5.3 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 1,720 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 20,446 W at 0.063 W/mm2, 11,885.9 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 394 copies of one unified HBM die -- `a100_sxm_80gb-x394-tensor`, 325,444 mm2, area ratio 0.9992 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 325,185 | 325,444 | 0.9992 |
| user tok/s | 1,720.2 | 329.2 | 5.23x |
| aggregate tok/s | 1,720 | 329 | 0.40x |
| resident sessions | 1 | 1,878 | -- |
| J/token | 11.8859 | 190.4722 | 16.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,878 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x280-tensor` at 231,280 mm2 and 421.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-tensor-x9` | 416,025 | 1,860.1 | 4.5 | 1 | 5.56x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-tensor-x9` | 416,025 | 1,860.1 | 4.5 | 1 | 5.56x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x340` | 277,100 | 717.2 | 2.6 | 1 | 2.21x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 1,720.2 | 5.3 | 1 | 5.23x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 1,720.2 | 5.3 | -- | 5.3 | ACCEPT |
| `ROM-N6-native-SRAMKV-wafer-tensor-x8` | 369,800 | 1,759.2 | 4.8 | 0.9 | 5.3 | stop |
| `ROM-N6-native-SRAMKV-wafer-tensor-x9` | 416,025 | 1,860.1 | 4.5 | 1.5 | 5.3 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x399` **<-- recommended** | 325,185 | 399 | 1,720.2 | 1,720 | 5.3 | 1 | `link_latency` | 20,446 | 11,885.9 | `a100_sxm_80gb-x394-tensor` | 5.23x |
| `ROM-N6-native-SRAMKV-wafer-tensor-x8` | 369,800 | 8 | 1,759.2 | 1,759 | 4.8 | 1 | `link_latency` | 26,663 | 15,156.3 | `a100_sxm_80gb-x448-tensor` | 5.30x |
| `ROM-N6-native-SRAMKV-wafer-tensor-x9` | 416,025 | 9 | 1,860.1 | 1,860 | 4.5 | 1 | `link_latency` | 33,394 | 17,953.4 | `a100_sxm_80gb-x504-tensor` | 5.56x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 48 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 1,720.2 | 5.3 | 1 |
| array | 48 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 1,720.2 | 5.3 | 1 |
| array | 48 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x340` | 277,100 | 717.2 | 2.6 | 1 |
| wafer | 39 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | 369,800 | 1,759.2 | 4.8 | 1 |
| wafer | 39 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x9` | 416,025 | 1,860.1 | 4.5 | 1 |
| wafer | 39 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x6` | 277,350 | 697.3 | 2.5 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 1,720.2 | 1,720 | 1 | 20,446 | 11,885.9 | `link_latency` | `a100_sxm_80gb-x394-tensor` | 329.2 | 1,878 | 190,472.2 | 0.999 | 5.23x | 16.0x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x9` | 416,025 | 1,860.1 | 1,860 | 1 | 33,394 | 17,953.4 | `link_latency` | `a100_sxm_80gb-x504-tensor` | 334.6 | 2,433 | 235,117.5 | 0.999 | 5.56x | 13.1x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x95` | 4,391,375 | 1,284.5 | 2,569 | 4,121 | 625,890 | 243,636.9 | `link_latency` | `a100_sxm_80gb-x5316-tensor` | 314.9 | 26,706 | 1,230,471.3 | 1.000 | 4.08x | 5.1x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x95` | 4,391,375 | 1,245.3 | 4,981 | 4,121 | 630,134 | 126,497.8 | `link_latency` | `a100_sxm_80gb-x5316-tensor` | 258.4 | 26,706 | 751,446.7 | 1.000 | 4.82x | 5.9x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x95` | 4,391,375 | 1,173.8 | 9,391 | 4,121 | 637,888 | 67,928.1 | `link_latency` | `a100_sxm_80gb-x5316-tensor` | 190.1 | 26,706 | 512,079.2 | 1.000 | 6.18x | 7.5x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x95` | 4,391,375 | 1,052.9 | 16,846 | 4,121 | 650,994 | 38,642.9 | `link_latency` | `a100_sxm_80gb-x5316-tensor` | 124.1 | 26,706 | 392,781.0 | 1.000 | 8.48x | 10.2x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x95` | 4,391,375 | 873.0 | 27,937 | 4,121 | 670,472 | 23,999.6 | `link_latency` | `a100_sxm_80gb-x5316-expert` | 83.0 | 21,543 | 294,637.9 | 1.000 | 10.52x | 12.3x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4,391,375 | 698.4 | 66,352 | 4,121 | 740,392 | 15,694.2 | `kv_read` | `a100_sxm_80gb-x5316-expert` | 79.6 | 21,543 | 155,648.0 | 1.000 | 8.77x | 9.9x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4,391,375 | 313.6 | 80,281 | 4,121 | 763,637 | 9,512.0 | `kv_read` | `a100_sxm_80gb-x5316-hybrid` | 78.7 | 26,706 | 55,754.2 | 1.000 | 3.99x | 4.6x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4,391,375 | 86.4 | 88,503 | 4,121 | 777,315 | 8,782.9 | `kv_read` | `a100_sxm_80gb-x5316-hybrid` | 69.5 | 26,706 | 24,323.4 | 1.000 | 1.24x | 1.7x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4,391,375 | 22.2 | 90,829 | 4,121 | 781,039 | 8,599.1 | `kv_read` | `a100_sxm_80gb-x5316-hybrid` | 35.2 | 26,706 | 13,056.5 | 1.000 | 0.63x | 1.0x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | array | SRAM | 1 |
| 2-32 | `ROM-N6-native-HBMKV-wafer-tensor-x95` | 4,391,375 | wafer | HBM | 4,121 |
| 64-4096 | `ROM-N6-native-HBMKV-wafer-hybrid-x95` | 4,391,375 | wafer | HBM | 4,121 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Kimi-K3 | SRAM | rom | 340, 382, 396, 399 |
| Kimi-K3 | SRAM | sram | 340, 382, 396, 399 |

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

- **0 of 1,122 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 91% of its cooling budget, and the busiest wafer-scale ROM design 36%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 771 | 0 | 75.8% | 90.6% | 0.439 | 48% |
| rom | wafer (>=40,000 mm2) | 351 | 0 | 15.1% | 35.6% | 0.178 | 95% |

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
| Kimi-K3 | 1 | 416,025 | `Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x9` | 17.953357 | 33,394.5 | link_latency | `Kimi-K3/a100_sxm_80gb-x504-tensor` | 235.117511 | 78,672.8 | link_latency | 13.10x |
| Kimi-K3 | 2 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95` | 243.636916 | 625,890.4 | link_latency | `Kimi-K3/a100_sxm_80gb-x5316-tensor` | 1,230.471325 | 774,962.3 | link_latency | 5.05x |
| Kimi-K3 | 4 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95` | 126.497847 | 630,134.1 | link_latency | `Kimi-K3/a100_sxm_80gb-x5316-tensor` | 751.446690 | 776,648.3 | link_latency | 5.94x |
| Kimi-K3 | 8 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95` | 67.928111 | 637,888.4 | link_latency | `Kimi-K3/a100_sxm_80gb-x5316-tensor` | 512.079181 | 778,576.0 | link_latency | 7.54x |
| Kimi-K3 | 16 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95` | 38.642874 | 650,994.4 | link_latency | `Kimi-K3/a100_sxm_80gb-x5316-tensor` | 392.780955 | 780,164.9 | link_latency | 10.16x |
| Kimi-K3 | 32 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95` | 23.999629 | 670,471.7 | link_latency | `Kimi-K3/a100_sxm_80gb-x5316-expert` | 294.637929 | 782,660.4 | weight_read | 12.28x |
| Kimi-K3 | 64 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95` | 15.694221 | 740,391.6 | kv_read | `Kimi-K3/a100_sxm_80gb-x5316-expert` | 155.647990 | 793,290.6 | weight_read | 9.92x |
| Kimi-K3 | 256 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95` | 9.512049 | 763,636.9 | kv_read | `Kimi-K3/a100_sxm_80gb-x5316-hybrid` | 55.754154 | 1,690,477.6 | weight_read | 4.60x |
| Kimi-K3 | 1024 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95` | 8.782923 | 777,314.8 | kv_read | `Kimi-K3/a100_sxm_80gb-x5316-hybrid` | 24.323367 | 1,730,113.7 | weight_read | 1.66x |
| Kimi-K3 | 4096 | 4,391,375 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95` | 8.599052 | 781,039.2 | kv_read | `Kimi-K3/a100_sxm_80gb-x5316-hybrid` | 13.056480 | 1,882,433.9 | compute | 1.01x |

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
| Kimi-K3 | 1,000,000 | 2,800 B | 1,560.9 GB | 4.46 | 14.273 GB | 14.273 GB | 9.6 |

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
| Kimi-K3 | 6 | 277,350 | 995.4 | wafer-pipeline | 697.3 | wafer-tensor | 1.43x | 1,865.2 | pipeline | 325.0 | tensor | 5.74x | 0.53x | 2.15x | 4.02x |
| Kimi-K3 | 8 | 369,800 | 7,201.2 | wafer-pipeline | 1,759.2 | wafer-tensor | 4.09x | 2,137.7 | pipeline | 332.1 | tensor | 6.44x | 3.37x | 5.30x | 1.57x |
| Kimi-K3 | 12 | 554,700 | 13,353.5 | wafer-pipeline | 1,833.4 | wafer-tensor | 7.28x | 2,503.5 | pipeline | 339.6 | tensor | 7.37x | 5.33x | 5.40x | 1.01x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.01x to 4.02x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Kimi-K3 | 1 | fastest | Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x9 | 416,025 | 1,860.1 | 1,860.1 | link_latency | Kimi-K3/a100_sxm_80gb-x504-tensor | 416,304 | 1.00x | tensor | 2,778.55 | 334.6 | 334.6 | link_latency | 5.56x | 0.34x | 171.35x | 5.56x |
| Kimi-K3 | 1 | smallest silicon | Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x340 | 277,100 | 717.2 | 717.2 | compute | Kimi-K3/a100_sxm_80gb-x335-tensor | 276,710 | 1.00x | tensor | 2,776.01 | 324.9 | 324.9 | link_latency | 2.21x | 0.20x | 66.07x | 2.21x |
| Kimi-K3 | 2 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,284.5 | 2,568.9 | link_latency | Kimi-K3/a100_sxm_80gb-x5316-tensor | 4,391,016 | 1.00x | tensor | 3,125.98 | 314.9 | 629.8 | link_latency | 4.08x | 0.04x | 118.33x | 4.08x |
| Kimi-K3 | 4 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,245.3 | 4,981.4 | link_latency | Kimi-K3/a100_sxm_80gb-x5316-tensor | 4,391,016 | 1.00x | tensor | 3,811.64 | 258.4 | 1,033.5 | link_latency | 4.82x | 0.09x | 114.72x | 4.82x |
| Kimi-K3 | 8 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,173.8 | 9,390.6 | link_latency | Kimi-K3/a100_sxm_80gb-x5316-tensor | 4,391,016 | 1.00x | tensor | 5,182.96 | 190.1 | 1,520.4 | link_latency | 6.18x | 0.16x | 108.14x | 6.18x |
| Kimi-K3 | 16 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,052.9 | 16,846.4 | link_latency | Kimi-K3/a100_sxm_80gb-x5316-tensor | 4,391,016 | 1.00x | tensor | 7,925.60 | 124.1 | 1,986.3 | link_latency | 8.48x | 0.29x | 96.99x | 8.48x |
| Kimi-K3 | 32 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 873.0 | 27,936.8 | link_latency | Kimi-K3/a100_sxm_80gb-x5316-expert | 4,391,016 | 1.00x | expert | 1,318.98 | 83.0 | 2,656.3 | weight_read | 10.52x | 0.48x | 80.42x | 10.52x |
| Kimi-K3 | 64 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 698.4 | 66,352.2 | kv_read | Kimi-K3/a100_sxm_80gb-x5316-expert | 4,391,016 | 1.00x | expert | 1,330.37 | 79.6 | 5,096.7 | weight_read | 8.77x | 1.15x | 64.34x | 8.77x |
| Kimi-K3 | 256 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 313.6 | 80,281.0 | kv_read | Kimi-K3/a100_sxm_80gb-x5316-hybrid | 4,391,016 | 1.00x | hybrid | 1,192.85 | 78.7 | 52,314.5 | weight_read | 3.99x | 1.39x | 28.89x | 4.45x |
| Kimi-K3 | 1024 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 86.4 | 88,503.0 | kv_read | Kimi-K3/a100_sxm_80gb-x5316-hybrid | 4,391,016 | 1.00x | hybrid | 1,233.92 | 69.5 | 71,129.7 | weight_read | 1.24x | 1.24x | 7.96x | 1.39x |
| Kimi-K3 | 4096 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 22.2 | 90,828.5 | kv_read | Kimi-K3/a100_sxm_80gb-x5316-hybrid | 4,391,016 | 1.00x | hybrid | 1,585.42 | 35.2 | 144,176.2 | compute | 0.63x | 0.63x | 2.04x | 0.70x |

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
| Kimi-K3 | 56 | 46,256 | 10.9 | 273.9 | 80.1 | tensor | 1,982.76 | 54.3% | link_latency |
| Kimi-K3 | 112 | 92,512 | 10.9 | 350.4 | 80.0 | tensor | 2,005.62 | 70.3% | link_latency |
| Kimi-K3 | 168 | 138,768 | 10.9 | 386.4 | 79.9 | tensor | 2,013.23 | 77.8% | link_latency |
| Kimi-K3 | 172 | 142,072 | 10.9 | 388.2 | 78.2 | tensor | 2,013.93 | 78.2% | link_latency |
| Kimi-K3 | 201 | 166,026 | 10.9 | 399.9 | 77.3 | tensor | 2,016.16 | 80.6% | link_latency |
| Kimi-K3 | 211 | 174,286 | 10.9 | 403.3 | 78.1 | tensor | 2,016.62 | 81.3% | link_latency |
| Kimi-K3 | 214 | 176,764 | 10.9 | 404.3 | 79.1 | tensor | 2,016.62 | 81.5% | link_latency |
| Kimi-K3 | 224 | 185,024 | 10.9 | 407.4 | 79.8 | tensor | 2,017.04 | 82.2% | link_latency |
| Kimi-K3 | 280 | 231,280 | 10.9 | 421.0 | 79.7 | tensor | 2,019.33 | 85.0% | link_latency |
| Kimi-K3 | 335 | 276,710 | 10.9 | 324.9 | 79.3 | tensor | 2,776.01 | 90.2% | link_latency |
| Kimi-K3 | 336 | 277,536 | 10.9 | 325.0 | 79.6 | tensor | 2,776.01 | 90.2% | link_latency |
| Kimi-K3 | 377 | 311,402 | 10.9 | 328.0 | 78.1 | tensor | 2,776.97 | 91.1% | link_latency |
| Kimi-K3 | 391 | 322,966 | 10.9 | 329.0 | 79.3 | tensor | 2,777.10 | 91.4% | link_latency |
| Kimi-K3 | 394 | 325,444 | 10.9 | 329.2 | 78.3 | tensor | 2,777.23 | 91.4% | link_latency |
| Kimi-K3 | 448 | 370,048 | 10.9 | 332.1 | 79.3 | tensor | 2,777.92 | 92.3% | link_latency |
| Kimi-K3 | 504 | 416,304 | 10.9 | 334.6 | 79.2 | tensor | 2,778.55 | 93.0% | link_latency |
| Kimi-K3 | 616 | 508,816 | 10.9 | 338.3 | 79.0 | tensor | 2,779.48 | 94.0% | link_latency |
| Kimi-K3 | 672 | 555,072 | 10.9 | 339.6 | 78.9 | tensor | 2,779.82 | 94.4% | link_latency |
| Kimi-K3 | 834 | 688,884 | 10.9 | 342.6 | 78.2 | tensor | 2,780.58 | 95.3% | link_latency |
| Kimi-K3 | 1175 | 970,550 | 10.9 | 346.3 | 78.7 | tensor | 2,781.45 | 96.3% | link_latency |
| Kimi-K3 | 1287 | 1,063,062 | 10.9 | 347.1 | 78.7 | tensor | 2,781.64 | 96.6% | link_latency |
| Kimi-K3 | 5316 | 4,391,016 | 10.9 | 353.6 | 78.7 | tensor | 2,783.15 | 98.4% | link_latency |

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
| Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x399 | Kimi-K3 | 399 | pipeline | rom_package_ucie | rom_board_serdes | 92 | 3.42 us | 29,235.7 tok/s | 292,356.8 tok/s | 69 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.94 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.48 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x396 | Kimi-K3 | 396 | tensor | rom_package_ucie | rom_board_serdes | 372 | 377.90 us | 264.6 tok/s | 2,646.2 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 99 on rom_board_serdes (traversals 19.8) = 372.68 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x399 | Kimi-K3 | 399 | hybrid | rom_package_ucie | rom_board_serdes | 278 | 15.15 us | 6,599.5 tok/s | 65,995.1 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 92 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 9.93 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x399 | Kimi-K3 | 399 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x23 | Kimi-K3 | 23 | pipeline | on_wafer | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x382 | Kimi-K3 | 382 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.97 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,823.63 us |
| Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x9 | Kimi-K3 | 9 | tensor | on_wafer | rom_wafer_serdes | 372 | 441.08 us | 226.7 tok/s | 2,267.2 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 186 x all_reduce span 9 on rom_wafer_serdes (traversals 4.4) = 83.03 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x399 | Kimi-K3 | 399 | hybrid | nvlink3 | infiniband_hdr | 235 | 1,080.90 us | 92.5 tok/s | 925.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 49 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 127.57 us |
| Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x21 | Kimi-K3 | 21 | hybrid | on_wafer | rom_wafer_serdes | 206 | 360.10 us | 277.7 tok/s | 2,777.0 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 20 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 2.05 us |
| Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | Kimi-K3 | 95 | pipeline | on_wafer | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | Kimi-K3 | 95 | tensor | on_wafer | rom_wafer_serdes | 372 | 727.65 us | 137.4 tok/s | 1,374.3 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 186 x all_reduce span 95 on rom_wafer_serdes (traversals 19.8) = 369.60 us |
| Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | Kimi-K3 | 95 | hybrid | on_wafer | rom_wafer_serdes | 278 | 367.47 us | 272.1 tok/s | 2,721.3 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 92 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 9.42 us |
| Kimi-K3/a100_sxm_80gb-x56-pipeline | Kimi-K3 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| Kimi-K3/a100_sxm_80gb-x56-tensor | Kimi-K3 | 56 | tensor | nvlink3 | infiniband_hdr | 372 | 1,982.76 us | 50.4 tok/s | 504.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 1,029.43 us |
| Kimi-K3/a100_sxm_80gb-x56-hybrid | Kimi-K3 | 56 | hybrid | nvlink3 | infiniband_hdr | 192 | 968.95 us | 103.2 tok/s | 1,032.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| Kimi-K3/a100_sxm_80gb-x56-expert | Kimi-K3 | 56 | expert | nvlink3 | infiniband_hdr | 372 | 1,341.39 us | 74.5 tok/s | 745.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 933.33 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 408.05 us |
| Kimi-K3/a100_sxm_80gb-x112-pipeline | Kimi-K3 | 112 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x112-tensor | Kimi-K3 | 112 | tensor | nvlink3 | infiniband_hdr | 372 | 2,005.62 us | 49.9 tok/s | 498.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 1,052.28 us |
| Kimi-K3/a100_sxm_80gb-x112-hybrid | Kimi-K3 | 112 | hybrid | nvlink3 | infiniband_hdr | 199 | 987.18 us | 101.3 tok/s | 1,013.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| Kimi-K3/a100_sxm_80gb-x112-expert | Kimi-K3 | 112 | expert | nvlink3 | infiniband_hdr | 372 | 1,324.48 us | 75.5 tok/s | 755.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.67 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 392.82 us |
| Kimi-K3/a100_sxm_80gb-x168-pipeline | Kimi-K3 | 168 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x168-tensor | Kimi-K3 | 168 | tensor | nvlink3 | infiniband_hdr | 372 | 2,013.23 us | 49.7 tok/s | 496.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 1,059.90 us |
| Kimi-K3/a100_sxm_80gb-x168-hybrid | Kimi-K3 | 168 | hybrid | nvlink3 | infiniband_hdr | 206 | 1,005.40 us | 99.5 tok/s | 994.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| Kimi-K3/a100_sxm_80gb-x168-expert | Kimi-K3 | 168 | expert | nvlink3 | infiniband_hdr | 372 | 1,318.85 us | 75.8 tok/s | 758.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.11 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 387.74 us |
| Kimi-K3/a100_sxm_80gb-x172-pipeline | Kimi-K3 | 172 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x172-tensor | Kimi-K3 | 172 | tensor | nvlink3 | infiniband_hdr | 372 | 2,013.93 us | 49.7 tok/s | 496.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 1,060.59 us |
| Kimi-K3/a100_sxm_80gb-x172-hybrid | Kimi-K3 | 172 | hybrid | nvlink3 | infiniband_hdr | 207 | 1,008.00 us | 99.2 tok/s | 992.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 54.67 us |
| Kimi-K3/a100_sxm_80gb-x172-expert | Kimi-K3 | 172 | expert | nvlink3 | infiniband_hdr | 372 | 1,318.61 us | 75.8 tok/s | 758.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.11 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 387.50 us |
| Kimi-K3/a100_sxm_80gb-x201-pipeline | Kimi-K3 | 201 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x201-tensor | Kimi-K3 | 201 | tensor | nvlink3 | infiniband_hdr | 372 | 2,016.16 us | 49.6 tok/s | 496.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 1,062.83 us |
| Kimi-K3/a100_sxm_80gb-x201-hybrid | Kimi-K3 | 201 | hybrid | nvlink3 | infiniband_hdr | 211 | 1,018.42 us | 98.2 tok/s | 981.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| Kimi-K3/a100_sxm_80gb-x201-expert | Kimi-K3 | 201 | expert | nvlink3 | infiniband_hdr | 372 | 1,317.00 us | 75.9 tok/s | 759.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.93 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 386.07 us |
| Kimi-K3/a100_sxm_80gb-x211-pipeline | Kimi-K3 | 211 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x211-tensor | Kimi-K3 | 211 | tensor | nvlink3 | infiniband_hdr | 372 | 2,016.62 us | 49.6 tok/s | 495.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 1,063.29 us |
| Kimi-K3/a100_sxm_80gb-x211-hybrid | Kimi-K3 | 211 | hybrid | nvlink3 | infiniband_hdr | 212 | 1,021.02 us | 97.9 tok/s | 979.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 67.69 us |
| Kimi-K3/a100_sxm_80gb-x211-expert | Kimi-K3 | 211 | expert | nvlink3 | infiniband_hdr | 372 | 1,316.57 us | 76.0 tok/s | 759.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.90 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 385.67 us |
| Kimi-K3/a100_sxm_80gb-x214-pipeline | Kimi-K3 | 214 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x214-tensor | Kimi-K3 | 214 | tensor | nvlink3 | infiniband_hdr | 372 | 2,016.62 us | 49.6 tok/s | 495.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 1,063.29 us |
| Kimi-K3/a100_sxm_80gb-x214-hybrid | Kimi-K3 | 214 | hybrid | nvlink3 | infiniband_hdr | 212 | 1,021.02 us | 97.9 tok/s | 979.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 67.69 us |
| Kimi-K3/a100_sxm_80gb-x214-expert | Kimi-K3 | 214 | expert | nvlink3 | infiniband_hdr | 372 | 1,316.45 us | 76.0 tok/s | 759.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.90 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 385.55 us |
| Kimi-K3/a100_sxm_80gb-x224-pipeline | Kimi-K3 | 224 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x224-tensor | Kimi-K3 | 224 | tensor | nvlink3 | infiniband_hdr | 372 | 2,017.04 us | 49.6 tok/s | 495.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 1,063.71 us |
| Kimi-K3/a100_sxm_80gb-x224-hybrid | Kimi-K3 | 224 | hybrid | nvlink3 | infiniband_hdr | 213 | 1,023.62 us | 97.7 tok/s | 976.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| Kimi-K3/a100_sxm_80gb-x224-expert | Kimi-K3 | 224 | expert | nvlink3 | infiniband_hdr | 372 | 1,316.03 us | 76.0 tok/s | 759.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.83 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 385.20 us |
| Kimi-K3/a100_sxm_80gb-x280-pipeline | Kimi-K3 | 280 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x280-tensor | Kimi-K3 | 280 | tensor | nvlink3 | infiniband_hdr | 372 | 2,019.33 us | 49.5 tok/s | 495.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 35 on infiniband_hdr (traversals 2.0) = 1,066.00 us |
| Kimi-K3/a100_sxm_80gb-x280-hybrid | Kimi-K3 | 280 | hybrid | nvlink3 | infiniband_hdr | 220 | 1,041.85 us | 96.0 tok/s | 959.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 34 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 88.52 us |
| Kimi-K3/a100_sxm_80gb-x280-expert | Kimi-K3 | 280 | expert | nvlink3 | infiniband_hdr | 372 | 1,314.34 us | 76.1 tok/s | 760.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.67 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 383.67 us |
| Kimi-K3/a100_sxm_80gb-x335-pipeline | Kimi-K3 | 335 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x335-tensor | Kimi-K3 | 335 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.01 us | 36.0 tok/s | 360.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,822.68 us |
| Kimi-K3/a100_sxm_80gb-x335-hybrid | Kimi-K3 | 335 | hybrid | nvlink3 | infiniband_hdr | 227 | 1,060.07 us | 94.3 tok/s | 943.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| Kimi-K3/a100_sxm_80gb-x335-expert | Kimi-K3 | 335 | expert | nvlink3 | infiniband_hdr | 372 | 1,313.24 us | 76.1 tok/s | 761.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.57 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.67 us |
| Kimi-K3/a100_sxm_80gb-x336-pipeline | Kimi-K3 | 336 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x336-tensor | Kimi-K3 | 336 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.01 us | 36.0 tok/s | 360.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,822.68 us |
| Kimi-K3/a100_sxm_80gb-x336-hybrid | Kimi-K3 | 336 | hybrid | nvlink3 | infiniband_hdr | 227 | 1,060.07 us | 94.3 tok/s | 943.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| Kimi-K3/a100_sxm_80gb-x336-expert | Kimi-K3 | 336 | expert | nvlink3 | infiniband_hdr | 372 | 1,313.21 us | 76.1 tok/s | 761.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.56 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.66 us |
| Kimi-K3/a100_sxm_80gb-x377-pipeline | Kimi-K3 | 377 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x377-tensor | Kimi-K3 | 377 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.97 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,823.63 us |
| Kimi-K3/a100_sxm_80gb-x377-hybrid | Kimi-K3 | 377 | hybrid | nvlink3 | infiniband_hdr | 233 | 1,075.69 us | 93.0 tok/s | 929.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| Kimi-K3/a100_sxm_80gb-x377-expert | Kimi-K3 | 377 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.60 us | 76.2 tok/s | 761.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.50 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.11 us |
| Kimi-K3/a100_sxm_80gb-x391-pipeline | Kimi-K3 | 391 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x391-tensor | Kimi-K3 | 391 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.10 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,823.77 us |
| Kimi-K3/a100_sxm_80gb-x391-hybrid | Kimi-K3 | 391 | hybrid | nvlink3 | infiniband_hdr | 234 | 1,078.30 us | 92.7 tok/s | 927.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| Kimi-K3/a100_sxm_80gb-x391-expert | Kimi-K3 | 391 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.43 us | 76.2 tok/s | 761.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.49 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.94 us |
| Kimi-K3/a100_sxm_80gb-x394-pipeline | Kimi-K3 | 394 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x394-tensor | Kimi-K3 | 394 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.23 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 50 on infiniband_hdr (traversals 4.0) = 1,823.90 us |
| Kimi-K3/a100_sxm_80gb-x394-hybrid | Kimi-K3 | 394 | hybrid | nvlink3 | infiniband_hdr | 235 | 1,080.90 us | 92.5 tok/s | 925.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 49 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 127.57 us |
| Kimi-K3/a100_sxm_80gb-x394-expert | Kimi-K3 | 394 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.39 us | 76.2 tok/s | 762.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.48 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.91 us |
| Kimi-K3/a100_sxm_80gb-x448-pipeline | Kimi-K3 | 448 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x448-tensor | Kimi-K3 | 448 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.92 us | 36.0 tok/s | 360.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,824.59 us |
| Kimi-K3/a100_sxm_80gb-x448-hybrid | Kimi-K3 | 448 | hybrid | nvlink3 | infiniband_hdr | 241 | 1,096.52 us | 91.2 tok/s | 912.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| Kimi-K3/a100_sxm_80gb-x448-expert | Kimi-K3 | 448 | expert | nvlink3 | infiniband_hdr | 372 | 1,311.81 us | 76.2 tok/s | 762.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.42 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.39 us |
| Kimi-K3/a100_sxm_80gb-x504-pipeline | Kimi-K3 | 504 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x504-tensor | Kimi-K3 | 504 | tensor | nvlink3 | infiniband_hdr | 372 | 2,778.55 us | 36.0 tok/s | 359.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 63 on infiniband_hdr (traversals 4.0) = 1,825.22 us |
| Kimi-K3/a100_sxm_80gb-x504-hybrid | Kimi-K3 | 504 | hybrid | nvlink3 | infiniband_hdr | 248 | 1,114.75 us | 89.7 tok/s | 897.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 62 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 161.41 us |
| Kimi-K3/a100_sxm_80gb-x504-expert | Kimi-K3 | 504 | expert | nvlink3 | infiniband_hdr | 372 | 1,311.34 us | 76.3 tok/s | 762.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.37 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 380.97 us |
| Kimi-K3/a100_sxm_80gb-x616-pipeline | Kimi-K3 | 616 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x616-tensor | Kimi-K3 | 616 | tensor | nvlink3 | infiniband_hdr | 372 | 2,779.48 us | 36.0 tok/s | 359.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 77 on infiniband_hdr (traversals 4.0) = 1,826.14 us |
| Kimi-K3/a100_sxm_80gb-x616-hybrid | Kimi-K3 | 616 | hybrid | nvlink3 | infiniband_hdr | 262 | 1,151.19 us | 86.9 tok/s | 868.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 76 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 197.86 us |
| Kimi-K3/a100_sxm_80gb-x616-expert | Kimi-K3 | 616 | expert | nvlink3 | infiniband_hdr | 372 | 1,310.65 us | 76.3 tok/s | 763.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.30 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 380.35 us |
| Kimi-K3/a100_sxm_80gb-x672-pipeline | Kimi-K3 | 672 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x672-tensor | Kimi-K3 | 672 | tensor | nvlink3 | infiniband_hdr | 372 | 2,779.82 us | 36.0 tok/s | 359.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,826.49 us |
| Kimi-K3/a100_sxm_80gb-x672-hybrid | Kimi-K3 | 672 | hybrid | nvlink3 | infiniband_hdr | 269 | 1,169.42 us | 85.5 tok/s | 855.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 83 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 216.09 us |
| Kimi-K3/a100_sxm_80gb-x672-expert | Kimi-K3 | 672 | expert | nvlink3 | infiniband_hdr | 372 | 1,310.40 us | 76.3 tok/s | 763.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.28 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 380.12 us |
| Kimi-K3/a100_sxm_80gb-x834-pipeline | Kimi-K3 | 834 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x834-tensor | Kimi-K3 | 834 | tensor | nvlink3 | infiniband_hdr | 372 | 2,780.58 us | 36.0 tok/s | 359.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 105 on infiniband_hdr (traversals 4.0) = 1,827.25 us |
| Kimi-K3/a100_sxm_80gb-x834-hybrid | Kimi-K3 | 834 | hybrid | nvlink3 | infiniband_hdr | 278 | 1,192.85 us | 83.8 tok/s | 838.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 92 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 239.52 us |
| Kimi-K3/a100_sxm_80gb-x834-expert | Kimi-K3 | 834 | expert | nvlink3 | infiniband_hdr | 372 | 1,309.85 us | 76.3 tok/s | 763.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.22 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 379.63 us |
| Kimi-K3/a100_sxm_80gb-x1175-pipeline | Kimi-K3 | 1175 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x1175-tensor | Kimi-K3 | 1175 | tensor | nvlink3 | infiniband_hdr | 372 | 2,781.45 us | 36.0 tok/s | 359.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 147 on infiniband_hdr (traversals 4.0) = 1,828.12 us |
| Kimi-K3/a100_sxm_80gb-x1175-hybrid | Kimi-K3 | 1175 | hybrid | nvlink3 | infiniband_hdr | 278 | 1,192.85 us | 83.8 tok/s | 838.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 92 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 239.52 us |
| Kimi-K3/a100_sxm_80gb-x1175-expert | Kimi-K3 | 1175 | expert | nvlink3 | infiniband_hdr | 372 | 1,309.19 us | 76.4 tok/s | 763.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.16 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 379.03 us |
| Kimi-K3/a100_sxm_80gb-x1287-pipeline | Kimi-K3 | 1287 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x1287-tensor | Kimi-K3 | 1287 | tensor | nvlink3 | infiniband_hdr | 372 | 2,781.64 us | 35.9 tok/s | 359.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 161 on infiniband_hdr (traversals 4.0) = 1,828.31 us |
| Kimi-K3/a100_sxm_80gb-x1287-hybrid | Kimi-K3 | 1287 | hybrid | nvlink3 | infiniband_hdr | 278 | 1,192.85 us | 83.8 tok/s | 838.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 92 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 239.52 us |
| Kimi-K3/a100_sxm_80gb-x1287-expert | Kimi-K3 | 1287 | expert | nvlink3 | infiniband_hdr | 372 | 1,309.05 us | 76.4 tok/s | 763.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.15 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 378.91 us |
| Kimi-K3/a100_sxm_80gb-x5316-pipeline | Kimi-K3 | 5316 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x5316-tensor | Kimi-K3 | 5316 | tensor | nvlink3 | infiniband_hdr | 372 | 2,783.15 us | 35.9 tok/s | 359.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 665 on infiniband_hdr (traversals 4.0) = 1,829.82 us |
| Kimi-K3/a100_sxm_80gb-x5316-hybrid | Kimi-K3 | 5316 | hybrid | nvlink3 | infiniband_hdr | 278 | 1,192.85 us | 83.8 tok/s | 838.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 92 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 239.52 us |
| Kimi-K3/a100_sxm_80gb-x5316-expert | Kimi-K3 | 5316 | expert | nvlink3 | infiniband_hdr | 372 | 1,307.94 us | 76.5 tok/s | 764.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.04 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 377.90 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Kimi-K3 | 1 | wafer | array | Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x9 | 416,025 | 1,860.1 | 0.004 | 1,697.8 (322,740) | 1,860.1 (416,025) | 1.10x | link_latency |
| Kimi-K3 | 2 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,284.5 | 0.000 | — (—) | 1,284.5 (4,391,375) | — | link_latency |
| Kimi-K3 | 4 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,245.3 | 0.000 | — (—) | 1,245.3 (4,391,375) | — | link_latency |
| Kimi-K3 | 8 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,173.8 | 0.000 | — (—) | 1,173.8 (4,391,375) | — | link_latency |
| Kimi-K3 | 16 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 1,052.9 | 0.000 | — (—) | 1,052.9 (4,391,375) | — | link_latency |
| Kimi-K3 | 32 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95 | 4,391,375 | 873.0 | 0.000 | — (—) | 873.0 (4,391,375) | — | link_latency |
| Kimi-K3 | 64 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 698.4 | 0.000 | — (—) | 698.4 (4,391,375) | — | kv_read |
| Kimi-K3 | 256 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 313.6 | 0.000 | — (—) | 313.6 (4,391,375) | — | kv_read |
| Kimi-K3 | 1024 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 86.4 | 0.000 | — (—) | 86.4 (4,391,375) | — | kv_read |
| Kimi-K3 | 4096 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 22.2 | 0.000 | — (—) | 22.2 (4,391,375) | — | kv_read |

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

## Sizing one expert region

The per-region machine's cost is not arithmetic; it is a
pre-compute block and an activation distribution network per
region. The block is small against the array it serves. The
distribution network is the real cost and this model does not
price it.

| Model | Experts | Routed bytes/expert | One region | Pre-compute/region | All regions | All pre-compute | Whole checkpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kimi-K3 | 896 | 1,614.3 MB | 354.1 mm2 | 63.73 mm2 (18.0%) | 317,241 mm2 | 57,103 mm2 | 342,333 mm2 = 420.0 reticles |

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
| Kimi-K3 | 1 | sram | 70,039.0 | 23,554.4 | 23,554.4 | 2.97x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 2 | sram | 70,039.0 | 23,554.4 | 23,554.4 | 2.97x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4 | sram | 70,039.0 | 23,554.4 | 23,554.4 | 2.97x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 8 | sram | 70,039.0 | 23,554.4 | 23,554.4 | 2.97x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 16 | sram | 70,039.0 | 23,554.4 | 23,554.4 | 2.97x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 32 | sram | 70,039.0 | 23,554.4 | 27,936.8 | 2.97x | 1.19x | kv_read | weight_read | link_latency |
| Kimi-K3 | 64 | sram | 70,039.0 | 23,554.4 | 41,644.4 | 2.97x | 1.77x | kv_read | weight_read | link_latency |
| Kimi-K3 | 256 | sram | 80,281.0 | 25,100.3 | 65,893.1 | 3.20x | 2.63x | kv_read | weight_read | kv_read |
| Kimi-K3 | 1024 | sram | 88,503.0 | 25,851.2 | 88,503.0 | 3.42x | 3.42x | kv_read | weight_read | kv_read |
| Kimi-K3 | 4096 | sram | 90,828.5 | 26,046.0 | 90,828.5 | 3.49x | 3.49x | kv_read | weight_read | kv_read |
| Kimi-K3 | 1 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 2 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 8 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 16 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 32 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 64 | rom | 70,039.0 | 70,039.0 | 70,039.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 256 | rom | 80,281.0 | 80,281.0 | 80,281.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 1024 | rom | 88,503.0 | 88,503.0 | 88,503.0 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4096 | rom | 90,828.5 | 90,828.5 | 90,828.5 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Kimi-K3 | 1 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 1 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 1 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 1 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 1 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 1 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 2 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 2 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 2 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 2 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 4 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 4 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 4 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 4 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 8 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 8 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 8 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 8 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 16 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 16 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 16 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 16 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 32 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 32 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 32 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95-perregion | 4,391,375 | 1.00 | 4.10 | 27,936.8 | 0.006 | link_latency | 0.40x |
| Kimi-K3 | 32 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95 | 4,391,375 | 1.00 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-romfill | 4,391,375 | 8.93 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 64 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 1.00 | 23,554.4 | 0.005 | weight_read | 0.34x |
| Kimi-K3 | 64 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perstream-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 64 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95-perregion | 4,391,375 | 1.00 | 5.73 | 41,644.4 | 0.009 | link_latency | 0.59x |
| Kimi-K3 | 64 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x95-perregion-romfill | 4,391,375 | 32.36 | 1.00 | 70,039.0 | 0.016 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 1.00 | 1.00 | 80,281.0 | 0.018 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-romfill | 4,391,375 | 8.93 | 1.00 | 80,281.0 | 0.018 | kv_read | 1.00x |
| Kimi-K3 | 256 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 2.69 | 25,100.3 | 0.006 | weight_read | 0.31x |
| Kimi-K3 | 256 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream-romfill | 4,391,375 | 32.36 | 2.69 | 80,281.0 | 0.018 | kv_read | 1.00x |
| Kimi-K3 | 256 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x95-perregion | 4,391,375 | 1.00 | 12.69 | 65,893.1 | 0.015 | kv_read | 0.82x |
| Kimi-K3 | 256 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion-romfill | 4,391,375 | 32.36 | 1.48 | 80,281.0 | 0.018 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 1.00 | 1.00 | 88,503.0 | 0.020 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-romfill | 4,391,375 | 8.93 | 1.00 | 88,503.0 | 0.020 | kv_read | 1.00x |
| Kimi-K3 | 1024 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 10.78 | 25,851.2 | 0.006 | weight_read | 0.29x |
| Kimi-K3 | 1024 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream-romfill | 4,391,375 | 32.36 | 10.78 | 88,503.0 | 0.020 | kv_read | 1.00x |
| Kimi-K3 | 1024 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 2.53 | 88,503.0 | 0.020 | kv_read | 1.00x |
| Kimi-K3 | 1024 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion-romfill | 4,391,375 | 32.36 | 2.53 | 88,503.0 | 0.020 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95 | 4,391,375 | 1.00 | 1.00 | 90,828.5 | 0.021 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-romfill | 4,391,375 | 8.93 | 1.00 | 90,828.5 | 0.021 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream | 4,391,375 | 1.00 | 43.12 | 26,046.0 | 0.006 | weight_read | 0.29x |
| Kimi-K3 | 4096 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perstream-romfill | 4,391,375 | 32.36 | 43.12 | 90,828.5 | 0.021 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion | 4,391,375 | 1.00 | 4.70 | 90,828.5 | 0.021 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x95-perregion-romfill | 4,391,375 | 32.36 | 4.70 | 90,828.5 | 0.021 | kv_read | 1.00x |

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
| Kimi-K3 | 1 | 174 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 2 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4 | 227 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 8 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 16 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 32 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 64 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 256 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 1024 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4096 | 5,389 | 1.00 | 1.000 | 1.000 | 1.00x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| Kimi-K3 | 1 | 56 | 14.03 | 8.04 | 1.74x |
| Kimi-K3 | 2 | 56 | 24.38 | 11.36 | 2.14x |
| Kimi-K3 | 4 | 56 | 37.78 | 15.32 | 2.47x |
| Kimi-K3 | 8 | 56 | 49.59 | 19.81 | 2.50x |
| Kimi-K3 | 16 | 56 | 55.02 | 24.46 | 2.25x |
| Kimi-K3 | 32 | 56 | 55.95 | 28.73 | 1.95x |
| Kimi-K3 | 64 | 56 | 56.00 | 32.07 | 1.75x |
| Kimi-K3 | 1 | 112 | 14.97 | 9.58 | 1.56x |
| Kimi-K3 | 2 | 112 | 27.73 | 13.98 | 1.98x |
| Kimi-K3 | 4 | 112 | 47.95 | 19.84 | 2.42x |
| Kimi-K3 | 8 | 112 | 73.92 | 27.12 | 2.73x |
| Kimi-K3 | 16 | 112 | 97.03 | 35.27 | 2.75x |
| Kimi-K3 | 32 | 112 | 108.69 | 43.36 | 2.51x |
| Kimi-K3 | 64 | 112 | 111.54 | 50.14 | 2.22x |
| Kimi-K3 | 256 | 112 | 111.96 | 55.81 | 2.01x |
| Kimi-K3 | 1 | 168 | 15.31 | 10.59 | 1.45x |
| Kimi-K3 | 2 | 168 | 28.98 | 15.31 | 1.89x |
| Kimi-K3 | 4 | 168 | 52.19 | 22.71 | 2.30x |
| Kimi-K3 | 8 | 168 | 86.07 | 31.82 | 2.70x |
| Kimi-K3 | 16 | 168 | 124.00 | 42.49 | 2.92x |
| Kimi-K3 | 32 | 168 | 151.88 | 53.65 | 2.83x |
| Kimi-K3 | 64 | 168 | 163.68 | 63.35 | 2.58x |
| Kimi-K3 | 256 | 168 | 167.16 | 71.73 | 2.33x |
| Kimi-K3 | 1 | 172 | 15.32 | 10.65 | 1.44x |
| Kimi-K3 | 2 | 172 | 29.04 | 15.38 | 1.89x |
| Kimi-K3 | 4 | 172 | 52.40 | 22.89 | 2.29x |
| Kimi-K3 | 8 | 172 | 86.70 | 32.10 | 2.70x |
| Kimi-K3 | 16 | 172 | 125.52 | 42.93 | 2.92x |
| Kimi-K3 | 32 | 172 | 154.57 | 54.28 | 2.85x |
| Kimi-K3 | 64 | 172 | 167.18 | 64.17 | 2.61x |
| Kimi-K3 | 256 | 172 | 171.02 | 72.74 | 2.35x |
| Kimi-K3 | 1 | 201 | 15.42 | 11.05 | 1.40x |
| Kimi-K3 | 2 | 201 | 29.41 | 15.89 | 1.85x |
| Kimi-K3 | 4 | 201 | 53.69 | 24.04 | 2.23x |
| Kimi-K3 | 8 | 201 | 90.68 | 33.94 | 2.67x |
| Kimi-K3 | 16 | 201 | 135.37 | 45.89 | 2.95x |
| Kimi-K3 | 32 | 201 | 172.64 | 58.56 | 2.95x |
| Kimi-K3 | 64 | 201 | 191.56 | 69.79 | 2.74x |
| Kimi-K3 | 256 | 201 | 198.59 | 79.63 | 2.49x |
| Kimi-K3 | 1 | 211 | 15.44 | 11.17 | 1.38x |
| Kimi-K3 | 2 | 211 | 29.51 | 16.05 | 1.84x |
| Kimi-K3 | 4 | 211 | 54.06 | 24.40 | 2.22x |
| Kimi-K3 | 8 | 211 | 91.84 | 34.50 | 2.66x |
| Kimi-K3 | 16 | 211 | 138.34 | 46.82 | 2.95x |
| Kimi-K3 | 32 | 211 | 178.32 | 59.93 | 2.98x |
| Kimi-K3 | 64 | 211 | 199.54 | 71.60 | 2.79x |
| Kimi-K3 | 256 | 211 | 207.88 | 81.86 | 2.54x |
| Kimi-K3 | 1 | 214 | 15.45 | 11.21 | 1.38x |
| Kimi-K3 | 2 | 214 | 29.54 | 16.10 | 1.83x |
| Kimi-K3 | 4 | 214 | 54.16 | 24.50 | 2.21x |
| Kimi-K3 | 8 | 214 | 92.17 | 34.66 | 2.66x |
| Kimi-K3 | 16 | 214 | 139.20 | 47.09 | 2.96x |
| Kimi-K3 | 32 | 214 | 179.98 | 60.33 | 2.98x |
| Kimi-K3 | 64 | 214 | 201.89 | 72.13 | 2.80x |
| Kimi-K3 | 256 | 214 | 210.64 | 82.51 | 2.55x |
| Kimi-K3 | 1 | 224 | 15.48 | 11.32 | 1.37x |
| Kimi-K3 | 2 | 224 | 29.63 | 16.26 | 1.82x |
| Kimi-K3 | 4 | 224 | 54.50 | 24.84 | 2.19x |
| Kimi-K3 | 8 | 224 | 93.22 | 35.18 | 2.65x |
| Kimi-K3 | 16 | 224 | 141.93 | 47.96 | 2.96x |
| Kimi-K3 | 32 | 224 | 185.33 | 61.63 | 3.01x |
| Kimi-K3 | 64 | 224 | 209.59 | 73.86 | 2.84x |
| Kimi-K3 | 256 | 224 | 219.77 | 84.66 | 2.60x |
| Kimi-K3 | 1 | 280 | 15.58 | 11.88 | 1.31x |
| Kimi-K3 | 2 | 280 | 30.03 | 17.05 | 1.76x |
| Kimi-K3 | 4 | 280 | 55.95 | 26.38 | 2.12x |
| Kimi-K3 | 8 | 280 | 97.92 | 37.69 | 2.60x |
| Kimi-K3 | 16 | 280 | 154.55 | 52.25 | 2.96x |
| Kimi-K3 | 32 | 280 | 211.28 | 68.18 | 3.10x |
| Kimi-K3 | 64 | 280 | 248.79 | 82.61 | 3.01x |
| Kimi-K3 | 256 | 280 | 268.28 | 95.59 | 2.81x |
| Kimi-K3 | 1024 | 280 | 268.65 | 95.95 | 2.80x |
| Kimi-K3 | 1 | 335 | 15.65 | 12.32 | 1.27x |
| Kimi-K3 | 2 | 335 | 30.30 | 17.75 | 1.71x |
| Kimi-K3 | 4 | 335 | 56.93 | 27.49 | 2.07x |
| Kimi-K3 | 8 | 335 | 101.18 | 39.78 | 2.54x |
| Kimi-K3 | 16 | 335 | 163.73 | 55.86 | 2.93x |
| Kimi-K3 | 32 | 335 | 231.42 | 73.59 | 3.14x |
| Kimi-K3 | 64 | 335 | 281.43 | 90.01 | 3.13x |
| Kimi-K3 | 256 | 335 | 311.38 | 104.93 | 2.97x |
| Kimi-K3 | 1024 | 335 | 312.00 | 105.34 | 2.96x |
| Kimi-K3 | 1 | 336 | 15.65 | 12.32 | 1.27x |
| Kimi-K3 | 2 | 336 | 30.31 | 17.76 | 1.71x |
| Kimi-K3 | 4 | 336 | 56.95 | 27.51 | 2.07x |
| Kimi-K3 | 8 | 336 | 101.23 | 39.82 | 2.54x |
| Kimi-K3 | 16 | 336 | 163.87 | 55.92 | 2.93x |
| Kimi-K3 | 32 | 336 | 231.74 | 73.68 | 3.15x |
| Kimi-K3 | 64 | 336 | 281.98 | 90.14 | 3.13x |
| Kimi-K3 | 256 | 336 | 312.12 | 105.09 | 2.97x |
| Kimi-K3 | 1024 | 336 | 312.75 | 105.50 | 2.96x |
| Kimi-K3 | 1 | 377 | 15.69 | 12.59 | 1.25x |
| Kimi-K3 | 2 | 377 | 30.46 | 18.24 | 1.67x |
| Kimi-K3 | 4 | 377 | 57.50 | 28.15 | 2.04x |
| Kimi-K3 | 8 | 377 | 103.10 | 41.25 | 2.50x |
| Kimi-K3 | 16 | 377 | 169.28 | 58.36 | 2.90x |
| Kimi-K3 | 32 | 377 | 244.12 | 77.29 | 3.16x |
| Kimi-K3 | 64 | 377 | 303.04 | 95.02 | 3.19x |
| Kimi-K3 | 256 | 377 | 341.27 | 111.33 | 3.07x |
| Kimi-K3 | 1024 | 377 | 342.10 | 111.79 | 3.06x |
| Kimi-K3 | 1 | 391 | 15.70 | 12.67 | 1.24x |
| Kimi-K3 | 2 | 391 | 30.50 | 18.39 | 1.66x |
| Kimi-K3 | 4 | 391 | 57.66 | 28.35 | 2.03x |
| Kimi-K3 | 8 | 391 | 103.65 | 41.72 | 2.48x |
| Kimi-K3 | 16 | 391 | 170.91 | 59.14 | 2.89x |
| Kimi-K3 | 32 | 391 | 247.94 | 78.46 | 3.16x |
| Kimi-K3 | 64 | 391 | 309.68 | 96.60 | 3.21x |
| Kimi-K3 | 256 | 391 | 350.67 | 113.34 | 3.09x |
| Kimi-K3 | 1024 | 391 | 351.58 | 113.82 | 3.09x |
| Kimi-K3 | 1 | 394 | 15.70 | 12.69 | 1.24x |
| Kimi-K3 | 2 | 394 | 30.51 | 18.42 | 1.66x |
| Kimi-K3 | 4 | 394 | 57.70 | 28.39 | 2.03x |
| Kimi-K3 | 8 | 394 | 103.77 | 41.81 | 2.48x |
| Kimi-K3 | 16 | 394 | 171.25 | 59.31 | 2.89x |
| Kimi-K3 | 32 | 394 | 248.73 | 78.71 | 3.16x |
| Kimi-K3 | 64 | 394 | 311.07 | 96.93 | 3.21x |
| Kimi-K3 | 256 | 394 | 352.66 | 113.77 | 3.10x |
| Kimi-K3 | 1024 | 394 | 353.58 | 114.24 | 3.10x |
| Kimi-K3 | 1 | 448 | 15.73 | 12.97 | 1.21x |
| Kimi-K3 | 2 | 448 | 30.65 | 18.99 | 1.61x |
| Kimi-K3 | 4 | 448 | 58.23 | 29.05 | 2.00x |
| Kimi-K3 | 8 | 448 | 105.59 | 43.53 | 2.43x |
| Kimi-K3 | 16 | 448 | 176.68 | 62.05 | 2.85x |
| Kimi-K3 | 32 | 448 | 261.69 | 82.87 | 3.16x |
| Kimi-K3 | 64 | 448 | 334.19 | 102.64 | 3.26x |
| Kimi-K3 | 256 | 448 | 386.29 | 121.03 | 3.19x |
| Kimi-K3 | 1024 | 448 | 387.51 | 121.55 | 3.19x |
| Kimi-K3 | 1 | 504 | 15.76 | 13.22 | 1.19x |
| Kimi-K3 | 2 | 504 | 30.77 | 19.53 | 1.58x |
| Kimi-K3 | 4 | 504 | 58.66 | 29.62 | 1.98x |
| Kimi-K3 | 8 | 504 | 107.10 | 45.16 | 2.37x |
| Kimi-K3 | 16 | 504 | 181.25 | 64.49 | 2.81x |
| Kimi-K3 | 32 | 504 | 272.91 | 86.62 | 3.15x |
| Kimi-K3 | 64 | 504 | 354.89 | 107.93 | 3.29x |
| Kimi-K3 | 256 | 504 | 417.45 | 127.90 | 3.26x |
| Kimi-K3 | 1024 | 504 | 418.97 | 128.47 | 3.26x |
| Kimi-K3 | 1 | 616 | 15.81 | 13.60 | 1.16x |
| Kimi-K3 | 2 | 616 | 30.94 | 20.49 | 1.51x |
| Kimi-K3 | 4 | 616 | 59.30 | 30.58 | 1.94x |
| Kimi-K3 | 8 | 616 | 109.35 | 47.97 | 2.28x |
| Kimi-K3 | 16 | 616 | 188.20 | 68.35 | 2.75x |
| Kimi-K3 | 32 | 616 | 290.50 | 92.94 | 3.13x |
| Kimi-K3 | 64 | 616 | 388.54 | 117.05 | 3.32x |
| Kimi-K3 | 256 | 616 | 470.24 | 139.89 | 3.36x |
| Kimi-K3 | 1024 | 616 | 472.33 | 140.54 | 3.36x |
| Kimi-K3 | 1 | 672 | 15.82 | 13.76 | 1.15x |
| Kimi-K3 | 2 | 672 | 31.00 | 20.92 | 1.48x |
| Kimi-K3 | 4 | 672 | 59.55 | 31.00 | 1.92x |
| Kimi-K3 | 8 | 672 | 110.20 | 49.15 | 2.24x |
| Kimi-K3 | 16 | 672 | 190.91 | 69.95 | 2.73x |
| Kimi-K3 | 32 | 672 | 297.51 | 95.79 | 3.11x |
| Kimi-K3 | 64 | 672 | 402.36 | 121.20 | 3.32x |
| Kimi-K3 | 256 | 672 | 492.68 | 145.31 | 3.39x |
| Kimi-K3 | 1024 | 672 | 495.04 | 145.99 | 3.39x |
| Kimi-K3 | 1 | 834 | 15.86 | 14.12 | 1.12x |
| Kimi-K3 | 2 | 834 | 31.14 | 22.00 | 1.42x |
| Kimi-K3 | 4 | 834 | 60.07 | 32.13 | 1.87x |
| Kimi-K3 | 8 | 834 | 112.07 | 51.86 | 2.16x |
| Kimi-K3 | 16 | 834 | 196.86 | 74.06 | 2.66x |
| Kimi-K3 | 32 | 834 | 313.29 | 103.41 | 3.03x |
| Kimi-K3 | 64 | 834 | 434.37 | 131.82 | 3.30x |
| Kimi-K3 | 256 | 834 | 546.30 | 159.00 | 3.44x |
| Kimi-K3 | 1024 | 834 | 549.35 | 159.81 | 3.44x |
| Kimi-K3 | 1 | 1175 | 15.90 | 14.59 | 1.09x |
| Kimi-K3 | 2 | 1175 | 31.30 | 23.70 | 1.32x |
| Kimi-K3 | 4 | 1175 | 60.71 | 34.25 | 1.77x |
| Kimi-K3 | 8 | 1175 | 114.37 | 55.31 | 2.07x |
| Kimi-K3 | 16 | 1175 | 204.36 | 81.76 | 2.50x |
| Kimi-K3 | 32 | 1175 | 333.88 | 115.54 | 2.89x |
| Kimi-K3 | 64 | 1175 | 477.90 | 147.91 | 3.23x |
| Kimi-K3 | 256 | 1175 | 622.91 | 181.61 | 3.43x |
| Kimi-K3 | 1024 | 1175 | 627.07 | 182.53 | 3.44x |
| Kimi-K3 | 4096 | 1175 | 627.07 | 182.53 | 3.44x |
| Kimi-K3 | 1 | 1287 | 15.91 | 14.70 | 1.08x |
| Kimi-K3 | 2 | 1287 | 31.34 | 24.14 | 1.30x |
| Kimi-K3 | 4 | 1287 | 60.84 | 34.90 | 1.74x |
| Kimi-K3 | 8 | 1287 | 114.87 | 56.05 | 2.05x |
| Kimi-K3 | 16 | 1287 | 206.01 | 84.05 | 2.45x |
| Kimi-K3 | 32 | 1287 | 338.50 | 118.38 | 2.86x |
| Kimi-K3 | 64 | 1287 | 487.94 | 152.43 | 3.20x |
| Kimi-K3 | 256 | 1287 | 641.18 | 188.02 | 3.41x |
| Kimi-K3 | 1024 | 1287 | 645.63 | 189.01 | 3.42x |
| Kimi-K3 | 4096 | 1287 | 645.63 | 189.01 | 3.42x |
| Kimi-K3 | 1 | 5316 | 15.98 | 15.65 | 1.02x |
| Kimi-K3 | 2 | 5316 | 31.62 | 29.16 | 1.08x |
| Kimi-K3 | 4 | 5316 | 61.95 | 47.88 | 1.29x |
| Kimi-K3 | 8 | 5316 | 118.94 | 68.92 | 1.73x |
| Kimi-K3 | 16 | 5316 | 219.76 | 109.35 | 2.01x |
| Kimi-K3 | 32 | 5316 | 378.50 | 171.37 | 2.21x |
| Kimi-K3 | 64 | 5316 | 579.20 | 223.24 | 2.59x |
| Kimi-K3 | 256 | 5316 | 817.11 | 284.58 | 2.87x |
| Kimi-K3 | 1024 | 5316 | 824.63 | 286.70 | 2.88x |
| Kimi-K3 | 4096 | 5316 | 824.63 | 286.70 | 2.88x |

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
| gpu | Kimi-K3 | 1 | 27.74 | 1.2% |
| rom | Kimi-K3 | 1 | 27.74 | 8.6% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| Kimi-K3 | sram | interleaved | 128 B | 1.00x |
| Kimi-K3 | hbm | interleaved | 32 B | 1.00x |

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
| Kimi-K3 | 1 | 174 | 91.65% | 1,525.44 | 9.57 |
| Kimi-K3 | 2 | 4 | 14.48% | 314.45 | 9.57 |
| Kimi-K3 | 4 | 4 | 14.48% | 314.45 | 9.57 |

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
| Kimi-K3 | 1 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 2 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 4 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 8 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 16 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 32 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 64 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 256 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 1024 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |
| Kimi-K3 | 4096 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 17.0 | 70,039.0 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 73 |
| gpu | infeasible | 109 |
| gpu | link_latency | 189 |
| gpu | weight_read | 509 |
| rom | compute | 56 |
| rom | infeasible | 1419 |
| rom | kv_read | 97 |
| rom | link_latency | 115 |
| rom | weight_read | 83 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 109 |
| rom | CAPACITY | 1419 |

## Mechanical consistency audit

**FAIL** over 37,649 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x382', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x396', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x382', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x396', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x382', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x396', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x382', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x396', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x9', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x21', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x23', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x382', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x396', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x9', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x21', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x23', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x382', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x396', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x9', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x21', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x23', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x340-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x382-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x396-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x399-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x340-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x382-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x396-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x399-romfill', 'Kimi-K3', 1)

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
