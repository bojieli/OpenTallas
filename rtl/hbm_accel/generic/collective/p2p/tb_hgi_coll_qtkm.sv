`timescale 1ns/1ps
// tb_hgi_coll_qtkm (HBM P2P step 1, 2026-10-14): derived from tb_hgi_coll_tkm.sv (untouched): the SW quadrant body
// ot_hgi_coll_qep (qid 0 = QSOLO: TOPK_MERGE runs whole) with its line writes crossing RLY relays by credit flow
// (ot_hgi_coll_crl_tx / rx, the vmport FIFO); the record must not retire before the last write landed.  CRL_MUT 1 must FAIL.
// Original: tb_hgi_coll_tkm (hgi-1010/k): hardware COLL.TOPK_MERGE on ot_hgi_coll_ep (TKM = 1), one real rank of a G-rank group.
//
// The record (header COLL op 2, A / B / O [/ R] effective descriptors) enters through the die record bus (hgi_rec +
// hgi_recx); the group size through the config station (word 46).  Models (labelled, as hgi_e2e_coll_slot):
//   * VM: this rank's A (values) / B (ids) at their bases; the inject path reads the two 8-word halves the endpoint
//     names (hgi_inj_addr) -- flit f = {B[8f .. 8f+7], A[8f .. 8f+7]};
//   * switch tier + peers: every departure of this die's flit f releases each peer q's flit f (q's own A / B) LATC cycles
//     later (+ q mod 5 skew, +SKEW random), one flit per port per cycle, egress credits returning CRED cycles after use;
//   * the sink's O / R line writes land in VM (word mask), with +WSTALL% random write back-pressure.
// Checks: O (and R) against the golden (tools/hgi_coll_tkm_vectors.py = hgi_sim u_coll_topk_merge), no write outside
// O / R, retire with done (or with fault when the case expects one: NaN).  Reports go -> done cycles.
//   +DIR=<case dir>  +WSTALL=<pct>  +SKEW=<max extra cycles>  +SEED=<n>
module tb_hgi_coll_qtkm;
    parameter integer TKM_KMAX = 2048, TKM_NATIVE = 1;
    parameter integer MUT_TKM = 0;
    parameter integer RLY = 8, TCRD = 8, CRL_MUT = 0;
    parameter integer LATC = 453, CRED = 137;
    parameter integer INJLAT = 12, INJSU = INJLAT;
    localparam integer NMAX = 2048, GMAX = 96;
    localparam integer LANES = 16, FW = 512, PWT = FW + 33, NPT = 3, INJ = 2, DEL = 4;
    reg clk = 0, rst_n = 0;
    always #0.4167 clk = ~clk;
    // ---------------------------------------------------------------- case
    reg [31:0] cfgw [0:15];
    reg [31:0] pa [0:GMAX*NMAX-1];
    reg [31:0] pb [0:GMAX*NMAX-1];
    reg [31:0] eo [0:NMAX-1];
    reg [31:0] er [0:NMAX-1];
    reg [31:0] nq [0:GMAX-1];            // every rank's n (n.hex)
    integer G, N, M, NL, K, RANK, HASR, NOUT, XFAULT, ABASE, BBASE, OBASE, RBASE, WSTALL, SKEW, SEED, PF, GB;
    reg [31:0] vm [0:262143];
    bit vmw [0:262143];                    // words written by the sink
    // ---------------------------------------------------------------- DUT
    reg  [967:0] rec; reg [553:0] recx; reg [39:0] cfg;
    wire [2:0] ret;
    wire [INJ*16-1:0] ii; wire [INJ-1:0] ir; wire [4*INJ*FW-1:0] injq;
    wire [NPT-1:0] txv, rxc; wire [NPT*PWT-1:0] txf; reg [NPT-1:0] crr, rxv; reg [NPT*PWT-1:0] rxf;
    wire [DEL-1:0] dv; wire [DEL*PWT-1:0] dfl; wire flt; wire [31:0] cst; wire [93:0] rfo; wire [79:0] vma;
    wire [INJ*80-1:0] iad; wire tw_v; wire [39:0] tw_a; wire [15:0] tw_m; wire [FW-1:0] tw_d; reg tw_r;
    // P2P: the SW quadrant body (qid 0, QSOLO: TOPK_MERGE runs whole here) with its TOPK line writes crossing RLY die relay
    // stages each way by credit flow (ot_hgi_coll_crl_tx in the engine, ot_hgi_coll_crl_rx in ot_hgi_coll_vmport) to the
    // VM write model (valid / ready with +WSTALL back-pressure)
    wire q_v, q_r, q_idle, t_v, f_cr, ctxf, crxf; wire [39:0] q_a; wire [15:0] q_m; wire [FW-1:0] q_d; wire [FW+55:0] t_d, o_d;
    ot_hgi_coll_qep #(.TKM_NATIVE(TKM_NATIVE), .INJLAT(INJLAT), .QSOLO(0), .SOLO_CAP(1), .PFMAX(512), .TKM(1), .TKM_KMAX(TKM_KMAX), .MUT_TKM(MUT_TKM), .NPT(NPT), .PIPE(1),
                      .RGXHW(1), .RFMT(0)) u_ce (.clk(clk), .rst_n(rst_n), .tkm_clk_core(clk), .tkm_clk_buffer(clk), .tkm_clk_packer(clk), .tkm_clk_lane({4{clk}}), .tkm_clk_tile({32{clk}}), .pclk(clk), .prst_n(rst_n), .qid(2'd0),
        .rank(8'd0), .pf(16'd0), .go(1'b0),
        .inj_idx(ii), .inj_rd(ir), .inj_q(injq), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
        .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dv), .del_flit(dfl), .fault(flt), .stat_credit_stall(cst),
        .hgi_rec(rec), .hgi_ret(ret), .hgi_cfg(cfg), .hgi_rowfmt_o(rfo), .hgi_rowfmt_i(3'b000), .hgi_vmaddr(vma), .hgi_del_obase(),
        .rg_lq_v(), .rg_lq_rdy(1'b1), .rg_lq_addr(), .rg_lr_v(1'b0), .rg_lr_data(512'd0), .rg_hq_v(), .rg_hq_rdy(2'b11),
        .rg_hq_addr(), .rg_hq_tag(), .rg_hr_v(2'b00), .rg_hr_tag(16'd0), .rg_hr_data(512'd0), .rg_w_v(), .rg_w_addr(),
        .rg_w_vm(), .rg_w_data(), .rg_w_rdy({DEL{1'b1}}), .rg_w_idle(1'b1),
        .hgi_recx(recx), .hgi_inj_addr(iad), .tk_w_v(q_v), .tk_w_addr(q_a), .tk_w_mask(q_m), .tk_w_data(q_d), .tk_w_rdy(q_r),
        .tk_w_idle(q_idle));
    ot_hgi_coll_crl_tx #(.W(FW + 56), .CRD(TCRD)) u_tx (.clk(clk), .rst_n(rst_n), .in_v(q_v), .in_d({q_a, q_m, q_d}), .in_rdy(q_r),
        .idle(q_idle), .t_v(t_v), .t_d(t_d), .f_cr(bw[RLY-1]), .fault(ctxf));
    reg [FW+56:0] fw [0:RLY-1]; reg bw [0:RLY-1];
    always @(posedge clk) begin fw[0] <= {t_v, t_d}; bw[0] <= f_cr; for (integer i = 1; i < RLY; i = i + 1) begin fw[i] <= fw[i-1]; bw[i] <= bw[i-1]; end end
    ot_hgi_coll_crl_rx #(.W(FW + 56), .CRD(TCRD), .MUT(CRL_MUT)) u_rx (.clk(clk), .rst_n(rst_n), .t_v(fw[RLY-1][FW+56]), .t_d(fw[RLY-1][FW+55:0]),
        .f_cr(f_cr), .out_v(tw_v), .out_d(o_d), .out_rdy(tw_r), .fault(crxf));
    assign tw_a = o_d[FW+55 -: 40]; assign tw_m = o_d[FW+15 -: 16]; assign tw_d = o_d[FW-1:0];
    // ---------------------------------------------------------------- inject model (two 8-word halves a flit)
    reg [4*INJ*FW-1:0] inj_now;
    always @* begin
        inj_now = 0;
        for (integer i = 0; i < INJ; i = i + 1) if (ir[i]) begin
            integer f, lo, hi; f = int'(ii[16*i +: 16]);
            lo = int'(iad[80*i +: 40]); hi = int'(iad[80*i + 40 +: 40]);
            for (integer j = 0; j < 8; j = j + 1) begin
                inj_now[(f % 4) * INJ * FW + i * FW + 32 * j +: 32] = vm[(lo + j) & 262143];
                inj_now[(f % 4) * INJ * FW + i * FW + 32 * (8 + j) +: 32] = vm[(hi + j) & 262143];
            end
        end
    end
    // Real quadrant shape: the SU responds after the die transport latency, never on the request edge.
    // INJSU differs from INJLAT only for the response-latency mutant.
    generate if (INJSU == 0) begin : g_inj0
        assign injq = inj_now;
    end else begin : g_inj_lat
        reg [4*INJ*FW-1:0] inj_pipe [0:INJSU-1];
        always @(posedge clk) begin
            inj_pipe[0] <= rst_n ? inj_now : '0;
            for (integer j = 1; j < INJSU; j = j + 1) inj_pipe[j] <= inj_pipe[j-1];
        end
        assign injq = inj_pipe[INJSU-1];
    end endgenerate
    function automatic [FW-1:0] peer_flit(input integer q, input integer m);
        reg [FW-1:0] d;
        d = '0;
        for (integer j = 0; j < 8; j = j + 1) begin
            // the sender's TOPK_MERGE inject (ot_hgi_coll_ep TKM): pad slots past its n, NaN canonicalised
            if (8 * m + j < int'(nq[q])) begin
                d[32*j +: 32] = pa[q * NMAX + 8 * m + j];
                if (d[32*j + 23 +: 8] == 8'hFF && d[32*j +: 23] != 23'd0) d[32*j +: 32] = 32'h7FC0_0000;
                d[32*(8+j) +: 32] = pb[q * NMAX + 8 * m + j];
            end else begin
                d[32*j +: 32] = 32'hFFFF_FFFF; d[32*(8+j) +: 32] = 32'hFFFF_FFFF;
            end
        end
        peer_flit = d;
    endfunction
    // ---------------------------------------------------------------- switch tier + peers (as hgi_e2e_coll_slot)
    localparam integer QD = 16384;
    reg [PWT-1:0] eqf [0:NPT*QD-1]; longint eqt [0:NPT*QD-1]; integer eh [0:NPT-1]; integer et [0:NPT-1];
    longint cin [0:NPT*QD-1]; integer ch [0:NPT-1]; integer ct [0:NPT-1];
    longint ceg [0:NPT*QD-1]; integer gh [0:NPT-1]; integer gt [0:NPT-1]; integer eg_cred [0:NPT-1];
    longint cyc = 0;
    initial for (integer p = 0; p < NPT; p = p + 1) begin eg_cred[p] = 256; eh[p] = 0; et[p] = 0; ch[p] = 0; ct[p] = 0; gh[p] = 0; gt[p] = 0; end
    task automatic sched(input integer p, input longint t, input [PWT-1:0] f);
        begin
            if (et[p] - eh[p] >= QD) $fatal(1, "switch queue overflow");
            eqf[p*QD + et[p] % QD] = f; eqt[p*QD + et[p] % QD] = t; et[p] = et[p] + 1;
        end
    endtask
    integer seed_r;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
                reg [PWT-1:0] f; integer idx, m, rel;
                f = txf[p*PWT +: PWT]; idx = int'(f[FW +: 16]);
                cin[p*QD + ct[p] % QD] = cyc + CRED; ct[p] = ct[p] + 1;
                rel = RANK - GB; m = idx - rel * PF;
                if (!f[PWT-1] || m < 0 || m >= PF) $fatal(1, "unexpected departure kind %0d idx %0d", f[PWT-1], idx);
                for (integer q = 0; q < G; q = q + 1) if (q != rel)
                    sched((q + m) % NPT, cyc + LATC + (q % 5) + ((SKEW > 0) ? ($urandom() % (SKEW + 1)) : 0),
                          {1'b1, 8'hFF, 8'(GB + q), 16'(q * PF + m), peer_flit(q, m)});
            end
            for (integer p = 0; p < NPT; p = p + 1) begin
                while (gt[p] > gh[p] && ceg[p*QD + gh[p] % QD] <= cyc) begin gh[p] = gh[p] + 1; eg_cred[p] = eg_cred[p] + 1; end
                rxv[p] <= 1'b0;
                if (et[p] > eh[p] && eqt[p*QD + eh[p] % QD] <= cyc && eg_cred[p] > 0) begin
                    rxv[p] <= 1'b1; rxf[p*PWT +: PWT] <= eqf[p*QD + eh[p] % QD];
                    eh[p] = eh[p] + 1; eg_cred[p] = eg_cred[p] - 1;
                end
                if (rxc[p]) begin ceg[p*QD + gt[p] % QD] = cyc + CRED; gt[p] = gt[p] + 1; end
                crr[p] <= 1'b0;
                if (ct[p] > ch[p] && cin[p*QD + ch[p] % QD] <= cyc) begin ch[p] = ch[p] + 1; crr[p] <= 1'b1; end
            end
            // ---- sink writes
            if (tw_v && tw_r) begin
                for (integer j = 0; j < 16; j = j + 1) if (tw_m[j]) begin
                    vm[int'(tw_a) + j] = tw_d[32*j +: 32]; vmw[int'(tw_a) + j] = 1'b1;
                end
            end
            tw_r <= (WSTALL == 0) || (($urandom() % 100) >= WSTALL);
            if (|dv) $fatal(1, "a delivery reached the SU deliver port during a TOPK_MERGE");
        end else begin
            rxv <= 0; crr <= 0; tw_r <= 1'b1;
        end
    end
    // ---------------------------------------------------------------- phase timeline (report only)
    reg [3:0] ph_q = 0; longint t_first = -1, t_last = -1, nperm0 = 0, t_rec = 0;
    always @(posedge clk) if (rst_n) begin
        if (rec[0]) t_rec = cyc;
        if (u_ce.g_tkm.phase_trace != ph_q) $display("PHASE %0d at %0d", u_ce.g_tkm.phase_trace, cyc - t_rec);
        ph_q <= u_ce.g_tkm.phase_trace;
        if (|u_ce.e_dv) begin if (t_first < 0) t_first = cyc - t_rec; t_last = cyc - t_rec; end
        if (u_ce.g_tkm.phase_trace == 4'd1 && u_ce.tk_permit != 4'hF) nperm0 = nperm0 + 1;
    end
    // ---------------------------------------------------------------- record construction
    function automatic [255:0] desc(input integer space, input integer fmt, input integer base, input integer n);
        reg [255:0] d;
        d = '0; d[1:0] = 2'(space); d[4:2] = 3'(fmt); d[47:8] = 40'(base); d[67:48] = 20'(n); d[87:68] = 20'd1;
        desc = d;
    endfunction
    string dir;
    integer t0, t1, errs, ok_done, ok_fault;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR=");
        if (!$value$plusargs("WSTALL=%d", WSTALL)) WSTALL = 0;
        if (!$value$plusargs("SKEW=%d", SKEW)) SKEW = 0;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        seed_r = SEED; void'($urandom(SEED));
        $readmemh({dir, "/cfg.hex"}, cfgw);
        $readmemh({dir, "/a.hex"}, pa);
        $readmemh({dir, "/b.hex"}, pb);
        $readmemh({dir, "/o.hex"}, eo);
        $readmemh({dir, "/r.hex"}, er);
        $readmemh({dir, "/n.hex"}, nq);
        G = cfgw[0]; N = cfgw[1]; K = cfgw[2]; RANK = cfgw[3]; HASR = cfgw[4]; NOUT = cfgw[5]; XFAULT = cfgw[6];
        ABASE = cfgw[7]; BBASE = cfgw[8]; OBASE = cfgw[9]; RBASE = cfgw[10]; M = cfgw[12];
        GB = (G == 96) ? 0 : (RANK / G) * G; NL = int'(nq[RANK - GB]);
        PF = ((M != 0 ? M : NL) + 7) / 8;
        for (integer i = 0; i < 262144; i = i + 1) vm[i] = 32'hDEAD_0000 | (i & 16'hFFFF);
        for (integer i = 0; i < 262144; i = i + 1) vmw[i] = 1'b0;
        for (integer j = 0; j < NL; j = j + 1) begin
            vm[ABASE + j] = pa[(RANK - GB) * NMAX + j]; vm[BBASE + j] = pb[(RANK - GB) * NMAX + j];
        end
        rec = '0; recx = '0; cfg = 40'd0;
        repeat (5) @(posedge clk);
        rst_n = 1;
        repeat (3) @(posedge clk);
        cfg <= {1'b0, 1'b1, 6'd46, 32'(G)}; @(posedge clk);
        cfg <= {1'b1, 1'b0, 6'd0, 32'd0}; @(posedge clk);
        cfg <= 40'd0;
        repeat (10) @(posedge clk);
        while (!ret[0]) @(posedge clk);
        begin
            reg [127:0] h;
            h = '0; h[127:124] = 4'd6; h[123:118] = 6'd2; h[99:93] = HASR ? 7'b0110011 : 7'b0010011; h[63:32] = 32'(K); h[75:64] = 12'(M);
            rec <= {8'(RANK), 21'd0, 21'(NOUT), 21'(NL), 256'd0, desc(1, 5, OBASE, NOUT), desc(1, 0, ABASE, NL), h, 1'b1};
            recx <= {21'(HASR ? NOUT : 0), 21'(NL), HASR ? desc(1, 0, RBASE, NOUT) : 256'd0, desc(1, 5, BBASE, NL)};
        end
        t0 = int'(cyc);
        @(posedge clk); rec[0] <= 1'b0;
        ok_done = 0; ok_fault = 0;
        while (!ret[1] && !ret[2] && int'(cyc) - t0 < 400000) @(posedge clk);
        t1 = int'(cyc);
        ok_done = ret[1]; ok_fault = ret[2];
        repeat (5) @(posedge clk);
        errs = 0;
        if (XFAULT != 0) begin
            if (!ok_fault) begin $display("FAIL expected a fault (done %0d)", ok_done); errs = errs + 1; end
        end else begin
            if (!ok_done || ok_fault) begin $display("FAIL no clean retire: done %0d fault %0d", ok_done, ok_fault); errs = errs + 1; end
            for (integer j = 0; j < NOUT; j = j + 1) begin
                if (vm[OBASE + j] !== eo[j]) begin
                    if (errs < 8) $display("FAIL O[%0d] = %08x golden %08x", j, vm[OBASE + j], eo[j]); errs = errs + 1;
                end
                if (HASR && vm[RBASE + j] !== er[j]) begin
                    if (errs < 8) $display("FAIL R[%0d] = %08x golden %08x", j, vm[RBASE + j], er[j]); errs = errs + 1;
                end
            end
            for (integer i = 0; i < 262144; i = i + 1)
                if (vmw[i] && !(i >= OBASE && i < OBASE + NOUT) && !(HASR && i >= RBASE && i < RBASE + NOUT)) begin
                    if (errs < 8) $display("FAIL write outside O / R at %0d", i); errs = errs + 1;
                end
        end
        $display("TKM G=%0d n=%0d M=%0d k=%0d nout=%0d rank=%0d R=%0d CYCLES=%0d SURV=%0d INS=%0d SINK=%0d", G, NL, M, K, NOUT, RANK, HASR,
                 t1 - t0, u_ce.g_tkm.stat_surv, u_ce.g_tkm.stat_ins, u_ce.g_tkm.stat_cycles);
        $display("TIMELINE first_delivery=%0d last_delivery=%0d sink_credit_blocked_cycles=%0d", t_first, t_last, nperm0);
        if (ctxf || crxf) begin $display("FAIL credit link fault tx %0d rx %0d", ctxf, crxf); errs = errs + 1; end
        if (errs == 0) $display("PASS tb_hgi_coll_tkm %s", dir);
        else $display("FAIL tb_hgi_coll_tkm %s errors %0d", dir, errs);
        $finish;
    end
endmodule
