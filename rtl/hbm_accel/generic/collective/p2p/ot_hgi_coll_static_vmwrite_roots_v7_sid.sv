// Four literal-SID physical masters for the actual die quadrants.
// SW=0 SE=1 NW=2 NE=3. Related phase-0 roots and all functional cycles
// match v6; only the compile-time identity replaces the dynamic SID pins.

`timescale 1ns/1ps
`default_nettype none
// Pure wiring adapter: every native leaf IO BASE name belongs to one root.
// Same16scalar clocks, zero added FF/logic/edges; original vector ABI remains
// on the proven core. Every related-clock crossing keeps normal setup/hold.
module ot_hgi_coll_static_vmwrite_roots_v7_sid0 #(
    parameter integer MUT = 0
) (
    input wire clk_rgx_data0, clk_rgx_data1, clk_rgx_data2, clk_rgx_data3,
    input wire clk_rgx_ctrl, clk_tkw, clk_meta, clk_body,
    input wire clk_bank0, clk_bank1, clk_bank2, clk_bank3,
    input wire clk_bank4, clk_bank5, clk_bank6, clk_bank7,
    input wire rst_n,
   
    input wire [3:0] rgx_v,
    input wire [159:0] rgx_addr,
    input wire [511:0] rgx_data0,
    input wire [511:0] rgx_data1,
    input wire [511:0] rgx_data2,
    input wire [511:0] rgx_data3,
    input wire rgx_vm,
    input wire tkw_v,
    input wire [567:0] tkw_d,
    input wire [4:0] ingress_slot,
    input wire [7:0] slot_valid,
    input wire [31:0] slot_owner,
    output wire [280:0] kq0,
    output wire [280:0] kq1,
    output wire [280:0] kq2,
    output wire [280:0] kq3,
    output wire [280:0] kq4,
    output wire [280:0] kq5,
    output wire [280:0] kq6,
    output wire [280:0] kq7,
    output wire [4:0] launch_done,
    output wire fault
);
 ot_hgi_coll_static_vmwrite_roots_v6 #(.MUT(MUT)) core(
  .clk_rgx_data0(clk_rgx_data0),
  .clk_rgx_data1(clk_rgx_data1),
  .clk_rgx_data2(clk_rgx_data2),
  .clk_rgx_data3(clk_rgx_data3),
  .clk_rgx_ctrl(clk_rgx_ctrl),
  .clk_tkw(clk_tkw),
  .clk_meta(clk_meta),
  .clk_body(clk_body),
  .clk_bank0(clk_bank0),
  .clk_bank1(clk_bank1),
  .clk_bank2(clk_bank2),
  .clk_bank3(clk_bank3),
  .clk_bank4(clk_bank4),
  .clk_bank5(clk_bank5),
  .clk_bank6(clk_bank6),
  .clk_bank7(clk_bank7),
  .rst_n(rst_n),
  .sid(2'd0),
  .rgx_v(rgx_v),
  .rgx_addr(rgx_addr),
  .rgx_vm(rgx_vm),
  .tkw_v(tkw_v),
  .tkw_d(tkw_d),
  .ingress_slot(ingress_slot),
  .slot_valid(slot_valid),
  .slot_owner(slot_owner),
  .launch_done(launch_done),
  .fault(fault),
  .rgx_data({rgx_data3,rgx_data2,rgx_data1,rgx_data0}),
  .kq({kq7,kq6,kq5,kq4,kq3,kq2,kq1,kq0})
 );
