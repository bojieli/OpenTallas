// Frozen hardware reference from531642618; component equivalence only.
module bfqg_reference (
    input  wire               clk, clk_n, clk_s,
    input  wire               clk_m0, clk_m1, clk_m2, clk_m3, clk_m4, clk_m5, clk_m6, clk_m7,
    input  wire               rst_n,
    input  wire [1023:0]      c_d,
    input  wire               wce,
    input  wire               mhi, mlo,
    input  wire [6:0]         wa,
    input  wire [7:0]         r_ce,
    input  wire [6:0]         r_a,
    output reg  [255:0]       rwq
);
    wire [7:0] cm = {clk_m7, clk_m6, clk_m5, clk_m4, clk_m3, clk_m2, clk_m1, clk_m0};
    wire [0:0] rn_l;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn_l));
    (* keep = 1 *) reg mask_hi, mask_lo;
    always @(posedge clk) begin mask_hi <= mhi; mask_lo <= mlo; end
    (* keep = 1 *) reg [1023:0] cdq; (* keep = 1 *) reg [6:0] wa_q, ra_q;
    always @(posedge clk_n) cdq <= c_d;
    always @(posedge clk) begin wa_q <= wa; ra_q <= r_a; end
    (* keep = 1 *) reg wce_q;
    always @(posedge clk or negedge rn_l[0]) if (!rn_l[0]) wce_q <= 1'b0; else wce_q <= wce;
    wire [255:0] cap [0:7];
    genvar gt;
    generate for (gt = 0; gt < 8; gt = gt + 1) begin : g_t
        (* keep = 1 *) reg rp_ce; reg rp_sel;
        wire [255:0] wp_d = {cdq[gt*128 +: 128], cdq[gt*128 +: 128]};
        wire [255:0] wp_m = {{128{mask_hi}}, {128{mask_lo}}};
        reg [255:0] cq;
        wire [255:0] rd;
        always @(posedge clk or negedge rn_l[0]) begin
            if (!rn_l[0]) begin rp_ce <= 1'b0; rp_sel <= 1'b0; end
            else begin rp_ce <= r_ce[gt]; rp_sel <= rp_ce; end
        end
        always @(posedge clk) begin
            cq <= rd & {256{rp_sel}};
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(cm[gt]),
            .r_ce_in(rp_ce), .r_addr_in(ra_q), .rd_out(rd),
            .w_ce_in(wce_q), .w_addr_in(wa_q), .wd_in(wp_d), .w_mask_in(wp_m),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign cap[gt] = cq;
    end endgenerate
    reg [255:0] or4a, or4b;
    always @(posedge clk) begin
        or4a <= cap[0] | cap[1] | cap[2] | cap[3];
        or4b <= cap[4] | cap[5] | cap[6] | cap[7];
    end
    always @(posedge clk_s) rwq <= or4a | or4b;
endmodule
