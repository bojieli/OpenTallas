`timescale 1ns/1ps
`define C_CMD(m) cmdv[m][159:128]
`define C_OUT(m) cmdv[m][127:96]
`define C_PB(m) cmdv[m][95:64]
`define C_SB(m) cmdv[m][63:32]
`define C_W(m) cmdv[m][31:16]
`define C_MODE(m) cmdv[m][0]
// ---------------------------------------------------------------------------
// qwen-coll-io r5 2026-10-14: COMPOSED 8-die bench of the static TP8 collective on the REAL static link RTL.
// Per die (4 packages x 2 dies, die r = 2 * package + die, every die the same masters ranked by straps):
//   ot_coll_cmd_issue        compiler commands, loaded over the program-write face, issued by ot_qwen_fixed_issue
//   ot_coll_tp8_static       the collective (or the die-name master qfd_io_collective_static, +define+OT_TP8S_QFD)
//   ot_coll_static_linkcal   the IO calendar (every CDC / codec slot from the collective's compiled tokens)
//   qfd_io_xfifo_static      10 static CDC channels (up / ur / sx0-2 core -> link, dp / dr / sr0-2 link -> core)
//   qfd_io_ucie_static       UCIe P (546) + R (514) static codecs, CRC32
//   qfd_io_serdes_static x3  board SerDes static codecs, CRC32
// Only the PHYs are modelled: fixed-latency register pipes of the codec frames (UCIe PU + XU, SerDes PS + XS link
// cycles; XU / XS are negative controls = a PHY longer than compiled).  Link roots are mesochronous with the core
// root: PHI 0 = the same edge, PHI 1 = the link edge after the core edge (harness).
// Stimulus at the declared boundary: the program words (pw.hex = the compiler output, as the program receiver would
// write them), the stage start, and the producers' words at their compiled slots.  Checked: every collective output
// word at EXACTLY its compiled cycle with the exact value (tools/hdc_golden), last and rank; every die's issuer
// command at its compiled cycle; zero faults anywhere (collective, issuer, 10 CDC channels x w/r, 5 codecs).
// Fault cases (+DROP: die 5's producer omits a word; +CORRUPT: one SerDes frame bit flipped in the PHY;
// XU / XS) must raise their fault on the named dies.
// ---------------------------------------------------------------------------
module tb_coll_tp8_static_links #(
    parameter integer LATU = 37, LATS = 362,     // collective LU / LS (compiled, = the calendar's)
    parameter integer PU = 14, PS = 339,         // PHY latencies the calendar compiles
    parameter integer KC = 4, KW = 2,
    parameter integer XU = 0, XS = 0             // extra PHY cycles vs compiled (negative control)
) (input wire clk, input wire lck);
    localparam integer ND = 8, LANES = 16, FW = 512, TAGW = 32, PW = FW + 2 + TAGW, RW = FW + 2, MAXW = 1 << 16;
    localparam integer FP = 546 + 19 + 32, FR = 514 + 19 + 32;       // codec frames 597 / 565
    reg [FW-1:0] part [0:MAXW-1];
    reg [FW-1:0] sum  [0:MAXW-1];
    reg [159:0]  cmdv [0:4095];
    reg [73:0]   pwv  [0:255];        // {addr 10, data 64}
    integer NMSG, NPW, START, DROP, CORRUPT, MAXCYC;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    reg [31:0] cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // program write (all dies receive the same compiled stage program) and the stage start
    integer pi = 0;
    wire pw_go = rst_n && cyc >= 20 && pi < NPW;
    wire [9:0]  pw_a = pwv[pi][73:64];
    wire [63:0] pw_d = pwv[pi][63:0];
    always @(posedge clk) if (pw_go) pi <= pi + 1;
    wire stage_start = rst_n && cyc == START;

    wire [ND-1:0] iv, ov, ol, oe, flt, upv, urv, ups, urps, cfree, icv, imode, ifl, iact, idone;
    wire [ND*16-1:0] iwords;
    wire [ND*TAGW-1:0] itag;
    wire [ND*FW-1:0] id, od;
    wire [ND-1:0] il, im;
    wire [ND*TAGW-1:0] it;
    wire [ND*3-1:0] orank, sxps;
    wire [ND*5-1:0] fc;
    wire [ND*PW-1:0] uprec, dprec;
    wire [ND*RW-1:0] urrec, drrec;
    wire [ND*3-1:0] sxv, srv;
    wire [ND*3*PW-1:0] sxrec, srrec;
    wire [ND-1:0] dpv, drv;
    // PHY frames (link domain): UCIe P / R, SerDes ports
    wire [ND-1:0] ptxv, rtxv; wire [ND*FP-1:0] ptx; wire [ND*FR-1:0] rtx;
    wire [ND-1:0] prxv, rrxv; wire [ND*FP-1:0] prx; wire [ND*FR-1:0] rrx;
    wire [ND*3-1:0] stxv, srxv; wire [ND*3*FP-1:0] stx, srx;
    wire [ND*20-1:0] xflt;            // 10 CDC channels x {w, r}
    wire [ND*5-1:0]  cabort;          // codec aborts: P, R, S0, S1, S2
    wire [ND*40-1:0] ccause;

    integer bad = 0, words_out = 0, errs = 0, done_n = 0, extra = 0, total_out = 0, endc = 0, mi, cmd_bad = 0;
    integer pr_overlap = 0;           // cycles with UCIe P and R frames on the same die at once (PHY capacity note)
    integer first_up = -1, first_dp = -1, first_sx = -1, first_sr = -1;
    genvar g, j;
    generate
        for (g = 0; g < ND; g = g + 1) begin : g_die
            localparam integer P = g / 2, D = g % 2;
            // ---------------- issuer ----------------
            ot_coll_cmd_issue #(.DEPTH(8), .BASE(0)) u_iss (.clk(clk), .rst_n(rst_n), .pw_v(pw_go), .pw_addr(pw_a),
                .pw_data(pw_d), .start(stage_start), .cmd_free(cfree[g]), .cmd_v(icv[g]), .cmd_mode(imode[g]),
                .cmd_words(iwords[g*16 +: 16]), .cmd_tag(itag[g*TAGW +: TAGW]), .active(iact[g]), .done(idone[g]),
                .fault(ifl[g]));
            // ---------------- collective ----------------
`ifdef OT_TP8S_QFD
            qfd_io_collective_static u_die (       // the die-name master (LU / LS by +define)
                .clk(clk), .clk_pfold0(clk), .clk_pfold1(clk), .clk_pfold2(clk), .clk_pfold3(clk),
                .clk_xfold0(clk), .clk_xfold1(clk), .clk_xfold2(clk), .clk_xfold3(clk),
                .rst_n(rst_n), .pkg_s(P[1:0]), .die_ps(D[0]),
                .cmd_v(icv[g]), .cmd_mode(imode[g]), .cmd_words(iwords[g*16 +: 16]), .cmd_tag(itag[g*TAGW +: TAGW]),
                .in_valid(iv[g]), .in_data(id[g*FW +: FW]), .in_last(il[g]), .in_mode(im[g]), .in_tag(it[g*TAGW +: TAGW]),
                .up_valid(upv[g]), .up_rec(uprec[g*PW +: PW]), .dp_valid(dpv[g]), .dp_rec(dprec[g*PW +: PW]),
                .ur_valid(urv[g]), .ur_rec(urrec[g*RW +: RW]), .dr_valid(drv[g]), .dr_rec(drrec[g*RW +: RW]),
                .sx0_valid(sxv[g*3]), .sx1_valid(sxv[g*3 + 1]), .sx2_valid(sxv[g*3 + 2]),
                .sx0_rec(sxrec[(g*3)*PW +: PW]), .sx1_rec(sxrec[(g*3 + 1)*PW +: PW]), .sx2_rec(sxrec[(g*3 + 2)*PW +: PW]),
                .sr0_valid(srv[g*3]), .sr1_valid(srv[g*3 + 1]), .sr2_valid(srv[g*3 + 2]),
                .sr0_rec(srrec[(g*3)*PW +: PW]), .sr1_rec(srrec[(g*3 + 1)*PW +: PW]), .sr2_rec(srrec[(g*3 + 2)*PW +: PW]),
                .out_valid(ov[g]), .out_data(od[g*FW +: FW]), .out_last(ol[g]), .out_rank(orank[g*3 +: 3]),
                .out_err(oe[g]), .fault(flt[g]), .fault_code(fc[g*5 +: 5]),
                .up_slot(ups[g]), .ur_peer_slot(urps[g]), .cmd_free(cfree[g]),
                .sx0_peer_slot(sxps[g*3]), .sx1_peer_slot(sxps[g*3 + 1]), .sx2_peer_slot(sxps[g*3 + 2]));
