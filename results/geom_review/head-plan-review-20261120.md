# HEAD r11b and r13 floorplan review

Viewed head_r11b.png, head_r13.png, and r11b_serdes_kit.png on 2026-11-20. The die plan panels use the lane geometry and the frozen clock-tree endpoint table, using one representative clock endpoint pattern per type. The hd_serdes panel uses the exact r11b bootstrap kit pin, macro placement, and landing geometry.

The die places repeated tile arrays symmetrically east and west of the center spine. Most wide links meet their neighboring faces directly. The long north and south side corridors have relay positions along their spans. The r13 hd_lep0N clock endpoints concentrate at its side interfaces and the mid-block load band. The new taps do not move the die-level bus faces. The narrow center spine and the corner turns need route overflow measurements. The die image does not resolve PG via access.

The r11b hd_serdes has its south-facing coll_i0 window next to the receiver landing group. The adjacent coll_o0 window faces the KP4 core cluster. The two SRAMs and KP4 retain distinct macro channels, and the layout leaves routes around the outside of the cluster. Clock taps follow the populated southern region. The image cannot establish SRAM pin access or PG continuity.

Verdict: r11b hd_serdes geometry is suitable for an exploratory kit run with its adopted tools. r13 die-level planned geometry is suitable for kit generation after the bind gates. Review emitted r13 kits before dispatch to physical tools. Require the final r13 PG access read before a whole-die route.

The hd_lep0N r13 zoom, head_r13_lep.png, was viewed separately. It overlays the plan hard macros, eight new station ranks, stage rectangles, taps and relevant port windows. The four pair macros leave a central cross and outer channels. The coll_i0/o0 stations step through the upper channel, coll_i3/o3 through the east aisle, and coll_o2 stays close to the west pair face. No plotted station center lies inside the four macros. The narrow east strip between the pair macro and coll_i3/o3 lanes is the first congestion measurement to inspect, along with the SRAM band at the center. No claim of routed closure follows from this image.

Two plan-stage paths still exceed 300 um by pessimistic band-corner bounds. The pin_s5u chain and PLW need placed pin-level reads to size new per-bit stage rows, and the fault output is a smaller 315 um class. This plan image is suitable to generate the exact r13 pilot kit. Recheck these data paths in the emitted layout before routing.

## r11b production SerDes a8 emitted geometry

Viewed [the exact generated a8 kit](head-r11b-serdes-a8-exact.png) from E10 `kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r11b/items/hd_serdes/attempt_8/gen/hd_serdes`. The 1,028 emitted pins separate ingress and egress on the south face. The ingress landing rectangle x1824.88–2030.08 µm, y17.28–62.64 µm clears the channel macro. Its top edge is 44.688 µm below the channel's bottom edge. The two SRAMs leave 16.632 µm between their x edges and each is 24.444 µm above the channel's north edge. The macro cluster leaves open area to the north and east. Generation and kit preflight passed. The held plan read advisory clk_t21 (1,817 sinks against 1,000 and 487.614 µm radius against 200) still needs placed reach and CTS. Placement is running in the existing E10 wave attempt. Route requires the placed geometry review.

The r11b tap warning reproduces in the pinned budget tool against its older native spatial census (10,557 total modeled sinks, t20/t21 5,940/1,817). The r13r source uses the newer actual placed per-root census and replacements for those explicit taps. In that plan budget, 14,991 primary FFs and four controls are assigned with maximum 662 sinks and 161.675 µm, including t20 436 sinks / 36.668 µm and t21 418 / 39.484 µm. This source-census estimate belongs to r13r. It does not qualify CTS in the running r11b kit.

### r11b SerDes attempt 8 detailed placement

**ISSUES.** Viewed [detailed placement](head-r11b-serdes-a8-placed.png) and [density](head-r11b-serdes-a8-placed-density.png) from the exact attempt 8 `3_5_place_dp.odb`, sealed placement unit 2401510-1795177397 on E10. The distinct south pin banks and three-macro clearances survived placement. Cell area falls mainly in the available southern bands next to the macro cluster and pin entries. The exact layout scan measured 0 opposite-face paths among 2,143 checked pins, 26.4% worst pin-track window, 10.1% estimated channel-track use and 63.6% peak local density.

Six classes of checks gave one flag, fanout spread. Native PHY reset `u_phy.u_link.rs_t[1]` drives 634 sinks over a 538.8 µm Manhattan box, landing reset `u_cland_rst_coll_i0/q` drives 28 sinks over 513.6 µm, and the SerDes syndrome (S_q) groups reach roughly 446–461 µm. The stock-capacitance placement remains a physical baseline. Keep route held here while the NOMCAP successor and planned reset-tap update generate the new form.

### r13r nominal-capacitance SerDes generated kit

Viewed [the exact emitted kit](head-r13r-serdes-nomcap-generated.png) after successful E10 KIT_RTL and GEN, unit 2075244-1795190643. The source is the immutable r13r nominal-capacitance snapshot, manifest 6d3c0e3e43d9. The kit emitted six approved libraries and declares 833 ps recovered-clock period. All 1,054 exact emitted io.tcl port records match r11b a8 names, layers and coordinates. The separate south banks, 16.632 µm SRAM-to-SRAM gap and 24.444 µm SRAM-to-channel clearance are visible. The ingress landing rectangle ends 44.688 µm below the channel.

The generated budget names 37 clock taps. All 56 distinct emitted reset and START sites clear the three macro interiors. The view supports moving the exact nominal candidate into placement. Placed reach, fanout and timing are open. The prior a8 stock-form ISSUES hold remains in force. No route is authorized by this generated geometry review.
