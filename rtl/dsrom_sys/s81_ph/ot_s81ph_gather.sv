`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_gather -- S81 die return gather core (CLAUDE S81-PH, 2026-10-06).  Contract:
// results/rtl/s81_ph_20261006/gather/contract.json.
//
// The S81 field column trees end in a NODE word (the column's top ot_v41_retn_w17w10 output, 66 b
// {e, d32, t32, v}), forwarded over the die return trunks.  The region roots of ot_v41_field_w17w10 (one
// ot_v41_ret_root per column, D = QD = ROOTD = 128 as the field and the S81 physical return contract) are
// therefore here: lane r (already in root order) -> u_root[r] -> one finished row per cycle per root.
// No arithmetic here: the roots are the unchanged W10 ot_v41_ret_root.  Every input is registered once before
// the root, every output is the root's own output register re-registered once (block boundary flop-to-flop).
// Column status: a lane word also carries {fault, busy} of its column FIFO; trunk status {fault, live}.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_gather #(
    parameter integer NR    = 128,
    parameter integer ROOTD = 128,
    parameter integer NT    = 12,           // trunks (status pairs)
    parameter integer ROOT_BLK = 0          // 1: each root is the hardened ot_s81ph_root_blk (own pin registers)
                                            // 2: 4 columns x 32 abutted ot_s81ph_root_tile chains (NR 128)
) (
    input  wire              clk,
    input  wire              rst_n,             // synchronised, active low
    input  wire [NR-1:0]     lane_v,            // registered lanes, root order
    input  wire [NR*68-1:0]  lane_w,            // {fault, busy, e, d32, t32, v}
    input  wire [NT*2-1:0]   trunk_st,          // {fault, live} per trunk
    output wire [NR-1:0]     row_v,
    output wire [NR*52-1:0]  row_d,             // {e, pos3, row16, fp32 32}
    output reg               g_fault,           // sticky: root fault, column fault, trunk fault
    output reg               g_busy,            // OR of the last busy seen per column
    output reg               g_live             // every trunk end live
);
    wire [NR-1:0] rv, re, rf;
    wire [NR*16-1:0] rrow;
    wire [NR*3-1:0]  rpos;
    wire [NR*32-1:0] rfp;
    reg  [NR-1:0] busy_l;
    // reset copies: one per 16 roots (kept: >= 64 loads per net otherwise)
    localparam integer NG = (NR + 15) / 16;
    (* keep *) reg [NG-1:0] rst_c;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_c <= {NG{1'b0}}; else rst_c <= {NG{1'b1}};
    genvar g;
    wire [1:0] tst_col [0:3];
    generate if (ROOT_BLK == 2) begin : g_tile
        // columns 0, 1 = roots 0..31, 32..63 (west lanes; column 1's lane passes through column 0),
        // columns 3, 2 = roots 96..127, 64..95 (east lanes; column 2's lane passes through column 3, mirrored tiles);
        // root (column c, row k) = 32 c + k; its result leaves the column top in chain slot 31 - k
        localparam integer NROW = 32;
        localparam integer CW = 53 * NROW;
        wire [69*NROW-1:0] lthru_w, lthru_e;     // lane thru: column 0 -> 1, column 3 -> 2
        genvar c, k;
        for (c = 0; c < 4; c = c + 1) begin : g_c
            wire [CW*(NROW+1)-1:0] ch;
            wire [2*(NROW+1)-1:0] fs;
            wire [NROW:0] rsc;
            assign ch[CW-1:0] = {CW{1'b0}}; assign fs[1:0] = 2'b00; assign rsc[0] = rst_c[c];
            for (k = 0; k < NROW; k = k + 1) begin : g_k
                localparam integer R = 32 * c + k;
                localparam integer RT = (c == 0) ? 32 + k : 64 + k;   // lane passed through (columns 0, 3)
                wire [68:0] li, lti, lto;
                if (c == 0 || c == 3) begin : g_own
                    assign li = {lane_w[68*R +: 68], lane_v[R]};
                    assign lti = {lane_w[68*RT +: 68], lane_v[RT]};
                    if (c == 0) begin : g_w assign lthru_w[69*k +: 69] = lto; end
                    else begin : g_e assign lthru_e[69*k +: 69] = lto; end
                end else begin : g_in
                    assign li = (c == 1) ? lthru_w[69*k +: 69] : lthru_e[69*k +: 69];
                    assign lti = 69'd0;
                end
                ot_s81ph_root_tile #(.ROOTD(ROOTD), .NS(NROW), .NL(1)) u_t (.ck(clk), .rs(rsc[k]), .rso(rsc[k+1]),
                    .li(li), .lti(lti), .lto(lto), .ci(ch[CW*k +: CW]), .co(ch[CW*(k+1) +: CW]),
                    .fi(fs[2*k +: 2]), .fo(fs[2*(k+1) +: 2]));
                assign row_v[R] = ch[CW*NROW + 53*(NROW-1-k)];
                assign row_d[52*R +: 52] = ch[CW*NROW + 53*(NROW-1-k) + 1 +: 52];
            end
            assign tst_col[c] = fs[2*NROW +: 2];
        end
        assign rv = row_v; assign rf = {NR{1'b0}};
        always @(posedge clk or negedge rst_n) if (!rst_n) busy_l <= {NR{1'b0}};
                                              else busy_l <= {{(NR-4){1'b0}}, tst_col[3][1], tst_col[2][1], tst_col[1][1], tst_col[0][1]};
    end else begin : g_roots
    for (g = 0; g < NR; g = g + 1) begin : g_r
        wire [67:0] w = lane_w[68*g +: 68];
        if (ROOT_BLK != 0) begin : g_blk
            wire [52:0] o; wire f;
            ot_s81ph_root_blk #(.ROOTD(ROOTD)) u_rb (.ck(clk), .rs(rst_c[g/16]), .i({w[65:1], lane_v[g] & w[0]}), .o(o), .f(f));
            assign rv[g] = o[0]; assign rf[g] = f;
            assign row_v[g] = o[0]; assign row_d[52*g +: 52] = o[52:1];
            always @(posedge clk or negedge rst_c[g/16]) if (!rst_c[g/16]) busy_l[g] <= 1'b0; else if (lane_v[g]) busy_l[g] <= w[66];
        end else begin : g_flat
            wire [15:0] bf_unused;
            ot_v41_ret_root #(.D(ROOTD), .QD(ROOTD)) u_root (.clk(clk), .rst_n(rst_c[g/16]),
                .i_v(lane_v[g] & w[0]), .i_t(w[32:1]), .i_d(w[64:33]), .i_e(w[65]),
                .r_v(rv[g]), .r_row(rrow[16*g +: 16]), .r_pos(rpos[3*g +: 3]), .r_fp32(rfp[32*g +: 32]),
                .r_bf16(bf_unused), .r_e(re[g]), .fault(rf[g]));
            reg rvq; reg [51:0] rdq;
            always @(posedge clk or negedge rst_c[g/16])
                if (!rst_c[g/16]) begin rvq <= 1'b0; busy_l[g] <= 1'b0; end
                else begin
                    rvq <= rv[g];
                    if (lane_v[g]) busy_l[g] <= w[66];
                end
            always @(posedge clk) rdq <= {re[g], rpos[3*g +: 3], rrow[16*g +: 16], rfp[32*g +: 32]};
            assign row_v[g] = rvq; assign row_d[52*g +: 52] = rdq;
        end
    end
        assign tst_col[0] = 2'b00; assign tst_col[1] = 2'b00; assign tst_col[2] = 2'b00; assign tst_col[3] = 2'b00;
    end endgenerate
    reg [NR-1:0] cflt;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin g_fault <= 1'b0; g_busy <= 1'b0; g_live <= 1'b0; cflt <= {NR{1'b0}}; end
        else begin
            for (i = 0; i < NR; i = i + 1) cflt[i] <= (ROOT_BLK == 2) ? (i < 4 && tst_col[i % 4][0]) : (rf[i] | (lane_v[i] & lane_w[68*i + 67]));
            g_fault <= g_fault | (|cflt);
            for (i = 0; i < NT; i = i + 1) if (trunk_st[2*i + 1]) g_fault <= 1'b1;
            g_busy <= |busy_l;
            g_live <= &{trunk_st[22], trunk_st[20], trunk_st[18], trunk_st[16], trunk_st[14], trunk_st[12],
                        trunk_st[10], trunk_st[8], trunk_st[6], trunk_st[4], trunk_st[2], trunk_st[0]};
        end
    end
    initial if (NT != 12) $fatal(1, "ot_s81ph_gather: 12 trunks");
endmodule
