# Architecture specification

**Document:** SPEC-ARCH 1.0

**Architecture:** immutable-weight, statically scheduled, multi-stage decode engine

## ARCH-1 Scope and evidence

### ARCH-1.1 Architectural objective

OpenTallas removes ordinary target-decode weight traffic from HBM by placing a
pinned model image in mask-programmed ROM adjacent to arithmetic. A deployment
instance pipelines a fixed contiguous layer partition across one or more physical
stages. Stage-local HBM holds mutable session/KV state; immutable weights are not
copied into HBM for normal operation.

The architecture is optimized for autoregressive decode. Prompt prefill,
multimodal front ends, tokenizer/sampler policy, API networking, storage tiering,
and production session orchestration remain software or external accelerator
responsibilities. Hooks do not constitute performance claims for those paths.

### ARCH-1.2 Evidence contract

The layer topology and released storage inventories are measured or published.
The stage capacities, bandwidths, frequencies, arithmetic roofs, area, power,
repair efficiency, collective timing, HBM organization, links, cost, and package
in `budgets.json` are legacy public-reference proxy values. The architecture
freezes their logical contracts so RTL can test them; it does not promote them to
silicon facts or product targets. Current comparison envelopes live in
`configs/hardware/technology_inputs.json` and `results/iso-node/`. Any report must
preserve this precedence and distinction.

### ARCH-1.3 Configuration versus personalization

Model weights, per-weight scales, immutable tensor layout, image identity, and
ROM repair rows/columns are personalization data. Schedules, tile/link quarantine,
session tables, performance controls, error masks, and operating state are
configuration data. Configuration can select only behavior allowed by the fixed
image manifest; it cannot create a weight write path or reinterpret the image as
an unrelated model.

## ARCH-2 Physical/logical hierarchy

### ARCH-2.1 Hierarchy and limits

The hierarchy is:

```text
deployment instance
└── pipeline of 1..16 stages
    └── 8 × 8 logical reticle fields per stage
        └── 64 service tiles per reticle field
            ├── immutable ROM shards and scale ROM
            ├── format/dequantization and MAC lanes
            ├── activation/partial-sum SRAM and integrity logic
            ├── static local switch endpoint
            └── repair, BIST, counters, and control endpoint
```

The public-reference proxy has 4,096 service tiles per stage. A public RTL regression
uses reduced dimensions but retains the same protocols, scheduling rules, IDs,
and aggregation semantics. Parameter reduction is a verification technique, not
a different architecture.

Architectural fields support 16 stages, 128 layers, 1,024 experts, top-16 routing,
24-bit session IDs, 20-bit zero-based token positions, and 16-bit transaction IDs.
The position field covers indices 0 through 1,048,575.

### ARCH-2.2 Frozen public-reference model configurations

The legacy proxy compiler partition is fixed independently of context and batch. Layer
intervals are zero-based and half open:

| Image | Role | Stage layer intervals | Capacity-accounted bytes by stage |
|---|---|---|---|
| DeepSeek-V4-Flash-0731 | primary proof | `[0,22)`, `[22,43)` | 85.066 GB, 81.812 GB |
| DeepSeek-V4-Pro-0813 | stretch | `[0,11)`, then five ten-layer intervals through `[51,61)` | 155.669 GB, then 147.412 GB × 5 |
| Kimi-K3 | stress/control | `[0,9)`, seven/eight/nine-layer intervals ending `[84,93)` | 135.755–152.281 GB |
| Qwen3-8B | dense control | `[0,36)` | 16.381 GB on one stage; input embedding is resident-only |

Kimi needs eleven stages because indivisible contiguous layer groups cannot be
packed legally into the aggregate ten-stage byte lower bound. Non-layer, draft,
embedding/front-end, and resident-only tensors use compiler-declared slack regions;
they do not alter the contiguous main-layer ownership. Qwen3-8B is dense (no expert
router), uses the BF16 vector profile and full GQA cache at 8,192 tokens, and is
included to exercise the single-stage dense control path rather than to establish
a product target.

These partitions validate image, schedule, capacity, and pipeline interfaces.
They are not the stage counts used by the iso-node product studies, which repack
the exact checkpoint separately for each technology envelope.

### ARCH-2.3 Stage identity

Every stage has a physical device identity, stage index, image identity, active
schedule epoch, repair-map generation, owned layer interval, and published usable
capacity. Neighbors reject mismatched image IDs, pipeline length, or incompatible
ABI major versions before inference enable.

