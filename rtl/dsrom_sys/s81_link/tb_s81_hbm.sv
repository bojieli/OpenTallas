`timescale 1ns/1ps
// tb_s81_hbm (s81-die-rtl-bind 2026-10-14, F10 / HBM): the S81 HBM macro RTL (32 K pseudo-channel controllers + the
// behavioural PHY / device with its timing checker) under random traffic: per channel random writes then reads (len
// 1..8 sectors, addresses in a few rows of a few banks -> row hits, conflicts, bank-group CCD), random kr_rdy
// back-pressure.  Checks: every read sector returns the last data written there (golden byte-masked memory), in
// request order with its tag and beat; every write request returns wr_done; refreshes happen; the device model's
// timing checker sees NO violation.  PASS line TB_S81_HBM ... PASS.  Mutant MUT 1 (tRCD) must FAIL (violation).
module tb_s81_hbm;
    parameter integer MUT = 0, NREQ = 120;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [31:0] k_v = 0; wire [31:0] k_rdy; reg [959:0] k_addr = 0; reg [127:0] k_len = 0; reg [543:0] k_tag = 0;
    reg [31:0] k_we = 0; reg [8191:0] k_wdata = 0; reg [1023:0] k_wstrb = 0; wire [31:0] k_wr_done;
    wire [31:0] kr_v; reg [31:0] kr_rdy = 0; wire [543:0] kr_tag; wire [127:0] kr_beat; wire [8191:0] kr_data;
`ifdef PHY_K
    // BIND/mu4: the S81 K-only macro (no W port, no counter ports); refreshes read hierarchically from the model
    wire k_oor; wire [63:0] refreshes = dut.n_refreshes;
    ot_hbm3e_phy_v41x_aw30_e8p5_k #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr),
        .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .kr_v(kr_v),
        .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data), .k_oor(k_oor));
`else
    wire w_rdy; wire [7:0] w_room, wr_v; wire [79:0] wr_tag; wire [39:0] wr_beat; wire [2047:0] wr_data;
    wire k_oor, w_oor; wire [63:0] refreshes; wire [31:0] w_reads;
    ot_hbm3e_phy_v41x_aw30_e8p5 #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr),
        .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .kr_v(kr_v),
        .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data), .w_v(1'b0), .w_rdy(w_rdy), .w_addr(24'd0),
        .w_len(6'd0), .w_tag(10'd0), .w_room(w_room), .wr_v(wr_v), .wr_rdy(8'hFF), .wr_tag(wr_tag), .wr_beat(wr_beat),
        .wr_data(wr_data), .k_oor(k_oor), .w_oor(w_oor), .refreshes(refreshes), .w_reads(w_reads));
`endif
    // golden memory per channel: sector -> 256 b
    reg [255:0] gm [int];
    // expected read sectors per channel, in order: {tag, beat, data}
    typedef struct { int tag; int beat; logic [255:0] d; } exp_t;
    exp_t ex [32][$];
    int sent [32], wdone_exp [32], wdone_got [32], got [32], bad = 0, viol = 0;
    initial begin
        repeat (5) @(posedge clk); rst_n = 1;
    end
    // per-channel request generator: 1/3 writes until half way, then mostly reads
    genvar p;
    wire [31:0] vio; wire [127:0] vcode;
    generate for (p = 0; p < 32; p = p + 1) begin : g_p
        assign vio[p] = dut.g_k[p].u_d.viol; assign vcode[4*p +: 4] = dut.g_k[p].u_d.viol_code;
        always @(negedge clk) if (rst_n) begin : gen
            int len, sec, i, wr; logic [255:0] d; logic [31:0] st;
            if (k_v[p] && k_rdy[p]) k_v[p] <= 1'b0;
            else if (!k_v[p] && sent[p] < NREQ && ($urandom % 3) == 0) begin
                len = 1 + $urandom % 8;
                sec = (($urandom % 3) << 9) | (($urandom % 4) << 5) | ($urandom % 24);   // 3 rows x 4 banks
                wr = (sent[p] < NREQ / 2) ? ($urandom % 3 != 0) : ($urandom % 5 == 0);
                d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                st = (sent[p] % 7 == 3) ? $urandom : 32'hFFFFFFFF;
                k_v[p] <= 1'b1; k_addr[30*p +: 30] <= sec; k_len[4*p +: 4] <= len; k_tag[17*p +: 17] <= sent[p];
                k_we[p] <= wr; k_wdata[256*p +: 256] <= d; k_wstrb[32*p +: 32] <= st;
                for (i = 0; i < len; i = i + 1) begin : g
                    int key; logic [255:0] o; int b;
                    key = p * 4096 + sec + i;
                    o = gm.exists(key) ? gm[key] : 256'd0;
                    if (wr) begin for (b = 0; b < 32; b = b + 1) if (st[b]) o[8*b +: 8] = d[8*b +: 8]; gm[key] = o; end
                    else ex[p].push_back('{sent[p], i, o});
                end
                if (wr) wdone_exp[p]++;
                sent[p]++;
            end
            kr_rdy[p] <= ($urandom % 4) != 0;
        end
        always @(posedge clk) if (rst_n) begin
            if (k_wr_done[p]) wdone_got[p]++;
            if (kr_v[p] && kr_rdy[p]) begin : chk
                exp_t e;
                if (ex[p].size() == 0) begin bad++; $display("ERR ch %0d unexpected read", p); end
                else begin
                    e = ex[p].pop_front();
                    if (kr_tag[17*p +: 17] != e.tag || kr_beat[4*p +: 4] != e.beat || kr_data[256*p +: 256] !== e.d) begin
                        bad++; if (bad < 5) $display("ERR ch %0d tag %0d/%0d beat %0d/%0d data %s", p, kr_tag[17*p +: 17], e.tag, kr_beat[4*p +: 4], e.beat, (kr_data[256*p +: 256] === e.d) ? "ok" : "BAD");
                    end
                end
                got[p]++;
            end
        end
    end endgenerate
    int cyc = 0;
    always @(posedge clk) begin
        cyc++;
        if (cyc == 60000) begin : fin
            int c, pend = 0, wd_bad = 0, v = 0, sn = 0, gn = 0;
            for (c = 0; c < 32; c++) begin pend += ex[c].size(); if (wdone_got[c] != wdone_exp[c]) wd_bad++; sn += sent[c]; gn += got[c];
                if (vio[c]) begin v++; if (v < 3) $display("VIOL ch %0d code %0d", c, vcode[4*c +: 4]); end end
            $display("TB_S81_HBM MUT=%0d requests=%0d read_sectors=%0d bad=%0d pending=%0d wr_done_bad=%0d refreshes=%0d timing_violations=%0d k_oor=%0d %s",
                     MUT, sn, gn, bad, pend, wd_bad, refreshes, v, k_oor,
                     (bad == 0 && pend == 0 && wd_bad == 0 && v == 0 && refreshes > 0 && sn == 32 * NREQ && !k_oor) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
