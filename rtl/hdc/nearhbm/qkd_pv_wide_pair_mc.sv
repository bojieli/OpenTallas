`timescale 1ns/1ps
// Actual physical partition of the native w16 P.V pair. Wires only: 289
// independently delivered clocks, one per 256 slices, 32 joins and control.
// The die delivers phi-R per child from the actual child insertion view.
// No synthesis clock tree is allowed to span the child boundaries.
// Data/control mapping and arithmetic order are identical to the source pair.
module qkd_pv_wide_pair_mc #(
 parameter integer PAIR=0,
 parameter integer CTL_RESET_PIN=1,
 parameter integer LEAF_RESET_PIN=1, // opt-in local reset capture; normal command timeline unchanged
 parameter integer FIRST_INPUT_AGE=20,   // pair cycle (after the start cycle) of the q = 0 arrival = 1 + V return latency
 parameter integer MUT=0                 // bench negative control: 1 = level-5 join pairs (b0+b2),(b1+b3) (wrong order)
)(
 input wire clk,rst_n,start,input wire[288:0] leaf_clk,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[8191:0] in_v,input wire[511:0] in_e,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output wire[7:0] req_valid,output wire[111:0] req_t,
 output wire out_valid,output wire[16383:0] out_leaf,output wire[15:0] out_epoch,
 output wire fault,output wire busy,output wire[15:0] out_age
);
 wire[59:0] cmd;wire[31:0] cf,cv;wire ctl_fault;
 ot_qwen_tp8_pv_wide_ctl #(.FIRST_INPUT_AGE(FIRST_INPUT_AGE),.RESET_PIN(CTL_RESET_PIN)) u_ctl(.clk(leaf_clk[288]),.rst_n(rst_n),.pair_id(1'(PAIR)),.start(start),
  .context_len(context_len),.epoch(epoch),.in_valid(in_valid),.in_t(in_t),.in_epoch(in_epoch),
  .req_valid(req_valid),.req_t(req_t),.cmd(cmd),.col_valid(cv),.col_fault(cf),
  .out_epoch(out_epoch),.fault(ctl_fault),.busy(busy),.out_age(out_age));
 // the pair output pulse is column 0's own pinned y_valid; the control tile checks every column against its slot
 assign out_valid=cv[0];
 genvar s;
 generate for(s=0;s<32;s=s+1)begin:g_col
  localparam integer H=s/8,GS=s%8;
  wire[1023:0] v;wire[127:0] e;
  genvar k;
  for(k=0;k<8;k=k+1)begin:g_port
   assign v[128*k+:128]=in_v[1024*k+128*GS+:128];
   assign e[16*k+:16]=in_e[64*k+16*H+:16];
  end
  qkd_pv_col_mc #(.MUT(MUT),.RESET_PIN(LEAF_RESET_PIN)) u_col(.leaf_clk(leaf_clk[9*s+:9]),.rst_n(rst_n),.pv(v),.pe(e),.cmd(cmd),
   .y(out_leaf[512*s+:512]),.y_valid(cv[s]),.fault(cf[s]));
 end endgenerate
 assign fault=ctl_fault;
endmodule

module qkd_pv_col_mc #(parameter integer MUT=0,RESET_PIN=0)(
 input wire[8:0] leaf_clk,input wire rst_n,
 input wire[1023:0] pv,input wire[127:0] pe,     // per V port k (0-3: stack PAIR lane k; 4-7: stack PAIR+2 lane k-4)
 input wire[59:0] cmd,
 output wire[511:0] y,output wire y_valid,output wire fault
);
 wire[4095:0] ts;wire[7:0] sf;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:g_bank
  localparam integer PA=l,PB=l^4;
  wire[22:0] bc={cmd[30:15],cmd[14:11],(l<4)?cmd[9]:cmd[10],cmd[1+l],cmd[0]};
  ot_qwen_tp8_pv_slice_t #(.RESET_PIN(RESET_PIN)) u_bank(.clk(leaf_clk[l]),.rst_n(rst_n),.pv2({pv[128*PB+:128],pv[128*PA+:128]}),
   .pe2({pe[16*PB+:16],pe[16*PA+:16]}),.bc(bc),.ts(ts[512*l+:512]),.fault(sf[l]));
 end endgenerate
 ot_qwen_tp8_pv_join_t #(.MUT(MUT),.RESET_PIN(RESET_PIN)) u_join(.clk(leaf_clk[8]),.rst_n(rst_n),.ts0(ts[1023:0]),.ts1(ts[2047:1024]),.ts2(ts[3071:2048]),
  .ts3(ts[4095:3072]),.join_go(cmd[31]),.sf(sf),
  .y(y),.y_valid(y_valid),.fault(fault));
endmodule
