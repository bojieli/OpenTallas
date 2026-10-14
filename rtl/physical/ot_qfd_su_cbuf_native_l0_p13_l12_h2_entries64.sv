`timescale 1ns/1ps
// Eight actual native layer0 cbuf leaves. Parent contains wires only.
// Clock/PG/placement and cross-leaf readiness reduction belong to the parent.
module qfd_su_cbuf_native_l0_p13_l12_h2_entries64 #(parameter integer MUT=0,GROUP_MUT=0,RESET_MUT=0)(
 input wire[7:0]ck,input wire rst_n,epoch,
 input wire[63:0]crom_re,input wire[1535:0]crom_addr,input wire[5:0]crom_stage,
 output wire[4095:0]crom_q,input wire[5:0]stage,input wire tok_start,input wire[17:0]tpos,
 output wire[7:0]st_rdy,output wire[47:0]st_rdy_stage,output wire[143:0]st_rdy_tpos,
 output wire[63:0]f_re,output wire[1535:0]f_addr,output wire[47:0]f_stage,
 input wire[4095:0]f_q,input wire[7:0]f_fault,input wire[4:0]f_lat,
 output wire[7:0]fault,output wire[15:0]fault_code);
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_group
  qfd_su_cbuf_native_l0_p13_l12_h2 #(.MUT(MUT))u(
   .clk(ck[g]),.rst_n(rst_n|((RESET_MUT!=0&&g==7)?epoch:1'b0)),
   .crom_re(crom_re[g*8+:8]),.crom_addr(crom_addr[g*192+:192]),.crom_stage(crom_stage),
   .crom_q(crom_q[g*512+:512]),.stage(stage),
   .tok_start(tok_start&&!((RESET_MUT!=0&&g==7)&&epoch)),.tpos(tpos),
   .grp((GROUP_MUT!=0&&g==7)?3'd6:3'(g)),.st_rdy(st_rdy[g]),.st_rdy_stage(st_rdy_stage[g*6+:6]),.st_rdy_tpos(st_rdy_tpos[g*18+:18]),
   .f_re(f_re[g*8+:8]),.f_addr(f_addr[g*192+:192]),.f_stage(f_stage[g*6+:6]),
   .f_q(f_q[g*512+:512]),.f_fault(f_fault[g]),.f_lat_total(f_lat),
   .fault(fault[g]),.fault_code(fault_code[g*2+:2]));
 end endgenerate
endmodule
