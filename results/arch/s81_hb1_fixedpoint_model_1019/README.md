# Production HB1 complete copy model and retained-source proposal

MODEL ONLY. Exact production `ceaed19c4`, XR SHA
`cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3`,
top `ot_s81sl_xr3`, HB1/W1104/V276, no FOREG. The completed unchanged-source
unplaced native census contains 64,383 cells, 18,352 FF, and 73 unsafe roots
(50 FF, 21 combinational, two ties). No HB0 receipt or count is transferred.

The full BUF/INV-transparent capacity construction adds **841 FF, 344
combinational gates, and 65 physical tie cells**, **355.72284 um²** total
(352.87974 functional + 2.84310 tie area). Added real CLK capacitance is
**389.321733 fF TT / 423.188548 fF FF**, excluding future CTS and wiring.
Iterations are 1161 → 1248 → 1250 → 1250 total added cells: first-pass cloning
misses 89 upstream cells. All 54,140 nonclock, nontransparent roots, including
safe originals whose inputs expand, are checked; 69,993 is the entire driver
record count, which also includes transparent chains and clock. Raw source
input demand remains at most nine logical pins. The construction assigns
41,023 expanded terminals with native inversion parity; every resulting source
copy drives at most 32 logical pins, including D, RESETN, SETN and functional
constant outputs. It copies 56 original FF and 38 original combinational
cells; 98 real combinational ancestors form the retained classifier cone.

`model.json` contains every changed original, incoming owner/polarity, terminal
capacity and FF family. `correspondence.json.gz` also contains every assigned
expanded terminal and the complete classifier cone. Names are exact native
ODB identities; mapped-source bracket normalization is a separate census
join, never an excuse to drop an owner. The source D and async pin identities
are distinct from a guessed signal name or QN polarity.

## Minimum private source mechanism proposed for ROOT grant

Create a distinct `ot_s81sl_xr3_hb1_retained_1019` namespace, private source and
private reset/wrapper files. Public production and frozen QF inputs remain
byte-identical. A default-off retained option selects the new component;
its zero/default branch must project to the exact anchor. It has the original
ports, full payload widths, original no-FOREG timing and no new data edges.
This is a concrete source proposal, not permission to synthesize or route it.

Retain all five independent **1024-bit** holding states and each leaf's
independent context/read cursor. They have overlapping lifetimes and OLD
final-pair reads concurrent with a new complete packet write. No aggregate
5120-bit single-read store, payload truncation, masking, arbitration or SRAM
partition is introduced. HB1's declared 1104-bit `bb` and 1104-bit `bo_r` are
real existing pipeline stages. Optimization of provably unused bits is the
anchor mapper's behavior; do not remove a live header or upper payload bit.

A generated endpoint ledger must drive the source transformation, not a
fixed-width rule assuming one load per data bit. The modeled useful copies are:

| Original decision/state | Added FF | Exact consumer obligation |
|---|---:|---|
| `rwe[0:4]` | 320 | Packet-word write selection and real unpacker context |
| `un[0:4][0:1]` | 240 | Existing OLD 256-bit pair selection and cursor feedback |
| `rwr[0:4]` | 60 | Existing CTL priority for each row-write data/address word |
| `lov[0:4]` | 40 | Actual input word-OR/select logic, no new valid stage |
| `ev_c[0:4]` | 30 | ENG captures, copy checking and dated fault logic |
| `el` / `pn` / `pi` | 22 / 18 / 10 | Original collector/send counters and their feedback |
| `pk_go` / `vct` | 10 / 9 | Existing CI/B selection, preserve V CTL priority |
| `pv` / `tg` / `ekd` / `erun` / `s_dir` | 10 / 4 / 3 / 2 / 1 | Actual norm/ENG/config and band-output decisions |
| Local reset relays / sync / second face | 59 / 1 / 2 | Same inherited reset edges, specified below |

