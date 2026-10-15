`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_wfc_stg_static (claude S81 VM F7 static-wfc2, 2026-10-15): the STATIC stage WFC kit of an S81 layer die, built
// from scratch for the owner static-cycle rule (2026-10-14T18:59: the compiler schedules links, memory and buffers; no
// runtime ready, grant or credit decides when anything issues on a production path).  It replaces the grant-form kit
// dsfd_wfc_stg_cl (closed tokpipe WFC + dsfd_wfc_lnk credits + dsfd_wfc_vmx_p grant links / ratio FIFOs) at the same
// die pins minus the two link grants (t_lir, f_lor), with the same stage function:
//   inbound  HIDDEN message = header + RXW payload words, written to VM rows RXB + j; a DRAFT (one flit) is dropped;
//            header checks: no last on a header, user < MAXU, per-user position window (pos <= upos <= pos + WIN,
//            upos = last pos + 1, as ot_rom_pkg_ctrl_wfc_tokpipe_upos); payload last only on word RXW - 1.
//   start    after the payload writes, the START doorbell (VM addr 7fff, data {user, token, pos}) and, START_GAP + 1
//            serial edges later, t_ks = {start, user, token, pos} to the stage core (the capture); HEP epoch on the doorbell.
//   done     f_kd = {done, next_token, next_val}: TXW rows TXB.. are read, one row a serial edge (the RD2 pins stay; the
//            second slot is unused: one word a serial edge keeps the stream crossing at 514 b, see TXD for the cost).
//   outbound HIDDEN header (dest HID_DEST, src PKG_ID, len TXW, the job's user / pos / token, idx = next_token + ROW0,
//            val = next_val) and the TXW words, on consecutive fast edges, last on the final word.
// Every action is at a FIXED offset from the event that schedules it, and every would-be wait is a sticky fault:
//   RX:  header parsed at fast edge h -> payload word j written into the RX buffer (64 x 512 macro) on its arrival edge;
//        VM write k (k = 0 .. RXW - 1, then the doorbell) leaves at the k-th fast edge >= h + 2 whose x43 sample index
//        is 0 / 2 / 3, i.e. one VM write per serial edge, back to back (fault: word not yet arrived = calendar gap,
//        header while the previous job's writes are still leaving, doorbell before the message end).
//   VM:  t_swv / t_swd from the x43 output flops; the VM grants f_swr / f_srr are CHECKED (low on an issue = fault),
//        never waited on; f_swa = the VM's sticky error level (fault); a data write while the core runs = fault (the
//        compiler places job j + 1's RX header so its writes start at or after job j's first read: same-edge read
//        sees the VM before the write; each outbound row only on or after the edge its read was launched).
//   DONE (serial edge K, pin flop): read w is launched at serial edge K + 2 + w; its response must be in the f_srq
//        pin flop exactly RLAT serial edges after its launch (fault otherwise); responses cross to the fast side through
//        the fixed-phase ot_s81_vm_x34 (514 b) into one 64 x 512 macro; the DONE marker crosses on the same transfer and
//        the outbound header leaves TXD fast edges after it (TXD derived from RLAT below); word w is read at header
//        edge + w and must have been written before (fault: underflow).
// Clocks: ck = stream (1.2 GHz), ckv = serial (0.9 GHz), phase-locked on the common 3:4 epoch; both resets released
// so that the first rising edges after release are epoch edge 0 (the x34 / x43 startup contract, aa670a062 family).
// Hard structure: a wires-only parent over six hard children, one clock root each (ref_tile leaves), every leaf pin at a
// flop (native pin rule: inputs captured by their first flop, outputs launched from flops):
//   u_t     dsfd_wfc_ss_t     stream core: link pins, parser, RX / TX buffers (2 x 64 x 512), position table (128 x 256),
//                             writer slots, framing, hop endpoint, the kit's fault register
//   u_x43t  dsfd_wfc_ss_x43_t   W 527 stream half of the fixed-phase write transfer (S81 VM per-root CDC leaf)
//   u_x43s  dsfd_wfc_ss_x43_s   W 527 serial half: its output flops ARE the die pins t_swv / t_swd
//   u_s     dsfd_wfc_ss_s     serial core: write-channel copy, START, DONE, reads, return check, HEP table (512 x 64)
//   u_x34s  dsfd_wfc_ss_x34_s   W 514 serial half of the fixed-phase return transfer
//   u_x34t  dsfd_wfc_ss_x34_t   W 514 stream half
// The x43 / x34 halves exchange their banks as related 3:4 parent arcs (the same open epoch-root decision as the VM's).
// Mutants (each must FAIL its gate case): OT_WFCSS_MUT_SWAP (neighbouring outbound words swapped), OT_WFCSS_MUT_TXEARLY (TX
// 8 edges early: underflow fault), OT_WFCSS_MUT_PH1 (writer uses x43 sample index 1: phase fault), OT_WFCSS_MUT_UPOS
// (expected position outside the window: position fault), OT_WFCSS_MUT_GAP0 (START with the doorbell: the core reads
// stale rows),
// OT_WFCSS_MUT_RLAT (response latency check off by one: fault).
// ---------------------------------------------------------------------------------------------------------------
`ifdef DSFD_WFC_STG_STATIC_DIE
module dsfd_wfc_stg
`else
module dsfd_wfc_stg_s
`endif
#(
    parameter integer RLAT = 17,          // serial edges, read launch -> response in the f_srq pin flop (die: + stations)
    parameter integer START_GAP = 4       // serial edges, doorbell launch -> t_ks START launch
) (
    input  wire [0:0]    ck, ckv, rst, rsv,
    input  wire [84:0]   c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,      // engine 7 (hop) endpoint
    input  wire [0:0]    f_liv, input wire [512:0] f_lid,                               // link in  {last, data}
    output wire [0:0]    t_lov, output wire [512:0] t_lod,                              // link out {last, data}
    output wire [0:0]    t_swv, output wire [526:0] t_swd, input wire [0:0] f_swr, input wire [0:0] f_swa,
    output wire [0:0]    t_srv, output wire [30:0] t_srd, input wire [0:0] f_srr,
    input  wire [1025:0] f_srq,
    output wire [52:0]   t_ks, input wire [53:0] f_kd,
    output wire [35:0]   t_hep,
    output wire [3:0]    t_ft
);
    // six hard children, wires only (no parameter on a hardened child: the leaf defaults are the die build, RLAT 17,
    // START_GAP 4; the CDC halves are the S81 VM per-root leaves at W 527 / 514)
    wire xv, wv, ov, sv, sft, xph1, xmark, smark, xf, of;
    wire [526:0] xd, wd; wire [527:0] xb0, xb2, xb3; wire [2:0] xpar, spar;
    wire [513:0] sd, od; wire [514:0] sb0, sb1, sb2;
    dsfd_wfc_ss_t
