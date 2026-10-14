`timescale 1ns/1ps
// el1011-hbm-smmv-b (2026-10-12): SM.MATVEC THROUGHPUT bench for the TRACK-B record engine.  Same production shape,
// vectors, HBM model (+LAT, +BWX10), real VM and golden check as tb_hgi_sm_tput, but records are DISPATCHED ON rec_rdy
// (the engine keeps up to W in flight) and the service of record i = ret_i - max(disp_i, ret_(i-1)) (retire to retire).
// ot_hgi_smmv (engine, NSM 32) -> ot_hgi_sm_xload (NXC 4, BD with XBD) -> x-write relay (slot base) -> 32 SMs (2 real
// ot_hbm_accel_smh + 30 shadows) -> ot_hgi_smmv_pub (record-pipelined) -> ot_hgi_vm_unit.
// Shadows: SM s replays real SM (s mod 2); per record r it is active iff M_r > s Q_r, emits rows < R_s(r) of the op the
// real SM is emitting (row pointer) and toggles its own arrive only for ops it is active in (arrive pointer).
// Mutants (must FAIL): MUT_ROW (pub drops s Q), MUT_SLOT (every x at slot 0), MUT_EARLY (retire on issue: caught by
// the RETIRE SCOREBOARD -- every retire must follow its record's pub_done and its real SMs' arrives),
// MUT_XRS (an XR hit reads the previous load's slot), MUT_B8E (BW8: a fragment emits before its last wave lands; run
// with +XLJIT=n so a tpair's waves land apart).
// B2 (+define+NCL=4): NCL cluster engines of NSM/NCL SMs each (strap sm_base = c NSM/NCL), each with its own x loader
// and record-pipelined pub on the VM; every record goes to all clusters (accepted when all are ready) and retires when
// the last cluster retires it.  Real SMs 0/1 sit in cluster 0; x writes of clusters > 0 reach shadows only.
// BDW8 (+define+WVM8, smmv-b 10-12): every cluster's x loader runs BW8 (block-dot x over the cluster's LOCAL VM slice
// 8-lane group); each cluster has its OWN slice model (8 lanes, lane b <-> bank b = sector[2:0], one sector a lane an
// edge, +XLUP request relay edges, +XLBK bank edges, +XLDN response / credit relay edges; data = the x image, which no
// record writes: A < 200,000 words, O >= 200,000).  +define+XQ=n: engine loads in flight.  +define+MUT_B8: BW8 mutant.
// Per-record trace (cluster 0): xi = x stage (load issued / XR hit), xd = x done, is = SM issue done, a0 = real SM 0
// done (arrive), pd = publication done.
// XP (+define+XP, owner 10-13 redesign step 5): the x loader of every cluster is the NEW x plane ot_hgi_xp_load (wave
// reader + feed-forward quantise / pack; block-dot AND BF16 x on the 8-lane slice group) and the real SMs take their x
// writes from the registered spine ot_hgi_xp_spine (SM s taps stage s).  Needs WVM8 (the slice model).  Mutants:
// MUT_WDROP (a wave never reaches the pack stage), MUT_BEAT (a beat never leaves), MUT_LANE (waves land one lane off).
// +define+XSPD=n: n relay stages between the pack stage and SM 0 (placement: slice 7 - 17 mm from the SMs).
module tb_hgi_smmv_tput;
`ifndef XSPD
`define XSPD 0
`endif
`ifndef XCR
`define XCR 16
`endif
`ifndef SMMV_DE
`define SMMV_DE 0
`endif
`ifdef MUT_DE
    localparam integer MDE = 1;      // el1013: the start pass does not wait for the x (must FAIL: stale x under the op)
`else
    localparam integer MDE = 0;
`endif
`ifdef MUT_WDROP
    localparam integer MWD = 1;
`else
    localparam integer MWD = 0;
`endif
`ifdef MUT_BEAT
    localparam integer MBT = 1;
`else
    localparam integer MBT = 0;
`endif
`ifdef MUT_LANE
    localparam integer MLN = 1;
`else
    localparam integer MLN = 0;
`endif
`ifdef MUT_ROW
    localparam integer MW = 1;
`else
    localparam integer MW = 0;
`endif
`ifdef MUT_SLOT
    localparam integer MS = 1;
`else
    localparam integer MS = 0;
`endif
`ifdef MUT_EARLY
    localparam integer ME = 1;
`else
    localparam integer ME = 0;
`endif
`ifdef MUT_B8E
    localparam integer MB8E = 1;
`else
    localparam integer MB8E = 0;
`endif
`ifdef MUT_XRS
    localparam integer MXR = 1;
`else
    localparam integer MXR = 0;
`endif
`ifndef WIN
`define WIN 4
`endif
`ifndef NCL
`define NCL 1
`endif
`ifndef XQ
`define XQ 1
`endif
    // smmv-cr (2026-10-12): +define+SMMV_CR = engine row credits (CR 1, AD `TB_AD, default 8) with a credit-on-arrival
    // model (sm_cr = the SM's own result rows, shadows' gated rows included: exact per slot); +define+MUT_CRDL = the
    // pre-fix chunk rule (min(CH, AD), not wave-aligned): at TB_AD 4 it must DEADLOCK -> watchdog FAIL.
