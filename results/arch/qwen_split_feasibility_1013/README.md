# Qwen TP8 split feasibility — candidate, not adoption

The merged eight-die design remains the plan of record. This parallel study asks whether separate compute and KV/system dies offer a credible fallback. It establishes a partial geometric construction and traffic lower bound, not physical closure or accepted performance.

## Why an apparently 55–60% floorplan became difficult

The original F2 estimate (stream log 2026-10-12 07:34) was 31.17 × 25.78 mm, about 804 mm², with roughly 60% **modeled slot occupancy**. This was not placed standard-cell utilization. Empty area included required relay, bus, clock and power corridors. It was not a freely allocatable contiguous reserve.

Actual hardened hierarchy increased the ROM tile request from 311.04 × 1296 µm to 362.88 × 1442.88 µm. The 2026-10-13 08:38 request explains the cause: a closed 311.04-µm-wide ROM-pair leaf needs edge access, each 1024-bit return row needs a channel, and the lane/node leaves must fit with legal spacing. Across 768 tiles, the request adds about 92.6 mm² before other growth. The latest 399.6-µm-wide candidate is larger still; at a 419.904-µm pitch it leaves only 20.304 µm beside the tile, while the station needs 52.68 µm, or 64.8 µm after the wider root format. This is a direct geometry contradiction.

The independent window audit's actual g8 assembly has 501.264 mm² of non-relay hard-frame union in an 822.993 mm² die (60.907%): ROM tiles 314.717; stations 4.194; KV/HBM frames 120.431; IO 32.124; other ROM/shared-system frames 29.799. Its remaining 321.729 mm² includes 19.222 mm² of relay/reset frames. The g5 larger-tile trial increases tile area by 87.369 mm² while increasing die area by only 35.273 mm², consuming 52.096 mm² of former outside area. Its 26.0172-mm height exceeds the 26-mm limit. These are frame measurements, not standard-cell density.

The VM is a separate local-routing problem: its current reservation is 4.8384 × 2.54664 mm (12.322 mm²). Moving that rectangle alone frees only 1.44% of the reticle area. Its band cut was already greater than 100% before root-gather/control traffic. Correct tile X delivery requires 32 × 128-bit roots plus tags; the former two-root representation did not implement the full array. The split should keep VM, SU and X delivery beside ROM compute; exporting that hot local network would create a much harder D2D bandwidth problem.

## Constructive compute-field candidate

`split_feasibility.py` generates 768 tile-request rectangles and 768 station allowances, checks every pair for overlap and checks the die outline. It uses the larger 399.6 × 1442.88-µm tile request, a 472.608-µm column pitch, 43.2-µm row channels, a 5.2-mm center reservation and a 1.963816-mm south IO/channel reservation. The result is **27.928384 × 25.741096 mm = 718.907214 mm²**, with zero overlaps/outside rectangles.

This is a useful falsifiable partial construction. It proves tile/station rectangle packing with sizable width relief after removing KV shorelines. It does **not** place the center's native slab groups, VM, SU, control, IO, D2D interfaces or the tree/clock/reset relays. It does not prove that its row channels have enough actual routing tracks. Those remain explicit gates in the JSON. The tile and expanded station sizes are current requests/allowances, not claimed closed masters.

## Partition and communication

Keep the ROM field, VM, SU, tree, local X caches and compute collectives on the compute die. Move HBM PHYs/controllers, attention heads/aggregators, posted KV write/merge and host/prefill handling onto the KV/system die. The exact role of package control and collective PHYs must be assigned once, with explicit transport between dies.

At TP8, under equal contiguous head ownership, one die owns 4 query heads and 1 KV head, with dimension 128. Per layer the minimum payload is:

| Direction | Payload | Bytes | 512-bit words |
|---|---|---:|---:|
| Compute → system | 512 FP32 Q values plus 256 E4M3 new K/V values | 2304 | 36 |
| System → compute | 512 FP32 attention-result values | 2048 | 32 |

