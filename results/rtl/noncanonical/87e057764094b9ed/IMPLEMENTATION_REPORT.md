# Public implementation-proxy campaign

**Status:** PARTIAL_NONCANONICAL

Baseline commit: `6b5e6cf4580c709024a7365d25abe22d103be7b3`  
Run fingerprint: `87e057764094b9ed`  
Evidence class: `synthetic_open_pdk_proxy`

This is a Nangate45 45 nm typical-corner methodology and scaling proxy. It is not target-node or product signoff, does not establish 1 GHz, and excludes ROM/SRAM/HBM/PHY/package/analog macro PPA.

## Case summary

| Case | Mapping profile | Cells | Area proxy (um^2) | Sequential area | 100 MHz prelayout WNS (ns) | Architectural diagnostic WNS (ns) | Final setup WNS (ns) | Final hold WNS (ns) | Final DRC | Generic equiv | Mapped equiv | Postroute equiv | Physical |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| numeric_e1_l4 | default_delay_oriented | 999 | 1,265.096 | 191.520 | 6.067 | -0.683 | 5.480 | 0.463 | 0 | pass | pass | pass | pass |
| numeric_e1_l16 | default_delay_oriented | 4,372 | 4,942.014 | 191.520 | 4.206 | -2.544 | n/a | n/a | n/a | not_required_scaling_point | not_required_trusted_mapping_boundary | not_required | not_required_scaling_point |
| numeric_e4_l16 | default_delay_oriented | 19,183 | 21,412.734 | 191.520 | -3.068 | -9.818 | n/a | n/a | n/a | not_required_scaling_point | not_required_trusted_mapping_boundary | not_required | not_required_scaling_point |
| numeric_e16_l16 | bounded_structural_liberty_v1 | 145,186 | 165,780.776 | 191.520 | -46.684 | -53.434 | n/a | n/a | n/a | not_required_scaling_point | not_required_trusted_mapping_boundary | not_required | not_required_scaling_point |
| stage_reduced | default_delay_oriented | 32,815 | 74,695.726 | 41,251.280 | -38.257 | -46.807 | 4.318 | 0.043 | 0 | pass | not_required_trusted_mapping_boundary | pass | pass |
| stage_midpoint | default_delay_oriented | 41,718 | 95,008.816 | 52,142.384 | -20.900 | -29.450 | n/a | n/a | n/a | not_required_scaling_point | not_required_trusted_mapping_boundary | not_required | not_required_scaling_point |
| stage_default | default_delay_oriented | 70,985 | 154,729.274 | 75,246.080 | -61.661 | -70.211 | n/a | n/a | n/a | not_required_scaling_point | not_required_trusted_mapping_boundary | not_required | not_required_scaling_point |

## Gate disposition

- Required cases passing: 7/7.
- Generic equivalence closures: 2/2.
- Actual mapped-netlist equivalence closures: 1/1.
- ORFS synthesized-to-final equivalence closures: 2/2.
- Physical proxy completions: 2/2.
- All mapped cases contain zero internal/unmapped cells, latches, blackboxes, and structural errors; exact enumerated warnings are recorded in JSON.
- `numeric_e16_l16` alone uses the governed bounded structural Liberty mapping profile and a 300-second outer timeout. Its area, cell count, and timing are scaling diagnostics and are not directly QoR-comparable to the default delay-oriented cases.
- Required physical cases close final setup, hold, electrical, max-fanout, flow-error, connectivity, equivalence, and detailed-route DRC proxy gates.
- The 100 MHz prelayout setup check gates only the small arithmetic representative; stage-control timing closes on the buffered postroute proxy. Architectural-frequency timing is diagnostic only.
- Unrouted minimum-delay and reset recovery/removal results remain diagnostic until clock-tree/routing and target integration; no broad reset waiver is claimed.
- Vectorless OpenSTA power is illustrative library scaling only and reports an ideal clock network; it is not a product power estimate.
- OpenROAD vectorless power and default-grid IR drop are recorded as non-gating diagnostics and are not product power-integrity evidence.

## Evidence boundary and open obligations

Public Nangate45 45 nm typical-corner synthesis, static timing, logical equivalence, and place/CTS/route methodology proxies. Results are not target-node, ROM/SRAM/HBM/PHY, clock-tree, package, power-integrity, reliability, manufacturing, or product-silicon signoff and cannot substantiate the 1 GHz architecture target.

- immutable weight ROM arrays, sense amplifiers, repair, and characterization
- qualified SRAM/register-file macros
- HBM controller, PHY, stack, package beachfront, and signal integrity
- stage-link PHY and package channels
- PLL, clock macros, IO/ESD, power grid, thermal sensors, and analog monitors
- scan compression, ATPG, MBIST, fuse, and production test macros

The machine-readable result retains exact inputs, tool and library hashes, parameters, warning inventory, constraints, timing checks, proof-point counts, physical metrics, and hashes for all local raw artifacts.
