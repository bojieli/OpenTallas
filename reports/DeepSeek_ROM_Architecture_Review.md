# DeepSeek ROM accelerator: progress and architecture review

## Update after expert review — recommendation changed

**The 725 µs ROM reference used below was stale. I should have refreshed main before publishing the brief. The separate wide-TP successor is no longer recommended for development.**

I read the [recovery owner's reply at `42a326e4a`](https://github.com/bojieli/OpenTallas/blob/42a326e4a/reports/DeepSeek_ROM_Architecture_Review_Reply.md) and inspected its pinned composition and lever records.

| Configuration | AR µs/token | MTP step µs | Evidence status |
|---|---:|---:|---|
| S81 recovery at the reply revision | **620.078** | **871.315** | Adopted-lever component composition; not whole-system physical sign-off |
| S81 with field-phase overlap | **514.6** | **746.1** | Reported counterfactual; field lever remains `REJECT` pending spine timing closure |
| HBM comparison at the same revision | **460.053** | **888.077** | Conditional component composition; common-cost corrections still required |

At matched τ = 3.8879, current S81 already satisfies the numerical MTP-step comparison by about 17 µs. The 1,303 µs and 708 µs adapted designs are slower than current S81. The proposed direct fabric adds substantial power, wiring and qualification risk without an established full-system advantage.

**Revised recommendation:** retain S81's pipeline and local TP4 organization; apply operand forwarding, lane-local fusion, phase overlap and exact workgroups inside it. Prioritize the recovery owner's existing spine, vector-chain and integration work; do not duplicate those streams or launch the separate architecture.

Important qualifications:

- The field-phase lever is exact, but its record explicitly reports SS failures of approximately −723 to −906 ps and an R128 FF hold failure. The roughly 515 µs result is not adopted performance; a successor spine must close and its added cycles must be recomposed.
- Approximately 183 µs of vector-chain path is an optimization target, **not** a demonstrated 183 µs saving. The review's 430–480 µs AR range remains a projection.
- Component compositions, routed element passes and whole-die qualification are different evidence levels. Spine, IR/power, draft placement/link capacity and all-on integration remain gates. The adopted draft placement adds 52 dies and must be counted in the matched silicon/power comparison.
- Apply HBM accounting corrections and shared improvements before the final AR/MTP decision. Do not compare one design's target clock with the other's slower closure sensitivity as if they were matched.

The earlier analysis is retained below as history. Its useful findings can inform S81, but its baseline and recommendation are superseded by this update. [Pinned correction evidence](deepseek_rom_review_evidence/recovery_correction.json).

---

## Historical exploration brief — superseded recommendation

**Historical status:** Architecture exploration before the recovery review. No successor was selected or physically qualified.

## Objective and decision rule

Design for minimum single-user decode latency at **one-million context**, preserving the released checkpoint and exact golden rounding/reduction order. The successor must substantially outperform current ROM, offer pure autoregressive (AR) performance comparable to HBM, and support MTP at comparable useful-token speed. A marginal improvement over current ROM is insufficient. If no credible architecture meets both modes, stop the effort.

The owner authorizes **the same MTP acceptance assumption as HBM**. Compare the same workload, precision, context and acceptance, counting all memory dies and power. Applicable architectural improvements must also be credited to HBM.

## 1. Reference figures and previous work

| Case | Reference or estimate | Status |
|---|---:|---|
| Current ROM | 725.057 µs / AR token | Conditional component composition |
| HBM accelerator | 460.053 µs / AR token | Conditional component composition |
| HBM MTP | 888.077 µs / speculative step; 4,377.9 useful tokens/s | Same acceptance used for the new design |
| First layer-local compute-reuse proposal | 1,303.348 µs / AR token | Rejected: slower than current ROM |
| Subsequent global compute-reuse adaptation | 707.858 µs / AR token | Rejected: only 2.4% faster than current ROM |

These are **not measured end-to-end product results**. The final adapted design also reached approximately 891 µs in a slower component-clock sensitivity. Its nominal margin did not justify implementation.

The first proposal limited active compute to too few dies and introduced additional activation/KV movement. The second retained global participation but accumulated source, dispatch and distribution costs. Further gap-closing on that adaptation has stopped.

The audit also corrected the comparison: unused issue slots, separate operation drains and activation loading were incompletely accounted for in the inherited HBM composition. Those costs are **not inherently ROM penalties**. Earlier partial RTL is preserved as history; it does not qualify the proposed architecture. No full connected successor PASS or contextual SS/FF closure is claimed.

## 2. Findings that change the architectural choices

| Finding | Architectural implication |
|---|---|
| Full configuration and 1M program contain **933.233 MB** of unique shared compressed KV/index state | Mutable-state capacity is much smaller than the inherited HBM provision suggests. |
| At 96 ranks, maximum persistent payload is **12.429 MB/rank**, including 40 windows | Banked local SRAM is a credible candidate. |
| Protected SRAM provision: approximately **19.36 mm²/rank**, versus **46.02 mm²** for four HBM PHYs/controllers | Potential area recovery, subject to ports, timing and remaining memory uses. These are analytical reservations. |
| Active main-matrix weights: approximately **12.879 GB/token** in stored format | Separate ROM storage requires at least **17.8 TB/s** aggregate payload bandwidth at 725 µs/token, before bursts and protocol overhead. |
| HC projection weights: **157.286 MB per compute rank** | Keep them local; streaming all 96 replicas adds approximately **15.1 GB/token**. |
| Approximately **203 GB** of Engram tables | These are active lookup services, not merely archival capacity. |

The SRAM organization supplies 64 index keys/cycle and one arbitrary compressed-KV row/cycle. Capacity alone does not establish sufficient service: selected-row concentration, capture/ECC latency, updates and speculative state lifetimes remain relevant.

Pre-MTP area screens retain 96 and 128 ranks as candidates. The 96-rank AR reservations are roughly **700–720 mm² within an 814 mm² die**, including local auxiliary ROM. This does **not** prove an MTP-capable engine fits or that its routes close. A provisional auxiliary allocation adds 24 Engram and four archive/embedding dies: **124 logic dies** for 96 compute ranks, or **156** for 128. Neither organization is selected.

## 3. Current proposed architecture

The proposal is a **ROM dataflow accelerator**, not an unchanged HBM accelerator with substituted memory:

- **Separate capacity from active compute sizing.** Colocate ROM banks with reusable matrix-compute clusters. Store all experts, while sizing arithmetic for selected work and its deadlines.
- **Keep working state near consumers.** Use local SRAM where feasible; retain activations across reuse; deliver results directly toward the next operation instead of repeatedly returning to a central hub.
- **Choose workgroups from arithmetic dependencies.** Twelve routed-expert gate/up matrices share one input and can form one larger set of independent output rows. An analytical TP96 example saves about 37 µs/token without changing per-row arithmetic. Credit this improvement to both ROM and HBM.
- **Design communication for the actual collectives.** Stream gathers and exact reductions through a purpose-built direct or hierarchical fabric. Preserve the golden tree and price physical distance, bandwidth, buffering, skew and concentrated traffic.
- **Provision AR and MTP together.** Wide-column resources can reuse weights across dense/shared/draft verification positions. Narrower resources may be more efficient for routed experts with little position overlap. A heterogeneous compute organization is under evaluation.

First-use ROM ordering has an analytical finite schedule that reconstructs the exact native stream at one response/cycle after fill. This supports bandwidth feasibility; it is not RTL or physical qualification.

### Communication is the largest unresolved lever

The current HBM composition charges about **207 µs AR** and **325 µs P6 verification** to collectives and transport tails. A sparse hierarchy examined so far provides insufficient improvement.

A direct fabric connecting all pairs of 48 two-die compute packages has a preliminary central communication budget of **103 µs AR / 169 µs P6**. However, its matched analytical reference is **199 / 264 µs**; the discrepancy with the published composition, especially P6, must be reconciled before claiming savings.

This candidate requires **1,128 compute links plus auxiliary links**, approximately **32 mm² interconnect reservation per compute die**, and roughly **3.2 kW of system PHY power under an assumed energy coefficient**, excluding some additional logic/UCIe costs. Selected KV requires priced relay phases to handle source concentration. Cable density, bounded PHY/FEC latency, power and receiver distribution are serious open constraints. **The fabric is not selected or qualified.**

## 4. MTP requirements and emerging compute tradeoff

Use five draft tokens, six-position verification, and **τ = 3.8879 emitted tokens per step**, matching HBM. Useful-token rate is τ divided by complete step time—not six divided by verification time.

| HBM reference component | Time |
|---|---:|
| Verification, including modeled expert-union additions | 839.230 µs |
| DSpark drafting | 45.280 µs |
| Seed/commit | 3.567 µs |
| **Complete step** | **888.077 µs** |

The reference mixes component evidence and modeled terms; it does not establish complete rollback/next-iteration correctness. Its actual three-stage DSpark drafter, five-slot generation and serial Markov-head feedback must be modeled. Storing `mtp.*` weights is not sufficient, and generic native MTP is not an interchangeable substitute.

A uniform single-column engine is unattractive for dense verification: the current area lower-bound study finds that it buys only about **1.87×** as many engines as a six-column organization, yet needs six dense weight passes. Routed experts differ because positions can select different experts; up to 36 expert-position selections per layer must be serviced. Acceptance matching does not establish expert overlap.

The successor must price drafting, causal verification, expert unions, activation/accumulator storage, accepted-prefix commit, rejected-suffix retirement and subsequent iteration reuse. No complete AR/MTP projection has passed yet.

## 5. Selection gate and requested expert review

A strict sufficient admission test is **AR ≤ 460.053 µs** and **MTP step ≤ 888.077 µs**, at matched acceptance and a credible silicon/power budget. The earlier 500 µs AR screening target alone is not admission. Any improvements or corrections available to HBM belong in the matched comparison.

Please review:

1. Can ownership and communication materially shorten the dependency path without changing exact arithmetic or assuming free overlap?
2. Is the direct-fabric opportunity credible after power, wiring, traffic concentration and P6 reference reconciliation—or is a different physical organization preferable?
3. Does a heterogeneous dense/routed compute pool offer a viable AR/MTP tradeoff once operand storage and expert-position scheduling are included?
4. Are important costs missing: auxiliary lookups, speculative-state lifetimes, whole-die distribution, physical margins or fair HBM improvements?

**Next decision:** select an architecture only after a complete, matched AR/MTP budget establishes a credible path. Otherwise terminate the effort. No further implementation of the rejected adaptation is planned.

## Evidence

- [HBM reference composition](../results/rtl/dshbm_1m_allmeasured_20261004/composition.json) and [current ROM composition](../results/rtl/dsrom_1m_allmeasured_20261004/composition.json).
- [Committed first-principles evidence](../results/uarch/hbrom/first_principles/manifest.json): state capacity, rank-area screens, active traffic, workgroups and initial placement. Source commit `ef1949ee1`, integrated as `c5572502b`.
- [MTP comparison contract](deepseek_rom_review_evidence/hbrom-newarch-mtp-contract.json), [AR/MTP compute frontier](deepseek_rom_review_evidence/hbrom-newarch-compute-mtp-frontier.json), and [interconnect frontier](deepseek_rom_review_evidence/hbrom-newarch-interconnect-frontier.json): review-stage snapshots, each carrying source references and limitations.
- [Review evidence index](deepseek_rom_review_evidence/index.json): snapshot hashes, including the rejected adaptation's terminal composition.
