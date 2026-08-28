# Public pre-NDA readiness and external-gate report

**As of:** 2026-08-28 UTC  
**Program disposition:** ready for evidence acquisition, compiler implementation,
and partner feasibility discussions; not ready for executable-architecture
validation, product architecture freeze, or silicon authorization.

## Readiness summary

| Gate | Status | What the status authorizes |
|---|---|---|
| Evidence-first analytical baseline | **Pass** | Use the two iso-node studies to prioritize measurements and ask quantitative questions. |
| Public model/format/workload accounting | **Pass** | Quote released bytes, operator counts, and traffic equations with their stated scope. |
| Public digital/physical-reference methodology | **Conditional pass** | Continue interface, RTL, verification, compact-array extraction, and statistical-method work; do not infer target PPA. |
| `COMP-01` executable model mapping | **Open** | Implement complete payload ingestion, semantic IR, physical images, microcode, independently certified schedules, artifact-driven service execution, and model differential evidence before interpreting system performance as validated. |
| Model-owner engagement package | **Ready to send** | Request checkpoint-lifetime, router/KV, quality, and serving evidence. |
| Foundry/ROM macro feasibility | **Open** | No target density, timing, power, sense-margin, yield, or repair claim. |
| OSAT/HBM/wafer package feasibility | **Open** | No stack-count, beachfront, SI/PI, thermal, or known-good-die claim. |
| Target format-specific PPA | **Open** | No wafer compute roof or frequency claim. |
| Product architecture freeze | **Blocked by `COMP-01` and external evidence** | Keep all conservative/central/aggressive profiles as scenarios. |
| Test chip / tapeout | **Not authorized** | Requires the entry artifacts and approvals below. |
| Production performance/economics | **Not authorized** | No price, margin, production tok/s, yield, or full-TCO claim. |

“Pass” above means the public arithmetic/artifact gate passed. It never promotes
an assumed physical input to measured evidence.

`COMP-01` is an internal architecture-correctness gate, not an external foundry
gate. The current repository inventories checkpoint headers and counts tensor
contractions, but does not compile complete payloads into physical ROM/HBM
artifacts or execute the declared model through an operator-complete service
engine. `docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md` defines the implementation,
independence, vertical-slice, full-model, and claim-reentry criteria. Until that
gate closes, all analytical speedups are conditional break-even scenarios.

The first `COMP-01` plumbing slice is now implemented under `compiler/` and
`runtime/`: a strict exact-integer fixture emits deterministic ROM and microcode
artifacts, passes an independently implemented inverse-image check, executes in
the artifact-only software service engine, matches an independent reference and
known answer, and reconciles functional counters exactly. This closes only a
unit-test fixture. It does not ingest a real checkpoint, implement DeepSeek
operators or target formats, emit certified physical schedules, model hardware
cycles, or drive RTL, so `COMP-01` remains open.

The governed open-library implementation-methodology campaign is now closed from
an isolated clean baseline. All seven arithmetic and stage-control cases pass
mapped synthesis, structural checks, and complete proxy STA coverage; both
generic-equivalence representatives pass, the actual mapped arithmetic
representative passes equivalence, and both physical representatives pass
place/CTS/route/extraction, final setup/hold/electrical/fanout/antenna/DRC gates,
connectivity audits, and synthesized-to-final sequential equivalence. The exact
large arithmetic scaling point uses a reviewed, 300-second bounded structural
Liberty mapping recipe and is explicitly not QoR-comparable to default-profile
cases. The canonical fingerprint is `87e057764094b9ed`; 386 referenced artifacts
were hash-rechecked after clean-run promotion. Exact evidence and limitations are
in `results/rtl/IMPLEMENTATION_STATUS.md`, `results/rtl/IMPLEMENTATION_REPORT.md`,
and `results/rtl/CLEAN_BASELINE_REPLAY.md`. This closes a public Nangate45
methodology proxy only—not target numerical PPA, macros, a full chip/wafer, or
product signoff.

