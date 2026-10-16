`timescale 1ns/1ps
// hgi-e2e (2026-10-09): unit slots of the die-level harness that need more than a wire-up.
//
// hgi_e2e_su_slot: SU.VOP (unit 2) or SFU.GLU (unit 3, GLU = 1) on the D1 die body ot_hgi_su_unit (hgi-adapters:
// record adapter -> stage the op's VM operands into the unit's local operand memory through ONE VM packet client ->
// the unchanged ot_hdc_v41x_vec -> dirty-masked drain back to VM -> retire).  VM = the harness VM model's packet port.
`ifdef E2E_VEC
module hgi_e2e_su_slot #(
    parameter integer UNIT = 2,
    parameter integer GLU = 0,
    parameter integer N = 16,
    parameter integer M = 8,
    parameter integer LV = 6,
    parameter integer LWB = 18,
    parameter integer VLAT = 6,
    parameter integer WIDE = 0
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
    wire [337:0] vq; wire [273:0] vr;
    wire [32*16-1:0] wrq; wire [31:0] wrq_cr, wwq_cr, wwq_done; wire [32*257-1:0] wrr; wire [32*280-1:0] wwq;
    if (WIDE) begin : g_lanes
        hgi_e2e_vmlanes #(.UNIT(UNIT)) u_ln (.clk(clk), .rst_n(rst_n), .rq(wrq), .rq_cr(wrq_cr), .rr(wrr), .wq(wwq),
            .wq_cr(wwq_cr), .wq_done(wwq_done));
    end else begin : g_nolanes
        assign wrq_cr = '0; assign wrr = '0; assign wwq_cr = '0; assign wwq_done = '0;
    end
    ot_hgi_su_unit #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .WIDE(WIDE)) u_su (.clk(clk), .rst_n(rst_n), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_desc[0 +: 256]), .rec_b(rec_desc[256 +: 256]),
        .rec_c(rec_desc[512 +: 256]), .rec_d(rec_desc[768 +: 256]), .rec_o(rec_desc[1024 +: 256]),
        .rec_r(rec_desc[1280 +: 256]), .rec_i(rec_desc[1536 +: 256]), .rec_n_a(rec_n_a), .rec_done(rec_done),
        .rec_fault(rec_fault), .halted(), .vmq(vq), .vmr(vr), .s0_v(1'b0), .s0_idx(20'd0), .s0_data(32'd0),
        .am_stream(), .am_rdy(1'b1), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done),
        .rg_req(), .rg_gnt(1'b1), .wg_req(), .wg_gnt(1'b1));
    hgi_e2e_vmc #(.UNIT(UNIT), .LAT(VLAT)) u_vm (.clk(clk), .rst_n(rst_n), .q(vq), .r(vr));
endmodule
`endif

// hgi_e2e_coll_slot: COLL (unit 6) = the die's collective block body ot_hgi_coll_ep (record binding ot_hgi_coll_record,
// GX11 decoder, PSG TU endpoint incl. the gather bypass) on the die record bus, plus three labelled MODELS:
//   * SU-quarter inject: flit i of the rank's contribution = VM words [A + 16 i, A + 16 i + 16) on quarter i mod 4
//     (hfd_su's collective inject path is not in the harness);
//   * SU deliver: a reduced result flit gi (BF16-packed when the endpoint's BF16 = 1) lands at O + 32 gi (as FP32 words
//     carrying the BF16 value) or O + 16 gi (BF16 = 0); a gathered flit gi = q pf + m from rank q lands element
//     e = 16 m + j at O + e iff e is in rank q's even-split slice [floor(q n / G), floor((q + 1) n / G)) (spec 6.7
//     ALL_GATHER; the SU's selection rule is not specified in RTL);
//     ARGMAX_MERGE: the endpoint's fold (ot_hgi_coll_amerge) emits ONE flit, the merged token in word 0 -> O word 0;
//   * the switch tier + the other ranks (the established single-rank method of tb_hbm_accel_tu_endpoint /
//     tb_hgi_coll_bypass): every departure of this die releases the symmetric peer flits LATC cycles later -- peers'
//     partials carry their exported A contributions (real operands: this die's owned slice is reduced by the RTL tree
//     from them), other owners' results carry the GOLDEN result (placement), gathered flits carry the peers' A.
//     Credits return CRED cycles after use; one flit per port per cycle.
`ifdef E2E_COLL
module hgi_e2e_coll_slot #(
    parameter integer LATC = 453,      // 377.6 ns PHY + switch + cable budget (uarch_model TU) at 1.2 GHz
    parameter integer CRED = 137,      // 113.8 ns reverse-link credit latency
    parameter integer COLL_BF16 = 1,   // the endpoint's result packing (die: 1)
    parameter integer COLL_PFMAX = 64  // the endpoint's flit capacity per contributor (die: the PSG default 64)
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
    import "DPI-C" function void e2e_coll_part_w(input int q, input int w0, output bit [511:0] out);
    import "DPI-C" function void e2e_coll_res(input int obase, input int gi, input int bf16, output bit [511:0] out);
    localparam integer LANES = 16, FW = 512, PWT = FW + 33, NPT = 8, INJ = 2, DEL = 4;
    wire [INJ*16-1:0] ii; wire [INJ-1:0] ir; reg [4*INJ*FW-1:0] injq;
    wire [NPT-1:0] txv, rxc; wire [NPT*PWT-1:0] txf; reg [NPT-1:0] crr, rxv; reg [NPT*PWT-1:0] rxf;
    wire [DEL-1:0] dv; wire [DEL*PWT-1:0] dfl; wire flt; wire [31:0] cst; wire [93:0] rfo; wire [79:0] vma;
    ot_hgi_coll_ep u_ce (.clk(clk), .rst_n(rst_n), .pclk(clk), .prst_n(rst_n), .rank(8'd0), .pf(16'd0), .go(1'b0),
        .inj_idx(ii), .inj_rd(ir), .inj_q(injq), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
        .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dv), .del_flit(dfl), .fault(flt), .stat_credit_stall(cst),
        .hgi_rec(rec), .hgi_ret(ret), .hgi_cfg(cfg), .hgi_rowfmt_o(rfo), .hgi_rowfmt_i(3'b000), .hgi_vmaddr(vma));
    // what-ifs (COLL_BF16 = 0 / COLL_PFMAX != 64): tools/hgi_e2e/run.py compiles a copy of ot_hgi_coll_ep whose PSG
    // instance carries those parameters in place of the die's (Verilator applies a defparam even in a dead generate
    // branch, so the copy is the reliable form); these parameters only tell the models what the endpoint was built with
    // hgi-takeover F2 / F4: the die endpoint packs results per collective (BF16RT = 1: O.fmt from the record, r_bf16)
    // and carries PFMAX 512; a static what-if copy (BF16RT 0) still pins BF16 = COLL_BF16
    initial if ((u_ce.u_ep.BF16RT == 0 && u_ce.u_ep.BF16 != COLL_BF16) || u_ce.u_ep.PFMAX != COLL_PFMAX)
        $fatal(1, "E2E COLL: endpoint BF16 %0d (RT %0d) PFMAX %0d, models expect %0d / %0d", u_ce.u_ep.BF16, u_ce.u_ep.BF16RT,
               u_ce.u_ep.PFMAX, COLL_BF16, COLL_PFMAX);
    integer rbf;
    always @* rbf = (u_ce.u_ep.BF16RT != 0) ? int'(u_ce.r_bf16) : COLL_BF16;
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
    longint cyc = 0; integer cfseen = 0;
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
                OG = rnk / nsub; J = rnk % nsub; OF = pf / nsub; ROF = rbf ? OF / 2 : OF;
                if (isbyp != 0) begin                       // gathered flit m: every peer's flit m
                    base = (mall != 0) ? 0 : (rnk / gsize) * gsize;
                    m = idx - (rnk - base) * pf;
                    for (integer q = base; q < base + gsize; q = q + 1) if (q != rnk) begin
                        // F3: a sliced gather carries peer q's slice words s_q + 16 m .. (s_q = floor((q - base) n / G))
                        if (u_ce.g_slice) e2e_coll_part_w(q, (((q - base) * n_a) / gsize) + 16 * m, d);
                        else e2e_coll_part(q, m, d);
                        sched((q + m) % NPT, cyc + LATC + (q % 5), {1'b1, 8'hFF, 8'(q), 16'((q - base) * pf + m), d});
                    end
                end else if (kind == 0) begin               // partial to owner dst: peer 2J - s sends us its slice-J flit
                    sl = dst - OG * nsub; jp = ((2 * J - sl) % nsub + nsub) % nsub;
                    e2e_coll_part(OG * nsub + jp, J * OF + idx, d);
                    sched(p, cyc + LATC, {1'b0, 8'(rnk), 8'(OG * nsub + jp), 16'(idx), d});
                end else begin                               // our result m: every other owner's result m
                    m = idx - (OG * nsub + J) * ROF;
`ifdef E2E_COLL_DEBUG
                    $display("E2E COLL DBG cyc %0d result dep port %0d idx %0d m %0d src %0d dst %0d", cyc, p, idx, m, int'(f[FW+16 +: 8]), dst);
`endif
                    nown = (mall != 0) ? gsize : nsub; o0 = (mall != 0) ? 0 : OG * nsub;
                    for (integer o = o0; o < o0 + nown; o = o + 1) if (o != rnk) begin
                        e2e_coll_res(obase, o * ROF + m, rbf, d);
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
            if (ret[2] && !cfseen) begin
                cfseen = 1;
                $display("E2E COLL FAULT k %0d: dec_err %0d pf_bad %0d pfg_bad %0d ep_fault %0d multi %0d gsz %0d pf %0d byp %0d mall %0d rank %0d g %0d st %0d",
                         k, u_ce.u_rec.dc_ev, u_ce.u_rec.pf_bad, u_ce.u_rec.pfg_bad, u_ce.u_ep.fault, u_ce.multi_err,
                         u_ce.r_gsz, u_ce.r_pf, u_ce.r_byp, u_ce.r_mall, u_ce.r_rank, u_ce.cfg_w46[7:0], u_ce.u_rec.st);
                $display("E2E COLL FAULT parts: ovf %0d dupe %0d mode %0d result %0d", u_ce.u_ep.g_on.anyovf,
                         u_ce.u_ep.g_on.dupe, u_ce.u_ep.g_on.mode_error, u_ce.u_ep.g_on.result_error);
            end
            // ---- SU deliver model
            for (integer l = 0; l < DEL; l = l + 1) if (dv[l]) begin : del
                reg [PWT-1:0] f; integer gi, q, m, e, lo, hi;
                f = dfl[l*PWT +: PWT]; gi = int'(f[FW +: 16]);
`ifdef E2E_COLL_DEBUG
                $display("E2E COLL DBG cyc %0d deliver lane %0d gi %0d src %0d", cyc, l, gi, int'(f[FW+16 +: 8]));
`endif
                if (u_ce.amx_run) begin                    // ARGMAX_MERGE (hgi-1010/g3): the folded token flit -> O word 0
                    if (gi != 0) $fatal(1, "E2E COLL: ARGMAX_MERGE delivered flit gi %0d (the fold emits one flit, gi 0)", gi);
                    e2e_vm_wr(6, obase, int'(f[31:0]));
                end else if (isbyp != 0 && u_ce.g_slice) begin      // F3: {lanes, w}: words O + w .. + lanes - 1
                    for (integer j = 0; j < 16; j = j + 1)
                        if (j < int'(f[FW+24 +: 8])) e2e_vm_wr(6, obase + gi + j, int'(f[32*j +: 32]));
                end else if (isbyp != 0) begin
                    q = gi / pf; m = gi % pf;
                    lo = (q * n_a) / gsize; hi = ((q + 1) * n_a) / gsize;
                    for (integer j = 0; j < 16; j = j + 1) begin
                        e = 16 * m + j;
                        if (e >= lo && e < hi) e2e_vm_wr(6, obase + e, int'(f[32*j +: 32]));
                    end
                end else if (rbf != 0) begin
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
`endif

// hgi_e2e_fused_slot: FUSED (unit 4 front) = ot_hgi_fused_record UNIT = 1 (the D1 die body: micro-ops on an internal
// ot_hgi_su_unit through one VM packet client) + its DMA row mover (gain loads: kport lane on the HBM model, VM packet
// client + the VM wide write port) + the quant record bus out (QDQ_*).  cfg_scratch = SCRATCH (compiler-reserved,
// excluded from the checks).
`ifdef E2E_FUSED
module hgi_e2e_fused_slot #(
    parameter integer KLAT = 40, parameter integer VLAT = 6, parameter integer SCRATCH = 256064,
    parameter integer UN = 32, parameter integer UM = 8,       // the FUSED unit's stream unit (die: ot_hgi_fused_record defaults)
    parameter integer UWIDE = 0                                // 1: its D1 body is the WIDE successor (VM wide lanes)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [1791:0] rec_desc,
    input  wire [146:0]  rec_n,
    output wire          rec_done,
    output wire          rec_fault,
    output wire [682:0]  q_rec,
    input  wire          q_done,
    input  wire          q_fault,
    input  wire [17:0]   scratch           // the compiler-reserved scratch base (static; default SCRATCH)
);
    wire mv_v, mv_rdy, mv_done, mv_fault; wire [226:0] mv; wire [337:0] fq, mq; wire [273:0] fr, mr;
    wire [32*16-1:0] wrq; wire [31:0] wrq_cr, wwq_cr, wwq_done; wire [32*257-1:0] wrr; wire [32*280-1:0] wwq;
    if (UWIDE) begin : g_lanes
        hgi_e2e_vmlanes #(.UNIT(4)) u_ln (.clk(clk), .rst_n(rst_n), .rq(wrq), .rq_cr(wrq_cr), .rr(wrr), .wq(wwq),
            .wq_cr(wwq_cr), .wq_done(wwq_done));
    end else begin : g_nolanes
        assign wrq_cr = '0; assign wrr = '0; assign wwq_cr = '0; assign wwq_done = '0;
    end
    ot_hgi_fused_record #(.UNIT(1), .UN(UN), .UM(UM), .UWIDE(UWIDE)) u_f (.clk(clk), .rst_n(rst_n), .cfg_scratch(scratch), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(rec_hdr), .rec_a(rec_desc[0 +: 256]), .rec_b(rec_desc[256 +: 256]), .rec_c(rec_desc[512 +: 256]),
        .rec_o(rec_desc[1024 +: 256]), .rec_n_a(rec_n[0 +: 21]), .rec_n_b(rec_n[21 +: 21]), .rec_n_o(rec_n[84 +: 21]),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(),
        .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault),
        .op_v(), .op_rdy(1'b0), .op_w(), .su_idle(1'b1), .su_fault(1'b0), .vmq(fq), .vmr(fr),
        .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .rg_req(), .rg_gnt(1'b1),
        .wg_req(), .wg_gnt(1'b1),
        .ne_v(), .ne_rdy(1'b0), .ne_job(), .ne_done(1'b0), .ne_fault(1'b0), .q_rec(q_rec), .q_done(q_done), .q_fault(q_fault));
    wire k_req_v, k_req_we, k_rsp_rdy, k_rsp_v, k_rsp_we, k_req_rdy; wire [36:0] k_addr; wire [255:0] k_wd, k_rd;
    wire [31:0] k_ws; wire [15:0] k_tag; wire [279:0] wl; wire wl_done;
    // hgi-1010/c: the mover's four HBM lanes (bursts / full-sector writes) on hgi_e2e_rlanes (the DPI HBM)
    wire [3:0] r_req_v, r_req_rdy, r_rsp_v, r_rsp_rdy, r_rsp_last; wire [4*37-1:0] r_req_addr; wire [15:0] r_req_len;
    wire [63:0] r_req_tag, r_rsp_tag; wire [1023:0] r_rsp_data, r_req_wdata; wire [3:0] r_req_we, r_rsp_we; wire [127:0] r_req_wstrb;
    hgi_e2e_rlanes #(.LAT(KLAT)) u_rl (.clk(clk), .rst_n(rst_n), .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr),
        .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag),
        .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data));
    ot_hgi_dma_mover u_mv (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .fence_v(1'b0), .fence_rdy(), .fence_done(),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd),
        .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rd), .k_fault(1'b0), .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb),
        .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .vr2q(), .vr2r(8257'd0),
        .vmq(mq), .vmr(mr), .wl(wl), .wl_done(wl_done));
    hgi_e2e_kport #(.LAT(KLAT)) u_kp (.clk(clk), .rst_n(rst_n), .req_v(k_req_v), .req_rdy(k_req_rdy), .req_we(k_req_we),
        .req_addr(k_addr), .req_wd(k_wd), .req_ws(k_ws), .rsp_v(k_rsp_v), .rsp_we(k_rsp_we), .rsp_d(k_rd));
    hgi_e2e_vmc #(.UNIT(4), .LAT(VLAT)) u_vf (.clk(clk), .rst_n(rst_n), .q(fq), .r(fr));
    hgi_e2e_vmc #(.UNIT(4), .LAT(VLAT)) u_vm (.clk(clk), .rst_n(rst_n), .q(mq), .r(mr));
    hgi_e2e_vmw #(.UNIT(4), .NW(1)) u_vmw (.clk(clk), .rst_n(rst_n), .wl(wl), .done(wl_done));
`ifdef E2E_FUSED_DEBUG
    // fault-source report (debug builds): the adapter state, its internal SU unit's state, the vec's refusal flags
    reg seen = 1'b0; longint c = 0;
    always @(posedge clk) begin
        c <= c + 1;
        if (u_f.s_v && u_f.s_rdy) $display("E2E FUSED DBG cyc %0d sub-op: sut %h a %h n %0d o %h", c, u_f.s_sut[141:0], u_f.s_a[87:0], u_f.s_n, u_f.s_o[87:0]);
        if (rst_n && (u_f.s_fault || rec_fault) && !seen) begin
            seen <= 1'b1;
            $display("E2E FUSED FAULT cyc %0d: adapter st %0d s_fault %0d su_unit st %0d su_rec fault %0d vec fault %0d p_bad %0d lw_lim %0d",
                     c, u_f.st, u_f.s_fault, u_f.g_unit.u_su.st, u_f.g_unit.u_su.u_rec.rec_fault, u_f.g_unit.u_su.vfault,
                     u_f.g_unit.u_su.u_vec.p_bad, u_f.g_unit.u_su.SBASE);
        end
    end
`endif
endmodule
`endif

// hgi-1010/g: the ATT unit's HBM read lane on the HBM model: a sector request {sector address, tag} a cycle (always
// ready), answered IN ORDER LAT cycles later with {tag, 256 b} (the memory is read at acceptance).
module hgi_e2e_att_hbm #(parameter integer LAT = 40) (
    input wire clk, input wire rst_n, input wire req_v, output wire req_rdy, input wire [34:0] req_sec,
    input wire [7:0] req_tag, output reg rsp_v, output reg [7:0] rsp_tag, output reg [255:0] rsp_d);
    import "DPI-C" function void e2e_hbm_sector(input longint addr, input bit we, input bit [255:0] wd,
                                                input bit [31:0] strb, output bit [255:0] rd);
    reg [263:0] qd [0:1023]; longint qt [0:1023]; integer qh = 0, qn = 0; longint tn = 0;
    assign req_rdy = rst_n && qn < 1000;
    always @(posedge clk) begin
        tn <= tn + 1;
        rsp_v <= 1'b0;
        if (qn > 0 && qt[qh % 1024] <= tn) begin rsp_v <= 1'b1; {rsp_tag, rsp_d} <= qd[qh % 1024]; qh = qh + 1; qn = qn - 1; end
        if (rst_n && req_v && req_rdy) begin : acc
            bit [255:0] rd;
            e2e_hbm_sector({24'd0, req_sec, 5'd0}, 1'b0, 256'd0, 32'd0, rd);
            qd[(qh + qn) % 1024] = {req_tag, rd}; qt[(qh + qn) % 1024] = tn + LAT - 1; qn = qn + 1;
        end
    end
endmodule

// hgi-1010/g: the HC unit's HBM lane on the HC weight-set map (hcw.bin): a burst request {sector, len 1..4, tag} a
// cycle (always ready), its beats returned IN ORDER from LAT cycles after the request, one beat a cycle.
module hgi_e2e_hc_hbm #(parameter integer LAT = 40, parameter integer TG = 11) (
    input wire clk, input wire rst_n, input wire req_v, output wire req_rdy, input wire [34:0] req_sec,
    input wire [2:0] req_len, input wire [TG-1:0] req_tag, output reg rsp_v, output reg [TG-1:0] rsp_tag,
    output reg [1:0] rsp_beat, output reg [255:0] rsp_d);
    import "DPI-C" function void e2e_hcw_sector(input longint sec, output bit [255:0] rd);
    reg [34:0] qa [0:1023]; reg [2:0] ql [0:1023]; reg [TG-1:0] qg [0:1023]; longint qt [0:1023];
    integer qh = 0, qn = 0, bi = 0; longint tn = 0;
    assign req_rdy = rst_n && qn < 1000;
    always @(posedge clk) begin : srv
        bit [255:0] rd;
        tn <= tn + 1;
        rsp_v <= 1'b0;
        if (qn > 0 && qt[qh % 1024] <= tn) begin
            e2e_hcw_sector({29'd0, qa[qh % 1024]} + bi, rd);
            rsp_v <= 1'b1; rsp_tag <= qg[qh % 1024]; rsp_beat <= bi[1:0]; rsp_d <= rd;
            bi = bi + 1;
            if (bi == ql[qh % 1024]) begin bi = 0; qh = qh + 1; qn = qn - 1; end
        end
        if (rst_n && req_v && req_rdy) begin
            qa[(qh + qn) % 1024] = req_sec; ql[(qh + qn) % 1024] = req_len; qg[(qh + qn) % 1024] = req_tag;
            qt[(qh + qn) % 1024] = tn + LAT - 1; qn = qn + 1;
        end
    end
endmodule
