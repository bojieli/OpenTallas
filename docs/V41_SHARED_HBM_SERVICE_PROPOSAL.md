# V4.1 common HBM service: proposal for root approval

Baseline: `9ac1d9be`. This is an architecture proposal, not implemented shared-HBM evidence.

## Existing interfaces and failure mechanism

`ot_chip_v41x_hbm3e_phy` currently instantiates two independent timing models per physical stack. The K model has 32 PC request/response ports, 256-bit sectors, 4-bit lengths/beat IDs, KTAGW=17 after K arbitration, 64 queued sectors/PC and per-bank refresh mode 3. W is a separate model with NPC_W=8, one burst request, 6-bit length, LWIN=10 tag, 5-bit beat ID, eight 256-bit response ports, and independent bank, queue and refresh state. W and K cannot both claim the full physical stack. Region sizes also refer to independent backing arrays, not a common allocation.

The adopted QE `S_ROWS` consumes one 4352-bit logical word every clock without ready/stall. FP8 requires 17 sectors/word; FP4 requires nine. Its 1024-word window and `cfg_rate` admission threshold cannot guarantee correctness under arbitrary shared traffic. Eight PCs at the model's 1024 ps sector spacing provide at most 7.8125 sectors/clock at a 1000 ps core clock: below even the nine-sector FP4 demand. Long operations therefore already require a finite-operation head start; arbitrary long operations are unsustainable at eight PCs.

## Proposed common timing owner

1. One 32-PC `ot_hdc_v41x_idx_hbm` instance owns bank/open-row/refresh/command timing and allocated contents for each stack. Preserve all its timing constants and refresh policy; do not add the independent W model's bandwidth.
2. Full-shape W uses NPC_W=32 and the same XOR PC mapping as K. Reduced historical mode remains explicit and separate. Do not silently turn eight PC lanes into 32 without recording the changed interface.
3. W burst adapter splits a 9/17-sector word into one-sector requests by actual PC. Preserve original word tag and sector index in the model request tag. K bursts retain their current mapping restriction: every beat must belong to the request PC. K response tags/beat IDs pass unchanged; W returns carry the original word tag and five-bit sector index.
4. A common physical address ledger assigns disjoint K and W intervals. Existing local image offsets require explicit relocation. Both ranges are checked before model request admission. No high-address modulo aliases and no claim that two separate allocations fit the same stack.
5. WINDOW owner proposes eight outstanding single-sector reads per stack, at most one response/clock into its stage. Scale follows all sixteen code replies; rows drain before reuse. Writes remain completion-serialized. Respect this existing endpoint rate; no extra WINDOW banking is assumed.

## Reservation and queue proposal

Root requires minimum W service rather than optimistic fair arbitration. Use configurable per-PC sector credits (candidate W:K reservations 1:1, 3:2 and 5:3), plus work-conserving borrowing when the reserved client is idle. Requests are admitted only if the scheduled combined workload fits its measured/proven service envelope. Reservation applies to sector service opportunities, not merely burst grants. A 15-sector K burst must not count as one sector. The memory scheduler must enforce the reservation or provide a worst-case service envelope covering its reordering; front-end arbitration alone does not prove a DRAM bandwidth guarantee.

Initial bounded adapter budget: eight W burst descriptors, maximum 32 sectors/descriptor (existing five-bit return beat field), at most 16 W sectors outstanding per physical PC. Reserve return storage before admitting the burst: 16 × 32 × 32 B = 16 KiB W data capacity, plus tag/valid metadata. Common DRAM queue stays 64 sectors/PC, shared, not 64 for each client. Admission must reserve space for the complete burst; no partially accepted word that deadlocks on its own credits. Exact metadata widths and physical implementation require review after tag composition.

K and W response paths must be independently backpressurable through bounded demux buffers; a stalled W consumer must not lock the only shared return head indefinitely. K write completion remains attributable to K because W is read-only in this first implementation. Additional weight families must join this budget before the comparator is complete.

## Ideal bandwidth arithmetic, not achieved rates

At 1000 ps core clock / 1024 ps sector spacing, 32 PCs have an ideal ceiling 31.25 sectors/clock, before row conflicts, refresh, command timing and controller stalls.

| W share | Ideal W sectors/clock | FP8 word/clock | Ideal residual K sectors/clock |
|---|---:|---:|---:|
| 1/2 | 15.625 | 0.9191 | 15.625 |
| 3/5 | 18.750 | 1.1029 | 12.500 |
| 5/8 | 19.53125 | 1.1489 | 11.71875 |

Thus a 1:1 split cannot sustain an arbitrarily long FP8 phase even at ideal timing. The 3:2 and 5:3 rows are candidates to measure, not approved guarantees. Real per-PC address skew and bank timing can invalidate both. Recompute for the adopted clock; do not preserve these numbers when frequency changes.

Let C(t) be actual QE word consumption, S(t) completed words with all sectors received, and B initial resident words. Require `B + S(t) - C(t) >= 0` on every cycle and occupancy no greater than 1024. The required initial buffer is `max_t(C(t)-S(t))`, over the real finite operation and all supported service stalls. A service-latency envelope beta(t) must include refresh, older queued requests, row conflicts and response backpressure. `RFCPB_PS=200000` is not itself the complete blackout bound. Without a valid bound, no fixed-latency full-shape admission guarantee exists.

## Minimum executable acceptance before adoption

Run identical actual-model workloads: W only; K only; combined; combined with consumer backpressure; combined across refresh; same-PC conflicting rows and distinct-PC controls. Use nonzero address-derived data, writes with completion then dependent reads, FP8/FP4 word assembly, and high-region range guards. Count unique accepted/completed sectors, physical command/refresh events, per-client maximum service gap, occupancy and W underflow. Compare shared service to an intentionally separate-model negative control, which must expose double-counting.

For every real QE descriptor, replay its exact request/consumption trace and report the required head start against the 1024-word window. Sweep candidate reservations with the same addresses and timing constants. Include the WINDOW eight-credit trace and actual index trace simultaneously. Accepted result must show exact data, no starvation under the defined bounded-stall assumptions, no underflow, and achievable required service. If the reservation cannot satisfy all clients, send root the deficit and options: change placement/PC allocation, increase local capacity within physical budget, alter scheduling with its real latency cost, or add explicit QE stall/replay. Do not silently serialize away the throughput objective.

No implementation or rate is approved by this document alone.
