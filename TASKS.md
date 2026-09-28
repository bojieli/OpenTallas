# OpenTallas critical-path tracker

Updated 2026-09-28 against the current integration branch. The goal is four **full-shape, bit-exact, source-pinned end-to-end** ROM/HBM results, with physical evidence for the implemented blocks and a rate model calibrated from those results. A reduced test, design-point model, or placed block cannot be promoted to a full-chip throughput claim. The paper is [`docs/ARCHITECTURE_ATLAS.html`](docs/ARCHITECTURE_ATLAS.html); this file tracks its remaining proof obligations.

**Statuses:** `[x]` published and passed at the stated scope; `[~]` assigned/in progress; `[ ]` queued; `[!]` a measured blocker. Owner names below identify responsibility; their branch/worktree is the handoff location, not evidence until merged. The live assignment table below supersedes older agent activity descriptions. Completed agents resume only for a concrete, nonoverlapping critical-path task. Optional sweeps and superseded routes stay stopped. Root stopped the old DEPTH32 non-px collective detailed route (checkpoint retained), recovering about 30 GiB locally; large new gates run remotely with memory caps. The root agent integrates and pushes main. On every substantive merge, the owner of that item updates its gate, source-pinned record and next blocker here. Old campaign details belong in their records.

## Architecture-owned execution — current priority

The user approved [the architecture ownership and verification contract](ARCHITECTURE_EXECUTION_CONTRACT.md). Root owns topology and all budgets. Agent proposals and measurements inform root decisions; agents do not independently change pipeline latency, replication, memory layout or physical partitioning.

- [~] **Root:** review and adopt the complete implementation contract; publish approved integrations and invalidate dependent evidence when contracts change.
- [~] **v41_model_reprice:** machine-readable dependency/service/budget proposal, with unknown terminal latency kept null; no headline changes.
- [~] **v41_hbm_region_audit:** complete single-user HBM region/service candidate and executable constraints, including disconnected clients and width limits.
- [~] **v41_fullshape_core:** actual layer connection manifest, selected-ID/descriptor lifecycle and full-shape width propagation proposal.
- [~] **v41_vm_bank_physical + v41_me_he_macro_pipeline:** macro/register placement and real timing budgets before the next neighborhood implementation; preserve current negative evidence.
- [~] **v41_index_score_major:** query lifetime and reader/scorer/selector burst/queue contract before replication.
- [~] **Qwen owners:** continue bounded exactness and existing physical verification; root reviews architecture-changing fixes first.

The older assignment snapshot below describes file ownership; this section supersedes its activity count and sequencing. Completed implementation branches await integration or a reviewed next contract. Existing independent runs may finish.

## Live parallel assignments — 2026-09-28

Root owns publication, this tracker, and the architectural acceptance boundary. Twelve subagents are assigned active work after the requested parallelism increase; this is an assignment snapshot, not a count of background processes. Integration reviewers use isolated branches and never change frozen simulation inputs.

| Owner | Current deliverable | Edit/coordination boundary |
| --- | --- | --- |
| `qwen_o4_end_to_end` | Full-size compilation and identical-source hierarchical/flat exactness checks | Owns frozen simulation inputs and verdicts; no duplicate full-size builds |
| `v41_fullshape_core` | All-unit layer execution and real-checkpoint local ROM-bank bridge | Owns harness/QE source; coordinates core/tile/die edits with attention owner |
| `v41_attention_physical` | Full-mode direct packed-KV input, removing redundant buffer/re-encoders | Owns attention bypass and agreed core/tile/die plumbing; reduced mode preserved |
| `v41_me_he_macro_pipeline` | Exact checkpoint replay and registered SRAM operand/control route | Owns MAC/store implementation and its physical cut |
| `v41_vm_bank_physical` | Composed VM interface and collective output physical closure | Owns VM/collective physical boundary; coordinates with MAC owner |
| `v41_index_score_major` | Combined finite reader/scorer/selector exact gate | Owns new scoring integration; reuses measured reader, no core/die edits |
| `qwen_o4_hbm_comparator` | Mixed-client finite timed HBM gate and completion ordering | Owns PC service/adapters; no frozen-build or core edits |
| `qwen_int8_tile_physical` | Existing route verdicts and legal local scale/control timing fix | Owns scale physical probe; production RTL changes coordinated first |
| `v41_hbm_region_audit` | Executable packed-KV/index/RoPE/weight region and capacity checks | Audit/tests only; no live RTL or model repricing |
| `v41_hbm_comparator_weights` | Missing weight-family bounded HBM service with exact checkpoint gate | New standalone adapter/tests; core owner agrees interface before hookup |
| `critical_path_tracker` | Tested Qwen integration candidate including shared-HBM fixes | Isolated integration only; root publishes and maintains TASKS |
| `v41_integration` | Tested packed-KV/RoPE/core integration candidate | Isolated integration of agreed stable commits; no new feature RTL |