The first custom-transistor physical-methodology gate is now closed locally on
the exact locked SKY130A public PDK: zero Magic DRC errors, a unique Netgen LVS
match for ten MOS devices/fifteen nets/ten ports, exactly one physical via1
programming delta, capacitance extraction, and 33/33 deterministic extracted
PVT/load cases. A separate mismatch-only nominal-TT campaign passes 256/256
fixed-seed local samples, reproduces the repeated seed exactly, and detects
cross-seed electrical variation. The governed records are
`results/spice/sky130_physical/physical.json` and
`results/spice/sky130_extracted_pvt.json`, plus
`results/spice/sky130_extracted_mismatch.json`. A complementary integrated
full-RC campaign preserves 630 explicit resistor elements and 269 capacitors in
each of five interconnect styles, passes all five fresh-directory semantic
replays, and closes 165/165 deterministic local electrical cases. Its governed
record is `results/spice/sky130_resistance/resistance.json`.

The independent IHP replication chain is now closed locally. The
exact public SG13G2 `v0.3.0` checkout is recursively content-locked and remains
pristine; all four official ngspice Verilog-A modules compile twice
byte-identically for `target_cpu=generic`; and the official 1.2-V NMOS/PMOS TT
DC/transient smoke deck passes. The independently implemented IHP slice then
closes zero-error full DRC, unique ten-port LVS, ten MOS devices/fifteen nets,
the exact 6/5 programming-via count, base capacitance PEX, and 33/33 official-
PSP103 deterministic PVT/load cases. Its five public detailed-RC styles each
retain 10 MOS, 41 resistor, and 68 capacitor elements plus all six extracted
NMOS body-resistance paths; 5/5 semantic replays and 165/165 electrical cases
pass. Governed records are under `results/spice/ihp_device_smoke/`,
`results/spice/ihp_sg13g2_physical/`,
`results/spice/ihp_sg13g2_extracted_pvt.json`, and
`results/spice/ihp_sg13g2_resistance/`. These local public-PDK results still do
not close compact/full-array extraction, statistical/silicon yield,
target-foundry correlation, EXT-06/07/14, or any N7/N4 or product claim.

## Public analytical gates completed

