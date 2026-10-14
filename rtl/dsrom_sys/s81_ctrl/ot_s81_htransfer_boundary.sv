`timescale 1ns/1ps
// Native boundary candidate: wires package VM writes into the HC landing leaf,
// derives input-present from the HC queue HEAD (never latest issued command),
// and protects cut-through hop reads. All VM writes remain on the original
// production VM path. This module neither changes coefficients nor FP order.
// Composition must provide actual head descriptors, accepted H_STORE, and
// committed full-row writes. Not yet bound to a native120 deployed program.
module ot_s81_htransfer_boundary #(
 parameter integer XW=640,RXB=0,TXB=2048,S_RD=2,S_WR=8,HWM=8,HDEPTH=4
)(
 input wire clk,rst_n,
 input wire land_v,input wire [13:0] land_a,input wire [511:0] land_d,
 input wire [85:0] hc_head, // dsfd_sp_hc_c t_head: {valid,accepted,descriptor84}
 input wire hc_done_v,input wire [7:0] hc_done_tag,
 input wire normal_inputs_present,
 output wire hc_inputs_present,
 input wire [S_RD-1:0] hc_rq_v,input wire [S_RD*14-1:0] hc_rq_row,
 output wire [S_RD-1:0] hc_rs_v,output wire [S_RD*512-1:0] hc_rs_d,
 output wire [S_RD-1:0] vm_rq_v,output wire [S_RD*14-1:0] vm_rq_row,
 input wire [S_RD-1:0] vm_rs_v,input wire [S_RD*512-1:0] vm_rs_d,

 input wire [S_WR-1:0] commit_v,input wire [S_WR*14-1:0] commit_a,
 input wire [S_WR*16-1:0] commit_mask,
 output wire hop_go,
 input wire hop_re,input wire [13:0] hop_ra,
 output wire hop_vm_re,output wire [13:0] hop_vm_ra,
 output wire fault,output wire [3:0] fault_code
);
 wire hc_head_valid=hc_head[85], hc_head_slot=hc_head[83];
 wire [23:0] hc_head_arg=hc_head[30:7];
 wire is_store=hc_head[84] && hc_head_arg[23:20]==1;
 wire store_base_ok=hc_head_arg[13:0]==14'(TXB+(hc_head_slot?XW:0));
 wire store_accept=is_store && store_base_ok;
 reg bind_fault;
 always @(posedge clk or negedge rst_n)
   if(!rst_n) bind_fault<=0; else if(is_store && !store_base_ok) bind_fault<=1;
 wire store_slot=hc_head_slot;
 wire landing_head=hc_head_valid && hc_head_arg[23:20]==0 &&
   hc_head_arg[13:0]==14'(RXB+(hc_head_slot?XW:0));
 // A landing H_LOAD may start at the HEADER. hland itself withholds responses
 // until the matching rows land. Post-Engram or other bases keep normal gating.
 reg [1:0] h_resident, load_pending;
 reg [6:0] load_tag[0:1];
 // Match the actual returned completion, never an issue event or delay price.
 // The cseq serializes H_STORE behind the prior H operation. Its fixed forward
 // bus preserves order even when that operation completes before leaf drain.
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n)begin h_resident<=0;load_pending<=0;load_tag[0]<=0;load_tag[1]<=0;end
   else begin
     if(hc_done_v && load_pending[hc_done_tag[7]] && load_tag[hc_done_tag[7]]==hc_done_tag[6:0])begin
       h_resident[hc_done_tag[7]]<=1;load_pending[hc_done_tag[7]]<=0;
     end
     if(hc_head[84] && hc_head_arg[23:20]==0)begin
       h_resident[hc_head_slot]<=0;load_pending[hc_head_slot]<=1;load_tag[hc_head_slot]<=hc_head[6:0];
     end
   end
 end
 wire resident_store=hc_head_valid && hc_head_arg[23:20]==1 && h_resident[hc_head_slot];
 assign hc_inputs_present=landing_head || resident_store || normal_inputs_present;
 wire lf,tf;wire [3:0] lc,tc;
 wire [31:0] stream_count,vm_count;
 wire [2*$clog2(XW+1)-1:0] committed;
 ot_s81_hc_hland #(.XW(XW),.RXB(RXB),.S_RD(S_RD),.FD(16)) landing(
 .clk(clk),.rst_n(rst_n),.lw_v(land_v),.lw_a(land_a),.lw_d(land_d),
 .h_rq_v(hc_rq_v),.h_rq_row(hc_rq_row),.h_rs_v(hc_rs_v),.h_rs_d(hc_rs_d),
 .v_rq_v(vm_rq_v),.v_rq_row(vm_rq_row),.v_rs_v(vm_rs_v),.v_rs_d(vm_rs_d),
 .fault(lf),.fault_code(lc),.st_stream(stream_count),.st_vm(vm_count));
 ot_s81_htransfer #(.XW(XW),.TXB(TXB),.S_WR(S_WR),.HWM(HWM),.DEPTH(HDEPTH)) store(
 .clk(clk),.rst_n(rst_n),.store_begin(store_accept),.store_slot(store_slot),
 .wr_v(commit_v),.wr_a(commit_a),.wr_mask(commit_mask),.hop_go(hop_go),
 .hop_re(hop_re),.hop_ra(hop_ra),.vm_re(hop_vm_re),.vm_ra(hop_vm_ra),
 .fault(tf),.fault_code(tc),.committed_rows(committed));
 assign fault=lf||tf||bind_fault;
 assign fault_code=bind_fault?4'd5:lf?lc:tc;
endmodule
