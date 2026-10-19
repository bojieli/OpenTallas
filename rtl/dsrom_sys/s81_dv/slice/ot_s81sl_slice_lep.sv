`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-S81 (owner 0dv 2026-10-18): the END-SLICE link endpoint master (p4j end_slice_lep: s_0S / s_0N = W end,
// s_7S / s_7N = E end; residual row 1: lt_lk_{WS,WN,ES,EN}{0,1} 8 x 512 b had no producer).
//
// Function (SPEC 0b-p4i "end-slice link endpoints"; SPEC l.217 "the end slices' outward E/W ring port carries the PHY
// link lanes along the street"): the tier LINE simply continues across the die edge.  A line beat that reaches an end
// slice with hops > 1 is forwarded by the unchanged ring stop (ot_s81sl_rstop) out of the slice's OUTWARD port
// (W end: ro_w, E end: ro_e); here that port feeds two reliable UCIe link lanes instead of a neighbour.  The peer die's
// end slice presents the beat on its outward input (ri_w / ri_e), where its ring stop delivers it (hops 1) or forwards
// it inward (hops - 1) exactly like a neighbour's beat: cross-die all-gather rows (XQ / XB) join the mesh stream at the
// end slice, all-reduce partials ride to the owning slice, which keeps the fixed fold order ((p0+p1)+(p2+p3)).
// The compiler addresses an off-die destination by hop count (col + 1 + remote hops for a W-bound beat).
//
// Structure (cluster, wires only; every function in a hardened child with its own clock root):
//   ot_s81sl_slice            the vector slice cluster, UNCHANGED (HB = 0, C1)
//   ot_s81sl_lep              link-port leaf (this file): outward-port pin flops, per-lane TX landing FIFOs, RX pair
//                             re-assembly, lane-receive enables, the fault collector
//   dsfd_coll_lane_w / _e x2  the hardened collective link lane tile (ot_s81ph_link_ep reliable link layer: seq, CRC-32,
//                             go-back-N replay, credits + ot_s81ph_link_gbx 512-b beat format), unchanged
//   A 1,104-b ring beat = 2 link flits of 552 b (FLIT_BYTES 69): low half [551:0] on lane 0, high half [1103:552] on
//   lane 1; the flit's `last` bit carries the beat-sequence parity (checked at re-assembly).
// Flow control exists ONLY at this off-die boundary (owner 10-14: flow control kept at SerDes / d2d incl. cross-die
// collectives): the ring side is static (a valid beat on ro is pushed the same cycle; a full landing FIFO is a sticky
// fault: the compiler keeps the off-die rate <= the lane rate 456/596 * 1023/1024 = 0.764 beats/cycle with bursts
// <= DT / (1 - 0.764) = ~2,170 back-to-back beats at DT = 512), the lane side is the link layer's valid/ready + credits.
//
// Ports (lepw = W end; lepe = E end mirrors ri_e/ro_e <-> ri_w/ro_w):
//   tx0 / tx1 [511:0]   -> ot_pdie_ucie tx (lt_lk_<side><tier>{0,1})
//   rx0 / rx1 [513:0]   <- {ot_pdie_ucie st[1:0] = {live, fault}, rx[511:0]} (lr_lk_*; the plan lane is 512 b: + 2 st)
//   tf [1:0]            forwarded lane clocks (to the PHY macro side)
//   ch_b                static strap: 0 = UCIe lane timeout basis, 1 = board lane
//   t_host 77 / t_kd 54 <- dsdv_seq_host (host status / completion, key-store done): sent as THOST / TKD link frames
//   f_host 515 / f_lf 4 / f_ks 53 -> dsdv_seq_host: HOST / KS link frames from the peer (the host-side endpoint) and
//                       the lane block status {fault, live} x 2 (lane 1, lane 0) -- the HOST PLANE of the cross-die link
//                       (coordinator 10-18: seq_host's host lane is the end-slice link, not a separate PHY)
//   all other ports     = ot_s81sl_slice (inward line port, V rung, band port (mode-unused at HB 0), x chains, return
//                         lanes, forwarded clocks)
// The lane rx word {fault, live, beat, valid} of dsfd_coll_lane_*: valid = the lep's registered lane-receive enable
// (1 from the cycle after reset release): ot_pdie_ucie's rate matcher presents a beat EVERY cycle (an IDLE beat 512'b10
// when its FIFO is empty, skipped by the gearbox), and the gearbox qualifies beats with `live` itself.
// Pin rules (S81-RTLB3 2026-10-18; gate b6bf54dea WARNs: lo0_r / lo1_r drove 556 / 558 loads, 6 levels to wp; one
// reset flop drove 1,232 loads): the core-side lane faces are CREDIT links (rtl/common/ot_link_credit.sv protocol, the
// lane tile in LCR = 1 mode, as the S81 collective die lanes: run_die_layer.sh +define+OT_S81PH_LANE_CR).  lo_r is a
// credit pulse that lands in ONE pin flop (cr_q); a TX read is issued only with a credit in hand (CRED 8 = the lane's
// landing depth), lo_v / lo_d leave from flops.  li_v / li_d land in pin flops, li_r is a registered credit pulse per pop
// (RX landing DR 8 = the lane sender's CRED 8).  The rst_n port drives only an ot_rst_relay (4 regions: TX lane 0, TX
// lane 1, RX, host plane / faults); the 1,103 ri data bits carry no reset (ri[0] is the beat valid).
// Added edges vs the valid/ready skid face (compiler + die): ro -> lane endpoint +2 cycles (lane credit landing pin flop
// + FIFO), lane -> ri +1 cycle (lane credit sender flop); reset release +1 cycle (relay stage: 3 edges from rst_n).
// The credit round trips (TX ~7, RX ~6 cycles) stay inside 8 credits: full beat rate; the off-die rate cap (0.764) and
// the TX landing burst bound are unchanged.
// Mutants (bench only): OT_S81SL_LEP_MUT_SWAP (halves swapped onto the lanes), OT_S81SL_LEP_MUT_NOPAIR (re-assembly
// releases on lane 0 alone), OT_S81SL_LEP_MUT_NOOVF (landing-FIFO overflow not flagged), OT_S81SL_LEP_MUT_KSOFF
// (key-store payload decoded one bit off), OT_S81SL_LEP_MUT_HDROP (a pending t_v host word overwritten),
// OT_S81SL_LEP_MUT_NHACC (a HOST_EN = 0 endpoint accepts HOST / KS frames silently).
// HOST_EN (S81-LEPV 2026-10-18, owner "remove ties where cheap"): only s_7N carries the host plane.  HOST_EN = 0 removes
// the host plane from the leaf (no t_host / t_kd pin flops, no THOST / TKD pending registers, no f_host / f_ks / f_lf
// registers; a HOST / KS frame arriving there is a protocol fault like any unknown frame type).  The PORTS go with it in
// the parameter-free tops ot_s81sl_lep_nh (leaf) and ot_s81sl_slice_lepw / ot_s81sl_slice_lepe_nh (die masters), so the
// three host-less endpoints carry no tied die pads.  The core's host ports are unread at HOST_EN = 0 (generate), so
// synthesis of a _nh top keeps no host pin and no host logic.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_lep #(
    parameter integer DT = 512,        // TX landing FIFO depth per lane (flits; SRAM macro depth)
    parameter integer DR = 8,          // RX landing FIFO depth per lane (flits, flops) = the lane sender's CRED 8
    parameter integer CRED = 8,        // TX credits = the lane's core-face landing depth (ot_link_credit_rx DEPTH 8)
    parameter integer SRAM = 1,        // 1: TX storage in SRAM macros (0: flops, same cycle behaviour)
    parameter integer HOST_EN = 1      // 1: host plane (THOST / TKD out, HOST / KS in, f_lf); 0: ring beats only
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
    output reg  [1:0]      rxv,        // lane receive enables (the lane rx word's valid bit)
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
    output reg             fault
);
    localparam integer H = 552;
    localparam integer AT = $clog2(DT), AR = $clog2(DR);
    // regional reset: the port drives only this relay (own synchroniser on this leaf's clock root); one copy per region
    wire [3:0] rr;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rstr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[3];                                   // host plane, outward-port valid, fault collector
    wire rnx = rr[2];                                  // RX landing + re-assembly
    always @(posedge clk or negedge rnx) if (!rnx) rxv <= 2'b00; else rxv <= 2'b11;

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
    reg [2*H-1:0] fr;
    always @(*) begin
        fr = {2*H{1'b0}};
        if (rov) fr = roq;
        else if (hp_go) begin fr[3:1] = 3'd3; fr[4 +: 77] = ph_d; end
        else if (kp_go) begin fr[3:1] = 3'd4; fr[4 +: 54] = pk_d; end
    end
    reg sq;                                            // frame-sequence parity (TX)
    always @(posedge clk or negedge rn) if (!rn) sq <= 1'b0; else if (push) sq <= ~sq;
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
    wire [1:0] ovf;
    wire [1:0] lo_v, lo_r = {lo1_r, lo0_r};
    wire [2*(H+1)-1:0] lo_d;
    localparam integer CW = $clog2(CRED + 1);
    genvar t;
    generate for (t = 0; t < 2; t = t + 1) begin : g_tx
        wire rt = rr[t];
        reg [AT-1:0] wp, rp; reg [AT:0] n; reg [CW-1:0] cnt;
        reg inf, of, ov; reg [H:0] od;
        (* keep = "true" *) reg cr_q;                  // lo_r pin flop
        wire [H:0] q;
        wire iss = n != 0 && cnt != 0;
        wire wr = push && (n != DT || iss);
        ot_s81ph_mem1r1w #(.W(H + 1), .DEPTH(DT), .SRAM(SRAM), .WREG(1)) u_m (.clk(clk), .rst_n(rt), .we(wr), .wa(wp),
            .wd({sq, (t == 0) ? hf0 : hf1}), .re(iss), .ra(rp), .q(q));
        always @(posedge clk or negedge rt)
            if (!rt) begin wp <= 0; rp <= 0; n <= 0; inf <= 1'b0; of <= 1'b0; cr_q <= 1'b0; cnt <= CW'(CRED); ov <= 1'b0; end
            else begin
                cr_q <= lo_r[t];
                cnt <= cnt + CW'(cr_q) - CW'(iss);
                if (wr) wp <= (wp == DT - 1) ? 0 : wp + 1'b1;
                if (iss) rp <= (rp == DT - 1) ? 0 : rp + 1'b1;
                n <= n + (wr ? 1'b1 : 1'b0) - (iss ? 1'b1 : 1'b0);
                inf <= iss;
                ov <= inf;
`ifndef OT_S81SL_LEP_MUT_NOOVF
                if (push && n == DT && !iss) of <= 1'b1;