## ARCH-3 Execution model

### ARCH-3.1 Image and epoch binding

An accepted command is bound to:

- the 256-bit mask-programmed image SHA-256 identity;
- a model image slot whose manifest matches that identity;
- an 8-bit schedule epoch and schedule ID;
- the active repair-map generation;
- a configured session ID and expected sequence position.

Identity or epoch mismatch produces a terminal error before layer state changes.
Schedule epoch reuse is permitted only after all transactions from the prior use
have retired and software has observed the wrap guard.

### ARCH-3.2 Ordinary decode

For an ordinary decode command, each stage performs its owned layers in increasing
order. Within a layer the abstract sequence is:

1. acquire the session's layer-local KV/state shard;
2. compute attention/recurrent service through the HBM/vector boundary;
3. obtain router IDs for MoE layers and validate count/range;
4. broadcast the activation and route record using the static schedule;
5. read enabled dense/shared and selected routed ROM words;
6. dequantize, multiply, accumulate, and reduce in the frozen order;
7. apply specified vector/post-processing macro operations;
8. commit the next layer's state only if the transaction is unpoisoned;
9. send the final hidden activation to the next stage or terminal output.

The public reference implements and verifies the control, ROM/MAC, scheduling,
integrity, buffering, and abstract memory/vector boundaries. It may use a golden
functional macro for transformer operations outside that synthesizable scope, but
the macro must obey the same transaction, numeric, error, and timing contract.

### ARCH-3.3 Speculative verification

`SPECULATIVE_VERIFY` accepts one through fifteen candidate positions. Target
verification treats the candidate dimension as additional positions sharing one
weight traversal where legal; KV and arithmetic scale with candidate count. Draft
generation is a distinct operation that uses manifest-declared draft tensors and
cost. Acceptance selection is returned as metadata; the architecture never assumes
a particular acceptance probability.

Draft and target formats, weights, traffic, state commit, and poison behavior are
separately counted. Only the accepted prefix plus the required fallback token may
advance the architectural session position. A detected error commits none of the
candidate state.

### ARCH-3.4 Sessions and ordering

A session-table entry binds session ID, image slot, expected position, context
length, per-stage KV base/limit, numerical mode, active/poison state, and generation.
One session has at most one state-mutating command in flight per stage. Different
sessions may interleave subject to credits. Responses retire in acceptance order on
the host response queue; transaction IDs disambiguate internal completion.

Session release waits for in-flight work or explicitly aborts it. A reused session
ID increments its generation so late HBM/link responses cannot update the new
session.

## ARCH-4 Immutable placement and compute

### ARCH-4.1 Interleaved expert placement

Each expert matrix is deterministically striped across every service tile. A tile
holds a disjoint word/output shard of every expert assigned to the stage, not a
complete local expert. Router IDs are broadcast as data, decoded into a local
wordline mask, and applied to the same physical route and reduction schedule for
all legal selections. Duplicate IDs enable one logical expert once; invalid IDs
poison the transaction.

Dense/shared matrices use always-enabled banks. Draft and resident-only regions
have explicit manifest roles and cannot be accidentally streamed as ordinary
target weights. The stripe function includes image region, tensor ID, matrix row,
block, tile, ROM macro, wordline, nibble order, scale address, and CRC block.

### ARCH-4.2 ROM service contract

In the public-reference proxy, 4,096 tiles expose an aggregate 100 TB/s stage ROM
counter/interface budget. The nominal tile macro interface is 256 physical bits per service
cycle; array duty, repaired resources, clock, and system scheduling make exposed
and achieved bandwidth smaller and are recorded separately. Reads are synchronous,
fixed latency within one macro class, and aligned with scale data and block CRC.

The 100-TB/s number is not a current ROM-wafer assumption or physical claim. N7
and N4 raw/effective services are independently derived and swept in the iso-node
studies; target macro and full-array evidence must replace both.

There is no functional write. Test access can select addresses and observe
signatures/sense outputs but cannot change logical content. Behavioral ROM uses
immutable initialization files whose hash is bound to the manifest.

### ARCH-4.3 Arithmetic organization

The nominal tile contains 128 mixed-precision MAC-equivalent lanes, counting one
multiply and one add as two operations. DeepSeek routed work is explicitly an
MXFP4 E2M1 weight multiplied by an FP8 activation; it is not FP4 × FP4 work.
Dense/shared DeepSeek work is FP8 × FP8, and the dense control uses BF16 × BF16.
The public-proxy service roofs are 0.5 POP/s for each DeepSeek matrix format and
0.25 POP/s for BF16 × BF16 before subsequent derates. The larger raw lane issue
count is not credited until format decode, scale delivery, accumulation, wiring,
and power close together in post-layout evidence.

