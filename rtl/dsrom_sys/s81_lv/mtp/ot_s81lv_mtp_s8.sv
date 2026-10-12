`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81lv_mtp_s8 (s81lv/C-mtp, 2026-10-12): seam S8 of the S81 layer vehicle -- layer output h -> hrow -> MTP seed.
//
// Drop-in for tb_s81_die_layer (`ifdef OT_S81LV_MTP_REAL): attaches to the HC master's H_STORE write ports
// (dsfd_sp_hc_c wq_v / wq_row / wq_mask / wq_d, S_WR slots, rows S_BASE ..) in parallel with the VM, and carries the
// head-die MTP sequencer handshake.  Every block below is the real element RTL, unchanged:
//
//   H_STORE taps --> [h window: the VM rows S_BASE .. S_BASE+HROWS-1 as 1,024-b beats + row-completion counter]
//       (vehicle stand-in for the VM region the production dsfd_mtp_hrow_src reads; written lane-masked, counted per
//        row once all 16 lanes landed -- the s81-vm-1011 row-completion counter)
//   completion --> one WFC-kit hep event per hrow position {user, pos, epoch} (positions POS, POS+1)
//   3 x dsfd_mtp_hrow_src (PART 0 / 1 / 2)  -- VM reads (grant link -> ot_dsrom_mtp_lrx_rtt -> window, in order)
//            --> hidden lanes (ot_dsrom_mtp_hrow_tx flit stream, grant protocol)
//   dsfd_mtp_hrow_tc (TILES=1, the hardened two-level composition) | dsfd_mtp_hrow (TILES=0, flat)
//            --> its real seed-client read port (f_vrq / t_vrq / t_vrs) is this module's port
//   RESULT (head controller, valid/ready) --> [GATE: held until every hidden-lane flit of both positions has landed at
//            the hrow] --> dsfd_cap_mtp_ep --> dsfd_mtp_seq_rtt --> seed / token return --> dsfd_coll_mtp_ep (c_s* / c_t*)
//            draft-head steps / rows-ready / draft-head results <--> dsfd_vm_mtp_ep (c_h* / c_w* / c_q*)
//
// h layout: HROWS = 640 H_STORE rows (HC x D BF16, hc_gate Run.h_rows packing) = 320 beats of 1,024 b; beat b =
// {row 2b+1, row 2b}.  One hrow position holds 3 parts x 80 beats = 240 beats, so h occupies position POS (beats
// 0..239, part p = beats 80p..80p+79) and POS+1 (beats 240..319 in part 0; parts 1, 2 read as zero pad).
//
// Mutants (negative controls, never in a real build):
//   OT_S81LV_MTP_MUT_DROP   the data of one H_STORE beat (row DROP_ROW) is not written into the hrow path (its
//                           completion is still counted, as a datapath write lost after the row counter)
//   OT_S81LV_MTP_MUT_EARLY  no GATE: the RESULT reaches the sequencer before the hrow row is complete
// ---------------------------------------------------------------------------------------------------------------
module ot_s81lv_mtp_s8 #(
    parameter integer S_WR = 8, parameter integer S_BASE = 6144, parameter integer HROWS = 640,
    parameter integer NW = 21, parameter integer USER_W = 10, parameter integer FLIT = 512, parameter integer AW = 24,
    parameter integer TILES = 1,
    parameter integer SEQ_MAXU = 8,
`ifdef OT_S81LV_MTP_MUT_DROP
    parameter integer DROP_ROW = 333,
`else
    parameter integer DROP_ROW = -1,
