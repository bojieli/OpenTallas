`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HA3 successor of rtl/test/gpu_sys/tb_gpu_hbm_system.sv (byte-identical) for
// rtl/hbm_accel/collective/ot_hbm_accel_hbm_system.sv (parameter HA3), plus a
// +TRACE collective trace (per SM: cycle of each COLL/COLLX issue and response).
// End-to-end bench of the GPU-organised HBM comparator system top
// (rtl/gpu_sys/ot_gpu_hbm_system.sv): this module is the HOST -- its CPU's
// register accesses on the BAR (AXI4-Lite), its memory (answering the chip's
// AXI4 DMA, holding the submission/completion rings and the prompt), and the
// driver's module/graph load through the loader port (SM instruction memories,
// per-die command lists).  HBM contents are the load-time weight images
// (tools/gpu_sys/qwen_hbm.py --emit, placed per partition by
// tools/gpu_sys/mem_image.py) read into the HBM models at time 0.
//
// The driver follows runtime/hdc/driver.py: rings at SQ 0x0000 / CQ 0x1000,
// one GENERATE descriptor (greedy, stop at EOS) for the prompt, SQ_TAIL
// doorbell, then it polls the completion ring by phase bit.  Every decode
// step the chip runs (prompt positions teacher-forced, then generated tokens
// fed back) is checked against the golden's next token, and the CQ token
// stream against the golden generation.
// Plusargs: +DIR=<emit dir>  optional +MAXCYC=<diagnostic clk_sm cycles>
// ---------------------------------------------------------------------------
module tb_hbm_accel_ha3_system;
    parameter integer HA3 = 0;
    parameter integer EPI = 1;           // HA3 port epilogue built (0: cut-through only)
    parameter integer FLAT = 5;          // FP pipe depth of the SMs and the HA3 port (7: the SS re-pipelined copies)
    parameter integer ND = 2, NSM = 2, NL = 128, IMW = 13, CB = 8, MEM_WORDS = 65536, HAS_DIV = 0, HAS_BD = 0;
    reg clk_host = 0, clk_sm = 0, clk_mem = 0, clk_link = 0;
    always #2.0    clk_host = ~clk_host;      // 250 MHz host/PCIe side
    always #0.4165 clk_sm   = ~clk_sm;        // 1.2 GHz SM domain
    always #0.5    clk_mem  = ~clk_mem;       // 1.0 GHz crossbar / L2 / HBM service
    always #0.45   clk_link = ~clk_link;      // 1.11 GHz die <-> switch links
    reg por_n = 0;

    // ---------------- BAR (AXI4-Lite) and DMA (AXI4) ports
    reg         s_awvalid = 0, s_wvalid = 0, s_bready = 1, s_arvalid = 0, s_rready = 1;
    reg  [11:0] s_awaddr = 0, s_araddr = 0;
    reg  [31:0] s_wdata = 0;
    wire        s_awready, s_wready, s_bvalid, s_arready, s_rvalid;
    wire [31:0] s_rdata;
    wire        m_arvalid, m_awvalid, m_wvalid, irq;
    wire [63:0] m_araddr, m_awaddr, m_wdata;
    wire [7:0]  m_wstrb;
    reg         m_arready = 1, m_rvalid = 0, m_awready = 1, m_wready = 1, m_bvalid = 0;
    reg  [63:0] m_rdata = 0;
    // ---------------- loader
    reg         ld_v = 0, ld_target = 0;
    reg  [3:0]  ld_die = 0, ld_sm = 0;
    reg  [23:0] ld_addr = 0;
    reg  [63:0] ld_data = 0;
    wire        ld_rdy;
    wire        sys_fault;
    wire [31:0] st_steps;

`ifdef GPU_SYS_USE_W2
    localparam integer USE_W2 = 1;