`endif
            end
        always @(posedge clk) od <= q;
        assign lo_v[t] = ov; assign lo_d[t * (H + 1) +: H + 1] = od; assign ovf[t] = of;
    end endgenerate
    assign lo0_v = lo_v[0]; assign lo0_d = lo_d[H:0];
    assign lo1_v = lo_v[1]; assign lo1_d = lo_d[2*H+1:H+1];

    // ---------------------------------------------------------------- RX pair re-assembly
    // Credit receiver per lane (ot_link_credit_rx WFREE 2 form): li_v / li_d land in pin flops (vq / dq); the landing
    // register is written every non-full cycle into mem[wp] through REGISTERED one-hot slot enables (credits guarantee a
    // free slot), the non-empty flag is registered, li_r is a registered credit pulse per pop, a beat landing on a full
    // FIFO is a sticky fault.  The read pointer is replicated RREP times (each copy selects <= 35 data columns).
    localparam integer RREP = 16, SW = (H + 1 + RREP - 1) / RREP;
    wire [1:0] li_v = {li1_v, li0_v}; wire [2*(H+1)-1:0] li_d = {li1_d, li0_d};
    wire [1:0] rne, rxf; wire [2*(H+1)-1:0] rhd; wire [1:0] lir;
`ifdef OT_S81SL_LEP_MUT_NOPAIR
    wire rel = rne[0];
