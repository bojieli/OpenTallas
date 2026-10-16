# Inner RF core, middle SFU group — measured planning alternative

Status: **UNADOPTED; source-specific endpoint views and static cycles remain open.**

This coherent alternative inserts the complete SFU core/store before bank-pair
group2 while retaining the quarter RF/reducer core at the inner band end. The
quarter core reserves a 330.48 × 330.48 µm native-kit successor (gate pending),
with its centre-facing RF boundary kept at the old band edge. Native common-flow
synthesis retains all six RF payload replicas: 76,220 flops and 52,285.28 µm²
total cell-plus-macro area. The earlier generic count of 38,176 flops omitted
the physical keep-register hook and cannot size this block. The former
276.48 µm square would have about 70.6% core fill; the enlarged candidate has
about 49.2%, before native placement and clock qualification. The upper core
overhangs the low join column by 54 µm while retaining the original 276.48 µm
column pitch; the enlarged source-bound SUCX remains 32.4 µm away horizontally.
Charging the full enlarged width through the linear band fails by 53.592 µm,
so that unrevised linear arrangement is explicitly rejected. The native source
candidate relocates the existing RF ingress register rung; full normal component
edge equivalence is measured separately by the qcore owner. This plan does not
overlay the compact source on any old physical view.

Same780.0mm2 outline; old graph plan0overlaps/outside/fixed-return violations;
existing graph cuts V0.493/H0.566 at lane slack1200, zero windows over0.60;
weighted old-graph stages8.686. The new current source graph must replace old
aggregate links before these cuts can qualify the die.

All16 RF geometric polylines avoid hard rectangles. Their minimum depth is at
most32 at480um; keeping the actual production36 stages places all576 source-
bound standard48 footprints with no overlaps and max centre interval427.128um.
Actual source/sink pins, all66 qcore root references, routing and TT/FF/DRC
remain open. The actual external RF capture endpoint after rung relocation is
clk_ctl; the64 internal ctl-to-bank commit paths remain required STA paths.

The three coherent alternatives are compared in ../sfu_geometry_compare_1016.json
and its to-scale PNG. All actual596forward/516return SFR bits and the528-bit
SFU-to-SUCX result leg are counted; core-to-slice edges come from source-pinned
S contract SHA77df74f1. These are rectangle-gap lower bounds, not actual routes.

| Metric | Inner RF / hub SFU | Inner RF / middle SFU |
|---|---:|---:|
| Worst SFU-to-group gap | 12134.840um | 4883.296um |
| SFR bit-mm | 139021.56 | 46998.49 |
| Worst528-bit result-to-SUCX gap | 669.960um | 6287.776um |
| Result bit-mm | 1215.31 | 12980.32 |
| Actual core-to-slice bit-mm | 31395.04 | 34234.18 |
| Worst core-to-slice gap | 8874.944um | 9660.104um |

The middle SFU sharply reduces the broad LG transport, at the cost of explicitly
retiming the narrower result leg. No source currently instantiates those result
stages; compiler availability/phase and measured token cost must be rebuilt.
Local RF broadcasts to four distant slices remain a separate structural issue:
either registered fixed-latency distribution or real distributed RF replicas.
The isolated qcore component proof does not close that whole-SU path.

The hub-SFU alternative's12134.84um rectangle gap alone exceeds24x500um, so23
relay stages cannot qualify that worst leg even before actual native reach and
obstacles. The actual624-bit masters fail native220ps launch in every flow.
../relay_compare_1016.json compares all20 real standard masters, exact source
files and insertion references. Only48 passes all directions;136 passes SN/NS,
with balanced125/125/125/125/124 live lanes per624-bit station and56 explicit
spares.304/624/1136 are not native-qualified replacements. Footprints, clock
roots, pin direction, cut and actual stage count must be priced for either
qualified replacement; a functional lane split does not eliminate traffic.
The actual 13 × 48-bit station composition also requires 13 reset-region flops
and two reset synchronizers (15 additional flops per station). Native leaf
area and sink counts in the comparison exclude that new station glue. Across
736 stations this adds 11,040 reset flops, with physical area, clock/reset
placement, routes and release timing still unqualified.

Recommended next physical study: this middle-SFU alternative, using actual
qualified relay leaves, explicit result transport and complete current graph.
It is not an adoption recommendation until those gates and actual cost pass.
The plotted straight gap segments cross SU hard frames and are explicitly
marked inadmissible routes; they only expose the relevant source boundaries.

Images inspected with the image tool: ../sfu_geometry_compare_1016.png and
rf_centre_allocation.png. Programme partition remains coordinator-owned;
XC actual native kit224.64x216 and typed VM/writer local-clock gates are owned
by their dedicated physical workers. No extra die area is inferred from the
historical incorrect per-XC0.52mm2 interpretation.

Reproduce:

```sh
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 2891.92 --su-w 1797.12 --su-h 2671.92 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --out results/arch/hbm_die_v15/core4_sfu2
python3 tools/hbm_die_v15/v6_eval.py results/arch/hbm_die_v15/core4_sfu2 --slack 1200
python3 tools/hbm_die_v15/rf_centre_routes.py results/arch/hbm_die_v15/core4_sfu2
python3 tools/hbm_die_v15/rf_centre_allocate.py results/arch/hbm_die_v15/core4_sfu2
python3 tools/hbm_die_v15/standard_relay_compare_1016.py
python3 tools/hbm_die_v15/sfu_geometry_compare_1016.py
```
