`timescale 1ns/1ps
// Exactness of the margin-first loader host (ot_hfd_loader_host_m, make_loader_m.py) against the unchanged
// ot_hbm_accel_loader_host (ND 2): each sits in its own copy of one environment (AXI-lite programs on the upper BAR,
// a 64-bit host DMA memory, a per-die MREQ memory with random ready / response delay; host 1.0 ns, memory 0.833 ns).
// Programs per seed: LOAD (verify on/off, right / wrong expected CRC), STORE back, a misaligned descriptor.
// Compared: the ordered memory-write stream (die, address, data), the DMA write stream (address, data, strobes), and
// every CSR of every engine after each descriptor completes except CYCLES (the busy-cycle count, +2 by design).  `MARGIN selects the module of instance b; `HALF_B=<SHARED> makes it the half-rate adapter ot_hfd_loader_half, `DIV_B=<SHARED> the divided-clock CDC adapter ot_hfd_loader_div (L-DIV), `SAME_CLK ties clk_mem to clk_host.
module ldm_env #(parameter integer MARGIN = 0, parameter integer SEED = 1) (input wire clk_host, input wire clk_mem,
    input wire rst_n, output reg [63:0] mw_hash, output reg [63:0] dw_hash, output integer mw_n, output integer dw_n);
    localparam integer ND = 2;
    reg s_awvalid=0, s_wvalid=0, s_bready=0, s_arvalid=0, s_rready=0; reg [11:0] s_awaddr=0, s_araddr=0;
    reg [31:0] s_wdata=0; reg [3:0] s_wstrb=4'hf;
    wire s_awready, s_wready, s_bvalid, s_arready, s_rvalid; wire [31:0] s_rdata;
    wire h_awvalid, h_wvalid, h_bready, h_arvalid, h_rready; wire [11:0] h_awaddr, h_araddr; wire [31:0] h_wdata; wire [3:0] h_wstrb;
    wire m_arvalid, m_rready, m_awvalid, m_wvalid, m_wlast, m_bready; reg m_arready=0, m_rvalid=0, m_rlast=0, m_awready=0, m_wready=0, m_bvalid=0;
    wire [63:0] m_araddr, m_awaddr, m_wdata; wire [7:0] m_arlen, m_awlen, m_wstrb; wire [2:0] m_arsize, m_awsize; reg [63:0] m_rdata=0; reg [1:0] m_rresp=0, m_bresp=0;
    wire [ND-1:0] req_v, req_we, rsp_rdy; reg [ND-1:0] req_rdy=0, rsp_v=0, rsp_we=0; wire [ND*32-1:0] req_addr, req_wstrb; wire [ND*256-1:0] req_wdata; wire [ND*16-1:0] req_tag;
    reg [ND*16-1:0] rsp_tag=0; reg [ND*256-1:0] rsp_data=0; wire irq, fault;
    wire h_dma_arready, h_dma_rvalid, h_dma_rlast, h_dma_awready, h_dma_wready, h_dma_bvalid; wire [63:0] h_dma_rdata; wire [1:0] h_dma_rresp, h_dma_bresp;
    generate if (MARGIN) begin : g_m
`ifdef DIV_B
        ot_hfd_loader_div #(.ENABLE(1), .ND(ND), .SHARED(`DIV_B)) dut (
