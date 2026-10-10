`timescale 1ns/1ps
// hgi-e2e (2026-10-09): unit slots of the die-level harness that need more than a wire-up.
//
// hgi_e2e_su_slot: SU.VOP (unit 2, GLU = 0: ot_hgi_su_record) or SFU.GLU (unit 3, GLU = 1: ot_hgi_sfu_record), the
// routed adapter form (LEGACY = 0), driving the REFERENCE stream unit ot_hdc_v41x_vec (N lanes, M SFU lanes) whose op
// port the adapters target.  The vec's synchronous VM ports (per lane: gather-index read, 4 operand reads returning the
// next cycle, element writes, reducer result writes) land on the harness VM model.  DIE GAP (hgi-adapters D1): the
// die's hfd_su / hfd_sfu are not bound to records, and the HGI packet VM has no synchronous streaming port; this slot
// shows the adapter + the reference unit's arithmetic on the record stream, not the die's SU timing.
module hgi_e2e_su_slot #(
    parameter integer UNIT = 2,
    parameter integer GLU = 0,
    parameter integer N = 16,
    parameter integer M = 8,
    parameter integer LV = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [1791:0] rec_desc,       // {I, R, O, D, C, B, A}
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault
);
    import "DPI-C" function int e2e_vm_rd(input int a);
    import "DPI-C" function void e2e_vm_wr(input int unit, input int a, input int v);
    localparam integer AW = 24, NR = N / 8, WB = 670;
    wire op_v, op_rdy, su_idle, su_fault; wire [WB-1:0] w;
    generate if (GLU) begin : g_sfu
        ot_hgi_sfu_record #(.LEGACY(0)) u_a (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
            .rec_hdr(rec_hdr), .rec_a(rec_desc[0 +: 256]), .rec_b(rec_desc[256 +: 256]), .rec_c(rec_desc[512 +: 256]),
            .rec_o(rec_desc[1024 +: 256]), .rec_n_a(rec_n_a), .rec_done(rec_done), .rec_fault(rec_fault), .halted(),
            .lg_v(1'b0), .lg_rdy(), .lg_w({WB{1'b0}}), .op_v(op_v), .op_rdy(op_rdy), .op_w(w), .su_idle(su_idle),
            .su_fault(su_fault));
    end else begin : g_su
        ot_hgi_su_record #(.LEGACY(0)) u_a (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
            .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_desc[0 +: 256]), .rec_b(rec_desc[256 +: 256]),
            .rec_c(rec_desc[512 +: 256]), .rec_d(rec_desc[768 +: 256]), .rec_o(rec_desc[1024 +: 256]),
            .rec_r(rec_desc[1280 +: 256]), .rec_i(rec_desc[1536 +: 256]), .rec_n_a(rec_n_a), .rec_done(rec_done),
            .rec_fault(rec_fault), .halted(), .drained(), .lg_v(1'b0), .lg_rdy(), .lg_w({WB{1'b0}}), .op_v(op_v),
            .op_rdy(op_rdy), .op_w(w), .su_idle(su_idle), .su_fault(su_fault));
    end endgenerate
    wire [N-1:0] vi_re; wire [N*AW-1:0] vi_addr; reg [N*32-1:0] vi_q;
    wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; reg [4*N*32-1:0] rd_q;
    wire [N-1:0] vm_we, kv_we; wire [N*AW-1:0] vm_waddr, kv_waddr; wire [N*32-1:0] vm_wdata, kv_wdata;
    wire [NR-1:0] res_we; wire [NR*AW-1:0] res_addr; wire [NR*32-1:0] res_data;
    wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire order_fault, retire_o;
    wire dbg_emit, dbg_ret, dbg_res; wire [7:0] dbg_eseq, dbg_rseq, dbg_sseq;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV)) u_vec (
        .clk(clk), .rst_n(rst_n), .go(op_v), .ready(op_rdy), .idle(su_idle),
        .i_nout(w[0 +: 16]), .i_nin(w[16 +: 16]), .i_asrc(w[32 +: 2]), .i_bsrc(w[34 +: 2]), .i_csrc(w[36 +: 2]),
        .i_dsrc(w[38 +: 2]), .i_abase(w[40 +: 24]), .i_aso(w[64 +: 24]), .i_asi(w[88 +: 24]),
        .i_aibase(w[112 +: 24]), .i_aind(w[136 +: 2]), .i_bbase(w[138 +: 24]), .i_bso(w[162 +: 24]),
        .i_bsi(w[186 +: 24]), .i_bhalf(w[210]), .i_cbase(w[211 +: 24]), .i_cso(w[235 +: 24]),
        .i_csi(w[259 +: 24]), .i_cpair(w[283]), .i_dbase(w[284 +: 24]), .i_dso(w[308 +: 24]),
        .i_dsi(w[332 +: 24]), .i_arnd(w[356]), .i_arelu(w[357]), .i_amin(w[358]), .i_cclip(w[359]),
        .i_m1(w[360 +: 3]), .i_m2(w[363 +: 2]), .i_qm(w[365 +: 3]), .i_ad(w[368 +: 3]), .i_sfu(w[371 +: 3]),
        .i_e1(w[374 +: 3]), .i_e2(w[377 +: 2]), .i_rnd(w[379]), .i_dst(w[380 +: 2]), .i_obase(w[382 +: 24]),
        .i_oso(w[406 +: 24]), .i_osi(w[430 +: 24]), .i_orow(w[454 +: 24]), .i_red(w[478 +: 2]),
        .i_redsq(w[480]), .i_redwhole(w[481]), .i_redtree(w[482]), .i_redrnd(w[483]), .i_rbase(w[484 +: 24]),
        .i_rso(w[508 +: 24]), .i_imm1(w[532 +: 32]), .i_imm2(w[564 +: 32]), .i_imm3(w[596 +: 32]),
        .i_ch_src(w[628 +: 2]), .i_ch_seq(w[630 +: 8]), .i_ch_lead(w[638 +: 16]), .i_ch_mul(w[654 +: 16]),
        .x_seq(8'd0), .x_dseq(8'hFF), .x_cnt(16'd0),
        .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we),
        .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .fault(su_fault), .order_fault(order_fault), .emitted(emitted),
        .retire_o(retire_o), .dbg_emit(dbg_emit), .dbg_eseq(dbg_eseq), .dbg_ret(dbg_ret), .dbg_rseq(dbg_rseq),
        .dbg_res(dbg_res), .dbg_sseq(dbg_sseq));
    // the VM model's synchronous ports: reads registered (the word the next cycle), then this edge's writes
    integer l, s;
    reg fseen = 1'b0;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) vi_q[32*l +: 32] <= e2e_vm_rd(int'(vi_addr[l*AW +: 18]));
            for (s = 0; s < 4; s = s + 1)
                if (rd_re[4*l + s]) rd_q[(4*l + s)*32 +: 32] <= e2e_vm_rd(int'(rd_addr[(4*l + s)*AW +: 18]));
        end
        if (rst_n) begin
            for (l = 0; l < N; l = l + 1)
                if (vm_we[l]) e2e_vm_wr(UNIT, int'(vm_waddr[l*AW +: 18]), int'(vm_wdata[32*l +: 32]));
            for (l = 0; l < NR; l = l + 1)
                if (res_we[l]) e2e_vm_wr(UNIT, int'(res_addr[l*AW +: 18]), int'(res_data[32*l +: 32]));
            if (kv_we != 0) $display("E2E SU%0d wrote the KV port (no KV SRAM on the HBM die)", UNIT);
`ifdef E2E_SU_DEBUG
            if (su_fault && !fseen) begin
                fseen <= 1'b1;
                $display("E2E SU%0d FAULT lanes %h side %0d red %0d cfg %0d (promote %0d) red.fsq %0d fch %0d tf %0d sf %0d top_bad %0d tap_multi %0d res_multi %0d",
                         UNIT, u_vec.l_fault, u_vec.side_f, u_vec.red_f, u_vec.p_bad, u_vec.promote,
                         |u_vec.u_red.fsq, |u_vec.u_red.fch, |u_vec.u_red.tf, |u_vec.u_red.sf, u_vec.u_red.top_bad,
                         u_vec.u_red.tap_multi, u_vec.u_red.res_multi);
            end
