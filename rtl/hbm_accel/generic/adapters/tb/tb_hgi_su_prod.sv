`timescale 1ns/1ps
// hgi-unitrate (2026-10-10): PRODUCTION-SHAPE bench of the SU / SFU die body ot_hgi_su_unit (D1: record -> stage from
// the REAL HGI VM -> the REAL ot_hdc_v41x_vec on its local memory -> drain back to VM -> retire).  Vectors:
// tools/hgi_unitrate/su_prod_vec.py: the hbm-sim Qwen3-8B token program's layer-0 SU / SFU dispatches at P 8,191 (real
// shapes: softmax over 65,536 scores, row_scale_gu 6,144, SwiGLU 3,072, ...), one record a case, run on one die state.
// Per case: VM is loaded with every source AND sink sector (pre-op values), the record runs, and every sink sector
// is read back whole: written words must equal the golden, unwritten words of those sectors must keep their pre-op
// value.  Reports per case the record's service (rec_v accepted -> rec_done) and its controller phase census
// (span / stage / compute / drain), so the measured cost compares against timing.py's price (N1024 / M256 vec).
// Defines: N, M, LV, LWB (local memory), SFU (run the SFU cases on the GLU body, else the SU cases), WIDE (the wide
// stage / drain successor: VM wide read lanes + second wide write group), MUT_DIRTY (drain mutant).
`ifdef WIDE2
`define CTLP u.g_xctl.u_ctl
`elsif WIDE
`define CTLP u.g_wctl.u_ctl
`elsif OLDHIER
`define CTLP u.u_ctl
`else
`define CTLP u.g_ctl.u_ctl
`endif
module tb_hgi_su_prod;
`ifndef N
`define N 64
`endif
`ifndef M
`define M 64
`endif
`ifndef LV
`define LV 7
`endif
`ifndef LWB
`define LWB 18
`endif
`ifdef MUT_DIRTY
    localparam integer MD = 1;
`else
    localparam integer MD = 0;
`endif
`ifdef SFU
    localparam integer GL = 1;
`else
    localparam integer GL = 0;
`endif
`ifdef WIDE
    localparam integer WD = 1;
`else
    localparam integer WD = 0;