All 344 added combinational gates are copies of the 38 exact originals in
`model.json`. Retain the actual E/W/V/B header source-priority, this-slice mask,
kind/leaf classifiers, packet-pair writes, CI/B output enables and counter
next-state cones. For each gate the full Boolean master identity, input pin,
input owner, polarity and sequential ancestor boundary is exported. The
additional B leaf classifiers are included rather than borrowing HB0's E/W
cone. Useful destination groups own their same-edge decisions; they do not
share one broad decode after synthesis.

Use kept scalar FF and kept, separate decision modules with explicit
`keep_hierarchy` boundaries and retained output nets. The existing keep-reg
canonicalization recipe remains unchanged. Merely emitting many equal-D
register declarations or retaining FF alone permits ABC/Yosys to recreate a
single high-fanout source. A successor must be audited from actual mapped
native terminals after synthesis; 841/344 are an exact graph construction,
not a guaranteed source-mapping area ceiling. Against native anchor area
9250.89336 um² the complete graph construction is 9606.61620 um² (+3.8453%).
Native anchor TT/FF FF-clock load is 8698.411086/9557.712796 fF; the constructed
loads are 9087.732819/9980.901344 fF before CTS. Master polarity, hierarchy,
buffering and legal physical distribution may cost more.

## Reset, cold first use and tied pins

There are 17/9/35/2 total retained local outputs for original regions
0/1/2/3, two total copies of second synchronizer state, and three total copies
of the second outer face landing. Keep the first face landing and first
synchronizer stage, their original D functions, async pin functions, and
all inherited ages. The exact native D/RESETN/SETN ledger includes QN and
inversion parity; a reset tree must not substitute a zero-delay raw reset or
add a release pipeline. The private outer wrapper owns the three parallel
second-stage face FFs, so generic automatic pin/reset wrapping must not
silently double-land the private component.

For ordinary resettable copies, equal initial reset state, identical D
functions and identical asynchronous events imply same-edge equality by
induction. All feedback references must use equal-state copies. This is a
source proof obligation, not executed RTL equivalence. Ordinary unreset face
FFs can differ at power-up; all three second face FFs only become equal after
sampling the first face stage. Actual cold/occupied-reset tests must therefore
cover assertions between edges, release offsets, source valid/payload activity
and earliest qualified first use, without a warmup mask. Retain all inherited
assertion and release events; digital same-edge equality does not establish
physical recovery/removal or metastability behavior.

The physical graph uses 64 total TIEHI and three total TIELO owners. The
anchor HI has 1178 SETN loads plus one real D load; LO has 36 reserved `bo`
bits, 28 reserved `ci_b` bits and one `x_si` bit. These are distinct roles. Assign
SETN/other native tied inputs to legal local real tie cells, and preserve the
functional constant output bits separately. No live output becomes an unused
pin, stub, waived constant, masked payload or fake logical port. Tie placement
and actual implementation ownership remain physical prerequisites; graph
capacity alone does not qualify them.

## Exact dates and qualification boundary

Input capture at K, classification at K+1, full packet/context write at K+2,
and first qualified unpacker read at K+3 remain unchanged. Existing outer
landing is a diagnostic hardening boundary, not two additional QF programme
edges. Preserve CTL override, OLD final-pair/new-packet coincidence, occupied
reset, all collector ordering, CI priority and exact sticky-fault dates.
No alternative current-control pipeline or isolated delayed valid is allowed.

Before a source grant, ROOT can review this complete modeled mechanism. A
subsequent minimum component would need actual full-width anchor/private
miter, default-source identity, cold/occupied reset plus the existing causal
HOPS/ROW/NOCOL/etc. negatives. Only then can a separately granted mapped
retention inventory demonstrate the source construction. Reach405, registered
boundaries, logic depth, legal outline/one 40–60% band, reset/clock region
placement, neighbor-matched TT/FF spread, electrical/PG/access and actual
single/multi-user token schedules all remain OPEN. An unplaced ODB establishes
none of those physical properties. No new simulation, mapping, OpenROAD,
floorplan, physical gate, helper, programme or production source was launched
or changed for this packet.

Reproduce the lightweight endpoint model with `python3 model.py <exact
native_census.json.gz>` from the companion diagnostic packet. The census hash
is pinned in both outputs. `witness.log` records the full construction and the
causal rejection of the incomplete one-pass estimate.
