# V4.1: wafer versus chip-array feasibility for 100 µs/token

**Superseding direction:** derive maximum performance from a physically constrained
machine and its dependency/communication schedule. The 100 µs values below are
historical sensitivity cases, not fixed design requirements. See the
[resource-first method](RESOURCE_FIRST_PERFORMANCE_METHOD.md) for current acceptance
criteria and the single-sequence versus aggregate-throughput distinction.

**Current comparison priority:** HBM accelerator array is the primary baseline;
ROM chip array is the primary proposed design; one or more connected ROM wafers
are secondary. Both ROM options are evaluated for 100 µs/token feasibility.
See the [three-design comparison](DEEPSEEK_V41_THREE_DESIGN_COMPARISON.md)
for the authoritative scope, fair comparison rules and expert-fabric analysis.

The user has now explicitly retained **100 µs per ordinary decode token** as a
feasibility target. This supersedes the earlier decision not to select a token
latency target. The previous 40 µs expert allocation remains adjustable. The goal
is to derive physical performance ceilings for an **integrated wafer-scale ROM
system versus an array of separate ROM chips with fast interconnect**, before
implementation or workload simulation. The user explicitly clarified “array,”
with NVLink/NVL72-style connectivity as examples, not a single-reticle system.
Compare equal total die area first, and separately the scale each needs to
implement the system. No particular vendor link rate or topology is assumed.

## First boundary: can the model reside in the device?

Use the existing assumed N5 ROM density, 9,379,500 B/mm², and 2% reserve. These
are planning inputs, not a characterized wide-port ROM macro. Retained checkpoint
capacity includes objects with no credited ordinary-decode throughput; removing
such objects needs a new deployment inventory rather than free capacity relief.

| Placement | Retained weight capacity | Required ROM area alone |
|---|---:|---:|
| All ROM | 510.286 GB | 55,515 mm² |
| Engram in external memory | 307.528 GB | 33,456 mm² |

| Device-area screen | All-ROM capacity | Hybrid capacity | Hybrid area left for everything else |
|---|---|---|---:|
| One 815 mm² planning reticle | Fails | Fails | None |
| Ideal 45,000 mm² square wafer region | Fails | Fits bytes only | 11,544 mm² |
| Hypothetical 60,000 mm² usable irregular wafer region | Fits bytes only | Fits bytes only | 26,544 mm² |
| Entire ideal 300 mm disk, 70,686 mm² | Fits bytes only | Fits bytes only | 37,229 mm² |

The 45,000 mm² value is the largest square inscribed in an ideal 300 mm circle,
without edge margin. The 60,000 mm² layout is hypothetical. The gross disk is an
absolute geometric upper bound, not usable circuitry area: wafer edges, streets,
repair, connectivity and yield reduce it. An all-ROM 60,000 mm² region leaves
only 4,485 mm² for all compute, SRAM, control, fabric and physical infrastructure.
A design that fits weight capacity alone has not passed architecture feasibility.

A single self-contained reticle-scale ROM implementation is therefore rejected
under these density and inventory assumptions. Even allocating *every square
millimeter* to ROM needs at least 42 reticles with Engram elsewhere, or 69 for the
all-ROM inventory, before compute and other overhead. Earlier 400 mm²-ROM-per-die
screens needed 84 and 139 respectively because they reserve area for other uses.
These results are consistent, not competing die-count estimates.

The single-reticle rejection is only a per-chip capacity observation; **it does
not reject the chip-array architecture**. The array distributes the weights and
compute across enough chips. At equal total silicon area and the same ROM density,
the raw capacity budget is identical before integration-specific overhead:

| Reference total area | Example chip count | Area per chip for exact area matching |
|---|---:|---:|
| 45,000 mm² | 56 | 803.6 mm² |
| 60,000 mm² | 74 | 810.8 mm² |
| 70,685.8 mm² gross-disk bound | 87 | 812.5 mm² |

These are area partitions, not selected packages or a claim that a gross disk is
usable. The array must fit its PHYs, controllers, SRAM and compute within that
same area. The wafer must charge stitching, repair, routing and other integration
overhead. Compare equal system power as a second constraint; packaging, switches
and interconnect power cannot be omitted because they are outside compute dies.

