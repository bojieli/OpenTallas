`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// Main-model hidden rows for the DSpark seed (mtp-dsbind 2026-10-10).
//
// The seed projection (mtp.0.main_proj, K = 15,360) reads, for every committed position, mh = the BF16 HC means of the
// residual at the input of layers 37, 38 and 39 (3 parts x 5,120 BF16 = 3 x 80 beats of 1,024 b).  Each part is
// captured on the stage die that holds the layer (rank k) and must reach DSpark primary die P.k.
//
// Transport (ds-1010 lane decision: MTP traffic on DEDICATED lanes, never a queue in the collective core): one
// dedicated board lane per part (stage die of layer 37 / 38 / 39, rank k -> P.k; the lane = one more closed lane tile
// dsfd_coll_lane_w LCR 1 on a --mtp-links SerDes, as the head-die MTP lane), carrying the grant-protocol flit stream of
// ot_dsrom_mtp_hrow_tx: a header flit {user, pos, issue epoch, part} then 160 data flits (80 beats x 2 halves).
//
//   ot_dsrom_mtp_hrow_tx   stage die: {header} + 80 beats (valid/ready) -> grant-protocol link, flit {hdr, last, 512}
//   dsfd_mtp_hrow          primary die: 3 RTT-sized part receivers + the ROW STORE + the seed client's read port
//                          (grant-protocol request {epoch, user, pos mod 256, beat}, in-order 1,024-b response), the
//                          port dsfd_mtp_seed_launch reads.  The closed VM keeps its ports: the store holds
//                          MAXU x RS rows x 30 KB (3.9 MB at 8 x 16), far beyond the VM slab.
//
// Exactness by construction (versioned rows).  A row is identified by {user, pos, issue epoch}: positions squashed
// by a rejection are re-issued under epoch + 1, so their old rows (which land first: one in-order lane per part) and
// the re-verified rows differ in the epoch.  A read for {epoch e, user, pos} is served only when ALL THREE parts of
// slot {user, pos mod RS} carry exactly {pos, e} and are complete; otherwise the read waits (a late re-verified row).
// A header landing in a slot whose part holds a DIFFERENT position that was never read is an overrun (ring too small,
// or a dropped part that blocked the slot): sticky fault[0]; a header on the wrong part port: fault[1]; a data flit
// without a header: fault[2].
// Mutants (negative controls): OT_HROW_MUT_NOEPOCH (serve any epoch of the position), OT_HROW_MUT_NOPART (serve when
// the requested beat's own part is complete, ignoring the other two parts).
// ---------------------------------------------------------------------------------------------------------------
module ot_dsrom_mtp_hrow_tx #(parameter integer NW = 21, parameter integer USER_W = 10,
                              parameter integer HW = USER_W + NW + 4 + 2) (
    input  wire          clk, rst_n,
    input  wire          h_v,              // row header {user, pos, issue epoch, part}
    output wire          h_r,
    input  wire [HW-1:0] h_d,
    input  wire          b_v,              // 80 beats of 64 BF16
    output wire          b_r,
    input  wire [1023:0] b_d,
    output wire          l_valid,
    input  wire          l_ready,          // grant from the receiver
    output wire [513:0]  l_data             // {hdr flag, last, 512}
);
    reg [1:0] st;                          // 0 header, 1 lo half, 2 hi half
    reg [6:0] nb;
    reg [511:0] hi;
    wire cv; wire cr; reg [513:0] cd;
    assign cv = (st == 2'd0) ? h_v : (st == 2'd1) ? b_v : 1'b1;
    always @(*) case (st)
        2'd0: cd = {1'b1, 1'b0, {(512-HW){1'b0}}, h_d};
        2'd1: cd = {1'b0, 1'b0, b_d[511:0]};
        default: cd = {1'b0, nb == 7'd80, hi};
    endcase
    assign h_r = (st == 2'd0) && cr;
    assign b_r = (st == 2'd1) && cr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin st <= 2'd0; nb <= 7'd0; end
        else if (cv && cr) case (st)
            2'd0: begin st <= 2'd1; nb <= 7'd0; end
            2'd1: begin st <= 2'd2; hi <= b_d[1023:512]; nb <= nb + 7'd1; end
            default: st <= (nb == 7'd80) ? 2'd0 : 2'd1;
        endcase
    ot_dsrom_mtp_ltx #(.W(514)) u_tx (.clk(clk), .rst_n(rst_n), .c_valid(cv), .c_ready(cr), .c_data(cd),
        .l_valid(l_valid), .l_ready(l_ready), .l_data(l_data));
endmodule

// the row store core (behind the receivers): NP part ingress ports, one in-order read port
module ot_dsrom_mtp_hrow_store #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer NP = 3, parameter integer PB = 80,
    parameter integer CQ = 3,     // relay stages part ingress <-> central tag unit (events in, read commands out)
    parameter integer DD = 2,     // relay stages part root -> bank pair (the last one decodes the bank enables)
    parameter integer RD = 2,     // relay stages bank pair -> part return root
    parameter integer RP = 4      // relay stages part return root -> output OR
) (
    input  wire                 clk, rst_n,
    input  wire [NP-1:0]        i_v,
    output wire [NP-1:0]        i_r,
    input  wire [NP*514-1:0]    i_d,
    input  wire                 c_v,                 // host: clear a user's slots
    input  wire [USER_W-1:0]    c_user,
    input  wire                 q_v,                 // read request {epoch 4, user, pos 8, beat 8}
    output wire                 q_r,
    input  wire [AW-1:0]        q_a,
    output reg                  r_v,
    output reg  [1023:0]        r_d,
    output wire [2:0]           fault
);
    // rev 3 (el1011-ds-mtp 2026-10-11, owner textbook audit): hierarchical store.
    //   part p ingress (beside its link pin): header / beat FSM, local faults, write commands through a WDLY-stage delay
    //     line to the part root; header / completion events to the central tag unit through CQ relays
    //   central tag unit (beside the request / response pins): tags, complete, generations; a skid-buffered request
    //     queue, a REGISTERED 128-slot lookup and an issue stage with a one-cycle slot-hazard re-check (retry on miss);
    //     read commands to the part roots through CQ relays
    //   part root -> DD relays (per bank pair) -> hardened banks dsfd_mtp_hrow_bank (registered seams, local clock tree)
    //   bank -> pair OR -> RD relays -> part OR -> RP relays -> output OR: every bank has the same depth (in order)
    // Ordering (same relative order as the flat store at every bank): a read that did not see a part's header reaches
    // the part root at most 2 CQ + 1 edges after the header, the header's first write at least 2 + WDLY edges after it;
    // a read that saw the completion reaches the root at least 2 CQ + 3 edges after the last write's issue, which lands
    // WDLY edges after it.  WDLY = 2 CQ + 1 meets both strictly.
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer SB = $clog2(RS);
    localparam integer NS = MAXU * RS;                 // slots
    localparam integer SW = UB + SB;
    localparam integer DP = NS * PB;                   // beats a part
    localparam integer NM = (DP + 1023) / 1024;        // banks a part (1024 rows x 1024 b each)
    localparam integer NQ = (NM + 1) / 2;              // bank pairs a part
    localparam integer DB = $clog2(NM * 1024);
    localparam integer WDLY = 2 * CQ + 1;
    localparam integer WC = 1 + DB + 1024;             // write command {d, a, v}
    localparam integer RC = 1 + DB;                    // read command {a, v}
    localparam integer EV = 2 + SW + 12;               // event {kind (1 header / 0 complete), v, slot, pos 8, epoch 4}
    initial if ((1 << SB) != RS || RS > 256 || NP != 3 || CQ < 1 || DD < 1) $fatal(1, "hrow_store: bad dimensions");
    // ---------------- regional resets (one synchroniser a region; datapath registers carry no reset)
    wire rn_c; wire [NP-1:0] rn_p;
    ot_dsrom_mtp_rstsync u_rsc (.clk(clk), .rst_n_async(rst_n), .rst_n(rn_c));
    assign i_r = {NP{1'b1}};                           // the receivers' flits are always taken (one write port a part)
    // part <-> central wires
    wire [EV-1:0] ev_c [0:NP-1];                       // events at the central end of their relays
    wire [RC-1:0] rc_c [0:NP-1];                       // read commands at the central end
    wire [1024:0] pr [0:NP-1];                         // part results {d, v} at the output end of their relays
    wire [1:0] pflt [0:NP-1];
    genvar gp, gq, gk;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_part
        ot_dsrom_mtp_rstsync u_rsp (.clk(clk), .rst_n_async(rst_n), .rst_n(rn_p[gp]));
        wire rn = rn_p[gp];
        wire [513:0] d = i_d[gp*514 +: 514];
        // ---------------- ingress FSM (beside the part link)
        reg inh, ihalf; reg [SW-1:0] islot; reg [6:0] ibeat; reg [511:0] ilo; reg [1:0] flt;
        reg [EV-1:0] ev0; reg [WC-1:0] wc0;
        wire [1:0] hq = d[1:0]; wire [3:0] he = d[5:2]; wire [NW-1:0] hp = d[6 +: NW]; wire [UB-1:0] hu = d[6 + NW +: UB];
        always @(posedge clk or negedge rn)
            if (!rn) begin inh <= 1'b0; ihalf <= 1'b0; flt <= 2'b0; ev0 <= '0; wc0[0] <= 1'b0; islot <= '0; ibeat <= 7'd0; end
            else begin
                ev0[EV-2] <= 1'b0; wc0[0] <= 1'b0;
                if (i_v[gp]) begin
                    if (d[513]) begin
                        if (hq != gp[1:0] || inh) flt[0] <= 1'b1;
                        ev0[EV-2] <= 1'b1; ev0[EV-1] <= 1'b1; ev0[0 +: 12 + SW] <= {{hu, hp[SB-1:0]}, hp[7:0], he};
                        islot <= {hu, hp[SB-1:0]}; ibeat <= 7'd0; ihalf <= 1'b0; inh <= 1'b1;
                    end else if (!inh) flt[1] <= 1'b1;
                    else if (!ihalf) ihalf <= 1'b1;
                    else begin
                        wc0[0] <= 1'b1;
                        ihalf <= 1'b0; ibeat <= ibeat + 7'd1;
                        if (d[512]) begin                         // last flit: the part is complete
                            inh <= 1'b0; ev0[EV-2] <= 1'b1; ev0[EV-1] <= 1'b0; ev0[0 +: 12 + SW] <= {islot, 12'd0};
                            if (ibeat != 7'd79) flt[1] <= 1'b1;
                        end
                    end
                end
            end
        // ilo is datapath: no reset, own block (a non-reset bit in an async-reset block synthesises as an async-load flop)
        always @(posedge clk) if (i_v[gp] && !d[513] && inh && !ihalf) ilo <= d[511:0];
        always @(posedge clk) if (i_v[gp] && !d[513] && inh && ihalf) begin
            wc0[WC-1:1] <= {d[511:0], ilo, DB'(islot) * DB'(PB) + DB'(ibeat)};
        end
        assign pflt[gp] = flt;
        // events -> central (CQ relays)
        reg [EV-1:0] evr [0:CQ-1];
        for (gk = 0; gk < CQ; gk = gk + 1) begin : g_evr
            always @(posedge clk or negedge rn) if (!rn) evr[gk][EV-2] <= 1'b0;
                                                else evr[gk][EV-2] <= (gk == 0) ? ev0[EV-2] : evr[(gk == 0) ? 0 : gk-1][EV-2];
            always @(posedge clk) begin
                evr[gk][EV-1] <= (gk == 0) ? ev0[EV-1] : evr[(gk == 0) ? 0 : gk-1][EV-1];
                evr[gk][EV-3:0] <= (gk == 0) ? ev0[EV-3:0] : evr[(gk == 0) ? 0 : gk-1][EV-3:0];
            end
        end
        assign ev_c[gp] = evr[CQ-1];
        // write commands: WDLY-stage delay line to the part root
        reg [WC-1:0] wdl [0:WDLY-1];
        for (gk = 0; gk < WDLY; gk = gk + 1) begin : g_wdl
            always @(posedge clk or negedge rn) if (!rn) wdl[gk][0] <= 1'b0;
                                                else wdl[gk][0] <= (gk == 0) ? wc0[0] : wdl[(gk == 0) ? 0 : gk-1][0];
            always @(posedge clk) wdl[gk][WC-1:1] <= (gk == 0) ? wc0[WC-1:1] : wdl[(gk == 0) ? 0 : gk-1][WC-1:1];
        end
        // read commands from central (CQ relays)
        reg [RC-1:0] rcr [0:CQ-1];
        for (gk = 0; gk < CQ; gk = gk + 1) begin : g_rcr
            always @(posedge clk or negedge rn) if (!rn) rcr[gk][0] <= 1'b0;
                                                else rcr[gk][0] <= (gk == 0) ? rc_c[gp][0] : rcr[(gk == 0) ? 0 : gk-1][0];
            always @(posedge clk) rcr[gk][RC-1:1] <= (gk == 0) ? rc_c[gp][RC-1:1] : rcr[(gk == 0) ? 0 : gk-1][RC-1:1];
        end
        wire [WC-1:0] wroot = wdl[WDLY-1];
        wire [RC-1:0] rroot = rcr[CQ-1];
        // ---------------- part root -> bank pairs -> banks
        wire [1024:0] qd [0:NQ-1];                     // pair results at the part return root
        for (gq = 0; gq < NQ; gq = gq + 1) begin : g_q
            reg [WC-1:0] wq [0:DD-2 < 0 ? 0 : DD-2];
            reg [RC-1:0] rq [0:DD-2 < 0 ? 0 : DD-2];
            wire [WC-1:0] wl = (DD > 1) ? wq[DD-2] : wroot;
            wire [RC-1:0] rl = (DD > 1) ? rq[DD-2] : rroot;
            for (gk = 0; gk < DD - 1; gk = gk + 1) begin : g_d
                always @(posedge clk or negedge rn)
                    if (!rn) begin wq[gk][0] <= 1'b0; rq[gk][0] <= 1'b0; end
                    else begin wq[gk][0] <= (gk == 0) ? wroot[0] : wq[(gk == 0) ? 0 : gk-1][0];
                               rq[gk][0] <= (gk == 0) ? rroot[0] : rq[(gk == 0) ? 0 : gk-1][0]; end
                always @(posedge clk) begin wq[gk][WC-1:1] <= (gk == 0) ? wroot[WC-1:1] : wq[(gk == 0) ? 0 : gk-1][WC-1:1];
                                            rq[gk][RC-1:1] <= (gk == 0) ? rroot[RC-1:1] : rq[(gk == 0) ? 0 : gk-1][RC-1:1]; end
            end
            // last distribution stage: decoded per-bank enables (registered), shared address / data
            integer bb;
            reg [1:0] bwe, bre; reg [9:0] bwa, bra; reg [1023:0] bwd;
            always @(posedge clk or negedge rn)
                if (!rn) begin bwe <= 2'b0; bre <= 2'b0; end
                else for (bb = 0; bb < 2; bb = bb + 1) begin
                    bwe[bb] <= wl[0] && wl[DB:11] == (2 * gq + bb);
                    bre[bb] <= rl[0] && rl[DB:11] == (2 * gq + bb);
                end
            always @(posedge clk) begin bwa <= wl[10:1]; bwd <= wl[WC-1:DB+1]; bra <= rl[10:1]; end
            wire [1024:0] bt [0:1];
            for (gk = 0; gk < 2; gk = gk + 1) begin : g_b
                if (2 * gq + gk < NM) begin : g_on
                    dsfd_mtp_hrow_bank u_bk (.ck(clk), .rst(rn), .f_w({bwd, bwa, bwe[gk]}), .f_r({bra, bre[gk]}),
                                             .t_d(bt[gk]));
                end else begin : g_off
                    assign bt[gk] = '0;
                end
            end
            // pair OR (bank outputs are valid-gated flops) -> RD relays
            reg [1024:0] po [0:RD];
            always @(posedge clk or negedge rn) if (!rn) po[0][0] <= 1'b0; else po[0][0] <= bt[0][0] | bt[1][0];
            always @(posedge clk) po[0][1024:1] <= bt[0][1024:1] | bt[1][1024:1];
            for (gk = 1; gk <= RD; gk = gk + 1) begin : g_r
                always @(posedge clk or negedge rn) if (!rn) po[gk][0] <= 1'b0; else po[gk][0] <= po[(gk == 0) ? 0 : gk-1][0];
                always @(posedge clk) po[gk][1024:1] <= po[(gk == 0) ? 0 : gk-1][1024:1];
            end
            assign qd[gq] = po[RD];
        end
        // part OR -> RP relays
        reg [1024:0] pacc; integer j;
        always @(*) begin pacc = '0; for (j = 0; j < NQ; j = j + 1) pacc = pacc | qd[j]; end
        reg [1024:0] pp [0:RP];
        always @(posedge clk or negedge rn) if (!rn) pp[0][0] <= 1'b0; else pp[0][0] <= pacc[0];
        always @(posedge clk) pp[0][1024:1] <= pacc[1024:1];
        for (gk = 1; gk <= RP; gk = gk + 1) begin : g_p
            always @(posedge clk or negedge rn) if (!rn) pp[gk][0] <= 1'b0; else pp[gk][0] <= pp[(gk == 0) ? 0 : gk-1][0];
            always @(posedge clk) pp[gk][1024:1] <= pp[(gk == 0) ? 0 : gk-1][1024:1];
        end
        assign pr[gp] = pp[RP];
    end endgenerate
    // ---------------- output OR (one part answers a cycle)
    always @(posedge clk or negedge rn_c) if (!rn_c) r_v <= 1'b0; else r_v <= pr[0][0] | pr[1][0] | pr[2][0];
    always @(posedge clk) r_d <= pr[0][1024:1] | pr[1][1024:1] | pr[2][1024:1];
    // ---------------- central tag unit
    reg [11:0] tag  [0:NP-1][0:NS-1];                  // {pos[7:0], epoch}: no reset (guarded by cmp / ld)
    reg        cmp  [0:NP-1][0:NS-1];
    reg        wg   [0:NP-1][0:NS-1];
    reg        rg   [0:NP-1][0:NS-1];
    reg        ld   [0:NP-1][0:NS-1];
    reg        f0;
    // request skid (2 entries): q_r is a register
    reg [AW-1:0] sk [0:1]; reg [1:0] skn; reg skw, skr;
    reg qr_q;
    assign q_r = qr_q;
    // Q1: head of the skid; Q2: looked-up request
    reg v2, ok2, hz2; reg [SW-1:0] s2; reg [1:0] p2; reg [6:0] pb2; reg [DB-1:0] a2;
    wire issue = v2 && ok2 && !hz2;
    wire adv = !v2 || issue;                           // Q2 takes a new request this edge
    wire take = adv && skn != 0;
    // the request whose lookup is registered this edge: the retried Q2 request or the skid head
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
    // events consumed this edge that touch slot ks (any part header, or a clear of its user): the lookup above used the
    // state before them, so the issue next edge must not trust it
    reg k_hz; integer ei;
    always @(*) begin
        k_hz = c_v && c_user < MAXU && c_user[UB-1:0] == ks[SW-1:SB];
        for (ei = 0; ei < NP; ei = ei + 1)
            if (ev_c[ei][EV-2] && ev_c[ei][EV-1] && ev_c[ei][12 +: SW] == ks) k_hz = 1'b1;
    end
    // read commands to the part roots
    reg [RC-1:0] rcq [0:NP-1];
    assign rc_c[0] = rcq[0]; assign rc_c[1] = rcq[1]; assign rc_c[2] = rcq[2];
    integer p, s;
    always @(posedge clk or negedge rn_c)
        if (!rn_c) begin
            skn <= 2'd0; skw <= 1'b0; skr <= 1'b0; qr_q <= 1'b0; v2 <= 1'b0; f0 <= 1'b0;
            for (p = 0; p < NP; p = p + 1) begin
                rcq[p][0] <= 1'b0;
                for (s = 0; s < NS; s = s + 1) begin cmp[p][s] <= 1'b0; wg[p][s] <= 1'b0; rg[p][s] <= 1'b0; ld[p][s] <= 1'b0; end
            end
        end else begin
            // skid
            if (q_v && qr_q) begin sk[skw] <= q_a; skw <= ~skw; end
            if (take) skr <= ~skr;
            skn <= skn + (q_v && qr_q) - take;
            qr_q <= (skn + (q_v && qr_q) - take) < 2'd2;
            // Q2
            if (adv) v2 <= take;
            if (adv ? take : 1'b1) begin
                ok2 <= k_ok; hz2 <= k_hz;
            end
            if (take) begin
                s2 <= {l_u, l_pos[SB-1:0]}; p2 <= l_part; pb2 <= l_pb; pos2 <= l_pos; ep2 <= l_ep;
                a2 <= DB'({l_u, l_pos[SB-1:0]}) * DB'(PB) + DB'(l_pb);
            end
            for (p = 0; p < NP; p = p + 1) rcq[p][0] <= issue && p2 == p;
            if (issue && pb2 == 7'd79) rg[p2][s2] <= wg[p2][s2];   // part read through: consumed
            // events
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
`ifdef OT_HROW_DBG
    integer dcy = 0; integer dn = 0;
    always @(posedge clk) begin
        dcy <= dcy + 1;
        if (issue && dn < 4000) begin dn <= dn + 1; $display("DBG %0d ISSUE p%0d s%0d pb%0d", dcy, p2, s2, pb2); end
        for (int z = 0; z < NP; z = z + 1) if (ev_c[z][EV-2]) $display("DBG %0d EV p%0d k%0d s%0d pos%0d", dcy, z, ev_c[z][EV-1], ev_c[z][12 +: SW], ev_c[z][11:4]);
        if (v2 && !issue && s2 == 4 && dn < 4000) begin dn <= dn + 1; $display("DBG %0d WAIT s%0d p%0d pb%0d ok%0d hz%0d", dcy, s2, p2, pb2, ok2, hz2); end
    end
