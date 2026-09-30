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
    // VM_DIST = 1: the vector memory is the distributed lane-group banks (rtl/chip/ot_v41_vm_dist.sv, NG = N/8
    // groups); the reducer's results cross SU_RES_STAGES tree registers (ot_hdc_v41x_vec RES_STAGES) and the
    // external producer's writes -- the matvec result scatter -- RET_SCATTER_STAGES, its credits delayed alike.
    // 0: the flat memory (bit- and cycle-identical to the bench before VM_DIST).
    parameter integer VM_DIST = 0,
    parameter integer SU_RES_STAGES = 4,
    parameter integer RET_SCATTER_STAGES = 6,
    parameter integer BCAST_STAGES = 0,
    parameter integer RET_STAGES = 0,
    // option H of the distributed VM (VM_DIST = 1): the residual networks, held per op (ot_hdc_v41x_vec VMD_NG),
    // and the element writes into the lane's own group (SU_EWR_STAGES, in place of RET_STAGES)
    parameter integer VM_DIST_H = 0,
    parameter integer SU_EWR_STAGES = 1,
    parameter integer ROT_STAGES = 17,
    parameter integer GATH_STAGES = 18,
    parameter integer SCAL_STAGES = 8
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
    integer quiet = 0;
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
    // the producer's credits as the unit sees them: RET_SCATTER_STAGES late under VM_DIST (its writes are)
    localparam integer XD = VM_DIST ? RET_SCATTER_STAGES : 0;
    reg [15:0] x_cnt_d [0:(XD > 0 ? XD : 1)-1];
    wire [15:0] x_cnt_u = (XD > 0) ? x_cnt_d[(XD > 0 ? XD : 1)-1] : x_cnt;
    integer xk;
    always @(posedge clk) begin
        x_cnt_d[0] <= x_cnt;
        for (xk = 1; xk < XD; xk = xk + 1) x_cnt_d[xk] <= x_cnt_d[xk-1];
    end
    initial for (xk = 0; xk < (XD > 0 ? XD : 1); xk = xk + 1) x_cnt_d[xk] = 0;
    always @(*) begin
        x_seq = xseq[7:0];
        x_dseq = (xnv > 0 && x_cnt_u == xnv) ? xseq[7:0] : xseq[7:0] - 8'd1;
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
    wire [4*N*32-1:0] rd_q_u;
    wire [N*32-1:0]   vi_q_u;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(BCAST_STAGES),
                      .RET_STAGES(VM_DIST ? SU_EWR_STAGES : RET_STAGES), .RES_STAGES(VM_DIST ? SU_RES_STAGES : -1),
                      .VMD_NG((VM_DIST != 0 && VM_DIST_H != 0) ? N / 8 : 0), .ROT_STAGES(ROT_STAGES),
                      .GATH_STAGES(GATH_STAGES), .SCAL_STAGES(SCAL_STAGES)) dut (
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
        .x_seq(x_seq), .x_dseq(x_dseq), .x_cnt(x_cnt_u),
        .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q_u), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
        .rd_q(rd_q_u),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(fault), .order_fault(order_fault), .emitted(emitted), .retire_o(retire_o),
        .dbg_emit(dbg_emit), .dbg_eseq(dbg_eseq), .dbg_ret(dbg_ret), .dbg_rseq(dbg_rseq),
        .dbg_res(dbg_res), .dbg_sseq(dbg_sseq));

    // ---- memories -------------------------------------------------------------------------------------
    integer l, s;
    reg [AW-1:0] ad;
    wire xwr = xrun && xt == xper - 1;          // the producer writes vector xn this cycle
    wire xpipe_busy;
    generate if (VM_DIST == 0) begin : g_flat
    assign rd_q_u = rd_q; assign vi_q_u = vi_q; assign xpipe_busy = 1'b0;
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
    end else begin : g_dist
    // the distributed banks: reads 4*l+s (operand s of lane l, VM-sourced only), then the N gather-index reads;
    // writes: the N element writes, the N/8 reducer results, the producer's XVMAX words (the flat order)
    localparam integer NRD = 5 * N, NWR = N + NR + XVMAX;
    reg  [NRD-1:0] d_re; reg [NRD*VMA-1:0] d_ra; reg [NRD*3-1:0] d_rc; wire [NRD*32-1:0] d_q;
    reg  [NWR-1:0] d_we; reg [NWR*VMA-1:0] d_wa; reg [NWR*32-1:0] d_wd;
    wire d_fault;
    // the scatter tree: the producer's words XD cycles late
    reg  [XVMAX-1:0]     x_v  [0:XD-1];
    reg  [XVMAX*VMA-1:0] x_a  [0:XD-1];
    reg  [XVMAX*32-1:0]  x_d  [0:XD-1];
    reg  [XVMAX-1:0]     x_v0; reg [XVMAX*VMA-1:0] x_a0; reg [XVMAX*32-1:0] x_d0;
    reg  [XD-1:0]        x_live;
    integer k;
    always @(*) begin
        for (e = 0; e < XVMAX; e = e + 1) begin
            x_v0[e] = xwr && e < xvec;
            x_a0[e*VMA +: VMA] = VMA'(xbase + xn * xvec + e);
            x_d0[e*32 +: 32] = xb[(xn * xvec + e) & ((1<<XBA)-1)];
        end
    end
    always @(posedge clk) begin
        x_v[0] <= x_v0; x_a[0] <= x_a0; x_d[0] <= x_d0; x_live[0] <= |x_v0;
        for (k = 1; k < XD; k = k + 1) begin x_v[k] <= x_v[k-1]; x_a[k] <= x_a[k-1]; x_d[k] <= x_d[k-1]; x_live[k] <= x_live[k-1]; end
    end
    initial begin for (k = 0; k < XD; k = k + 1) x_v[k] = 0; x_live = 0; end
    assign xpipe_busy = |x_live;
    always @(*) begin
        d_re = 0; d_ra = 0; d_rc = 0; d_we = 0; d_wa = 0; d_wd = 0;
        for (l = 0; l < N; l = l + 1) begin
            for (s = 0; s < 4; s = s + 1) begin
                d_re[4*l + s] = rd_re[4*l + s] && rd_src[8*l + 2*s +: 2] == 2'd0;
                d_ra[(4*l + s)*VMA +: VMA] = rd_addr[(4*l + s)*AW +: VMA];
                d_rc[(4*l + s)*3 +: 3] = 3'(s);
            end
            d_re[4*N + l] = vi_re[l];
            d_ra[(4*N + l)*VMA +: VMA] = vi_addr[l*AW +: VMA];
            d_rc[(4*N + l)*3 +: 3] = 3'd4;
            d_we[l] = vm_we[l]; d_wa[l*VMA +: VMA] = vm_waddr[l*AW +: VMA]; d_wd[l*32 +: 32] = vm_wdata[32*l +: 32];
        end
        for (l = 0; l < NR; l = l + 1) begin
            d_we[N + l] = res_we[l]; d_wa[(N + l)*VMA +: VMA] = res_addr[l*AW +: VMA];
            d_wd[(N + l)*32 +: 32] = res_data[32*l +: 32];
        end
        d_we[N + NR +: XVMAX] = x_v[XD-1]; d_wa[(N + NR)*VMA +: XVMAX*VMA] = x_a[XD-1];
        d_wd[(N + NR)*32 +: XVMAX*32] = x_d[XD-1];
    end
    reg bd_load = 1'b0, bd_dump = 1'b0;
    ot_v41_vm_dist #(.NG(N / 8), .VMA(VMA), .NL(N), .NRD(NRD), .NWR(NWR)) u_vmd (
        .clk(clk), .rst_n(rst_n), .rd_re(d_re), .rd_addr(d_ra), .rd_cls(d_rc), .rd_q(d_q),
        .wr_we(d_we), .wr_addr(d_wa), .wr_data(d_wd), .bd_load(bd_load), .bd_dump(bd_dump), .fault(d_fault));
    // the other sources (constant / weight ROM) and the KV SRAM stay flat; a VM-sourced read takes the banks'
    reg [4*N-1:0] was_vm;
    reg [4*N*32-1:0] rq_mix;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            for (s = 0; s < 4; s = s + 1) begin
                ad = rd_addr[(4*l + s)*AW +: AW];
                if (rd_re[4*l + s]) was_vm[4*l + s] <= rd_src[8*l + 2*s +: 2] == 2'd0;
                if (rd_re[4*l + s])
                    case (rd_src[8*l + 2*s +: 2])
                        2'd0: ;
                        2'd1: rd_q[(4*l + s)*32 +: 32] <= cr[ad & ((1<<CRA)-1)][31:0];
                        2'd2: rd_q[(4*l + s)*32 +: 32] <= cr[ad & ((1<<CRA)-1)][63:32];
                        default: rd_q[(4*l + s)*32 +: 32] <= {wr[ad & ((1<<WRA)-1)], 16'h0000};
                    endcase
            end
            if (kv_we[l]) kv[kv_waddr[l*AW +: AW] & ((1<<KVA)-1)] <= kv_wdata[32*l +: 32];
        end
    end
    // a port holds its last word between reads (the flat memory's registers do): keep the bank answer
    reg [4*N*32-1:0] rd_hold; reg [N*32-1:0] vi_hold;
    reg [4*N-1:0] rd_live; reg [N-1:0] vi_live;
    always @(posedge clk) begin
        rd_live <= d_re[4*N-1:0]; vi_live <= d_re[4*N +: N];
        for (l = 0; l < 4 * N; l = l + 1) if (rd_live[l]) rd_hold[l*32 +: 32] <= d_q[l*32 +: 32];
        for (l = 0; l < N; l = l + 1) if (vi_live[l]) vi_hold[l*32 +: 32] <= d_q[(4*N + l)*32 +: 32];
    end
    always @(*) begin
        for (l = 0; l < 4 * N; l = l + 1)
            rq_mix[l*32 +: 32] = !was_vm[l] ? rd_q[l*32 +: 32] : rd_live[l] ? d_q[l*32 +: 32] : rd_hold[l*32 +: 32];
    end
    assign rd_q_u = rq_mix;
    initial begin was_vm = 0; rd_live = 0; vi_live = 0; end
    genvar gv;
    for (gv = 0; gv < N; gv = gv + 1) begin : g_vi
        assign vi_q_u[gv*32 +: 32] = vi_live[gv] ? d_q[(4*N + gv)*32 +: 32] : vi_hold[gv*32 +: 32];
    end
    // the flat image in (cycle 1, before reset leaves) and out (two cycles before the dump below)
    integer bi;
    always @(posedge clk) begin
        bd_load <= (cyc == 1);
        if (cyc == 1) for (bi = 0; bi < (1 << VMA); bi = bi + 1) u_vmd.bd_img[bi] = vm[bi];
        bd_dump <= (quiet == 5 || cyc == TMAX - 1);
        if (quiet == 7 || cyc == TMAX) begin
            for (bi = 0; bi < (1 << VMA); bi = bi + 1) vm[bi] = u_vmd.bd_img[bi];
            u_vmd.report();
        end
        if (d_fault) $display("F %0d vmdist", cyc);
    end
    end endgenerate

    // ---- trace and end ----------------------------------------------------------------------------------
    always @(posedge clk) if (rst_n) begin
        if (dbg_emit || dbg_ret || dbg_res)
            $display("C %0d %s%0d %s%0d %s%0d", cyc, dbg_emit ? "e" : "-", dbg_eseq, dbg_ret ? "r" : "-", dbg_rseq,
                     dbg_res ? "s" : "-", dbg_sseq);
        if (fault) $display("F %0d fault", cyc);
        if (order_fault) $display("O %0d order", cyc);
        quiet <= (pc >= nprog && idle && !xrun && !xpipe_busy) ? quiet + 1 : 0;
        if (quiet == 8 || cyc > TMAX) begin
            $writememh(fvmo, vm);
            $writememh(fkvo, kv);
            $display("END %0d %s", cyc, (cyc > TMAX) ? "timeout" : "ok");
            $finish;
        end
    end
endmodule