endmodule
`default_nettype wire

`timescale 1ns/1ps
`default_nettype none
// Pure wiring adapter: every native leaf IO BASE name belongs to one root.
// Same16scalar clocks, zero added FF/logic/edges; original vector ABI remains
// on the proven core. Every related-clock crossing keeps normal setup/hold.
module ot_hgi_coll_static_vmwrite_roots_v7_sid1 #(
    parameter integer MUT = 0
) (
    input wire clk_rgx_data0, clk_rgx_data1, clk_rgx_data2, clk_rgx_data3,
    input wire clk_rgx_ctrl, clk_tkw, clk_meta, clk_body,
    input wire clk_bank0, clk_bank1, clk_bank2, clk_bank3,
    input wire clk_bank4, clk_bank5, clk_bank6, clk_bank7,
    input wire rst_n,
   
    input wire [3:0] rgx_v,
    input wire [159:0] rgx_addr,
    input wire [511:0] rgx_data0,
    input wire [511:0] rgx_data1,
    input wire [511:0] rgx_data2,
    input wire [511:0] rgx_data3,
    input wire rgx_vm,
    input wire tkw_v,
    input wire [567:0] tkw_d,
    input wire [4:0] ingress_slot,
    input wire [7:0] slot_valid,
    input wire [31:0] slot_owner,
    output wire [280:0] kq0,
    output wire [280:0] kq1,
    output wire [280:0] kq2,
    output wire [280:0] kq3,
    output wire [280:0] kq4,
    output wire [280:0] kq5,
    output wire [280:0] kq6,
    output wire [280:0] kq7,
    output wire [4:0] launch_done,
    output wire fault
);
 ot_hgi_coll_static_vmwrite_roots_v6 #(.MUT(MUT)) core(
  .clk_rgx_data0(clk_rgx_data0),
  .clk_rgx_data1(clk_rgx_data1),
  .clk_rgx_data2(clk_rgx_data2),
  .clk_rgx_data3(clk_rgx_data3),
  .clk_rgx_ctrl(clk_rgx_ctrl),
  .clk_tkw(clk_tkw),
  .clk_meta(clk_meta),
  .clk_body(clk_body),
  .clk_bank0(clk_bank0),
  .clk_bank1(clk_bank1),
  .clk_bank2(clk_bank2),
  .clk_bank3(clk_bank3),
  .clk_bank4(clk_bank4),
  .clk_bank5(clk_bank5),
  .clk_bank6(clk_bank6),
  .clk_bank7(clk_bank7),
  .rst_n(rst_n),
  .sid(2'd1),
  .rgx_v(rgx_v),
  .rgx_addr(rgx_addr),
  .rgx_vm(rgx_vm),
  .tkw_v(tkw_v),
  .tkw_d(tkw_d),
  .ingress_slot(ingress_slot),
  .slot_valid(slot_valid),
  .slot_owner(slot_owner),
  .launch_done(launch_done),
  .fault(fault),
  .rgx_data({rgx_data3,rgx_data2,rgx_data1,rgx_data0}),
  .kq({kq7,kq6,kq5,kq4,kq3,kq2,kq1,kq0})
 );
endmodule
`default_nettype wire

`timescale 1ns/1ps
`default_nettype none
// Pure wiring adapter: every native leaf IO BASE name belongs to one root.
// Same16scalar clocks, zero added FF/logic/edges; original vector ABI remains
// on the proven core. Every related-clock crossing keeps normal setup/hold.
module ot_hgi_coll_static_vmwrite_roots_v7_sid2 #(
    parameter integer MUT = 0
) (
    input wire clk_rgx_data0, clk_rgx_data1, clk_rgx_data2, clk_rgx_data3,
    input wire clk_rgx_ctrl, clk_tkw, clk_meta, clk_body,
    input wire clk_bank0, clk_bank1, clk_bank2, clk_bank3,
    input wire clk_bank4, clk_bank5, clk_bank6, clk_bank7,
    input wire rst_n,
   
    input wire [3:0] rgx_v,
    input wire [159:0] rgx_addr,
    input wire [511:0] rgx_data0,
    input wire [511:0] rgx_data1,
    input wire [511:0] rgx_data2,
    input wire [511:0] rgx_data3,
    input wire rgx_vm,
    input wire tkw_v,
    input wire [567:0] tkw_d,
    input wire [4:0] ingress_slot,
    input wire [7:0] slot_valid,
    input wire [31:0] slot_owner,
    output wire [280:0] kq0,
    output wire [280:0] kq1,
    output wire [280:0] kq2,
    output wire [280:0] kq3,
    output wire [280:0] kq4,
    output wire [280:0] kq5,
    output wire [280:0] kq6,
    output wire [280:0] kq7,
    output wire [4:0] launch_done,
    output wire fault
);
 ot_hgi_coll_static_vmwrite_roots_v6 #(.MUT(MUT)) core(
  .clk_rgx_data0(clk_rgx_data0),
  .clk_rgx_data1(clk_rgx_data1),
  .clk_rgx_data2(clk_rgx_data2),
  .clk_rgx_data3(clk_rgx_data3),
  .clk_rgx_ctrl(clk_rgx_ctrl),
  .clk_tkw(clk_tkw),
  .clk_meta(clk_meta),
  .clk_body(clk_body),
  .clk_bank0(clk_bank0),
  .clk_bank1(clk_bank1),
  .clk_bank2(clk_bank2),
  .clk_bank3(clk_bank3),
  .clk_bank4(clk_bank4),
  .clk_bank5(clk_bank5),
  .clk_bank6(clk_bank6),
  .clk_bank7(clk_bank7),
  .rst_n(rst_n),
  .sid(2'd2),
  .rgx_v(rgx_v),
  .rgx_addr(rgx_addr),
  .rgx_vm(rgx_vm),
  .tkw_v(tkw_v),
  .tkw_d(tkw_d),
  .ingress_slot(ingress_slot),
  .slot_valid(slot_valid),
  .slot_owner(slot_owner),
  .launch_done(launch_done),
  .fault(fault),
  .rgx_data({rgx_data3,rgx_data2,rgx_data1,rgx_data0}),
  .kq({kq7,kq6,kq5,kq4,kq3,kq2,kq1,kq0})
 );
