// MEM v2 (S81 svc fit 2026-11-03): ot_t7_land_capture_candidate with 12 x ot_sram_1r1w_160x256_m1_r0c0.
// DISABLED T7 LAND data-cut child (TOK-DS-3, 2026-11-02): normal form of land_candidate.sv MUT=0, no mutant/test state.
// Replaces the native 640x256 land helper (4c805), the rowword/kc_w composition and the 1060-bit ekv_w capture.
// 12 x ot_sram_1r1w_256x256_m2_r2c2 [writer PC0/PC1/ROWS][bank r&3] + reset-free 640x2 latest-writer table + 4x10-bit
// per-lane code (0..767 {writer,scale} window, 768..770 needed-compressed writer, 771 ignored, 772 invalid).
// Inputs valid/win/need/scale are the parent's existing per-lane compares, need expression and scale shifter.
module ot_t7_land_capture_v2 (
    input  wire          clk,
    input  wire [223:0]  WR_ADDR,
    input  wire [1791:0] WR_DATA,
    input  wire [1791:0] WR_EN,
    input  wire [9:0]    rc,
    input  wire [3:0]    valid,
    input  wire [3:0]    win,
    input  wire [3:0]    need,
    input  wire [31:0]   scale,
    output wire [1059:0] q
);
    wire [6:0] se;
    for (genvar s = 0; s < 7; s = s + 1) begin : g_se
        assign se[s] = WR_EN[256*s];
    end
    wire [2:0]   ch_en = {se[6], se[3] | se[4] | se[5], se[0] | se[1] | se[2]};
    wire [9:0]   ch_row [0:2];
    wire [255:0] ch_d   [0:2];
    assign ch_row[0] = se[0] ? {2'd0, WR_ADDR[7:0]}   : WR_ADDR[41:32];
    assign ch_row[1] = se[3] ? {2'd0, WR_ADDR[103:96]} : WR_ADDR[137:128];
    assign ch_row[2] = WR_ADDR[201:192];
    assign ch_d[0] = se[0] ? WR_DATA[255:0]    : se[1] ? WR_DATA[511:256]   : WR_DATA[767:512];
    assign ch_d[1] = se[3] ? WR_DATA[1023:768] : se[4] ? WR_DATA[1279:1024] : WR_DATA[1535:1280];
    assign ch_d[2] = WR_DATA[1791:1536];
    wire [2:0] w_ok;
    for (genvar c = 0; c < 3; c = c + 1) begin : g_ok
        assign w_ok[c] = ch_en[c] && (ch_row[c] < 10'd640);
    end
    wire [9:0] rbase = rc - 10'd1;
    wire [255:0] mq [0:11];
    // rows 160..255 of the old 256-row master are never written (ch_row < 640) and read their zero start
    wire r_in = rbase[7:0] < 8'd160;
    reg  r_in_q;
    always @(posedge clk) r_in_q <= r_in;
    for (genvar w = 0; w < 3; w = w + 1) begin : g_w
        for (genvar b = 0; b < 4; b = b + 1) begin : g_b
            wire [255:0] mraw;
            ot_sram_1r1w_160x256_m1_r0c0 ram (
                .clk(clk), .r_ce_in(1'b1), .r_addr_in(r_in ? rbase[7:0] : 8'd0), .rd_out(mraw),
                .w_ce_in(w_ok[w] && ch_row[w][1:0] == b), .w_addr_in(ch_row[w][9:2]),
                .wd_in(ch_d[w]), .w_mask_in({256{1'b1}}));
            assign mq[4*w+b] = mraw & {256{r_in_q}};
        end
    end
    reg [1:0] lvt [0:639];
    always @(posedge clk) begin
        if (w_ok[0]) lvt[ch_row[0]] <= 2'd0;
        if (w_ok[1]) lvt[ch_row[1]] <= 2'd1;
        if (w_ok[2]) lvt[ch_row[2]] <= 2'd2;
    end
    reg [9:0] mcode [0:3];
    for (genvar j = 0; j < 4; j = j + 1) begin : g_lane
        wire [31:0] row = 4 * (32'(rc) - 1) + j;
        wire [1:0]  wr  = (row < 32'd640) ? lvt[row[9:0]] : 2'd0;
        always @(posedge clk)
            mcode[j] <= !valid[j] ? 10'd772 : win[j] ? {wr, scale[8*j +: 8]} : need[j] ? 10'd768 + 10'(wr) : 10'd771;
        wire [9:0]   c   = mcode[j];
        wire [1:0]   sel = (c < 10'd768) ? c[9:8] : (c < 10'd771) ? 2'(c - 10'd768) : 2'd0;
        wire [255:0] l   = (sel == 2'd0) ? mq[j] : (sel == 2'd1) ? mq[4+j] : mq[8+j];
        assign q[265*j +: 265] = (c < 10'd768) ? {1'b0, c[7:0], l} :
                                 (c < 10'd771) ? {1'b1, 120'd0, l[143:0]} :
                                 (c == 10'd771) ? {1'b1, 264'd0} : 265'd0;
    end
endmodule