`ifdef SMMV_CR
    localparam integer CRB = 1;
`else
    localparam integer CRB = 0;
`endif
`ifndef TB_AD
`define TB_AD 8
`endif
`ifdef MUT_CRDL
    localparam integer CRDL = 1;
`else
    localparam integer CRDL = 0;
`endif
`ifdef WVM8
    localparam integer BW = 1;
`else
    localparam integer BW = 0;
`endif
`ifdef MUT_B8
    localparam integer MB8 = 1;
`else
    localparam integer MB8 = 0;
`endif
    integer xlup, xldn, xlbk, xljit;
    initial begin
        if (!$value$plusargs("XLJIT=%d", xljit)) xljit = 0;   // BW8 slice model: + 0..XLJIT random edges a bank response (in order a lane)
        if (!$value$plusargs("XLUP=%d", xlup)) xlup = 4;
        if (!$value$plusargs("XLDN=%d", xldn)) xldn = 4;
        if (!$value$plusargs("XLBK=%d", xlbk)) xlbk = 3;
    end
    `include "tput_sizes.svh"
    localparam integer NSM = 32, NREAL = 2, CW = 106, NXC = 4, NPC = 4, NCL = `NCL, NSL = NSM / NCL;
    reg [255:0] xmem [0:32767];
    integer xi_c [0:NREC-1]; integer xd_c [0:NREC-1]; integer is_c [0:NREC-1]; integer a0_c [0:NREC-1]; integer pd_c [0:NREC-1];
    reg clk = 0;
    always #1 clk = ~clk;
    reg [937:0] recm [0:NREC-1]; reg [119:0] infm [0:NREC-1]; reg [2063:0] xwm [0:NXW-1];
    reg [287:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1]; reg [1119:0] linem [0:NLINE-1];
    reg [1087:0] lmem [0:LSPAN-1]; reg lhas [0:LSPAN-1];
    reg [8*256-1:0] dir; integer i, lat, bwx10, nvmi;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NVMI=%d", nvmi)) nvmi = NVMI;      // the XR vectors of a layer = the same sizes, fewer x sectors
        if (!$value$plusargs("LAT=%d", lat)) lat = 104;
        if (!$value$plusargs("BWX10=%d", bwx10)) bwx10 = 31667;
        $readmemh({dir, "/tput_rec.mem"}, recm); $readmemh({dir, "/tput_info.mem"}, infm);
        $readmemh({dir, "/tput_vmi.mem"}, vmim); $readmemh({dir, "/tput_vme.mem"}, vmem); $readmemh({dir, "/tput_lines.mem"}, linem);
        for (i = 0; i < LSPAN; i = i + 1) lhas[i] = 1'b0;
        for (i = 0; i < NLINE; i = i + 1) begin lmem[linem[i][1119:1088] - LBASE] = linem[i][1087:0]; lhas[linem[i][1119:1088] - LBASE] = 1'b1; end
    end
    integer errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy; wire [NCL-1:0] c_pdone; wire [NCL-1:0] c_rdy, c_done, c_fault, c_halt, c_pfault, c_xfault; wire [NCL*3-1:0] c_iss;
    wire fault = |c_fault;
    assign rec_rdy = &c_rdy;
    wire [NSM*CW-1:0] sm_cmd; wire [NSM*4-1:0] sm_ret; wire [2:0] iss_seq = c_iss[2:0];
    wire xw_en; wire [6:0] xw_addr, xw_grp; wire [2047:0] xw_data;
    wire [NSM-1:0] rv; wire [NSM*12-1:0] rrow; wire [NSM*256-1:0] rdata;
`ifdef XBD
    localparam integer XB = 1;
