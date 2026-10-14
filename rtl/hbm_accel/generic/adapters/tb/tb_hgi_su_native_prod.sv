// Native adaptation of immutable33fe61ec9 production-vector bench.
// Compile SV/WIDE only; no monolithic VM or synthetic grant.
`timescale 1ps/1fs
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
// SV (el1013-hbm-redesign-suvop): the unit is ot_hgi_sv_unit (ports = ot_hgi_su_unit WIDE = 1; parameters N, M, LV, LWB,
// LQ, MUT_V); MUT_V = 1..6 its mutants.  The phase census reads `CTLP.a_span / a_stage / a_run / a_drain (1 b each;
// CTLP defaults to u.u_ctl, override with -DSV_CTLP=<path>); -DSV_WALK=<path> names its strided-sink frame-walk
// counter: printed a case, and an error when the production chain (CASE 0) used the fallback.
// SU_AUX (the vector set carries su_aux.svh / su_price.mem / su_vmg.mem): the summary adds the priced cost of each
// case's records (read from the vectors, never computed here) and service / price, and every case reports its
// mismatches split into written words and guard words (unwritten words of its sink sectors: SINK_UNSTAGED).
`ifdef SV
`ifdef SV_CTLP
`define CTLP `SV_CTLP
`else
`define CTLP u.u_ctl
`endif
`elsif WIDE2
`define CTLP u.g_xctl.u_ctl
`elsif WIDE
`define CTLP u.g_wctl.u_ctl
`elsif OLDHIER
`define CTLP u.u_ctl
`else
`define CTLP u.g_ctl.u_ctl
`endif
module tb_hgi_su_native_prod;
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
`ifdef SU_AUX
    `include "su_aux.svh"
    reg [31:0] pricem [0:NREC-1]; reg [7:0] vmgm [0:NVME-1];
`endif
    reg clk = 0; always #416.666625 clk = ~clk;
    reg vclk = 0; always #555.5555 vclk = ~vclk;
    reg [2196:0] recm [0:NREC-1]; reg [223:0] casem [0:NCASE-1];
    reg [287:0] vmim [0:NVMI-1]; reg [287:0] vmem [0:NVME-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/su_rec.mem"}, recm); $readmemh({dir, "/su_case.mem"}, casem);
        $readmemh({dir, "/su_vmi.mem"}, vmim); $readmemh({dir, "/su_vme.mem"}, vmem);
`ifdef SU_AUX
        $readmemh({dir, "/su_price.mem"}, pricem); $readmemh({dir, "/su_vmg.mem"}, vmgm);
`endif
    end
    integer errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [2196:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [18:0] vm_status; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire [RPL*16-1:0] rq; wire [RPL-1:0] rq_cr; wire [RPL*257-1:0] rr;
    wire [RPL*280-1:0] w2q; wire [RPL-1:0] w2_done, w2_cr;
`ifdef SV
`ifndef LQ
`define LQ 8
`endif
`ifndef MUT_V
`define MUT_V 0
`endif
    ot_hgi_sv_unit #(.N(`N), .M(`M), .LV(`LV), .LWB(`LWB), .LQ(`LQ), .MUT_V(`MUT_V)
`ifdef EP0
        , .EP0(`EP0)
`endif
       
`else
    ot_hgi_su_unit #(.N(`N), .M(`M), .LV(`LV), .LWB(`LWB), .GLU(GL), .MUT_DIRTY(MD)
