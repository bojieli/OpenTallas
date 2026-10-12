// dsfd_mtp_hrow TWO-LEVEL composition (el1011-ds-mtp 2026-10-11, owner rule TWO-LEVEL HIERARCHY): the row store as
// hardened tiles placed directly by the S81 die, no intermediate parent route.
//   dsfd_mtp_hrow_ing   x 3  beside part link pin p: link receiver (RTT) + ingress header / beat FSM; registered write
//                            command t_wc (to the part's bank pairs) and event t_ev (to the hub); part id is a strap pin
//   dsfd_mtp_hrow_hub   x 1  seed-client receiver, clear, central tag unit (registered lookup + hazard retry), read
//                            commands t_rc0..2, final 3:1 OR + response / fault flops
//   dsfd_mtp_hrow_pnode x 15 one per bank pair: pin flops, bank-enable decode (pair id strap), shared address / data to
//                            its 2 banks, registered 2:1 OR of their responses
//   dsfd_mtp_hrow_por   x 3  one per part: registered 5:1 OR of the pair responses
//   dsfd_mtp_hrow_bank  x 30 (CLOSED)
// Every tile port lands in / leaves from a flop. Every tile-to-tile seam is a DIE-LEVEL seam (relays placed by the die);
// the relay counts below are the die contract. Ordering (as rev 3): event ing -> hub CQ edges, read command hub -> pair
// pin flop CQ + DD - 1 edges, write command ing -> pair pin flop WDLY + DD - 1 edges with WDLY = 2 CQ + 1; every pair
// of a part sees the same depth (die relays padded equal per class). Return depth is uniform per read (in order).
// Hard tiles take no parameter overrides: their defaults are the hardened configuration.

// die relay (composition model of a die-level relay station chain): N registered stages, bit 0 (valid) reset
module ot_dsrom_mtp_hrow_rly #(parameter integer W = 1, parameter integer N = 0) (
    input wire clk, rst_n, input wire [W-1:0] i, output wire [W-1:0] o);
    generate if (N == 0) begin : g_w
        assign o = i;
    end else begin : g_r
        reg [W-1:0] r [0:N-1];
        genvar k;
        for (k = 0; k < N; k = k + 1) begin : g_k
            always @(posedge clk or negedge rst_n) if (!rst_n) r[k][0] <= 1'b0; else r[k][0] <= (k == 0) ? i[0] : r[(k == 0) ? 0 : k-1][0];
            if (W > 1) begin : g_d
                always @(posedge clk) r[k][W-1:1] <= (k == 0) ? i[W-1:1] : r[(k == 0) ? 0 : k-1][W-1:1];
            end
        end
        assign o = r[N-1];
    end endgenerate
endmodule

