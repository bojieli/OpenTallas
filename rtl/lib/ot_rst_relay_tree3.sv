`timescale 1ns/1ps
`ifndef OT_LEP_AR
`ifdef OT_S81SL_LEP_SYNCRST
// R7 (ELEM-LEP/A 10-21, opt-in): reset only gates control/valid D inputs (synchronous); no async RESETN pin, so no
// removal check sits on two different clock leaves (r6v FF -34.22: local_r -> frame flop 1.7 um, 51 ps leaf skew).
// Release edges are unchanged; assertion needs the clock running for >= 4 cycles (benches hold reset 8).
`define OT_LEP_AR(r)
`else
`define OT_LEP_AR(r) or negedge r
`endif
`endif
// Balanced synchronous-release reset tree. The root, group and local flops
// release on edges1/2/3, exactly the existing SYNC_STAGES2+TREE_STAGES1 contract.
// Async assertion cascades through reset pins; constant D=1 means each group
// drives only <=32 reset pins, without a matching wide D broadcast.
module ot_rst_relay_tree3 #(parameter integer REGIONS=32, parameter integer LEAVES=32,
                           parameter integer GROUPS=(REGIONS+LEAVES-1)/LEAVES)(
 input wire clk, rst_n_in, output wire [REGIONS-1:0] rst_n);
 (* keep="true",dont_touch="true",async_reg="true" *) reg root_r;
 wire [GROUPS-1:0] group_q;
 wire root_q;
 always @(posedge clk `OT_LEP_AR(rst_n_in))
     if(!rst_n_in) root_r<=1'b0; else root_r<=1'b1;
`ifdef OT_S81SL_LEP_RSTHD
 // r7 RSTHD (ELEM-LEP/A 10-21, opt-in): every tree level drives its async RESETN loads through a kept 3 x HB4xp67 chain
 // (~114 ps at FF, dont_touch'ed by hdly_dont_touch.tcl): removal slack no longer depends on the source and receiver
 // sitting on the same clock leaf (r6v FF -34.22: local_r -> frame flop 1.7 um, leaves 505 / 556 ps).  Recovery keeps
 // a full cycle; release edges 1/2/3 unchanged; simulation identity.
 ot_lep_rsthd u_hdly_root(.a(root_r),.y(root_q));
`else
 assign root_q=root_r;
`endif
 genvar g,l;
 generate for(g=0;g<GROUPS;g=g+1) begin:g_group
     (* keep="true",dont_touch="true",async_reg="true" *) reg group_r;
`ifdef OT_S81SL_LEP_RSTHD
     ot_lep_rsthd u_hdly_group(.a(group_r),.y(group_q[g]));
`else
     assign group_q[g]=group_r;
`endif
     always @(posedge clk `OT_LEP_AR(root_q))
         if(!root_q) group_r<=1'b0; else group_r<=1'b1;
 end
 for(l=0;l<REGIONS;l=l+1) begin:g_local
     (* keep="true",dont_touch="true" *) reg local_r;
`ifdef OT_S81SL_LEP_RSTHD
     ot_lep_rsthd u_hdly_local(.a(local_r),.y(rst_n[l]));
`else
     assign rst_n[l]=local_r;
`endif
     always @(posedge clk `OT_LEP_AR(group_q[l/LEAVES]))
         if(!group_q[l/LEAVES]) local_r<=1'b0; else local_r<=1'b1;
 end endgenerate
`ifndef SYNTHESIS
 initial if(GROUPS>32 || LEAVES>32) $fatal(1,"reset fanout requires another explicitly priced tree shape");
`endif
endmodule
`ifdef OT_S81SL_LEP_RSTHD
`ifndef OT_LEP_RSTHD_DEFINED
`define OT_LEP_RSTHD_DEFINED
// r7 RSTHD kept reset hold-delay: 3 x HB4xp67 (~38 ps each at FF, ASAP7 RVT) in synthesis, a wire in simulation.
module ot_lep_rsthd(input wire a, output wire y);
`ifdef SYNTHESIS
 wire [3:0] c; assign c[0]=a;
 genvar k;
 for(k=0;k<3;k=k+1) begin:g_k
  (* keep *) HB4xp67_ASAP7_75t_R u_hb(.A(c[k]),.Y(c[k+1]));
 end
 assign y=c[3];
`else
 assign y=a;
`endif
endmodule
`endif
`endif
