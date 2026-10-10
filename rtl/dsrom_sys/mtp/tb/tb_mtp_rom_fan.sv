`timescale 1ns/1ps
// tb_mtp_rom_fan: dsfd_drf_fan (N = 4) with random traffic (stream mtp-rom, 2026-10-08).
// Down: NMSG messages from the parent, each with a random source route (low nibble 0 local / 1..4 child, high
// nibble the child's own route) and 1..6 flits; every output must receive exactly its messages, in order, the
// header DEST rewritten to the route's next nibble for a child.  Up: the local engine and the 4 children each send
// NMSG/2 messages (1..6 flits, payload {source, sequence, flit}); the parent output must carry whole messages
// (no interleave), every source's messages in order, all of them.  Random ready / valid stalls everywhere.
module tb_mtp_rom_fan;
    parameter integer SEED = 1, NMSG = 400, MAXC = 200000;
    localparam integer FLIT = 512, N = 4, W = FLIT + 1, M = N + 1;
    reg clk = 0; always #1.5 clk = ~clk;
    reg rst_n = 0; integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    function automatic [31:0] mix(input [31:0] h, input [31:0] x);
        reg [31:0] t; begin t = (h ^ (x * 32'h9E3779B1)) + 32'h7F4A7C15; t = t ^ (t >> 15); t = t * 32'h2C1B3C6D;
        mix = t ^ (t >> 12); end
    endfunction
    reg uiv = 0; reg [W-1:0] uid = 0; wire uir;
    wire uov; wire [W-1:0] uod; reg uor = 0;
    wire lov; wire [W-1:0] lod; reg lor = 0;
    reg liv = 0; reg [W-1:0] lid = 0; wire lir;
    wire [N-1:0] cov; wire [N*W-1:0] cod; reg [N-1:0] cor = 0;
    reg [N-1:0] civ = 0; reg [N*W-1:0] cid = 0; wire [N-1:0] cir;
    wire ft;
    dsfd_drf_fan u (.ck(clk), .rst(rst_n), .f_uiv(uiv), .f_uid(uid), .t_uir(uir), .t_uov(uov), .t_uod(uod), .f_uor(uor),
        .t_lov(lov), .t_lod(lod), .f_lor(lor), .f_liv(liv), .f_lid(lid), .t_lir(lir),
        .t_cov(cov), .t_cod(cod), .f_cor(cor), .f_civ(civ), .f_cid(cid), .t_cir(cir), .t_ft(ft));
    // ------------------------------------------------ down traffic
    integer dm_len [0:1023], dm_rt [0:1023];
    integer d_sent = 0, d_k = 0;                    // message, flit
    integer exp_q [0:M*1024-1], eq_w [0:M-1], eq_r [0:M-1], o_k [0:M-1], o_m [0:M-1];
    integer i, o, rnd, got_down = 0, got_up = 0;
    function automatic [W-1:0] dflit(input integer m, input integer k);
        reg [W-1:0] f; begin
            f = {mix(m, k), mix(k, m), mix(m + 1, k + 2), {(W - 96){1'b0}}};
            if (k == 0) f[7:0] = dm_rt[m];
            f[W-1] = (k == dm_len[m] - 1);
            dflit = f;
        end
    endfunction
    always @(posedge clk) if (rst_n) begin
        rnd = mix(SEED, cyc);
        if (uiv && uir) uiv <= 1'b0;
        if ((!uiv || uir) && d_sent < NMSG && rnd[1:0] != 0) begin
            uiv <= 1'b1; uid <= dflit(d_sent, d_k);
            if (d_k == 0) begin o = dm_rt[d_sent] & 15; exp_q[o * 1024 + eq_w[o]] = d_sent; eq_w[o] = eq_w[o] + 1; end
            d_k = d_k + 1;
            if (d_k == dm_len[d_sent]) begin d_k = 0; d_sent = d_sent + 1; end
        end
        lor <= rnd[3:2] != 0; cor <= rnd[7:4] | rnd[11:8];
        // outputs: local (port 0) and children 1..4
        for (o = 0; o < M; o = o + 1) begin : chk
            reg v, r_; reg [W-1:0] d; integer m;
            v = (o == 0) ? lov : cov[o-1]; r_ = (o == 0) ? lor : cor[o-1]; d = (o == 0) ? lod : cod[(o-1)*W +: W];
            if (v && r_) begin
                m = exp_q[o * 1024 + eq_r[o]];
                if (eq_r[o] >= eq_w[o]) begin $display("MTP_FAN FAIL: unexpected flit on port %0d", o); $finish; end
                begin : cmp
                    reg [W-1:0] e; e = dflit(m, o_k[o]);
                    if (o_k[o] == 0 && o != 0) e[7:0] = (dm_rt[m] >> 4) & 15;
                    if (d !== e) begin $display("MTP_FAN FAIL: port %0d message %0d flit %0d", o, m, o_k[o]); $finish; end
                end
                o_k[o] = o_k[o] + 1;
                if (o_k[o] == dm_len[m]) begin o_k[o] = 0; eq_r[o] = eq_r[o] + 1; got_down = got_down + 1; end
            end
        end
    end
    // ------------------------------------------------ up traffic
    localparam integer NU = NMSG / 2;
    integer um_len [0:M*1024-1], u_sent [0:M-1], u_k [0:M-1], u_seen [0:M-1];
    integer cur_s = -1, cur_k = 0, cur_m = 0;
    function automatic [W-1:0] uflit(input integer s, input integer m, input integer k);
        uflit = {k == um_len[s * 1024 + m] - 1, 64'd0, 32'(s), 32'(m), 32'(k), mix(s * 7 + m, k), {(W - 1 - 64 - 128){1'b0}}};
    endfunction
    integer s;
    always @(posedge clk) if (rst_n) begin
        rnd = mix(SEED + 99, cyc);
        if (liv && lir) liv <= 1'b0;
        for (s = 0; s < N; s = s + 1) if (civ[s] && cir[s]) civ[s] <= 1'b0;
        for (s = 0; s < M; s = s + 1) begin
            if (s == 0 ? (!liv || lir) : (!civ[s-1] || cir[s-1])) begin
                if (u_sent[s] < NU && rnd[s * 2 +: 2] != 0) begin
                    if (s == 0) begin liv <= 1'b1; lid <= uflit(s, u_sent[s], u_k[s]); end
                    else begin civ[s-1] <= 1'b1; cid[(s-1)*W +: W] <= uflit(s, u_sent[s], u_k[s]); end
                    u_k[s] = u_k[s] + 1;
                    if (u_k[s] == um_len[s * 1024 + u_sent[s]]) begin u_k[s] = 0; u_sent[s] = u_sent[s] + 1; end
                end
            end
        end
        uor <= rnd[12:11] != 0;
        if (uov && uor) begin : up
            integer ss, mm, kk;
            ss = uod[W - 66 -: 32]; mm = uod[W - 98 -: 32]; kk = uod[W - 130 -: 32];
            if (cur_s < 0) begin
                if (kk != 0 || mm != u_seen[ss]) begin $display("MTP_FAN FAIL: up message start s%0d m%0d k%0d", ss, mm, kk); $finish; end
                cur_s = ss; cur_m = mm; cur_k = 0;
            end
            if (ss != cur_s || mm != cur_m || kk != cur_k || uod !== uflit(ss, mm, kk)) begin
                $display("MTP_FAN FAIL: up flit s%0d m%0d k%0d inside s%0d m%0d k%0d (interleave / corrupt)", ss, mm, kk, cur_s, cur_m, cur_k);
                $finish;
            end
            cur_k = cur_k + 1;
            if (uod[W-1]) begin cur_s = -1; u_seen[ss] = u_seen[ss] + 1; got_up = got_up + 1; end
        end
        if (ft) begin $display("MTP_FAN FAIL: fault"); $finish; end
    end
    initial begin
        for (i = 0; i < NMSG; i = i + 1) begin
            dm_len[i] = 1 + mix(SEED * 3, i) % 6;
            dm_rt[i] = (mix(SEED * 5, i) % 5) | ((mix(SEED * 11, i) % 5) << 4);
        end
        for (o = 0; o < M; o = o + 1) begin
            eq_w[o] = 0; eq_r[o] = 0; o_k[o] = 0; u_sent[o] = 0; u_k[o] = 0; u_seen[o] = 0;
            for (i = 0; i < NU; i = i + 1) um_len[o * 1024 + i] = 1 + mix(SEED * 13 + o, i) % 6;
        end
        repeat (5) @(posedge clk); rst_n = 1;
        while ((got_down < NMSG || got_up < M * NU) && cyc < MAXC) @(posedge clk);
        if (got_down < NMSG || got_up < M * NU) begin
            $display("MTP_FAN FAIL: timeout down %0d / %0d up %0d / %0d", got_down, NMSG, got_up, M * NU); $finish; end
        $display("MTP_FAN PASS down=%0d up=%0d cycles=%0d", got_down, got_up, cyc);
        $finish;
    end
endmodule