`ifndef DSFD_WFC_SS_HARD
        #(.RLAT(RLAT))
`endif
        u_t (.ck(ck), .rst(rst), .f_liv(f_liv), .f_lid(f_lid), .t_lov(t_lov), .t_lod(t_lod), .t_xv(xv), .t_xd(xd),
        .f_rv(ov), .f_rd(od), .f_rft(of), .f_sft(sft), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .t_ft(t_ft));
    dsfd_wfc_ss_x43_t
        u_x43t (.t_ck(ck[0]), .t_rst_n(rst[0]), .s_v(xv), .s_d(xd), .b0(xb0), .b2(xb2), .b3(xb3), .bpar(xpar),
        .t_mark(xmark), .ph1_bad(xph1));
    dsfd_wfc_ss_x43_s
        u_x43s (.s_ck(ckv[0]), .s_rst_n(rsv[0]), .b0(xb0), .b2(xb2), .b3(xb3), .bpar(xpar), .t_mark(xmark),
        .ph1_bad(xph1), .o_v(wv), .o_d(wd), .fault(xf));
    assign t_swv = wv; assign t_swd = wd;                     // the VM write channel = the x43 serial output flops
    dsfd_wfc_ss_s
`ifndef DSFD_WFC_SS_HARD
        #(.RLAT(RLAT), .START_GAP(START_GAP))
`endif
        u_s (.ckv(ckv), .rsv(rsv), .f_wv(wv), .f_wd(wd), .f_xft(xf), .t_xsv(sv), .t_xsd(sd),
        .f_swr(f_swr), .f_swa(f_swa), .t_srv(t_srv), .t_srd(t_srd), .f_srr(f_srr),
        .f_srq(f_srq), .t_ks(t_ks), .f_kd(f_kd), .t_hep(t_hep), .t_sft(sft));
    dsfd_wfc_ss_x34_s
        u_x34s (.s_ck(ckv[0]), .s_rst_n(rsv[0]), .s_v(sv), .s_d(sd), .b0(sb0), .b1(sb1), .b2(sb2), .bpar(spar),
        .s_mark(smark));
    dsfd_wfc_ss_x34_t
        u_x34t (.t_ck(ck[0]), .t_rst_n(rst[0]), .b0(sb0), .b1(sb1), .b2(sb2), .bpar(spar), .s_mark(smark),
        .o_v(ov), .o_d(od), .fault(of));
