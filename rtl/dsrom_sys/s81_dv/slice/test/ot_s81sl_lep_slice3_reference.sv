`timescale 1ns/1ps
// Immutable reference core23fd77ae5 (TXRP1/RXSA1); no new successor control logic.
module ot_s81sl_lep_slice3_reference_core #(
    parameter integer DT = 512,        // TX landing FIFO depth per lane (flits; SRAM macro depth)
    parameter integer DR = 8,          // RX landing FIFO depth per lane (flits, flops) = the lane sender's CRED 8
    parameter integer CRED = 8,        // TX credits = the lane's core-face landing depth (ot_link_credit_rx DEPTH 8)
    parameter integer SRAM = 1,        // 1: TX storage in SRAM macros (0: flops, same cycle behaviour)
    parameter integer HOST_EN = 1,     // 1: host plane (THOST / TKD out, HOST / KS in, f_lf); 0: ring beats only
    parameter integer MU_EN = 0,       // 1: user-tag windows (TX stamp, RX strip / land / replay merge)
    parameter integer AB_EN = 0,       // 1: second lane pair (copy B static circuit)
    parameter integer NB = 80,         // ring beats per h message per endpoint (40,960 B / 4 end slices / 128 B)
    parameter integer TXRP = 0,        // 1: TX read pipeline register beside the SRAM column (+1 lo edge; S81-SLICE3-LEP)
    parameter integer RXSA = 0         // 1: grouped show-ahead RX head + registered one-hot selects (0 edges; MU_EN 0 only)
) (
    input  wire            clk,
    input  wire            rst_n,
    // slice outward line port
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    // link lanes (dsfd_coll_lane_* core side: lo = to link, li = from link)
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,        // lane receive enables (the lane rx word's valid bit)
    // fault collector: slice fault, lane faults {meso, gearbox, endpoint}
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,      // ot_pdie_ucie st {live, fault} of lane 0 / lane 1
    input  wire [1:0]      l1_st,
    // host plane (dsdv_seq_host host lane + key store), carried as non-ring link frames
    input  wire [76:0]     t_host,     // seq_host t_host {alive, st 11, t_v, t_d 64}  -> THOST frames
    input  wire [53:0]     t_kd,       // seq_host t_kd {done, tok 21, 32'b0}          -> TKD frames
    output wire [514:0]    f_host,     // -> seq_host f_host {h_cls 2, h_d 512, h_v}   <- HOST frames
    output wire [3:0]      f_lf,       // -> seq_host f_lf {fault, live} x 2 (lane 1, lane 0)
    output wire [52:0]     f_ks,       // -> seq_host f_ks {start, user 10, tok 21, pos 21} <- KS frames
    // MU (MU_EN 1): TX tag window command, RX tag, landing leaf ports
    input  wire [33:0]     mu_c,       // {pos 21, user 10, land, ab, v}
    output wire [31:0]     mu_rt,      // {v, user 10, pos 21} of the beat on ri this cycle
    output wire            ml_wv,      // -> dsdv_mu_land: a land = 1 tagged beat (full beat, tag kept)
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,      // <- dsdv_mu_land: replayed beat
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,       // <- dsdv_mu_land fault (collected here)
    // copy-B lane pair (AB_EN 1)
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output reg             fault
);
    localparam integer H = 552;
    localparam integer AT = $clog2(DT), AR = $clog2(DR);
    localparam integer NL = (AB_EN != 0) ? 4 : 2;      // lanes (2 per pair)
    localparam integer NBW = $clog2(NB + 1);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2;
    localparam integer TG = 1045;                      // tag field base: [TG] tag, [TG+1] land, user, pos
    // regional reset: the port drives only this relay (own synchroniser on this leaf's clock root); one copy per region
    wire [3:0] rr;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rstr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[3];                                   // host plane, outward-port valid, fault collector
    wire rnx = rr[2];                                  // RX landing + re-assembly
    reg [NL-1:0] rxv_r;
    always @(posedge clk or negedge rnx) if (!rnx) rxv_r <= {NL{1'b0}}; else rxv_r <= {NL{1'b1}};
    assign rxv = rxv_r[1:0];

    // ---------------------------------------------------------------- outward-port pin flops
    reg rov; reg [1103:0] roq;
    always @(posedge clk or negedge rn) if (!rn) rov <= 1'b0; else rov <= ro[0];
    always @(posedge clk) roq <= ro;
    // ---------------------------------------------------------------- host plane, TX: THOST / TKD frames
    // Link frame = one flit pair.  Ring beat: bit 0 = 1 (the beat itself).  Host-plane frame: bit 0 = 0, [3:1] type
    // (1 HOST, 2 KS: inbound; 3 THOST, 4 TKD: outbound), payload at [4 +: n] in the low half, the rest 0.
    // THOST is sent on t_v or on a change of {alive, st}; TKD on done.  A frame waits in its pending register while ring
    // beats (which never wait) take the lanes; a status-only change merges into a pending t_v frame; a second t_v / done
    // event while one is still pending is a sticky fault (the compiler's host slots respect the lane rate).
    wire hp_go, kp_go, herr; wire [76:0] ph_d; wire [53:0] pk_d;
    generate if (HOST_EN != 0) begin : g_htx
    reg [76:0] thq; reg [53:0] tkq;
    always @(posedge clk) begin thq <= t_host; tkq <= t_kd; end
    reg ph_v, pk_v, he; reg [76:0] pd; reg [53:0] kd; reg [11:0] st_l;
    wire ev_h = thq[64] || thq[76:65] != st_l, ev_k = tkq[53];
    assign hp_go = !rov && ph_v; assign kp_go = !rov && !ph_v && pk_v;
    assign herr = he; assign ph_d = pd; assign pk_d = kd;
    always @(posedge clk or negedge rn)
        if (!rn) begin ph_v <= 1'b0; pk_v <= 1'b0; he <= 1'b0; st_l <= 12'd0; end
        else begin
            if (hp_go) ph_v <= 1'b0;
            if (kp_go) pk_v <= 1'b0;
            if (ev_h) begin
                ph_v <= 1'b1; st_l <= thq[76:65];
`ifdef OT_S81SL_LEP_MUT_HDROP
                pd <= thq;                                             // MUTANT: a pending t_v word is overwritten