Acceptance remains full-shape bit-exact execution plus finite shared resources and physical evidence. Component cycles are not token rates. Existing remote jobs are reused; new substantial jobs require checking host memory and use bounded resources. Other completed or pending agents remain inactive until a distinct useful dependency is available.

## Immediate architecture recovery priority

**Primary design directive:** [single-user-first top-down design](DEEPSEEK_V41_SINGLE_USER_DESIGN.md). Root owns the operating-point/physical/arithmetic contract; placement and emitter owners bind integer ownership; schedule owner builds the complete finite-resource token trace. Rank RTL/fabric changes by exposed end-to-end latency reduction. Multiuser utilization and stage balancing are secondary and must preserve the selected single-user service contract.

**Fabric review (2026-09-28):** [V41_FABRIC_DESIGN_PROPOSAL.md](docs/V41_FABRIC_DESIGN_PROPOSAL.md) defines the proposed weight-stationary hierarchy and acceptance order. Newly confirmed blockers: the 12-collective exact layer program differs from the fused benchmark; fractional stage placement omits split-expert return traffic; HBM clients need one shared service schedule. Prioritize the ownership manifest, executable packet trace, mixed-HBM layer and two-stage exact gate before any new rate claim. The pin problem has a routed local slice, but powered composition is still open.

The objective is the highest demonstrated single-user rate within fixed hardware,
power and arithmetic constraints; no arbitrary token-rate target is adopted.
[COMPUTE_CLUSTER_PLAN.md](COMPUTE_CLUSTER_PLAN.md) defines the proposed local
sharing boundary, executable contract, experiments and ownership. This is a
proposal to validate, not a claim that a new cluster is implemented.

**Latest user direction:** lead with weight-stationary ROM-bank-local compute for
single-user latency, comparing fixed local tiles against limited nearby-bank MAC
sharing. Count replicated idle hardware and activation/result networks in the same
area/power budget. Whole-die MFU is diagnostic; no global weight-routing or target
token rate is assumed.

**Pipeline operating point:** also evaluate independent users streamed through
different layer stages. Record isolated token latency, initiation interval,
aggregate throughput, queue latency, stage/expert occupancy and per-user state
capacity. Multi-user pipeline fill can improve utilization of dedicated ROM
tiles; it does not remove one user's autoregressive feedback dependency.

- [~] **Root: integration and architectural contract** — integrate completed exact
  operator/local-route records; define concrete tensor/expert placement, all
  storage and the finite shared-resource schedule before selecting cluster width.
- [!] **Pooling must be physically realizable** — the model already shares
  quantized weight/index MACs and BF16 weight/attention MACs, with an assumed 10%
  operand-mux area. Require a real ROM-bank/activation-bank-to-cluster mapping,
  routed multicast, conflict handling and complete memory ledger.
- [!] **Discrete placement and expert imbalance** — the 28-stage placement cuts
  cumulative layer bytes into fractions without tensor/expert ownership. The
  budget scales expert time by those fractions although routed expert IDs may
  concentrate in one stage. `v41_fullshape_emitter_binding` owns an integer
  expert/tensor-fragment manifest and explicit boundary packets;
  `v41_model_reprice` owns the resulting resource conflicts, observed/worst-case
  stage service, and power. A byte-balanced placement alone cannot validate rate.