endmodule

// ---------------------------------------------------------------------------------------------------------------
// stream leaf
// ---------------------------------------------------------------------------------------------------------------
module dsfd_wfc_ss_t #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer VWA = 15,
    parameter integer MAXU = 866, parameter integer RXW = 41, parameter integer TXW = 46, parameter integer RXB = 0,
    parameter integer WIN = 6, parameter integer ROW0 = 0, parameter integer PKG_ID = 0, parameter integer HID_DEST = 1,
    parameter integer RLAT = 17
) (
    input  wire [0:0]          ck, rst,
    input  wire [0:0]          f_liv, input wire [FLIT:0] f_lid,
    output reg  [0:0]          t_lov, output reg [FLIT:0] t_lod,
    output reg                 t_xv, output reg [VWA+FLIT-1:0] t_xd,     // to the x43 stream half (from flops)
    input  wire                f_rv, input wire [FLIT+1:0] f_rd,          // from the x34 stream half {kind, v, word}
    input  wire                f_rft,                                     // x34 alignment fault
    input  wire                f_sft,                                     // serial leaf fault level
    input  wire [84:0]         c_cmd, output wire [8:0] c_done, output wire [1:0] c_st,
    output reg  [3:0]          t_ft
);
    localparam integer HDR_DEST = 0, HDR_SRC = 8, HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40,
                       HDR_IDX = HDR_POS + NW, HDR_VAL = HDR_IDX + NW, HDR_TOK = HDR_VAL + 32, HDR_ADDR = HDR_TOK + NW,
                       HDR_USER_HI = HDR_ADDR + 16, UHIW = USER_W - 8, SP = USER_W + 2 * NW;
    localparam [3:0] MT_HIDDEN = 4'd1, MT_DRAFT = 4'd4;
    initial if (RXW > 64 || TXW > 64 || USER_W != 10 || MAXU > 1024 || NW > 32 || FLIT != 512)
        $fatal(1, "dsfd_wfc_ss_t: RXW <= 64, TXW <= 64, USER_W 10, MAXU <= 1024, NW <= 32, FLIT 512");
    // TXD: fast edges from the DONE marker at the x34 output to the outbound header.  Word w reaches the x34 bank
    // RLAT + 2 + w serial edges after the marker = at most (4 (RLAT + 2 + w) + 2) / 3 fast edges at the x34 output,
    // + 1 edge into the macro; it leaves at header + 1 + w.  Words arrive at 0.75 a fast edge and leave at 1, so the
    // LAST word (w = TXW - 1) bounds the header edge; + 3 edges of margin (the gate removes them on every phase).
