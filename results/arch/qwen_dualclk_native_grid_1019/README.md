# Native-phase access variant: MODEL ONLY, HOLD

This bounded variant retains the exact `693ac5af4` core translation, all 206
original 24×24 nm contact rectangles and all 44 PG rectangles. Original
geometry and the `7814bb23a` terminal review remain immutable. No macro
view, RTL, Liberty, gate, native DRC job or physical route is generated.

The long M4 wires move −9 nm to y≡3 (mod 48 nm); M5 columns and VIA45
centers move −12 nm in x to x≡0. Both ends of each vertical column move
−9 nm in y. The original source pad remains at its exact coordinate: the
shifted horizontal lead overlaps it across 24×15 nm. The model explicitly
includes the unchanged pad and its 216 nm² local tail beyond the lead.
Rectangle-union area counts overlap once. This establishes an abstract
electrical connection without moving or renaming a contact.

| Bounded result | Variant |
|---|---:|
| Connected original-contact to terminal paths | 206 |
| Native-phase long lead rectangles / VIA45 instances | 614 / 408 |
| Contained and protected via metal enclosures | 816 |
| Unchanged original contact / PG rectangles | 206 / 44 |
| Minimum cross-net M4 / M5 / cut axis gap | 50 / 72 / 72 nm |
| Source-pin/OBS terminal protection and approaches | 206 PASS |
| Causal contact/grid/blocked-terminal mutants | 4 FAIL |
| Outline / 26-bank macro area | 52.440×21.144 µm / 28,828.575 µm² |

The scalar evaluation checks actual rectangle widths, connected-patch
minimum area, thin-wire PRL spacing (the 48 nm scalar clearance exceeds
the 24 nm thin-wire table), wide-PG 72 nm clearance, cut spacing,
enclosure containment, original OBS and proposed terminal protection.
The retained 24×24 nm pad is smaller than minimum area in isolation;
its connected union with the source lead exceeds the 2,000 nm² rule.
That is why minimum area is evaluated on connected same-layer patches.

**The local join remains native DRC HOLD.** Its union is 33 nm tall with
a 9 nm step/notch. The supplied M4/M5 blocks contain no explicit MINSTEP,
but do contain RECTONLY, discrete WIDTHTABLE, EOL and corner rules.
Absence of a MINSTEP statement does not prove acceptance. A conservative
33 nm bounding-width interpretation could demand 72 nm PRL clearance
where a local pad-to-neighbor gap is 63 nm; applicability to the actual
short union requires native rule interpretation. Neither a fabricated
failure nor a native PASS is claimed from that bound. Original retained
contacts remain on their original phase and are explicitly distinguished
from the new long conductors.

The technology snapshot supplies M4 pitch/offset 48/3 nm and M5 48/0 nm,
with RIGHTWAYONGRIDONLY. These are nominal parent-track facts, not proof
that every original internal macro rectangle must obey an R0 track test.
No native interpreter receipt establishes that applicability. The original
614 nominal phase discrepancies therefore remain an analytical HOLD,
not routed DRC failures. The variant's explicit scenario is master R0 at
origin (0,0), with bank origins advancing (86,400,43,200) nm, both divisible
by 48. Its 52,440×21,144 nm dimensions are 24 mod 48: mirroring x changes
the M5 phase to 24 nm; mirroring y changes M4 phase to 21 nm. Parent TRACKS,
orientation, placement transform and real access points remain unbound.

| Passive access cost | FF | TT | SS sensitivity |
|---|---:|---:|---:|
| Maximum clock lead upper envelope, ps | 3.777 | 4.077 | 4.875 |
| Maximum input lead upper envelope, ps | 3.832 | 4.767 | 6.493 |
| Maximum output lead at 46.08 fF, ps | 18.546 | 19.371 | 20.866 |
| All 52 clock input caps, fF | 635.418 | 581.994 | 547.568 |
| All-bank full-activity R+W energy, pJ | 13.837 | 11.456 | 9.301 |

Compared with original TT 581.910 fF and 11.452 pJ, the explicit variant
is 581.993659 fF and 11.456485 pJ. Exact unrounded original and variant
costs are in `comparison.json`. Outline, macro count, 52 clock contacts,
408 access vias per macro and the 259.2×388.8 µm placement reservation
remain unchanged. The soft band, real PG straps, parent escapes, tie/reset
copies and native extraction remain unpriced. Full activity charges every
nonclock lead one complete 0→1→0 event plus both clock leads and original
core R+W energy, as in the original model.

RC uses exact metal-union area divided by 24 nm as a conservative passive
length surrogate; VIA45 resistance and native enclosure dimensions come
from the unchanged source deck/platform snapshots. This is not extracted
RC of the local junction. Via-cut fringe capacitance and coupling are
unavailable. Macro internals remain conditional on the original analytical
source; no GDS/CDL is invented, and no minimum CQ or silicon timing is
asserted. Zero added pipeline edges is a proposal, not a qualified native
clock/first-use/reset/K or token-latency result.

All 44 PG rectangles also have explicit hypothetical nominal-grid VIA45
enclosures contained inside their exact M4 pin and 24×84 nm M5 landing
patches clear of M5 OBS. These are *unbuilt, unpriced witnesses*. The
supplied technology does not establish a same-net PG-pin exception through
the overlapping M4 macro OBS. Actual accessibility, domain ownership,
straps, all native MTerm→ITerm binding and connectivity remain PG HOLD.
No blanket OBS waiver is used.

Reproduce bounded arithmetic with `python3
results/arch/qwen_dualclk_native_grid_1019/model.py`. `source/` preserves
the exact original model/input, native deck/platform and SC2 terminal
checker, with SHA-256 identities in `comparison.json`. Two initial script
bookkeeping failures (missing inherited proof key, uppercase corner key)
are retained in `initial_failure.log` and `second_failure.log`; neither is
physical evidence. The successful bounded run is in `model.log`.

ROOT must review the priced variant and unresolved local native join,
track-transform and PG-access mechanism before any generation. This packet
does not authorize views, RTL, gate, reroute, binding or adoption.
