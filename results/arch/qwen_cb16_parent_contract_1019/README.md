# CB16 parent integration contract — MODEL, HOLD

This packet reconciles the preserved standalone CB16 incumbent with its real
packed native port ABI. It does not select a successor source, generate RTL or
views, or qualify clocks, reset, storage, PG, fanout, timing or routing.

Run `timeout 120 python3 results/arch/qwen_cb16_parent_contract_1019/reconcile.py`
from the repository. The finite check reads committed inputs, verifies all eight
native asset hashes and every data/flag rectangle in the four final landing
LEFs, then emits `contract.json`, `bindings.json` and `per_bit.jsonl.gz`.
The latter contains every packed signal bit, its logical-record mapping,
physical endpoint pin and candidate R0 position; unavailable native source FF,
clock root/phase, reset epoch, first use and fanout remain explicitly NULL.
R0 positions are the old diagnostic packing convention, not an adopted DEF.

## Source and hierarchy are different contracts

The old CP incumbent, preserved by `16f76334c`, labels its source `ac8e4c483`.
The original `qfd_c_b16_dv_fabric.sv` is byte-identical to that revision. However,
neither `qfd_c_land_safe.sv` nor the graph helper existed there. The current
audited safe source and helpers are hash-pinned separately in `contract.json`
at `c672ee40ff58ad02d870ee3a540a4dadd9be16f7`. The old source label alone cannot
reproduce a composed safe parent. No successor parent source has been selected.

The frozen die `dv2f18dh2` / `0d4c9808f` contains inter-macro CB16 buses. Its
264 CB16 links / 136,080 payload bits in `eb0ee1e0b` are a different graph from
the standalone parent's internal packed pin connectivity. There is no valid
one-to-one join by centroid, instance-level clock union, or a generic 516-bit
width. The A0 `e09907596` / `a5ff641cb` models likewise do not export a qualified
replacement A0 boundary. The 121 native-endpoint bindings (45,152 signal bits)
without A0/boundary pin ownership remain unqualified.

## Exact packed ABI and reach debt

| Item | Count |
|---|---:|
| Physical data children | 413 |
| Packed signal bindings | 735 |
| Ordinary data / bank data / written flags | 155,814 / 111,120 / 4,752 bits |
| Native geometry-known / unqualified bits | 226,534 / 45,152 |
| Known bits beyond 405 um | 68,542 |
| Same-region ordinary failures | 136 buses / 48,158 bits |
| Cross-region bank failures | 38 face buses / 19,548 bits |
| Cross-region written-flag failures | 19 buses / 836 bits |

The preserved CP graph has 519 expanded edges and 210 violating edges:
136 same-region, 19 cross-region, 55 unqualified; overrun is 61,344.631 um.
It collapses both bank faces and flags for each writer/reader pair. Thus its
19 cross-region failures correspond to 38 bank-face plus 19 flag buses, while
its 136 same-region failures remain 136 actual ordinary buses. Flag paths
are ordinary timing; no bank window or data MCP is granted. These distances
are Manhattan lower bounds; obstacle avoidance can only add obligations.

Each full 514/516-bit crossing uses two 257/258-bit siblings. The slot map is
`full[slot*W + part*H + j] -> half[slot*H + j]`, with slots 0/1 on `bank_w`
and 2/3 on `bank_e`. Each half carries **4H bank bits plus 44 written flags**;
the flags are not four global bits. All eleven slices have two source reset
captures, their own select/valid state, and a reader warm/age state. A writer
has 1,128/1,132 FF and a reader 346/347 FF at H=257/258. There are 84/24
writer halves and 84/24 reader halves, respectively. All 413 data children
cost 263,634 FF and 3.066139008 mm² outline in the historical inventory,
excluding A0, root clock/PG and the separate 2,502-FF reset MODEL.

The siblings carry parts of one coherent record and share the publication
epoch. Their data-level independence is **not proven**. A full D4 record is
2,056/2,064 state bits; passing a per-half 1,028/1,032-bit threshold does not
prove a whole-record storage exception. The actual source is D4/K2; it does
not inherit LAND600 D8/mod16/ICG proofs. Replacing it requires an explicit
storage/lifecycle architecture decision and new source/clock/reset pricing.

