# OpenTallas architecture and specification baseline

Version 1.0 freezes the public-reference architecture that may be implemented
with non-NDA tools. It is a logical and digital-design contract, not a tapeout
release and not evidence that the assumed wafer-scale ROM, HBM beachfront,
frequency, power, yield, or package is manufacturable.

The baseline has three deliberately separate scopes:

1. **Product hypothesis.** A model-specific ROM pipeline with two stages for
   DeepSeek V4 Flash and six for DeepSeek V4 Pro under the analytical midpoint;
   Kimi K3 is an eleven-stage stress configuration and Qwen3-8B is a one-stage
   dense-control configuration, neither promoted to a product target.
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
- `CHANGE_CONTROL.md` — freeze, waiver, and compatibility policy
- `ARCHITECTURE_REVIEW.md` — gate disposition and open external risks

The executable analytical evidence remains under `results/`; the source and
assumption registers remain under `docs/`. Numerical claims in this directory
inherit those evidence labels and do not silently promote assumptions.
