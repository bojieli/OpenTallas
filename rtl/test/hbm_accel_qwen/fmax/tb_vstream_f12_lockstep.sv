`timescale 1ns/1ps
// Exactness + latency bench of the 1.2 GHz stream-unit successor (tools/qwen_hbmacc_vstream_f12_emit.py):
// the pinned unit (REF: ot_hdc_vstream_rt, the vehicle's emit_vstream of rtl/hdc/ot_hdc_vstream.sv) and the
// successor (DUT: ot_hdc_vstream_rt_f12 #(LA, LM)) run the SAME random op list, each issued as soon as its own
// unit is ready (op k may first wait for the unit to go idle: a barrier, flag drawn per op), against identical
// read-only memories (word = hash(port, address)).  Every write port's stream is logged per lane in order:
// vector-memory writes, KV writes (FP8), reducer writes, and the fault flag; at the end the two logs must be
// identical word for word.  Barrier ops also give each op's isolated latency (accept -> idle) on both units.
// Build (Verilator 5.050): --binary --timing +seed=n -GNOPS=n -GLA=7 -GLM=6
module tb_vstream_f12_lockstep;
    parameter integer SW = 64, LV = 7, WR = 16, AW = 24, NW = 18;
    parameter integer LA = 7, LM = 6;
    parameter integer NOPS = 200;             // op list length (run: +seed=<n>)
    parameter integer MAXNIN = 600;
    localparam integer NOPF = 1 + 18 + 18 + 3 * (1 + 3 * 24) + 2 + 2 + 3 + 3 + 1 + 1 + 2 + 3 * 24 + 2 + 1 + 2 * 24 + 64 + 1;

    reg clk = 0, rst_n = 0;
    integer SEED = 1;
    reg dump = 0;
    initial dump = $test$plusargs("dump");
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    initial forever #0.5 clk = ~clk;

    // ---------------- op list ----------------
    reg [NW-1:0] o_nout [0:NOPS-1], o_nin [0:NOPS-1];
    reg          o_asrc [0:NOPS-1], o_bsrc [0:NOPS-1], o_csrc [0:NOPS-1];
    reg [AW-1:0] o_ab [0:NOPS-1], o_aso [0:NOPS-1], o_asi [0:NOPS-1];
    reg [AW-1:0] o_bb [0:NOPS-1], o_bso [0:NOPS-1], o_bsi [0:NOPS-1];
    reg [AW-1:0] o_cb [0:NOPS-1], o_cso [0:NOPS-1], o_csi [0:NOPS-1];
    reg [1:0]    o_ma [0:NOPS-1], o_mb [0:NOPS-1], o_dst [0:NOPS-1], o_red [0:NOPS-1];
    reg [2:0]    o_ad [0:NOPS-1], o_sfu [0:NOPS-1];
    reg          o_mc [0:NOPS-1], o_md [0:NOPS-1], o_redsq [0:NOPS-1], o_bar [0:NOPS-1];
    reg [AW-1:0] o_db [0:NOPS-1], o_dso [0:NOPS-1], o_dsi [0:NOPS-1], o_rb [0:NOPS-1], o_rso [0:NOPS-1];
    reg [31:0]   o_i1 [0:NOPS-1], o_i2 [0:NOPS-1];

    function automatic [31:0] rfloat(input integer lo, input integer hi);
        reg [31:0] r; integer e;
        begin
            r = $urandom;
            e = lo + ($urandom % (hi - lo + 1));
            rfloat = {r[31], e[7:0], r[22:0]};
        end
    endfunction
    function automatic [31:0] hmix(input [31:0] x);
        reg [31:0] h;
        begin
            h = x ^ (x >> 16); h = h * 32'h7feb352d; h = h ^ (h >> 15); h = h * 32'h846ca68b; h = h ^ (h >> 16);
            hmix = h;
        end
    endfunction
    // memory word: a float with exponent in [115, 133] (|x| in ~2^-12 .. 2^6), occasionally 0 or a huge value
    function automatic [31:0] mword(input [3:0] port, input [AW-1:0] a, input integer k);
        reg [31:0] h; reg [7:0] e;
        begin
            h = hmix({port, a[23:0], 4'(k)} ^ (SEED * 32'h9e3779b9));
            e = 8'd115 + (h[30:23] % 8'd19);
            if (h[7:0] == 8'd0) mword = 32'd0;
            else if (h[7:0] == 8'd1) mword = {h[31], 8'd250, h[22:0]};
            else mword = {h[31], e, h[22:0]};
        end
    endfunction

    integer k;
    initial begin
        if (!$value$plusargs("seed=%d", SEED)) SEED = 1;
        void'($urandom(SEED));
        for (k = 0; k < NOPS; k = k + 1) begin
            o_nout[k] = 1 + ($urandom % 3);
            case ($urandom % 4)
                0: o_nin[k] = 1 + ($urandom % 64);
                1: o_nin[k] = 1 + ($urandom % MAXNIN);
                2: o_nin[k] = 64 * (1 + ($urandom % 4));
                default: o_nin[k] = 1 + ($urandom % 200);
            endcase
            o_asrc[k] = ($urandom % 16) == 0; o_bsrc[k] = $urandom % 2; o_csrc[k] = $urandom % 2;
            o_ab[k] = $urandom % 65536; o_aso[k] = $urandom % 1024; o_asi[k] = $urandom % 3;
            o_bb[k] = $urandom % 65536; o_bso[k] = $urandom % 1024; o_bsi[k] = $urandom % 3;
            o_cb[k] = $urandom % 65536; o_cso[k] = $urandom % 1024; o_csi[k] = $urandom % 3;
            o_ma[k] = $urandom % 4; o_mb[k] = $urandom % 3; o_ad[k] = $urandom % 5; o_sfu[k] = $urandom % 5;
            o_mc[k] = $urandom % 2; o_md[k] = $urandom % 2;
            o_dst[k] = $urandom % 3; o_red[k] = $urandom % 3; o_redsq[k] = $urandom % 2;
            o_db[k] = $urandom % 65536; o_dso[k] = $urandom % 1024; o_dsi[k] = 1;
            o_rb[k] = $urandom % 65536; o_rso[k] = 1;
            o_i1[k] = rfloat(118, 130); o_i2[k] = rfloat(118, 130);
            o_bar[k] = ($urandom % 3) == 0;
            // reductions: at most 2^LV vectors a segment
            if (o_red[k] != 0 && o_nin[k] > SW * (1 << LV)) o_nin[k] = SW * (1 << LV);
        end
    end

    // ---------------- one unit + its driver + its memories + its logs ----------------
`define SU_SIDE(NAME, MOD, PARAMS) \
    reg NAME``_go; \
    wire NAME``_ready, NAME``_idle, NAME``_fault, NAME``_act; \
    wire [7:0] NAME``_inf; \
    integer NAME``_k; \
    reg [NW-1:0] NAME``_nout, NAME``_nin; reg NAME``_asrc, NAME``_bsrc, NAME``_csrc; \
    reg [AW-1:0] NAME``_ab, NAME``_aso, NAME``_asi, NAME``_bb, NAME``_bso, NAME``_bsi, NAME``_cb, NAME``_cso, NAME``_csi; \
    reg [1:0] NAME``_ma, NAME``_mb, NAME``_dst, NAME``_red; reg [2:0] NAME``_ad, NAME``_sfu; reg NAME``_mc, NAME``_md, NAME``_redsq; \
    reg [AW-1:0] NAME``_db, NAME``_dso, NAME``_dsi, NAME``_rb, NAME``_rso; reg [31:0] NAME``_i1, NAME``_i2; \
    wire [SW-1:0] NAME``_va_re, NAME``_vb_re, NAME``_vc_re, NAME``_crom_re, NAME``_vm_we, NAME``_kv_we; \
    wire [SW*AW-1:0] NAME``_va_addr, NAME``_vb_addr, NAME``_vc_addr, NAME``_crom_addr, NAME``_vm_waddr, NAME``_kv_waddr; \
    reg  [SW*32-1:0] NAME``_va_q, NAME``_vb_q, NAME``_vc_q; reg [SW*64-1:0] NAME``_crom_q; \
    wire [SW*32-1:0] NAME``_vm_wdata, NAME``_kv_wdata; \
    wire NAME``_wrom_re; wire [AW-1:0] NAME``_wrom_addr; reg [WR*16-1:0] NAME``_wrom_q; \
    wire NAME``_red_we; wire [AW-1:0] NAME``_red_addr; wire [31:0] NAME``_red_data; \
    wire [15:0] NAME``_prog, NAME``_progr; \
    MOD PARAMS u_``NAME ( \
        .rt_active(NAME``_act), .rt_inflight(NAME``_inf), \
        .clk(clk), .rst_n(rst_n), .go(NAME``_go), .ready(NAME``_ready), .idle(NAME``_idle), \
        .i_nout(NAME``_nout), .i_nin(NAME``_nin), \
        .i_asrc(NAME``_asrc), .i_abase(NAME``_ab), .i_aso(NAME``_aso), .i_asi(NAME``_asi), \
        .i_bsrc(NAME``_bsrc), .i_bbase(NAME``_bb), .i_bso(NAME``_bso), .i_bsi(NAME``_bsi), \
        .i_csrc(NAME``_csrc), .i_cbase(NAME``_cb), .i_cso(NAME``_cso), .i_csi(NAME``_csi), \
        .i_ma(NAME``_ma), .i_mb(NAME``_mb), .i_ad(NAME``_ad), .i_sfu(NAME``_sfu), .i_mc(NAME``_mc), .i_md(NAME``_md), \
        .i_dst(NAME``_dst), .i_dbase(NAME``_db), .i_dso(NAME``_dso), .i_dsi(NAME``_dsi), \
        .i_red(NAME``_red), .i_redsq(NAME``_redsq), .i_rbase(NAME``_rb), .i_rso(NAME``_rso), .i_imm1(NAME``_i1), .i_imm2(NAME``_i2), \
        .va_re(NAME``_va_re), .va_addr(NAME``_va_addr), .va_q(NAME``_va_q), \
        .vb_re(NAME``_vb_re), .vb_addr(NAME``_vb_addr), .vb_q(NAME``_vb_q), \
        .vc_re(NAME``_vc_re), .vc_addr(NAME``_vc_addr), .vc_q(NAME``_vc_q), \
        .wrom_re(NAME``_wrom_re), .wrom_addr(NAME``_wrom_addr), .wrom_q(NAME``_wrom_q), \
        .crom_re(NAME``_crom_re), .crom_addr(NAME``_crom_addr), .crom_q(NAME``_crom_q), \
        .vm_we(NAME``_vm_we), .vm_waddr(NAME``_vm_waddr), .vm_wdata(NAME``_vm_wdata), \
        .kv_we(NAME``_kv_we), .kv_waddr(NAME``_kv_waddr), .kv_wdata(NAME``_kv_wdata), \
        .red_we(NAME``_red_we), .red_addr(NAME``_red_addr), .red_data(NAME``_red_data), \
        .progress(NAME``_prog), .progress_rows(NAME``_progr), .fault(NAME``_fault)); \
    integer NAME``_l; \
    always @(posedge clk) begin \
        for (NAME``_l = 0; NAME``_l < SW; NAME``_l = NAME``_l + 1) begin \
            NAME``_va_q[32*NAME``_l +: 32] <= mword(4'd1, NAME``_va_addr[AW*NAME``_l +: AW], 0); \
            NAME``_vb_q[32*NAME``_l +: 32] <= mword(4'd2, NAME``_vb_addr[AW*NAME``_l +: AW], 0); \
            NAME``_vc_q[32*NAME``_l +: 32] <= mword(4'd3, NAME``_vc_addr[AW*NAME``_l +: AW], 0); \
            NAME``_crom_q[64*NAME``_l +: 64] <= {mword(4'd5, NAME``_crom_addr[AW*NAME``_l +: AW], 1), mword(4'd4, NAME``_crom_addr[AW*NAME``_l +: AW], 0)}; \
        end \
        for (NAME``_l = 0; NAME``_l < WR; NAME``_l = NAME``_l + 1) \
            NAME``_wrom_q[16*NAME``_l +: 16] <= mword(4'd6, NAME``_wrom_addr, NAME``_l) >> 16; \
    end \
    /* driver: op k waits for idle first when it is a barrier op */ \
    reg NAME``_wait_idle; integer NAME``_t_acc [0:NOPS-1]; integer NAME``_t_idle [0:NOPS-1]; integer NAME``_last; \
    always @(*) begin \
        NAME``_go = rst_n && NAME``_k < NOPS && (!o_bar[NAME``_k] || (NAME``_idle && NAME``_last < 0)); \
        NAME``_nout = o_nout[NAME``_k]; NAME``_nin = o_nin[NAME``_k]; \
        NAME``_asrc = o_asrc[NAME``_k]; NAME``_bsrc = o_bsrc[NAME``_k]; NAME``_csrc = o_csrc[NAME``_k]; \
        NAME``_ab = o_ab[NAME``_k]; NAME``_aso = o_aso[NAME``_k]; NAME``_asi = o_asi[NAME``_k]; \
        NAME``_bb = o_bb[NAME``_k]; NAME``_bso = o_bso[NAME``_k]; NAME``_bsi = o_bsi[NAME``_k]; \
        NAME``_cb = o_cb[NAME``_k]; NAME``_cso = o_cso[NAME``_k]; NAME``_csi = o_csi[NAME``_k]; \
        NAME``_ma = o_ma[NAME``_k]; NAME``_mb = o_mb[NAME``_k]; NAME``_ad = o_ad[NAME``_k]; NAME``_sfu = o_sfu[NAME``_k]; \
        NAME``_mc = o_mc[NAME``_k]; NAME``_md = o_md[NAME``_k]; NAME``_dst = o_dst[NAME``_k]; NAME``_red = o_red[NAME``_k]; \
        NAME``_redsq = o_redsq[NAME``_k]; NAME``_db = o_db[NAME``_k]; NAME``_dso = o_dso[NAME``_k]; NAME``_dsi = o_dsi[NAME``_k]; \
        NAME``_rb = o_rb[NAME``_k]; NAME``_rso = o_rso[NAME``_k]; NAME``_i1 = o_i1[NAME``_k]; NAME``_i2 = o_i2[NAME``_k]; \
    end \
    always @(posedge clk) begin \
        if (!rst_n) begin NAME``_k <= 0; NAME``_last <= -1; end \
        else begin \
            if (NAME``_go && NAME``_ready) begin \
                NAME``_t_acc[NAME``_k] <= cyc; \
                if (o_bar[NAME``_k]) NAME``_last <= NAME``_k; \
                NAME``_k <= NAME``_k + 1; \
            end else if (NAME``_last >= 0 && NAME``_idle && !(NAME``_go && NAME``_ready)) begin \
                NAME``_t_idle[NAME``_last] <= cyc; NAME``_last <= -1; \
            end \
        end \
    end \
    /* logs: a running checksum and count per lane per port (order-sensitive), plus the reducer stream */ \
    reg [63:0] NAME``_vmh [0:SW-1]; reg [63:0] NAME``_kvh [0:SW-1]; reg [63:0] NAME``_rdh; \
    integer NAME``_vmn, NAME``_kvn, NAME``_rdn, NAME``_faults; reg NAME``_fault_q; \
    integer NAME``_fd; initial if ($test$plusargs("dump")) NAME``_fd = $fopen(`"NAME.dump`", "w"); \
    always @(posedge clk) begin \
        if (!rst_n) begin \
            for (NAME``_l = 0; NAME``_l < SW; NAME``_l = NAME``_l + 1) begin NAME``_vmh[NAME``_l] <= 0; NAME``_kvh[NAME``_l] <= 0; end \
            NAME``_rdh <= 0; NAME``_vmn <= 0; NAME``_kvn <= 0; NAME``_rdn <= 0; NAME``_faults <= 0; NAME``_fault_q <= 0; \
        end else begin \
            for (NAME``_l = 0; NAME``_l < SW; NAME``_l = NAME``_l + 1) begin \
                if (NAME``_vm_we[NAME``_l]) NAME``_vmh[NAME``_l] <= {NAME``_vmh[NAME``_l][62:0], NAME``_vmh[NAME``_l][63]} ^ \
                    {8'd0, NAME``_vm_waddr[AW*NAME``_l +: AW], NAME``_vm_wdata[32*NAME``_l +: 32]} ^ 64'h9e3779b97f4a7c15 * (NAME``_vmh[NAME``_l] + 1); \
                if (NAME``_kv_we[NAME``_l]) NAME``_kvh[NAME``_l] <= {NAME``_kvh[NAME``_l][62:0], NAME``_kvh[NAME``_l][63]} ^ \
                    {8'd0, NAME``_kv_waddr[AW*NAME``_l +: AW], NAME``_kv_wdata[32*NAME``_l +: 32]} ^ 64'h9e3779b97f4a7c15 * (NAME``_kvh[NAME``_l] + 1); \
            end \
            if (dump) begin \
                if (NAME``_vm_we[0]) $fwrite(NAME``_fd, "vm %h %h\n", NAME``_vm_waddr[AW-1:0], NAME``_vm_wdata[31:0]); \
                if (NAME``_kv_we[0]) $fwrite(NAME``_fd, "kv %h %h\n", NAME``_kv_waddr[AW-1:0], NAME``_kv_wdata[31:0]); \
                if (NAME``_red_we) $fwrite(NAME``_fd, "rd %h %h\n", NAME``_red_addr, NAME``_red_data); \
                if (NAME``_go && NAME``_ready) $fwrite(NAME``_fd, "op %0d sfu %0d red %0d sq %0d ma %0d mb %0d ad %0d mc %0d md %0d dst %0d nin %0d nout %0d bsrc %0d csrc %0d asrc %0d\n", NAME``_k, NAME``_sfu, NAME``_red, NAME``_redsq, NAME``_ma, NAME``_mb, NAME``_ad, NAME``_mc, NAME``_md, NAME``_dst, NAME``_nin, NAME``_nout, NAME``_bsrc, NAME``_csrc, NAME``_asrc); \
            end \
            NAME``_vmn <= NAME``_vmn + $countones(NAME``_vm_we); NAME``_kvn <= NAME``_kvn + $countones(NAME``_kv_we); \
            if (NAME``_red_we) begin \
                NAME``_rdh <= {NAME``_rdh[62:0], NAME``_rdh[63]} ^ {8'd0, NAME``_red_addr, NAME``_red_data} ^ 64'h9e3779b97f4a7c15 * (NAME``_rdh + 1); \
                NAME``_rdn <= NAME``_rdn + 1; \
            end \
            NAME``_fault_q <= NAME``_fault; if (NAME``_fault && !NAME``_fault_q) NAME``_faults <= NAME``_faults + 1; \
            if (NAME``_inf == 8'hFF) begin $display("FAIL inflight saturated"); $finish; end \
        end \
    end

    `SU_SIDE(ref, ot_hdc_vstream_rt, #(.SW(SW), .LV(LV), .WR(WR), .AW(AW), .NW(NW), .KV_FP8(1)))
    `SU_SIDE(dut, ot_hdc_vstream_rt_f12, #(.LA(LA), .LM(LM), .SW(SW), .LV(LV), .WR(WR), .AW(AW), .NW(NW), .KV_FP8(1)))

    // ---------------- run, compare ----------------
    integer l, bad, ncmp, nlat, j, cls;
    integer dsum [0:4][0:2]; integer dcnt [0:4][0:2]; integer dmin [0:4][0:2]; integer dmax [0:4][0:2];
    integer rsum [0:4][0:2];
    initial begin
        repeat (4) @(posedge clk);
        rst_n = 1;
        wait (ref_k == NOPS && dut_k == NOPS);
        wait (ref_idle && dut_idle && !ref_go && !dut_go);
        repeat (400) @(posedge clk);
        bad = 0;
        for (l = 0; l < SW; l = l + 1) begin
            if (ref_vmh[l] != dut_vmh[l]) begin bad = bad + 1; $display("MISMATCH vm lane %0d", l); end
            if (ref_kvh[l] != dut_kvh[l]) begin bad = bad + 1; $display("MISMATCH kv lane %0d", l); end
        end
        if (ref_rdh != dut_rdh) begin bad = bad + 1; $display("MISMATCH reducer"); end
        if (ref_vmn != dut_vmn || ref_kvn != dut_kvn || ref_rdn != dut_rdn) begin bad = bad + 1; $display("MISMATCH counts"); end
        // the unit's fault pulses are the registered OR over lanes and stages, so their count depends on the
        // pipeline depths; the contract compared is the sticky flag (any faulting element) of the whole run
        if ((ref_faults != 0) != (dut_faults != 0)) begin bad = bad + 1; $display("MISMATCH faults %0d %0d", ref_faults, dut_faults); end
        // isolated latency of barrier ops followed by a barrier op (accept -> idle), per sfu class x reduction kind
        for (j = 0; j < 5; j = j + 1) for (cls = 0; cls < 3; cls = cls + 1) begin
            dsum[j][cls] = 0; dcnt[j][cls] = 0; dmin[j][cls] = 1 << 30; dmax[j][cls] = -(1 << 30); rsum[j][cls] = 0;
        end
        nlat = 0;
        for (j = 0; j + 1 < NOPS; j = j + 1) if (o_bar[j] && o_bar[j + 1]) begin
            dsum[o_sfu[j]][o_red[j]] = dsum[o_sfu[j]][o_red[j]] + ((dut_t_idle[j] - dut_t_acc[j]) - (ref_t_idle[j] - ref_t_acc[j]));
            rsum[o_sfu[j]][o_red[j]] = rsum[o_sfu[j]][o_red[j]] + (ref_t_idle[j] - ref_t_acc[j]);
            if ((dut_t_idle[j] - dut_t_acc[j]) - (ref_t_idle[j] - ref_t_acc[j]) < dmin[o_sfu[j]][o_red[j]]) dmin[o_sfu[j]][o_red[j]] = (dut_t_idle[j] - dut_t_acc[j]) - (ref_t_idle[j] - ref_t_acc[j]);
            if ((dut_t_idle[j] - dut_t_acc[j]) - (ref_t_idle[j] - ref_t_acc[j]) > dmax[o_sfu[j]][o_red[j]]) dmax[o_sfu[j]][o_red[j]] = (dut_t_idle[j] - dut_t_acc[j]) - (ref_t_idle[j] - ref_t_acc[j]);
            dcnt[o_sfu[j]][o_red[j]] = dcnt[o_sfu[j]][o_red[j]] + 1; nlat = nlat + 1;
        end
        for (j = 0; j < 5; j = j + 1) for (cls = 0; cls < 3; cls = cls + 1) if (dcnt[j][cls] != 0)
            $display("LAT sfu=%0d red=%0d n=%0d ref_mean=%0d delta_min=%0d delta_max=%0d", j, cls, dcnt[j][cls],
                     rsum[j][cls] / dcnt[j][cls], dmin[j][cls], dmax[j][cls]);
        $display("RESULT seed=%0d ops=%0d LA=%0d LM=%0d vm_writes=%0d kv_writes=%0d red_writes=%0d faults=%0d mismatches=%0d ref_cycles=%0d dut_cycles=%0d",
                 SEED, NOPS, LA, LM, ref_vmn, ref_kvn, ref_rdn, ref_faults, bad, ref_t_acc[NOPS-1], dut_t_acc[NOPS-1]);
        $finish;
    end
endmodule