endmodule
`default_nettype wire

`timescale 1ns/1ps
`default_nettype none
// Pure wiring adapter: every native leaf IO BASE name belongs to one root.
// Same16scalar clocks, zero added FF/logic/edges; original vector ABI remains
// on the proven core. Every related-clock crossing keeps normal setup/hold.
module ot_hgi_coll_static_vmwrite_roots_v7_sid3 #(
    parameter integer MUT = 0
) (
    input wire clk_rgx_data0, clk_rgx_data1, clk_rgx_data2, clk_rgx_data3,
    input wire clk_rgx_ctrl, clk_tkw, clk_meta, clk_body,
    input wire clk_bank0, clk_bank1, clk_bank2, clk_bank3,
    input wire clk_bank4, clk_bank5, clk_bank6, clk_bank7,
    input wire rst_n,
   
    input wire [3:0] rgx_v,
    input wire [159:0] rgx_addr,
    input wire [511:0] rgx_data0,
    input wire [511:0] rgx_data1,
    input wire [511:0] rgx_data2,
    input wire [511:0] rgx_data3,
    input wire rgx_vm,
    input wire tkw_v,
    input wire [567:0] tkw_d,
    input wire [4:0] ingress_slot,
    input wire [7:0] slot_valid,
    input wire [31:0] slot_owner,
    output wire [280:0] kq0,
    output wire [280:0] kq1,
    output wire [280:0] kq2,
    output wire [280:0] kq3,
    output wire [280:0] kq4,
    output wire [280:0] kq5,
    output wire [280:0] kq6,
    output wire [280:0] kq7,
    output wire [4:0] launch_done,
    output wire fault
);
 ot_hgi_coll_static_vmwrite_roots_v6 #(.MUT(MUT)) core(
  .clk_rgx_data0(clk_rgx_data0),
  .clk_rgx_data1(clk_rgx_data1),
  .clk_rgx_data2(clk_rgx_data2),
  .clk_rgx_data3(clk_rgx_data3),
  .clk_rgx_ctrl(clk_rgx_ctrl),
  .clk_tkw(clk_tkw),
  .clk_meta(clk_meta),
  .clk_body(clk_body),
  .clk_bank0(clk_bank0),
  .clk_bank1(clk_bank1),
  .clk_bank2(clk_bank2),
  .clk_bank3(clk_bank3),
  .clk_bank4(clk_bank4),
  .clk_bank5(clk_bank5),
  .clk_bank6(clk_bank6),
  .clk_bank7(clk_bank7),
  .rst_n(rst_n),
  .sid(2'd3),
  .rgx_v(rgx_v),
  .rgx_addr(rgx_addr),
  .rgx_vm(rgx_vm),
  .tkw_v(tkw_v),
  .tkw_d(tkw_d),
  .ingress_slot(ingress_slot),
  .slot_valid(slot_valid),
  .slot_owner(slot_owner),
  .launch_done(launch_done),
  .fault(fault),
  .rgx_data({rgx_data3,rgx_data2,rgx_data1,rgx_data0}),
  .kq({kq7,kq6,kq5,kq4,kq3,kq2,kq1,kq0})
 );
endmodule
`default_nettype wire
