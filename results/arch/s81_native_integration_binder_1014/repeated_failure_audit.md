# S81 gather and Q/operand corridor failure audit

This audit describes retained evidence and current candidates. It does not count
unrecorded attempts or promote diagnostic results into native qualification. The
die outline remains **33,000 × 26,000 µm**. No identical native207 full-planner
retry, period relaxation, uncertainty reduction, threshold waiver, or placeholder
daily contract is authorized by these results.

## Gather: proven safeguards and remaining physical failures

The current leaf outline is **190.08 × 164.16 µm**. The die-owned pin repair
`c837aa3c7` aligns each of the 828 forwarded output bits with its corresponding
input bit; the projected parent seam is 52.5 µm. Own counter/status/memory ports
remain distinct from the forwarded path. A small clock count therefore does not
establish data timing, macro clock slew, or a legal root clock spread.

| Candidate/evidence | Structural result | Actual physical result |
|---|---|---|
| SSA1 / gate `2a239`, retained history | Pin reassignment alone | RE D/Q 100.519 µm, 27 paths above 100; root maximum 328.3 ps/spread 96.5 ps. SS normalized zero-wire endpoint sums exceeded the 683.333 ps pair budget before wire. No route. |
| SSA2 source `bd086d432` | Real local EV/count logic; forward D/Q anchors prioritized over own-state placement | Fresh RE D/Q 98.137 µm, 0 above 100; clock maximum 293.6/spread 63.5 ps. SS internal −144.038 ps at the late valid/selection cone. RW initially failed DPL on actual overlap/offsite cells. A broader 61-row own-counter placement then passed native DPL/DPO without raising displacement limits; D/Q 99.911 µm. |
| Drive/consumed-copy source `44a0c986f`, proof `6adb1895b`, CTS archive `0c2cf23fb` | Existing 1,464 polarity INVs and 1,464 existing lead BUFs moved beside the real source FFs, tails retained; no new forwarding state or epoch. Four same-D/same-clock/same-reset SV copies drive actually consumed valid/operand/error/decoded choice. | Both DPLs pass. RW/RE actual clock sinks 13,077. D/Q 99.911/98.137 µm, zero above 100. FF internal hold +8.391/+5.947 ps. SS internal setup −124.952/−117.644 ps, now count cones rather than the repaired SV cone. RW maximum 294.490/spread 81.782 ps fails 80. RE maximum 297.3/spread 66.8 passes 300/80. |
| Per-bank count source `3566a4825`, frozen proof `65f7d4154`, CTS archive `fafd7d97b` | Existing count updates use their real per-bank current/use decisions at the same edge; no extra state or epoch. | D/Q remains 99.911/98.137 µm, zero above 100; actual SV copies still same D/clock/reset. FF hold +6.664/+2.945 ps. SS setup −111.179/−111.496 ps; worst now key update enables. RW clock maximum 292.1/spread 60.9 passes. RE maximum 302.290/spread 89.9 fails both limits. Actual post-CTS utilization including clock/hold/tap cells is 61.326/61.251%. No route. |
| Per-bank key source `ad50382d0`, freeze `e34622d7d` | Existing key updates move into the same consumed per-bank count decision, preserving data, edge, state, pins and epochs. Root274/full14/reset6/startup6 proofs are terminal PASS. | Distinct key+clockleaf jobs `dsfd_gth_rw_clockleaf-20261014-044915` and `dsfd_gth_re_clockleaf-20261014-044916`, sessions 7886/39540, are now terminal. RW has 13,077 sinks, TT maximum 298.9/spread 59.9 and macro clock flag false; its actual SS/FF/per-bit/DQ results are being collected. RE fails DPL-0033 before CTS, with 45 illegal cells/765 violations through native 2,000 iterations. Its hook never ran, so no new RE clock result exists. No route. |

The exact/source safeguards include a real 128-root/32-leaf production-size
bench, separate original references, tested input SHA snapshots, early/reset
and drained-restart cases, and functional mutants. The first select-phase mutant
did not fail an earlier prototype; that gate failure was retained. The final
consumed-copy revision made the phase observable: the root mutant produced
15,035 mismatch cycles and the full-size mutant 176 lost/mismatched rows. All
four SV copies were subsequently observed in the actual CTS netlist with
`D=dv[6]`, `CLK=ck`, `RESETN=rso`, matching the original SV.

These are stronger safeguards than an unused kept-copy declaration. They still
do not prove per-corner physical timing or an external producer phase. Each new
physical candidate needs its own exact frozen receipt; old insertion and old
corner reports cannot qualify a new source or hook. The full 46 effective remote
helpers were checked for the archived count candidate.