| ID | Completed artifact/check | Evidence class | Scope boundary |
|---|---|---|---|
| ANA-01 | Pinned Flash/Pro configs, model cards, safetensors indices, and exact tensor-role inventories | measured/published | Metadata integrity and storage only; no checkpoint execution or quality claim. |
| ANA-02 | Official DeepSeek numerical roles retained tensor/operator-wise | published/derived | Hardware accuracy and achievable kernel rate remain unmeasured. |
| ANA-03 | Exact tensor-contraction shape inventory plus selected source-derived auxiliary counts for sparse indexing, attention, mHC, normalization, nonlinear, top-k, Sinkhorn, and LM head paths | derived | Tensor buckets receive format roofs; auxiliary categories receive break-even rate requirements only. The auxiliary ledger is not operator-complete and contributes no modeled service time or energy. |
| ANA-04 | Immutable weight versus mutable KV/state separation and no capacity double counting | architectural/derived | Assumes the proposed physical tiering can be implemented. |
| ANA-05 | N7/HBM2e/A100 and N4/HBM3e/B300 studies generated independently | derived/simulated | ROM target values remain extrapolated envelopes. |
| ANA-06 | Exact local stage packing, batch×stage residence, pipeline interval/latency identities, and capacity endpoints | derived/simulated | No measured pipeline imbalance or failure-domain behavior. |
| ANA-07 | Two all-reduces/layer and topology/payload-derived wafer service | derived/simulated | No placed-and-routed target NoC timing. |
| ANA-08 | Mechanical audit: 12,091 N7 checks and 7,881 leading-node checks pass | generated | Arithmetic identities, configured tensor ceilings, and auxiliary break-even identities only; auxiliary service remains unpriced. |
| ANA-09 | B300 undisclosed FP32 roof swept from 19.5 to 180 TOP/s | assumed sensitivity | No headline 200K change; this does not validate other B300 runtime inputs. |
| ANA-10 | Hardware-independent Flash/Pro/Kimi weight/KV matrices across context and batch | derived | Traffic screen only, not a speedup claim. |
| ANA-11 | Huawei Tau/韬 and vertical-integration boundary documented | published/derived | No generic Tau or 1.4-nm-equivalent multiplier is used. |
| PHY-01 | Exact SKY130A/open_pdks tree, tool, generator, schematic, deck, and output identities locked and hash-verified | measured from installed public artifacts | Establishes reproducibility only; SKY130 is not an N7/N4 proxy. |
| PHY-02 | Two-column via-programmed ROM slice passes zero-error Magic DRC and unique Netgen LVS including all ports | open-PDK DRC/LVS | The deliberately roomy slice proves local legal geometry/connectivity, not compact macro density or target-foundry late-via availability. |
| PHY-03 | Physical programming invariant and base capacitance extraction audited | extracted from layout | Exactly one via1 delta; 59 capacitance elements. This base PEX is intentionally capacitance-only. |
| PHY-04 | Exact archived PEX slice passes 33/33 deterministic SS/TT/FF, voltage, temperature, and output-load cases | simulated from open-PDK extraction | Deterministic PVT only; no target-node correlation or silicon claim. |
| PHY-05 | Exact archived PEX slice passes 256/256 mismatch-only fixed-seed nominal-TT cases, exact same-seed replay, and cross-seed variation detection | simulated from public per-instance mismatch equations | Finite public-model sensitivity only; not silicon yield, random-defect coverage, sign-off Monte Carlo, target-node correlation, or silicon. |
| PHY-06 | Integrated full-RC extraction under five declared Magic styles passes exact semantic replay and 33 deterministic electrical cases per style | extracted/simulated from the archived public-PDK geometry | 5/5 replays and 165/165 cases pass; each style has 10 MOS, 630 R, and 269 C elements. This is local full-RC-versus-capacitance-only evidence, not compact/full-array RC, target-node timing, or silicon. |
| PHY-07 | Exact IHP SG13G2 public release, model compiler and OSDI simulator path are locked and replayed before independent layout work | measured/compiled/simulated from public artifacts | 5,121 payload entries and five gitlinks verify pristine; 4/4 official models compile twice byte-identically; official 1.2-V NMOS/PMOS DC/transient smoke passes. This row is the prerequisite; PHY-08 through PHY-10 record the physical replication. |
| PHY-08 | Independently implemented IHP controlled-via slice passes zero-error full DRC, unique port-complete LVS, programming-via audit, and capacitance extraction | independent public-PDK DRC/LVS/PEX | 10 MOS, 15 nets, 10 ports, exact 6-versus-5 via1 count, and 59 capacitance elements. The roomy local slice is not a compact density macro or target-foundry evidence. |
| PHY-09 | Exact archived IHP PEX passes the governed official-PSP103 deterministic PVT/load matrix | simulated from independent public-PDK extraction | 33/33 cases pass across SS/TT/FF, voltage, temperature, and load; mismatch/yield, compact-array and target-node claims remain open. |
| PHY-10 | IHP detailed-RC extraction under all five public Magic styles passes exact replay, graph invariants and 33 electrical cases per style | extracted/simulated from archived IHP geometry | 5/5 replays and 165/165 cases pass; each style has 10 MOS, 41 R and 68 C elements, and all six NMOS body paths reach ground. This is local full-RC-versus-capacitance-only evidence, not compact/full-array RC, target-node timing, yield, or silicon. |
| RTL-IMPL-01 | Full seven-case public synthesis/STA/equivalence/physical-proxy campaign reproduced from an isolated clean source baseline | synthetic open-library implementation proxy | 7/7 cases, 2/2 generic equivalence, 1/1 actual mapped equivalence, 2/2 physical proxies, and 2/2 post-route equivalence pass; 386 result-referenced artifacts verify after archival. Nangate45 results are not target-node or product PPA. |

Authoritative artifacts:

- `docs/METHODOLOGY.md`
- `docs/SOURCES.md`
- `docs/ASSUMPTIONS.md`
- `results/model-traffic/REPORT.md`
- `results/iso-node/n7_architecture_attribution/REPORT.md`
- `results/iso-node/leading_node_market/REPORT.md`
- `results/spice/sky130_physical/REPORT.md`
- `results/spice/SKY130_EXTRACTED_PVT_REPORT.md`
- `results/spice/SKY130_EXTRACTED_MISMATCH_REPORT.md`
- `results/spice/sky130_resistance/REPORT.md`
- `results/spice/ihp_device_smoke/REPORT.md`
- `results/spice/ihp_sg13g2_physical/REPORT.md`
- `results/spice/IHP_SG13G2_EXTRACTED_PVT_REPORT.md`
- `results/spice/ihp_sg13g2_resistance/REPORT.md`
- `results/rtl/IMPLEMENTATION_REPORT.md`
- `results/rtl/CLEAN_BASELINE_REPLAY.md`
- `results/DECISION.md`

## External evidence gates

| ID | Gate and owner | Minimum entry artifact | Pass criterion | Why it can change the answer |
|---|---|---|---|---|
| EXT-01 | Checkpoint lifetime — model owner/business | Signed model revision, tensor manifest hash, supported service life, update/recall and security policy | A specific image can remain economically serviceable through amortization, or a re-personalization plan is accepted | Mask ROM is model-specific; a short checkpoint life can dominate every silicon advantage. |
| EXT-02 | Production routing — model owner/runtime | Per-layer expert IDs/counts over representative production prompts, including temporal correlation and tails | Trace-driven placement/load-balance result fits power, bandwidth, and tail-latency budgets | Uniform routing can understate hotspots and repair/placement interactions. |
| EXT-03 | KV implementation — model owner/runtime | Allocator layout plus HBM read/write counters by layer, context, batch, prefix hit, and kernel | Measured bytes including rereads, metadata, alignment, and writeback remain inside mutable-memory envelopes | The ROM benefit is set by weight service relative to mutable KV service. |
| EXT-04 | GPU baseline — GPU/runtime lab | Reproducible A100/B300 runs for exact revisions at 8K/32K/200K/1M and B1/B8/B32/B64; power and topology logs | Throughput, latency distribution, HBM, compute, collective, and power counters are archived and independently reproduced | Present GPU efficiencies, expert engagement, collectives, and prices are assumptions. |
| EXT-05 | Numerical quality — model owner/numerics | Golden logits/tasks and target implementation results for every format, rounding, scale, accumulation, and exception rule | Agreed quality/non-regression thresholds pass across long-context and routing tests | Storage compatibility does not prove inference quality. |
| EXT-06 | ROM bitcell/macro — foundry/memory IP | N7 and intended leading-node macro reports with area, organization, read timing, sense margin, PVT/aging, energy, leakage, ECC, repair, and DFT | Characterized usable density and sustained read service close at required corners and duty cycle | Capacity and weight service are currently extrapolated from unlike public macros. |
| EXT-07 | Simultaneous full-array activity — foundry/physical | Vector/activity-driven current, IR/noise, thermal and timing analysis at representative expert selections | Concurrent macro activation meets timing and reliability without violating power/cooling | Summing local macro bandwidth can overstate whole-wafer service by orders of magnitude. |
| EXT-08 | Format-specific compute PPA — digital/foundry | Synthesized and placed MXFP4×FP8, FP8×FP8, BF16, FP4-index, FP32, reduction, scale-delivery, and SRAM paths | Achieved throughput, area, energy, and timing replace WSE/GC200 fraction envelopes | Compute binds many N7 central/high-batch points. |
| EXT-09 | Wafer NoC/clock — physical design | Reticle/tile floorplan, wire classes, repeaters, bisection, clocks, skew, barriers, contention and repair routes | Extracted timing and power meet both all-reduces/layer over PVT and degraded topologies | Leading-node central points are often collective-bound. |
| EXT-10 | HBM/package beachfront — OSAT/HBM vendor | Stack floorplan, channel/PHY assignment, escape/routing, SI/PI, interposer/substrate, keep-outs, assembly flow and stack availability | Required capacity/bandwidth fits perimeter, power, thermals, yield, test, and mechanical rules | KV remains in HBM; stack totals in the model are only pitch checks. |
| EXT-11 | PDN/cooling/reliability — package/system/foundry | Transient workload power, EM/IR, regulator/decap, hotspot, thermal resistance, coolant, cycling and lifetime analysis | Sustained service meets junction, voltage, EM, mechanical and facility limits with margin | More tiers/arrays can add capacity while reducing usable bandwidth through heat. |
| EXT-12 | Yield/repair/failure domains — foundry/DFT | Reticle defect distribution, stitching, known-good-region test, redundancy, repair compiler, spares and field-failure model | Productive yield, degraded modes, test time, and fleet availability meet economic targets | Wafer-scale yield and repair can dominate unit count, power, latency, and cost. |
| EXT-13 | Economics/supply — foundry/OSAT/HBM/finance | Volume-specific NRE, masks, wafers, HBM, assembly, test, yield, cooling, spares, financing and service quotes | Full TCO and schedule remain competitive under conservative measured performance | Current $100k wafer/$100M NRE and GPU acquisition values are proxies. |
| EXT-14 | Reticle test silicon — program | Signed-off macro/compute/NoC test-vehicle specification with correlation plan | Silicon measurements correlate to pre-silicon models before wafer-scale commitment | Public/open-PDK proxies cannot validate target-node analog/physical behavior. |