`else
    localparam integer XB = 0;
    initial $fatal(1, "tb_hgi_smmv_tput needs +define+XBD (native block-dot x)");
`endif
    wire [NCL*NXC*338-1:0] xq; wire [NCL*NXC*274-1:0] xr; wire [NCL*NPC*338-1:0] pq; wire [NCL*NPC*274-1:0] pr;
    wire [273:0] tr; reg [337:0] tq = 0;
    reg wd_fire = 0;                        // deadlock: every cluster dumps its engine state once, then FAIL
    genvar cl;
    generate for (cl = 0; cl < NCL; cl = cl + 1) begin : g_cl
        wire x_v, x_rdy, x_done, x_fault, pub_v, pub_rdy, pub_done, pub_fault;
        wire [39:0] x_base, pub_base; wire [20:0] x_n; wire [3:0] x_p, pub_p; wire [31:0] x_stride, pub_stride;
        wire [1:0] x_space, x_fmt, pub_space; wire pub_bf16; wire [19:0] pub_m; wire [12:0] pub_q; wire [6:0] x_xb;
        wire l_en; wire [6:0] l_addr, l_grp; wire [2047:0] l_data;
        ot_hgi_smmv #(.NSM(NSL), .W(`WIN), .XQ(`XQ), .MUT_SLOT(MS), .MUT_EARLY(ME), .MUT_XRS(MXR), .CR(CRB), .AD(`TB_AD), .MUT_CRDL(CRDL), .DE(`SMMV_DE), .MUT_DE(MDE)) u_a (.clk(clk), .rst_n(rst_n), .sm_base(5'(cl * NSL)),
            .rec_v(rec_v && rec_rdy), .rec_rdy(c_rdy[cl]),
            .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]), .rec_n_a(cur[916:896]),
            .rec_n_b(cur[937:917]), .rec_done(c_done[cl]), .rec_fault(c_fault[cl]), .halted(c_halt[cl]), .x_v(x_v), .x_rdy(x_rdy),
            .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_xb(x_xb),
            .x_done(x_done), .x_fault(x_fault), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base),
            .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16),
            .pub_done(pub_done), .pub_fault(pub_fault), .sm_cmd(sm_cmd[cl*NSL*CW +: NSL*CW]), .sm_ret(sm_ret[cl*NSL*4 +: NSL*4]),
            .sm_cg_en(), .dbg_iss_seq(c_iss[cl*3 +: 3]), .sm_cr(rv[cl*NSL +: NSL]));
        wire rg_req; reg rg_gnt = 0; wire [32*16-1:0] wrq; reg [31:0] wrq_cr = 0; reg [32*257-1:0] wrr = 0;