The latest completed SS key path explains why closure keeps failing despite
13,077 sinks: `s2_hit` passes through the global selected-valid/key reduction and
`dec_ins`, then a NAND2 drives 18–19 loads with 242–250 ps slew and 153–160 ps
cell delay, followed by a BUF6 and the key FF mux. Count factoring repaired the
previous count path and exposed the next global reduction. The current key-local
candidate addresses that real consumed cone, rather than changing a constraint
or adding a dummy register. Its fresh physical result remains pending.

The drive repair also materially reduced endpoint prices. For the completed
count candidate, normalized SS zero-wire sums are RW/RE **576.65/600.24 ps**
for E/W forwarding and **619.71/636.70 ps** for counter-chain transfers against
683.333 ps. FF minimum endpoint sums are 204.07/203.41 ps and 210.82/212.94 ps
respectively. These leave a wire/load budget; they are not a routed pair PASS.
Actual seam wires, loads, corner insertion, reset paths and phase/skew must
still be priced.

The clock failure has separate physical evidence. In the completed drive
candidate, an early SRAM clock at (130.476,79.836) saw 212.708 ps through six
BUFx24 stages, with the last net feeding four real macros. A late register
`g_r1.add_b25` at (13.651,73.035) saw 294.490 ps through seven stages and a
24-register leaf. In the completed count candidate, RE `p_t[2][1]` at
(177.379,82.485) is the latest register at 302.290 ps. Its leaf BUF311 is driven
by BUF6_58 across approximately 95 µm; adding delay to the early macro branch
cannot by itself remove this late-register maximum violation.

Source-owned per-macro clock hook `2208dd1cd` / diagnostic `09cd23897` uses eight
real BUFx24 cells, each original clock net → buffer A and buffer Y → dedicated
CLOCK net → exact SRAM/clk. Hook SHA is
`10d2ad58941b372ccc6952f14ebf74de6c6e3f352f16c3522f05d715c6c5654c`.
All eight inserted buffers passed native placement on the old drive ODB;
buffer-output-to-macro distances are at most 12.239/13.043 µm. The old-source
read-only clock diagnostic reduced loaded macro slew to TT 17.53/17.70,
SS 22.63/22.75 and FF 15.88/16.33 ps, below the unchanged 120 ps rule, and
spreads to 73.193/62.023 ps. This is a useful structural witness, **not a new
source gate or route qualification**. The distinct live kits preserve deployed
helpers, add only their source-owned hook, and retain 833.333 ps, setup 60,
hold 25, maximum 300, spread 80 and macro slew 120. No shared helper was edited.

The decisive next evidence is the source-matched RW key-local plus clockleaf collection and the exact RE illegal-row/site/occupancy classification. The RE placement failure must be resolved before a new clock claim. Required evidence includes:
all-corner internal setup/hold, actual per-bit first/last endpoint prices,
loaded macro slew, actual root paths, reset timing and D/Q. A late RE root or
remaining SS key/control cone must be repaired structurally if it persists.
Warning-only gate labels do not override these failed native requirements.

## Q and operand corridors: actual topology and fixed-outline evidence

Retained native207 is a **terminal geometry screen**, not an adopted native
assembly: 59,546 instances/226,746 hops; zero outline overlap/outside/pin-clash
does not compensate for the following bit-pair failures:

| Failure family | Failed bits | Maximum / required reach (µm) |
|---|---:|---:|
| A relay → bank | 144,896 | 985.8 / 406.5 |
| B relay → bank | 102,144 | 1,243.8 / 407.2 |
| B relay → Q/BF slot endpoint | 102,144 | 989.1 / 500 |
| A relay → Q/BF slot endpoint | 36,224 | 854 / 500 |

The retained `t#` endpoints include BF/slot placeholders; they must not all be
described as native Q leaves. Overall native207 has **1,729,687 unbound data
bits**, 519 pin-alignment FAILs and two missing controller `st` endpoints. The
old source overlay excludes current native Q/PQ/VM/gather integration. Missing
canonical native field source, instruction/field schedule, actual producers,
clock/reset wiring, and actual successor views remain explicit obligations.

Generator `38811afe8` fixed a concrete search defect: a trial chain did not
reserve earlier stations, so a later trial could reuse their space and look
clean before real construction fell back. Temporary occupancy now reserves
each station and rolls back exactly, including exceptions; two meaningful
regressions pass. `0cf054949` adds opt-in `--operand-path-pick` for both A/B/control
L directions with real trial occupancy and unchanged register count. It records
selected direction and non-first search tiers. This is a search repair, not a
claim that centroid placement satisfies every actual bit.

