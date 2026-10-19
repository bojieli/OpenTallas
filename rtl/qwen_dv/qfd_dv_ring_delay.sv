`timescale 1ns/1ps
// Small local delays use four-slot rings; at most two prefix flops account
// for residual edges. Final readers provide real same-edge state copies.
module qfd_dv_ring_delay #(parameter integer W=32,D=1,RESET=0,ID=0)(
 input wire clk,rst_n,input wire[W-1:0] d,output wire[W-1:0] q
);
 generate if(D==0) begin:g_wire assign q=d;
 end else if(D<=2) begin:g_short
  reg[W-1:0] p[0:D-1];
  always @(posedge clk) begin p[0]<=d;for(integer k=1;k<D;k=k+1)p[k]<=p[k-1];end
  assign q=p[D-1];
 end else begin:g_ring
  qfd_dv_ring_replicated #(.W(W),.D(D),.COPIES(1),.ID(ID)) u_r(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
 end endgenerate
`ifndef SYNTHESIS
 initial if(RESET!=0||W<1||W>32||D<0||D>12)$fatal(1,"SAFE_RING_DELAY unsupported shape");
`endif
endmodule
module qfd_dv_ring_replicated #(parameter integer W=1,D=7,COPIES=1,ID=0)(
 input wire clk,rst_n,input wire[W-1:0] d,output wire[COPIES*W-1:0] q
);
 localparam integer N=D/3,R=D%3,C=(W+23)/24;
 wire local_reset;
 qfd_dv_reset_tree #(.N(1)) u_rt(.ck(clk),.rst_n(rst_n),.q(local_reset));
 wire[W-1:0] stage[0:N];
 generate if(R==0) begin:g_no_prefix assign stage[0]=d;
 end else begin:g_prefix
  (* keep_hierarchy="yes" *) qfd_dv_ring_prefix #(.W(W),.D(R),.ID(ID)) u_p(.clk(clk),.d(d),.q(stage[0]));
 end
 for(genvar i=0;i<N;i=i+1) begin:g_stage
  wire[4*W-1:0] bank;wire[11:0] epo;wire[4*C-1:0] valid;
  ot_pl_land_chunk_w #(.W(W),.D(4),.CHUNK_BITS(24)) u_w(
   .ck(clk),.rsi(local_reset),.i(stage[i]),.bank(bank),.epo(epo),.vld(valid));
  if(i<N-1) begin:g_middle
   ot_pl_land_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24)) u_r(
    .ck(clk),.rsi(local_reset),.bank(bank),.epo(epo),.vld(valid),.o(stage[i+1]));
  end else begin:g_final
   for(genvar o=0;o<COPIES;o=o+1) begin:g_copy
    ot_pl_land_chunk_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(24)) u_r(
     .ck(clk),.rsi(local_reset),.bank(bank),.epo(epo),.vld(valid),.o(q[W*o+:W]));
   end
  end
 end endgenerate
`ifndef SYNTHESIS
 initial if(W<1||W>32||D<3||D>12||COPIES<1||COPIES>3)$fatal(1,"SAFE_RING_REPLICATED unsupported shape");
`endif
endmodule

// ID distinguishes real prefix captures that would otherwise merge when several
// consumers carry the same valid. Every retained output drives its own ring.
(* keep_hierarchy="yes" *) module qfd_dv_ring_prefix #(parameter integer W=1,D=1,ID=0)(input wire clk,input wire[W-1:0] d,output wire[W-1:0] q);
reg[W-1:0] p[0:D-1];
always @(posedge clk) begin p[0]<=d;for(integer k=1;k<D;k=k+1)p[k]<=p[k-1];end
assign q=p[D-1];
endmodule
