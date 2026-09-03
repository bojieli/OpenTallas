# Qwen3-8B ROM hardware implementation plan

**Plan ID:** TA-QW-ROM-3.0

**Status:** active under frozen ABI 3.0; TA-A3-ARCH-0 is closed

**Model:** Qwen/Qwen3-8B at b968826d9c46dd6066d109eabc6255188de91218

**Mandatory context:** exactly 8,000 natural prompt tokens

**Physical topology:** one conventional reticle-bounded ROM accelerator chip
**Issue date:** 2026-08-29

## 1. Mission

This lane turns the retained Qwen3 functional ROM deployment into a
model-specific immutable-weight hardware design. The result may use a
Qwen-specialized datapath, physical partition, netlist, and mask set. It does
not need to run DeepSeek and must not be reported as the shared programmable
HBM/SRAM tensor accelerator.

The first release is exactly one conventional reticle-bounded ROM accelerator
chip/package with external HBM for live mutable buffers. It is the chip-versus-chip
peer of one conventional Qwen HBM/SRAM accelerator node. Wafer-scale or
multi-accelerator execution may not be credited to the Qwen comparison. If the
complete immutable payload cannot close the one-chip capacity, repair, power,
yield, or timing gates, the release fails and returns to architecture review
rather than silently becoming a wafer or cluster.

The Qwen ROM design must nevertheless preserve the common model semantics,
numeric contracts, live-buffer behavior, workload, EOS rules, evidence
schemas, and same-technology-view comparison boundary used by the Qwen HBM
deployment.

Completion means:

- every pinned Qwen weight bit has one immutable physical location and inverse
  proof;
- all 616 semantic nodes plus terminal completion execute causally from
  generated artifacts;
- no framework operator supplies model arithmetic;
- mutable KV is written directly to ordinary HBM/SRAM buffers and ordered by
  events plus the token-step fence;
- vocabulary selection and EOS are explicit;
- complete natural and agentic decoding produces legitimate output;
- representative complete programs execute through ROM RTL/co-simulation;
- the exact 8,000-token natural and separate stress workloads pass; and
- separate SKY130 and ASAP7 physical reports can be compared with the one-node
  Qwen HBM/SRAM reports in the matching technology view.

## 2. Retained baseline and exact limitations

### 2.1 What is already valuable

The current compiler/qwen3 path provides:

- a cryptographically pinned five-shard BF16 checkpoint and tokenizer;
- 399 tensors, 8,190,735,360 parameters, and 16,381,470,720 payload bytes;
- a complete 616-node, nine-operator semantic graph;
- a fixed 617-instruction Qwen semantic microprogram;
- complete immutable image emission and inverse reconstruction;
- a dependency-complete certified functional schedule;
- full 36-layer prefill/decode service execution;
- exact official differential results, EOS behavior, and token evidence;
- an exact 8,000-position functional boundary;
- six natural question runs through EOS; and
- two pinned bash-agent task runs with withheld tests.

These are strong source, payload, workload, and functional goldens.

### 2.2 What those results do not prove

The current service engine:

- memory-maps compiled image files but invokes PyTorch embedding, linear,
  normalization, attention, and vector operations;
- loads one logical layer image onto a CUDA device at a time;
- does not execute a ROM tile, microsequencer, physical NoC, SRAM bank, HBM
  controller, or RTL datapath;
- uses host-side greedy selection in its current end-to-end loop; and
- reports functional counters rather than implementation cycles.

The existing qwen3-stage-00 through qwen3-stage-35 image names mean one image per
model layer in that deployment compiler. They do not establish 36 physical
chips or stages. The older architecture document separately says Qwen payload
capacity fits one public-reference stage. This lane must resolve the terminology
and physical partition inside one conventional chip from capacity, bandwidth,
timing, power, and yield evidence. New artifacts will distinguish logical layer
image, ROM region, on-chip partition, and package device. A logical image file
or internal pipeline region is not a separate chip or cluster node.

## 3. Product boundary

### 3.1 Included in the first release

- batch-one prefill and ordinary greedy decode;
- exactly 8,000 accepted prompt tokens;
- Qwen BF16 dense projections with FP32 accumulation;
- RMSNorm and per-head RMSNorm;
- Q/K RoPE;
- GQA causal attention;
- BF16 residual and SiLU-gated MLP;
- immutable token embedding and vocabulary weights;
- HBM/SRAM KV buffers;
- on-device deterministic argmax, token append, and EOS;
- pinned chat and simple tool-use templates;
- fail-stop error completion, fresh-run reset, counters, and trace; and
- separate SKY130 implementation and ASAP7 predictive methodologies.

