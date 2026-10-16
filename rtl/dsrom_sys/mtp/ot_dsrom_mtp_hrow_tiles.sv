`ifdef OT_HROW_RESET_ACK
// Epoch request is upstream of the conditioner. Actual local reset LOW and
// consumer initialization must be observed at a consumer edge in this epoch.
module dsfd_mtp_reset_ack #(parameter integer N=1)(
 input wire clk,request_n,input wire [N-1:0] local_release,
 input wire consumer_live,reset_initialized,output wire ack);
 reg reset_seen,ack_q;
 always @(posedge clk or negedge request_n)
   if(!request_n) begin reset_seen<=0;ack_q<=0;end
   else begin
`ifdef OT_HROW_MUT_ACK_WRONG_WITNESS
     if(!consumer_live) reset_seen<=1;
`else
     if(!( |local_release) && reset_initialized) reset_seen<=1;
`endif
`ifdef OT_HROW_MUT_ACK_NO_EPOCH
     ack_q<=(&local_release)&&consumer_live;
`else
     ack_q<=reset_seen&&(&local_release)&&consumer_live;
`endif
   end
`ifdef OT_HROW_MUT_ACK_MIRROR
 assign ack=request_n;
`else
 assign ack=ack_q&&(&local_release)&&consumer_live;
`endif
endmodule
`endif
// dsfd_mtp_hrow as hardened tiles placed directly by the S81 die (el1011-ds-mtp; rev 5 hrow-r5 2026-10-12, owner GLUE
// PLACEMENT: per-bank glue inside the bank tiles, no tile over 15k clock sinks).
//   dsfd_mtp_hrow_ing x 3  beside part link pin p: drain link receiver + ingress header / beat FSM + WK-edge write
//                          delay; registered write command t_wc (to its chain head) and event t_ev (to the hub)
//   dsfd_mtp_hrow_hub x 1  seed-client receiver, clear, central tag unit (registered lookup + hazard retry), read
//                          commands t_rc0..2, final 3:1 OR + response / fault flops
//   dsfd_mtp_hrow_cbe x 15 / dsfd_mtp_hrow_cbw x 15  chain bank tiles (one bank each; see the rev-5 note below)
// Every tile port lands in / leaves from a flop.  Tile-to-tile seams outside the chains are DIE-LEVEL seams (relays
// placed by the die); the relay counts in dsfd_mtp_hrow_tc are the die contract.  Hard tiles take no parameter
// overrides: their defaults are the hardened configuration.

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
    parameter integer PB = 80, parameter integer FWD_P = 9, parameter integer RET_P = 9,
    parameter integer WK = 7       // write-side ordering delay (edges) inside the tile
) (
    input  wire          ck, rst,
    input  wire [514:0]  f_hp,                 // part link {flit 514, valid}
    output wire          t_hpg,                // its grant
    input  wire [1:0]    f_pid,                // strap: part index
    output wire [1038:0] t_wc,                 // write command {d 1024, a 14, v}
    output wire [20:0]   t_ev,                 // event {kind, v, slot 7, pos 8, epoch 4}
    output wire [1:0]    t_flt
`ifdef OT_HROW_RESET_ACK
    ,output wire rst_ack
`endif
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
    ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn));
    reg [1:0] pid;
    always @(posedge ck) pid <= f_pid;
    wire iv; wire [513:0] d;
    // rev 5: the ingress always takes its flits (c_ready = 1), so the RTT receiver's FWD_P + RET_P + 4 deep queue never
    // holds a flit (cnt stays 0, every grant is 1): ot_dsrom_mtp_hrow_drx is that receiver with the dead queue removed
    // (identical l_ready / c_valid / c_data sequences; -11.3k flops a part)
    ot_dsrom_mtp_hrow_drx #(.W(514)) u_rx (
        .clk(ck), .rst_n(rn), .l_valid(f_hp[0]), .l_ready(t_hpg), .l_data(f_hp[514:1]), .c_valid(iv), .c_data(d)
`ifdef OT_HROW_RESET_ACK
        ,.rst_live(rx_live)
