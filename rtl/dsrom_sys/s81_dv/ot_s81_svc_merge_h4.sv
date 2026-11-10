`timescale 1ns/1ps
// R5 provider cut: four independent heads, unchanged per-head binary-counter
// ring/reduction order. Each provider clones the original head-zero tag chain.
// Production H8: DPT=8, MLEV=5, FPL=4, F12=1; 1+MLEV*FPL=21 cycles.
(* keep_hierarchy = 1 *)
module ot_s81_svc_merge_h4 #(
    parameter integer DPT=8, MLEV=5, FPL=4, F12=1
)(
    input wire clk,rst_n,iv,ifin,
    input wire [MLEV-1:0] iblk,
    input wire [127:0] iy,
    input wire [3:0] if_,
    output wire ov,
    output wire [127:0] oy,
    output wire [3:0] of_
);
    ot_hdc_v41x_attn_merge_x #(.H(4),.DPT(DPT),.MLEV(MLEV),.FPL(FPL),.F12(F12)) u_merge
      (.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),.iblk(iblk),.iy(iy),.if_(if_),.ov(ov),.oy(oy),.of_(of_));
endmodule

// Logical H8 drop-in. Provider boundary flops are separately priced when hardened;
// this source cut adds zero cycles to the native H8 merge interface.
module ot_s81_svc_merge_h8_split #(
    parameter integer DPT=8, MLEV=5, FPL=4, F12=1
)(
    input wire clk,rst_n,iv,ifin,
    input wire [MLEV-1:0] iblk,
    input wire [255:0] iy,
    input wire [7:0] if_,
    output wire ov,
    output wire [255:0] oy,
    output wire [7:0] of_
);
    wire [1:0] ov_h;
    genvar h;
    generate for(h=0;h<2;h=h+1)begin:g_h4
        ot_s81_svc_merge_h4 #(.DPT(DPT),.MLEV(MLEV),.FPL(FPL),.F12(F12)) u_h4
          (.clk(clk),.rst_n(rst_n),.iv(iv),.ifin(ifin),
`ifdef OT_SVC_MERGE_H4_MUT
           .iblk(h==1 ? iblk^{{(MLEV-1){1'b0}},1'b1} : iblk), // bench-only negative control
`else
           .iblk(iblk),
`endif
           .iy(iy[h*128+:128]),.if_(if_[h*4+:4]),.ov(ov_h[h]),.oy(oy[h*128+:128]),.of_(of_[h*4+:4]));
    end endgenerate
    assign ov=ov_h[0];
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_n && ov_h[0]!==ov_h[1]) $fatal(1,"H4 provider valid divergence");
`endif
endmodule