`else
    wire rel = rne[0] && rne[1];
`endif
    genvar c;
    generate for (t = 0; t < 2; t = t + 1) begin : g_rx
        reg [H:0] mem [0:DR-1];
        reg [AR-1:0] wp, rp; reg [AR:0] n; reg vq, nz, cr, f; reg [DR-1:0] we; reg [H:0] dq;
        wire pop = rel && nz;
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
            for (j = 0; j < DR; j = j + 1) if (we[j]) mem[j] <= dq;
        end
        for (c = 0; c < RREP; c = c + 1) begin : g_c
            localparam integer LO = c * SW, HI = ((c + 1) * SW > H + 1) ? H + 1 : (c + 1) * SW;
            if (LO < H + 1) begin : g_on
                (* keep = "true" *) reg [AR-1:0] rpc;
                always @(posedge clk or negedge rnx) if (!rnx) rpc <= 0; else rpc <= rp_nx;
                wire [H:0] row = mem[rpc];
                assign rhd[t * (H + 1) + LO +: HI - LO] = row[HI-1:LO];
            end
        end
        assign rne[t] = nz; assign lir[t] = cr; assign rxf[t] = f;
    end endgenerate
    assign li0_r = lir[0]; assign li1_r = lir[1];
    wire [H:0] h0 = rhd[H:0], h1 = rhd[2*H+1:H+1];
    reg perr;
    // host-plane frame types this endpoint accepts (HOST 1, KS 2) -- none at HOST_EN 0