- [!] **Physical ROM traffic** — `v41_fullshape_weight_layout` found that the
  physical tile's weight word formats imply about 453,684 physical B/cycle for
  the specified lanes versus 348,288 useful B/cycle; current reduced tile geometry
  and truncated ROM addresses do not establish that full-shape read network.
  Bind packed words, port counts, bank ownership and expansion to the same
  executable cluster before a ROM bandwidth claim.
- [ ] **Select clusters by measured end-to-end gain** — compare shared local
  matrix tiles plus dedicated SFU/reduction/quantization pipelines; measure useful
  and issued MAC work, all memory/link traffic and stall reasons at batch one.
  Verify actual shared HBM weight/KV/index contention and exact TP rounding.
- [!] **Additional capacity risks** — source-pinned branch audits report a 268.4
  MB replicated 1M RoPE table versus 71.6 MB minimum ROM spare, and about 81 mm2
  activation SRAM if the small ME slice is naively replicated. Production RoPE
  storage/computation and shared activation-cluster topology must be costed;
  sparse single-position fixtures establish arithmetic only.

## Single-user-first implementation started

**Parallel Qwen ROM/HBM track:** user confirmed ROM, not an SRAM-weight variant. `qwen_o4_end_to_end` owns frozen real G6144 layer0 execution and core integration; `qwen_fullshape_emitter` owns full-token program/image binding; `qwen_o4_hbm_comparator` owns matched full-shape weight supply including remaining scale/constant families; `qwen_int8_tile_physical` owns a coordinated physical boundary on that path. Preserve frozen builds and use available remote capacity. Qwen is evaluated independently; simpler topology is not proof of modeled throughput.

- [x] **Root: finite-resource validation foundation** — integrated the schedule checker. The earlier GW1 subset is now explicitly historical and blocked against changed RTL; current GW4 service comes from the exact emitted sequence. Sixteen focused tests pass after malformed-input and queue/evidence hardening. Checks cover physical aliases, same-stack HBM accounting, integer tensor coverage, local ROM ownership, and die area/power constraints. This is a component scheduling foundation, not a complete token schedule.
- [~] **v41_model_reprice: constructive schedule builder** — 111-instruction preflight and descriptor-matched service binding implemented. All 12 measured collectives bind to exact PC/tag/sequence/fields; missing physical/producer/shared-service contracts are ranked explicitly. Token latency remains null until a complete feasible schedule exists.
- [~] **v41_fullshape_emitter_binding: executable stage ownership** — candidate ownership now covers all 40 layers/TP ranks, with ordered L1 S0/S1 packets and bitwise accumulation tests. L0 binder exports 111 validated instructions. Physical ROM addresses, executable L1 stage programs and full-token trace remain open.
- [x] **v41_collective_throughput: actual-program component baseline** — all 12 emitted layer-0 descriptors pass across four ranks, including VM write/readback and reuse; 2,780 blocked service cycles (2,802 testbench wall cycles). Synthetic operands and behavioral VM: producer compute, shared HBM and routed closure remain outside this gate.
- [~] **v41_fullshape_weight_layout: local physical ROM contract** — real FP8/FP4 checkpoint-to-bank/lane/row map and exact packed roundtrip implemented for one tile. Actual skew replay is now included: zero bank-port conflicts but 80,640 FP4 macro reads, not the idealized 46,080. Full-die fit and tile RTL expansion remain explicit gaps.
- [~] **v41_index_sharding: index collector cadence** — integrated the exact four-stack baseline (262,144 keys, 557,056 sectors, 13,131 cycles) and first pipeline correction. Root rechecks pass: 14 collector lengths/190 beats, 2,208 mapping cases, and short four-stack N65/N1040 at 80/132 cycles (baseline 82/149). Full key-delivery-only corrected gate now passes exactly: 557,056 sectors in 9,278 cycles (60.041 sectors/cycle), 29.3% fewer cycles than baseline. Shared-KV/HBM contention and full-token gain remain separate gates.
- [!] **v41_index_score_major: production scoring consumer** — current correctness adapter accepts a 64-key beat only every >=130 cycles and writes scores through one scalar VM lane. New pipelined full-dimension scorer/direct-selector path is the priority. Reader gate uses synthetic HBM with always-ready sink; no attention/token throughput credit. Already-run one-cycle reader candidate was 2.57% slower, so retain the 9,278-cycle two-cycle collector and stop reader tuning.
- [~] **v41_fullshape_core: production RoPE delivery** — standalone exact cache and routed 0.92 ns sub-block are ready; now integrating shared die HBM service, non-overlapping region assignment and SU coefficient mux. Root retains full-layer integration as pending.
- [x] **critical_path_tracker: schedule-checker correctness review** — rejects malformed/nonfinite resource claims, empty referenced queues and mismatched evidence; 16 focused tests pass. This strengthens admission checking, not a full-token verdict.