`endif
`ifdef SV
`elsif WIDE2
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
        , .wrq(rq), .wrq_cr(rq_cr), .wrr(rr), .wwq(w2q), .wwq_cr(w2_cr), .wwq_done(w2_done), .rg_req(native_rg_req), .rg_gnt(native_rg_gnt), .wg_req(native_wg_req), .wg_gnt(native_wg_gnt)
`endif
`endif
        );
    wire native_rg_req,native_rg_gnt,native_wg_req,native_wg_gnt;
    wire[420:0]native_fault;wire[3:0]native_released;
    assign vm_status=19'b0;
    ot_hgi_sv_native_vm_fixture native(.clk(clk),.vclk(vclk),.rst_n(rst_n),
      .rg_req(native_rg_req),.rg_gnt(native_rg_gnt),.wg_req(native_wg_req),.wg_gnt(native_wg_gnt),
      .rq(rq),.rq_cr(rq_cr),.rr(rr),.wq(w2q),.wcredit(w2_cr),.wdone(w2_done),
      .su_q(uq),.bench_q(tq),.su_r(ur),.bench_r(tr),.fault(native_fault),.released(native_released));
    always @(posedge clk)if(rst_n&&(|native_fault))begin
      $display("HGI_SU_NATIVE_PROD FAIL native_fault=%h",native_fault);$finish;
    end
    // sector write / read through bench client 1 (one request in flight)
    task automatic vm_sec(input we, input [31:0] sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, sec[26:0], 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 10000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 10000) begin $display("ERR bench VM request timed out"); errors = errors + 1; end
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
        $display("ERR no record retired for 300000 edges (hang): retired %0d", k); $display("HGI_SU_NATIVE_PROD FAIL errors=hang"); $finish;
    end
    always @(posedge clk) begin if (rst_n && done) begin t_ret[k] = cyc; k = k + 1; end if (rst_n && fault) nf = nf + 1; end
`ifdef DRAIN_TRAFFIC
    // The software model records each record's sink before later in-place writes replace it. Observe actual
    // SU VM write pins; match each masked transaction once. No controller internals supply expected data.
    `include "su_drain_traffic.svh"
    reg [295:0] dt_file [0:NDRAIN_TRAFFIC-1];
    reg [255:0] dt_data [0:8*32768-1]; reg [7:0] dt_mask [0:8*32768-1];
    reg dt_valid [0:8*32768-1]; integer dt_next [0:32767];
    integer dt_seen = 0, dt_missing;
    initial begin : dt_init
        integer a, ix, sec;
        for (a = 0; a < 8*32768; a = a + 1) dt_valid[a] = 0;
        for (a = 0; a < 32768; a = a + 1) dt_next[a] = 0;
        #0.1;
        $readmemh({dir, "/su_drain_traffic.mem"}, dt_file);
        for (a = 0; a < NDRAIN_TRAFFIC; a = a + 1) begin
            sec = dt_file[a][295:264]; ix = 8*sec + dt_next[sec]; dt_next[sec] = dt_next[sec] + 1;
            dt_data[ix] = dt_file[a][255:0]; dt_mask[ix] = dt_file[a][263:256]; dt_valid[ix] = 1;
        end
    end
    always @(posedge clk) if (rst_n && inrec && c == 0) begin : dt_observe
        integer lane, sec, v, wordi, found; reg equalv; reg [255:0] data; reg [7:0] mask;
        for (lane = 0; lane < RPL; lane = lane + 1) if (w2q[lane*280 + 279]) begin
            sec = w2q[lane*280 + 264 +: 15]; data = w2q[lane*280 + 8 +: 256]; mask = w2q[lane*280 +: 8]; found = -1;
            for (v = 0; v < 8; v = v + 1) begin
                equalv = dt_valid[8*sec + v] && dt_mask[8*sec + v] == mask;
                for (wordi = 0; wordi < 8; wordi = wordi + 1)
                    if (mask[wordi] && data[32*wordi +: 32] !== dt_data[8*sec + v][32*wordi +: 32]) equalv = 0;
                if (equalv && found == -1) found = 8*sec + v;
            end
            if (found == -1) begin errors = errors + 1; if (errors < 20) $display("ERR DRAIN_TRAFFIC unexpected sector %0d mask %02x", sec, mask); end
            else begin dt_valid[found] = 0; dt_seen = dt_seen + 1; end
        end
    end
`endif
    // controller phase census (st sampled each edge while a record is in the unit)
    integer ph [0:4]; reg inrec = 0;