These fixed roofs exercise counters and throttling only. Product analysis uses
the per-envelope, format-specific ceilings generated from the technology ledger.

Format decode, scale application, block accumulation, tile reduction, and wafer
reduction obey `NUMERICS.md`. Arithmetic is transaction tagged. Valid, route,
activation, weight, scale, accumulator, poison, and completion pipelines must
remain aligned through stalls and legal clock throttling.

## ARCH-5 Deterministic NoC

### ARCH-5.1 Two-level static fabric

Within a reticle, a compile-time scheduled exchange distributes broadcasts and
collects reductions. Across the 8×8 reticle grid, a deterministic mesh/tree
schedule carries the same traffic. The architectural link budgets are 128 bytes
per local cycle and 256 bytes per mesh cycle at the assumed 1 GHz service clock.
The public proxy serializes these aggregates over narrower parameterized ports.

Service traffic uses no routing-table lookup, adaptive choice, or run-time output
arbitration. A schedule entry selects each output's source or idle for one slot.

### ARCH-5.2 Schedule banks and epoch change

Each switch has active and shadow schedule banks with 256 slots. Software/compiler
loads the shadow bank, its length, expected CRC, and proof-certificate hash. The
hardware recomputes CRC and range legality. Commit occurs atomically on a global
epoch boundary only after the affected virtual traffic class is quiescent. A
failed check leaves the active bank unchanged and emits an error.

### ARCH-5.3 Collective service bound

The public-reference proxy uses a 100 ns fixed per-layer NoC floor plus payload at
128 GB/s, followed by the independent synchronization efficiency. The iso-node
analytical contract instead derives communication from topology, path hops,
clock, bisection, endpoint/barrier cycles, and two DeepSeek all-reduces per layer.
Neither is placed-and-routed timing. Activation
payload is BF16-sized and partial-sum payload is FP32-sized unless the manifest
selects another qualified numeric profile.

### ARCH-5.4 Admission credit and flow control

Static links do not carry ready. Before launch, the admission controller reserves
a transaction credit at every destination/egress required by the certified route.
Once launched, each scheduled slot either transports the expected flit or an idle;
missing, duplicate, late, bad-CRC, wrong-epoch, or unexpected flits poison the
transaction. Credits return only after terminal consumption or abort cleanup.

External host, HBM, tile ingress/egress, and stage-link boundaries use ready/valid
elasticity. Egress buffers isolate their stalls from the static core. If an
external stall exhausts admission credits, new work waits outside the NoC.

### ARCH-5.5 Schedule proof obligations

The schedule certificate must establish for every slot and route:

- each selected source is in range and enabled by the active repair map;
- no physical output has more than one source;
- every launched flit reaches exactly its declared sink;
- sequence numbers are continuous and terminal markers unique;
- modeled buffer occupancy never exceeds its configured depth;
- all routes terminate within the epoch and do not depend on future traffic;
- quarantined tiles/links are absent;
- the emitted schedule bytes and certificate share a manifest hash.

Hardware range/CRC checks defend loading errors; the compiler proof and independent
checker establish global properties.

### ARCH-5.6 Determinism

For fixed image, input, schedule, repair map, and error-free state, slot choice,
delivery order, reduction order, and output bits are deterministic. Empty source
slots insert idle, not delayed traffic. Legal clock throttling stretches wall time
but preserves slot count and order.

### ARCH-5.7 Faulted fabric

Permanent faults are quarantined. The compiler emits a replacement stripe/schedule
consistent with remaining capacity and the repair map. Dynamic detours are disabled
in deterministic service mode. If no legal schedule retains the requested image
and capacity, the stage publishes reduced capability or remains unavailable.

## ARCH-6 Memory hierarchy

### ARCH-6.1 Immutable weight tier

Each public-reference stage exposes a 160-GB usable weight address contract from a
184-GB raw proxy hypothesis.
The raw-to-usable gap covers row/column repair, layout fragmentation, immutable
metadata, CRC/signature storage, and service reserve. The compiler checks every
physical stage and largest indivisible layer region; aggregate capacity alone is
insufficient.

This address/capacity contract is not a product density claim. Iso-node stage
capacity ranges from the independently derived macro/floorplan envelopes and
therefore produces different Flash/Pro stage counts.