## Current claim boundary and priority

| Target | Current published result | Required next gate |
| --- | --- | --- |
| Qwen3-8B, two-reticle INT8 ROM, AR and DFlash | Model: **10,874 AR / 18,720 DFlash tok/s** at 8K; reduced INT8 TP-2 AR passes 18 exact steps (`results/rtl/hdc_qwen_int8_tp2_ar.json`). | Bind the source-pinned full-row W8 image to the full-shape program; run norm-folded TP-2 AR and DFlash exact tokens, then cycle and physical reprice. |
| Qwen3-8B, matched two-reticle weight-HBM | Model: **881 AR / 2,651 DFlash tok/s**; reduced same-controller A/B and cooling-capped AR ratios only. | Same full-shape program and RTL with weight source switched, exact state in both arms, sustained bandwidth and routed comparator path. |
| DeepSeek-V4.1-Flash ROM array | Old K-split model: **7,049 AR / 15,890 MTP tok/s at 1M**; bit-exact row-split with transferred old tails: **6,630 / 14,601**. Exact depth-128 collective tails condition AR to **5,033**; the correct TP-4 `wo_a` activation load at the current G4 read width further conditions AR to **3,668** (`results/arch/v41_fullshape_load_floor.json`). The six-position stage MTP sensitivities **6,851 fused / 6,185 serial** omit this full producer load and are not calibrated. None is measured chip throughput. | Execute the real full-shape program with packed images and exact state; widen the activation read path and remeasure its critical-path load, collective writes, index scan, full die cycles and route. |
| DeepSeek-V4.1-Flash HBM-only comparator | Model-only, about **3,580 AR tok/s class**; reduced two-package QE-only weight-source A/B passes (`results/rtl/hdc_v41x_matched_weight_ab.json`). | Stream **all** weight families through bounded HBM windows on the same full-shape program; exact array A/B and shared-controller saturation. |

Qwen ROM DFlash assumes four extra lane copies (m=5), an **open physical feasibility gate**. V4.1 adopted-width die gather RTL with a 128-entry receive FIFO measures **1,220-cycle activation and 476-cycle output exposed tails**; the original 16-entry FIFO measured 4,948/1,408 cycles, while the old model allowed 219/167 (`results/rtl/v41_collective_depth_campaign.json`). The 5,033 AR and 6,851/6,185 MTP rates retain stage stubs, behavioural links, inherited other tails and unresolved index throughput. Keep these limits visible in the paper.

## Qwen ROM: full-shape exact path