`endif
);
    reg inh, ihalf; reg [SW-1:0] islot; reg [6:0] ibeat; reg [511:0] ilo; reg [1:0] flt;
    reg [EV-1:0] ev0; reg [WC-1:0] wc0;
    wire [1:0] hq = d[1:0]; wire [3:0] he = d[5:2]; wire [NW-1:0] hp = d[6 +: NW]; wire [UB-1:0] hu = d[6 + NW +: UB];
    always @(posedge ck or negedge rn)
        if (!rn) begin inh <= 1'b0; ihalf <= 1'b0; flt <= 2'b0; ev0 <= '0; islot <= '0; ibeat <= 7'd0; end
        else begin
            ev0[EV-2] <= 1'b0;
            if (iv) begin
                if (d[513]) begin
                    if (hq != pid || inh) flt[0] <= 1'b1;
                    ev0[EV-2] <= 1'b1; ev0[EV-1] <= 1'b1; ev0[0 +: 12 + SW] <= {{hu, hp[SB-1:0]}, hp[7:0], he};
                    islot <= {hu, hp[SB-1:0]}; ibeat <= 7'd0; ihalf <= 1'b0; inh <= 1'b1;
                end else if (!inh) flt[1] <= 1'b1;
                else if (!ihalf) ihalf <= 1'b1;
                else begin
                    ihalf <= 1'b0; ibeat <= ibeat + 7'd1;
                    if (d[512]) begin
                        inh <= 1'b0; ev0[EV-2] <= 1'b1; ev0[EV-1] <= 1'b0; ev0[0 +: 12 + SW] <= {islot, 12'd0};
                        if (ibeat != 7'd79) flt[1] <= 1'b1;
                    end
                end
            end
        end
    // rev 5: the write side runs WK edges behind the FSM (the ordering delay WDLY = 2 CQ + 1 lives here, on the 528-b
    // half-beat stream {d 512, a 14, hi, lo}, not on die relays of the 1,039-b assembled command); the assembly below
    // is the rev-3 assembly delayed by exactly WK edges
    wire lo_s = iv && !d[513] && inh && !ihalf;
    wire hi_s = iv && !d[513] && inh && ihalf;      // = the edge at which rev 3 set wc0[0]
    localparam integer KW = 2 + DB + 512;
    reg [KW-1:0] kd [0:WK-1];
    genvar gk;
    generate for (gk = 0; gk < WK; gk = gk + 1) begin : g_k
        always @(posedge ck or negedge rn) if (!rn) kd[gk][1:0] <= 2'b0;
            else kd[gk][1:0] <= (gk == 0) ? {hi_s, lo_s} : kd[(gk == 0) ? 0 : gk-1][1:0];
        always @(posedge ck) kd[gk][KW-1:2] <= (gk == 0) ? {d[511:0], DB'(islot) * DB'(PB) + DB'(ibeat)}
                                                            : kd[(gk == 0) ? 0 : gk-1][KW-1:2];
    end endgenerate
    wire [KW-1:0] kq = kd[WK-1];
    always @(posedge ck or negedge rn) if (!rn) wc0[0] <= 1'b0; else wc0[0] <= kq[1];
    always @(posedge ck) if (kq[0]) ilo <= kq[KW-1 -: 512];
    always @(posedge ck) if (kq[1]) wc0[WC-1:1] <= {kq[KW-1 -: 512], ilo, kq[2 +: DB]};
    assign t_wc = wc0; assign t_ev = ev0; assign t_flt = flt;
`ifdef OT_HROW_RESET_ACK
    wire rx_live;
    dsfd_mtp_reset_ack #(.N(2)) u_ack(.clk(ck),.request_n(rst),.local_release({rn,rx_live}),.consumer_live(rx_live),.reset_initialized(1'b1),.ack(rst_ack));
`endif
endmodule

module dsfd_mtp_hrow_hub #(
    parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16, parameter integer PB = 80,
    parameter integer AW = 24, parameter integer FWD_Q = 6, parameter integer RET_Q = 6,
    parameter integer LOCAL_GROUP_SLOTS = 0 // default-off exact same-edge local key/reset copies
) (
    input  wire            ck, rst,
    input  wire [AW:0]     f_vrq,              // seed client request {addr, valid}
    output wire            t_vrq,              // grant
    output wire [1024:0]   t_vrs,              // response {data, valid}
    input  wire [USER_W:0] f_clr,
    output wire [2:0]      t_flt,
    input  wire [20:0]     f_ev0, f_ev1, f_ev2,    // part events (from dsfd_mtp_hrow_ing t_ev)
    input  wire [1:0]      f_if0, f_if1, f_if2,    // part ingress faults
    output wire [14:0]     t_rc0, t_rc1, t_rc2,    // read commands {a 14, v} to the part's pairs
    input  wire [1024:0]   f_pr0, f_pr1, f_pr2     // part results {d, v} (from dsfd_mtp_hrow_por)
`ifdef OT_HROW_RESET_ACK
    ,output wire [6:0] rst_ack