`ifdef OT_WFCSS_TXD_ADJ
    localparam integer TXD = (4 * (RLAT + 1 + TXW) + 2) / 3 - (TXW - 1) + 3 - `OT_WFCSS_TXD_ADJ;   // margin sweep (bench only)
`else
    localparam integer TXD = (4 * (RLAT + 1 + TXW) + 2) / 3 - (TXW - 1) + 3;
`endif
    wire clk = ck[0], rn = rst[0];
    // epoch phase: tp = index of the last edge (3 at reset: the first edge after release is epoch edge 0)
    reg [1:0] tp;
    always @(posedge clk or negedge rn) if (!rn) tp <= 2'd3; else tp <= tp + 2'd1;
    // a word issued at this edge (SRAM read) is registered at t_xd on the next edge and sampled by the x43 stream half
    // one edge later, at sample index tp + 3: legal unless that index is 1
`ifdef OT_WFCSS_MUT_PH1
    wire nxt_ok = tp != 2'd1;                 // MUTANT: the writer presents words for sample index 1
`else
    wire nxt_ok = tp != 2'd2;
`endif
    // ---------------------------------------------------------------- link-in pin flops and the parser
    reg liv_q; reg [FLIT:0] lid_q;
    always @(posedge clk or negedge rn) if (!rn) liv_q <= 1'b0; else liv_q <= f_liv[0];
    always @(posedge clk) lid_q <= f_lid;
    wire [FLIT-1:0] ld = lid_q[FLIT-1:0]; wire ll = lid_q[FLIT];
    wire [3:0] in_type = ld[HDR_TYPE +: 4];
    wire [USER_W-1:0] in_user = {ld[HDR_USER_HI +: UHIW], ld[HDR_USER +: 8]};
    wire [NW-1:0] in_pos = ld[HDR_POS +: NW], in_tok = ld[HDR_TOK +: NW];
    reg rx_in; reg [6:0] rx_j, rx_cnt;
    wire hdr = liv_q && !rx_in, hid = hdr && in_type == MT_HIDDEN, pay = liv_q && rx_in;
    reg [USER_W-1:0] h_user; reg [NW-1:0] h_pos, h_tok;
    // ---------------------------------------------------------------- VM writer (fixed slots, x43 stream banks)
    reg wact, warm; reg [6:0] wk; reg xv, xdb; reg [VWA-1:0] xa;
    wire w_iss = wact && warm && nxt_ok;
    wire w_db = wk == RXW[6:0];
    wire [FLIT-1:0] rx_rd;
    ot_sram_1r1w_64x512_m1_r2c2 u_rxb (.clk(clk), .r_ce_in(w_iss && !w_db), .r_addr_in(wk[5:0]), .rd_out(rx_rd),
        .w_ce_in(pay), .w_addr_in(rx_j[5:0]), .wd_in(ld), .w_mask_in({FLIT{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    wire [VWA+FLIT-1:0] x_d = {xa, xdb ? FLIT'({h_user, h_tok, h_pos}) : rx_rd};
    always @(posedge clk) t_xd <= x_d;
    // ---------------------------------------------------------------- per-user expected position (128 x 256 macro)
    reg [MAXU-1:0] uval; reg uc_v, uc_val; reg [2:0] uc_s; reg [6:0] uc_row; reg [NW-1:0] uc_pos; reg [USER_W-1:0] uc_u;
    wire [255:0] up_q;
    wire [NW-1:0] up_cur = uc_val ? up_q[{uc_s, 5'd0} +: NW] : {NW{1'b0}};
`ifdef OT_WFCSS_MUT_UPOS
    wire [NW-1:0] up_new = uc_pos + WIN + 2;  // MUTANT: wrong expected position (outside the window)