- [x] Contract and quality: signed INT8, per-output-row BF16 scale after FP32 K-split sum, two reticles, 6,144 lane groups/die, eight HBM3E stacks/package. Full-model deployed-arithmetic quality passes the pre-set rule (`results/quality/qwen3_8b_weight_format_search.json`). This does not prove TP-2 hardware's different K-split order.
- [x] Reduced two-die INT8 AR: 18/18 exact steps, tokens 1073/382/93, zero logit/KV/VM mismatches (`results/rtl/hdc_qwen_int8_tp2_ar.json`). Scalar SU, unfolded norms, behavioural ROM/UCIe and reduced shape limit the claim. Reduced m=5 arithmetic and logical exchange gates exist (`results/rtl/hdc_qwen_m5_arith_commit.json`, `results/rtl/hdc_qwen_m5_verify.json`), without full O4 timing or area.
- [~] **Full-row W8 checkpoint image and golden** — `qwen_fullshape_int8_image`, `/tmp/opentallas-qwen-fullshape-int8-image`; `qwen_fullshape_emitter` and `qwen_o4_end_to_end` integrate full-shape ISA/program. Full-row-before-slice code/scale and folded-norm layer-0 images pass a source-pinned real-checkpoint probe (`results/rtl/qwen_o4_int8_layer0_image_audit.json`); bind them to ROM words and exact execution. The old reduced image quantized each slice separately; real `o`/`down` rows disagree. Widen token IDs for the 151,936-word vocabulary. Next: checkpoint layer-0 exact outputs, then a full token.
- [~] **DFlash acceptance and schedule** — bounded exact-INT8 target and drafter pilots are pinned (`results/speculative/qwen3_dflash_int8_target_pilot.json`, `results/speculative/qwen3_dflash_int8_drafter_pilot.json`), but τ remains a sensitivity. `qwen_o4_end_to_end` must resolve the drafter's fused-versus-separate qkv K-split and run exact TP-2 draft, m=5 verify, accept and commit before a rate claim.
- [~] **Controller correctness and cycle calibration** — `qwen_o4_end_to_end` fixes G6144 DYN attention tile count and non-power-of-two argmax. The G6144 split-tree depth is corrected in the published AR model (`5723c128`; now 10,874 tok/s), but `qwen_m5_model_reprice`, `/tmp/opentallas-qwen-m5-reprice`, still must reconcile UCIe, 8K KV, drafter and m=5 reducer timing with the actual program. Full 8K consecutive-token/bounded-buffer evidence remains open. Regenerate DFlash and Atlas after exact gates.

## Qwen HBM comparator and physical closure

- [x] Same-core reduced ROM versus weight-HBM comparison passes; its +5.60% vector delta is a reduced-bench measurement, not O4 throughput. Cooling-capped **AR model** ratios are source-pinned in `results/arch/qwen3_budget.json` (scenario B liquid 12.4536×); speculative HBM capped point is open.
- [~] **Full-shape HBM-only source switch** — `qwen_o4_hbm_comparator`, `/tmp/opentallas-qwen-o4-hbm-comparator`; same INT8 program/images, controller, KV HBM and state checks as ROM. Gate exact logits/token/KV/VM in both arms before a cycle delta.
- [x] **Reduced same-controller bandwidth knee** — two exact G4/SW16 steps with timed KV HBM and one weight pseudo-channel give ROM 50,759 versus HBM 189,428 cycles (3.732×); HBM delivers 89.1% of channel peak. Four channels give ROM 50,950 versus HBM 53,592 (1.052×) (`results/rtl/hdc_qwen_weight_bandwidth_bound_g4sw16.json`). `qwen_hbm_knee` owns TP-2 full-shape replay; these deliberately bandwidth-bound reduced points are not O4 rates.
- [!] **Full-shape HBM stream contract** — current `wchunk<=32` cannot split an unsplittable K-round: qkv needs 128 words and gu 512 words at full shape. `qwen_o4_hbm_comparator` must implement bounded within-round continuation and a separate `lm_head` scale base before the same-program HBM comparator token gate.
- [!] **m=5 area/timing** — direct INT8 arithmetic detailed route is DRC-clean but misses 0.92 ns by 297.76 ps. A bounded ROM/32-product-lane shard reached global route, but ROM-output→first-product register WNS is **−1,218.18 ps** and post-ROM combinational delay **1,333.16 ps** at a 920-ps clock (`results/physical_hdc/asap7/qwen_o4_int8_shard/global_route.json`). A registered ROM probe improves that boundary by only 37.66 ps; wide `x` fanout remains. `qwen_m5_route_result` and `qwen_int8_tile_physical` own a new retimed lane route and matched N1/N5 area before any m=5 claim.
- [ ] **Package physical evidence** — route adopted INT8 tile/core boundary with realistic ROM/SRAM/HBM/UCIe abstracts, then per-die area, wire, power and setup/hold. Historical G4/W4 and W4/G2 routes do not close O4.

## V4.1 ROM: full-shape exact path

