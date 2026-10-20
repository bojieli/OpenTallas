`timescale 1ns/1ps
// Internal chunk operand+bank skew. This is not a standalone physical tile.
// The enclosing chunk supplies registered data pins. Exactly D capture edges:
// write at t, read at t+D-2, registered capture at t+D-1.
// Packet validity is real epoch/fill state; no uninitialized SRAM word is valid.
(* keep_hierarchy *)
module ot_s81svc7_skew_sram #(
    parameter integer W=21,
    parameter integer D=5
) (
    input wire clk,rst_n,iv,
    input wire [W-1:0] i,
    output wire ov,
    output wire [W-1:0] o
);
    (* keep *) reg reset0,run_c,run_q;
    always @(posedge clk) begin
        reset0<=rst_n;
        run_c<=reset0;
        run_q<=reset0;
    end
    reg [4:0] wc;
    reg [5:0] fill;
    always @(posedge clk) begin
        if(!run_c) begin wc<=0;fill<=0;end
        else begin wc<=wc+5'd1;if(fill<D)fill<=fill+6'd1;end
    end
    `ifdef SVC7_SKEW_MUT_ADDR
    wire [4:0] r_addr=wc-(D-3);
`else
    wire [4:0] r_addr=wc-(D-2);
`endif
    wire [63:0] rd;
    ot_sram_1r1w_32x64_m1 u_mem(
        .clk(clk),.r_ce_in(run_c),.r_addr_in(r_addr),.rd_out(rd),
        .w_ce_in(run_c),.w_addr_in(wc),
        .wd_in({{(63-W){1'b0}},iv,i}),.w_mask_in(64'hffffffffffffffff));
    reg [W:0] q;
    always @(posedge clk) begin
        if(!run_q)q<=0;
        `ifdef SVC7_SKEW_MUT_FILL
        else q<=rd[W:0];
`else
        else if(fill>=D-1)q<=rd[W:0];
        else q<=0;
`endif
    end
    assign {ov,o}=q;
`ifndef SYNTHESIS
    initial begin
        if(W<1 || W>63)$fatal(1,"SVC7_SKEW_W");
        if(D<3 || D>31)$fatal(1,"SVC7_SKEW_D");
    end
`endif
endmodule