`else
                pd <= (ph_v && !hp_go && pd[64] && !thq[64]) ? {thq[76:65], pd[64:0]} : thq;
                if (ph_v && !hp_go && pd[64] && thq[64]) he <= 1'b1;
`endif
            end
            if (ev_k) begin pk_v <= 1'b1; kd <= tkq; if (pk_v && !kp_go) he <= 1'b1; end
        end
    end else begin : g_nhtx                            // HOST_EN 0: ring beats only (t_host / t_kd unread)
    assign hp_go = 1'b0; assign kp_go = 1'b0; assign herr = 1'b0; assign ph_d = 77'd0; assign pk_d = 54'd0;
    end endgenerate
    wire push = rov || hp_go || kp_go;
    // ---------------------------------------------------------------- MU TX tag window (MU_EN 1)
    wire wopen, wab; wire [32:0] wtag; wire terr;       // window open, pair B, {pos, user, land, 1}
    generate if (MU_EN != 0) begin : g_mtx
    reg [33:0] mcq; reg [NBW-1:0] wn; reg w_ab, te; reg [32:0] w_t;
    always @(posedge clk or negedge rn) if (!rn) mcq <= 34'd0; else mcq <= mu_c;   // command pin flop
    wire mcv = mcq[0];
    wire [9:0] mcu = mcq[12:3];
    wire ab_ok = (AB_EN != 0) && mcu != 10'd0;           // the latency user (0) is always on copy A
    always @(posedge clk or negedge rn)
        if (!rn) begin wn <= '0; w_ab <= 1'b0; te <= 1'b0; end
        else begin
            if (mcv) begin
                if (wn != '0 && !(rov && wn == NBW'(1))) te <= 1'b1;     // a window while one is open
                wn <= NBW'(NB); w_ab <= mcq[1] && ab_ok; w_t <= {mcq[33:13], mcq[12:3], mcq[2], 1'b1};
                if (mcq[1] && !ab_ok) te <= 1'b1;                        // ab with user 0 / without pair B
            end else if (rov && wn != '0) wn <= wn - 1'b1;
            if (rov && wn != '0 && roq[3:1] != K_XB && roq[3:1] != K_XQ) te <= 1'b1;   // non-h beat inside a window
        end
    assign wopen = wn != '0; assign wtag = w_t; assign terr = te;
`ifdef OT_S81SL_LEP_MUT_WRONGCOPY
    assign wab = 1'b0;                                 // MUTANT: copy select ignored
`else
    assign wab = w_ab;
`endif
    end else begin : g_nmtx
    assign wopen = 1'b0; assign wab = 1'b0; assign wtag = 33'd0; assign terr = 1'b0;
    end endgenerate
    wire stamp = rov && wopen;
    wire bsel = stamp && wab;                          // this frame goes to pair B
    reg [2*H-1:0] fr;
    always @(*) begin
        fr = {2*H{1'b0}};
        if (rov) begin
            fr = roq;
`ifndef OT_S81SL_LEP_MUT_TAGDROP
            if (stamp) fr[TG +: 33] = wtag;
`endif
        end
        else if (hp_go) begin fr[3:1] = 3'd3; fr[4 +: 77] = ph_d; end
        else if (kp_go) begin fr[3:1] = 3'd4; fr[4 +: 54] = pk_d; end
    end
    wire [1:0] pp = {push && bsel, push && !bsel};     // push per pair
    reg [1:0] sq;                                      // frame-sequence parity (TX), per pair
    always @(posedge clk or negedge rn) if (!rn) sq <= 2'b00; else sq <= sq ^ pp;
`ifdef OT_S81SL_LEP_MUT_SWAP
    wire [H-1:0] hf0 = fr[2*H-1:H], hf1 = fr[H-1:0];
`else
    wire [H-1:0] hf0 = fr[H-1:0], hf1 = fr[2*H-1:H];
`endif

    // ---------------------------------------------------------------- TX landing FIFOs (one per lane)
    // Storage: ot_s81ph_mem1r1w SRAM = 1 (5 x ot_sram_1r1w_512x128_m4_r2c2 a lane, registered write port WREG = 1,
    // registered read), DT entries.  Credit sender: lo_r (a credit pulse per freed lane landing slot) lands in the pin flop
    // cr_q; a read is issued only with a credit in hand (the credit is spent at issue), its word leaves on lo_v / lo_d
    // from flops two edges later.  lo_d loads the SRAM read word every cycle (the lane samples it only with lo_v).
    // Lanes 2 / 3 (AB_EN 1) = pair B, same structure, fed by pp[1] (reset regions: lane 2 with lane 0, lane 3 with 1).
    wire [NL-1:0] ovf;
    wire [3:0] lo_v; wire [3:0] lo_r = {lo3_r, lo2_r, lo1_r, lo0_r};
    wire [4*(H+1)-1:0] lo_d;
    localparam integer CW = $clog2(CRED + 1);
    genvar t;
    generate for (t = 0; t < NL; t = t + 1) begin : g_tx
        wire rt = rr[t % 2];
        reg [AT-1:0] wp, rp; reg [AT:0] n; reg [CW-1:0] cnt;
        reg inf, of, ov; reg [H:0] od;
        wire inq; wire [H:0] qd;                      // read word / valid one stage before the lo pin flops
        (* keep = "true" *) reg cr_q;                  // lo_r pin flop
        wire [H:0] q;
        wire iss = n != 0 && cnt != 0;
        wire psh = pp[t / 2];
        wire wr = psh && (n != DT || iss);
        ot_s81ph_mem1r1w #(.W(H + 1), .DEPTH(DT), .SRAM(SRAM), .WREG(1)) u_m (.clk(clk), .rst_n(rt), .we(wr), .wa(wp),
            .wd({sq[t / 2], (t % 2 == 0) ? hf0 : hf1}), .re(iss), .ra(rp), .q(q));
        always @(posedge clk or negedge rt)
            if (!rt) begin wp <= 0; rp <= 0; n <= 0; inf <= 1'b0; of <= 1'b0; cr_q <= 1'b0; cnt <= CW'(CRED); ov <= 1'b0; end
            else begin
                cr_q <= lo_r[t];
                cnt <= cnt + CW'(cr_q) - CW'(iss);
                if (wr) wp <= (wp == DT - 1) ? 0 : wp + 1'b1;
                if (iss) rp <= (rp == DT - 1) ? 0 : rp + 1'b1;
                n <= n + (wr ? 1'b1 : 1'b0) - (iss ? 1'b1 : 1'b0);
                inf <= iss;
                ov <= inq;
`ifndef OT_S81SL_LEP_MUT_NOOVF
                if (psh && n == DT && !iss) of <= 1'b1;
`endif
            end
        if (TXRP != 0) begin : g_rp                   // read pipeline register beside the SRAM column
            reg inr; reg [H:0] odr;
            always @(posedge clk or negedge rt) if (!rt) inr <= 1'b0; else inr <= inf;
            always @(posedge clk) odr <= q;
`ifdef OT_S81SL_LEP_MUT_TXRPV
            assign inq = inf;                         // MUTANT: lo_v skips the read pipeline stage (valid 1 edge early)
`else
            assign inq = inr;
`endif
            assign qd = odr;
        end else begin : g_nrp
            assign inq = inf; assign qd = q;
        end
        always @(posedge clk) od <= qd;
        assign lo_v[t] = ov; assign lo_d[t * (H + 1) +: H + 1] = od; assign ovf[t] = of;
    end
    if (NL == 2) begin : g_txnb                         // AB_EN 0: no pair-B lanes (lo2 / lo3 unread outputs = 0)
        assign lo_v[3:2] = 2'b00; assign lo_d[4*(H+1)-1:2*(H+1)] = '0;
    end endgenerate
    assign lo0_v = lo_v[0]; assign lo0_d = lo_d[H:0];
    assign lo1_v = lo_v[1]; assign lo1_d = lo_d[2*H+1:H+1];
    assign lo2_v = lo_v[2]; assign lo2_d = lo_d[3*H+2:2*H+2];
    assign lo3_v = lo_v[3]; assign lo3_d = lo_d[4*H+3:3*H+3];

    // ---------------------------------------------------------------- RX pair re-assembly
    // Credit receiver per lane (ot_link_credit_rx WFREE 2 form): li_v / li_d land in pin flops (vq / dq); the landing
    // register is written every non-full cycle into mem[wp] through REGISTERED one-hot slot enables (credits guarantee a
    // free slot), the non-empty flag is registered, li_r is a registered credit pulse per pop, a beat landing on a full
    // FIFO is a sticky fault.  The read pointer is replicated RREP times (each copy selects <= 35 data columns).
    localparam integer RREP = 16, SW = (H + 1 + RREP - 1) / RREP;
    wire [3:0] li_v = {li3_v, li2_v, li1_v, li0_v}; wire [4*(H+1)-1:0] li_d = {li3_d, li2_d, li1_d, li0_d};
    wire [NL-1:0] rne, rxf; wire [NL*(H+1)-1:0] rhd; wire [NL-1:0] lir;
    wire [NL-1:0] rhk;                                 // MU_EN 1: pre-decoded land bit of each lane's head row
    // RXSA (MU_EN 0, 2 lanes): grouped show-ahead RX + registered one-hot selects
    localparam integer RXS = (RXSA != 0 && MU_EN == 0 && NL == 2) ? 1 : 0;
    localparam integer RXG = 18, RSW = (H + 1 + RXG - 1) / RXG;      // 18 column groups of <= 31 bits
    wire [NL-1:0] rnz_nx;                              // next-cycle non-empty flag per lane (= nz after this edge)
    wire [2:0] rk_nx;                                  // next-cycle lane-0 head kind {ks, host, ring}
`ifdef OT_S81SL_LEP_MUT_NOPAIR
    wire rel_nx = rnz_nx[0];
`else
    wire rel_nx = rnz_nx[0] && rnz_nx[1];
`endif
    wire [1:0] relp;                                   // pair releases (pair B only at AB_EN 1)
`ifdef OT_S81SL_LEP_MUT_NOPAIR
    assign relp[0] = rne[0];
`else
    assign relp[0] = rne[0] && rne[1];
`endif
    generate if (NL == 4) begin : g_relb
        assign relp[1] = rne[2] && rne[3];
    end else begin : g_nrelb
        assign relp[1] = 1'b0;
    end endgenerate
    wire rel = relp[0] || relp[1];
    wire rpb = relp[1] && !relp[0];                    // the released pair is B
    genvar c;
    generate for (t = 0; t < NL; t = t + 1) begin : g_rx
        reg [H:0] mem [0:DR-1];
        reg [AR-1:0] wp, rp; reg [AR:0] n; reg vq, nz, cr, f; reg [DR-1:0] we; reg [H:0] dq;
        wire pop = relp[t / 2] && nz;
        wire full = n == (AR+1)'(DR);
        wire wr = vq && !full;
        wire [AR-1:0] wp_nx = wr ? ((wp == AR'(DR - 1)) ? '0 : wp + 1'b1) : wp;
        wire [AR-1:0] rp_nx = pop ? ((rp == AR'(DR - 1)) ? '0 : rp + 1'b1) : rp;
        wire [AR:0] n_nx = n + (AR+1)'(wr) - (AR+1)'(pop);
        integer k;
        always @(posedge clk or negedge rnx)
            if (!rnx) begin wp <= 0; rp <= 0; n <= 0; vq <= 1'b0; nz <= 1'b0; cr <= 1'b0; f <= 1'b0; we <= DR'(1); end
            else begin
                vq <= li_v[t];
                cr <= pop;
                if (vq && full && !pop) f <= 1'b1;
                wp <= wp_nx; rp <= rp_nx; n <= n_nx; nz <= n_nx != 0;
                for (k = 0; k < DR; k = k + 1) we[k] <= (wp_nx == AR'(k)) && (n_nx != (AR+1)'(DR));
            end
        integer j;
        always @(posedge clk) begin
            dq <= li_d[t * (H + 1) +: H + 1];
            if (RXS == 0) for (j = 0; j < DR; j = j + 1) if (we[j]) mem[j] <= dq;
        end
        // MU_EN 0: the head is read combinationally from mem[rpc] (pre-MU structure, unchanged; loop empty at MU_EN 1)
        assign rnz_nx[t] = n_nx != 0;
        if (RXS != 0) begin : g_s
            // lane-0 frame kind pre-decoded per row at write: {ks, host, ring}; next head kind like the g_sa land bit
            if (t == 0) begin : g_k
                wire [2:0] kd = {!dq[0] && dq[3:1] == 3'd2, !dq[0] && dq[3:1] == 3'd1, dq[0]};
                reg [2:0] mk [0:DR-1];
                integer jk;
                always @(posedge clk) for (jk = 0; jk < DR; jk = jk + 1) if (we[jk]) mk[jk] <= kd;
                assign rk_nx = we[rp_nx] ? kd : mk[rp_nx];
            end
            for (c = 0; c < RXG; c = c + 1) begin : g_g
                localparam integer LO = c * RSW, HI = ((c + 1) * RSW > H + 1) ? H + 1 : (c + 1) * RSW;
                if (LO < H + 1) begin : g_on
                    // kept per-group copies: slot enables, one-hot head pointer, pop
                    (* keep = "true" *) reg [DR-1:0] wg;
                    (* keep = "true" *) reg [DR-1:0] oh;
                    (* keep = "true" *) reg pc;
                    reg [HI-LO-1:0] mg [0:DR-1];
                    reg [HI-LO-1:0] hd;
                    wire [DR-1:0] ohn = pc ? {oh[DR-2:0], oh[DR-1]} : oh;      // one-hot of rp_nx
                    integer kk, jg;
                    reg [HI-LO-1:0] row;
                    always @(*) begin
                        row = '0;
                        for (kk = 0; kk < DR; kk = kk + 1) row = row | ({(HI - LO){ohn[kk]}} & mg[kk]);
                    end
                    always @(posedge clk or negedge rnx)
                        if (!rnx) begin wg <= DR'(1); oh <= DR'(1); pc <= 1'b0; end
                        else begin
                            for (kk = 0; kk < DR; kk = kk + 1) wg[kk] <= (wp_nx == AR'(kk)) && (n_nx != (AR+1)'(DR));
                            oh <= ohn;
                            pc <= rel_nx && (n_nx != 0);           // = next cycle's pop of this lane
                        end
                    always @(posedge clk) begin
                        for (jg = 0; jg < DR; jg = jg + 1) if (wg[jg]) mg[jg] <= dq[HI-1:LO];
`ifdef OT_S81SL_LEP_MUT_RXBYP
                        hd <= row;                                 // MUTANT: same-edge landing word not bypassed
`else
                        hd <= (|(wg & ohn)) ? dq[HI-1:LO] : row;
`endif
                    end
                    assign rhd[t * (H + 1) + LO +: HI - LO] = hd;
                end
            end
        end
        for (c = 0; c < ((MU_EN != 0 || RXS != 0) ? 0 : RREP); c = c + 1) begin : g_c
            localparam integer LO = c * SW, HI = ((c + 1) * SW > H + 1) ? H + 1 : (c + 1) * SW;
            if (LO < H + 1) begin : g_on
                (* keep = "true" *) reg [AR-1:0] rpc;
                always @(posedge clk or negedge rnx) if (!rnx) rpc <= 0; else rpc <= rp_nx;
                wire [H:0] row = mem[rpc];
                assign rhd[t * (H + 1) + LO +: HI - LO] = row[HI-1:LO];
            end
        end
        // MU-S81-2/RX (10-19): SHOW-AHEAD head register (MU_EN 1).  hd = mem[rp] at every cycle, from flops: on each edge
        // it loads the row the pointer will hold (rp_nx), or the landing word dq when that row is written on the same
        // edge (registered one-hot enables we).  Same FIFO order, nz timing and full / empty faults; 0 added cycles.
        // The pointer copy + increment is replicated per column group (as RREP above); pop = this pair's release (nz
        // flops of the pair only), so rp_nx -> 8:1 row mux -> hd stays inside the lane.  hk = a PRE-DECODED land bit of
        // the head row (stored per row at write): lane 0 of a pair = XB / XQ ring beat, lane 1 = tag && land bits.
        if (MU_EN != 0) begin : g_sa
            wire kd = (t % 2 == 0) ? (dq[0] && (dq[3:1] == K_XB || dq[3:1] == K_XQ)) : (dq[TG - H] && dq[TG + 1 - H]);
            reg [DR-1:0] mk; reg hk;
            integer jk;
            always @(posedge clk) begin
                for (jk = 0; jk < DR; jk = jk + 1) if (we[jk]) mk[jk] <= kd;
`ifdef OT_S81SL_LEP_MUT_STALEHD
                hk <= mk[rp];
`else
                hk <= we[rp_nx] ? kd : mk[rp_nx];
`endif
            end
            assign rhk[t] = hk;
            for (c = 0; c < RREP; c = c + 1) begin : g_h
                localparam integer LO = c * SW, HI = ((c + 1) * SW > H + 1) ? H + 1 : (c + 1) * SW;
                if (LO < H + 1) begin : g_on
                    (* keep = "true" *) reg [AR-1:0] rpc;
                    wire [AR-1:0] rpn = pop ? ((rpc == AR'(DR - 1)) ? '0 : rpc + 1'b1) : rpc;
                    reg [HI-LO-1:0] hd;
                    always @(posedge clk or negedge rnx) if (!rnx) rpc <= 0; else rpc <= rpn;
                    wire [H:0] row = mem[rpn];
                    always @(posedge clk)
`ifdef OT_S81SL_LEP_MUT_STALEHD
                        hd <= mem[rpc][HI-1:LO];               // MUTANT: no show-ahead (head of the OLD pointer / old row)
`else
                        hd <= we[rpn] ? dq[HI-1:LO] : row[HI-1:LO];
`endif
                    assign rhd[t * (H + 1) + LO +: HI - LO] = hd;
                end
            end
        end
        assign rne[t] = nz; assign lir[t] = cr; assign rxf[t] = f;
    end endgenerate
    assign li0_r = lir[0]; assign li1_r = lir[1];
    generate if (NL == 4) begin : g_rxb
        assign li2_r = lir[2]; assign li3_r = lir[3]; assign rxvb = rxv_r[3:2];
    end else begin : g_nrxb
        assign li2_r = 1'b0; assign li3_r = 1'b0; assign rxvb = 2'b00;
    end endgenerate
    wire [H:0] h0, h1;
    generate if (NL == 4) begin : g_hsel
        assign h0 = rpb ? rhd[3*H+2:2*H+2] : rhd[H:0];
        assign h1 = rpb ? rhd[4*H+3:3*H+3] : rhd[2*H+1:H+1];
    end else begin : g_hsel0
        assign h0 = rhd[H:0]; assign h1 = rhd[2*H+1:H+1];
    end endgenerate
    reg perr;
    // host-plane frame types this endpoint accepts (HOST 1, KS 2) -- none at HOST_EN 0, never on pair B
`ifdef OT_S81SL_LEP_MUT_NHACC
    wire hacc = !h0[0] && (h0[3:1] == 3'd1 || h0[3:1] == 3'd2);        // MUTANT: accepted even at HOST_EN 0
`else
    wire hacc = (HOST_EN != 0) && !rpb && !h0[0] && (h0[3:1] == 3'd1 || h0[3:1] == 3'd2);
`endif
    reg [1103:1] rid; reg riv;
    assign ri = {rid, riv};
    wire mcol_w;                                       // MU: replay collided with a cut-through beat
    wire [1103:0] rb = {h1[H-1:0], h0[H-1:0]};          // the released frame (ring beat when bit 0)
    generate if (MU_EN == 0) begin : g_rxr
    if (RXS == 0) begin : g_rid0
    always @(posedge clk) rid <= (rel && h0[0]) ? {h1[H-1:0], h0[H-1:1]} : 1103'd0;   // data: no reset
    end else begin : g_rid1                            // RXSA: 35 registered select copies (<= 32 rid bits each)
    localparam integer SG = 35, SGW = (1103 + SG - 1) / SG;
    wire [1103:1] rfr = {h1[H-1:0], h0[H-1:1]};
    for (c = 0; c < SG; c = c + 1) begin : g_sr
        localparam integer LO = 1 + c * SGW, HI = (1 + (c + 1) * SGW > 1104) ? 1104 : 1 + (c + 1) * SGW;
        if (LO < 1104) begin : g_on
            (* keep = "true" *) reg sr;
`ifdef OT_S81SL_LEP_MUT_RXSEL
            if (c == 0) begin : g_m
                always @(posedge clk or negedge rnx) if (!rnx) sr <= 1'b0; else sr <= rel && h0[0];   // MUTANT: late
            end else begin : g_n
                always @(posedge clk or negedge rnx) if (!rnx) sr <= 1'b0; else sr <= rel_nx && rk_nx[0];
            end
`else
            always @(posedge clk or negedge rnx) if (!rnx) sr <= 1'b0; else sr <= rel_nx && rk_nx[0];
`endif
            always @(posedge clk) rid[HI-1:LO] <= sr ? rfr[HI-1:LO] : '0;
        end
    end
    end
    always @(posedge clk or negedge rnx)
        if (!rnx) riv <= 1'b0;
        else riv <= rel && h0[0];
    assign mu_rt = 32'd0; assign ml_wv = 1'b0; assign ml_wd = 1104'd0; assign mcol_w = 1'b0; assign rhk = '0;
    end else begin : g_rxm
    // tagged = an XB / XQ ring beat with the tag bit; land = 1 -> landing leaf, else ri (tag stripped, tag on mu_rt)
    function automatic [1103:0] strip(input [1103:0] b);
        begin strip = b; strip[TG +: 33] = 33'd0; end
    endfunction
    function automatic tagd(input [1103:0] b);
        begin tagd = b[0] && (b[3:1] == K_XB || b[3:1] == K_XQ) && b[TG]; end
    endfunction
    reg mrv, mcol, mwv; reg [1103:0] mrd, mwd; reg [31:0] rtq;
    always @(posedge clk) mrd <= ml_rd;
    // MU-S81-2/RX: selects straight from the show-ahead flops.  Per pair X: gX = X releases a ring beat (pair A wins a
    // collision, as rpb), lX = its pre-decoded land bit (lane 0 XB / XQ ring beat && lane 1 tag && land); sX = deliver
    // X's beat on ri, sM = deliver the replayed beat (cut-through wins a collision, mcol fault as before).
    wire [1103:0] bA = {rhd[2*H:H+1], rhd[H-1:0]};     // pair A frame (lane 1 high half, lane 0 low half)
    wire lA = rhk[0] && rhk[1];
    wire gA = relp[0] && rhd[0];
    wire [1103:0] bB; wire lB, gB;
    if (NL == 4) begin : g_mb
        assign bB = {rhd[4*H+2:3*H+3], rhd[3*H+1:2*H+2]};
        assign lB = rhk[2] && rhk[3];
        assign gB = rpb && rhd[2*(H+1)];               // rpb: nz flops only
    end else begin : g_nmb
        assign bB = 1104'd0; assign lB = 1'b0; assign gB = 1'b0;
    end
`ifdef OT_S81SL_LEP_MUT_LANDCUT
    wire ldA = 1'b0, ldB = 1'b0;                       // MUTANT: land bit ignored (landed beats cut through to ri)
`else
    wire ldA = lA, ldB = lB;
`endif
    wire rr_land = (gA && ldA) || (gB && ldB);
    wire rr_dlv = (gA && !ldA) || (gB && !ldB);
    wire [1103:0] db = rr_dlv ? rb : mrd;               // delivered beat (tag fields only: rtq)
    // rid: one AO222 per bit, {sA, sB, sM} duplicated per column group (keep) so each select net drives ~70 bits
    localparam integer OREP = 16, OW = (1103 + OREP - 1) / OREP;
    wire [1103:1] nrid;
    wire [1103:0] sbA = strip(bA), sbB = strip(bB), sbM = strip(mrd);
    for (c = 0; c < OREP; c = c + 1) begin : g_o
        localparam integer LO = 1 + c * OW, HI = (1 + (c + 1) * OW > 1104) ? 1104 : 1 + (c + 1) * OW;
        if (LO < 1104) begin : g_on
            (* keep = "true" *) wire sA = gA && !ldA;
            (* keep = "true" *) wire sB = gB && !ldB;
            (* keep = "true" *) wire sM = mrv && !(gA && !ldA) && !(gB && !ldB);
            assign nrid[HI-1:LO] = ({(HI - LO){sA}} & sbA[HI-1:LO]) | ({(HI - LO){sB}} & sbB[HI-1:LO])
                                 | ({(HI - LO){sM}} & sbM[HI-1:LO]);
        end
    end
    always @(posedge clk) begin
        rid <= nrid;
        mwd <= rb;
        rtq <= tagd(db) ? {1'b1, db[TG + 2 +: 10], db[TG + 12 +: 21]} : 32'd0;
    end
    always @(posedge clk or negedge rnx)
        if (!rnx) begin riv <= 1'b0; mrv <= 1'b0; mcol <= 1'b0; mwv <= 1'b0; end
        else begin
            mrv <= ml_rv;
            riv <= rr_dlv || mrv;
            mwv <= rr_land;
            if (rr_dlv && mrv) mcol <= 1'b1;            // replay against a cut-through beat
        end
    assign mu_rt = riv ? rtq : 32'd0; assign ml_wv = mwv; assign ml_wd = mwd; assign mcol_w = mcol;
    end endgenerate
    always @(posedge clk or negedge rnx)
        if (!rnx) perr <= 1'b0;
        else begin
            if (|rxf) perr <= 1'b1;                    // a beat landed on a full RX FIFO (credit protocol broken)
            // a released pair must be one frame (equal sequence parity); a die endpoint accepts ring / HOST / KS only
            // (ring only at HOST_EN 0 and on pair B); both pairs releasing in one cycle is a collision
            if (rel && (h0[H] != h1[H] || (!h0[0] && !hacc))) perr <= 1'b1;
            if (relp[0] && relp[1]) perr <= 1'b1;
        end
    generate if (HOST_EN != 0) begin : g_hrx
`ifdef OT_S81SL_LEP_MUT_KSOFF
    wire [52:0] ksp = h0[5 +: 53];                     // MUTANT: key-store payload read one bit off
`else
    wire [52:0] ksp = h0[4 +: 53];
`endif
    reg fh_v, fk_s; reg [513:0] fh_d; reg [51:0] fk_d; reg [3:0] lf;
    always @(posedge clk or negedge rnx)
        if (!rnx) begin fh_v <= 1'b0; fk_s <= 1'b0; end
        else begin
            fh_v <= rel && hacc && h0[3:1] == 3'd1;
            fk_s <= rel && hacc && h0[3:1] == 3'd2 && ksp[52];
        end
    always @(posedge clk) lf <= {l1_st[0] | (|l1_f), l1_st[1], l0_st[0] | (|l0_f), l0_st[1]};
    if (RXS == 0) begin : g_hs0
        always @(posedge clk) begin
            if (rel && hacc && h0[3:1] == 3'd1) fh_d <= h0[4 +: 514];
            if (rel && hacc && h0[3:1] == 3'd2) fk_d <= ksp[51:0];
        end
    end
    if (RXS != 0) begin : g_hs                         // RXSA: registered one-hot select copies (<= 32 bits each)
        for (c = 0; c < 17; c = c + 1) begin : g_h       // fh_d 514 = 16 x 31 + 18
            localparam integer LO = c * 31, HI = (c == 16) ? 514 : (c + 1) * 31;
            (* keep = "true" *) reg sh;
            always @(posedge clk or negedge rnx) if (!rnx) sh <= 1'b0; else sh <= rel_nx && rk_nx[1];
            always @(posedge clk) if (sh) fh_d[HI-1:LO] <= h0[4 + LO +: HI - LO];
        end
        for (c = 0; c < 2; c = c + 1) begin : g_k        // fk_d 52 = 2 x 26
            (* keep = "true" *) reg sk;
            always @(posedge clk or negedge rnx) if (!rnx) sk <= 1'b0; else sk <= rel_nx && rk_nx[2];
            always @(posedge clk) if (sk) fk_d[c * 26 +: 26] <= ksp[c * 26 +: 26];
        end
    end
    assign f_host = {fh_d, fh_v};
    assign f_ks = {fk_s, fk_d};
    assign f_lf = lf;
    end else begin : g_nhrx                            // HOST_EN 0: no host outputs (the _nh tops have no such ports)
    assign f_host = 515'd0; assign f_ks = 53'd0; assign f_lf = 4'd0;
    end endgenerate

    // ---------------------------------------------------------------- fault collector (sticky)
    wire mferr;
    generate if (MU_EN != 0) begin : g_mf
        reg mlfq;
        always @(posedge clk or negedge rn) if (!rn) mlfq <= 1'b0; else mlfq <= ml_f;
        assign mferr = terr || mcol_w || mlfq;
    end else begin : g_nmf
        assign mferr = 1'b0;
    end endgenerate
    wire [5:0] lfb_in;
    generate if (NL == 4) begin : g_lfb
        assign lfb_in = {l3_f, l2_f};
    end else begin : g_nlfb
        assign lfb_in = 6'd0;
    end endgenerate
    reg slq; reg [5:0] lfq, lfbq;
    always @(posedge clk or negedge rn)
        if (!rn) begin slq <= 1'b0; lfq <= 6'd0; lfbq <= 6'd0; fault <= 1'b0; end
        else begin
            slq <= sl_f; lfq <= {l1_f, l0_f}; lfbq <= lfb_in;
            if ((|ovf) || perr || herr || slq || (|lfq) || (|lfbq) || mferr) fault <= 1'b1;
        end
endmodule
