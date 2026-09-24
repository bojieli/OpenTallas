# Area-constrained roofline: n6_vs_a100-mimo-v26-pro-8k

> CANDIDATE MODEL under n6_vs_a100: MiMo-V2.6-Pro at 8,192 tokens. Reticle-class mask-ROM silicon at TSMC N6 against NVIDIA A100 80GB at N7, compared at equal silicon area with the area stated on both sides. This is the pairing the Taalas HC1 anchor validates: 815 mm2 at N6 against 826 mm2 at N7, essentially the same die one node apart. Same rule, same code path as the primary; the model is profiled from its official checkpoint headers and has been executed by no lane in this repository. The primary artifact is unchanged.

Every figure below is produced by `src/opentallas/roofline.py` from
`configs/hardware/technology.json` and the released model profiles. Nothing
here is hand-computed. Silicon area is the primary input; capacity,
bandwidth and compute roof are derived from it.

## What the model says

1. **The ROM path has a hard per-token ceiling that is a technology constant, not a design choice.** The full-array sweep time is the ROM capacity density divided by its read-bandwidth density, so it does not depend on model size, batch, or expert coverage: 34.5 us, or 29,015 tok/s per user. Under this derivation both densities scale with the same published bitcell-area ratio, so that ceiling is the same at every node: process scaling buys a ROM design capacity, not per-token speed.
2. **Per-user latency and aggregate throughput are now separate quantities, and separating them is the largest correction in this report.** A token under pipeline parallelism is served by one stage's silicon at a time and must visit every stage, so its latency is the aggregate service time multiplied by `token_slots`, not divided by anything. The two factors cancel exactly: **adding devices under pipeline parallelism buys aggregate throughput and buys one user nothing.** On the ROM side the correction reaches 203x (ROM-N6-native-SRAMKV-wafer-pipeline-x12, 681 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 60 devices. On the GPU side the correction reaches 107x (a100_sxm_80gb-x672-pipeline, 672 slots), and the batch-1 design that now wins -- the smallest silicon within 5% of the best per-user rate, which is the rule this report has since REPLACED and keeps only to compute the before/after -- runs `tensor` on 130 devices. Both validation gates are single-slot machines and are unchanged to the digit.
3. **Each model is recommended one design, by a rule stated in this report, and the answer is not the same class for all three.** The rule keeps every design nothing else beats on BOTH per-user tokens/s and tokens/s per mm2, then walks that frontier from the smallest feasible machine and stops when the next slab of silicon returns less than the silicon already bought. MiMo-V2.6-Pro takes 132 x 815 mm2 (107,580 mm2, array, KV in SRAM) at 5,254 tok/s per user and 49 tok/s per 1,000 mm2, holding 1 session, against 130 copies of one unified HBM die at the same silicon: 8.8x per user. Every model lands in the same class under this rule, which is a result rather than an assumption. Ranking on per-user rate alone -- which is what this report used to do -- hands Qwen3-8B a whole wafer for a checkpoint that holds in three reticle dies.
4. **The largest ratio anywhere in this study is not the study's result, and it is reported here so nobody has to go looking for it.** The maximum batch-1 per-user ratio is MiMo-V2.6-Pro on 277,100 mm2 of ROM silicon at 5,478 tok/s per user against 276,710 mm2 of a100_sxm_80gb-x335-tensor at 467 tok/s: **11.7x**, ROM binding on `weight_read` and the GPU on `link_latency`. It holds 53,362 resident sessions against the GPU cluster's 51,343. A maximum over a sampling grid is a fact about the grid; the recommended-design ratios above are the ones this report stands behind.
5. **The layer cap on serial stage boundaries is still applied and is no longer visible in the headline, because no comparator it binds on wins any more.** A token cannot cross more stage boundaries than the model has layers, and this study charges at most that many. With per-user latency separated from aggregate throughput, both families now pick a topology with a tensor group at batch 1, and a tensor group has one stage and no boundary for the cap to remove. The `Ratio without the layer cap` column in the iso-area table therefore equals the stated ratio wherever the winner is tensor-parallel; it still differs wherever a pipeline wins.
6. **Letting the GPU choose its own parallelism is worth up to 15.22x to it.** At 205,380 mm2 on MiMo-V2.6-Pro the pipeline-only GPU delivers 41.17 tok/s and the same silicon running tensor delivers 627 tok/s.
7. **The advantage erodes with batch, and the erosion is a KV effect.** At batch 4096 the aggregate ratio at equal area spans 0.02x (MiMo-V2.6-Pro, ROM binding on `link_latency`) to 4.60x (MiMo-V2.6-Pro, ROM binding on `compute`). Weight traffic is what ROM removes; KV traffic it does not, and KV traffic is what grows with batch.
8. **Sparse MoE buys aggregate throughput on a ROM machine, not latency.** MiMo-V2.6-Pro engages 100.0% of its ROM array at batch 1 and 100.0% at batch 4096, while the weight-read time is identical at both. What the machine delivers rises from 208 to 27,502 tok/s, and its rate with every slot occupied from 27,403 to 27,502. The second rises far less than the first because the batch-1 figure is already a full-machine number -- this design has 132 slots -- so most of what batching adds there is coverage rather than occupancy. An unselected expert's read ports cannot be borrowed, so its idle bandwidth is only recovered by giving the sweep more users.
9. **Tensor parallelism is better on a wafer than on NVLink and is not good anywhere, and the published claim that it reaches Taalas-class rates on-wafer is RETRACTED.** Two all-reduces per layer per token cost up to 2,056 us over NVLink, capping per-user decode at 486 tok/s before any arithmetic happens; the same collectives on-wafer cost at most 300.9 us and cap it at 3,323 tok/s. The ordering survives, and on a like-for-like comparison -- the same model's collective on one wafer against the same model's on NVLink -- the wafer is at least nanx cheaper. But the previous figures of 116,278 and 81,966 tok/s came from charging a stitched 2-D mesh one flat hop however many reticle fields the collective spanned. A mesh has no switch, so an all-reduce costs about 1.1 times its diameter, and the model now charges that. What the collective buys is what makes it worth paying: with per-user latency separated from aggregate throughput, a tensor group is the only arrangement that puts the whole machine on one token, and the topology tables below show both families choosing one at batch 1 in spite of this cost.
10. **Which topology wins depends entirely on what is being maximised, and the study reports both rather than choosing.** On per-user rate at equal area a wafer wins 0 of 10 operating points and an array 10; on tokens per second per square millimetre the same points go 10 to the array and 0 to the wafer. A wafer is not faster per unit silicon -- it is faster because it is more silicon, plus a hop latency an array cannot match.
11. **A wafer has less die edge per unit area than the same area of separate dies, and that is an argument against it.** Perimeter grows as the square root of area, so HBM beachfront -- and therefore KV bandwidth -- does not scale with wafer area the way compute and ROM capacity do. This model charges both sides the same edge utilisation a shipping GPU achieves, and the consequence shows up wherever a design binds on `kv_read`: 246 of 3891 feasible points.
12. **The largest open question is not in this model's inputs but in the architecture, and a batch-1 anchor cannot settle its scaling law.** If a ROM cell both stores and multiplies, each concurrent stream needs its own pass and aggregate per-die throughput never exceeds the per-user rate. At batch 4096 that costs up to 40.6x of aggregate throughput (MiMo-V2.6-Pro). Their sweep counts coincide at batch 1, but their cell and pre-compute costs make their floorplans different; the current compute-in-ROM anchor reconstruction fails capacity. A batch-1 validation therefore cannot establish either high-batch law.
13. **A third machine sits between them, and for a sparse model it recovers part of what compute-in-ROM gives up -- less than the mean-region arithmetic used to say.** Give each expert region its own activation port and two tokens selecting disjoint experts drive disjoint regions at the same time; only the tokens landing on one region serialise, and the sweep waits for the BUSIEST region rather than the average engaged one. The largest gain over a global broadcast is 9.08x, on MiMo-V2.6-Pro at batch 4096, where the busiest region carries 3.17x the load of the mean engaged one. It is not free ground: per-region still loses to the amortising ROM-plus-MAC machine at 20 of 20 operating points. A dense model has one region, so it gains nothing -- the disjointness is what sparsity buys.
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

### MiMo-V2.6-Pro at 8,192 tokens

**Recommended: `ROM-N6-native-SRAMKV-array-hw-tensor-x132`** -- 132 x 815 mm2 reticle dies, 107,580 mm2 total, `tensor`-parallel, KV in SRAM, spare silicon to `sram`.

- **5,254.3 tok/s per user** (0.19 ms/token), binding on `link_latency`
- **48.8 tok/s per 1,000 mm2** -- the quantity the rule maximises
- 5,254 tok/s aggregate with every slot full, over 1 resident session (fill limited by `batch`)
- 6,690 W at 0.062 W/mm2, 1,273.2 mJ/token, thermal scale 1.000

**Iso-area, at the area the rule chose.** The comparator is 130 copies of one unified HBM die -- `a100_sxm_80gb-x130-tensor`, 107,380 mm2, area ratio 1.0019 -- running the `tensor` topology it chose for itself.

| | ROM | iso-area GPU | ratio |
| --- | ---: | ---: | ---: |
| silicon mm2 | 107,580 | 107,380 | 1.0019 |
| user tok/s | 5,254.3 | 595.6 | 8.82x |
| aggregate tok/s | 5,254 | 596 | 0.98x |
| resident sessions | 1 | 19,169 | -- |
| J/token | 1.2732 | 35.7028 | 28.0x |

The areas match to within 2%, so no granularity correction is needed on this row.

**Read the resident-session row before the ratio row.** A per-user rate divided by a per-user rate is a latency claim, and a latency claim taken from a machine that holds 1 session against one that holds 19,169 is not the trade it looks like. Where those two numbers are far apart the honest reading is the batch-regime table below, not this row.

The GPU's own best machine at **any** area is `a100_sxm_80gb-x249-tensor` at 205,674 mm2 and 626.6 tok/s per user, which is the area-free bound and is quoted so the iso-area row is not the only comparison on the page.

**Headline before and after.**

| rule | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions | iso-area ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| before -- smallest within 5% of peak rate | `ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 171,965 | 5,819.1 | 33.8 | 33,115 | 9.39x |
| rank on per-user rate alone | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 34.0 | 33,272 | 9.48x |
| smallest feasible machine | `ROM-N6-native-SRAMKV-array-hw-tensor-x122` | 99,430 | 4,652.2 | 46.8 | 1 | 7.87x |
| **after -- this report's rule** | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | 107,580 | 5,254.3 | 48.8 | 1 | 8.82x |

**The walk, rung by rung.** The number in the `marginal` column is what the next slab of silicon returns; the number in `incumbent average` is what the silicon already bought returns. The walk stops the first time the former is not larger.

| design | mm2 | user tok/s | tok/s per 1,000 mm2 | marginal | incumbent average | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | 107,580 | 5,254.3 | 48.8 | -- | 48.8 | ACCEPT |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x135` | 110,025 | 5,316.9 | 48.3 | 25.6 | 48.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x137` | 111,655 | 5,349.1 | 47.9 | 23.3 | 48.8 | stop |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x138` | 112,470 | 5,357.2 | 47.6 | 21.1 | 48.8 | stop |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 34.0 | 9.6 | 48.8 | stop |

**The frontier at batch 1, published in full.** Every design here is one that nothing else beats on both axes at once, so a reader with a latency target this report does not know about can read their own point off it. An honest curve beats a false single answer, and the rows above and below the recommendation are the ones that show what the rule is doing.

| design | mm2 | devices | user tok/s | aggregate tok/s | tok/s per 1,000 mm2 | resident sessions | binds on | W | mJ/token | iso-area GPU | ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x132` **<-- recommended** | 107,580 | 132 | 5,254.3 | 5,254 | 48.8 | 1 | `link_latency` | 6,690 | 1,273.2 | `a100_sxm_80gb-x130-tensor` | 8.82x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x135` | 110,025 | 135 | 5,316.9 | 5,317 | 48.3 | 1 | `link_latency` | 6,841 | 1,286.6 | `a100_sxm_80gb-x133-tensor` | 8.90x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x137` | 111,655 | 137 | 5,349.1 | 5,349 | 47.9 | 1 | `link_latency` | 6,941 | 1,297.6 | `a100_sxm_80gb-x135-tensor` | 8.94x |
| `ROM-N6-native-SRAMKV-array-hw-tensor-x138` | 112,470 | 138 | 5,357.2 | 5,357 | 47.6 | 1 | `link_latency` | 6,991 | 1,305.0 | `a100_sxm_80gb-x136-tensor` | 8.95x |
| `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 212 | 5,877.1 | 311,489 | 34.0 | 33,272 | `compute` | 38,220 | 3,174.3 | `a100_sxm_80gb-x209-tensor` | 9.48x |

**Array or wafer, with the losing class's own best machine on the page.** A frontier can honestly be a single row -- that is what it means for one design to win on both axes at once -- and a single row tells a reader nothing about what it beat. Each class enters at its own optimum, never at its minimum-feasible machine, because comparing against a floor is how a class gets beaten by its own under-provisioning rather than by the other class.

