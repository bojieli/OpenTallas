// PRIVATE SVC hardening cut: preserve the exact per-head arithmetic and tag order.
// Existing merge_x duplicates all tags per head; use contiguous head groups as macros.
// No additional datapath/reset stages. Parent source/clock/plan adoption is separate.
module codex_svc_merge_head_groups #(
    parameter integer H=16, GROUP=4, DPT=8, MLEV=5, FPL=5, F12=1, MUT=0
)(
    input wire clk, rst_n, iv, ifin,
    input wire [MLEV-1:0] iblk,
    input wire [H*32-1:0] iy,
    input wire [H-1:0] if_,
    output wire ov,
    output wire [H*32-1:0] oy,
    output wire [H-1:0] of_
);
    localparam integer NG=H/GROUP;
    wire [NG-1:0] ovs;
    genvar g;
    generate for(g=0;g<NG;g=g+1)begin:g_head
        wire [GROUP*32-1:0] data_in=iy[g*GROUP*32+:GROUP*32];
        wire [GROUP*32-1:0] used_data=(MUT==1 && g==NG-1)?data_in^{1'b1,{(GROUP*32-1){1'b0}}}:data_in;
        wire used_iv=(MUT==2 && g==NG-1)?1'b0:iv;
        ot_hdc_v41x_attn_merge_x #(.H(GROUP),.DPT(DPT),.MLEV(MLEV),.FPL(FPL),.F12(F12)) u_native(
            .clk(clk),.rst_n(rst_n),.iv(used_iv),.ifin(ifin),.iblk(iblk),
            .iy(used_data),.if_(if_[g*GROUP+:GROUP]),.ov(ovs[g]),
            .oy(oy[g*GROUP*32+:GROUP*32]),.of_(of_[g*GROUP+:GROUP]));
    end endgenerate
    // Original ov is head0's replicated control. Keep that exact representative.
    assign ov=ovs[0];
endmodule