module dsfd_mtp_hrow_ing #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer PB = 80, parameter integer FWD_P = 9, parameter integer RET_P = 9
) (
    input  wire [0:0]    ck, rst,
    input  wire [514:0]  f_hp,                 // part link {flit 514, valid}
    output wire [0:0]    t_hpg,                // its grant
    input  wire [1:0]    f_pid,                // strap: part index
    output wire [1038:0] t_wc,                 // write command {d 1024, a 14, v}
    output wire [20:0]   t_ev,                 // event {kind, v, slot 7, pos 8, epoch 4}
    output wire [1:0]    t_flt
);
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer SB = $clog2(RS);
    localparam integer SW = UB + SB;
    localparam integer NS = MAXU * RS;
    localparam integer NM = (NS * PB + 1023) / 1024;
    localparam integer DB = $clog2(NM * 1024);
    localparam integer WC = 1 + DB + 1024;
    localparam integer EV = 2 + SW + 12;
    initial if (WC != 1039 || EV != 21) $fatal(1, "hrow_ing: port widths assume the hardened configuration");
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    reg [1:0] pid;
    always @(posedge ck[0]) pid <= f_pid;
    wire iv; wire [513:0] d;
    ot_dsrom_mtp_lrx_rtt #(.W(514), .D(FWD_P + RET_P + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(FWD_P), .RETURN_HOPS(RET_P)) u_rx (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_hp[0]), .l_ready(t_hpg[0]), .l_data(f_hp[514:1]),
        .c_valid(iv), .c_ready(1'b1), .c_data(d));
    reg inh, ihalf; reg [SW-1:0] islot; reg [6:0] ibeat; reg [511:0] ilo; reg [1:0] flt;
    reg [EV-1:0] ev0; reg [WC-1:0] wc0;
    wire [1:0] hq = d[1:0]; wire [3:0] he = d[5:2]; wire [NW-1:0] hp = d[6 +: NW]; wire [UB-1:0] hu = d[6 + NW +: UB];
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin inh <= 1'b0; ihalf <= 1'b0; flt <= 2'b0; ev0 <= '0; wc0[0] <= 1'b0; islot <= '0; ibeat <= 7'd0; end
        else begin
            ev0[EV-2] <= 1'b0; wc0[0] <= 1'b0;
            if (iv) begin
                if (d[513]) begin
                    if (hq != pid || inh) flt[0] <= 1'b1;
                    ev0[EV-2] <= 1'b1; ev0[EV-1] <= 1'b1; ev0[0 +: 12 + SW] <= {{hu, hp[SB-1:0]}, hp[7:0], he};
                    islot <= {hu, hp[SB-1:0]}; ibeat <= 7'd0; ihalf <= 1'b0; inh <= 1'b1;
                end else if (!inh) flt[1] <= 1'b1;
                else if (!ihalf) ihalf <= 1'b1;
                else begin
                    wc0[0] <= 1'b1;
                    ihalf <= 1'b0; ibeat <= ibeat + 7'd1;
                    if (d[512]) begin
                        inh <= 1'b0; ev0[EV-2] <= 1'b1; ev0[EV-1] <= 1'b0; ev0[0 +: 12 + SW] <= {islot, 12'd0};
                        if (ibeat != 7'd79) flt[1] <= 1'b1;
                    end
                end
            end
        end
    always @(posedge ck[0]) if (iv && !d[513] && inh && !ihalf) ilo <= d[511:0];
    always @(posedge ck[0]) if (iv && !d[513] && inh && ihalf) wc0[WC-1:1] <= {d[511:0], ilo, DB'(islot) * DB'(PB) + DB'(ibeat)};
    assign t_wc = wc0; assign t_ev = ev0; assign t_flt = flt;
endmodule

module dsfd_mtp_hrow_hub #(
    parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16, parameter integer PB = 80,
    parameter integer AW = 24, parameter integer FWD_Q = 6, parameter integer RET_Q = 6
) (
    input  wire [0:0]      ck, rst,
    input  wire [AW:0]     f_vrq,              // seed client request {addr, valid}
    output wire [0:0]      t_vrq,              // grant
    output wire [1024:0]   t_vrs,              // response {data, valid}
    input  wire [USER_W:0] f_clr,
    output wire [2:0]      t_flt,
    input  wire [20:0]     f_ev0, f_ev1, f_ev2,    // part events (from dsfd_mtp_hrow_ing t_ev)
    input  wire [1:0]      f_if0, f_if1, f_if2,    // part ingress faults
    output wire [14:0]     t_rc0, t_rc1, t_rc2,    // read commands {a 14, v} to the part's pairs
    input  wire [1024:0]   f_pr0, f_pr1, f_pr2     // part results {d, v} (from dsfd_mtp_hrow_por)
);
    localparam integer NP = 3;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer SB = $clog2(RS);
    localparam integer NS = MAXU * RS;
    localparam integer SW = UB + SB;
    localparam integer NM = (NS * PB + 1023) / 1024;
    localparam integer DB = $clog2(NM * 1024);
    localparam integer RC = 1 + DB;
    localparam integer EV = 2 + SW + 12;
    initial if (RC != 15 || EV != 21) $fatal(1, "hrow_hub: port widths assume the hardened configuration");
    wire rn_c;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn_c));
    wire clk = ck[0];
    // seed client receiver
    wire q_v, q_r; wire [AW-1:0] q_a;
    ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(FWD_Q + RET_Q + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(FWD_Q), .RETURN_HOPS(RET_Q)) u_q (
        .clk(clk), .rst_n(rn_c), .l_valid(f_vrq[0]), .l_ready(t_vrq[0]), .l_data(f_vrq[AW:1]),
        .c_valid(q_v), .c_ready(q_r), .c_data(q_a));
    // pin flops
    reg [USER_W:0] i_clr;
    always @(posedge clk or negedge rn_c) if (!rn_c) i_clr[0] <= 1'b0; else i_clr[0] <= f_clr[0];
    always @(posedge clk) i_clr[USER_W:1] <= f_clr[USER_W:1];
    wire c_v = i_clr[0]; wire [USER_W-1:0] c_user = i_clr[USER_W:1];
    wire [EV-1:0] ev_in [0:NP-1]; wire [1024:0] pr_in [0:NP-1]; wire [1:0] if_in [0:NP-1];
    assign ev_in[0] = f_ev0; assign ev_in[1] = f_ev1; assign ev_in[2] = f_ev2;
    assign pr_in[0] = f_pr0; assign pr_in[1] = f_pr1; assign pr_in[2] = f_pr2;
    assign if_in[0] = f_if0; assign if_in[1] = f_if1; assign if_in[2] = f_if2;
    reg [EV-1:0] ev_c [0:NP-1]; reg [1024:0] pr [0:NP-1]; reg [1:0] pflt [0:NP-1];
    integer z;
    always @(posedge clk or negedge rn_c)
        if (!rn_c) for (z = 0; z < NP; z = z + 1) begin ev_c[z][EV-2] <= 1'b0; pr[z][0] <= 1'b0; pflt[z] <= 2'b0; end
        else for (z = 0; z < NP; z = z + 1) begin ev_c[z][EV-2] <= ev_in[z][EV-2]; pr[z][0] <= pr_in[z][0]; pflt[z] <= if_in[z]; end
    always @(posedge clk) for (z = 0; z < NP; z = z + 1) begin
        ev_c[z][EV-1] <= ev_in[z][EV-1]; ev_c[z][EV-3:0] <= ev_in[z][EV-3:0]; pr[z][1024:1] <= pr_in[z][1024:1];
    end
    // output OR (one part answers a cycle) + response flop
    reg r_v; reg [1023:0] r_d; reg [1024:0] o_rs;
    always @(posedge clk or negedge rn_c) if (!rn_c) begin r_v <= 1'b0; o_rs[0] <= 1'b0; end
                                          else begin r_v <= pr[0][0] | pr[1][0] | pr[2][0]; o_rs[0] <= r_v; end
    always @(posedge clk) begin r_d <= pr[0][1024:1] | pr[1][1024:1] | pr[2][1024:1]; o_rs[1024:1] <= r_d; end
    assign t_vrs = o_rs;
    // ---------------- central tag unit (as rev 3 ot_dsrom_mtp_hrow_store)
    reg [11:0] tag  [0:NP-1][0:NS-1];
    reg        cmp  [0:NP-1][0:NS-1];
    reg        wg   [0:NP-1][0:NS-1];
    reg        rg   [0:NP-1][0:NS-1];
    reg        ld   [0:NP-1][0:NS-1];
    reg        f0;
    reg [AW-1:0] sk [0:1]; reg [1:0] skn; reg skw, skr;
    reg qr_q;
    assign q_r = qr_q;
    reg v2, ok2, hz2; reg [SW-1:0] s2; reg [1:0] p2; reg [6:0] pb2; reg [DB-1:0] a2;
    wire issue = v2 && ok2 && !hz2;
    wire adv = !v2 || issue;
    wire take = adv && skn != 0;
    wire [AW-1:0] la = sk[skr];
    wire [3:0] l_ep = la[UB+16 +: 4];
    wire [UB-1:0] l_u = la[16 +: UB];
    wire [7:0] l_pos = la[15:8];
    wire [7:0] l_beat = la[7:0];
    wire [1:0] l_part = (l_beat < 8'd80) ? 2'd0 : (l_beat < 8'd160) ? 2'd1 : 2'd2;
    wire [6:0] l_pb = l_beat - (l_part == 2'd0 ? 8'd0 : l_part == 2'd1 ? 8'd80 : 8'd160);
    reg [7:0] pos2; reg [3:0] ep2;
    wire [SW-1:0] ks = adv ? {l_u, l_pos[SB-1:0]} : s2;
    wire [7:0] kpos = adv ? l_pos : pos2;
    wire [3:0] kep = adv ? l_ep : ep2;
    wire [1:0] kpart = adv ? l_part : p2;
    reg k_ok; integer pi;
    always @(*) begin
        k_ok = 1'b1;
        for (pi = 0; pi < NP; pi = pi + 1) begin
`ifdef OT_HROW_MUT_NOPART
            if (pi == kpart)
`endif
            begin
`ifdef OT_HROW_MUT_NOEPOCH
                if (!(cmp[pi][ks] && tag[pi][ks][11:4] == kpos)) k_ok = 1'b0;
`else
                if (!(cmp[pi][ks] && tag[pi][ks] == {kpos, kep})) k_ok = 1'b0;
`endif
            end
        end
    end
    reg k_hz; integer ei;
    always @(*) begin
        k_hz = c_v && c_user < MAXU && c_user[UB-1:0] == ks[SW-1:SB];
        for (ei = 0; ei < NP; ei = ei + 1)
            if (ev_c[ei][EV-2] && ev_c[ei][EV-1] && ev_c[ei][12 +: SW] == ks) k_hz = 1'b1;
    end
    reg [RC-1:0] rcq [0:NP-1];
    assign t_rc0 = rcq[0]; assign t_rc1 = rcq[1]; assign t_rc2 = rcq[2];
    integer p, s;
    always @(posedge clk or negedge rn_c)
        if (!rn_c) begin
            skn <= 2'd0; skw <= 1'b0; skr <= 1'b0; qr_q <= 1'b0; v2 <= 1'b0; f0 <= 1'b0;
            for (p = 0; p < NP; p = p + 1) begin
                rcq[p][0] <= 1'b0;
                for (s = 0; s < NS; s = s + 1) begin cmp[p][s] <= 1'b0; wg[p][s] <= 1'b0; rg[p][s] <= 1'b0; ld[p][s] <= 1'b0; end
            end
        end else begin
            if (q_v && qr_q) begin sk[skw] <= q_a; skw <= ~skw; end
            if (take) skr <= ~skr;
            skn <= skn + (q_v && qr_q) - take;
            qr_q <= (skn + (q_v && qr_q) - take) < 2'd2;
            if (adv) v2 <= take;
            if (adv ? take : 1'b1) begin
                ok2 <= k_ok; hz2 <= k_hz;
            end
            if (take) begin
                s2 <= {l_u, l_pos[SB-1:0]}; p2 <= l_part; pb2 <= l_pb; pos2 <= l_pos; ep2 <= l_ep;
                a2 <= DB'({l_u, l_pos[SB-1:0]}) * DB'(PB) + DB'(l_pb);
            end
            for (p = 0; p < NP; p = p + 1) rcq[p][0] <= issue && p2 == p;
            if (issue && pb2 == 7'd79) rg[p2][s2] <= wg[p2][s2];
            for (p = 0; p < NP; p = p + 1)
                if (ev_c[p][EV-2]) begin
                    if (ev_c[p][EV-1]) begin
                        if (ld[p][ev_c[p][12 +: SW]] && tag[p][ev_c[p][12 +: SW]][11:4] != ev_c[p][11:4] &&
                            rg[p][ev_c[p][12 +: SW]] != wg[p][ev_c[p][12 +: SW]]) f0 <= 1'b1;
                        cmp[p][ev_c[p][12 +: SW]] <= 1'b0; wg[p][ev_c[p][12 +: SW]] <= ~wg[p][ev_c[p][12 +: SW]];
                        ld[p][ev_c[p][12 +: SW]] <= 1'b1;
                    end else cmp[p][ev_c[p][12 +: SW]] <= 1'b1;
                end
            if (c_v && c_user < MAXU)
                for (p = 0; p < NP; p = p + 1) for (s = 0; s < RS; s = s + 1) begin
                    cmp[p][{c_user[UB-1:0], SB'(s)}] <= 1'b0; ld[p][{c_user[UB-1:0], SB'(s)}] <= 1'b0;
                end
        end
    always @(posedge clk) begin
        for (p = 0; p < NP; p = p + 1) begin
            rcq[p][RC-1:1] <= a2;
            if (ev_c[p][EV-2] && ev_c[p][EV-1]) tag[p][ev_c[p][12 +: SW]] <= ev_c[p][11:0];
        end
    end
    reg [2:0] fq;
    always @(posedge clk or negedge rn_c) if (!rn_c) fq <= 3'd0;
        else fq <= {fq[2] | pflt[0][1] | pflt[1][1] | pflt[2][1], fq[1] | pflt[0][0] | pflt[1][0] | pflt[2][0], fq[0] | f0};
    reg [2:0] o_flt;
    always @(posedge clk or negedge rn_c) if (!rn_c) o_flt <= 3'd0; else o_flt <= fq;
    assign t_flt = o_flt;
endmodule

// one bank pair: pin flops, enable decode against the pair-id strap, shared address / data, registered 2:1 OR
module dsfd_mtp_hrow_pnode (
    input  wire [0:0]    ck, rst,
    input  wire [1038:0] f_wc,                 // write command {d 1024, a 14, v}
    input  wire [14:0]   f_rc,                 // read command {a 14, v}
    input  wire [3:0]    f_qid,                // strap: index of the pair's first bank in its part (2 q)
    output wire [1033:0] t_wd,                 // {wd 1024, wa 10} to both banks
    output wire [1:0]    t_we,                 // write enable bank 2q / 2q+1
    output wire [9:0]    t_ra,
    output wire [1:0]    t_re,
    input  wire [1024:0] f_bt0, f_bt1,         // bank responses {rd, valid}
    output wire [1024:0] t_po                  // pair response {d, v}
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    reg [1038:0] wl; reg [14:0] rl; reg [3:0] qid; reg [1024:0] b0, b1;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin wl[0] <= 1'b0; rl[0] <= 1'b0; b0[0] <= 1'b0; b1[0] <= 1'b0; end
        else begin wl[0] <= f_wc[0]; rl[0] <= f_rc[0]; b0[0] <= f_bt0[0]; b1[0] <= f_bt1[0]; end
    always @(posedge ck[0]) begin
        wl[1038:1] <= f_wc[1038:1]; rl[14:1] <= f_rc[14:1]; qid <= f_qid; b0[1024:1] <= f_bt0[1024:1]; b1[1024:1] <= f_bt1[1024:1];
    end
    reg [1:0] bwe, bre; reg [9:0] bwa, bra; reg [1023:0] bwd; reg [1024:0] po;
    wire [3:0] q1 = qid + 4'd1;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin bwe <= 2'b0; bre <= 2'b0; po[0] <= 1'b0; end
        else begin
            bwe[0] <= wl[0] && wl[14:11] == qid; bwe[1] <= wl[0] && wl[14:11] == q1;
            bre[0] <= rl[0] && rl[14:11] == qid; bre[1] <= rl[0] && rl[14:11] == q1;
            po[0] <= b0[0] | b1[0];
        end
    always @(posedge ck[0]) begin bwa <= wl[10:1]; bwd <= wl[1038:15]; bra <= rl[10:1]; po[1024:1] <= b0[1024:1] | b1[1024:1]; end
    assign t_wd = {bwd, bwa}; assign t_we = bwe; assign t_ra = bra; assign t_re = bre; assign t_po = po;
endmodule

// one part: registered 5:1 OR of its pair responses
module dsfd_mtp_hrow_por (
    input  wire [0:0]    ck, rst,
    input  wire [1024:0] f_q0, f_q1, f_q2, f_q3, f_q4,
    output wire [1024:0] t_pp
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    reg [1024:0] q0, q1, q2, q3, q4, pp;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin q0[0] <= 1'b0; q1[0] <= 1'b0; q2[0] <= 1'b0; q3[0] <= 1'b0; q4[0] <= 1'b0; pp[0] <= 1'b0; end
        else begin q0[0] <= f_q0[0]; q1[0] <= f_q1[0]; q2[0] <= f_q2[0]; q3[0] <= f_q3[0]; q4[0] <= f_q4[0];
                   pp[0] <= q0[0] | q1[0] | q2[0] | q3[0] | q4[0]; end
    always @(posedge ck[0]) begin
        q0[1024:1] <= f_q0[1024:1]; q1[1024:1] <= f_q1[1024:1]; q2[1024:1] <= f_q2[1024:1];
        q3[1024:1] <= f_q3[1024:1]; q4[1024:1] <= f_q4[1024:1];
        pp[1024:1] <= q0[1024:1] | q1[1024:1] | q2[1024:1] | q3[1024:1] | q4[1024:1];
    end
    assign t_pp = pp;
endmodule

// RTL composition of the tiles as the die places them (die relays modelled by ot_dsrom_mtp_hrow_rly); same ports as
// dsfd_mtp_hrow; the composition bench (tools/mtp_hrow_gate.py --tiles) runs on this
module dsfd_mtp_hrow_tc #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer FWD_P = 9, parameter integer RET_P = 9,
    parameter integer FWD_Q = 6, parameter integer RET_Q = 6,
    parameter integer CQ = 3, parameter integer DD = 2, parameter integer RD = 2, parameter integer RP = 4
) (
    input  wire [0:0]     ck, rst,
    input  wire [514:0]   f_hp0, f_hp1, f_hp2,
    output wire [2:0]     t_hpg,
    input  wire [AW:0]    f_vrq,
    output wire [0:0]     t_vrq,
    output wire [1024:0]  t_vrs,
    input  wire [USER_W:0] f_clr,
    output wire [2:0]     t_flt
);
    localparam integer WDLY = 2 * CQ + 1;
    initial if (DD < 2 || CQ < 1) $fatal(1, "hrow_tc: DD >= 2 (the pair pin flop is the last distribution stage), CQ >= 1");
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    wire [514:0] fin [0:2];
    assign fin[0] = f_hp0; assign fin[1] = f_hp1; assign fin[2] = f_hp2;
    wire [20:0] ev [0:2]; wire [20:0] evh [0:2]; wire [1:0] ifl [0:2]; wire [1:0] iflh [0:2];
    wire [14:0] rc [0:2]; wire [1024:0] pp [0:2]; wire [1024:0] pph [0:2];
    genvar gp, gq;
    generate for (gp = 0; gp < 3; gp = gp + 1) begin : g_part
        wire [1038:0] wc, wroot; wire [14:0] rroot;
        dsfd_mtp_hrow_ing #(.NW(NW), .USER_W(USER_W), .MAXU(MAXU), .RS(RS), .FWD_P(FWD_P), .RET_P(RET_P)) u_ig (
            .ck(ck), .rst(rst), .f_hp(fin[gp]), .t_hpg(t_hpg[gp]), .f_pid(gp[1:0]), .t_wc(wc), .t_ev(ev[gp]), .t_flt(ifl[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(21), .N(CQ - 1)) u_ev (.clk(ck[0]), .rst_n(rn), .i(ev[gp]), .o(evh[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(2), .N(CQ - 1)) u_if (.clk(ck[0]), .rst_n(rn), .i(ifl[gp]), .o(iflh[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(1039), .N(WDLY)) u_wd (.clk(ck[0]), .rst_n(rn), .i(wc), .o(wroot));
        ot_dsrom_mtp_hrow_rly #(.W(15), .N(CQ)) u_rc (.clk(ck[0]), .rst_n(rn), .i(rc[gp]), .o(rroot));
        wire [1024:0] qo [0:4];
        for (gq = 0; gq < 5; gq = gq + 1) begin : g_q
            wire [1038:0] wl; wire [14:0] rl; wire [1033:0] wd; wire [1:0] we, re; wire [9:0] ra;
            wire [1024:0] bt0, bt1, po;
            ot_dsrom_mtp_hrow_rly #(.W(1039), .N(DD - 2)) u_dw (.clk(ck[0]), .rst_n(rn), .i(wroot), .o(wl));
            ot_dsrom_mtp_hrow_rly #(.W(15), .N(DD - 2)) u_dr (.clk(ck[0]), .rst_n(rn), .i(rroot), .o(rl));
            dsfd_mtp_hrow_pnode u_pn (.ck(ck), .rst(rst), .f_wc(wl), .f_rc(rl), .f_qid(4'(2 * gq)), .t_wd(wd), .t_we(we),
                                      .t_ra(ra), .t_re(re), .f_bt0(bt0), .f_bt1(bt1), .t_po(po));
            dsfd_mtp_hrow_bank u_b0 (.ck(ck), .rst(rst), .f_w({wd, we[0]}), .f_r({ra, re[0]}), .t_d(bt0));
            dsfd_mtp_hrow_bank u_b1 (.ck(ck), .rst(rst), .f_w({wd, we[1]}), .f_r({ra, re[1]}), .t_d(bt1));
            ot_dsrom_mtp_hrow_rly #(.W(1025), .N(RD)) u_rd (.clk(ck[0]), .rst_n(rn), .i(po), .o(qo[gq]));
        end
        dsfd_mtp_hrow_por u_po (.ck(ck), .rst(rst), .f_q0(qo[0]), .f_q1(qo[1]), .f_q2(qo[2]), .f_q3(qo[3]), .f_q4(qo[4]),
                                .t_pp(pp[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(1025), .N(RP)) u_rp (.clk(ck[0]), .rst_n(rn), .i(pp[gp]), .o(pph[gp]));
    end endgenerate
    dsfd_mtp_hrow_hub #(.USER_W(USER_W), .MAXU(MAXU), .RS(RS), .AW(AW), .FWD_Q(FWD_Q), .RET_Q(RET_Q)) u_hub (
        .ck(ck), .rst(rst), .f_vrq(f_vrq), .t_vrq(t_vrq), .t_vrs(t_vrs), .f_clr(f_clr), .t_flt(t_flt),
        .f_ev0(evh[0]), .f_ev1(evh[1]), .f_ev2(evh[2]), .f_if0(iflh[0]), .f_if1(iflh[1]), .f_if2(iflh[2]),
        .t_rc0(rc[0]), .t_rc1(rc[1]), .t_rc2(rc[2]), .f_pr0(pph[0]), .f_pr1(pph[1]), .f_pr2(pph[2]));
endmodule