`else
    localparam integer USE_W2 = 0;
`endif
    ot_hbm_accel_hbm_system #(.ENABLE(1), .HA3(HA3), .FLAT(FLAT), .EPI(EPI), .ND(ND), .NSM(NSM), .NL(NL), .IMW(IMW), .CB(CB), .USE_W2(USE_W2), .MEM_WORDS(MEM_WORDS), .HAS_DIV(HAS_DIV),
                        .HAS_BD(HAS_BD)) dut (
        .por_n(por_n), .clk_host(clk_host), .clk_sm(clk_sm), .clk_mem(clk_mem), .clk_link(clk_link),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr), .s_wvalid(s_wvalid), .s_wready(s_wready),
        .s_wdata(s_wdata), .s_wstrb(4'hF), .s_bvalid(s_bvalid), .s_bready(s_bready), .s_arvalid(s_arvalid), .s_arready(s_arready),
        .s_araddr(s_araddr), .s_rvalid(s_rvalid), .s_rready(s_rready), .s_rdata(s_rdata),
        .m_arvalid(m_arvalid), .m_arready(m_arready), .m_araddr(m_araddr), .m_rvalid(m_rvalid), .m_rdata(m_rdata), .m_rresp(2'b00), .m_rlast(m_rvalid),
        .m_awvalid(m_awvalid), .m_awready(m_awready), .m_awaddr(m_awaddr), .m_wvalid(m_wvalid), .m_wready(m_wready),
        .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_bvalid(m_bvalid), .m_bresp(2'b00), .irq(irq),
        .ld_v(ld_v), .ld_rdy(ld_rdy), .ld_target(ld_target), .ld_die(ld_die), .ld_sm(ld_sm), .ld_addr(ld_addr),
        .ld_data(ld_data), .sys_fault(sys_fault), .st_steps(st_steps));

    // ---------------- host memory (64-bit words), answering single-beat DMA
    reg [63:0] hmem [longint];
    function automatic [63:0] hrd(input longint a);
        hrd = hmem.exists(a >> 3) ? hmem[a >> 3] : 64'd0;
    endfunction
    reg [63:0] aw_q; reg aw_have; reg [63:0] w_q; reg [7:0] ws_q; reg w_have;
    always @(posedge clk_host) begin
        if (m_rvalid) m_rvalid <= 0;
        if (m_arvalid && m_arready) begin m_rvalid <= 1; m_rdata <= hrd(m_araddr); end
        if (m_bvalid) m_bvalid <= 0;
        if (m_awvalid && m_awready) begin aw_q <= m_awaddr; aw_have <= 1; end
        if (m_wvalid && m_wready) begin w_q <= m_wdata; ws_q <= m_wstrb; w_have <= 1; end
        if (aw_have && w_have) begin
            reg [63:0] old;
            old = hrd(aw_q);
            for (int b = 0; b < 8; b++) if (ws_q[b]) old[b*8 +: 8] = w_q[b*8 +: 8];
            hmem[aw_q >> 3] = old;
            aw_have <= 0; w_have <= 0; m_bvalid <= 1;
        end
    end
    initial begin aw_have = 0; w_have = 0; end

    task automatic bar_wr(input [11:0] a, input [31:0] d);
        @(negedge clk_host); s_awvalid = 1; s_awaddr = a; s_wvalid = 1; s_wdata = d;
        while (!(s_awready && s_wready)) @(negedge clk_host);
        @(negedge clk_host); s_awvalid = 0; s_wvalid = 0;
        while (!s_bvalid) @(negedge clk_host);
    endtask
    task automatic bar_rd(input [11:0] a, output [31:0] d);
        @(negedge clk_host); s_arvalid = 1; s_araddr = a;
        while (!s_arready) @(negedge clk_host);
        @(negedge clk_host); s_arvalid = 0;
        while (!s_rvalid) @(negedge clk_host);
        d = s_rdata;
    endtask
    task automatic load(input reg tgt, input integer die, input integer sm, input integer addr, input [63:0] data);
        @(negedge clk_host); ld_v = 1; ld_target = tgt; ld_die = die; ld_sm = sm; ld_addr = addr; ld_data = data;
        @(posedge clk_host); while (!ld_rdy) @(posedge clk_host);
        @(negedge clk_host); ld_v = 0;
    endtask

    // ---------------- step monitor: every decode step's next token vs the golden
    string dir;
    integer exp_n, nsteps, fails, fd, i, j, k, maxcyc, cyc_sm;
    reg [31:0] exp_tok [0:63];
    reg [31:0] exp_in  [0:63];
    reg [63:0] prog [0:(1<<IMW)-1];
    reg [63:0] cmds [0:255];
    reg [31:0] prompt [0:63];
    integer nprompt, ngen, nimem, ncmd;
    always @(posedge clk_sm) cyc_sm <= cyc_sm + 1;
    always @(posedge clk_host) if (dut.g_on.eng_done) begin
        if (nsteps < exp_n && (dut.g_on.eng_next_token !== exp_tok[nsteps][15:0] || dut.g_on.eng_pos !== nsteps ||
                               dut.g_on.eng_token !== exp_in[nsteps][15:0])) begin
            $display("STEP %0d MISMATCH pos %0d in %0d next %0d expected in %0d next %0d fault %0d", nsteps,
                     dut.g_on.eng_pos, dut.g_on.eng_token, dut.g_on.eng_next_token, exp_in[nsteps], exp_tok[nsteps],
                     dut.g_on.eng_fault);
            fails = fails + 1;
        end else
            $display("STEP %0d pos %0d in %0d next %0d OK  (step %0d clk_sm cycles, sim cycle %0d) fault %0d", nsteps,
                     dut.g_on.eng_pos, dut.g_on.eng_token, dut.g_on.eng_next_token, dut.g_on.eng_cycles, cyc_sm,
                     dut.g_on.eng_fault);
        if (dut.g_on.eng_fault) fails = fails + 1;
        nsteps = nsteps + 1;
        $fflush();
    end

    // ---------------- +TRACE: collective issue / response per SM (ND = 2, NSM = 2 bench shape)
    integer trace;
    initial if (!$value$plusargs("TRACE=%d", trace)) trace = 0;
`define HA3_CTRACE(D, S) \
    reg [3:0] bq_``D``_``S; \
    always @(posedge clk_sm) begin \
        bq_``D``_``S <= dut.g_on.g_die[D].g_sm[S].u_sm.g_on.bst; \
        if (trace != 0 && dut.g_on.g_die[D].g_sm[S].u_sm.g_on.bst != bq_``D``_``S) begin \
            if (dut.g_on.g_die[D].g_sm[S].u_sm.g_on.bst == 4'd2) $display("CT %0d d%0d s%0d REQ x%0d", cyc_sm, D, S, dut.g_on.g_die[D].g_sm[S].u_sm.g_on.c_x); \
            if (bq_``D``_``S == 4'd3) $display("CT %0d d%0d s%0d RSP", cyc_sm, D, S); \
            if (dut.g_on.g_die[D].g_sm[S].u_sm.g_on.bst == 4'd4) $display("CT %0d d%0d s%0d BAR", cyc_sm, D, S); \
            if (bq_``D``_``S == 4'd4) $display("CT %0d d%0d s%0d BARREL", cyc_sm, D, S); \
            if (dut.g_on.g_die[D].g_sm[S].u_sm.g_on.bst == 4'd5) $display("CT %0d d%0d s%0d TCWAIT", cyc_sm, D, S); \
            if (bq_``D``_``S == 4'd5) $display("CT %0d d%0d s%0d TCDONE", cyc_sm, D, S); \
        end \
        if (trace != 0 && dut.g_on.g_die[D].g_sm[S].u_sm.launch_v && !dut.g_on.g_die[D].g_sm[S].u_sm.g_on.running) \
            $display("CT %0d d%0d s%0d LAUNCH %0d", cyc_sm, D, S, dut.g_on.g_die[D].g_sm[S].u_sm.launch_pc); \
        if (trace != 0 && dut.g_on.g_die[D].g_sm[S].u_sm.sm_done) $display("CT %0d d%0d s%0d DONE", cyc_sm, D, S); \
    end
    `HA3_CTRACE(0, 0)
    `HA3_CTRACE(0, 1)
    `HA3_CTRACE(1, 0)
    `HA3_CTRACE(1, 1)

    reg [31:0] r32;
    reg [63:0] w0, w1;
    integer cq_head, phase, got_last, ntok;
    reg [15:0] cq_tok [0:63];
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 0; // No default cycle limit; admitted builds run to completion.
        fd = $fopen({dir, "/tb_cfg.txt"}, "r");
        void'($fscanf(fd, "%d %d %d %d %d", exp_n, nprompt, ngen, nimem, ncmd));
        for (i = 0; i < exp_n; i++) void'($fscanf(fd, "%d %d", exp_in[i], exp_tok[i]));
        for (i = 0; i < nprompt; i++) void'($fscanf(fd, "%d", prompt[i]));
        $fclose(fd);
        nsteps = 0; fails = 0; cyc_sm = 0;
        #20 por_n = 1;
        while (!dut.g_on.rst_host_n) @(posedge clk_host);
        // ---- driver: module load (instruction memories) and graph load (command lists)
        for (int d = 0; d < ND; d++) begin
            for (int s = 0; s < NSM; s++) begin
                $readmemh($sformatf("%s/prog_d%0d_s%0d.hex", dir, d, s), prog, 0, nimem - 1);
                for (i = 0; i < nimem; i++) load(1, d, s, i, prog[i]);
            end
            $readmemh($sformatf("%s/cmd_d%0d.hex", dir, d), cmds, 0, ncmd - 1);
            for (i = 0; i < ncmd; i++) load(0, d, 0, i, cmds[i]);
        end
        $display("LOADED %0d instruction words x %0d SMs, %0d commands x %0d dies", nimem, ND * NSM, ncmd, ND);
        // ---- driver: host interface bring-up (runtime/hdc/driver.py)
        bar_rd(12'h000, r32);
        if (r32 != 32'h4F544849) begin $display("FAIL BAR ID %h", r32); $finish; end
        bar_wr(12'h010, 32'h0000); bar_wr(12'h014, 0); bar_wr(12'h018, 6);
        bar_wr(12'h024, 32'h1000); bar_wr(12'h028, 0); bar_wr(12'h02C, 8);
        bar_wr(12'h03C, 3); bar_wr(12'h008, 1);
        // prompt at 0x10000, packed 16-bit ids
        for (i = 0; i < nprompt; i++) begin
            w0 = hrd(64'h10000 + (i / 4) * 8);
            w0[(i % 4) * 16 +: 16] = prompt[i][15:0];
            hmem[(64'h10000 + (i / 4) * 8) >> 3] = w0;
        end
        // GENERATE, greedy | stop-at-EOS, tag 7, prompt length, max new tokens; EOS 93
        hmem[0] = 64'h1 | (64'h3 << 8) | (64'd7 << 16) | (64'(nprompt) << 32) | (64'(ngen) << 48);
        hmem[1] = 64'h10000;
        hmem[2] = 64'd0;
        hmem[3] = 64'd93 | (64'd93 << 16);
        bar_wr(12'h01C, 1);                       // SQ_TAIL doorbell
        // ---- poll the completion ring
        cq_head = 0; phase = 1; got_last = 0; ntok = 0;
        while (!got_last && (maxcyc == 0 || cyc_sm < maxcyc)) begin
            repeat (200) @(posedge clk_host);
            forever begin
                w0 = hrd(64'h1000 + cq_head * 16);
                w1 = hrd(64'h1000 + cq_head * 16 + 8);
                if (w0[0] != phase[0]) break;
                $display("CQ kind %0d status %0d slot %0d tag %0d pos %0d token %0d step_cycles %0d generated %0d",
                         w0[2:1], w0[7:4], w0[15:8], w0[31:16], w0[47:32], w0[63:48], w1[31:0], w1[47:32]);
                cq_tok[ntok] = w0[63:48]; ntok++;
                if (w0[2:1] != 2'd1) got_last = 1;
                cq_head++;
            end
            if (cq_head != 0) begin bar_wr(12'h030, cq_head); bar_wr(12'h038, 1); end
        end
        if (!got_last) begin $display("FAIL timeout at %0d clk_sm cycles, %0d steps", cyc_sm, nsteps); fails++; end
        for (i = 0; i < ntok; i++)
            if (cq_tok[i] != exp_tok[nprompt - 1 + i][15:0]) begin
                $display("CQ token %0d = %0d expected %0d", i, cq_tok[i], exp_tok[nprompt - 1 + i]); fails++;
            end
        if (ntok != ngen) begin $display("CQ delivered %0d tokens, expected %0d", ntok, ngen); fails++; end
        if (nsteps != exp_n) begin $display("ran %0d steps, expected %0d", nsteps, exp_n); fails++; end
        if (sys_fault) begin $display("system fault flag set"); fails++; end
        bar_rd(12'h070, r32); $display("BAR tokens counter %0d", r32);
        bar_rd(12'h07C, r32); $display("BAR MSIs %0d", r32);
        $display("TB_GPU_HBM_SYSTEM %s steps=%0d cq_tokens=%0d clk_sm_cycles=%0d fails=%0d", fails ? "FAIL" : "PASS",
                 nsteps, ntok, cyc_sm, fails);
        $finish;
    end
endmodule
