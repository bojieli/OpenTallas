# Area-constrained roofline: n6_vs_a100-kimi-k3

> CANDIDATE MODEL under n6_vs_a100: Kimi-K3 at 200,000 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 617x (ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream, 1,248 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 167 devices. On the GPU side the correction reaches 257x (a100_sxm_80gb-x1231-pipeline, 1,231 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 168 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. Kimi-K3 takes 386 x 815 mm2 (314,590 mm2, array, KV in SRAM) at 2,212 tok/s per user and 7 tok/s per 1,000 mm2, holding 1 session, against 381 copies of one unified HBM die at the same silicon: 6.7x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is Kimi-K3 on 325,185 mm2 of ROM silicon at 2,251 tok/s per user against 325,444 mm2 of a100_sxm_80gb-x394-tensor at 331 tok/s: **6.8x**, ROM binding on `link_latency` and the GPU on `link_latency`. It holds 1 resident session against the GPU cluster's 8,340. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 29.68x to it.** At 1,016,950 mm2 on Kimi-K3 the pipeline-only GPU delivers 11.71 tok/s and the same silicon running tensor delivers 347 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.06x (Kimi-K3, ROM binding on `link_latency`) to 0.71x (Kimi-K3, ROM binding on `kv_read`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** Kimi-K3 engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 23 to 8,657 tok/s, and its rate with every slot occupied from 8,651 to 8,657. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 374 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,782 us over NVLink, capping per-user decode at 360 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 523.0 us and cap it at 1,912 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 8 of 10 operating points and an array 2; on tokens per second per square millimetre the same points go 5 to the array and 5 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 103 of 1646 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 3.3x of aggregate throughput (Kimi-K3). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 3.24x, on Kimi-K3 at batch 4096, where the busiest region carries 3.43x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 10 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
14. **Every number here is conditional on the assumed inputs listed in the evidence ledger below.** The ROM cell-area ratio and the ROM read bandwidth density are the two that move the answer most, and neither has been measured at N6.
15. **No point in this study is power-limited.** Static power is charged per mm2 per second, so this is a statement about the designs rather than an artifact of a traffic-proportional energy model: the worst point here reaches 89% of its cooling budget. The companion study at the other node does have power-limited points.


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

### Kimi-K3 at 200,000 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x386`** -- 386 x 815 mm2 reticle dies, 314,590 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **2,211.7 tok/s per user** (0.45 ms/token), binding on `link_latency`
- **7.0 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 2,212 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 19,523 W at 0.062 W/mm2, 8,827.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 381 copies of one unified HBM die -- `a100_sxm_80gb-x381-tensor`, 314,706 mm2, area ratio 0.9996 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 314,590 | 314,706 | 0.9996 |
| user tok/s | 2,211.7 | 330.2 | 6.70x |
| aggregate tok/s | 2,212 | 330 | 0.50x |
| resident sessions | 1 | 8,049 | -- |
| J/token | 8.8272 | 181.7398 | 20.6x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 8,049 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x224-tensor` at 185,024 mm2 and 412.4 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-SRAMKV-array-hw-tensor-x386` | 314,590 | 2,211.7 | 7.0 | 1 | 6.70x |
| rank on per-user rate alone | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 2,250.7 | 6.9 | 1 | 6.80x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x340` | 277,100 | 1,756.4 | 6.3 | 1 | 5.37x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x386` | 314,590 | 2,211.7 | 7.0 | 1 | 6.70x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x386` | 314,590 | 2,211.7 | 7.0 | -- | 7.0 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x398` | 324,370 | 2,248.1 | 6.9 | 3.7 | 7.0 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 2,250.7 | 6.9 | 3.7 | 7.0 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x386` **<-- recommended** | 314,590 | 386 | 2,211.7 | 2,212 | 7.0 | 1 | `link_latency` | 19,523 | 8,827.2 | `a100_sxm_80gb-x381-tensor` | 6.70x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x398` | 324,370 | 398 | 2,248.1 | 2,248 | 6.9 | 1 | `link_latency` | 20,262 | 9,013.0 | `a100_sxm_80gb-x393-tensor` | 6.79x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 399 | 2,250.7 | 2,251 | 6.9 | 1 | `link_latency` | 20,381 | 9,055.4 | `a100_sxm_80gb-x394-tensor` | 6.80x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 96 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x386` | 314,590 | 2,211.7 | 7.0 | 1 |
| array | 96 | fastest | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 2,250.7 | 6.9 | 1 |
| array | 96 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x340` | 277,100 | 1,756.4 | 6.3 | 1 |
| wafer | 30 | densest | `ROM-N6-native-SRAMKV-wafer-tensor-x6` | 277,350 | 1,587.9 | 5.7 | 1 |
| wafer | 30 | fastest | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | 369,800 | 2,034.9 | 5.5 | 1 |
| wafer | 30 | smallest | `ROM-N6-native-SRAMKV-wafer-tensor-x6` | 277,350 | 1,587.9 | 5.7 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-SRAMKV-array-hw-tensor-x399` | 325,185 | 2,250.7 | 2,251 | 1 | 20,381 | 9,055.4 | `link_latency` | `a100_sxm_80gb-x394-tensor` | 331.0 | 8,340 | 187,019.4 | 0.999 | 6.80x | 20.7x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-tensor-x8` | 369,800 | 2,034.9 | 2,035 | 1 | 26,828 | 13,184.1 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 333.8 | 9,549 | 208,933.4 | 0.999 | 6.10x | 15.8x |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | 1,874.4 | 3,749 | 8,937 | 27,594 | 7,360.5 | `link_latency` | `a100_sxm_80gb-x394-tensor` | 293.9 | 8,340 | 106,073.4 | 0.999 | 6.38x | 14.4x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x22` | 1,016,950 | 1,737.7 | 3,475 | 4,238 | 124,837 | 35,919.5 | `link_latency` | `a100_sxm_80gb-x1231-tensor` | 309.2 | 27,089 | 296,688.9 | 1.000 | 5.62x | 8.3x |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | 1,498.7 | 5,995 | 8,937 | 28,570 | 4,765.9 | `link_latency` | `a100_sxm_80gb-x394-tensor` | 240.2 | 8,340 | 65,535.4 | 0.999 | 6.24x | 13.8x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-tensor-x22` | 1,016,950 | 1,662.6 | 6,651 | 4,238 | 126,234 | 18,981.0 | `link_latency` | `a100_sxm_80gb-x1231-tensor` | 253.5 | 27,089 | 181,585.0 | 1.000 | 6.56x | 9.6x |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | 1,069.8 | 8,558 | 8,937 | 29,684 | 3,468.4 | `compute` | `a100_sxm_80gb-x394-tensor` | 176.1 | 8,340 | 45,141.7 | 0.999 | 6.07x | 13.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | 1,548.3 | 34,063 | 4,238 | 139,445 | 10,425.6 | `link_latency` | `a100_sxm_80gb-x1231-tensor` | 186.5 | 27,089 | 123,908.4 | 1.000 | 8.30x | 11.9x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | 680.4 | 10,886 | 8,937 | 30,690 | 2,819.3 | `compute` | `a100_sxm_80gb-x394-tensor` | 115.3 | 8,340 | 34,715.3 | 0.999 | 5.90x | 12.3x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | 1,548.3 | 34,063 | 4,238 | 139,445 | 5,450.6 | `link_latency` | `a100_sxm_80gb-x1231-tensor` | 122.1 | 27,089 | 94,840.5 | 1.000 | 12.68x | 17.4x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | 393.7 | 12,599 | 8,937 | 31,424 | 2,494.1 | `compute` | `a100_sxm_80gb-x394-hybrid` | 83.9 | 8,340 | 36,339.6 | 0.999 | 4.69x | 11.7x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | 1,310.4 | 41,932 | 4,238 | 142,735 | 3,403.9 | `link_latency` | `a100_sxm_80gb-x1231-hybrid` | 84.2 | 27,089 | 81,110.6 | 1.000 | 15.56x | 22.3x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | 213.7 | 13,675 | 8,937 | 31,872 | 2,330.6 | `compute` | `a100_sxm_80gb-x394-hybrid` | 79.6 | 8,340 | 23,756.2 | 0.999 | 2.68x | 7.4x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | 878.4 | 56,220 | 4,238 | 148,704 | 2,645.0 | `kv_read` | `a100_sxm_80gb-x1231-hybrid` | 84.2 | 27,089 | 48,133.3 | 1.000 | 10.43x | 15.6x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x399` | 325,185 | 63.9 | 16,350 | 8,937 | 33,307 | 2,037.1 | `compute` | `a100_sxm_80gb-x394-expert` | 50.0 | 6,680 | 5,834.8 | 0.999 | 1.28x | 2.9x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | 295.0 | 75,520 | 4,238 | 156,729 | 2,075.3 | `kv_read` | `a100_sxm_80gb-x1231-hybrid` | 74.7 | 27,089 | 19,777.7 | 1.000 | 3.95x | 5.8x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 325,185 | 16.0 | 16,391 | 8,937 | 33,324 | 2,033.1 | `compute` | `a100_sxm_80gb-x394-expert` | 35.6 | 6,680 | 2,475.7 | 0.999 | 0.45x | 1.2x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | 80.7 | 82,609 | 4,238 | 159,539 | 1,931.2 | `kv_read` | `a100_sxm_80gb-x1231-expert` | 56.1 | 21,832 | 4,012.3 | 1.000 | 1.44x | 2.1x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x399` | 325,185 | 4.0 | 16,397 | 8,937 | 33,154 | 2,022.0 | `compute` | `a100_sxm_80gb-x394-expert` | 9.7 | 6,680 | 2,232.5 | 0.999 | 0.41x | 1.1x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 1,016,950 | 20.8 | 85,225 | 4,238 | 161,722 | 1,897.6 | `kv_read` | `a100_sxm_80gb-x1231-expert` | 29.4 | 21,832 | 2,271.9 | 1.000 | 0.71x | 1.2x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x386` | 314,590 | array | SRAM | 1 |
| 2-16 | `ROM-N6-native-HBMKV-array-hw-tensor-x399` | 325,185 | array | HBM | 8,937 |
| 32-1024 | `ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1,016,950 | wafer | HBM | 4,238 |
| 4096 | `ROM-N6-native-HBMKV-wafer-pipeline-x22` | 1,016,950 | wafer | HBM | 4,238 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| Kimi-K3 | HBM | rom | 374, 393, 399 |
| Kimi-K3 | HBM | sram | 374, 393, 399 |
| Kimi-K3 | SRAM | rom | 340, 353, 386, 398, 399 |
| Kimi-K3 | SRAM | sram | 340, 353, 386, 398, 399 |

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

- **0 of 1,646 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 89% of its cooling budget, and the busiest wafer-scale ROM design 32%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | wafer (>=40,000 mm2) | 734 | 0 | 76.0% | 88.7% | 0.430 | 47% |
| rom | wafer (>=40,000 mm2) | 912 | 0 | 19.4% | 66.5% | 0.333 | 83% |

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
| Kimi-K3 | 1 | 314,590 | `Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x386` | 8.827172 | 19,523.2 | link_latency | `Kimi-K3/a100_sxm_80gb-x381-tensor` | 181.739797 | 60,015.2 | link_latency | 20.59x |
| Kimi-K3 | 2 | 320,295 | `Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x393` | 7.344399 | 26,751.7 | link_latency | `Kimi-K3/a100_sxm_80gb-x388-tensor` | 104.705164 | 61,475.3 | link_latency | 14.26x |
| Kimi-K3 | 4 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x22` | 18.981040 | 126,233.9 | link_latency | `Kimi-K3/a100_sxm_80gb-x1231-tensor` | 181.585026 | 184,147.1 | link_latency | 9.57x |
| Kimi-K3 | 8 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22` | 10.425553 | 139,444.7 | link_latency | `Kimi-K3/a100_sxm_80gb-x1231-tensor` | 123.908358 | 184,850.8 | link_latency | 11.89x |
| Kimi-K3 | 16 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22` | 5.450582 | 139,444.7 | link_latency | `Kimi-K3/a100_sxm_80gb-x1231-tensor` | 94.840533 | 185,292.1 | link_latency | 17.40x |
| Kimi-K3 | 32 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22` | 3.403923 | 142,734.7 | link_latency | `Kimi-K3/a100_sxm_80gb-x1231-hybrid` | 81.110625 | 374,293.1 | weight_read | 22.30x |
| Kimi-K3 | 64 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22` | 2.645023 | 148,704.2 | kv_read | `Kimi-K3/a100_sxm_80gb-x1231-hybrid` | 48.133303 | 374,293.1 | weight_read | 15.57x |
| Kimi-K3 | 256 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22` | 2.075342 | 156,729.1 | kv_read | `Kimi-K3/a100_sxm_80gb-x1231-hybrid` | 19.777749 | 378,257.1 | weight_read | 5.77x |
| Kimi-K3 | 1024 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22` | 1.931248 | 159,538.8 | kv_read | `Kimi-K3/a100_sxm_80gb-x1231-expert` | 4.012307 | 230,378.3 | weight_read | 2.08x |
| Kimi-K3 | 4096 | 1,016,950 | `Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22` | 1.897596 | 161,722.2 | kv_read | `Kimi-K3/a100_sxm_80gb-x1231-expert` | 2.271885 | 273,764.0 | compute | 1.20x |

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
| Kimi-K3 | 200,000 | 2,800 B | 1,560.9 GB | 4.46 | 3.214 GB | 3.214 GB | 42.6 |

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
| Kimi-K3 | 6 | 277,350 | 4,994.3 | wafer-pipeline | 1,587.9 | wafer-tensor | 3.15x | 1,937.2 | pipeline | 327.1 | tensor | 5.92x | 2.58x | 4.85x | 1.88x |
| Kimi-K3 | 8 | 369,800 | 16,167.9 | wafer-pipeline | 2,034.9 | wafer-tensor | 7.95x | 2,208.3 | pipeline | 333.8 | tensor | 6.62x | 7.32x | 6.10x | 0.83x |
| Kimi-K3 | 12 | 554,700 | 19,623.2 | wafer-pipeline | 1,917.5 | wafer-tensor | 10.23x | 2,567.5 | pipeline | 340.8 | tensor | 7.53x | 7.64x | 5.63x | 0.74x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.74x to 1.88x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| Kimi-K3 | 1 | fastest | Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x399 | 325,185 | 2,250.7 | 2,250.7 | link_latency | Kimi-K3/a100_sxm_80gb-x394-tensor | 325,444 | 1.00x | tensor | 2,777.23 | 331.0 | 331.0 | link_latency | 6.80x | 0.49x | 192.26x | 6.80x |
| Kimi-K3 | 1 | smallest silicon | Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x340 | 277,100 | 1,756.4 | 1,756.4 | link_latency | Kimi-K3/a100_sxm_80gb-x335-tensor | 276,710 | 1.00x | tensor | 2,776.01 | 327.0 | 327.0 | link_latency | 5.37x | 0.45x | 150.04x | 5.37x |
| Kimi-K3 | 2 | fastest | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x399 | 325,185 | 1,874.4 | 3,748.9 | link_latency | Kimi-K3/a100_sxm_80gb-x394-tensor | 325,444 | 1.00x | tensor | 3,114.14 | 293.9 | 587.8 | link_latency | 6.38x | 0.81x | 160.12x | 6.38x |
| Kimi-K3 | 2 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x374 | 304,810 | 1,556.3 | 3,112.6 | link_latency | Kimi-K3/a100_sxm_80gb-x369-tensor | 304,794 | 1.00x | tensor | 3,113.33 | 292.4 | 584.9 | link_latency | 5.32x | 0.72x | 132.95x | 5.32x |
| Kimi-K3 | 4 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x22 | 1,016,950 | 1,662.6 | 6,650.5 | link_latency | Kimi-K3/a100_sxm_80gb-x1231-tensor | 1,016,806 | 1.00x | tensor | 3,805.25 | 253.5 | 1,014.1 | link_latency | 6.56x | 0.46x | 142.03x | 6.56x |
| Kimi-K3 | 4 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x374 | 304,810 | 1,129.5 | 4,518.0 | compute | Kimi-K3/a100_sxm_80gb-x369-tensor | 304,794 | 1.00x | tensor | 3,786.33 | 238.9 | 955.7 | link_latency | 4.73x | 1.05x | 96.49x | 4.73x |
| Kimi-K3 | 8 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 1,548.3 | 34,062.6 | link_latency | Kimi-K3/a100_sxm_80gb-x1231-tensor | 1,016,806 | 1.00x | tensor | 5,170.19 | 186.5 | 1,491.8 | link_latency | 8.30x | 2.36x | 132.26x | 8.30x |
| Kimi-K3 | 8 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x374 | 304,810 | 729.4 | 5,835.3 | compute | Kimi-K3/a100_sxm_80gb-x369-tensor | 304,794 | 1.00x | tensor | 5,132.35 | 175.2 | 1,401.3 | link_latency | 4.16x | 1.35x | 62.31x | 4.16x |
| Kimi-K3 | 16 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 1,548.3 | 34,062.6 | link_latency | Kimi-K3/a100_sxm_80gb-x1231-tensor | 1,016,806 | 1.00x | tensor | 7,900.06 | 122.1 | 1,953.7 | link_latency | 12.68x | 2.36x | 132.26x | 12.68x |
| Kimi-K3 | 16 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x374 | 304,810 | 426.9 | 6,831.2 | compute | Kimi-K3/a100_sxm_80gb-x369-tensor | 304,794 | 1.00x | tensor | 7,824.37 | 114.6 | 1,833.8 | link_latency | 3.73x | 1.58x | 36.47x | 3.73x |
| Kimi-K3 | 32 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 1,310.4 | 41,932.4 | link_latency | Kimi-K3/a100_sxm_80gb-x1231-hybrid | 1,016,806 | 1.00x | hybrid | 1,192.85 | 84.2 | 12,968.9 | weight_read | 15.56x | 2.91x | 111.94x | 15.77x |
| Kimi-K3 | 32 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x374 | 304,810 | 233.4 | 7,468.5 | compute | Kimi-K3/a100_sxm_80gb-x369-hybrid | 304,794 | 1.00x | hybrid | 1,073.09 | 83.7 | 3,933.7 | weight_read | 2.79x | 1.73x | 19.94x | 2.79x |
| Kimi-K3 | 64 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 878.4 | 56,220.4 | kv_read | Kimi-K3/a100_sxm_80gb-x1231-hybrid | 1,016,806 | 1.00x | hybrid | 1,192.85 | 84.2 | 12,968.9 | weight_read | 10.43x | 3.90x | 75.04x | 10.57x |
| Kimi-K3 | 64 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x374 | 304,810 | 122.4 | 7,833.9 | compute | Kimi-K3/a100_sxm_80gb-x369-hybrid | 304,794 | 1.00x | hybrid | 1,091.07 | 78.2 | 5,007.8 | weight_read | 1.56x | 1.56x | 10.46x | 1.56x |
| Kimi-K3 | 256 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 295.0 | 75,519.6 | kv_read | Kimi-K3/a100_sxm_80gb-x1231-hybrid | 1,016,806 | 1.00x | hybrid | 1,243.24 | 74.7 | 19,125.4 | weight_read | 3.95x | 3.95x | 25.20x | 4.00x |
| Kimi-K3 | 256 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-hybrid-x374 | 304,810 | 33.8 | 8,643.8 | compute | Kimi-K3/a100_sxm_80gb-x369-expert | 304,794 | 1.00x | expert | 2,621.38 | 48.9 | 12,518.3 | weight_read | 0.69x | 0.69x | 2.88x | 0.69x |
| Kimi-K3 | 1024 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 80.7 | 82,609.2 | kv_read | Kimi-K3/a100_sxm_80gb-x1231-expert | 1,016,806 | 1.00x | expert | 2,883.33 | 56.1 | 57,417.9 | weight_read | 1.44x | 1.44x | 6.89x | 1.44x |
| Kimi-K3 | 1024 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-pipeline-x374 | 304,810 | 8.5 | 8,655.1 | compute | Kimi-K3/a100_sxm_80gb-x369-expert | 304,794 | 1.00x | expert | 6,562.78 | 34.4 | 35,244.0 | compute | 0.25x | 0.25x | 0.98x | 0.25x |
| Kimi-K3 | 4096 | fastest | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 20.8 | 85,224.7 | kv_read | Kimi-K3/a100_sxm_80gb-x1231-expert | 1,016,806 | 1.00x | expert | 7,610.56 | 29.4 | 120,500.8 | compute | 0.71x | 0.71x | 2.62x | 0.71x |
| Kimi-K3 | 4096 | smallest silicon | Kimi-K3/ROM-N6-native-HBMKV-array-hw-pipeline-x374 | 304,810 | 2.1 | 8,656.8 | compute | Kimi-K3/a100_sxm_80gb-x369-expert | 304,794 | 1.00x | expert | 22,328.38 | 9.1 | 37,144.7 | compute | 0.23x | 0.23x | 0.53x | 0.23x |

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
| Kimi-K3 | 56 | 46,256 | 11.7 | 283.2 | 85.9 | tensor | 1,982.76 | 56.1% | link_latency |
| Kimi-K3 | 112 | 92,512 | 11.7 | 357.9 | 85.8 | tensor | 2,005.62 | 71.8% | link_latency |
| Kimi-K3 | 165 | 136,290 | 11.7 | 391.1 | 84.2 | tensor | 2,013.23 | 78.7% | link_latency |
| Kimi-K3 | 168 | 138,768 | 11.7 | 392.5 | 85.6 | tensor | 2,013.23 | 79.0% | link_latency |
| Kimi-K3 | 181 | 149,506 | 11.7 | 398.0 | 84.3 | tensor | 2,014.56 | 80.2% | link_latency |
| Kimi-K3 | 205 | 169,330 | 11.7 | 406.6 | 84.4 | tensor | 2,016.16 | 82.0% | link_latency |
| Kimi-K3 | 224 | 185,024 | 11.7 | 412.4 | 85.5 | tensor | 2,017.04 | 83.2% | link_latency |
| Kimi-K3 | 335 | 276,710 | 11.7 | 327.0 | 85.0 | tensor | 2,776.01 | 90.8% | link_latency |
| Kimi-K3 | 336 | 277,536 | 11.7 | 327.1 | 85.2 | tensor | 2,776.01 | 90.8% | link_latency |
| Kimi-K3 | 348 | 287,448 | 11.7 | 328.0 | 84.3 | tensor | 2,776.36 | 91.1% | link_latency |
| Kimi-K3 | 369 | 304,794 | 11.7 | 329.5 | 83.7 | tensor | 2,776.82 | 91.5% | link_latency |
| Kimi-K3 | 381 | 314,706 | 11.7 | 330.2 | 84.5 | tensor | 2,776.97 | 91.7% | link_latency |
| Kimi-K3 | 388 | 320,488 | 11.7 | 330.7 | 84.3 | tensor | 2,777.10 | 91.8% | link_latency |
| Kimi-K3 | 393 | 324,618 | 11.7 | 330.9 | 83.7 | tensor | 2,777.23 | 91.9% | link_latency |
| Kimi-K3 | 394 | 325,444 | 11.7 | 331.0 | 83.9 | tensor | 2,777.23 | 91.9% | link_latency |
| Kimi-K3 | 448 | 370,048 | 11.7 | 333.8 | 85.0 | tensor | 2,777.92 | 92.7% | link_latency |
| Kimi-K3 | 560 | 462,560 | 11.7 | 338.0 | 84.7 | tensor | 2,779.06 | 93.9% | link_latency |
| Kimi-K3 | 672 | 555,072 | 11.7 | 340.8 | 84.4 | tensor | 2,779.82 | 94.7% | link_latency |
| Kimi-K3 | 1231 | 1,016,806 | 11.7 | 347.4 | 84.2 | tensor | 2,781.55 | 96.6% | link_latency |

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
| Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x386 | Kimi-K3 | 386 | tensor | rom_package_ucie | rom_board_serdes | 372 | 377.90 us | 264.6 tok/s | 2,646.2 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 97 on rom_board_serdes (traversals 19.8) = 372.68 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x399 | Kimi-K3 | 399 | hybrid | rom_package_ucie | rom_board_serdes | 278 | 15.15 us | 6,599.5 tok/s | 65,995.1 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 92 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 9.93 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x399 | Kimi-K3 | 399 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x10 | Kimi-K3 | 10 | pipeline | on_wafer | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x353 | Kimi-K3 | 353 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.52 us | 36.0 tok/s | 360.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 45 on infiniband_hdr (traversals 4.0) = 1,823.19 us |
| Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x8 | Kimi-K3 | 8 | tensor | on_wafer | rom_wafer_serdes | 372 | 441.06 us | 226.7 tok/s | 2,267.3 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 186 x all_reduce span 8 on rom_wafer_serdes (traversals 4.4) = 83.01 us |
| Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x398 | Kimi-K3 | 398 | hybrid | nvlink3 | infiniband_hdr | 235 | 1,080.90 us | 92.5 tok/s | 925.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 49 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 127.57 us |
| Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x10 | Kimi-K3 | 10 | hybrid | on_wafer | rom_wafer_serdes | 195 | 358.97 us | 278.6 tok/s | 2,785.7 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 9 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.92 us |
| Kimi-K3/ROM-N6-native-HBMKV-array-hw-pipeline-x399 | Kimi-K3 | 399 | pipeline | rom_package_ucie | rom_board_serdes | 92 | 3.42 us | 29,235.7 tok/s | 292,356.8 tok/s | 69 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.94 us; 23 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 2.48 us |
| Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x393 | Kimi-K3 | 393 | tensor | rom_package_ucie | rom_board_serdes | 372 | 377.90 us | 264.6 tok/s | 2,646.2 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 186 x all_reduce span 99 on rom_board_serdes (traversals 19.8) = 372.68 us |
| Kimi-K3/ROM-N6-native-HBMKV-array-hw-hybrid-x399 | Kimi-K3 | 399 | hybrid | rom_package_ucie | rom_board_serdes | 278 | 15.15 us | 6,599.5 tok/s | 65,995.1 tok/s | 186 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 5.22 us; 92 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 9.93 us |
| Kimi-K3/ROM-N6-native-HBMKV-array-pipeline-x399 | Kimi-K3 | 399 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | Kimi-K3 | 22 | pipeline | on_wafer | rom_wafer_serdes | 92 | 11.48 us | 8,712.7 tok/s | 87,127.5 tok/s | 91 x point_to_point span 2 on on_wafer (traversals 1.0) = 11.38 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| Kimi-K3/ROM-N6-native-HBMKV-array-tensor-x374 | Kimi-K3 | 374 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.82 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,823.49 us |
| Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x22 | Kimi-K3 | 22 | tensor | on_wafer | rom_wafer_serdes | 372 | 523.00 us | 191.2 tok/s | 1,912.0 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 186 x all_reduce span 22 on rom_wafer_serdes (traversals 8.8) = 164.95 us |
| Kimi-K3/ROM-N6-native-HBMKV-array-hybrid-x399 | Kimi-K3 | 399 | hybrid | nvlink3 | infiniband_hdr | 235 | 1,080.90 us | 92.5 tok/s | 925.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 49 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 127.57 us |
| Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | Kimi-K3 | 22 | hybrid | on_wafer | rom_wafer_serdes | 207 | 360.20 us | 277.6 tok/s | 2,776.2 tok/s | 186 x all_reduce span 57 on on_wafer (traversals 15.4) = 358.05 us; 21 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 2.15 us |
| Kimi-K3/a100_sxm_80gb-x56-pipeline | Kimi-K3 | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 140.46 us | 711.9 tok/s | 7,119.4 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.84 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| Kimi-K3/a100_sxm_80gb-x56-tensor | Kimi-K3 | 56 | tensor | nvlink3 | infiniband_hdr | 372 | 1,982.76 us | 50.4 tok/s | 504.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 1,029.43 us |
| Kimi-K3/a100_sxm_80gb-x56-hybrid | Kimi-K3 | 56 | hybrid | nvlink3 | infiniband_hdr | 192 | 968.95 us | 103.2 tok/s | 1,032.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.62 us |
| Kimi-K3/a100_sxm_80gb-x56-expert | Kimi-K3 | 56 | expert | nvlink3 | infiniband_hdr | 372 | 1,341.39 us | 74.5 tok/s | 745.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 933.33 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 408.05 us |
| Kimi-K3/a100_sxm_80gb-x112-pipeline | Kimi-K3 | 112 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x112-tensor | Kimi-K3 | 112 | tensor | nvlink3 | infiniband_hdr | 372 | 2,005.62 us | 49.9 tok/s | 498.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 1,052.28 us |
| Kimi-K3/a100_sxm_80gb-x112-hybrid | Kimi-K3 | 112 | hybrid | nvlink3 | infiniband_hdr | 199 | 987.18 us | 101.3 tok/s | 1,013.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 33.84 us |
| Kimi-K3/a100_sxm_80gb-x112-expert | Kimi-K3 | 112 | expert | nvlink3 | infiniband_hdr | 372 | 1,324.48 us | 75.5 tok/s | 755.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.67 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 392.82 us |
| Kimi-K3/a100_sxm_80gb-x165-pipeline | Kimi-K3 | 165 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x165-tensor | Kimi-K3 | 165 | tensor | nvlink3 | infiniband_hdr | 372 | 2,013.23 us | 49.7 tok/s | 496.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 1,059.90 us |
| Kimi-K3/a100_sxm_80gb-x165-hybrid | Kimi-K3 | 165 | hybrid | nvlink3 | infiniband_hdr | 206 | 1,005.40 us | 99.5 tok/s | 994.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| Kimi-K3/a100_sxm_80gb-x165-expert | Kimi-K3 | 165 | expert | nvlink3 | infiniband_hdr | 372 | 1,319.09 us | 75.8 tok/s | 758.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.17 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 387.92 us |
| Kimi-K3/a100_sxm_80gb-x168-pipeline | Kimi-K3 | 168 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x168-tensor | Kimi-K3 | 168 | tensor | nvlink3 | infiniband_hdr | 372 | 2,013.23 us | 49.7 tok/s | 496.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 1,059.90 us |
| Kimi-K3/a100_sxm_80gb-x168-hybrid | Kimi-K3 | 168 | hybrid | nvlink3 | infiniband_hdr | 206 | 1,005.40 us | 99.5 tok/s | 994.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.07 us |
| Kimi-K3/a100_sxm_80gb-x168-expert | Kimi-K3 | 168 | expert | nvlink3 | infiniband_hdr | 372 | 1,318.85 us | 75.8 tok/s | 758.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.11 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 387.74 us |
| Kimi-K3/a100_sxm_80gb-x181-pipeline | Kimi-K3 | 181 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x181-tensor | Kimi-K3 | 181 | tensor | nvlink3 | infiniband_hdr | 372 | 2,014.56 us | 49.6 tok/s | 496.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 1,061.23 us |
| Kimi-K3/a100_sxm_80gb-x181-hybrid | Kimi-K3 | 181 | hybrid | nvlink3 | infiniband_hdr | 208 | 1,010.61 us | 99.0 tok/s | 989.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.28 us |
| Kimi-K3/a100_sxm_80gb-x181-expert | Kimi-K3 | 181 | expert | nvlink3 | infiniband_hdr | 372 | 1,318.07 us | 75.9 tok/s | 758.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 931.06 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 387.01 us |
| Kimi-K3/a100_sxm_80gb-x205-pipeline | Kimi-K3 | 205 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x205-tensor | Kimi-K3 | 205 | tensor | nvlink3 | infiniband_hdr | 372 | 2,016.16 us | 49.6 tok/s | 496.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 1,062.83 us |
| Kimi-K3/a100_sxm_80gb-x205-hybrid | Kimi-K3 | 205 | hybrid | nvlink3 | infiniband_hdr | 211 | 1,018.42 us | 98.2 tok/s | 981.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.09 us |
| Kimi-K3/a100_sxm_80gb-x205-expert | Kimi-K3 | 205 | expert | nvlink3 | infiniband_hdr | 372 | 1,316.84 us | 75.9 tok/s | 759.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.93 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 385.90 us |
| Kimi-K3/a100_sxm_80gb-x224-pipeline | Kimi-K3 | 224 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x224-tensor | Kimi-K3 | 224 | tensor | nvlink3 | infiniband_hdr | 372 | 2,017.04 us | 49.6 tok/s | 495.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 1,063.71 us |
| Kimi-K3/a100_sxm_80gb-x224-hybrid | Kimi-K3 | 224 | hybrid | nvlink3 | infiniband_hdr | 213 | 1,023.62 us | 97.7 tok/s | 976.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.29 us |
| Kimi-K3/a100_sxm_80gb-x224-expert | Kimi-K3 | 224 | expert | nvlink3 | infiniband_hdr | 372 | 1,316.03 us | 76.0 tok/s | 759.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.83 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 385.20 us |
| Kimi-K3/a100_sxm_80gb-x335-pipeline | Kimi-K3 | 335 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x335-tensor | Kimi-K3 | 335 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.01 us | 36.0 tok/s | 360.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,822.68 us |
| Kimi-K3/a100_sxm_80gb-x335-hybrid | Kimi-K3 | 335 | hybrid | nvlink3 | infiniband_hdr | 227 | 1,060.07 us | 94.3 tok/s | 943.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| Kimi-K3/a100_sxm_80gb-x335-expert | Kimi-K3 | 335 | expert | nvlink3 | infiniband_hdr | 372 | 1,313.24 us | 76.1 tok/s | 761.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.57 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.67 us |
| Kimi-K3/a100_sxm_80gb-x336-pipeline | Kimi-K3 | 336 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x336-tensor | Kimi-K3 | 336 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.01 us | 36.0 tok/s | 360.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,822.68 us |
| Kimi-K3/a100_sxm_80gb-x336-hybrid | Kimi-K3 | 336 | hybrid | nvlink3 | infiniband_hdr | 227 | 1,060.07 us | 94.3 tok/s | 943.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 106.74 us |
| Kimi-K3/a100_sxm_80gb-x336-expert | Kimi-K3 | 336 | expert | nvlink3 | infiniband_hdr | 372 | 1,313.21 us | 76.1 tok/s | 761.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.56 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.66 us |
| Kimi-K3/a100_sxm_80gb-x348-pipeline | Kimi-K3 | 348 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x348-tensor | Kimi-K3 | 348 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.36 us | 36.0 tok/s | 360.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 44 on infiniband_hdr (traversals 4.0) = 1,823.03 us |
| Kimi-K3/a100_sxm_80gb-x348-hybrid | Kimi-K3 | 348 | hybrid | nvlink3 | infiniband_hdr | 229 | 1,065.28 us | 93.9 tok/s | 938.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 43 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 111.95 us |
| Kimi-K3/a100_sxm_80gb-x348-expert | Kimi-K3 | 348 | expert | nvlink3 | infiniband_hdr | 372 | 1,313.03 us | 76.2 tok/s | 761.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.54 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.48 us |
| Kimi-K3/a100_sxm_80gb-x369-pipeline | Kimi-K3 | 369 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x369-tensor | Kimi-K3 | 369 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.82 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,823.49 us |
| Kimi-K3/a100_sxm_80gb-x369-hybrid | Kimi-K3 | 369 | hybrid | nvlink3 | infiniband_hdr | 232 | 1,073.09 us | 93.2 tok/s | 931.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 119.76 us |
| Kimi-K3/a100_sxm_80gb-x369-expert | Kimi-K3 | 369 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.71 us | 76.2 tok/s | 761.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.51 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.20 us |
| Kimi-K3/a100_sxm_80gb-x381-pipeline | Kimi-K3 | 381 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x381-tensor | Kimi-K3 | 381 | tensor | nvlink3 | infiniband_hdr | 372 | 2,776.97 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 48 on infiniband_hdr (traversals 4.0) = 1,823.63 us |
| Kimi-K3/a100_sxm_80gb-x381-hybrid | Kimi-K3 | 381 | hybrid | nvlink3 | infiniband_hdr | 233 | 1,075.69 us | 93.0 tok/s | 929.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 47 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 122.36 us |
| Kimi-K3/a100_sxm_80gb-x381-expert | Kimi-K3 | 381 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.56 us | 76.2 tok/s | 761.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.50 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 382.06 us |
| Kimi-K3/a100_sxm_80gb-x388-pipeline | Kimi-K3 | 388 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x388-tensor | Kimi-K3 | 388 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.10 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 49 on infiniband_hdr (traversals 4.0) = 1,823.77 us |
| Kimi-K3/a100_sxm_80gb-x388-hybrid | Kimi-K3 | 388 | hybrid | nvlink3 | infiniband_hdr | 234 | 1,078.30 us | 92.7 tok/s | 927.4 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 48 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 124.97 us |
| Kimi-K3/a100_sxm_80gb-x388-expert | Kimi-K3 | 388 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.46 us | 76.2 tok/s | 761.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.49 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.98 us |
| Kimi-K3/a100_sxm_80gb-x393-pipeline | Kimi-K3 | 393 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x393-tensor | Kimi-K3 | 393 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.23 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 50 on infiniband_hdr (traversals 4.0) = 1,823.90 us |
| Kimi-K3/a100_sxm_80gb-x393-hybrid | Kimi-K3 | 393 | hybrid | nvlink3 | infiniband_hdr | 235 | 1,080.90 us | 92.5 tok/s | 925.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 49 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 127.57 us |
| Kimi-K3/a100_sxm_80gb-x393-expert | Kimi-K3 | 393 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.40 us | 76.2 tok/s | 762.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.48 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.92 us |
| Kimi-K3/a100_sxm_80gb-x394-pipeline | Kimi-K3 | 394 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x394-tensor | Kimi-K3 | 394 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.23 us | 36.0 tok/s | 360.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 50 on infiniband_hdr (traversals 4.0) = 1,823.90 us |
| Kimi-K3/a100_sxm_80gb-x394-hybrid | Kimi-K3 | 394 | hybrid | nvlink3 | infiniband_hdr | 235 | 1,080.90 us | 92.5 tok/s | 925.2 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 49 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 127.57 us |
| Kimi-K3/a100_sxm_80gb-x394-expert | Kimi-K3 | 394 | expert | nvlink3 | infiniband_hdr | 372 | 1,312.39 us | 76.2 tok/s | 762.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.48 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.91 us |
| Kimi-K3/a100_sxm_80gb-x448-pipeline | Kimi-K3 | 448 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x448-tensor | Kimi-K3 | 448 | tensor | nvlink3 | infiniband_hdr | 372 | 2,777.92 us | 36.0 tok/s | 360.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,824.59 us |
| Kimi-K3/a100_sxm_80gb-x448-hybrid | Kimi-K3 | 448 | hybrid | nvlink3 | infiniband_hdr | 241 | 1,096.52 us | 91.2 tok/s | 912.0 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 143.19 us |
| Kimi-K3/a100_sxm_80gb-x448-expert | Kimi-K3 | 448 | expert | nvlink3 | infiniband_hdr | 372 | 1,311.81 us | 76.2 tok/s | 762.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.42 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 381.39 us |
| Kimi-K3/a100_sxm_80gb-x560-pipeline | Kimi-K3 | 560 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x560-tensor | Kimi-K3 | 560 | tensor | nvlink3 | infiniband_hdr | 372 | 2,779.06 us | 36.0 tok/s | 359.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 70 on infiniband_hdr (traversals 4.0) = 1,825.73 us |
| Kimi-K3/a100_sxm_80gb-x560-hybrid | Kimi-K3 | 560 | hybrid | nvlink3 | infiniband_hdr | 255 | 1,132.97 us | 88.3 tok/s | 882.6 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 179.64 us |
| Kimi-K3/a100_sxm_80gb-x560-expert | Kimi-K3 | 560 | expert | nvlink3 | infiniband_hdr | 372 | 1,310.96 us | 76.3 tok/s | 762.8 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.33 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 380.63 us |
| Kimi-K3/a100_sxm_80gb-x672-pipeline | Kimi-K3 | 672 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x672-tensor | Kimi-K3 | 672 | tensor | nvlink3 | infiniband_hdr | 372 | 2,779.82 us | 36.0 tok/s | 359.7 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,826.49 us |
| Kimi-K3/a100_sxm_80gb-x672-hybrid | Kimi-K3 | 672 | hybrid | nvlink3 | infiniband_hdr | 269 | 1,169.42 us | 85.5 tok/s | 855.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 83 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 216.09 us |
| Kimi-K3/a100_sxm_80gb-x672-expert | Kimi-K3 | 672 | expert | nvlink3 | infiniband_hdr | 372 | 1,310.40 us | 76.3 tok/s | 763.1 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.28 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 380.12 us |
| Kimi-K3/a100_sxm_80gb-x1231-pipeline | Kimi-K3 | 1231 | pipeline | nvlink3 | infiniband_hdr | 92 | 235.01 us | 425.5 tok/s | 4,255.2 tok/s | 81 x point_to_point span 2 on nvlink3 (traversals 1.0) = 206.37 us; 11 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 28.64 us |
| Kimi-K3/a100_sxm_80gb-x1231-tensor | Kimi-K3 | 1231 | tensor | nvlink3 | infiniband_hdr | 372 | 2,781.55 us | 36.0 tok/s | 359.5 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 186 x all_reduce span 154 on infiniband_hdr (traversals 4.0) = 1,828.22 us |
| Kimi-K3/a100_sxm_80gb-x1231-hybrid | Kimi-K3 | 1231 | hybrid | nvlink3 | infiniband_hdr | 278 | 1,192.85 us | 83.8 tok/s | 838.3 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 953.33 us; 92 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 239.52 us |
| Kimi-K3/a100_sxm_80gb-x1231-expert | Kimi-K3 | 1231 | expert | nvlink3 | infiniband_hdr | 372 | 1,309.12 us | 76.4 tok/s | 763.9 tok/s | 186 x all_reduce span 8 on nvlink3 (traversals 2.0) = 930.15 us; 186 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 378.97 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| Kimi-K3 | 1 | array | array | Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x386 | 314,590 | 2,211.7 | 0.007 | 2,211.7 (314,590) | 2,034.9 (369,800) | 0.92x | link_latency |
| Kimi-K3 | 2 | array | array | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x393 | 320,295 | 1,821.2 | 0.006 | 1,821.2 (320,295) | 1,737.7 (1,016,950) | 0.95x | link_latency |
| Kimi-K3 | 4 | wafer | array | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x22 | 1,016,950 | 1,662.6 | 0.002 | 1,431.8 (320,295) | 1,662.6 (1,016,950) | 1.16x | link_latency |
| Kimi-K3 | 8 | wafer | array | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 1,548.3 | 0.002 | 1,069.8 (325,185) | 1,548.3 (1,016,950) | 1.45x | link_latency |
| Kimi-K3 | 16 | wafer | array | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 1,548.3 | 0.002 | 680.4 (325,185) | 1,548.3 (1,016,950) | 2.28x | link_latency |
| Kimi-K3 | 32 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 1,310.4 | 0.001 | 393.7 (325,185) | 1,310.4 (1,016,950) | 3.33x | link_latency |
| Kimi-K3 | 64 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 878.4 | 0.001 | 213.7 (325,185) | 878.4 (1,016,950) | 4.11x | kv_read |
| Kimi-K3 | 256 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 295.0 | 0.000 | 63.9 (325,185) | 295.0 (1,016,950) | 4.62x | kv_read |
| Kimi-K3 | 1024 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22 | 1,016,950 | 80.7 | 0.000 | 16.0 (325,185) | 80.7 (1,016,950) | 5.04x | kv_read |
| Kimi-K3 | 4096 | wafer | wafer | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 20.8 | 0.000 | 4.0 (325,185) | 20.8 (1,016,950) | 5.20x | kv_read |

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
| Kimi-K3 | 1 | sram | 85,066.4 | 26,091.7 | 26,091.7 | 3.26x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 2 | sram | 85,066.4 | 26,091.7 | 26,091.7 | 3.26x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 4 | sram | 85,066.4 | 26,091.7 | 26,091.7 | 3.26x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 8 | sram | 85,066.4 | 26,091.7 | 26,091.7 | 3.26x | 1.00x | kv_read | weight_read | weight_read |
| Kimi-K3 | 16 | sram | 85,066.4 | 26,091.7 | 28,344.8 | 3.26x | 1.09x | kv_read | weight_read | link_latency |
| Kimi-K3 | 32 | sram | 85,066.4 | 26,091.7 | 37,559.6 | 3.26x | 1.44x | kv_read | weight_read | link_latency |
| Kimi-K3 | 64 | sram | 85,066.4 | 26,091.7 | 46,333.9 | 3.26x | 1.78x | kv_read | weight_read | kv_read |
| Kimi-K3 | 256 | sram | 85,066.4 | 26,091.7 | 75,519.6 | 3.26x | 2.89x | kv_read | weight_read | kv_read |
| Kimi-K3 | 1024 | sram | 85,066.4 | 26,091.7 | 82,609.2 | 3.26x | 3.17x | kv_read | weight_read | kv_read |
| Kimi-K3 | 4096 | sram | 85,224.7 | 26,106.6 | 84,594.5 | 3.26x | 3.24x | kv_read | weight_read | kv_read |
| Kimi-K3 | 1 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 2 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 8 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 16 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 32 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 64 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 256 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 1024 | rom | 85,066.4 | 85,066.4 | 85,066.4 | 1.00x | 1.00x | kv_read | kv_read | kv_read |
| Kimi-K3 | 4096 | rom | 85,224.7 | 85,224.7 | 85,224.7 | 1.00x | 1.00x | kv_read | kv_read | kv_read |

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
| Kimi-K3 | 1 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 1 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 1 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 2 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 2 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 2 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 2 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 2 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 4 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 4 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 8 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 8 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 8 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 8 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 8 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 16 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 16 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 16 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 16 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x183-perregion | 149,145 | 1.00 | 3.05 | 28,344.8 | 0.190 | link_latency | 0.33x |
| Kimi-K3 | 16 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 32 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 32 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 32 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 32 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-array-hw-tensor-x183-perregion | 149,145 | 1.00 | 4.10 | 37,559.6 | 0.252 | link_latency | 0.44x |
| Kimi-K3 | 32 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 64 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 64 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 64 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 64 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-tensor-x22-perregion | 1,016,950 | 1.00 | 5.73 | 46,333.9 | 0.046 | kv_read | 0.54x |
| Kimi-K3 | 64 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 256 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 256 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 256 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 256 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22-perregion | 1,016,950 | 1.00 | 2.63 | 75,519.6 | 0.074 | kv_read | 0.89x |
| Kimi-K3 | 256 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1024 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1024 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 1.00 | 26,091.7 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 1024 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 1024 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22-perregion | 1,016,950 | 1.00 | 4.89 | 82,609.2 | 0.081 | kv_read | 0.97x |
| Kimi-K3 | 1024 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.00 | 85,066.4 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22 | 1,016,950 | 1.00 | 1.00 | 85,224.7 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4096 | batched | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-romfill | 1,016,950 | 2.07 | 1.00 | 85,224.7 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_stream | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream | 1,016,950 | 1.00 | 3.28 | 26,106.6 | 0.026 | weight_read | 0.31x |
| Kimi-K3 | 4096 | per_stream | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perstream-romfill | 1,016,950 | 7.49 | 3.28 | 85,224.7 | 0.084 | kv_read | 1.00x |
| Kimi-K3 | 4096 | per_region | sram | Kimi-K3/ROM-N6-native-HBMKV-wafer-hybrid-x22-perregion | 1,016,950 | 1.00 | 10.42 | 84,594.5 | 0.083 | kv_read | 0.99x |
| Kimi-K3 | 4096 | per_region | rom | Kimi-K3/ROM-N6-native-HBMKV-wafer-pipeline-x22-perregion-romfill | 1,016,950 | 7.49 | 1.65 | 85,224.7 | 0.084 | kv_read | 1.00x |

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
| Kimi-K3 | 1 | 167 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 2 | 171 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 4 | 183 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 8 | 183 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 16 | 183 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 32 | 183 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 64 | 183 | 1.00 | 1.000 | 1.000 | 1.00x |
| Kimi-K3 | 256 | 183 | 1.40 | 1.004 | 1.099 | 1.10x |
| Kimi-K3 | 1024 | 183 | 5.60 | 1.042 | 2.041 | 1.96x |
| Kimi-K3 | 4096 | 183 | 22.38 | 1.204 | 3.460 | 2.87x |

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
| Kimi-K3 | 256 | 56 | 56.00 | 34.72 | 1.61x |
| Kimi-K3 | 1 | 112 | 14.97 | 9.58 | 1.56x |
| Kimi-K3 | 2 | 112 | 27.73 | 13.98 | 1.98x |
| Kimi-K3 | 4 | 112 | 47.95 | 19.84 | 2.42x |
| Kimi-K3 | 8 | 112 | 73.92 | 27.12 | 2.73x |
| Kimi-K3 | 16 | 112 | 97.03 | 35.27 | 2.75x |
| Kimi-K3 | 32 | 112 | 108.69 | 43.36 | 2.51x |
| Kimi-K3 | 64 | 112 | 111.54 | 50.14 | 2.22x |
| Kimi-K3 | 256 | 112 | 111.96 | 55.81 | 2.01x |
| Kimi-K3 | 1024 | 112 | 111.96 | 55.97 | 2.00x |
| Kimi-K3 | 1 | 165 | 15.29 | 10.54 | 1.45x |
| Kimi-K3 | 2 | 165 | 28.93 | 15.25 | 1.90x |
| Kimi-K3 | 4 | 165 | 52.02 | 22.58 | 2.30x |
| Kimi-K3 | 8 | 165 | 85.58 | 31.60 | 2.71x |
| Kimi-K3 | 16 | 165 | 122.83 | 42.15 | 2.91x |
| Kimi-K3 | 32 | 165 | 149.83 | 53.17 | 2.82x |
| Kimi-K3 | 64 | 165 | 161.03 | 62.72 | 2.57x |
| Kimi-K3 | 256 | 165 | 164.25 | 70.96 | 2.31x |
| Kimi-K3 | 1024 | 165 | 164.29 | 71.19 | 2.31x |
| Kimi-K3 | 1 | 168 | 15.31 | 10.59 | 1.45x |
| Kimi-K3 | 2 | 168 | 28.98 | 15.31 | 1.89x |
| Kimi-K3 | 4 | 168 | 52.19 | 22.71 | 2.30x |
| Kimi-K3 | 8 | 168 | 86.07 | 31.82 | 2.70x |
| Kimi-K3 | 16 | 168 | 124.00 | 42.49 | 2.92x |
| Kimi-K3 | 32 | 168 | 151.88 | 53.65 | 2.83x |
| Kimi-K3 | 64 | 168 | 163.68 | 63.35 | 2.58x |
| Kimi-K3 | 256 | 168 | 167.16 | 71.73 | 2.33x |
| Kimi-K3 | 1024 | 168 | 167.20 | 71.96 | 2.32x |
| Kimi-K3 | 1 | 181 | 15.35 | 10.78 | 1.42x |
| Kimi-K3 | 2 | 181 | 29.17 | 15.55 | 1.88x |
| Kimi-K3 | 4 | 181 | 52.84 | 23.27 | 2.27x |
| Kimi-K3 | 8 | 181 | 88.04 | 32.71 | 2.69x |
| Kimi-K3 | 16 | 181 | 128.79 | 43.89 | 2.93x |
| Kimi-K3 | 32 | 181 | 160.44 | 55.67 | 2.88x |
| Kimi-K3 | 64 | 181 | 174.94 | 65.98 | 2.65x |
| Kimi-K3 | 256 | 181 | 179.67 | 74.95 | 2.40x |
| Kimi-K3 | 1024 | 181 | 179.74 | 75.20 | 2.39x |
| Kimi-K3 | 1 | 205 | 15.43 | 11.10 | 1.39x |
| Kimi-K3 | 2 | 205 | 29.45 | 15.96 | 1.85x |
| Kimi-K3 | 4 | 205 | 53.84 | 24.19 | 2.23x |
| Kimi-K3 | 8 | 205 | 91.15 | 34.16 | 2.67x |
| Kimi-K3 | 16 | 205 | 136.58 | 46.27 | 2.95x |
| Kimi-K3 | 32 | 205 | 174.94 | 59.11 | 2.96x |
| Kimi-K3 | 64 | 205 | 194.78 | 70.52 | 2.76x |
| Kimi-K3 | 256 | 205 | 202.32 | 80.53 | 2.51x |
| Kimi-K3 | 1024 | 205 | 202.44 | 80.81 | 2.51x |
| Kimi-K3 | 1 | 224 | 15.48 | 11.32 | 1.37x |
| Kimi-K3 | 2 | 224 | 29.63 | 16.26 | 1.82x |
| Kimi-K3 | 4 | 224 | 54.50 | 24.84 | 2.19x |
| Kimi-K3 | 8 | 224 | 93.22 | 35.18 | 2.65x |
| Kimi-K3 | 16 | 224 | 141.93 | 47.96 | 2.96x |
| Kimi-K3 | 32 | 224 | 185.33 | 61.63 | 3.01x |
| Kimi-K3 | 64 | 224 | 209.59 | 73.86 | 2.84x |
| Kimi-K3 | 256 | 224 | 219.77 | 84.66 | 2.60x |
| Kimi-K3 | 1024 | 224 | 219.93 | 84.95 | 2.59x |
| Kimi-K3 | 1 | 335 | 15.65 | 12.32 | 1.27x |
| Kimi-K3 | 2 | 335 | 30.30 | 17.75 | 1.71x |
| Kimi-K3 | 4 | 335 | 56.93 | 27.49 | 2.07x |
| Kimi-K3 | 8 | 335 | 101.18 | 39.78 | 2.54x |
| Kimi-K3 | 16 | 335 | 163.73 | 55.86 | 2.93x |
| Kimi-K3 | 32 | 335 | 231.42 | 73.59 | 3.14x |
| Kimi-K3 | 64 | 335 | 281.43 | 90.01 | 3.13x |
| Kimi-K3 | 256 | 335 | 311.38 | 104.93 | 2.97x |
| Kimi-K3 | 1024 | 335 | 312.00 | 105.34 | 2.96x |
| Kimi-K3 | 4096 | 335 | 312.00 | 105.34 | 2.96x |
| Kimi-K3 | 1 | 336 | 15.65 | 12.32 | 1.27x |
| Kimi-K3 | 2 | 336 | 30.31 | 17.76 | 1.71x |
| Kimi-K3 | 4 | 336 | 56.95 | 27.51 | 2.07x |
| Kimi-K3 | 8 | 336 | 101.23 | 39.82 | 2.54x |
| Kimi-K3 | 16 | 336 | 163.87 | 55.92 | 2.93x |
| Kimi-K3 | 32 | 336 | 231.74 | 73.68 | 3.15x |
| Kimi-K3 | 64 | 336 | 281.98 | 90.14 | 3.13x |
| Kimi-K3 | 256 | 336 | 312.12 | 105.09 | 2.97x |
| Kimi-K3 | 1024 | 336 | 312.75 | 105.50 | 2.96x |
| Kimi-K3 | 4096 | 336 | 312.75 | 105.50 | 2.96x |
| Kimi-K3 | 1 | 348 | 15.66 | 12.40 | 1.26x |
| Kimi-K3 | 2 | 348 | 30.35 | 17.90 | 1.70x |
| Kimi-K3 | 4 | 348 | 57.12 | 27.71 | 2.06x |
| Kimi-K3 | 8 | 348 | 101.82 | 40.24 | 2.53x |
| Kimi-K3 | 16 | 348 | 165.56 | 56.66 | 2.92x |
| Kimi-K3 | 32 | 348 | 235.57 | 74.76 | 3.15x |
| Kimi-K3 | 64 | 348 | 288.40 | 91.61 | 3.15x |
| Kimi-K3 | 256 | 348 | 320.90 | 106.97 | 3.00x |
| Kimi-K3 | 1024 | 348 | 321.59 | 107.40 | 2.99x |
| Kimi-K3 | 4096 | 348 | 321.59 | 107.40 | 2.99x |
| Kimi-K3 | 1 | 369 | 15.68 | 12.54 | 1.25x |
| Kimi-K3 | 2 | 369 | 30.43 | 18.14 | 1.68x |
| Kimi-K3 | 4 | 369 | 57.40 | 28.04 | 2.05x |
| Kimi-K3 | 8 | 369 | 102.76 | 40.97 | 2.51x |
| Kimi-K3 | 16 | 369 | 168.30 | 57.90 | 2.91x |
| Kimi-K3 | 32 | 369 | 241.85 | 76.61 | 3.16x |
| Kimi-K3 | 64 | 369 | 299.12 | 94.10 | 3.18x |
| Kimi-K3 | 256 | 369 | 335.77 | 110.16 | 3.05x |
| Kimi-K3 | 1024 | 369 | 336.56 | 110.61 | 3.04x |
| Kimi-K3 | 4096 | 369 | 336.56 | 110.61 | 3.04x |
| Kimi-K3 | 1 | 381 | 15.69 | 12.61 | 1.24x |
| Kimi-K3 | 2 | 381 | 30.47 | 18.28 | 1.67x |
| Kimi-K3 | 4 | 381 | 57.55 | 28.21 | 2.04x |
| Kimi-K3 | 8 | 381 | 103.26 | 41.38 | 2.50x |
| Kimi-K3 | 16 | 381 | 169.76 | 58.59 | 2.90x |
| Kimi-K3 | 32 | 381 | 245.23 | 77.63 | 3.16x |
| Kimi-K3 | 64 | 381 | 304.96 | 95.48 | 3.19x |
| Kimi-K3 | 256 | 381 | 343.98 | 111.91 | 3.07x |
| Kimi-K3 | 1024 | 381 | 344.84 | 112.38 | 3.07x |
| Kimi-K3 | 4096 | 381 | 344.84 | 112.38 | 3.07x |
| Kimi-K3 | 1 | 388 | 15.69 | 12.65 | 1.24x |
| Kimi-K3 | 2 | 388 | 30.49 | 18.36 | 1.66x |
| Kimi-K3 | 4 | 388 | 57.63 | 28.31 | 2.04x |
| Kimi-K3 | 8 | 388 | 103.54 | 41.62 | 2.49x |
| Kimi-K3 | 16 | 388 | 170.57 | 58.98 | 2.89x |
| Kimi-K3 | 32 | 388 | 247.14 | 78.22 | 3.16x |
| Kimi-K3 | 64 | 388 | 308.28 | 96.27 | 3.20x |
| Kimi-K3 | 256 | 388 | 348.68 | 112.92 | 3.09x |
| Kimi-K3 | 1024 | 388 | 349.57 | 113.39 | 3.08x |
| Kimi-K3 | 4096 | 388 | 349.57 | 113.39 | 3.08x |
| Kimi-K3 | 1 | 393 | 15.70 | 12.68 | 1.24x |
| Kimi-K3 | 2 | 393 | 30.51 | 18.41 | 1.66x |
| Kimi-K3 | 4 | 393 | 57.69 | 28.38 | 2.03x |
| Kimi-K3 | 8 | 393 | 103.73 | 41.78 | 2.48x |
| Kimi-K3 | 16 | 393 | 171.14 | 59.25 | 2.89x |
| Kimi-K3 | 32 | 393 | 248.47 | 78.63 | 3.16x |
| Kimi-K3 | 64 | 393 | 310.60 | 96.82 | 3.21x |
| Kimi-K3 | 256 | 393 | 352.00 | 113.63 | 3.10x |
| Kimi-K3 | 1024 | 393 | 352.91 | 114.10 | 3.09x |
| Kimi-K3 | 4096 | 393 | 352.91 | 114.10 | 3.09x |
| Kimi-K3 | 1 | 394 | 15.70 | 12.69 | 1.24x |
| Kimi-K3 | 2 | 394 | 30.51 | 18.42 | 1.66x |
| Kimi-K3 | 4 | 394 | 57.70 | 28.39 | 2.03x |
| Kimi-K3 | 8 | 394 | 103.77 | 41.81 | 2.48x |
| Kimi-K3 | 16 | 394 | 171.25 | 59.31 | 2.89x |
| Kimi-K3 | 32 | 394 | 248.73 | 78.71 | 3.16x |
| Kimi-K3 | 64 | 394 | 311.07 | 96.93 | 3.21x |
| Kimi-K3 | 256 | 394 | 352.66 | 113.77 | 3.10x |
| Kimi-K3 | 1024 | 394 | 353.58 | 114.24 | 3.10x |
| Kimi-K3 | 4096 | 394 | 353.58 | 114.24 | 3.10x |
| Kimi-K3 | 1 | 448 | 15.73 | 12.97 | 1.21x |
| Kimi-K3 | 2 | 448 | 30.65 | 18.99 | 1.61x |
| Kimi-K3 | 4 | 448 | 58.23 | 29.05 | 2.00x |
| Kimi-K3 | 8 | 448 | 105.59 | 43.53 | 2.43x |
| Kimi-K3 | 16 | 448 | 176.68 | 62.05 | 2.85x |
| Kimi-K3 | 32 | 448 | 261.69 | 82.87 | 3.16x |
| Kimi-K3 | 64 | 448 | 334.19 | 102.64 | 3.26x |
| Kimi-K3 | 256 | 448 | 386.29 | 121.03 | 3.19x |
| Kimi-K3 | 1024 | 448 | 387.51 | 121.55 | 3.19x |
| Kimi-K3 | 4096 | 448 | 387.51 | 121.55 | 3.19x |
| Kimi-K3 | 1 | 560 | 15.79 | 13.42 | 1.18x |
| Kimi-K3 | 2 | 560 | 30.86 | 20.03 | 1.54x |
| Kimi-K3 | 4 | 560 | 59.01 | 30.12 | 1.96x |
| Kimi-K3 | 8 | 560 | 108.33 | 46.64 | 2.32x |
| Kimi-K3 | 16 | 560 | 185.03 | 66.56 | 2.78x |
| Kimi-K3 | 32 | 560 | 282.39 | 89.93 | 3.14x |
| Kimi-K3 | 64 | 560 | 372.84 | 112.66 | 3.31x |
| Kimi-K3 | 256 | 560 | 445.29 | 134.13 | 3.32x |
| Kimi-K3 | 1024 | 560 | 447.10 | 134.75 | 3.32x |
| Kimi-K3 | 4096 | 560 | 447.10 | 134.75 | 3.32x |
| Kimi-K3 | 1 | 672 | 15.82 | 13.76 | 1.15x |
| Kimi-K3 | 2 | 672 | 31.00 | 20.92 | 1.48x |
| Kimi-K3 | 4 | 672 | 59.55 | 31.00 | 1.92x |
| Kimi-K3 | 8 | 672 | 110.20 | 49.15 | 2.24x |
| Kimi-K3 | 16 | 672 | 190.91 | 69.95 | 2.73x |
| Kimi-K3 | 32 | 672 | 297.51 | 95.79 | 3.11x |
| Kimi-K3 | 64 | 672 | 402.36 | 121.20 | 3.32x |
| Kimi-K3 | 256 | 672 | 492.68 | 145.31 | 3.39x |
| Kimi-K3 | 1024 | 672 | 495.04 | 145.99 | 3.39x |
| Kimi-K3 | 4096 | 672 | 495.04 | 145.99 | 3.39x |
| Kimi-K3 | 1 | 1231 | 15.90 | 14.64 | 1.09x |
| Kimi-K3 | 2 | 1231 | 31.32 | 23.92 | 1.31x |
| Kimi-K3 | 4 | 1231 | 60.78 | 34.58 | 1.76x |
| Kimi-K3 | 8 | 1231 | 114.63 | 55.70 | 2.06x |
| Kimi-K3 | 16 | 1231 | 205.22 | 82.92 | 2.47x |
| Kimi-K3 | 32 | 1231 | 336.28 | 117.02 | 2.87x |
| Kimi-K3 | 64 | 1231 | 483.11 | 150.19 | 3.22x |
| Kimi-K3 | 256 | 1231 | 632.37 | 184.89 | 3.42x |
| Kimi-K3 | 1024 | 1231 | 636.68 | 185.84 | 3.43x |
| Kimi-K3 | 4096 | 1231 | 636.68 | 185.84 | 3.43x |

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
| gpu | Kimi-K3 | 1 | 27.74 | 1.1% |
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
| Kimi-K3 | 1 | 167 | 70.08% | 1,237.12 | 10.57 |
| Kimi-K3 | 2 | 3 | 33.71% | 609.24 | 10.57 |

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
| Kimi-K3 | 1 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 2 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 4 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 8 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 16 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 32 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 64 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 256 | 1.79% | 137.0 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 23.1 | 8,651.2 |
| Kimi-K3 | 1024 | 4.81% | 180.8 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 8.5 | 8,655.1 |
| Kimi-K3 | 4096 | 17.91% | 370.2 GB | 100.00% | 45,287.76 TB/s | 45,287.76 TB/s | 2.1 | 8,656.8 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 30 |
| gpu | infeasible | 26 |
| gpu | link_latency | 184 |
| gpu | weight_read | 520 |
| rom | compute | 332 |
| rom | infeasible | 1128 |
| rom | kv_read | 103 |
| rom | link_latency | 278 |
| rom | weight_read | 199 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 26 |
| rom | CAPACITY | 1128 |

## Mechanical consistency audit

**FAIL** over 52,411 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x353', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x386', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x398', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x353', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x386', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x398', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x353', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x386', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x398', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-hybrid-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x353', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x386', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x398', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-pipeline-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x10', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-pipeline-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x353', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x386', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x398', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-tensor-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x10', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-tensor-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x340', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x353', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x386', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x398', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hybrid-x399', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x6', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x8', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x10', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-wafer-hybrid-x12', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x340-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x353-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x386-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x398-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-pipeline-x399-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x340-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x353-romfill', 'Kimi-K3', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('Kimi-K3/ROM-N6-native-SRAMKV-array-hw-tensor-x386-romfill', 'Kimi-K3', 1)

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
