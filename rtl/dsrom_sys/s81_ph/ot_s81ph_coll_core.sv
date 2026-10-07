`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81ph_coll_core (CLAUDE S81-PH, 2026-10-06): the stream-domain logic of the S81 die collective slab
// (dsfd_sp_collective).  Contract: results/rtl/s81_ph_20261006/collective/contract.json.
//
//  * TP4 collective engine = the S81 C8 parent's engine, unchanged: ot_w15_rom_oneshot_die_px_acceptedpop
//    #(N 4, LANES 16, TAGW 32, DEPTH 256, PKG_DIES 2, RELAY 0, ADD_LAT 3, PAIRWISE 1, GW 4, OUT_BP 1,
//    FIX_ACCEPTED_POP 1) with its receive FIFOs in SRAM (FIFO_SRAM 1).  ONE die master serves every rank, so the
//    engine is built with RANK = 0 and the die's runtime rank R (config word) relabels it: engine port j is
//    absolute rank R ^ j.  The pairwise fold ((p0 + p1) + (p2 + p3)) is then computed as ((pR + pR^1) +
//    (pR^2 + pR^3)), the same two inner sums and the same outer sum with operands swapped -- equal bit for bit
//    because the binary32 RNE add is commutative (tb_s81ph_coll_rank: against the engine built with RANK = R).
//    The all-gather beat (4 words in engine port order) is re-ordered to absolute rank order (slot a <- word a ^ R).
//  * Links: lane 0 = W0 (UCIe, package peer = engine port 1), lane 1 = W1 and lane 2 = W2 (board T1 to the
//    partner package's dies R^2 and R^3 = engine ports 2, 3), lanes 3..7 = W3, E0..E3: five pass-through channels
//    (stage hop in / out, token return, draft; their use is the VM program's).  Every lane: ot_s81ph_link_ep
//    (reliable link layer of ot_dsrom_link_ct) + ot_s81ph_link_gbx (512-b beat format).
//  * Engine link flit (552 b): [546:0] engine record {tag, mode, last, par, data}, [547] record valid,
//    [549:548] / [551:550] credit returns of parity 0 / 1 (0..3 each).  Records leave through a 2-entry skid per
//    link (engine tx_ready = skid room); credits returned by the engine (cr_out) are counted and sent in the next
//    flit (a credit-only flit when no record waits); received counts are replayed into cr_in one a cycle.
//  * VM side (stream domain; the serial <-> stream ratio CDC end blocks are generator glue):
//    f_vm[591:0] = {data 552, tag 32, mode, last, link 3, type 2, valid}: type 1 engine record, 2 pass-through
//      flit (link 0..4), 3 config (data[1:0] rank, data[2] engine enable).  The VM sends only with credits:
//      6 input queues (q0 engine, q1..q5 pass-through) of QD words each.
//    t_vm[2099:0] header [51:0] + data 2048 (layout in the contract); ts[0] = the CDC has room for >= 4 words.
// ---------------------------------------------------------------------------
module ot_s81ph_coll_core #(
    parameter integer FB = 69,
    parameter integer CREDITS = 512,
    parameter integer SEQW = 10,
    parameter integer CH_UCIE = 100,
    parameter integer CH_BOARD = 400,
    parameter integer IDLE_P = 1024,
    parameter integer SRAM = 1,
    parameter integer QD = 8,                  // pass-through input queues (VM credits)
    parameter integer QD0 = 16,                // engine input queue (covers the VM credit round trip)
    parameter integer TRACE = 0,
    parameter integer EXT = 0                  // CLAUDE S81-PH coll v2: 1 = the 8 links live in lane tiles (x_* ports)
) (
    input  wire              clk,
    input  wire              rst_n,
    // lanes (registered at the pins by the caller)
    input  wire [8*515-1:0]  lane_rx,      // per lane {fault, live, data 512, valid}
    output wire [8*512-1:0]  lane_tx,
    // VM
    input  wire [591:0]      f_vm,
    input  wire [2:0]        ts,
    output reg  [2099:0]     t_vm,
    output reg               fault,
    output reg  [1:0]        rank,
    output reg               eng_en,
    // EXT = 1: lane tile interfaces (the link endpoint's in_* / out_* streams; skids in the tiles), lane faults
    output wire [7:0]        x_lo_v,
    input  wire [7:0]        x_lo_r,
    output wire [8*552-1:0]  x_lo_d,
    output wire [7:0]        x_lo_l,
    input  wire [7:0]        x_li_v,
    output wire [7:0]        x_li_r,
    input  wire [8*552-1:0]  x_li_d,
    input  wire [7:0]        x_li_l,
    input  wire [23:0]       x_lflt         // per lane {meso end fault, gearbox fault, endpoint fault}
);
    localparam integer W = FB * 8;                         // 552
    localparam integer FFW = SEQW + 1 + W + 32;            // 595
    localparam integer RFW = 1 + SEQW + $clog2(CREDITS + 1) + 32;   // 53
    localparam integer G = 509 - RFW;                      // 456
    localparam integer S = FFW + 1;                        // 596
    localparam integer PNUM = FB * G * (IDLE_P - 1);
    localparam integer PDEN = S * IDLE_P;
    localparam integer FW = 512, TAGW = 32, PW = FW + 3 + TAGW;   // 547
    genvar l, j;


    // ------------------------------------------------------------------ config
    wire        fv = f_vm[0];
    wire [1:0]  ftype = f_vm[2:1];
    wire [2:0]  flink = f_vm[5:3];
    wire        flast = f_vm[6];
    wire        fmode = f_vm[7];
    wire [31:0] ftag = f_vm[39:8];
    wire [W-1:0] fdata = f_vm[40 +: W];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rank <= 0; eng_en <= 1'b0; end
        else if (fv && ftype == 2'd3) begin rank <= fdata[1:0]; eng_en <= fdata[2]; end
    reg erst_n;                                            // engine reset: released one cycle after enable
    always @(posedge clk or negedge rst_n) if (!rst_n) erst_n <= 1'b0; else erst_n <= eng_en;

    // ------------------------------------------------------------------ input queues (VM credits)
    wire [5:0]  q_hv, q_pop, q_flt;
    wire [W+33:0] q_hd [0:5];                              // {last, mode, tag, data}
    generate for (j = 0; j < 6; j = j + 1) begin : g_q
        wire psh = fv && ((j == 0) ? (ftype == 2'd1) : (ftype == 2'd2 && flink == j - 1));
        ot_s81ph_rfifo #(.W(W + 34), .D((j == 0) ? QD0 : QD)) u_q (.clk(clk), .rst_n(rst_n), .push(psh),
            .wd({flast, fmode, ftag, fdata}), .pop(q_pop[j]), .hv(q_hv[j]), .hd(q_hd[j]), .room(), .room2(),
            .fault(q_flt[j]));
    end endgenerate

    // ------------------------------------------------------------------ links
    wire [7:0]  ep_iv, ep_ir, ep_ov, ep_or, ep_ol, ep_il, ep_flt, gb_flt, gb_lock;
    wire [W-1:0] ep_id [0:7];
    wire [W-1:0] ep_od [0:7];
    generate for (l = 0; l < 8; l = l + 1) begin : g_link
      if (EXT == 0) begin : g_int

        wire          ftv, rtv, frv, rrv;
        wire [FFW-1:0] ft, fr;
        wire [RFW-1:0] rt, rr;
        wire [514:0]  lr = lane_rx[l*515 +: 515];
        wire [511:0]  bt;
        ot_s81ph_link_ep #(.FLIT_BYTES(FB), .TX_STAGES(2), .RX_STAGES(3), .CHANNEL_CYCLES(l == 0 || l == 4 ? CH_UCIE : CH_BOARD),
            .CREDITS(CREDITS), .SEQW(SEQW), .PHY_NUM(PNUM), .PHY_DEN(PDEN), .SRAM(SRAM)) u_ep (
            .clk(clk), .rst_n(rst_n), .ch_b(1'b0),
            .in_valid(ep_iv[l]), .in_ready(ep_ir[l]), .in_data(ep_id[l]), .in_last(ep_il[l]),
            .out_valid(ep_ov[l]), .out_ready(ep_or[l]), .out_data(ep_od[l]), .out_last(ep_ol[l]),
            .f_tx_v(ftv), .f_tx(ft), .f_rx_v(frv), .f_rx(fr), .r_tx_v(rtv), .r_tx(rt), .r_rx_v(rrv), .r_rx(rr),
            .credit_stalls(), .fault(ep_flt[l]), .fault_code(), .st_flits_tx(), .st_flits_rx_ok(), .st_crc_err(),
            .st_naks(), .st_replays(), .st_timeouts(), .st_retx_flits(), .st_max_replay_occ());
        ot_s81ph_link_gbx #(.FFW(FFW), .RFW(RFW), .IDLE_P(IDLE_P)) u_gb (
            .clk(clk), .rst_n(rst_n), .f_tx_v(ftv), .f_tx(ft), .r_tx_v(rtv), .r_tx(rt), .beat_tx(bt),
            .beat_rx_v(lr[0] && lr[513]), .beat_rx(lr[512:1]), .f_rx_v(frv), .f_rx(fr), .r_rx_v(rrv), .r_rx(rr),
            .locked(gb_lock[l]), .fault(gb_flt[l]));
        assign lane_tx[l*512 +: 512] = bt;
        assign x_lo_v[l] = 1'b0; assign x_lo_d[l*W +: W] = {W{1'b0}}; assign x_lo_l[l] = 1'b0; assign x_li_r[l] = 1'b0;
      end else begin : g_ext
        assign x_lo_v[l] = ep_iv[l]; assign ep_ir[l] = x_lo_r[l]; assign x_lo_d[l*W +: W] = ep_id[l]; assign x_lo_l[l] = ep_il[l];
        assign ep_ov[l] = x_li_v[l]; assign x_li_r[l] = ep_or[l]; assign ep_od[l] = x_li_d[l*W +: W]; assign ep_ol[l] = x_li_l[l];
        assign ep_flt[l] = x_lflt[3*l]; assign gb_flt[l] = x_lflt[3*l+1]; assign gb_lock[l] = 1'b1;
        assign lane_tx[l*512 +: 512] = 512'd0;
      end
    end endgenerate

    // ------------------------------------------------------------------ engine (RANK 0, runtime relabel)
    wire          e_iv = q_hv[0] && erst_n;
    wire          e_ir;
    wire [3:0]    tx_valid, tx_ready;
    wire [PW-1:0] tx_rec;
    wire [7:0]    cr_in, cr_out;
    wire [3:0]    rx_valid;
    wire [PW-1:0] rx_rec1, rx_rec2, rx_rec3;
    wire [4*PW-1:0] rx_rec_f = {rx_rec3, rx_rec2, rx_rec1, {PW{1'b0}}};
    wire [3:1]    sk_flt_v;
    wire          o_v, o_last, o_err; wire [1:0] o_rank; wire [4*FW-1:0] o_d;
    reg           o_rdy;
    wire          e_flt; wire [2:0] e_code;
    assign q_pop[0] = e_iv && e_ir;
    ot_w15_rom_oneshot_die_px_acceptedpop #(.FIX_ACCEPTED_POP(1), .N(4), .RANK(0), .LANES(16), .TAGW(TAGW),
        .DEPTH(256), .PKG_DIES(2), .RELAY(0), .ADD_LAT(3), .PAIRWISE(1), .GW(4), .OUT_BP(1),
        .FIFO_SRAM(SRAM), .SRAM_MACRO(1)) u_eng (
        .clk(clk), .rst_n(erst_n),
        .in_valid(e_iv), .in_ready(e_ir), .in_data(q_hd[0][FW-1:0]), .in_last(q_hd[0][W+33]),
        .in_mode(q_hd[0][W+32]), .in_tag(q_hd[0][W +: TAGW]),
        .tx_valid(tx_valid), .tx_rec(tx_rec), .tx_ready(tx_ready), .cr_in(cr_in),
        .rx_valid(rx_valid), .rx_rec(rx_rec_f), .cr_out(cr_out),
        .rl_tx_valid(), .rl_tx_rec(), .rl_rx_valid(4'd0), .rl_rx_rec({4*PW{1'b0}}),
        .out_valid(o_v), .out_ready(o_rdy), .out_data(o_d), .out_last(o_last), .out_rank(o_rank), .out_err(o_err),
        .fault(e_flt), .fault_code(e_code));
    assign tx_ready[0] = 1'b1;
    assign cr_in[1:0] = 2'b00;
    // engine ports 1..3 <-> lanes 0..2
    assign rx_valid[0] = 1'b0;
    generate for (j = 1; j < 4; j = j + 1) begin : g_ep
        localparam integer L = j - 1;
        wire sk_hv, sk_room2; wire [PW-1:0] sk_hd;
        wire flit_go = ep_iv[L] && ep_ir[L];
        reg  [7:0] crx0, crx1, crs0, crs1;                 // credits received (to replay) / returned (to send), <= PD
        wire [1:0] cs0 = (crs0 > 3) ? 2'd3 : crs0[1:0], cs1 = (crs1 > 3) ? 2'd3 : crs1[1:0];
        reg        rxv; reg [PW-1:0] rxr;
        ot_s81ph_rfifo #(.W(PW), .D(4)) u_sk (.clk(clk), .rst_n(erst_n), .push(tx_valid[j]), .wd(tx_rec),
            .pop(flit_go && sk_hv), .hv(sk_hv), .hd(sk_hd), .room(), .room2(sk_room2), .fault(sk_flt_v[j]));
        assign tx_ready[j] = sk_room2;
        assign ep_iv[L] = erst_n && (sk_hv || crs0 != 0 || crs1 != 0);
`ifdef OT_S81PH_MUT_NOCREDIT
        assign ep_id[L] = {2'b00, 2'b00, sk_hv, sk_hd};   // negative control: credit returns never carried