`endif
    reg [2:0] fq;
    always @(posedge clk or negedge rn_c) if (!rn_c) fq <= 3'd0;
        else fq <= {fq[2] | pflt[0][1] | pflt[1][1] | pflt[2][1], fq[1] | pflt[0][0] | pflt[1][0] | pflt[2][0], fq[0] | f0};
    assign fault = fq;
endmodule

// dsfd_mtp_hrow: the primary-die master.  Part links in through RTT-sized receivers (FWD_P / RET_P stations each), the
// seed client's request link in through an RTT-sized receiver (FWD_Q / RET_Q), responses and faults from flops.
module dsfd_mtp_hrow #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer MAXU = 8, parameter integer RS = 16,
    parameter integer AW = 24, parameter integer FWD_P = 9, parameter integer RET_P = 9,
    parameter integer FWD_Q = 6, parameter integer RET_Q = 6
) (
    input  wire [0:0]     ck, rst,
    input  wire [514:0]   f_hp0, f_hp1, f_hp2,     // part links {flit 514, valid} (lane adapters)
    output wire [2:0]     t_hpg,                   // their grants
    input  wire [AW:0]    f_vrq,                   // seed client request {addr, valid} (= seedl t_vrq)
    output wire [0:0]     t_vrq,                   // grant (= seedl f_vrq)
    output wire [1024:0]  t_vrs,                   // response {data, valid} (= seedl f_vrs)
    input  wire [USER_W:0] f_clr,
    output wire [2:0]     t_flt
);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    wire [2:0] pv, pr; wire [3*514-1:0] pd;
    wire [514:0] fin [0:2];
    assign fin[0] = f_hp0; assign fin[1] = f_hp1; assign fin[2] = f_hp2;
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : g_rx
        ot_dsrom_mtp_lrx_rtt #(.W(514), .D(FWD_P + RET_P + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                               .FORWARD_HOPS(FWD_P), .RETURN_HOPS(RET_P)) u_p (
            .clk(ck[0]), .rst_n(rn), .l_valid(fin[g][0]), .l_ready(t_hpg[g]), .l_data(fin[g][514:1]),
            .c_valid(pv[g]), .c_ready(pr[g]), .c_data(pd[514*g +: 514]));
    end endgenerate
    wire qv, qr; wire [AW-1:0] qa;
    ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(FWD_Q + RET_Q + 4), .ENABLE_RTT(1), .OUTPUT_PIPE(1),
                           .FORWARD_HOPS(FWD_Q), .RETURN_HOPS(RET_Q)) u_q (
        .clk(ck[0]), .rst_n(rn), .l_valid(f_vrq[0]), .l_ready(t_vrq[0]), .l_data(f_vrq[AW:1]),
        .c_valid(qv), .c_ready(qr), .c_data(qa));
    reg [USER_W:0] i_clr;
    always @(posedge ck[0] or negedge rn) if (!rn) i_clr[0] <= 1'b0; else i_clr[0] <= f_clr[0];
    always @(posedge ck[0]) i_clr[USER_W:1] <= f_clr[USER_W:1];
    wire rv; wire [1023:0] rd; wire [2:0] flt;
    ot_dsrom_mtp_hrow_store #(.NW(NW), .USER_W(USER_W), .MAXU(MAXU), .RS(RS), .AW(AW)) u_st (
        .clk(ck[0]), .rst_n(rn), .i_v(pv), .i_r(pr), .i_d(pd), .c_v(i_clr[0]), .c_user(i_clr[USER_W:1]),
        .q_v(qv), .q_r(qr), .q_a(qa), .r_v(rv), .r_d(rd), .fault(flt));
    reg [1024:0] o_rs; reg [2:0] o_flt;
    always @(posedge ck[0] or negedge rn) if (!rn) begin o_rs[0] <= 1'b0; o_flt <= 3'd0; end
                                          else begin o_rs[0] <= rv; o_flt <= flt; end
    always @(posedge ck[0]) o_rs[1024:1] <= rd;
    assign t_vrs = o_rs; assign t_flt = o_flt;
endmodule

// dsfd_mtp_hrow_src: the stage-die master on the dies of layers 37 / 38 / 39 (PART 0 / 1 / 2), rank k: for every stage
// start the WFC kit reports (t_hep: one-cycle {v, user, pos, issue epoch}, dsfd_wfc_hep), read the position's HC-mean
// row (5,120 BF16 = 80 beats; written into the VM by the SU program at the layer input, VM ring of HR rows a user,
// address HBASE + {user mod 8, pos mod HR, beat}; the VM read waits for the row's completion -- s81-vm-1011 row-completion counter) and send
// {user, pos, issue epoch, PART} + the 80 beats on the dedicated hidden lane to P.k (ot_dsrom_mtp_hrow_tx).
// Events queue in an HQ-deep FIFO (sticky fault[0] on overflow); at most OUT beats are outstanding at the VM, landing in
// an OUT-deep beat FIFO, so the lane's 2-flits-a-beat pace never loses a response (fault[1] = FIFO overflow).
// Mutants: OT_HSRC_MUT_NOQ (no event queue: an event arriving while a row is in flight is lost),
//          OT_HSRC_MUT_STALEEP (the header carries the previous event's epoch).
module dsfd_mtp_hrow_src #(
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer PART = 0, parameter integer HR = 8,
    parameter integer VM_AW = 24, parameter integer HBASE = 0, parameter integer HQ = 8, parameter integer OUT = 8,
    parameter integer FWD_V = 6, parameter integer RET_V = 6
) (
    input  wire [0:0]          ck, rst,
    input  wire [USER_W+NW+4:0] f_hep,         // WFC kit t_hep {v, user, pos, epoch}
    output wire [VM_AW:0]      t_vrq,          // VM read request {addr, valid} (grant protocol)
    input  wire [0:0]          f_vrq,          // VM grant
    input  wire [1024:0]       f_vrs,          // VM response {data, valid}, in order
    output wire [514:0]        t_hp,           // hidden lane {flit 514, valid} (grant protocol)
    input  wire [0:0]          f_hpg,          // lane grant
    output wire [1:0]          t_flt
);
    localparam integer HW = USER_W + NW + 6;
    localparam integer RB = $clog2(HR);
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(ck[0]), .rst_n_async(rst[0]), .rst_n(rn));
    reg [USER_W+NW+4:0] i_hep; reg [1024:0] i_vrs;
    always @(posedge ck[0] or negedge rn) if (!rn) begin i_hep[USER_W+NW+4] <= 1'b0; i_vrs[0] <= 1'b0; end
                                         else begin i_hep[USER_W+NW+4] <= f_hep[USER_W+NW+4]; i_vrs[0] <= f_vrs[0]; end
    always @(posedge ck[0]) begin i_hep[USER_W+NW+3:0] <= f_hep[USER_W+NW+3:0]; i_vrs[1024:1] <= f_vrs[1024:1]; end
    // event FIFO
    reg [USER_W+NW+3:0] q [0:HQ-1]; reg [$clog2(HQ):0] qn; reg [$clog2(HQ)-1:0] qw, qr;
    reg [1:0] fault;
    // row engine
    reg act; reg [USER_W+NW+3:0] cur; reg [3:0] prev_ep; reg hdr_sent; reg [6:0] nrq; reg [6:0] nsent;
    reg [$clog2(OUT+1)-1:0] outst;
    wire rqv, rqr; wire [VM_AW-1:0] rqa;
    // beat FIFO
    reg [1023:0] bq [0:OUT-1]; reg [$clog2(OUT):0] bn; reg [$clog2(OUT)-1:0] bw, br_;
    wire hv, hr, bv, brd;
    wire pop_ev = !act && qn != 0;
    wire beat_pop = bv && brd;
`ifdef OT_HSRC_MUT_NOQ
    wire push_ev = i_hep[USER_W+NW+4] && !act && qn == 0;
