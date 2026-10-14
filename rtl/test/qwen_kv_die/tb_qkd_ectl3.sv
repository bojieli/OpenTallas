`timescale 1ns/1ps
// q13-kvleaves 2026-10-13: the three-leaf row-engine control cell (qkd_ectl3 = qkd_ectl_a | _b | _c,
// rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv) against the one-tile qkd_ectl (KVD_ECTL_SLOT) it was cut from.
//   DUT  = qkd_ectl3 in a closed loop with bench models of its neighbours: an in-order HBM row responder (random
//          latency), the e memory (data one cycle after the read), random head-tile score returns, an aggregator that
//          returns one node credit per staged node, a q broadcast of 32 beats, exp_done bits arriving at random;
//   REF  = qkd_ectl fed the SAME inputs, delayed by the cycles the split spends on its seams (start / exp_done / nb_cr
//          +2 and T with start, q beat +1, row response +1; cyc8 as is): rq, so, t0, t1, e0..e3 must equal the DUT's on EVERY cycle.
// Several layers (random T, covering K-only, short and full contexts) per run.  Prints
// "ECTL3 PASS layers <n> cycles <c> compares <m> rows <r> vrows <v> nodes <b>" or "ECTL3 FAIL ...".
// Mutants (must FAIL): +define+KVD_ECTL3_MUT_A / _B / _C (one per leaf).
module tb_qkd_ectl3;
    parameter integer S = 1, E = 3, NL = 4, SEED = 20261013;
    reg ck = 0, rst_n = 0;
    always #0.5 ck = ~ck;
    // DUT-side inputs
    reg  [633:0]  si;  reg [1024:0] rs;  reg [33:0] s0, s1, s2, s3;
    wire [424:0]  d_so, r_so;  wire [15:0] d_rq, r_rq;  wire [1558:0] d_t0, d_t1, r_t0, r_t1;
    wire [15:0]   d_e0, d_e1, d_e2, d_e3, r_e0, r_e1, r_e2, r_e3;
    qkd_ectl3 #(.S(S), .E(E)) u_d (.ck(ck), .rst_n(rst_n), .e0(d_e0), .e1(d_e1), .e2(d_e2), .e3(d_e3), .s0(s0), .s1(s1),
        .s2(s2), .s3(s3), .t0(d_t0), .t1(d_t1), .rq(d_rq), .rs(rs), .si(si), .so(d_so));
    // reference inputs: the same, delayed per signal
    reg  [633:0]  si1, si2;  reg [1024:0] rs1;
    always @(posedge ck) begin si1 <= si; si2 <= si1; rs1 <= rs; end
    // si = {nb_cr, er_data 64, exp_done 32, q_data 512, q_beat 6, q_valid, cyc8 3, T 14, start}
    wire [633:0]  r_si = {si2[633], si[632:569], si2[568:537], si1[536:18], si[17:15], si2[14:1], si2[0]};   // T moves with start
    qkd_ectl #(.S(S), .E(E), .R(8), .DQ(128)) u_r (.ck(ck), .rst_n(rst_n), .e0(r_e0), .e1(r_e1), .e2(r_e2), .e3(r_e3),
        .s0(s0), .s1(s1), .s2(s2), .s3(s3), .t0(r_t0), .t1(r_t1), .rq(r_rq), .rs(rs1), .si(r_si), .so(r_so));
    integer seed = SEED;
    function automatic [1023:0] rowf(input [14:0] a);
        integer i; begin for (i = 0; i < 32; i = i + 1) rowf[32*i +: 32] = (a * 32'd2654435761) ^ (i * 32'h9e3779b9) ^ {a, a, 2'b01}; end
    endfunction
    // HBM responder: requests in order, each answered after a random latency
    reg [14:0] rq_q [0:1023]; integer rq_w, rq_r, rsp_wait;
    // aggregator credits, e memory
    integer cr_pend, cr_wait;
    reg er_v_q; reg [11:0] er_a_q;
    integer cyc, layer, cmps, bad, rows, vrows, nodes, k, qb, phase, idle, T;
    reg [2:0] cyc8;
    reg [31:0] expd;
    wire d_vdone = d_so[423];
    initial begin
        si = 0; rs = 0; s0 = 0; s1 = 0; s2 = 0; s3 = 0; cyc8 = 0; rq_w = 0; rq_r = 0; rsp_wait = 0; cr_pend = 0; cr_wait = 0;
        er_v_q = 0; er_a_q = 0; cmps = 0; bad = 0; rows = 0; vrows = 0; nodes = 0; expd = 0; layer = 0; phase = 0; qb = 0; idle = 0;
        k = $urandom(seed);
        repeat (6) @(posedge ck);
        rst_n = 1;
        repeat (80) @(posedge ck);
        for (cyc = 0; layer < NL && cyc < 400000; cyc = cyc + 1) begin
            @(negedge ck);
            si = 0; rs[0] = 1'b0;
            cyc8 = cyc8 + 3'd1; si[17:15] = cyc8;
            // layer sequencing: start, then 32 q beats, then run to v_done
            if (phase == 0) begin
                case (layer % 4) 0: T = 1 + $urandom % 40; 1: T = 8192; 2: T = 300 + $urandom % 3000; default: T = 4097 + $urandom % 4000; endcase
                si[0] = 1'b1; phase = 1; qb = 0; expd = 0; idle = 0;
            end else if (phase == 1) begin
                if (($urandom % 3) != 0) begin si[18] = 1'b1; si[24:19] = qb[5:0];
                    for (k = 0; k < 16; k = k + 1) si[25 + 32*k +: 32] = $urandom; qb = qb + 1; if (qb == 32) phase = 2; end
            end else begin
                if (d_vdone) begin idle = idle + 1; if (idle > 400 && rq_r == rq_w && cr_pend == 0) begin phase = 0; layer = layer + 1; end end
            end
            si[14:1] = T[13:0];
            // exp_done bits arrive at random once the layer runs
            if (phase == 2 && ($urandom % 8) == 0) expd[$urandom % 32] = 1'b1;
            if (phase == 2 && ($urandom % 400) == 0) expd = 32'hffffffff;
            si[568:537] = expd;
            // e memory: data one cycle after the read
            if (er_v_q) si[632:569] = {er_a_q, 20'h5a5a5, er_a_q, 20'hc3c3c} ^ 64'h0123456789abcdef;
            // aggregator credit
            if (cr_pend > 0) begin if (cr_wait == 0) begin si[633] = 1'b1; cr_pend = cr_pend - 1; cr_wait = $urandom % 12; end else cr_wait = cr_wait - 1; end
            // HBM response
            if (rq_r != rq_w) begin
                if (rsp_wait == 0) begin rs[0] = 1'b1; rs[1024:1] = rowf(rq_q[rq_r % 1024]); rq_r = rq_r + 1; rsp_wait = ($urandom % 4 == 0) ? $urandom % 9 : 0; end
                else rsp_wait = rsp_wait - 1;
            end
            // head-tile returns: random scores, no fault flags
            s0 = {2'b00, $urandom}; s1 = {2'b00, $urandom}; s2 = {2'b00, $urandom}; s3 = {2'b00, $urandom};
            @(posedge ck); #0.1;
            cmps = cmps + 1;
            if (d_rq !== r_rq || d_so !== r_so || d_t0 !== r_t0 || d_t1 !== r_t1 || {d_e3, d_e2, d_e1, d_e0} !== {r_e3, r_e2, r_e1, r_e0}) begin
                bad = bad + 1;
                if (bad < 6) $display("LOCKSTEP mismatch cyc %0d layer %0d: rq %s so %s t0 %s t1 %s e %s (so xor %h)", cyc, layer,
                    d_rq === r_rq ? "eq" : "NE", d_so === r_so ? "eq" : "NE", d_t0 === r_t0 ? "eq" : "NE", d_t1 === r_t1 ? "eq" : "NE",
                    {d_e3, d_e2, d_e1, d_e0} === {r_e3, r_e2, r_e1, r_e0} ? "eq" : "NE", d_so ^ r_so);
            end
            if (d_rq[0]) begin rq_q[rq_w % 1024] = d_rq[15:1]; rq_w = rq_w + 1; rows = rows + 1; if (d_rq[1]) vrows = vrows + 1; end
            er_v_q = d_so[0]; er_a_q = d_so[12:1];
            if (d_so[412] && d_so[416:413] == 4'd0) begin cr_pend = cr_pend + 1; nodes = nodes + 1; end
            if (d_so[424]) begin $display("ECTL3 FAIL fault at cycle %0d layer %0d", cyc, layer); $finish; end
        end
        if (bad == 0 && layer == NL && rows > 100 && vrows > 50 && nodes > 0)
            $display("ECTL3 PASS layers %0d cycles %0d compares %0d rows %0d vrows %0d nodes %0d (S %0d E %0d)", layer, cyc, cmps, rows, vrows, nodes, S, E);
        else $display("ECTL3 FAIL lockstep %0d layers %0d/%0d rows %0d vrows %0d nodes %0d cycles %0d", bad, layer, NL, rows, vrows, nodes, cyc);
        $finish;
    end
endmodule