`else
        assign ep_id[L] = {cs1, cs0, sk_hv, sk_hd};
`endif
        assign ep_il[L] = 1'b0;
        assign ep_or[L] = 1'b1;
        assign cr_in[2*j +: 2] = {crx1 != 0, crx0 != 0};
        assign rx_valid[j] = rxv;
        if (j == 1) begin : g_r1 assign rx_rec1 = rxr; end
        else if (j == 2) begin : g_r2 assign rx_rec2 = rxr; end
        else begin : g_r3 assign rx_rec3 = rxr; end
        wire [1:0] in0 = ep_ov[L] ? ep_od[L][PW + 1 +: 2] : 2'd0;
        wire [1:0] in1 = ep_ov[L] ? ep_od[L][PW + 3 +: 2] : 2'd0;
        always @(posedge clk or negedge erst_n) begin
            if (!erst_n) begin
                crx0 <= 0; crx1 <= 0; crs0 <= 0; crs1 <= 0; rxv <= 1'b0; rxr <= 0;
            end else begin
                rxv <= ep_ov[L] && ep_od[L][PW];
                if (ep_ov[L]) rxr <= ep_od[L][PW-1:0];
                // received counts: one credit a cycle into cr_in (the peer engine returns <= 1 a cycle a parity)
                crx0 <= crx0 - ((crx0 != 0) ? 8'd1 : 8'd0) + {6'd0, in0};
                crx1 <= crx1 - ((crx1 != 0) ? 8'd1 : 8'd0) + {6'd0, in1};
                // engine credits counted; the count carried by the flit is subtracted when it goes
                crs0 <= crs0 + (cr_out[2*j] ? 8'd1 : 8'd0) - (flit_go ? {6'd0, cs0} : 8'd0);
                crs1 <= crs1 + (cr_out[2*j+1] ? 8'd1 : 8'd0) - (flit_go ? {6'd0, cs1} : 8'd0);
            end
        end
    end endgenerate

    // ------------------------------------------------------------------ pass-through lanes 3..7
    generate for (j = 0; j < 5; j = j + 1) begin : g_pt
        localparam integer L = 3 + j;
        assign ep_iv[L] = q_hv[1 + j];
        assign ep_id[L] = q_hd[1 + j][W-1:0];
        assign ep_il[L] = q_hd[1 + j][W+33];
        assign q_pop[1 + j] = ep_iv[L] && ep_ir[L];
    end endgenerate

    // ------------------------------------------------------------------ engine output: order, reorder, pack
    // Engine outputs leave in pop order = the fire order of this die's own records (every index pops all four
    // sources at once), so a 1-bit FIFO of the own records' modes tells which output is a reduce word (no
    // handshake) and which an all-gather beat (held by out_ready, OUT_BP).
    reg  [511:0] mq;                                       // mode FIFO (<= 256 in the self FIFO + pipeline)
    reg  [8:0]   mq_w, mq_r;
    reg          mq_flt;
    wire         hmode = mq[mq_r];
    wire         e_fire = e_iv && e_ir;
    reg  [4*FW-1:0] pk_d;
    reg  [3:0]   pk_l;
    reg          pk_err;
    reg  [2:0]   pk_n;
    wire         oq_room2, oq_hv; wire [2099:1] oq_hd; wire oq_flt;
    wire         in_red = o_v && !hmode;
    always @(*) o_rdy = hmode && (pk_n == 0) && oq_room2;
    wire         in_gat = o_v && hmode && o_rdy;
    wire         o_take = in_red || in_gat;
    // gather beat in absolute rank order
    reg  [4*FW-1:0] gat_d;
`ifdef OT_S81PH_MUT_NOREORDER
    always @(*) gat_d = o_d;                               // negative control: no rank relabel of the gather beat
`else
    always @(*) for (integer i = 0; i < 4; i = i + 1) gat_d[i*FW +: FW] = o_d[(i ^ rank)*FW +: FW];
`endif
    wire         pk_emit = (pk_n != 0) && (pk_n == 4 || !in_red);
    // pass-through receive: round robin over lanes 3..7 when no engine beat is pushed this cycle
    reg  [2:0]   rr;
    reg  [4:0]   pt_sel;
    always @(*) begin
        pt_sel = 5'd0;
        if (!pk_emit && !in_gat && oq_room2)
            for (integer i = 4; i >= 0; i = i - 1) if (ep_ov[3 + ((rr + i) % 5)]) pt_sel = 5'd1 << ((rr + i) % 5);
    end
    generate for (j = 0; j < 5; j = j + 1) begin : g_ptr
        assign ep_or[3 + j] = pt_sel[j];
    end endgenerate
    reg  [2:0]   pt_l;
    always @(*) begin pt_l = 0; for (integer i = 0; i < 5; i = i + 1) if (pt_sel[i]) pt_l = i; end
    wire         pt_push = pt_sel != 0;
    // credits returned to the VM (one per input-queue pop), carried in every beat; status beats when idle
    reg  [4:0]   qc [0:5];
    reg  [3:0]   qf [0:5];
    always @(*) for (integer i = 0; i < 6; i = i + 1) qf[i] = (qc[i] > 15) ? 4'd15 : qc[i][3:0];
    reg  [7:0]   fv_flt;
    reg          fault_sent;
    wire         st_need = (qc[0] != 0 || qc[1] != 0 || qc[2] != 0 || qc[3] != 0 || qc[4] != 0 || qc[5] != 0 ||
                            (fault && !fault_sent));
    wire         st_push = !pk_emit && !in_gat && !pt_push && st_need && oq_room2;
    wire         oq_push = pk_emit || in_gat || pt_push || st_push;
    wire [1:0]   b_type = (pk_emit || in_gat) ? 2'd1 : pt_push ? 2'd2 : 2'd3;
    wire [3:0]   b_mask = pk_emit ? ((pk_n == 4) ? 4'hF : (pk_n == 3) ? 4'h7 : (pk_n == 2) ? 4'h3 : 4'h1) :
                          in_gat ? 4'hF : 4'h0;
    wire [3:0]   b_last = pk_emit ? pk_l : in_gat ? {o_last, 3'b000} : 4'h0;
    wire [4*FW-1:0] b_d = pk_emit ? pk_d : in_gat ? gat_d : pt_push ? {{(4*FW-W){1'b0}}, ep_od[3 + pt_l]} : {4*FW{1'b0}};
    wire [23:0]  b_cr = {qf[5], qf[4], qf[3], qf[2], qf[1], qf[0]};
    // header [51:1] (bit 0 = valid at the pin)
    wire [2099:1] b_word = {b_d, rank, fv_flt, fault, b_cr, pk_emit ? pk_err : 1'b0, in_gat && !pk_emit,
                            pt_push ? ep_ol[3 + pt_l] : 1'b0, b_last, b_mask, pt_push ? pt_l : 3'd0, b_type};
    ot_s81ph_rfifo #(.W(2099), .D(4)) u_oq (.clk(clk), .rst_n(rst_n), .push(oq_push), .wd(b_word),
        .pop(oq_hv && ts[0]), .hv(oq_hv), .hd(oq_hd), .room(), .room2(oq_room2), .fault(oq_flt));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) t_vm <= 0;
        else t_vm <= (oq_hv && ts[0]) ? {oq_hd, 1'b1} : 2100'd0;

    reg [7:0] lane_flt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mq_w <= 0; mq_r <= 0; mq_flt <= 1'b0; pk_n <= 0; pk_l <= 0; pk_err <= 1'b0; rr <= 0;
            for (integer i = 0; i < 6; i = i + 1) qc[i] <= 0;
            fv_flt <= 0; fault <= 1'b0; fault_sent <= 1'b0; lane_flt <= 0;
        end else begin
            if (e_fire) begin mq[mq_w] <= q_hd[0][W+32]; mq_w <= mq_w + 1'b1; end
            if (o_take) mq_r <= mq_r + 1'b1;
            if (o_v && mq_w == mq_r) mq_flt <= 1'b1;
            if (e_fire && (mq_w + 9'd1) == mq_r) mq_flt <= 1'b1;
            // packer
            if (pk_emit) begin pk_n <= 0; pk_l <= 0; pk_err <= 1'b0; end
            if (in_red) begin
                pk_d[(pk_emit ? 0 : pk_n) * FW +: FW] <= o_d[FW-1:0];
                if (pk_emit) begin pk_n <= 1; pk_l <= {3'b000, o_last}; pk_err <= o_err; end
                else begin pk_n <= pk_n + 1'b1; pk_l[pk_n] <= o_last; pk_err <= pk_err | o_err; end
            end
            if (pt_push) rr <= (pt_l == 4) ? 0 : pt_l + 1'b1;
            for (integer i = 0; i < 6; i = i + 1)
                qc[i] <= qc[i] - (oq_push ? {1'b0, qf[i]} : 5'd0) + (q_pop[i] ? 5'd1 : 5'd0);
            for (integer i = 0; i < 8; i = i + 1) if (EXT ? x_lflt[3*i+2] : lane_rx[i*515 + 514]) lane_flt[i] <= 1'b1;
            fv_flt <= fv_flt | {|lane_flt, mq_flt, oq_flt, |q_flt, e_flt, |gb_flt, |ep_flt,
                                |sk_flt_v};
            if (|fv_flt) fault <= 1'b1;
            if (st_push && fault) fault_sent <= 1'b1;
        end
    end
    wire unused_ok = &{1'b0, o_rank, e_code, gb_lock, ts[2:1], ep_ol[2:0]};
endmodule
