# Native routed expert IDs (component, integration open)

The new collector receives the actual `ot_hbm_idx_topk_static` CQ VM-write packet.
It recognizes the production MoE descriptor (384 scores, top 6, one row, ascending
IDs), checks the fixed write edge, destination address, byte mask, tag, sequence,
ID range and ascending order, then packs six U32 results into six nine-bit IDs.
The score/ID arithmetic remains in the existing engine. No ID payload comes from
host configuration, a golden preload, an attention selector or a second selection
implementation.

`ID_COHORT=1` is an opt-in relative issuer/group mode. A real accepted whole-layer
RUN increments a 16-bit counter and invalidates the previous IDs. The collector
counts the same CP launches and latches their layer metadata. Each issuer accepts
exactly one matching broadcast while running. Pre-run, duplicate, wrong-layer and
stale-cohort broadcasts fault; absent IDs fault by the first routed descriptor's
fixed go edge. Legacy default behavior remains unchanged. Counter equality is
paired with a finite native TOPK arrival window; it is not an unbounded packet
history or a software-provided token tag. All issuers must receive the same RUN
sequence and reset before this mode is admitted.

## Source-derived throughput and latency model

For `n=384,k=6,m=1`, let `ns=48` for aligned A, or 49 for unaligned A. The source
engine timeline gives `W=3+2(ns-1)+9+XRT+7+4*6+1`, hence aligned CQ at
`G+138+XRT+GO_DELAY+CQ_DELAY`. The collector publishes two edges after CQ becomes
visible; issuer capture is the following edge. The AM root has one command and one
CQ pin register, `XRT=1+VM_RT`; the `_am_pin` wrapper sets `VM_RT=1` (aligned CQ
G+142, publication G+144, issuer capture G+145). The existing unparameterized
231.5-cycle TOPK price and SMB `IDS_LAG=200` are not production proofs.

Only one 338-bit CQ result is sampled per routing layer; publication is one
79-bit word (valid + layer8 + IDs54 + cohort16). Six IDs arrive together, sustaining
one result per bounded TOPK transaction without credits. Sixteen SVG destinations
give 16 loads per broadcast bit before relay partitioning. The collector has
under 1,024 bits of fixed payload/control flops, no indexed storage and no queue;
each issuer adds one 16-bit run counter. Payload register banks are below the
2-kbit SRAM threshold. Actual synthesis area, mapped fanout/reset proof, physical
slot, macro inventory of the containing SVG, and regional clock compensation
remain obligations. No physical gate has been submitted.

Current compiled SMB programme groups the entire layer in one RUN. Exact existing
chronology (fixture evidence, not native TOPK integration):

| Layer | Arm / launch / rc0 | Router last command | Synthetic IDs | First routed reserve | First routed command |
|---|---|---:|---:|---:|---:|
| L00 | 630 / 632 / 635 | 7933 | 8133 | 8137 | 9328 |
| L02 | 13851 / 13853 / 13856 | 23028 | 23228 | 23232 | 24423 |
| L14 | 28946 / 28948 / 28951 | 41282 | 41482 | 41486 | 42677 |

The four-edge synthetic-ID-to-first-reserve spacing means adding a native collector
cannot simply reuse the old injection time. The compiler must derive visibility
of router activation/bias output, launch the actual TOPK descriptor/calendar,
then price its CQ+publication+landed-broadcast path and every reserve/fetch before
the unchanged fixed expert go. Shared-expert work may precede routed IDs.

## Integration obligations

`l17_router_ids.py` adds a real source-connected collector to the l15 relative
contract, copies real TOPK descriptor drivers, uses the designated CP RUN identity,
and wires all 16 relative SVG ID/cohort inputs. It refuses unknown TOPK masters,
missing l15 run metadata, prior ID drivers or partial source mappings. Its report
is explicitly structural only. No inputs are exposed as an ID oracle.

Before adoption: provide the `router_ids` physical grant; generate registered
79-bit broadcast lanes with every wire <=405 um and landed regional crossings;
prove CP run-count agreement, independent reset/reload behavior and latest-ID
arrival; compose the real router activation and TOPK VM calendars with the full
programme; run source-bound TT setup / FF hold/native closure. The collector's
status fault is a functional die output in the structural contract.

The minimum bench contains the real 384-score TOPK engine, its real CQ output,
collector and relative issuer with actual descriptor SRAM simulation. It checks
result order, repeated same-layer runs, reset/reload and expert address arithmetic.
Its VM score-return driver models fixed native return timing. VM write-ack protocol,
the full SVG/HBM feed and physical relay timing are outside this component bench;
their existing proofs do not establish this new end-to-end path.

Command (fleet, Verilator 5.050):
`bash rtl/test/hbm_idx_static/run_router_ids_static.sh OUT`.
Profiles: raw engine; AM-pin timing with `XRT=2` and input/output collar registers.
Mutants: wrong layer, wrong ID order, late CQ, absent second-run IDs,
previous-cohort second-run IDs, and previous result replayed on the next RUN edge.
