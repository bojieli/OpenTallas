# Registered load ingress for the adopted HDC memory tile

Source-pinned RTL and test commit: `b2f3716312f223e1ea52d5c68f56ba653107e9c7`.
This is the same reduced `ot_hdc_matvec` W4/G2 compute plus one ROM and four
SRAM proxy macros as the direct-load baseline in the sibling directory. The
adopted `ot_hdc_matvec` RTL is unchanged. Only the physical wrapper adds
registers on the KV and vector SRAM load enables, addresses and 256-bit data.
Each ingress accepts a load on a rising edge; both replicated SRAM banks write
it on the **next** rising edge, and `*_load_commit` rises after that write edge.
A producer must wait for commit before reading the loaded address. Both
ingresses accept one load per cycle, including consecutive writes.

`tests/rtl/run_hdc_matvec_memory_tile_ingress.sh` uses Verilator 5.050 to
compare the registered tile against the direct-load tile pinned at `4ca61a20`.
It sends consecutive distinct KV and vector loads, checks both commit pulses,
waits for the ingress to drain, then issues a KV matvec. All eight output slots
and the complete visible result/control bundle matched cycle by cycle through
idle, with no fault. This checks the extra load latency and the unchanged
compute behavior for the exercised operation; it is not a full Qwen model
simulation. The production load protocol must account for this new latency.

## Physical route

Reproduce from the commit above with
`tools/run_hdc_matvec_memory_tile_ingress.sh --max-transition-ns --slew-margin-percent 45 --force`.
The record `physical.json` hashes the clean source tree, exact RTL and macro
views, toolchain and retained artifacts. It uses ASAP7 RVT TT, 0.7 V, 0 °C,
1.5 ns clock, 0.2-period input/output delay, explicit 0.32 ns extracted
max-transition limit, 45% slew repair margin, fanout limit 32, 15% target core
utilization, placement density 0.55 and 5 µm macro halos. No false path or
multicycle exception was added.

| Measure | Registered ingress | Direct-load baseline |
| --- | ---: | ---: |
| Full flow completed | yes | yes |
| Setup WNS | +68.8685 ps | +97.8839 ps |
| Hold WNS | +20.7139 ps | +6.56275 ps |
| Detailed-route DRC / antenna nets | 0 / 0 | 0 / 0 |
| Max slew / cap / fanout violations | **3 / 0 / 0** | **4 / 0 / 0** |
| Standard-cell area | 11,764 µm² | 11,012.8 µm² |
| Macro area | 63,846.9 µm² | 63,846.9 µm² |
| Routed wire / vias | 1,056,791 µm / 747,546 | 982,473 µm / 691,545 |
| Derived Fmax from setup | 698.748 MHz | 713.208 MHz |
| Engineering acceptance | **NOT_MET** | **NOT_MET** |

The three remaining extracted slew violations against 320 ps are
`mx_data[20]` at 332.27 ps, `g_bank[1].u_x/wd_in[120]` at 328.05 ps, and
`mx_data[104]` at 320.75 ps. The physical result therefore remains NOT_MET.
The changed violating pins and 4-to-3 count do not prove a general electrical
improvement: register insertion changes placement and repair topology. CTS
inserted 18,568 hold buffers in this route; its worst reported min path before
routing was the external `go` input to `u_me.ov_mark[0]` at -22.47 ps. The
clock report also measured 118.60 ps setup skew between an ingress flop and
one KV macro clock pin. The final extracted hold WNS is positive, but this
amount of hold repair is a risk for a larger tile. The archived SDC has no
explicit hold uncertainty; this run did not relax any timing constraint.

This is an ASAP7 physical proxy with analytical memory compiler LEF/Liberty
views and empty macro-internal GDS. The SRAM address depth, bank coverage and
lane count are deliberately reduced. It does not establish manufacturability,
full Qwen core closure, target-node timing, power or token throughput. A
complete electrical fix needs the three named paths resolved in a matched
route while preserving the registered load protocol.
