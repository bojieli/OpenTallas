# E2 same-root insertion-aware perimeter successor

E2 same-root structural perimeter tree for clk_w1 only. Exact old3_place prefix reproduces old ALL1035 platform TT133.588/FF148.819 failure. Real sink islands240west/795east,132leaves; equal buffer-depth7 below common root, same-root west/east perimeter topology avoids SRAM-column cross-branches. Actual candidate ALL1035 platformTT17.686/FF15.466 and calTT14.184/FF12.456. Other roots,20hard clock entries, RTL/ports/WR3, outline, edges, RCrestore and hybrid checks unchanged. Diagnostic prefix is not gate qualification. 0 added cycles.

One bounded candidate only; previous rw10sp/spb failures remain immutable. Exact prefix packet: `results/arch/hbm_hc_e2_perimeter_1021/prefix_model_summary.json`. Prefix model is diagnostic, not physical qualification.

SAFE before necessary gate:

1. Pins: same exact WR3 RTL and real registered boundary contracts; no extra pin/data stages.
2. Reach: same 734.4um outline/20 hard children; no data reach changes. Clock uses actual west/east perimeter topology; actual placed reach remains gate obligation.
3. Fanout: identical RTL prior canonical native max32 PASS; fresh canonical native before layout mandatory. Clock loads retain real ALL1035 sink census, no dummy loads.
4. Depth: data logic unchanged; new uniform clock-buffer depth7 is distribution only. Actual setup/hold decide.
5. Storage: unchanged SRAM inventory/rings and exact hard-child Liberty references.
6. Floorplan: exact734.4 square outline, unchanged SRAM lattice and hardchild placements/full cell band. Actual utilization/PNG/pin/reach checks remain mandatory.
7. Clock: ONLY clk_w1 topology changes; other22 roots/20 independent hard entries unchanged. Existing hybrid guards, platform RC restoration and strict80ps TT/FF remain. Prefix ALL1035 platformTT17.686/FF15.466; no relabel/subset waiver. Actual full-gate child boundary/parent STA decide.
8. Schedule: ports/clock edges/reset/data calendars unchanged; zero added cycles.

Critical geometry and actual clock/native/GRT/STA packet require coordinator review before REVIEW or route submission. No route authorization or CLOSED claim.