`endif
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
    ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn_c));
    wire clk = ck;
    // seed client receiver
    wire q_v, q_r; wire [AW-1:0] q_a;
    ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(FWD_Q + RET_Q + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(FWD_Q), .RETURN_HOPS(RET_Q)) u_q (
        .clk(clk), .rst_n(rn_c), .l_valid(f_vrq[0]), .l_ready(t_vrq), .l_data(f_vrq[AW:1]),
        .c_valid(q_v), .c_ready(q_r), .c_data(q_a)
`ifdef OT_HROW_RESET_ACK
        ,.rst_live(q_live)
`endif
);
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
    // r5d (hub r5c TT -8.08 / WC -71: ABC folded the r5c dual lookup back into ONE lookup on an adv-selected key, so
    // v2 -> adv again drove the 128:1 tag/cmp mux selects through 8 buffer levels): both lookup results AND the select
    // are registered (okn2/okh2/hzn2/hzh2 + sel2, same enable as the old ok2/hz2), ok2/hz2 = sel2 ? n : h after the
    // flops -- no logic path from v2 into the tag muxes exists for synthesis to recreate.  Same values every cycle.
    // Per-part tag state is built per part / per slot with its own reset synchroniser per half part (6 x 256 async
    // loads instead of one 1,573-load reset net; textbook class 2); key registers are per part (replicated selects).
    localparam integer NR = 2;
    reg [AW-1:0] sk [0:1]; reg [1:0] skn; reg skw, skr;
    reg qr_q;
    assign q_r = qr_q;
    reg v2, okn2, okh2, hzn2, hzh2, sel2; reg [SW-1:0] s2; reg [1:0] p2; reg [6:0] pb2; reg [DB-1:0] a2;
    wire ok2 = sel2 ? okn2 : okh2;
    wire hz2 = sel2 ? hzn2 : hzh2;
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
    reg [1:0] hk_part, hs_part; reg [SW-1:0] hz_ks, hz_hs;
    wire        sk_push = q_v && qr_q;
    wire        skr_n   = skr ^ take;
    wire [AW-1:0] la_n  = (sk_push && skw == skr_n) ? q_a : sk[skr_n];
    wire [7:0]  ln_beat = la_n[7:0];
    always @(posedge clk) begin
        hk_part <= (ln_beat < 8'd80) ? 2'd0 : (ln_beat < 8'd160) ? 2'd1 : 2'd2;
        hz_ks <= {la_n[16 +: UB], la_n[8 +: SB]};
        if (take) begin hs_part <= l_part; hz_hs <= {l_u, l_pos[SB-1:0]}; end
    end
    wire clr_u = c_v && c_user < MAXU;
    localparam integer LG = LOCAL_GROUP_SLOTS > 0 ? LOCAL_GROUP_SLOTS : NS;
    localparam integer NG = NS / LG;
    localparam integer GPH = NG / NR;
    initial if (LOCAL_GROUP_SLOTS > 0 && (NS % LG != 0 || LG > NS/NR || NG % NR != 0))
        $fatal(1,"hub local groups must divide each original reset half");
    wire [NP*NG-1:0] rn_group;
    wire [NP*NR-1:0] rn_a;
    wire [NP-1:0] ok_n_p, ok_h_p, f0_p;
    genvar gp, gs, gr;
    generate
        for (gr = 0; gr < NP * NR; gr = gr + 1) begin : g_rs
            if (LOCAL_GROUP_SLOTS == 0) begin:g_old
                ot_dsrom_mtp_rstsync u_rsa (.clk(clk), .rst_n_async(rst), .rst_n(rn_a[gr]));
            end else assign rn_a[gr]=rn_group[gr*GPH];
        end
        if (LOCAL_GROUP_SLOTS > 0) begin:g_group_rst
            for(genvar gi=0;gi<NP*NG;gi=gi+1) begin:g_r
                dsfd_mtp_hrow_group_rst u_rs(.ck(clk),.rst(rst),.rn(rn_group[gi]));
            end
        end
        for (gp = 0; gp < NP; gp = gp + 1) begin : g_p
            reg [11:0] tag [0:NS-1];
            wire [NS-1:0] cmp, wg, rg, ld;
            wire          ev_v = ev_c[gp][EV-2];
            wire          ev_w = ev_c[gp][EV-1];
            wire [SW-1:0] ev_s = ev_c[gp][12 +: SW];
            for (gs = 0; gs < NS; gs = gs + 1) begin : g_s
                wire rn = LOCAL_GROUP_SLOTS > 0 ? rn_group[gp*NG+gs/LG] : rn_a[gp * NR + (gs * NR) / NS];
                reg cmp_r, wg_r, rg_r, ld_r;
                assign cmp[gs] = cmp_r; assign wg[gs] = wg_r; assign rg[gs] = rg_r; assign ld[gs] = ld_r;
                wire hit = ev_v && ev_s == gs;
                wire clr = clr_u && c_user[UB-1:0] == (gs >> SB);
                always @(posedge clk or negedge rn)
                    if (!rn) begin cmp_r <= 1'b0; wg_r <= 1'b0; rg_r <= 1'b0; ld_r <= 1'b0; end
                    else begin
                        if (issue && pb2 == 7'd79 && p2 == gp && s2 == gs) rg_r <= wg_r;
                        if (hit) begin
                            if (ev_w) begin cmp_r <= 1'b0; wg_r <= ~wg_r; ld_r <= 1'b1; end
                            else cmp_r <= 1'b1;
                        end
                        if (clr) begin cmp_r <= 1'b0; ld_r <= 1'b0; end
                    end
            end
            reg f0r;
            assign f0_p[gp] = f0r;
            always @(posedge clk or negedge rn_a[gp * NR])
                if (!rn_a[gp * NR]) f0r <= 1'b0;
                else if (ev_v && ev_w && ld[ev_s] && tag[ev_s][11:4] != ev_c[gp][11:4] && rg[ev_s] != wg[ev_s]) f0r <= 1'b1;
            always @(posedge clk) if (ev_v && ev_w) tag[ev_s] <= ev_c[gp][11:0];
            wire okn,okh;
            if (LOCAL_GROUP_SLOTS == 0) begin:g_lookup_old
            // per-part key copies: next skid head (hk*) and held entry (hs*)
            reg [SW-1:0] hk_s, hs_s; reg [7:0] hk_pos, hs_pos; reg [3:0] hk_ep, hs_ep;
            always @(posedge clk) begin
                hk_s <= {la_n[16 +: UB], la_n[8 +: SB]}; hk_pos <= la_n[15:8]; hk_ep <= la_n[UB+16 +: 4];
                if (take) begin hs_s <= {l_u, l_pos[SB-1:0]}; hs_pos <= l_pos; hs_ep <= l_ep; end
            end
`ifdef OT_HROW_MUT_NOEPOCH
            assign okn = cmp[hk_s] && tag[hk_s][11:4] == hk_pos;
            assign okh = cmp[hs_s] && tag[hs_s][11:4] == hs_pos;
