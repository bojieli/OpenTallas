# OpenTallas pre-NDA technology and validation roadmap

**Public-collateral review date:** 2026-08-28

## Bottom line

OpenTallas is a model-specific inference architecture in which immutable model
weights are encoded in mask ROM close to arithmetic, while mutable state such
as the KV cache remains in writable SRAM/HBM. The intended benefit is to avoid
streaming active weights through the same off-chip memory tier on every decode
step. The cost is model inflexibility, mask/NRE exposure, repair complexity,
and a much harder custom-memory, power-delivery, packaging, and yield problem.

The repository is presently a reproducible research and requirements program,
not an N7 or N4 implementation. It contains exact checkpoint/operator
accounting, analytical architecture models, public-reference RTL, mature-node
custom-ROM methodology vehicles, and a predictive ASAP7 digital campaign. It
does not contain a foundry ROM compiler, a complete exact-format arithmetic
implementation, or a signoff-ready wafer-scale product.

The public review found no redistributable, manufacturable TSMC N7/N4,
Samsung 4-nm, or equivalent frontier foundry PDK. Public 7-nm and 3-nm kits are
predictive research kits. That does not make pre-NDA work pointless: it can
establish necessary requirements, eliminate architectures that miss them,
validate the implementation method, and produce a PDK-portable collateral
package. It cannot positively establish target-node manufacturability.

The asymmetry is important:

- a failed exact-accounting, formal, timing, capacity, bandwidth, or thermal
  gate can disprove the current design;
- passing public and predictive gates means "not yet disproven," not "N4
  feasible"; and
- a defensible GPU-superiority claim ultimately requires the same model,
  arithmetic, accuracy, context, batch/concurrency, latency, and power scope on
  measured implementations.

## What is already validated

| Evidence | What it establishes | What it does not establish |
| --- | --- | --- |
| Pinned model inventories and operator accounting | Checkpoint bytes, active-weight traffic, KV traffic, and operation counts for the exact declared model revisions | Runtime kernels, achieved accuracy, router traces, or silicon throughput |
| Public-reference RTL, simulation, formal, CDC/RDC, and fault injection | The checked control/dataflow behavior and enumerated public fault cases | Product RTL completeness, exact FP8/MXFP4/BF16/FP32 arithmetic, ATPG, or physical signoff |
| SKY130A and IHP SG13G2 controlled-via ROM slices | Independent DRC/LVS/PEX/SPICE methodology, programming invariant, PVT/load test method, and mismatch/extraction plumbing on real mature-process-derived public collateral | A dense production ROM macro, target-node scaling, or silicon yield |
| ASAP7 synthesis through GDS plus formal equivalence | Predictive digital timing, cell area, routing, parasitics, congestion, and tool-flow reproducibility for the exact proxy RTL | A foundry N7/N4 result or any ROM-array property |
| Public ROM/CIM papers and commercial architecture disclosures | Fabricated or simulated anchor points and system-level ceilings with declared provenance | A transferable density/bandwidth multiplier or OpenTallas performance |
| Inverse GPU break-even calculation | The minimum capacity, byte rates, exact-format operation rates, latency, and energy ceilings that a future implementation must beat | Evidence that a future implementation achieves any threshold |

## Public collateral that is actually available

### Manufacturable-process-derived public PDKs

These are the strongest public collateral for validating a custom-memory
method, but they are mature nodes and must not be used as N7/N4 scaling anchors.