`dc2847ae1` adds an independent retained-frame0 endpoint screen using final LEF
rectangles, source/load bit identity and recorded pair limits. It checks 41
operand relays, **23,856 unique bound bit pairs and zero missing pins**. Before:
4,791 pair violations. Simultaneous requests from independent per-relay optima:
1,525 pair violations, maximum 552.262 µm; 37/41 requests overlap retained cells.
Fallback classes explicitly use only the flat ceiling and remain unqualified
until the full pair table is applied. No alignment, cuts or placement PASS is
inferred from this necessary-condition screen.

For `g_xb_0_4_bs4_0` and `g_xb_0_9_bs12_0`, no translation of the current R0
master meets both frozen endpoints: the best remaining excess is +9.688 µm
even before obstacles. Reflections improve the endpoint arithmetic, but every
tested feasible origin on the current candidate 0.432/0.576 µm relay lattice
is occupied: MY 65,813 each; MX 6,963/6,964; R180 96,154 each. Global pin access
and reflected track-phase admission remain open. This is direct evidence for
replanning the corridor/nearby Q packing; adding a register or moving a relay
without releasing a real site is not a completed repair.

Old retained QS5f has actual SS internal −187.246 ps at 833.333/60 and a
53,105-sink clock root with approximately R506/spread96. QS6 source `11ab82556`
retained actual setup −66.787 ps under its diagnostic 163/25 context and 4,260
setup violations. These failures were preserved; neither was relabeled as
native repair.

Actual production Q source `6ed42d12c` was extracted from its compiler graph:
control 8,186 FFs, two TW17 lanes 13,149 each and two return groups 9,912 each
with two actual ROMs each. The reconstructed partition totals 54,308 mapped FFs;
the eight-count difference from the unpartitioned 54,300 comes from preserved
partition boundaries, not new operation epochs. The four real ROMs are
125.28 × 62.91 µm. Clock entry pins are source identities, not proof of seven
independent clock origins: the old source shares raw and generated clocks.
`6c3bc641d` explicitly exports a source-produced generated clock as a clock
output port instead of leaving it disguised inside a functional data vector.

The initial five opaque boxes, 552.384 × 285.12 µm, fit only eight field slots
where the actual 1,792-pair/128-root/four-BF allocation needs nine. No requirement
was reduced to fit that result. The fixed-outline request `6b94ea842` instead
co-locates the real return groups in a 328.32 × 233.28 four-ROM container and the
real control plus kept lanes in a 164.16 × 198.72 container, with 20.16 µm between
them: total **512.64 × 233.28 µm**. Using existing mapped receipts, nominal
standard-plus-macro/core utilization is 56.31% for return and 56.62% for data;
real 20 µm macro guards are retained. Reducing the cfg-to-element offset from
77.76 to 71.28 leaves 4.008 µm after the actual 62.952 µm cfg ROM. The current
generator geometry gives nine slots/frame height 2,676.24 µm and 33.216 µm
horizontal slack at the unchanged die outline. This is an **unassigned
co-location/corridor request**; pins, access, source-preserving clock delivery,
utilization after real buffering, and cuts still require actual qualification.

Clock clone source `7602aac02` adds a default-off genuine per-group gate mode
with used enable copies and zero operation epochs. Unlike historical simulation
clock aliases, the candidate simulates the real latch-based gate behavior. Exact
PQ0 evidence `dfff64206` has ten positive runs and an actual half0 inverted-gate
mutant failure. Production PQ1 numerical proof, startup gate keepalive, mapped
per-clock sink counts and physical clocks remain separate requirements.

Production-PQ1 compiler graph plus exact container extractor `cd377489a`
completed unit `2311452`: every original cell/connection and memory is
reconstructed, both source containers are generated, and Yosys `CHECK` returns
zero problems. This proves source-graph preservation and produces a concrete
compiled candidate; it does not prove physical first/last-register boundaries,
clock insertion, route or native release. The old core can also stop its gated
clock before a gated consumer samples reset release. A genuine ACK-dependent
startup controller therefore needs explicit gate keepalive/consumer epoch
proof; no fixed counter or old readiness flag can stand in for that handshake.

The distinct controller-shell source `68f53c142` now exports its actual final
local release after wrapper two-FF and child two-FF conditioning, with historical
controller masters unchanged. Unit `2264206` passes the first real program word,
real SOURCE pending/admission path, six stopped-clock raw reset epochs, and
rejects a forged-ready mutant. Its source packet still has null physical outline,
pin assignment, global producer phase and recovery/removal qualification.

The decisive Q/corridor work is now the real source-preserving container map,
actual source/receiver pin assignment, occupied-corridor retile and complete
four-family per-bit reach/alignment/cut screen at the current die outline.
Registered-stage cost must be explicit if zero-epoch topology cannot close.
Missing native bindings, new reset ACK views and physical clock producers must
remain visible rather than being replaced by legacy LEF coordinates or labels.
