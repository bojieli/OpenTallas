# Architecture-comparison methodology

**Status:** normative simulation contract  
**Scope:** decode only unless a result explicitly says otherwise

This document prevents a numerically attractive result from being created by
mixing technology generations or by treating immutable weights and mutable KV
state as if they were the same memory problem.  A generated report is conforming
only if it follows every rule below and exposes the listed intermediate values.

## 1. Comparison families never mix

The repository maintains two independent studies.

| Study | Proposed weight store | Mutable-memory generation | GPU comparator | Wafer feasibility anchor |
|---|---|---|---|---|
| Architecture attribution | TSMC N6/N7-class mask ROM | HBM2e-era interfaces, or an explicitly bounded on-wafer SRAM partition | NVIDIA A100 80 GB (TSMC N7, HBM2e) | Cerebras WSE-2 (TSMC N7) |
| Commercial competitiveness | TSMC N4/4NP-class mask ROM | HBM3e | NVIDIA B300 (custom TSMC 4NP, HBM3e) | Cerebras WSE-3 (TSMC N5) |

WSE-2 and WSE-3 establish that wafer-scale construction existed at the stated
nodes.  Their SRAM bandwidth, core count, or marketing compute rate is not
silently assigned to the proposed ROM product.  B200/B300 results must never be
used as the comparator for an N7 ROM envelope, and HBM4 is not used in either
study.

## 2. Storage mutability is a hard constraint

For ordinary autoregressive decode:

- encoded model weights are immutable and may be placed in mask ROM;
- the KV cache, recurrent state, session metadata, and routing workspaces are
  mutable and therefore may **not** be placed in mask ROM;
- an SRAM design may store both weights and KV, but they consume the same scarce
  silicon capacity unless the floorplan explicitly reserves separate banks;
- an HBM design may store both, but both streams consume HBM capacity and channel
  bandwidth;
- no result may pool separate ROM and HBM capacities, or count the same SRAM byte
  once for weights and again for KV.

The capacity check is performed per physical device or wafer stage.  For a ROM
pipeline, a session has a persistent KV shard on every stage, so a microbatch of
`B` requires `B × stages` resident session shards.  Aggregate capacity alone is
not sufficient.

## 3. Bytes, not parameter labels, drive storage and traffic

The released checkpoint is inventoried tensor by tensor.  Storage includes
packed values, scale tensors, BF16/FP32 tensors, draft modules, embeddings, and
resident-only tensors in their actual released representations.  The A100 study
uses a separately derived, offline BF16-expanded deployment because Ampere has no
native floating-point FP8, MXFP4, or FP4 Tensor Core path.

For one decode step:

```text
weight_read_bytes(B) = dense_decode_bytes
                     + routed_decode_bytes × expert_coverage(B)
                     + any explicitly enabled draft-module bytes

kv_transfer_bytes(B) = B × positions ×
                       (kv_read_bytes × implementation_reread_factor
                        + kv_write_bytes)
```

GPU HBM service charges `weight_read_bytes + kv_transfer_bytes`, because the two
streams share channels.  A ROM/HBM design evaluates ROM weight service and HBM KV
service independently, then takes the applicable overlap maximum.  An SRAM-rich
reference must state whether banks are statically partitioned or bandwidth is
shared; the simulator may not choose whichever interpretation is faster after
seeing the result.

The report must emit at least:

- encoded checkpoint and active-step weight bytes;
- weight-read bytes/s at the achieved operating point;
- KV read bytes/token, KV write bytes/token, and total KV bytes/s;
- physical capacity and usable capacity for every storage tier;
- raw and effective bandwidth for every storage tier;
- the binding capacity, bandwidth, compute, communication, or thermal term.

## 4. Density and bandwidth are different quantities

Capacity density (bytes/mm²), read service density (bytes/s/mm²), energy per
access, and write capability are tracked separately.  A dense memory is not
assumed to have proportionally high usable bandwidth, and a high-bandwidth SRAM
is not assumed to have ROM-like capacity.