`endif
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer DW = USER_W + 3 + NW
) (
    input  wire [0:0]            ck, rst,                 // rst: active-low (dsfd convention)
    // static configuration of the head position: {epoch, pos, user}; sequencer {glen, plen}
    input  wire [USER_W-1:0]     cfg_user,
    input  wire [NW-1:0]         cfg_pos,
    input  wire [3:0]            cfg_ep,
    input  wire [2*NW-1:0]       cfg_seq,
    // H_STORE taps (dsfd_sp_hc_c write ports)
    input  wire [S_WR-1:0]       wq_v,
    input  wire [S_WR*14-1:0]    wq_row,
    input  wire [S_WR*16-1:0]    wq_mask,
    input  wire [S_WR*512-1:0]   wq_d,
    // RESULT from the head controller (valid / ready)
    input  wire                  c_rv, output wire c_rr, input wire [FLIT-1:0] c_rd,
    // collective end of the sequencer: seed and token return (valid / ready)
    output wire                  c_sv, input wire c_sr, output wire [SW-1:0] c_sd,
    output wire                  c_tv, input wire c_tr, output wire [FLIT-1:0] c_td,
    // VM end: draft-head steps out, rows ready in, draft-head results in (valid / ready)
    output wire                  c_hv, input wire c_hr, output wire [DW-1:0] c_hd,
    input  wire                  c_wv, output wire c_wr, input wire [USER_W-1:0] c_wd,
    input  wire                  c_qv, output wire c_qr, input wire [DW-1:0] c_qd,
    // hrow seed-client read port (grant protocol: request {addr {epoch, user, pos 8, beat 8}, valid}, grant, response)
    input  wire [AW:0]           f_vrq,
    output wire [0:0]            t_vrq,
    output wire [1024:0]         t_vrs,
    // status
    output wire                  h_done,                  // every H_STORE row of h landed (row counter)
    output wire                  hrow_landed,             // every hidden-lane flit of both positions at the hrow
    output wire [3:0]            hrow_flt,                // {window addr fault, hrow store fault[2:0]}
    output wire [5:0]            src_flt,
    output wire [2*NW+USER_W+4:0] t_acc
);
    localparam integer NB = HROWS / 2;                    // 320 beats
    localparam integer HR = 8;                            // hrow_src VM ring rows a user (address field only)
    wire clk = ck[0];
    wire rn;
    ot_dsrom_mtp_rstsync u_rs (.clk(clk), .rst_n_async(rst[0]), .rst_n(rn));

    // ------------------------------------------------------------ h window + row-completion counter
    reg [511:0] win [0:HROWS-1];
    reg [15:0]  lanes [0:HROWS-1];
    reg [$clog2(HROWS+1)-1:0] ndone;
    integer s, l, r;
    reg [$clog2(HROWS+1)-1:0] inc;
    always @(posedge clk or negedge rn)
        if (!rn) begin
            ndone <= 0;
            for (r = 0; r < HROWS; r = r + 1) lanes[r] <= 16'h0;
        end else begin
            inc = 0;
            for (s = 0; s < S_WR; s = s + 1)
                if (wq_v[s] && wq_row[14*s +: 14] >= S_BASE && wq_row[14*s +: 14] < S_BASE + HROWS) begin
                    if (lanes[wq_row[14*s +: 14] - S_BASE] != 16'hFFFF &&
                        (lanes[wq_row[14*s +: 14] - S_BASE] | wq_mask[16*s +: 16]) == 16'hFFFF) inc = inc + 1;
                    lanes[wq_row[14*s +: 14] - S_BASE] <= lanes[wq_row[14*s +: 14] - S_BASE] | wq_mask[16*s +: 16];
                end
            ndone <= ndone + inc;
        end
    always @(posedge clk)
        for (s = 0; s < S_WR; s = s + 1)
            if (wq_v[s] && wq_row[14*s +: 14] >= S_BASE && wq_row[14*s +: 14] < S_BASE + HROWS
                && (wq_row[14*s +: 14] - S_BASE) != DROP_ROW)
                for (l = 0; l < 16; l = l + 1)
                    if (wq_mask[16*s + l]) win[wq_row[14*s +: 14] - S_BASE][32*l +: 32] <= wq_d[512*s + 32*l +: 32];
    assign h_done = ndone == HROWS;

    // ------------------------------------------------------------ hep events: positions POS, POS+1 after completion
    reg [1:0] hst;                                        // 0 wait, 1 sent POS, 2 sent POS+1
    reg [USER_W+NW+4:0] hep;
    always @(posedge clk or negedge rn)
        if (!rn) begin hst <= 2'd0; hep[USER_W+NW+4] <= 1'b0; end
        else begin
            hep[USER_W+NW+4] <= 1'b0;
            if (hst == 2'd0 && h_done) begin hst <= 2'd1; hep[USER_W+NW+4] <= 1'b1; end
            else if (hst == 2'd1)       begin hst <= 2'd2; hep[USER_W+NW+4] <= 1'b1; end
        end
    always @(posedge clk) hep[USER_W+NW+3:0] <= {cfg_user, (hst == 2'd0) ? cfg_pos : cfg_pos + 1'b1, cfg_ep};

    // ------------------------------------------------------------ 3 x hrow_src -> window reads -> hidden lanes
    wire [514:0] hp [0:2];
    wire [2:0] hpg;
    reg  [2:0] wflt;
    genvar gp;
    generate for (gp = 0; gp < 3; gp = gp + 1) begin : g_src
        wire [AW:0] vrq; wire vrg; reg [1024:0] vrs;
        dsfd_mtp_hrow_src #(.NW(NW), .USER_W(USER_W), .PART(gp), .HR(HR), .VM_AW(AW), .HBASE(gp << 13)) u_src (
            .ck(ck), .rst(rst), .f_hep(hep), .t_vrq(vrq), .f_vrq(vrg), .f_vrs(vrs), .t_hp(hp[gp]), .f_hpg(hpg[gp]),
            .t_flt(src_flt[2*gp +: 2]));
        // VM port of the window: RTT receiver, then a 2-stage fixed-latency read (in order)
        wire qv; wire [AW-1:0] qa;
        ot_dsrom_mtp_lrx_rtt #(.W(AW), .D(16), .ENABLE_RTT(1), .FORWARD_HOPS(1), .RETURN_HOPS(1)) u_vq (
            .clk(clk), .rst_n(rn), .l_valid(vrq[0]), .l_ready(vrg), .l_data(vrq[AW:1]),
            .c_valid(qv), .c_ready(1'b1), .c_data(qa));
        // addr = HBASE(part << 13) + {user mod 8, pos mod 8, beat 7}
        wire [2:0] n3 = qa[9:7] - cfg_pos[2:0];          // hrow position index (0: POS, 1: POS+1)
        wire [9:0] gb = (n3 == 3'd0 ? 10'd0 : 10'd240) + 10'(gp * 80) + 10'(qa[6:0]);
        wire bad = qa[14:13] != gp || qa[12:10] != cfg_user[2:0] || n3 > 3'd1 || qa[6:0] > 7'd79;
        reg v1; reg [9:0] gb1;
        always @(posedge clk or negedge rn)
            if (!rn) begin v1 <= 1'b0; vrs[0] <= 1'b0; wflt[gp] <= 1'b0; end
            else begin
                v1 <= qv; vrs[0] <= v1;
                if (qv && bad) wflt[gp] <= 1'b1;
            end
        always @(posedge clk) begin
            gb1 <= gb;
            vrs[1024:1] <= (gb1 < NB) ? {win[2*gb1+1], win[2*gb1]} : 1024'd0;
        end
    end endgenerate

    // ------------------------------------------------------------ the hrow (real store)
    wire [2:0] sflt;
    generate if (TILES) begin : g_tc
        dsfd_mtp_hrow_tc #(.NW(NW), .USER_W(USER_W), .AW(AW)) u_hrow (.ck(ck), .rst(rst),
            .f_hp0(hp[0]), .f_hp1(hp[1]), .f_hp2(hp[2]), .t_hpg(hpg),
            .f_vrq(f_vrq), .t_vrq(t_vrq), .t_vrs(t_vrs), .f_clr({(USER_W+1){1'b0}}), .t_flt(sflt));
    end else begin : g_flat
        dsfd_mtp_hrow #(.NW(NW), .USER_W(USER_W), .AW(AW)) u_hrow (.ck(ck), .rst(rst),
            .f_hp0(hp[0]), .f_hp1(hp[1]), .f_hp2(hp[2]), .t_hpg(hpg),
            .f_vrq(f_vrq), .t_vrq(t_vrq), .t_vrs(t_vrs), .f_clr({(USER_W+1){1'b0}}), .t_flt(sflt));
    end endgenerate
    assign hrow_flt = {|wflt, sflt};

    // landed flits at the hrow pins: 2 positions x 3 parts x (1 header + 160 data)
    localparam integer NFL = 2 * 3 * 161;
    reg [$clog2(NFL+1)-1:0] nfl;
    always @(posedge clk or negedge rn)
        if (!rn) nfl <= 0;
        else nfl <= nfl + hp[0][0] + hp[1][0] + hp[2][0];
    assign hrow_landed = nfl == NFL;

    // ------------------------------------------------------------ RESULT gate -> capture end -> sequencer
`ifdef OT_S81LV_MTP_MUT_EARLY
    wire gate = 1'b1;