### ARCH-6.2 Mutable HBM tier

Each public-reference stage models 384 GB physical HBM and exposes at most 90% for
session/KV state.
The remainder is reserved for allocator metadata, queues, activation workspace,
communication, diagnostics, and safety margin. Twelve logical controller ports
share the 8 TB/s stage budget; their mapping to actual stacks/PHYs is an external
package decision.

Product studies use same-generation HBM2e/HBM3e stack matrices and explicit
perimeter-pitch checks instead of this fixed proxy. All stack counts remain OSAT
and HBM-vendor gates.

Requests are tagged and may complete out of order across tags, in order within a
tag. The public memory model implements the interface and error behavior but does
not impersonate vendor PHY timing. HBM ECC status is translated into the common
RAS classes and is covered by end-to-end CRC at declared boundaries.

### ARCH-6.3 Local capacity and state commit

Every long-lived session has a layer-local state shard on every stage. Admission
uses the worst local stage after repair and reserve; ROM/HBM bytes cannot be pooled
between stages. State writes use prepare/commit semantics: new KV/state becomes
architectural only after the layer or speculative transaction passes integrity
checks. Abort discards prepared state or invalidates it by generation.

## ARCH-7 Pipeline

### ARCH-7.1 Stage pipeline semantics

Stages operate concurrently on different microbatches. A batch value is the
microbatch active at one stage. A fully occupied S-stage pipeline therefore holds
S microbatches and requires `batch × S` resident sessions. Pipeline fill/drain is
reported separately from steady-state interval.

### ARCH-7.2 Resident capacity

The front-end reserves all stage-local session resources before admitting a
pipeline wave. Partial reservation rolls back without changing any session. The
published maximum batch per stage is the minimum over all stage-local HBM limits
divided by pipeline depth, after integer flooring and repair degradation.

### ARCH-7.3 Cross-stage link

The abstract stage link carries 256-bit NoC flits plus packet CRC32C at 128 GB/s
payload and 0.5 microsecond one-way fixed latency. Packet credits prevent overflow.
A CRC or sequence error requests at most two retries from the retained packet
buffer; exhaustion poisons and aborts the transaction. Duplicate replay is
recognized by epoch, transaction, and sequence and cannot double-commit state.

## ARCH-8 Host, lifecycle, and observability

### ARCH-8.1 Host boundary

The public boundary is the exact ready/valid command, response, CSR, and telemetry
ICD. A product may bridge this to PCIe/CXL or another host transport without
changing command semantics. DMA addresses use 64-byte units and are validated by
the trusted host/IOMMU boundary; the public reference does not claim hostile-DMA
isolation.

### ARCH-8.2 Lifecycle operations

Boot, configure session, decode, speculative verify, release session, load shadow
schedule, commit epoch, load repair map, BIST, diagnostics, quiesce, resume, and
abort have explicit opcodes. Quiesce blocks admission and drains. Warm reset uses
quiesce or terminal abort. Test mode blocks inference. No operation can alter
logical ROM data.

### ARCH-8.3 Observability

Architectural counters cover admissions, completions, errors, active/idle/throttle
cycles, stall classes, ROM words, HBM bytes, NoC flits/idles/CRC failures, link
retries, repairs, BIST, and latency histograms. First-error capture and fatal
telemetry are lossless until acknowledged. Counter overflow is sticky and does
not affect functional state.

## ARCH-9 Black boxes and security boundary

### ARCH-9.1 External macros

Foundry ROM, SRAM compilers, HBM controller/PHY, stage-link PHY, PLL/clock macros,
thermal/voltage sensors, eFuse/OTP, root of trust, scan compression, IO/ESD, and
package structures are external. Each uses a behavioral wrapper with frozen
request/response, timing class, reset, BIST, integrity, and fault signaling. Open
standard-cell proxies validate logic and methodology only.

### ARCH-9.2 Security scope

The public reference assumes a trusted host and trusted manufacturing/test flow.
SHA-256 binds identity and integrity but an unsigned manifest does not authenticate
an owner. Tenant isolation, confidentiality, secure boot keys, anti-rollback,
side-channel resistance, physical attack resistance, and hostile DMA protection
require product security architecture and qualified macros outside this freeze.

Diagnostic CSRs expose identities, counters, syndromes, repair maps, and signatures,
not arbitrary live session payload. This boundary prevents accidental debug leakage
but is not a complete security certification.
