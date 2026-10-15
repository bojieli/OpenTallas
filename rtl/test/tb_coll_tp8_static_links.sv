`timescale 1ns/1ps
`define C_CMD(m) cmdv[m][159:128]
`define C_OUT(m) cmdv[m][127:96]
`define C_PB(m) cmdv[m][95:64]
`define C_SB(m) cmdv[m][63:32]
`define C_W(m) cmdv[m][31:16]
`define C_MODE(m) cmdv[m][0]
`ifdef OT_TP8S_QFD
`define C_ISS(m) (`C_CMD(m)-1)
`else
`define C_ISS(m) `C_CMD(m)
`endif
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
    parameter integer RU=0,RS0=0,RS1=0,RS2=0,SHARED=0,SIXFIVE=0,
    parameter integer XU = 0, XS = 0             // extra PHY cycles vs compiled (negative control)
) (input wire clk, input wire lck,input wire fdi_ck,input wire blk_ck);
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
    wire[ND-1:0]shareflt;wire[ND-1:0]sharetxv,sharerxv;wire[ND*1043-1:0]sharetx,sharerx;
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
`ifdef OT_TP8S_PARENT
            wire[54:0]fck;
            for(genvar cf=0;cf<5;cf=cf+1)begin:g_faceclocks
              assign fck[cf*11+:11]={{5{lck}},clk,lck,lck,clk,lck,clk};
            end
            wire[5*597-1:0]prpack,ptpack;
            wire[4:0]prv,ptv;
            assign prv={srxv[g*3+:3],rrxv[g],prxv[g]};
            assign prpack={srx[g*3*FP+:3*FP],32'd0,rrx[g*FR+:FR],prx[g*FP+:FP]};
            assign {stxv[g*3+:3],rtxv[g],ptxv[g]}=ptv;
            assign stx[g*3*FP+:3*FP]=ptpack[2*597+:3*597];
            assign rtx[g*FR+:FR]=ptpack[597+:FR];assign ptx[g*FP+:FP]=ptpack[0+:FP];
`ifdef OT_TP8S_PRODUCTION_WRAPPER
            assign ptv[1:0]=u_parent.u_io.phy_tx_valid[1:0];
            assign ptpack[0+:1194]=u_parent.u_io.phy_tx[0+:1194];
            qfd_collective_static_io_production #(.PU(PU),.PS(PS),.LU(LATU),.LS(LATS),.RU(RU),.RS0(RS0),.RS1(RS1),.RS2(RS2))u_parent(
`else
            qfd_collective_static_io #(.PU(PU),.PS(PS),.LU(LATU),.LS(LATS),.RU(RU),.RS0(RS0),.RS1(RS1),.RS2(RS2),.SHARED_UCIE(SHARED),.SIX_FIVE(SIXFIVE))u_parent(
`endif
              .clk(clk),.clk_pfold0(clk),.clk_pfold1(clk),.clk_pfold2(clk),.clk_pfold3(clk),
              .clk_xfold0(clk),.clk_xfold1(clk),.clk_xfold2(clk),.clk_xfold3(clk),
              .clk_pring0(clk),.clk_pring1(clk),.clk_sring0(clk),.clk_sring1(clk),.clk_sring2(clk),.clk_sring3(clk),.clk_sring4(clk),.clk_rring0(clk),.clk_rring1(clk),
              .rst_n(rst_n),.pkg_s(P[1:0]),.die_ps(D[0]),
              .cmd_v(icv[g]),.cmd_mode(imode[g]),.cmd_words(iwords[g*16+:16]),.cmd_tag(itag[g*TAGW+:TAGW]),
              .in_valid(iv[g]),.in_data(id[g*FW+:FW]),.in_last(il[g]),.in_mode(im[g]),.in_tag(it[g*TAGW+:TAGW]),
              .out_valid(ov[g]),.out_data(od[g*FW+:FW]),.out_last(ol[g]),.out_rank(orank[g*3+:3]),.out_err(oe[g]),
              .fault(flt[g]),.fault_code(fc[g*5+:5]),.cmd_free(cfree[g]),
              .face_ck(fck),.relay_ck({((2*(2*RU+RS0+RS1+RS2)>0)?2*(2*RU+RS0+RS1+RS2):1){clk}}),
