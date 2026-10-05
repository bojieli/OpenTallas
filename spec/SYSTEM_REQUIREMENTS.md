# System requirements specification

**Document:** SPEC-REQ 1.0

**Status:** frozen for public-reference RTL

**Product-silicon authority:** none

## REQ-1.1 Normative source

`requirements.json` is the canonical requirement record. Each requirement has a
stable ID, priority, evidence basis, architectural allocation, implementation
allocation, and planned verification reference. This document defines the
interpretation and acceptance rules; the generated `TRACEABILITY.md` renders the
complete record for review.

The words *shall* and *must* are mandatory. *Should* identifies a planned feature
whose absence requires an owned waiver but does not invalidate the primary Flash
proof configuration. Product-level items dependent on a target foundry, OSAT,
model owner, production traces, or licensed IP remain external gates and cannot
be converted into passed requirements with analytical or open-PDK evidence.

## REQ-1.2 Evidence boundary

Requirements use the repository-wide evidence classes:

- measured — extracted from a pinned artifact with reproducible integrity data;
- published — stated in a pinned primary vendor/model source;
- derived — arithmetic or structural interpretation of published/measured data;
- assumed — an engineering hypothesis or budget;
- simulated — emitted by executable identified inputs;
- synthetic — generated stimulus, never a production trace.

An assumed requirement can be verified as “implemented to the assumption”; that
does not verify the physical assumption. For example, RTL can prove that its
counter model accepts a 100 TB/s service budget, but only target-node silicon can
establish that bandwidth.

The 160-GB/100-TB/s/8-TB/s values in the machine-readable specification are
public-reference proxy requirements. They are not the product-comparison
baseline. `docs/METHODOLOGY.md` and `results/iso-node/` control analytical product
questions; this package controls stable public RTL behavior.

## REQ-2.1 Program objective

The public program shall determine whether model-specific immutable-weight
silicon can retain a defensible latency, capacity, power, and partial-TCO case in
two non-mixed studies: N6/N7 ROM plus HBM2e-era interfaces versus A100 80 GB, and
N4-class ROM plus HBM3e versus B300. DeepSeek V4 Flash and Pro are evaluated at
8K, 32K, 200K, and 1M context. Kimi K3 remains a negative/stress control and
Qwen3-8B is a dense 8K control for the model-general/public-reference path. The
architecture shall remain
model-general within its declared limits; target profiles are compiler/image
inputs rather than hard-coded control decisions.

The independent iso-node analytical result controls product prioritization:

1. DeepSeek V4 Flash is the primary proof target.
2. DeepSeek V4 Pro is a capacity/pipeline stretch target; its stage count varies
   by technology envelope and is not fixed at six for product analysis.
3. Kimi K3 is a model-general traffic/stress configuration.
4. Qwen3-8B is a public-reference dense/GQA control at 8,192 context tokens; it is not a
   product target and has no attached speculative draft scenario.

The old brief's Pro B8 and B32 throughput claims are not requirements. They exceed
the current modeled resource ceilings and are retained only as audited hypotheses.

## REQ-2.2 Required operating matrix

The product-analysis matrix shall cover 8,192, 32,768, 200,000, and 1,000,000
resident context tokens for DeepSeek and batch per stage 1, 8, 32, and 64. The
model-general/public-reference verification matrix additionally retains Kimi at
200K/1M, Qwen3-8B at 8K, batch 128 stress, and capacity endpoints. These are
verification stimuli, not fixed product modes.

Ordinary decode and the legacy/public-reference assumed speculative midpoint are
distinct scenarios. The authoritative iso-node studies are ordinary decode only.
Speculative acceptance and draft cost remain assumed until production traces
replace them. The architecture supports up to fifteen candidates but does not
promise that speculation improves either ROM or GPU throughput.

## REQ-3.1 Requirement groups

The canonical IDs are organized as follows:

| Prefix | Scope |
|---|---|
| `SYS-FUNC` | image binding, decode, speculation, sessions, lifecycle |
| `SYS-PERF` | bandwidth, arithmetic, latency, counters, claim hygiene |
| `SYS-CAP` | ROM/HBM/stage capacity and architectural maxima |
| `SYS-NOC` | interleaving, static scheduling, credits, repair, determinism |
| `SYS-IF` | host, CSR, memory, link, telemetry, and handshake behavior |
| `SYS-NUM` | formats, rounding, order, exceptional values, DV surrogate |
| `SYS-RAS` | integrity, containment, repair, diagnostics, degradation |
| `SYS-PWR` | clocks, reset, power states, throttling, CDC |
| `SYS-DFT` | scan, BIST, access, coverage, inference interlock |
| `SYS-FW` | deterministic compiler, manifests, schedules, boot, ABI |
| `SYS-SEC` | immutable weights, identity boundary, trusted-host scope |
| `SYS-IMP` | RTL process, macro wrappers, static quality, reproducibility |
| `SYS-VER` | traceability, tool independence, campaigns, closure, synthesis gate |
| `SYS-EVD` | evidence labeling and replacement criteria |

## REQ-4.1 Acceptance semantics

A requirement can have these lifecycle states outside the frozen JSON record:

1. **Specified** — allocated and testable; no implementation evidence implied.
2. **Implemented** — RTL/software/artifact allocation exists and static checks pass.
3. **Verified** — all planned checks mapped to the requirement pass on the frozen
   baseline and required coverage is closed.
4. **Externally blocked** — the public implementation is complete but qualifying
   evidence requires production traces, licensed IP, PDK, foundry, OSAT, or silicon.
5. **Waived** — an authorized deviation names owner, risk, expiration, containment,
   and re-entry criterion. A waiver is not a pass.

The machine-readable baseline remains `specified` until implementation work adds
evidence links. No requirement may be marked verified solely because its document
was written or its happy-path simulation passed.

## REQ-4.2 Architecture gate

Entry to serious RTL requires all of the following:

- every must requirement has an architecture allocation and planned check;
- all externally visible records have exact widths and field semantics;
- numerical ordering, formats, exceptions, and the integer-surrogate boundary are
  frozen;
- clocks, resets, power states, CDC/RDC crossings, error containment, repair, DFT,
  firmware, floorplan, and verification closure are specified;
- machine checks pass with no unresolved normative placeholders;
- the review explicitly distinguishes public-reference closure from product PPA
  and signoff gaps;
- the specification commit is pushed before implementation RTL changes begin.

## REQ-4.3 Verification and synthesis gates

Verification is the long pole. The exact targets are in `verification.json` and
`VERIFICATION_PLAN.md`. Implementation synthesis is forbidden until the frozen
candidate has complete requirement evidence, zero open severity-1/2 defects, no
unexplained static findings, passing planned formal properties with non-vacuous
covers, closed must-bin functional coverage, reviewed code/toggle exclusions,
and an owned CDC/RDC and waiver record.

Open-PDK synthesis/physical results can verify methodology and topology only.
They cannot close target ROM, HBM, PLL, PHY, package, thermal, yield, reliability,
DFT, or commercial PPA requirements.

## REQ-5.1 External product gates

The following remain mandatory before product silicon even if every public
requirement passes:

- checkpoint lifetime commitment and change-control agreement with the model owner;
- measured production router, KV, speculative-acceptance, and A100/B300 serving traces;
- target-node ROM and standard-cell/macro characterization under NDA;
- OSAT HBM beachfront, stitched-wafer, power-delivery, cooling, test, and repair review;
- target-qualified security, DFT/ATPG, CDC/RDC, STA, SI, EM/IR, DRC/LVS/ERC,
  reliability, and final signoff;
- reticle test-silicon correlation before any wafer-scale product authorization.

The public architecture review may pass while every item above remains open. That
pass authorizes only the scoped digital reference implementation.
