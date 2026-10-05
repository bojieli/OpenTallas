`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// End-to-end functional simulation of the Qwen3 ROM system top
// (rtl/qwen_sys/ot_qwen_rom_sys_top.sv), reduced vehicle, TP-4.
//
// Outside the DUT (what silicon has as hard IP or software):
//   * the HOST: a register-level driver (AXI4-Lite master) and host memory
//     (AXI4 slave) holding the submission and completion rings, the prompts
//     and the MSI target -- it boots the system, configures the rings, writes
//     one GENERATE descriptor per user, rings the SQ doorbell and consumes
//     completions on interrupt (CQ phase bit, CQ_HEAD doorbell, IRQ W1C);
//   * the die-to-die channels (ot_qwen_d2d_chan; in-package UCIe LAT_PKG,
//     the board link between the two 2-die packages LAT_BOARD) with optional
//     bit-error injection (+FLIP=<period>);
//   * one HBM device + controller model per die (ot_qwen_hbm_model_ack,
//     WR_ACK = 1: writes complete on a tagged write-done; refresh, bank timing,
//     FR-FCFS reordering, per-PC response ports).
// Nothing inside the DUT is driven by the bench.
//
// Checks (bit for bit against tools/hdc_program.py --tp 4 images: the
// ISA-level tensor group, itself bit-exact with tools/hdc_golden.py at every
// step; generated ids against the torch oracle):
//   1. every step of every user: all dies' {token, logit} == expect_steps[pos];
//   2. the host's completions: kind, tag, slot, position and token of every
//      generated token, the last flagged, == generated.hex;
//   3. every die's HBM, every user's KV region, == expect_kv (the KV written by
//      the RTL through the KV service and acknowledged by HBM);
//   4. every die's vector memory == expect_vm;
//   5. FAULT_STATUS (read by the host) == 0 and fault_src == 0 (or, for the
//      negative runs, the expected source latched and an error completion);
//   6. +FLIP: CRC errors detected and replays performed, tokens still exact.
// Fault-injection runs: +HBM_TAG_FLIP=<n> corrupts the tag of die 2's n-th
// HBM response; +BREAK=<cycle> breaks die 0 -> die 3's channel at that cycle.
// ---------------------------------------------------------------------------
module tb_qwen_rom_sys #(
    parameter integer LAT_PKG   = 8,
    parameter integer LAT_BOARD = 40,
    parameter integer ME_CDC    = 0,
    parameter integer KV_PREFETCH = 0
) (input wire sclk, input wire fclk, input wire [63:0] tick);
    // clocks from rtl/test/qwen_sys/qsys_harness2.cpp: +CLK=slow (one 0.9 GHz clock) or +CLK=split
    // (fclk 1.2 GHz for the matrix engines, sclk 0.9 GHz for everything else, 3:4 from one PLL)
    wire clk = sclk;
    localparam integer N = 4, G = 4, NW = 16, NSLOT = 4, KVW = 512, NPC = 4, HTAGW = 7;
    localparam integer TAGW = 2 + 2 * NW + 6;
    localparam integer LFW = 32 + 1 + 1 + 8 + 1 + 8 + 1 + 1 + 3 + (512 + 2 + TAGW);
    localparam integer HMEM_WORDS = NSLOT * KVW * 2 + 64;
    localparam integer W = 16, VM_ELEMS = 4096;

    integer cyc = 0;
    reg por_n = 1'b0;
    reg [8*512-1:0] dir;
    integer USERS = 2;                 // +USERS=<n> (1..4)
    integer flip = 0, tag_flip = -1, brk = -1, expect_fault = 0, ngen = 3, n_prompt = 16;

    // ------------------------------------------------------------ DUT
    reg  s_awvalid = 0, s_wvalid = 0, s_bready = 1, s_arvalid = 0, s_rready = 1;
    reg  [12:0] s_awaddr = 0, s_araddr = 0;
    reg  [31:0] s_wdata = 0;
    wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid;
    wire [31:0] s_rdata;
    wire m_arvalid, m_rready, m_awvalid, m_wvalid, m_wlast, m_bready, irq;
    reg  m_arready = 0, m_rvalid = 0, m_awready = 0, m_wready = 0, m_bvalid = 0;
    wire [63:0] m_araddr, m_awaddr, m_wdata;
    reg  [63:0] m_rdata = 0;
    wire [7:0] m_wstrb, m_arlen, m_awlen;
    wire [2:0] m_arsize, m_awsize;
    wire [N*N*LFW-1:0] ph_tx, ph_rx;
    wire [N*N-1:0] ph_rx_v;
    wire [N-1:0] h_req_v, h_req_rdy, h_req_we;
    wire [N*24-1:0] h_req_addr;
    wire [N*5-1:0] h_req_len;
    wire [N*HTAGW-1:0] h_req_tag;
    wire [N*256-1:0] h_req_wdata;
    wire [N*NPC-1:0] h_rsp_v, h_rsp_rdy, h_rsp_wr;
    wire [N*NPC*HTAGW-1:0] h_rsp_tag, h_rsp_tag_dut;
    wire [N*NPC*4-1:0] h_rsp_beat;
    wire [N*NPC*256-1:0] h_rsp_data;
    wire sys_ready;
    wire [31:0] fault_src;
    wire [N-1:0] die_done;
    wire [N*NW-1:0] die_token;
    wire [N*32-1:0] die_val;
    wire step_start;
    wire [NW-1:0] step_pos;

    ot_qwen_rom_sys_top #(.N(N), .G(G), .NW(NW), .NSLOT(NSLOT), .KVW(KVW), .TAGW(TAGW), .NPC(NPC), .HTAGW(HTAGW),
                          .LINK_TMO(4 * LAT_BOARD + 16), .ME_CDC(ME_CDC), .KV_PREFETCH(KV_PREFETCH)) dut (
        .clk(clk), .fclk(fclk), .por_n(por_n),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid), .s_wready(s_wready), .s_wdata(s_wdata), .s_wstrb(4'hF),
        .s_bvalid(s_bvalid), .s_bready(s_bready), .s_bresp(),
        .s_arvalid(s_arvalid), .s_arready(s_arready), .s_araddr(s_araddr),
        .s_rvalid(s_rvalid), .s_rready(s_rready), .s_rdata(s_rdata), .s_rresp(),
        .m_arvalid(m_arvalid), .m_arready(m_arready), .m_araddr(m_araddr), .m_arlen(m_arlen), .m_arsize(m_arsize),
        .m_rvalid(m_rvalid), .m_rready(m_rready), .m_rdata(m_rdata), .m_rresp(2'b00), .m_rlast(1'b1),
        .m_awvalid(m_awvalid), .m_awready(m_awready), .m_awaddr(m_awaddr), .m_awlen(m_awlen), .m_awsize(m_awsize),
        .m_wvalid(m_wvalid), .m_wready(m_wready), .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wlast(m_wlast),
        .m_bvalid(m_bvalid), .m_bready(m_bready), .m_bresp(2'b00), .irq(irq),
        .ph_tx(ph_tx), .ph_rx_v(ph_rx_v), .ph_rx(ph_rx),
        .h_req_v(h_req_v), .h_req_rdy(h_req_rdy), .h_req_we(h_req_we), .h_req_addr(h_req_addr),
        .h_req_len(h_req_len), .h_req_tag(h_req_tag), .h_req_wdata(h_req_wdata),
        .h_rsp_v(h_rsp_v), .h_rsp_rdy(h_rsp_rdy), .h_rsp_tag(h_rsp_tag_dut), .h_rsp_beat(h_rsp_beat),
        .h_rsp_data(h_rsp_data), .h_rsp_wr(h_rsp_wr),
        .sys_ready(sys_ready), .fault_src(fault_src), .die_done(die_done), .die_token(die_token), .die_val(die_val),
        .step_start(step_start), .step_pos(step_pos));

    // ------------------------------------------------------------ die-to-die channels
    integer n_flipped [0:N*N-1];
    genvar s, t;
    generate for (s = 0; s < N; s = s + 1) begin : g_s
        for (t = 0; t < N; t = t + 1) begin : g_t
            if (s == t) begin : g_none
                assign ph_rx_v[t*N + s] = 1'b0;
                assign ph_rx[(t*N + s)*LFW +: LFW] = {LFW{1'b0}};
            end else begin : g_ch
                // dies {0,1} and {2,3} share a package (UCIe); the others cross the board
                localparam integer LAT = ((s / 2) == (t / 2)) ? LAT_PKG : LAT_BOARD;
                integer fp, nf;
                ot_qwen_d2d_chan #(.FW(LFW), .LAT(LAT)) u_ch (
                    .clk(clk), .rst_n(por_n), .in_flit(ph_tx[(s*N + t)*LFW +: LFW]),
                    .out_valid(ph_rx_v[t*N + s]), .out_flit(ph_rx[(t*N + s)*LFW +: LFW]),
                    .flip_period(fp), .flip_start(3000 + 7 * (s*N + t)), .flip_bit(13 + 37 * (s*N + t)),
                    .n_flipped(nf));
                always @(*) begin
                    fp = (brk >= 0 && s == 0 && t == 3 && cyc >= brk) ? 1 : flip;
                    n_flipped[s*N + t] = nf;
                end
            end
        end
    end endgenerate

    // ------------------------------------------------------------ HBM, one stack model per die
    integer rsp_count2 = 0;
    generate for (s = 0; s < N; s = s + 1) begin : g_hbm
        ot_qwen_hbm_model_ack #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(HMEM_WORDS), .TAGW(HTAGW),
                                .LENW(5), .BEATW(4), .CLK_PS(1111), .PC_RDY(1), .PC_ROOM(16), .WR_ACK(1)) u_hbm (
            .clk(clk), .rst_n(por_n), .req_v(h_req_v[s]), .req_rdy(h_req_rdy[s]), .pc_room(),
            .req_we(h_req_we[s]), .req_addr(h_req_addr[s*24 +: 24]), .req_len(h_req_len[s*5 +: 5]),
            .req_tag(h_req_tag[s*HTAGW +: HTAGW]), .req_wdata(h_req_wdata[s*256 +: 256]),
            .rsp_v(h_rsp_v[s*NPC +: NPC]), .rsp_rdy(h_rsp_rdy[s*NPC +: NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*HTAGW +: NPC*HTAGW]), .rsp_beat(h_rsp_beat[s*NPC*4 +: NPC*4]),
            .rsp_data(h_rsp_data[s*NPC*256 +: NPC*256]), .rsp_wr(h_rsp_wr[s*NPC +: NPC]));
    end endgenerate
    // fault injection: one corrupted response tag on die 2 (+HBM_TAG_FLIP=n)
    reg tag_hit;
    always @(*) tag_hit = (tag_flip >= 0) && sys_ready && h_rsp_v[2*NPC] && (rsp_count2 == tag_flip);
    // the generation bit (HTAGW-1) of die 2's port-0 response
    assign h_rsp_tag_dut = h_rsp_tag ^ (tag_hit ? ({{(N*NPC*HTAGW-1){1'b0}}, 1'b1} << (2*NPC*HTAGW + HTAGW - 1)) : 0);
    // counted from system ready (the boot scrub's write-dones are not counted)
    always @(posedge clk) if (sys_ready && h_rsp_v[2*NPC]) rsp_count2 <= rsp_count2 + 1;

    // ------------------------------------------------------------ dual-clock collision monitor (ME_CDC)
    // The safe ordering rule of the two-clock core: every fast-clock read (engine x port of the VM, engine KV
    // port) of a word written on the slow clock happens more than two slow cycles (8 VCO ticks) after the write.
    // Counted per die from the slow-domain write ports; must stay 0.
    integer collisions = 0;
    generate for (s = 0; s < N; s = s + 1) begin : g_coll
        reg [63:0] vm_wt [0:4095];
        reg [63:0] kv_wt [0:KVW-1];
        integer q, l;
        initial begin
            for (q = 0; q < 4096; q = q + 1) vm_wt[q] = 0;
            for (q = 0; q < KVW; q = q + 1) kv_wt[q] = 0;
        end
        always @(posedge sclk) begin
            for (q = 0; q < G; q = q + 1)
                if (dut.g_die[s].u_die.vw_me_we[q])
                    for (l = 0; l < 16; l = l + 1)
                        if (dut.g_die[s].u_die.vw_me_mask[q*16 + l])
                            vm_wt[{dut.g_die[s].u_die.vw_me_addr[q*24 +: 8], 4'b0} + l] = tick;
            if (dut.g_die[s].u_die.vw_mx_we)
                for (l = 0; l < 16; l = l + 1)
                    if (dut.g_die[s].u_die.vw_mx_mask[l]) vm_wt[{dut.g_die[s].u_die.vw_mx_addr[7:0], 4'b0} + l] = tick;
            if (dut.g_die[s].u_die.vw_su_we) vm_wt[dut.g_die[s].u_die.vw_su_addr[11:0]] = tick;
            if (dut.g_die[s].u_die.vw_rd_we) vm_wt[dut.g_die[s].u_die.vw_rd_addr[11:0]] = tick;
            if (dut.g_die[s].u_die.s_vwe)
                for (l = 0; l < 16; l = l + 1) vm_wt[{dut.g_die[s].u_die.s_vwaddr, 4'b0} + l] = tick;
            if (dut.g_die[s].u_die.kv_we) kv_wt[dut.g_die[s].u_die.kv_waddr[12:4]] = tick;
        end
        always @(posedge fclk) if (ME_CDC != 0) begin
            for (q = 0; q < G; q = q + 1) begin
                if (dut.g_die[s].u_die.vx_re[q] && tick - vm_wt[dut.g_die[s].u_die.vx_addr[q*24 +: 12]] <= 8)
                    collisions = collisions + 1;
                if (dut.g_die[s].u_die.kv_re && tick - kv_wt[dut.g_die[s].u_die.kv_raddr[q*24 +: 9]] <= 8)
                    collisions = collisions + 1;
            end
        end
    end endgenerate

    // ------------------------------------------------------------ host memory and DMA slave
    reg [63:0] hmem [0:4095];          // 32 KB, byte address >> 3
    reg [63:0] rd_addr;
    reg        wr_pend;
    integer    n_msi = 0;
    always @(posedge clk) begin
        m_arready <= 1'b0; m_rvalid <= 1'b0; m_awready <= 1'b0; m_wready <= 1'b0; m_bvalid <= 1'b0;
        if (m_arvalid && !m_arready && !m_rvalid) begin m_arready <= 1'b1; rd_addr <= m_araddr; end
        if (m_arready) begin m_rvalid <= 1'b1; m_rdata <= hmem[rd_addr[14:3]]; end
        if (m_awvalid && m_wvalid && !m_awready && !m_bvalid) begin
            m_awready <= 1'b1; m_wready <= 1'b1;
            for (integer b = 0; b < 8; b = b + 1)
                if (m_wstrb[b]) hmem[m_awaddr[14:3]][8*b +: 8] <= m_wdata[8*b +: 8];
            if (m_awaddr == 64'h4000) n_msi = n_msi + 1;
        end
        if (m_awready) m_bvalid <= 1'b1;
    end

    // ------------------------------------------------------------ expectations
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold [0:255];
    reg [63:0]   estep [0:255];
    reg [31:0]   evm [0:N*VM_ELEMS-1];
    reg [31:0]   ekv [0:N*KVW*W-1];

    // ------------------------------------------------------------ step checker (every step, every die)
    integer bad = 0, steps_checked = 0;
    reg [NW-1:0] cur_pos;
    reg checking = 0, done_d = 0;
    always @(posedge clk) begin
        done_d <= &die_done;
        if (step_start) begin cur_pos <= step_pos; checking <= 1'b1; end
        else if (checking && (&die_done) && !done_d && !step_start) begin
            checking <= 1'b0;
            steps_checked = steps_checked + 1;
            for (integer k = 0; k < N; k = k + 1)
                if (die_token[k*NW +: NW] != estep[cur_pos][32 +: 16] || die_val[k*32 +: 32] != estep[cur_pos][31:0]) begin
                    bad = bad + 1;
                    $display("STEP_MISMATCH die=%0d pos=%0d token=%0d logit=%08x expect token=%0d logit=%08x",
                             k, cur_pos, die_token[k*NW +: NW], die_val[k*32 +: 32], estep[cur_pos][32 +: 16], estep[cur_pos][31:0]);
                end
        end
    end

    // ------------------------------------------------------------ the host driver
    localparam integer SQ = 32'h1000, CQ = 32'h2000, PR = 32'h3000, MSI = 32'h4000;
    localparam integer CQ_LOG = 4;
    integer h_st = 0, h_pc = 0, wait_c = 0;
    reg [31:0] rd_val;
    reg        op_busy = 0, op_wr = 0;
    integer cq_i = 0;
    reg cq_ph = 1'b1;
    integer gen_got [0:NSLOT-1];
    integer last_got = 0, err_got = 0, cq_entries = 0;
    reg [31:0] fault_status_rd, fault_first_rd, sys_status_rd;
    reg [31:0] ctr [0:15];
    integer ci;
    // configuration writes: {addr, data}
    reg [44:0] cfg [0:15];
    initial begin
        cfg[0]  = {13'h1014, 32'hFFFF_FFFF};      // FAULT_MASK
        cfg[1]  = {13'h0010, SQ};                 // SQ_BASE lo
        cfg[2]  = {13'h0014, 32'd0};
        cfg[3]  = {13'h0018, 32'd3};              // SQ_LOG2: 8 entries (a ring of 2^n holds 2^n - 1)
        cfg[4]  = {13'h0024, CQ};
        cfg[5]  = {13'h0028, 32'd0};
        cfg[6]  = {13'h002C, CQ_LOG};             // 16 entries
        cfg[7]  = {13'h003C, 32'd3};              // IRQ_MASK
        cfg[8]  = {13'h0040, MSI};
        cfg[9]  = {13'h0044, 32'd0};
        cfg[10] = {13'h0048, 32'h0000_C0DE};
        cfg[11] = {13'h004C, 32'd1};              // MSI enable
        cfg[12] = {13'h0008, 32'd1};              // CTRL enable
    end
    task automatic axil_write(input [12:0] a, input [31:0] d);
        begin s_awaddr <= a; s_wdata <= d; s_awvalid <= 1'b1; s_wvalid <= 1'b1; op_busy <= 1'b1; op_wr <= 1'b1; end
    endtask
    task automatic axil_read(input [12:0] a);
        begin s_araddr <= a; s_arvalid <= 1'b1; op_busy <= 1'b1; op_wr <= 1'b0; end
    endtask
    reg [63:0] w0;
    integer u;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 10) por_n <= 1'b1;
        // AXI-Lite handshakes
        if (s_awvalid && s_awready) begin s_awvalid <= 1'b0; s_wvalid <= 1'b0; end
        if (op_busy && op_wr && s_bvalid) op_busy <= 1'b0;
        if (s_arvalid && s_arready) s_arvalid <= 1'b0;
        if (op_busy && !op_wr && s_rvalid) begin op_busy <= 1'b0; rd_val <= s_rdata; end
        if (!op_busy && !(s_awvalid || s_arvalid) && por_n) case (h_st)
            0: begin axil_read(13'h1004); h_st <= 1; end                       // poll SYS_STATUS
            1: begin
                if (rd_val[0]) begin sys_status_rd <= rd_val; h_pc <= 0; h_st <= 2;
                    $display("BOOT sys_ready at cycle %0d status=%08x boot_cycles", cyc, rd_val);
                end else if (rd_val[1]) begin
                    $display("BOOT_FAULT status=%08x", rd_val); h_st <= 90;
                end else h_st <= 0;
            end
            2: begin axil_write(cfg[h_pc][44:32], cfg[h_pc][31:0]);
                if (h_pc == 12) h_st <= 3; else h_pc <= h_pc + 1; end
            3: begin
                // the host writes one GENERATE descriptor per user and the shared prompt
                for (integer k = 0; k < 4; k = k + 1)
                    hmem[(PR >> 3) + k] = {prompt[4*k + 3], prompt[4*k + 2], prompt[4*k + 1], prompt[4*k]};
                for (u = 0; u < USERS; u = u + 1) begin
                    hmem[(SQ >> 3) + 4*u + 0] = {ngen[15:0], n_prompt[15:0], 16'h5A00 + u[15:0], 8'h01, 8'h01};
                    hmem[(SQ >> 3) + 4*u + 1] = PR;
                    hmem[(SQ >> 3) + 4*u + 2] = u;
                    hmem[(SQ >> 3) + 4*u + 3] = 64'd0;
                end
                axil_write(13'h001C, USERS);                                  // SQ_TAIL doorbell
                h_st <= 4;
            end
            4: if (irq) h_st <= 5;                                            // wait for the interrupt
            5: begin
                // consume every new completion (phase bit)
                w0 = hmem[(CQ >> 3) + 2*cq_i];
                if (w0[0] == cq_ph) begin
                    cq_entries = cq_entries + 1;
                    // kind 3 (error) or a last entry with status 7 (ST_FAULT: the step was aborted by a fault)
                    if (w0[2:1] == 2'd3 || w0[7:4] == 4'd7) begin
                        err_got = err_got + 1;
                        $display("CQ error slot=%0d tag=%04x status=%0d", w0[15:8], w0[31:16], w0[7:4]);
                    end else begin
                        if (w0[63:48] != gold[gen_got[w0[15:8]]] || w0[47:32] != n_prompt - 1 + gen_got[w0[15:8]] ||
                            w0[31:16] != 16'h5A00 + w0[15:8]) begin
                            bad = bad + 1;
                            $display("CQ_MISMATCH slot=%0d tag=%04x pos=%0d token=%0d expect %0d", w0[15:8], w0[31:16],
                                     w0[47:32], w0[63:48], gold[gen_got[w0[15:8]]]);
                        end
                        $display("CQ slot=%0d tag=%04x pos=%0d token=%0d kind=%0d cycle=%0d", w0[15:8], w0[31:16],
                                 w0[47:32], w0[63:48], w0[2:1], cyc);
                        gen_got[w0[15:8]] = gen_got[w0[15:8]] + 1;
                        if (w0[2:1] == 2'd2) last_got = last_got + 1;
                    end
                    if (cq_i == (1 << CQ_LOG) - 1) cq_ph <= ~cq_ph;
                    cq_i <= (cq_i + 1) % (1 << CQ_LOG);
                    // stay in 5 for the next entry
                end else h_st <= 6;
            end
            6: begin axil_write(13'h0030, cq_i); h_st <= 7; end                // CQ_HEAD doorbell
            7: begin axil_write(13'h0038, 32'd1); h_st <= 8; end               // IRQ_STATUS W1C
            8: h_st <= (last_got + err_got >= USERS || (expect_fault && fault_src != 0 && err_got > 0)) ? 10 : 9;
            9: h_st <= irq ? 5 : 9;
            10: begin axil_read(13'h1010); h_st <= 11; end                    // FAULT_STATUS
            11: begin fault_status_rd <= rd_val; axil_read(13'h1018); h_st <= 12; end
            12: begin fault_first_rd <= rd_val; ci <= 0; h_st <= 13; end
            13: begin axil_read(13'h1020 + 4 * ci); h_st <= 14; end           // counters
            14: begin ctr[ci] <= rd_val; if (ci == 15) h_st <= 20; else begin ci <= ci + 1; h_st <= 13; end end
            20: h_st <= 21;
            default: ;
        endcase
    end

    // ------------------------------------------------------------ end-of-run checks
    integer kv_bad = 0, vm_bad = 0, e, w, l, d2, kb, vb;
    reg [255:0] sec;
    reg [31:0] got;
    always @(posedge clk) if (h_st == 21) begin
        for (d2 = 0; d2 < N; d2 = d2 + 1) begin
            kb = 0; vb = 0;
            for (u = 0; u < USERS; u = u + 1)
                for (e = 0; e < KVW * W; e = e + 1) begin
                    w = e / W; l = e % W;
                    case (d2)
                        0: sec = g_hbm[0].u_hbm.mem[2 * (u * KVW + w) + l / 8];
                        1: sec = g_hbm[1].u_hbm.mem[2 * (u * KVW + w) + l / 8];
                        2: sec = g_hbm[2].u_hbm.mem[2 * (u * KVW + w) + l / 8];
                        default: sec = g_hbm[3].u_hbm.mem[2 * (u * KVW + w) + l / 8];
                    endcase
                    got = sec[32 * (l % 8) +: 32];
                    if (got !== ekv[d2 * KVW * W + e]) kb = kb + 1;
                end
            for (e = 0; e < VM_ELEMS; e = e + 1) begin
                case (d2)
                    0: got = dut.g_die[0].u_die.vm[e];
                    1: got = dut.g_die[1].u_die.vm[e];
                    2: got = dut.g_die[2].u_die.vm[e];
                    default: got = dut.g_die[3].u_die.vm[e];
                endcase
                if (got !== evm[d2 * VM_ELEMS + e]) vb = vb + 1;
            end
            $display("DIE %0d hbm_kv_mismatches=%0d vm_mismatches=%0d", d2, kb, vb);
            kv_bad = kv_bad + kb; vm_bad = vm_bad + vb;
        end
        $display("COUNTERS kv_fill_words=%0d,%0d,%0d,%0d kv_wb_sectors=%0d,%0d,%0d,%0d link_crc_err=%0d link_replays=%0d link_seq_drops=%0d boot_cycles=%0d steps=%0d die0_coll_cycles=%0d die0_busy=%0d die0_kvok_wait=%0d",
                 ctr[0], ctr[1], ctr[2], ctr[3], ctr[4], ctr[5], ctr[6], ctr[7], ctr[8], ctr[9], ctr[10], ctr[11], ctr[12],
                 ctr[13], ctr[14], ctr[15]);
        $display("FAULT_STATUS=%08x FAULT_FIRST=%08x fault_src=%08x msi=%0d cq_entries=%0d errors=%0d",
                 fault_status_rd, fault_first_rd, fault_src, n_msi, cq_entries, err_got);
        $display("SYS users=%0d me_cdc=%0d steps_checked=%0d mismatches=%0d kv_mismatches=%0d vm_mismatches=%0d collisions=%0d flip=%0d cycles=%0d ticks=%0d",
                 USERS, ME_CDC, steps_checked, bad, kv_bad, vm_bad, collisions, flip, cyc, tick);
        if (expect_fault != 0) begin
            if (fault_status_rd[expect_fault - 1] && fault_first_rd[31] && err_got > 0) $display("PASS");
            else $display("FAIL");
        end else if (bad == 0 && kv_bad == 0 && vm_bad == 0 && collisions == 0 && fault_status_rd == 0 && fault_src == 0 &&
                     last_got == USERS && err_got == 0 && steps_checked == USERS * (n_prompt + ngen - 1) &&
                     (flip == 0 || (ctr[8] > 0 && ctr[9] > 0)))
            $display("PASS");
        else $display("FAIL");
        $finish;
    end
    integer prog_every = 0;
    always @(posedge clk) if (prog_every > 0 && cyc % prog_every == 0) begin
        $display("PROGRESS cyc=%0d boot_state=%0d sys_ready=%0d h_st=%0d op_busy=%0d arv=%0d arr=%0d rv=%0d rd=%08x steps_checked=%0d fault_src=%08x",
                 cyc, dut.boot_state, sys_ready, h_st, op_busy, s_arvalid, s_arready, s_rvalid, rd_val, steps_checked, fault_src);
        $fflush();
    end
    always @(posedge clk) if (cyc > 60000000 || h_st == 90) begin
        $display("TIMEOUT h_st=%0d steps_checked=%0d fault_src=%08x", h_st, steps_checked, fault_src);
        $display("FAIL"); $finish;
    end

    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("FLIP=%d", flip)) flip = 0;
        if (!$value$plusargs("PROGRESS=%d", prog_every)) prog_every = 0;
        if (!$value$plusargs("USERS=%d", USERS)) USERS = 2;
        if (!$value$plusargs("HBM_TAG_FLIP=%d", tag_flip)) tag_flip = -1;
        if (!$value$plusargs("BREAK=%d", brk)) brk = -1;
        if (!$value$plusargs("EXPECT_FAULT=%d", expect_fault)) expect_fault = 0;   // FAULT_STATUS bit + 1
        $readmemh({dir, "/prompt.hex"}, prompt);
        $readmemh({dir, "/generated.hex"}, gold);
        $readmemh({dir, "/expect_steps.hex"}, estep);
        $readmemh({dir, "/expect_vm_d0.hex"}, evm, 0 * VM_ELEMS);
        $readmemh({dir, "/expect_vm_d1.hex"}, evm, 1 * VM_ELEMS);
        $readmemh({dir, "/expect_vm_d2.hex"}, evm, 2 * VM_ELEMS);
        $readmemh({dir, "/expect_vm_d3.hex"}, evm, 3 * VM_ELEMS);
        for (integer i = 0; i < N * KVW * W; i = i + 1) ekv[i] = 32'd0;
        $readmemh({dir, "/expect_kv_d0.hex"}, ekv, 0 * KVW * W);
        $readmemh({dir, "/expect_kv_d1.hex"}, ekv, 1 * KVW * W);
        $readmemh({dir, "/expect_kv_d2.hex"}, ekv, 2 * KVW * W);
        $readmemh({dir, "/expect_kv_d3.hex"}, ekv, 3 * KVW * W);
        for (integer i = 0; i < 4096; i = i + 1) hmem[i] = 64'd0;
        for (integer i = 0; i < NSLOT; i = i + 1) gen_got[i] = 0;
    end
endmodule