The source-bound native profile is GT3072, four Q heads and one KV head per rank. Q contributes 32 FP32 words; new K/V contributes four E4M3 words. The reverse path carries 32 FP32 result words. Total payload is 4,352 bytes per rank and layer before control, embedding, framing, arbitration and credit stalls; this is not an end-to-end latency estimate. Q stays FP32 over transport and is RNE rounded to BF16 only at the canonical attention ingress. The 40-word receiver credit capacity remains valid for 36 actual incoming words, with no dummy second KV head. Source hashes are pinned in `../qwen_tp8_native_abi_1013/split_native_traffic.json` (formatter c8d25629c, receiver 4b66ce3a4, program 14065c8c7). Physical framing, credit timing, link rate and crossing cycles remain unqualified.

The historical TP4 split contract already keeps context-sized KV streams on the KV die and transports Q/new-KV/results. Its x64 PHY reference is 0.6047 mm² and 777.6 µm shoreline per endpoint, with a 777.6 × 518.4-µm adapter frame. Two endpoints add at least about 2.016 mm² per pair before bump keepout, buffers, clock/reset and routing. That older PHY and transport are not current TP8 physical qualifications. Historical latency numbers cannot be copied into the current ledger.

The current KV/HBM hard frames occupy approximately 120.4 mm² in g8, before relay corridors, center/host functions and larger head requests. This is a lower bound, not a separate system-die outline. A fresh constructive system-die plan must preserve four-HBM placement, real PHY dimensions, 128 current head views and 96 controller subleaves. The former generator provides a starting topology, not a valid current layout.

## Recommendation and decision gates

Run this feasibility path in parallel, while the merged design continues. Do not adopt a split solely from the partial packing. Require a complete real-view placement on both dies, actual-pin cuts and reach, explicit clock/PG hierarchy, native finite-credit D2D exactness and measured incremental layer/token latency. Compare total silicon, PHY, packaging, HBM placement and power, then choose the better verified design.

Increasing TP from 8 to 16 also shrinks each ROM field, but duplicates per-die interfaces/control and changes reduction and HBM ownership. It is a separate model/traffic/cost study, not the first fix for a demonstrable corridor/abstract mismatch. Neither TP16 nor the split eliminates the defective local X-delivery representation; that functional repair is required independently.

## Independent system-die geometric translation

A second candidate translates the **575 actual g8 KV/HBM/center frames** as three groups, preserving all relative geometry inside each shoreline and the six center frames. It reserves a 2.320056-mm center width for the current host-PHY outline, a provisional host-transport region, and the historical D2D PHY/adapter rectangles. Result: **10.044816 × 24.334512 mm = 244.435695 mm²**, zero rectangle overlaps and zero outside frames. The source-only frame extract retains the SHA of the complete source model.

This still excludes regenerated die relay/clock/reset trees and their actual pin/cut checks. It uses the older aggregate ECTL frame, so the 96 real A/B/C subleaves must be bound within it. Translations must be legalized against both signal lattices and actual PG phase. Host transport and D2D rectangles remain reservations/reference views. Thus this is a second partial construction, not a legal physical system die.

The two geometric candidates sum to **963.342909 mm² per pair**, about **12.3% above an 858-mm² single die**, before omitted or changed physical overheads. For eight pairs this means sixteen accelerator dies instead of eight, plus eight additional compute-to-system package links. This is a visible silicon/package penalty to trade against reduced physical risk, not a free area saving. A smaller complete compute layout or different system sharing could change the comparison; neither has been established.

## Actual-leaf follow-up: local geometry and protocol shape

The SU lane component now uses the four actual CLOSED LEFs and their TT/FF ETMs plus measured insertion records. Place the lane head at (108,0), EXP at (0,151.2), RCP at (151.2,151.2), and RSQ at (280.8,151.2) µm. Repeating 64 lanes with channels gives a 3434.4 × 2570.4-µm component, with 4.837294 mm² of children. All **199 exact bit-pin seams per lane** (12,736 repeated seam bits) have Manhattan length at most 285.78 µm; the actual-view per-pair 833-ps sensitivity reports 199 passes and no setup/hold failures. The initial EXP-to-the-right arrangement failed 37 seams, illustrating why geometric locality matters even when total area fits. This component omits the actual 88k-flop reducer, common glue, native x3 formatter and external interfaces. It is not an implementation of the full SU parent, and the sensitivity does not prove routed wires, SS internal paths or physical clock delivery.