`ifdef OT_S81SL_LEP_MUT_NHACC
    wire hacc = !h0[0] && (h0[3:1] == 3'd1 || h0[3:1] == 3'd2);        // MUTANT: accepted even at HOST_EN 0
`else
    wire hacc = (HOST_EN != 0) && !h0[0] && (h0[3:1] == 3'd1 || h0[3:1] == 3'd2);
`endif
    reg [1103:1] rid; reg riv;
    assign ri = {rid, riv};
    always @(posedge clk) rid <= (rel && h0[0]) ? {h1[H-1:0], h0[H-1:1]} : 1103'd0;   // data: no reset
    always @(posedge clk or negedge rnx)
        if (!rnx) begin riv <= 1'b0; perr <= 1'b0; end
        else begin
            riv <= rel && h0[0];
            if (|rxf) perr <= 1'b1;                    // a beat landed on a full RX FIFO (credit protocol broken)
            // a released pair must be one frame (equal sequence parity); a die endpoint accepts ring / HOST / KS only
            // (ring only at HOST_EN 0)
            if (rel && (h0[H] != h1[H] || (!h0[0] && !hacc))) perr <= 1'b1;
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
            fh_v <= rel && !h0[0] && h0[3:1] == 3'd1;
            fk_s <= rel && !h0[0] && h0[3:1] == 3'd2 && ksp[52];
        end
    always @(posedge clk) begin
        if (rel && !h0[0] && h0[3:1] == 3'd1) fh_d <= h0[4 +: 514];
        if (rel && !h0[0] && h0[3:1] == 3'd2) fk_d <= ksp[51:0];
        lf <= {l1_st[0] | (|l1_f), l1_st[1], l0_st[0] | (|l0_f), l0_st[1]};
    end
    assign f_host = {fh_d, fh_v};
    assign f_ks = {fk_s, fk_d};
    assign f_lf = lf;
    end else begin : g_nhrx                            // HOST_EN 0: no host outputs (the _nh tops have no such ports)
    assign f_host = 515'd0; assign f_ks = 53'd0; assign f_lf = 4'd0;
    end endgenerate

    // ---------------------------------------------------------------- fault collector (sticky)
    reg slq; reg [5:0] lfq;
    always @(posedge clk or negedge rn)
        if (!rn) begin slq <= 1'b0; lfq <= 6'd0; fault <= 1'b0; end
        else begin
            slq <= sl_f; lfq <= {l1_f, l0_f};
            if ((|ovf) || perr || herr || slq || (|lfq)) fault <= 1'b1;
        end
endmodule

// HOST_EN = 0 leaf top (hardened master of the three host-less endpoints s_0S / s_0N / s_7S): no host ports
module ot_s81sl_lep_nh #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    output wire            fault
);
    // no l0_st / l1_st: the PHY lane status feeds only f_lf (host plane) at HOST_EN 1 (the lane tiles still take it in
    // their rx word, and lane faults reach the fault collector through l0_f / l1_f).  The core reads none of t_host / t_kd /
    // l*_st at HOST_EN 0 (generate), so these constants are not logic: synthesis of this top keeps no host pin or flop.
    ot_s81sl_lep #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0)) u (.clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(), .fault(fault));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The end-slice cluster: slice + lep + 2 link lanes.  SIDE 0 = W end (outward = ri_w / ro_w), 1 = E end.  The die
// masters are the parameter-free tops below (one per outward face: pin plans differ, as dsfd_coll_lane_w / _e).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_slice_lep #(
    parameter integer SIDE = 0,
    parameter integer HOST_EN = 1        // 0: leaf ot_s81sl_lep_nh, host ports unread / driven 0 (the _nh masters drop them)
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_n,         // inward line port (from / to the inward neighbour)
    output wire [1103:0]   ro_n,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [1103:0] bo,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    input  wire            ch_b,
    output wire [511:0]    tx0, output wire [511:0] tx1,
    input  wire [513:0]    rx0, input  wire [513:0] rx1,
    output wire [1:0]      tf,
    input  wire [76:0]     t_host, input wire [53:0] t_kd,
    output wire [514:0]    f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    output wire            fault
);
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    generate if (SIDE == 0) begin : g_w
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(lri), .ri_e(ri_n), .ro_e(ro_n), .ro_w(lro),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_w #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .tf(tf[0]), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_w #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .tf(tf[1]), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end else begin : g_e
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_n), .ri_e(lri), .ro_e(lro), .ro_w(ro_n),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_e #(.LCR(1)) u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .tf(tf[0]), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_e #(.LCR(1)) u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .tf(tf[1]), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end endgenerate
    generate if (HOST_EN != 0) begin : g_h
    ot_s81sl_lep u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .l0_st(rx0[513:512]), .l1_st(rx1[513:512]),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .fault(fault));
    end else begin : g_nh
    ot_s81sl_lep_nh u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .fault(fault));
    assign f_host = 515'd0; assign f_lf = 4'd0; assign f_ks = 53'd0;
    end endgenerate
endmodule

// die masters (S81-LEPV 10-18: host plane only on s_7N)
//   dsdv_slice_lepw     s_0S / s_0N   W end, no host plane (HOST_EN 0: no host ports)
//   dsdv_slice_lepe     s_7N          E end, host plane (t_host / t_kd in, f_host / f_lf / f_ks out)
//   dsdv_slice_lepe_nh  s_7S          E end, no host plane
module ot_s81sl_slice_lepw (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(0), .HOST_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_e), .ro_n(ro_e), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(), .fault(fault));   // host ports unread at HOST_EN 0
endmodule
module ot_s81sl_slice_lepe (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    input  wire [76:0] t_host, input wire [53:0] t_kd, output wire [514:0] f_host, output wire [3:0] f_lf, output wire [52:0] f_ks,
    output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(1), .HOST_EN(1)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .fault(fault));
endmodule
module ot_s81sl_slice_lepe_nh (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf,
    output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(1), .HOST_EN(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(), .fault(fault));   // host ports unread at HOST_EN 0
endmodule
