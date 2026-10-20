`timescale 1ns/1ps
// KV-FRAMEPINS 10-20: die-path bench of the five KV-die observations that had no frame pin group (bind v2 OUTPUT_OPEN):
// dcal adm_done / cal_ready / running / layer and the D2D end's recovery_cycles -> kv_oneway relayed die buses
// (ks_obs_dcal 3 b, ks_obs_dlay 6 b, ks_obs_rcy 32 b; the relay stages are the closed qkd_rlys_36 standard) -> the
// OBSX HOST root's inputs obs_dcal_* / obs_d2d_recovery_cycles -> the HOST observation window qkd_host_obs_csr at the
// OBSX shape (host_obs_map_x.json: 1376 obs + 71 sticky bits, ext LSB 1335).
// Checks: after every CAPTURE the window words carry, at the map's bit positions, EXACTLY the source values of
// (relay stages) edges before the snapshot edge (the priced observation lag; all bits of a bus equally late = never torn),
// the 1,335 HOST bits unchanged around them, fixed 3-edge window reads, CSR pass-through.
// PASS line "TB_KV_OBSX_PATH PASS".  Mutants: OBS_MUT 1..4 (window, see qkd_host_obs_csr), PATH_MUT 5 = ext wired one bit
// low (the old map / a wrong concat), PATH_MUT 6 = one relay stage more than priced on ks_obs_rcy.
module tb_kv_obsx_path;
`ifndef OBS_NB
`define OBS_NB 1376
`endif
`ifndef OBS_NF
`define OBS_NF 71
`endif
`ifndef EXT_LSB
`define EXT_LSB 1335
`endif
`ifndef RLY_DOB
`define RLY_DOB 3
`endif
`ifndef RLY_LAY
`define RLY_LAY 3
`endif
`ifndef RLY_RCY
`define RLY_RCY 4
`endif
`ifndef OBS_MUT
`define OBS_MUT 0
`endif
`ifndef PATH_MUT
`define PATH_MUT 0
`endif
    localparam integer NB = `OBS_NB, NF = `OBS_NF, NT = NB + NF, NW = (NT + 31) / 32, EL = `EXT_LSB;
    localparam integer KD = `RLY_DOB, KL = `RLY_LAY, KR = `RLY_RCY;
    localparam integer KR_ACT = KR + ((`PATH_MUT == 6) ? 1 : 0);
    localparam integer EL_ACT = EL - ((`PATH_MUT == 5) ? 1 : 0);
    initial if (EL + 41 != NB) $fatal(1, "tb_kv_obsx_path: EXT_LSB + 41 != OBS_NB (map mismatch)");
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;
    // ---- die sources (dcal status levels / run index, D2D recovery cycle counter): registered outputs on ck
    reg s_adm = 0, s_rdy = 0, s_run = 0;
    reg [5:0] s_lay = 0;
    reg [31:0] s_rcy = 0;
    always @(posedge clk) if (rst_n) begin
        s_adm <= $urandom; s_rdy <= $urandom; s_run <= $urandom; s_lay <= s_lay + 6'($urandom % 3);
        s_rcy <= ($urandom % 5 == 0) ? 32'($urandom) : s_rcy + 1;
    end
    // ---- relayed die buses: chains of the closed relay standard (one register a stage, no reset)
    wire [35:0] d_ch [0:KD];
    wire [35:0] l_ch [0:KL];
    wire [35:0] r_ch [0:KR_ACT];
    assign d_ch[0] = {33'd0, s_run, s_rdy, s_adm};
    assign l_ch[0] = {30'd0, s_lay};
    assign r_ch[0] = {4'd0, s_rcy};
    genvar g;
    generate
        for (g = 0; g < KD; g = g + 1) begin : g_d qkd_rlys_36 u(.ck(clk), .a(d_ch[g]), .b(d_ch[g + 1])); end
        for (g = 0; g < KL; g = g + 1) begin : g_l qkd_rlys_36 u(.ck(clk), .a(l_ch[g]), .b(l_ch[g + 1])); end
        for (g = 0; g < KR_ACT; g = g + 1) begin : g_r qkd_rlys_36 u(.ck(clk), .a(r_ch[g]), .b(r_ch[g + 1])); end
    endgenerate
    // ---- the OBSX root's window bus: {obs_d2d_recovery_cycles, obs_dcal_layer, running, cal_ready, adm_done, HOST 1335}
    reg [EL-1:0] host_obs;
    wire [40:0] ext = {r_ch[KR_ACT][31:0], l_ch[KL][5:0], d_ch[KD][2:0]};
    wire [NB-1:0] obs_dut;
    generate if (`PATH_MUT == 5) begin : g_m5
        assign obs_dut = {1'b0, ext, host_obs[EL-2:0]};        // ext one bit low (host bit EL-1 overwritten)
    end else begin : g_ok
        assign obs_dut = {ext, host_obs};
    end endgenerate
    reg [NF-1:0] flt = 0;
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
    reg d_bvalid = 0, d_rvalid = 0;
    reg [31:0] d_rdata = 0;
    reg d_rbusy = 0, d_wbusy = 0;
    wire d_arready = !d_rbusy, d_awready = !d_wbusy && d_wvalid, d_wready = !d_wbusy && d_awvalid;
    always @(posedge clk) begin
        if (d_arvalid && d_arready) begin d_rbusy <= 1; d_rdata <= {16'hC5C5, 3'b0, d_araddr}; end
        if (d_rbusy && !d_rvalid) d_rvalid <= 1;
        if (d_rvalid && d_rready) begin d_rvalid <= 0; d_rbusy <= 0; end
        if (d_awvalid && d_wvalid && d_awready) d_wbusy <= 1;
        if (d_wbusy && !d_bvalid) d_bvalid <= 1;
        if (d_bvalid && d_bready) begin d_bvalid <= 0; d_wbusy <= 0; end
    end
    qkd_host_obs_csr #(.NB(NB), .NF(NF), .MUT(`OBS_MUT)) dut(.clk(clk), .rst_n(rst_n), .obs(obs_dut), .flt(flt),
        .u_awvalid(u_awvalid), .u_awready(u_awready), .u_awaddr(u_awaddr), .u_wvalid(u_wvalid), .u_wready(u_wready),
        .u_wdata(u_wdata), .u_wstrb(u_wstrb), .u_bvalid(u_bvalid), .u_bready(u_bready), .u_bresp(u_bresp),
        .u_arvalid(u_arvalid), .u_arready(u_arready), .u_araddr(u_araddr), .u_rvalid(u_rvalid), .u_rready(u_rready),
        .u_rdata(u_rdata), .u_rresp(u_rresp),
        .d_awvalid(d_awvalid), .d_awready(d_awready), .d_awaddr(d_awaddr), .d_wvalid(d_wvalid), .d_wready(d_wready),
        .d_wdata(d_wdata), .d_wstrb(d_wstrb), .d_bvalid(d_bvalid), .d_bready(d_bready), .d_bresp(2'b00),
        .d_arvalid(d_arvalid), .d_arready(d_arready), .d_araddr(d_araddr), .d_rvalid(d_rvalid), .d_rready(d_rready),
        .d_rdata(d_rdata), .d_rresp(2'b00));
    // ---- reference (independent of the relay / window structure): source history by edge, snapshot edge
    integer cyc = 0;
    reg [40:0] hist [0:4095];
    reg [EL-1:0] hhist [0:4095];
    always @(posedge clk) begin
        hist[cyc % 4096] <= {s_rcy, s_lay, s_run, s_rdy, s_adm};   // pre-edge value at edge cyc
        hhist[cyc % 4096] <= host_obs;
        cyc <= cyc + 1;
    end
    wire wr_hs = u_awvalid && u_wvalid && u_awready && u_wready;
    reg r_cap = 0;
    integer cap_cyc = -1;
    always @(posedge clk) if (rst_n) begin
        r_cap <= wr_hs && u_awaddr == 13'h1800 && u_wdata[0];
        if (r_cap) cap_cyc = cyc;                     // the snapshot edge: obs_q <= obs (its pre-edge value)
    end
    task automatic axi_write(input [12:0] a, input [31:0] d);
        begin
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
    integer errors = 0, i, k, it, lat, nchk = 0;
    reg [31:0] rd;
    reg [NW*32-1:0] win;
    reg [40:0] got, e;
    reg [EL-1:0] eh;
    initial begin
        host_obs = 0;
        repeat (5) @(negedge clk); rst_n = 1;
        for (it = 0; it < 12; it = it + 1) begin
            for (k = 0; k < 10 + it; k = k + 1) begin
                @(negedge clk);
                for (i = 0; i < EL; i = i + 32) host_obs[i +: 32] = $urandom;
            end
            axi_write(13'h1800, 32'h1);
            for (k = 0; k < 4; k = k + 1) @(negedge clk);
            for (k = 0; k < NW; k = k + 1) begin
                axi_read(13'h1900 + 4 * k, rd, lat);
                win[32 * k +: 32] = rd;
                if (lat != 3) begin errors = errors + 1; $display("ERR word %0d latency %0d", k, lat); end
            end
            got = win[EL +: 41];
            // expected: each bus = its source KD / KL / KR edges before the snapshot edge
            e[2:0] = hist[(cap_cyc - KD) % 4096][2:0];
            e[8:3] = hist[(cap_cyc - KL) % 4096][8:3];
            e[40:9] = hist[(cap_cyc - KR) % 4096][40:9];
            eh = hhist[cap_cyc % 4096];
            nchk = nchk + 1;
            if (got !== e) begin errors = errors + 1; $display("ERR it %0d ext got %h exp %h (adm/rdy/run %b lay %0d rcy %h)",
                                                               it, got, e, got[2:0], got[8:3], got[40:9]); end
            if (win[EL-1:0] !== eh) begin errors = errors + 1; $display("ERR it %0d HOST bits changed", it); end
            axi_read(13'h1804, rd, lat);
            if (rd !== {16'(NF), 16'(NB)}) begin errors = errors + 1; $display("ERR nb %h", rd); end
            axi_read(13'h1010, rd, lat);
            if (rd !== {16'hC5C5, 3'b0, 13'h1010}) begin errors = errors + 1; $display("ERR passthru %h", rd); end
        end
        if (errors == 0) $display("TB_KV_OBSX_PATH PASS words=%0d captures=%0d lag dob/lay/rcy=%0d/%0d/%0d", NW, nchk, KD, KL, KR);
        else $display("TB_KV_OBSX_PATH FAIL errors=%0d", errors);
        $finish;
    end
endmodule
