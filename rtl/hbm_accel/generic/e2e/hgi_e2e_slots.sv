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
            if (su_fault && !fseen) begin
                fseen <= 1'b1;
                $display("E2E SU%0d FAULT lanes %h side %0d red %0d cfg %0d (promote %0d) red.fsq %0d fch %0d tf %0d sf %0d top_bad %0d tap_multi %0d res_multi %0d",
                         UNIT, u_vec.l_fault, u_vec.side_f, u_vec.red_f, u_vec.p_bad, u_vec.promote,
                         |u_vec.u_red.fsq, |u_vec.u_red.fch, |u_vec.u_red.tf, |u_vec.u_red.sf, u_vec.u_red.top_bad,
                         u_vec.u_red.tap_multi, u_vec.u_red.res_multi);
            end
        end
    end
endmodule
