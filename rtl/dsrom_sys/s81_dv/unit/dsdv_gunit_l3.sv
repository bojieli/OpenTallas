`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l3 -- G-unit leaf L3 (bottom, S face = the unit's s_3S rung pins): routing-weight
// normalisation and the two weight CTL rows.
//     w_j = mul(div(scores[ids[j]], add(seqsum(scores[ids]), 1e-20)), route_scale)        ot_s81_su_rw (unchanged)
// Operand rows come from L1 (rw_*: the ids row, then ceil(ne / 16) unbiased score rows, one a cycle, with the job's
// route_scale / row / masks); the weights go back to L1 (merged there into the router CTL toward L2) as
//     row + 1 mask 1111 {w3, w2, w1, w0}, then on the next edge row + 2 mask 0011 {w5, w4}.
// The rung passes through (2 edges each way).  Every input lands in a flop; every output leaves a flop.
// MUT (bench only): 4 = ot_s81_su_rw MUT 4 (route_scale skipped).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l3 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // N face (L1)
    input  wire [275:0]  rn_i,  output wire [275:0] rn_o,
    input  wire          rw_st, input wire rw_v, input wire rw_l, input wire [511:0] rw_x,
    input  wire [31:0]   rw_scale, input wire [9:0] rw_row, input wire [4:0] rw_lm, input wire [15:0] rw_sm,
    input  wire [3:0]    sid_i,
    output reg           w_v, output reg [275:0] w_b, output reg fault,
    // S face (unit pins, s_3S)
    output wire [275:0]  vo_s,  input wire [275:0] vi_s
);
    localparam integer V = 276, K = 6;
    // S81-NATIVE3 (10-17, NATIVE-2 audit: rst_n 447.5 ps capture): rst_n drives only a local reset relay (2 sync + 1 tree
    // stage per region, release +3 edges): rung pass / operand capture / su_rw / weight output each reset from their copy.
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_p = rsv[0], rs_i = rsv[1], rs_w = rsv[2], rs_o = rsv[3];
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rs_p), .d(rn_i), .q(vo_s));
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rs_p), .d(vi_s), .q(rn_o));
    reg st_q, v_q, l_q; reg [511:0] x_q; reg [31:0] sc_q; reg [9:0] row_q, row_c; reg [4:0] lm_q, lm_c; reg [15:0] sm_q, sm_c; reg [3:0] sid_q;
    always @(posedge clk or negedge rs_i)
        if (!rs_i) begin st_q <= 1'b0; v_q <= 1'b0; end else begin st_q <= rw_st; v_q <= rw_v; end
    always @(posedge clk) begin
        l_q <= rw_l; x_q <= rw_x; sc_q <= rw_scale; sid_q <= sid_i;
        row_c <= rw_row; lm_c <= rw_lm; sm_c <= rw_sm;
        if (st_q) begin row_q <= row_c; lm_q <= lm_c; sm_q <= sm_c; end
    end
    wire o_v; wire [511:0] o_d; wire [15:0] o_m; wire f_rw;
    ot_s81_su_rw #(.MUT(MUT == 4 ? 4 : 0), .KMAX(8)) u_rw (.clk(clk), .rst_n(rs_w), .start(st_q), .k_i(K[3:0]),
        .scale_i(sc_q), .off_i(4'd0), .i_v(v_q), .i_x(x_q), .i_last(l_q), .o_v(o_v), .o_d(o_d), .o_m(o_m), .fault(f_rw));
    function automatic [V-1:0] ctl(input [9:0] a, input [3:0] m, input [127:0] d, input [15:0] sm, input [4:0] lm,
                                   input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = m; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    reg e2, e3; reg [191:0] wq;
    // S81-KITS-RTLB 10-24 (owner: register every pin, in RTL): fault leaves a pin-only flop loaded with the
    // kept sticky state's next value (fault == flt_s every cycle, 0 cycles); before, the sticky flop fed its own D.
    (* keep *) reg flt_s;
    wire flt_n = flt_s | f_rw;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin e2 <= 1'b0; e3 <= 1'b0; w_v <= 1'b0; fault <= 1'b0; flt_s <= 1'b0; end
        else begin
            e2 <= o_v; e3 <= e2; w_v <= e2 || e3;
            flt_s <= flt_n;
`ifdef OT_RTLB_PINFLOP_MUT
            fault <= flt_s;                                // mutant: pin flop one edge late (current state, not next)
`else
            fault <= flt_n;
`endif
        end
    always @(posedge clk) begin
        if (o_v) wq <= o_d[191:0];
        w_b <= e2 ? ctl(row_q + 10'd1, 4'hf, wq[127:0], sm_q, lm_q, sid_q)
           : e3 ? ctl(row_q + 10'd2, 4'h3, {64'd0, wq[191:128]}, sm_q, lm_q, sid_q) : {V{1'b0}};
    end
endmodule
