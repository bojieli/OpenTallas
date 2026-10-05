# DeepSeek single-user floorplan connectivity contract

Baseline: `8f6925ba`. This is a placement input, not a placed or routed design.
The machine-readable ledger is `results/contracts/v41_floorplan_connectivity.json`.
Root owns coordinates, replication, storage additions and clock budgets.

## Placement constraints that follow from the implemented interfaces

1. **ROM_MAC:** keep each weight bank, capture registers and consuming MACs in
   the same local cluster. The 274-bit physical macro word is not the core's
   logical lane word. Preserve the validated FP4/FP8 lane map and bank-port
   ownership; no global weight bus is assumed. Orient pins toward consumers.
2. **VM/ME:** place activation read banks, converters, ME activation SRAM and
   bank-local write controls together. The G4 operand path is four scalar FP32
   elements (128 bits) per cycle, not four vector words. Two K4096 `wo_a` loads
   expose at least 2048 issue cycles before additional pipeline/control time.
3. **ATTENTION:** place four packed row banks, their read registers, chronological
   row rotation, merger and attention ingress in one neighborhood. Its buses are
   16896 bits before per-block format tags and 16960 bits at engine ingress;
   these are local connections, not proposed full-die spines. The intrinsic
   staging memory accepts four rows each cycle with a two-cycle read path.
4. **Probability storage:** place the adapter's head/row banks by PV tiles and
   their VM producer. The current 512-bit local readout comes *after* a G4 scalar
   preload. H16/T640 takes 2560 issue cycles; L0 T128 takes512. Widening readout
   to1024 bits saves a local phase but does not remove that dependency. Proposed
   four-row/head readout needs64 explicit16-bit read banks. Existing adapter
   storage20KiB and proposed engine stationary storage increment64KiB are
   different allocations and must not be conflated.
5. **COLLECTIVE/VM:** locate transpose output beside four destination VM banks.
   Reserve four local512-bit channels and bank-local capture. Word bank is low
   two address bits. The source is one512-bit word/cycle with two skid entries;
   the destination is four words/cycle with a two-cycle commit pipeline. ISA
   addresses are elements; DMA addresses are16-element words after alignment
   checks. Completion must wait for the final write commit.
6. **HBM_SERVICE/INDEX:** keep pseudo-channel demultiplexing and collection near
   stack interfaces. Send packed sectors to attention staging and locally score
   index keys before candidate reduction. Do not expand all128 PC interfaces
   into top-level physical pins. Allocate latency/credits for registered links
   between these neighborhoods; the allocation is still a root decision.

## Exposed latency, in priority order

| Priority | Boundary | Present evidence / required correction |
|---|---|---|
| 1 | HBM WINDOW refill → attention | Current source allows one transaction and completes refill before stream.128 rows need2176 sectors. The II1 replay candidate alone does not solve refill. |
| 2 | VM → HE/PV preload | HE reads20480 elements at8/cycle; PV reads10240 at4/cycle. Both have2560-cycle ideal issue floors before pipeline/drain costs. |
| 3 | Index delivery → scorer → select → CKV | 9278-cycle four-stack reader record is an always-ready consumer measurement. Combined consumer service and global ID ownership remain required. |
| 4 | ROM/SRAM → compute | Integer bank placement, macro access and local routing must preserve exact arithmetic and the priced clock. |
| 5 | Collective → VM → dependent op | Charge the emitted sequence and final commit, not unlimited sink bandwidth or speculative overlap. |

This is an engineering priority order, not an additive full-token latency
estimate. Paths differ across layers and may overlap only when the executable
resource schedule permits it.

## Layer types and dependence boundaries

L0 at position199999 uses128 WINDOW rows, no selected compressed rows. Its
attention service proof does not prove later indexed layers. Indexed paths add
scan, exact global candidate merge, source-owner mapping and up to512 selected
288-byte CKV rows before the packed640-row attention job can complete. WINDOW
FP8 rows contain528 bytes and consume17 physical32-byte sectors.

The PV operand contains **unnormalized exponentials**. Preserve the emitted
scale/max then exp/sum ordering before PV reads S; denominator division follows
PV. Streaming before the max is ready is a numerical architecture change.

MoE/shared `w2` uses output-row partitioning, activation gather, and rounded
output gather. `wo_b` K-split uses the fixed FP32 tree
`((r0+r1)+(r2+r3))`. Physical routing must not silently change reduction order.

## What the parent floorplan must supply

For each ledger edge: endpoint regions, maximum wire delay, pin side and
layer allocation, pipeline latency, burst/credit/storage allocation, and actual
arrival/required times. Distances remain null until macro geometry and library
parasitics justify them. A guessed micron limit is not a timing budget.

Acceptance requires both a single-user dependency schedule and a physical fit.
Only afterward schedule independent users into idle resources; do not sacrifice
the critical single-user path to maximize nominal occupancy. Queues must cover
arrival-minus-service backlog including response bursts, not only mean traffic.

The inventory partner supplies `results/floorplan/v41_resource_inventory.json`:
it flags the actual/model controller, router and collective count mismatch.
Until root resolves those counts, neither fit nor full-die throughput is proven.

## Evidence scope

Every repository source used for this ledger is SHA256-pinned. The probability
producer proposal is separately identified by commit39c5bc82; it is a transport
model, not adopted RTL. Existing records are retained at their own pins and are
not silently promoted to current composed-system evidence. None of this report
claims a numerical full-layer result, a routed die, or a token rate.