All data/flag final rectangles match the old endpoint snapshots. `ck`, `rsi`,
VDD and VSS rectangles differ or are newly present; the initial all-pin
equality assertion correctly failed on `ck`, then on VDD absent in the old
snapshot. These differences are recorded, not treated as timing or PG proof.
The four routed halves retain their TT/FF component timing CLOSED records,
but `0ea3` reports PG_HOLD with 116/122/44/44 unbound terminals. Source PG
repair belongs to the sole merger. Neither data rectangle equality nor old
timing automatically adopts a parent or establishes native pin fanout.

## Smallest next topology MODEL

`complete_record_lower_bounds.json` makes the forwarding alternative concrete
for every one of the 357 original complete ABI connections, joining both
siblings, both bank faces and all flags before computing `ceil(max_pin_reach /
405)`. There are 303 forward records (203×514, 84×516, 16×508 bits) and 54
coherent bank records. Of the forward records, 88 lack a complete endpoint;
their segment count is NULL. The remaining 215 include 117 violating complete
records requiring at least 156 intermediate captures and **80,306 full-word
state bits**. Their control fields, tag and go/valid bits already travel inside
the complete ABI word; they are never stripped for the price. At least 312
additional reset-capture FF would accompany those hypothetical stations.
Native clock ownership is unknown: this is same-logical-region forwarding,
not a proved same-root implementation or a priced half-cycle schedule.

The 54 complete banks include 15 violating whole-bank connections, requiring
at least 18 intermediate capture points and **38,624 bank-plus-flag state
bits**, plus a reset-capture floor of 36 FF. Each individual captured bank is
2,144/2,152 bits including all 88 flags, already over 2 kb: a full-word flop
forwarder is not an approved implementation. The record lists exact existing
landing costs separately: 4W ring data + W registered output + 88 written
flags + 176 select + 48 reset-capture + 22 warm + 44 age = **5W+378 FF**,
2,948/2,958 FF and four clock pins per complete writer/reader pair. These
are baseline source costs, not a free additional crossing or a new SRAM price.
The abstract epoch tags in the simulation helper are diagnostic monitors,
not existing hardware protection; new epoch/control hardware remains NULL.

All these figures are geometric lower bounds at the preserved positions,
without assumed interpolation sites. Every record has NULL legal site,
native phase/root, extra control/epoch state, clock buffers, physical area,
PG reservation, first use, and SU/MU delta. Obstacle detours, coherent capture
alignment and actual phase/reset choices can only add dependencies or cost.

1. Select and hash the composed parent source: original fabric, exact safe
   half modules, full record alias map, chosen A0 candidate and reset model.
   Resolve A0 bit/pin/publication/clock ownership for all 121 missing endpoint
   bindings before assigning landing roots or phases. Keep all eight A0
   transmit contexts and canonical feedback/first-use dependencies intact.
2. Partition the **136 same-region ordinary buses** into actual source-to-
   destination corridors using this bit map and native terminal geometry.
   Choose local region boundaries or forwarded capture stations per complete
   record. Merely landing the 19 inter-region pairs cannot fix those buses.
   The old distance-only intermediate counts (175 same, 22 cross, 95 unknown)
   are lower bounds, not selected stations, bit-stage prices or serial ages.
   Do not resume old CP searches or assume a smaller outline repairs them.
3. Model each selected complete-record station's real data/state and control,
   fanout copies, clock sinks, two reset face stages, reset assertion/release
   propagation, footprint, PG and first-use warm-up. For widths 514/516,
   one added capture alone costs 514/516 data FF plus explicit control/clock/
   reset costs; any deeper runtime-indexed storage needs whole-record SRAM
   treatment. A half-cycle forwarding station is not a free full-cycle hop.
4. For each bank and written-flag path, bind real writer clock-to-Q and reader
   setup/hold to the **actual native** root phase, reset epoch and overwrite
   lifetime. Model all four slot histories and both halves together. Supply
   compiler SU/MU deltas only after those absolute ages are known. Native
   all-role transparent fanout, PG repair and terminal-root ownership remain
   prerequisites; no blanket data exception, next GEN, gate or route follows
   from this packet.

The six superseded CP jobs and old CTS job remain stopped; all preserved
failure topologies and stop receipts in `16f76334c` remain authoritative.
