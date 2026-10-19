# HBM-BW functional successor evidence (2026-10-19)

Source revision: `9e8fcf77e` on `claude/hbm-bw-1019`. Four real PC leaves feed the sparse DRAM fixture with native command timing checks. All measurements use Verilator 5.050 and convert 0.9765625 GHz HBM cycles into 1.2 GHz stream edges.

| Controller/layout | Sustained B/stream edge |
| --- | ---: |
| Original leaf, row per block | 45.03 |
| Original leaf, DS bank-set trace | 41.53 |
| Multi-row, DS with one expert copy | 72.52 |
| Multi-row, DS with three expert copies, seeds 1/2/3 | 95.19 / 95.69 / 95.25 |
| Multi-row, packed sequential stream | 103.96 |

The three-copy DS trace is within 10% of the 98.9 B/edge price. Packed streaming is a peak demonstration and is not a substitute for production measurement. Controller JSONs are diagnostic performance evidence, not a data-exactness proof: their response tracker does not compare payloads. The integrated production `bw_l14.json` provides the data proof: all 23 matvec operations and 93 result rows pass bit-exact, all 39 descriptor go slots match the static compiler slots, no fault, at the 88-edge/full-block price. This test uses the real die SM master, relative issuer, programme store, four successor controller leaves and physical DRAM command fixture.

## Adoption conditions

This successor is **not physically qualified and must not be bound to a release die** yet. Old masters remain unchanged; the successor is selected in this bench only by `HBM_MR`.

* `layout_bw` stores three copies of routed experts on distinct bank sets. Price logical payload and reserved row footprint against each model's HBM capacity; the old row-per-block allocator reserved more space than its payload, so a payload-only multiplier is insufficient.
* The new leaf has a 64x64-bit queue plus row sidecar, two 128x21-bit identity rings, and the AQ has 64x30-bit metadata. These are runtime indexed flop arrays, violating the SAFE >2kb SRAM rule. Move identity/FIFO metadata to SRAM, retain a small registered head, and expose per-bank pending-row summaries to ACT lookahead rather than scanning a 64-entry indexed flop queue.
* The AQ's combinational oldest-first scan and 32-bank priority selection require a pipeline/fanout audit. Any added stage must be charged to the compiler's fixed prefetch lead and rechecked at the 88-edge price.
* No physical kit, gate, SS setup, FF hold or area claim exists for this successor. The ordinary DRAM fixture checks individual command timing; it does not independently prove each bank's maximum refresh interval. Add a retention-window monitor before signoff of the new pull-in policy.

The four-layer production replay `bw_full.json` FAILS after one completed run:24of66 ops pass,37of154gos, issuer late-go atcycle14290 in L02. This is an open qualification failure. The late-ids negative replay faults atcycle9093 as expected; IMUT=2 preserves all39exactgo slots but corrupts12of23 operations. Their raw witnesses are committed under `witness/`. These results must remain visible in any adoption decision.