`else
            assign okn = cmp[hk_s] && tag[hk_s] == {hk_pos, hk_ep};
            assign okh = cmp[hs_s] && tag[hs_s] == {hs_pos, hs_ep};
`endif
            end else begin:g_lookup_local
                wire [NG-1:0] on,oh;
                for(genvar gi=0;gi<NG;gi=gi+1) begin:g_group
                    (* keep=1 *) reg [SW-1:0] hk_s,hs_s;
                    (* keep=1 *) reg [7:0] hk_pos,hs_pos;
                    (* keep=1 *) reg [3:0] hk_ep,hs_ep;
                    always @(posedge clk) begin
`ifdef OT_HROW_LOCAL_MUT_KEY_LATE
                        hk_s <= {la[16 +: UB],la[8 +: SB]};
`else
                        hk_s <= {la_n[16 +: UB],la_n[8 +: SB]};
`endif
                        hk_pos <= la_n[15:8];hk_ep <= la_n[UB+16 +: 4];
                        if(take)begin hs_s<={l_u,l_pos[SB-1:0]};hs_pos<=l_pos;hs_ep<=l_ep;end
                    end
                    wire [LG-1:0] sn,sh;
                    for(genvar si=0;si<LG;si=si+1)begin:g_slot
                        localparam integer SLOT=gi*LG+si;
`ifdef OT_HROW_MUT_NOEPOCH
                        assign sn[si]=cmp[SLOT] && hk_s==SW'(SLOT) && tag[SLOT][11:4]==hk_pos;
                        assign sh[si]=cmp[SLOT] && hs_s==SW'(SLOT) && tag[SLOT][11:4]==hs_pos;
`else
                        assign sn[si]=cmp[SLOT] && hk_s==SW'(SLOT) && tag[SLOT]=={hk_pos,hk_ep};
                        assign sh[si]=cmp[SLOT] && hs_s==SW'(SLOT) && tag[SLOT]=={hs_pos,hs_ep};
`endif
                    end
                    assign on[gi]=|sn;assign oh[gi]=|sh;
                end
                assign okn=|on;assign okh=|oh;
            end
