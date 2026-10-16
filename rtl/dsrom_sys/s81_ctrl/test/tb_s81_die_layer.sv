`timescale 1ns/1ps
`ifdef TB_MIX4_REAL
`define TB_FIXED
`endif
`ifdef TB_HCX_REAL
`define TB_FIXED
`endif
// ---------------------------------------------------------------------------------------------------------------------
// tb_s81_die_layer (s81die-1011/ctrl bench, 2026-10-11): ONE DeepSeek-V4.1 layer on the S81 die control plane with
// REAL slab masters, golden-exact at the LAYER OUTPUT (the next layer's h that HC H_STORE writes to the VM).
// Stage program + golden: tools/s81_ctrl/die_layer_stim.py (layer L0 of the 1M token = the hc_gate golden chain
// attn -> ffn -> next h; the committed stage programs' L0.attn.* + L0.ffn.* ops on the real masters' descriptors).
//   dsfd_sp_ctrl_e (program memory, guard, package controller, stage sequencer; one job = one user's layer)
//   port 0 fld : dsfd_sp_gather_c + dsfd_sp_capture_c (real; field phases + reference roots as tb_s81_die_fld)
//   port 2 hc  : dsfd_sp_hc_c (real: GAIN / H_LOAD / COEF / NORM / POST / H_STORE).  f_inp = the bench VM's row-
//                completion state of the head descriptor's operands (H rows landed by the package controller's
//                HIDDEN writes, gain rows, the coefficient rows the hcx producers write; POST: a y beat on the bus),
//                dropped on the cycle the adapter takes a head (f_inp is registered in the master: the next head is
//                re-evaluated before it can start).
//   port 3 coll: dsfd_sp_collective_c (real, +define+OT_S81PH_COLL_JOB, production split3cr composition) in a 4-die
//                TP4 group: dies 1..3 are real collective slabs with their own ot_s81_stage_seq + record feeders, all
//                lanes ot_dsrom_link_chan (bit errors, go-back-N), every die's output checked in order against the
//                four C8 reference engines (as tb_s81ph_coll_sys).  Die 0's VM feeds a message's records only when
//                the coll job's predecessors have ended (dataflow).  The all-reduce words die 0's t_vm delivers are
//                forwarded in order onto the HC y bus (bench glue: the direct coll -> HC bus of contract v2 is not in
//                dsfd_sp_collective yet) and checked equal to the golden y.
//   ports 1 su, 4 svc, 5 sel, 6 col, 9 hcx (the HC coefficient producers fn/sumsq/rsqrt/pre_post/sinkhorn, which
//                write the golden coefficient rows at their end), 7, 8, 10, 11: behavioural engines behind REAL
//                ot_s81_slab_ep endpoints (golden durations, dataflow start).
//   port 1 su (+define+TB_SU_REAL, s81-functional-token r3 2026-10-14): the PRODUCTION SU slab dsfd_sp_su_h (full
//                shape, S_RD 16 / S_WR 16 VM rows a cycle, behind the dsfd_sp_su_c pin flops) runs the layer's SU jobs
//                (QN / KV / QR / SE / SO / QB / RA / RB / SW + the GQ / GK gain loads) on the golden operands of the
//                layer (die_layer_stim.py --su-snap: rows from SU_BASE in vm_boot.mem); f_inp = the head job's program
//                predecessors ended (dataflow, dropped on the take); every SU result row (su_expa / su_expd.mem) is
//                checked bit-exact against the CPU golden at the end.  SU ops with no SU job kind run behavioural on
//                port 11.  SUMUT / SUXMUT: the slab's MUT / XMUT negative controls (4 gain set ignored; 3 QR inverse).
//   port 10 eng: default behavioural; TB_MIX4_REAL binds dsfd_engram_mix4_c and consumes actual row writes.
//                (no Engram RTL in this vehicle).  The HIDDEN payload is then the layer-ENTRY h; the op with wrow >= 0
//                (eng.add) writes the XW golden post-Engram h rows (coef.mem) over the H rows at its end, and the HC
//                H_LOAD's f_inp waits on that write (eng_h / eng_done) as well as on its eng.add predecessor.
// Clocks: the die PLL in die 0's collective slab (pll_stream 1.2 GHz = ck for the controller and every stream slab;
// pll_serial 0.9 GHz = ckv for the gather/capture serial side).
// CHECKS: (1) capture VM writes = reference per root (multiset); (2) every done at dsfd_sp_ctrl_e is the next op of its
// port in program order, once; (3) every job starts at or after its predecessors ended (HC: core take / core done; the POST's coll
// predecessor is a streaming bus operand: POST must END after it); (4) stage done once; (5) no fault anywhere;
// (6) collective outputs of all 4 dies = C8 reference, in order; (7) y words on the HC bus = golden y, bit-exact;
// (8) HC NORM output rows and H_STORE rows (the layer output) = CPU golden, bit-exact.
// MUT (gather endpoint) 2 wrong done tag / 4 dropped done; HMUT (HC core) 1 hc_post does not write h back;
// +define+OT_S81PH_MUT_TREP (collective output slice 1 pops one cycle early); INP1 (HC f_inp tied 1).  Each must FAIL.
// Plusargs: +DIR=<stim dir>.  Continuous run (s81-ftok r3): +HIN=<flits> sends the PREVIOUS stage's hop_tx output
// (header + 640 payload flits, dumped by its +HOUT) as this layer's HIDDEN payload instead of payload.mem (every row
// checked equal to the golden layer-entry h; the header is the bench's own: the vehicle's die ids are fixed);
// +HOUT=<file> dumps this layer's hop_tx flits (needs HTX != 0).
// ---------------------------------------------------------------------------------------------------------------------
module tb_s81_die_layer;
    parameter integer MXMUT = 0, MUT = 0, HMUT = 0, INP1 = 0, NG = 16, TMAX = 45000, EPER = 97, CHB = 60, CHU = 12, TSR = 7;
    // HC slab structure (defaults = the flat engine).  The production slab is the hierarchical tuple of the HC gate
    // (tools/s81_suhc/hc_gate.py --hier 3): HIER 1, HALF 1, CSPLIT 1, TAIL_SPLIT 2, HEAD_ROWS 10, CNL_PIN 1, CHAIN_STEP 6
    // at NG 256; build it with +define+TB_HC_HIER (the probes below then read the slab's sequencer tile).
    parameter integer HIER = 0, HALF = 0, CSPLIT = 0, TAIL_SPLIT = 0, HEAD_ROWS = 10, CNL_PIN = 0, CHAIN_STEP = 4;
    // NORM tree variant of the hierarchical slab (el1014-s81-norm-tree; XG="-GNTREE=1 -GNT_K=<k>"): default 0 = unchanged
    parameter integer NTREE = 0, NT_K = 67;
    localparam integer NR = 128, XW = 640, MAXC = 16384, MAXR = 1024, MAXQ = 4096, MAXE = 2048, MAXM = 16, FW = 512,
                       PW = 547, W = 552;
    // LVM: read latency of the bench's behavioural VM (request -> rs_v), <= 63.  A measurement knob for the serial cost of
    // the VM read round trip in the layer (bgq28 leaf chain / front-end hierarchy add latency, not rate); default unchanged.
    parameter integer LVM = 10;
    // rom-layer-tput 2026-10-13 (h transfer): PIPE / PIPE_PD = the HC sequencer's POST issue-order done (ot_s81_hc_cseq);
    // HST 1 = the H landing streamer ot_s81_hc_hland between the HC and the VM (H_LOAD answered from the landing rows as
    // they arrive; f_inp of the H_LOAD is then 1), HLMUT its negative control; HTX = the stage hand-off on the real
    // ot_s81_hop_tx (HIDDEN message, the layer output rows S_BASE.. to a link that takes one flit a cycle):
    // 0 none, 1 go at the H_STORE done (store and forward), 2 cut-through: go when HWM rows of the H_STORE have been
    // written (the die's form: the VM ARMN of the hand-off slot armed at HWM rows), 3 negative control: go at the
    // H_STORE take.  Checked: every flit = the golden layer output row, no row read before it was written.
    // PGAP: idle cycles between the HIDDEN header and its first payload flit (a legal link gap).  The bench program holds
    // the HC's two boot GAIN loads (352 cycles) in front of the layer; with PGAP >= 400 they are over before the payload
    // lands, which is the production condition of a stage entry (HC idle, gain sets loaded at boot).  The h transfer
    // record then counts the layer from the cycle before the first payload flit (layer_adj / xfer_adj).
    parameter integer PIPE = 0, PIPE_PD = 40, HST = 0, HLMUT = 0, HTX = 0, HWM = 8, PGAP = 0;
    parameter integer SUMUT = 0, SUXMUT = 0;
`ifdef TB_MIX4_REAL
    localparam MXR = 1;
`else
    localparam MXR = 0;
`endif
`ifdef TB_HCX_REAL
    localparam HCXR = 1;
`else
    localparam HCXR = 0;
`endif
`ifdef TB_SU_REAL
    localparam integer SUR = 1;
`else
    localparam integer SUR = 0;
`endif
    localparam integer S_RD = 2, S_WR = 8, H_BASE = 0, G_BASE = 1280, GROWS = 320, C_BASE = 2560, S_BASE = 6144;
    parameter integer C_STRIDE = 2;   // coefficient row stride (16 with --vm-coeff-align; the real HCX post requires 16)
    string dir;
`ifdef TB_SEQC
    localparam integer JOBS = 3;         // kit starts (sequential jobs of the same layer): the drop-start mutant loses the 3rd
`define SEQ u_ctl.u_seq
`else
    localparam integer JOBS = 1;
`define SEQ u_ctl.u.u.u_seq
`endif
    // ---------------- clocks: the die PLL (die 0's collective slab)
    reg refclk = 0; always #5 refclk = ~refclk;
    reg por = 0; initial #50 por = 1;
    wire [3:0] cks, ckvs, rsts;
    wire ck = cks[0], ckv = ckvs[0];
    reg rst = 0, rsv = 0;
    integer cyc = 0, e3;
    integer nxt [0:11];
    always @(posedge ck) cyc <= cyc + 1;
    reg [63:0] rs = 64'h243F6A8885A308D3;
    function [31:0] rnd(input integer d);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 7); rs = rs ^ (rs << 17); rnd = rs[31:0]; end
    endfunction
    // ---------------- program + stimulus tables
    integer nop = 0, nph = 0, ncl = 0;
    integer o_port [0:127], o_arg [0:127], o_dur [0:127], o_np [0:127], o_p [0:127][0:3], o_ph [0:127], o_cm [0:127], o_wr [0:127];
    reg [63:0] ph_par [0:15][0:9]; integer ph_c0 [0:15], ph_cn [0:15];
    integer c_gap [0:MAXC-1], c_root [0:MAXC-1], c_e [0:MAXC-1]; reg [31:0] c_t [0:MAXC-1], c_d [0:MAXC-1];
    reg [511:0] payload [0:XW-1];
    reg [511:0] ygold [0:MAXR-1];
    reg [13:0]  ea [0:MAXE-1];
    reg [511:0] ed [0:MAXE-1];
    reg [511:0] coefm [0:16383];
    reg [31:0]  nm [0:4];
    integer NE, TOT, NMSG, NY, NST;
    integer errors = 0, nwr = 0;
    integer endt [0:3][0:127], stt [0:3][0:127];
    integer cj = -1;                     // the current job (jobs run one after another)
    reg pk_v = 0; reg [6:0] pk_a = 0; reg [27:0] pk_d = 0; reg [7:0] pk_len = 0; reg peer_go = 0;
    // ---------------- DUT: control plane
    reg pw_v = 0; reg [6:0] pw_a = 0; reg [27:0] pw_d = 0; reg [7:0] plen = 0;
    reg i_v = 0; wire i_r; reg [511:0] i_d = 0; reg i_l = 0;
    wire [84:0] legacy_mix_c, legacy_hcx_c;
    wire [8:0] ctl_d9 = HCXR ? 9'd0 : d[9];   // TB_HCX_REAL: the chain runs only on the fixed calendar (engine 11)
    wire [84:0] hcx_c; wire [8:0] hcx_d; wire [1:0] hcx_st;
    wire [84:0] c [0:11]; wire [8:0] d [0:11]; wire [1:0] est [0:11];
`ifdef TB_SEQC
    // decision A: dsfd_stage_seq_c (kit start / done + program write on the serial clock); the kit (bench) writes the
    // HIDDEN payload rows into the VM after each start
    reg vwe = 0; reg [13:0] vwa = 0; reg [511:0] vwd = 0;
    reg [52:0] f_ks = 0; wire [53:0] t_kd; reg [35:0] f_pw = 0; wire [5:0] t_st;
    wire flt = t_st[5], stk = 1'b0; wire [15:0] fvec = {10'd0, t_st}, snap = 16'd0;
    dsfd_stage_seq_c u_ctl (.ckv(ckv), .rsv(rsv), .ck(ck), .rst(rst), .f_ks(f_ks), .t_kd(t_kd), .f_pw(f_pw), .f_plen(plen),
        .t_st(t_st),
        .c0(c[0]), .c1(c[1]), .c2(c[2]), .c3(c[3]), .c4(c[4]), .c5(c[5]), .c6(c[6]), .c7(c[7]), .c8(c[8]), .c9(legacy_hcx_c),
        .c10(legacy_mix_c), .c11(c[11]),
        .d0(d[0]), .d1(d[1]), .d2(d[2]), .d3(d[3]), .d4(d[4]), .d5(d[5]), .d6(d[6]), .d7(d[7]), .d8(d[8]), .d9(ctl_d9),
        .d10(d[10]), .d11(d[11]),
        .s0(est[0]), .s1(est[1]), .s2(est[2]), .s3(est[3]), .s4(est[4]), .s5(est[5]), .s6(est[6]), .s7(est[7]),
        .s8(est[8]), .s9(est[9]), .s10(est[10]), .s11(est[11]));
    integer kdn = 0;
    always @(posedge ckv) if (t_kd[53]) kdn <= kdn + 1;
