# Architecture review and gate disposition

**Review record:** AR-1.1

**Review date:** 2026-08-28 UTC

**Disposition:** PASS for the public-reference RTL/proxy scope; CONTINUE public
evidence acquisition; HOLD for selected product architecture and silicon.

## Scope reviewed

This review distinguishes three baselines that must not be conflated:

1. The authoritative product-comparison studies are N6/N7 ROM plus HBM2e-era
   interfaces versus A100 80 GB, and N4-class ROM plus HBM3e versus B300.
2. The fixed 160-GB/100-TB/s specification is a stable public-reference RTL,
   firmware, counter, fault, and verification proxy only.
3. Open-PDK implementation results validate methodology and digital structure;
   they cannot establish target ROM, HBM, NoC, clock, power, yield, or package PPA.

The review covers the pinned Flash/Pro model inventories and exact operator
accounting, `docs/METHODOLOGY.md`, both generated iso-node studies, the
hardware-independent Flash/Pro/Kimi traffic screen, this specification package,
and the explicit pre-NDA external-gate report.

## Evidence disposition

| Area | Disposition | Rationale |
|---|---|---|
| Model identity/storage | pass for analysis | Pinned official revisions; safetensors headers fully classified; decode/draft/resident roles separated. |
| Numerical/operator accounting | pass for analysis | Official FP8/MXFP4/BF16/FP32 roles and exact operator shapes; no `2 × active parameter` proxy. |
| Weight/KV accounting | pass for analysis | Immutable and mutable tiers are separate; batch/context traffic matrices and capacity identities are executable. |
| Iso-technology comparison | pass for conditional simulation | N7/A100 and N4/B300 do not mix node or HBM generation; ROM values remain extrapolated envelopes. |
| Communication/pipeline arithmetic | pass for conditional simulation | Two all-reduces/layer, topology/payload service, local capacity, batch×stage residence, and cross-stage terms are explicit. |
| Mechanical consistency | pass | 6,565 N7 and 3,921 leading-node checks close generated identities/ceilings only. |
| GPU application baseline | open external gate | Exact A100/B300 production runs, placement, collectives, KV counters, and acquisition economics are absent. |
| ROM/compute/NoC target PPA | open external gate | No target macro, simultaneous full-array power, format-specific P&R, or wafer NoC timing. |
| Package/power/yield/economics | open external gate | Stack pitch is only a first-order check; OSAT, SI/PI, thermal, repair, yield, and quotes are absent. |
| Public RTL interfaces/numeric/RAS/DFT | pass for continued public-reference work | Frozen behavioral contracts and planned checks exist; target macros and production signoff remain external. |
| Product authorization | hold | No deterministic envelope is selected or qualified as manufacturable silicon. |

## Decisions frozen

1. `docs/METHODOLOGY.md` and `results/iso-node/` control product comparisons.
2. The numeric values in `spec/budgets.json` control only stable public-proxy
   interface and verification behavior.
3. DeepSeek V4 Flash remains the smallest proof vehicle; Pro remains a capacity
   and pipeline stretch. This ordering is a measurement priority, not a product
   performance promise.
4. A100 is the N7 attribution comparator. B300 is the leading-node comparator.
   B200/B300-versus-N7 figures in legacy outputs are superseded.
5. DeepSeek routed work is MXFP4×FP8, not pure FP4. Exact operator formats remain
   mandatory through analysis, RTL interfaces, DV, and target qualification.
6. Mutable KV/state stays in SRAM/HBM. No ROM capacity or service claim includes
   KV.
7. Huawei Tau/韬 scaling is a co-design framework, not a numerical multiplier. Any
   vertical-ROM study is separate and must close links, power, thermals, yield,
   repair, and test.
8. Open-PDK and public RTL evidence cannot substitute for target-node signoff.

## Authorized work

Public interface/RTL/verification work, exact model/runtime profiling, reproducible
A100/B300 benchmarking, foundry/OSAT question preparation, macro/test-vehicle
planning, and bounded topology/PPA exploration may continue. No work product may
claim selected wafer capacity, frequency, power, yield, price, production token
rate, or quality until the corresponding external gate closes.

## External gates and phase transition

The owned gate list, minimum entry artifacts, and pass criteria are normative in
`results/PRE_NDA_READINESS.md`. Product architecture freeze requires a model-owner
checkpoint commitment, production router/KV/GPU evidence, target ROM and numeric
PPA, extracted NoC, feasible HBM package/PDN/cooling, yield/repair/test plans, and
regenerated conservative results. Reticle test silicon must correlate these models
before any wafer-scale product authorization.