`ifdef OT_HROW_MUT_NOPART
            assign ok_n_p[gp] = okn || hk_part != gp;
            assign ok_h_p[gp] = okh || hs_part != gp;
`else
            assign ok_n_p[gp] = okn;
            assign ok_h_p[gp] = okh;
`endif
        end
    endgenerate
    wire k_ok_n = &ok_n_p;
    wire k_ok_h = &ok_h_p;
    wire f0 = |f0_p;
    reg k_hz_n, k_hz_h; integer ei;
    always @(*) begin
        k_hz_n = c_v && c_user < MAXU && c_user[UB-1:0] == hz_ks[SW-1:SB];
        k_hz_h = c_v && c_user < MAXU && c_user[UB-1:0] == hz_hs[SW-1:SB];
        for (ei = 0; ei < NP; ei = ei + 1) begin
            if (ev_c[ei][EV-2] && ev_c[ei][EV-1] && ev_c[ei][12 +: SW] == hz_ks) k_hz_n = 1'b1;
            if (ev_c[ei][EV-2] && ev_c[ei][EV-1] && ev_c[ei][12 +: SW] == hz_hs) k_hz_h = 1'b1;
        end
    end
    reg [RC-1:0] rcq [0:NP-1];
    assign t_rc0 = rcq[0]; assign t_rc1 = rcq[1]; assign t_rc2 = rcq[2];
    integer p;
    always @(posedge clk or negedge rn_c)
        if (!rn_c) begin
            skn <= 2'd0; skw <= 1'b0; skr <= 1'b0; qr_q <= 1'b0; v2 <= 1'b0;
            for (p = 0; p < NP; p = p + 1) rcq[p][0] <= 1'b0;
        end else begin
            if (q_v && qr_q) begin sk[skw] <= q_a; skw <= ~skw; end
            if (take) skr <= ~skr;
            skn <= skn + (q_v && qr_q) - take;
            qr_q <= (skn + (q_v && qr_q) - take) < 2'd2;
            if (adv) v2 <= take;
            if (adv ? take : 1'b1) begin
                okn2 <= k_ok_n; okh2 <= k_ok_h; hzn2 <= k_hz_n; hzh2 <= k_hz_h; sel2 <= adv;
            end
            if (take) begin
                s2 <= {l_u, l_pos[SB-1:0]}; p2 <= l_part; pb2 <= l_pb; pos2 <= l_pos; ep2 <= l_ep;
                a2 <= DB'({l_u, l_pos[SB-1:0]}) * DB'(PB) + DB'(l_pb);
            end
            for (p = 0; p < NP; p = p + 1) rcq[p][0] <= issue && p2 == p;
        end
    always @(posedge clk) for (p = 0; p < NP; p = p + 1) rcq[p][RC-1:1] <= a2;
    reg [2:0] fq;
    always @(posedge clk or negedge rn_c) if (!rn_c) fq <= 3'd0;
        else fq <= {fq[2] | pflt[0][1] | pflt[1][1] | pflt[2][1], fq[1] | pflt[0][0] | pflt[1][0] | pflt[2][0], fq[0] | f0};
    reg [2:0] o_flt;
    always @(posedge clk or negedge rn_c) if (!rn_c) o_flt <= 3'd0; else o_flt <= fq;
    assign t_flt = o_flt;
`ifdef OT_HROW_RESET_ACK
    wire q_live;
    dsfd_mtp_reset_ack #(.N(2)) u_ack_c(.clk(ck),.request_n(rst),.local_release({rn_c,q_live}),.consumer_live(q_live),.reset_initialized(1'b1),.ack(rst_ack[0]));
    for(genvar ai=0;ai<6;ai=ai+1) begin:g_ack_a
      if(LOCAL_GROUP_SLOTS==0)begin:g_old
      dsfd_mtp_reset_ack u_ack(.clk(ck),.request_n(rst),.local_release(rn_a[ai]),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(rst_ack[ai+1]));
      end else begin:g_local
`ifdef OT_HROW_LOCAL_MUT_RST_WITNESS
        dsfd_mtp_reset_ack u_ack(.clk(ck),.request_n(rst),.local_release(rn_group[ai*GPH]),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(rst_ack[ai+1]));
`else
        dsfd_mtp_reset_ack #(.N(GPH)) u_ack(.clk(ck),.request_n(rst),.local_release(rn_group[ai*GPH+:GPH]),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(rst_ack[ai+1]));