`else
    wire push_ev = i_hep[USER_W+NW+4];
`endif
    assign rqv = act && nrq != 7'd80 && (outst + bn) < OUT;
    assign rqa = VM_AW'(HBASE) + {{(VM_AW-3-RB-7){1'b0}}, cur[4+NW +: 3], cur[4 + RB - 1:4], nrq};   // {user mod 8, pos mod HR, beat}
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin
            qn <= 0; qw <= 0; qr <= 0; fault <= 2'b0; act <= 1'b0; hdr_sent <= 1'b0; nrq <= 0; nsent <= 0; outst <= 0;
            bn <= 0; bw <= 0; br_ <= 0; prev_ep <= 4'd0;
        end else begin
            if (push_ev) begin
                if (qn == HQ) fault[0] <= 1'b1; else begin q[qw] <= i_hep[USER_W+NW+3:0]; qw <= qw + 1'b1; end
            end
            if (pop_ev) begin
                cur <= q[qr]; qr <= qr + 1'b1; act <= 1'b1; hdr_sent <= 1'b0; nrq <= 0; nsent <= 0;
            end
            qn <= qn + (push_ev && qn != HQ) - pop_ev;
            if (rqv && rqr) nrq <= nrq + 1'b1;
            outst <= outst + (rqv && rqr) - i_vrs[0];
            if (i_vrs[0]) begin
                if (bn == OUT) fault[1] <= 1'b1; else begin bq[bw] <= i_vrs[1024:1]; bw <= bw + 1'b1; end
            end
            bn <= bn + (i_vrs[0] && bn != OUT) - beat_pop;
            if (beat_pop) begin br_ <= br_ + 1'b1; nsent <= nsent + 1'b1; end
            if (hv && hr) hdr_sent <= 1'b1;
            if (act && beat_pop && nsent == 7'd79) begin act <= 1'b0; prev_ep <= cur[3:0]; end
        end
    assign hv = act && !hdr_sent;
`ifdef OT_HSRC_MUT_STALEEP
    wire [3:0] hep_e = prev_ep;
`else
    wire [3:0] hep_e = cur[3:0];
`endif
    wire [HW-1:0] hd = {cur[USER_W+NW+3:4+NW], cur[NW+3:4], hep_e, 2'(PART)};
    assign bv = act && hdr_sent && bn != 0;
    ot_dsrom_mtp_ltx #(.W(VM_AW)) u_rq (.clk(ck[0]), .rst_n(rn), .c_valid(rqv), .c_ready(rqr), .c_data(rqa),
        .l_valid(t_vrq[0]), .l_ready(f_vrq[0]), .l_data(t_vrq[VM_AW:1]));
    ot_dsrom_mtp_hrow_tx #(.NW(NW), .USER_W(USER_W)) u_tx (.clk(ck[0]), .rst_n(rn), .h_v(hv), .h_r(hr), .h_d(hd),
        .b_v(bv), .b_r(brd), .b_d(bq[br_]), .l_valid(t_hp[0]), .l_ready(f_hpg[0]), .l_data(t_hp[514:1]));
    reg [1:0] o_flt;
    always @(posedge ck[0] or negedge rn) if (!rn) o_flt <= 2'b0; else o_flt <= fault;
    assign t_flt = o_flt;
endmodule
