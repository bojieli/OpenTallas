# Adopted HDC compute plus memory tile: ASAP7 proxy gate

Base: `aa9eed5b7d311b118a5918dbbe94d03b91219cfe` (Claude Qwen integration).
This gate uses the adopted `rtl/hdc/ot_hdc_matvec.sv`, not an ABI3 `ot_a3_*`
vehicle. It is a deliberately reduced physical tile: `W=4`, `G=2`, `IL=8`,
`AW=16`, `NW=8` (eight BF16 multiply/FP32 accumulate lanes). The production
matvec defaults are `W=16`, `G=4`, `IL=8`, `AW=24`, `NW=16`.

## Reproduce

From this worktree root:

```sh
tools/run_hdc_matvec_memory_tile.sh --force
```

The script lists every RTL source and macro blackbox source. It invokes
`tools/run_abi3_physical.py` solely as the existing OpenROAD driver; the
design under test is entirely HDC. The result JSON hashes each source, macro
view, platform file, tool binary and container image. The archived
`physical_artifacts/constraint.sdc` and `config.mk` are the exact SDC and flow
configuration. Clock: ASAP7 RVT TT at 0.7 V, 0 °C, 1.5 ns target; all
non-clock inputs and outputs have 0.2-period delays, outputs have 3.898 fF
load, and max fanout is 32. Core utilization target 15%, place density 0.55,
macro halo 5 µm in both axes. No false path or multicycle exception was used.

## What is physically present

| Path | Implementation in this gate | Boundary of the evidence |
| --- | --- | --- |
| Weight | One 8192×266 ROM; 256 data bits decoded by the adopted SECDED decoder, low 128 bits feed the eight lanes | One 8192-word row, no Qwen weight image or full ROM row selection |
| KV | Two replicated 1024×256 1R1W SRAM macros; one synchronous read per HDC group, common whole-word load | Low 128 bits used per group; no full KV address range, BIST collar or repair control |
| Vector operand | Two replicated 1024×256 1R1W SRAM macros; one synchronous read per group, common whole-word load | Low 32 bits used per word; full multiport vector memory and result writes are outside this tile |
| Compute | Eight real `ot_hdc_matvec` lanes, split reduction, issue/address logic and result interface | No Qwen controller, HBM bridge, network, output SRAM or complete token run |

The wrapper in `rtl/hdc/physical/ot_hdc_matvec_memory_tile.sv` uses the same
one-cycle macro read contract as `ot_hdc_memsys`. Synthesis retained exactly
one ROM and four SRAM instances. The write ports make the replicated operand
banks loadable; this run did not load Qwen content. The 16-bit addresses are
truncated to 13 bits for the ROM and 10 bits for the SRAMs, so the tile is not
a full-depth memory system.

## Measured route

| Measure | Result |
| --- | ---: |
| Flow | Completed synthesis, placement, CTS, global and detailed route, extraction and final report |
| Standard-cell area | 10,502.6 µm² |
| Macro abstract area | 63,846.9 µm² across five macros |
| Core area | 476,340 µm²; final utilization 15.6085% |
| Standard cells after route | 111,142 |
| Routed wire / vias | 992,335 µm / 658,200 |
| Detailed-route DRC | 10,917 initially; 975, 438, 10, then **0** after repair |
| Antenna | 0 violating nets and pins |
| Extracted setup WNS / violations | +0.117703 ns / 0 |
| Extracted hold WNS / violations | +0.000681954 ns / 0 |
| Derived routed Fmax | 723.433 MHz at this proxy corner |
| Max slew / max capacitance / max fanout violations | **51 / 8 / 0** |
| Engineering acceptance | **NOT_MET**: signal-integrity violations remain |

The eight max-capacitance violations are on `g_bank[1].u_kv/rd_out` pins.
Their extracted loads are 48.98–57.91 fF against a 46.08 fF macro limit.
The worst slew is 465.13 ps against a 320 ps cell limit. This is the concrete
operand-delivery blocker even though setup, hold and DRC passed. The global
router ran extra congestion removal iterations, and detailed routing reduced
its DRC count to zero; no separate post-route congestion heatmap was retained.
The final DRC count is the available routability evidence, not a density or
yield signoff.

The first attempt at 25% core utilization is retained as
`attempt1_cts_failure.json`. It completed synthesis and macro placement but
stopped during CTS: hold repair left nine overlapping cells, and OpenROAD
reported `DPL-0033`. The 15% run avoided that legalization failure. This is
one floorplan comparison, not a sweep or proof that 15% is optimal.

## Collateral and inference limits

The ROM and SRAM LEF/Liberty views under `physical/asap7_memory_macros/` are
analytical compiler outputs calibrated from limited data. They are model-grade
abstracts, not silicon-qualified memory macros. The P&R configuration uses
`GDS_ALLOW_EMPTY` for these five macros, so the route has abstract macro
outlines and pins but **no macro-internal GDS**. The result does not establish
macro manufacturability, extracted internal memory parasitics, full-die
closure, target-node timing, power, or Qwen token throughput. It is an ASAP7
predictive proxy for this exact reduced compute-plus-operand path only.

Next physical action: reduce the SRAM output loads and slew violations in a
new matched route, then repeat with complete vector/output banking and the
production HDC lane count. The current routed gate must not be counted as
closed at 1.5 ns while those 59 electrical violations remain.
