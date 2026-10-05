# OpenTallas architecture and specification baseline

[Project home](../README.md) · [Documentation](../docs/README.md) ·
[Contributing](../CONTRIBUTING.md)

Version 1.1 retains the version-1.0 public-reference architecture and adds the
deterministic DeepSeek V4 `HC_PRE` numeric contract required by the executable
compiler recovery program. The package may be implemented with non-NDA tools.
It is a logical and digital-design contract, not the current
analytical product envelope, a tapeout release, or evidence that wafer-scale ROM,
HBM beachfront, frequency, power, yield, or packaging is manufacturable.

The specification is also not evidence that its complete compiler and
microprogram contracts are implemented. A deterministic exact-integer fixture in
`../compiler/` and `../runtime/` now exercises the first generated-artifact path,
but it is not a real checkpoint, transformer layer, target numeric
implementation, physical schedule, or RTL execution. The
`../docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md` governs the remaining work required
to close `COMP-01`: complete checkpoint ingestion, executable model semantics,
physical image generation, artifact-driven service execution, independent
checking, and end-to-end model differential evidence.

Product-comparison authority belongs to `docs/METHODOLOGY.md`,
`configs/hardware/technology_inputs.json`, and `results/iso-node/`. The fixed
160-GB/100-TB/s values in this specification are retained only as a stable RTL and
verification interface proxy. They must not override, calibrate, or be averaged
with the N7/A100 or N4/B300 envelopes.

The baseline has three deliberately separate scopes:

1. **Public-reference proxy.** A model-specific ROM pipeline using the legacy
   two-stage Flash, six-stage Pro, eleven-stage Kimi stress, and one-stage Qwen
   dense-control images. These fixed partitions keep RTL/firmware regressions
   stable but are not current product stage counts or performance targets.
2. **Public-reference implementation.** Parameterized control, tile, static-NoC,
   repair, integrity, and numerical datapaths that can be linted, simulated,
   formally checked, synthesized, and physically proxied with public tools.
3. **Black-box boundaries.** Foundry ROM, HBM PHY/controller hard macros,
   high-speed stage links, PLLs, sensors, eFuse/OTP, security roots, scan
   compression, and package/thermal structures. Their interfaces and budgets are
   frozen here; their implementation and signoff remain external gates.

Normative prose and machine-readable records are both required. The canonical
inventory is `manifest.json`; `tools/check_spec.py` rejects missing documents,
duplicate IDs, untraced must-have requirements, inconsistent widths, invalid
budgets, or unresolved normative placeholders. `TRACEABILITY.md` is generated
from the canonical requirement and verification records.

No serious RTL change is permitted until this package is reviewed, committed,
and pushed. After that gate, any externally visible behavior change requires a
versioned specification change and a traceability update in the same or earlier
commit.

## Document map

- `SYSTEM_REQUIREMENTS.md` — testable system requirements and evidence boundary
- `ARCHITECTURE.md` — system/stage/reticle/tile hierarchy and execution model
- `MICROARCHITECTURE.md` — block contracts, pipelines, buffering, and state
- `INTERFACES.md` — host, memory, NoC, link, CSR, telemetry, debug, and test ICD
- `NUMERICS.md` — canonical formats, ordering, rounding, saturation, and errors
- `CLOCK_RESET_POWER.md` — domains, crossings, sequencing, and power states
- `RAS_REPAIR_DFT.md` — integrity, containment, repair, diagnostics, and DFT
- `FIRMWARE_COMPILER.md` — image, schedule, ABI, boot, and reproducibility contract
- `FLOORPLAN_PPA.md` — explicit product hypotheses and public-proxy budgets
- `VERIFICATION_PLAN.md` — environments, methods, coverage, and closure criteria
- `fault_campaign.json` — exact public RTL fault sites, expected containment, recovery, and external gates
- `implementation_proxy.json` — pinned synthesis, STA, equivalence, and physical-proxy cases and gates
- `CHANGE_CONTROL.md` — freeze, waiver, and compatibility policy
- `ARCHITECTURE_REVIEW.md` — gate disposition and open external risks
- `../docs/EXECUTABLE_SYSTEM_RECOVERY_PLAN.md` — executable compiler, runtime,
  RTL-integration, validation, and claim-reentry plan

The executable analytical evidence remains under `results/`; the source,
methodology, and assumption registers remain under `docs/`. If a numerical proxy
here conflicts with an iso-node study, the proxy controls only public-reference
interface testing and the iso-node study controls product comparison. Numerical
claims in this directory never promote assumptions to silicon facts.

The current public implementation-methodology result is the clean-baseline
fingerprint `87e057764094b9ed` in `../results/rtl/IMPLEMENTATION_REPORT.md`, with
the isolated-source replay audit in
`../results/rtl/CLEAN_BASELINE_REPLAY.md`. It is a Nangate45 proxy and does not
close any target-node or product-silicon gate.
