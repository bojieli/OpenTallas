module fmem_dut #(parameter integer W = 128, parameter integer BYP = 1) (
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
    localparam integer NB = (W + 31) / 32;
    wire [NM+NB:0] write_leaf;
`ifdef OT_S81_ATTW_ENABLE_R4
    // Same-cycle write enable copies: 32 captured bits per leaf, one per SRAM bank.
    ot_s81_attw_reset_fork #(.N(NM+NB+1)) u_write_fork (.d(we), .q(write_leaf));
`else
    assign write_leaf = {(NM+NB+1){we}};
`endif
    genvar b;
    generate for (b = 0; b < NM; b = b + 1) begin : g_m
        ot_sram_1r1w_32x128_m1 u_m (.clk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(q[128*b +: 128]),
            .w_ce_in(write_leaf[b]), .w_addr_in(wa), .wd_in(wdp[128*b +: 128]), .w_mask_in({128{1'b1}}));
    end
    if (BYP != 0) begin : g_byp
        reg byp; reg [W-1:0] bd;
        wire [NB-1:0] bypass_leaf;
`ifdef OT_S81_ATTW_ENABLE_R4
        ot_s81_attw_reset_fork #(.N(NB)) u_bypass_fork (.d(byp), .q(bypass_leaf));
`else
        assign bypass_leaf = {NB{byp}};
`endif
        always @(posedge clk) byp <= write_leaf[NM+NB] && wa == ra;
        for (genvar word_i=0; word_i<NB; word_i=word_i+1) begin : g_word
            localparam integer CW = ((W-32*word_i) < 32) ? W-32*word_i : 32;
            always @(posedge clk) if (write_leaf[NM+word_i]) bd[32*word_i +: CW] <= wd[32*word_i +: CW];
            assign rd[32*word_i +: CW] = bypass_leaf[word_i] ? bd[32*word_i +: CW] : q[32*word_i +: CW];
        end
    end else begin : g_nobyp
        assign rd = q[W-1:0];
    end endgenerate
endmodule
