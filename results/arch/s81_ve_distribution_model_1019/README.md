# VE useful-copy/reset distribution model

**MODEL, source choice held.** Exact source `78ad1399f`, saved GRT ODB `c795bfb691f2f0769f0ea13a2c26cdbc067f18d5532553709e7b319f1e0bdb79`, prior pickup `43c858814`. No RTL, synthesis, route, REVIEW, gate or timing constraint changed. The current terminal WARN and earlier failed route remain historical evidence, not qualification.

The candidate retains the golden streaming arithmetic and existing **129-edge reduce / 44-edge add** calendars. Copies capture the same-age useful state, feed local original compute/decode groups, and add no arithmetic operator or new data stage. All 36 real independent OLD rings remain; their largest coherent indexed store is 832 bits. No >2kb storage is divided to evade SRAM policy. Static issue and no backpressure remain requirements.

## Complete load recurrence and exact cell costs

`model.py` starts from the retained uncapped native endpoint graph, transparently crosses BUF/INV and the sole CKINV, and counts every destination copy's input PIN. It increases each original cell's retained copy count until **all** nonclock output roots can partition those expanded pin loads into groups of at most 32. This includes new D, enable, reset, combinational upstream and local tie loads, rather than pricing only the initial unsafe roots. All source/input roots are included; their maximum remains one. Clocks are priced separately.

| Quantity | Fixed-point candidate |
| --- | ---: |
| Added FF | 1,716 |
| Added combinational cells | 856 |
| Added local TIEHI cells | 2 |
| Additional nonclock input-pin loads | 4,133 |
| Native-cell area | 604.31184 um² |
| Additional clock pins | 1,716 |
| Added TT / FF clock input capacitance | 813.174244 / 893.385668 fF |

These are exact selected-native-master scalar costs from the real RVT TT/FF SEQ/SIMPLE/AO/OA/INVBUF libraries, with compressed-file hashes and all affected master coefficients in `price.json`. The recurrence converged after 1,258 count updates. The earlier 1,685FF/837comb floor leaves **46** roots over capacity when its own upstream loads are included; `ownership.json` retains causal failure examples. Every original source/control/address FF instance and anonymous mapped comb root needing copies is listed in `fixed_point.json`. Mapped combinational names have **not** been asserted to be a proved RTL source correspondence.

**Not included or bounded by these cell figures:** new CTS buffers and routing, detours/vias/hold repair, real PG connectivity, source attribute survival and cell legalization. They must be measured after an exact source/native ownership proof. The copy count is an analytical connectivity construction, not an actual new netlist native PASS.

## Reset, cold pointers and literal output pins

The recurrence contains 80 added FF identified as existing reset-leaf/landing-stage copies (126 total added native DFFASRHQN cells). Each reset copy must retain its original stage's **same D, same asynchronous clear source, assertion and release age**. Replacing this with an appended `ot_rst_relay` tree would add release edges and is excluded. The existing face landing remains two registered stages. The largest final reset stage changes from 2,320 original loads to 2,370 expanded loads, requiring 75 total same-age copies. The four surviving native reset-state owners and every D/RESETN/SETN source are listed in `authoritative.json`: face rl0←rst_n (one), rl1←rl0 (three total copies), shared leaf sync0←TIEHI with clear←rl1 (three), and leaf sync1←sync0 with clear←rl1 (75). Source reset synchronizer stages were merged in the current native graph; source implementation must explicitly preserve their inherited identities and mapping.

Unreset pointer copies cannot be blindly assigned independent feedback. `cold_copy.py` enumerates **12,584** arbitrary initial write/read pointer-code pairs over every row count 1..26, with **285,300** required OLD outputs checked. Feeding every copy the **same next-state function of one canonical pointer vector** aligns all copies after edge 1; the first required input is written at edge 2 and read at unchanged edge D=N+2. No initialization, new reset, or free edge is assumed. The independently advancing feedback mutant fails at N=2, edge4: expected input1, received input2. The exact native owner ledger in `authoritative.json` names all113 original pointer bits/36 rings, their718 added pointer FF, and278 canonical next-state combinational cells. Reserving one authoritative next-state cone and all pointer-copy D loads uses at most31 loads on any root; the remaining address/decode loads fit the converged partition capacity. Each ring has one canonical vector and explicit per-bit D source; the two address sides must derive from it after the first edge. This is an abstract coherent load allocation, not merely identical counter equations. Source mapping must retain the common next-state function and coherent read/write ownership; the actual production valid/bubble/occupied-reset comparator is still required.

