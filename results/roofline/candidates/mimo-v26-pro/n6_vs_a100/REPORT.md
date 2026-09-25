# Area-constrained roofline: n6_vs_a100-mimo-v26-pro

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Pro at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 704x (ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream, 3,857 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `hybrid` on 2 devices. On the GPU side the correction reaches 20x (a100_sxm_80gb-x3805-pipeline, 3,805 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 104 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 3 x 46,225 mm2 (138,675 mm2, wafer, KV in SRAM) at 4,465 tok/s per user and 32 tok/s per 1,000 mm2, holding 1 session, against 168 copies of one unified HBM die at the same silicon: 19.9x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 138,675 mm2 of ROM silicon at 4,465 tok/s per user against 138,768 mm2 of a100_sxm_80gb-x168-tensor at 224 tok/s: **19.9x**, ROM binding on `layer_fixed_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 1,121. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 7.17x to it.** At 198,860 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 31.66 tok/s and the same silicon running tensor delivers 227 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.12x (MiMo-V2.6-Pro, ROM binding on `layer_fixed_latency`) to 0.42x (MiMo-V2.6-Pro, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 24 to 93,666 tok/s, and its rate with every slot occupied from 93,649 to 93,666. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 3,857 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,058 us over NVLink, capping per-user decode at 486 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 516.7 us and cap it at 1,935 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 10 of 10 operating points and an array 0; on tokens per second per square millimetre the same points go 0 to the array and 10 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 114 of 1209 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 3.6x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 3.59x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 80% of its cooling budget. The companion study at the other node does have power-limited points.


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

### MiMo-V2.6-Pro at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-wafer-hybrid-x3`** -- 3 x 46,225 mm2 wafers, 138,675 mm2 total, `hybrid`-parallel, KV in SRAM, spare silicon to `sram`.

- **4,465.4 tok/s per user** (0.22 ms/token), binding on `layer_fixed_latency`
- **32.2 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 4,465 tok/s aggregate with every slot full, over 1 resident session (fill limited by `kv_capacity`)
- 10,159 W at 0.073 W/mm2, 2,275.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 168 copies of one unified HBM die -- `a100_sxm_80gb-x168-tensor`, 138,768 mm2, area ratio 0.9993 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 138,675 | 138,768 | 0.9993 |
| user tok/s | 4,465.4 | 224.5 | 19.89x |
| aggregate tok/s | 4,465 | 224 | 0.84x |
| resident sessions | 1 | 1,121 | -- |
| J/token | 2.2752 | 113.3212 | 49.8x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 1,121 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x241-tensor` at 199,066 mm2 and 227.0 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 32.2 | 1 | 19.89x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 32.2 | 1 | 19.89x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | 107,580 | 2,079.4 | 19.3 | 1 | 9.36x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 32.2 | 1 | 19.89x |

**There is nothing to walk to.** The frontier is a single row, which is what it means for one design to beat every other feasible design of this model on BOTH axes at once. No trade-off has to be argued and no threshold is doing any work here: the recommendation is simply the only non-dominated machine. What it beat is in the class table below.

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-wafer-hybrid-x3` **<-- recommended** | 138,675 | 3 | 4,465.4 | 4,465 | 32.2 | 1 | `layer_fixed_latency` | 10,159 | 2,275.2 | `a100_sxm_80gb-x168-tensor` | 19.89x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 120 | densest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x153` | 124,695 | 2,624.8 | 21.0 | 1 |
| array | 120 | fastest | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 146,700 | 2,984.6 | 20.3 | 1 |
| array | 120 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | 107,580 | 2,079.4 | 19.3 | 1 |
| wafer | 36 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 32.2 | 1 |
| wafer | 36 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 32.2 | 1 |
| wafer | 36 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 32.2 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-hybrid-x180` | 146,700 | 2,984.6 | 2,985 | 1 | 11,248 | 3,768.5 | `layer_fixed_latency` | `a100_sxm_80gb-x178-tensor` | 224.9 | 1,191 | 119,524.1 | 0.998 | 13.27x | 31.7x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | 4,465 | 1 | 10,159 | 2,275.2 | `layer_fixed_latency` | `a100_sxm_80gb-x168-tensor` | 224.5 | 1,121 | 113,321.2 | 0.999 | 19.89x | 49.8x |
| 1 | array @ wafer area | `ROM-N6-native-SRAMKV-array-hw-hybrid-x170` | 138,550 | 2,755.4 | 2,755 | 1 | 10,054 | 3,648.8 | `layer_fixed_latency` | `a100_sxm_80gb-x168-tensor` | 224.5 | 1,121 | 113,321.2 | 0.998 | 12.27x | 31.1x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 4,465.4 | -- | 1 | -- | 2,275.2 | -- | -- | -- | -- | -- | 0.999 | 1.62x wafer/array | -- |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 2,360.2 | 40,124 | 4,096 | 498,457 | 97,326.3 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 26,596 | 1,345,341.4 | 1.000 | 11.51x | 13.8x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 2,360.2 | 40,124 | 4,096 | 498,457 | 49,214.3 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 26,596 | 675,307.6 | 1.000 | 11.51x | 13.7x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 2,360.2 | 40,124 | 4,096 | 498,457 | 25,158.4 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 26,596 | 340,290.7 | 1.000 | 11.51x | 13.5x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 2,360.2 | 40,124 | 4,096 | 498,457 | 13,130.4 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 26,596 | 172,782.2 | 1.000 | 11.51x | 13.2x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,715.1 | 58,314 | 4,096 | 518,508 | 9,378.6 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 205.0 | 26,596 | 89,028.0 | 1.000 | 8.37x | 9.5x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 1,104.2 | 75,086 | 4,096 | 536,998 | 7,529.8 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 203.5 | 26,596 | 47,260.0 | 1.000 | 5.42x | 6.3x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 346.3 | 88,665 | 4,096 | 551,924 | 6,224.9 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 163.4 | 26,596 | 16,806.6 | 1.000 | 2.12x | 2.7x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | 90.6 | 92,764 | 4,096 | 556,439 | 5,998.4 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 120.9 | 26,596 | 8,108.5 | 1.000 | 0.75x | 1.4x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 3,143,300 | 22.9 | 93,666 | 4,096 | 557,432 | 5,951.3 | `kv_read` | `a100_sxm_80gb-x3805-hybrid` | 53.9 | 26,596 | 5,045.7 | 1.000 | 0.42x | 0.8x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | wafer | SRAM | 1 |
| 2-1024 | `ROM-N6-native-HBMKV-wafer-hybrid-x68` | 3,143,300 | wafer | HBM | 4,096 |
| 4096 | `ROM-N6-native-HBMKV-wafer-pipeline-x68` | 3,143,300 | wafer | HBM | 4,096 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | SRAM | rom | 132, 136, 153, 170, 180, 183, 227, 244, 340, 366 |
| MiMo-V2.6-Pro | SRAM | sram | 132, 136, 153, 170, 180, 183, 227, 244, 340, 366 |

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
| MiMo-V2.6-Pro | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 1 | 57 on `rom_wafer_express` | 3.00 | centre_mesh, one_shot | 163.66 | 31.09 | 36.52 | 34.54 | 4,465.4 |
| MiMo-V2.6-Pro | `a100_sxm_80gb-x168-tensor` | 1 | 168 | 3.00 | hierarchical | 1,366.30 | 2,909.23 | 178.83 | 1,495.86 | 224.5 |
| MiMo-V2.6-Pro | `a100_sxm_80gb-x168-tensor` | 64 | 168 | 3.00 | hierarchical | 1,366.30 | 22,227.03 | 3,890.25 | 14,830.49 | 36.4 |

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
| Taalas HC1, Llama-3.1-8B on 815 mm2 at N6, per user | 16,960.0 tok/s | 10,723.2 tok/s | 0.63x | within 2x | PASS |
| A100 80GB weight-bound, Llama-3.1-8B FP8 batch 1 on 826 mm2 | 253.91 tok/s | 253.91 tok/s | 1.00x | within 1% | PASS |
| A100 80GB at its published TDP, saturating load | 400.0 W | 461.7 W | 1.15x | within 2x | PASS |
| Taalas HC1 card power at its published operating point | 200.0-250.0 W | 77.6 W | 0.31x | within 2x | FAIL |

HC1 binds on `layer_fixed_latency`. Its component times are weight_read 34.47 us, kv_read 3.13 us, compute 34.47 us, link_latency 0.00 us, layer_fixed_latency 60.22 us.

The model **under**-predicts the shipping part by 1.58x. Rather than tune the densities until the anchor
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
| range low | 1,387.3 ns/layer | 44.40 us | 6.06 us | 12,915.3 | 0.76x | layer_fixed_latency |
| range stated | 1,882.0 ns/layer | 60.22 us | 6.06 us | 10,723.2 | 0.63x | layer_fixed_latency |
| range high | 3,233.9 ns/layer | 103.49 us | 6.06 us | 7,448.3 | 0.44x | layer_fixed_latency |

The per-layer serial cost that would land the model exactly on the
published figure is **810.3 ns/layer**. It is reported so the distance between the measured chain and the one the shipping part implies is visible. It is never used as an input: a chain longer than it means the hardwired datapath modelled here is serially slower than HC1's.

### Anchor sensitivity

| Stored bits/parameter | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 3.0 | 10,704.6 | 0.63x | layer_fixed_latency |
| 3.5 | 10,723.2 | 0.63x | layer_fixed_latency |
| 4.0 | 10,704.6 | 0.63x | layer_fixed_latency |
| 5.0 | 0.0 | 0.00x | capacity_or_format |
| 6.0 | 0.0 | 0.00x | capacity_or_format |

| Anchor context | Modelled tok/s | Ratio | Binds on |
|---:|---:|---:|---|
| 1,024 | 11,622.0 | 0.69x | layer_fixed_latency |
| 1,536 | 11,157.1 | 0.66x | layer_fixed_latency |
| 2,048 | 10,723.2 | 0.63x | layer_fixed_latency |

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
| Taalas HC1 card power | 200.0-250.0 W | 77.6 W | 0.31x | FAIL |

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
| **total** | 461.7 W | 77.6 W |

On HC1 the enumerated static power is 52.2 W and the measured clocked-idle floor is 50.0 W, so the enumeration binds and the floor is inert.

**The band.** Every term in the power block bar one is `assumed`, and
two of them -- the fabric clock and the array clock multiplier --
multiply, so the gates are reported at both ends of the whole band
with every term moved together. Moving one at a time would report a
sensitivity that is really a bias.

| Power band | A100 at TDP | Ratio | HC1 card | Ratio to 250 W | Ratio to 200 W |
|---|---:|---:|---:|---:|---:|
| low | 338.9 W | 0.85x | 56.8 W | 0.23x | 0.28x |
| stated | 461.7 W | 1.15x | 77.6 W | 0.31x | 0.39x |
| high | 698.3 W | 1.75x | 338.7 W | 1.35x | 1.69x |

**The outcome, stated as an outcome.** The A100 gate lands at 1.15x of its published TDP. The HC1 gate lands at 0.31x of the top of its published band, **3.22x low**, against 2.58x low at the bottom of it. The asymmetry is the finding and it should not be smoothed over.

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
| Taalas HC1 (modelled reconstruction) | 0.007235 J/token | 77.6 | 10,723.2 |
| A100 80GB, weight-bound gate, same model and batch | 1.537721 J/token | 336.2 | 218.6 |

That is a factor of 213 in tokens per joule, and **it is a ceiling on the ROM advantage, not a measurement of it**, for three reasons that all point the same way. The GPU is at batch 1, which is a GPU's worst operating point -- it re-reads the whole checkpoint from DRAM for one token, and the batched rows in the table below are the fair comparison. The ROM side's read energy is `assumed` over a 17x bracket. And the HC1 power gate says this model's ROM total is 2.6-3.2x below the shipping part's published card power, so the ROM joules here are a lower bound by roughly that factor.

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

- **0 of 1,209 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 35%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 771 | 0 | 42.7% | 79.8% | 0.386 | 84% |
| rom | wafer (>=40,000 mm2) | 438 | 0 | 15.3% | 35.5% | 0.177 | 98% |

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
| MiMo-V2.6-Pro | 1 | 138,675 | `MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 2.275168 | 10,159.5 | layer_fixed_latency | `MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor` | 113.321198 | 25,440.5 | link_latency | 49.81x |
| MiMo-V2.6-Pro | 2 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 97.326268 | 498,456.6 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 1,345.341352 | 614,243.5 | link_latency | 13.82x |
| MiMo-V2.6-Pro | 4 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 49.214326 | 498,456.6 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 675.307562 | 614,243.5 | link_latency | 13.72x |
| MiMo-V2.6-Pro | 8 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 25.158354 | 498,456.6 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 340.290668 | 614,243.5 | link_latency | 13.53x |
| MiMo-V2.6-Pro | 16 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 13.130369 | 498,456.6 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 172.782220 | 614,243.5 | link_latency | 13.16x |
| MiMo-V2.6-Pro | 32 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 9.378551 | 518,508.3 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 89.027996 | 614,243.5 | link_latency | 9.49x |
| MiMo-V2.6-Pro | 64 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 7.529816 | 536,998.4 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 47.260020 | 615,652.6 | link_latency | 6.28x |
| MiMo-V2.6-Pro | 256 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 6.224851 | 551,924.0 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 16.806594 | 702,841.8 | link_latency | 2.70x |
| MiMo-V2.6-Pro | 1024 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68` | 5.998413 | 556,439.2 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 8.108509 | 1,003,548.5 | weight_read | 1.35x |
| MiMo-V2.6-Pro | 4096 | 3,143,300 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68` | 5.951262 | 557,432.3 | kv_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid` | 5.045667 | 1,114,962.9 | weight_read | 0.85x |

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
| MiMo-V2.6-Pro | 200,000 | 1,020 B | 566.0 GB | 4.44 | 10.279 GB | 10.279 GB | 3.8 |

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
| MiMo-V2.6-Pro | 3 | 138,675 | 5,063.7 | wafer-pipeline | 4,465.4 | wafer-hybrid | 1.13x | 580.6 | pipeline | 224.5 | tensor | 2.59x | 8.72x | 19.89x | 2.28x |
| MiMo-V2.6-Pro | 4 | 184,900 | 5,499.8 | wafer-pipeline | 4,392.1 | wafer-hybrid | 1.25x | 596.1 | pipeline | 226.6 | tensor | 2.63x | 9.23x | 19.38x | 2.10x |
| MiMo-V2.6-Pro | 6 | 277,350 | 5,499.8 | wafer-pipeline | 4,085.1 | wafer-hybrid | 1.35x | 612.4 | pipeline | 208.1 | hybrid | 2.94x | 8.98x | 19.63x | 2.19x |
| MiMo-V2.6-Pro | 8 | 369,800 | 5,499.8 | wafer-pipeline | 3,801.0 | wafer-hybrid | 1.45x | 620.9 | pipeline | 210.9 | hybrid | 2.94x | 8.86x | 18.02x | 2.03x |
| MiMo-V2.6-Pro | 12 | 554,700 | 5,695.1 | wafer-pipeline | 3,522.7 | wafer-hybrid | 1.62x | 629.6 | pipeline | 209.5 | hybrid | 3.01x | 9.04x | 16.81x | 1.86x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 1.86x to 2.28x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 4,465.4 | 4,465.4 | layer_fixed_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor | 138,768 | 1.00x | tensor | 2,909.23 | 224.5 | 224.5 | link_latency | 19.89x | 0.84x | 141.05x | 19.89x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x132 | 107,580 | 2,079.4 | 2,079.4 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | 107,380 | 1.00x | tensor | 2,906.10 | 222.0 | 222.0 | link_latency | 9.36x | 0.51x | 65.68x | 9.36x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 40,124.2 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,038.40 | 205.0 | 12,299.0 | link_latency | 11.51x | 0.33x | 74.55x | 11.51x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 40,124.2 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,038.40 | 205.0 | 12,299.0 | link_latency | 11.51x | 0.33x | 74.55x | 11.51x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 40,124.2 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,038.40 | 205.0 | 12,299.0 | link_latency | 11.51x | 0.33x | 74.55x | 11.51x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 40,124.2 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,038.40 | 205.0 | 12,299.0 | link_latency | 11.51x | 0.33x | 74.55x | 11.51x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,715.1 | 58,313.6 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,038.40 | 205.0 | 12,299.0 | link_latency | 8.37x | 0.48x | 54.18x | 8.37x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,104.2 | 75,086.5 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,059.34 | 203.5 | 13,026.9 | link_latency | 5.42x | 0.62x | 34.88x | 5.42x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 346.3 | 88,664.6 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 3,355.62 | 163.4 | 41,819.4 | link_latency | 2.12x | 0.74x | 10.94x | 2.17x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 90.6 | 92,764.4 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 1,308.90 | 120.9 | 123,764.9 | weight_read | 0.75x | 0.75x | 2.86x | 0.86x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 22.9 | 93,666.2 | kv_read | MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | 3,142,930 | 1.00x | hybrid | 1,659.31 | 53.9 | 220,974.3 | weight_read | 0.42x | 0.42x | 0.74x | 0.48x |

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
| MiMo-V2.6-Pro | 56 | 46,256 | 31.7 | 209.0 | 188.8 | tensor | 2,882.61 | 60.2% | link_latency |
| MiMo-V2.6-Pro | 66 | 54,516 | 31.7 | 212.2 | 193.5 | tensor | 2,891.49 | 61.4% | link_latency |
| MiMo-V2.6-Pro | 68 | 56,168 | 31.7 | 212.8 | 194.5 | tensor | 2,891.49 | 61.5% | link_latency |
| MiMo-V2.6-Pro | 104 | 85,904 | 31.7 | 219.5 | 206.8 | tensor | 2,901.04 | 63.7% | link_latency |
| MiMo-V2.6-Pro | 112 | 92,512 | 31.7 | 220.4 | 208.6 | tensor | 2,902.58 | 64.0% | link_latency |
| MiMo-V2.6-Pro | 130 | 107,380 | 31.7 | 222.0 | 201.8 | tensor | 2,906.10 | 64.5% | link_latency |
| MiMo-V2.6-Pro | 134 | 110,684 | 31.7 | 222.4 | 202.7 | tensor | 2,906.10 | 64.6% | link_latency |
| MiMo-V2.6-Pro | 151 | 124,726 | 31.7 | 223.6 | 205.9 | tensor | 2,907.83 | 65.0% | link_latency |
| MiMo-V2.6-Pro | 168 | 138,768 | 31.7 | 224.5 | 208.4 | tensor | 2,909.23 | 65.3% | link_latency |
| MiMo-V2.6-Pro | 178 | 147,028 | 31.7 | 224.9 | 209.8 | tensor | 2,910.39 | 65.5% | link_latency |
| MiMo-V2.6-Pro | 181 | 149,506 | 31.7 | 225.1 | 210.1 | tensor | 2,910.39 | 65.5% | link_latency |
| MiMo-V2.6-Pro | 186 | 153,636 | 31.7 | 225.3 | 210.7 | tensor | 2,910.90 | 65.6% | link_latency |
| MiMo-V2.6-Pro | 187 | 154,462 | 31.7 | 225.3 | 210.8 | tensor | 2,910.90 | 65.6% | link_latency |
| MiMo-V2.6-Pro | 224 | 185,024 | 31.7 | 226.6 | 208.3 | tensor | 2,912.56 | 66.0% | link_latency |
| MiMo-V2.6-Pro | 241 | 199,066 | 31.7 | 227.0 | 210.0 | tensor | 2,913.52 | 66.1% | link_latency |
| MiMo-V2.6-Pro | 335 | 276,710 | 31.7 | 191.4 | 208.0 | hybrid | 2,902.24 | 60.4% | link_latency |
| MiMo-V2.6-Pro | 336 | 277,536 | 31.7 | 191.4 | 208.1 | hybrid | 2,902.24 | 60.4% | link_latency |
| MiMo-V2.6-Pro | 361 | 298,186 | 31.7 | 191.6 | 209.7 | hybrid | 2,902.24 | 60.9% | link_latency |
| MiMo-V2.6-Pro | 448 | 370,048 | 31.7 | 192.2 | 210.9 | hybrid | 2,904.76 | 61.3% | link_latency |
| MiMo-V2.6-Pro | 593 | 489,818 | 31.7 | 192.7 | 209.0 | hybrid | 2,912.33 | 60.9% | link_latency |
| MiMo-V2.6-Pro | 672 | 555,072 | 31.7 | 192.9 | 209.5 | hybrid | 2,914.85 | 61.1% | link_latency |
| MiMo-V2.6-Pro | 3805 | 3,142,930 | 31.7 | 194.2 | 205.0 | hybrid | 3,038.40 | 62.3% | link_latency |

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
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x180 | MiMo-V2.6-Pro | 180 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x136 | MiMo-V2.6-Pro | 136 | tensor | rom_package_ucie | rom_board_serdes | 280 | 160.55 us | 622.9 tok/s | 6,228.6 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 34 on rom_board_serdes (traversals 11.0) = 156.78 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x180 | MiMo-V2.6-Pro | 180 | hybrid | rom_package_ucie | rom_board_serdes | 184 | 8.47 us | 11,809.1 tok/s | 118,090.9 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 44 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 4.70 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x180 | MiMo-V2.6-Pro | 180 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | MiMo-V2.6-Pro | 3 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x132 | MiMo-V2.6-Pro | 132 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3 | MiMo-V2.6-Pro | 3 | tensor | on_wafer | rom_wafer_serdes | 280 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 31.37 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hybrid-x180 | MiMo-V2.6-Pro | 180 | hybrid | nvlink3 | infiniband_hdr | 162 | 770.53 us | 129.8 tok/s | 1,297.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.47 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | MiMo-V2.6-Pro | 3 | hybrid | on_wafer | rom_wafer_serdes | 142 | 269.70 us | 370.8 tok/s | 3,707.8 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | MiMo-V2.6-Pro | 68 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x68 | MiMo-V2.6-Pro | 68 | tensor | on_wafer | rom_wafer_serdes | 280 | 516.75 us | 193.5 tok/s | 1,935.2 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 68 on rom_wafer_serdes (traversals 17.6) = 247.25 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | MiMo-V2.6-Pro | 68 | hybrid | on_wafer | rom_wafer_serdes | 207 | 276.34 us | 361.9 tok/s | 3,618.8 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 67 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 6.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Pro | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 139.64 us | 716.1 tok/s | 7,161.5 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.51 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Pro | 56 | tensor | nvlink3 | infiniband_hdr | 280 | 1,460.40 us | 68.5 tok/s | 684.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 745.35 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Pro | 56 | hybrid | nvlink3 | infiniband_hdr | 146 | 730.18 us | 137.0 tok/s | 1,369.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-expert | MiMo-V2.6-Pro | 56 | expert | nvlink3 | infiniband_hdr | 280 | 996.18 us | 100.4 tok/s | 1,003.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 702.15 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 294.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-pipeline | MiMo-V2.6-Pro | 66 | pipeline | nvlink3 | infiniband_hdr | 65 | 165.01 us | 606.0 tok/s | 6,060.4 tok/s | 57 x point_to_point span 2 on nvlink3 (traversals 1.0) = 144.83 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-tensor | MiMo-V2.6-Pro | 66 | tensor | nvlink3 | infiniband_hdr | 280 | 1,466.95 us | 68.2 tok/s | 681.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 751.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-hybrid | MiMo-V2.6-Pro | 66 | hybrid | nvlink3 | infiniband_hdr | 148 | 735.22 us | 136.0 tok/s | 1,360.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-expert | MiMo-V2.6-Pro | 66 | expert | nvlink3 | infiniband_hdr | 280 | 994.42 us | 100.6 tok/s | 1,005.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.88 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 292.54 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x68-pipeline | MiMo-V2.6-Pro | 68 | pipeline | nvlink3 | infiniband_hdr | 67 | 170.09 us | 587.9 tok/s | 5,879.3 tok/s | 59 x point_to_point span 2 on nvlink3 (traversals 1.0) = 149.92 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x68-tensor | MiMo-V2.6-Pro | 68 | tensor | nvlink3 | infiniband_hdr | 280 | 1,466.95 us | 68.2 tok/s | 681.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 751.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x68-hybrid | MiMo-V2.6-Pro | 68 | hybrid | nvlink3 | infiniband_hdr | 148 | 735.22 us | 136.0 tok/s | 1,360.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x68-expert | MiMo-V2.6-Pro | 68 | expert | nvlink3 | infiniband_hdr | 280 | 994.18 us | 100.6 tok/s | 1,005.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.88 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 292.30 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x104-pipeline | MiMo-V2.6-Pro | 104 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x104-tensor | MiMo-V2.6-Pro | 104 | tensor | nvlink3 | infiniband_hdr | 280 | 1,474.01 us | 67.8 tok/s | 678.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 13 on infiniband_hdr (traversals 2.0) = 758.96 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x104-hybrid | MiMo-V2.6-Pro | 104 | hybrid | nvlink3 | infiniband_hdr | 152 | 745.31 us | 134.2 tok/s | 1,341.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 12 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 30.26 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x104-expert | MiMo-V2.6-Pro | 104 | expert | nvlink3 | infiniband_hdr | 280 | 990.65 us | 100.9 tok/s | 1,009.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.16 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 289.49 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Pro | 112 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Pro | 112 | tensor | nvlink3 | infiniband_hdr | 280 | 1,475.15 us | 67.8 tok/s | 677.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 760.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Pro | 112 | hybrid | nvlink3 | infiniband_hdr | 153 | 747.83 us | 133.7 tok/s | 1,337.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 32.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-expert | MiMo-V2.6-Pro | 112 | expert | nvlink3 | infiniband_hdr | 280 | 990.19 us | 101.0 tok/s | 1,009.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.08 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 289.12 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-pipeline | MiMo-V2.6-Pro | 130 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | MiMo-V2.6-Pro | 130 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | MiMo-V2.6-Pro | 130 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-expert | MiMo-V2.6-Pro | 130 | expert | nvlink3 | infiniband_hdr | 280 | 989.38 us | 101.1 tok/s | 1,010.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-pipeline | MiMo-V2.6-Pro | 134 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-tensor | MiMo-V2.6-Pro | 134 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-hybrid | MiMo-V2.6-Pro | 134 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x134-expert | MiMo-V2.6-Pro | 134 | expert | nvlink3 | infiniband_hdr | 280 | 989.25 us | 101.1 tok/s | 1,010.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.31 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x151-pipeline | MiMo-V2.6-Pro | 151 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x151-tensor | MiMo-V2.6-Pro | 151 | tensor | nvlink3 | infiniband_hdr | 280 | 1,479.03 us | 67.6 tok/s | 676.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 763.97 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x151-hybrid | MiMo-V2.6-Pro | 151 | hybrid | nvlink3 | infiniband_hdr | 158 | 760.44 us | 131.5 tok/s | 1,315.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 45.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x151-expert | MiMo-V2.6-Pro | 151 | expert | nvlink3 | infiniband_hdr | 280 | 988.68 us | 101.1 tok/s | 1,011.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.84 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.85 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Pro | 168 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Pro | 168 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.06 us | 67.6 tok/s | 675.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 765.01 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Pro | 168 | hybrid | nvlink3 | infiniband_hdr | 160 | 765.48 us | 130.6 tok/s | 1,306.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 50.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-expert | MiMo-V2.6-Pro | 168 | expert | nvlink3 | infiniband_hdr | 280 | 988.19 us | 101.2 tok/s | 1,011.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.48 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x178-pipeline | MiMo-V2.6-Pro | 178 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x178-tensor | MiMo-V2.6-Pro | 178 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.92 us | 67.5 tok/s | 675.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 765.86 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x178-hybrid | MiMo-V2.6-Pro | 178 | hybrid | nvlink3 | infiniband_hdr | 162 | 770.53 us | 129.8 tok/s | 1,297.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x178-expert | MiMo-V2.6-Pro | 178 | expert | nvlink3 | infiniband_hdr | 280 | 987.98 us | 101.2 tok/s | 1,012.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.68 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.29 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x181-pipeline | MiMo-V2.6-Pro | 181 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x181-tensor | MiMo-V2.6-Pro | 181 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.92 us | 67.5 tok/s | 675.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 765.86 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x181-hybrid | MiMo-V2.6-Pro | 181 | hybrid | nvlink3 | infiniband_hdr | 162 | 770.53 us | 129.8 tok/s | 1,297.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x181-expert | MiMo-V2.6-Pro | 181 | expert | nvlink3 | infiniband_hdr | 280 | 987.93 us | 101.2 tok/s | 1,012.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.68 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-pipeline | MiMo-V2.6-Pro | 186 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-tensor | MiMo-V2.6-Pro | 186 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.29 us | 67.5 tok/s | 675.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 766.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-hybrid | MiMo-V2.6-Pro | 186 | hybrid | nvlink3 | infiniband_hdr | 163 | 773.05 us | 129.4 tok/s | 1,293.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-expert | MiMo-V2.6-Pro | 186 | expert | nvlink3 | infiniband_hdr | 280 | 987.81 us | 101.2 tok/s | 1,012.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.65 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-pipeline | MiMo-V2.6-Pro | 187 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-tensor | MiMo-V2.6-Pro | 187 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.29 us | 67.5 tok/s | 675.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 766.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-hybrid | MiMo-V2.6-Pro | 187 | hybrid | nvlink3 | infiniband_hdr | 163 | 773.05 us | 129.4 tok/s | 1,293.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x187-expert | MiMo-V2.6-Pro | 187 | expert | nvlink3 | infiniband_hdr | 280 | 987.80 us | 101.2 tok/s | 1,012.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.65 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.14 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Pro | 224 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Pro | 224 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.52 us | 67.5 tok/s | 674.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 767.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Pro | 224 | hybrid | nvlink3 | infiniband_hdr | 167 | 783.13 us | 127.7 tok/s | 1,276.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-expert | MiMo-V2.6-Pro | 224 | expert | nvlink3 | infiniband_hdr | 280 | 987.20 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.66 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x241-pipeline | MiMo-V2.6-Pro | 241 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x241-tensor | MiMo-V2.6-Pro | 241 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.23 us | 67.4 tok/s | 674.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 31 on infiniband_hdr (traversals 2.0) = 768.18 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x241-hybrid | MiMo-V2.6-Pro | 241 | hybrid | nvlink3 | infiniband_hdr | 170 | 790.70 us | 126.5 tok/s | 1,264.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 30 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 75.65 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x241-expert | MiMo-V2.6-Pro | 241 | expert | nvlink3 | infiniband_hdr | 280 | 986.99 us | 101.3 tok/s | 1,013.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.50 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.48 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Pro | 335 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Pro | 335 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Pro | 335 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-expert | MiMo-V2.6-Pro | 335 | expert | nvlink3 | infiniband_hdr | 280 | 986.21 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.37 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Pro | 336 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Pro | 336 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Pro | 336 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-expert | MiMo-V2.6-Pro | 336 | expert | nvlink3 | infiniband_hdr | 280 | 986.20 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.36 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x361-pipeline | MiMo-V2.6-Pro | 361 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x361-tensor | MiMo-V2.6-Pro | 361 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.80 us | 48.7 tok/s | 486.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 46 on infiniband_hdr (traversals 4.0) = 1,338.75 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x361-hybrid | MiMo-V2.6-Pro | 361 | hybrid | nvlink3 | infiniband_hdr | 185 | 828.52 us | 120.7 tok/s | 1,207.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 45 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 113.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x361-expert | MiMo-V2.6-Pro | 361 | expert | nvlink3 | infiniband_hdr | 280 | 986.06 us | 101.4 tok/s | 1,014.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.33 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.72 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Pro | 448 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Pro | 448 | tensor | nvlink3 | infiniband_hdr | 280 | 2,054.60 us | 48.7 tok/s | 486.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,339.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Pro | 448 | hybrid | nvlink3 | infiniband_hdr | 195 | 853.74 us | 117.1 tok/s | 1,171.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 138.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-expert | MiMo-V2.6-Pro | 448 | expert | nvlink3 | infiniband_hdr | 280 | 985.70 us | 101.5 tok/s | 1,014.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.27 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x593-pipeline | MiMo-V2.6-Pro | 593 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x593-tensor | MiMo-V2.6-Pro | 593 | tensor | nvlink3 | infiniband_hdr | 280 | 2,055.54 us | 48.6 tok/s | 486.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 75 on infiniband_hdr (traversals 4.0) = 1,340.49 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x593-hybrid | MiMo-V2.6-Pro | 593 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x593-expert | MiMo-V2.6-Pro | 593 | expert | nvlink3 | infiniband_hdr | 280 | 985.33 us | 101.5 tok/s | 1,014.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.20 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Pro | 672 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Pro | 672 | tensor | nvlink3 | infiniband_hdr | 280 | 2,055.83 us | 48.6 tok/s | 486.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,340.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Pro | 672 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-expert | MiMo-V2.6-Pro | 672 | expert | nvlink3 | infiniband_hdr | 280 | 985.20 us | 101.5 tok/s | 1,015.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.18 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.02 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x3805-pipeline | MiMo-V2.6-Pro | 3805 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x3805-tensor | MiMo-V2.6-Pro | 3805 | tensor | nvlink3 | infiniband_hdr | 280 | 2,057.86 us | 48.6 tok/s | 485.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 476 on infiniband_hdr (traversals 4.0) = 1,342.80 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x3805-hybrid | MiMo-V2.6-Pro | 3805 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x3805-expert | MiMo-V2.6-Pro | 3805 | expert | nvlink3 | infiniband_hdr | 280 | 984.38 us | 101.6 tok/s | 1,015.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.03 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 284.34 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | 138,675 | 4,465.4 | 0.032 | 2,984.6 (146,700) | 4,465.4 (138,675) | 1.50x | layer_fixed_latency |
| MiMo-V2.6-Pro | 2 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 0.001 | — (—) | 2,360.2 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 4 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 0.001 | — (—) | 2,360.2 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 8 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 0.001 | — (—) | 2,360.2 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 16 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 2,360.2 | 0.001 | — (—) | 2,360.2 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 32 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,715.1 | 0.001 | — (—) | 1,715.1 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 64 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 1,104.2 | 0.000 | — (—) | 1,104.2 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 256 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 346.3 | 0.000 | — (—) | 346.3 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 1024 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68 | 3,143,300 | 90.6 | 0.000 | — (—) | 90.6 (3,143,300) | — | kv_read |
| MiMo-V2.6-Pro | 4096 | wafer | wafer | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 22.9 | 0.000 | — (—) | 22.9 (3,143,300) | — | kv_read |

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
| MiMo-V2.6-Pro | 384 | 1,383.7 MB | 303.5 mm2 | 54.63 mm2 (18.0%) | 116,538 mm2 | 20,977 mm2 | 124,143 mm2 = 152.3 reticles |

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
| MiMo-V2.6-Pro | 1 | sram | 93,648.9 | 26,087.3 | 26,087.3 | 3.59x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 93,648.9 | 26,087.3 | 26,087.3 | 3.59x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 93,648.9 | 26,087.3 | 26,087.3 | 3.59x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 93,648.9 | 26,087.3 | 26,087.3 | 3.59x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | sram | 93,648.9 | 26,087.3 | 26,087.3 | 3.59x | 1.00x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | sram | 93,648.9 | 26,087.3 | 32,320.2 | 3.59x | 1.24x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 64 | sram | 93,648.9 | 26,087.3 | 49,037.9 | 3.59x | 1.88x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 256 | sram | 93,648.9 | 26,087.3 | 83,860.8 | 3.59x | 3.21x | kv_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 1024 | sram | 93,648.9 | 26,087.3 | 92,221.5 | 3.59x | 3.54x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | sram | 93,666.2 | 26,088.6 | 93,540.9 | 3.59x | 3.59x | kv_read | weight_read | kv_read |
| MiMo-V2.6-Pro | 1 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 2 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 4 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 8 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 16 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 32 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 64 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 256 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 1024 | rom | 93,640.4 | 93,623.4 | 93,623.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| MiMo-V2.6-Pro | 4096 | rom | 93,652.5 | 93,640.3 | 93,640.3 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 1.14 | 32,320.2 | 0.010 | weight_read | 0.35x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 1.58 | 49,037.9 | 0.016 | weight_read | 0.52x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 2.12 | 83,860.8 | 0.027 | weight_read | 0.90x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,648.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,640.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.00 | 26,087.3 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 2.19 | 92,221.5 | 0.029 | kv_read | 0.98x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.00 | 93,623.4 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68 | 3,143,300 | 1.00 | 1.00 | 93,666.2 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-romfill | 3,143,300 | 17.62 | 1.00 | 93,652.5 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream | 3,143,300 | 1.00 | 1.06 | 26,088.6 | 0.008 | weight_read | 0.28x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perstream-romfill | 3,143,300 | 63.88 | 1.06 | 93,640.3 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x68-perregion | 3,143,300 | 1.00 | 2.20 | 93,540.9 | 0.030 | kv_read | 1.00x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x68-perregion-romfill | 3,143,300 | 63.88 | 1.01 | 93,640.3 | 0.030 | kv_read | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 67 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 256 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 1024 | 3,857 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4096 | 3,857 | 1.06 | 1.001 | 1.009 | 1.01x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Pro | 2 | 56 | 13.90 | 8.00 | 1.74x |
| MiMo-V2.6-Pro | 4 | 56 | 23.97 | 11.25 | 2.13x |
| MiMo-V2.6-Pro | 8 | 56 | 36.84 | 15.03 | 2.45x |
| MiMo-V2.6-Pro | 16 | 56 | 48.26 | 19.16 | 2.52x |
| MiMo-V2.6-Pro | 32 | 56 | 54.12 | 23.13 | 2.34x |
| MiMo-V2.6-Pro | 64 | 56 | 55.67 | 26.26 | 2.12x |
| MiMo-V2.6-Pro | 256 | 56 | 55.94 | 28.52 | 1.96x |
| MiMo-V2.6-Pro | 1 | 66 | 7.59 | 5.96 | 1.27x |
| MiMo-V2.6-Pro | 2 | 66 | 14.17 | 8.34 | 1.70x |
| MiMo-V2.6-Pro | 4 | 66 | 24.89 | 11.88 | 2.09x |
| MiMo-V2.6-Pro | 8 | 66 | 39.40 | 16.05 | 2.45x |
| MiMo-V2.6-Pro | 16 | 66 | 53.66 | 20.72 | 2.59x |
| MiMo-V2.6-Pro | 32 | 66 | 62.27 | 25.27 | 2.46x |
| MiMo-V2.6-Pro | 64 | 66 | 65.14 | 28.93 | 2.25x |
| MiMo-V2.6-Pro | 256 | 66 | 65.81 | 31.60 | 2.08x |
| MiMo-V2.6-Pro | 1 | 68 | 7.60 | 6.00 | 1.27x |
| MiMo-V2.6-Pro | 2 | 68 | 14.22 | 8.40 | 1.69x |
| MiMo-V2.6-Pro | 4 | 68 | 25.05 | 12.00 | 2.09x |
| MiMo-V2.6-Pro | 8 | 68 | 39.85 | 16.24 | 2.45x |
| MiMo-V2.6-Pro | 16 | 68 | 54.64 | 21.00 | 2.60x |
| MiMo-V2.6-Pro | 32 | 68 | 63.82 | 25.67 | 2.49x |
| MiMo-V2.6-Pro | 64 | 68 | 66.99 | 29.44 | 2.28x |
| MiMo-V2.6-Pro | 256 | 68 | 67.76 | 32.19 | 2.11x |
| MiMo-V2.6-Pro | 1 | 104 | 7.74 | 6.49 | 1.19x |
| MiMo-V2.6-Pro | 2 | 104 | 14.75 | 9.36 | 1.58x |
| MiMo-V2.6-Pro | 4 | 104 | 26.93 | 13.54 | 1.99x |
| MiMo-V2.6-Pro | 8 | 104 | 45.48 | 18.91 | 2.40x |
| MiMo-V2.6-Pro | 16 | 104 | 68.01 | 25.26 | 2.69x |
| MiMo-V2.6-Pro | 32 | 104 | 87.13 | 31.74 | 2.74x |
| MiMo-V2.6-Pro | 64 | 104 | 97.32 | 37.16 | 2.62x |
| MiMo-V2.6-Pro | 256 | 104 | 101.41 | 41.24 | 2.46x |
| MiMo-V2.6-Pro | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Pro | 2 | 112 | 14.83 | 9.53 | 1.56x |
| MiMo-V2.6-Pro | 4 | 112 | 27.20 | 13.79 | 1.97x |
| MiMo-V2.6-Pro | 8 | 112 | 46.33 | 19.40 | 2.39x |
| MiMo-V2.6-Pro | 16 | 112 | 70.17 | 26.03 | 2.70x |
| MiMo-V2.6-Pro | 32 | 112 | 91.30 | 32.86 | 2.78x |
| MiMo-V2.6-Pro | 64 | 112 | 103.24 | 38.61 | 2.67x |
| MiMo-V2.6-Pro | 256 | 112 | 108.37 | 42.96 | 2.52x |
| MiMo-V2.6-Pro | 1 | 130 | 7.79 | 6.71 | 1.16x |
| MiMo-V2.6-Pro | 2 | 130 | 14.96 | 9.90 | 1.51x |
| MiMo-V2.6-Pro | 4 | 130 | 27.69 | 14.28 | 1.94x |
| MiMo-V2.6-Pro | 8 | 130 | 47.90 | 20.40 | 2.35x |
| MiMo-V2.6-Pro | 16 | 130 | 74.33 | 27.63 | 2.69x |
| MiMo-V2.6-Pro | 32 | 130 | 99.61 | 35.16 | 2.83x |
| MiMo-V2.6-Pro | 64 | 130 | 115.52 | 41.61 | 2.78x |
| MiMo-V2.6-Pro | 256 | 130 | 123.21 | 46.55 | 2.65x |
| MiMo-V2.6-Pro | 1 | 134 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Pro | 2 | 134 | 14.99 | 9.97 | 1.50x |
| MiMo-V2.6-Pro | 4 | 134 | 27.78 | 14.38 | 1.93x |
| MiMo-V2.6-Pro | 8 | 134 | 48.20 | 20.61 | 2.34x |
| MiMo-V2.6-Pro | 16 | 134 | 75.14 | 27.96 | 2.69x |
| MiMo-V2.6-Pro | 32 | 134 | 101.28 | 35.64 | 2.84x |
| MiMo-V2.6-Pro | 64 | 134 | 118.06 | 42.24 | 2.80x |
| MiMo-V2.6-Pro | 256 | 134 | 126.35 | 47.30 | 2.67x |
| MiMo-V2.6-Pro | 1 | 151 | 7.82 | 6.85 | 1.14x |
| MiMo-V2.6-Pro | 2 | 151 | 15.08 | 10.27 | 1.47x |
| MiMo-V2.6-Pro | 4 | 151 | 28.12 | 14.76 | 1.91x |
| MiMo-V2.6-Pro | 8 | 151 | 49.33 | 21.44 | 2.30x |
| MiMo-V2.6-Pro | 16 | 151 | 78.21 | 29.26 | 2.67x |
| MiMo-V2.6-Pro | 32 | 151 | 107.77 | 37.56 | 2.87x |
| MiMo-V2.6-Pro | 64 | 151 | 128.15 | 44.75 | 2.86x |
| MiMo-V2.6-Pro | 256 | 151 | 139.09 | 50.31 | 2.76x |
| MiMo-V2.6-Pro | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Pro | 2 | 168 | 15.15 | 10.53 | 1.44x |
| MiMo-V2.6-Pro | 4 | 168 | 28.40 | 15.10 | 1.88x |
| MiMo-V2.6-Pro | 8 | 168 | 50.25 | 22.20 | 2.26x |
| MiMo-V2.6-Pro | 16 | 168 | 80.79 | 30.42 | 2.66x |
| MiMo-V2.6-Pro | 32 | 168 | 113.39 | 39.29 | 2.89x |
| MiMo-V2.6-Pro | 64 | 168 | 137.21 | 47.05 | 2.92x |
| MiMo-V2.6-Pro | 256 | 168 | 150.85 | 53.09 | 2.84x |
| MiMo-V2.6-Pro | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| MiMo-V2.6-Pro | 1 | 178 | 7.84 | 6.99 | 1.12x |
| MiMo-V2.6-Pro | 2 | 178 | 15.19 | 10.68 | 1.42x |
| MiMo-V2.6-Pro | 4 | 178 | 28.54 | 15.28 | 1.87x |
| MiMo-V2.6-Pro | 8 | 178 | 50.71 | 22.61 | 2.24x |
| MiMo-V2.6-Pro | 16 | 178 | 82.12 | 31.04 | 2.65x |
| MiMo-V2.6-Pro | 32 | 178 | 116.36 | 40.23 | 2.89x |
| MiMo-V2.6-Pro | 64 | 178 | 142.10 | 48.31 | 2.94x |
| MiMo-V2.6-Pro | 256 | 178 | 157.34 | 54.62 | 2.88x |
| MiMo-V2.6-Pro | 1024 | 178 | 157.54 | 54.72 | 2.88x |
| MiMo-V2.6-Pro | 1 | 181 | 7.85 | 7.01 | 1.12x |
| MiMo-V2.6-Pro | 2 | 181 | 15.20 | 10.72 | 1.42x |
| MiMo-V2.6-Pro | 4 | 181 | 28.57 | 15.33 | 1.86x |
| MiMo-V2.6-Pro | 8 | 181 | 50.84 | 22.73 | 2.24x |
| MiMo-V2.6-Pro | 16 | 181 | 82.50 | 31.22 | 2.64x |
| MiMo-V2.6-Pro | 32 | 181 | 117.21 | 40.51 | 2.89x |
| MiMo-V2.6-Pro | 64 | 181 | 143.51 | 48.68 | 2.95x |
| MiMo-V2.6-Pro | 256 | 181 | 159.22 | 55.07 | 2.89x |
| MiMo-V2.6-Pro | 1024 | 181 | 159.44 | 55.17 | 2.89x |
| MiMo-V2.6-Pro | 1 | 186 | 7.85 | 7.03 | 1.12x |
| MiMo-V2.6-Pro | 2 | 186 | 15.22 | 10.79 | 1.41x |
| MiMo-V2.6-Pro | 4 | 186 | 28.64 | 15.42 | 1.86x |
| MiMo-V2.6-Pro | 8 | 186 | 51.05 | 22.92 | 2.23x |
| MiMo-V2.6-Pro | 16 | 186 | 83.10 | 31.51 | 2.64x |
| MiMo-V2.6-Pro | 32 | 186 | 118.57 | 40.95 | 2.90x |
| MiMo-V2.6-Pro | 64 | 186 | 145.81 | 49.28 | 2.96x |
| MiMo-V2.6-Pro | 256 | 186 | 162.31 | 55.80 | 2.91x |
| MiMo-V2.6-Pro | 1024 | 186 | 162.53 | 55.91 | 2.91x |
| MiMo-V2.6-Pro | 1 | 187 | 7.85 | 7.03 | 1.12x |
| MiMo-V2.6-Pro | 2 | 187 | 15.22 | 10.81 | 1.41x |
| MiMo-V2.6-Pro | 4 | 187 | 28.65 | 15.44 | 1.86x |
| MiMo-V2.6-Pro | 8 | 187 | 51.10 | 22.96 | 2.23x |
| MiMo-V2.6-Pro | 16 | 187 | 83.22 | 31.57 | 2.64x |
| MiMo-V2.6-Pro | 32 | 187 | 118.84 | 41.04 | 2.90x |
| MiMo-V2.6-Pro | 64 | 187 | 146.26 | 49.40 | 2.96x |
| MiMo-V2.6-Pro | 256 | 187 | 162.92 | 55.95 | 2.91x |
| MiMo-V2.6-Pro | 1024 | 187 | 163.14 | 56.05 | 2.91x |
| MiMo-V2.6-Pro | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Pro | 2 | 224 | 15.32 | 11.26 | 1.36x |
| MiMo-V2.6-Pro | 4 | 224 | 29.02 | 16.04 | 1.81x |
| MiMo-V2.6-Pro | 8 | 224 | 52.37 | 24.21 | 2.16x |
| MiMo-V2.6-Pro | 16 | 224 | 86.96 | 33.46 | 2.60x |
| MiMo-V2.6-Pro | 32 | 224 | 127.51 | 44.02 | 2.90x |
| MiMo-V2.6-Pro | 64 | 224 | 161.19 | 53.46 | 3.02x |
| MiMo-V2.6-Pro | 256 | 224 | 183.50 | 60.94 | 3.01x |
| MiMo-V2.6-Pro | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| MiMo-V2.6-Pro | 1 | 241 | 7.88 | 7.22 | 1.09x |
| MiMo-V2.6-Pro | 2 | 241 | 15.36 | 11.44 | 1.34x |
| MiMo-V2.6-Pro | 4 | 241 | 29.16 | 16.29 | 1.79x |
| MiMo-V2.6-Pro | 8 | 241 | 52.84 | 24.70 | 2.14x |
| MiMo-V2.6-Pro | 16 | 241 | 88.35 | 34.22 | 2.58x |
| MiMo-V2.6-Pro | 32 | 241 | 130.82 | 45.26 | 2.89x |
| MiMo-V2.6-Pro | 64 | 241 | 167.07 | 55.16 | 3.03x |
| MiMo-V2.6-Pro | 256 | 241 | 191.82 | 63.02 | 3.04x |
| MiMo-V2.6-Pro | 1024 | 241 | 192.18 | 63.15 | 3.04x |
| MiMo-V2.6-Pro | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 335 | 15.49 | 12.24 | 1.27x |
| MiMo-V2.6-Pro | 4 | 335 | 29.66 | 17.53 | 1.69x |
| MiMo-V2.6-Pro | 8 | 335 | 54.61 | 26.66 | 2.05x |
| MiMo-V2.6-Pro | 16 | 335 | 93.75 | 37.88 | 2.48x |
| MiMo-V2.6-Pro | 32 | 335 | 144.17 | 51.16 | 2.82x |
| MiMo-V2.6-Pro | 64 | 335 | 191.76 | 62.99 | 3.04x |
| MiMo-V2.6-Pro | 256 | 335 | 228.15 | 72.67 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| MiMo-V2.6-Pro | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 336 | 15.49 | 12.24 | 1.26x |
| MiMo-V2.6-Pro | 4 | 336 | 29.67 | 17.54 | 1.69x |
| MiMo-V2.6-Pro | 8 | 336 | 54.62 | 26.67 | 2.05x |
| MiMo-V2.6-Pro | 16 | 336 | 93.80 | 37.91 | 2.47x |
| MiMo-V2.6-Pro | 32 | 336 | 144.27 | 51.21 | 2.82x |
| MiMo-V2.6-Pro | 64 | 336 | 191.97 | 63.06 | 3.04x |
| MiMo-V2.6-Pro | 256 | 336 | 228.47 | 72.76 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| MiMo-V2.6-Pro | 1 | 361 | 7.92 | 7.45 | 1.06x |
| MiMo-V2.6-Pro | 2 | 361 | 15.51 | 12.41 | 1.25x |
| MiMo-V2.6-Pro | 4 | 361 | 29.76 | 17.84 | 1.67x |
| MiMo-V2.6-Pro | 8 | 361 | 54.94 | 27.05 | 2.03x |
| MiMo-V2.6-Pro | 16 | 361 | 94.80 | 38.78 | 2.44x |
| MiMo-V2.6-Pro | 32 | 361 | 146.84 | 52.50 | 2.80x |
| MiMo-V2.6-Pro | 64 | 361 | 196.89 | 64.75 | 3.04x |
| MiMo-V2.6-Pro | 256 | 361 | 235.97 | 74.97 | 3.15x |
| MiMo-V2.6-Pro | 1024 | 361 | 236.58 | 75.13 | 3.15x |
| MiMo-V2.6-Pro | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Pro | 2 | 448 | 15.57 | 12.88 | 1.21x |
| MiMo-V2.6-Pro | 4 | 448 | 30.00 | 18.77 | 1.60x |
| MiMo-V2.6-Pro | 8 | 448 | 55.80 | 28.11 | 1.99x |
| MiMo-V2.6-Pro | 16 | 448 | 97.49 | 41.50 | 2.35x |
| MiMo-V2.6-Pro | 32 | 448 | 153.83 | 56.17 | 2.74x |
| MiMo-V2.6-Pro | 64 | 448 | 210.61 | 70.02 | 3.01x |
| MiMo-V2.6-Pro | 256 | 448 | 257.32 | 81.76 | 3.15x |
| MiMo-V2.6-Pro | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| MiMo-V2.6-Pro | 1 | 593 | 7.95 | 7.65 | 1.04x |
| MiMo-V2.6-Pro | 2 | 593 | 15.64 | 13.43 | 1.16x |
| MiMo-V2.6-Pro | 4 | 593 | 30.24 | 20.08 | 1.51x |
| MiMo-V2.6-Pro | 8 | 593 | 56.68 | 29.42 | 1.93x |
| MiMo-V2.6-Pro | 16 | 593 | 100.33 | 45.04 | 2.23x |
| MiMo-V2.6-Pro | 32 | 593 | 161.40 | 60.71 | 2.66x |
| MiMo-V2.6-Pro | 64 | 593 | 225.93 | 77.46 | 2.92x |
| MiMo-V2.6-Pro | 256 | 593 | 281.92 | 90.40 | 3.12x |
| MiMo-V2.6-Pro | 1024 | 593 | 282.84 | 90.63 | 3.12x |
| MiMo-V2.6-Pro | 1 | 672 | 7.96 | 7.69 | 1.03x |
| MiMo-V2.6-Pro | 2 | 672 | 15.66 | 13.65 | 1.15x |
| MiMo-V2.6-Pro | 4 | 672 | 30.33 | 20.68 | 1.47x |
| MiMo-V2.6-Pro | 8 | 672 | 57.00 | 30.02 | 1.90x |
| MiMo-V2.6-Pro | 16 | 672 | 101.38 | 46.51 | 2.18x |
| MiMo-V2.6-Pro | 32 | 672 | 164.27 | 62.86 | 2.61x |
| MiMo-V2.6-Pro | 64 | 672 | 231.89 | 80.75 | 2.87x |
| MiMo-V2.6-Pro | 256 | 672 | 291.68 | 94.44 | 3.09x |
| MiMo-V2.6-Pro | 1024 | 672 | 292.67 | 94.67 | 3.09x |
| MiMo-V2.6-Pro | 4096 | 672 | 292.67 | 94.67 | 3.09x |
| MiMo-V2.6-Pro | 1 | 3805 | 7.99 | 7.94 | 1.01x |
| MiMo-V2.6-Pro | 2 | 3805 | 15.80 | 15.37 | 1.03x |
| MiMo-V2.6-Pro | 4 | 3805 | 30.89 | 27.82 | 1.11x |
| MiMo-V2.6-Pro | 8 | 3805 | 59.07 | 43.55 | 1.36x |
| MiMo-V2.6-Pro | 16 | 3805 | 108.26 | 61.00 | 1.77x |
| MiMo-V2.6-Pro | 32 | 3805 | 183.67 | 91.38 | 2.01x |
| MiMo-V2.6-Pro | 64 | 3805 | 273.88 | 127.80 | 2.14x |
| MiMo-V2.6-Pro | 256 | 3805 | 363.72 | 155.28 | 2.34x |
| MiMo-V2.6-Pro | 1024 | 3805 | 365.30 | 155.69 | 2.35x |
| MiMo-V2.6-Pro | 4096 | 3805 | 365.30 | 155.69 | 2.35x |

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
| gpu | MiMo-V2.6-Pro | 1 | 1,366.30 | 31.0% |
| rom | MiMo-V2.6-Pro | 1 | 150.59 | 68.3% |

### 4. KV access granularity, which is a layout choice

`workload.kv_traffic` counts the bytes the algorithm needs. A memory
moves whole granules, and for a sparse-index model most of the KV
read is a scan of entries far smaller than one granule. Whether that
costs anything is a **layout** decision, so it is stated as one.

| Model | KV store | Layout | Granule | Inflation |
|---|---|---|---:|---:|
| MiMo-V2.6-Pro | sram | interleaved | 128 B | 1.00x |
| MiMo-V2.6-Pro | hbm | interleaved | 32 B | 1.00x |

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
| MiMo-V2.6-Pro | 1 | 67 | 87.33% | 542.63 | 9.27 |
| MiMo-V2.6-Pro | 2 | 2 | 12.14% | 128.37 | 9.27 |
| MiMo-V2.6-Pro | 4 | 2 | 12.14% | 128.37 | 9.27 |
| MiMo-V2.6-Pro | 8 | 2 | 12.14% | 128.37 | 9.27 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 256 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 1024 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 24.3 | 93,648.9 |
| MiMo-V2.6-Pro | 4096 | 2.21% | 40.0 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 22.9 | 93,666.2 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | infeasible | 109 |
| gpu | kv_read | 15 |
| gpu | link_latency | 364 |
| gpu | weight_read | 392 |
| rom | compute | 18 |
| rom | infeasible | 2142 |
| rom | kv_read | 99 |
| rom | layer_fixed_latency | 118 |
| rom | link_latency | 122 |
| rom | weight_read | 81 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 109 |
| rom | CAPACITY | 2142 |

## Mechanical consistency audit

**FAIL** over 43,841 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x136', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x153', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x180', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x183', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x244', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x366', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x136', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x153', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x180', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x183', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x244', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x366', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x136', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x153', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x180', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x183', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x244', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x366', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x136', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x153', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x180', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x183', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x244', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x366', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x136', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x153', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x180', 'MiMo-V2.6-Pro', 1)

- Generated arithmetic identities, area-accounting identities and the ROM full-array sweep floor only.
- A passing audit is not evidence for ROM macro timing, array read bandwidth at a leading node, NoC timing, package, power delivery, yield, or model accuracy.
- The two validation gates are reported separately and are the only checks against a shipping part.

## Evidence ledger

| Grade | Inputs |
|---|---:|
| measured | 4 |
| published | 75 |
| derived | 50 |
| assumed | 85 |

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
- `links.rom_wafer_express.fabric`
- `links.rom_wafer_express.hop_latency_s`
- `links.rom_wafer_express.router_latency_s`
- `links.rom_wafer_express.wire_clock_hz`
- `links.rom_wafer_express.wire_layers`
- `links.rom_wafer_express.wire_track_pitch_um`
- `links.rom_wafer_express.wire_track_share`
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
- `serial_latency.hardware_links.rom_wafer_express`
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