| Collateral | Public facts | Appropriate OpenTallas use |
| --- | --- | --- |
| [SkyWater SKY130A](https://github.com/google/skywater-pdk) | Foundry-derived 130-nm-class public PDK; its maintainers call the release an experimental preview suitable for test chips and initial verification, not production | Custom topology, layout, DRC/LVS/PEX, SPICE, mismatch, repair concept, test structures |
| [IHP SG13G2](https://github.com/IHP-GmbH/IHP-Open-PDK) | 130-nm BiCMOS open PDK derived from a process used for manufactured designs; current public release is still labelled preview | Independent replication so results do not depend on one PDK or one extractor/model stack |
| [GlobalFoundries GF180MCU](https://github.com/google/gf180mcu-pdk) | Foundry-derived 180-nm MCU public PDK, also labelled experimental preview | A third-methodology replication if SKY130/IHP disagreement remains; not needed merely to add another node |

### Predictive advanced-node research kits

| Collateral | Contents visible publicly | Valid use | Invalid use |
| --- | --- | --- | --- |
| [ASAP7 v1.7](https://github.com/The-OpenROAD-Project/asap7) and its [paper](https://doi.org/10.1016/j.mejo.2016.04.006) | BSD-licensed predictive 7-nm FinFET PDK, design-rule manual, HSPICE FF/TT/SS model cards, routing collateral, and 7.5-track/6-track cells | Digital synthesis/P&R/congestion/timing/extraction; separately governed predictive transistor-level ROM experiments if simulator/model compatibility is proven | Calling a result TSMC N7, N4, or silicon-calibrated; using the bundled FakeRAM as a target ROM |
| [FreePDK3](https://github.com/ncsu-eda/FreePDK3) | NCSU/Synopsys predictive 3-nm kit with nanosheet-oriented rules, buried power rails, HSPICE models, StarRC data, ICV DRC/LVS, and a 13-metal-plus-RDL stack | A second predictive custom-layout/circuit sensitivity study when licensed Synopsys tools are available | Treating "3 nm" as a foundry node or as an N4 error bar; assuming its tool formats form an open-source flow |
| [FreePDK45](https://eda.ncsu.edu/freepdk/freepdk45/) / Nangate45 | Generic, non-fabricable teaching/research process and cell library | Flow development, formal/netlist plumbing, rough structural scaling | Transistor, memory, or manufacturability evidence |

ASAP7 is currently the best public choice for the digital branch because a
pinned OpenROAD flow can consume it end to end. FreePDK3 is useful as a
different predictive-device/rule sensitivity point, especially for custom
layout, but it does not improve the foundry claim class.

### Public memory and system anchors

| Source | Evidence class | Bounded use |
| --- | --- | --- |
| [28-nm hybrid SRAM/ROM-CIM, JSSC 2025](https://doi.org/10.1109/JSSC.2025.3556008) | Fabricated macro; paper reports 8.928 Mbit/mm^2 | Planar density anchor; any scaling to 7/4 nm remains derived and is swept |
| [YOLoC, DAC 2022](https://doi.org/10.1145/3489517.3530576) | 28-nm circuit/architecture simulation, not fabricated silicon | ROM-CIM bandwidth-density anchor only, with explicit array/power/clock/repair derates |
| [3D-METRO, ASP-DAC 2025](https://doi.org/10.1145/3658617.3697570) | Evaluated transistorless 3-D-metal ROM proposal, not fabricated silicon | Aggressive density ceiling only; no automatic vertical-integration multiplier |
| [NVIDIA A100 product/architecture material](https://images.nvidia.com/aem-dam/en-zz/Solutions/data-center/nvidia-ampere-architecture-whitepaper.pdf) | Commercial TSMC-N7 GPU disclosure | Same-generation system comparator and published capacity/bandwidth/compute/power inputs |
| [NVIDIA DGX B300 system guide](https://docs.nvidia.com/dgx/dgxb300-user-guide/introduction-to-dgxb300.html) | Commercial custom-TSMC-4NP/HBM3e system disclosure | Leading-node system comparator; undisclosed quantities remain assumptions/sweeps |
| [Cerebras WSE-3](https://www.cerebras.ai/product-chip) | Fabricated TSMC-N5 wafer-scale product disclosure | Proof that wafer-scale construction exists and a loose physical/system ceiling, not a ROM-wafer proxy |

Public foundry brochures, architecture white papers, and product pages can
anchor node, memory generation, power envelope, and advertised system
capabilities. They do not disclose the device models, statistical corners,
BEOL stack/rules, extraction coefficients, EM limits, or custom-ROM compiler
views needed for signoff.

## Quantitative pre-NDA gate

The inverse calculation deliberately starts from a comparator and asks what a
future OpenTallas product must achieve. The current reference is
DeepSeek-V4-Flash-0731, B300 x1, batch 1, 8,192-token context. The B300 result
is a governed analytical comparator using published/derived system inputs, not
a measured local B300 run.

| Equality requirement | Current value | Evidence status |
| --- | ---: | --- |
| Aggregate decode throughput | 438.315 token/s | Comparator-derived target, not achieved |
| Full usable checkpoint capacity | 166.879 GB | Exact model inventory; target ROM implementation absent |
| Effective active-weight delivery | 4.917 TB/s | Exact traffic x target step rate; target ROM implementation absent |
| Mutable-KV delivery | 5.775 GB/s effective; 8.251 GB/s raw at 70% efficiency | Derived requirement; HBM/package unvalidated |
| Active B1 KV capacity | 31.953 MB | Exact profile-derived minimum; does not include fleet/session margin |
| Tensor arithmetic | 12.948 TOP/s total | Derived exact-format requirement; current integer RTL is not qualifying evidence |
| Decode interval | 2.281467 ms maximum | Whole-step ceiling, not a component timing budget |
| Allocated-power energy parity | 4.135 J/token; 139.987 pJ/tensor-op | Derived from 1,812.5-W B300 system allocation; not measured board energy |

The required reference arithmetic mix is 6.016 TOP/s FP8xFP8,
5.692 TOP/s MXFP4xFP8, 0.309 TOP/s FP4xFP4, 0.901 TOP/s BF16xBF16,
and 0.0297 TOP/s FP32xFP32. Each path must be implemented and bit-accurately
qualified; a generic integer multiplier count cannot replace this check.

One-wafer capacity depends strongly on how much wafer area is assigned to ROM
and how much raw array capacity remains usable:

| Declared case | ROM area | Usable fraction | Required usable density | Required raw density |
| --- | ---: | ---: | ---: | ---: |
| 35% area | 16,178.75 mm^2 | 80% | 82.517 Mbit/mm^2 | 103.147 Mbit/mm^2 |
| 48% area | 22,188.00 mm^2 | 86% | 60.169 Mbit/mm^2 | 69.964 Mbit/mm^2 |
| 55% area | 25,423.75 mm^2 | 90% | 52.511 Mbit/mm^2 | 58.346 Mbit/mm^2 |

The current public-assumption envelopes produce 101.111, 242.651, and
473.644 GB usable capacity. Thus the conservative case requires at least two
capacity stages, while the central and aggressive arithmetic envelopes fit the
checkpoint on one wafer. This is an assumption-screen result, not an N4 macro
result. In particular, it omits a foundry-calibrated density error bar,
periphery closure, sense margin, simultaneous-read power, repair structures,
and yield.

The first governed ASAP7 physical point supplies another useful negative
constraint. The current unpipelined one-cycle 16-lane signed-integer proxy
failed a correctly scaled 1.25-ns/800-MHz constraint with -2.121-ns setup WNS.
It passed at 4.25 ns, with 243.123-MHz reported fmax, exact mapped and post-route
equivalence, and zero DRC, antenna, hold, or unconstrained-endpoint violations.
It therefore does not support the present analytical 0.9-1.1-GHz whole-product
clock assumptions. The RTL must be pipelined/restructured and remeasured; the
frequency assumption cannot simply be inherited from a node label.

The bounded local RTX PRO 6000 measurement also completed, with the existing
Qwen3-VL-30B-A3B-Instruct-FP8 endpoint left in service. At concurrency one,
median 64-token end-to-end completion rates were 171.342, 180.198, and
164.876 token/s for 256-, 2,048-, and 8,192-token prompts respectively. The
256-token concurrency-two case measured 142.393 token/s per request by the same
request-level metric. All ten requests passed exact usage checks. Seven compute
processes and a second serving endpoint shared the device, so the run is
`shared_contended`; its whole-GPU power observations are not energy attributed.
It is a Qwen service target, not a DeepSeek result and not an OpenTallas/GPU
speedup comparison.

## How far validation can go without a frontier PDK

### Level 1 — architecture and model correctness: closeable publicly

- Hash exact model revisions and tensor inventories.
- Retain exact dense/routed formats and operation shapes.
- Run bit-accurate golden models and numerical qualification.
- Use trace-derived expert coverage when production traces become available;
  keep the independent-routing model labelled as an assumption until then.
- Prove RTL safety/liveness/control invariants and run dual-simulator/fault
  campaigns.

### Level 2 — implementation structure: closeable publicly

- Implement every arithmetic format rather than extrapolating from integer
  proxies.
- Run synthesis, STA, floorplan, CTS, routing, extraction, DRC, antenna, and
  post-route equivalence in pinned ASAP7.
- Sweep utilization, aspect ratio, pipeline depth, clock period, voltage/corner
  models, and routing pressure. Preserve failed points.
- Produce an FPGA or cycle-accurate system prototype with the real scheduling,
  reduction, repair indirection, KV traffic, and stage backpressure.

### Level 3 — custom-ROM method: closeable publicly, target value not closeable

- Keep the independent SKY130A and SG13G2 DRC/LVS/PEX/SPICE vehicles.
- Expand from a slice into subarrays with decoder, wordline driver, bitline
  loading, sense path, output latch, ECC/repair, and simultaneous-read cases.
- Port the same parameterized testbench to ASAP7 HSPICE/BSIM-CMG models and,
  where tool access permits, FreePDK3. Record these as predictive studies.
- Sweep extracted RC, PVT, loading, modeled mismatch, activity, IR-drop
  injection, and faults. Do not invent target-foundry distributions.
- Measure a mature-node test chip if budget permits. This validates the
  topology and the scaling methodology, not N4 values.

### Level 4 — system break-even and competitor baseline: closeable publicly

- Derive inverse capacity/bandwidth/compute/NoC/HBM/energy requirements for
  every context and batch rather than claiming an assumed ROM throughput.
- Benchmark available GPUs with raw requests, usage, TTFT, latency, throughput,
  process inventory, and power samples. Label shared runs as contaminated and
  do not attribute whole-GPU joules.
- Run a same-checkpoint comparator on suitable GPUs before making a speedup
  claim. A Qwen service measurement is useful operational evidence but cannot
  substitute for a DeepSeek comparison.
- Treat public A100/B300/WSE disclosures as ceilings or comparator inputs, not
  measurements of OpenTallas.

### Level 5 — target technology signoff: not closeable without controlled access

The following remain outside the public validation ceiling:

- target mask-ROM compiler or custom bitcell approval and density;
- target statistical/PVT/aging models and sense/read margin;
- target DRC/LVS/PEX/DFM decks and fill/coloring rules;
- BEOL RC, coupling, via rules, clocking, power grid, EM/IR, and simultaneous
  full-array activity;
- HBM PHY/controller, interposer/bridge, bump maps, reticle or stitching rules,
  and OSAT assembly constraints;
- thermal-mechanical analysis with package boundary conditions;
- wafer yield, defect maps, repair coverage, test time, reliability, lifetime,
  and cost; and
- fabricated same-model throughput, latency, energy, and accuracy.

No amount of scaling from 130 nm, ASAP7, or a public product white paper can
close these gates.

## Practical access routes

If "no NDA" means no agreement is currently in place, use a program that can
sponsor and administer access. If it means the project is unwilling or unable
to sign any confidentiality agreement, it must stop at the public validation
ceiling above.

### TSMC N7 through a university/research channel

[EUROPRACTICE's TSMC University FinFET Program](https://europractice-ic.com/tsmc-university-finfet-program/)
publicly offers N16 and N7 design collateral and MPW/test-chip access to member
universities, including universities in North America. Applications are
reviewed by TSMC; after approval, an NDA is issued and collateral is delivered
through imec's secure platform. The public
[access page](https://europractice-ic.com/technologies/asics/tsmc/access-contacts/)
also states that companies and research institutes can request TSMC N7/N5
access through imec, with TSMC approval and a three-party
TSMC-imec-customer NDA.

This is a concrete route to real N7 collateral, but it is not an open-PDK route
and the public program does not promise a suitable mask-ROM compiler.

### Samsung 4 nm through an MPW/customer channel

Samsung Foundry's public
[2026 MPW page](https://semiconductor.samsung.com/foundry/manufacturing/mpw-service/)
lists 4-nm SF4X and 5-nm SF5 shuttles. It directs new customers to submit a
company/application package for review and then use the controlled B2B CONNECT
service. Samsung's [SAFE program](https://semiconductor.samsung.com/foundry/safe/)
publicly describes the ecosystem that supplies PDKs, design methods, IP, EDA,
design-service, multi-die, and OSAT support.

This establishes that a controlled 4-nm MPW path exists; it does not make the
PDK, ROM IP, or commercial terms public.

### Intermediaries and parallel partners

- [IC-Link by imec](https://www.imeciclink.com/en/asic-fabrication) is a TSMC
  Value Chain Alliance member and a main EUROPRACTICE partner for design-to-
  production access.
- A foundry-approved design-service/VCA/SAFE partner can perform the target-PDK
  work in its secure environment and return a governed result package. The
  project still needs the appropriate confidentiality and IP agreements.
- Contact memory-IP vendors early. Standard-cell access does not imply a mask-
  ROM compiler, and an SRAM compiler is not an acceptable ROM-density proxy.
- Engage an OSAT/package partner in parallel. A ROM wafer with HBM is a package
  and power-delivery program, not only a front-end process exercise.
- University, national-lab, and government prototyping programs may subsidize
  access, but they do not eliminate foundry approval or confidentiality.

## PDK-portable handoff package to prepare now

The highest-value pre-NDA output is a package a secure foundry/design partner
can retarget quickly:

1. Exact model/tensor revision, accuracy baseline, arithmetic formats, and
   bit-accurate vectors.
2. Parameterized ROM subarray schematic/layout intent, programming rule,
   decoder/sense/ECC/repair architecture, and activity cases.
3. Synthesizable pipelined arithmetic/control/NoC RTL with formal properties
   and clean regression evidence.
4. Machine-readable constraints: capacity, area fractions, read ports, byte
   rates, per-format operation rates, latency allocation, power, HBM, and NoC.
5. Mature-node and predictive testbenches with identical stimulus, metric
   definitions, PVT/load grids, failure injection, and acceptance criteria.
6. Floorplan/PDN/package sketch with ROM, compute, HBM, clock, repair, test, and
   thermal regions explicitly reserved.
7. A request list for the partner: device/model corners, BEOL/RC options,
   standard-cell and I/O libraries, ROM compiler availability/views, permitted
   customization, SRAM/ECC, HBM/PHY, EM/IR limits, package stack, DFM/yield,
   reliability, test, and cost/schedule.

## Decision rule

Public work can support the statement:

> "The architecture is logically consistent, its required capacity/traffic/
> compute/latency/energy are quantified, its custom-ROM method works in two
> mature public PDKs, and selected digital blocks route in a predictive
> advanced-node environment. These results justify—or fail to justify—a
> controlled target-PDK study."

It cannot support the statement:

> "OpenTallas is feasible in N7/N4 and outperforms a current GPU."

That stronger statement requires target-PDK custom-ROM and full-chip closure,
package/thermal/yield work, and a same-model measured comparison. Until then,
the correct product of the program is a quantified risk register and an
auditable set of necessary thresholds, not a projected speedup headline.
