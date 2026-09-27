# Qwen reduced matvec tile: registered-ingress slew closure

The clean source tree for this route is commit
`d9364a8e317f102c0cd4d078f92c306969fae189`. Run
`tools/run_hdc_matvec_memory_tile_ingress_slew60.sh` from that commit to
reproduce `physical.json`. The flow used the pinned OpenROAD-flow-scripts
container and ASAP7 RVT TT, 0.7 V, 0 °C view. The 1.5 ns clock, 0.2-period
input/output delays, 320 ps `set_max_transition`, fanout limit 32, 15% target
core utilization, 0.55 placement density, and 5 µm macro halos are unchanged
from the registered-ingress baseline. The only physical-flow change is
`SLEW_MARGIN` from 45% to 60%, asking placement repair to leave more margin
before final extraction. The synthesis netlist and SDC SHA256 values match the
baseline exactly:

- `1_2_yosys.v`: `a3303d16802374fb60501aae9b9efa3ea9dca71d2826f71a6da90306010a5dea`
- `constraint.sdc`: `761642202ad4bae185cdf17cdcdb66ef7a5494f91df58452e5cf817f9b5d88f6`

The registered-ingress RTL, including its one-cycle load-to-macro commit
latency, is unchanged. `tests/rtl/run_hdc_matvec_memory_tile_ingress.sh`
passed with Verilator 5.050: consecutive KV and vector loads committed as
specified and all eight exercised matvec output slots matched the direct-load
reference cycle by cycle. This is a focused differential operation, not a full
Qwen model run.

| Post-route extracted measure | 45% baseline | 60% route |
| --- | ---: | ---: |
| Engineering acceptance | NOT_MET | **PASS** |
| Setup WNS | +68.8685 ps | +83.7999 ps |
| Hold WNS | +20.7139 ps | +19.7745 ps |
| Max-slew / cap / fanout violations | 3 / 0 / 0 | **0 / 0 / 0** |
| Detailed-route DRC / antenna nets | 0 / 0 | 0 / 0 |
| Standard-cell area | 11,764 µm² | 12,217.6 µm² |
| Macro area | 63,846.9 µm² | 63,846.9 µm² |
| Routed wire length / vias | 1,056,791 µm / 747,546 | 1,061,015 µm / 770,839 |
| CTS hold buffers | 18,568 | 18,810 |
| Fmax derived from setup | 698.748 MHz | 706.115 MHz |

The stronger repair clears the three extracted slew violations observed in
the matched 45% run. It costs 453.6 µm² of standard-cell area, 4,224 µm of
routed wire, 23,293 vias, and 242 more hold buffers at CTS. The final report
has zero setup and hold violating paths, zero DRC errors, and zero antenna-
violating nets and pins. The GDS and DEF hashes are recorded in
`physical.json`; the retained netlists, final timing report, SDC, configuration,
DRC report, and metrics are under `physical_artifacts/`.

This is a **reduced W4/G2 compute and memory tile** with one ROM and four
SRAM proxy macros. The macro LEF and Liberty views are analytical compiler
models and their GDS has no internal layout. The address depth, lane count,
and bank coverage are smaller than the proposed full Qwen core. This pass
establishes an electrical closure point for the modeled tile only; it does
not establish manufacturability, full-core closure, target-node operation,
power, or token throughput. The 18,810 CTS hold buffers are a scaling risk.