**Placement determines the fabric requirement.** Keep each selected expert's
weights local to its compute where feasible, multicast input activations, and
return outputs for the required merge. The 112.8 TB/s expert-probe rate is local
ROM read service, not a required NVLink-like external rate. If experts or dense
operators are tensor-sharded across chips, charge their partial reductions and
synchronization separately. KV-owner placement and cross-layer transfers also
need explicit accounting. Fast fabric is not zero-latency fabric.

The next comparison must sweep endpoint rate, hop/switch latency, bisection,
concentrated routes, and link energy. NVL72 is an example of a connected system,
not a specification that can be copied as one bandwidth number. Distinguish
per-direction payload bandwidth from bidirectional or system-wide totals. Wafer
links need the same delivery and critical-path treatment. Neither integration
approach receives free global bandwidth or perfect utilization.

## Necessary service for 100 µs/token

Using the retained analytical work inventory at batch one and 200K context:

| Work category | Necessary average rate across the full 100 µs |
|---|---:|
| All active weight reads, 13.035 GB | 130.351 TB/s local aggregate |
| Routed portion, 4.512 GB | 45.122 TB/s local aggregate |
| Tensor arithmetic, 40.114 Goperations | 401.139 TOp/s |
| KV reads at 200K, 46.763 MB | 0.468 TB/s |
| KV reads at 1M, 182.763 MB | 1.828 TB/s |

These rows are necessary average demands, not a complete additive schedule. A
category assigned less than the full interval needs a higher active rate. The
112.8 TB/s expert figure corresponds specifically to a 40 µs expert allocation.
The full tensor work excludes some auxiliary service priced in other units;
index items, nonlinear items and normalization items are not interchangeable MACs.
All rates require delivery to the active regions, not unused installed capacity.

At 4.5 TB/s delivered HBM per independently usable endpoint, uncached weight
service alone needs at least 29 endpoints to fit 100 µs. Fully caching the
non-routed inventory reduces that count to 11 for routed reads alone, while
charging local cache reads, compute and cache area separately. Neither count
proves a valid placement or complete HBM latency. See the
[speedup conditions](DEEPSEEK_V41_SPEEDUP_CONDITIONS.md) for cache sensitivity and
unchanged critical-path work.

## How the performance ceiling will be established

Capacity screens can already reject some configurations. A defensible numeric
physical tokens/s ceiling still requires evidence for:

1. **ROM banking:** density versus port width, read latency, energy and active-bank
   selection; no assumption that capacity-dominated regions provide free bandwidth.
2. **Compute and reduction:** area and clock of the admitted numerical contracts,
   finite lane scheduling, scale conversion and ordered partial accumulation.
3. **Mutable storage:** KV/index ownership, attention working set, bank conflicts,
   finite partial buffering and cache placement.
4. **Distance and topology:** wafer links versus package links, route/return
   latency, bisection demand and worst-case concentrated expert selection.
5. **Power:** local ROM, arithmetic, SRAM and fabric energy per token, leakage,
   package delivery and cooling. Area alone cannot establish an operating point.
6. **Whole-token dependencies:** use the slowest admitted critical path and real
   overlap limits, not a sum of independent peak rates. Distinguish single-user
   100 µs latency from multi-user pipeline throughput.

For each physical resource r, a necessary service bound is `work_r / rate_r`.
Combine those bounds with numerical dependencies and serial communication, using
an explicit schedule for overlap. The reciprocal of a proven lower latency bound
is a conditional throughput ceiling, not achieved performance. Array and wafer
comparisons must each name capacity, area, power, deployment tier and concurrency.

**Current design direction:** evaluate both wafer and chip-array hybrids with
expert-local ROM, non-routed matrix locality and owner-local KV/index. Retain
all-ROM variants for both. Do not choose an integration winner before measuring
the area/power cost and critical-path effect of their respective interconnects. Do not declare 100 µs feasible yet:
capacity is only the first gate and the required physical macro evidence is open.
The Qwen ROM/HBM redesign remains in scope; this document addresses the separate
V4.1 deployment rather than extrapolating its results to Qwen.

Reproduce with `python3 tools/audit_v41_physical_envelope.py`; see
[the machine-readable envelope](../results/architecture/v41_physical_envelope.json).
