`timescale 1ns/1ps
// Host -> HBM loader bench (HBM accelerator die, 2026-10-04).
// Host memory: an AXI4 slave with a fixed read latency (+HLAT host cycles, PCIe-like) and in-order 256-bit beats,
// holding the host image (+HOSTIMG, one 32-byte sector per hex line).  Memory: the die memory system
// ot_gpu_memsys (crossbar, NS = 2 L2 slices, 2 HBM partitions around the timing-faithful HBM model, MEM_WORDS
// per partition), with NO load-time image: the model starts zeroed and only the loader writes it.
// Expected: the partitions' load-time images of the DeepSeek-V4.1 HBM system run (+EXP0 / +EXP1, the
// $readmemh files the system bench uses), restricted to the loaded windows.  After the transfers the bench
// compares EVERY model word of both partitions: inside a loaded window it must equal the expected image, outside
// it must still be zero.
// Transfers (+NT, then per transfer +T<i>=<host_sector>,<die_byte_addr>,<bytes>,<crc32>,<verify>):
//   the bench programs the AXI-Lite registers, starts, waits for irq, and checks STATUS == 0, CRC_GOT == VCRC_GOT
//   (verify) == the expected CRC, SECTORS == bytes / 32.  Negative cases follow: misaligned size (status 3),
//   one corrupted beat (status 1), an AXI SLVERR beat (status 4).
module tb_hbm_accel_loader;
    parameter integer MEM_WORDS = 2097152;
    parameter integer HWORDS    = 524288;
    parameter real    HCLK      = 1.0;            // host clock period (ns)
    reg clk_host = 0, clk_mem = 0, rst_host_n = 0, rst_mem_n = 0;
    always #(HCLK / 2.0) clk_host = ~clk_host;
    always #0.5 clk_mem = ~clk_mem;               // ot_gpu_memsys CLK_PS 1000
    integer HLAT = 400;
    // ---- AXI-Lite master ----
    reg s_awvalid = 0, s_wvalid = 0, s_bready = 1, s_arvalid = 0, s_rready = 1;
    reg [11:0] s_awaddr = 0, s_araddr = 0; reg [31:0] s_wdata = 0;
    wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid; wire [31:0] s_rdata;
    // ---- AXI read master <-> host memory ----
    wire m_arvalid; reg m_arready = 1; wire [63:0] m_araddr; wire [7:0] m_arlen; wire [2:0] m_arsize; wire [1:0] m_arburst;
    reg m_rvalid = 0; wire m_rready; reg [255:0] m_rdata = 0; reg [1:0] m_rresp = 0; reg m_rlast = 0;
    wire irq;
    // ---- MREQ ----
    wire req_v, req_rdy, req_we, rsp_v, rsp_rdy, rsp_we, mfault; wire [31:0] req_addr, req_wstrb; wire [255:0] req_wdata, rsp_data;
    wire [15:0] req_tag, rsp_tag;
    ot_hbm_accel_loader #(.ENABLE(1)) dut (
        .clk_host(clk_host), .rst_host_n(rst_host_n),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr), .s_wvalid(s_wvalid), .s_wready(s_wready),
        .s_wdata(s_wdata), .s_bvalid(s_bvalid), .s_bready(s_bready), .s_arvalid(s_arvalid), .s_arready(s_arready),
        .s_araddr(s_araddr), .s_rvalid(s_rvalid), .s_rready(s_rready), .s_rdata(s_rdata),
        .m_arvalid(m_arvalid), .m_arready(m_arready), .m_araddr(m_araddr), .m_arlen(m_arlen), .m_arsize(m_arsize),
        .m_arburst(m_arburst), .m_rvalid(m_rvalid), .m_rready(m_rready), .m_rdata(m_rdata), .m_rresp(m_rresp),
        .m_rlast(m_rlast), .irq(irq),
        .clk_mem(clk_mem), .rst_mem_n(rst_mem_n), .req_v(req_v), .req_rdy(req_rdy), .req_we(req_we),
        .req_addr(req_addr), .req_wdata(req_wdata), .req_wstrb(req_wstrb), .req_tag(req_tag),
        .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_we(rsp_we), .rsp_data(rsp_data));
    ot_gpu_memsys #(.ENABLE(1), .NC(1), .NS(2), .NPC(2), .MEM_WORDS(MEM_WORDS), .CLK_PS(1000)) u_mem (
        .clk(clk_mem), .rst_n(rst_mem_n), .req_v(req_v), .req_rdy(req_rdy), .req_we(req_we), .req_addr(req_addr),
        .req_wdata(req_wdata), .req_wstrb(req_wstrb), .req_tag(req_tag), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy),
        .rsp_tag(rsp_tag), .rsp_we(rsp_we), .rsp_data(rsp_data), .fault(mfault));

    // ---- host memory: AXI4 read slave, fixed latency, in order ----
    reg [255:0] hmem [0:HWORDS-1];
    localparam integer QN = 64;
    reg [63:0] q_addr [0:QN-1]; reg [8:0] q_len [0:QN-1]; longint q_t [0:QN-1];
    integer q_wr = 0, q_rd = 0, beat_i = 0;
    longint hcyc = 0;
    integer corrupt_at = -1, slverr_at = -1, beats_total = 0;
    always @(posedge clk_host) begin
        hcyc <= hcyc + 1;
        if (m_arvalid && m_arready) begin
            q_addr[q_wr % QN] = m_araddr; q_len[q_wr % QN] = {1'b0, m_arlen} + 9'd1; q_t[q_wr % QN] = hcyc + HLAT;
            q_wr = q_wr + 1;
        end
        m_arready <= (q_wr - q_rd) < QN - 1;
        if (m_rvalid && m_rready) begin
            beat_i = beat_i + 1; beats_total = beats_total + 1;
            if (beat_i == q_len[q_rd % QN]) begin q_rd = q_rd + 1; beat_i = 0; end
        end
        if (q_rd != q_wr && hcyc >= q_t[q_rd % QN]) begin
            m_rvalid <= 1;
            m_rdata <= hmem[(q_addr[q_rd % QN] >> 5) + beat_i];
            if (beats_total == corrupt_at) m_rdata <= hmem[(q_addr[q_rd % QN] >> 5) + beat_i] ^ 256'h1;
            m_rresp <= (beats_total == slverr_at) ? 2'b10 : 2'b00;
            m_rlast <= beat_i == q_len[q_rd % QN] - 1;
        end else begin
            m_rvalid <= 0; m_rlast <= 0;
        end
    end

    always @(posedge clk_host) if (hcyc % 2000000 == 0 && hcyc > 0)
        $display("HB hcyc=%0d busy=%b ar_sec=%0d rx_sec=%0d out=%0d ms=%0d w_idx=%0d w_ack=%0d r_idx=%0d f_idx=%0d req_v=%b req_rdy=%b",
                 hcyc, dut.g_on.busy, dut.g_on.ar_sec, dut.g_on.rx_sec, dut.g_on.out_bursts, dut.g_on.ms,
                 dut.g_on.w_idx, dut.g_on.w_ack, dut.g_on.r_idx, dut.g_on.f_idx, req_v, req_rdy);
    // ---- register access ----
    task automatic wreg(input [11:0] a, input [31:0] d);
        @(negedge clk_host); s_awvalid = 1; s_wvalid = 1; s_awaddr = a; s_wdata = d;
        @(posedge clk_host); while (!(s_awready && s_wready)) @(posedge clk_host);
        @(negedge clk_host); s_awvalid = 0; s_wvalid = 0;
    endtask
    task automatic rreg(input [11:0] a, output [31:0] d);
        @(negedge clk_host); s_arvalid = 1; s_araddr = a;
        @(posedge clk_host); while (!s_arready) @(posedge clk_host);
        @(negedge clk_host); s_arvalid = 0;
        while (!s_rvalid) @(posedge clk_host);
        d = s_rdata;
        @(posedge clk_host);
    endtask
    integer fails = 0;
    task automatic transfer(input longint hsec, input [31:0] daddr, input [31:0] bytes, input [31:0] crc,
                            input integer verify, input integer expect_status, input string name);
        reg [31:0] st, cg, vg, ns, cy;
        longint t0;
        wreg(12'h08, 32'(hsec << 5)); wreg(12'h0C, 32'((hsec << 5) >> 32)); wreg(12'h10, daddr);
        wreg(12'h14, bytes); wreg(12'h18, crc);
        t0 = hcyc;
        wreg(12'h00, {30'd0, verify[0], 1'b1});
        @(posedge clk_host); while (!irq) @(posedge clk_host);
        rreg(12'h04, st); rreg(12'h1C, cg); rreg(12'h20, vg); rreg(12'h24, ns); rreg(12'h28, cy);
        $display("XFER %s status=%0d crc_got=%08h vcrc_got=%08h crc_exp=%08h sectors=%0d cycles=%0d bytes=%0d verify=%0d",
                 name, st[3:0], cg, vg, crc, ns, cy, bytes, verify);
        if (st[3:0] != expect_status[3:0]) begin $display("FAIL %s: status %0d, expected %0d", name, st[3:0], expect_status); fails = fails + 1; end
        if (expect_status == 0 && (cg != crc || (verify && vg != crc) || ns != bytes / 32)) begin
            $display("FAIL %s: crc/sectors", name); fails = fails + 1;
        end
        wreg(12'h04, 32'h100);
    endtask

    // ---- expected images and the full-memory comparison ----
    reg [255:0] exp0 [0:MEM_WORDS-1];
    reg [255:0] exp1 [0:MEM_WORDS-1];
    integer NT = 0;
    longint t_hsec [0:7]; longint t_daddr [0:7]; longint t_bytes [0:7]; longint t_crc [0:7]; integer t_ver [0:7];
    function automatic bit in_window(input integer part, input integer w);
        // partition-local sector w of slice `part` -> die-global byte address (tools/gpu_sys/mem_image.py die_address)
        longint local_b, a;
        local_b = longint'(w) << 5;
        a = ((local_b >> 7) << 8) | (longint'(part) << 7) | (local_b & 127);
        in_window = 0;
        for (integer i = 0; i < NT; i = i + 1)
            if (a >= t_daddr[i] && a < t_daddr[i] + t_bytes[i]) in_window = 1;
    endfunction
    initial begin
        reg [8*512-1:0] fn;
        reg [8*256-1:0] spec;
        reg [31:0] tmp;
        integer i, w, bad, loaded, nz, a, b, c, d, e;
        void'($value$plusargs("HLAT=%d", HLAT));
        if (!$value$plusargs("HOSTIMG=%s", fn)) $fatal(1, "+HOSTIMG required");
        $readmemh(fn, hmem);
        for (w = 0; w < MEM_WORDS; w = w + 1) begin exp0[w] = 0; exp1[w] = 0; end
        if (!$value$plusargs("EXP0=%s", fn)) $fatal(1, "+EXP0 required");
        $readmemh(fn, exp0);
        if (!$value$plusargs("EXP1=%s", fn)) $fatal(1, "+EXP1 required");
        $readmemh(fn, exp1);
        void'($value$plusargs("NT=%d", NT));
        for (i = 0; i < NT; i = i + 1) begin
            if (!$value$plusargs($sformatf("T%0d=%%s", i), spec)) $fatal(1, "missing +T%0d", i);
            if ($sscanf(spec, "%d:%d:%d:%h:%d", a, b, c, d, e) != 5) $fatal(1, "bad +T%0d", i);
            t_hsec[i] = a; t_daddr[i] = longint'(unsigned'(b)); t_bytes[i] = c; t_crc[i] = longint'(unsigned'(d)); t_ver[i] = e;
        end
        repeat (5) @(posedge clk_host);
        rst_host_n = 1; rst_mem_n = 1;
        repeat (20) @(posedge clk_host);
        // negative: misaligned size
        transfer(0, 32'h0, 32'd31, 32'h0, 0, 3, "misaligned");
        for (i = 0; i < NT; i = i + 1)
            transfer(t_hsec[i], 32'(t_daddr[i]), 32'(t_bytes[i]), 32'(t_crc[i]), t_ver[i], 0, $sformatf("T%0d", i));
        // full comparison of both partitions
        bad = 0; loaded = 0; nz = 0;
        for (w = 0; w < MEM_WORDS; w = w + 1) begin
            if (in_window(0, w)) begin
                loaded = loaded + 1; if (exp0[w] != 0) nz = nz + 1;
                if (u_mem.g_on.g_s[0].u_part.g_on.u_model.mem[w] !== exp0[w]) begin
                    if (bad < 5) $display("MISMATCH p0 w=%0d got %h exp %h", w, u_mem.g_on.g_s[0].u_part.g_on.u_model.mem[w], exp0[w]);
                    bad = bad + 1; end
            end else if (u_mem.g_on.g_s[0].u_part.g_on.u_model.mem[w] !== 256'd0) begin
                if (bad < 5) $display("STRAY p0 w=%0d", w); bad = bad + 1; end
            if (in_window(1, w)) begin
                loaded = loaded + 1; if (exp1[w] != 0) nz = nz + 1;
                if (u_mem.g_on.g_s[1].u_part.g_on.u_model.mem[w] !== exp1[w]) begin
                    if (bad < 5) $display("MISMATCH p1 w=%0d got %h exp %h", w, u_mem.g_on.g_s[1].u_part.g_on.u_model.mem[w], exp1[w]);
                    bad = bad + 1; end
            end else if (u_mem.g_on.g_s[1].u_part.g_on.u_model.mem[w] !== 256'd0) begin
                if (bad < 5) $display("STRAY p1 w=%0d", w); bad = bad + 1; end
        end
        $display("COMPARE words=%0d loaded=%0d nonzero_loaded=%0d mismatches=%0d memsys_fault=%b", 2 * MEM_WORDS, loaded, nz, bad, mfault);
        if (bad != 0 || mfault) fails = fails + 1;
        // negative: one corrupted beat (payload CRC) and one SLVERR beat, on a 4 KB transfer of the first window
        if (NT > 0) begin
            if (!$value$plusargs("CRC4K=%h", tmp)) $fatal(1, "+CRC4K required");
            transfer(t_hsec[0], 32'(t_daddr[0]), 32'd4096, tmp, 1, 0, "clean_4k");
            corrupt_at = beats_total + 37;
            transfer(t_hsec[0], 32'(t_daddr[0]), 32'd4096, tmp, 0, 1, "corrupt_beat");
            corrupt_at = -1; slverr_at = beats_total + 5;
            transfer(t_hsec[0], 32'(t_daddr[0]), 32'd4096, tmp, 0, 4, "axi_slverr");
        end
        if (fails == 0) $display("PASS transfers=%0d", NT);
        else $display("FAILED %0d", fails);
        $finish;
    end
endmodule
