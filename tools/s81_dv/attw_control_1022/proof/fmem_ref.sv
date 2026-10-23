module fmem_ref #(parameter integer W = 128, parameter integer BYP = 1) (
    input  wire         clk,
    input  wire         we,
    input  wire [4:0]   wa,
    input  wire [W-1:0] wd,
    input  wire [4:0]   ra,
    output wire [W-1:0] rd
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
        reg byp; reg [W-1:0] bd;
        always @(posedge clk) begin byp <= we && wa == ra; if (we) bd <= wd; end
        assign rd = byp ? bd : q[W-1:0];
    end else begin : g_nobyp
        assign rd = q[W-1:0];
    end endgenerate
endmodule
