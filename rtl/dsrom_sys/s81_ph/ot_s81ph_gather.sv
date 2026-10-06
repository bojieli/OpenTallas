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
    generate for (g = 0; g < NR; g = g + 1) begin : g_r
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
    end endgenerate
    reg [NR-1:0] cflt;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin g_fault <= 1'b0; g_busy <= 1'b0; g_live <= 1'b0; cflt <= {NR{1'b0}}; end
        else begin
            for (i = 0; i < NR; i = i + 1) cflt[i] <= rf[i] | (lane_v[i] & lane_w[68*i + 67]);
            g_fault <= g_fault | (|cflt);
            for (i = 0; i < NT; i = i + 1) if (trunk_st[2*i + 1]) g_fault <= 1'b1;
            g_busy <= |busy_l;
            g_live <= &{trunk_st[22], trunk_st[20], trunk_st[18], trunk_st[16], trunk_st[14], trunk_st[12],
                        trunk_st[10], trunk_st[8], trunk_st[6], trunk_st[4], trunk_st[2], trunk_st[0]};
        end
    end
    initial if (NT != 12) $fatal(1, "ot_s81ph_gather: 12 trunks");
endmodule
