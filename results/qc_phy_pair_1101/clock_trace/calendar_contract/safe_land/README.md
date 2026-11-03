# Existing SAFE/LAND_CORE does not bridge the unequal clock rates

The exact frozen native source from the parent packet was inspected for both
`ot_coll_lcal_tx` and `ot_coll_lcal_rx`. SAFE1 selects SAFE_RING1/LAND_CORE1 in
the face. Both calendar crossings instantiate the same `ot_coll_token_landing`:
TX carries `slot`, RX carries `exp`. The ring writes every core edge, advances
both pointers independently, and reads `(rp-2) mod4` every FDI edge. It has no
request hold, acknowledgment, event toggle, occupancy check, or rate correction.
SAFE_RING changes long **single-clock** delay implementations and does not add
any of those crossing mechanisms.

Under core833ps/FDI1000ps, a writer word survives four core edges =3332ps, while
the reader revisits that physical slot every four FDI edges =4000ps. A sparse
one-edge event can therefore be overwritten before that slot is read. A fixed
initial PLL phase cannot remove unequal-rate pointer drift indefinitely.
The original related/mesochronous contract must not be extended to arbitrary
833/1000 event sampling simply by selecting SAFE1.

The actual branch was compiled without modifying its source. The existing
`OT_COLL_MUT_LAND_UNLANDED` control bypasses the ring in a separate build.
Intel1 job `oth-ubuntu-1329617-1793626076`,1GB/1thread, completed the bounded
diagnostic. No Intel2 or full-QC job was run.

| Case | Actual result |
|---|---|
| Native SAFE1/LAND1, isolated source edge100 | PASS: one event, first FDI r_slot at86500ps |
| Native SAFE1/LAND1, isolated source edge115 | **FAIL retained**: source1, received0 |
| Reset at84800ps, after ring write/before read, then restart | PASS: pending event canceled, no ghost token |
| Existing unlanded mutant at edge100 | REJECT: first r_slot84500ps differs from native86500ps |

The positive source launch is83716ps, so measured launch-to-r_slot is2784ps:
`2784/1000` FDI periods and `2784/833` core periods. It is not an integer
source-clock edge count or an adopted calendar delay. For a source launch n,
the ring captures it on writer edge n+1. If an address-matching FDI read m
occurs before the next write to that slot, r_slot appears at FDI edge
`m+(KC-3)`. If no such read occurs, the event is lost. At KC4 the delivered
latency lies between approximately1833ps and5165ps before physical apertures,
or it is missing; there is no phase-independent fixed latency to price.

The branch's fixed tails can still be stated exactly, conditional on an event
surviving the crossing:

- TX landing tail: KC−3 =1 FDI edge; r_slot→wr_v =4 more FDI edges;
  wr_v→rd_v =KW=2 more FDI edges.
- RX landing tails for the actual three calls are380/354/378 FDI edges from
  the landing output; the following write tail is2 FDI edges (WX0).
- RX core read tails are L−4−2R =390/386/386 **core** edges.

One FDI edge is1000ps and one core edge833ps in this proposed source condition.
Convert any fixed tail by its own clock unit; do not replace FDI edges with
core edges or adopt the selected L436 as proof of the composed path.

No existing safe source selector can be emitted from these branches for
phase-independent transfer. Without a qualified phase-constrained compiler
schedule, the missing hardware is a retained event/request plus an explicit
completion/acknowledgment or equivalent rate/spacing protocol. A stretched
level alone would also need a receiver one-shot and a proved spacing/hold
contract to avoid duplicate or merged events. Any such bridge adds state and
potentially variable clock-domain edges; it needs its own RTL proof and model
price. The existing data CDC SRAM and publication-fault checks do not recreate
a lost calendar event. No RTL selector, public clock, native CDC, programme,
calendar, physical qualification or rate claim was changed by this inspection.