`else
    wire gate = hrow_landed;
`endif
    wire cr;
    assign c_rr = cr && gate;
    wire s_rv, s_rg; wire [FLIT-1:0] s_rd;
    dsfd_cap_mtp_ep #(.FLIT(FLIT)) e_cap (.ck(ck), .rst(rst), .c_rv(c_rv && gate), .c_rr(cr), .c_rd(c_rd),
        .t_rv(s_rv), .t_rd(s_rd), .f_rg(s_rg));
    wire p_tv, p_tg, p_sv, p_sg, p_wv, p_wg, p_hv, p_hg, p_qv, p_qg;
    wire [FLIT-1:0] p_td; wire [SW-1:0] p_sd; wire [USER_W-1:0] p_wd; wire [DW-1:0] p_hd, p_qd;
    dsfd_mtp_seq_rtt #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W), .MAXU(SEQ_MAXU)) u_seq (
        .ck(ck), .rst(rst), .f_cfg(cfg_seq),
        .f_rv(s_rv), .f_rd(s_rd), .t_rg(s_rg), .t_tv(p_tv), .t_td(p_td), .f_tg(p_tg),
        .t_sv(p_sv), .t_sd(p_sd), .f_sg(p_sg), .f_wv(p_wv), .f_wd(p_wd), .t_wg(p_wg),
        .t_hv(p_hv), .t_hd(p_hd), .f_hg(p_hg), .f_qv(p_qv), .f_qd(p_qd), .t_qg(p_qg), .t_acc(t_acc));
    dsfd_coll_mtp_ep #(.FLIT(FLIT), .NW(NW), .USER_W(USER_W)) e_coll (.ck(ck), .rst(rst),
        .f_tv(p_tv), .f_td(p_td), .t_tg(p_tg), .f_sv(p_sv), .f_sd(p_sd), .t_sg(p_sg),
        .c_tv(c_tv), .c_tr(c_tr), .c_td(c_td), .c_sv(c_sv), .c_sr(c_sr), .c_sd(c_sd));
    dsfd_vm_mtp_ep #(.NW(NW), .USER_W(USER_W)) e_vm (.ck(ck), .rst(rst),
        .f_hv(p_hv), .f_hd(p_hd), .t_hg(p_hg), .c_hv(c_hv), .c_hr(c_hr), .c_hd(c_hd),
        .c_wv(c_wv), .c_wr(c_wr), .c_wd(c_wd), .t_wv(p_wv), .t_wd(p_wd), .f_wg(p_wg),
        .c_qv(c_qv), .c_qr(c_qr), .c_qd(c_qd), .t_qv(p_qv), .t_qd(p_qd), .f_qg(p_qg));
endmodule