The 130 literal native output pins are enumerated exactly in `ownership.json`: eight BF16 result words' 16 low bits, plus `p_hh[31]` and `p_kk[31]`. Low bits are explicit source zeros. Square operands have sign a31 XOR a31=0; nonfinite/overflow refusal encodes zero, and nonnegative reductions preserve sign. A selected-source proof for the actual f12 arithmetic/refusal chain remains required for the two sum sign bits; they are not masked or waived.

To satisfy physical registered pins, a bounded **retained constant pin-register variant** prices another 130 DFFHQNx1 FF (existing local ties feed D; Q feeds only the actual port). It requires synthesis retention and constant semantic proof. This price is for **unreset** DFFHQNx1 only. Zero capture by the first edge must be proved to precede every observable use under the actual valid/reset contract; pre-first-edge behavior differs from an ideal literal tie. First-observable initialization and occupied restart remain unqualified. Adding reset would require different FF coefficients and a new reset-load fixed point, and is not included. No valid/data calendar delay is proposed, and no all-pins contract PASS follows. Total candidate increment becomes **1,846FF, 856comb, two ties, 642.21984um², TT874.889924fF / FF961.246968fF clock**. This variant has not been implemented or granted.

## Region and wiring construction

An analytical 8×6 lattice outline is **345.6×259.2um**, one full-width standard-cell band, aspect 4:3, zero macros. Historical CTS area40,683um² plus all candidate cells is 41,325.21984um²: **46.132%** of its89,579.52um² outline before additional CTS/route/PG costs. This is a capacity estimate, not an instruction to shrink the old gate or a finite-cell floorplan.

`geometry.py` constructs a point embedding of every native pin: retain x, scale y by0.75, and center the sole long-reach reset stage and all its copy input terminals. All copies otherwise share their original zero-area point. It accounts for all555,508 expanded sink pin terms, with no abstract direct pair over405um and maximum292.448125um; summed pin-to-pin Manhattan lengths total3,883,381.3095um. This shows a zero-added-edge geometric candidate exists in a smaller rectangle. **Co-located zero-area points are not legal cells, Manhattan distance is not routed length, and this is not a measured reach or timing PASS.** The full real placement must reserve copy footprints and wire/clock/PG space, rerun uncapped native reach and retain the same source ownership.

A center-fed root beside actual FF mass is the candidate clock topology (outline below1mm); old TT/FF spread30.5/30.9ps is not transferred. Any eventual regional-clock or capture seam must state its exact forwarding/landing age and update both129/44 calendars and the actual parent/compiler. New arbitrary pipeline stages are not included.

## Next source mechanism and admission boundary

LEAD-S81/ROOT choose the following **bounded source-only mechanism** after reviewing this model: private retained same-age copies per actual state/decode ownership group; common canonical next-state pointer copies; same-age reset stage copies; retained130 constant output-pin FF if their exact semantic proof passes. Preserve every numerical operation, reduction order, input/output tag and dated fault. Do not replicate full arithmetic, add delay shifts, alter reset age, or open a physical gate from the count or geometry witness.

Before source is called complete: map all856 anonymous copied comb cells to an exact selected-source cone or use a rigorously equivalent explicit local Boolean cone; prove every original and copied canonical D/control/reset function and first-use dependency; compare actual production valid/data/tag/fault/occupied-reset traces, including all cold pointer codes and causal read/write/missing-reset/output-sign mutants. Then measure retention, all native roots including input/reset/ties, clock/PG, legal one-band placement and actual wire≤405; require TT setup/FF hold, TT/FF spread≤80 and native-neighbor matching, io_hold_margin≥0.03. Final route and production throughput are open. No complete safe-source or parent adoption claim follows from this bounded model.