`else
    wire vwe; wire [13:0] vwa; wire [511:0] vwd; wire flt, stk; wire [15:0] fvec, snap;
    dsfd_sp_ctrl_e #(.MY_ID(2), .SRC_LO(1), .SRC_HI(1)) u_ctl (.ck(ck), .rs(rst), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d),
        .prog_len(plen), .cfg_users(12'd4), .i_v(i_v), .i_r(i_r), .i_d(i_d), .i_l(i_l),
        .c0(c[0]), .c1(c[1]), .c2(c[2]), .c3(c[3]), .c4(c[4]), .c5(c[5]), .c6(c[6]), .c7(c[7]), .c8(c[8]), .c9(legacy_hcx_c),
        .c10(legacy_mix_c), .c11(c[11]),
        .d0(d[0]), .d1(d[1]), .d2(d[2]), .d3(d[3]), .d4(d[4]), .d5(d[5]), .d6(d[6]), .d7(d[7]), .d8(d[8]), .d9(ctl_d9),
        .d10(d[10]), .d11(d[11]),
        .vwe(vwe), .vwa(vwa), .vwd(vwd), .flt(flt), .fvec(fvec), .stk(stk), .snap(snap));
`endif
    // job take: the jobs of this bench run one after another; per-port done order restarts with each job
    always @(posedge ck) if (`SEQ.job_v && `SEQ.job_rdy) begin cj = cj + 1; for (e3 = 0; e3 < 12; e3 = e3 + 1) nxt[e3] = 0; end
    // ---------------- DUT: gather + capture (fld, port 0)
    reg [511:0] f_vm = 0;
    wire [6946:0] tcap; wire [13375:0] tvm; wire [11:0] tcd; wire [10:0] xgo;
    reg [760:0] tp [0:11];
    dsfd_sp_gather_c #(.MUT(MUT)) u_g (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_vm(f_vm), .t_capture(tcap),
        .rW0(tp[0][691:0]), .rW1(tp[1][760:0]), .rW2(tp[2][760:0]), .rW3(tp[3][760:0]), .rW4(tp[4][760:0]), .rW5(tp[5][691:0]),
        .rE0(tp[6][691:0]), .rE1(tp[7][760:0]), .rE2(tp[8][760:0]), .rE3(tp[9][760:0]), .rE4(tp[10][760:0]), .rE5(tp[11][691:0]),
        .c_cmd(c[0]), .c_done(d[0]), .c_st(est[0]), .f_cd(tcd), .t_xgo(xgo));
    dsfd_sp_capture_c u_c (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(tcap), .t_vm(tvm), .t_cd(tcd));
    wire [63:0] dst = tvm[13312 +: 64];
    // ---------------- DUT: HC (port 2)
    wire hc_inp;
    reg  y_v = 0; wire y_rdy; reg [NG*32-1:0] y_d = 0;
    wire [S_RD-1:0] rq_v; wire [S_RD*14-1:0] rq_row; reg [S_RD-1:0] rs_v = 0; reg [S_RD*512-1:0] rs_d = 0;
    // HC <-> VM read path: direct, or through the H landing streamer (HST)
    wire [S_RD-1:0] hrs_v; wire [S_RD*512-1:0] hrs_d; wire [S_RD-1:0] vq_v; wire [S_RD*14-1:0] vq_row;
    wire hl_flt; wire [3:0] hl_fc; wire [31:0] hl_ns, hl_nv;
    generate if (HST != 0) begin : g_hst
        ot_s81_hc_hland #(.S_RD(S_RD), .XW(XW), .RXB(H_BASE), .VWA(14), .FD(16), .MUT(HLMUT)) u_hl (
            .clk(ck), .rst_n(rst), .lw_v(vwe), .lw_a(vwa), .lw_d(vwd), .h_rq_v(rq_v), .h_rq_row(rq_row),
            .h_rs_v(hrs_v), .h_rs_d(hrs_d), .v_rq_v(vq_v), .v_rq_row(vq_row), .v_rs_v(rs_v), .v_rs_d(rs_d),
            .fault(hl_flt), .fault_code(hl_fc), .st_stream(hl_ns), .st_vm(hl_nv));
    end else begin : g_nhst
        assign hrs_v = rs_v; assign hrs_d = rs_d; assign vq_v = rq_v; assign vq_row = rq_row;
        assign hl_flt = 1'b0; assign hl_fc = 4'd0; assign hl_ns = 0; assign hl_nv = 0;
    end endgenerate
    wire [S_WR-1:0] wq_v; wire [S_WR*14-1:0] wq_row; wire [S_WR*16-1:0] wq_mask; wire [S_WR*512-1:0] wq_d;
    dsfd_sp_hc_c #(.NG(NG), .D(5120), .S_RD(S_RD), .S_WR(S_WR), .MUT(HMUT), .HIER(HIER), .HALF(HALF), .CSPLIT(CSPLIT),
                   .TAIL_SPLIT(TAIL_SPLIT), .HEAD_ROWS(HEAD_ROWS), .CNL_PIN(CNL_PIN), .CHAIN_STEP(CHAIN_STEP), .PIPE(PIPE), .PIPE_PD(PIPE_PD), .NTREE(NTREE), .NT_K(NT_K)) u_hc (.ck(ck), .rst(rst), .c_cmd(c[2]),
        .c_done(d[2]), .c_st(est[2]), .f_inp(hc_inp), .y_v(y_v), .y_rdy(y_rdy), .y_d(y_d), .rq_v(rq_v), .rq_row(rq_row),
        .rs_v(hrs_v), .rs_d(hrs_d), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d));
    wire [3:0] hfcode = u_hc.fcode;      // the fault code is internal to dsfd_sp_hc_c since cdb57463d; the flat engine sits in g_flat
    // ---------------- DUT: the TP4 collective group (port 3 of die 0)
    wire [514:0] rx [0:3][0:7];
    wire [511:0] tx [0:3][0:7];
    reg  [591:0] fvm [0:3];
    reg  [2:0]   tsr [0:3];
    wire [2099:0] tv [0:3];
    wire [84:0] ccmd [0:3]; wire [8:0] cdn [0:3]; wire [1:0] cst [0:3];
    assign ccmd[0] = c[3]; assign d[3] = cdn[0]; assign est[3] = cst[0];
    genvar gd, gl;
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_die
        wire tf0, tf1, tf2, tf3, tf4, tf5, tf6, tf7;
        dsfd_sp_collective_c u (.refclk(refclk), .por(por), .f_vm(fvm[gd]), .ts(tsr[gd]),
            .c_cmd(ccmd[gd]), .c_done(cdn[gd]), .c_st(cst[gd]),
            .rW0(rx[gd][0]), .rW1(rx[gd][1]), .rW2(rx[gd][2]), .rW3(rx[gd][3]),
            .rE0(rx[gd][4]), .rE1(rx[gd][5]), .rE2(rx[gd][6]), .rE3(rx[gd][7]),
            .pll_stream(cks[gd]), .pll_serial(ckvs[gd]), .pll_hbm(), .rst_stream(rsts[gd]), .rst_serial(), .rst_hbm(),
            .t_vm(tv[gd]),
            .tdW0(tx[gd][0]), .tdW1(tx[gd][1]), .tdW2(tx[gd][2]), .tdW3(tx[gd][3]),
            .tdE0(tx[gd][4]), .tdE1(tx[gd][5]), .tdE2(tx[gd][6]), .tdE3(tx[gd][7]),
            .tfW0(tf0), .tfW1(tf1), .tfW2(tf2), .tfW3(tf3), .tfE0(tf4), .tfE1(tf5), .tfE2(tf6), .tfE3(tf7));
        for (gl = 0; gl < 8; gl = gl + 1) begin : g_lane
            localparam integer X = (gl == 0) ? 1 : (gl == 1) ? 2 : (gl == 2) ? 3 : (gl == 6) ? 2 : (gl == 7) ? 3 : 1;
            localparam integer DL = (gl == 0 || gl == 4) ? CHU : CHB;
            wire ov; wire [511:0] od;
            ot_dsrom_link_chan #(.W(512), .MAXD(DL), .ERR_PERIOD(EPER), .ERR_OFFSET(gd * 8 + gl), .ERR_STRIDE(37)) u_ch (
                .clk(ck), .rst_n(rsts[gd ^ X]), .delay(16'd0), .in_valid(rsts[gd ^ X]), .in_data(tx[gd ^ X][gl]),
                .out_valid(ov), .out_data(od), .err_injected());
            assign rx[gd][gl] = {1'b0, 1'b1, od, ov};
        end
        // peers (dies 1..3): their own stage sequencer issues the coll messages (one job, all descriptors)
        if (gd > 0) begin : g_peer
            wire [11:0] cv; wire [12*84-1:0] cd; wire jd_, pf, jr;
            reg jv = 0; integer started = 0;
            ot_s81_stage_seq #(.NOPS(128), .NENG(12), .ARGW(24), .USER_W(10), .NW(21), .QD(8), .FQ(4)) u_sq (
                .clk(ck), .rst_n(rst), .pw_v(pk_v), .pw_a(pk_a), .pw_d(pk_d), .prog_len(pk_len),
                .job_v(jv), .job_rdy(jr), .job_user(10'(gd)), .job_pos(21'd1048575), .job_tok(21'd12345),
                .job_done(jd_), .cmd_v(cv), .cmd_d(cd),
                .dn_v({8'd0, cdn[gd][8], 3'd0}), .dn_tag({64'd0, cdn[gd][7:0], 24'd0}),
                .busy(), .fault(pf), .fault_code(), .st_jobs(), .st_cmds());
            assign ccmd[gd] = {cv[3], cd[3*84 +: 84]};
            integer njd = 0, ndn = 0;
            always @(posedge ck) if (rst) begin
                if (jv && jr) jv <= 1'b0;
                if (peer_go && !jv && started < JOBS && njd >= started) begin jv <= 1'b1; started <= started + 1; end   // one peer job at a time (as the kit)
                if (jd_) njd <= njd + 1;
                if (cdn[gd][8]) begin
                    if (cdn[gd][6:0] !== 7'(ndn % NMSG)) begin errors = errors + 1; $display("ERR peer %0d done tag %h exp %0d", gd, cdn[gd][7:0], ndn); end
                    ndn <= ndn + 1;
                end
                if (pf || cst[gd][0] || (cv & ~12'h008) != 0) begin errors = errors + 1; if (errors < 20) $display("ERR peer %0d fault seq %b ep %b cv %h cyc %0d", gd, pf, cst[gd][0], cv, cyc); end
            end
        end
    end endgenerate
    // ---------------- collective records + C8 reference engines
    reg [FW-1:0] own [0:3][0:MAXR-1];
    reg ownl [0:MAXR-1]; reg ownm [0:MAXR-1]; reg [31:0] ownt [0:MAXR-1];
    integer m_mode [0:MAXM-1], m_n [0:MAXM-1], m_r0 [0:MAXM-1], m_op [0:MAXM-1];
    integer first_send_cyc = -1;
    reg  [3:0] r_iv = 0; wire [3:0] r_ir;
    wire [3:0] r_txv [0:3]; wire [PW-1:0] r_txr [0:3]; wire [7:0] r_cro [0:3];
    wire [3:0] r_ov, r_ol, r_oe; wire [4*FW-1:0] r_od [0:3];
    integer rptr [0:3];
    generate for (gd = 0; gd < 4; gd = gd + 1) begin : g_ref
        wire [3:0] rxv; wire [4*PW-1:0] rxr; wire [7:0] cri;
        for (gl = 0; gl < 4; gl = gl + 1) begin : g_s
            assign rxv[gl] = (gl == gd) ? 1'b0 : r_txv[gl][gd];
            assign rxr[gl*PW +: PW] = (gl == gd) ? {PW{1'b0}} : r_txr[gl];
            assign cri[2*gl +: 2] = (gl == gd) ? 2'b00 : r_cro[gl][2*gd +: 2];
        end
        ot_w15_rom_oneshot_die_px_acceptedpop #(.FIX_ACCEPTED_POP(1), .N(4), .RANK(gd), .LANES(16), .TAGW(32),
            .DEPTH(256), .PKG_DIES(2), .RELAY(0), .ADD_LAT(3), .PAIRWISE(1), .GW(4), .OUT_BP(1)) u (
            .clk(ck), .rst_n(rsts[0]),
            .in_valid(r_iv[gd]), .in_ready(r_ir[gd]), .in_data(own[gd][rptr[gd] % TOT]), .in_last(ownl[rptr[gd] % TOT]),
            .in_mode(ownm[rptr[gd] % TOT]), .in_tag(ownt[rptr[gd] % TOT]),
            .tx_valid(r_txv[gd]), .tx_rec(r_txr[gd]), .tx_ready(4'hF), .cr_in(cri),
            .rx_valid(rxv), .rx_rec(rxr), .cr_out(r_cro[gd]),
            .rl_tx_valid(), .rl_tx_rec(), .rl_rx_valid(4'd0), .rl_rx_rec({4*PW{1'b0}}),
            .out_valid(r_ov[gd]), .out_ready(1'b1), .out_data(r_od[gd]), .out_last(r_ol[gd]), .out_rank(),
            .out_err(r_oe[gd]), .fault(), .fault_code());
    end endgenerate
    reg [4*FW+1:0] rq [0:3][0:MAXQ];
    reg            rqe [0:3][0:MAXQ];
    integer rn [0:3], ridx [0:3], rp_n, dd;
    initial for (dd = 0; dd < 4; dd = dd + 1) begin rptr[dd] = 0; rn[dd] = 0; ridx[dd] = 0; end
    always @(posedge ck) for (dd = 0; dd < 4; dd = dd + 1) begin
        if (r_ov[dd]) begin rq[dd][rn[dd]] = {ownm[ridx[dd] % TOT], r_ol[dd], r_od[dd]}; rqe[dd][rn[dd]] = r_oe[dd]; rn[dd] = rn[dd] + 1; ridx[dd] = ridx[dd] + 1; end
        rp_n = rptr[dd] + ((r_iv[dd] && r_ir[dd]) ? 1 : 0);
        rptr[dd] <= rp_n;
        r_iv[dd] <= rsts[0] && (first_send_cyc >= 0) && (rp_n < TOT * JOBS);
    end
    // ---------------- collective VM models (all dies): consume t_vm, feed records under credits
    integer cr [0:3][0:5], sp [0:3], dn [0:3], cfgd [0:3], nwv, q, k2, coll_err = 0, msg0 = 0;
    reg [2099:0] b;
    reg acc_err;
    // HC y bus FIFO (die 0's all-reduce words, in order)
    reg [511:0] yq [0:MAXQ-1];
    integer ywr = 0, yrd = 0, y_ok = 0, y_bad = 0, yi;
    localparam integer YB = NG / 16;
    function automatic integer ready_op(input integer jb, input integer op);
        integer i, r;
        begin
            r = 1;
            if (o_np[op] == 0) r = (nwr >= XW * (jb + 1));
            for (i = 0; i < o_np[op]; i = i + 1) if (endt[jb][o_p[op][i]] < 0) r = 0;
            ready_op = r;
        end
    endfunction
    integer ctl_up = 0;
    always @(posedge ck) begin
        for (dd = 0; dd < 4; dd = dd + 1) begin
            b = tv[dd];
            if (b[0]) begin
                for (q = 0; q < 6; q = q + 1) cr[dd][q] = cr[dd][q] + b[17 + 4*q +: 4];
                if (b[41] && b[49:42] != 0) begin coll_err = coll_err + 1; if (coll_err < 20) $display("ERR DIE %0d coll FAULT vec %b", dd, b[49:42]); end
                if (b[2:1] == 2'd1) begin
                    if (b[15]) begin
                        if (dn[dd] >= rn[dd] || rq[dd][dn[dd]] !== {1'b1, b[13], b[52 +: 4*FW]}) begin
                            coll_err = coll_err + 1; if (coll_err < 20) $display("ERR DIE %0d GATHER beat %0d mismatch", dd, dn[dd]); end
                        dn[dd] = dn[dd] + 1;
                    end else begin
                        nwv = b[6] + b[7] + b[8] + b[9]; acc_err = 0;
                        for (k2 = 0; k2 < nwv; k2 = k2 + 1) begin
                            if (dn[dd] >= rn[dd] || rq[dd][dn[dd]] !== {1'b0, b[10 + k2], {3*FW{1'b0}}, b[52 + k2*FW +: FW]}) begin
                                coll_err = coll_err + 1; if (coll_err < 20) $display("ERR DIE %0d REDUCE word %0d mismatch", dd, dn[dd]); end
                            acc_err = acc_err | rqe[dd][dn[dd]];
                            dn[dd] = dn[dd] + 1;
                            if (dd == 0) begin
                                yq[ywr] = b[52 + k2*FW +: FW];
                                if (ywr < NY * JOBS && yq[ywr] === ygold[ywr % NY]) y_ok = y_ok + 1;
                                else begin y_bad = y_bad + 1; if (y_bad < 5) $display("ERR y word %0d != golden", ywr); end
                                ywr = ywr + 1;
                            end
                        end
                        if (acc_err !== b[16]) begin coll_err = coll_err + 1; if (coll_err < 20) $display("ERR DIE %0d err flag", dd); end
                    end
                end
            end
            tsr[dd] <= {2'b01, (rnd(0) % 8) < TSR};
            fvm[dd] <= 0;
            if (rsts[dd] && cyc > 20) begin
                if (cfgd[dd] < 2) begin
                    cfgd[dd] = cfgd[dd] + 1;
                    if (cfgd[dd] == 2) fvm[dd] <= {{(W-3){1'b0}}, 1'b1, dd[1:0], 32'd0, 1'b0, 1'b0, 3'd0, 2'd3, 1'b1};
                end else if (cr[dd][0] > 0 && sp[dd] < TOT * JOBS) begin
                    // die 0: a message's records exist once its coll job's predecessors have ended (dataflow)
                    if (dd != 0 || (ctl_up && ready_op(msg0 / NMSG, m_op[msg0 % NMSG]))) begin
                        if (dd == 0 && sp[0] % TOT == m_r0[msg0 % NMSG]) stt[msg0 / NMSG][m_op[msg0 % NMSG]] = cyc;
                        fvm[dd] <= {{(W-FW){1'b0}}, own[dd][sp[dd] % TOT], ownt[sp[dd] % TOT], ownm[sp[dd] % TOT], ownl[sp[dd] % TOT], 3'd0, 2'd1, 1'b1};
                        if (first_send_cyc < 0) first_send_cyc = cyc;
                        if (dd == 0 && ownl[sp[0] % TOT]) msg0 = msg0 + 1;
                        sp[dd] = sp[dd] + 1; cr[dd][0] = cr[dd][0] - 1;
                    end
                end
            end
        end
    end
    // y bus to the HC: in order, valid while a word is buffered
    always @(posedge ck) begin
        // one HC y beat = NG lanes x 32 b = YB all-reduce words of 16 (NG 16: one word a beat; NG 256: 16 words a beat)
        if (y_v && y_rdy) yrd = yrd + YB;
        y_v <= (yrd + YB <= ywr);
        for (yi = 0; yi < YB; yi = yi + 1) y_d[512 * yi +: 512] <= yq[yrd + yi];
    end
`ifdef TB_SU_REAL
    // ---------------- DUT: the production SU slab (port 1), dsfd_sp_su_c pin convention around dsfd_sp_su_h
    localparam integer SU_RD = 16, SU_WR = 16, MAXSU = 8192;
    wire [SU_RD-1:0] su_rq_v; wire [SU_RD*14-1:0] su_rq_row; reg [SU_RD-1:0] su_rs_v = 0; reg [SU_RD*512-1:0] su_rs_d = 0;
    wire [SU_WR-1:0] su_wq_v; wire [SU_WR*14-1:0] su_wq_row; wire [SU_WR*16-1:0] su_wq_mask; wire [SU_WR*512-1:0] su_wq_d;
    wire su_inp, su_dv, su_flt, su_onl; wire [7:0] su_dt; wire [3:0] su_fc;
    reg [1:0] su_rsq = 0; always @(posedge ck or negedge rst) if (!rst) su_rsq <= 2'b00; else su_rsq <= {su_rsq[0], 1'b1};
    wire su_rn = su_rsq[1];
    reg su_cv = 0; reg [83:0] su_cd = 0;
    always @(posedge ck or negedge su_rn) if (!su_rn) su_cv <= 1'b0; else su_cv <= c[1][84];
    always @(posedge ck) su_cd <= c[1][83:0];
    dsfd_sp_su_h #(.S_RD(SU_RD), .S_WR(SU_WR), .MUT(SUMUT), .XMUT(SUXMUT)) u_su (
        .cck(ck), .crs(su_rn), .sk(ck), .srs(su_rn), .c_cmd_v(su_cv), .c_cmd_d(su_cd), .c_done_v(su_dv), .c_done_tag(su_dt),
        .inp(su_inp), .rq_v(su_rq_v), .rq_row(su_rq_row), .rs_v(su_rs_v), .rs_d(su_rs_d), .wq_v(su_wq_v), .wq_row(su_wq_row),
        .wq_mask(su_wq_mask), .wq_d(su_wq_d), .flt(su_flt), .online(su_onl), .fcode(su_fc));
    reg [8:0] su_cdn = 0; reg [1:0] su_cst = 0;
    always @(posedge ck or negedge su_rn) if (!su_rn) begin su_cdn <= 9'd0; su_cst <= 2'b00; end
                                          else begin su_cdn <= {su_dv, su_dt}; su_cst <= {su_onl, su_flt}; end
    assign d[1] = su_cdn; assign est[1] = su_cst;
    // dataflow: the adapter's head job may start once its program predecessors have ended (registered in the slab)
    wire        su_hv = u_su.u_ctl.u_ad.rv;
    wire [83:0] su_hq = u_su.u_ctl.u_ad.rq;
    wire        su_take = u_su.u_ctl.e_v && u_su.u_ctl.e_r;
    assign su_inp = su_hv && ready_op(cj, su_hq[6:0]) && !su_take;
    integer su_nj = 0;
    always @(posedge ck) begin
        if (su_take) begin stt[cj][u_su.u_ctl.e_d[6:0]] = cyc; su_nj = su_nj + 1;
            if (o_port[u_su.u_ctl.e_d[6:0]] != 1) begin errors = errors + 1; $display("ERR SU got op %0d of port %0d", u_su.u_ctl.e_d[6:0], o_port[u_su.u_ctl.e_d[6:0]]); end end
        if (u_su.u_ctl.d_v) endt[cj][u_su.u_ctl.d_t[6:0]] = cyc;
    end
    reg [13:0] su_ea [0:MAXSU-1];
    reg [511:0] su_ed [0:MAXSU-1];
    reg [31:0] su_nm [0:0];
    integer SUN = 0;
`endif
    // ---------------- bench VM (HC rows, HIDDEN payload, coefficient rows) + row-completion state
    reg [511:0] vm [0:16383];
    reg vm_ok [0:16383];
    integer hcnt = 0, gcnt [0:1];
`ifdef TB_FIXED
    // ONE fixed issuer (ot_s81_fixed_issue, OP_BASE 2) for every engine moved onto the compiled calendar:
    // engine 10 = MIX4 (TB_MIX4_REAL), engine 9 = the HC coefficient chain (TB_HCX_REAL). Program: fixed_program.mem,
    // {rows, PW words}: fixed_meta.mem (die_layer_stim.py; done = issue + 1 + pin-to-pin for every row).
    localparam [12:0] FX_PRESENT = (MXR ? 13'h400 : 13'h0) | (HCXR ? 13'h800 : 13'h0);
    wire [12:0] mx_cv; wire [1091:0] mx_cd;
    // engine 11 = the HC projection/coefficient chain (die static sequencer ABI, lower_native_graph port 11)
    wire [12:0] mx_av = {1'b0, HCXR ? hcx_st[1] : 1'b0, MXR ? est[10][1] : 1'b0, 10'b0};
    wire [12:0] mx_dv = {1'b0, HCXR ? hcx_d[8] : 1'b0, MXR ? d[10][8] : 1'b0, 10'b0};
    wire [103:0] mx_dt = {8'b0, HCXR ? hcx_d[7:0] : 8'b0, MXR ? d[10][7:0] : 8'b0, 80'b0};
    // Reset release is a compiler startup edge, driven on the opposite phase;
    // do not derive async reset from an NBA-updated stream counter expression.
    reg mx_rst_n=0;
    initial begin
        while(cyc<1000) @(negedge ck);
        mx_rst_n=1;
    end
    reg mx_pw_v=0; reg [6:0] mx_pw_a=0; reg [27:0] mx_pw_d=0;
    wire mx_is_fault; wire [3:0] mx_is_code; wire [1:0] mx_phase;
    reg [34:0] mx_pmem [0:63]; reg [31:0] fx_meta [0:1];
    initial begin fx_meta[0]=2; fx_meta[1]=8; end
    ot_s81_fixed_issue #(.NOPS(8),.NENG(13),.STAGE(0),.OP_BASE(2),.ENG_PRESENT(FX_PRESENT)) mx_issuer(
        .clk(ck),.rst_n(mx_rst_n),.pw_v(mx_pw_v),.pw_a(mx_pw_a),.pw_d(mx_pw_d),.prog_len(fx_meta[0][7:0]),
        .job_v(cyc==1250),.job_user(10'd0),.job_pos(21'd0),.job_tok(21'd1000),
        .cmd_v(mx_cv),.cmd_d(mx_cd),.engine_available(mx_av),.dn_v(mx_dv),.dn_tag(mx_dt),
        .fault(mx_is_fault),.fault_code(mx_is_code),.phase(mx_phase),
        .job_rdy(),.busy(),.job_done(),.job_kdone(),.done_slot(),.kit_tok(),.st_jobs(),.st_cmds());
    initial begin: fixed_boot
        wait(dir != "");
        $readmemh({dir,"/fixed_program.mem"},mx_pmem);
        $readmemh({dir,"/fixed_meta.mem"},fx_meta);
        while(cyc<1010) @(negedge ck);
        for(int z=0;z<fx_meta[1];z++) begin
            mx_pw_v=1; mx_pw_a=mx_pmem[z][34:28]; mx_pw_d=mx_pmem[z][27:0];
            @(negedge ck); mx_pw_v=0; @(negedge ck);
        end
    end
    always @(posedge ck) if(rst && mx_is_fault) $fatal(1,"FIXED_ISSUER fault code=%0d cycle=%0d phase=%0d sealed=%0d cfg=%0d",mx_is_code,cyc,mx_phase,mx_issuer.sealed,mx_issuer.cfg_fault);
    initial begin
        if(JOBS!=1) $fatal(1,"fixed component calendar contains one context; compile all contexts before use");
`ifdef TB_SEQC
        $fatal(1,"fixed component calendar requires its declared packet-clock profile");
`endif
    end
`endif
`ifdef TB_MIX4_REAL
    assign c[10] = {mx_cv[10],mx_cd[840+:84]};
    wire [19:0] mx_rq_v; wire [279:0] mx_rq_row;
    reg [19:0] mx_rs_v = 0; reg [10239:0] mx_rs_d = 0;
    wire [3:0] mx_wq_v; wire [55:0] mx_wq_row;
    wire [63:0] mx_wq_mask; wire [2047:0] mx_wq_d;
    dsfd_engram_mix4_c #(.MUT(MXMUT)) u_mix4 (
        .ck({149{ck}}), .rst(rst), .c_cmd(c[10]), .c_done(d[10]), .c_st(est[10]),
        .f_inp(hcnt == XW), .rq_v(mx_rq_v), .rq_row(mx_rq_row),
        .rs_v(mx_rs_v), .rs_d(mx_rs_d), .wq_v(mx_wq_v), .wq_row(mx_wq_row),
        .wq_mask(mx_wq_mask), .wq_d(mx_wq_d));
    integer mx_reads = 0, mx_writes = 0;
    always @(posedge ck) begin
        mx_rs_v <= mx_rq_v;
        for (int ml=0; ml<20; ml++) if(mx_rq_v[ml]) begin
            mx_rs_d[512*ml+:512] <= vm[mx_rq_row[14*ml+:14]]; mx_reads++;
        end
        for (int ml=0; ml<4; ml++) if(mx_wq_v[ml]) begin
            for(int mw=0; mw<16; mw++) if(mx_wq_mask[16*ml+mw])
                vm[mx_wq_row[14*ml+:14]][32*mw+:32] = mx_wq_d[512*ml+32*mw+:32];
            mark(mx_wq_row[14*ml+:14]); mx_writes++;
        end
        if(u_mix4.jnew) stt[cj][u_mix4.jnd[6:0]] = cyc;
        if(u_mix4.done) begin endt[cj][u_mix4.jd[6:0]] = cyc; eng_done = 1; end
    end
`else
    assign c[10] = legacy_mix_c;
`endif
`ifdef TB_HCX_REAL
    // ---------------- port 9: the HC COEFFICIENT CHAIN on real RTL (no golden coefficient rows anywhere)
    // ot_s81_hcx_chain_seq (one compiled command per block) -> 4 x dsfd_sp_hcx_projection HLAYOUT 1 (ranks 0..3, 24 rows,
    // resident fn ROMs, reading the layer's H rows in the HC h_rows layout) -> TP4 raw gather -> ot_s81_hcx_gatherpack ->
    // ot_s81_hcx_post_gain_native (post) -> coefficient rows C_BASE.. that the HC COEF job reads (f_inp = VM presence).
    // Offsets = the measured chain (tb_s81_hcx_chain, same clocks and reset edges). DECLARED: bench VM (RL/WL 4), the TP4
    // raw gather is bench transport (collective glue), ranks 1..3 read die 0's H rows and receive rank 0's command.
    parameter integer HX_FAST = 0, HX_PROJ_DONE = 1, HX_G_OFF = 1, HX_GP_DONE = 24, HX_POST_TOG = 1, HX_POST_SEEN = 1, HX_DONE_OFF = 2, HXMUT = 0;
    assign c[9] = legacy_hcx_c; assign d[9] = 9'd0; assign est[9] = 2'b10;   // no port-9 op remains
    assign hcx_c = {mx_cv[11], mx_cd[84*11+:84]};
    reg hcx_srst_n = 0; initial begin while(cyc<1000) @(negedge ck); @(negedge ckv); hcx_srst_n = 1; end
    wire [84:0] hcx_pcmd; wire [8:0] hcx_pd [0:3]; wire [1:0] hcx_pst [0:3];
    wire hcx_gs, hcx_gd, hcx_gf, hcx_ss, hcx_sffn, hcx_sd, hcx_sf; wire [13:0] hcx_graw, hcx_sraw, hcx_scoef; wire [5:0] hcx_slayer;
    ot_s81_hcx_chain_seq #(.PROJ_DONE(HX_PROJ_DONE),.G_OFF(HX_G_OFF),.GP_DONE(HX_GP_DONE),.POST_TOG(HX_POST_TOG),.POST_SEEN(HX_POST_SEEN),
        .DONE_OFF(HX_DONE_OFF),.RAW_BASE(14'd2624),.COEF_BASE(C_BASE),.COEF_STRIDE(14'(C_STRIDE))) u_hcx (
        .ck(ck),.rst_n(mx_rst_n),.skv(ckv),.srst_n(hcx_srst_n),.c_cmd(hcx_c),.c_done(hcx_d),.c_st(hcx_st),
        .p_cmd(hcx_pcmd),.p_done(hcx_pd[0]),.p_st(hcx_pst[0]),.g_start(hcx_gs),.g_raw_base(hcx_graw),.g_done(hcx_gd),.g_fault(hcx_gf),
        .s_start(hcx_ss),.s_ffn(hcx_sffn),.s_layer(hcx_slayer),.s_raw_base(hcx_sraw),.s_coef_base(hcx_scoef),.s_done(hcx_sd),.s_fault(hcx_sf));
    wire [7:0] hcx_rq [0:3]; wire [111:0] hcx_rr [0:3]; reg [7:0] hcx_rv [0:3][0:3]; reg [4095:0] hcx_rd [0:3][0:3];
    wire hcx_tv [0:3]; wire [191:0] hcx_td [0:3];
    integer hcx_reads = 0, hcx_writes = 0, hcx_errs = 0, hcx_cmds = 0, hcx_cmd_cyc [0:1];
    genvar hr;
    generate for (hr = 0; hr < 4; hr = hr + 1) begin : g_hx
        dsfd_sp_hcx_projection #(.RANK(hr),.RL(4),.FAST_CYC(HX_FAST),.HLAYOUT(HXMUT == 1 ? 0 : 1)) u_p (
            .cck(ck),.crst_n(mx_rst_n),.skctl(ckv),.srst_n(hcx_srst_n),.sk_leaf({6{ckv}}),.c_cmd(hcx_pcmd),.c_done(hcx_pd[hr]),
            .c_st(hcx_pst[hr]),.rq_v(hcx_rq[hr]),.rq_row(hcx_rr[hr]),.rs_v(hcx_rv[hr][3]),.rs_d(hcx_rd[hr][3]),
            .t_raw_v(hcx_tv[hr]),.t_raw_d(hcx_td[hr]));
`ifdef OT_HCX_ROM_HIERLOAD
  for (genvar l = 0; l < 6; l++) for (genvar b = 0; b < 8; b++) for (genvar m = 0; m < 4; m++) for (genvar pg = 0; pg < 2; pg++) begin : g_ld
   initial begin string rd; #1;
    if ($value$plusargs("OT_ROM_DIR=%s", rd))
     $readmemh($sformatf("%s/hcx_r%0d_p%0d_b%0d_l%0d_p%0d.viamap.hex", rd, hr, l, b, m, pg), u_p.g_leaf[l].leaf.g_bank[b].g_rom[m].g_page[pg].rom.arr);
   end
  end
`endif
        always @(posedge ckv) begin
            hcx_rv[hr][0] <= hcx_rq[hr];
            for (int p8 = 0; p8 < 8; p8++) begin
                hcx_rd[hr][0][512*p8+:512] <= vm[hcx_rr[hr][14*p8+:14]];
                if (hr == 0 && hcx_rq[hr][p8]) hcx_reads++;
            end
            for (int i = 1; i < 4; i++) begin hcx_rv[hr][i] <= hcx_rv[hr][i-1]; hcx_rd[hr][i] <= hcx_rd[hr][i-1]; end
        end
    end endgenerate
    reg [191:0] hcx_rawq [0:3]; reg hcx_rawseen [0:3];
    initial for (int q = 0; q < 4; q++) hcx_rawseen[q] = 0;
    always @(posedge ckv) for (int q = 0; q < 4; q++) if (hcx_tv[q]) begin hcx_rawq[q] <= hcx_td[q]; hcx_rawseen[q] <= 1; end
    reg hcx_iv = 0; reg [1:0] hcx_irk = 0; reg [511:0] hcx_id = 0; integer hcx_gk = 0, hcx_gq;
    always @(posedge ck) begin
        hcx_iv <= 0;
        if (hcx_gs) hcx_gk <= 1; else if (hcx_gk > 0 && hcx_gk < 16) hcx_gk <= hcx_gk + 1; else hcx_gk <= 0;
        if (hcx_gs || hcx_gk == 4 || hcx_gk == 8 || hcx_gk == 12) begin
            hcx_gq = hcx_gs ? 0 : hcx_gk / 4;
            if (!hcx_rawseen[hcx_gq]) begin hcx_errs++; $display("ERR HCX raw record of rank %0d absent at its gather slot", hcx_gq); end
            hcx_iv <= 1; hcx_irk <= 2'(hcx_gq); hcx_id <= '1; hcx_id[191:0] <= hcx_rawq[hcx_gq]; hcx_rawseen[hcx_gq] <= 0;
        end
    end
    wire hcx_gwv; wire [13:0] hcx_gwa; wire [15:0] hcx_gwm; wire [511:0] hcx_gwd; reg [3:0] hcx_gc = 0;
    reg [13:0] hcx_ga [0:3]; reg [511:0] hcx_gdp [0:3];
    ot_s81_hcx_gatherpack u_hxgp (.clk(ck),.rst_n(mx_rst_n),.start(hcx_gs),.raw_base_row(hcx_graw),.i_v(hcx_iv),.i_rank(hcx_irk),
        .i_d(hcx_id),.wq_v(hcx_gwv),.wq_row(hcx_gwa),.wq_mask(hcx_gwm),.wq_d(hcx_gwd),.wq_commit(hcx_gc[3]),.done(hcx_gd),.fault(hcx_gf));
    always @(posedge ck) begin
        hcx_gc <= {hcx_gc[2:0], hcx_gwv}; hcx_ga[0] <= hcx_gwa; hcx_gdp[0] <= hcx_gwd;
        for (int i = 1; i < 4; i++) begin hcx_ga[i] <= hcx_ga[i-1]; hcx_gdp[i] <= hcx_gdp[i-1]; end
        if (hcx_gc[3]) begin vm[hcx_ga[3]] = hcx_gdp[3]; mark(hcx_ga[3]); end
        if (hcx_c[84]) begin if (hcx_cmds < 2) hcx_cmd_cyc[hcx_cmds] = cyc; hcx_cmds++; end
    end
    wire hcx_srv, hcx_swv; wire [13:0] hcx_sra, hcx_swa; wire [15:0] hcx_swm; wire [511:0] hcx_swd;
    reg [3:0] hcx_sv = 0, hcx_sc = 0; reg [511:0] hcx_sdp [0:3]; reg [13:0] hcx_sap [0:3]; reg [15:0] hcx_smp [0:3]; reg [511:0] hcx_swp [0:3];
    ot_s81_hcx_post_gain_native #(.MUT_POST(HXMUT == 2)) u_hxpost (.clk(ckv),.rst_n(hcx_srst_n),.start(hcx_ss),.gain_mode(1'b0),
        .gain_draft(1'b0),.ffn(hcx_sffn),.raw_base_row(hcx_sraw),.coef_base_row(hcx_scoef),.gain_base_row(14'd4096),
        .layer_idx(hcx_slayer),.norm_eps(32'h1e3ce508),.compiled_cycles(16'd540),.done(hcx_sd),.rq_v(hcx_srv),.rq_row(hcx_sra),
        .rs_v(hcx_sv[3]),.rs_d(hcx_sdp[3]),.wq_v(hcx_swv),.wq_row(hcx_swa),.wq_mask(hcx_swm),.wq_d(hcx_swd),.wq_commit(hcx_sc[3]),
        .fault(hcx_sf));
    always @(posedge ckv) begin
        hcx_sv <= {hcx_sv[2:0], hcx_srv}; hcx_sdp[0] <= vm[hcx_sra]; for (int i = 1; i < 4; i++) hcx_sdp[i] <= hcx_sdp[i-1];
        hcx_sc <= {hcx_sc[2:0], hcx_swv}; hcx_sap[0] <= hcx_swa; hcx_smp[0] <= hcx_swm; hcx_swp[0] <= hcx_swd;
        for (int i = 1; i < 4; i++) begin hcx_sap[i] <= hcx_sap[i-1]; hcx_smp[i] <= hcx_smp[i-1]; hcx_swp[i] <= hcx_swp[i-1]; end
        if (hcx_sc[3]) begin
            for (int w = 0; w < 16; w++) if (hcx_smp[3][w]) vm[hcx_sap[3]][32*w+:32] = hcx_swp[3][32*w+:32];
            mark(hcx_sap[3]); hcx_writes++;
        end
    end
    always @(posedge ck) if (rst && hcx_st[0]) $fatal(1, "HCX chain fault cycle=%0d cfault=%0d post=%0d gather=%0d proj_st=%b ctl_c=%0d ctl_s=%0d",
        cyc, u_hcx.cfault, hcx_sf, hcx_gf, hcx_pst[0], g_hx[0].u_p.controller.cfault, g_hx[0].u_p.controller.sfault);
`else
    assign c[9] = legacy_hcx_c;
`endif
    reg eng_h = 0, eng_done = 0;         // eng_h: the program has an Engram h write (a port-10 op with wrow >= 0)
    reg clr_req = 0;
    task automatic mark(input integer r);
        begin
            if (!vm_ok[r]) begin
                vm_ok[r] = 1'b1;
                if (r >= H_BASE && r < H_BASE + XW) hcnt = hcnt + 1;
                if (r >= G_BASE && r < G_BASE + 2 * GROWS) gcnt[(r - G_BASE) / GROWS] = gcnt[(r - G_BASE) / GROWS] + 1;
            end
        end
    endtask
`ifdef TB_SU_REAL
    reg [15:0]        su_dl_v [0:63];
    reg [16*14-1:0]   su_dl_a [0:63];
    initial for (int z = 0; z < 64; z = z + 1) begin su_dl_v[z] = 0; su_dl_a[z] = 0; end
`endif
    reg [S_RD-1:0]    dl_v [0:63];
    reg [S_RD*14-1:0] dl_a [0:63];
    integer s, i2;
    always @(posedge ck) begin
        if (clr_req) begin
            for (i2 = H_BASE; i2 < H_BASE + XW; i2 = i2 + 1) vm_ok[i2] = 1'b0;
            for (i2 = 0; i2 < 4; i2 = i2 + 1) vm_ok[C_BASE + C_STRIDE * (i2 / 2) + i2 % 2] = 1'b0;   // the 2 x 2 coefficient rows
            hcnt = 0; clr_req = 0; eng_done = 0;
        end
        if (vwe) begin vm[vwa] = vwd; mark(vwa); nwr = nwr + 1; end
`ifndef TB_HCX_REAL
        if (g_eng[9].g_b.jdone_r && o_wr[g_eng[9].g_b.dop_r] >= 0) begin
            vm[o_wr[g_eng[9].g_b.dop_r]] = coefm[o_wr[g_eng[9].g_b.dop_r]]; mark(o_wr[g_eng[9].g_b.dop_r]); end
`endif
`ifndef TB_MIX4_REAL
        if (g_eng[10].g_b.jdone_r && o_wr[g_eng[10].g_b.dop_r] >= 0) begin
            for (i2 = 0; i2 < XW; i2 = i2 + 1) begin
                vm[o_wr[g_eng[10].g_b.dop_r] + i2] = coefm[o_wr[g_eng[10].g_b.dop_r] + i2]; mark(o_wr[g_eng[10].g_b.dop_r] + i2); end
            eng_done = 1;
        end
`endif
        for (s = 0; s < S_WR; s = s + 1) if (wq_v[s]) begin vm[wq_row[14 * s +: 14]] = wq_d[512 * s +: 512]; mark(wq_row[14 * s +: 14]); end
`ifdef TB_SU_REAL
        // the SU's write slots, under each slot's 32-bit word mask (the QN / QB exponent rows are merged word by word),
        // and its S_RD read slots (LVM)
        for (s = 0; s < SU_WR; s = s + 1) if (su_wq_v[s]) begin
            for (i2 = 0; i2 < 16; i2 = i2 + 1)
                if (su_wq_mask[16 * s + i2]) vm[su_wq_row[14 * s +: 14]][32 * i2 +: 32] = su_wq_d[512 * s + 32 * i2 +: 32];
            mark(su_wq_row[14 * s +: 14]);
        end
        for (i2 = 63; i2 > 0; i2 = i2 - 1) begin su_dl_v[i2] = su_dl_v[i2 - 1]; su_dl_a[i2] = su_dl_a[i2 - 1]; end
        su_dl_v[0] = su_rq_v; su_dl_a[0] = su_rq_row;
        su_rs_v <= su_dl_v[LVM - 1];
        for (s = 0; s < SU_RD; s = s + 1) su_rs_d[512 * s +: 512] <= vm[su_dl_a[LVM - 1][14 * s +: 14]];
`endif
        for (i2 = 63; i2 > 0; i2 = i2 - 1) begin dl_v[i2] = dl_v[i2 - 1]; dl_a[i2] = dl_a[i2 - 1]; end
        dl_v[0] = vq_v; dl_a[0] = vq_row;
        rs_v <= dl_v[LVM - 1];
        for (s = 0; s < S_RD; s = s + 1) rs_d[512 * s +: 512] <= vm[dl_a[LVM - 1][14 * s +: 14]];
    end
    // f_inp: the head descriptor's operands are complete in the VM (dropped on the take cycle)
`ifdef TB_HC_HIER
`define HCAD u_hc.u_hc.g_hier.u_cb.u_seq.u_ad
    wire        hdv = u_hc.u_hc.g_hier.u_cb.u_seq.d_v;
    wire [7:0]  hdt = u_hc.u_hc.g_hier.u_cb.u_seq.d_t;
`else
`define HCAD u_hc.u_hc.g_flat.u_ad
    wire        hdv = u_hc.u_hc.g_flat.d_v;
    wire [7:0]  hdt = u_hc.u_hc.g_flat.d_t;
`endif
    wire [83:0] hq = `HCAD.rq;
    wire        hrv = `HCAD.rv;
    wire        htake = u_hc.u_hc.e_v && u_hc.u_hc.e_r;
    wire [3:0]  hkind = hq[30:27];
    wire [13:0] hbase = hq[20:7];
    reg hpres;
    always @* begin
        case (hkind)
            4'd0: hpres = (hbase == H_BASE) ? ((HST != 0) ? !eng_h : ((hcnt == XW) && (!eng_h || eng_done))) : eng_done;
            4'd2: hpres = vm_ok[hbase] && vm_ok[hbase + 1];
            4'd3: hpres = (yrd + YB <= ywr) || y_v;
            4'd5: hpres = (hbase == G_BASE) ? (gcnt[0] == GROWS) : (hbase == G_BASE + GROWS) ? (gcnt[1] == GROWS) : 1'b0;
            default: hpres = 1'b1;
        endcase
    end
    assign hc_inp = INP1 ? 1'b1 : (hrv && hpres && !htake);     // INP1: negative control, f_inp tied 1
    // HC job start (the core takes the descriptor)
    always @(posedge ck) if (u_hc.u_hc.e_v && u_hc.u_hc.e_r) stt[cj][u_hc.u_hc.e_d[6:0]] = cyc;
    // HC job end: the core's done (the job's last result committed); the controller-pin done follows through the adapter
    // (hierarchical slab: the sequencer tile's done BEFORE its DW-cycle done delay to the adapter: the cycle the next
    // job can be taken, the same event as the flat core's done)
    always @(posedge ck) if (hdv) endt[cj][hdt[6:0]] = cyc;
    // ---------------- reference roots (as tb_s81ph_gather_capture)
    reg [NR-1:0] s_v; reg [31:0] s_t [0:NR-1]; reg [31:0] s_d [0:NR-1]; reg [NR-1:0] s_e, s_b;
    wire [NR-1:0] rr_v, rr_e, rr_f;
    wire [NR*16-1:0] rr_row, rr_bf; wire [NR*3-1:0] rr_pos; wire [NR*32-1:0] rr_fp;
    reg rst_n_ref = 0;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_ref_root
        ot_v41_ret_root #(.D(128), .QD(128)) u_root (.clk(ck), .rst_n(rst_n_ref), .i_v(s_v[g]), .i_t(s_t[g]), .i_d(s_d[g]),
            .i_e(s_e[g]), .r_v(rr_v[g]), .r_row(rr_row[16*g +: 16]), .r_pos(rr_pos[3*g +: 3]), .r_fp32(rr_fp[32*g +: 32]),
            .r_bf16(rr_bf[16*g +: 16]), .r_e(rr_e[g]), .fault(rr_f[g]));
    end endgenerate
    reg p_v = 0;
    reg [46:0] p_id = 0; reg [9:0] p_ph = 0; reg [29:0] p_ob = 0, p_ops = 0; reg [2:0] p_np = 0; reg [1:0] p_fmt = 0;
    reg [15:0] p_rs = 0, p_rows = 0; reg p_lo = 0, p_hi = 0;
    wire [128*19-1:0] quota;
    ot_dsrom_s81_phase_capture_profile #(.ENABLE(1)) u_prof (.phase_rows(p_rows), .phase_np(p_np), .root_returns(quota));
    wire [NR-1:0] rv_valid; wire [NR*30-1:0] rv_addr; wire [NR*32-1:0] rv_data;
    wire r_ready, r_live, r_idle, r_drained, r_fault;
    ot_dsrom_rd64_vm_capture #(.ENABLE(1), .ROOTS(NR), .CAPACITY(1), .VM_AW(19), .VM_ALWAYS_ACCEPT(1)) u_rc (
        .clk(ck), .rst_n(rst_n_ref), .reset_request(1'b0), .phase_valid(p_v), .phase_ready(r_ready),
        .phase_identity(p_id), .phase_id(p_ph), .phase_root_rows(quota), .phase_obase(p_ob), .phase_ops(p_ops),
        .phase_np(p_np), .phase_fmt(p_fmt), .phase_rsplit(p_rs), .phase_fp32_low(p_lo), .phase_fp32_high(p_hi),
        .r_valid(rr_v), .r_error(rr_e), .r_row(rr_row), .r_bf16(rr_bf), .r_pos(rr_pos), .r_fp32(rr_fp),
        .vm_valid(rv_valid), .vm_accept(rv_valid), .vm_addr(rv_addr), .vm_data(rv_data), .vm_row(), .vm_pos(),
        .held_identity(), .held_phase(), .phase_live(r_live), .phase_idle(r_idle), .phase_drained(r_drained),
        .fault(r_fault));
    wire ref_fault = r_fault | (|rr_f);
    localparam integer NC [0:5] = '{10, 11, 11, 11, 11, 10};
    function automatic integer port_of(input integer r);
        integer h, t, bb;
        begin h = r / 64; bb = h * 64; port_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (port_of < 0 && r < bb + NC[t]) port_of = 6 * h + t; bb = bb + NC[t]; end end
    endfunction
    function automatic integer lane_of(input integer r);
        integer h, t, bb;
        begin h = r / 64; bb = h * 64; lane_of = -1;
            for (t = 0; t < 6; t = t + 1) begin if (lane_of < 0 && r < bb + NC[t]) lane_of = NC[t] - 1 - (r - bb); bb = bb + NC[t]; end end
    endfunction
    integer pi, li, rr;
    always @* begin
        for (pi = 0; pi < 12; pi = pi + 1) begin
            tp[pi] = 761'd0;
            tp[pi][69 * NC[pi % 6] +: 2] = 2'b01;
        end
        for (rr = 0; rr < NR; rr = rr + 1) begin
            pi = port_of(rr); li = lane_of(rr);
            tp[pi][69 * li] = s_v[rr];
            tp[pi][69 * li + 1 +: 68] = {1'b0, s_b[rr], s_e[rr], s_d[rr], s_t[rr], s_v[rr]};
        end
    end
    reg [50:0] refq [0:NR-1][$];
    reg [50:0] dutq [0:NR-1][$];
    integer k;
    always @(posedge ck) for (k = 0; k < NR; k = k + 1) if (rv_valid[k]) refq[k].push_back({rv_data[32*k +: 32], rv_addr[30*k +: 19]});
    always @(posedge ckv) for (k = 0; k < NR; k = k + 1) begin
        if (tvm[104*k]) dutq[k].push_back(tvm[104*k + 1 +: 51]);
        if (tvm[104*k + 52]) dutq[k].push_back(tvm[104*k + 53 +: 51]);
    end
    // ---------------- behavioural engines behind real slab endpoints (ports 1, 4..11; 9 = hcx)
    genvar ge;
    generate for (ge = 1; ge < 12; ge = ge + 1) begin : g_eng
        if (ge != 2 && ge != 3 && !(ge == 1 && SUR) && !(ge == 10 && MXR) && !(ge == 9 && HCXR)) begin : g_b
            wire jv, jnew, epf; wire [83:0] jd, jnd;
            reg jdone_r = 1'b0, busy = 1'b0; integer rem = 0; reg [6:0] dop_r = 0;
            ot_s81_slab_ep #(.QD(8), .JQ(2)) u_ep (.c_clk(ck), .c_rst_n(rst), .c_cmd(c[ge]), .c_done(d[ge]), .c_st(est[ge]),
                .e_clk(ck), .e_rst_n(rst), .j_v(jv), .j_d(jd), .j_new(jnew), .j_new_d(jnd), .j_present(1'b1),
                .j_done(jdone_r), .slab_fault(1'b0), .ep_fault(epf));
            always @(posedge ck) begin
                jdone_r <= 1'b0;
                if (jv && !jdone_r) begin
                    if (!busy) begin
                        if (ready_op(cj, jd[6:0])) begin
                            busy <= 1'b1; rem <= (o_dur[jd[6:0]] > 0) ? o_dur[jd[6:0]] : 1; stt[cj][jd[6:0]] = cyc;
                            if (o_port[jd[6:0]] != ge) begin errors = errors + 1; $display("ERR engine %0d got op %0d of port %0d", ge, jd[6:0], o_port[jd[6:0]]); end
                        end
                    end else if (rem <= 1) begin
                        jdone_r <= 1'b1; busy <= 1'b0; endt[cj][jd[6:0]] = cyc; dop_r <= jd[6:0];
                    end else rem <= rem - 1;
                end
            end
        end
    end endgenerate
    always @(posedge ck) begin
        if (u_g.jnew) stt[cj][u_g.jnd[6:0]] = cyc;
        if (u_g.dn) endt[cj][u_g.jd[6:0]] = cyc;
    end
    // ---------------- done order at the controller pins (ports 2 / 3: the slab's done is the job's end)
    integer ndone = 0, maxlat = 0, t_hstore = -1, t_layer0 = -1;
    integer e2, s2, t2;
    always @(posedge ck) if (rst) for (e2 = 0; e2 < 12; e2 = e2 + 1) if (d[e2][8]) begin
        s2 = d[e2][7]; t2 = d[e2][6:0];
        if (e2 == 3 && endt[cj][t2] < 0) endt[cj][t2] = cyc;
        if (e2 == 2 && t2 == nop - 1 && t_hstore < 0) t_hstore = cyc;
        while (nxt[e2] < nop && o_port[nxt[e2]] != e2) nxt[e2] = nxt[e2] + 1;
        if (nxt[e2] != t2) begin
            errors = errors + 1;
            if (errors < 10) $display("ERR done order: port %0d slot %0d got op %0d expected %0d", e2, s2, t2, nxt[e2]);
        end else nxt[e2] = nxt[e2] + 1;
        if (endt[cj][t2] < 0) begin errors = errors + 1; $display("ERR done before engine end: port %0d op %0d", e2, t2); end
        else if (cyc - endt[cj][t2] > maxlat) maxlat = cyc - endt[cj][t2];
        ndone = ndone + 1;
    end
    integer jdn = 0;
    always @(posedge ck) if (`SEQ.job_done) jdn <= jdn + 1;
    // ---------------- bench VM: post the field phase words in fld order when the job's inputs are present
    integer pj = 0, pk = 0, posted = 0, released = 0;
    always @(posedge ck) if (xgo[10]) released <= released + 1;
    function automatic integer next_fld(input integer from);
        integer qq; begin next_fld = nop; for (qq = nop - 1; qq >= from; qq = qq - 1) if (o_ph[qq] >= 0) next_fld = qq; end
    endfunction
    initial begin : vm_post
        integer ph;
        wait (rst && plen != 0);
        pk = next_fld(0);
        while (pj < JOBS) begin
            @(negedge ckv);
            if (pk >= nop) begin pj = pj + 1; pk = next_fld(0); end
            else if (posted - released < 3 && ready_op(pj, pk)) begin
                ph = o_ph[pk];
                f_vm = 0; f_vm[0] = 1;
                f_vm[159:1] = {1'b0, ph_par[ph][0][15:0], ph_par[ph][7][0], ph_par[ph][6][0], ph_par[ph][5][15:0],
                               ph_par[ph][4][1:0], ph_par[ph][1][2:0], ph_par[ph][3][29:0], ph_par[ph][2][29:0],
                               ph_par[ph][9][9:0], ph_par[ph][8][46:0], 2'b00};
                @(negedge ckv); f_vm[0] = 0;
                posted = posted + 1;
                pk = next_fld(pk + 1);
            end
        end
    end
    // ---------------- field model: the x broadcast of a released phase -> its golden partials
    integer nfp = 0;
    initial begin : field
        integer ph, ci, j;
        s_v = 0; s_e = 0; s_b = 0;
        for (j = 0; j < NR; j = j + 1) begin s_t[j] = 0; s_d[j] = 0; end
        forever begin
            @(posedge ck); #0.1;
            if (xgo[10]) begin
                ph = xgo[9:0];
                @(negedge ck);
                p_rows = ph_par[ph][0]; p_np = ph_par[ph][1]; p_ob = ph_par[ph][2]; p_ops = ph_par[ph][3]; p_fmt = ph_par[ph][4];
                p_rs = ph_par[ph][5]; p_lo = ph_par[ph][6]; p_hi = ph_par[ph][7]; p_id = ph_par[ph][8]; p_ph = ph_par[ph][9];
                for (j = 0; j < 256 && !r_ready; j = j + 1) @(negedge ck);
                if (!r_ready) begin errors = errors + 1; $display("ERR reference not ready at phase %0d", ph); end
                p_v = 1; @(negedge ck); p_v = 0;
                for (j = 0; j < 30; j = j + 1) @(negedge ck);
                begin : drive
                    reg [NR-1:0] n_v, n_e; reg [31:0] n_t [0:NR-1]; reg [31:0] n_d [0:NR-1];
                    n_v = 0; n_e = 0;
                    for (ci = ph_c0[ph]; ci < ph_c0[ph] + ph_cn[ph]; ci = ci + 1) begin
                        if (c_gap[ci] != 0) begin
                            for (j = 0; j < NR; j = j + 1) begin s_v[j] = n_v[j]; s_t[j] = n_t[j]; s_d[j] = n_d[j]; s_e[j] = n_e[j]; s_b[j] = $random; end
                            n_v = 0; n_e = 0;
                            @(negedge ck); s_v = 0;
                            for (j = 1; j < c_gap[ci]; j = j + 1) @(negedge ck);
                        end
                        n_v[c_root[ci]] = 1; n_t[c_root[ci]] = c_t[ci]; n_d[c_root[ci]] = c_d[ci]; n_e[c_root[ci]] = c_e[ci];
                    end
                    for (j = 0; j < NR; j = j + 1) begin s_v[j] = n_v[j]; s_t[j] = n_t[j]; s_d[j] = n_d[j]; s_e[j] = n_e[j]; s_b[j] = $random; end
                    @(negedge ck); s_v = 0;
                end
                nfp = nfp + 1;
            end
        end
    end
    // ---------------- the stage hand-off (HTX): the real hop framer reads the layer output rows from the bench VM and
    // hands them to a link that takes one flit a cycle (the priced hop: 640 payload flits + header)
    reg [511:0] gs [0:XW-1];             // golden layer output rows by index
    reg         gs_ok [0:XW-1];
    integer t_hgo = -1, t_hx0 = -1, t_hx1 = -1, tx_ok = 0, tx_bad = 0, tx_early = 0, tx_n = 0, swr = 0, t_sw0 = -1,
            t_land1 = -1, tx_lead_min = 1 << 30, tx_rd = 0, hst_take = -1, t_pay0 = -1;
    reg  hx_cmd = 0, hx_go = 0, hx_go_done = 0;
    wire hx_re, hx_ov, hx_ol, hx_dn, hx_flt; wire [13:0] hx_ra; reg [511:0] hx_rq = 0; wire [511:0] hx_od;
    wire [7:0] hx_dt; wire [3:0] hx_fc;
    generate if (HTX != 0) begin : g_htx
        ot_s81_hop_tx #(.WINDOW_CONTEXT(0), .MY_ID(2), .FLIT(512), .NW(21), .USER_W(12), .VWA(14), .XW(XW), .TXB(S_BASE),
                        .CMDW(84), .OPW(7), .ARGW(24), .SUW(10), .USE_VM_RVALID(0), .OUT_DEPTH(8), .QD(8)) u_tx (
            .clk(ck), .rst_n(rst), .win_ctx_v(1'b0), .win_ctx_slot(1'b0), .win_ctx_user(12'd0), .win_ctx_pos(21'd0),
            .win_ctx_tok(21'd0), .win_ctx_ids(68'd0), .win_ctx_dead(1'b0),
            .cmd_v(hx_cmd), .cmd_d({1'b0, 10'd0, 21'd0, 21'd1000, {8'd0, 12'd3, 4'd1}, 7'd0}), .dn_v(hx_dn), .dn_tag(hx_dt),
            .go(hx_go), .res_v(1'b0), .res_tok(21'd0), .res_val(32'd0), .res_stop(1'b0), .run_eosen(1'b0), .run_eos(21'd0),
            .run_maxl(22'd0), .vm_re(hx_re), .vm_raddr(hx_ra), .vm_rq(hx_rq), .vm_rvalid(1'b0),
            .out_valid(hx_ov), .out_ready(1'b1), .out_data(hx_od), .out_last(hx_ol), .fault(hx_flt), .fault_code(hx_fc),
            .st_msgs());
    end else begin : g_nhtx
        assign hx_re = 1'b0; assign hx_ra = 14'd0; assign hx_ov = 1'b0; assign hx_ol = 1'b0; assign hx_dn = 1'b0;
        assign hx_flt = 1'b0; assign hx_od = 512'd0; assign hx_dt = 8'd0; assign hx_fc = 4'd0;
    end endgenerate
    integer sx, hout_fd = 0, hin_bad = 0, hin_n = 0;
    reg [511:0] hin_m [0:XW];
    always @(posedge ck) begin
        // landing: the cycle of the last HIDDEN row
        if (vwe && vwa == H_BASE + XW - 1 && t_land1 < 0) t_land1 = cyc;
        // H_STORE rows written (the hand-off's input)
        for (sx = 0; sx < S_WR; sx = sx + 1) if (wq_v[sx] && wq_row[14 * sx +: 14] >= S_BASE) begin
            swr = swr + 1; if (t_sw0 < 0) t_sw0 = cyc; end
        if (htake && hkind == 4'd1 && hst_take < 0) hst_take = cyc;
        hx_cmd <= 1'b0; hx_go <= 1'b0;
        if (HTX != 0 && rst && ctl_up && cj == 0 && !hx_go_done) begin
            if (t_hgo == -1) begin hx_cmd <= 1'b1; t_hgo = -2; end                      // the descriptor is queued at the job start
            else if ((HTX == 1 && t_hstore >= 0) || (HTX == 2 && swr >= HWM) || (HTX == 3 && hst_take >= 0)) begin
                hx_go <= 1'b1; hx_go_done <= 1'b1; t_hgo = cyc;
            end
        end
        // the VM's registered read (data on vm_rq two edges after the issue)
        if (hx_re) begin
            hx_rq <= vm[hx_ra];
            if (!vm_ok[hx_ra]) begin tx_early = tx_early + 1; if (tx_early < 4) $display("ERR hop TX read row %0d before it was written (cyc %0d)", hx_ra, cyc); end
            tx_rd = tx_rd + 1;
            if (swr < XW && swr - tx_rd < tx_lead_min) tx_lead_min = swr - tx_rd;   // rows written ahead of the reader while the store runs
        end
        if (hx_ov) begin
            if (hout_fd != 0) $fdisplay(hout_fd, "%0128h", hx_od);
            if (tx_n == 0) t_hx0 = cyc;
            else if (tx_n <= XW) begin
                if (gs_ok[tx_n - 1] && hx_od === gs[tx_n - 1]) tx_ok = tx_ok + 1;
                else begin tx_bad = tx_bad + 1; if (tx_bad < 4) $display("ERR hop TX flit %0d != golden layer output row (cyc %0d)", tx_n - 1, cyc); end
            end
            if (hx_ol) t_hx1 = cyc;
            tx_n = tx_n + 1;
        end
        if (hx_flt || hl_flt) begin errors = errors + 1; if (errors < 20) $display("ERR hand-off fault: hop_tx %b code %0d, hland %b code %0d (cyc %0d)", hx_flt, hx_fc, hl_flt, hl_fc, cyc); end
    end
    // ---------------- main
    task automatic send_flit(input [511:0] dt, input ll);
        begin
            i_v = 1; i_d = dt; i_l = ll;
            while (!i_r) @(negedge ck);
            if (t_layer0 < 0) t_layer0 = cyc;
            @(negedge ck);
        end
    endtask
    initial begin : main
        integer kit_ok;
        integer fd, rc, w, jb, e, bad, tot, tr, td, gst_f, n_ok, n_bad, st_ok, st_bad, m, r0, pt, xm, su_ok, su_bad;
        reg [8*8-1:0] cmd; reg [63:0] a [0:9];
        reg [511:0] hdr;
        for (jb = 0; jb < 4; jb = jb + 1) for (w = 0; w < 128; w = w + 1) begin endt[jb][w] = -1; stt[jb][w] = -1; end
        for (e = 0; e < 12; e = e + 1) nxt[e] = 0;
        for (w = 0; w < 16384; w = w + 1) begin vm[w] = 0; vm_ok[w] = 0; coefm[w] = 0; end
        gcnt[0] = 0; gcnt[1] = 0;
        for (dd = 0; dd < 4; dd = dd + 1) begin
            sp[dd] = 0; dn[dd] = 0; cfgd[dd] = 0; fvm[dd] = 0; tsr[dd] = 0;
            for (q = 0; q < 6; q = q + 1) cr[dd][q] = (q == 0) ? 16 : 8;
        end
        for (w = 0; w < 64; w = w + 1) begin dl_v[w] = 0; dl_a[w] = 0; end
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        begin : hio
            string hf;
            if ($value$plusargs("HIN=%s", hf)) begin
                for (w = 0; w <= XW; w = w + 1) hin_m[w] = 'x;
                $readmemh(hf, hin_m); hin_n = XW + 1;
                for (w = 0; w <= XW; w = w + 1) if (^hin_m[w] === 1'bx) begin hin_n = 0; $display("ERR HIN %s: flit %0d missing", hf, w); end
                if (hin_n == 0) errors = errors + 1;
            end
            if ($value$plusargs("HOUT=%s", hf)) hout_fd = $fopen(hf, "w");
        end
        fd = $fopen({dir, "/prog.txt"}, "r");
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%d %d %d %d %d %d %d %d %d %d %d\n", o_port[nop], o_arg[nop], o_dur[nop], o_np[nop],
                         o_p[nop][0], o_p[nop][1], o_p[nop][2], o_p[nop][3], o_ph[nop], o_cm[nop], o_wr[nop]);
            if (rc == 11) begin if (o_port[nop] == 10 && o_wr[nop] >= 0) eng_h = 1; nop = nop + 1; end
        end
        $fclose(fd);
        fd = $fopen({dir, "/stim.txt"}, "r");
        while (!$feof(fd)) begin
            rc = $fscanf(fd, "%s", cmd);
            if (rc != 1) break;
            if (cmd == "P") begin
                rc = $fscanf(fd, "%h %h %h %h %h %h %h %h %h %h", a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8], a[9]);
                for (w = 0; w < 10; w = w + 1) ph_par[nph][w] = a[w];
                ph_c0[nph] = ncl; ph_cn[nph] = 0; nph = nph + 1;
            end else if (cmd == "C") begin
                rc = $fscanf(fd, "%h %h %h %h %h", a[0], a[1], a[2], a[3], a[4]);
                c_gap[ncl] = a[0]; c_root[ncl] = a[1]; c_t[ncl] = a[2]; c_d[ncl] = a[3]; c_e[ncl] = a[4];
                ncl = ncl + 1; ph_cn[nph - 1] = ph_cn[nph - 1] + 1;
            end
        end
        $fclose(fd);
        $readmemh({dir, "/n.mem"}, nm);
        NE = nm[0]; TOT = nm[1]; NMSG = nm[2]; NY = nm[3]; NST = nm[4];
        $readmemh({dir, "/payload.mem"}, payload);
        $readmemh({dir, "/y_gold.mem"}, ygold);
        $readmemh({dir, "/expa.mem"}, ea);
        $readmemh({dir, "/expd.mem"}, ed);
        $readmemh({dir, "/vm_boot.mem"}, vm);
        $readmemh({dir, "/coef.mem"}, coefm);
`ifdef TB_SU_REAL
        $readmemh({dir, "/su_n.mem"}, su_nm); SUN = su_nm[0];
        $readmemh({dir, "/su_expa.mem"}, su_ea);
        $readmemh({dir, "/su_expd.mem"}, su_ed);
`endif
        // rows present in the VM at job start (written before this layer: boot_ok.txt, empty unless --coef-split)
        fd = $fopen({dir, "/boot_ok.txt"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%d\n", w) == 1) mark(w); $fclose(fd); end
        begin : own_load
            reg [511:0] tmp [0:4*MAXR-1];
            $readmemh({dir, "/coll_own.mem"}, tmp);
            for (w = 0; w < TOT; w = w + 1) for (dd = 0; dd < 4; dd = dd + 1) own[dd][w] = tmp[4 * w + dd];
        end
        fd = $fopen({dir, "/coll_msg.txt"}, "r");
        r0 = 0;
        for (m = 0; m < NMSG; m = m + 1) begin
            rc = $fscanf(fd, "%d %d\n", m_mode[m], m_n[m]); m_r0[m] = r0;
            for (w = 0; w < m_n[m]; w = w + 1) begin ownl[r0 + w] = (w == m_n[m] - 1); ownm[r0 + w] = m_mode[m][0]; ownt[r0 + w] = r0 + w; end
            r0 = r0 + m_n[m];
        end
        $fclose(fd);
        m_op[NMSG] = 0;
        for (w = 0; w < nop; w = w + 1) if (o_cm[w] >= 0) m_op[o_cm[w]] = w;
        for (w = G_BASE; w < G_BASE + 2 * GROWS; w = w + 1) mark(w);     // gain sets: boot image
        for (w = 0; w < XW; w = w + 1) gs_ok[w] = 1'b0;
        for (w = 0; w < NE; w = w + 1) if (ea[w] >= S_BASE && ea[w] < S_BASE + XW) begin gs[ea[w] - S_BASE] = ed[w]; gs_ok[ea[w] - S_BASE] = 1'b1; end
        if (r0 != TOT) $fatal(1, "coll records %0d != %0d", r0, TOT);
        $display("TB_S81_DIE_LAYER program %0d ops, %0d field phases, %0d partials, %0d coll messages / %0d records, %0d y words, %0d golden rows (%0d H_STORE), MUT %0d HMUT %0d NG %0d",
                 nop, nph, ncl, NMSG, TOT, NY, NE, NST, MUT, HMUT, NG);
        // reset: the collective group's resets first (PLL lock), then the die controller and slabs
        wait (rsts == 4'hF);
        repeat (10) @(negedge ck);
        rst = 1; rsv = 1; rst_n_ref = 1;
        repeat (60) @(negedge ck);
`ifdef TB_SEQC
        // f_pw has no ready: the kit paces program writes (one per 4 ckv cycles) so the 4-deep async FIFO never fills
        for (w = 0; w < nop; w = w + 1) begin f_pw = {1'b1, 7'(w), o_port[w][3:0], o_arg[w][23:0]}; @(negedge ckv); f_pw = 0; repeat (3) @(negedge ckv); end
        f_pw = 0; plen = nop;
        repeat (8) @(negedge ckv);
`else
        for (w = 0; w < nop; w = w + 1) begin
            pw_v = 1; pw_a = w; pw_d = {o_port[w][3:0], o_arg[w][23:0]}; @(negedge ck);
        end
        pw_v = 0; plen = nop;
`endif
        // peer programs: the coll messages
        for (m = 0; m < NMSG; m = m + 1) begin pk_v = 1; pk_a = m; pk_d = {4'd3, 7'd0, m_mode[m][0], 16'(m_n[m])}; @(negedge ck); end
        pk_v = 0; pk_len = NMSG;
        repeat (4) @(negedge ck);
        peer_go = 1;
        // the links are trained before the token arrives (collective first-send point of the coll gate)
        while (cyc < 1200) @(negedge ck);
        ctl_up = 1;
`ifdef TB_SEQC
        // the kit: start job j after job j-1's kit done, then land the HIDDEN payload rows in the VM (one a cycle)
        for (jb = 0; jb < JOBS; jb = jb + 1) begin
            while (kdn < jb && cyc < TMAX) @(negedge ck);
            if (jb > 0) begin clr_req = 1; @(negedge ck); end
            @(negedge ckv); f_ks = {1'b1, 10'd0, 21'(1000 + jb), 21'(jb)}; @(negedge ckv); f_ks = 0;
            if (t_layer0 < 0) t_layer0 = cyc;
            for (w = 0; w < XW; w = w + 1) begin @(negedge ck); vwe = 1; vwa = H_BASE + w; vwd = payload[w]; end
            @(negedge ck); vwe = 0;
        end
`else
        hdr = 0; hdr[11:0] = 2; hdr[23:12] = 1; hdr[27:24] = 1; hdr[39:28] = XW; hdr[51:40] = 0; hdr[72:52] = 0;
        hdr[146:126] = 1000;
        send_flit(hdr, 1'b0);
        i_v = 0; repeat (PGAP) @(negedge ck);
        t_pay0 = cyc;
        if (hin_n > 0) for (w = 0; w < XW; w = w + 1) begin
            if (hin_m[w + 1] !== payload[w]) begin hin_bad = hin_bad + 1; if (hin_bad < 4) $display("ERR HIN row %0d != golden layer-entry h", w); end
            send_flit(hin_m[w + 1], w == XW - 1);
        end
        else for (w = 0; w < XW; w = w + 1) send_flit(payload[w], w == XW - 1);
        i_v = 0; i_l = 0;
`endif
        while (jdn < JOBS && cyc < TMAX) @(negedge ck);
        if (HTX != 0) while (t_hx1 < 0 && cyc < TMAX) @(negedge ck);
        repeat (600) @(negedge ck);
        // ---- compare: capture writes
        bad = 0; tot = 0;
        for (k = 0; k < NR; k = k + 1) begin
            tr = refq[k].size(); td = dutq[k].size(); tot = tot + tr;
            if (tr != td) begin bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d: ref %0d writes, dut %0d", k, tr, td); end
            else begin
                refq[k].sort(); dutq[k].sort();
                for (rr = 0; rr < tr; rr = rr + 1) if (refq[k][rr] != dutq[k][rr]) begin
                    bad = bad + 1; if (bad < 6) $display("MISMATCH root %0d sorted write %0d: ref %h dut %h", k, rr, refq[k][rr], dutq[k][rr]); break; end
            end
        end
        // ---- the HC rows: NORM outputs and the layer output (H_STORE)
        n_ok = 0; n_bad = 0; st_ok = 0; st_bad = 0;
        for (w = 0; w < NE; w = w + 1) begin
            if (vm[ea[w]] === ed[w]) begin if (ea[w] >= S_BASE) st_ok = st_ok + 1; else n_ok = n_ok + 1; end
            else begin
                if (ea[w] >= S_BASE) st_bad = st_bad + 1; else n_bad = n_bad + 1;
                if (n_bad + st_bad < 6) $display("MISMATCH VM row %0d got %h want %h", ea[w], vm[ea[w]][63:0], ed[w][63:0]);
            end
        end
        // ---- the SU result rows (TB_SU_REAL)
        su_ok = 0; su_bad = 0;
`ifdef TB_SU_REAL
        for (w = 0; w < SUN; w = w + 1)
            if (vm[su_ea[w]] === su_ed[w]) su_ok = su_ok + 1;
            else begin su_bad = su_bad + 1; if (su_bad < 6) $display("MISMATCH SU VM row %0d got %h want %h", su_ea[w], vm[su_ea[w]][63:0], su_ed[w][63:0]); end
        $display("SU_REAL jobs_taken=%0d rows_exact=%0d/%0d bad=%0d fault=%0d code=%0d SUMUT=%0d SUXMUT=%0d", su_nj, su_ok, SUN, su_bad, su_flt, su_fc, SUMUT, SUXMUT);
        if (su_flt) errors = errors + 1;
`endif
        // ---- dataflow
        for (jb = 0; jb < JOBS; jb = jb + 1) for (w = 0; w < nop; w = w + 1) begin
            if (endt[jb][w] < 0) begin errors = errors + 1; if (errors < 20) $display("ERR job %0d op %0d never ended (port %0d)", jb, w, o_port[w]); end
            for (e = 0; e < o_np[w]; e = e + 1) begin
                pt = o_p[w][e];
                if (o_port[w] == 2 && o_port[pt] == 3) begin
                    if (endt[jb][w] >= 0 && endt[jb][w] < endt[jb][pt]) begin errors = errors + 1; $display("ERR op %0d (HC POST) ended %0d before its all-reduce %0d ended %0d", w, endt[jb][w], pt, endt[jb][pt]); end
                end else if (stt[jb][w] < 0 || stt[jb][w] < endt[jb][pt]) begin
                    errors = errors + 1; $display("ERR job %0d op %0d started %0d before pred %0d ended %0d", jb, w, stt[jb][w], pt, endt[jb][pt]); end
            end
        end
        gst_f = 0; for (e = 0; e < 12; e = e + 1) if (est[e][0]) begin gst_f = gst_f + 1; $display("ERR endpoint %0d fault", e); end
        xm = 0;
        for (dd = 0; dd < 4; dd = dd + 1) if (dn[dd] != rn[dd] || ridx[dd] != TOT * JOBS) begin xm = xm + 1; $display("ERR DIE %0d coll INCOMPLETE dut %0d ref %0d of %0d", dd, dn[dd], rn[dd], TOT); end
        if (g_die[1].g_peer.ndn != NMSG * JOBS || g_die[2].g_peer.ndn != NMSG * JOBS || g_die[3].g_peer.ndn != NMSG * JOBS) begin xm = xm + 1; $display("ERR peer dones incomplete"); end
`ifdef TB_SEQC
        kit_ok = (kdn == JOBS);
        $display("KIT starts %0d kit_dones %0d t_st %b", JOBS, kdn, t_st);
`else
        kit_ok = 1;
`endif
        // per-op timing dump (rom-layer-tput 2026-10-13): cycles of every op of job 0, for the per-class throughput record
        for (w = 0; w < nop; w = w + 1) $display("OPT %0d port %0d dur %0d start %0d end %0d", w, o_port[w], o_dur[w], stt[0][w], endt[0][w]);
        if (hout_fd != 0) $fclose(hout_fd);
        $display("HIO hin=%0d hin_bad=%0d hout=%0d", hin_n, hin_bad, hout_fd != 0);
        if (hin_bad != 0) errors = errors + 1;
`ifdef TB_HCX_REAL
        $display("HCX_REAL commands=%0d at %0d,%0d rank0_h_row_reads=%0d post_vm_writes=%0d raw_gather_errors=%0d golden_coefficient_injection=0 native_layer=0",
            hcx_cmds, hcx_cmd_cyc[0], hcx_cmd_cyc[1], hcx_reads, hcx_writes, hcx_errs);
        if (hcx_cmds != 2*JOBS || hcx_reads != 2*640*JOBS || hcx_errs) begin errors++; $display("ERR HCX chain transaction count"); end
`endif
`ifdef TB_MIX4_REAL
        $display("MIX4_REAL reads=%0d writes=%0d golden_output_injection=0 native_layer=0", mx_reads, mx_writes);
        if(mx_reads != JOBS*4161 || mx_writes != JOBS*640) begin errors++; $display("ERR MIX4 transaction count"); end
`endif
        $display("SUMMARY jobs=%0d layer_cycles=%0d (header %0d -> H_STORE done %0d) stage_done_cycle=%0d jobs_done=%0d/%0d dones=%0d/%0d phases_released=%0d field_phases=%0d capture_writes=%0d mismatching_roots=%0d coll_words_die0=%0d coll_errors=%0d coll_incomplete=%0d y_exact=%0d/%0d y_bad=%0d y_consumed=%0d norm_rows_exact=%0d/%0d hstore_rows_exact=%0d/%0d ref_fault=%0d dut_fault=%0d ctrl_flt=%0d fvec=%h stuck=%0d ep_faults=%0d gather_stage_fault=%0d hc_fcode=%0d max_done_latency=%0d errors=%0d first_coll_send=%0d",
                 JOBS, t_hstore - t_layer0, t_layer0, t_hstore, cyc, jdn, JOBS, ndone, JOBS * nop, released, nfp, tot, bad, dn[0], coll_err, xm,
                 y_ok, NY * JOBS, y_bad, yrd, n_ok, NE - NST, st_ok, NST, ref_fault, dst[3], flt, fvec, stk, gst_f, u_g.sf, hfcode, maxlat, errors, first_send_cyc);
        // h transfer record (rom-layer-tput 2026-10-13)
        $display("XFER PIPE=%0d HST=%0d HLMUT=%0d HTX=%0d HWM=%0d LVM=%0d | landing last row %0d (header %0d) hland stream=%0d vm=%0d | H_STORE take %0d first row written %0d rows %0d done %0d | hop go %0d first flit %0d last flit %0d flits %0d exact %0d/%0d bad %0d early_reads %0d min_lead_rows %0d | xfer_cycles=%0d (header -> last hand-off flit) | PGAP=%0d first payload flit %0d layer_adj=%0d xfer_adj=%0d (from the cycle before the first payload flit)",
                 PIPE, HST, HLMUT, HTX, HWM, LVM, t_land1, t_layer0, hl_ns, hl_nv, hst_take, t_sw0, swr, t_hstore, t_hgo, t_hx0, t_hx1, tx_n, tx_ok, XW, tx_bad, tx_early,
                 (tx_lead_min < (1 << 30)) ? tx_lead_min : -1, (t_hx1 >= 0) ? t_hx1 - t_layer0 : -1,
                 PGAP, t_pay0, (t_pay0 >= 0) ? t_hstore - (t_pay0 - 1) : t_hstore - t_layer0,
                 (t_hx1 >= 0) ? t_hx1 - ((t_pay0 >= 0) ? t_pay0 - 1 : t_layer0) : -1);
        if (HTX != 0 && !(tx_ok == XW && tx_bad == 0 && tx_early == 0 && tx_n == XW + 1 && t_hx1 >= 0)) begin
            errors = errors + 1; $display("ERR stage hand-off: %0d/%0d flits exact, %0d bad, %0d early reads, %0d flits", tx_ok, XW, tx_bad, tx_early, tx_n); end
        if (bad == 0 && errors == 0 && jdn == JOBS && ndone == JOBS * nop && !ref_fault && !dst[3] && !flt && gst_f == 0 && !u_g.sf &&
            tot > 0 && coll_err == 0 && xm == 0 && y_ok == NY * JOBS && y_bad == 0 && yrd == NY * JOBS && kit_ok && n_ok == NE - NST && st_ok == NST && n_bad == 0 && st_bad == 0 &&
            su_bad == 0 && (!SUR || su_ok > 0))
            $display("TB_S81_DIE_LAYER PASS");
        else $display("TB_S81_DIE_LAYER FAIL");
        $finish;
    end

    // Optional fixed-cycle workload evidence. This observes existing signals;
    // it never gates an issue or changes latency. Golden/behavioural producers
    // are explicitly labelled so this trace cannot claim a fully native token.
    integer vm_trace_fd = 0;
    reg [7:0] vm_trace_hc_tag = 0, vm_trace_su_tag = 0;
    always @(posedge ck) if (htake) vm_trace_hc_tag <= {u_hc.u_hc.e_d[83],u_hc.u_hc.e_d[6:0]};
`ifdef TB_SU_REAL
    always @(posedge ck) if (su_take) vm_trace_su_tag <= {u_su.u_ctl.e_d[83],u_su.u_ctl.e_d[6:0]};
`endif
    string vm_trace_path;
    initial if ($value$plusargs("VM_TRACE=%s", vm_trace_path)) begin
        vm_trace_fd = $fopen(vm_trace_path, "w");
        if (!vm_trace_fd) $fatal(1, "cannot open VM_TRACE");
        $fwrite(vm_trace_fd, "time_ns,stream_cycle,job,client,event,slot,row,mask,tag\n");
    end
    always @(posedge ck) if (vm_trace_fd && rst) begin
        if (d[2][8]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,hc,done,0,-1,0000,%0d\n",$realtime,cyc,cj,d[2][7:0]);
`ifdef TB_SU_REAL
        if (d[1][8]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,su,done,0,-1,0000,%0d\n",$realtime,cyc,cj,d[1][7:0]);
`endif
        if (htake) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,hc,start,0,-1,0000,%0d\n",$realtime,cyc,cj,{u_hc.u_hc.e_d[83],u_hc.u_hc.e_d[6:0]});
        if (hdv) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,hc,core_done,0,-1,0000,%0d\n",$realtime,cyc,cj,hdt);
`ifdef TB_SU_REAL
        if (su_take) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,su,start,0,-1,0000,%0d\n",$realtime,cyc,cj,{u_su.u_ctl.e_d[83],u_su.u_ctl.e_d[6:0]});
        if (u_su.u_ctl.d_v) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,su,core_done,0,-1,0000,%0d\n",$realtime,cyc,cj,u_su.u_ctl.d_t);
`endif
        for (integer z = 0; z < S_RD; z = z + 1) begin
            if (vq_v[z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,hc,read,%0d,%0d,ffff,%0d\n", $realtime, cyc, cj, z, vq_row[14*z+:14], vm_trace_hc_tag);
            if (rs_v[z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,hc,response,%0d,%0d,ffff,%0d\n", $realtime, cyc, cj, z, dl_a[LVM-1][14*z+:14], vm_trace_hc_tag);
        end
        for (integer z = 0; z < S_WR; z = z + 1)
            if (wq_v[z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,hc,write,%0d,%0d,ffff,%0d\n", $realtime, cyc, cj, z, wq_row[14*z+:14], vm_trace_hc_tag);
`ifdef TB_SU_REAL
        for (integer z = 0; z < SU_RD; z = z + 1) begin
            if (su_rq_v[z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,su,read,%0d,%0d,ffff,%0d\n", $realtime, cyc, cj, z, su_rq_row[14*z+:14], vm_trace_su_tag);
            if (su_rs_v[z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,su,response,%0d,%0d,ffff,%0d\n", $realtime, cyc, cj, z, su_dl_a[LVM-1][14*z+:14], vm_trace_su_tag);
        end
        for (integer z = 0; z < SU_WR; z = z + 1)
            if (su_wq_v[z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,su,write,%0d,%0d,%04h,%0d\n", $realtime, cyc, cj, z, su_wq_row[14*z+:14], su_wq_mask[16*z+:16], vm_trace_su_tag);
`endif
        if (vwe) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,ctrl,write,0,%0d,ffff,-1\n", $realtime, cyc, cj, vwa);
`ifndef TB_HCX_REAL
        if (g_eng[9].g_b.jdone_r && o_wr[g_eng[9].g_b.dop_r] >= 0)
            $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,fixture_hcx,write,0,%0d,ffff,-1\n", $realtime, cyc, cj, o_wr[g_eng[9].g_b.dop_r]);
`endif
    end
    always @(posedge ckv) if (vm_trace_fd && rsv)
        for (integer z = 0; z < NR; z = z + 1) begin
            if (tvm[104*z]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,fixture_capture,element_write,%0d,%0d,0001,-1\n", $realtime,cyc,cj,z,tvm[104*z+1+:19]);
            if (tvm[104*z+52]) $fwrite(vm_trace_fd, "%0.3f,%0d,%0d,fixture_capture,element_write,%0d,%0d,0001,-1\n", $realtime,cyc,cj,z,tvm[104*z+53+:19]);
        end
endmodule
