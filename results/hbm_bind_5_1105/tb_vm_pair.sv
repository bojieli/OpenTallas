`timescale 1ns/1ps
module tb; reg clk=0, rst_n=0; always #1 clk=~clk;
 reg av=0,bv=0; reg [15:0] as=0,bs=0; reg wa=0,wb=0; wire [16:0] rq; wire [280:0] wq; wire arv,brv,coll; wire [255:0] ard,brd;
 reg [256:0] pipe [0:5]; integer i, err=0, reads=0;
 ot_hnx_fused_vm_pair u(.clk(clk),.rst_n(rst_n),.a_rq_v(av),.a_rq_s(as),.a_wq_v(wa),.a_wq_s(as),.a_wq_d({240'd0,as}),.a_rr_v(arv),.a_rr_d(ard),.b_rq_v(bv),.b_rq_s(bs),.b_wq_v(wb),.b_wq_s(bs),.b_wq_d({240'd0,bs}),.b_rr_v(brv),.b_rr_d(brd),.rq0(rq),.wq0(wq),.rr0(pipe[5]),.coll(coll));
 reg [1:0] who [0:5]; // bank model: response n+6
 initial begin for(i=0;i<6;i=i+1) begin pipe[i]=0; who[i]=0; end
  repeat(4) @(posedge clk); #0.1 rst_n=1;
  repeat(2000) begin @(negedge clk); {av,bv}=0; {wa,wb}=0;
   case($urandom%4) 0: begin av=1; as=$urandom; end 1: begin bv=1; bs=$urandom; end endcase
   case($urandom%3) 0: begin wa=1; as=$urandom; end 1: begin wb=1; bs=$urandom; end endcase
   @(posedge clk); #0.1;
   if(arv && who[5]!=1) err=err+1; if(brv && who[5]!=2) err=err+1; if(pipe[5][256] && !arv && !brv) err=err+1;
   if(arv && ard!==pipe[5][255:0]) err=err+1; if(brv && brd!==pipe[5][255:0]) err=err+1;
   if(arv||brv) reads=reads+1;
  end
  $display("reads %0d err %0d", reads, err); if(err==0 && reads>500) $display("PASS"); else $display("FAIL"); $finish; end
 always @(posedge clk) begin for(i=5;i>0;i=i-1) begin pipe[i]<=pipe[i-1]; who[i]<=who[i-1]; end
  pipe[0]<= {rq[16], 240'd0, rq[15:0]} & {257{rq[16]}}; who[0]<= av?1:(bv?2:0); end
endmodule
