`timescale 1ns/1ps
// hgi-1010/c 2026-10-10: the die-side memory adapters of hardware COLL.ROW_GATHER in hfd_coll, end to end through their
// die-net partners: ot_hgi_coll_rgx_hbm (row source -> 2 ot_hgi_hbm_rd_client -> 2 ot_hgi_hbm_rd_server -> kport lane
// models; list fetch -> a VM packet client -> VM packet model) and ot_hgi_coll_rgx_snk (VM-space flits -> the W2 group
// through ot_hgi_vm_lanearb (K 2: a second client idles / bursts) -> a W2 lane model with LQ credits and dones;
// HBM-space flits -> 2 write clients -> 2 ot_hgi_hbm_wr_server -> kport lane models).  Checks: every row-source response
// = the HBM sector of its request with its tag, in request order a lane; every list word = {VM sector 2w + 1, 2w};
// every flit's two sectors written exactly once with their data (VM: bank lane = sector mod 32, word mask all); no
// credit is ever overdrawn; everything drains.  Mutants: SNK_MUT 1 / 2, LF_MUT 1 must FAIL.  Prints RGXMEM PASS / FATAL.
module tb_hgi_coll_rgx_mem;
    parameter integer SNK_MUT = 0, LF_MUT = 0;
    localparam integer DEL = 4, LQ = 8;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer seed = 3; function automatic integer rnd(); rnd = int'($urandom % 32'h7FFFFFFF); endfunction
    function automatic [255:0] hsec(input longint s, input integer salt);
        longint x;
        begin for (integer w = 0; w < 4; w = w + 1) begin x = (s * 4 + w + 64'(salt) * 1000003) ^ 64'h5DEECE66D; x = x * 64'h9E3779B97F4A7C15;
            x = x ^ (x >> 31); hsec[64*w +: 64] = x; end end
    endfunction
    // ---------------- DUTs
    reg [1:0] hq_v = 0; wire [1:0] hq_rdy; reg [69:0] hq_a = 0; reg [15:0] hq_t = 0; wire [1:0] hr_v; wire [15:0] hr_t; wire [511:0] hr_d;
    reg lq_v = 0; wire lq_rdy; reg [31:0] lq_a = 0; wire lr_v; wire [511:0] lr_d;
    wire [75:0] xq; wire [513:0] xr; wire [337:0] vmq; reg [273:0] vmr = 0;
    ot_hgi_coll_rgx_hbm #(.MUT_LF(LF_MUT)) u_h (.clk(clk), .rst_n(rst_n), .rg_hq_v(hq_v), .rg_hq_rdy(hq_rdy), .rg_hq_addr(hq_a),
        .rg_hq_tag(hq_t), .rg_hr_v(hr_v), .rg_hr_tag(hr_t), .rg_hr_data(hr_d), .rg_lq_v(lq_v), .rg_lq_rdy(lq_rdy),
        .rg_lq_addr(lq_a), .rg_lr_v(lr_v), .rg_lr_data(lr_d), .xq(xq), .xr(xr), .vmq(vmq), .vmr(vmr));
    reg [DEL-1:0] w_v = 0; reg [DEL*40-1:0] w_a = 0; reg w_vm = 1; reg [DEL*512-1:0] w_d = 0; wire [DEL-1:0] w_rdy;
    wire c_req, c_gnt0; wire [32*280-1:0] c_q; wire [31:0] c_cr, c_rsp; wire [2*326-1:0] xw; wire [1:0] xwa; wire sfault;
    ot_hgi_coll_rgx_snk #(.DEL(DEL), .LQ(LQ), .MUT(SNK_MUT)) u_s (.clk(clk), .rst_n(rst_n), .rg_w_v(w_v), .rg_w_addr(w_a),
        .rg_w_vm(w_vm), .rg_w_data(w_d), .rg_w_rdy(w_rdy), .c_req(c_req), .c_gnt(c_gnt0), .c_q(c_q), .c_cr(c_cr), .c_rsp(c_rsp),
        .xw(xw), .xwa(xwa), .fault(sfault));
    // ---------------- the W2 group: lanearb (client 0 = the sink, client 1 = a bursting agent) + lane model
    reg agent_req = 0; wire [1:0] gnt; wire [2*32-1:0] cr2; wire [2*32-1:0] rs2; wire [32*280-1:0] g_q; reg [31:0] g_cr = 0, g_rsp = 0;
    ot_hgi_vm_lanearb #(.K(2), .REQW(280), .RSPW(1)) u_arb (.clk(clk), .rst_n(rst_n), .c_req({agent_req, c_req}), .c_gnt(gnt),
        .c_q({{32*280{1'b0}}, c_q}), .c_cr(cr2), .c_rsp(rs2), .g_q(g_q), .g_cr(g_cr), .g_rsp(g_rsp));
    assign c_gnt0 = gnt[0]; assign c_cr = cr2[31:0]; assign c_rsp = rs2[31:0];
    reg [255:0] vmem [0:32767]; reg [0:32767] vok = 0; integer occ [0:31]; reg [14:0] lq_sec [0:31][0:15]; integer lqh [0:31], lqn [0:31];
    initial for (integer b = 0; b < 32; b = b + 1) begin occ[b] = 0; lqh[b] = 0; lqn[b] = 0; end
    integer errs = 0, vwr = 0;
    always @(posedge clk) if (rst_n) begin
        g_cr <= 0; g_rsp <= 0;
        for (integer b = 0; b < 32; b = b + 1) begin
            if (g_q[b*280 + 279]) begin
                if (g_q[b*280 + 264 +: 5] != 5'(b)) begin $display("FATAL: lane %0d carries bank %0d", b, g_q[b*280 + 264 +: 5]); errs = errs + 1; end
                if (lqn[b] == LQ) begin $display("FATAL: lane %0d credit overdrawn", b); errs = errs + 1; end
                lq_sec[b][(lqh[b] + lqn[b]) % 16] = g_q[b*280 + 264 +: 15]; lqn[b] = lqn[b] + 1;
                if (vok[g_q[b*280 + 264 +: 15]]) begin $display("FATAL: VM sector %0d written twice", g_q[b*280 + 264 +: 15]); errs = errs + 1; end
                vmem[g_q[b*280 + 264 +: 15]] = g_q[b*280 + 8 +: 256]; vok[g_q[b*280 + 264 +: 15]] = 1'b1; vwr = vwr + 1;
            end
            if (lqn[b] > 0 && (rnd() % 3) == 0) begin lqh[b] = lqh[b] + 1; lqn[b] = lqn[b] - 1; g_cr[b] <= 1'b1; g_rsp[b] <= 1'b1; end
        end
    end
    // ---------------- loader side: 2 read servers + 2 write servers on kport lane models (in order, latency 3..10)
    wire [1:0] rq_v, wq_v; wire [2*37-1:0] rq_a, wq_a; wire [2*256-1:0] wq_d; wire [2*32-1:0] wq_s; reg [1:0] rq_rdy = 2'b11, wq_rdy = 2'b11;
    reg [1:0] rr_v = 0, wa_v = 0; reg [2*256-1:0] rr_d = 0; wire [1:0] rsf, wsf;
    reg [255:0] hmem [0:32767]; reg [0:32767] hok = 0; integer hwr = 0;
    for (genvar l = 0; l < 2; l = l + 1) begin : g_srv
        ot_hgi_hbm_rd_server u_r (.clk(clk), .rst_n(rst_n), .xq(xq[l*38 +: 38]), .xr(xr[l*257 +: 257]), .req_v(rq_v[l]),
            .req_rdy(rq_rdy[l]), .req_addr(rq_a[l*37 +: 37]), .rsp_v(rr_v[l]), .rsp_data(rr_d[l*256 +: 256]), .fault(rsf[l]));
        ot_hgi_hbm_wr_server u_w (.clk(clk), .rst_n(rst_n), .xw(xw[l*326 +: 326]), .xa(xwa[l]), .req_v(wq_v[l]), .req_rdy(wq_rdy[l]),
            .req_addr(wq_a[l*37 +: 37]), .req_wdata(wq_d[l*256 +: 256]), .req_wstrb(wq_s[l*32 +: 32]), .rsp_v(wa_v[l]), .fault(wsf[l]));
        integer rdue = -1, wdue = -1; reg [36:0] ra;
        always @(posedge clk) if (rst_n) begin
            rr_v[l] <= 1'b0; wa_v[l] <= 1'b0;
            if (rq_v[l] && rq_rdy[l]) begin ra = rq_a[l*37 +: 37]; rdue = cyc + 3 + rnd() % 8; end
            if (rdue >= 0 && cyc >= rdue) begin rr_v[l] <= 1'b1; rr_d[l*256 +: 256] <= hsec(longint'(ra[36:5]), 1); rdue = -1; end
            if (wq_v[l] && wq_rdy[l]) begin
                if (wq_s[l*32 +: 32] != 32'hFFFFFFFF) begin $display("FATAL: partial HBM write"); errs = errs + 1; end
                if (hok[wq_a[l*37 + 5 +: 15]]) begin $display("FATAL: HBM sector written twice"); errs = errs + 1; end
                hmem[wq_a[l*37 + 5 +: 15]] = wq_d[l*256 +: 256]; hok[wq_a[l*37 + 5 +: 15]] = 1'b1; hwr = hwr + 1; wdue = cyc + 3 + rnd() % 8;
            end
            if (wdue >= 0 && cyc >= wdue) begin wa_v[l] <= 1'b1; wdue = -1; end
            rq_rdy[l] <= (rnd() % 4) != 0; wq_rdy[l] <= (rnd() % 4) != 0;
        end
    end
    // ---------------- VM packet model (the list): in order, latency 4..9, 4 outstanding at most
    reg [337:0] pq [0:15]; integer pqh = 0, pqt = 0, pdue [0:15];
    always @(posedge clk) if (rst_n) begin
        vmr <= 0;
        if (vmq[337]) begin
            if (pqt - pqh >= 4) begin $display("FATAL: VM client over 4 outstanding"); errs = errs + 1; end
            pq[pqt % 16] = vmq; pdue[pqt % 16] = cyc + 4 + rnd() % 6; if (pqt > pqh && pdue[pqt % 16] < pdue[(pqt - 1) % 16]) pdue[pqt % 16] = pdue[(pqt - 1) % 16];
            pqt = pqt + 1;
        end
        if (pqt > pqh && pdue[pqh % 16] <= cyc) begin
            vmr <= {1'b1, pq[pqh % 16][15:0], 1'b0, hsec(longint'(pq[pqh % 16][335:309]), 2)}; pqh = pqh + 1;
        end
    end
    // ---------------- stimulus + checks
    // row source
    integer hq_n = 0, hr_n = 0; reg [42:0] hexp [0:1][0:63]; integer heh [0:1], het [0:1];
    initial begin heh[0] = 0; heh[1] = 0; het[0] = 0; het[1] = 0; end
    always @(posedge clk) if (rst_n) begin
        for (integer l = 0; l < 2; l = l + 1) begin
            if (hq_v[l] && hq_rdy[l]) begin hexp[l][het[l] % 64] = {hq_t[l*8 +: 8], hq_a[l*35 +: 35]}; het[l] = het[l] + 1; hq_n = hq_n + 1; end
            if (hr_v[l]) begin
                if (het[l] == heh[l]) begin $display("FATAL: unexpected row-source response lane %0d", l); errs = errs + 1; end
                else begin
                    if (hr_t[l*8 +: 8] !== hexp[l][heh[l] % 64][42:35] || hr_d[l*256 +: 256] !== hsec(longint'(hexp[l][heh[l] % 64][34:0]), 1)) begin
                        $display("FATAL: row-source lane %0d response %0d wrong", l, heh[l]); errs = errs + 1; end
                    heh[l] = heh[l] + 1; hr_n = hr_n + 1;
                end
            end
        end
    end
    // list fetch
    integer lq_n = 0, lr_n = 0; reg [31:0] lexp [0:63]; integer leh = 0, let_ = 0;
    always @(posedge clk) if (rst_n) begin
        if (lq_v && lq_rdy) begin lexp[let_ % 64] = lq_a; let_ = let_ + 1; lq_n = lq_n + 1; end
        if (lr_v) begin
            if (lr_d !== {hsec(2 * longint'(lexp[leh % 64]) + 1, 2), hsec(2 * longint'(lexp[leh % 64]), 2)}) begin
                $display("FATAL: list word %0d (addr %0d) wrong", leh, lexp[leh % 64]); errs = errs + 1; end
            leh = leh + 1; lr_n = lr_n + 1;
        end
    end
    // drivers (negedge)
    integer nflit = 0, wsent = 0; integer fbase;
    // w_rdy is combinational on the current head: sample it at the edge
    reg [DEL-1:0] w_rdy_q; always @(posedge clk) w_rdy_q <= w_rdy;
    always @(negedge clk) if (rst_n) begin
        for (integer l = 0; l < 2; l = l + 1) if (!hq_v[l] || hq_rdy[l]) begin
            hq_v[l] = (hq_n < 200) && (rnd() % 2);
            hq_a[l*35 +: 35] = 35'(rnd() % 100000); hq_t[l*8 +: 8] = 8'(rnd());
        end
        if (!lq_v || lq_rdy) begin lq_v = (lq_n < 100) && (rnd() % 2); lq_a = 32'(rnd() % 4000); end
    end
    task automatic flits(input integer vm, input integer n);
        integer sent, t0;
        begin
            w_vm = vm[0]; sent = 0; t0 = cyc;
            while (sent < n || w_v != 0) begin
                @(negedge clk);
                for (integer l = 0; l < DEL; l = l + 1) begin
                    if (w_v[l] && w_rdy_q[l]) w_v[l] = 1'b0;   // popped at the edge just passed (rdy sampled there)
                end
                for (integer l = 0; l < DEL; l = l + 1) if (!w_v[l] && sent < n && (rnd() % 3) != 0) begin
                    w_v[l] = 1'b1;
                    w_a[l*40 +: 40] = vm ? 40'(fbase + 16 * sent) : 40'(64 * (fbase + sent));
                    w_d[l*512 +: 512] = {hsec(fbase + sent, 4), hsec(fbase + sent, 3)};
                    sent = sent + 1;
                end
                if (cyc - t0 > 200000) $fatal(1, "FATAL: sink stuck");
            end
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        fork
            begin fbase = 1000; flits(1, 300); fbase = 9000; flits(0, 120); fbase = 40000; flits(1, 200); end
            begin repeat (300) @(negedge clk); agent_req = 1; repeat (60) @(negedge clk); agent_req = 0; end
        join
        repeat (300) @(negedge clk);
        // VM: every sector of flit k (word address base + 16 k) = sectors 2 (base/16 + k) .. + 1
        for (integer k = 0; k < 500; k = k + 1) for (integer h = 0; h < 2; h = h + 1) begin : vchk
            integer s, fb, kk; fb = (k < 300) ? 1000 : 40000; kk = (k < 300) ? k : k - 300; s = (fb + 16 * kk) / 8 + h;
            if (!vok[s] || vmem[s] !== hsec(fb + kk, 3 + h)) begin if (errs < 10) $display("FATAL: VM flit %0d half %0d", k, h); errs = errs + 1; end
        end
        for (integer k = 0; k < 120; k = k + 1) for (integer h = 0; h < 2; h = h + 1) begin : hchk
            integer s; s = 2 * (9000 + k) + h;
            if (!hok[s] || hmem[s] !== hsec(9000 + k, 3 + h)) begin if (errs < 10) $display("FATAL: HBM flit %0d half %0d", k, h); errs = errs + 1; end
        end
        if (u_s.outst != 0 || c_req) begin $display("FATAL: sink not drained (outst %0d req %0d)", u_s.outst, c_req); errs = errs + 1; end
        if (hr_n != hq_n || lr_n != lq_n || vwr != 2 * 500 || hwr != 2 * 120) begin
            $display("FATAL: counts hq %0d hr %0d lq %0d lr %0d vwr %0d hwr %0d", hq_n, hr_n, lq_n, lr_n, vwr, hwr); errs = errs + 1; end
        if (sfault || |rsf || |wsf) begin $display("FATAL: fault"); errs = errs + 1; end
        if (errs == 0) $display("RGXMEM PASS rows %0d list %0d vm_sectors %0d hbm_sectors %0d cycles %0d", hr_n, lr_n, vwr, hwr, cyc);
        else $display("FATAL RGXMEM errors=%0d", errs);
        $finish;
    end
endmodule