| class | designs | pick | design | mm2 | user tok/s | tok/s per 1,000 mm2 | resident sessions |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| array | 288 | densest | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | 107,580 | 5,254.3 | 48.8 | 1 |
| array | 288 | fastest | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 34.0 | 33,272 |
| array | 288 | smallest | `ROM-N6-native-SRAMKV-array-hw-tensor-x122` | 99,430 | 4,652.2 | 46.8 | 1 |
| wafer | 54 | densest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,160.2 | 22.8 | 1 |
| wafer | 54 | fastest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,160.2 | 22.8 | 1 |
| wafer | 54 | smallest | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,160.2 | 22.8 | 1 |

**Three classes at iso-area, batch by batch.** Each ROM class enters at its fastest feasible design for that batch and is read against the GPU comparator at *its own* silicon area (the area ratio is stated). The `array @ wafer area` row is the fastest reticle array within 5% of the wafer's silicon, which is the wafer-versus-array comparison at iso-area. Read resident sessions before the ratio.

| batch | class | design | mm2 | user tok/s | aggregate tok/s | resident sessions | W | mJ/token | binds on | iso-area GPU | GPU user tok/s | GPU sessions | GPU mJ/token | area ratio | speed ratio | J/token ratio |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 311,489 | 33,272 | 38,220 | 3,174.3 | `compute` | `a100_sxm_80gb-x209-tensor` | 619.8 | 31,568 | 52,874.4 | 1.001 | 9.48x | 16.7x |
| 1 | wafer | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,160.2 | 3,160 | 1 | 10,401 | 3,291.3 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 610.0 | 25,133 | 43,953.4 | 0.999 | 5.18x | 13.4x |
| 1 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-tensor-x170` | 138,550 | 4,706.2 | 4,706 | 26,681 | 13,030 | 2,768.6 | `link_latency` | `a100_sxm_80gb-x168-tensor` | 610.0 | 25,133 | 43,953.4 | 0.998 | 7.71x | 15.9x |
| 1 | wafer reference | `ROM-N6-native-SRAMKV-wafer-hybrid-x3` | 138,675 | 3,160.2 | -- | 1 | -- | 3,291.3 | -- | -- | -- | -- | -- | 0.999 | 0.67x wafer/array | -- |
| 2 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 311,489 | 33,272 | 38,220 | 1,619.2 | `compute` | `a100_sxm_80gb-x209-tensor` | 537.7 | 31,568 | 30,754.5 | 1.001 | 10.93x | 19.0x |
| 2 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,145.4 | 12,581 | 5,398 | 18,356 | 2,854.0 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 540.4 | 33,922 | 32,617.1 | 0.999 | 5.82x | 11.4x |
| 2 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 5,641.4 | 321,562 | 35,627 | 40,847 | 1,859.9 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 540.4 | 33,922 | 32,617.1 | 1.000 | 10.44x | 17.5x |
| 2 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,145.4 | -- | 5,398 | -- | 2,854.0 | -- | -- | -- | -- | -- | 1.001 | 0.56x wafer/array | -- |
| 4 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 311,489 | 33,272 | 38,220 | 841.6 | `compute` | `a100_sxm_80gb-x209-tensor` | 425.3 | 31,568 | 19,662.2 | 1.001 | 13.82x | 23.4x |
| 4 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,145.4 | 12,581 | 5,398 | 18,356 | 1,459.0 | `link_latency` | `a100_sxm_80gb-x224-tensor` | 427.7 | 33,922 | 20,829.5 | 0.999 | 7.35x | 14.3x |
| 4 | array @ wafer area | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | 5,641.4 | 321,562 | 35,627 | 40,847 | 961.9 | `weight_read` | `a100_sxm_80gb-x224-tensor` | 427.7 | 33,922 | 20,829.5 | 1.000 | 13.19x | 21.7x |
| 4 | wafer reference | `ROM-N6-native-HBMKV-wafer-hybrid-x4` | 184,900 | 3,145.4 | -- | 5,398 | -- | 1,459.0 | -- | -- | -- | -- | -- | 1.001 | 0.56x wafer/array | -- |
| 8 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 311,489 | 33,272 | 38,220 | 452.8 | `compute` | `a100_sxm_80gb-x209-tensor` | 300.7 | 31,568 | 14,054.4 | 1.001 | 19.55x | 31.0x |
| 8 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x8` | 369,800 | 3,141.3 | 25,131 | 10,797 | 46,452 | 1,848.4 | `link_latency` | `a100_sxm_80gb-x448-tensor` | 266.7 | 69,078 | 31,825.0 | 0.999 | 11.78x | 17.2x |
| 16 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 311,489 | 33,272 | 38,220 | 258.4 | `compute` | `a100_sxm_80gb-x209-hybrid` | 255.8 | 31,568 | 11,563.1 | 1.001 | 22.98x | 43.1x |
| 16 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 3,034.7 | 48,554 | 16,196 | 75,136 | 1,547.5 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 255.3 | 104,234 | 27,943.3 | 0.999 | 11.89x | 18.1x |
| 32 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | 5,877.1 | 311,489 | 33,272 | 38,220 | 161.2 | `compute` | `a100_sxm_80gb-x209-hybrid` | 245.1 | 31,568 | 7,570.3 | 1.001 | 23.98x | 46.9x |
| 32 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,683.4 | 85,870 | 16,196 | 77,156 | 898.5 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 255.3 | 104,234 | 16,066.5 | 0.999 | 10.51x | 17.9x |
| 64 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill` | 205,380 | 5,479.6 | 350,692 | 39,550 | 45,212 | 128.9 | `weight_read` | `a100_sxm_80gb-x249-hybrid` | 207.7 | 37,846 | 5,396.8 | 0.999 | 26.39x | 39.0x |
| 64 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 2,179.1 | 139,461 | 16,196 | 80,048 | 574.0 | `link_latency` | `a100_sxm_80gb-x672-hybrid` | 255.3 | 104,234 | 10,128.1 | 0.999 | 8.54x | 17.6x |
| 256 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill` | 308,070 | 2,663.9 | 681,969 | 59,326 | 74,072 | 108.6 | `compute` | `a100_sxm_80gb-x373-hybrid` | 129.0 | 57,307 | 3,342.3 | 1.000 | 20.66x | 18.1x |
| 256 | wafer | `ROM-N6-native-HBMKV-wafer-hybrid-x12` | 554,700 | 1,024.1 | 262,175 | 16,196 | 86,561 | 330.2 | `kv_read` | `a100_sxm_80gb-x672-hybrid` | 173.9 | 104,234 | 4,347.8 | 0.999 | 5.89x | 8.8x |
| 1024 | array | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 308,070 | 999.0 | 1,022,965 | 59,326 | 97,236 | 95.1 | `compute` | `a100_sxm_80gb-x373-expert` | 100.6 | 54,534 | 635.1 | 1.000 | 9.94x | 6.7x |
| 1024 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 359.4 | 367,993 | 16,196 | 94,605 | 257.1 | `kv_read` | `a100_sxm_80gb-x672-expert` | 125.2 | 99,119 | 868.5 | 0.999 | 2.87x | 3.4x |
| 4096 | array | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 308,070 | 259.0 | 1,060,858 | 59,326 | 99,341 | 93.6 | `compute` | `a100_sxm_80gb-x373-expert` | 56.3 | 54,534 | 302.6 | 1.000 | 4.60x | 3.2x |
| 4096 | wafer | `ROM-N6-native-HBMKV-wafer-pipeline-x12` | 554,700 | 90.4 | 370,429 | 16,196 | 93,077 | 251.3 | `kv_read` | `a100_sxm_80gb-x672-expert` | 81.2 | 99,119 | 360.8 | 0.999 | 1.11x | 1.4x |

**The best design differs by batch, and here is where it changes.**