Each proposed wafer envelope is derived from a cited macro or product anchor and
an explicit scaling rule.  Whole-wafer values deduct ROM/SRAM array area,
compute, NoC, PHY, control, repair, and spare fractions.  Ideal feature-size
squared scaling is an aggressive bound, not a measurement.  Macro results are
not extrapolated across a wafer without separate efficiency, power, repair, and
communication terms.

An SRAM-rich iso-node reference is included to isolate the architectural value
of immutable dense storage.  It is described as a Graphcore-like *style* only:
unless a row is a directly published product value, wafer extrapolations are
labelled derived and are not presented as measured Graphcore performance.

## 5. Computation follows operators and official formats

One multiply plus one add is two operations.  Decode work is generated from the
released DeepSeek implementation and exact tensor dimensions, including
context-linear attention and the final vocabulary projection.  The simulator
does not use `2 × active_parameters` for DeepSeek decode.

Logical operation buckets retain the released operand contract, including
FP8×FP8, MXFP4×FP8, BF16×BF16, FP4×FP4 index scans, and FP32×FP32 mHC work.  A
hardware profile must provide a native path or an explicit emulation path for
every bucket.  Packed four-bit storage does not turn all computation into FP4.

## 6. Communication is derived, not entered as ns/layer

The official DeepSeek tensor-parallel block performs two FP32 all-reduces per
layer: the row-parallel attention output and the MoE output.  The wafer model
therefore charges two events per layer unless a different executable mapping
proves otherwise.  For custom hardware, each event reduces FP32 partial sums and
may distribute the correctly rounded BF16 result.

Communication service is derived from mesh dimensions, path hops, clock, payload
width, bisection width, endpoint/barrier cycles, batch size, hidden size, and
payload efficiency.  Reports expose propagation and serialization separately.
A WSE-like nearest-neighbour mesh is a physical feasibility anchor; a coarse
hierarchical exchange remains an implementation hypothesis until floorplan and
timing evidence exists.

For multi-GPU profiles, each event has a logical FP32 reduction payload plus a
BF16 result payload. Both events are serialized through the configured effective
collective bandwidth. The configured `collective_latency_s_per_layer` remains an
explicitly GPU-favorable **aggregate** latency floor for all inter-GPU events in
the layer; it is not multiplied by two. A one-GPU profile has zero collective
events and zero communication time. This fixed GPU model does not claim to
capture topology-specific ring/tree traffic amplification, contention, launch
behavior, or overlap; those require measured traces for the exact runtime.

## 7. Results are bounds until silicon evidence closes the gates

Conservative, central, and aggressive envelopes are deterministic scenarios,
not confidence intervals.  No product, wafer-cost, yield, or production
throughput claim is authorized until target-node ROM macros, sense margins,
repair overhead, full-array activity, NoC timing, HBM/package integration, power,
and cooling have supporting evidence.  Changing a source fact or scaling rule
requires regenerating both studies and diffing the binding-constraint column
before interpreting headline ratios.

## 8. Huawei Tau and 3-D integration are scenario boundaries, not multipliers

Huawei's **Tau (τ) Scaling Law** (Chinese: **韬(τ)定律**) is treated as a
multi-level optimization framework. Huawei's public ISCAS 2026 release defines
τ scaling as reducing effective delay across four levels: device resistance and
parasitic capacitance, circuit critical paths through LogicFolding, chip-level
software/architecture/silicon co-design, and system communication through
UnifiedBus. This is broader than a rule about stack height.

The same release says LogicFolding breaks the physical boundaries of conventional
planar layout, but it does not disclose whether a particular implementation uses
monolithic sequential devices, face-to-face bonded logic tiers, memory-on-logic,
chiplets, backside interconnect, or only circuit/layout restructuring. It gives
no public tier count, bond pitch, vertical bandwidth or energy, per-tier power,
thermal resistance, yield, repair, or package limits. Huawei's projected 2031
"14 Å (1.4 nm) equivalent" transistor density is therefore a company projection,
not measured present-day silicon and not an allowed numerical input to either
iso-node baseline.