`endif
        end
    end
endmodule

// hgi_e2e_coll_slot: COLL (unit 6) = the die's collective block body ot_hgi_coll_ep (record binding ot_hgi_coll_record,
// GX11 decoder, PSG TU endpoint incl. the gather bypass) on the die record bus, plus three labelled MODELS:
//   * SU-quarter inject: flit i of the rank's contribution = VM words [A + 16 i, A + 16 i + 16) on quarter i mod 4
//     (hfd_su's collective inject path is not in the harness);
//   * SU deliver: a reduced result flit gi (BF16-packed when the endpoint's BF16 = 1) lands at O + 32 gi (as FP32 words
//     carrying the BF16 value) or O + 16 gi (BF16 = 0); a gathered flit gi = q pf + m from rank q lands element
//     e = 16 m + j at O + e iff e is in rank q's even-split slice [floor(q n / G), floor((q + 1) n / G)) (spec 6.7
//     ALL_GATHER; the SU's selection rule is not specified in RTL);
//   * the switch tier + the other ranks (the established single-rank method of tb_hbm_accel_tu_endpoint /
//     tb_hgi_coll_bypass): every departure of this die releases the symmetric peer flits LATC cycles later -- peers'
//     partials carry their exported A contributions (real operands: this die's owned slice is reduced by the RTL tree
//     from them), other owners' results carry the GOLDEN result (placement), gathered flits carry the peers' A.
//     Credits return CRED cycles after use; one flit per port per cycle.
module hgi_e2e_coll_slot #(
    parameter integer LATC = 453,      // 377.6 ns PHY + switch + cable budget (uarch_model TU) at 1.2 GHz
    parameter integer CRED = 137,      // 113.8 ns reverse-link credit latency
    parameter integer COLL_BF16 = 1    // the endpoint's result packing (die: 1)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [967:0]  rec,
    input  wire [39:0]   cfg,
    output wire [2:0]    ret,
    input  wire          k_v,            // the record index of this dispatch (with rec[0])
    input  wire [31:0]   k_in,
    input  wire [7:0]    group_size      // the model descriptor's coll_group_size (for the stub only)
);
    import "DPI-C" function int e2e_vm_rd(input int a);
    import "DPI-C" function void e2e_vm_wr(input int unit, input int a, input int v);
    import "DPI-C" function int e2e_coll_load(input int k, input int g);
    import "DPI-C" function void e2e_coll_part(input int q, input int f, output bit [511:0] out);
    import "DPI-C" function void e2e_coll_res(input int obase, input int gi, input int bf16, output bit [511:0] out);
    localparam integer LANES = 16, FW = 512, PWT = FW + 33, NPT = 8, INJ = 2, DEL = 4;
    wire [INJ*16-1:0] ii; wire [INJ-1:0] ir; reg [4*INJ*FW-1:0] injq;
    wire [NPT-1:0] txv, rxc; wire [NPT*PWT-1:0] txf; reg [NPT-1:0] crr, rxv; reg [NPT*PWT-1:0] rxf;
    wire [DEL-1:0] dv; wire [DEL*PWT-1:0] dfl; wire flt; wire [31:0] cst; wire [93:0] rfo; wire [79:0] vma;
    ot_hgi_coll_ep u_ce (.clk(clk), .rst_n(rst_n), .pclk(clk), .prst_n(rst_n), .rank(8'd0), .pf(16'd0), .go(1'b0),
        .inj_idx(ii), .inj_rd(ir), .inj_q(injq), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
        .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dv), .del_flit(dfl), .fault(flt), .stat_credit_stall(cst),
        .hgi_rec(rec), .hgi_ret(ret), .hgi_cfg(cfg), .hgi_rowfmt_o(rfo), .hgi_rowfmt_i(3'b000), .hgi_vmaddr(vma));
    generate if (COLL_BF16 == 0) begin : g_fp32 defparam u_ce.u_ep.BF16 = 0; end endgenerate   // what-if: FP32 results
    // ---- record context (what the endpoint was told)
    integer k = -1, n_a = 0, gsize = 4, pf = 1, rnk = 0, nsub = 4, isbyp = 0, mall = 0;
    integer abase, obase;
    always @(posedge clk) if (k_v) begin
        k = int'(k_in); gsize = int'(group_size);
        n_a = e2e_coll_load(k, gsize);
    end
    always @* begin
        abase = int'(vma[39:0]); obase = int'(vma[79:40]);
        pf = int'(u_ce.r_pf); rnk = int'(u_ce.r_rank); isbyp = int'(u_ce.r_byp); mall = int'(u_ce.r_mall);
        nsub = 1 << int'(u_ce.r_gsz);
    end
    // ---- SU-quarter inject model
    always @* begin
        injq = 0;
        for (integer i = 0; i < INJ; i = i + 1) if (ir[i]) begin
            integer f; f = int'(ii[16*i +: 16]);
            for (integer j = 0; j < 16; j = j + 1)
                injq[(f % 4) * INJ * FW + i * FW + 32 * j +: 32] = e2e_vm_rd(abase + 16 * f + j);
        end
    end
    // ---- switch tier + peers
    localparam integer QD = 8192;
    reg [PWT-1:0] eqf [0:NPT*QD-1]; longint eqt [0:NPT*QD-1]; integer eh [0:NPT-1]; integer et [0:NPT-1];
    longint cin [0:NPT*QD-1]; integer ch [0:NPT-1]; integer ct [0:NPT-1];
    longint ceg [0:NPT*QD-1]; integer gh [0:NPT-1]; integer gt [0:NPT-1]; integer eg_cred [0:NPT-1];
    longint cyc = 0;
    initial for (integer p = 0; p < NPT; p = p + 1) begin eg_cred[p] = 256; eh[p] = 0; et[p] = 0; ch[p] = 0; ct[p] = 0; gh[p] = 0; gt[p] = 0; end
    task automatic sched(input integer p, input longint t, input [PWT-1:0] f);
        begin
            if (et[p] - eh[p] >= QD) $fatal(1, "E2E COLL stub queue overflow");
            eqf[p*QD + et[p] % QD] = f; eqt[p*QD + et[p] % QD] = t; et[p] = et[p] + 1;
        end
    endtask
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
                reg [PWT-1:0] f; reg [511:0] d; integer kind, dst, idx, OG, J, OF, ROF, sl, jp, m, base, nown, o0;
                f = txf[p*PWT +: PWT]; kind = int'(f[PWT-1]); dst = int'(f[FW+24 +: 8]); idx = int'(f[FW +: 16]);
                cin[p*QD + ct[p] % QD] = cyc + CRED; ct[p] = ct[p] + 1;
                OG = rnk / nsub; J = rnk % nsub; OF = pf / nsub; ROF = COLL_BF16 ? OF / 2 : OF;
                if (isbyp != 0) begin                       // gathered flit m: every peer's flit m
                    base = (mall != 0) ? 0 : (rnk / gsize) * gsize;
                    m = idx - (rnk - base) * pf;
                    for (integer q = base; q < base + gsize; q = q + 1) if (q != rnk) begin
                        e2e_coll_part(q, m, d);
                        sched((q + m) % NPT, cyc + LATC + (q % 5), {1'b1, 8'hFF, 8'(q), 16'((q - base) * pf + m), d});
                    end
                end else if (kind == 0) begin               // partial to owner dst: peer 2J - s sends us its slice-J flit
                    sl = dst - OG * nsub; jp = ((2 * J - sl) % nsub + nsub) % nsub;
                    e2e_coll_part(OG * nsub + jp, J * OF + idx, d);
                    sched(p, cyc + LATC, {1'b0, 8'(rnk), 8'(OG * nsub + jp), 16'(idx), d});
                end else begin                               // our result m: every other owner's result m
                    m = idx - (OG * nsub + J) * ROF;
                    nown = (mall != 0) ? gsize : nsub; o0 = (mall != 0) ? 0 : OG * nsub;
                    for (integer o = o0; o < o0 + nown; o = o + 1) if (o != rnk) begin
                        e2e_coll_res(obase, o * ROF + m, COLL_BF16, d);
                        sched((o + m) % NPT, cyc + LATC, {1'b1, 8'hFF, 8'(o / nsub), 16'(o * ROF + m), d});
                    end
                end
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
            // ---- SU deliver model
            for (integer l = 0; l < DEL; l = l + 1) if (dv[l]) begin : del
                reg [PWT-1:0] f; integer gi, q, m, e, lo, hi;
                f = dfl[l*PWT +: PWT]; gi = int'(f[FW +: 16]);
                if (isbyp != 0) begin
                    q = gi / pf; m = gi % pf;
                    lo = (q * n_a) / gsize; hi = ((q + 1) * n_a) / gsize;
                    for (integer j = 0; j < 16; j = j + 1) begin
                        e = 16 * m + j;
                        if (e >= lo && e < hi) e2e_vm_wr(6, obase + e, int'(f[32*j +: 32]));
                    end
                end else if (COLL_BF16 != 0) begin
                    for (integer j = 0; j < 32; j = j + 1) e2e_vm_wr(6, obase + 32 * gi + j, int'({f[16*j +: 16], 16'h0}));
                end else begin
                    for (integer j = 0; j < 16; j = j + 1) e2e_vm_wr(6, obase + 16 * gi + j, int'(f[32*j +: 32]));
                end
            end
        end else begin
            rxv <= 0; crr <= 0;
        end
    end
endmodule
