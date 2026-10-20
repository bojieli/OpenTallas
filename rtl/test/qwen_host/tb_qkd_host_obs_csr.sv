`timescale 1ns/1ps
// KV-BIND5-OBS 10-19: behavioural bench of qkd_host_obs_csr (HOST observation window between the packet AXI master and
// the CSR slave).  Checks: (1) CAPTURE snapshots every obs bit exactly at the write edge, later obs changes are not seen;
// (2) the sticky flt vector keeps a 1-cycle pulse until CLEAR; (3) every window word reads back at a FIXED 3 edges after
// the AR handshake; (4) CTRL / NB words; (5) pass-through reads and writes outside the window reach the CSR slave with
// its own data; (6) random interleaving of window / CSR transactions.  PASS line: "TB_QKD_HOST_OBS_CSR PASS".
module tb_qkd_host_obs_csr;
`ifndef OBS_NB
`define OBS_NB 1335
`endif
`ifndef OBS_NF
`define OBS_NF 71
`endif
    // default = the generated HOST root's window (host_obs_map.json: 1335 obs + 71 sticky bits, 44 words)
    localparam integer NB = `OBS_NB, NF = `OBS_NF, NT = NB + NF, NW = (NT + 31) / 32;
`ifndef OBS_MUT
`define OBS_MUT 0
`endif
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    reg [NB-1:0] obs;
    reg [NF-1:0] flt;
    reg u_awvalid = 0, u_wvalid = 0, u_bready = 1, u_arvalid = 0, u_rready = 1;
    reg [12:0] u_awaddr = 0, u_araddr = 0;
    reg [31:0] u_wdata = 0;
    reg [3:0] u_wstrb = 4'hf;
    wire u_awready, u_wready, u_bvalid, u_arready, u_rvalid;
    wire [1:0] u_bresp, u_rresp;
    wire [31:0] u_rdata;
    wire d_awvalid, d_wvalid, d_bready, d_arvalid, d_rready;
    wire [12:0] d_awaddr, d_araddr;
    wire [31:0] d_wdata;
    wire [3:0] d_wstrb;
    // CSR slave model: one transaction at a time, read data = {16'hC5C5, 3'b0, addr}, 1-edge accept, 2-edge response
    reg d_bvalid = 0, d_rvalid = 0;
    reg [31:0] d_rdata = 0;
    reg d_rbusy = 0, d_wbusy = 0;
    wire d_arready = !d_rbusy, d_awready = !d_wbusy && d_wvalid, d_wready = !d_wbusy && d_awvalid;
    integer d_writes = 0, d_aw_hs = 0;
    always @(posedge clk) begin
        if (d_arvalid && d_arready) begin d_rbusy <= 1; d_rdata <= {16'hC5C5, 3'b0, d_araddr}; end
        if (d_rbusy && !d_rvalid) d_rvalid <= 1;
        if (d_rvalid && d_rready) begin d_rvalid <= 0; d_rbusy <= 0; end
        if (d_awvalid && d_wvalid && d_awready) begin d_wbusy <= 1; d_aw_hs = d_aw_hs + 1; end
        if (d_wbusy && !d_bvalid) d_bvalid <= 1;
        if (d_bvalid && d_bready) begin d_bvalid <= 0; d_wbusy <= 0; d_writes = d_writes + 1; end
    end
    qkd_host_obs_csr #(.NB(NB), .NF(NF), .MUT(`OBS_MUT)) dut(.clk(clk), .rst_n(rst_n), .obs(obs), .flt(flt),
        .u_awvalid(u_awvalid), .u_awready(u_awready), .u_awaddr(u_awaddr), .u_wvalid(u_wvalid), .u_wready(u_wready),
        .u_wdata(u_wdata), .u_wstrb(u_wstrb), .u_bvalid(u_bvalid), .u_bready(u_bready), .u_bresp(u_bresp),
        .u_arvalid(u_arvalid), .u_arready(u_arready), .u_araddr(u_araddr), .u_rvalid(u_rvalid), .u_rready(u_rready),
        .u_rdata(u_rdata), .u_rresp(u_rresp),
        .d_awvalid(d_awvalid), .d_awready(d_awready), .d_awaddr(d_awaddr), .d_wvalid(d_wvalid), .d_wready(d_wready),
        .d_wdata(d_wdata), .d_wstrb(d_wstrb), .d_bvalid(d_bvalid), .d_bready(d_bready), .d_bresp(2'b00),
        .d_arvalid(d_arvalid), .d_arready(d_arready), .d_araddr(d_araddr), .d_rvalid(d_rvalid), .d_rready(d_rready),
        .d_rdata(d_rdata), .d_rresp(2'b00));

    // reference model (independent of the RTL structure): live flt seen one edge late, sticky OR, snapshot at the
    // CAPTURE handshake edge
    reg [NF-1:0] r_fq = 0, r_st = 0;
    reg [NT-1:0] r_snap = 0;
    reg [15:0] r_ncap = 0;
    wire wr_hs = u_awvalid && u_wvalid && u_awready && u_wready;
    wire wr_ctrl = wr_hs && u_awaddr == 13'h1800;
    reg r_cap = 0, r_clr = 0;          // CAPTURE / CLEAR act one edge after the OBS_CTRL write handshake
    always @(posedge clk) if (rst_n) begin
        r_cap <= wr_ctrl && u_wdata[0];
        r_clr <= wr_ctrl && u_wdata[1];
        r_fq <= flt;
        r_st <= r_clr ? r_fq : (r_st | r_fq);
        if (r_cap) r_snap <= {r_st | r_fq, obs};
        if (wr_ctrl && u_wdata[0]) r_ncap <= r_ncap + 1;
    end
    integer errors = 0, cyc = 0, lat;
    always @(posedge clk) cyc <= cyc + 1;
    task automatic axi_write(input [12:0] a, input [31:0] d);
        begin
            // ready is sampled mid-cycle after the combinational split settled (#0.05): the next posedge is the handshake
            @(negedge clk); u_awaddr = a; u_wdata = d; u_awvalid = 1; u_wvalid = 1; #0.05;
            while (!(u_awready && u_wready)) begin @(negedge clk); #0.05; end
            @(negedge clk); u_awvalid = 0; u_wvalid = 0;
            while (!u_bvalid) @(negedge clk);
        end
    endtask
    task automatic axi_read(input [12:0] a, output [31:0] d, output integer l);
        integer c0;
        begin
            @(negedge clk); u_araddr = a; u_arvalid = 1; #0.05;
            while (!u_arready) begin @(negedge clk); #0.05; end
            c0 = cyc; @(negedge clk); u_arvalid = 0;
            while (!u_rvalid) @(negedge clk);
            d = u_rdata; l = cyc - c0;
        end
    endtask
    reg [31:0] rd, exp;
    integer i, k, it;
    initial begin
        obs = 0; flt = 0;
        repeat (5) @(negedge clk); rst_n = 1;
        for (it = 0; it < 6; it = it + 1) begin
            // a 1-cycle fault pulse well before the capture (sticky must keep it)
            @(negedge clk); flt = 0; flt[(it * 13) % NF] = 1'b1; @(negedge clk); flt = 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(negedge clk);
                for (i = 0; i < NB; i = i + 32) obs[i +: 32] = $urandom;
            end
            axi_write(13'h1800, 32'h1);                                  // CAPTURE (snapshot 1 edge after the handshake)
            @(negedge clk);
            for (i = 0; i < NB; i = i + 32) obs[i +: 32] = $urandom;      // later changes must not be seen
            for (k = 0; k < NW; k = k + 1) begin
                axi_read(13'h1900 + 4 * k, rd, lat);
                exp = (32 * k + 32 <= NT) ? r_snap[32 * k +: 32] : (r_snap >> (32 * k));
                if (rd !== exp) begin errors = errors + 1; if (errors < 10) $display("ERR word %0d got %h exp %h", k, rd, exp); end
                if (lat != 3) begin errors = errors + 1; if (errors < 10) $display("ERR word %0d latency %0d != 3", k, lat); end
                if (k % 7 == 3) begin                                      // interleaved CSR read (pass-through)
                    axi_read(13'h1004 + 4 * k, rd, lat);
                    if (rd !== {16'hC5C5, 3'b0, 13'h1004 + 13'(4 * k)}) begin errors = errors + 1; $display("ERR passthru %h", rd); end
                end
            end
            axi_read(13'h1800, rd, lat);
            if (rd !== {8'h0B, 8'(NW), r_ncap}) begin errors = errors + 1; $display("ERR ctrl %h", rd); end
            axi_read(13'h1804, rd, lat);
            if (rd !== {16'(NF), 16'(NB)}) begin errors = errors + 1; $display("ERR nb %h", rd); end
            axi_write(13'h1008 + 4 * it, 32'h5);                          // pass-through write reaches the CSR
            if (it % 2) axi_write(13'h1800, 32'h2);                      // CLEAR sticky
        end
        if (d_writes != 6) begin errors = errors + 1; $display("ERR pass-through writes %0d (aw handshakes %0d)", d_writes, d_aw_hs); end
        if (errors == 0) $display("TB_QKD_HOST_OBS_CSR PASS words=%0d captures=%0d", NW, r_ncap);
        else $display("TB_QKD_HOST_OBS_CSR FAIL errors=%0d", errors);
        $finish;
    end
endmodule