### 3.2 Separate extensions

- seeded or stochastic sampling;
- batch greater than one;
- contexts beyond the release session bound, which Phase F must qualify at no
  less than 8,256 positions; the separately retained 8,192 case is a legacy
  boundary fixture inside that release bound;
- speculative decoding;
- multimodal front ends;
- fleet/API scheduling; and
- production foundry/package signoff.

An extension cannot be silently credited to the first release.

## 4. Architecture

The candidate Qwen ROM hierarchy is:

~~~text
host and shared management/session boundary
                    |
Qwen ROM microprogram controller and generation loop
                    |
one conventional reticle-bounded Qwen ROM chip
                    |
+-------------------+---------------------+
| immutable BF16 ROM tensor regions       |
| BF16/FP32 tensor lanes                  |
| RMSNorm/RoPE/vector service             |
| GQA attention and HBM KV buffers        |
| SRAM activation/accumulator banks       |
| vocabulary reduction, argmax, and EOS   |
+-------------------+---------------------+
                    |
external HBM controller/PHY boundary for mutable buffers
~~~

### 4.1 Control reuse

The ROM design should reuse the reviewed ABI 3.0 management, host queue,
run, live-buffer, counter, trace, trap, and generation semantics
where compatible. It may use a ROM-specialized device program and static
schedule, but those artifacts must bind the same source graph/kernel operations
and expose equivalent results and buffer contents.

The control path may be smaller than the shared HBM accelerator because Qwen
has no expert route engine and weights are immutable. It still must implement
bounded loops, events, fences, errors, argmax, EOS, and complete program
retirement. A semantic microprogram executed by Python is not the hardware
controller.

### 4.2 Immutable weight service

Every weight tensor is compiled into:

- one-chip physical partition and ROM-region ownership;
- macro, bank, wordline, bit/nibble, and scale location as applicable;
- alignment, padding, integrity, spare, and repair allocation;
- logical row/tile mapping;
- fixed read latency class;
- expected payload and image hashes; and
- independent inverse reconstruction metadata.

No functional weight write path exists. Test/repair controls may select,
diagnose, or remap resources but cannot alter logical model content.

### 4.3 Mutable memory

ROM removes ordinary weight traffic from HBM; it does not remove mutable data.
HBM/SRAM holds:

- all 36 layer KV resources;
- token and output buffers;
- current valid extents;
- activation/attention spill explicitly required by the physical plan;
- run metadata where configured; and
- trace buffers.

Buffer capacity must include the exact 8,000-token prompt plus the frozen
256-token generation maximum, or at least 8,256 session positions. The
separately reported 8,192 case remains a legacy boundary fixture rather than
the release maximum. A failure ends the run, and its partially written buffers
are neither published as a successful result nor reused.

### 4.4 Compute specialization

The first Qwen datapath supports only the required dense BF16/GQA union:

- BF16 weight and activation decode;
- exact declared product and FP32 reduction ordering;
- final BF16 conversion;
- RMSNorm reciprocal-square-root contract;
- Q/K head normalization and RoPE;
- FP32 softmax reference boundary and BF16 attention output;
- residual addition and SiLU-gate multiply; and
- vocabulary reduction with deterministic tie handling.

DeepSeek FP8, MXFP4, expert routing, sparse attention, compressor, and mHC
hardware are not required in the Qwen ROM netlist.

## 5. Compiler plan

### 5.1 Semantic migration

The retained Qwen semantic graph and complete current differential remain the
source oracle. After the common production IR freezes, the lane:

1. exports the same graph into the common Model Graph contract;
2. verifies exact operation, tensor, live-buffer, source, and numeric coverage;
3. consumes the common Qwen Tensor Kernel IR;
4. lowers immutable logical weights to the Qwen ROM Physical Plan IR;
5. emits the Qwen ROM program and schedule;
6. compares every semantic boundary with the retained deployment; and
7. preserves any divergence as a failed migration artifact.

No ROM address, stage, or Qwen-specific hardware operation enters the neutral
graph/kernel.

### 5.2 Qwen ROM Physical Plan IR

The plan records:

- the mandatory one-chip topology and on-chip layer/region partition;
- ROM macro/region geometry and tensor placement;
- scale, padding, integrity, repair, and test regions;
- tensor-lane and reduction topology;
- activation/SRAM allocation and lifetime;
- HBM KV layout, direct writes, dependencies, and token-step fence;
- on-chip NoC and local schedule;
- program/event/queue mapping;
- vocabulary partition and argmax reduction;
- capacity, timing, power, repair, and yield assumptions; and
- exact expected operation, ROM, HBM, SRAM, link, and live-buffer counters.

Physical chip count is frozen at one. The compiler must prove that all payload,
padding, integrity, repair reserve, datapath, SRAM, control, HBM interface, power,
clock, and route requirements fit that conventional boundary. It may explore
internal pipeline and floorplan partitions, but it may not emit a second chip,
wafer fabric, or cluster schedule. The selected on-chip topology is versioned
and does not inherit the old image-file count.

### 5.3 Independent checks

An implementation-independent checker:

- rereads all 399 checkpoint tensors;
- reconstructs logical payloads from ROM images and repair maps;
- proves unique placement, bounds, padding, integrity, and no write path;
- reconstructs SRAM/HBM object and tensor-view legality;
- verifies schedule paths, conflicts, credits, and queue occupancy;
- derives program work and counters; and
- rejects missing tensors, aliasing, schedule conflicts, repair exhaustion, or
  incomplete producer/consumer and token-fence ordering.

## 6. Simulator plan

### 6.1 Functional ROM device

The artifact-only functional simulator consumes the new ROM deployment, not the
current Python graph builder. It implements:

- ROM reads and fixed logical payload reconstruction;
- Qwen tensor/vector/attention operations through qualified native kernels;
- the generated ROM microprogram and static schedule;
- SRAM/HBM live objects, faults, and counters;
- on-device vocabulary argmax and EOS control; and
- direct KV writes with token-boundary fence visibility.

It may reuse independently qualified arithmetic libraries. It may not invoke
PyTorch linear, attention, or model modules in an acceptance run.

### 6.2 Cycle model

The cycle model adds:

- ROM macro latency, bank availability, repair derate, and read energy;
- tensor/vector pipeline issue and stalls;
- SRAM ports, banking, arbitration, ECC, and occupancy;
- actual GQA KV HBM traffic and response timing;
- on-chip NoC transfers, credits, and HBM-interface traffic;
- microprogram/event/fence retirement;
- selection/EOS latency; and
- activity-derived counters for physical feedback.

Timing-only analytical replay is useful for screening but cannot replace the
data-bearing mandatory runs.

## 7. RTL plan

RTL is introduced after the generated program and functional device agree.
The sequence is:

1. immutable ROM wrapper, integrity, BIST, and no-write proof;
2. program fetch/control, loops, events, traps, counters, and completion;
3. tensor-lane plus SRAM boundary for one real Qwen tile;
4. RMSNorm, head RMSNorm, and RoPE;
5. GQA attention plus direct KV write and token-boundary fence;
6. residual, SiLU-gate, and final RMSNorm;
7. vocabulary partition/reduction, argmax, token append, and EOS;
8. one connected real checkpoint layer;
9. one complete chip program;
10. selected production-parameter on-chip pipeline correlation; and
11. reset, repair, fault, power, CDC/RDC, formal, and coverage closure.

Existing general ROM shell blocks may be reused only when their command,
session, schedule, integrity, and live-buffer behavior maps explicitly to the new
contract. Existing Qwen HBM ot_ta_* arithmetic slices remain independent
differential evidence, not automatic ROM RTL.

## 8. Workload and correctness plan

### 8.1 Short retained gates

Before long execution, reproduce:

- the retained 32-token official differential;
- all six natural question contexts and outputs;
- arithmetic, geography, science, computer-science, practical-advice, and
  reasoning EOS behavior;
- the hello-world and fix-permissions agent tasks; and
- exact prompt, token, live-buffer, layer, and logit evidence.

The current ROM results are goldens, not inputs. The new simulator must generate
them causally.

### 8.2 Mandatory Qwen 8K

Two separate 8,000-token runs are required:

1. a natural official-template context, followed by frozen greedy decode through
   first official EOS or the declared 256-token maximum; and
2. repeated-special-token stress, followed by the separately frozen decode
   length.

The natural run retains:

- rendered input context and exact 8,000 prompt IDs;
- every generated ID including EOS;
- raw and visible decoded text;
- tokenizer legality and round-trip evidence;
- complete KV/token buffer identities at the terminal fence;
- operation, ROM, HBM, SRAM, link, cycle, and energy-event counters; and
- comparison with the common Qwen reference and Qwen HBM result.

The stress run supports only capacity, boundary, and robustness claims.

The current ROM capability, source adapter, neutral IR, KV resources and RoPE
qualification still stop at 8,192 positions. They must be qualified and
regenerated at no less than 8,256 before this natural lane can satisfy the
declared maximum; reducing the natural cap to 192 would weaken the frozen
workload and is not an accepted closure route.

### 8.3 Agentic execution

Each model turn uses the pinned official Qwen tool template. The ROM device
generates until an allowed stop. A fail-closed parser accepts only the declared
bash command schema. The action runs in the frozen isolated environment, its
actual result becomes the next prompt, and withheld tests run only after model
termination. No action or token is preselected by the test harness.

## 9. SKY130 and ASAP7 physical plan

The Qwen ROM design is evaluated twice. SKY130 is the mature open 130-nm
implementation/verification baseline. ASAP7 is a separate academic predictive
7-nm projection, not production foundry signoff. Within each view, the Qwen ROM
chip uses the same PVT, clock-view, SRAM methodology, external HBM/link boundary,
workload, and evidence class as the one-node Qwen HBM design. Values are never
mixed across views.

Physical work proceeds through:

1. ROM bitcell/macro methodology and extracted slice;
2. representative tensor/vector/ROM tile;
3. SRAM/ROM/control integration;
4. one-chip floorplan, clock, route, congestion, IR/power, and thermal proxy;
5. repair, spare, BIST, DFT, and yield model;
6. conventional package and external-HBM boundary;
7. executed-activity power analysis; and
8. compiler/capability feedback and recompilation.

Public PDK proxies establish methodology, not production mask-ROM density,
yield, HBM package closure, or commercial signoff. Those gaps remain explicit.

## 10. Milestones

| Gate | Outcome | Exit evidence |
|---|---|---|
| QROM-A0 | architecture/control reuse accepted | TA-A3-ARCH-0 plus Qwen lane review |
| QROM-C1 | common-IR migration | exact coverage and retained-boundary equivalence |
| QROM-P2 | physical plan and images | all 399 tensors inverse-reconstruct; one-chip capacity/repair legal |
| QROM-F3 | artifact-only full short model | no framework fallback; exact logits/live buffers/tokens/EOS |
| QROM-S4 | data-bearing cycle model | causal ROM/HBM/SRAM/link timing and counters |
| QROM-R5 | representative ROM RTL | generated program, connected layer, live-buffer and selection correlation |
| QROM-N6 | natural and agent campaign | six prompts and two agent tasks reproduce accepted goldens |
| QROM-8K7 | exact mandatory context | natural 8K plus separate stress, legitimate text and EOS |
| QROM-PHY8-SKY | SKY130 physical convergence | one-chip characterized capability, recompile, rerun |
| QROM-PHY8-A7 | ASAP7 predictive convergence | separate academic one-chip projection, recompile, rerun, limitations |
| QROM-REL9 | Qwen ROM release | reproducible artifacts/evidence and governed Qwen ROM-versus-HBM report |

## 11. Agent ownership and handoff

The Qwen ROM agent owns only Qwen-specific ROM compiler, simulator, RTL,
physical, and result paths allocated by the master plan. It consumes common IR,
ABI/session, source, numeric, tokenizer, workload, and evidence contracts without
privately changing them.

Every handoff records:

- main baseline and delivered commit;
- common schema and Qwen source/checkpoint/workload identities;
- one-chip topology decision and physical-plan identity;
- ROM image, inverse report, program, and schedule identities;
- functional/cycle/RTL report identities;
- exact test and campaign scope;
- physical evidence class and external assumptions;
- current failure and first divergence; and
- next authorized gate.

## 12. Immediate next work after TA-A3-ARCH-0

The first Qwen ROM task is a migration audit, not a new full campaign:

1. classify each current Qwen graph, microcode, image, schedule, service, and
   report field against the common IR and ABI 3.0 architecture;
2. resolve logical-layer-image versus one-chip physical-partition terminology;
3. define the Qwen ROM Physical Plan IR and independent inverse obligations;
4. lower one embedding-through-first-RMSNorm slice without PyTorch execution;
5. compare exact retained values and counters; and
6. proceed to a connected layer only after that vertical slice passes.