`ifdef XP
        ot_hgi_xp_load #(.NXC(NXC), .CR(`XCR), .XDD(`XSPD + 12), .MUT_WDROP(MWD), .MUT_BEAT(MBT), .MUT_LANE(MLN)) u_x (
`else
        ot_hgi_sm_xload #(.NXC(NXC), .BD(XB), .BW8(BW), .MUT_B8(MB8), .MUT_B8E(MB8E)) u_x (
`endif
            .clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base),
            .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_xb(x_xb), .x_done(x_done),
            .x_fault(x_fault), .xw_en(l_en), .xw_addr(l_addr), .xw_grp(l_grp), .xw_data(l_data),
            .vmq(xq[cl*NXC*338 +: NXC*338]), .vmr(xr[cl*NXC*274 +: NXC*274]),
            .rg_req(rg_req), .rg_gnt(rg_gnt), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr));
        // the cluster's LOCAL slice 8-lane group (behavioural; time-stamped in-order queues a lane)
        integer lq_s [0:7][0:255]; longint lq_t [0:7][0:255]; integer lh [0:8], lt [0:8];
        longint cr_t [0:7][0:255]; integer ch [0:7], ct [0:7];
        longint rs_t [0:7][0:255]; reg [255:0] rs_d [0:7][0:255]; integer rh2 [0:7], rt2 [0:7];
        initial for (integer b = 0; b < 8; b = b + 1) begin lh[b] = 0; lt[b] = 0; ch[b] = 0; ct[b] = 0; rh2[b] = 0; rt2[b] = 0; end
        always @(posedge clk) begin
            rg_gnt <= rg_req;
            for (integer b = 0; b < 8; b = b + 1) begin
                wrq_cr[b] <= 1'b0; wrr[b*257 + 256] <= 1'b0;
                if (rst_n && wrq[b*16 + 15]) begin
                    if (wrq[b*16 +: 3] != 3'(b)) begin $display("ERR cluster %0d lane %0d got sector %0d (bank %0d)", cl, b, wrq[b*16 +: 15], wrq[b*16 +: 3]); errors = errors + 1; end
                    lq_s[b][lt[b] % 256] = wrq[b*16 +: 15]; lq_t[b][lt[b] % 256] = cyc + xlup; lt[b] = lt[b] + 1;
                    if (lt[b] - lh[b] > 64) begin $display("ERR cluster %0d lane %0d queue overrun", cl, b); errors = errors + 1; end
                end
                if (lh[b] != lt[b] && lq_t[b][lh[b] % 256] <= cyc) begin            // the bank takes one an edge
                    cr_t[b][ct[b] % 256] = cyc + xldn; ct[b] = ct[b] + 1;
                    rs_t[b][rt2[b] % 256] = cyc + xlbk + xldn + ((xljit > 0) ? longint'($urandom % (xljit + 1)) : 0);
                    if (rt2[b] > 0 && rs_t[b][rt2[b] % 256] < rs_t[b][(rt2[b] - 1) % 256]) rs_t[b][rt2[b] % 256] = rs_t[b][(rt2[b] - 1) % 256];
                    rs_d[b][rt2[b] % 256] = xmem[lq_s[b][lh[b] % 256]]; rt2[b] = rt2[b] + 1;
                    lh[b] = lh[b] + 1;
                end
                if (ch[b] != ct[b] && cr_t[b][ch[b] % 256] <= cyc) begin wrq_cr[b] <= 1'b1; ch[b] = ch[b] + 1; end
                if (rh2[b] != rt2[b] && rs_t[b][rh2[b] % 256] <= cyc) begin
                    wrr[b*257 +: 257] <= {1'b1, rs_d[b][rh2[b] % 256]}; rh2[b] = rh2[b] + 1; end
            end
        end
        if (cl == 0) begin : g_xw
            assign xw_en = l_en; assign xw_addr = l_addr; assign xw_grp = l_grp; assign xw_data = l_data;
        end
        // +SMT=1: engine issue trace of cluster 0 (every change of the issue / publication pointers and the pending masks)
        if (cl == 0) begin : g_et
            integer smt_e; initial if (!$value$plusargs("SMT=%d", smt_e)) smt_e = 0;
            reg [63:0] et_q = 0;
            wire [63:0] et = {u_a.tail[3:0], u_a.xp[3:0], u_a.ip[3:0], u_a.rh[3:0], u_a.ppc[3:0], u_a.pdc[3:0], u_a.go, u_a.fq_v, u_a.fld_v, u_a.pub_v,
                              u_a.st_pend[7:0], u_a.d_pend[7:0], u_a.e_xd[7:0], u_a.xn[1:0]} ^ {60'd0, u_a.dp[3:0]} ^ {59'd0, u_a.dgo, 4'd0};
            always @(posedge clk) if (rst_n && smt_e != 0) begin
                et_q <= et;
                if (et != et_q) $display("SME %0d tail %0d xp %0d ip %0d rh %0d ppc %0d pdc %0d go %b fq %b fld %b pub_v %b st_pend %b d_pend %b e_xd %b xn %0d dp %0d dgo %b",
                    cyc, u_a.tail, u_a.xp, u_a.ip, u_a.rh, u_a.ppc, u_a.pdc, u_a.go, u_a.fq_v, u_a.fld_v, u_a.pub_v, u_a.st_pend, u_a.d_pend, u_a.e_xd, u_a.xn, u_a.dp, u_a.dgo);
            end
        end
        ot_hgi_smmv_pub #(.NSM(NSL), .NPC(NPC), .W(`WIN), .MUT_ROW(MW)) u_p (.clk(clk), .rst_n(rst_n), .sm_base(5'(cl * NSL)),
            .pub_v(pub_v), .pub_rdy(pub_rdy),
            .pub_base(pub_base), .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_bf16(pub_bf16),
            .pub_done(pub_done), .pub_fault(pub_fault), .sm_rv(rv[cl*NSL +: NSL]), .sm_rrow(rrow[cl*NSL*12 +: NSL*12]),
            .sm_rdata(rdata[cl*NSL*256 +: NSL*256]), .vmq(pq[cl*NPC*338 +: NPC*338]), .vmr(pr[cl*NPC*274 +: NPC*274]),
            .s0_v(), .s0_idx(), .s0_data());
        assign c_pfault[cl] = pub_fault; assign c_xfault[cl] = x_fault; assign c_pdone[cl] = pub_done;
        integer n_xt = 0, n_xd = 0, n_pd = 0, n_rt = 0; reg wd_pr = 0;
        always @(posedge clk) if (rst_n) begin
            if (x_v && x_rdy) n_xt = n_xt + 1; if (x_done) n_xd = n_xd + 1; if (pub_done) n_pd = n_pd + 1; if (c_done[cl]) n_rt = n_rt + 1;
            if (wd_fire && !wd_pr) begin
                wd_pr = 1'b1;
                $display("  CL %0d: x taken %0d done %0d, pub_done %0d, retired %0d | tail %0d xp %0d ip %0d rh %0d ppc %0d pdc %0d xn %0d x_v %b e_xd %b e_xr %b used %0d ap %0d a_ok %b xo %0d xo_v %b go %b fq %b fld %b rdy %b halt %b",
                         cl, n_xt, n_xd, n_pd, n_rt, u_a.tail, u_a.xp, u_a.ip, u_a.rh, u_a.ppc, u_a.pdc, u_a.xn, u_a.x_v, u_a.e_xd, u_a.e_xr,
                         u_a.used, u_a.ap, u_a.a_ok, u_a.xo, u_a.xo_v, u_a.go, u_a.fq_v, u_a.fld_v, u_a.rdy_r, u_a.halt_q);
            end
        end
    end endgenerate
    ot_hgi_vm_unit #(.NC(NCL * (NXC + NPC) + 1)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, pq, xq}), .cr({tr, pr, xr}), .status());
    integer lines_req [0:NREAL-1];
    wire [NREAL-1:0] sxw_en; wire [NREAL*7-1:0] sxw_addr, sxw_grp; wire [NREAL*2048-1:0] sxw_data;
`ifdef XP
    wire [7:0] sp_en; wire [8*7-1:0] sp_addr, sp_grp; wire [8*2048-1:0] sp_data;
    ot_hgi_xp_spine #(.NS(8), .PRE(`XSPD)) u_spine (.clk(clk), .rst(!rst_n), .i_en(xw_en), .i_addr(xw_addr), .i_grp(xw_grp), .i_data(xw_data),
        .o_en(sp_en), .o_addr(sp_addr), .o_grp(sp_grp), .o_data(sp_data));
    assign sxw_en = sp_en[NREAL-1:0]; assign sxw_addr = sp_addr[NREAL*7-1:0]; assign sxw_grp = sp_grp[NREAL*7-1:0];
    assign sxw_data = sp_data[NREAL*2048-1:0];
    integer n_beat = 0;
    always @(posedge clk) if (rst_n && xw_en) n_beat = n_beat + 1;