`ifdef SV
`ifdef SVDBG
    // ot_hgi_sv_unit diagnosis: every fault source at its first edge, and the controller state every 5,000 edges of a stall
    reg svf_seen = 0;
    always @(posedge clk) if (rst_n && !svf_seen && (`CTLP.dfault || `CTLP.rnfault || `CTLP.bkfault || `CTLP.lm_err_q || `CTLP.st_err || `CTLP.ad_fault)) begin
        svf_seen <= 1;
        $display("SVFAULT cyc %0d retired %0d d %0d rn %0d bk %0d lm %0d st %0d ad %0d | dstt %0d rk %0d lo %0d hi %0d too_big %0d a_two %0d ffr %b free %b stallc %0d cnt %0d rs %0d",
                 cyc, k, `CTLP.dfault, `CTLP.rnfault, `CTLP.bkfault, `CTLP.lm_err_q, `CTLP.st_err, `CTLP.ad_fault, `CTLP.dstt, `CTLP.rk,
                 `CTLP.cur_lo, `CTLP.cur_hi, `CTLP.too_big, `CTLP.a_two, `CTLP.ffr, `CTLP.fr_free, `CTLP.stallc, `CTLP.cnt, `CTLP.rs_r);
        $fflush;
    end
    always @(posedge clk) if (inrec && cyc - last_prog > 4000 && cyc % 5000 == 0) begin
        $display("SVSTALL cyc %0d retired %0d dstt %0d rk %0d rs %0d cnt %0d hfault %0d halted %0d fr_st %0d%0d%0d%0d fr_pin %0d %0d %0d %0d tail %b open %0d hst %h go %0d idle %0d x_cnt %0d cr_cnt %0d",
                 cyc, k, `CTLP.dstt, `CTLP.rk, `CTLP.rs_r, `CTLP.cnt, `CTLP.hfault, halted, `CTLP.fr_st[3], `CTLP.fr_st[2], `CTLP.fr_st[1], `CTLP.fr_st[0],
                 `CTLP.fr_pin[3], `CTLP.fr_pin[2], `CTLP.fr_pin[1], `CTLP.fr_pin[0], `CTLP.fr_tail, `CTLP.open_v, `CTLP.hst, `CTLP.go, `CTLP.idle, `CTLP.x_cnt, `CTLP.cr_cnt);
        $fflush;
    end
`endif
`endif
`ifdef WIDE
    // the wide unit pipelines records: count each slot's busy edges (they overlap)
    always @(posedge clk) if (inrec) begin
        if (`CTLP.a_span) ph[0] = ph[0] + 1;
        if (`CTLP.a_stage) ph[1] = ph[1] + 1;
        if (`CTLP.a_run) ph[2] = ph[2] + 1;
        if (`CTLP.a_drain) ph[3] = ph[3] + 1;
    end
`ifdef PHTRACE
`ifndef SV
    // el1011-sutput diagnosis: the record pipeline every 4 edges (FRONT state, RUN / DRAIN slots, streamed prefix)
    always @(posedge clk) if (inrec && cyc % 4 == 0)
        $display("PT %0d st %0d r %0d/%0d gop %0d cd %0d d %0d/%0d q1 %0d x %0d fs %0d lo %b idle %0d go %0d", cyc, `CTLP.st, `CTLP.r_v,
                 `CTLP.r_tag, `CTLP.r_gop, `CTLP.r_cdone, `CTLP.d_v, `CTLP.d_tag, `CTLP.q1_v, `CTLP.x_cnt, `CTLP.fs_on,
                 `CTLP.late_open, `CTLP.idle_q, `CTLP.go);
`endif
`endif
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
    reg [255:0] qd; integer e_wr, e_gd, n_gd, e0, pr, walk0 = 0;
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
`ifdef SU_AUX
            // SINK_UNSTAGED runs on the unit as the previous case left it (its local memory holds that case's data)
            if (cid != SU_CASE || c == 0) begin rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk); end
`else
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
`endif
`endif
            for (j = 0; j < nvi; j = j + 1) vm_sec(1'b1, vmim[vi0 + j][287:256], vmim[vi0 + j][255:0], qd);
            k = 0; nf = 0; for (j = 0; j < 5; j = j + 1) ph[j] = 0;
            e0 = errors; e_wr = 0; e_gd = 0; n_gd = 0;
`ifdef SV_WALK
            walk0 = `SV_WALK;
`endif
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
`ifdef DRAIN_TRAFFIC
            if (c == 0) begin
                dt_missing = 0;
                for (integer dt_i = 0; dt_i < 8*32768; dt_i = dt_i + 1) if (dt_valid[dt_i]) dt_missing = dt_missing + 1;
                $display("DRAIN_TRAFFIC golden %0d matched %0d missing %0d", NDRAIN_TRAFFIC, dt_seen, dt_missing);
                if (dt_missing != 0) errors = errors + dt_missing;
            end
`endif
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", cid, k, nr, nf); errors = errors + 1; end
            for (j = 0; j < k; j = j + 1) $display("REC %0d %0d accept %0d retire %0d", cid, j, t_acc[j] - t0, t_ret[j] - t0);
            $display("CASE %0d service %0d span %0d stage %0d compute %0d drain %0d other %0d", cid, t1 - t0, ph[0], ph[1],
                     ph[2], ph[3], ph[4]); $fflush;
`ifdef SU_AUX
            // the priced cost of this case's records (su_prod.json 'priced' x 10, generated: the bench never prices)
            pr = 0; for (j = 0; j < nr; j = j + 1) pr = pr + pricem[r0 + j];
            for (j = 0; j < nr; j = j + 1) $display("PRICE %0d %0d priced %0d.%0d", cid, j, pricem[r0 + j] / 10, pricem[r0 + j] % 10);
            $display("THROUGHPUT case %0d: service %0d price sum %0d.%0d (%0d records) ratio service/price %0.3f", cid,
                     t1 - t0, pr / 10, pr % 10, nr, (t1 - t0) * 10.0 / pr);
            if (cid == SU_CASE) $display("THROUGHPUT case %0d is SINK_UNSTAGED: exactness only, not a production price", cid);
`endif
`ifdef SV_WALK
            $display("WALK case %0d strided-sink frame walks %0d", cid, `SV_WALK - walk0);
            if (cid == 0 && `SV_WALK != walk0) begin errors = errors + 1; $display("ERR case 0 used the frame-walk drain fallback"); end
`endif
            for (j = 0; j < nve; j = j + 1) begin
                vm_sec(1'b0, vmem[ve0 + j][287:256], 256'd0, qd);
                for (w = 0; w < 8; w = w + 1)
                    if (qd[32*w +: 32] !== vmem[ve0 + j][32*w +: 32]) begin
                        if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", cid, vmem[ve0 + j][287:256] * 8 + w,
                                                  qd[32*w +: 32], vmem[ve0 + j][32*w +: 32]);
                        errors = errors + 1;
`ifdef SU_AUX
                        if (vmgm[ve0 + j][w]) e_wr = e_wr + 1; else e_gd = e_gd + 1;
`endif
                    end
`ifdef SU_AUX
                for (w = 0; w < 8; w = w + 1) if (!vmgm[ve0 + j][w]) n_gd = n_gd + 1;
`endif
                words = words + 8;
            end
`ifdef SU_AUX
            $display("CASECHK %0d: %0d sink sectors, %0d guard words; errors %0d (written words %0d, guard words %0d)", cid,
                     nve, n_gd, errors - e0, e_wr, e_gd);
            if (cid == SU_CASE) $display("CASECHK %0d is SINK_UNSTAGED", cid);
`endif
            cases = cases + 1;
        end
        if (vm_status[18]) begin errors = errors + 1; $display("ERR VM status fault %b", vm_status[18:16]); end
        $display("summary: %0d production-shape cases, %0d sink-sector words checked (written = golden, rest = pre-op)",
                 cases, words);
        if (errors == 0 && cases > 0) $display("HGI_SU_NATIVE_PROD PASS"); else $display("HGI_SU_NATIVE_PROD FAIL errors=%0d", errors);
        $finish;
    end
endmodule
