`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-2 (2026-10-17, S81-DV p4h): ot_s81_su_smq, the PER-HEAD softmax tap, successor of the 2-head SM stop tap
// ot_s81_su_smt (dsfd_su_t_smt, 73 x 346 um, 5.4k pins: native capture FAIL 266 / 319 ps on its 2,560-b parameter tap).
// One per regional service slice, beside its head's lane subtree ot_s81_su_smh.
//
// What moved: the stop tap read 5 parallel 512-b parameter slots and both heads' rows off a 16-slot spine.  Here the
// service slice delivers the head's rows on ONE 512-b row port, compiler-scheduled at fixed latency (no ready/credit):
//   r_v, r_p = 1: parameter row r_j (0: fields, 1: sinks (SE) / cos lo (SO), 2: cos hi, 3: sin lo, 4: sin hi)
//   r_v, r_p = 0: the head's operand row (SE: 16 scores, SO: 16 lanes of P.V)
// Parameters, sink selection, the cos / sin stream and the row addresses are ot_s81_su_smt's, field for field:
//   c_nv = row0[64 +: 7], c_scale = row0[96 +: 32], c_lt = row0[128 +: 3], obase = row0[13:0];
//   sink (SE) = row1[32 g +: 32] (g = cfg_g, the global head index; smt: row1[64 ti +: 64] = {head 1, head 0});
//   cos / sin pair k (k = 0..31): {cos word k, sin word k} of {row2, row1} / {row4, row3}, cs_i = k, one a cycle;
//   SE row (e): addr obase + 16 oc + g, mask FFFF;   SO row (o): addr obase + 8 oc + g / 2, this head's half
//   (mask 00FF for head 2 ti, FF00 for 2 ti + 1; smt wrote both halves of that row in one write).
// Every input lands in a flop; every output leaves a flop.  The operand row is forwarded registered with its valid, so
// the subtree takes it at DOP = SRL.
// MUT (bench mutants): 1 = sink column of the pair neighbour, 2 = SO half mask swapped, 3 = cos / sin pair off by one.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_su_smq #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_in,
    input  wire [3:0]    cfg_g,                        // global head index (0..15)
    // job and rows from the service slice
    input  wire          j_st,
    input  wire [3:0]    j_kind,
    input  wire [7:0]    j_jid,
    input  wire          r_v,
    input  wire          r_p,
    input  wire [2:0]    r_j,
    input  wire [511:0]  r_d,
    // to the head's lane subtree (ot_s81_su_smh)
    output reg           s_v,
    output reg           p_v,
    output reg           c_v,
    output reg  [6:0]    c_nv,
    output reg  [2:0]    c_lt,
    output reg  [31:0]   c_scale,
    output reg  [31:0]   c_sink,
    output reg           cs_v,
    output reg  [4:0]    cs_i,
    output reg  [63:0]   cs_d,
    output reg  [511:0]  d_o,
    // from the subtree
    input  wire          e_v,
    input  wire [511:0]  e_d,
    input  wire          o_vi,
    input  wire [255:0]  o_di,
    input  wire          den_v,
    input  wire [7:0]    f_i,
    // the head's write row and status, to the service slice
    output reg           w_v,
    output reg  [13:0]   w_a,
    output reg  [15:0]   w_m,
    output reg  [511:0]  w_d,
    output reg           o_fu, o_fo, o_alive, o_den,
    output reg  [7:0]    o_rjid
);
    localparam [3:0] K_SE = 4, K_SO = 5;
    // regional reset relay
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;

    // ------------------------------------------------------------------ pin flops
    reg          st_q, rv_q, rp_q, ev_q, ov_q, dv_q;
    reg  [3:0]   kind_q, g;
    reg  [7:0]   jid_q, f_q;
    reg  [2:0]   rj_q;
    reg  [511:0] rd_q, ed_q;
    reg  [255:0] od_q;
    always @(posedge clk) begin
        kind_q <= j_kind; jid_q <= j_jid; rj_q <= r_j; rd_q <= r_d; ed_q <= e_d; od_q <= o_di; g <= cfg_g;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin st_q <= 1'b0; rv_q <= 1'b0; rp_q <= 1'b0; ev_q <= 1'b0; ov_q <= 1'b0; dv_q <= 1'b0; f_q <= 8'd0; end
        else begin st_q <= j_st; rv_q <= r_v; rp_q <= r_p; ev_q <= e_v; ov_q <= o_vi; dv_q <= den_v; f_q <= f_i; end

    // ------------------------------------------------------------------ job, parameter rows
    reg  [3:0]   jkind;
    reg          mine, pin, pdone, ofault;
    reg  [7:0]   jid;
    reg  [2:0]   np;
    reg  [13:0]  obase;
    reg  [6:0]   nv;
    reg  [2:0]   lt;
    reg  [31:0]  scale;
    reg  [511:0] prow1, prow2, prow3, prow4;
    wire         prow = mine && rv_q && rp_q;
    wire         orow = mine && rv_q && !rp_q;
    always @(posedge clk) if (prow) begin
        if (rj_q == 3'd0) begin obase <= rd_q[13:0]; nv <= rd_q[64 +: 7]; scale <= rd_q[96 +: 32]; lt <= rd_q[128 +: 3]; end
        if (rj_q == 3'd1) prow1 <= rd_q;
        if (rj_q == 3'd2) prow2 <= rd_q;
        if (rj_q == 3'd3) prow3 <= rd_q;
        if (rj_q == 3'd4) prow4 <= rd_q;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin jkind <= 0; mine <= 0; jid <= 0; np <= 0; pin <= 0; pdone <= 0; ofault <= 0; end
        else begin
            pdone <= 1'b0;
            if (st_q) begin
                jkind <= kind_q; jid <= jid_q; mine <= (kind_q == K_SE || kind_q == K_SO);
                np <= (kind_q == K_SO) ? 3'd5 : 3'd2; pin <= 1'b0;
            end else if (prow) begin
                if (rj_q >= np) ofault <= 1'b1;                 // a parameter row the job does not have
                if (rj_q == np - 3'd1) begin pin <= 1'b1; pdone <= 1'b1; end
            end
            if (orow && !pin) ofault <= 1'b1;                   // an operand row before the job's parameters
        end
    end

    // ------------------------------------------------------------------ configuration, cos / sin stream, operand row
    wire [3:0]  gs = (MUT == 1) ? (g ^ 4'd1) : g;
    reg  [5:0]  cs_n;                                           // pairs still to stream
    wire [4:0]  ck = 5'd31 - (cs_n[4:0] - 5'd1);                // pair index this cycle (smt's cs_i)
    wire [4:0]  ckm = (MUT == 3) ? ck + 5'd1 : ck;
    wire [1023:0] cosw = {prow2, prow1}, sinw = {prow4, prow3};
    always @(posedge clk) begin
        if (pdone && jkind == K_SE) begin c_nv <= nv; c_lt <= lt; c_scale <= scale; c_sink <= prow1[32 * gs +: 32]; end
        cs_i <= ck;
        cs_d <= {cosw[32 * ckm +: 32], sinw[32 * ckm +: 32]};
        d_o <= rd_q;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s_v <= 0; p_v <= 0; c_v <= 0; cs_v <= 0; cs_n <= 0; end
        else begin
            s_v <= orow && pin && jkind == K_SE;
            p_v <= orow && pin && jkind == K_SO;
            c_v <= pdone && jkind == K_SE;
            cs_v <= cs_n != 0;
            if (pdone && jkind == K_SO) cs_n <= 6'd32;
            else if (cs_n != 0) cs_n <= cs_n - 6'd1;
        end
    end

    // ------------------------------------------------------------------ result rows (one a cycle; no staging needed)
    reg  [15:0] oc;
    reg         ufs, ovf, dn;
    wire        se_ev = ev_q && jkind == K_SE;
    wire        hi = (MUT == 2) ? ~g[0] : g[0];
    always @(posedge clk) begin
        if (ov_q) begin
            w_a <= obase + oc[13:0] * 14'd8 + {11'd0, g[3:1]};
            w_m <= hi ? 16'hFF00 : 16'h00FF;
            w_d <= hi ? {od_q, 256'd0} : {256'd0, od_q};
        end else begin
            w_a <= obase + oc[13:0] * 14'd16 + {10'd0, g};
            w_m <= 16'hFFFF;
            w_d <= ed_q;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w_v <= 0; oc <= 0; ufs <= 0; ovf <= 0; dn <= 0; o_fu <= 0; o_fo <= 0; o_alive <= 0; o_den <= 0; o_rjid <= 0; end
        else begin
            w_v <= se_ev || ov_q;
            if (se_ev && ov_q) ovf <= 1'b1;                     // two rows in one cycle (smt: staging overflow)
            if (st_q) oc <= 0; else if (se_ev || ov_q) oc <= oc + 1;
            if (st_q) dn <= 1'b0; else if (dv_q) dn <= 1'b1;
            if (|f_q) ufs <= 1'b1;
            o_fu <= ufs; o_fo <= ovf || ofault; o_alive <= 1'b1; o_den <= dn; o_rjid <= jid;
        end
    end
endmodule
