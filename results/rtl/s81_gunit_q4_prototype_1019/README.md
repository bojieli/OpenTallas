# Paid Q4 source component — PASS, storage blocked

The opt-in `Q4=1` quotient captures exact remainder correction and signed-11-bit
range predicates at a new boundary. The same baseline arithmetic and packing
remain; recurrence D0/DS become18/16 and ITERS20 LAT becomes642 rather than602.
L5's new `OT_S81_GUNIT_Q4` flag defaults0; it passes Q4 through the tail, whose
SLAT/CAP/L expressions all move together. This wiring and calendar source have
not been built as a complete GUNIT. Default branch quotient final arithmetic is
byte-identical, and the entire original base/scales table read/write/select
region is byte-identical to12ab196b6 (`source_scope.json`).

Actual Verilator5.050 fleet component result: **201 jobs PASS**,129 normal and72
fault, baseline602/candidate642 edges from the same accept, eight abort/reset/
recovery phases, invalid pulses and changing input while busy, and stopped-clock
assertion. Old602/early641/late643 calendar expectations all FAIL. An actual Q4
low-range-predicate corruption FAILS the numerical/fault comparison in case0.
All seven consumed RTL/bench hashes match the checked-in source. The component
compares new Q4 to default-off pipelined Sinkhorn; it does not exercise GUNIT's
base table or the complete HC producer. It reuses the model's458,752-case exact
integer algebra proof instead of claiming it as a new RTL result.

The useful-copy **supported source subset** is the Q4 predicate boundary:
pack3 and range6 are distinct fixed kept modules, both clocked on the original
clock with no enable/reset added. Pack consumes correction/zero; range consumes
its own correction/zero plus high/low predicates. This declares144 useful FF:
96 logical +48 duplicate, within the192-FF reserve. No unused high/low copies or
artificial consumers are manufactured. Each original correction/zero predicate
feeds two real FF D pins; each high/low predicate feeds one. This is source
correspondence, not a mapped survival or timing claim.

**Zero of the original1,874 mapped >32 findings is certified closed.** The
complete fixed-point model is inherited at
`../s81_gunit_controls_1019/whole_model.json`, with the complete original census
in `mapped/fanout_uncapped.json`; neither was truncated. Exact remaining model
families/counts are recorded in `source_scope.json`. The model names post-ABC
native roots, not sufficient handwritten RTL consumer equations. Completing all
3,133 proposed useful FF and Boolean copies requires per-root real producer and
consumer correspondence, retained opposite polarity, every D/enable/reset input
recursively charged, complete remapping, original consumer retention, actual
load census and area/clock capacitance. The Q4 subset is not that construction.

The3,072-bit `base_t` remains the original flop table and **STORAGE IS BLOCKED**.
No SRAM drop-in was implemented. Actual four-word ownership/lifetime, config
settle, same-address read/write, reset/abort/restart and old-read behavior must
be established by the producer and compared with a real prefetch/cache and the
12-native-bank alternative. No unspecified collision or initialization is used.

The separate reset contract source is **not connected to GUNIT**. Its digital
bench covers six positive pulses (0.02/0.1/0.25ns running and stopped), three
clock-stopped cases and one coincident assert/release case. Stable noncoincident
release stays three edges; coincident ordering has only bounded recovery proof.
Raw asynchronous contacts are2, sync0 one D+12 async pins=13, sync1 twelve D.
Assertion now traverses raw->sync0 async-clear/Q->regional async-clear/Q; this
adds a real propagation arc. Zero-delay simulation proves no physical minimum
pulse, recovery/removal, assertion propagation, metastability or electrical
equality. Those bounds and parent first-valid guard remain priced obligations.

The explicit candidate downstream calendar is lastHP_N1015N/1013S (+40),40
additional edges per HC job,80 for two serialized HC jobs. At0.77ns this is
30.8ns/job; at1.2GHz33.333ns/job. Compiler reservations, every CTL row, END and
token costs must move together in a source-qualified candidate; this packet
changes no release compiler constant and admits no calendar. Actual full HC
numerical, HOP1015/1013 and old/+1 causal age witnesses are still required.

SAFE checklist for this bounded source packet: pins OPEN actual GUNIT/native;
reach OPEN exact parent/regions; fanout OPEN all1,874 original findings; depth
Q4 boundary implemented but mapped depth OPEN both sides; storage BLOCKED;
floorplan OPEN actual post-conversion area/fill/slots/PG, with388.8x432 only the
inherited sizing model; clock OPEN paid new FF/native spread/insertion/power;
schedule candidate +40 priced but compiler/CTL/END/token integration OPEN.
No full GUNIT qualification, gate, CTS or route was run or authorized by this
packet. The old source, model, active HOP jobs and parent chains are preserved.

Runs: Q4 unit `oth-ubuntu-1561769-1792433363` on ot-agidock128 (24GB/12 threads),
reset unit `oth-ubuntu-2489337-1792433507` on ot-epyc6 (2GB/4 threads). Full logs,
including causal failures and build commands, are in component/ and reset/.