## Partner question packages

### Model owner

Request the exact checkpoint-freeze horizon, serving/quality acceptance suite,
router traces, KV layout/counters, draft/speculation traces, expected request
context/batch distributions, prefix-cache behavior, and upgrade policy. Ask for
permission to embed the immutable tensor image and scales in mask data.

### Foundry and memory-IP provider

Provide both iso-node targets, array organization, read duty cycle, total enabled
bitlines/wordlines, required numerical paths, repair targets, and current/power
waveforms. Request measured or qualified macro bands rather than a single density
number. Separate planar ROM, metal ROM, monolithic tiers, and bonded tiers.

### OSAT, HBM vendor, and package partner

Provide the 16/32/48 HBM2e and 24/40/56 HBM3e scenario matrices as questions,
not requirements. Ask for feasible stack count, pitch, beachfront escape, link
lengths, interposer/substrate technology, power, cooling, assembly/test, stack
capacity/bin availability, yield, and cost. A lower feasible stack count must feed
back into KV capacity and service before any architecture choice.

### GPU/runtime lab

Use exact model revisions and deployment representations. Record per-user and
aggregate token rate, latency percentiles, HBM capacity/read/write, SM/Tensor-Core
activity, NVLink traffic, collective time, power, clocks, expert placement, and
software versions. Report same active batch and same resident-session comparisons.

## Tau/3-D optional workstream

Huawei's Tau Scaling Law can motivate delay reduction and cross-layer co-design,
but it is not a stack-height equation. If a partner proposes 3-D ROM, create a
third study rather than modifying either 2-D iso-node baseline. It must expose:

- integration type, tier/node, usable tier count and area;
- bond pitch, known-good-tier/bond yield, test and repair;
- vertical-link bandwidth, latency, energy and failure modes;
- shared/replicated decoders, sense amplifiers, compute, NoC and power delivery;
- per-tier read current, thermal resistance, hotspots and cooling;
- HBM/package interaction and total unit economics.

The service bound remains the minimum of weight, KV, compute, horizontal NoC,
vertical links, and cooling. Capacity alone is not throughput.

## Phase transition criteria

The program may enter a target-node reticle test-chip design only after EXT-01,
EXT-02/03, a reproducible GPU baseline, preliminary EXT-05/06/08, an owned
package/power/yield plan, and a passing real-model `COMP-01` vertical slice exist.
A wafer-scale product architecture may freeze only after full `COMP-01` closure,
correlated reticle silicon closes ROM, compute, NoC, repair, and thermal models,
and the conservative regenerated study clears product latency, capacity, quality,
availability, schedule, and full-TCO thresholds.