`ifdef OT_TP8S_PRODUCTION_WRAPPER
              .ucie_up(1'b1),.serdes_up(3'b111),.serdes_rx_valid(prv[4:2]),.serdes_rx(prpack[2*597+:3*597]),
              .serdes_tx_valid(ptv[4:2]),.serdes_tx(ptpack[2*597+:3*597]),
`else
              .phy_up(5'b11111),.phy_rx_valid(prv),.phy_rx(prpack),.phy_tx_valid(ptv),.phy_tx(ptpack),
`endif
              .gearbox_core_ck(clk),.fdi_rx_ck(fdi_ck),.blk_ck({2{blk_ck}}),.fdi_ck(fdi_ck),.shared_rx_valid(sharerxv[g]),.shared_rx(sharerx[g*1043+:1043]),.shared_tx_valid(sharetxv[g]),.shared_tx(sharetx[g*1043+:1043]),.shared_fault(shareflt[g]),
              .transport_cdc_fault(xflt[g*20+:20]),.transport_abort(cabort[g*5+:5]),.transport_fault_cause(ccause[g*40+:40]));
            // Read-only source observations used by the existing latency meter.
`ifdef OT_TP8S_PRODUCTION_WRAPPER
            assign upv[g]=u_parent.u_io.up_valid;assign dpv[g]=u_parent.u_io.dp_valid;
            assign sxv[g*3+:3]={u_parent.u_io.sx2_valid,u_parent.u_io.sx1_valid,u_parent.u_io.sx0_valid};
            assign srv[g*3+:3]={u_parent.u_io.sr2_valid,u_parent.u_io.sr1_valid,u_parent.u_io.sr0_valid};
`else
            assign upv[g]=u_parent.up_valid;assign dpv[g]=u_parent.dp_valid;
            assign sxv[g*3+:3]={u_parent.sx2_valid,u_parent.sx1_valid,u_parent.sx0_valid};
            assign srv[g*3+:3]={u_parent.sr2_valid,u_parent.sr1_valid,u_parent.sr0_valid};
`endif
`else
            assign shareflt[g]=0;
            // ---------------- collective ----------------
`ifdef OT_TP8S_QFD
            qfd_io_collective_static u_die (       // the die-name master (LU / LS by +define)
                .clk(clk), .clk_pfold0(clk), .clk_pfold1(clk), .clk_pfold2(clk), .clk_pfold3(clk),
                .clk_xfold0(clk), .clk_xfold1(clk), .clk_xfold2(clk), .clk_xfold3(clk),
                .clk_pring0(clk),.clk_pring1(clk),.clk_sring0(clk),.clk_sring1(clk),.clk_sring2(clk),.clk_sring3(clk),.clk_sring4(clk),.clk_rring0(clk),.clk_rring1(clk),
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
                .clk_mem({9{clk}}),.clk(clk), .clk_pfold({4{clk}}), .clk_xfold({4{clk}}),
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
            // Production transport parent, five independent physical channels.
            for(j=0;j<5;j=j+1)begin:g_face
                localparam integer W=(j==1)?514:546;
                localparam integer PYW=W+51;
                wire ts=(j==0)?ups[g]:(j==1)?urv[g]:sxv[g*3];
                wire ps=(j==0)?ups[g]:(j==1)?urps[g]:sxps[g*3+j-2];
                wire tv=(j==0)?upv[g]:(j==1)?urv[g]:sxv[g*3+j-2];
                wire[W-1:0]td;wire[W-1:0]rd;wire rv;
                wire pv,ptv;wire[PYW-1:0]pr,pt;
                if(j==0)begin
                    assign td=uprec[g*PW+:PW];assign pv=prxv[g];assign pr=prx[g*FP+:FP];
                    assign ptxv[g]=ptv;assign ptx[g*FP+:FP]=pt;
                    assign dpv[g]=rv;assign dprec[g*PW+:PW]=rd;
                end else if(j==1)begin
                    assign td=urrec[g*RW+:RW];assign pv=rrxv[g];assign pr=rrx[g*FR+:FR];
                    assign rtxv[g]=ptv;assign rtx[g*FR+:FR]=pt;
                    assign drv[g]=rv;assign drrec[g*RW+:RW]=rd;
                end else begin
                    assign td=sxrec[(g*3+j-2)*PW+:PW];assign pv=srxv[g*3+j-2];assign pr=srx[(g*3+j-2)*FP+:FP];
                    assign stxv[g*3+j-2]=ptv;assign stx[(g*3+j-2)*FP+:FP]=pt;
                    assign srv[g*3+j-2]=rv;assign srrec[(g*3+j-2)*PW+:PW]=rd;
                end
                qfd_coll_static_face #(.FW(W),.PHY(j<2?PU:PS),.L(j<2?LATU:LATS),.KC(KC),.KW(KW))u_face(
                    .cal_ck(clk),.cal_lck(lck),.tx_wck(clk),.tx_rck(lck),.rx_wck(lck),.rx_rck(clk),.codec_ck({5{lck}}),
                    .rst_n(rst_n),.tx_slot(ts),.peer_slot(ps),.tx_valid(tv),.tx_data(td),.rx_valid(rv),.rx_data(rd),
                    .phy_up(1'b1),.phy_rx_valid(pv),.phy_rx(pr),.phy_tx_valid(ptv),.phy_tx(pt),
                    .cdc_fault(xflt[g*20+j*4+:4]),.epoch_abort(cabort[g*5+j]),.fault_cause(ccause[g*40+j*8+:8]));
            end
`endif
            // ---------------- PHY models (link domain, fixed latency) ----------------
            if(SHARED)begin:g_one_ucie
            tb_phy_pipe #(.W(1043),.L((SIXFIVE?4:PU)+XU))u_phy(.clk(SIXFIVE?fdi_ck:lck),.rst_n(rst_n),.v_in(sharetxv[g]),.d_in(sharetx[g*1043+:1043]),.flip(1'b0),.v_out(sharerxv[g^1]),.d_out(sharerx[(g^1)*1043+:1043]));
            assign prxv[g]=0;assign rrxv[g]=0;assign prx[g*FP+:FP]=0;assign rrx[g*FR+:FR]=0;
            end else begin:g_dual_diagnostic
            tb_phy_pipe #(.W(FP), .L(PU + XU)) u_pp (.clk(lck), .rst_n(rst_n), .v_in(ptxv[g]), .d_in(ptx[g*FP +: FP]),
                .flip(1'b0), .v_out(prxv[g ^ 1]), .d_out(prx[(g ^ 1)*FP +: FP]));
            tb_phy_pipe #(.W(FR), .L(PU + XU)) u_rp (.clk(lck), .rst_n(rst_n), .v_in(rtxv[g]), .d_in(rtx[g*FR +: FR]),
                .flip(1'b0), .v_out(rrxv[g ^ 1]), .d_out(rrx[(g ^ 1)*FR +: FR]));
            end
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
                    if (cm >= NMSG || cyc != `C_ISS(cm) || imode[g] != `C_MODE(cm) || iwords[g*16 +: 16] != `C_W(cm) ||
                        itag[g*TAGW +: TAGW] != cm) begin
                        cmd_bad = cmd_bad + 1;
                        if (cmd_bad < 5) $display("CMD die=%0d cyc=%0d msg=%0d", g, cyc, cm);
                    end
                    cm <= cm + 1;
                end else if (cm < NMSG && cyc == `C_ISS(cm)) begin
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
                dief[t] = (SHARED && shareflt[t]) | flt[t] | ifl[t] | (|xflt[t*20 +: 20]) | (|cabort[t*5 +: 5]);
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