`endif
      end
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------
// rev 5 (el1011-ds-mtp hrow-r5 2026-10-12, owner GLUE PLACEMENT; the rev-3 cluster carried 140,653 flops on one clock
// root and failed reg2reg -7.7 ns on bwd -> bank f_w, a 1,039-b register fanning out to 2 banks across the store).
// The per-bank glue goes INTO the bank tiles: a part's 10 banks form a systolic chain.  Write and read commands enter
// the chain head and move one tile every 2 edges (pin flop -> out flop); each bank decodes its own enables against a
// bank-id strap; the response bus runs the SAME way and each bank ORs its (valid-gated) data in at its out flop, so
// every bank of a part answers at the chain end at the same depth (in order, no collisions: one read a cycle, one bank
// a read).  No pair nodes, no part ORs, no store-wide relay trees.  Tiles (every port on a pin flop / out flop):
//   dsfd_mtp_hrow_ing x 3 (drain receiver + FSM + WK-edge write delay), dsfd_mtp_hrow_hub x 1 (unchanged),
//   dsfd_mtp_hrow_cbe x 15 (chain W -> E), dsfd_mtp_hrow_cbw x 15 (chain E -> W; same core, mirrored pin plan, so the
//   snake turns without a mirrored macro): part p = row a: 5 x cbe, row b: 5 x cbw; head and end on the same (west)
//   side next to the ing tiles and the hub.
// ---------------------------------------------------------------------------------------------------------------

// receiver for a consumer that is always ready: the ot_dsrom_mtp_lrx_rtt_core sequences with c_ready = 1 (queue empty
// for ever: push needs ne, ne needs push; every grant = (0 + inflight <= D - 1) = 1)
module ot_dsrom_mtp_hrow_drx #(parameter integer W = 514) (
    input  wire         clk, rst_n,
    input  wire         l_valid,
    output wire         l_ready,
    input  wire [W-1:0] l_data,
    output wire         c_valid,
    output wire [W-1:0] c_data
`ifdef OT_HROW_RESET_ACK
    ,output wire rst_live
`endif
);
    reg live, g0, pv, valid; reg [W-1:0] pd, data;
    always @(posedge clk) live <= rst_n;
    always @(posedge clk) begin pv <= l_valid; pd <= l_data; end
    always @(posedge clk) begin
        g0 <= live;
        valid <= live && pv;
        if (live && pv) data <= pd;
    end
    assign l_ready = g0; assign c_valid = valid; assign c_data = data;
`ifdef OT_HROW_RESET_ACK
 assign rst_live=live;
