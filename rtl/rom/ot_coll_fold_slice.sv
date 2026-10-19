`timescale 1ns/1ps
// el1011-q-coll 2026-10-11: one hardened all-reduce lane slice (4 x 32-bit lanes = 128 bits of every source word): the
// rank-order fold ((p0 + p1) + p2) + p3 for its bits, with its own skew lines, LAT adders, valid chain (from its lane 0:
// deterministic, identical in every slice), partial error OR chain and reset leaf (control only; no datapath reset
// added).  SEAM = 1: every input lands in a pin flop and every output leaves a flop (+2 edges).
// QW-CLUSTER3 safe3 (2026-10-19, opt-in, defaults = original): DLRING=1 puts every skew delay line (D = (g-1)*ADD_LAT
// >= 2 edges) in a fixed-offset SRAM ring (ot_coll_nring, same D-edge age, no flop->flop hold chains); NLIVE < N ties the
// constant-zero sources g >= NLIVE to 0 directly (their delay lines only ever held 0); ADRST=0 resets only the adders'
// valid bits (data reset off, outputs consumed only when valid); RSTSPLIT=1 gives the seam and every fold stage its own
// two-flop reset leaf (all leaves fed by the same rst_n and released on the same edge; each <= 32 sinks).
module ot_coll_fold_slice #(parameter integer N = 4, parameter integer ADD_LAT = 7, parameter integer SEAM = 1,
                            parameter integer DLRING = 0, parameter integer NLIVE = N, parameter integer ADRST = `ifdef OT_FP_DATA_NORST 0 `else 1 `endif,
                            parameter integer RSTSPLIT = 0) (
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
    wire [N-1:0] rsg;   // per-stage reset (RSTSPLIT: own leaf per stage, else the slice leaf)
    genvar gr;
    generate for (gr = 0; gr < N; gr = gr + 1) begin : g_rsg
        if (RSTSPLIT != 0 && gr > 0) begin : g_l
            (* keep_hierarchy *) ot_coll_rst_leaf u_rs (.clk(clk), .arst_n(rst_n), .q(rsg[gr]));
        end else begin : g_s
            assign rsg[gr] = rs;
        end
    end endgenerate
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
        if (g >= NLIVE) begin : g_z
            assign pg = 128'd0;
        end else if (g == 1) begin : g_nd
            assign pg = di[128 +: 128];
        end else if (DLRING != 0) begin : g_dr
            // pg = di[g] sampled D edges earlier, exactly as the D-deep shift line (ring rd valid OFF = D edges after wd)
`ifdef OT_COLL_FOLD_MUT_DR
            localparam integer DOFF = (g - 1) * ADD_LAT - 1;   // negative control: ring one edge short
`else
            localparam integer DOFF = (g - 1) * ADD_LAT;
`endif
            ot_coll_nring #(.OFF(DOFF), .W(128), .ID(900 + g)) u_dr (.clk(clk), .rs_n(rsg[g]),
                .wd(di[g*128 +: 128]), .rd(pg));
        end else begin : g_d
            localparam integer D = (g - 1) * ADD_LAT;
            reg [128*D-1:0] dl;
            always @(posedge clk) dl <= {dl[128*(D-1)-1:0], di[g*128 +: 128]};
            assign pg = dl[128*D-1 -: 128];
        end
        reg [ADD_LAT-1:0] edl;
        always @(posedge clk or negedge rsg[g]) if (!rsg[g]) edl <= 0; else edl <= {edl[ADD_LAT-2:0], se[g-1]};
        wire [3:0] lv;
        wire [7:0] le;
        for (l = 0; l < 4; l = l + 1) begin : g_lane
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(ADRST)) u_add (
                .clk(clk), .rst_n(rsg[g]), .valid_in(sv[g-1]),
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
