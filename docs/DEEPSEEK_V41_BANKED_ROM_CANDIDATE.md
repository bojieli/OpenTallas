# An address-striped ROM candidate: explicit pooling requirements

The bank-ownership audit left a large gap between fixed expert ports and fully
pooled service. This candidate supplies a logical implementation of pooling:
**stripe every expert over the same banks, place different experts/layers in
different row ranges, and read selected expert streams in turn**. It is not a
physical macro implementation or a proof of advanced-node timing/density.

For N banks of 256-byte words, map packed expert byte offset a to:

- Bank: `floor(a/256) mod N`.
- Row: `expert_base_row + floor(a/(256N))`.
- Byte lane: `a mod 256`.

Expert base rows include layer identity and are aligned to complete stripes.
Each complete stripe accesses every bank once without a bank conflict. Six
selected experts time-share those ports; they do not each receive the entire
regional rate simultaneously. Padding and packet/format boundaries reduce useful
service. Scales must travel with their corresponding native 32-value blocks.

This logical layout demonstrates why ROM need not strand all cold experts' ports:
address depth, rather than separate ports, stores inactive experts. It also moves
the hard problem into deep banks, hierarchical decoding, subarray selection,
local compute placement and long wires. A logical bank is not one feasible SRAM-
style macro of arbitrary depth.

## Joint bank and compute requirements

Take the existing 80-chip, twenty-layer-stage map: four-chip expert islands,
500 mm² assumed ROM allocation and 4.596 GB usable capacity per chip. The table
assumes 1 GHz, 256 B/word, 65% delivered bank service and 65% scalar MAC utilization.
Rates are sensitivity choices, not measured properties or selected design points.

| Delivered regional rate | Logical banks | Words/bank | Capacity/bank | Scalar MAC lanes to consume routed stream |
|---|---:|---:|---:|---:|
| 4.5 TB/s | 28 | 641,177 | 164.14 MB | 13,032 |
| 18 TB/s | 109 | 164,706 | 42.16 MB | 52,127 |
| 72 TB/s | 433 | 41,462 | 10.61 MB | 208,507 |

The compute conversion uses 0.5 payload byte plus 1/32 scale byte per routed
weight. Dense FP8/BF16 paths need their own service and lane accounting. Scalar
lane counts do not include partial reduction, scales, activation or control.
The 315 mm² remaining on each chip is not all available to those lanes: SRAM,
PHYs, clocks, power infrastructure and routing also require area.

The audit charges complete-stripe padding to all 780 resident expert shards on
the most populated chip of this mapping. Backbone plus expert padding fits the
assumed payload for these three points, but complete dense/head/draft alignment
and remaining object placement still need proof. Round-up of bank depth is shown
separately and is not extra free capacity. The assumed 2% reserve stays reserved.

A viable physical implementation likely subdivides each logical bank into many
smaller arrays. Its read-latency/throughput, mux area, wiring and power must be
measured or supported by source evidence. The same 500 mm² cannot simultaneously
be assumed to provide arbitrary density, depth, port width and decoder speed.
The 130 nm macro evidence does not qualify this N5 organization.

## Energy places an independent ceiling

For delivered rate B TB/s and e pJ per delivered bit, read-path power is:

`P_read = 8 × B × e watts`.

| Rate | At 0.1 pJ/bit | At 0.5 pJ/bit | At 1 pJ/bit |
|---|---:|---:|---:|
| 4.5 TB/s | 3.6 W | 18 W | 36 W |
| 18 TB/s | 14.4 W | 72 W | 144 W |
| 72 TB/s | 57.6 W | 288 W | 576 W |

These energy values are illustrative. A 100 W read-path allocation would require
at most 0.174 pJ per delivered bit at 72 TB/s. That allocation is not a selected
package budget. Compute, SRAM, clocking, leakage, fabric and external memory are
additional. Idle chips reduce dynamic activity but still consume leakage and
system power; multi-user concurrency changes simultaneous activity.

Thus bank count alone cannot validate a high service rate. The next physical
contract must include read energy and the same decoder/mux/wire boundary used for
area and bandwidth. Native CIM arithmetic would be a different implementation
contract, not a way to substitute an operation-derived bandwidth into this design.

## Current decision

Retain address-striped banks as a concrete candidate for pooled ROM service,
with the layout and padding rules above. Do not choose a rate until a bank/subarray
hierarchy, compute area and power budget support it. Keep the fixed-bank alternative
as a separate organization with different active bandwidth. Neither establishes a
ROM/HBM decode speedup yet; both feed the resource-first array comparison.

Reproduce with `python3 tools/audit_v41_banked_rom.py`; see
[the requirements calculation](../results/architecture/v41_banked_rom.json).
No implementation or hardware/workload simulation was performed.
