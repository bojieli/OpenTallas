// KV-CDC2 (2026-10-18): leaf-local CDC fork of rtl/qwen_sys/host_20261013/qkd_host_qm_credit_pacer.sv for the HOST-cluster CDC leaves (qkd_hr_cdc_host /
// qkd_hr_ingest_qm, tools/qwen_kv_die/host_cluster/gen_cluster.py FORKS). The shared original is unchanged (it binds
// the closed core children and the flat root). Same ports and parameters as the original. Change: the clk_h registers take rst_n through an ot_reset_sync on clk_h
// (the raw core-family reset no longer releases host flops asynchronously).

`timescale 1ns/1ps
// QM returns a count of freed host-FIFO entries, sometimes several at once.
// Terminate that count in its OWN clk_h domain. The dedicated CDC output face
// promises four slots; exactly one reserved-slot credit can return per cycle.
// No binary count bus crosses clocks and capacity never means write commit.
module qkd_hr_qm_credit_pacer_cdc #(parameter integer MUT=0)(
 input wire clk_h,rst_n,in_v,input wire[4:0]in_crn,
 output reg out_cr,output reg fault
);
 reg vq;reg[4:0]cq;reg[3:0]owed,pending;
 wire pulse=!fault&&pending!=0;
 wire[5:0]next_pending={2'd0,pending}+{1'b0,cq}-6'(pulse);
 wire[5:0]next_owed={2'd0,owed}+6'(vq)-{1'b0,cq};
 // the reset arrives from the core family: assert asynchronously, release synchronised to clk_h
 wire rn_h;
 ot_reset_sync u_rsh(.clk(clk_h),.async_rst_n(rst_n),.sync_rst_n(rn_h));
 always @(posedge clk_h or negedge rn_h)begin
  if(!rn_h)begin vq<=0;cq<=0;owed<=0;pending<=0;out_cr<=0;fault<=0;end
  else begin
   vq<=in_v;cq<=in_crn;out_cr<=pulse;
   if((cq>{1'b0,owed}+5'(vq))||next_pending>4||next_owed>4)fault<=1;
   else begin owed<=next_owed[3:0];pending<=next_pending[3:0];end
   if(MUT==1)out_cr<=!fault&&cq!=0; // loses all but one of batched returns
  end
 end
endmodule