`elsif HALF_B
        ot_hfd_loader_half #(.ENABLE(1), .ND(ND), .SHARED(`HALF_B)) dut (
`else
        ot_hfd_loader_host_m #(.ENABLE(1), .ND(ND)) dut (
`endif.clk_host(clk_host),.rst_host_n(rst_n),.clk_mem(clk_mem),.rst_mem_n(rst_n),
         .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
         .s_bvalid(s_bvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),
         .h_awvalid(h_awvalid),.h_awready(1'b1),.h_awaddr(h_awaddr),.h_wvalid(h_wvalid),.h_wready(1'b1),.h_wdata(h_wdata),.h_wstrb(h_wstrb),.h_bvalid(1'b0),.h_bready(h_bready),
         .h_arvalid(h_arvalid),.h_arready(1'b1),.h_araddr(h_araddr),.h_rvalid(1'b0),.h_rready(h_rready),.h_rdata(32'd0),
         .h_dma_arvalid(1'b0),.h_dma_arready(h_dma_arready),.h_dma_araddr(64'd0),.h_dma_rvalid(h_dma_rvalid),.h_dma_rready(1'b1),.h_dma_rdata(h_dma_rdata),.h_dma_rresp(h_dma_rresp),.h_dma_rlast(h_dma_rlast),
         .h_dma_awvalid(1'b0),.h_dma_awready(h_dma_awready),.h_dma_awaddr(64'd0),.h_dma_wvalid(1'b0),.h_dma_wready(h_dma_wready),.h_dma_wdata(64'd0),.h_dma_wstrb(8'd0),.h_dma_bvalid(h_dma_bvalid),.h_dma_bready(1'b1),.h_dma_bresp(h_dma_bresp),
         .m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
         .m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),
         .m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),
         .req_v(req_v),.req_rdy(req_rdy),.req_we(req_we),.req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb(req_wstrb),.req_tag(req_tag),
         .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.irq(irq),.fault(fault));
    end else begin : g_o
        ot_hbm_accel_loader_host #(.ENABLE(1), .ND(ND)) dut (.clk_host(clk_host),.rst_host_n(rst_n),.clk_mem(clk_mem),.rst_mem_n(rst_n),
         .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),
         .s_bvalid(s_bvalid),.s_bready(s_bready),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),
         .h_awvalid(h_awvalid),.h_awready(1'b1),.h_awaddr(h_awaddr),.h_wvalid(h_wvalid),.h_wready(1'b1),.h_wdata(h_wdata),.h_wstrb(h_wstrb),.h_bvalid(1'b0),.h_bready(h_bready),
         .h_arvalid(h_arvalid),.h_arready(1'b1),.h_araddr(h_araddr),.h_rvalid(1'b0),.h_rready(h_rready),.h_rdata(32'd0),
         .h_dma_arvalid(1'b0),.h_dma_arready(h_dma_arready),.h_dma_araddr(64'd0),.h_dma_rvalid(h_dma_rvalid),.h_dma_rready(1'b1),.h_dma_rdata(h_dma_rdata),.h_dma_rresp(h_dma_rresp),.h_dma_rlast(h_dma_rlast),
         .h_dma_awvalid(1'b0),.h_dma_awready(h_dma_awready),.h_dma_awaddr(64'd0),.h_dma_wvalid(1'b0),.h_dma_wready(h_dma_wready),.h_dma_wdata(64'd0),.h_dma_wstrb(8'd0),.h_dma_bvalid(h_dma_bvalid),.h_dma_bready(1'b1),.h_dma_bresp(h_dma_bresp),
         .m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
         .m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),
         .m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),
         .req_v(req_v),.req_rdy(req_rdy),.req_we(req_we),.req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb(req_wstrb),.req_tag(req_tag),
         .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.irq(irq),.fault(fault));
    end endgenerate
    // ---- private random stream (same seed in both environments; draws are state-independent per cycle)
    reg [63:0] lfsr_h = 64'h9E3779B97F4A7C15 ^ SEED, lfsr_m = 64'hC2B2AE3D27D4EB4F ^ SEED;
    always @(posedge clk_host) lfsr_h <= {lfsr_h[62:0], lfsr_h[63] ^ lfsr_h[62] ^ lfsr_h[60] ^ lfsr_h[59]};
    always @(posedge clk_mem)  lfsr_m <= {lfsr_m[62:0], lfsr_m[63] ^ lfsr_m[62] ^ lfsr_m[60] ^ lfsr_m[59]};
    // ---- host DMA memory (64-bit AXI slave): word(a) = f(a) unless written
    reg [63:0] hmem [longint];
    function automatic [63:0] hword(input [63:0] a); begin
        if (hmem.exists(a)) hword = hmem[a]; else hword = {a[31:0] ^ 32'h5A5A1234, ~a[31:0] + 32'h3}; end endfunction
    reg [63:0] ar_q [$]; reg [8:0] ar_l [$]; reg [63:0] rd_a; reg [8:0] rd_left = 0; reg rd_busy = 0;
    always @(posedge clk_host) begin
        m_arready <= lfsr_h[3] | lfsr_h[7];
        if (m_arvalid && m_arready) begin ar_q.push_back(m_araddr); ar_l.push_back({1'b0, m_arlen} + 9'd1); end
        if (m_rvalid && m_rready) begin rd_a = rd_a + 8; rd_left = rd_left - 1; if (rd_left == 0) rd_busy = 0; end
        if (!rd_busy && ar_q.size() > 0) begin rd_a = ar_q.pop_front(); rd_left = ar_l.pop_front(); rd_busy = 1; end
        m_rvalid <= rd_busy && (lfsr_h[11] | lfsr_h[13] | lfsr_h[17]);
        m_rdata <= hword(rd_a); m_rlast <= rd_left == 1; m_rresp <= 2'b00;
    end
    reg [63:0] aw_q [$]; reg [63:0] wr_a; reg wr_busy = 0; integer b_pend = 0;
    always @(posedge clk_host) begin
        m_awready <= lfsr_h[21] | lfsr_h[23];
        if (m_awvalid && m_awready) aw_q.push_back(m_awaddr);
        if (!wr_busy && aw_q.size() > 0) begin wr_a = aw_q.pop_front(); wr_busy = 1; end
        m_wready <= wr_busy && (lfsr_h[29] | lfsr_h[31]);
        if (m_wvalid && m_wready) begin
            hmem[wr_a] = m_wdata; dw_hash = {dw_hash[62:0], dw_hash[63]} ^ wr_a ^ (m_wdata * 64'h100000001b3) ^ {56'd0, m_wstrb};
            dw_n = dw_n + 1; wr_a = wr_a + 8; if (m_wlast) begin wr_busy = 0; b_pend = b_pend + 1; end
        end
        if (m_bvalid && m_bready) b_pend = b_pend - 1;
        m_bvalid <= b_pend > (m_bvalid && m_bready ? 0 : 0) && lfsr_h[37];
        m_bresp <= 2'b00;
    end
    // ---- per-die MREQ memory (in-order responses, random delay)
    reg [255:0] dmem [ND][longint];
    reg [31:0] q_a [ND][$]; reg q_we [ND][$]; reg [15:0] q_t [ND][$]; integer q_age [ND][$];
    genvar d;
    for (d = 0; d < ND; d = d + 1) begin : g_mem
        always @(posedge clk_mem) begin
            req_rdy[d] <= lfsr_m[5 + d] | lfsr_m[9 + d];
            if (req_v[d] && req_rdy[d]) begin
                if (req_we[d]) begin
                    dmem[d][req_addr[d*32 +: 32]] = req_wdata[d*256 +: 256];
                    mw_hash = {mw_hash[62:0], mw_hash[63]} ^ {d[0], req_addr[d*32 +: 32]} ^ req_wdata[d*256 +: 64] ^ req_wdata[d*256 + 64 +: 64]
                              ^ req_wdata[d*256 + 128 +: 64] ^ req_wdata[d*256 + 192 +: 64] ^ {32'd0, req_wstrb[d*32 +: 32]};
                    mw_n = mw_n + 1;
                end
                q_a[d].push_back(req_addr[d*32 +: 32]); q_we[d].push_back(req_we[d]); q_t[d].push_back(req_tag[d*16 +: 16]);
                q_age[d].push_back(2 + lfsr_m[20 + 3*d +: 3]);
            end
            if (rsp_v[d] && rsp_rdy[d]) rsp_v[d] <= 1'b0;
            if (q_age[d].size() > 0 && q_age[d][0] > 0) q_age[d][0] = q_age[d][0] - 1;
            if ((!rsp_v[d] || rsp_rdy[d]) && q_a[d].size() > 0 && q_age[d][0] == 0) begin
                rsp_v[d] <= 1'b1; rsp_we[d] <= q_we[d][0]; rsp_tag[d*16 +: 16] <= q_t[d][0];
                rsp_data[d*256 +: 256] <= dmem[d].exists(q_a[d][0]) ? dmem[d][q_a[d][0]] : 256'd0;
                void'(q_a[d].pop_front()); void'(q_we[d].pop_front()); void'(q_t[d].pop_front()); void'(q_age[d].pop_front());
            end
        end
    end
    // ---- AXI-lite master
    task automatic wr(input [11:0] a, input [31:0] v);
        begin @(negedge clk_host); s_awaddr = a; s_wdata = v; s_awvalid = 1; s_wvalid = 1;
              do @(posedge clk_host); while (!(s_awready && s_wready)); @(negedge clk_host); s_awvalid = 0; s_wvalid = 0; s_bready = 1;
              do @(posedge clk_host); while (!s_bvalid); @(negedge clk_host); s_bready = 0; end endtask
    task automatic rd(input [11:0] a, output [31:0] v);
        begin @(negedge clk_host); s_araddr = a; s_arvalid = 1; do @(posedge clk_host); while (!s_arready); @(negedge clk_host); s_arvalid = 0;
              s_rready = 1; do @(posedge clk_host); while (!s_rvalid); v = s_rdata; @(negedge clk_host); s_rready = 0; end endtask
    function automatic [31:0] crc_fold(input [31:0] s, input [255:0] w); reg fb; integer i; begin crc_fold = s;
        for (i = 0; i < 256; i = i + 1) begin fb = crc_fold[31] ^ w[i]; crc_fold = {crc_fold[30:0], 1'b0} ^ (fb ? 32'h04C11DB7 : 32'h0); end end endfunction
    function automatic [31:0] img_crc(input [63:0] ha, input integer nsec); reg [31:0] c; integer s; reg [255:0] w; begin c = 32'hFFFFFFFF;
        for (s = 0; s < nsec; s = s + 1) begin w = {hword(ha + 32*s + 24), hword(ha + 32*s + 16), hword(ha + 32*s + 8), hword(ha + 32*s)}; c = crc_fold(c, w); end
        img_crc = c; end endfunction
    // one descriptor: program, start, wait done, read every CSR into the CSR log
    reg [31:0] csr_log [0:4095]; integer csr_n = 0;
    task automatic desc(input integer die, input integer store, input [63:0] ha, input [31:0] da, input [31:0] nb, input [31:0] ce, input integer ver);
        reg [11:0] b; reg [31:0] v; integer k;
        begin b = 12'h800 | (die << 8) | (store ? 12'h40 : 12'h0);
              wr(b | 12'h08, ha[31:0]); wr(b | 12'h0C, ha[63:32]); wr(b | 12'h10, da); wr(b | 12'h14, nb); wr(b | 12'h18, ce);
              wr(b | 12'h00, 32'h1 | (ver ? 32'h2 : 32'h0));
              v = 0; k = 0; do begin rd(b | 12'h04, v); k = k + 1; end while (!v[8] && k < 200000);
              for (k = 0; k <= 12'h28; k = k + 4) begin rd(b | k[11:0], v); if (k != 12'h28) begin csr_log[csr_n] = v; csr_n = csr_n + 1; end end
              wr(b | 12'h04, 32'h100); end endtask
    integer t, die, ns; reg [63:0] ha; reg [31:0] da, ce;
    initial begin mw_hash = 0; dw_hash = 0; mw_n = 0; dw_n = 0; end
    reg done = 0;
    initial begin @(posedge rst_n); repeat (5) @(posedge clk_host); run_programs(`NPROG); done = 1; end
    task automatic run_programs(input integer nprog);
        begin for (t = 0; t < nprog; t = t + 1) begin
            die = t % 2; ns = 1 + ((t * 37 + SEED) % 70); ha = 64'h1_0000_0000 + 64'h10000 * t; da = 32'h40000 * (t % 5);
            ce = img_crc(ha, ns) ^ ((t % 4 == 3) ? 32'h1 : 32'h0);                      // every 4th: wrong expected CRC
            desc(die, 0, ha, da, ns * 32, ce, (t % 3) != 0);                             // LOAD (verify 2 of 3)
            desc(die, 1, 64'h8_0000_0000 + 64'h10000 * t, da, ns * 32, ce, 0);         // STORE back
            if (t % 7 == 6) desc(die, 0, ha + 8, da, ns * 32, ce, 1);                    // misaligned: status 3
        end end endtask
endmodule

module tb_loader_m_equiv;
    reg clk_host = 0, clk_mem = 0, rst_n = 0;
    always #0.5 clk_host = ~clk_host;
`ifdef SAME_CLK
    always @(clk_host) clk_mem = clk_host;     // views agent: one die clock (ot_hfd_loader_half SHARED=1)
`else
    always #0.4165 clk_mem = ~clk_mem;
`endif
    wire [63:0] mwa, dwa, mwb, dwb; wire integer mna, dna, mnb, dnb;
    ldm_env #(.MARGIN(0), .SEED(`SEED)) a (.clk_host(clk_host), .clk_mem(clk_mem), .rst_n(rst_n), .mw_hash(mwa), .dw_hash(dwa), .mw_n(mna), .dw_n(dna));
    ldm_env #(.MARGIN(`MARGIN_B), .SEED(`SEED)) b (.clk_host(clk_host), .clk_mem(clk_mem), .rst_n(rst_n), .mw_hash(mwb), .dw_hash(dwb), .mw_n(mnb), .dw_n(dnb));
    integer i, bad = 0, st0 = 0, st1 = 0, st2 = 0, st3 = 0;
`ifdef LDM_TMO
    initial begin #(`LDM_TMO); $display("LDM_EQUIV TIMEOUT a.done=%0d b.done=%0d", a.done, b.done); $fatal(1, "FAIL"); end
`endif
    initial begin
        repeat (5) @(posedge clk_host); rst_n = 1;
        wait (a.done && b.done);
        repeat (50) @(posedge clk_host);
        if (a.csr_n != b.csr_n) bad = bad + 1;
        for (i = 0; i < a.csr_n; i = i + 1) begin
            if (i % 10 == 1) begin st0 += (a.csr_log[i][3:0] == 0); st1 += (a.csr_log[i][3:0] == 1); st2 += (a.csr_log[i][3:0] == 2); st3 += (a.csr_log[i][3:0] == 3); end
            if (a.csr_log[i] !== b.csr_log[i]) begin bad = bad + 1; if (bad < 6) $display("CSR %0d (%0d) %h vs %h", i, i % 10, a.csr_log[i], b.csr_log[i]); end
        end
        if (mwa !== mwb || mna != mnb) begin bad = bad + 1; $display("MREQ write stream differs %0d %0d", mna, mnb); end
        if (dwa !== dwb || dna != dnb) begin bad = bad + 1; $display("DMA write stream differs %0d %0d", dna, dnb); end
        $display("LDM_EQUIV descriptors=%0d mreq_writes=%0d dma_writes=%0d status0=%0d status1=%0d status2=%0d status3=%0d mismatches=%0d",
                 a.csr_n / 10, mna, dna, st0, st1, st2, st3, bad);
        if (bad || st0 == 0 || st1 == 0) $fatal(1, "FAIL"); $finish;
    end
endmodule
