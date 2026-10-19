`timescale 1ns/1ps
// el1011-q-coll 2026-10-11: one hardened all-reduce lane slice (4 x 32-bit lanes = 128 bits of every source word): the
// rank-order fold ((p0 + p1) + p2) + p3 for its bits, with its own skew lines, LAT adders, valid chain (from its lane 0:
// deterministic, identical in every slice), partial error OR chain and reset leaf (control only; no datapath reset
// added).  SEAM = 1: every input lands in a pin flop and every output leaves a flop (+2 edges).
module ot_coll_fold_slice #(parameter integer N = 4, parameter integer ADD_LAT = 7, parameter integer SEAM = 1) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             red_in,
    input  wire [N*128-1:0] src,
    output wire [127:0]     sum,
    output wire             v_out,
    output wire             e_out
);
    wire rs;
    (* keep_hierarchy *) ot_coll_rst_leaf u_rs (.clk(clk), .arst_n(rst_n), .q(rs));
    wire             vi;
    wire [N*128-1:0] di;
    generate if (SEAM != 0) begin : g_si
        reg vq; reg [N*128-1:0] dq;
        always @(posedge clk or negedge rs) if (!rs) vq <= 1'b0; else vq <= red_in;
        always @(posedge clk) dq <= src;
        assign vi = vq; assign di = dq;
    end else begin : g_sw
        assign vi = red_in; assign di = src;
    end endgenerate
    wire [127:0] sm [0:N-1];
    wire [N-1:0] sv, se;
    assign sm[0] = di[127:0];
    assign sv[0] = vi;
    assign se[0] = 1'b0;
    genvar g, l;
    generate for (g = 1; g < N; g = g + 1) begin : g_st
        wire [127:0] pg;
        if (g == 1) begin : g_nd
            assign pg = di[128 +: 128];
        end else begin : g_d
            localparam integer D = (g - 1) * ADD_LAT;
            reg [128*D-1:0] dl;
            always @(posedge clk) dl <= {dl[128*(D-1)-1:0], di[g*128 +: 128]};
            assign pg = dl[128*D-1 -: 128];
        end
        reg [ADD_LAT-1:0] edl;
        always @(posedge clk or negedge rs) if (!rs) edl <= 0; else edl <= {edl[ADD_LAT-2:0], se[g-1]};
        wire [3:0] lv;
        wire [7:0] le;
        for (l = 0; l < 4; l = l + 1) begin : g_lane
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                .clk(clk), .rst_n(rs), .valid_in(sv[g-1]),
                .a(sm[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                .y(sm[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
        end
        assign sv[g] = lv[0];
        assign se[g] = (|le) || edl[ADD_LAT-1];
    end endgenerate
    generate if (SEAM != 0) begin : g_so
        reg [127:0] sq; reg vq, eq;
        always @(posedge clk) sq <= sm[N-1];
        always @(posedge clk or negedge rs) if (!rs) begin vq <= 1'b0; eq <= 1'b0; end else begin vq <= sv[N-1]; eq <= se[N-1]; end
        assign sum = sq; assign v_out = vq; assign e_out = eq;
    end else begin : g_sw2
        assign sum = sm[N-1]; assign v_out = sv[N-1]; assign e_out = se[N-1];
    end endgenerate
endmodule