- [x] Reduced adopted tile/die exists; one die token passes exactly with behavioural HBM-backed attention KV (`results/rtl/hdc_v41x_die_top_smoke.json`). Reduced two-package same-program ROM/QE-weight-HBM A/B is exact: 1,006,625 versus 1,283,915 cycles (+27.55%; `results/rtl/hdc_v41x_matched_weight_ab.json`). Neither is a full-shape rate.
- [x] Full-shape ISA address/count/ID profiles, DYN geometry, blocking COLL op and TP layer-0 emitter are published. Full-shape golden shard records cover 200K and 1M (`results/rtl/hdc_v41x_fullshape_golden.json`), with tokens 121449 and 11045 respectively; the 200K margin is only 0.00998, and independent exact replication remains required before either token is an RTL reference. `w2` output-row split is mandatory: old K-split differs from real golden rows; `wo_b` keeps fixed-rank unrounded FP32 reduction. No full RTL token match yet.
- [~] **Full-shape weight/image layout and shard replay** — full-only CHUNK8 QE passes a standalone exact 192-block/8-row LINQ gate (`results/rtl/hdc_v41_fullshape_qe_gate.json`). The 200K L0 rank-0 selected-token layout packs 29 matrices and 11 CROM objects, with exact `wo_a` BF16 and ME `plg3` probes (`results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json`); sparse HBM sectors map identically (`results/rtl/hdc_v41x_fullshape_hbm_sector_map.json`). The RTL parameter preflight still fails closed on ME and HE full-shape geometry; `token_runnable=false` pending emitter and full shard. `v41_fullshape_weight_layout`, `v41_fullshape_core` and `v41_fullshape_golden` own the exact L0 replay.
- [!] **Image format versus QE port** — the selected-checkpoint image is physically packed FP4 but the core consumes a 16-lane expanded qstream. Expanding the selected L0 QE words would need **3.912 GB**, above the 2.714 GB/die ROM capacity; packed storage plus other engines is **2.127 GB**. `v41_fullshape_weight_layout` has a source-pinned 25-matrix logical stream gate in isolated commit `23381181`; integrate it and implement the packed-to-expanded adapter with exact word order, buffering and routed area before a token or capacity claim.
- [!] **Activation and HE load floors** — the former `wo_a` splitj=8/xjs=2048 descriptor exceeds the TP rank's 8192-element ACC and is invalid. The correct two no-splitj ME operations, each K4096, require **2,048 read cycles per layer** at the current G4 VM path, across 40 sequential layers. With otherwise unchanged measured collective tails, conditional 1M AR is **3,668**, not 5,033 (`results/arch/v41_fullshape_load_floor.json`). The HE K2560 path needs 2,560 read cycles per operation at 8 elements/cycle; hiding that behind other work is unproven. `v41_fullshape_core` owns real-operand two-op replay; `v41_me_he_macro_pipeline` owns bank-local wide preloads. Reprice only after those exact gates and a physical macro boundary.
- [!] **Constant-ROM and expert placement** — the preliminary full-shape program also leaves CROM constants and expert bases at zero. Bind norms, RoPE, Engram constants and HC scales to a checked manifest; use physical expert IDs with fixed sparse slots or an explicit ID remap. A one-matrix image does not make a layer runnable.
- [~] **Packed HBM KV** — core/tile packed-window block sideband and selected-CKV K arbitration are integrated (`854a0a27`, `7126946d`); `v41_die_packed_kv` still owns 528-B FP8+scale row write-through, prefetch, staging and generation. `v41_integration` owns array replay. Next: full-row read/write through four shared stacks with concurrent index traffic, then exact die token. Unpacked 32-bit-lane KV uses about 3.9× modeled storage/traffic.
- [!] **Absolute KV row addressing** — the full-mode die packed-window write boundary is linted and faults on unreserved users, stale rows and saturated local `WINM1` rows (`results/rtl/chip_v41x_packed_die_boundary.json`). The full-shape emitter still clamps `WINM1` to 128; the producer must pass an independent absolute HBM row or rebuild the local window, then prove boundary/wrap exactness before a 1M token. Full-shape scalar KVD reads still fault.
- [~] **Compressed KV and Engram** — selected-CKV standalone DMA passes two exact 512-element FP4 rows on distinct stacks and exhaustive 4,096 code-scale pairs (`results/rtl/v41x_ckv_selected_dma.json`); remote-die fabric, die integration and throughput remain open. The 68-macro attention stage passes reduced three-job golden in 444 cycles and full geometry lints (`results/rtl/hdc_v41x_attn_macro_stage.json`). `v41_ckv_selected_dma` and `v41_attention_physical` own direct packed-row integration and the adapter BF16 row-buffer/re-encoder replacement; neither standalone gate closes the full engine.
- [!] **Collective throughput and switched array** — die DMA/fixed-rank reduction pass exact gates, including 64 real L0 `wo_b` rows (`results/rtl/v41x_coll_die_gate.json`). A 128-entry FIFO reduces exact adopted-width gather tails from 4,948/1,408 to **1,220/476 cycles** (`results/rtl/v41_collective_depth_campaign.json`). An act266-flit all-gather writes **1,064 64-B VM words per die**; one VM write/cycle cannot meet the old 219-cycle exposure even with unlimited link credits. The collective throughput owner must add ≥5 write banks/ports or prove overlap and remeasure. The six-position MTP stage is exact for fused and serial descriptors, but the full producer schedule is unverified; `v41_integration` owns array replay.
- [~] **Index-key capacity and throughput** — opt-in paired sharded writer/reader passes exact 65-row HBM roundtrip (`results/rtl/hdc_v41x_idx_shard_roundtrip.json`) and 1M address boundaries, but default still replicates keys. Serial sharded scan reaches **0.297 sectors/cycle** and tagged per-PC scan **2.154**, only **1.72% of 125 modeled** (`results/rtl/hdc_v41x_idx_shard_reader_pc.json`). `v41_index_sharding` owns parallel scheduling, user offsets and array integration. Reprice capacity/power and prove concurrent multi-user scan before using 866 users as demonstrated capacity.
- [~] **Clock and power reprice** — `v41_model_reprice`, `/tmp/opentallas-v41-model-reprice`, must price exact two-gather `w2`, repaired index sharding, packed KV, measured collective tails and busiest-die liquid cap. Published 7,049/15,890 and provisional `results/arch/v41_tp_exact_reprice.json` remain sensitivities. With the depth-128 exact stage tails, `results/arch/v41_tp_rowsplit_measured_reprice.json` conditions AR to **5,033 at 1M** and MTP to **6,851 fused / 6,185 serial** only for the measured six-position stage. The one-write-per-cycle VM interface needs 1,064 cycles just to emit the 266-flit all-gather output, so old 219-cycle exposure is structurally impossible without more ports or proven overlap. Index and full producer timing remain outside these rates.
- [~] **Rate-lever order** — the source-pinned sensitivity `results/arch/v41_rate_optimization_search.json` places index delivery and collective VM writes ahead of wider weight lanes: the tagged reader's measured 2.154 sectors/cycle would condition AR to 2,315; hypothetical four-stack 60 sectors/cycle gives 4,952; the modeled effective 103.5-sector/cycle cap gives 5,033. A four-write-bank gather is an **unbuilt** 6,231 AR sensitivity, not an RTL result. `v41_collective_throughput` owns the exact GW4/transpose gate; `v41_index_sharding` owns four-stack request scheduling and collection; `v41_vm_bank_physical` owns banked VM route. Only an integrated, routed gain can replace the headline.
- [!] **Competing rate floors** — collective-only 5,033 and index-only sensitivities above omit the corrected TP-4 activation load. The source-pinned load floor gives 3,668 AR at 1M for G4 with inherited other tails; this remains optimistic until the index reader reaches the modeled 103.5 sectors/cycle and the full program executes. Treat any faster write-bank or link result as a separate conditional sensitivity until the same source-pinned schedule includes ME/HE loads, index traffic, KV and HBM contention.
- [!] **GW4 physical width** — the exact four-word/cycle gather produces **4×512 bits per clock**. A representative 128-bit quarter-slice pre-route STA passed, but the full 2,048-bit rotating distributor misses the 0.92 ns target by **1.498 ns before route**. `v41_collective_throughput` and `v41_vm_bank_physical` are changing the transpose-buffer output to static physical bank order, then will route the complete boundary. The 469/240-cycle GW4 exact stage tail is simulation evidence, not an adopted clock/rate.