`endif
endmodule

// chain bank core: one bank (4 x ot_sram_1r1w_1024x256 side by side in bits) + its chain stage
//   write {d 1024, a 14, v}: pin flop wi (bank write enable = v && a[13:10] == id, at the edge after wi: as rev-3's
//   bank pin flop), out flop wo; read {a 14, v}: ri / ro likewise; response {d, v}: pin flop di, out flop
//   dq = di | (capture & valid): the bank's data joins the bus 3 edges after ri (rev-3 bank latency), so a bank k hops
//   down the chain answers at the end 2 N + 1 edges after the head pin flop for every k
module ot_dsrom_mtp_hrow_cbcore (
    input  wire          clk, rn,
    input  wire [3:0]    bid,
    input  wire [1038:0] f_w,  output wire [1038:0] t_w,
    input  wire [14:0]   f_r,  output wire [14:0]   t_r,
    input  wire [1024:0] f_d,  output wire [1024:0] t_d
);
    // wi/ri carry keep too: without it yosys opt_merge folds each un-kept chain pin flop into the kept macro launch
    // copy with the same D (r7 netlist: wi/ri 5 cells each; one flop drove SRAM wd_in AND the forwarding register).
    (* keep = 1 *) reg [1038:0] wi; (* keep = 1 *) reg [14:0] ri;
    reg [1038:0] wo; reg [14:0] ro; reg [1024:0] di, dq; reg [3:0] id; reg [1023:0] cap; reg s1, s2;
    wire we = wi[0] && wi[14:11] == id;
    wire re = ri[0] && ri[14:11] == id;
    always @(posedge clk or negedge rn)
        if (!rn) begin wi[0] <= 1'b0; wo[0] <= 1'b0; ri[0] <= 1'b0; ro[0] <= 1'b0; di[0] <= 1'b0; dq[0] <= 1'b0;
                       s1 <= 1'b0; s2 <= 1'b0; end
        else begin wi[0] <= f_w[0]; wo[0] <= wi[0]; ri[0] <= f_r[0]; ro[0] <= ri[0]; di[0] <= f_d[0];
                   dq[0] <= di[0] | s2; s1 <= re; s2 <= s1; end
    always @(posedge clk) begin
        id <= bid;
        wi[1038:1] <= f_w[1038:1]; wo[1038:1] <= wi[1038:1];
        ri[14:1] <= f_r[14:1]; ro[14:1] <= ri[14:1];
        di[1024:1] <= f_d[1024:1]; dq[1024:1] <= di[1024:1] | (cap & {1024{s2}});
    end
    wire [1023:0] rdo;
    genvar gc;
    generate for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
        // Dedicated kept launch copies: chain pin flops wi/ri feed only the
        // forwarding registers; each macro gets local address/data launch flops.
        // Capture the same input edge as wi/ri, preserving SRAM and chain latency.
        (* keep = 1 *) reg [9:0] macro_wa, macro_ra;
        (* keep = 1 *) reg [255:0] macro_wd;
        always @(posedge clk) begin
            macro_wa <= f_w[10:1]; macro_ra <= f_r[10:1];
            macro_wd <= f_w[15 + 256*gc +: 256];
        end
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk),
            .r_ce_in(re), .r_addr_in(macro_ra), .rd_out(rdo[256*gc +: 256]),
            .w_ce_in(we), .w_addr_in(macro_wa), .wd_in(macro_wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(18'b0), .cr_en(2'b0), .cr_sel(16'b0));
    end endgenerate
    always @(posedge clk) cap <= rdo;
    assign t_w = wo; assign t_r = ro; assign t_d = dq;
endmodule

// the two hardened chain tiles (same core; cbe: in on W, out on E; cbw: in on E, out on W -- pin plans in the specs)
module dsfd_mtp_hrow_cbe (
    input  wire       ck, rst, input wire [3:0] f_bid,
    input  wire [1038:0] f_w, output wire [1038:0] t_w, input wire [14:0] f_r, output wire [14:0] t_r,
    input  wire [1024:0] f_d, output wire [1024:0] t_d
`ifdef OT_HROW_RESET_ACK
    ,output wire rst_ack
`endif
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn));
    ot_dsrom_mtp_hrow_cbcore u_c (.clk(ck), .rn(rn), .bid(f_bid), .f_w(f_w), .t_w(t_w), .f_r(f_r), .t_r(t_r),
                                  .f_d(f_d), .t_d(t_d));
`ifdef OT_HROW_RESET_ACK
    dsfd_mtp_reset_ack u_ack(.clk(ck),.request_n(rst),.local_release(rn),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(rst_ack));
`endif
endmodule
module dsfd_mtp_hrow_cbw (
    input  wire       ck, rst, input wire [3:0] f_bid,
    input  wire [1038:0] f_w, output wire [1038:0] t_w, input wire [14:0] f_r, output wire [14:0] t_r,
    input  wire [1024:0] f_d, output wire [1024:0] t_d
`ifdef OT_HROW_RESET_ACK
    ,output wire rst_ack
`endif
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn));
    ot_dsrom_mtp_hrow_cbcore u_c (.clk(ck), .rn(rn), .bid(f_bid), .f_w(f_w), .t_w(t_w), .f_r(f_r), .t_r(t_r),
                                  .f_d(f_d), .t_d(t_d));
`ifdef OT_HROW_RESET_ACK
    dsfd_mtp_reset_ack u_ack(.clk(ck),.request_n(rst),.local_release(rn),.consumer_live(1'b1),.reset_initialized(1'b1),.ack(rst_ack));