`else
    wire [NW-1:0] up_new = uc_pos + 1'b1;
`endif
    wire pos_bad = (uc_pos > up_cur) || ({1'b0, uc_pos} + WIN < {1'b0, up_cur});
    wire hid_ok = hid && !ll && in_user < MAXU;
    ot_sram_1r1w_128x256_m1_r2c2 u_up (.clk(clk), .r_ce_in(hid_ok), .r_addr_in(in_user[9:3]), .rd_out(up_q),
        .w_ce_in(uc_v), .w_addr_in(uc_row), .wd_in({8{11'd0, up_new}}), .w_mask_in(256'({NW{1'b1}}) << {uc_s, 5'd0}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // ---------------------------------------------------------------- job records (RX header -> TX header), 2 deep
    reg [SP-1:0] jq [0:1]; reg [1:0] jq_w, jq_r;
    wire jq_n0 = jq_w == jq_r;
    // ---------------------------------------------------------------- return path: x34 reader, TX buffers, framing
    reg ro_v, x34f; reg [FLIT+1:0] ro_d;                      // pin flops of the x34 stream half's outputs
    always @(posedge clk or negedge rn) if (!rn) begin ro_v <= 1'b0; x34f <= 1'b0; end else begin ro_v <= f_rv; x34f <= f_rft; end
    always @(posedge clk) ro_d <= f_rd;
    wire r_done = ro_v && ro_d[FLIT+1], r_dat = ro_v && !ro_d[FLIT+1];
    wire r_v0 = ro_d[FLIT];
    reg [6:0] pi; reg [63:0] got; reg tx_arm, rd_go, q_v, q_last; reg [6:0] txc, rk;
    reg [NW-1:0] r_idx; reg [31:0] r_val;
    wire [FLIT-1:0] tq;
    wire t0 = tx_arm && txc == 7'd0;          // header edge
    wire rd_now = t0 || rd_go;                // word rk is read at this edge
`ifdef OT_WFCSS_MUT_SWAP
    wire [5:0] rk_a = rk[5:0] ^ 6'd1;         // MUTANT: neighbouring words swapped
`else
    wire [5:0] rk_a = rk[5:0];
`endif
    ot_sram_1r1w_64x512_m1_r2c2 u_txb (.clk(clk), .r_ce_in(rd_now), .r_addr_in(rk_a), .rd_out(tq),
        .w_ce_in(r_dat && r_v0), .w_addr_in(pi[5:0]), .wd_in(ro_d[FLIT-1:0]), .w_mask_in({FLIT{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    wire [SP-1:0] jh = jq[jq_r[0]];           // {user, token, pos} of the oldest job
    wire [FLIT-1:0] hdr_o = FLIT'({jh[2*NW +: USER_W] >> 8}) << HDR_USER_HI | FLIT'(jh[NW +: NW]) << HDR_TOK |
                            FLIT'(r_val) << HDR_VAL | FLIT'(r_idx) << HDR_IDX | FLIT'(jh[NW-1:0]) << HDR_POS |
                            FLIT'(jh[2*NW +: 8]) << HDR_USER | FLIT'(TXW[7:0]) << HDR_LEN |
                            FLIT'(MT_HIDDEN) << HDR_TYPE | FLIT'(PKG_ID[7:0]) << HDR_SRC | FLIT'(HID_DEST[7:0]);
`ifdef OT_WFCSS_MUT_TXEARLY
    localparam integer TXD_E = TXD - 8;       // MUTANT: the header leaves 8 edges early
`else
    localparam integer TXD_E = TXD;
`endif
    // ---------------------------------------------------------------- sequencing and faults
    reg f_proto, f_lnk, f_vmx, sft_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin
            rx_in <= 1'b0; rx_j <= 0; rx_cnt <= 0; wact <= 1'b0; warm <= 1'b0; wk <= 0; xv <= 1'b0; xdb <= 1'b0; t_xv <= 1'b0;
            uval <= {MAXU{1'b0}}; uc_v <= 1'b0; jq_w <= 0; jq_r <= 0;
            pi <= 0; got <= 0; tx_arm <= 1'b0; rd_go <= 1'b0; q_v <= 1'b0; txc <= 0; rk <= 0;
            t_lov <= 1'b0; f_proto <= 1'b0; f_lnk <= 1'b0; f_vmx <= 1'b0; sft_q <= 1'b0; t_ft <= 4'd0;
        end else begin
            // ---- writer: one VM write per legal slot
            xv <= w_iss; t_xv <= xv;
            if (w_iss) begin
                xdb <= w_db; xa <= w_db ? {VWA{1'b1}} : VWA'(RXB + wk);
                if (!w_db && rx_cnt <= wk) f_lnk <= 1'b1;            // the word has not arrived (calendar gap)
                if (w_db && rx_in) f_lnk <= 1'b1;                    // doorbell before the message end
                wk <= wk + 1'b1;
                if (w_db) wact <= 1'b0;
            end
            if (wact) warm <= 1'b1;
            // ---- parser
            if (hdr) begin
                if (in_type == MT_HIDDEN) begin
                    if (ll || in_user >= MAXU) f_proto <= 1'b1;
                    if (wact) f_lnk <= 1'b1;                         // previous job's writes still leaving
                    if (jq_w - jq_r == 2'd2) f_lnk <= 1'b1;          // more than two jobs in flight
                    rx_in <= 1'b1; rx_j <= 0; rx_cnt <= 0; wact <= 1'b1; warm <= 1'b0; wk <= 0;
                    h_user <= in_user; h_pos <= in_pos; h_tok <= in_tok;
                    jq[jq_w[0]] <= {in_user, in_tok, in_pos}; jq_w <= jq_w + 1'b1;
                end else if (in_type == MT_DRAFT) begin
                    if (!ll) f_lnk <= 1'b1;                          // a DRAFT is one flit (dropped: no t_dw sink)
                end else f_proto <= 1'b1;
            end
            if (pay) begin
                rx_j <= rx_j + 1'b1; rx_cnt <= rx_cnt + 1'b1;
                if (ll != (rx_j == RXW - 1)) f_proto <= 1'b1;
                if (rx_j == RXW - 1) rx_in <= 1'b0;
            end
            // ---- position window: read at h, check / write at h + 1
            uc_v <= hid_ok;
            if (hid_ok) begin uc_s <= in_user[2:0]; uc_row <= in_user[9:3]; uc_pos <= in_pos; uc_u <= in_user; uc_val <= uval[in_user]; end
            if (uc_v) begin uval[uc_u] <= 1'b1; if (pos_bad) f_proto <= 1'b1; end
            // ---- return: DONE marker, response pairs into the TX macros
            if (r_done) begin
                if (tx_arm || rd_go || q_v || jq_n0) f_vmx <= 1'b1;    // DONE while the previous TX leaves / no job
                tx_arm <= 1'b1; txc <= 7'(TXD_E); pi <= 0; got <= 0;
                r_idx <= ro_d[32 +: NW] + ROW0[NW-1:0]; r_val <= ro_d[31:0];
            end
            if (r_dat) begin
                if (!tx_arm && !rd_go) f_vmx <= 1'b1;                // a response outside a job's read window
                if (!r_v0) f_vmx <= 1'b1;
                pi <= pi + 1'b1;
                got[pi[5:0]] <= r_v0;
            end
            // ---- TX: header at t0, word rk read at t0 + rk, launched one edge later
            t_lov <= 1'b0;
            if (tx_arm && txc != 7'd0) txc <= txc - 1'b1;
            if (t0) begin
                tx_arm <= 1'b0;
                t_lov <= 1'b1; t_lod <= {1'b0, hdr_o}; jq_r <= jq_r + 1'b1;
            end
            if (rd_now) begin
                if (!got[rk[5:0]]) f_vmx <= 1'b1;                         // underflow: the word is not in its macro
                if (rk == TXW - 1) begin rk <= 0; rd_go <= 1'b0; end else begin rk <= rk + 1'b1; rd_go <= 1'b1; end
            end
            q_v <= rd_now; q_last <= rk == TXW - 1;
            if (q_v) begin t_lov <= 1'b1; t_lod <= {q_last, tq}; end
            // ---- faults
            if (x34f) f_vmx <= 1'b1;
            sft_q <= f_sft;
            t_ft <= {f_proto, f_lnk, 1'b0, f_vmx || sft_q};
        end
    dsfd_wfc_hop_ep u_hop (.ck(ck), .rst(rst), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st), .f_lov(t_lov), .f_lol(t_lod[FLIT]));
endmodule

// ---------------------------------------------------------------------------------------------------------------
// serial leaf
// ---------------------------------------------------------------------------------------------------------------
module dsfd_wfc_ss_s #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10, parameter integer VWA = 15,
    parameter integer TXW = 46, parameter integer TXB = 0, parameter integer RLAT = 17, parameter integer START_GAP = 4
) (
    input  wire [0:0]          ckv, rsv,
    input  wire                f_wv, input wire [VWA+FLIT-1:0] f_wd,     // the VM write channel (x43 serial half flops)
    input  wire                f_xft,                                     // x43 alignment / schedule fault
    output reg                 t_xsv, output reg [FLIT+1:0] t_xsd,       // to the x34 serial half {kind, v, word}
    input  wire [0:0]          f_swr, f_swa,
    output reg  [0:0]          t_srv, output reg [2*VWA:0] t_srd, input wire [0:0] f_srr,
    input  wire [2*FLIT+1:0]   f_srq,
    output reg  [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    output wire [USER_W+NW+4:0] t_hep,
    output reg                 t_sft
);
    localparam integer SP = USER_W + 2 * NW;
    initial if (RLAT < 4 || START_GAP < 1 || TXW > 128) $fatal(1, "dsfd_wfc_ss_s: RLAT >= 4, START_GAP >= 1, TXW <= 128");
    wire clk = ckv[0], rn = rsv[0];
    // ---------------------------------------------------------------- write channel copy (pin flops): the write launched
    // in the previous cycle (address and START payload only); every check against it uses the previous-edge state
    reg wv, x43f; reg [VWA-1:0] wa; reg [SP-1:0] wp;
    always @(posedge clk or negedge rn) if (!rn) begin wv <= 1'b0; x43f <= 1'b0; end else begin wv <= f_wv; x43f <= f_xft; end
    always @(posedge clk) begin wa <= f_wd[FLIT +: VWA]; wp <= f_wd[SP-1:0]; end
    wire db = wv && (&wa), dw = wv && !(&wa);
    // ---------------------------------------------------------------- pin flops
    reg swr_q, swa_q, srr_q, rv_q, rv1_q, kd_v; reg [FLIT-1:0] srq_q; reg [NW+31:0] kd_d;   // f_srq[2*FLIT:FLIT+1]: unused RD2 slot
    always @(posedge clk or negedge rn)
        if (!rn) begin swr_q <= 1'b0; swa_q <= 1'b0; srr_q <= 1'b0; rv_q <= 1'b0; rv1_q <= 1'b0; kd_v <= 1'b0; end
        else begin
            swr_q <= f_swr[0]; swa_q <= f_swa[0]; srr_q <= f_srr[0];
            rv_q <= f_srq[FLIT]; rv1_q <= f_srq[2*FLIT+1]; kd_v <= f_kd[NW+32];
        end
    always @(posedge clk) begin srq_q <= f_srq[FLIT-1:0]; kd_d <= f_kd[NW+31:0]; end
    // ---------------------------------------------------------------- return transfer (x34 banks): DONE marker or word
    always @(posedge clk or negedge rn) if (!rn) t_xsv <= 1'b0; else t_xsv <= kd_v || rv_q;
    always @(posedge clk) t_xsd <= kd_v ? {1'b1, (FLIT+1-NW-32)'(0), kd_d} : {1'b0, rv_q, srq_q[FLIT-1:0]};
    // ---------------------------------------------------------------- START, run window, reads, return check
    localparam integer GAP = START_GAP;
`ifdef OT_WFCSS_MUT_RLAT
    localparam integer RCHK = RLAT + 1;       // MUTANT: the return check expects one edge late
`else
    localparam integer RCHK = RLAT;
`endif
    reg st_p, run, rd_act; reg [7:0] st_c; reg [SP-1:0] st_d; reg [6:0] ri;
    reg [RCHK:0] ex0;                         // launch history: ex0[k] = a read launched k edges before this edge's value
    reg [USER_W+NW:0] hks; reg flt; reg run_d, st_p_d; reg [6:0] ri_d;   // previous-edge state (the write copy is one edge late)
    wire [VWA-1:0] a0 = VWA'(TXB) + VWA'(ri);
    always @(posedge clk or negedge rn)
        if (!rn) begin
            st_p <= 1'b0; run <= 1'b0; rd_act <= 1'b0; ri <= 7'(TXW); ex0 <= 0; t_srv <= 1'b0; t_ks <= 0;
            hks <= 0; flt <= 1'b0; t_sft <= 1'b0; st_c <= 0; run_d <= 1'b0; st_p_d <= 1'b0; ri_d <= 7'(TXW);
        end else begin
            // doorbell -> START after GAP edges; HEP epoch on the doorbell
            t_ks[SP] <= 1'b0; hks[USER_W+NW] <= 1'b0;
            if (db) begin
                if (st_p || run) flt <= 1'b1;
`ifdef OT_WFCSS_MUT_GAP0
                run <= 1'b1; t_ks <= {1'b1, wp};                   // MUTANT: START with the doorbell (no gap)
`else
                st_p <= 1'b1; st_c <= 8'(GAP - 1); st_d <= wp;
`endif
                hks <= {1'b1, wp[2*NW +: USER_W], wp[NW-1:0]};
            end
            if (st_p) begin
                if (st_c == 0) begin st_p <= 1'b0; run <= 1'b1; t_ks <= {1'b1, st_d}; end
                else st_c <= st_c - 1'b1;
            end
            run_d <= run; st_p_d <= st_p; ri_d <= ri;
            if (dw && (run_d || st_p_d)) flt <= 1'b1;               // VM rows written while the core owns them
            // write-after-read: a row of the outbound range may be rewritten only on or after the edge its read
            // was launched (same edge: the VM's read sees the row before the write); ri = rows launched so far
            if (dw && wa >= VWA'(TXB) + VWA'(ri_d) && wa < VWA'(TXB + TXW)) flt <= 1'b1;
            if (wv && !swr_q) flt <= 1'b1;                          // write launched without the VM's grant level
            // DONE -> read pairs
            if (kd_v) begin
                if (!run || rd_act) flt <= 1'b1;
                run <= 1'b0; rd_act <= 1'b1; ri <= 0;
                if (rv_q) flt <= 1'b1;                              // marker and a response on one edge
            end
            t_srv <= rd_act;
            if (rd_act) begin
                t_srd <= {1'b0, {VWA{1'b0}}, a0};          // one row a serial edge (RD2 slot 1 unused)
                if (!srr_q) flt <= 1'b1;
                ri <= ri + 1'b1;
                if (ri == TXW - 1) rd_act <= 1'b0;
            end
            ex0 <= {ex0[RCHK-1:0], rd_act};
            if (rv_q != ex0[RCHK] || rv1_q) flt <= 1'b1;            // response not exactly RLAT after its launch
            if (swa_q) flt <= 1'b1;                                  // VM error level
            if (x43f) flt <= 1'b1;
            t_sft <= flt;
        end
    dsfd_wfc_hep_t u_hep (.ckv(ckv), .rsv(rsv), .f_hks(hks), .t_hep(t_hep));
endmodule