The system candidate replaces its 32 aggregate ECTL frames with **96 real A/B/C views**, source-mapped cfg straps and the current engine-column mirror rule. All five RTL seams are included, including A.rvm_o → B.rvm_i. There are 19,808 exact bit-pin seams, no missing pins, no rectangle overlaps, and all TT/FF per-pair checks pass; the matched abutting seam pins are at most 0.084 µm apart. Full external head/controller buses, physical clocks, SS internals and translated PG/signal phase still need proof.

A real protocol mismatch also surfaced: the historical KV sequencer hardcodes **8 KV words, 32 Q words and 64 result words**. The earlier 4/16/32 BF16 transport proposal cannot complete unchanged and is not the current native ABI; current native transport requires 4/32/32 with FP32 Q. The earlier isolated shape prototype introduced HEAD_GROUPS=1 with BF16 Q, while leaving HEAD_GROUPS=2 historical defaults. Its receipts below remain historical control-component evidence. The actual newer named native sequencer `qkd_seq_tp8`/`qkd_seq_core_tp8`/`qkd_seq_xs_tp8` at 4b66ce3a4 uses HEADS1/Q_FP32=1 and nine independent child clock entries; old CLOSED TP4 views are not aliases for these masters. The one-group variant posts two rows with the correct `{v,0}` group tag and uses the corresponding Q/result counts. An admitted 8-GB, one-thread RTL control-component run on AGI passed two layers for each shape (one-group:32 Q/4 posted rows/64 results; two-group:64 Q/8 rows/128 results); corrupted halfword tags caused four actual output mismatches. This proves sequencer shape and row-tag behavior only. The harness synthesizes attention results and contains no PHY, native attention arithmetic, native SU formatter, full credit-loop composition or production throughput. Its 219/363 stimulus cycles are not latency prices.

The compute-local defects remain relevant to both architectures. Current VM region boundaries have thousands of actual-pin reach/timing failures and need registered, equalized staging. The current whole SU/reducer and host/prompt interfaces have incomplete physical masters. Removing HBM shorelines helps outer geometry but does not repair those components; the candidate cannot be selected until those shared blockers and complete native D2D composition are resolved.

## Why TP16 is not a drop-in alternative

The pinned Qwen3-8B config has 32 query heads and **8 KV heads**, each dimension 128. TP8 naturally owns four Q heads and one complete KV head per die. TP16 can own two Q heads per die, but it cannot own one-half of a KV head without a new partitioning mechanism. It must either replicate a KV head across two TP partners, serve those partners from a shared KV owner, or split the head dimension and introduce the required cross-partition attention reduction. Therefore a halved ROM field does not establish halved KV cache, HBM PHY, attention traffic or controller area. A TP16 study must account for the actual ownership mechanism and collective latency instead of simply dividing every current block by two.

## Concrete provisional host-static sites

The current closed controller-PC outline is 246.24 × 172.8 µm, smaller than the inherited 247.512 × 378-µm frame. For each of 128 PCs, placing the requested 129.6 × 172.8-µm static arbiter at (0,194.4) relative to the PC, and the requested 86.4-µm-square station at (151.2,194.4), gives a combined 246.24 × 367.2-µm envelope. All 128 combinations fit their old frames with no overlap, so these requested host sites need not enlarge the shorelines if their actual implementations retain those outlines. This opportunity applies to the merged plan as well as the split.

The new static/station outlines remain requests. The host-observer controller variant must also retain the closed PC's outline after adding its actual pins. Source hashes and request snapshots are included, but actual pin orientation, PG phase, clock/root and native saturation/ACK proofs are still gates. This geometric result must not be presented as placed or routed host logic.
