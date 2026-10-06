`timescale 1ps/1ps
// CLAUDE S81-PH exact gate of dsfd_ctrl (the S81 HBM controller boundary).  Two copies of the functional PHY model
// (rtl/chip/ot_chip_v41x_hbm3e_phy.sv, KTAGW 17, K_AW 30): REF driven directly at ckh by per-PC valid/ready drivers
// with the request list; DUT behind dsfd_ctrl on the 22238-b phy bundle, the requests issued by a svc-side driver in
// the stream domain (cks) under the contract's credit flow.  Checks:
//   (a) the PHY-side request sequence of every PC (k_v & k_rdy at the DUT PHY) equals the issued rq sequence, field
//       by field (we, addr, len, tag, wstrb, wdata), in order;
//   (b) every rd word (rv) equals, in order, the response the DUT PHY handed over (kr_v & kr_rdy) on that PC;
//   (c) the DUT response set {(tag, beat) -> data} equals the REF set (same data incl. read-after-write per PC);
//   (d) wd pulses per PC = REF k_wr_done count = writes; all credits returned; st = {0, 1}; no request dropped;
//   (e) a mid-run die reset after a quiet phase, then a second traffic phase (directed: every PC issuing every cycle).
// Latency of each crossing is measured and printed (cks cycles).  Plusargs: +seed=, +n=, +p= (issue %, phase 1).
module tb_dsfd_ctrl;
    parameter integer CKS_PS = 833;
    parameter integer CKH_PS = 1024;
    parameter integer DQ = 8;
    localparam integer NPC = 32, NMAX = 256;
    reg cks = 0, ckh = 0, rst = 0;
    always #(CKS_PS / 2) cks = ~cks;
    always #(CKH_PS / 2) ckh = ~ckh;
    wire [22237:0] phy;
    wire [8895:0] rd;
    reg  [NPC*341-1:0] rq;
    wire [31:0] rk, wd;
    wire [1:0] st;
    dsfd_ctrl dut (.ckh(ckh), .cks(cks), .rst(rst), .phy(phy), .rd(rd), .rq(rq), .rk(rk), .wd(wd), .st(st));
    ot_s81ph_phy_on_bus #(.CLK_PS(CKH_PS)) u_bus (.phy(phy));
    // ---------------- reference PHY
    reg  [31:0] r_kv; wire [31:0] r_krdy, r_wdone, r_krv;
    reg  [32*30-1:0] r_kaddr; reg [32*4-1:0] r_klen; reg [32*17-1:0] r_ktag; reg [31:0] r_kwe;
    reg  [32*256-1:0] r_kwdata; reg [32*32-1:0] r_kwstrb;
    wire [32*17-1:0] r_krtag; wire [32*4-1:0] r_krbeat; wire [32*256-1:0] r_krdata;
    reg  r_rst_n = 0;
    ot_chip_v41x_hbm3e_phy #(.NPC(32), .K_AW(30), .W_PORT(0), .KTAGW(17), .CLK_PS(CKH_PS)) u_ref (
        .clk(ckh), .rst_n(r_rst_n), .k_v(r_kv), .k_rdy(r_krdy), .k_addr(r_kaddr), .k_len(r_klen), .k_tag(r_ktag), .k_we(r_kwe),
        .k_wdata(r_kwdata), .k_wstrb(r_kwstrb), .k_wr_done(r_wdone), .kr_v(r_krv), .kr_rdy(32'hffffffff), .kr_tag(r_krtag),
        .kr_beat(r_krbeat), .kr_data(r_krdata), .w_v(1'b0), .w_rdy(), .w_addr(24'd0), .w_len(6'd0), .w_tag(10'd0), .w_room(),
        .wr_v(), .wr_rdy(8'd0), .wr_tag(), .wr_beat(), .wr_data(), .k_oor(), .w_oor(), .refreshes(), .w_reads());
    // ---------------- stimulus
    function automatic integer pc_of(input [29:0] s);
        pc_of = ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31;
    endfunction
    reg          s_we   [0:NPC-1][0:NMAX-1];
    reg [29:0]   s_addr [0:NPC-1][0:NMAX-1];
    reg [3:0]    s_len  [0:NPC-1][0:NMAX-1];
    reg [255:0]  s_wd   [0:NPC-1][0:NMAX-1];
    reg [31:0]   s_ws   [0:NPC-1][0:NMAX-1];
    integer n_req, seed, p_iss, phase, errors;
    integer base;      // request index base of the current phase
    function automatic [340:0] word(input integer c, input integer i, input integer ph);
        reg [16:0] tag;
        begin
            tag = {ph[0], c[4:0], i[10:0]};
            word = {s_wd[c][i], s_ws[c][i], tag, s_len[c][i], s_addr[c][i], s_we[c][i], 1'b1};
        end
    endfunction
    task automatic gen(input integer ph);
        integer c, i, k, j; reg [29:0] s; reg ok;
        for (c = 0; c < NPC; c = c + 1)
            for (i = 0; i < n_req; i = i + 1) begin
                // a write to a fresh sector or a read (often of an earlier write's sector: read-after-write)
                s_we[c][i] = ($urandom % 3) == 0;
                if (!s_we[c][i] && i > 0 && ($urandom % 2)) begin
                    j = $urandom % i; s = s_addr[c][j] & ~30'd3;
                end else begin
                    ok = 0;
                    while (!ok) begin s = ($urandom % (1 << 16)) & ~30'd3; ok = pc_of(s) == c; end
                end
                k = s_we[c][i] ? ($urandom % 4) : 0;
                s_addr[c][i] = s + k;
                s_len[c][i] = s_we[c][i] ? 4'd1 : 4'd1 + ($urandom % 4);     // a read stays in its 4-sector group
                s_wd[c][i] = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                s_ws[c][i] = s_we[c][i] ? ($urandom | 32'h1) : 32'd0;
            end
    endtask
    // ---------------- svc-side driver (stream domain, credit flow)
    integer crd [0:NPC-1], iss [0:NPC-1], acc_dut [0:NPC-1], rsp_dut [0:NPC-1], wd_n [0:NPC-1];
    reg live_seen;
    integer c0;
    longint t_iss [0:NPC-1][0:NMAX-1];
    longint lat_q_sum, lat_q_max, lat_r_sum, lat_r_max, lat_q_n, lat_r_n, lat_q_min, lat_r_min;
    always @(posedge cks) begin
        for (c0 = 0; c0 < NPC; c0 = c0 + 1) begin
            if (rk[c0]) crd[c0] = crd[c0] + 1;
            if (wd[c0]) wd_n[c0] = wd_n[c0] + 1;
        end
        if (st[0] && !live_seen) begin live_seen = 1; for (c0 = 0; c0 < NPC; c0 = c0 + 1) crd[c0] = DQ; end
        for (c0 = 0; c0 < NPC; c0 = c0 + 1) begin
            rq[c0*341 +: 341] <= 341'd0;
            if (live_seen && rst && iss[c0] < n_req && crd[c0] > 0 && ($urandom % 100) < p_iss) begin
                rq[c0*341 +: 341] <= word(c0, iss[c0], phase);
                t_iss[c0][iss[c0]] = $time;
                iss[c0] = iss[c0] + 1; crd[c0] = crd[c0] - 1;
            end
        end
    end
    // ---------------- DUT PHY side monitors: (a) requests, response hand-off queue for (b)
    reg [276:0] hq [0:NPC-1][$];
    longint     hq_t [0:NPC-1][$];
    reg [340:0] exp_w;
    integer c1;
    always @(posedge ckh) if (u_bus.rst_n) begin
        for (c1 = 0; c1 < NPC; c1 = c1 + 1) begin
            if (u_bus.k_v[c1] && u_bus.k_rdy[c1]) begin
                exp_w = word(c1, acc_dut[c1], phase);
                if ({u_bus.k_wdata[c1*256 +: 256], u_bus.k_wstrb[c1*32 +: 32], u_bus.k_tag[c1*17 +: 17], u_bus.k_len[c1*4 +: 4],
                     u_bus.k_addr[c1*30 +: 30], u_bus.k_we[c1], 1'b1} !== exp_w || acc_dut[c1] >= iss[c1]) begin
                    if (errors < 10) $display("ERR (a) pc %0d request %0d: PHY saw tag %h addr %h, issued tag %h addr %h", c1,
                        acc_dut[c1], u_bus.k_tag[c1*17 +: 17], u_bus.k_addr[c1*30 +: 30], exp_w[52:36], exp_w[31:2]);
                    errors = errors + 1;
                end
                lat_q_sum = lat_q_sum + ($time - t_iss[c1][acc_dut[c1]]); lat_q_n = lat_q_n + 1;
                if ($time - t_iss[c1][acc_dut[c1]] > lat_q_max) lat_q_max = $time - t_iss[c1][acc_dut[c1]];
                if ($time - t_iss[c1][acc_dut[c1]] < lat_q_min) lat_q_min = $time - t_iss[c1][acc_dut[c1]];
                acc_dut[c1] = acc_dut[c1] + 1;
            end
            if (u_bus.kr_v[c1] && u_bus.kr_rdy[c1]) begin
                hq[c1].push_back({u_bus.kr_data[c1*256 +: 256], u_bus.kr_tag[c1*17 +: 17], u_bus.kr_beat[c1*4 +: 4]});
                hq_t[c1].push_back($time);
            end
        end
    end
    // (b) rd in order against the hand-off queue; (c) DUT response map
    reg [255:0] dmap [int];
    reg [255:0] rmap [int];
    reg [276:0] h;
    longint ht;
    integer c2;
    always @(posedge cks) begin
        for (c2 = 0; c2 < NPC; c2 = c2 + 1) if (rd[8864 + c2]) begin
            if (hq[c2].size() == 0) begin
                if (errors < 10) $display("ERR (b) pc %0d: rd word with no PHY response", c2);
                errors = errors + 1;
            end else begin
                h = hq[c2].pop_front(); ht = hq_t[c2].pop_front();
                if ({rd[c2*256 +: 256], rd[8192 + c2*17 +: 17], rd[8736 + c2*4 +: 4]} !== h) begin
                    if (errors < 10) $display("ERR (b) pc %0d: rd tag %h beat %h != PHY tag %h beat %h", c2,
                        rd[8192 + c2*17 +: 17], rd[8736 + c2*4 +: 4], h[20:4], h[3:0]);
                    errors = errors + 1;
                end
                lat_r_sum = lat_r_sum + ($time - ht); lat_r_n = lat_r_n + 1;
                if ($time - ht > lat_r_max) lat_r_max = $time - ht;
                if ($time - ht < lat_r_min) lat_r_min = $time - ht;
                dmap[{rd[8192 + c2*17 +: 17], rd[8736 + c2*4 +: 4]}] = rd[c2*256 +: 256];
                rsp_dut[c2] = rsp_dut[c2] + 1;
            end
        end
    end
    // ---------------- REF drivers + map
    integer ri [0:NPC-1], rwd [0:NPC-1], c3;
    reg [340:0] rw;
    always @(posedge ckh) if (r_rst_n) begin
        for (c3 = 0; c3 < NPC; c3 = c3 + 1) begin
            if (r_kv[c3] && r_krdy[c3]) ri[c3] = ri[c3] + 1;
            if (r_wdone[c3]) rwd[c3] = rwd[c3] + 1;
            if (r_krv[c3]) rmap[{r_krtag[c3*17 +: 17], r_krbeat[c3*4 +: 4]}] = r_krdata[c3*256 +: 256];
            if (ri[c3] < n_req) begin
                rw = word(c3, ri[c3], phase);
                r_kv[c3] <= 1'b1; r_kwe[c3] <= rw[1]; r_kaddr[c3*30 +: 30] <= rw[31:2]; r_klen[c3*4 +: 4] <= rw[35:32];
                r_ktag[c3*17 +: 17] <= rw[52:36]; r_kwstrb[c3*32 +: 32] <= rw[84:53]; r_kwdata[c3*256 +: 256] <= rw[340:85];
            end else r_kv[c3] <= 1'b0;
        end
    end
    // ---------------- run
    integer c, nb, beats, wr_n, k, tmo;
    task automatic check_phase(input integer ph);
        integer key; reg [255:0] v;
        beats = 0; wr_n = 0;
        for (c = 0; c < NPC; c = c + 1) for (k = 0; k < n_req; k = k + 1) begin
            if (s_we[c][k]) wr_n = wr_n + 1; else beats = beats + s_len[c][k];
        end
        if (dmap.num() != beats || rmap.num() != beats) begin
            $display("ERR (c) phase %0d: response beats dut %0d ref %0d expected %0d", ph, dmap.num(), rmap.num(), beats);
            errors = errors + 1;
        end
        foreach (rmap[key]) begin
            if (!dmap.exists(key) || dmap[key] !== rmap[key]) begin
                if (errors < 10) $display("ERR (c) phase %0d: key %h data differs / missing", ph, key);
                errors = errors + 1;
            end
        end
        k = 0; nb = 0;
        for (c = 0; c < NPC; c = c + 1) begin k = k + wd_n[c]; nb = nb + rwd[c];
            if (crd[c] != DQ) begin $display("ERR (d) pc %0d credits %0d != %0d", c, crd[c], DQ); errors = errors + 1; end
            if (acc_dut[c] != n_req) begin $display("ERR (d) pc %0d accepted %0d != %0d", c, acc_dut[c], n_req); errors = errors + 1; end
        end
        if (k != wr_n || nb != wr_n) begin $display("ERR (d) phase %0d: write-done dut %0d ref %0d writes %0d", ph, k, nb, wr_n); errors = errors + 1; end
        if (st !== 2'b01) begin $display("ERR (d) phase %0d: st %b", ph, st); errors = errors + 1; end
        $display("phase %0d: %0d requests (%0d writes, %0d read beats) on 32 PCs; responses dut %0d ref %0d", ph, NPC * n_req,
                 wr_n, beats, dmap.num(), rmap.num());
    endtask
    task automatic clear();
        for (c = 0; c < NPC; c = c + 1) begin
            iss[c] = 0; acc_dut[c] = 0; rsp_dut[c] = 0; wd_n[c] = 0; ri[c] = 0; rwd[c] = 0; crd[c] = 0;
        end
        dmap.delete(); rmap.delete(); live_seen = 0;
    endtask
    task automatic run_phase(input integer ph);
        phase = ph; gen(ph);
        tmo = 0;
        while (tmo < 400000) begin
            @(posedge cks); tmo = tmo + 1;
            nb = 0;
            for (c = 0; c < NPC; c = c + 1) if (rsp_dut[c] + 0 >= 0) nb = nb + rsp_dut[c];
            beats = 0; wr_n = 0;
            for (c = 0; c < NPC; c = c + 1) for (k = 0; k < n_req; k = k + 1) if (!s_we[c][k]) beats = beats + s_len[c][k];
            k = 0; for (c = 0; c < NPC; c = c + 1) k = k + wd_n[c];
            for (c = 0; c < NPC; c = c + 1) for (nb = 0; nb < 1; nb = nb + 1) ;
            if (dmap.num() == beats && rmap.num() == beats) begin
                wr_n = 0; for (c = 0; c < NPC; c = c + 1) for (nb = 0; nb < n_req; nb = nb + 1) if (s_we[c][nb]) wr_n = wr_n + 1;
                if (k == wr_n) begin
                    nb = 1; for (c = 0; c < NPC; c = c + 1) if (crd[c] != DQ) nb = 0;
                    if (nb) break;
                end
            end
        end
        repeat (64) @(posedge cks);
        if (tmo >= 400000) begin $display("ERR phase %0d: timeout", ph); errors = errors + 1; end
        check_phase(ph);
    endtask
    initial begin
        if (!$value$plusargs("seed=%d", seed)) seed = 20261006;
        if (!$value$plusargs("n=%d", n_req)) n_req = 48;
        if (!$value$plusargs("p=%d", p_iss)) p_iss = 40;
        void'($urandom(seed));
        errors = 0; lat_q_sum = 0; lat_q_max = 0; lat_r_sum = 0; lat_r_max = 0; lat_q_n = 0; lat_r_n = 0; lat_q_min = 64'd1 << 40; lat_r_min = 64'd1 << 40;
        rq = 0; r_kv = 0; r_kwe = 0; r_kaddr = 0; r_klen = 0; r_ktag = 0; r_kwdata = 0; r_kwstrb = 0;
        clear();
        rst = 0; r_rst_n = 0; repeat (8) @(posedge ckh); rst = 1; r_rst_n = 1;
        run_phase(0);
        // mid-run die reset after the quiet phase, fresh REF, then every PC issuing every cycle it holds a credit
        rst = 0; r_rst_n = 0; repeat (6) @(posedge ckh); clear(); rst = 1; r_rst_n = 1;
        p_iss = 100;
        run_phase(1);
        $display("latency min (the crossing alone): request rq issue -> PHY accept %0.2f cks cycles; response PHY accept -> rd %0.2f cks cycles",
                 (1.0 * lat_q_min) / CKS_PS, (1.0 * lat_r_min) / CKS_PS);
        $display("latency: request rq issue -> PHY accept mean %0.2f max %0.2f cks cycles; response PHY -> rd mean %0.2f max %0.2f cks cycles (cks %0d ps, ckh %0d ps)",
                 (1.0 * lat_q_sum / lat_q_n) / CKS_PS, (1.0 * lat_q_max) / CKS_PS, (1.0 * lat_r_sum / lat_r_n) / CKS_PS,
                 (1.0 * lat_r_max) / CKS_PS, CKS_PS, CKH_PS);
        if (errors == 0) $display("TB_DSFD_CTRL PASS"); else $display("TB_DSFD_CTRL FAIL errors=%0d", errors);
        $finish;
    end
endmodule