## V4.1 HBM-only comparator and physical closure

- [~] **All-family HBM weight path** — The standalone eight-bank HCP ROM/HBM gate passes 144 golden outputs per arm from the same reduced L24 projection (`results/rtl/hdc_v41x_hcp_hbm_exact.json`, `52367cae`); ME/QE/HE and full-shape HCP integration remain open. `v41_integration` owns comparator die/array integration. Next: same full-shape program, all weight families HBM-fed, exact state against ROM and realistic contention with packed KV/index.
- [~] **Die and tile route** — `v41_die_physical`, `/tmp/opentallas-v41-die-physical-next`, owns arbiter/PHY/tile/die hierarchy. Original square 32-PC arbiter pin placement failed with 40,332 pins versus 5,008 positions; a 12-mm PHY-edge strip subsequently **passed pin placement** with all 40,332 pins (`results/physical_abi3/asap7/chip/v41x_hbm_karb/strip_pin_placement.json`). A four-channel local route case is defined, but neither strip nor local bank has routed setup/hold, DRC or power closure. Current reduced-scale macro/abstract tile and die cases are prerequisites, not full-shape die closure (`docs/V41X_DIE_PHYSICAL_PREFLIGHT.md`). `v41_attention_physical` owns banked attention. Next: adopted tile/die route with credible ROM/HBM/SRAM/PHY macros and extracted area/power/wire.
- [!] **Pin-access and macro boundary** — placing the monolithic 40,332-bit K-arbiter port in a PHY strip solved its pin placement, not full detailed routing. A separate attention SRAM bank reached global route but detailed route failed on macro pin access. Keep wide activation/score data bank-local with registered narrow flits across partitions; require a detailed-route gate on a representative local bank, then the adopted tile and die. No positive global-route slack is a full-route verdict.
- [!] **Serial full-shape HBM reader** — serial sharded reader delivers 0.297 sectors/cycle; a tagged per-PC variant improves to 2.154 sectors/cycle but still reaches only 1.72% of the modeled 125 (`results/rtl/hdc_v41x_idx_shard_reader_pc.json`). The parallel scheduler/port architecture is a throughput blocker; the comparator and ROM shared HBM model must use the measured implementation or a new source-pinned parallel gate.
- [ ] **Full-system rate** — after ROM and HBM paths are exact and physically feasible, run source-pinned batch-1/saturation schedules at 1M/200K, MTP both sides, measured controller/collective tails and per-die cooling. Then regenerate GPU/fused roofline/HBM/ROM comparison.