| batches | design | mm2 | class | KV | resident sessions |
| --- | --- | ---: | --- | --- | ---: |
| 1 | `ROM-N6-native-SRAMKV-array-hw-tensor-x132` | 107,580 | array | SRAM | 1 |
| 2-4 | `ROM-N6-native-HBMKV-array-hw-tensor-x140` | 114,100 | array | HBM | 21,972 |
| 8-32 | `ROM-N6-native-HBMKV-array-hw-hybrid-x212` | 172,780 | array | HBM | 33,272 |
| 64 | `ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 185,005 | array | HBM | 35,627 |
| 256 | `ROM-N6-native-HBMKV-array-hw-hybrid-x252` | 205,380 | array | HBM | 39,550 |
| 1024 | `ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 308,070 | array | HBM | 59,326 |
| 4096 | `ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 308,070 | array | HBM | 59,326 |

Per-user rate falls as the batch rises on a fixed machine, so `tok/s per 1,000 mm2` at batch B is the same ordering as `delivered tok/s per 1,000 mm2` at batch B -- delivered is exactly B times per-user. The rule is therefore the same rule at every batch, and the design moving is the study telling you the answer genuinely depends on the operating point, not the metric changing under it.

**Where the array class is sampled, so the reader can see the rungs rather than take them on trust.** Until 2026-09-03 the ROM array class was sampled only at the device counts each floorplan's own sizing sweep chose. It is now emitted on an explicit ladder: multiples of the smallest machine that holds the design (1.25x, 1.5x, 2x, 3x, 4x) and the device counts whose silicon equals each wafer rung of `ROM_AREA_LADDER`, so every wafer design has an array at the same area. The counts this study actually emitted, per model and per `(kv_store, spare_area_policy)` combination, are printed below:

| model | KV store | spare silicon | reticle counts emitted |
| --- | --- | --- | --- |
| MiMo-V2.6-Pro | HBM | rom | 132, 140, 158, 170, 181, 189, 211, 212, 227, 252, 340, 378 |
| MiMo-V2.6-Pro | HBM | sram | 132, 140, 158, 170, 181, 189, 211, 212, 227, 252, 340, 378 |
| MiMo-V2.6-Pro | SRAM | rom | 122, 132, 135, 137, 138, 147, 170, 176, 227, 234, 340, 351 |
| MiMo-V2.6-Pro | SRAM | sram | 122, 132, 135, 137, 138, 147, 170, 176, 227, 234, 340, 351 |

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

- **0 of 3,891 feasible points (0.0%) are power-limited.**
- 0 points are uncoolable at any speed (static power alone at or above the cooling budget).

Nothing in this study is power-limited. That is a statement about these designs and not an artifact of the energy model: static power is charged per mm2 per second, so a design cannot escape it by moving fewer bytes. The busiest point reaches 80% of its cooling budget, and the busiest wafer-scale ROM design 34%. The companion study at the other node, whose HBM generation delivers more than twice the bandwidth per stack, does have power-limited points.

| Family | Area class | Points | Throttled | Median power / budget | Worst power / budget | Peak W/mm2 | Median static share |
|---|---|---:|---:|---:|---:|---:|---:|
| gpu | large array (5,000-40,000 mm2) | 39 | 0 | 72.0% | 80.0% | 0.387 | 50% |
| gpu | wafer (>=40,000 mm2) | 1,200 | 0 | 69.5% | 79.8% | 0.387 | 68% |
| rom | wafer (>=40,000 mm2) | 2,652 | 0 | 23.7% | 64.7% | 0.323 | 77% |

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
| MiMo-V2.6-Pro | 1 | 171,965 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 3.182614 | 37,890.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x208-tensor` | 52.649282 | 32,628.4 | link_latency | 16.54x |
| MiMo-V2.6-Pro | 2 | 171,965 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 1.623314 | 37,890.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x208-tensor` | 30.622121 | 32,926.2 | link_latency | 18.86x |
| MiMo-V2.6-Pro | 4 | 171,965 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 0.843665 | 37,890.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x208-tensor` | 19.576159 | 33,307.4 | link_latency | 23.20x |
| MiMo-V2.6-Pro | 8 | 171,965 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 0.453840 | 37,890.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x208-tensor` | 13.991505 | 33,660.2 | link_latency | 30.83x |
| MiMo-V2.6-Pro | 16 | 171,965 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 0.258927 | 37,890.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x208-hybrid` | 11.333733 | 58,652.1 | weight_read | 42.82x |
| MiMo-V2.6-Pro | 32 | 171,965 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211` | 0.161471 | 37,890.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x208-hybrid` | 7.394289 | 58,987.8 | weight_read | 45.79x |
| MiMo-V2.6-Pro | 64 | 185,005 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x227` | 0.120865 | 42,360.8 | weight_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid` | 5.000980 | 64,739.6 | weight_read | 39.06x |
| MiMo-V2.6-Pro | 256 | 277,100 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x340` | 0.110357 | 74,317.1 | weight_read | `MiMo-V2.6-Pro/a100_sxm_80gb-x335-expert` | 1.838184 | 57,184.0 | weight_read | 16.66x |
| MiMo-V2.6-Pro | 1024 | 308,070 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378` | 0.095053 | 97,235.7 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x373-expert` | 0.635084 | 65,390.8 | weight_read | 6.68x |
| MiMo-V2.6-Pro | 4096 | 308,070 | `MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378` | 0.093642 | 99,341.2 | compute | `MiMo-V2.6-Pro/a100_sxm_80gb-x373-expert` | 0.302647 | 69,745.3 | link_latency | 3.23x |

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
| MiMo-V2.6-Pro | 8,192 | 1,020 B | 566.0 GB | 4.44 | 0.459 GB | 0.459 GB | 85.8 |

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
| MiMo-V2.6-Pro | 3 | 138,675 | 28,808.0 | wafer-pipeline | 3,160.2 | wafer-hybrid | 9.12x | 2,990.4 | pipeline | 610.0 | tensor | 4.90x | 9.63x | 5.18x | 0.54x |
| MiMo-V2.6-Pro | 4 | 184,900 | 30,786.8 | wafer-pipeline | 3,145.4 | wafer-hybrid | 9.79x | 3,349.5 | pipeline | 622.7 | tensor | 5.38x | 9.19x | 5.05x | 0.55x |
| MiMo-V2.6-Pro | 6 | 277,350 | 33,570.7 | wafer-pipeline | 3,143.3 | wafer-hybrid | 10.68x | 3,806.8 | pipeline | 467.1 | tensor | 8.15x | 8.82x | 6.73x | 0.76x |
| MiMo-V2.6-Pro | 8 | 369,800 | 35,160.5 | wafer-pipeline | 3,141.3 | wafer-hybrid | 11.19x | 4,085.7 | pipeline | 470.8 | tensor | 8.68x | 8.61x | 6.67x | 0.78x |
| MiMo-V2.6-Pro | 12 | 554,700 | 36,908.2 | wafer-pipeline | 3,137.3 | wafer-hybrid | 11.76x | 4,408.6 | pipeline | 474.5 | tensor | 9.29x | 8.37x | 6.61x | 0.79x |

**Did the error cancel in the ratio?** If it had, `Ratio change` would be 1.00x on every row. It runs from 0.54x to 0.79x across this ladder. It does not cancel, for the reason the two families reach equal area at very different device counts and therefore at very different slot counts, and because the correction changes which topology each side picks -- a change that lands on whichever side was relying on depth.


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
| MiMo-V2.6-Pro | 1 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x212 | 172,780 | 5,877.1 | 311,488.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x209-tensor | 172,634 | 1.00x | tensor | 1,482.25 | 619.8 | 619.8 | link_latency | 9.48x | 36.20x | 142.75x | 9.48x |
| MiMo-V2.6-Pro | 1 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x122 | 99,430 | 4,652.2 | 4,652.2 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x120-tensor | 99,120 | 1.00x | tensor | 1,476.13 | 590.8 | 590.8 | link_latency | 7.87x | 0.94x | 113.00x | 7.87x |
| MiMo-V2.6-Pro | 2 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x212 | 172,780 | 5,877.1 | 311,488.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x209-tensor | 172,634 | 1.00x | tensor | 1,696.09 | 537.7 | 1,075.3 | link_latency | 10.93x | 36.20x | 142.75x | 10.93x |
| MiMo-V2.6-Pro | 2 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x132 | 107,580 | 3,955.6 | 7,911.3 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | 107,380 | 1.00x | tensor | 1,687.10 | 515.2 | 1,030.5 | link_latency | 7.68x | 1.48x | 96.08x | 7.68x |
| MiMo-V2.6-Pro | 4 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x212 | 172,780 | 5,877.1 | 311,488.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x209-tensor | 172,634 | 1.00x | tensor | 2,123.78 | 425.3 | 1,701.3 | link_latency | 13.82x | 36.20x | 142.75x | 13.82x |
| MiMo-V2.6-Pro | 4 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x132 | 107,580 | 3,002.9 | 12,011.7 | link_latency | MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | 107,380 | 1.00x | tensor | 2,105.79 | 406.2 | 1,624.9 | link_latency | 7.39x | 2.24x | 72.94x | 7.39x |
| MiMo-V2.6-Pro | 8 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x212 | 172,780 | 5,877.1 | 311,488.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x209-tensor | 172,634 | 1.00x | tensor | 2,979.16 | 300.7 | 2,405.2 | link_latency | 19.55x | 36.20x | 142.75x | 19.55x |
| MiMo-V2.6-Pro | 8 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x132 | 107,580 | 2,026.7 | 16,213.5 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | 107,380 | 1.00x | tensor | 2,943.18 | 286.4 | 2,291.4 | link_latency | 7.08x | 3.03x | 49.23x | 7.08x |
| MiMo-V2.6-Pro | 16 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x212 | 172,780 | 5,877.1 | 311,488.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x209-hybrid | 172,634 | 1.00x | hybrid | 780.61 | 255.8 | 6,906.2 | weight_read | 22.98x | 36.20x | 142.75x | 22.98x |
| MiMo-V2.6-Pro | 16 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x132 | 107,580 | 1,228.1 | 19,650.3 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 755.40 | 254.9 | 4,334.0 | weight_read | 4.82x | 3.67x | 29.83x | 4.82x |
| MiMo-V2.6-Pro | 32 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x212 | 172,780 | 5,877.1 | 311,488.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x209-hybrid | 172,634 | 1.00x | hybrid | 785.77 | 245.1 | 7,843.7 | weight_read | 23.98x | 36.20x | 142.75x | 23.98x |
| MiMo-V2.6-Pro | 32 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 817.9 | 26,989.9 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 775.62 | 211.3 | 6,761.1 | weight_read | 3.87x | 3.99x | 19.87x | 3.87x |
| MiMo-V2.6-Pro | 64 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x252-romfill | 205,380 | 5,479.6 | 350,691.5 | weight_read | MiMo-V2.6-Pro/a100_sxm_80gb-x249-hybrid | 205,674 | 1.00x | hybrid | 823.51 | 207.7 | 13,290.8 | weight_read | 26.39x | 26.39x | 133.09x | 26.39x |
| MiMo-V2.6-Pro | 64 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x132 | 107,580 | 425.4 | 27,225.0 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | 107,380 | 1.00x | hybrid | 818.76 | 155.9 | 9,975.6 | weight_read | 2.73x | 2.73x | 10.33x | 2.73x |
| MiMo-V2.6-Pro | 256 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill | 308,070 | 2,663.9 | 681,969.4 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | 308,098 | 1.00x | hybrid | 998.52 | 129.0 | 33,015.0 | weight_read | 20.66x | 20.66x | 64.70x | 20.66x |
| MiMo-V2.6-Pro | 256 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x132 | 107,580 | 107.2 | 27,452.3 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-expert | 107,380 | 1.00x | expert | 2,309.11 | 84.3 | 21,587.1 | weight_read | 1.27x | 1.27x | 3.32x | 1.27x |
| MiMo-V2.6-Pro | 1024 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378 | 308,070 | 999.0 | 1,022,965.3 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x373-expert | 308,098 | 1.00x | expert | 2,830.59 | 100.6 | 102,963.9 | weight_read | 9.94x | 9.94x | 36.11x | 9.94x |
| MiMo-V2.6-Pro | 1024 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x132 | 107,580 | 26.8 | 27,492.1 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-expert | 107,380 | 1.00x | expert | 6,283.84 | 57.2 | 58,528.0 | weight_read | 0.47x | 0.47x | 1.84x | 0.47x |
| MiMo-V2.6-Pro | 4096 | fastest | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 259.0 | 1,060,857.6 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x373-expert | 308,098 | 1.00x | expert | 8,369.75 | 56.3 | 230,451.3 | link_latency | 4.60x | 4.60x | 22.49x | 4.60x |
| MiMo-V2.6-Pro | 4096 | smallest silicon | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x132 | 107,580 | 6.7 | 27,502.1 | compute | MiMo-V2.6-Pro/a100_sxm_80gb-x130-expert | 107,380 | 1.00x | expert | 22,182.78 | 24.5 | 100,310.8 | link_latency | 0.27x | 0.27x | 1.22x | 0.27x |

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
| MiMo-V2.6-Pro | 34 | 28,084 | 41.3 | 460.2 | 233.4 | tensor | 1,448.60 | 66.7% | link_latency |
| MiMo-V2.6-Pro | 56 | 46,256 | 41.2 | 524.5 | 266.1 | tensor | 1,460.40 | 76.6% | link_latency |
| MiMo-V2.6-Pro | 59 | 48,734 | 41.2 | 529.6 | 249.0 | tensor | 1,464.09 | 77.5% | link_latency |
| MiMo-V2.6-Pro | 65 | 53,690 | 41.2 | 539.5 | 244.6 | tensor | 1,466.95 | 79.1% | link_latency |
| MiMo-V2.6-Pro | 66 | 54,516 | 41.2 | 541.2 | 247.7 | tensor | 1,466.95 | 79.4% | link_latency |
| MiMo-V2.6-Pro | 67 | 55,342 | 41.2 | 542.8 | 250.7 | tensor | 1,466.95 | 79.6% | link_latency |
| MiMo-V2.6-Pro | 88 | 72,688 | 41.2 | 567.9 | 265.4 | tensor | 1,471.12 | 83.6% | link_latency |
| MiMo-V2.6-Pro | 112 | 92,512 | 41.2 | 586.1 | 264.8 | tensor | 1,475.15 | 86.5% | link_latency |
| MiMo-V2.6-Pro | 120 | 99,120 | 41.2 | 590.8 | 264.7 | tensor | 1,476.13 | 87.2% | link_latency |
| MiMo-V2.6-Pro | 130 | 107,380 | 41.2 | 595.6 | 254.9 | tensor | 1,477.75 | 88.0% | link_latency |
| MiMo-V2.6-Pro | 133 | 109,858 | 41.2 | 597.1 | 259.6 | tensor | 1,477.75 | 88.2% | link_latency |
| MiMo-V2.6-Pro | 135 | 111,510 | 41.2 | 598.1 | 262.8 | tensor | 1,477.75 | 88.4% | link_latency |
| MiMo-V2.6-Pro | 136 | 112,336 | 41.2 | 598.5 | 264.3 | tensor | 1,477.75 | 88.4% | link_latency |
| MiMo-V2.6-Pro | 138 | 113,988 | 41.2 | 599.2 | 255.3 | tensor | 1,478.42 | 88.6% | link_latency |
| MiMo-V2.6-Pro | 145 | 119,770 | 41.2 | 602.0 | 254.2 | tensor | 1,479.03 | 89.0% | link_latency |
| MiMo-V2.6-Pro | 156 | 128,856 | 41.2 | 606.1 | 258.5 | tensor | 1,479.57 | 89.7% | link_latency |
| MiMo-V2.6-Pro | 168 | 138,768 | 41.2 | 610.0 | 263.6 | tensor | 1,480.06 | 90.3% | link_latency |
| MiMo-V2.6-Pro | 174 | 143,724 | 41.2 | 611.7 | 261.1 | tensor | 1,480.51 | 90.6% | link_latency |
| MiMo-V2.6-Pro | 179 | 147,854 | 41.2 | 613.0 | 257.6 | tensor | 1,480.92 | 90.8% | link_latency |
| MiMo-V2.6-Pro | 186 | 153,636 | 41.2 | 614.8 | 256.5 | tensor | 1,481.29 | 91.1% | link_latency |
| MiMo-V2.6-Pro | 208 | 171,808 | 41.2 | 619.7 | 262.7 | tensor | 1,481.95 | 91.8% | link_latency |
| MiMo-V2.6-Pro | 209 | 172,634 | 41.2 | 619.8 | 255.8 | tensor | 1,482.25 | 91.9% | link_latency |
| MiMo-V2.6-Pro | 224 | 185,024 | 41.2 | 622.7 | 262.4 | tensor | 1,482.52 | 92.3% | link_latency |
| MiMo-V2.6-Pro | 231 | 190,806 | 41.2 | 623.9 | 261.3 | tensor | 1,482.77 | 92.5% | link_latency |
| MiMo-V2.6-Pro | 249 | 205,674 | 41.2 | 626.6 | 256.0 | tensor | 1,483.44 | 92.9% | link_latency |
| MiMo-V2.6-Pro | 335 | 276,710 | 41.2 | 467.0 | 259.4 | tensor | 2,053.38 | 95.9% | link_latency |
| MiMo-V2.6-Pro | 336 | 277,536 | 41.2 | 467.1 | 260.0 | tensor | 2,053.38 | 95.9% | link_latency |
| MiMo-V2.6-Pro | 346 | 285,796 | 41.2 | 467.5 | 256.2 | tensor | 2,053.60 | 96.0% | link_latency |
| MiMo-V2.6-Pro | 373 | 308,098 | 41.2 | 468.5 | 257.5 | tensor | 2,053.90 | 96.2% | link_latency |
| MiMo-V2.6-Pro | 448 | 370,048 | 41.2 | 470.8 | 257.6 | tensor | 2,054.60 | 96.7% | link_latency |
| MiMo-V2.6-Pro | 672 | 555,072 | 41.2 | 474.5 | 255.3 | tensor | 2,055.83 | 97.5% | link_latency |

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
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x137 | MiMo-V2.6-Pro | 137 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x132 | MiMo-V2.6-Pro | 132 | tensor | rom_package_ucie | rom_board_serdes | 280 | 160.55 us | 622.9 tok/s | 6,228.7 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 33 on rom_board_serdes (traversals 11.0) = 156.78 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x138 | MiMo-V2.6-Pro | 138 | hybrid | rom_package_ucie | rom_board_serdes | 174 | 7.40 us | 13,513.9 tok/s | 135,139.0 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 34 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 3.63 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x137 | MiMo-V2.6-Pro | 137 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3 | MiMo-V2.6-Pro | 3 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-tensor-x122 | MiMo-V2.6-Pro | 122 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.99 us | 67.7 tok/s | 677.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 16 on infiniband_hdr (traversals 2.0) = 761.94 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x3 | MiMo-V2.6-Pro | 3 | tensor | on_wafer | rom_wafer_serdes | 280 | 300.87 us | 332.4 tok/s | 3,323.7 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 3 on rom_wafer_serdes (traversals 2.2) = 31.37 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hybrid-x135 | MiMo-V2.6-Pro | 135 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-hybrid-x3 | MiMo-V2.6-Pro | 3 | hybrid | on_wafer | rom_wafer_serdes | 142 | 269.70 us | 370.8 tok/s | 3,707.8 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 2 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.20 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x212 | MiMo-V2.6-Pro | 212 | pipeline | rom_package_ucie | rom_board_serdes | 69 | 2.50 us | 40,067.4 tok/s | 400,673.6 tok/s | 52 x point_to_point span 2 on rom_package_ucie (traversals 1.0) = 0.68 us; 17 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 1.82 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x140 | MiMo-V2.6-Pro | 140 | tensor | rom_package_ucie | rom_board_serdes | 280 | 160.55 us | 622.8 tok/s | 6,228.5 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 140 x all_reduce span 35 on rom_board_serdes (traversals 11.0) = 156.79 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | MiMo-V2.6-Pro | 211 | hybrid | rom_package_ucie | rom_board_serdes | 192 | 9.32 us | 10,726.5 tok/s | 107,265.4 tok/s | 140 x all_reduce span 4 on rom_package_ucie (traversals 2.0) = 3.77 us; 52 x point_to_point span 2 on rom_board_serdes (traversals 1.0) = 5.55 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-pipeline-x211 | MiMo-V2.6-Pro | 211 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4 | MiMo-V2.6-Pro | 4 | pipeline | on_wafer | rom_wafer_serdes | 69 | 8.60 us | 11,625.1 tok/s | 116,251.0 tok/s | 68 x point_to_point span 2 on on_wafer (traversals 1.0) = 8.50 us; 1 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.10 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-tensor-x132 | MiMo-V2.6-Pro | 132 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-tensor-x4 | MiMo-V2.6-Pro | 4 | tensor | on_wafer | rom_wafer_serdes | 280 | 300.95 us | 332.3 tok/s | 3,322.9 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 140 x all_reduce span 4 on rom_wafer_serdes (traversals 2.2) = 31.45 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hybrid-x181 | MiMo-V2.6-Pro | 181 | hybrid | nvlink3 | infiniband_hdr | 162 | 770.53 us | 129.8 tok/s | 1,297.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.47 us |
| MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-hybrid-x4 | MiMo-V2.6-Pro | 4 | hybrid | on_wafer | rom_wafer_serdes | 143 | 269.81 us | 370.6 tok/s | 3,706.4 tok/s | 140 x all_reduce span 57 on on_wafer (traversals 15.4) = 269.50 us; 3 x point_to_point span 2 on rom_wafer_serdes (traversals 1.0) = 0.31 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-pipeline | MiMo-V2.6-Pro | 34 | pipeline | nvlink3 | infiniband_hdr | 33 | 83.77 us | 1,193.7 tok/s | 11,936.9 tok/s | 29 x point_to_point span 2 on nvlink3 (traversals 1.0) = 73.69 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 10.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-tensor | MiMo-V2.6-Pro | 34 | tensor | nvlink3 | infiniband_hdr | 280 | 1,448.60 us | 69.0 tok/s | 690.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 5 on infiniband_hdr (traversals 2.0) = 733.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-hybrid | MiMo-V2.6-Pro | 34 | hybrid | nvlink3 | infiniband_hdr | 144 | 725.14 us | 137.9 tok/s | 1,379.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 4 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 10.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x34-expert | MiMo-V2.6-Pro | 34 | expert | nvlink3 | infiniband_hdr | 280 | 1,004.15 us | 99.6 tok/s | 995.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 703.76 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 300.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-pipeline | MiMo-V2.6-Pro | 56 | pipeline | nvlink3 | infiniband_hdr | 55 | 139.64 us | 716.1 tok/s | 7,161.5 tok/s | 49 x point_to_point span 2 on nvlink3 (traversals 1.0) = 124.51 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-tensor | MiMo-V2.6-Pro | 56 | tensor | nvlink3 | infiniband_hdr | 280 | 1,460.40 us | 68.5 tok/s | 684.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 7 on infiniband_hdr (traversals 2.0) = 745.35 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-hybrid | MiMo-V2.6-Pro | 56 | hybrid | nvlink3 | infiniband_hdr | 146 | 730.18 us | 137.0 tok/s | 1,369.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 6 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 15.13 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x56-expert | MiMo-V2.6-Pro | 56 | expert | nvlink3 | infiniband_hdr | 280 | 996.18 us | 100.4 tok/s | 1,003.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 702.15 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 294.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-pipeline | MiMo-V2.6-Pro | 59 | pipeline | nvlink3 | infiniband_hdr | 58 | 147.24 us | 679.2 tok/s | 6,791.7 tok/s | 51 x point_to_point span 2 on nvlink3 (traversals 1.0) = 129.59 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.65 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-tensor | MiMo-V2.6-Pro | 59 | tensor | nvlink3 | infiniband_hdr | 280 | 1,464.09 us | 68.3 tok/s | 683.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 8 on infiniband_hdr (traversals 2.0) = 749.03 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-hybrid | MiMo-V2.6-Pro | 59 | hybrid | nvlink3 | infiniband_hdr | 147 | 732.70 us | 136.5 tok/s | 1,364.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 7 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 17.65 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x59-expert | MiMo-V2.6-Pro | 59 | expert | nvlink3 | infiniband_hdr | 280 | 995.68 us | 100.4 tok/s | 1,004.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 702.15 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 293.53 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-pipeline | MiMo-V2.6-Pro | 65 | pipeline | nvlink3 | infiniband_hdr | 64 | 162.47 us | 615.5 tok/s | 6,155.1 tok/s | 56 x point_to_point span 2 on nvlink3 (traversals 1.0) = 142.29 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-tensor | MiMo-V2.6-Pro | 65 | tensor | nvlink3 | infiniband_hdr | 280 | 1,466.95 us | 68.2 tok/s | 681.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 751.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-hybrid | MiMo-V2.6-Pro | 65 | hybrid | nvlink3 | infiniband_hdr | 148 | 735.22 us | 136.0 tok/s | 1,360.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x65-expert | MiMo-V2.6-Pro | 65 | expert | nvlink3 | infiniband_hdr | 280 | 994.55 us | 100.5 tok/s | 1,005.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.88 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 292.67 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-pipeline | MiMo-V2.6-Pro | 66 | pipeline | nvlink3 | infiniband_hdr | 65 | 165.01 us | 606.0 tok/s | 6,060.4 tok/s | 57 x point_to_point span 2 on nvlink3 (traversals 1.0) = 144.83 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-tensor | MiMo-V2.6-Pro | 66 | tensor | nvlink3 | infiniband_hdr | 280 | 1,466.95 us | 68.2 tok/s | 681.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 751.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-hybrid | MiMo-V2.6-Pro | 66 | hybrid | nvlink3 | infiniband_hdr | 148 | 735.22 us | 136.0 tok/s | 1,360.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x66-expert | MiMo-V2.6-Pro | 66 | expert | nvlink3 | infiniband_hdr | 280 | 994.42 us | 100.6 tok/s | 1,005.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.88 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 292.54 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x67-pipeline | MiMo-V2.6-Pro | 67 | pipeline | nvlink3 | infiniband_hdr | 66 | 167.55 us | 596.8 tok/s | 5,968.4 tok/s | 58 x point_to_point span 2 on nvlink3 (traversals 1.0) = 147.38 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x67-tensor | MiMo-V2.6-Pro | 67 | tensor | nvlink3 | infiniband_hdr | 280 | 1,466.95 us | 68.2 tok/s | 681.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 9 on infiniband_hdr (traversals 2.0) = 751.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x67-hybrid | MiMo-V2.6-Pro | 67 | hybrid | nvlink3 | infiniband_hdr | 148 | 735.22 us | 136.0 tok/s | 1,360.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x67-expert | MiMo-V2.6-Pro | 67 | expert | nvlink3 | infiniband_hdr | 280 | 994.30 us | 100.6 tok/s | 1,005.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.88 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 292.42 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x88-pipeline | MiMo-V2.6-Pro | 88 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x88-tensor | MiMo-V2.6-Pro | 88 | tensor | nvlink3 | infiniband_hdr | 280 | 1,471.12 us | 68.0 tok/s | 679.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 11 on infiniband_hdr (traversals 2.0) = 756.07 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x88-hybrid | MiMo-V2.6-Pro | 88 | hybrid | nvlink3 | infiniband_hdr | 150 | 740.27 us | 135.1 tok/s | 1,350.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 10 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 25.22 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x88-expert | MiMo-V2.6-Pro | 88 | expert | nvlink3 | infiniband_hdr | 280 | 991.82 us | 100.8 tok/s | 1,008.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.37 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 290.46 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-pipeline | MiMo-V2.6-Pro | 112 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-tensor | MiMo-V2.6-Pro | 112 | tensor | nvlink3 | infiniband_hdr | 280 | 1,475.15 us | 67.8 tok/s | 677.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 14 on infiniband_hdr (traversals 2.0) = 760.09 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-hybrid | MiMo-V2.6-Pro | 112 | hybrid | nvlink3 | infiniband_hdr | 153 | 747.83 us | 133.7 tok/s | 1,337.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 13 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 32.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x112-expert | MiMo-V2.6-Pro | 112 | expert | nvlink3 | infiniband_hdr | 280 | 990.19 us | 101.0 tok/s | 1,009.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.08 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 289.12 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-pipeline | MiMo-V2.6-Pro | 120 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-tensor | MiMo-V2.6-Pro | 120 | tensor | nvlink3 | infiniband_hdr | 280 | 1,476.13 us | 67.7 tok/s | 677.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 15 on infiniband_hdr (traversals 2.0) = 761.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-hybrid | MiMo-V2.6-Pro | 120 | hybrid | nvlink3 | infiniband_hdr | 154 | 750.35 us | 133.3 tok/s | 1,332.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 14 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 35.30 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x120-expert | MiMo-V2.6-Pro | 120 | expert | nvlink3 | infiniband_hdr | 280 | 989.79 us | 101.0 tok/s | 1,010.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 701.00 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.79 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-pipeline | MiMo-V2.6-Pro | 130 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-tensor | MiMo-V2.6-Pro | 130 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-hybrid | MiMo-V2.6-Pro | 130 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x130-expert | MiMo-V2.6-Pro | 130 | expert | nvlink3 | infiniband_hdr | 280 | 989.38 us | 101.1 tok/s | 1,010.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-pipeline | MiMo-V2.6-Pro | 133 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-tensor | MiMo-V2.6-Pro | 133 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-hybrid | MiMo-V2.6-Pro | 133 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x133-expert | MiMo-V2.6-Pro | 133 | expert | nvlink3 | infiniband_hdr | 280 | 989.28 us | 101.1 tok/s | 1,010.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x135-pipeline | MiMo-V2.6-Pro | 135 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x135-tensor | MiMo-V2.6-Pro | 135 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x135-hybrid | MiMo-V2.6-Pro | 135 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x135-expert | MiMo-V2.6-Pro | 135 | expert | nvlink3 | infiniband_hdr | 280 | 989.22 us | 101.1 tok/s | 1,010.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.94 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.28 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x136-pipeline | MiMo-V2.6-Pro | 136 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x136-tensor | MiMo-V2.6-Pro | 136 | tensor | nvlink3 | infiniband_hdr | 280 | 1,477.75 us | 67.7 tok/s | 676.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 17 on infiniband_hdr (traversals 2.0) = 762.69 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x136-hybrid | MiMo-V2.6-Pro | 136 | hybrid | nvlink3 | infiniband_hdr | 156 | 755.40 us | 132.4 tok/s | 1,323.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 16 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 40.34 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x136-expert | MiMo-V2.6-Pro | 136 | expert | nvlink3 | infiniband_hdr | 280 | 989.13 us | 101.1 tok/s | 1,011.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.89 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.25 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x138-pipeline | MiMo-V2.6-Pro | 138 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x138-tensor | MiMo-V2.6-Pro | 138 | tensor | nvlink3 | infiniband_hdr | 280 | 1,478.42 us | 67.6 tok/s | 676.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 18 on infiniband_hdr (traversals 2.0) = 763.37 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x138-hybrid | MiMo-V2.6-Pro | 138 | hybrid | nvlink3 | infiniband_hdr | 157 | 757.92 us | 131.9 tok/s | 1,319.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 17 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 42.87 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x138-expert | MiMo-V2.6-Pro | 138 | expert | nvlink3 | infiniband_hdr | 280 | 989.07 us | 101.1 tok/s | 1,011.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.89 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.19 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-pipeline | MiMo-V2.6-Pro | 145 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-tensor | MiMo-V2.6-Pro | 145 | tensor | nvlink3 | infiniband_hdr | 280 | 1,479.03 us | 67.6 tok/s | 676.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 19 on infiniband_hdr (traversals 2.0) = 763.97 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-hybrid | MiMo-V2.6-Pro | 145 | hybrid | nvlink3 | infiniband_hdr | 158 | 760.44 us | 131.5 tok/s | 1,315.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 18 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 45.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x145-expert | MiMo-V2.6-Pro | 145 | expert | nvlink3 | infiniband_hdr | 280 | 988.83 us | 101.1 tok/s | 1,011.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.84 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 288.00 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-pipeline | MiMo-V2.6-Pro | 156 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-tensor | MiMo-V2.6-Pro | 156 | tensor | nvlink3 | infiniband_hdr | 280 | 1,479.57 us | 67.6 tok/s | 675.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 20 on infiniband_hdr (traversals 2.0) = 764.52 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-hybrid | MiMo-V2.6-Pro | 156 | hybrid | nvlink3 | infiniband_hdr | 159 | 762.96 us | 131.1 tok/s | 1,310.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 19 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 47.91 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x156-expert | MiMo-V2.6-Pro | 156 | expert | nvlink3 | infiniband_hdr | 280 | 988.52 us | 101.2 tok/s | 1,011.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.79 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.73 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-pipeline | MiMo-V2.6-Pro | 168 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-tensor | MiMo-V2.6-Pro | 168 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.06 us | 67.6 tok/s | 675.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 21 on infiniband_hdr (traversals 2.0) = 765.01 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-hybrid | MiMo-V2.6-Pro | 168 | hybrid | nvlink3 | infiniband_hdr | 160 | 765.48 us | 130.6 tok/s | 1,306.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 20 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 50.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x168-expert | MiMo-V2.6-Pro | 168 | expert | nvlink3 | infiniband_hdr | 280 | 988.19 us | 101.2 tok/s | 1,011.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.48 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-pipeline | MiMo-V2.6-Pro | 174 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-tensor | MiMo-V2.6-Pro | 174 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.51 us | 67.5 tok/s | 675.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 22 on infiniband_hdr (traversals 2.0) = 765.45 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-hybrid | MiMo-V2.6-Pro | 174 | hybrid | nvlink3 | infiniband_hdr | 161 | 768.00 us | 130.2 tok/s | 1,302.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 21 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 52.95 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x174-expert | MiMo-V2.6-Pro | 174 | expert | nvlink3 | infiniband_hdr | 280 | 988.08 us | 101.2 tok/s | 1,012.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.72 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.36 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x179-pipeline | MiMo-V2.6-Pro | 179 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x179-tensor | MiMo-V2.6-Pro | 179 | tensor | nvlink3 | infiniband_hdr | 280 | 1,480.92 us | 67.5 tok/s | 675.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 23 on infiniband_hdr (traversals 2.0) = 765.86 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x179-hybrid | MiMo-V2.6-Pro | 179 | hybrid | nvlink3 | infiniband_hdr | 162 | 770.53 us | 129.8 tok/s | 1,297.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 22 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 55.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x179-expert | MiMo-V2.6-Pro | 179 | expert | nvlink3 | infiniband_hdr | 280 | 987.96 us | 101.2 tok/s | 1,012.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.68 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.28 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-pipeline | MiMo-V2.6-Pro | 186 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-tensor | MiMo-V2.6-Pro | 186 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.29 us | 67.5 tok/s | 675.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 24 on infiniband_hdr (traversals 2.0) = 766.24 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-hybrid | MiMo-V2.6-Pro | 186 | hybrid | nvlink3 | infiniband_hdr | 163 | 773.05 us | 129.4 tok/s | 1,293.6 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 23 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 57.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x186-expert | MiMo-V2.6-Pro | 186 | expert | nvlink3 | infiniband_hdr | 280 | 987.81 us | 101.2 tok/s | 1,012.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.65 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 287.16 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-pipeline | MiMo-V2.6-Pro | 208 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-tensor | MiMo-V2.6-Pro | 208 | tensor | nvlink3 | infiniband_hdr | 280 | 1,481.95 us | 67.5 tok/s | 674.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 26 on infiniband_hdr (traversals 2.0) = 766.90 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-hybrid | MiMo-V2.6-Pro | 208 | hybrid | nvlink3 | infiniband_hdr | 165 | 778.09 us | 128.5 tok/s | 1,285.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 25 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 63.04 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x208-expert | MiMo-V2.6-Pro | 208 | expert | nvlink3 | infiniband_hdr | 280 | 987.43 us | 101.3 tok/s | 1,012.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.58 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.85 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x209-pipeline | MiMo-V2.6-Pro | 209 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x209-tensor | MiMo-V2.6-Pro | 209 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.25 us | 67.5 tok/s | 674.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 27 on infiniband_hdr (traversals 2.0) = 767.19 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x209-hybrid | MiMo-V2.6-Pro | 209 | hybrid | nvlink3 | infiniband_hdr | 166 | 780.61 us | 128.1 tok/s | 1,281.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 26 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 65.56 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x209-expert | MiMo-V2.6-Pro | 209 | expert | nvlink3 | infiniband_hdr | 280 | 987.41 us | 101.3 tok/s | 1,012.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.58 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.83 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-pipeline | MiMo-V2.6-Pro | 224 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-tensor | MiMo-V2.6-Pro | 224 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.52 us | 67.5 tok/s | 674.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 28 on infiniband_hdr (traversals 2.0) = 767.47 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-hybrid | MiMo-V2.6-Pro | 224 | hybrid | nvlink3 | infiniband_hdr | 167 | 783.13 us | 127.7 tok/s | 1,276.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 27 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 68.08 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x224-expert | MiMo-V2.6-Pro | 224 | expert | nvlink3 | infiniband_hdr | 280 | 987.20 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.66 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-pipeline | MiMo-V2.6-Pro | 231 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-tensor | MiMo-V2.6-Pro | 231 | tensor | nvlink3 | infiniband_hdr | 280 | 1,482.77 us | 67.4 tok/s | 674.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 29 on infiniband_hdr (traversals 2.0) = 767.72 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-hybrid | MiMo-V2.6-Pro | 231 | hybrid | nvlink3 | infiniband_hdr | 168 | 785.66 us | 127.3 tok/s | 1,272.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 28 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 70.60 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x231-expert | MiMo-V2.6-Pro | 231 | expert | nvlink3 | infiniband_hdr | 280 | 987.12 us | 101.3 tok/s | 1,013.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.54 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.58 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-pipeline | MiMo-V2.6-Pro | 249 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-tensor | MiMo-V2.6-Pro | 249 | tensor | nvlink3 | infiniband_hdr | 280 | 1,483.44 us | 67.4 tok/s | 674.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 32 on infiniband_hdr (traversals 2.0) = 768.39 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-hybrid | MiMo-V2.6-Pro | 249 | hybrid | nvlink3 | infiniband_hdr | 171 | 793.22 us | 126.1 tok/s | 1,260.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 31 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 78.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x249-expert | MiMo-V2.6-Pro | 249 | expert | nvlink3 | infiniband_hdr | 280 | 986.90 us | 101.3 tok/s | 1,013.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.49 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 286.41 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-pipeline | MiMo-V2.6-Pro | 335 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-tensor | MiMo-V2.6-Pro | 335 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-hybrid | MiMo-V2.6-Pro | 335 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x335-expert | MiMo-V2.6-Pro | 335 | expert | nvlink3 | infiniband_hdr | 280 | 986.21 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.37 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-pipeline | MiMo-V2.6-Pro | 336 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-tensor | MiMo-V2.6-Pro | 336 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.38 us | 48.7 tok/s | 487.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 42 on infiniband_hdr (traversals 4.0) = 1,338.32 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-hybrid | MiMo-V2.6-Pro | 336 | hybrid | nvlink3 | infiniband_hdr | 181 | 818.44 us | 122.2 tok/s | 1,221.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 41 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 103.38 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x336-expert | MiMo-V2.6-Pro | 336 | expert | nvlink3 | infiniband_hdr | 280 | 986.20 us | 101.4 tok/s | 1,014.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.36 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.84 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-pipeline | MiMo-V2.6-Pro | 346 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-tensor | MiMo-V2.6-Pro | 346 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.60 us | 48.7 tok/s | 486.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 44 on infiniband_hdr (traversals 4.0) = 1,338.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-hybrid | MiMo-V2.6-Pro | 346 | hybrid | nvlink3 | infiniband_hdr | 183 | 823.48 us | 121.4 tok/s | 1,214.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 43 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 108.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x346-expert | MiMo-V2.6-Pro | 346 | expert | nvlink3 | infiniband_hdr | 280 | 986.14 us | 101.4 tok/s | 1,014.1 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.35 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.79 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-pipeline | MiMo-V2.6-Pro | 373 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-tensor | MiMo-V2.6-Pro | 373 | tensor | nvlink3 | infiniband_hdr | 280 | 2,053.90 us | 48.7 tok/s | 486.9 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 47 on infiniband_hdr (traversals 4.0) = 1,338.85 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-hybrid | MiMo-V2.6-Pro | 373 | hybrid | nvlink3 | infiniband_hdr | 186 | 831.04 us | 120.3 tok/s | 1,203.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 46 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 115.99 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x373-expert | MiMo-V2.6-Pro | 373 | expert | nvlink3 | infiniband_hdr | 280 | 986.00 us | 101.4 tok/s | 1,014.2 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.33 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-pipeline | MiMo-V2.6-Pro | 448 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-tensor | MiMo-V2.6-Pro | 448 | tensor | nvlink3 | infiniband_hdr | 280 | 2,054.60 us | 48.7 tok/s | 486.7 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 56 on infiniband_hdr (traversals 4.0) = 1,339.55 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-hybrid | MiMo-V2.6-Pro | 448 | hybrid | nvlink3 | infiniband_hdr | 195 | 853.74 us | 117.1 tok/s | 1,171.3 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 55 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 138.68 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x448-expert | MiMo-V2.6-Pro | 448 | expert | nvlink3 | infiniband_hdr | 280 | 985.70 us | 101.5 tok/s | 1,014.5 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.27 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.43 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-pipeline | MiMo-V2.6-Pro | 672 | pipeline | nvlink3 | infiniband_hdr | 69 | 175.17 us | 570.9 tok/s | 5,708.7 tok/s | 61 x point_to_point span 2 on nvlink3 (traversals 1.0) = 155.00 us; 8 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 20.17 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-tensor | MiMo-V2.6-Pro | 672 | tensor | nvlink3 | infiniband_hdr | 280 | 2,055.83 us | 48.6 tok/s | 486.4 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 140 x all_reduce span 84 on infiniband_hdr (traversals 4.0) = 1,340.78 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-hybrid | MiMo-V2.6-Pro | 672 | hybrid | nvlink3 | infiniband_hdr | 209 | 889.04 us | 112.5 tok/s | 1,124.8 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 715.05 us; 69 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 173.98 us |
| MiMo-V2.6-Pro/a100_sxm_80gb-x672-expert | MiMo-V2.6-Pro | 672 | expert | nvlink3 | infiniband_hdr | 280 | 985.20 us | 101.5 tok/s | 1,015.0 tok/s | 140 x all_reduce span 8 on nvlink3 (traversals 2.0) = 700.18 us; 140 x point_to_point span 2 on infiniband_hdr (traversals 1.0) = 285.02 us |

## Topology choice at each operating point

Selection rule: the smallest silicon area within 5% of the best
per-user rate at that point, so a topology cannot win by simply being
given more silicon.

| Model | B | Winner on rate | Winner per mm2 | Best design | Best mm2 | Best user tok/s | tok/s per mm2 | Best array tok/s (mm2) | Best wafer tok/s (mm2) | Wafer/array | Binds on |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|
| MiMo-V2.6-Pro | 1 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 5,819.1 | 0.034 | 5,819.1 (171,965) | 3,160.2 (138,675) | 0.54x | compute |
| MiMo-V2.6-Pro | 2 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 5,819.1 | 0.034 | 5,819.1 (171,965) | 3,145.4 (184,900) | 0.54x | compute |
| MiMo-V2.6-Pro | 4 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 5,819.1 | 0.034 | 5,819.1 (171,965) | 3,145.4 (184,900) | 0.54x | compute |
| MiMo-V2.6-Pro | 8 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 5,819.1 | 0.034 | 5,819.1 (171,965) | 3,040.3 (277,350) | 0.52x | compute |
| MiMo-V2.6-Pro | 16 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 5,819.1 | 0.034 | 5,819.1 (171,965) | 3,034.7 (554,700) | 0.52x | compute |
| MiMo-V2.6-Pro | 32 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x211 | 171,965 | 5,819.1 | 0.034 | 5,819.1 (171,965) | 2,683.4 (554,700) | 0.46x | compute |
| MiMo-V2.6-Pro | 64 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x227 | 185,005 | 5,476.3 | 0.030 | 5,476.3 (185,005) | 2,179.1 (554,700) | 0.40x | weight_read |
| MiMo-V2.6-Pro | 256 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 2,630.6 | 0.009 | 2,630.6 (277,100) | 1,024.1 (554,700) | 0.39x | weight_read |
| MiMo-V2.6-Pro | 1024 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378 | 308,070 | 999.0 | 0.003 | 999.0 (308,070) | 359.4 (554,700) | 0.36x | compute |
| MiMo-V2.6-Pro | 4096 | array | array | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 259.0 | 0.001 | 259.0 (308,070) | 90.4 (554,700) | 0.35x | compute |

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
| MiMo-V2.6-Pro | 1 | sram | 369,003.3 | 26,040.1 | 26,040.1 | 14.17x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | sram | 369,003.3 | 26,040.1 | 26,040.1 | 14.17x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | sram | 369,003.3 | 26,040.1 | 26,040.1 | 14.17x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | sram | 369,003.3 | 26,040.1 | 31,534.2 | 14.17x | 1.21x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 16 | sram | 369,003.3 | 26,040.1 | 51,338.3 | 14.17x | 1.97x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 32 | sram | 369,003.3 | 26,040.1 | 77,633.7 | 14.17x | 2.98x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 64 | sram | 369,003.3 | 26,040.1 | 113,813.9 | 14.17x | 4.37x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 256 | sram | 673,425.3 | 26,062.9 | 136,794.5 | 25.84x | 5.25x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 1024 | sram | 1,022,965.3 | 26,098.6 | 232,834.1 | 39.20x | 8.92x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | sram | 1,060,857.6 | 26,109.1 | 236,959.3 | 40.63x | 9.08x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 1 | rom | 589,994.3 | 97,095.4 | 97,095.4 | 6.08x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 2 | rom | 589,994.3 | 97,095.4 | 97,095.4 | 6.08x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 4 | rom | 589,994.3 | 97,095.4 | 97,095.4 | 6.08x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 8 | rom | 589,994.3 | 97,095.4 | 97,095.4 | 6.08x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 16 | rom | 589,994.3 | 97,095.4 | 97,095.4 | 6.08x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 32 | rom | 589,994.3 | 97,095.4 | 97,095.4 | 6.08x | 1.00x | weight_read | weight_read | weight_read |
| MiMo-V2.6-Pro | 64 | rom | 589,994.3 | 97,095.4 | 110,507.0 | 6.08x | 1.14x | weight_read | weight_read | link_latency |
| MiMo-V2.6-Pro | 256 | rom | 681,969.4 | 97,210.3 | 158,357.7 | 7.02x | 1.63x | compute | weight_read | weight_read |
| MiMo-V2.6-Pro | 1024 | rom | 729,970.1 | 97,890.5 | 313,254.3 | 7.46x | 3.20x | compute | weight_read | kv_read |
| MiMo-V2.6-Pro | 4096 | rom | 737,070.7 | 98,062.1 | 319,399.2 | 7.52x | 3.26x | compute | weight_read | kv_read |

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
| MiMo-V2.6-Pro | 1 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 1 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 1 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 1 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 1 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 2 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 2 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 2 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 2 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 2 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 4 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 4 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 4 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 4 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 4 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 8 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 8 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 8 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 8 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 8 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x66-perregion | 53,790 | 1.00 | 2.16 | 31,534.2 | 0.586 | link_latency | 0.09x |
| MiMo-V2.6-Pro | 8 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 16 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 16 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 16 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 16 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 16 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x66-perregion | 53,790 | 1.00 | 2.90 | 51,338.3 | 0.954 | link_latency | 0.14x |
| MiMo-V2.6-Pro | 16 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 32 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 32 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 32 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 32 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 32 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x66-perregion | 53,790 | 1.00 | 4.00 | 77,633.7 | 1.443 | link_latency | 0.21x |
| MiMo-V2.6-Pro | 32 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perregion-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 64 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 369,003.3 | 1.198 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 64 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 589,994.3 | 1.915 | weight_read | 1.60x |
| MiMo-V2.6-Pro | 64 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 1.00 | 26,040.1 | 0.141 | weight_read | 0.07x |
| MiMo-V2.6-Pro | 64 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.00 | 97,095.4 | 0.525 | weight_read | 0.26x |
| MiMo-V2.6-Pro | 64 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-tensor-x2-perregion | 92,450 | 1.00 | 5.71 | 113,813.9 | 1.231 | link_latency | 0.31x |
| MiMo-V2.6-Pro | 64 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-tensor-x89-perregion-romfill | 72,535 | 1.35 | 5.71 | 110,507.0 | 1.523 | link_latency | 0.30x |
| MiMo-V2.6-Pro | 256 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x340 | 277,100 | 1.00 | 1.00 | 673,425.3 | 2.430 | weight_read | 1.00x |
| MiMo-V2.6-Pro | 256 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378-romfill | 308,070 | 1.62 | 1.00 | 681,969.4 | 2.214 | compute | 1.01x |
| MiMo-V2.6-Pro | 256 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x66-perstream | 53,790 | 1.00 | 3.88 | 26,062.9 | 0.485 | weight_read | 0.04x |
| MiMo-V2.6-Pro | 256 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 1.13 | 97,210.3 | 0.526 | weight_read | 0.14x |
| MiMo-V2.6-Pro | 256 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x66-perregion | 53,790 | 1.00 | 2.82 | 136,794.5 | 2.543 | weight_read | 0.20x |
| MiMo-V2.6-Pro | 256 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x89-perregion-romfill | 72,535 | 1.35 | 2.43 | 158,357.7 | 2.183 | weight_read | 0.24x |
| MiMo-V2.6-Pro | 1024 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x378 | 308,070 | 1.00 | 1.00 | 1,022,965.3 | 3.321 | compute | 1.00x |
| MiMo-V2.6-Pro | 1024 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 729,970.1 | 2.369 | compute | 0.71x |
| MiMo-V2.6-Pro | 1024 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x66-perstream | 53,790 | 1.00 | 15.52 | 26,098.6 | 0.485 | weight_read | 0.03x |
| MiMo-V2.6-Pro | 1024 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 4.51 | 97,890.5 | 0.529 | weight_read | 0.10x |
| MiMo-V2.6-Pro | 1024 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x66-perregion | 53,790 | 1.00 | 5.53 | 232,834.1 | 4.329 | kv_read | 0.23x |
| MiMo-V2.6-Pro | 1024 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-hybrid-x89-perregion-romfill | 72,535 | 1.35 | 4.71 | 313,254.3 | 4.319 | kv_read | 0.31x |
| MiMo-V2.6-Pro | 4096 | batched | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378 | 308,070 | 1.00 | 1.00 | 1,060,857.6 | 3.444 | compute | 1.00x |
| MiMo-V2.6-Pro | 4096 | batched | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x378-romfill | 308,070 | 1.62 | 1.00 | 737,070.7 | 2.393 | compute | 0.69x |
| MiMo-V2.6-Pro | 4096 | per_stream | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream | 184,900 | 1.00 | 18.04 | 26,109.1 | 0.141 | weight_read | 0.02x |
| MiMo-V2.6-Pro | 4096 | per_stream | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-wafer-pipeline-x4-perstream-romfill | 184,900 | 3.76 | 18.04 | 98,062.1 | 0.530 | weight_read | 0.09x |
| MiMo-V2.6-Pro | 4096 | per_region | sram | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x66-perregion | 53,790 | 1.00 | 5.62 | 236,959.3 | 4.405 | kv_read | 0.22x |
| MiMo-V2.6-Pro | 4096 | per_region | rom | MiMo-V2.6-Pro/ROM-N6-native-HBMKV-array-hw-pipeline-x89-perregion-romfill | 72,535 | 1.35 | 4.79 | 319,399.2 | 4.403 | kv_read | 0.30x |

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
| MiMo-V2.6-Pro | 1 | 60 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 2 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 4 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 8 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 16 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 32 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 64 | 114 | 1.00 | 1.000 | 1.000 | 1.00x |
| MiMo-V2.6-Pro | 256 | 66 | 3.88 | 1.031 | 1.606 | 1.56x |
| MiMo-V2.6-Pro | 1024 | 66 | 15.52 | 1.160 | 2.860 | 2.47x |
| MiMo-V2.6-Pro | 4096 | 66 | 62.06 | 1.773 | 5.617 | 3.17x |

### 2. Expert-parallel devices: the busiest device, not the mean engaged one

The same error on the GPU side of the comparison. A routed fetch
finishes when the most loaded device finishes, not when the average
of the engaged ones does. `opentallas.workload` is shared with
`opentallas.analytical` and is unchanged; the correction is applied
in `roofline` and both numbers are carried on every point, because
correcting only the ROM side would be its own bias.

| Model | B | Devices | Mean engaged | Effective | Correction |
|---|---:|---:|---:|---:|---:|
| MiMo-V2.6-Pro | 1 | 34 | 7.22 | 5.11 | 1.41x |
| MiMo-V2.6-Pro | 2 | 34 | 12.81 | 6.98 | 1.84x |
| MiMo-V2.6-Pro | 4 | 34 | 20.53 | 9.37 | 2.19x |
| MiMo-V2.6-Pro | 8 | 34 | 28.25 | 12.06 | 2.34x |
| MiMo-V2.6-Pro | 16 | 34 | 32.72 | 14.80 | 2.21x |
| MiMo-V2.6-Pro | 32 | 34 | 33.88 | 17.29 | 1.96x |
| MiMo-V2.6-Pro | 64 | 34 | 33.99 | 19.16 | 1.77x |
| MiMo-V2.6-Pro | 256 | 34 | 34.00 | 20.47 | 1.66x |
| MiMo-V2.6-Pro | 1024 | 34 | 34.00 | 20.49 | 1.66x |
| MiMo-V2.6-Pro | 1 | 56 | 7.52 | 5.76 | 1.31x |
| MiMo-V2.6-Pro | 2 | 56 | 13.90 | 8.00 | 1.74x |
| MiMo-V2.6-Pro | 4 | 56 | 23.97 | 11.25 | 2.13x |
| MiMo-V2.6-Pro | 8 | 56 | 36.84 | 15.03 | 2.45x |
| MiMo-V2.6-Pro | 16 | 56 | 48.26 | 19.16 | 2.52x |
| MiMo-V2.6-Pro | 32 | 56 | 54.12 | 23.13 | 2.34x |
| MiMo-V2.6-Pro | 64 | 56 | 55.67 | 26.26 | 2.12x |
| MiMo-V2.6-Pro | 256 | 56 | 55.94 | 28.52 | 1.96x |
| MiMo-V2.6-Pro | 1024 | 56 | 55.94 | 28.56 | 1.96x |
| MiMo-V2.6-Pro | 4096 | 56 | 55.94 | 28.56 | 1.96x |
| MiMo-V2.6-Pro | 1 | 59 | 7.54 | 5.82 | 1.30x |
| MiMo-V2.6-Pro | 2 | 59 | 13.99 | 8.10 | 1.73x |
| MiMo-V2.6-Pro | 4 | 59 | 24.28 | 11.45 | 2.12x |
| MiMo-V2.6-Pro | 8 | 59 | 37.67 | 15.35 | 2.45x |
| MiMo-V2.6-Pro | 16 | 59 | 49.97 | 19.65 | 2.54x |
| MiMo-V2.6-Pro | 32 | 59 | 56.64 | 23.80 | 2.38x |
| MiMo-V2.6-Pro | 64 | 59 | 58.54 | 27.09 | 2.16x |
| MiMo-V2.6-Pro | 256 | 59 | 58.91 | 29.48 | 2.00x |
| MiMo-V2.6-Pro | 1024 | 59 | 58.92 | 29.52 | 2.00x |
| MiMo-V2.6-Pro | 4096 | 59 | 58.92 | 29.52 | 2.00x |
| MiMo-V2.6-Pro | 1 | 65 | 7.58 | 5.94 | 1.28x |
| MiMo-V2.6-Pro | 2 | 65 | 14.15 | 8.31 | 1.70x |
| MiMo-V2.6-Pro | 4 | 65 | 24.81 | 11.82 | 2.10x |
| MiMo-V2.6-Pro | 8 | 65 | 39.17 | 15.96 | 2.45x |
| MiMo-V2.6-Pro | 16 | 65 | 53.16 | 20.57 | 2.58x |
| MiMo-V2.6-Pro | 32 | 65 | 61.49 | 25.07 | 2.45x |
| MiMo-V2.6-Pro | 64 | 65 | 64.21 | 28.68 | 2.24x |
| MiMo-V2.6-Pro | 256 | 65 | 64.83 | 31.31 | 2.07x |
| MiMo-V2.6-Pro | 1024 | 65 | 64.83 | 31.35 | 2.07x |
| MiMo-V2.6-Pro | 4096 | 65 | 64.83 | 31.35 | 2.07x |
| MiMo-V2.6-Pro | 1 | 66 | 7.59 | 5.96 | 1.27x |
| MiMo-V2.6-Pro | 2 | 66 | 14.17 | 8.34 | 1.70x |
| MiMo-V2.6-Pro | 4 | 66 | 24.89 | 11.88 | 2.09x |
| MiMo-V2.6-Pro | 8 | 66 | 39.40 | 16.05 | 2.45x |
| MiMo-V2.6-Pro | 16 | 66 | 53.66 | 20.72 | 2.59x |
| MiMo-V2.6-Pro | 32 | 66 | 62.27 | 25.27 | 2.46x |
| MiMo-V2.6-Pro | 64 | 66 | 65.14 | 28.93 | 2.25x |
| MiMo-V2.6-Pro | 256 | 66 | 65.81 | 31.60 | 2.08x |
| MiMo-V2.6-Pro | 1024 | 66 | 65.81 | 31.65 | 2.08x |
| MiMo-V2.6-Pro | 4096 | 66 | 65.81 | 31.65 | 2.08x |
| MiMo-V2.6-Pro | 1 | 67 | 7.59 | 5.98 | 1.27x |
| MiMo-V2.6-Pro | 2 | 67 | 14.20 | 8.37 | 1.70x |
| MiMo-V2.6-Pro | 4 | 67 | 24.97 | 11.94 | 2.09x |
| MiMo-V2.6-Pro | 8 | 67 | 39.63 | 16.15 | 2.45x |
| MiMo-V2.6-Pro | 16 | 67 | 54.15 | 20.86 | 2.60x |
| MiMo-V2.6-Pro | 32 | 67 | 63.05 | 25.47 | 2.48x |
| MiMo-V2.6-Pro | 64 | 67 | 66.07 | 29.18 | 2.26x |
| MiMo-V2.6-Pro | 256 | 67 | 66.79 | 31.90 | 2.09x |
| MiMo-V2.6-Pro | 1024 | 67 | 66.79 | 31.94 | 2.09x |
| MiMo-V2.6-Pro | 4096 | 67 | 66.79 | 31.94 | 2.09x |
| MiMo-V2.6-Pro | 1 | 88 | 7.69 | 6.30 | 1.22x |
| MiMo-V2.6-Pro | 2 | 88 | 14.57 | 8.97 | 1.62x |
| MiMo-V2.6-Pro | 4 | 88 | 26.26 | 12.96 | 2.03x |
| MiMo-V2.6-Pro | 8 | 88 | 43.43 | 17.85 | 2.43x |
| MiMo-V2.6-Pro | 16 | 88 | 62.92 | 23.55 | 2.67x |
| MiMo-V2.6-Pro | 32 | 88 | 77.76 | 29.28 | 2.66x |
| MiMo-V2.6-Pro | 64 | 88 | 84.58 | 34.00 | 2.49x |
| MiMo-V2.6-Pro | 256 | 88 | 86.89 | 37.51 | 2.32x |
| MiMo-V2.6-Pro | 1024 | 88 | 86.91 | 37.57 | 2.31x |
| MiMo-V2.6-Pro | 4096 | 88 | 86.91 | 37.57 | 2.31x |
| MiMo-V2.6-Pro | 1 | 112 | 7.75 | 6.57 | 1.18x |
| MiMo-V2.6-Pro | 2 | 112 | 14.83 | 9.53 | 1.56x |
| MiMo-V2.6-Pro | 4 | 112 | 27.20 | 13.79 | 1.97x |
| MiMo-V2.6-Pro | 8 | 112 | 46.33 | 19.40 | 2.39x |
| MiMo-V2.6-Pro | 16 | 112 | 70.17 | 26.03 | 2.70x |
| MiMo-V2.6-Pro | 32 | 112 | 91.30 | 32.86 | 2.78x |
| MiMo-V2.6-Pro | 64 | 112 | 103.24 | 38.61 | 2.67x |
| MiMo-V2.6-Pro | 256 | 112 | 108.37 | 42.96 | 2.52x |
| MiMo-V2.6-Pro | 1024 | 112 | 108.42 | 43.03 | 2.52x |
| MiMo-V2.6-Pro | 4096 | 112 | 108.42 | 43.03 | 2.52x |
| MiMo-V2.6-Pro | 1 | 120 | 7.77 | 6.64 | 1.17x |
| MiMo-V2.6-Pro | 2 | 120 | 14.89 | 9.70 | 1.54x |
| MiMo-V2.6-Pro | 4 | 120 | 27.43 | 14.02 | 1.96x |
| MiMo-V2.6-Pro | 8 | 120 | 47.08 | 19.86 | 2.37x |
| MiMo-V2.6-Pro | 16 | 120 | 72.13 | 26.76 | 2.70x |
| MiMo-V2.6-Pro | 32 | 120 | 95.16 | 33.91 | 2.81x |
| MiMo-V2.6-Pro | 64 | 120 | 108.87 | 39.99 | 2.72x |
| MiMo-V2.6-Pro | 256 | 120 | 115.10 | 44.60 | 2.58x |
| MiMo-V2.6-Pro | 1024 | 120 | 115.17 | 44.68 | 2.58x |
| MiMo-V2.6-Pro | 4096 | 120 | 115.17 | 44.68 | 2.58x |
| MiMo-V2.6-Pro | 1 | 130 | 7.79 | 6.71 | 1.16x |
| MiMo-V2.6-Pro | 2 | 130 | 14.96 | 9.90 | 1.51x |
| MiMo-V2.6-Pro | 4 | 130 | 27.69 | 14.28 | 1.94x |
| MiMo-V2.6-Pro | 8 | 130 | 47.90 | 20.40 | 2.35x |
| MiMo-V2.6-Pro | 16 | 130 | 74.33 | 27.63 | 2.69x |
| MiMo-V2.6-Pro | 32 | 130 | 99.61 | 35.16 | 2.83x |
| MiMo-V2.6-Pro | 64 | 130 | 115.52 | 41.61 | 2.78x |
| MiMo-V2.6-Pro | 256 | 130 | 123.21 | 46.55 | 2.65x |
| MiMo-V2.6-Pro | 1024 | 130 | 123.30 | 46.63 | 2.64x |
| MiMo-V2.6-Pro | 4096 | 130 | 123.30 | 46.63 | 2.64x |
| MiMo-V2.6-Pro | 1 | 133 | 7.79 | 6.74 | 1.16x |
| MiMo-V2.6-Pro | 2 | 133 | 14.98 | 9.95 | 1.51x |
| MiMo-V2.6-Pro | 4 | 133 | 27.76 | 14.35 | 1.93x |
| MiMo-V2.6-Pro | 8 | 133 | 48.13 | 20.55 | 2.34x |
| MiMo-V2.6-Pro | 16 | 133 | 74.94 | 27.87 | 2.69x |
| MiMo-V2.6-Pro | 32 | 133 | 100.87 | 35.52 | 2.84x |
| MiMo-V2.6-Pro | 64 | 133 | 117.43 | 42.08 | 2.79x |
| MiMo-V2.6-Pro | 256 | 133 | 125.57 | 47.11 | 2.67x |
| MiMo-V2.6-Pro | 1024 | 133 | 125.67 | 47.19 | 2.66x |
| MiMo-V2.6-Pro | 4096 | 133 | 125.67 | 47.19 | 2.66x |
| MiMo-V2.6-Pro | 1 | 135 | 7.80 | 6.75 | 1.15x |
| MiMo-V2.6-Pro | 2 | 135 | 14.99 | 9.99 | 1.50x |
| MiMo-V2.6-Pro | 4 | 135 | 27.80 | 14.40 | 1.93x |
| MiMo-V2.6-Pro | 8 | 135 | 48.28 | 20.66 | 2.34x |
| MiMo-V2.6-Pro | 16 | 135 | 75.33 | 28.04 | 2.69x |
| MiMo-V2.6-Pro | 32 | 135 | 101.69 | 35.76 | 2.84x |
| MiMo-V2.6-Pro | 64 | 135 | 118.68 | 42.39 | 2.80x |
| MiMo-V2.6-Pro | 256 | 135 | 127.13 | 47.48 | 2.68x |
| MiMo-V2.6-Pro | 1024 | 135 | 127.23 | 47.56 | 2.68x |
| MiMo-V2.6-Pro | 4096 | 135 | 127.23 | 47.56 | 2.68x |
| MiMo-V2.6-Pro | 1 | 136 | 7.80 | 6.76 | 1.15x |
| MiMo-V2.6-Pro | 2 | 136 | 15.00 | 10.01 | 1.50x |
| MiMo-V2.6-Pro | 4 | 136 | 27.82 | 14.43 | 1.93x |
| MiMo-V2.6-Pro | 8 | 136 | 48.35 | 20.71 | 2.33x |
| MiMo-V2.6-Pro | 16 | 136 | 75.53 | 28.12 | 2.69x |
| MiMo-V2.6-Pro | 32 | 136 | 102.10 | 35.87 | 2.85x |
| MiMo-V2.6-Pro | 64 | 136 | 119.30 | 42.55 | 2.80x |
| MiMo-V2.6-Pro | 256 | 136 | 127.90 | 47.67 | 2.68x |
| MiMo-V2.6-Pro | 1024 | 136 | 128.01 | 47.75 | 2.68x |
| MiMo-V2.6-Pro | 4096 | 136 | 128.01 | 47.75 | 2.68x |
| MiMo-V2.6-Pro | 1 | 138 | 7.80 | 6.77 | 1.15x |
| MiMo-V2.6-Pro | 2 | 138 | 15.01 | 10.04 | 1.49x |
| MiMo-V2.6-Pro | 4 | 138 | 27.87 | 14.47 | 1.93x |
| MiMo-V2.6-Pro | 8 | 138 | 48.49 | 20.81 | 2.33x |
| MiMo-V2.6-Pro | 16 | 138 | 75.91 | 28.28 | 2.68x |
| MiMo-V2.6-Pro | 32 | 138 | 102.90 | 36.11 | 2.85x |
| MiMo-V2.6-Pro | 64 | 138 | 120.53 | 42.85 | 2.81x |
| MiMo-V2.6-Pro | 256 | 138 | 129.44 | 48.03 | 2.69x |
| MiMo-V2.6-Pro | 1024 | 138 | 129.55 | 48.11 | 2.69x |
| MiMo-V2.6-Pro | 4096 | 138 | 129.55 | 48.11 | 2.69x |
| MiMo-V2.6-Pro | 1 | 145 | 7.81 | 6.82 | 1.15x |
| MiMo-V2.6-Pro | 2 | 145 | 15.05 | 10.17 | 1.48x |
| MiMo-V2.6-Pro | 4 | 145 | 28.01 | 14.63 | 1.91x |
| MiMo-V2.6-Pro | 8 | 145 | 48.96 | 21.15 | 2.31x |
| MiMo-V2.6-Pro | 16 | 145 | 77.19 | 28.82 | 2.68x |
| MiMo-V2.6-Pro | 32 | 145 | 105.59 | 36.90 | 2.86x |
| MiMo-V2.6-Pro | 64 | 145 | 124.71 | 43.89 | 2.84x |
| MiMo-V2.6-Pro | 256 | 145 | 134.71 | 49.28 | 2.73x |
| MiMo-V2.6-Pro | 1024 | 145 | 134.83 | 49.36 | 2.73x |
| MiMo-V2.6-Pro | 4096 | 145 | 134.83 | 49.36 | 2.73x |
| MiMo-V2.6-Pro | 1 | 156 | 7.82 | 6.88 | 1.14x |
| MiMo-V2.6-Pro | 2 | 156 | 15.10 | 10.35 | 1.46x |
| MiMo-V2.6-Pro | 4 | 156 | 28.21 | 14.86 | 1.90x |
| MiMo-V2.6-Pro | 8 | 156 | 49.61 | 21.67 | 2.29x |
| MiMo-V2.6-Pro | 16 | 156 | 79.01 | 29.62 | 2.67x |
| MiMo-V2.6-Pro | 32 | 156 | 109.50 | 38.08 | 2.88x |
| MiMo-V2.6-Pro | 64 | 156 | 130.92 | 45.45 | 2.88x |
| MiMo-V2.6-Pro | 256 | 156 | 142.65 | 51.15 | 2.79x |
| MiMo-V2.6-Pro | 1024 | 156 | 142.80 | 51.24 | 2.79x |
| MiMo-V2.6-Pro | 4096 | 156 | 142.80 | 51.24 | 2.79x |
| MiMo-V2.6-Pro | 1 | 168 | 7.84 | 6.95 | 1.13x |
| MiMo-V2.6-Pro | 2 | 168 | 15.15 | 10.53 | 1.44x |
| MiMo-V2.6-Pro | 4 | 168 | 28.40 | 15.10 | 1.88x |
| MiMo-V2.6-Pro | 8 | 168 | 50.25 | 22.20 | 2.26x |
| MiMo-V2.6-Pro | 16 | 168 | 80.79 | 30.42 | 2.66x |
| MiMo-V2.6-Pro | 32 | 168 | 113.39 | 39.29 | 2.89x |
| MiMo-V2.6-Pro | 64 | 168 | 137.21 | 47.05 | 2.92x |
| MiMo-V2.6-Pro | 256 | 168 | 150.85 | 53.09 | 2.84x |
| MiMo-V2.6-Pro | 1024 | 168 | 151.03 | 53.19 | 2.84x |
| MiMo-V2.6-Pro | 4096 | 168 | 151.03 | 53.19 | 2.84x |
| MiMo-V2.6-Pro | 1 | 174 | 7.84 | 6.97 | 1.12x |
| MiMo-V2.6-Pro | 2 | 174 | 15.18 | 10.62 | 1.43x |
| MiMo-V2.6-Pro | 4 | 174 | 28.48 | 15.21 | 1.87x |
| MiMo-V2.6-Pro | 8 | 174 | 50.53 | 22.45 | 2.25x |
| MiMo-V2.6-Pro | 16 | 174 | 81.60 | 30.80 | 2.65x |
| MiMo-V2.6-Pro | 32 | 174 | 115.20 | 39.86 | 2.89x |
| MiMo-V2.6-Pro | 64 | 174 | 140.18 | 47.82 | 2.93x |
| MiMo-V2.6-Pro | 256 | 174 | 154.78 | 54.02 | 2.87x |
| MiMo-V2.6-Pro | 1024 | 174 | 154.97 | 54.12 | 2.86x |
| MiMo-V2.6-Pro | 4096 | 174 | 154.97 | 54.12 | 2.86x |
| MiMo-V2.6-Pro | 1 | 179 | 7.85 | 7.00 | 1.12x |
| MiMo-V2.6-Pro | 2 | 179 | 15.19 | 10.69 | 1.42x |
| MiMo-V2.6-Pro | 4 | 179 | 28.55 | 15.30 | 1.87x |
| MiMo-V2.6-Pro | 8 | 179 | 50.76 | 22.65 | 2.24x |
| MiMo-V2.6-Pro | 16 | 179 | 82.25 | 31.10 | 2.64x |
| MiMo-V2.6-Pro | 32 | 179 | 116.64 | 40.33 | 2.89x |
| MiMo-V2.6-Pro | 64 | 179 | 142.57 | 48.44 | 2.94x |
| MiMo-V2.6-Pro | 256 | 179 | 157.97 | 54.77 | 2.88x |
| MiMo-V2.6-Pro | 1024 | 179 | 158.18 | 54.87 | 2.88x |
| MiMo-V2.6-Pro | 4096 | 179 | 158.18 | 54.87 | 2.88x |
| MiMo-V2.6-Pro | 1 | 186 | 7.85 | 7.03 | 1.12x |
| MiMo-V2.6-Pro | 2 | 186 | 15.22 | 10.79 | 1.41x |
| MiMo-V2.6-Pro | 4 | 186 | 28.64 | 15.42 | 1.86x |
| MiMo-V2.6-Pro | 8 | 186 | 51.05 | 22.92 | 2.23x |
| MiMo-V2.6-Pro | 16 | 186 | 83.10 | 31.51 | 2.64x |
| MiMo-V2.6-Pro | 32 | 186 | 118.57 | 40.95 | 2.90x |
| MiMo-V2.6-Pro | 64 | 186 | 145.81 | 49.28 | 2.96x |
| MiMo-V2.6-Pro | 256 | 186 | 162.31 | 55.80 | 2.91x |
| MiMo-V2.6-Pro | 1024 | 186 | 162.53 | 55.91 | 2.91x |
| MiMo-V2.6-Pro | 4096 | 186 | 162.53 | 55.91 | 2.91x |
| MiMo-V2.6-Pro | 1 | 208 | 7.87 | 7.11 | 1.11x |
| MiMo-V2.6-Pro | 2 | 208 | 15.28 | 11.07 | 1.38x |
| MiMo-V2.6-Pro | 4 | 208 | 28.88 | 15.79 | 1.83x |
| MiMo-V2.6-Pro | 8 | 208 | 51.87 | 23.70 | 2.19x |
| MiMo-V2.6-Pro | 16 | 208 | 85.48 | 32.69 | 2.61x |
| MiMo-V2.6-Pro | 32 | 208 | 124.04 | 42.78 | 2.90x |
| MiMo-V2.6-Pro | 64 | 208 | 155.13 | 51.77 | 3.00x |
| MiMo-V2.6-Pro | 256 | 208 | 175.04 | 58.86 | 2.97x |
| MiMo-V2.6-Pro | 1024 | 208 | 175.31 | 58.97 | 2.97x |
| MiMo-V2.6-Pro | 4096 | 208 | 175.31 | 58.97 | 2.97x |
| MiMo-V2.6-Pro | 1 | 209 | 7.87 | 7.12 | 1.11x |
| MiMo-V2.6-Pro | 2 | 209 | 15.28 | 11.09 | 1.38x |
| MiMo-V2.6-Pro | 4 | 209 | 28.89 | 15.81 | 1.83x |
| MiMo-V2.6-Pro | 8 | 209 | 51.90 | 23.74 | 2.19x |
| MiMo-V2.6-Pro | 16 | 209 | 85.58 | 32.74 | 2.61x |
| MiMo-V2.6-Pro | 32 | 209 | 124.26 | 42.86 | 2.90x |
| MiMo-V2.6-Pro | 64 | 209 | 155.52 | 51.88 | 3.00x |
| MiMo-V2.6-Pro | 256 | 209 | 175.58 | 58.99 | 2.98x |
| MiMo-V2.6-Pro | 1024 | 209 | 175.86 | 59.11 | 2.98x |
| MiMo-V2.6-Pro | 4096 | 209 | 175.86 | 59.11 | 2.98x |
| MiMo-V2.6-Pro | 1 | 224 | 7.88 | 7.17 | 1.10x |
| MiMo-V2.6-Pro | 2 | 224 | 15.32 | 11.26 | 1.36x |
| MiMo-V2.6-Pro | 4 | 224 | 29.02 | 16.04 | 1.81x |
| MiMo-V2.6-Pro | 8 | 224 | 52.37 | 24.21 | 2.16x |
| MiMo-V2.6-Pro | 16 | 224 | 86.96 | 33.46 | 2.60x |
| MiMo-V2.6-Pro | 32 | 224 | 127.51 | 44.02 | 2.90x |
| MiMo-V2.6-Pro | 64 | 224 | 161.19 | 53.46 | 3.02x |
| MiMo-V2.6-Pro | 256 | 224 | 183.50 | 60.94 | 3.01x |
| MiMo-V2.6-Pro | 1024 | 224 | 183.81 | 61.05 | 3.01x |
| MiMo-V2.6-Pro | 4096 | 224 | 183.81 | 61.05 | 3.01x |
| MiMo-V2.6-Pro | 1 | 231 | 7.88 | 7.19 | 1.10x |
| MiMo-V2.6-Pro | 2 | 231 | 15.33 | 11.34 | 1.35x |
| MiMo-V2.6-Pro | 4 | 231 | 29.08 | 16.14 | 1.80x |
| MiMo-V2.6-Pro | 8 | 231 | 52.57 | 24.42 | 2.15x |
| MiMo-V2.6-Pro | 16 | 231 | 87.55 | 33.78 | 2.59x |
| MiMo-V2.6-Pro | 32 | 231 | 128.92 | 44.54 | 2.89x |
| MiMo-V2.6-Pro | 64 | 231 | 163.68 | 54.17 | 3.02x |
| MiMo-V2.6-Pro | 256 | 231 | 187.01 | 61.81 | 3.03x |
| MiMo-V2.6-Pro | 1024 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 4096 | 231 | 187.34 | 61.93 | 3.02x |
| MiMo-V2.6-Pro | 1 | 249 | 7.89 | 7.24 | 1.09x |
| MiMo-V2.6-Pro | 2 | 249 | 15.37 | 11.52 | 1.33x |
| MiMo-V2.6-Pro | 4 | 249 | 29.22 | 16.41 | 1.78x |
| MiMo-V2.6-Pro | 8 | 249 | 53.04 | 24.91 | 2.13x |
| MiMo-V2.6-Pro | 16 | 249 | 88.94 | 34.57 | 2.57x |
| MiMo-V2.6-Pro | 32 | 249 | 132.26 | 45.83 | 2.89x |
| MiMo-V2.6-Pro | 64 | 249 | 169.65 | 55.93 | 3.03x |
| MiMo-V2.6-Pro | 256 | 249 | 195.52 | 63.96 | 3.06x |
| MiMo-V2.6-Pro | 1024 | 249 | 195.90 | 64.09 | 3.06x |
| MiMo-V2.6-Pro | 4096 | 249 | 195.90 | 64.09 | 3.06x |
| MiMo-V2.6-Pro | 1 | 335 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 335 | 15.49 | 12.24 | 1.27x |
| MiMo-V2.6-Pro | 4 | 335 | 29.66 | 17.53 | 1.69x |
| MiMo-V2.6-Pro | 8 | 335 | 54.61 | 26.66 | 2.05x |
| MiMo-V2.6-Pro | 16 | 335 | 93.75 | 37.88 | 2.48x |
| MiMo-V2.6-Pro | 32 | 335 | 144.17 | 51.16 | 2.82x |
| MiMo-V2.6-Pro | 64 | 335 | 191.76 | 62.99 | 3.04x |
| MiMo-V2.6-Pro | 256 | 335 | 228.15 | 72.67 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 335 | 228.71 | 72.82 | 3.14x |
| MiMo-V2.6-Pro | 4096 | 335 | 228.71 | 72.82 | 3.14x |
| MiMo-V2.6-Pro | 1 | 336 | 7.92 | 7.41 | 1.07x |
| MiMo-V2.6-Pro | 2 | 336 | 15.49 | 12.24 | 1.26x |
| MiMo-V2.6-Pro | 4 | 336 | 29.67 | 17.54 | 1.69x |
| MiMo-V2.6-Pro | 8 | 336 | 54.62 | 26.67 | 2.05x |
| MiMo-V2.6-Pro | 16 | 336 | 93.80 | 37.91 | 2.47x |
| MiMo-V2.6-Pro | 32 | 336 | 144.27 | 51.21 | 2.82x |
| MiMo-V2.6-Pro | 64 | 336 | 191.97 | 63.06 | 3.04x |
| MiMo-V2.6-Pro | 256 | 336 | 228.47 | 72.76 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 336 | 229.03 | 72.91 | 3.14x |
| MiMo-V2.6-Pro | 4096 | 336 | 229.03 | 72.91 | 3.14x |
| MiMo-V2.6-Pro | 1 | 346 | 7.92 | 7.43 | 1.07x |
| MiMo-V2.6-Pro | 2 | 346 | 15.50 | 12.31 | 1.26x |
| MiMo-V2.6-Pro | 4 | 346 | 29.71 | 17.66 | 1.68x |
| MiMo-V2.6-Pro | 8 | 346 | 54.76 | 26.83 | 2.04x |
| MiMo-V2.6-Pro | 16 | 346 | 94.21 | 38.26 | 2.46x |
| MiMo-V2.6-Pro | 32 | 346 | 145.34 | 51.74 | 2.81x |
| MiMo-V2.6-Pro | 64 | 346 | 194.00 | 63.75 | 3.04x |
| MiMo-V2.6-Pro | 256 | 346 | 231.56 | 73.65 | 3.14x |
| MiMo-V2.6-Pro | 1024 | 346 | 232.14 | 73.81 | 3.14x |
| MiMo-V2.6-Pro | 4096 | 346 | 232.14 | 73.81 | 3.14x |
| MiMo-V2.6-Pro | 1 | 373 | 7.93 | 7.47 | 1.06x |
| MiMo-V2.6-Pro | 2 | 373 | 15.52 | 12.48 | 1.24x |
| MiMo-V2.6-Pro | 4 | 373 | 29.80 | 17.97 | 1.66x |
| MiMo-V2.6-Pro | 8 | 373 | 55.08 | 27.22 | 2.02x |
| MiMo-V2.6-Pro | 16 | 373 | 95.24 | 39.18 | 2.43x |
| MiMo-V2.6-Pro | 32 | 373 | 147.96 | 53.07 | 2.79x |
| MiMo-V2.6-Pro | 64 | 373 | 199.07 | 65.53 | 3.04x |
| MiMo-V2.6-Pro | 256 | 373 | 239.33 | 75.99 | 3.15x |
| MiMo-V2.6-Pro | 1024 | 373 | 239.95 | 76.15 | 3.15x |
| MiMo-V2.6-Pro | 4096 | 373 | 239.95 | 76.15 | 3.15x |
| MiMo-V2.6-Pro | 1 | 448 | 7.94 | 7.55 | 1.05x |
| MiMo-V2.6-Pro | 2 | 448 | 15.57 | 12.88 | 1.21x |
| MiMo-V2.6-Pro | 4 | 448 | 30.00 | 18.77 | 1.60x |
| MiMo-V2.6-Pro | 8 | 448 | 55.80 | 28.11 | 1.99x |
| MiMo-V2.6-Pro | 16 | 448 | 97.49 | 41.50 | 2.35x |
| MiMo-V2.6-Pro | 32 | 448 | 153.83 | 56.17 | 2.74x |
| MiMo-V2.6-Pro | 64 | 448 | 210.61 | 70.02 | 3.01x |
| MiMo-V2.6-Pro | 256 | 448 | 257.32 | 81.76 | 3.15x |
| MiMo-V2.6-Pro | 1024 | 448 | 258.06 | 81.95 | 3.15x |
| MiMo-V2.6-Pro | 4096 | 448 | 258.06 | 81.95 | 3.15x |
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
| gpu | MiMo-V2.6-Pro | 1 | 15.80 | 1.0% |
| rom | MiMo-V2.6-Pro | 1 | 15.80 | 10.3% |

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
| MiMo-V2.6-Pro | 1 | 60 | 58.58% | 326.18 | 9.28 |
| MiMo-V2.6-Pro | 2 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 4 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 8 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 16 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 32 | 2 | 0.54% | 5.73 | 9.28 |
| MiMo-V2.6-Pro | 64 | 2 | 0.54% | 5.73 | 9.28 |

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
| MiMo-V2.6-Pro | 1 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 2 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 4 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 8 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 16 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 32 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 64 | 2.08% | 39.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 207.6 | 27,402.6 |
| MiMo-V2.6-Pro | 256 | 4.00% | 49.5 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 107.2 | 27,452.3 |
| MiMo-V2.6-Pro | 1024 | 15.07% | 108.3 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 26.8 | 27,492.1 |
| MiMo-V2.6-Pro | 4096 | 47.97% | 283.1 GB | 100.00% | 16,423.08 TB/s | 16,423.08 TB/s | 6.7 | 27,502.1 |

## Binding constraint census

| Family | Binding constraint | Points |
|---|---|---:|
| gpu | compute | 2 |
| gpu | infeasible | 1 |
| gpu | link_latency | 346 |
| gpu | weight_read | 891 |
| rom | compute | 649 |
| rom | infeasible | 1908 |
| rom | kv_read | 246 |
| rom | link_latency | 1129 |
| rom | weight_read | 628 |

Why the infeasible points are infeasible:

| Family | Reason class | Points |
|---|---|---:|
| gpu | CAPACITY | 1 |
| rom | CAPACITY | 1908 |

## Mechanical consistency audit

**FAIL** over 122,921 checks.

- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x138', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-pipeline-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x138', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-tensor-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x138', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-hw-hybrid-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x122', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x132', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x135', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x137', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x138', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x147', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x170', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x176', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x227', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x234', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x340', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-array-pipeline-x351', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x3', 'MiMo-V2.6-Pro', 1)
- ERROR: ROM weight time below the serial full-array sweep floor ('MiMo-V2.6-Pro/ROM-N6-native-SRAMKV-wafer-pipeline-x4', 'MiMo-V2.6-Pro', 1)

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