`endif
    localparam integer RPL = WD ? 32 : 1;
    `include "su_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [2196:0] recm [0:NREC-1]; reg [223:0] casem [0:NCASE-1];
    reg [287:0] vmim [0:NVMI-1]; reg [287:0] vmem [0:NVME-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/su_rec.mem"}, recm); $readmemh({dir, "/su_case.mem"}, casem);
        $readmemh({dir, "/su_vmi.mem"}, vmim); $readmemh({dir, "/su_vme.mem"}, vmem);
    end
    integer errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [2196:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [18:0] vm_status; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire [RPL*16-1:0] rq; wire [RPL-1:0] rq_cr; wire [RPL*257-1:0] rr;
    wire [RPL*280-1:0] w2q; wire [RPL-1:0] w2_done, w2_cr;
    ot_hgi_su_unit #(.N(`N), .M(`M), .LV(`LV), .LWB(`LWB), .GLU(GL), .MUT_DIRTY(MD)
`ifdef WIDE2
        , .WIDE(2), .MACRO(0)
`ifdef MUT_X
        , .MUT_X(`MUT_X)
`endif
`elsif WIDE
        , .WIDE(1)
`ifdef LQ
        , .LQ(`LQ)
`endif
`ifdef LRLAT
        , .LRLAT(`LRLAT)
`endif
`ifdef MUT_RV
        , .MUT_RV(`MUT_RV)
`endif
`endif
`ifdef MUT_W
        , .MUT_W(`MUT_W)
`endif
        ) u (.clk(clk), .rst_n(rst_n),
        .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_sut(cur[383:128]), .rec_a(cur[639:384]), .rec_b(cur[895:640]), .rec_c(cur[1151:896]),
        .rec_d(cur[1407:1152]), .rec_o(cur[1663:1408]), .rec_r(cur[1919:1664]), .rec_i(cur[2175:1920]),
        .rec_n_a(cur[2196:2176]), .rec_done(done), .rec_fault(fault), .halted(halted), .vmq(uq), .vmr(ur),
        .s0_v(1'b0), .s0_idx(20'd0), .s0_data(32'd0), .am_stream(), .am_rdy(1'b0)
`ifdef WIDE
`ifdef SHARED
        , .wrq(rq), .wrq_cr(rq_cr), .wrr(rr), .wwq(w2q), .wwq_cr(w2_cr), .wwq_done(w2_done), .rg_req(rg_req[0]), .rg_gnt(rg_gnt[0]),
          .wg_req(wg_req[0]), .wg_gnt(wg_gnt[0])
`else
        , .wrq(rq), .wrq_cr(rq_cr), .wrr(rr), .wwq(w2q), .wwq_cr(w2_cr), .wwq_done(w2_done), .rg_req(), .rg_gnt(1'b1), .wg_req(), .wg_gnt(1'b1)
`endif
`endif
        );
`ifdef SHARED
    // SHARED lane groups: the SU (client 0) shares one read group with a read-burst agent (client 1) and one write group
    // with a write-burst agent (client 2) through ot_hgi_vm_lanearb (registered bus each way; LQ sized to the loop)
    wire [2:0] rg_req, rg_gnt, wg_req, wg_gnt; wire [32*16-1:0] g_rq; wire [31:0] g_rcr, g_wcr, g_wdone; wire [32*257-1:0] g_rr;
    wire [32*280-1:0] g_wq; wire [3*32-1:0] c_rcr, c_wcr; wire [3*32*257-1:0] c_rr; wire [3*32-1:0] c_wdone;
    reg [32*16-1:0] a1_q = 0; reg [32*280-1:0] a2_q = 0; reg a1_req = 0, a2_req = 0;
    assign rg_req[1] = a1_req; assign rg_req[2] = 1'b0; assign wg_req[1] = 1'b0; assign wg_req[2] = a2_req;
`ifndef RLY
`define RLY 0
`endif
`ifndef LQ
`define LQ 8
`endif
`ifdef CHAIN
    // CHAIN topology (hbm-phys): head at the VM face, RLY relay stations, then station 0 = the SU, 1, 2 (the agents)
    localparam integer NST = 3 + `RLY;
    wire [3*NST-1:0] rcq_u, rcq_d; wire [32*16*(NST+1)-1:0] rq_bus; wire [3*(NST+1)-1:0] rreq_bus, rgnt_bus;
    wire [32*(NST+1)-1:0] rcr_bus; wire [32*257*(NST+1)-1:0] rrsp_bus;
    wire [32*280*(NST+1)-1:0] wq_bus; wire [3*(NST+1)-1:0] wreq_bus, wgnt_bus; wire [32*(NST+1)-1:0] wcr_bus, wdn_bus;
    assign rq_bus[32*16*NST +: 32*16] = '0; assign rreq_bus[3*NST +: 3] = '0;
    assign wq_bus[32*280*NST +: 32*280] = '0; assign wreq_bus[3*NST +: 3] = '0;
    ot_hgi_vm_lanehead #(.K(3), .REQW(16), .RSPW(257), .MUT(`ifdef ARBMUT 1 `else 0 `endif)) u_hr (.clk(clk), .rst_n(rst_n),
        .c_req(rreq_bus[2:0]), .c_q(rq_bus[0 +: 32*16]), .c_gnt(rgnt_bus[2:0]), .c_cr(rcr_bus[31:0]), .c_rsp(rrsp_bus[0 +: 32*257]),
        .g_q(g_rq), .g_cr(g_rcr), .g_rsp(g_rr));
    ot_hgi_vm_lanehead #(.K(3), .REQW(280), .RSPW(1), .MUT(`ifdef ARBMUT 1 `else 0 `endif)) u_hw (.clk(clk), .rst_n(rst_n),
        .c_req(wreq_bus[2:0]), .c_q(wq_bus[0 +: 32*280]), .c_gnt(wgnt_bus[2:0]), .c_cr(wcr_bus[31:0]), .c_rsp(wdn_bus[31:0]),
        .g_q(g_wq), .g_cr(g_wcr), .g_rsp(g_wdone));
    wire [32*16*3-1:0] cl_rq = {512'd0, a1_q, rq}; wire [32*280*3-1:0] cl_wq = {a2_q, {32*280{1'b0}}, w2q};
    for (genvar st_ = 0; st_ < NST; st_ = st_ + 1) begin : g_st
        localparam integer CID = st_ - `RLY;                 // < 0: a relay
        wire lr_gnt, lw_gnt; wire [31:0] lr_cr, lw_cr; wire [32*257-1:0] lr_rsp; wire [31:0] lw_dn;
        ot_hgi_vm_lanestation #(.K(3), .ID(CID < 0 ? 0 : CID), .REQW(16), .RSPW(257), .TAP(CID >= 0)) u_sr (.clk(clk), .rst_n(rst_n),
            .up_req(rreq_bus[3*st_ +: 3]), .up_q(rq_bus[32*16*st_ +: 32*16]), .up_gnt(rgnt_bus[3*st_ +: 3]), .up_cr(rcr_bus[32*st_ +: 32]),
            .up_rsp(rrsp_bus[32*257*st_ +: 32*257]), .dn_req(rreq_bus[3*(st_+1) +: 3]), .dn_q(rq_bus[32*16*(st_+1) +: 32*16]),
            .dn_gnt(rgnt_bus[3*(st_+1) +: 3]), .dn_cr(rcr_bus[32*(st_+1) +: 32]), .dn_rsp(rrsp_bus[32*257*(st_+1) +: 32*257]),
            .l_req(CID >= 0 ? rg_req[CID < 0 ? 0 : CID] : 1'b0), .l_gnt(lr_gnt), .l_q(CID >= 0 ? cl_rq[32*16*(CID < 0 ? 0 : CID) +: 32*16] : '0),
            .l_cr(lr_cr), .l_rsp(lr_rsp));
        ot_hgi_vm_lanestation #(.K(3), .ID(CID < 0 ? 0 : CID), .REQW(280), .RSPW(1), .TAP(CID >= 0)) u_sw (.clk(clk), .rst_n(rst_n),
            .up_req(wreq_bus[3*st_ +: 3]), .up_q(wq_bus[32*280*st_ +: 32*280]), .up_gnt(wgnt_bus[3*st_ +: 3]), .up_cr(wcr_bus[32*st_ +: 32]),
            .up_rsp(wdn_bus[32*st_ +: 32]), .dn_req(wreq_bus[3*(st_+1) +: 3]), .dn_q(wq_bus[32*280*(st_+1) +: 32*280]),
            .dn_gnt(wgnt_bus[3*(st_+1) +: 3]), .dn_cr(wcr_bus[32*(st_+1) +: 32]), .dn_rsp(wdn_bus[32*(st_+1) +: 32]),
            .l_req(CID >= 0 ? wg_req[CID < 0 ? 0 : CID] : 1'b0), .l_gnt(lw_gnt), .l_q(CID >= 0 ? cl_wq[32*280*(CID < 0 ? 0 : CID) +: 32*280] : '0),
            .l_cr(lw_cr), .l_rsp(lw_dn));
        if (CID >= 0) begin : g_tap
            assign rg_gnt[CID] = lr_gnt; assign wg_gnt[CID] = lw_gnt;
            assign c_rcr[32*CID +: 32] = lr_cr; assign c_rr[32*257*CID +: 32*257] = lr_rsp;
            assign c_wcr[32*CID +: 32] = lw_cr; assign c_wdone[32*CID +: 32] = lw_dn;
        end
    end
`else
    ot_hgi_vm_lanearb #(.K(3), .REQW(16), .RSPW(257), .RLY(`RLY), .MUT(`ifdef ARBMUT 1 `else 0 `endif)) u_ar (.clk(clk), .rst_n(rst_n),
        .c_req(rg_req), .c_gnt(rg_gnt), .c_q({512'd0, a1_q, rq}), .c_cr(c_rcr), .c_rsp(c_rr), .g_q(g_rq), .g_cr(g_rcr), .g_rsp(g_rr));
    ot_hgi_vm_lanearb #(.K(3), .REQW(280), .RSPW(1), .RLY(`RLY), .MUT(`ifdef ARBMUT 1 `else 0 `endif)) u_aw (.clk(clk), .rst_n(rst_n),
        .c_req(wg_req), .c_gnt(wg_gnt), .c_q({a2_q, {32*280{1'b0}}, w2q}), .c_cr(c_wcr), .c_rsp(c_wdone), .g_q(g_wq), .g_cr(g_wcr),
        .g_rsp(g_wdone));
`endif
    assign rq_cr = c_rcr[31:0]; assign rr = c_rr[0 +: 32*257]; assign w2_cr = c_wcr[31:0]; assign w2_done = c_wdone[31:0];
    ot_hgi_vm_unit #(.NC(2), .RP(32), .W2(32), .LQ(`LQ)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}),
        .status(vm_status), .wq(280'd0), .wq_done(), .rq(g_rq), .rq_cr(g_rcr), .rr(g_rr), .w2q(g_wq), .w2q_cr(g_wcr), .w2q_done(g_wdone));
    // ---- agents: bursts of 8 sectors a lane on the free region (sectors AR0.. read-only, AW0.. written), checked
    localparam integer AR0 = 14336, AW0 = 18432, AN = 2048;
    function automatic [255:0] apat(input integer sct, input integer it);
        for (integer w = 0; w < 8; w = w + 1) apat[32*w +: 32] = 32'(sct * 7919 + w * 131 + it * 1000003) ^ 32'hC3C3_0000;
    endfunction
    integer a_on = 0, a1_bursts = 0, a2_bursts = 0, a2_it = -1;
    initial begin : agent1
        integer cr [0:31]; integer nx [0:31]; integer exp_ [0:31][0:127]; integer h [0:31], t [0:31], got, base, gap;
        forever begin
            @(negedge clk);
            if (a_on) begin
                base = AR0 + 256 * ($urandom % (AN / 256));
                for (integer l = 0; l < 32; l = l + 1) begin cr[l] = `LQ; nx[l] = base + l; h[l] = 0; t[l] = 0; end
                a1_req = 1; while (!rg_gnt[1]) @(negedge clk); @(negedge clk);
                got = 0;
                while (got < 256) begin
                    for (integer l = 0; l < 32; l = l + 1) begin
                        a1_q[l*16 +: 16] = 0;
                        if (nx[l] < base + 256 && cr[l] > 0) begin
                            a1_q[l*16 +: 16] = {1'b1, 15'(nx[l])}; exp_[l][t[l] % 128] = nx[l]; t[l] = t[l] + 1; nx[l] = nx[l] + 32; cr[l] = cr[l] - 1;
                        end
                    end
                    @(posedge clk);
                    for (integer l = 0; l < 32; l = l + 1) begin
                        if (c_rcr[32 + l]) cr[l] = cr[l] + 1;
                        if (c_rr[(32 + l)*257 + 256]) begin
                            if (c_rr[(32 + l)*257 +: 256] !== apat(exp_[l][h[l] % 128], 0)) begin
                                errors = errors + 1; if (errors < 20) $display("ERR agent1 sector %0d", exp_[l][h[l] % 128]); end
                            h[l] = h[l] + 1; got = got + 1;
                        end
                    end
                    @(negedge clk);
                end
                a1_q = 0;
                begin : home integer w; w = 0; while (w < 12 + 2 * `RLY) begin @(posedge clk);
                    for (integer l = 0; l < 32; l = l + 1) if (c_rcr[32 + l]) cr[l] = cr[l] + 1; w = w + 1; end end
                for (integer l = 0; l < 32; l = l + 1) if (cr[l] != `LQ) begin errors = errors + 1; $display("ERR agent1 credits lane %0d = %0d", l, cr[l]); end
                @(negedge clk); a1_req = 0; a1_bursts = a1_bursts + 1;
                gap = $urandom % 300; repeat (gap) @(negedge clk);
            end
        end
    end
    initial begin : agent2
        integer cr [0:31]; integer nx [0:31]; integer sent, done_n, gap;
        forever begin
            @(negedge clk);
            if (a_on) begin
                a2_it = a2_it + 1;
                for (integer l = 0; l < 32; l = l + 1) begin cr[l] = `LQ; nx[l] = AW0 + l; end
                a2_req = 1; while (!wg_gnt[2]) @(negedge clk); @(negedge clk);
                sent = 0; done_n = 0;
                while (done_n < AN) begin
                    for (integer l = 0; l < 32; l = l + 1) begin
                        a2_q[l*280 +: 280] = 0;
                        if (nx[l] < AW0 + AN && cr[l] > 0) begin
                            a2_q[l*280 +: 280] = {1'b1, 15'(nx[l]), apat(nx[l], a2_it + 1), 8'hFF}; nx[l] = nx[l] + 32; cr[l] = cr[l] - 1; sent = sent + 1;
                        end
                    end
                    @(posedge clk);
                    for (integer l = 0; l < 32; l = l + 1) begin
                        if (c_wcr[64 + l]) cr[l] = cr[l] + 1;
                        if (c_wdone[64 + l]) done_n = done_n + 1;
                    end
                    @(negedge clk);
                end
                a2_q = 0;
                begin : home2 integer w; w = 0; while (w < 12 + 2 * `RLY) begin @(posedge clk);
                    for (integer l = 0; l < 32; l = l + 1) if (c_wcr[64 + l]) cr[l] = cr[l] + 1; w = w + 1; end end
                for (integer l = 0; l < 32; l = l + 1) if (cr[l] != `LQ) begin errors = errors + 1; $display("ERR agent2 credits lane %0d = %0d", l, cr[l]); end
                @(negedge clk); a2_req = 0; a2_bursts = a2_bursts + 1;
                gap = $urandom % 300; repeat (gap) @(negedge clk);
            end
        end
    end
`elsif WIDE
    ot_hgi_vm_unit #(.NC(2), .RP(32), .W2(32)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}),
        .status(vm_status), .wq(280'd0), .wq_done(), .rq(rq), .rq_cr(rq_cr), .rr(rr), .w2q(w2q), .w2q_cr(w2_cr), .w2q_done(w2_done));
`else
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status(vm_status), .wq(280'd0), .wq_done());
`endif
    // sector write / read through bench client 1 (one request in flight)
    task automatic vm_sec(input we, input [31:0] sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, sec[26:0], 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 1000) begin $display("ERR bench VM request timed out"); errors = errors + 1; end
            qd = tr[255:0];
        end
    endtask
    integer k, nf; integer t_acc [0:4095]; integer t_ret [0:4095];
    always @(posedge clk) if (inrec && cyc % 50000 == 0) begin $display("PROGRESS cyc %0d retired %0d", cyc, k); $fflush; end
`ifdef WIDE2
`ifdef XDBG
    reg xf_seen = 0;
    always @(posedge clk) if (`CTLP.st == 4'd11 && !xf_seen) begin
        xf_seen <= 1;
        $display("XFAULT cyc %0d vf_seen %0d vfault_q %0d lane_ovf %0d cfault_q %0d s0 %0d r_v %0d r_gop %0d st_prev? wl_nout %0d wl_nin %0d",
            cyc, `CTLP.vf_seen, `CTLP.vfault_q, `CTLP.lane_ovf, `CTLP.cfault_q, `CTLP.s0v_q, `CTLP.r_v, `CTLP.r_gop,
            `CTLP.wl[0 +: 16], `CTLP.wl[16 +: 16]); $fflush;
        $display("XFAULT wl A base %0d so %0d si %0d  B base %0d so %0d  R base %0d  red %0d sfu %0d m1 %0d lfull %0d lb0 %0d Lr0 %0d",
            `CTLP.wl[40 +: 24], `CTLP.wl[64 +: 24], `CTLP.wl[88 +: 24], `CTLP.wl[138 +: 24], `CTLP.wl[162 +: 24], `CTLP.wl[484 +: 24],
            `CTLP.wl[478 +: 2], `CTLP.wl[371 +: 3], `CTLP.wl[360 +: 3], `CTLP.l_full_q, `CTLP.lb[0], `CTLP.Lr[0]);
    end
    always @(posedge clk) if (`CTLP.go) $display("XGO cyc %0d A base %0d so %0d si %0d no %0d ni %0d", cyc, `CTLP.wl[40 +: 24],
        `CTLP.wl[64 +: 24], `CTLP.wl[88 +: 24], `CTLP.wl[0 +: 16], `CTLP.wl[16 +: 16]);
    always @(posedge clk) if (inrec && cyc % 2000 == 0) begin
        $display("XDBG cyc %0d st %0d r_v %0d r_gop %0d r_cdone %0d d_v %0d d_ph %0d st_busy %0d st_done %0d sk %0d s_rows %0d bq_n %0d rp_on %0d mq0 %0d lq0 %0d cr0 %0d dr_live %0d drk %0d e_rows %0d rg %0d/%0d nexec %0d",
            cyc, `CTLP.st, `CTLP.r_v, `CTLP.r_gop, `CTLP.r_cdone, `CTLP.d_v, `CTLP.d_ph, `CTLP.st_busy, `CTLP.st_done, `CTLP.sk,
            `CTLP.s_rows, `CTLP.bq_n, `CTLP.rp_on, `CTLP.mq_n[0], `CTLP.lq_n[0], `CTLP.cr[0], `CTLP.dr_live, `CTLP.drk, `CTLP.e_rows,
            `CTLP.rg_req, `CTLP.rg_q, `CTLP.u_rec.nexec); $fflush; end
    always @(posedge clk) if (inrec && cyc % 2000 == 1) begin
        $display("XBQ head id %0d cnt %0d b_act %0d b_left %0d s_md %0d | lane heads:", `CTLP.bq_id[`CTLP.bq_h], `CTLP.bq_cnt[`CTLP.bq_h],
                 `CTLP.b_act, `CTLP.b_left, `CTLP.s_md);
        for (integer b = 0; b < 32; b = b + 1) if (`CTLP.lq_n[b] != 0)
            $display("XBQ   lane %0d n %0d beat %0d md %0d", b, `CTLP.lq_n[b], `CTLP.m_bt(`CTLP.lq[b][`CTLP.lq_h[b]][`CTLP.MW+255 -: `CTLP.MW]),
                     `CTLP.m_md(`CTLP.lq[b][`CTLP.lq_h[b]][`CTLP.MW+255 -: `CTLP.MW]));
    end
`endif
`endif
    // progress watchdog: a record pipeline that stops retiring (a hang) is a FAIL, not a wait
    integer last_prog = 0;
    always @(posedge clk) if (rst_n && (done || !inrec)) last_prog = cyc;
`ifndef WDOG
`define WDOG 300000
`endif
    always @(posedge clk) if (inrec && cyc - last_prog > `WDOG) begin
        $display("ERR no record retired for 300000 edges (hang): retired %0d", k); $display("HGI_SU_PROD FAIL errors=hang"); $finish;
    end
    always @(posedge clk) begin if (rst_n && done) begin t_ret[k] = cyc; k = k + 1; end if (rst_n && fault) nf = nf + 1; end
    // controller phase census (st sampled each edge while a record is in the unit)
    integer ph [0:4]; reg inrec = 0;
`ifdef WIDE
    // the wide unit pipelines records: count each slot's busy edges (they overlap)
    always @(posedge clk) if (inrec) begin
        if (`CTLP.a_span) ph[0] = ph[0] + 1;
        if (`CTLP.a_stage) ph[1] = ph[1] + 1;
        if (`CTLP.a_run) ph[2] = ph[2] + 1;
        if (`CTLP.a_drain) ph[3] = ph[3] + 1;
    end
`else
    always @(posedge clk) if (inrec) begin
        case (`CTLP.st)
            4'd1, 4'd2, 4'd3: ph[0] = ph[0] + 1;                // span: region walk / extent multiply / placement
            4'd4, 4'd5: ph[1] = ph[1] + 1;                      // stage
            4'd6, 4'd7: ph[2] = ph[2] + 1;                      // compute (go -> idle)
            4'd8, 4'd9: ph[3] = ph[3] + 1;                      // drain
            default: ph[4] = ph[4] + 1;                         // accept / done / STREAM out
        endcase
    end
`endif
    integer c, j, t, cid, sfu, r0, nr, vi0, nvi, ve0, nve, cases = 0, words = 0, t0, t1, w;
    reg [255:0] qd;
    initial begin
        repeat (3) @(posedge clk);
`ifdef SHARED
        rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (j = AR0; j < AR0 + AN; j = j + 1) vm_sec(1'b1, j, apat(j, 0), qd);
`endif
        for (c = 0; c < NCASE; c = c + 1) begin
            r0 = casem[c][223:192]; nr = casem[c][191:160]; vi0 = casem[c][159:128];
            nvi = casem[c][127:96]; ve0 = casem[c][95:64]; nve = casem[c][63:32]; cid = casem[c][30:0]; sfu = casem[c][31];
            if (sfu != GL) continue;
`ifndef SHARED
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
`endif
            for (j = 0; j < nvi; j = j + 1) vm_sec(1'b1, vmim[vi0 + j][287:256], vmim[vi0 + j][255:0], qd);
            k = 0; nf = 0; for (j = 0; j < 5; j = j + 1) ph[j] = 0;
`ifdef SHARED
            a_on = 1;
`endif
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); if (j == 0) t0 = cyc; t_acc[j] = cyc; inrec = 1; #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
            t1 = cyc; inrec = 0;
`ifdef SHARED
            a_on = 0; repeat (2000) @(posedge clk);       // the agents finish their current bursts
            if (a1_req || a2_req) begin errors = errors + 1; $display("ERR agents still busy"); end
            for (j = AW0; j < AW0 + AN; j = j + 1) begin
                vm_sec(1'b0, j, 256'd0, qd);
                if (a2_it >= 0 && qd !== apat(j, a2_it + 1)) begin errors = errors + 1; if (errors < 20) $display("ERR agent2 final sector %0d", j); end
            end
            $display("SHARED case %0d: agent bursts read %0d write %0d (group shared with the SU)", cid, a1_bursts, a2_bursts);
`endif
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", cid, k, nr, nf); errors = errors + 1; end
            for (j = 0; j < k; j = j + 1) $display("REC %0d %0d accept %0d retire %0d", cid, j, t_acc[j] - t0, t_ret[j] - t0);
            $display("CASE %0d service %0d span %0d stage %0d compute %0d drain %0d other %0d", cid, t1 - t0, ph[0], ph[1],
                     ph[2], ph[3], ph[4]); $fflush;
            for (j = 0; j < nve; j = j + 1) begin
                vm_sec(1'b0, vmem[ve0 + j][287:256], 256'd0, qd);
                for (w = 0; w < 8; w = w + 1)
                    if (qd[32*w +: 32] !== vmem[ve0 + j][32*w +: 32]) begin
                        if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", cid, vmem[ve0 + j][287:256] * 8 + w,
                                                  qd[32*w +: 32], vmem[ve0 + j][32*w +: 32]);
                        errors = errors + 1;
                    end
                words = words + 8;
            end
            cases = cases + 1;
        end
        if (vm_status[18]) begin errors = errors + 1; $display("ERR VM status fault %b", vm_status[18:16]); end
        $display("summary: %0d production-shape cases, %0d sink-sector words checked (written = golden, rest = pre-op)",
                 cases, words);
        if (errors == 0 && cases > 0) $display("HGI_SU_PROD PASS"); else $display("HGI_SU_PROD FAIL errors=%0d", errors);
        $finish;
    end
endmodule
