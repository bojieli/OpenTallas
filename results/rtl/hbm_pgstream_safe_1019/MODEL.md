# PGSTREAM structural successor model (before implementation)

Source baseline: `53cbcc9a8`, QID1/G2, STRAP1, FAULT_REG1, read18/write15;
legacy10/7 and QID0 remain separate functional regressions. Frozen ROOT gate
95463 is not modified. This is a default-off source experiment, not a new gate.

Actual baseline synthesis has 7,650 FF, 22,731 cells, 3,444 um2 standard area;
18,797 complete non-clock/nonconstant roots include **25 above32**. The committed
`baseline_census.json` counts through BUF/INV, including reset and combinational
drivers. Worst cnt[0] is1707, stream mux600, tap.write_d565, stream return513,
bridge reset148, tap reset92 and leaf reset73. The old README fanout PASS does not
apply to actual synthesis. Boundary pos-to-inject-bank has10 logic levels.

## Static throughput and unchanged seam

Each of two bridges carries serial request17+281=298 bits/event and return257
bits/event. Serial request banks and stream return banks are two entries each.
Serial/stream clocks are4q/3q with q277.778ps. Three serial events map to four
stream edges; idle slot is fixed, no credits, stalls or arbitration. Request
bank n is written4n and read4n+6/5/4; unchanged required setup>=4q/hold>=2q.
Return stage uses SRD=ceil((3R+18)/4), STR=floor((4SRD-3(R+2)-8)/4).
R18 gives SRD18/STR1; W15 gives SWD16/STW1. Return read window remains2q/4q;
done3q/3q. Copies may change neither these windows nor fault/reset edges.
Boundary totals3577 bits and internal seam2346 bits do not change for a
same-edge copy repair. No added memory traffic, MACs or communication bandwidth.

## First bounded source step: bridge only

Split request and return datapaths into **15-bit physical control regions**,
each with its own genuinely retained local counter/phase/warm/active state.
Do not distribute one counter through kept buffer or combinational copies.
Hierarchical regional modules are retained through synthesis, then flattened
for the independent all-driver census. Their counters are exact copies of
baseline state on the same clock/reset edges. Region width15 budgets two
select/enable loads per data bit plus recurrence<=32; mapping must confirm it.

Serial request20 regions each keep one parity FF. Return18 regions each keep
parity plus5 warm FF (18/15); original effective parity+warm6. Serial-side
control growth is20+18*6-6=122 FF/bridge,244 total. Stream request20 regions
each retain phase4+warm5=9 FF; growth171/bridge,342 total. Return18 regions
need phase4+warm5+active20=29 FF each; naïve growth can exceed500/bridge.
Use exact local bank-enable history with independent phase/warm only after
equivalence proof. These are area upper estimates, not measured resource
admission; final census must report actual FF/cells and clock sinks. No clock
gate, physical buffer or threshold exception substitutes for source copies.

The implementation may initially leave tap/reset/inject inherited roots above32.
Such a result is explicitly **FAIL/no gate**, while establishing bridge proof.
Existing reset source names/ownership and stream-local fault reset are retained.
Additional independently reset state increases reset load: no reset PASS claim
until a balanced same-depth source partition is mapped and proven.

## Remaining whole-field choices, not silently implemented

* Tap read/write selects require useful kept per-payload-region samples at the
  existing pin capture edge. The payload mux then uses its local select copy.
* Three-bank inject serial select41 bits needs three local counters/14bit pieces.
  Dynamic inject and pos pins currently decode straight into bank FF. Registering
  these pins adds one stream capture edge unless a separately proven retiming
  changes the bank calendar. That added edge, downstream bank parity, setup/hold
  and compiler inject age must be priced jointly before source adoption.
* Boundary reset landing is3 serial edges, followed by inherited leaf/tap chains.
  Preserve all inherited release ages. New replicated terminal stages must have
  identical depth and exact source/clock ownership; no reset mask/guard shortcut.
* Runtime storage: bridge banks per bridge are596 request bits and514 return
  bits, each below2kb. Return staging STR1 is257 bits, not a>=3 deep delay.
  Active/read/write bit histories<=20 entries are control calendars; audit the
  storage rule explicitly rather than claiming every history is SRAM already.
* Tile216x259.2 has total Manhattan diameter475.2>405; actual connectivity/reach
  needs measured placement or a bounded region model. Prior estimated105um is
  not universal pairwise proof. Synthesis area must reprice the pin-bound
  low-util exception and clock mass. No CTS/route before ROOT checklist review.

## Required proof/admission

Fleet Verilator5.050 bridge lockstep at18/15 and10/7, exact cycle words and
reset phase sweeps, plus effective wrong-bank/wrong-age/early-read mutants.
Actual mapped TT-library all-driver census must include ports, every FF,
combinational driver and reset with BUF/INV transparency, not top8. Then full
parent source correspondence, boundary registration, actual reset fanout/depth,
SRAM inventory, sizing/43.2 lattice/channel/pin/reach model and ROOT PNG review.
TTsetup>=0/FFhold>=0, native TT+FF spread<=80 and neighbor compensation remain
physical requirements. This source step cannot qualify a token or release die.

## Native-map refinement (before revision3 source)

Revision2 actual parent passes7194 checks/9228 seam windows at18/15; native
mapping reports8664 FF. It correctly keeps regional state but request-bank
hold muxes use **four**, not two, control loads per payload bit (two banks,
complementary select implementation). The15bit request regions therefore
measure61 loads, not the analytical31. Preserve this failed source/census.
Revision3 reduces only serial request regions to7bits:43 regions per bridge,
predicted4*7+1=29loads and46 additional parity FF across both bridges. Return
and stream regions remain15bits. This is a source control partition, no added
edge/clock change. Reset port1680 is deliberately still unsafe in this
unwrapped source map. Inherited tap564/reset92/73 and inject83/82/81 roots
remain open; revision3 is not a whole-tile SAFE claim.
