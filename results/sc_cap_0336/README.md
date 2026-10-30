# sle_sc_v2 natural hard child budget

Actual542365 standard cells exceed the400000 per-part cap. A complete existing hierarchy gives a natural hard boundary without changing arithmetic, state, reset, ports or cycles:

| Scope | Mapped standard cells | Sequential cells | Combinational cells | Actual LEF master cell area |
|---|---:|---:|---:|---:|
| Existing u_bound.u_core = qfd_dv_s5_sc2_leaf→k79 |281884|43052|238832|36859.27518um²|
| Remaining wrapper + CA rings + FT/parent stages |260481|61618|198863|34108.29162um²|
| Whole current native parent |542365|104670|437695|70967.56680um²|

Proposed boundary: harden the complete existing u_core as one child; remaining parent carries one macro plus260481 standard cells before interface/clock/repair overhead. Headroom to400k is118116 for child and139519 for wrapper. No cells or state are omitted: child and wrapper must BOTH close, with full original module retained. These mapped counts are the actual existing full-wrapper native hierarchy; isolated native remap/CTS/repair must still be measured. Standard-cell counts alone are not a physical clearance or signoff.

Source k79 has43058 one-bit DFF helpers (42429 plain +629 async-reset0), of which current native mapping retains43052 FFs. The six difference is part of the existing baseline mapping, not a state-cut proposal; no source state pruning is performed here. The current whole logical LEC remains untouched. Child full source uses the same productionLA7/LM9, no parameter shrink or arithmetic cycle change.

Child interface:27 ports,572 bits =357 inputs +215 outputs. Groups: clock/reset2 inputs; config101 inputs; down48 in/48 out; up48 in/48 out; reduction57 inputs; VM42 inputs; AM59 inputs; writeback57 outputs; token60 outputs; busy/fault2 outputs. Exact direction/width and original parent nets are in port_interface.json. ck is existing clk and rst_n is existing mission rst_n; zero added clock domain or stages.

Parent outline stays613.44×1339.2um. Public face/layer windows stay unchanged; full payload/epoch spans in public_faces.json. Core up_o→existing x_fe_o bout onE/y272.352..281.76; dn_o→x_fw_o bout onW/y890.848..898.976; writeback/token/busy/fault→x_ctl_o bout onN/x122.76..143.208/y1339.2. Config+AM come from x_ctl_i/N; down from x_fe_i+flt_fe_i/E; up from x_fw_i/W; reduction from x_su_c_i/S through existing R8 chains; VM from x_su_l0_i/E-top andx_su_l1_i/S through existing8/6-cycle pad chains. Keep every existing chain/cycle; use placement of existing stages, not new registers, for reach.

Parent bay must price core-output→existing bout and CA ring read/boundary→core reaches≤405um, plus the actual hard child's internal timing/clock/reset/PDN and pin access. A nominal central rectangle is not approved. Actualcell area only: a40% reference footprint92148um²,30%122864um²,20%184296um²; final aspect/clock/pin/halo/channel footprint is a geometry decision.

There is NO actual parent FIRM placement: parent was explicitly held before floorplan due the cap. reserved_corridors.json contains67 generated CA/status group rectangles and17 FT chain stage envelopes derived from actual generated face_flops route rules and actual pins.json. They are MODEL TARGETS, not legalized body keepouts. Row/site snapping, TAP/endcap bodies, width/reservation and FF_near collision shifts must be included before declaring a bay clear. Actual sourcefiles remain read-only at the parent kit. This limitation prevents silently calling the17 chains empty space.

Parent owns same-outline internal decomposition and plan review. Next: price a child bay against those exact reserved corridors and per-interface405um reach; build unchanged full child native vehicle, render/review, close child TTsetup/FFhold833ps and all gates; then regenerate parent with frozen child view and retain full logical equivalence. No cap waiver, count omission, broad die rewrite or physical job launched by this census.
