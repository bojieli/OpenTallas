`timescale 1ns/1ps
// W11 quarter-per-stack ring layout: write -> migrate -> read-back gate.
//
// Keys of NU users are written through ot_hdc_v41x_idx_ring_kwr into four
// timed HBM models with backing storage (MEM_MODE 0): optionally a prefill
// (op PLACE) to PREFILL_N keys each, then decode steps (op STEP, users in
// round robin) up to NMAX keys each, every 32nd step migrating 48 keys a
// stack down.  At each checkpoint count CHK0..CHK3 (and at NMAX) every user is
// scanned by four ot_hdc_v41x_idx_kstream_ring readers (geometry from
// ot_hdc_v41x_idx_ring_ranges) joined by ot_hdc_v41x_idx_quarter_join, and
// every key, lane mask, last flag and refusal bit of every beat is checked
// against keygen(user, position).  Every HBM request is checked to fall in the
// active user's region (block in [KB + u UBLK, KB + (u+1) UBLK)), computed here
// independently with 64-bit integers, and the reader's sector count per scan
// is checked.  Writer and readers own the HBM ports in alternate phases.
module tb_w11_idx_ring_gate #(
    parameter integer AW=28, HW=21, UW=10, RSB=2, RTAIL=32,
    parameter integer KB=1000, MEM_WORDS=65521,
    parameter integer NU=2, U0=0, U1=5, U2=0, U3=0,
    parameter integer PREFILL_N=0, NMAX=8223,
    parameter integer CHK0=65, CHK1=1040, CHK2=4127, CHK3=0,
    parameter integer WB=128, GA=120, CLK_PS=967
) (input wire clk, rst_n, cmd_v);
    localparam integer NPC=32, TAGW=16, LENW=4, BEATW=4, DW=256, NW=HW+10;
    localparam integer C = RSB*1024 + RTAIL;
    localparam integer UBLK = RSB*17 + ((RTAIL != 0) ? 1 + (RTAIL + 63) / 64 : 0);

    function automatic integer user_id(input integer i);
        user_id = (i == 0) ? U0 : (i == 1) ? U1 : (i == 2) ? U2 : U3;
    endfunction
    function automatic bit is_chk(input integer n);
        is_chk = (n == NMAX) || (n != 0 && (n == CHK0 || n == CHK1 || n == CHK2 || n == CHK3));
    endfunction
    function automatic [31:0] mix(input [31:0] x);
        reg [31:0] y;
        begin y = x ^ (x >> 16); y = y * 32'h7feb352d; y = y ^ (y >> 15); y = y * 32'h846ca68b; mix = y ^ (y >> 16); end
    endfunction
    function automatic [543:0] keygen(input integer u, input integer p);
        integer w;
        begin
            for (w = 0; w < 17; w = w + 1) keygen[32*w +: 32] = mix(32'(u) * 32'h01000193 ^ 32'(p) * 32'h9E3779B1 ^ 32'(w) * 32'h85ebca6b);
        end
    endfunction
    function automatic ref_key(input [31:0] scale);
        ref_key = (scale[7:0] >= 253 || scale[15:8] >= 253 || scale[23:16] >= 253 || scale[31:24] >= 253);
    endfunction

    // ---------------- HBM, phase mux ----------------
    reg rd_phase;
    wire [4*NPC-1:0] h_req_v, h_req_rdy, h_req_we, h_rsp_v, h_rsp_rdy, h_wr_done;
    wire [4*NPC*AW-1:0] h_req_addr;
    wire [4*NPC*LENW-1:0] h_req_len;
    wire [4*NPC*TAGW-1:0] h_req_tag, h_rsp_tag;
    wire [4*NPC*DW-1:0] h_req_wdata, h_rsp_data;
    wire [4*NPC*(DW/8)-1:0] h_req_wstrb;
    wire [4*NPC*BEATW-1:0] h_rsp_beat;
    // writer
    wire [4*NPC-1:0] w_req_v, w_req_we, w_rsp_rdy;
    wire [4*NPC*AW-1:0] w_req_addr;
    wire [4*NPC*LENW-1:0] w_req_len;
    wire [4*NPC*TAGW-1:0] w_req_tag;
    wire [4*NPC*DW-1:0] w_req_wdata;
    wire [4*NPC*(DW/8)-1:0] w_req_wstrb;
    // readers
    wire [4*NPC-1:0] r_req_v, r_rsp_rdy;
    wire [4*NPC*AW-1:0] r_req_addr;
    wire [4*NPC*LENW-1:0] r_req_len;
    wire [4*NPC*TAGW-1:0] r_req_tag;
    assign h_req_v     = rd_phase ? r_req_v : w_req_v;
    assign h_req_addr  = rd_phase ? r_req_addr : w_req_addr;
    assign h_req_len   = rd_phase ? r_req_len : w_req_len;
    assign h_req_tag   = rd_phase ? r_req_tag : w_req_tag;
    assign h_req_we    = rd_phase ? '0 : w_req_we;
    assign h_req_wdata = w_req_wdata;
    assign h_req_wstrb = w_req_wstrb;
    assign h_rsp_rdy   = rd_phase ? r_rsp_rdy : w_rsp_rdy;

    reg dump = 0;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_stack
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(MEM_WORDS),
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(64),.RQD(32),.CLK_PS(CLK_PS),
            .REFPB(3),.MEM_MODE(0)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_req_v[s*NPC +:NPC]),
            .req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .req_we(h_req_we[s*NPC +:NPC]),.req_wdata(h_req_wdata[s*NPC*DW +:NPC*DW]),
            .req_wstrb(h_req_wstrb[s*NPC*(DW/8) +:NPC*(DW/8)]),.wr_done(h_wr_done[s*NPC +:NPC]),
            .rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]));
        always @(posedge clk) if (dump) begin : g_dump
            longint rd, wr, act, conf, refs;
            rd = 0; wr = 0; act = 0; conf = 0; refs = 0;
            for (integer p = 0; p < NPC; p = p + 1) begin
                rd += hm.st_rd[p]; wr += hm.st_wr[p]; act += hm.st_act[p]; conf += hm.st_conf[p]; refs += hm.st_ref[p];
            end
            $display("W11_RING_STACK s=%0d rd=%0d wr=%0d act=%0d conf=%0d ref=%0d", s, rd, wr, act, conf, refs);
        end
    end endgenerate

    // ---------------- writer ----------------
    reg          c_v, c_op;
    reg [UW-1:0] c_user;
    reg [NW-1:0] c_n, c_pos;
    reg [543:0]  c_key;
    wire         c_rdy, w_busy, w_fault;
    wire [47:0]  w_keys, w_migs, w_copied;
    ot_hdc_v41x_idx_ring_kwr #(.NPC(NPC),.AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),
        .DW(DW),.UW(UW),.RSB(RSB),.RTAIL(RTAIL)) wr_u (
        .clk(clk),.rst_n(rst_n),.cfg_key_base_block(HW'(KB)),
        .c_v(c_v),.c_rdy(c_rdy),.c_op(c_op),.c_user(c_user),.c_n(c_n),.c_pos(c_pos),.c_key(c_key),
        .busy(w_busy),.fault(w_fault),
        .h_req_v(w_req_v),.h_req_rdy(h_req_rdy),.h_req_addr(w_req_addr),.h_req_len(w_req_len),
        .h_req_tag(w_req_tag),.h_req_we(w_req_we),.h_req_wdata(w_req_wdata),.h_req_wstrb(w_req_wstrb),
        .h_wr_done(h_wr_done),.h_rsp_v(h_rsp_v & {4*NPC{!rd_phase}}),.h_rsp_rdy(w_rsp_rdy),
        .h_rsp_tag(h_rsp_tag),.h_rsp_data(h_rsp_data),
        .cnt_keys(w_keys),.cnt_migrations(w_migs),.cnt_copied_sectors(w_copied));

    // ---------------- readers + join ----------------
    reg          scan_go;
    reg [UW-1:0] scan_user;
    reg [NW-1:0] scan_n;
    wire [4*HW-1:0] g_base1, g_base2;
    wire [4*10-1:0] g_skip;
    wire [4*NW-1:0] g_n1, g_n2;
    wire [HW-1:0] g_ub;
    wire g_fault;
    ot_hdc_v41x_idx_ring_ranges #(.HW(HW),.UW(UW),.RSB(RSB),.RTAIL(RTAIL)) geo (
        .i_nkeys(scan_n),.i_user(scan_user),.cfg_key_base_block(HW'(KB)),
        .o_base1(g_base1),.o_skip(g_skip),.o_n1(g_n1),.o_base2(g_base2),.o_n2(g_n2),
        .o_user_base(g_ub),.o_fault(g_fault));
    wire [3:0] s_busy, s_valid, s_ready;
    wire [4*16-1:0] s_kv;
    wire [4*16*544-1:0] s_key;
    wire [4*48-1:0] s_keys, s_beats;
    generate for (s = 0; s < 4; s = s + 1) begin : g_rd
        ot_hdc_v41x_idx_kstream_ring #(.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW),
            .LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
            .clk(clk),.rst_n(rst_n),
            .cmd_v(scan_go && (g_n1[s*NW +: NW] + g_n2[s*NW +: NW]) != 0),
            .cmd_base(g_base1[s*HW +: HW]),.cmd_skip(g_skip[s*10 +: 10]),.cmd_nkeys(g_n1[s*NW +: NW]),
            .cmd_base2(g_base2[s*HW +: HW]),.cmd_nkeys2(g_n2[s*NW +: NW]),.busy(s_busy[s]),
            .req_v(r_req_v[s*NPC +:NPC]),.req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(r_req_addr[s*NPC*AW +:NPC*AW]),.req_len(r_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(r_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_v(h_rsp_v[s*NPC +:NPC] & {NPC{rd_phase}}),.rsp_rdy(r_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),.rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_valid(s_valid[s]),.o_ready(s_ready[s]),.o_kv(s_kv[s*16 +:16]),.o_key(s_key[s*16*544 +:16*544]),
            .cnt_keys_streamed(s_keys[s*48 +:48]),.cnt_hbm_beats(s_beats[s*48 +:48]));
    end endgenerate
    wire j_busy, j_fault, out_valid;
    wire [63:0] out_kv, out_ref;
    wire [3:0] out_last;
    wire [64*544-1:0] out_key;
    ot_hdc_v41x_idx_quarter_join join_u (
        .clk(clk),.rst_n(rst_n),.cmd_v(scan_go),.cmd_nkeys(30'(scan_n)),.cmd_skip(g_skip),
        .busy(j_busy),.fault(j_fault),.i_valid(s_valid),.i_ready(s_ready),.i_kv(s_kv),.i_key(s_key),
        .o_valid(out_valid),.o_ready(1'b1),.o_kv(out_kv),.o_last(out_last),.o_key(out_key),.o_ref(out_ref));

    // ---------------- address monitor ----------------
    integer act_user;
    longint max_sec = 0, n_req = 0;
    always @(posedge clk) if (rst_n) begin
        for (integer i = 0; i < 4*NPC; i = i + 1)
            if (h_req_v[i] && h_req_rdy[i]) begin : mon
                longint sec, lo, hi;
                sec = longint'(h_req_addr[i*AW +: AW]);
                lo = (longint'(KB) + longint'(act_user) * UBLK) * 128;
                hi = lo + longint'(UBLK) * 128;
                if (sec < lo || sec + longint'(h_req_len[i*LENW +: LENW]) > hi)
                    $fatal(1, "address %0d outside user %0d region [%0d,%0d) port %0d t=%0d ui=%0d n=%0d wst=%0d we=%0b", sec, act_user, lo, hi, i, t, ui, n, wr_u.st, h_req_we[i]);
                if (sec > max_sec) max_sec <= sec;
                n_req <= n_req + 1;
            end
    end

    // ---------------- sequencer + checker ----------------
    localparam [3:0] T_PRE=0, T_STEP=1, T_RWAIT=2, T_RGO=3, T_RRUN=4, T_RNEXT=5, T_END=6;
    reg [3:0] t;
    integer ui = 0, n = 0, pos = 0, ri = 0, cycle = 0, reads = 0, checked = 0, beats = 0;
    integer exp_beats, qs, sectors0, exp_sectors, finish_wait = 0;
    integer total_checked = 0, total_scans = 0, wrapped_scans = 0;
    reg [543:0] want;
    function automatic integer seg_sectors(input integer lo, input integer cnt);
        seg_sectors = (cnt == 0) ? 0 : 2 * cnt + (lo + cnt + 7) / 8 - lo / 8;
    endfunction
    always @* begin
        c_v = 0; c_op = 0; c_user = 0; c_n = 0; c_pos = 0; c_key = 0;
        if (t == T_PRE) begin
            c_v = 1; c_op = 1; c_user = UW'(user_id(ui)); c_n = NW'(PREFILL_N); c_pos = NW'(pos);
            c_key = keygen(user_id(ui), pos);
        end else if (t == T_STEP) begin
            c_v = 1; c_op = 0; c_user = UW'(user_id(ui)); c_n = NW'(n); c_key = keygen(user_id(ui), n);
        end
    end
    initial begin t = (PREFILL_N > 0) ? T_PRE : T_STEP; n = PREFILL_N; rd_phase = 0; scan_go = 0; act_user = U0; end
    always @(posedge clk) if (rst_n) begin
        cycle <= cycle + 1;
        scan_go <= 0;
        if (w_fault || j_fault || g_fault) $fatal(1, "fault writer=%b join=%b geometry=%b n=%0d", w_fault, j_fault, g_fault, n);
        case (t)
        T_PRE: begin
            if (c_rdy) act_user <= user_id(ui);
            if (c_v && c_rdy) begin
                if (pos + 1 == PREFILL_N) begin
                    pos <= 0;
                    if (ui + 1 == NU) begin ui <= 0; t <= is_chk(n) ? T_RWAIT : T_STEP; ri <= 0; end
                    else ui <= ui + 1;
                end else pos <= pos + 1;
            end
        end
        T_STEP: begin
            if (c_rdy) act_user <= user_id(ui);
            if (n >= NMAX) t <= T_END;
            else if (c_v && c_rdy) begin
                if (ui + 1 == NU) begin
                    ui <= 0; n <= n + 1;
                    if (is_chk(n + 1)) begin t <= T_RWAIT; ri <= 0; end
                end else ui <= ui + 1;
            end
        end
        T_RWAIT: if (!w_busy && c_rdy) begin
            rd_phase <= 1; scan_user <= UW'(user_id(ri)); scan_n <= NW'(n); act_user <= user_id(ri);
            t <= T_RGO;
        end
        T_RGO: begin
            scan_go <= 1; beats <= 0; checked <= 0;
            qs = (n / 32) * 8;
            exp_beats = (n - 3 * qs + 15) / 16;
            exp_sectors = 0;
            for (integer a = 0; a < 4; a = a + 1) begin
                exp_sectors += seg_sectors(int'(g_skip[a*10 +: 10]), int'(g_n1[a*NW +: NW]));
                exp_sectors += seg_sectors(0, int'(g_n2[a*NW +: NW]));
                if (g_n2[a*NW +: NW] != 0) wrapped_scans <= wrapped_scans + 1;
            end
            sectors0 = int'(s_beats[0 +: 48] + s_beats[48 +: 48] + s_beats[96 +: 48] + s_beats[144 +: 48]);
            t <= T_RRUN;
        end
        T_RRUN: begin
            if (out_valid) begin : chk
                integer hits, ql, pp;
                hits = 0;
                for (integer a = 0; a < 4; a = a + 1) begin
                    ql = (a == 3) ? n - 3 * qs : qs;
                    if (out_last[a] !== ((ql == 0) ? (beats == 0) : (beats == (ql - 1) / 16)))
                        $fatal(1, "last user=%0d n=%0d beat=%0d q=%0d", user_id(ri), n, beats, a);
                    for (integer b = 0; b < 16; b = b + 1) begin
                        pp = beats * 16 + b;
                        if (out_kv[a*16+b] !== (pp < ql)) $fatal(1, "mask user=%0d n=%0d beat=%0d q=%0d lane=%0d", user_id(ri), n, beats, a, b);
                        if (pp < ql) begin
                            want = keygen(user_id(ri), a * qs + pp);
                            if (out_key[(a*16+b)*544 +: 544] !== want)
                                $fatal(1, "key user=%0d n=%0d position=%0d (q=%0d beat=%0d lane=%0d)", user_id(ri), n, a*qs+pp, a, beats, b);
                            if (out_ref[a*16+b] !== ref_key(want[543:512])) $fatal(1, "ref user=%0d position=%0d", user_id(ri), a*qs+pp);
                            hits = hits + 1;
                        end else if (out_key[(a*16+b)*544 +: 544] !== 544'd0 || out_ref[a*16+b] !== 0)
                            $fatal(1, "padding user=%0d n=%0d beat=%0d", user_id(ri), n, beats);
                    end
                end
                beats <= beats + 1; checked <= checked + hits;
            end
            if (scan_go == 0 && !out_valid && !j_busy && s_busy == 0 && beats == exp_beats) t <= T_RNEXT;
        end
        T_RNEXT: begin
            if (checked != n) $fatal(1, "user %0d n=%0d checked %0d", user_id(ri), n, checked);
            if (int'(s_beats[0 +: 48] + s_beats[48 +: 48] + s_beats[96 +: 48] + s_beats[144 +: 48]) - sectors0 != exp_sectors)
                $fatal(1, "sectors user=%0d n=%0d got=%0d expected=%0d", user_id(ri), n,
                       int'(s_beats[0 +: 48] + s_beats[48 +: 48] + s_beats[96 +: 48] + s_beats[144 +: 48]) - sectors0, exp_sectors);
            $display("W11_RING_READ user=%0d n=%0d checked=%0d sectors=%0d wrap_n2=%0d,%0d,%0d,%0d cycle=%0d",
                     user_id(ri), n, checked, exp_sectors, g_n2[0 +: NW], g_n2[NW +: NW], g_n2[2*NW +: NW], g_n2[3*NW +: NW], cycle);
            total_checked <= total_checked + checked; total_scans <= total_scans + 1;
            if (ri + 1 == NU) begin
                rd_phase <= 0; t <= (n >= NMAX) ? T_END : T_STEP; ri <= 0;
            end else begin ri <= ri + 1; t <= T_RWAIT; end
        end
        T_END: begin
            if (finish_wait == 0) dump <= 1; else dump <= 0;
            finish_wait <= finish_wait + 1;
            if (finish_wait == 2) begin
                $display("W11_RING_WRITER keys=%0d migrations=%0d copied_sectors=%0d", w_keys, w_migs, w_copied);
                $display("W11_RING_MON requests=%0d max_sector=%0d", n_req, max_sec);
                $display("W11_RING_CONFIG aw=%0d hw=%0d uw=%0d rsb=%0d rtail=%0d c=%0d ublk=%0d kb=%0d mem_words=%0d nu=%0d users=%0d,%0d,%0d,%0d prefill=%0d nmax=%0d",
                         AW, HW, UW, RSB, RTAIL, C, UBLK, KB, MEM_WORDS, NU, U0, U1, U2, U3, PREFILL_N, NMAX);
                $display("W11_RING_PASS scans=%0d wrapped_stack_scans=%0d checked=%0d cycles=%0d", total_scans, wrapped_scans, total_checked, cycle);
                $finish;
            end
        end
        default: ;
        endcase
    end
endmodule