## Publication gate

- [x] **Automated final-number readiness inventory** — `results/arch/final_number_readiness.json` independently checks the source-pinned golden, executable image/program/geometry, activation-load model binding, collective tails, index bandwidth, HBM pin placement, full-shape exact ROM/HBM records and die route. `make check-figures` verifies the inventory remains current; `python3 tools/final_number_readiness.py --require-final` fails while any terminal gate is blocked. A passed partial gate never promotes a modeled rate.

- [x] Headline bundle and prose census are checked by `make check-figures`; V4.1 10→8 HBM-stack correction and busiest-stage occupancy are published. Qwen W8 and V4.1 2K arithmetic quality are separate from RTL throughput proof.
- [~] **Claim audit** — `paper_claim_audit` and `qwen_m5_model_reprice` track provisional Qwen m=5 and V4.1 row-split/capacity statements. After a rate-changing result, update its source record, Atlas, `docs/HEADLINE_BUNDLE.md` and this tracker together; run focused exact tests and `make check-figures`, then push main. Historical stale pins stay labeled; final-claim pins must be current.
- [ ] **Final release** — four full-shape exact records, ROM/HBM matched programs, full-chip cycle/energy/rate derivation, adopted physical route evidence and current source pins for every final claim. Close an item only with its commit and record path.
