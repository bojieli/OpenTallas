// HBM SU c12 (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/test/tb_hdc_v41x_vec.sv for the c12 unit
// (rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv): the same bench, forwarding the c12 parameters (tools/hbm_su_c12.py -G...).
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Performance and bit-exactness bench of the V4.1 vector stream unit
// (rtl/hdc/v41x/ot_hdc_v41x_vec.sv), driven by tools/rtl_hdc_v41x_vec_campaign.py.
//
// Memories, loaded with $readmemh from the files named by plusargs:
//   +VM=  vector memory, 32-bit words      +KV=  KV SRAM, 32-bit words
//   +CR=  constant ROM, 64-bit {hi, lo}     +WR=  BF16 weight ROM, 16-bit elements
//   +XB=  the external producer's data      +PROG= the program (one word per op,
//         field offsets in tb_hdc_v41x_vec_fields.svh, written by the tool)
// Every port has a one-cycle read: an address in cycle t is answered in t+1.  An operand
// read names its source (rd_src); the bench's memory returns that source's word.
// Writes land at the end of their cycle.
//
// Issue: op k goes when the unit is ready and op k's bench conditions hold:
// w_idle (the unit is idle), w_rseq (cr_rseq has reached a seq), w_dseq
// (cr_dseq has).
//
// External producer (the chaining bench), started by the op carrying
// x_start: every XPER cycles it writes one vector of XVEC words of XB to
// vm[XBASE + ...] and advances x_cnt (x_seq = XSEQ, x_dseq = XSEQ at the end).
//
// Trace (stdout): "A <cyc> <k>" accept of op k; "C <cyc> e<seq> r<seq> s<seq>"
// in a cycle with an emit, a retire or a result event of an op; "F <cyc> fault" /
// "O <cyc> order"; "X <cyc> <n>" the producer wrote vector n.  At the end the memories are
// written to +VMO= and +KVO=, then "END <cyc>".
// ---------------------------------------------------------------------------
module tb_hdc_v41x_vec #(
    parameter integer N = 64,
    parameter integer M = 16,
    parameter integer LV = 6,
    parameter integer VMA = 16,
    parameter integer KVA = 15,
    parameter integer CRA = 12,
    parameter integer WRA = 16,
    parameter integer XBA = 14,
    parameter integer PMAX = 4096,
    parameter integer XVMAX = 4 * N,        // the external producer's vector, at most
    parameter integer TMAX = 2000000,
    parameter integer BCAST_STAGES = 0,
    parameter integer RET_STAGES = 0,
    parameter integer MLAT = 3,
    parameter integer ALAT = 3,
    // c12 (rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv): forwarded to the unit
    parameter integer OPR = 0,
    parameter integer DDIV = 19,
    parameter integer SIDEX = 0,
    parameter integer FSQ = 0,
    parameter integer RPAD = 0,
    parameter integer CAPR = 0,
    parameter integer RSL = 0,
    parameter integer RTAP = 0,
    parameter integer ROUT = 0,
    parameter integer CTL13 = 0,
    parameter integer CTL12 = 0,
    parameter integer RSLICE = 64
) (input wire clk);
    `include "tb_hdc_v41x_vec_fields.svh"
    localparam integer AW = 24, NR = N / 8;
    reg [31:0] vm [0:(1<<VMA)-1];
    reg [31:0] kv [0:(1<<KVA)-1];
    reg [63:0] cr [0:(1<<CRA)-1];
    reg [15:0] wr [0:(1<<WRA)-1];
    reg [31:0] xb [0:(1<<XBA)-1];
    reg [PW-1:0] prog [0:PMAX-1];
    reg [8*512-1:0] fvm, fkv, fcr, fwr, fxb, fpg, fvmo, fkvo;
    integer nprog, xvec, xnv, xper, xbase, xseq;
    reg rst_n = 1'b0;
    integer cyc = 0;
    initial begin
        if (!$value$plusargs("VM=%s", fvm)) $finish;
        $value$plusargs("KV=%s", fkv); $value$plusargs("CR=%s", fcr); $value$plusargs("WR=%s", fwr);
        $value$plusargs("XB=%s", fxb); $value$plusargs("PROG=%s", fpg);
        $value$plusargs("VMO=%s", fvmo); $value$plusargs("KVO=%s", fkvo);
        if (!$value$plusargs("NPROG=%d", nprog)) nprog = 0;
        if (!$value$plusargs("XVEC=%d", xvec)) xvec = 0;
        if (!$value$plusargs("XNV=%d", xnv)) xnv = 0;
        if (!$value$plusargs("XPER=%d", xper)) xper = 1;
        if (!$value$plusargs("XBASE=%d", xbase)) xbase = 0;
        if (!$value$plusargs("XSEQ=%d", xseq)) xseq = 0;
        $readmemh(fvm, vm); $readmemh(fkv, kv); $readmemh(fcr, cr); $readmemh(fwr, wr); $readmemh(fpg, prog);
        if (xvec > 0) $readmemh(fxb, xb);
    end

    // ---- program issue -------------------------------------------------------------------------------
    integer pc = 0;
    wire [PW-1:0] w = prog[pc];
    wire ready, idle, fault, order_fault, retire_o;
    wire [7:0] cr_seq, cr_dseq, cr_rseq;
    wire [15:0] cr_cnt, emitted;
    wire [7:0] dr = cr_rseq - w[F_W_RSEQ +: 8];
    wire [7:0] dd = cr_dseq - w[F_W_DSEQ +: 8];
    wire cond = (!w[F_W_IDLE] || idle) && (!w[F_W_RSEQ_EN] || !dr[7]) && (!w[F_W_DSEQ_EN] || !dd[7]);
    wire go = rst_n && (pc < nprog) && cond;
    // external producer
    reg        xrun = 1'b0;
    integer    xn = 0, xt = 0;
    reg [15:0] x_cnt = 0;
    reg [7:0]  x_seq, x_dseq;
    integer e;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        if (go && ready) begin
            $display("A %0d %0d", cyc, pc);
            if (w[F_X_START]) begin xrun <= 1'b1; xt <= 0; end
            pc <= pc + 1;
        end
        if (xrun) begin
            if (xt == xper - 1) begin
                $display("X %0d %0d", cyc, xn);
                xn <= xn + 1; x_cnt <= xn + 1; xt <= 0;
                if (xn + 1 == xnv) xrun <= 1'b0;
            end else xt <= xt + 1;
        end
    end
    always @(*) begin
        x_seq = xseq[7:0];
        x_dseq = (xnv > 0 && x_cnt == xnv) ? xseq[7:0] : xseq[7:0] - 8'd1;
    end

    // ---- the unit -------------------------------------------------------------------------------------
    wire [N-1:0]      vi_re, vm_we, kv_we;
    wire [N*AW-1:0]   vi_addr, vm_waddr, kv_waddr;
    reg  [N*32-1:0]   vi_q;
    wire [4*N*AW-1:0] rd_addr;
    wire [4*N-1:0]    rd_re;
    wire [8*N-1:0]    rd_src;
    reg  [4*N*32-1:0] rd_q;
    wire [N*32-1:0]   vm_wdata, kv_wdata;
    wire [NR-1:0]     res_we;
    wire [NR*AW-1:0]  res_addr;
    wire [NR*32-1:0]  res_data;
    wire dbg_emit, dbg_ret, dbg_res;
    wire [7:0] dbg_eseq, dbg_rseq, dbg_sseq;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(BCAST_STAGES), .RET_STAGES(RET_STAGES), .MLAT(MLAT), .ALAT(ALAT),
                      .OPR(OPR), .DDIV(DDIV), .SIDEX(SIDEX), .FSQ(FSQ), .CAPR(CAPR), .RPAD(RPAD), .RSL(RSL), .RTAP(RTAP), .ROUT(ROUT), .CTL12(CTL12), .CTL13(CTL13),
                      .RSLICE(RSLICE)) dut (
        .clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(w[F_NOUT +: 16]), .i_nin(w[F_NIN +: 16]),
        .i_asrc(w[F_ASRC +: 2]), .i_bsrc(w[F_BSRC +: 2]), .i_csrc(w[F_CSRC +: 2]), .i_dsrc(w[F_DSRC +: 2]),
        .i_abase(w[F_ABASE +: 24]), .i_aso(w[F_ASO +: 24]), .i_asi(w[F_ASI +: 24]), .i_aibase(w[F_AIBASE +: 24]),
        .i_aind(w[F_AIND +: 2]),
        .i_bbase(w[F_BBASE +: 24]), .i_bso(w[F_BSO +: 24]), .i_bsi(w[F_BSI +: 24]), .i_bhalf(w[F_BHALF]),
        .i_cbase(w[F_CBASE +: 24]), .i_cso(w[F_CSO +: 24]), .i_csi(w[F_CSI +: 24]), .i_cpair(w[F_CPAIR]),
        .i_dbase(w[F_DBASE +: 24]), .i_dso(w[F_DSO +: 24]), .i_dsi(w[F_DSI +: 24]),
        .i_arnd(w[F_ARND]), .i_arelu(w[F_ARELU]), .i_amin(w[F_AMIN]), .i_cclip(w[F_CCLIP]),
        .i_m1(w[F_M1 +: 3]), .i_m2(w[F_M2 +: 2]), .i_qm(w[F_QM +: 3]), .i_ad(w[F_AD +: 3]), .i_sfu(w[F_SFU +: 3]),
        .i_e1(w[F_E1 +: 3]), .i_e2(w[F_E2 +: 2]), .i_rnd(w[F_RND]), .i_dst(w[F_DST +: 2]),
        .i_obase(w[F_OBASE +: 24]), .i_oso(w[F_OSO +: 24]), .i_osi(w[F_OSI +: 24]), .i_orow(w[F_OROW +: 24]),
        .i_red(w[F_RED +: 2]), .i_redsq(w[F_REDSQ]), .i_redwhole(w[F_REDWHOLE]), .i_redtree(w[F_REDTREE]),
        .i_redrnd(w[F_REDRND]), .i_rbase(w[F_RBASE +: 24]), .i_rso(w[F_RSO +: 24]),
        .i_imm1(w[F_IMM1 +: 32]), .i_imm2(w[F_IMM2 +: 32]), .i_imm3(w[F_IMM3 +: 32]),
        .i_ch_src(w[F_CH_SRC +: 2]), .i_ch_seq(w[F_CH_SEQ +: 8]), .i_ch_lead(w[F_CH_LEAD +: 16]),
        .i_ch_mul(w[F_CH_MUL +: 16]),
        .x_seq(x_seq), .x_dseq(x_dseq), .x_cnt(x_cnt),
        .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
        .rd_q(rd_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(fault), .order_fault(order_fault), .emitted(emitted), .retire_o(retire_o),
        .dbg_emit(dbg_emit), .dbg_eseq(dbg_eseq), .dbg_ret(dbg_ret), .dbg_rseq(dbg_rseq),
        .dbg_res(dbg_res), .dbg_sseq(dbg_sseq));

    // ---- memories -------------------------------------------------------------------------------------
    integer l, s;
    reg [AW-1:0] ad;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) vi_q[32*l +: 32] <= vm[vi_addr[l*AW +: AW] & ((1<<VMA)-1)];
            for (s = 0; s < 4; s = s + 1) begin
                ad = rd_addr[(4*l + s)*AW +: AW];
                if (rd_re[4*l + s])
                    case (rd_src[8*l + 2*s +: 2])
                        2'd0: rd_q[(4*l + s)*32 +: 32] <= vm[ad & ((1<<VMA)-1)];
                        2'd1: rd_q[(4*l + s)*32 +: 32] <= cr[ad & ((1<<CRA)-1)][31:0];
                        2'd2: rd_q[(4*l + s)*32 +: 32] <= cr[ad & ((1<<CRA)-1)][63:32];
                        default: rd_q[(4*l + s)*32 +: 32] <= {wr[ad & ((1<<WRA)-1)], 16'h0000};
                    endcase
            end
        end
        for (l = 0; l < N; l = l + 1) begin
            if (vm_we[l]) vm[vm_waddr[l*AW +: AW] & ((1<<VMA)-1)] <= vm_wdata[32*l +: 32];
            if (kv_we[l]) kv[kv_waddr[l*AW +: AW] & ((1<<KVA)-1)] <= kv_wdata[32*l +: 32];
        end
        for (l = 0; l < NR; l = l + 1)
            if (res_we[l]) vm[res_addr[l*AW +: AW] & ((1<<VMA)-1)] <= res_data[32*l +: 32];
        if (xrun && xt == xper - 1)
            for (e = 0; e < XVMAX; e = e + 1)
                if (e < xvec) vm[(xbase + xn * xvec + e) & ((1<<VMA)-1)] <= xb[(xn * xvec + e) & ((1<<XBA)-1)];
    end

    // ---- trace and end ----------------------------------------------------------------------------------
    integer quiet = 0;
    always @(posedge clk) if (rst_n) begin
        if (dbg_emit || dbg_ret || dbg_res)
            $display("C %0d %s%0d %s%0d %s%0d", cyc, dbg_emit ? "e" : "-", dbg_eseq, dbg_ret ? "r" : "-", dbg_rseq,
                     dbg_res ? "s" : "-", dbg_sseq);
        if (fault) $display("F %0d fault", cyc);
        if (order_fault) $display("O %0d order", cyc);
        quiet <= (pc >= nprog && idle && !xrun) ? quiet + 1 : 0;
        if (quiet == 8 || cyc > TMAX) begin
            $writememh(fvmo, vm);
            $writememh(fkvo, kv);
            $display("END %0d %s", cyc, (cyc > TMAX) ? "timeout" : "ok");
            $finish;
        end
    end
endmodule