`endif
endmodule

// composition model (the die): tiles + die relays.  Die contract (ordering, exact as rev 3):
//   E = CQ - 1 relays ing -> hub (events, faults); R = CQ relays hub -> chain head (read commands);
//   WD = 2 CQ + 1 - WK relays ing -> chain head (write commands; 0 at CQ = 3: the head bank abuts its ing tile);
//   P relays chain end -> hub, EQUAL for the three parts (R equal too); chain hops: tile to tile, no relay.
module dsfd_mtp_hrow_tc #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer FWD_P = 9, parameter integer RET_P = 9,
    parameter integer FWD_Q = 6, parameter integer RET_Q = 6,
    parameter integer CQ = 3, parameter integer WK = 7, parameter integer P = 2
) (
    input  wire           ck, rst,
    input  wire [514:0]   f_hp0, f_hp1, f_hp2,
    output wire [2:0]     t_hpg,
    input  wire [AW:0]    f_vrq,
    output wire           t_vrq,
    output wire [1024:0]  t_vrs,
    input  wire [USER_W:0] f_clr,
    output wire [2:0]     t_flt
);
    localparam integer WD = 2 * CQ + 1 - WK;
    initial if (CQ < 1 || WD < 0) $fatal(1, "hrow_tc: CQ >= 1 and WK <= 2 CQ + 1");
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck), .rst_n_async(rst), .rst_n(rn));
    wire [514:0] fin [0:2];
    assign fin[0] = f_hp0; assign fin[1] = f_hp1; assign fin[2] = f_hp2;
    wire [20:0] ev [0:2]; wire [20:0] evh [0:2]; wire [1:0] ifl [0:2]; wire [1:0] iflh [0:2];
    wire [14:0] rc [0:2]; wire [1024:0] pp [0:2]; wire [1024:0] pph [0:2];
    genvar gp, gk;
    generate for (gp = 0; gp < 3; gp = gp + 1) begin : g_part
        wire [1038:0] wc; wire [1038:0] cw [0:10]; wire [14:0] cr [0:10]; wire [1024:0] cd [0:10];
        dsfd_mtp_hrow_ing #(.NW(NW), .USER_W(USER_W), .MAXU(MAXU), .RS(RS), .FWD_P(FWD_P), .RET_P(RET_P), .WK(WK)) u_ig (
            .ck(ck), .rst(rst), .f_hp(fin[gp]), .t_hpg(t_hpg[gp]), .f_pid(gp[1:0]), .t_wc(wc), .t_ev(ev[gp]), .t_flt(ifl[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(21), .N(CQ - 1)) u_ev (.clk(ck), .rst_n(rn), .i(ev[gp]), .o(evh[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(2), .N(CQ - 1)) u_if (.clk(ck), .rst_n(rn), .i(ifl[gp]), .o(iflh[gp]));
        ot_dsrom_mtp_hrow_rly #(.W(1039), .N(WD)) u_wd (.clk(ck), .rst_n(rn), .i(wc), .o(cw[0]));
        ot_dsrom_mtp_hrow_rly #(.W(15), .N(CQ)) u_rc (.clk(ck), .rst_n(rn), .i(rc[gp]), .o(cr[0]));
        assign cd[0] = '0;
        for (gk = 0; gk < 10; gk = gk + 1) begin : g_c
            if (gk < 5) begin : g_e
                dsfd_mtp_hrow_cbe u_b (.ck(ck), .rst(rst), .f_bid(4'(gk)), .f_w(cw[gk]), .t_w(cw[gk+1]), .f_r(cr[gk]),
                                       .t_r(cr[gk+1]), .f_d(cd[gk]), .t_d(cd[gk+1]));
            end else begin : g_w
                dsfd_mtp_hrow_cbw u_b (.ck(ck), .rst(rst), .f_bid(4'(gk)), .f_w(cw[gk]), .t_w(cw[gk+1]), .f_r(cr[gk]),
                                       .t_r(cr[gk+1]), .f_d(cd[gk]), .t_d(cd[gk+1]));
            end
        end
        ot_dsrom_mtp_hrow_rly #(.W(1025), .N(P)) u_rp (.clk(ck), .rst_n(rn), .i(cd[10]), .o(pph[gp]));
    end endgenerate
    dsfd_mtp_hrow_hub #(.USER_W(USER_W), .MAXU(MAXU), .RS(RS), .AW(AW), .FWD_Q(FWD_Q), .RET_Q(RET_Q)) u_hub (
        .ck(ck), .rst(rst), .f_vrq(f_vrq), .t_vrq(t_vrq), .t_vrs(t_vrs), .f_clr(f_clr), .t_flt(t_flt),
        .f_ev0(evh[0]), .f_ev1(evh[1]), .f_ev2(evh[2]), .f_if0(iflh[0]), .f_if1(iflh[1]), .f_if2(iflh[2]),
        .t_rc0(rc[0]), .t_rc1(rc[1]), .t_rc2(rc[2]), .f_pr0(pph[0]), .f_pr1(pph[1]), .f_pr2(pph[2]));
endmodule

// Kept state prevents equivalent two-edge regional conditioners merging into
// a single high-fanout registered reset driver. Candidate-only instances.
module dsfd_mtp_hrow_group_rst(input wire ck,rst,output wire rn);
 (* keep=1 *) reg [1:0] s;
 always @(posedge ck or negedge rst) if(!rst)s<=0;else s<={s[0],1'b1};
 assign rn=s[1];
endmodule