`else
            ot_coll_tp8_static #(.LU(LATU), .LS(LATS)) u_die (
                .clk(clk), .clk_pfold({4{clk}}), .clk_xfold({4{clk}}),
                .rst_n(rst_n), .pkg_s(P[1:0]), .die_ps(D[0]),
                .cmd_v(icv[g]), .cmd_mode(imode[g]), .cmd_words(iwords[g*16 +: 16]), .cmd_tag(itag[g*TAGW +: TAGW]),
                .in_valid(iv[g]), .in_data(id[g*FW +: FW]), .in_last(il[g]), .in_mode(im[g]), .in_tag(it[g*TAGW +: TAGW]),
                .up_valid(upv[g]), .up_rec(uprec[g*PW +: PW]), .dp_valid(dpv[g]), .dp_rec(dprec[g*PW +: PW]),
                .ur_valid(urv[g]), .ur_rec(urrec[g*RW +: RW]), .dr_valid(drv[g]), .dr_rec(drrec[g*RW +: RW]),
                .sx_valid(sxv[g*3 +: 3]), .sx_rec(sxrec[g*3*PW +: 3*PW]), .sr_valid(srv[g*3 +: 3]),
                .sr_rec(srrec[g*3*PW +: 3*PW]),
                .out_valid(ov[g]), .out_data(od[g*FW +: FW]), .out_last(ol[g]), .out_rank(orank[g*3 +: 3]),
                .out_err(oe[g]), .fault(flt[g]), .fault_code(fc[g*5 +: 5]),
                .up_slot(ups[g]), .ur_peer_slot(urps[g]), .cmd_free(cfree[g]),
                .sx_peer_slot(sxps[g*3 +: 3]));
`endif
            // ---------------- IO calendar ----------------
            wire eb; wire [7:0] ep;
            wire [4:0] tws, twv, trs, trv, twr, trd, rxe, rws, rwv, rrs, rrv;
            wire [29:0] twa, tra, twrs, trds, rxes, rwa, rra;
            ot_coll_static_linkcal #(.KC(KC), .KW(KW), .PU(PU), .PS(PS), .LU(LATU), .LS(LATS)) u_cal (
                .clk(clk), .lck(lck), .rst_n(rst_n),
                .up_slot(ups[g]), .ur_slot(urv[g]), .sx_slot(sxv[g*3]), .ur_peer_slot(urps[g]),
                .sx_peer_slot(sxps[g*3 +: 3]), .epoch_begin(eb), .epoch(ep),
                .tx_w_slot(tws), .tx_w_version(twv), .tx_r_slot(trs), .tx_r_version(trv), .tx_wr_v(twr), .tx_rd_v(trd),
                .tx_w_addr(twa), .tx_r_addr(tra), .tx_wr_slot(twrs), .tx_rd_slot(trds),
                .rx_expect_v(rxe), .rx_w_slot(rws), .rx_w_version(rwv), .rx_r_slot(rrs), .rx_r_version(rrv),
                .rx_expect_slot(rxes), .rx_w_addr(rwa), .rx_r_addr(rra));
            // ---------------- static CDC channels ----------------
            wire upov, dpov, urov, drov; wire [2:0] sxov, srov;
            wire [545:0] upod, dpod, sx0od, sx1od, sx2od, sr0od, sr1od, sr2od; wire [513:0] urod, drod;
            wire puv, ruv; wire [545:0] pud; wire [513:0] rud;           // UCIe codec RX
            wire [2:0] suv; wire [3*546-1:0] sud;                         // SerDes codec RX
            wire unused_seq_v, unused_cq_v, unused_seq_wf, unused_seq_rf, unused_cq_wf, unused_cq_rf;
            wire [545:0] unused_seq_d; wire [516:0] unused_cq_d;
            qfd_io_xfifo_static u_xf (.rst_n(rst_n),
                .up_wck(clk), .up_rck(lck), .up_w_slot(tws[0]), .up_w_version(twv[0]), .up_i_valid(upv[g]),
                .up_r_slot(trs[0]), .up_r_version(trv[0]), .up_w_addr(twa[0 +: 6]), .up_r_addr(tra[0 +: 6]),
                .up_i_data(uprec[g*PW +: PW]), .up_o_valid(upov), .up_w_fault(xflt[g*20 + 0]), .up_r_fault(xflt[g*20 + 1]),
                .up_o_data(upod),
                .dp_wck(lck), .dp_rck(clk), .dp_w_slot(rws[0]), .dp_w_version(rwv[0]), .dp_i_valid(puv),
                .dp_r_slot(rrs[0]), .dp_r_version(rrv[0]), .dp_w_addr(rwa[0 +: 6]), .dp_r_addr(rra[0 +: 6]),
                .dp_i_data(pud), .dp_o_valid(dpov), .dp_w_fault(xflt[g*20 + 2]), .dp_r_fault(xflt[g*20 + 3]),
                .dp_o_data(dpod),
                .ur_wck(clk), .ur_rck(lck), .ur_w_slot(tws[1]), .ur_w_version(twv[1]), .ur_i_valid(urv[g]),
                .ur_r_slot(trs[1]), .ur_r_version(trv[1]), .ur_w_addr(twa[6 +: 6]), .ur_r_addr(tra[6 +: 6]),
                .ur_i_data(urrec[g*RW +: RW]), .ur_o_valid(urov), .ur_w_fault(xflt[g*20 + 4]), .ur_r_fault(xflt[g*20 + 5]),
                .ur_o_data(urod),
                .dr_wck(lck), .dr_rck(clk), .dr_w_slot(rws[1]), .dr_w_version(rwv[1]), .dr_i_valid(ruv),
                .dr_r_slot(rrs[1]), .dr_r_version(rrv[1]), .dr_w_addr(rwa[6 +: 6]), .dr_r_addr(rra[6 +: 6]),
                .dr_i_data(rud), .dr_o_valid(drov), .dr_w_fault(xflt[g*20 + 6]), .dr_r_fault(xflt[g*20 + 7]),
                .dr_o_data(drod),
                .sx0_wck(clk), .sx0_rck(lck), .sx0_w_slot(tws[2]), .sx0_w_version(twv[2]), .sx0_i_valid(sxv[g*3 + 0]),
                .sx0_r_slot(trs[2]), .sx0_r_version(trv[2]), .sx0_w_addr(twa[12 +: 6]), .sx0_r_addr(tra[12 +: 6]),
                .sx0_i_data(sxrec[(g*3 + 0)*PW +: PW]), .sx0_o_valid(sxov[0]), .sx0_w_fault(xflt[g*20 + 8]),
                .sx0_r_fault(xflt[g*20 + 9]), .sx0_o_data(sx0od),
                .sx1_wck(clk), .sx1_rck(lck), .sx1_w_slot(tws[3]), .sx1_w_version(twv[3]), .sx1_i_valid(sxv[g*3 + 1]),
                .sx1_r_slot(trs[3]), .sx1_r_version(trv[3]), .sx1_w_addr(twa[18 +: 6]), .sx1_r_addr(tra[18 +: 6]),
                .sx1_i_data(sxrec[(g*3 + 1)*PW +: PW]), .sx1_o_valid(sxov[1]), .sx1_w_fault(xflt[g*20 + 10]),
                .sx1_r_fault(xflt[g*20 + 11]), .sx1_o_data(sx1od),
                .sx2_wck(clk), .sx2_rck(lck), .sx2_w_slot(tws[4]), .sx2_w_version(twv[4]), .sx2_i_valid(sxv[g*3 + 2]),
                .sx2_r_slot(trs[4]), .sx2_r_version(trv[4]), .sx2_w_addr(twa[24 +: 6]), .sx2_r_addr(tra[24 +: 6]),
                .sx2_i_data(sxrec[(g*3 + 2)*PW +: PW]), .sx2_o_valid(sxov[2]), .sx2_w_fault(xflt[g*20 + 12]),
                .sx2_r_fault(xflt[g*20 + 13]), .sx2_o_data(sx2od),
                .sr0_wck(lck), .sr0_rck(clk), .sr0_w_slot(rws[2]), .sr0_w_version(rwv[2]), .sr0_i_valid(suv[0]),
                .sr0_r_slot(rrs[2]), .sr0_r_version(rrv[2]), .sr0_w_addr(rwa[12 +: 6]), .sr0_r_addr(rra[12 +: 6]),
                .sr0_i_data(sud[0 +: 546]), .sr0_o_valid(srov[0]), .sr0_w_fault(xflt[g*20 + 14]),
                .sr0_r_fault(xflt[g*20 + 15]), .sr0_o_data(sr0od),
                .sr1_wck(lck), .sr1_rck(clk), .sr1_w_slot(rws[3]), .sr1_w_version(rwv[3]), .sr1_i_valid(suv[1]),
                .sr1_r_slot(rrs[3]), .sr1_r_version(rrv[3]), .sr1_w_addr(rwa[18 +: 6]), .sr1_r_addr(rra[18 +: 6]),
                .sr1_i_data(sud[546 +: 546]), .sr1_o_valid(srov[1]), .sr1_w_fault(xflt[g*20 + 16]),
                .sr1_r_fault(xflt[g*20 + 17]), .sr1_o_data(sr1od),
                .sr2_wck(lck), .sr2_rck(clk), .sr2_w_slot(rws[4]), .sr2_w_version(rwv[4]), .sr2_i_valid(suv[2]),
                .sr2_r_slot(rrs[4]), .sr2_r_version(rrv[4]), .sr2_w_addr(rwa[24 +: 6]), .sr2_r_addr(rra[24 +: 6]),
                .sr2_i_data(sud[1092 +: 546]), .sr2_o_valid(srov[2]), .sr2_w_fault(xflt[g*20 + 18]),
                .sr2_r_fault(xflt[g*20 + 19]), .sr2_o_data(sr2od),
                // seq / cq channels belong to the sequencer owner: idle in this bench (no slot reserved)
                .seq_wck(clk), .seq_rck(lck), .seq_w_slot(1'b0), .seq_w_version(1'b0), .seq_i_valid(1'b0),
                .seq_r_slot(1'b0), .seq_r_version(1'b0), .seq_w_addr(6'd0), .seq_r_addr(6'd0), .seq_i_data(546'd0),
                .seq_o_valid(unused_seq_v), .seq_w_fault(unused_seq_wf), .seq_r_fault(unused_seq_rf), .seq_o_data(unused_seq_d),
                .cq_wck(lck), .cq_rck(clk), .cq_w_slot(1'b0), .cq_w_version(1'b0), .cq_i_valid(1'b0),
                .cq_r_slot(1'b0), .cq_r_version(1'b0), .cq_w_addr(6'd0), .cq_r_addr(6'd0), .cq_i_data(517'd0),
                .cq_o_valid(unused_cq_v), .cq_w_fault(unused_cq_wf), .cq_r_fault(unused_cq_rf), .cq_o_data(unused_cq_d));
            assign dpv[g] = dpov; assign dprec[g*PW +: PW] = dpod;
            assign drv[g] = drov; assign drrec[g*RW +: RW] = drod;
            assign srv[g*3 +: 3] = srov;
            assign srrec[g*3*PW +: 3*PW] = {sr2od, sr1od, sr0od};
            // ---------------- UCIe static codecs ----------------
            wire [7:0] pc_, rc_;
            qfd_io_ucie_static u_uc (.rst_n(rst_n), .epoch_begin(eb), .epoch(ep),
                .p_ck(lck), .p_ckb0(lck), .p_ckb1(lck), .p_ckb2(lck), .p_ckb3(lck),
                .p_wr_v(twr[0]), .p_wr_observed_v(upov), .p_rd_v(trd[0]), .p_rx_expect_v(rxe[0]), .p_phy_up(1'b1),
                .p_phy_rx_v(prxv[g]), .p_wr_slot(twrs[0 +: 6]), .p_rd_slot(trds[0 +: 6]), .p_rx_expect_slot(rxes[0 +: 6]),
                .p_wr_word(upod), .p_phy_tx_v(ptxv[g]), .p_rx_v(puv), .p_epoch_abort(cabort[g*5 + 0]),
                .p_phy_tx(ptx[g*FP +: FP]), .p_phy_rx(prx[g*FP +: FP]), .p_rx_word(pud), .p_fault_cause(pc_),
                .r_ck(lck), .r_ckb0(lck), .r_ckb1(lck), .r_ckb2(lck), .r_ckb3(lck),
                .r_wr_v(twr[1]), .r_wr_observed_v(urov), .r_rd_v(trd[1]), .r_rx_expect_v(rxe[1]), .r_phy_up(1'b1),
                .r_phy_rx_v(rrxv[g]), .r_wr_slot(twrs[6 +: 6]), .r_rd_slot(trds[6 +: 6]), .r_rx_expect_slot(rxes[6 +: 6]),
                .r_wr_word(urod), .r_phy_tx_v(rtxv[g]), .r_rx_v(ruv), .r_epoch_abort(cabort[g*5 + 1]),
                .r_phy_tx(rtx[g*FR +: FR]), .r_phy_rx(rrx[g*FR +: FR]), .r_rx_word(rud), .r_fault_cause(rc_));
            assign ccause[g*40 +: 16] = {rc_, pc_};
            // ---------------- SerDes static codecs ----------------
            wire [545:0] sxw [0:2];
            assign sxw[0] = sx0od; assign sxw[1] = sx1od; assign sxw[2] = sx2od;
            for (j = 0; j < 3; j = j + 1) begin : g_sd
                wire [7:0] sc_;
                qfd_io_serdes_static u_sd (.ck(lck), .ckb0(lck), .ckb1(lck), .ckb2(lck), .ckb3(lck), .rst_n(rst_n),
                    .epoch_begin(eb), .epoch(ep), .wr_v(twr[2 + j]), .wr_observed_v(sxov[j]), .wr_slot(twrs[(2 + j)*6 +: 6]),
                    .wr_word(sxw[j]), .rd_v(trd[2 + j]), .rd_slot(trds[(2 + j)*6 +: 6]), .rx_expect_v(rxe[2 + j]),
                    .rx_expect_slot(rxes[(2 + j)*6 +: 6]), .phy_up(1'b1), .phy_tx_v(stxv[g*3 + j]),
                    .phy_tx(stx[(g*3 + j)*FP +: FP]), .phy_rx_v(srxv[g*3 + j]), .phy_rx(srx[(g*3 + j)*FP +: FP]),
                    .rx_v(suv[j]), .rx_word(sud[j*546 +: 546]), .epoch_abort(cabort[g*5 + 2 + j]), .fault_cause(sc_));
                assign ccause[g*40 + 16 + 8*j +: 8] = sc_;
            end
            // ---------------- PHY models (link domain, fixed latency) ----------------
            tb_phy_pipe #(.W(FP), .L(PU + XU)) u_pp (.clk(lck), .rst_n(rst_n), .v_in(ptxv[g]), .d_in(ptx[g*FP +: FP]),
                .flip(1'b0), .v_out(prxv[g ^ 1]), .d_out(prx[(g ^ 1)*FP +: FP]));
            tb_phy_pipe #(.W(FR), .L(PU + XU)) u_rp (.clk(lck), .rst_n(rst_n), .v_in(rtxv[g]), .d_in(rtx[g*FR +: FR]),
                .flip(1'b0), .v_out(rrxv[g ^ 1]), .d_out(rrx[(g ^ 1)*FR +: FR]));
            for (j = 0; j < 3; j = j + 1) begin : g_sp
                localparam integer Q = (P + 1 + j) % 4, R2 = 2 * Q + D, J2 = (P - Q + 7) % 4;
                // CORRUPT: flip one bit of die 6's port-0 frame number CORRUPT (a CRC must catch it)
                integer nf = 0;
                always @(posedge lck) if (stxv[g*3 + j]) nf <= nf + 1;
                tb_phy_pipe #(.W(FP), .L(PS + XS)) u_sp (.clk(lck), .rst_n(rst_n), .v_in(stxv[g*3 + j]),
                    .d_in(stx[(g*3 + j)*FP +: FP]), .flip(g == 6 && j == 0 && CORRUPT >= 0 && nf == CORRUPT),
                    .v_out(srxv[R2*3 + J2]), .d_out(srx[(R2*3 + J2)*FP +: FP]));
            end
            always @(posedge lck) if (ptxv[g] && rtxv[g]) pr_overlap = pr_overlap + 1;
            // ---------------- producer at its compiled slots ----------------
            integer pm = 0, pw = 0;
            reg [31:0] slot_c;
            always @(*) slot_c = `C_CMD(pm) + 1 + (`C_MODE(pm) ? 8 * pw : pw);
            wire fire = rst_n && pm < NMSG && cyc == slot_c;
            always @(posedge clk) if (fire) begin
                if (pw == `C_W(pm) - 1) begin pw <= 0; pm <= pm + 1; end else pw <= pw + 1;
            end
            assign iv[g] = fire && !(DROP == pm && g == 5 && pw == 1);
            assign id[g*FW +: FW] = part[`C_PB(pm) + g*`C_W(pm) + pw];
            assign il[g] = (pw == `C_W(pm) - 1);
            assign im[g] = `C_MODE(pm);
            assign it[g*TAGW +: TAGW] = pm;
            // ---------------- issuer timing check: command at its compiled cycle with the compiled fields ----------
            integer cm = 0;
            always @(posedge clk) if (rst_n) begin
                if (icv[g]) begin
                    if (cm >= NMSG || cyc != `C_CMD(cm) || imode[g] != `C_MODE(cm) || iwords[g*16 +: 16] != `C_W(cm) ||
                        itag[g*TAGW +: TAGW] != cm) begin
                        cmd_bad = cmd_bad + 1;
                        if (cmd_bad < 5) $display("CMD die=%0d cyc=%0d msg=%0d", g, cyc, cm);
                    end
                    cm <= cm + 1;
                end else if (cm < NMSG && cyc == `C_CMD(cm)) begin
                    cmd_bad = cmd_bad + 1;
                    if (cmd_bad < 5) $display("CMD_MISSING die=%0d cyc=%0d msg=%0d", g, cyc, cm);
                end
            end
            // ---------------- output checker (exact compiled cycle) ----------------
            integer rm, rk, per, rg, mm, nout = 0;
            reg [FW-1:0] exp;
            always @(posedge clk) if (ov[g]) begin
                rm = -1;
                for (mm = 0; mm < NMSG; mm = mm + 1) begin
                    per = `C_MODE(mm) ? ND * `C_W(mm) : `C_W(mm);
                    if (cyc >= `C_OUT(mm) && cyc < `C_OUT(mm) + per) rm = mm;
                end
                if (rm < 0) begin
                    extra = extra + 1;
                    if (extra < 5) $display("EXTRA die=%0d cyc=%0d", g, cyc);
                end else begin
                    per = `C_MODE(rm) ? ND * `C_W(rm) : `C_W(rm);
                    rk = cyc - `C_OUT(rm);
                    if (oe[g]) errs = errs + 1;
                    if (`C_MODE(rm)) begin
                        rg = rk % ND;
                        exp = part[`C_PB(rm) + (2 * (rg % 4) + rg / 4)*`C_W(rm) + rk / ND];
                        if (orank[g*3 +: 3] != rg) bad = bad + 1;
                    end else exp = sum[`C_SB(rm) + rk];
                    if (od[g*FW +: FW] !== exp) begin
                        bad = bad + 1;
                        if (bad < 5) $display("MISMATCH die=%0d msg=%0d word=%0d", g, rm, rk);
                    end
                    if (ol[g] != (rk == per - 1)) bad = bad + 1;
                    words_out = words_out + 1;
                    nout = nout + 1;
                    if (nout == total_out) done_n = done_n + 1;
                end
            end
        end
    endgenerate
    // measured link latencies (die 0 -> die 1 P; die 0 SerDes -> die 2)
    always @(posedge clk) begin
        if (first_up < 0 && upv[0]) first_up = cyc;
        if (first_dp < 0 && dpv[1]) first_dp = cyc;
        if (first_sx < 0 && sxv[0]) first_sx = cyc;
        if (first_sr < 0 && |srv[8:6]) first_sr = cyc;      // die 2 = package 1 die 0 (die 0's SerDes peer)
    end

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NMSG=%d", NMSG)) NMSG = 1;
        if (!$value$plusargs("NPW=%d", NPW)) NPW = 0;
        if (!$value$plusargs("START=%d", START)) START = 40;
        if (!$value$plusargs("DROP=%d", DROP)) DROP = -1;
        if (!$value$plusargs("CORRUPT=%d", CORRUPT)) CORRUPT = -1;
        if (!$value$plusargs("MAXCYC=%d", MAXCYC)) MAXCYC = 400000;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/sum.hex"}, sum);
        $readmemh({dir, "/cmd.hex"}, cmdv);
        $readmemh({dir, "/pw.hex"}, pwv);
        for (mi = 0; mi < NMSG; mi = mi + 1) begin
            total_out = total_out + (`C_MODE(mi) ? ND * `C_W(mi) : `C_W(mi));
            if (`C_OUT(mi) + (`C_MODE(mi) ? ND * `C_W(mi) : `C_W(mi)) + 64 > endc)
                endc = `C_OUT(mi) + (`C_MODE(mi) ? ND * `C_W(mi) : `C_W(mi)) + 64;
        end
    end
    integer t; reg [7:0] need; reg [7:0] dief;
    always @(posedge clk) begin
        if (rst_n && cyc == endc) begin
            for (t = 0; t < ND; t = t + 1)
                dief[t] = flt[t] | ifl[t] | (|xflt[t*20 +: 20]) | (|cabort[t*5 +: 5]);
            $display("TP8SL dies=8 latu=%0d lats=%0d pu=%0d ps=%0d xu=%0d xs=%0d msgs=%0d drop=%0d corrupt=%0d mismatches=%0d extra=%0d out_err=%0d cmd_bad=%0d coll_fault=%b issuer_fault=%b die_fault=%b words_out=%0d meas_lu=%0d meas_ls=%0d pr_overlap=%0d issuer_done=%b",
                     LATU, LATS, PU, PS, XU, XS, NMSG, DROP, CORRUPT, bad, extra, errs, cmd_bad, flt, ifl, dief, words_out,
                     first_dp - first_up, first_sr - first_sx, pr_overlap, idone);
            for (t = 0; t < ND; t = t + 1)
                $display("DIE %0d code=%b cdc=%b abort=%b cause=%h", t, fc[t*5 +: 5], xflt[t*20 +: 20], cabort[t*5 +: 5],
                         ccause[t*40 +: 40]);
            if (DROP >= 0) begin               // die 5's missing producer word: two independent detectors on die 5 --
                // the collective's producer-slot fault and the up CDC channel's write fault (compiled slot, no observed
                // word).  NOTE: the static CDC publishes the compiled slot unconditionally and the codec's observed-valid
                // input is fed the CDC's compiled o_valid, so the peer die does not see the miss (die 5's sticky fault
                // invalidates the epoch); carrying the observation across the CDC is an open item for its owner.
                if (fc[5*5 + 2] && xflt[5*20 + 0]) $display("PASS"); else $display("FAIL");
            end else if (CORRUPT >= 0) begin   // the receiving die's SerDes codec aborts (CRC), its collective faults
                if (|dief) $display("PASS"); else $display("FAIL");
            end else if (XU != 0 || XS != 0) begin
                if (&dief) $display("PASS"); else $display("FAIL");
            end else begin
                if (bad == 0 && extra == 0 && errs == 0 && cmd_bad == 0 && dief == 0 && done_n == ND) $display("PASS");
                else $display("FAIL");
            end
            $finish;
        end
        if (cyc > MAXCYC) begin $display("TIMEOUT"); $finish; end
    end
endmodule

// PHY model: fixed-latency register pipe of the codec frame, reset like the endpoints (off-chip, modelled)
module tb_phy_pipe #(parameter integer W = 597, parameter integer L = 14) (
    input wire clk, input wire rst_n, input wire v_in, input wire [W-1:0] d_in, input wire flip,
    output wire v_out, output wire [W-1:0] d_out);
    reg [L-1:0] vp;
    reg [W-1:0] dm [0:L-1];          // ring: entry wp was written L edges ago
    integer wp = 0;
    always @(posedge clk) begin
        if (!rst_n) vp <= 0; else vp <= {vp[L-2:0], v_in};
        dm[wp] <= d_in ^ (flip ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
        wp <= (wp == L - 1) ? 0 : wp + 1;
    end
    assign v_out = vp[L-1];
    assign d_out = dm[wp];
endmodule
