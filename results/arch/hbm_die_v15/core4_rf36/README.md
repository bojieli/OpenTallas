# Inner-quarter-core RF36 candidate — unadopted

The coherent quarter-core-at4 alternative keeps the measured 780.0 mm2 outline,
7200x1800 SM frames and 76.8 mm2 SU slices. It moves each complete quarter core
and COLL stack to the inner band end and leaves SFU beside the VM hub. NW QUANT
remains beside its bank pair. Existing graph plan: zero overlaps, outside and
fixed-return violations. At lane slack1200, existing-graph cuts are V0.553/H0.541
with zero windows over0.60; bit-weighted stages8.714. The current824new incident
edges have not been substituted for the corresponding old aggregate edges.

The old mid-core candidate required66 RF stages in its old route model. This
candidate instead uses centre-facing RF pins on the N faces of south quarter
cores and S faces of north quarter cores. It follows the free band/SM corridor,
the two inner channels and the two gaps between IDX scorers and central glue.
All16 polylines avoid hard footprints and need at most36 stages at480um
geometric reach. The41-bit ABI is the actual red_rf_v, red_tag[7:0], red_x tuple
to rf_wv[source], rf_wa[8*source+:8], rf_wd[32*source+:32]. Source outputs fan out
from the same declared location, not four inconsistent positions for one port.

`rf_centre_allocation.json` places all16x36=576 actual21.6x21.6 standard48 relay
footprints, binding each instance name/master to af261fbcb. All36 stages of the
four self routes occupy explicit three-column padding grids in the core/COLL
gaps. There are no cell/hard or cell/cell overlaps; total area0.26873856mm2.
The longest centre-polyline interval is480um. This is placement geometry only.

`rf_view_binding.json` binds the actual four standard48 WE/EW/SN/NS LEFs,
TT/FF Liberty models and per-corner insertion.json by exact SHA256 at b55c8b228.
It checks all41 used bits for all16 master-pair combinations. With die clock
delivered at phi-R for each root, the unchanged source-pinned RF domain is
serial900MHz: available setup budget1111.1−60−90=961.1ps. A conservative pin
wire envelope480+43.2=523.2um gives worst relay-pair TT margin+196.8313ps.
Worst zero-wire FF hold margin after25+90ps is+108.60137ps. These are actual
relay ETM checks with an assumed geometric wire bound, not routed STA.

The stream1.2GHz 683.3ps comparison is included only as sensitivity; it does
not change the implemented RF clock or require extra serial cycles. Production
RF36 remains provisional until actual qcore launch/capture views and all64 RF
clock-root references are measured. Qcore boundary views are absent here;
actual per-bit qcore and relay route, final clock insertion/spread, full graph
cuts and die GRT/STA/DRC0 are still open. No active contract or view was changed.

XC sizing correction:0.52mm2 is SRAM TOTAL across all32XC; each two-macro XC
has0.016206mm2 macro area. Current native kit is224.64x216, including actual
core margins. The historical500x1200 band reserves are not physical area needs.
XC belongs near its own SM command capture in the explicit parent-owned top
strip; the native XC source/kit owner is xc_physical, and parent integration
still requires the new SM hierarchical view. No die growth is based on old
inflated reserves. Programme301-macro physical partition is owned by coordinator.

The figure `rf_centre_allocation.png` was inspected with the image tool after
generation. It shows the actual576 footprints and all16 paths following free
channels; source-bound endpoint clocks and full graph evidence remain open.

Reproduce:

```sh
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-hub --band 2891.92 --su-w 1797.12 --su-h 2671.92 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --out results/arch/hbm_die_v15/core4_rf36
python3 tools/hbm_die_v15/v6_eval.py results/arch/hbm_die_v15/core4_rf36 --slack 1200
python3 tools/hbm_die_v15/rf_centre_routes.py results/arch/hbm_die_v15/core4_rf36
python3 tools/hbm_die_v15/rf_centre_allocate.py results/arch/hbm_die_v15/core4_rf36
python3 tools/hbm_die_v15/rf_view_binding.py results/arch/hbm_die_v15/core4_rf36
```