`else
    assign sxw_en = {NREAL{xw_en}}; assign sxw_addr = {NREAL{xw_addr}}; assign sxw_grp = {NREAL{xw_grp}}; assign sxw_data = {NREAL{xw_data}};
`endif
    wire [NREAL-1:0] arr_real;
    // record being issued (the engine's issue pointer advances once a record)
    integer rec_iss = 0; reg [2:0] iss_q = 0;
    always @(posedge clk) begin iss_q <= iss_seq; if (rst_n && iss_seq != iss_q) rec_iss = rec_iss + 1; end
    function automatic integer rows_of(input integer r, input integer s_);
        reg [119:0] f; integer q_, m_;
        begin f = infm[r]; q_ = f[115:100]; m_ = f[99:80];
              rows_of = (m_ > s_ * q_) ? (((m_ - s_ * q_) > q_) ? q_ : (m_ - s_ * q_)) : 0; end
    endfunction
    genvar s;
    generate for (s = 0; s < NREAL; s = s + 1) begin : g_sm
        wire [CW-1:0] c = sm_cmd[s*CW +: CW];
        wire start_ready, d_ready, req_v, fault_s, arrive, released, busy; wire [31:0] req_addr; wire [9:0] req_tag;
        wire [7:0] rrow8;
        reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
        assign sm_ret[s*4 +: 4] = {fault_s, arrive, d_ready, start_ready};
        assign arr_real[s] = arrive;
        assign rrow[s*12 +: 12] = {4'd0, rrow8};
        ot_hbm_accel_smh #(.ENABLE_INT8(1), .PIPE_INT8(1), .RMAX(256)) u_sm (.clk(clk), .rst_n(rst_n), .start(c[0]),
            .start_ready(start_ready), .op_rows(c[9:1]), .op_c(c[29:14]), .op_g(c[37:30]), .op_gs(c[38]),
            .op_fmt(c[40:39]), .op_xb(c[47:41]), .busy(busy), .d_valid(c[48]), .d_ready(d_ready), .d_base(c[80:49]),
            .d_lines(c[104:81]), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v),
            .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(sxw_en[s]), .xw_addr(sxw_addr[s*7 +: 7]), .xw_grp(sxw_grp[s*7 +: 7]), .xw_data(sxw_data[s*2048 +: 2048]),
            .rv(rv[s]), .rrow(rrow8), .rdata(rdata[s*256 +: 256]), .fault(fault_s), .arrive(arrive),
            .release_in(c[105]), .released(released));
        // HBM line model: in-order, ready at max(request + LAT, previous ready + LB x 32 / BW) (milli-cycles)
        reg [31:0] qa [0:4095]; reg [9:0] qt [0:4095]; longint qc [0:4095]; integer qh = 0, qtl = 0;
        longint nxt = 0; longint ival;
        always @(posedge clk) begin
            rsp_v <= 1'b0;
            ival = (((c[40:39] == 2'd3) ? 160 : 136) * 32 * 10000) / bwx10;   // milli-cycles a line
            if (req_v) begin
                longint t0; t0 = (cyc + lat) * 1000; if (t0 < nxt + ival) t0 = nxt + ival; nxt = t0;
                qa[qtl % 4096] = req_addr; qt[qtl % 4096] = req_tag; qc[qtl % 4096] = t0; qtl = qtl + 1;
                lines_req[s] = lines_req[s] + 1;
                if (qtl - qh > 4096) begin $display("ERR SM %0d HBM model queue overflow", s); errors = errors + 1; end
                if (req_addr < LBASE || req_addr >= LBASE + LSPAN || !lhas[req_addr - LBASE]) begin $display("ERR SM %0d read an unwritten line %0d", s, req_addr); errors = errors + 1; end
            end
            if (qh != qtl && qc[qh % 4096] <= longint'(cyc) * 1000) begin
                rsp_v <= 1'b1; rsp_tag <= qt[qh % 4096];
                rsp_data <= (qa[qh % 4096] >= LBASE && qa[qh % 4096] < LBASE + LSPAN) ? lmem[qa[qh % 4096] - LBASE] : 1088'd0;
                qh = qh + 1;
            end
            if (rst_n && fault_s) begin $display("ERR SM %0d fault", s); errors = errors + 1; end
        end
        // +SMT=1: event trace of real SM 0 (start / descriptor / first + last request and response / first row / arrive)
        integer smt, n_rq = 0, n_rs = 0, n_rv = 0; reg arr_t = 0;
        initial if (!$value$plusargs("SMT=%d", smt)) smt = 0;
        always @(posedge clk) if (rst_n && smt != 0 && s == 0) begin
            arr_t <= arrive;
            if (c[0] && start_ready) $display("SMT %0d START rows %0d fmt %0d xb %0d | rq %0d rs %0d rv %0d busy %b", cyc, c[9:1], c[40:39], c[47:41], n_rq, n_rs, n_rv, busy);
            if (c[48] && d_ready) $display("SMT %0d DESC lines %0d | rq %0d rs %0d", cyc, c[104:81], n_rq, n_rs);
            if (arrive != arr_t) $display("SMT %0d ARRIVE | rq %0d rs %0d rv %0d", cyc, n_rq, n_rs, n_rv);
            if (req_v) n_rq = n_rq + 1; if (rsp_v) n_rs = n_rs + 1; if (rv[s]) n_rv = n_rv + 1;
            if (req_v && (n_rq % 8) == 0) $display("SMT %0d RQ %0d", cyc, n_rq);
            if (rsp_v && (n_rs % 8) == 0) $display("SMT %0d RS %0d", cyc, n_rs);
            if (rv[s]) $display("SMT %0d ROW %0d", cyc, n_rv);
        end
        if (s == 0) begin : g_it
            integer n_adv = 0, n_wst = 0, n_hz = 0, n_nst = 0;
            always @(posedge clk) if (rst_n && smt != 0) begin
                if (u_sm.g_fp.u_fc.u_issue.adv) n_adv = n_adv + 1;
                if (u_sm.g_fp.u_fc.u_issue.need_line && !u_sm.g_fp.u_fc.u_issue.w_valid) n_wst = n_wst + 1;
                if (u_sm.g_fp.u_fc.u_issue.issuing && !u_sm.g_fp.u_fc.u_issue.my_turn) n_nst = n_nst + 1;
                if (u_sm.g_fp.u_fc.u_issue.start_v && !u_sm.g_fp.u_fc.u_issue.launch) n_hz = n_hz + 1;
                if (u_sm.g_fp.u_fc.u_issue.launch) $display("SMI %0d LAUNCH on %0d since %0d need %0d | adv %0d wstall %0d noturn %0d headwait %0d", cyc,
                    u_sm.g_fp.u_fc.u_issue.on, u_sm.g_fp.u_fc.u_issue.since, u_sm.g_fp.u_fc.u_issue.need_q, n_adv, n_wst, n_nst, n_hz);
                if (u_sm.g_fp.u_fc.u_issue.op_end) $display("SMI %0d OPEND | adv %0d wstall %0d noturn %0d headwait %0d", cyc, n_adv, n_wst, n_nst, n_hz);
                if (u_sm.g_fp.u_fc.u_issue.head_done) $display("SMI %0d HEADDONE on %0d", cyc, u_sm.g_fp.u_fc.u_issue.on);
            end
        end
    end endgenerate

    // per real SM: the list of records it took (start handshakes), a row pointer and an arrive pointer into it
    integer opl [0:NREAL-1][0:4095]; integer opn [0:NREAL-1]; integer rowp [0:NREAL-1]; integer rown [0:NREAL-1];
    integer arrp [0:NREAL-1]; reg [NREAL-1:0] arr_q;
    reg sb_arr [0:NREAL-1][0:NREC-1];        // retire scoreboard: real SM q arrived for record r
    integer rr0, ar0, rr1, ar1;               // front records (row / arrive) of real SM 0 / 1
    always @* begin rr0 = (rowp[0] < opn[0]) ? opl[0][rowp[0]] : 0; rr1 = (rowp[1] < opn[1]) ? opl[1][rowp[1]] : 0; end
    integer q0;
    always @(posedge clk) if (rst_n) begin
        for (q0 = 0; q0 < NREAL; q0 = q0 + 1) begin
            if (sm_cmd[q0*CW] && sm_ret[q0*4]) begin opl[q0][opn[q0]] = rec_iss; opn[q0] = opn[q0] + 1; end
            if (rv[q0]) begin rown[q0] = rown[q0] + 1; if (rown[q0] == rows_of(opl[q0][rowp[q0]], q0)) begin rown[q0] = 0; rowp[q0] = rowp[q0] + 1; end end
        end
    end
    // shadows
    reg [NSM-1:0] sh_arr = 0;
    generate for (s = NREAL; s < NSM; s = s + 1) begin : g_sh
        localparam integer SR = s % NREAL;
        wire [31:0] rfront = (SR == 0) ? rr0 : rr1;
        wire [31:0] rs_ = rows_of(rfront, s);
        assign sm_ret[s*4 +: 4] = {sm_ret[SR*4 + 3], sh_arr[s], sm_ret[SR*4 + 1], sm_ret[SR*4 + 0]};
        assign rv[s] = rv[SR] && ({20'd0, rrow[SR*12 +: 12]} < rs_);
        assign rrow[s*12 +: 12] = rrow[SR*12 +: 12];
        assign rdata[s*256 +: 256] = rdata[SR*256 +: 256];
    end endgenerate
    // arrive pointer: a real SM's toggle completes its op at arrp; each shadow active in that record toggles too
    integer s3;
    always @(posedge clk) if (rst_n) begin
        for (q0 = 0; q0 < NREAL; q0 = q0 + 1) begin
            arr_q[q0] <= arr_real[q0];
            if (arr_real[q0] != arr_q[q0]) begin
                for (s3 = NREAL; s3 < NSM; s3 = s3 + 1)
                    if (s3 % NREAL == q0 && rows_of(opl[q0][arrp[q0]], s3) > 0) sh_arr[s3] <= ~sh_arr[s3];
                if (q0 == 0 && opl[0][arrp[0]] < NREC) a0_c[opl[0][arrp[0]]] = cyc;
                if (opl[q0][arrp[q0]] < NREC) sb_arr[q0][opl[q0][arrp[q0]]] = 1'b1;
                arrp[q0] = arrp[q0] + 1;
            end
        end
    end
    // RETIRE SCOREBOARD (smmv-b 10-12): a retire must FOLLOW its record's completion.  Per cluster, the i-th retire
    // needs the cluster's i-th pub_done (the record's publication is done, in order) and, in cluster 0, an arrive of
    // every real SM active in record i.  A retire-on-issue engine (MUT_EARLY) retires before both -> FAIL here, even
    // when the late writes still land before the end-of-run VM readback (which is why MUT_EARLY used to pass).
    integer sb_ret [0:NCL-1]; integer sb_pd [0:NCL-1]; integer sb_c, sb_q, sb_e = 0;
    initial begin
        for (sb_c = 0; sb_c < NCL; sb_c = sb_c + 1) begin sb_ret[sb_c] = 0; sb_pd[sb_c] = 0; end
        for (sb_q = 0; sb_q < NREAL; sb_q = sb_q + 1) for (sb_c = 0; sb_c < NREC; sb_c = sb_c + 1) sb_arr[sb_q][sb_c] = 1'b0;
    end
    always @(posedge clk) if (rst_n) begin
        for (sb_c = 0; sb_c < NCL; sb_c = sb_c + 1) begin
            if (c_done[sb_c]) begin
                if (sb_pd[sb_c] <= sb_ret[sb_c]) begin
                    if (sb_e < 10) $display("ERR RETIRE-EARLY cluster %0d record %0d retired at cycle %0d before its publication was done (%0d pub_done)", sb_c, sb_ret[sb_c], cyc, sb_pd[sb_c]);
                    sb_e = sb_e + 1; errors = errors + 1;
                end
                if (sb_c == 0 && sb_ret[0] < NREC)
                    for (sb_q = 0; sb_q < NREAL; sb_q = sb_q + 1)
                        if (rows_of(sb_ret[0], sb_q) > 0 && !sb_arr[sb_q][sb_ret[0]]) begin
                            if (sb_e < 10) $display("ERR RETIRE-EARLY cluster 0 record %0d retired at cycle %0d before real SM %0d arrived", sb_ret[0], cyc, sb_q);
                            sb_e = sb_e + 1; errors = errors + 1;
                        end
                sb_ret[sb_c] = sb_ret[sb_c] + 1;
            end
            if (c_pdone[sb_c]) sb_pd[sb_c] = sb_pd[sb_c] + 1;
        end
    end
    task automatic vm_sec(input we, input [31:0] sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, sec[26:0], 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[255:0];
        end
    endtask
    // per-record trace of cluster 0
    integer nxp = 0, nip = 0, npd = 0, xlq [0:NREC-1], xlh = 0, xlt = 0; reg [7:0] xp_q = 0, ip_q = 0; reg ld_q = 0;
    initial for (integer z = 0; z < NREC; z = z + 1) begin xi_c[z] = -1; xd_c[z] = -1; is_c[z] = -1; a0_c[z] = -1; pd_c[z] = -1; end
    always @(posedge clk) if (rst_n) begin
        xp_q <= 8'(g_cl[0].u_a.xp); ip_q <= 8'(g_cl[0].u_a.ip); ld_q <= g_cl[0].u_a.x_ld_go;
        if (8'(g_cl[0].u_a.xp) != xp_q && nxp < NREC) begin
            xi_c[nxp] = cyc;
            if (ld_q) begin xlq[xlt] = nxp; xlt = xlt + 1; end else xd_c[nxp] = cyc;   // load / XR hit
            nxp = nxp + 1;
        end
        if (g_cl[0].x_done && xlh < xlt) begin xd_c[xlq[xlh]] = cyc; xlh = xlh + 1; end
        if (8'(g_cl[0].u_a.ip) != ip_q && nip < NREC) begin is_c[nip] = cyc; nip = nip + 1; end
        if (g_cl[0].pub_done && npd < NREC) begin pd_c[npd] = cyc; npd = npd + 1; end
    end
    integer j, t, k, nf, r, prev_ret, busy_sum;
    integer disp [0:NREC-1]; integer retc [0:NREC-1];
    // DEADLOCK WATCHDOG (smmv-cr): records in flight and no result row, no real-SM line request and no retire for WD
    // cycles (+WD=, default 20000) -> dump cluster 0's credit loop for the real SMs and FAIL (a hang is a FAIL)
    integer wd, wd_last = 0, wi; reg wd_on = 0;
    initial if (!$value$plusargs("WD=%d", wd)) wd = 20000;
    always @(posedge clk) if (rst_n) begin
        if (!wd_on || (|rv) || (|c_done) || g_sm[0].req_v || g_sm[1].req_v) wd_last = cyc;
        else if (cyc - wd_last > wd) begin
            if (!wd_fire) begin
            $display("ERR DEADLOCK: no row / line request / retire for %0d cycles at cycle %0d (retired %0d of %0d, CR %0d AD %0d)", wd, cyc, k, NREC, CRB, `TB_AD);
            for (wi = 0; wi < NREAL; wi = wi + 1)
                $display("  SM %0d: cr_s %0d rr_s %0d rr_nz %0d d_pend %0d st_pend %0d lines_req %0d", wi,
                         g_cl[0].u_a.cr_s[wi*$clog2(`TB_AD+1) +: $clog2(`TB_AD+1)], g_cl[0].u_a.rr_s[wi*13 +: 13],
                         g_cl[0].u_a.rr_nz[wi], g_cl[0].u_a.d_pend[wi], g_cl[0].u_a.st_pend[wi], lines_req[wi]);
            end
            if (wd_fire) begin $display("HGI_SMMV_TPUT FAIL deadlock"); $finish; end
            wd_fire = 1'b1; wd_last = cyc - wd;            // one more edge: the clusters dump, then FAIL
        end
    end
    reg [255:0] qd; reg [31:0] lastsec;
    integer kc [0:NCL-1]; integer kmin, c2;
    always @(posedge clk) begin
        for (c2 = 0; c2 < NCL; c2 = c2 + 1) if (rst_n && c_done[c2]) kc[c2] = kc[c2] + 1;
        kmin = kc[0]; for (c2 = 1; c2 < NCL; c2 = c2 + 1) if (kc[c2] < kmin) kmin = kc[c2];
        while (k < kmin) begin retc[k] = cyc; k = k + 1; end
        if (rst_n && fault) nf = nf + 1;
    end
    initial begin
        for (j = 0; j < NREAL; j = j + 1) begin lines_req[j] = 0; opn[j] = 0; rowp[j] = 0; rown[j] = 0; arrp[j] = 0; end
        arr_q = 0; k = 0; for (j = 0; j < NCL; j = j + 1) kc[j] = 0;
        repeat (3) @(posedge clk);
        rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
        for (j = 0; j < nvmi; j = j + 1) begin vm_sec(1'b1, vmim[j][287:256], vmim[j][255:0], qd); xmem[vmim[j][270:256]] = vmim[j][255:0]; end
        $display("x loaded: %0d sectors at cycle %0d (LAT %0d BWX10 %0d W %0d NCL %0d BW8 %0d XQ %0d XL %0d/%0d/%0d)", nvmi, cyc, lat, bwx10, `WIN, NCL, BW, `XQ, xlup, xlbk, xldn); $fflush;
        k = 0; nf = 0;
        for (r = 0; r < NREC && nf == 0; r = r + 1) begin
            @(negedge clk); cur = recm[r]; rec_v = 1;
            t = 0; while (!rec_rdy && t < 2000000 && nf == 0) begin @(negedge clk); t = t + 1; end
            @(posedge clk); disp[r] = cyc; #0.1 rec_v = 0; if (!wd_on) wd_last = cyc; wd_on = 1;
        end
        t = 0; while (k < NREC && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
        wd_on = 0;
        repeat (8) @(posedge clk);
        if (k != NREC || nf != 0) begin $display("ERR retired %0d of %0d, faults %0d (x_fault %b pub_fault %b)", k, NREC, nf, c_xfault, c_pfault); errors = errors + 1; end
        prev_ret = 0; busy_sum = 0;
        for (r = 0; r < k; r = r + 1) begin
            $display("TPUT %0d disp %0d ret %0d service %0d xi %0d xd %0d is %0d a0 %0d pd %0d", r, disp[r], retc[r],
                     retc[r] - (disp[r] > prev_ret ? disp[r] : prev_ret), xi_c[r], xd_c[r], is_c[r], a0_c[r], pd_c[r]);
            busy_sum = busy_sum + retc[r] - (disp[r] > prev_ret ? disp[r] : prev_ret); prev_ret = retc[r];
        end
        $display("lines real SM0 %0d SM1 %0d", lines_req[0], lines_req[1]);
        lastsec = 32'hFFFFFFFF;
        for (j = 0; j < NVME; j = j + 1) begin
            if (vmem[j][63:35] != lastsec) begin lastsec = vmem[j][63:35]; vm_sec(1'b0, {3'd0, lastsec}, 256'd0, qd); end
            if (qd[32 * vmem[j][34:32] +: 32] !== vmem[j][31:0]) begin
                if (errors < 30) $display("ERR O[%0d] = %h expected %h", vmem[j][63:32], qd[32 * vmem[j][34:32] +: 32], vmem[j][31:0]);
                errors = errors + 1; end
        end
        $display("summary: %0d SM.MATVEC records (window %0d, clusters %0d), service sum %0d cycles, %0d result words checked", NREC, `WIN, NCL, busy_sum, NVME);
        if (errors == 0) $display("HGI_SMMV_TPUT PASS"); else $display("HGI_SMMV_TPUT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
