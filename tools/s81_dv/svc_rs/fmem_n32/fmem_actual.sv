`timescale 1ns/1ps
module dsdv_svc_fmem #(parameter integer W = 128, parameter integer BYP = 1) (
    input  wire         clk,
    input  wire         we,
    input  wire [4:0]   wa,
    input  wire [W-1:0] wd,
    input  wire [4:0]   ra,
    output wire [W-1:0] rd
`ifdef OT_SVC_FMEM_N32
    , input wire [(W+255)/256-1:0] we_reps
`endif
);
    localparam integer NM = (W + 127) / 128;
    wire [NM*128-1:0] q;
    wire [NM*128-1:0] wdp = (NM*128)'(wd);
    genvar b;
    generate for (b = 0; b < NM; b = b + 1) begin : g_m
        ot_sram_1r1w_32x128_m1 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(q[128*b +: 128]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdp[128*b +: 128]), .w_mask_in({128{1'b1}}));
    end
    if (BYP != 0) begin : g_byp
`ifdef OT_SVC_FMEM_N32
        reg [W-1:0] bd;
        always @(posedge clk) bd <= wd; // observable only under the same-edge bypass flag
        wire eq_addr = wa == ra;
        for (genvar c = 0; c < (W+7)/8; c = c+1) begin : g_chunk
            localparam integer CW = (W-8*c < 8) ? W-8*c : 8;
            wire byp;
            ot_hdc_v41x_kreg #(.W(1),.R(0)) u_flag (.clk(clk),.rst_n(1'b1),
                .d(we_reps[c/32] && eq_addr),.q(byp));
            assign rd[8*c +: CW] = byp ? bd[8*c +: CW] : q[8*c +: CW];
        end
`else
        reg byp; reg [W-1:0] bd;
        always @(posedge clk) begin byp <= we && wa == ra; if (we) bd <= wd; end
        assign rd = byp ? bd : q[W-1:0];
`endif
    end else begin : g_nobyp
        assign rd = q[W-1:0];
    end endgenerate
endmodule
