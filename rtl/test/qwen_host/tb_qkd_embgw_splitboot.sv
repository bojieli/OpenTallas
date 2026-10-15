`timescale 1ns/1ps
// Exact bench of the slot cell qkd_embgw (Qwen ROM TP8 track B) THROUGH ITS OWN PORTS.
//   host boot words (hb, credit flow)  ->  qkd_embgw  <-> 4 x ot_qfd_emb_strip (the monolithic strip engine, UNCHANGED
//   RTL, one a stack) behind LD relay stages each way, in the landing leaf's field order <-> a per-PC HBM static-port
//   model (a store that returns "uncorrectable" for a sector that was never written).
//   SU driver: 64 code requests + the scale request a token on r_ea under the RQD = 32 credits of t_ecr.
// Golden (independent of the RTL): sector E holds G(E) (a 256-b hash); code word w of token t = {G(128 t + 2 w + 1),
// G(128 t + 2 w)}, the scale word = lane (t mod 16) of G(E_SCALE + t / 16).  Checks: every response word bit-exact and
// in request order; one credit a request; nothing answered before the boot check (first request posted before the
// load); emb_ready set, no fault, on est; boot count / checksum (crc32 sector sum) accepted; no strip fault; the bits
// the cell does not carry (link class bit, tag[6:4]) are proven constant on every strip word.
// Prints "PASS kv_gwhost embgw ..." or "FAIL kv_gwhost embgw ...".
module tb_emb_pc_model #(parameter integer DLY = 9, parameter integer NS = 96) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         s_v,
    input  wire         s_we,
    input  wire [28:0]  s_key,
    input  wire [255:0] w_d,
    output reg          s_cr,
    output reg          e_v,
    output reg  [257:0] e_d
);
    reg [28:0]  key [0:NS-1];
    reg [255:0] dat [0:NS-1];
    integer n = 0, i, hit;
    reg         qv  [0:DLY-1];
    reg         qwe [0:DLY-1];
    reg [28:0]  qk  [0:DLY-1];
    reg [255:0] qd  [0:DLY-1];
    integer writes = 0, reads = 0, miss = 0;
    initial for (i = 0; i < DLY; i = i + 1) qv[i] = 1'b0;
    always @(posedge clk) begin
        s_cr <= 1'b0; e_v <= 1'b0;
        if (rst_n) begin
            if (qv[DLY-1]) begin
                s_cr <= 1'b1;
                hit = -1;
                for (i = 0; i < n; i = i + 1) if (key[i] == qk[DLY-1]) hit = i;
                if (qwe[DLY-1]) begin
                    if (hit < 0) begin hit = n; n = n + 1; end
                    key[hit] = qk[DLY-1]; dat[hit] = qd[DLY-1]; writes = writes + 1;
                end else begin
                    e_v <= 1'b1; reads = reads + 1;
                    if (hit < 0) begin e_d <= {1'b1, 1'b0, {256{1'b1}}}; miss = miss + 1; end
                    else e_d <= {1'b0, 1'b0, dat[hit]};
                end
            end
            for (i = DLY - 1; i > 0; i = i - 1) begin qv[i] <= qv[i-1]; qwe[i] <= qwe[i-1]; qk[i] <= qk[i-1]; qd[i] <= qd[i-1]; end
            qv[0] <= s_v; qwe[0] <= s_we; qk[0] <= s_key; qd[0] <= w_d;
        end
    end
endmodule

module tb_qkd_embgw_splitboot;
    parameter integer NT   = 20;             // tokens loaded
    parameter integer NF   = 40;             // fetches
    parameter integer LD   = 3;              // relay stages each way between the cell and a strip
    localparam [24:0] E_SCALE = 25'd19447808;
    localparam integer NPC = 32;
    reg ck = 0, rst_n = 0;
    always #0.4165 ck = ~ck;
    integer cyc = 0;
    always @(posedge ck) cyc = cyc + 1;
    // ---- golden ----
    function automatic [255:0] gsec(input [24:0] e);
        reg [31:0] x; integer j;
        begin
            for (j = 0; j < 8; j = j + 1) begin
                x = {7'd0, e} * 32'h9E3779B1 + j * 32'h85EBCA6B + 32'h1234567;
                x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
                gsec[32*j +: 32] = x;
            end
        end
    endfunction
    function automatic [31:0] crc_sector(input [24:0] e, input [255:0] d);   // zlib.crc32 of {E 4 B LE, data 32 B}
        reg [287:0] m; reg [31:0] c; integer i;
        begin
            m = {d, 7'd0, e}; c = 32'hffffffff;
            for (i = 0; i < 288; i = i + 1) c = (c >> 1) ^ ((c[0] ^ m[i]) ? 32'hedb88320 : 32'h0);
            crc_sector = ~c;
        end
    endfunction
    function automatic [511:0] gword(input [17:0] t, input integer w);
        reg [255:0] s;
        begin
            if (w < 64) gword = {gsec({t, 7'd0} + 25'(2*w + 1)), gsec({t, 7'd0} + 25'(2*w))};
            else begin s = gsec(E_SCALE + 25'(t >> 4)); gword = {496'd0, s[16*t[3:0] +: 16]}; end
        end
    endfunction
    // ---- the cell ----
    reg  [25:0]  r_ea = 0;
    wire         t_ecr;
    wire [512:0] t_eq;
    wire [519:0] emr [0:3];
    wire [3:0]   emr_cr, emf_cr;
    wire [287:0] emf [0:3];
    reg  [282:0] hb = 0;
    wire         hb_cr;
    wire [12:0]  est;
    qkd_embgw_splitboot dut (.ck(ck), .rst_n(rst_n), .r_ea(r_ea), .t_ecr(t_ecr), .t_eq(t_eq),
        .emr_WS(emr[0]), .emr_WS_cr(emr_cr[0]), .emf_WS(emf[0]), .emf_WS_cr(emf_cr[0]),
        .emr_WN(emr[1]), .emr_WN_cr(emr_cr[1]), .emf_WN(emf[1]), .emf_WN_cr(emf_cr[1]),
        .emr_ES(emr[2]), .emr_ES_cr(emr_cr[2]), .emf_ES(emf[2]), .emf_ES_cr(emf_cr[2]),
        .emr_EN(emr[3]), .emr_EN_cr(emr_cr[3]), .emf_EN(emf[3]), .emf_EN_cr(emf_cr[3]),
        .hb(hb), .hb_cr(hb_cr), .est(est));
    // ---- four strips behind LD relay stages ----
    wire [3:0] strip_fault;
    integer    const_bad = 0, strip_words = 0;
    genvar k, p;
    generate for (k = 0; k < 4; k = k + 1) begin : g_stk
        reg [288:0] dn [0:LD-1];             // {credit, emf 288}
        reg [520:0] up [0:LD-1];             // {credit, emr 520}
        integer j;
        wire        o_v, i_cr;
        wire [522:0] o_d;
        wire [287:0] f = dn[LD-1][287:0];
        initial for (j = 0; j < LD; j = j + 1) begin dn[j] = 0; up[j] = 0; end
        always @(posedge ck) begin
            dn[0] <= {emf_cr[k], emf[k]};
            up[0] <= {i_cr, o_d[521:520], o_d[519], o_d[515:512], o_d[511:0], o_v};
            for (j = 1; j < LD; j = j + 1) begin dn[j] <= dn[j-1]; up[j] <= up[j-1]; end
            if (rst_n && o_v) begin
                strip_words = strip_words + 1;
                if (o_d[522] !== 1'b1 || o_d[518:516] !== 3'b000) const_bad = const_bad + 1;
            end
        end
        assign emr[k] = up[LD-1][519:0];
        assign emr_cr[k] = up[LD-1][520];
        wire [NPC-1:0] s_m, s_cr, w_m, e_rv; wire s_we; wire [4:0] s_bank, s_col; wire [18:0] s_row; wire [255:0] w_d;
        wire [NPC*258-1:0] e_rd;
        // the landing leaf's unpack: i_d = {class 1, kind, poison 0, 3'b0, sequence, data[511:281] = 0, data[280:0]}
        ot_qfd_emb_strip #(.STK(k)) u_strip (.clk(ck), .rst_n(rst_n),
            .i_v(f[0]), .i_d({1'b1, f[287:286], 1'b0, 3'b000, f[285:282], 231'd0, f[281:1]}), .i_cr(i_cr),
            .o_v(o_v), .o_d(o_d), .o_cr(dn[LD-1][288]),
            .s_m(s_m), .s_we(s_we), .s_bank(s_bank), .s_col(s_col), .s_row(s_row), .s_cr(s_cr), .w_m(w_m), .w_d(w_d),
            .e_v(e_rv), .e_d(e_rd), .fault(strip_fault[k]), .fault_code(), .ce_cnt(), .ue_info());
        for (p = 0; p < NPC; p = p + 1) begin : g_pc
            tb_emb_pc_model #(.DLY(7 + (p % 5))) u_pc (.clk(ck), .rst_n(rst_n), .s_v(s_m[p]), .s_we(s_we),
                .s_key({s_bank, s_col, s_row}), .w_d(w_d), .s_cr(s_cr[p]), .e_v(e_rv[p]), .e_d(e_rd[p*258 +: 258]));
        end
    end endgenerate
    // ---- drivers / checks ----
    integer seed = 20261013;
    integer errors = 0, early = 0, i, j, t, w, n_req = 0, n_cr = 0, n_rsp = 0, hbc = 4, eac = 32;
    integer boot_n = 0, lat_sum = 0, lat_max = 0, t0, ready_cyc = 0;
    reg [31:0] csum = 0;
    reg [17:0] toks [0:NT-1];
    reg [17:0] fq_t [0:NF*65-1];             // expected response order
    integer    fq_w [0:NF*65-1];
    integer    exp_n = 0;
    reg        scale_done [0:9495];
    always @(posedge ck) if (rst_n) begin
        if (hb_cr) hbc = hbc + 1;
        if (t_ecr) begin eac = eac + 1; n_cr = n_cr + 1; end
        if (t_eq[0]) begin
            if (!est[0]) early = early + 1;
            if (n_rsp >= exp_n) begin errors = errors + 1; $display("FAIL unexpected response %0d", n_rsp); end
            else if (t_eq[512:1] !== gword(fq_t[n_rsp], fq_w[n_rsp])) begin
                errors = errors + 1;
                if (errors < 6) $display("FAIL word %0d (token %0d w %0d): got %h exp %h", n_rsp, fq_t[n_rsp], fq_w[n_rsp],
                                         t_eq[64:1], gword(fq_t[n_rsp], fq_w[n_rsp]) & 512'hffffffffffffffff);
            end
            n_rsp = n_rsp + 1;
        end
    end
    task automatic hb_send(input en, input [24:0] e, input [255:0] d);
        begin
            @(negedge ck); while (hbc == 0) @(negedge ck);
            hb = {d, e, en, 1'b1}; hbc = hbc - 1;
            @(negedge ck); hb[0] = 1'b0;
        end
    endtask
    task automatic ea_send(input kind, input [23:0] a);
        begin
            @(negedge ck); while (eac == 0) @(negedge ck);
            r_ea = {a, kind, 1'b1}; eac = eac - 1; n_req = n_req + 1;
            @(negedge ck); r_ea[0] = 1'b0;
            if (($random(seed) & 7) == 0) repeat (($random(seed) & 3) + 1) @(negedge ck);
        end
    endtask
    task automatic fetch(input [17:0] tk);
        begin
            for (w = 0; w < 65; w = w + 1) begin fq_t[exp_n] = tk; fq_w[exp_n] = w; exp_n = exp_n + 1; end
            for (w = 0; w < 64; w = w + 1) ea_send(1'b0, {tk, 6'(w)});
            ea_send(1'b1, {6'd0, tk});
        end
    endtask
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 20261013;
        for (i = 0; i < 9496; i = i + 1) scale_done[i] = 1'b0;
        // tokens: spread over the vocabulary, rows and scale stacks (last row included)
        for (i = 0; i < NT; i = i + 1) toks[i] = (i == 0) ? 18'd0 : (i == 1) ? 18'd151935 : 18'(($random(seed) & 32'h7fffffff) % 151936);
        repeat (8) @(negedge ck); rst_n = 1; repeat (12) @(negedge ck);
        // the first token is requested BEFORE the load: it must wait for the boot check
        t0 = cyc;
        fork
            fetch(toks[0]);
            begin
                for (i = 0; i < NT; i = i + 1) begin
                    for (j = 0; j < 128; j = j + 1) begin
                        hb_send(1'b0, {toks[i], 7'd0} + 25'(j), gsec({toks[i], 7'd0} + 25'(j)));
                        csum = csum + crc_sector({toks[i], 7'd0} + 25'(j), gsec({toks[i], 7'd0} + 25'(j))); boot_n = boot_n + 1;
                    end
                    if (!scale_done[toks[i] >> 4]) begin
                        scale_done[toks[i] >> 4] = 1'b1;
                        hb_send(1'b0, E_SCALE + 25'(toks[i] >> 4), gsec(E_SCALE + 25'(toks[i] >> 4)));
                        csum = csum + crc_sector(E_SCALE + 25'(toks[i] >> 4), gsec(E_SCALE + 25'(toks[i] >> 4))); boot_n = boot_n + 1;
                    end
                end
                hb_send(1'b1, 25'd0, {192'd0, csum, 32'(boot_n)});
                $display("BOOT sent %0d sectors csum %h at cycle %0d", boot_n, csum, cyc);
            end
        join
        i = 0; while (!est[0] && !est[1] && i < 200000) begin @(negedge ck); i = i + 1; end
        ready_cyc = cyc;
        $display("BOOT emb_ready=%0d fault=%0d cause=%h at cycle %0d", est[0], est[1], est[12:2], cyc);
        if (!est[0]) errors = errors + 1;
        i = 0; while (n_rsp < 65 && i < 20000) begin @(negedge ck); i = i + 1; end
        for (t = 1; t < NF && !est[1]; t = t + 1) begin
            repeat (($random(seed) & 31)) @(negedge ck);
            t0 = cyc;
            fetch(toks[($random(seed) & 32'h7fffffff) % NT]);
            i = 0; while (n_rsp < exp_n && !est[1] && i < 20000) begin @(negedge ck); i = i + 1; end
            lat_sum = lat_sum + (cyc - t0); if (cyc - t0 > lat_max) lat_max = cyc - t0;
        end
        repeat (200) @(negedge ck);
        if (n_rsp != exp_n || n_cr != n_req) begin errors = errors + 1; $display("FAIL counts: rsp %0d of %0d, credits %0d of %0d", n_rsp, exp_n, n_cr, n_req); end
        if (early != 0) begin errors = errors + 1; $display("FAIL %0d responses before emb_ready", early); end
        if (est[1] || est[12:2] != 0) begin errors = errors + 1; $display("FAIL status fault cause %h", est[12:2]); end
        if (|strip_fault) begin errors = errors + 1; $display("FAIL strip fault %b", strip_fault); end
        if (const_bad != 0) begin errors = errors + 1; $display("FAIL %0d strip words with a non-constant dropped bit", const_bad); end
        if (errors == 0)
            $display("PASS kv_gwhost embgw tokens=%0d fetches=%0d words=%0d boot_sectors=%0d strip_words=%0d fetch_cycles_mean=%0d max=%0d (first request to last word, LD %0d, ideal PC model)",
                     NT, NF, n_rsp, boot_n, strip_words, lat_sum / (NF - 1), lat_max, LD);
        else $display("FAIL kv_gwhost embgw errors=%0d rsp=%0d/%0d", errors, n_rsp, exp_n);
        $finish;
    end
    initial begin #40000000; $display("FAIL kv_gwhost embgw timeout rsp=%0d/%0d cause=%h", n_rsp, exp_n, est[12:2]); $finish; end
endmodule