The authoritative N7 and leading-node studies remain two-dimensional
iso-technology baselines. Any future vertical-integration study must be a
separate, visibly labelled scenario and expose at least:

- ROM tier count and usable area per tier;
- integration type, bond pitch, vertical-link count, bandwidth, latency, and
  energy per transferred bit;
- shared versus replicated decoders, sense amplifiers, compute, NoC, and PHY;
- active read power per tier, thermal resistance, temperature and cooling limit;
- known-good-tier yield, bond yield, repair/spare policy, and test access;
- logic tier/node and HBM/package/power-delivery constraints.

Vertical capacity scales only with the characterized usable tiers. Throughput
is still bounded by the slowest concurrent service:

```text
throughput <= min(weight-read service,
                  mutable-KV service,
                  format-specific compute,
                  horizontal NoC service,
                  vertical-link service,
                  cooling/power service)
```

Accordingly, adding ROM tiers does not multiply token throughput unless read
power, sense/periphery resources, vertical links, compute, NoC, and cooling all
scale with them. Tau concepts may guide later implementation work—especially
critical-path shortening and system co-design—but the simulator never applies a
generic "Tau factor".

## 9. Open-PDK evidence is a methodology ladder, not a node-scaling rule

The open custom-transistor work has ten deliberately separate levels:

1. a generic level-1 MOS topology smoke test;
2. pinned SKY130 primitive-model sweeps with declared synthetic capacitance;
3. exact-deck custom layout, zero-error DRC, port-complete LVS, and physical
   capacitance extraction;
4. deterministic PVT/load simulation of the exact archived PEX slice.
5. fixed-seed sampling of the installed per-instance mismatch equations on that
   same PEX slice, including exact same-seed replay and cross-seed variation
   detection.
6. integrated detailed-resistance extraction under five declared interconnect
   styles, exact semantic extraction replay, graph-level programming-connectivity
   checks, and 33 deterministic electrical cases per style.
7. an independently developed foundry-PDK prerequisite: recursively lock the
   pristine IHP SG13G2 release, compile all official ngspice Verilog-A modules
   twice outside the PDK with a portable CPU target, require byte-identical
   outputs, and smoke-test the official 1.2-V NMOS/PMOS wrappers before drawing
   or interpreting the replicated ROM slice.
8. independent IHP custom layout, zero-error full DRC, port-complete unique LVS,
   one-via programming audit, and capacitance extraction;
9. deterministic PVT/load simulation of that exact archived IHP PEX using the
   official PSP103 low-voltage corner sections and pinned OSDI modules;
10. IHP detailed-resistance extraction under all five public interconnect
    styles, exact semantic replay, resistor-graph programming/body-path checks,
    and the same 33 deterministic electrical cases per style.

Every level records its own evidence class and forbidden inferences. A higher
level may replace a synthetic local load with extracted local geometry; it may
not inherit claims about a full row, array, wafer, or target node. The current
physical gates prove independently implemented legal present/absent-via
topologies under the exact installed SKY130A and IHP SG13G2 public decks, with
unique schematic/layout matches. Both deliberately roomy test footprints are
never divided into bits to claim density.

No feature-size, contacted-gate-pitch, SRAM-density, or marketing-node ratio may
scale SKY130 or IHP delay, area, energy, leakage, or bandwidth into N7/N4.
Target-node values change evidence class only after a target foundry supplies a
characterized macro and extracted read path and a reticle vehicle correlates
them to silicon. Until then, compact/full-array distributed resistance,
mismatch/sense yield, full-array activity, repair, late-via personalization
availability/economics, and silicon statistical correlation remain named gates
rather than hidden derates. Level 5 characterizes a public model over a finite
seed set; it does not close mismatch yield, random-defect yield, or product
sign-off. Levels 6 and 10 close only their local demonstration geometries; they
are neither compact-array RC models nor N7/N4 timing anchors. Levels 7 through
10 now close the public IHP device, physical, deterministic-PVT, and detailed-RC
replication chain. IHP statistical mismatch/yield, a compact/full array, and all
target-node and silicon gates remain open.
