`timescale 1ns/1ps
// W11: the core's key writer at FULL ring capacity (C = 65,568 slots a user a stack).
//
// ot_hdc_v41x_idx_pool_kwr (RING = 1, the die's writer in the ring layout) takes the
// SU's element writes of one key (the destination-3 store the core issues), encodes it
// and emits a record naming the key by (region base block, position) -- the WIDE record
// of ot_hdc_v41x_idx_ring_port (WIDE_REC = 1), with no 1,024-row limit.  The port places
// it (decode step, 48-key migration every 32nd count) through the four stacks' K ports
// (READ_FENCE = 1, as in the die); the pooled adapter's ring readers (ring ranges, four
// ot_hdc_v41x_idx_kstream_ring, the quarter join; the pooled adapter's ring arm) scan it back.
//
// Two users with 10-bit IDs, region base block KB + user x UBLK (UBLK = 1,090):
//   user UA: NA0 keys placed by the bench, then decode steps to NA1 through the writer:
//            positions 1,020 .. 1,059 -- ring slots past 1,024 (the second super-block);
//   user UB: NB0 keys placed by the bench, then steps to NB1: positions 65,560 .. 65,599 --
//            the quarter-3 ring WRAPS at 65,568 (slot 0 again; its scan reads two segments).
// Steps alternate between the users (two users' records interleave in the port's FIFO);
// after every step BOTH users are scanned in full and every key checked: bench-placed keys
// against their generator, written keys against the record the writer emitted.
module tb_w11_idx_ring_naming #(
    parameter integer AW=30, HW=23, RSB=64, RTAIL=32,
    parameter integer KB=7444668, MEM_WORDS=1055017,
    parameter integer UA=1, UB=865,
    parameter integer NA0=1020, NA1=1060, NB0=65560, NB1=65600,
    parameter integer WB=128, GA=120, CLK_PS=967,
    parameter integer WIDE=1          // 0: negative control -- the port decodes the legacy (block, row < 1,024) record
) (input wire clk, rst_n, cmd_v);
    localparam integer NPC=32, TAGW=16, LENW=4, BEATW=4, DW=256, NW=HW+10;
    localparam integer KAW=24;                        // the core's vector-memory address width
    localparam integer C = RSB*1024 + RTAIL;
    localparam integer UBLK = RSB*17 + ((RTAIL != 0) ? 1 + (RTAIL + 63) / 64 : 0);
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
    // element k of the key the SU writes for (user u, position p): BF16 values the E2M1 encoder takes
    // (block maximum exponent em, others em - 0..2, mantissa bits 5:0 zero; some zeros)
    function automatic [15:0] elem(input integer u, input integer p, input integer k);
        reg [31:0] r, rb;
        reg [7:0] em, e;
        begin
            rb = mix(32'(u) * 32'h2545F491 ^ 32'(p) * 32'h9E3779B1 ^ 32'(k / 32) * 32'h68E31DA4);
            em = 8'd100 + 8'(rb[4:0]);
            r = mix(32'(u) * 32'h27d4eb2f ^ 32'(p) * 32'h165667b1 ^ 32'(k) * 32'hd3a2646c);
            if (k % 32 == 0) e = em;
            else e = em - 8'(r[5:4] == 2'd3 ? 2'd0 : r[5:4]);
            elem = (k % 32 != 0 && r[3:0] == 4'd0) ? 16'd0 : {r[7], e, r[6], 6'd0};
        end
    endfunction

    wire [4*NPC-1:0] h_v, h_rdy, h_we, h_rsp_v, h_rsp_rdy, h_wr_done;
    wire [4*NPC*AW-1:0] h_addr;
    wire [4*NPC*LENW-1:0] h_len;
    wire [4*NPC*TAGW-1:0] h_tag, h_rsp_tag;
    wire [4*NPC*DW-1:0] h_wdata, h_rsp_data;
    wire [4*NPC*(DW/8)-1:0] h_wstrb;
    wire [4*NPC*BEATW-1:0] h_rsp_beat;
    wire [4*NPC-1:0] r_v, r_rdy, r_rsp_v, r_rsp_rdy;
    wire [4*NPC*AW-1:0] r_addr;
    wire [4*NPC*LENW-1:0] r_len;
    wire [4*NPC*TAGW-1:0] r_tag;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_stack
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(MEM_WORDS),.TAGW(TAGW),.LENW(LENW),
            .BEATW(BEATW),.QD(64),.RQD(32),.CLK_PS(CLK_PS),.REFPB(3),.MEM_MODE(0)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_v[s*NPC +:NPC]),.req_rdy(h_rdy[s*NPC +:NPC]),
            .req_addr(h_addr[s*NPC*AW +:NPC*AW]),.req_len(h_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_tag[s*NPC*TAGW +:NPC*TAGW]),.req_we(h_we[s*NPC +:NPC]),
            .req_wdata(h_wdata[s*NPC*DW +:NPC*DW]),.req_wstrb(h_wstrb[s*NPC*(DW/8) +:NPC*(DW/8)]),
            .wr_done(h_wr_done[s*NPC +:NPC]),.rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),.rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]));
    end endgenerate

    // ---------------- the core's key writer (RING record) ----------------
    reg          su_go;
    reg [AW-1:0] ubase_sec;
    reg [KAW-1:0] orow;
    reg [7:0]    kv_we;
    reg [8*KAW-1:0] kv_waddr;
    reg [8*32-1:0]  kv_wdata;
    wire w_v, w_rdy, kwr_fault;
    wire [3:0] w_mask;
    wire [AW-1:0] w_csec, w_ssec;
    wire [511:0] w_codes;
    wire [2:0] w_sslot;
    wire [31:0] w_scales, kwr_keys;
    ot_hdc_v41x_idx_pool_kwr #(.AW(KAW),.NW(16),.NL(8),.HAW(AW),.RING(1),.RING_UBLK(UBLK)) kwr (
        .clk(clk),.rst_n(rst_n),.cfg_ik_base(KAW'(0)),.i_user_base_sec(ubase_sec),.su_go(su_go),.i_dst(2'd3),
        .i_obase(KAW'(0)),.i_orow(orow),.i_nout(16'd1),.i_kdim(16'd128),.kv_we(kv_we),.kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata),.w_v(w_v),.w_rdy(w_rdy),.w_stack_mask(w_mask),.w_csec(w_csec),.w_codes(w_codes),
        .w_ssec(w_ssec),.w_sslot(w_sslot),.w_scales(w_scales),.fault(kwr_fault),.dbg_keys(kwr_keys));

    // ---------------- the ring K-port side (as in the die tile) ----------------
    wire         p_busy, p_fault;
    wire [31:0]  p_records, p_writes, p_hw, p_rstall, p_wstall;
    wire [47:0]  p_migs, p_copied;
    ot_hdc_v41x_idx_ring_port #(.NPC(NPC),.AW(AW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.RSB(RSB),
        .RTAIL(RTAIL),.RFQ(4),.READ_FENCE(1),.WIDE_REC(WIDE)) port (
        .clk(clk),.rst_n(rst_n),.w_v(w_v),.w_rdy(w_rdy),.w_csec(w_csec),.w_codes(w_codes),.w_ssec(w_ssec),
        .w_sslot(w_sslot),.w_scales(w_scales),.d_v(1'b0),.d_rdy(),.d_base('0),.d_n('0),.d_key('0),
        .r_v(r_v),.r_rdy(r_rdy),.r_addr(r_addr),.r_len(r_len),.r_tag(r_tag),.r_rsp_v(r_rsp_v),.r_rsp_rdy(r_rsp_rdy),
        .h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),.h_len(h_len),.h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),
        .h_wstrb(h_wstrb),.h_wr_done(h_wr_done),.h_rsp_v(h_rsp_v),.h_rsp_rdy(h_rsp_rdy),.h_rsp_tag(h_rsp_tag),
        .h_rsp_data(h_rsp_data),.busy(p_busy),.fault(p_fault),.dbg_records(p_records),.dbg_writes(p_writes),
        .dbg_fifo_highwater(p_hw),.dbg_read_stalls(p_rstall),.dbg_writer_stalls(p_wstall),
        .dbg_migrations(p_migs),.dbg_copied_sectors(p_copied));

    // ---------------- the pooled adapter's ring reader ----------------
    reg          scan_go;
    reg [HW-1:0] scan_base;
    reg [NW-1:0] scan_n;
    reg [9:0]    scan_user;
    wire [4*HW-1:0] g_base1, g_base2;
    wire [4*10-1:0] g_skip;
    wire [4*NW-1:0] g_n1, g_n2;
    wire g_fault;
    ot_hdc_v41x_idx_ring_ranges #(.HW(HW),.UW(1),.RSB(RSB),.RTAIL(RTAIL)) geo (
        .i_nkeys(scan_n),.i_user(1'b0),.cfg_key_base_block(scan_base),
        .o_base1(g_base1),.o_skip(g_skip),.o_n1(g_n1),.o_base2(g_base2),.o_n2(g_n2),.o_user_base(),.o_fault(g_fault));
    wire [3:0] s_busy, s_valid, s_ready;
    wire [4*16-1:0] s_kv;
    wire [4*16*544-1:0] s_key;
    wire [4*48-1:0] s_keys, s_beats;
    generate for (s = 0; s < 4; s = s + 1) begin : g_rd
        ot_hdc_v41x_idx_kstream_ring #(.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW),
            .LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
            .clk(clk),.rst_n(rst_n),.cmd_v(scan_go && (g_n1[s*NW +: NW] + g_n2[s*NW +: NW]) != 0),
            .cmd_base(g_base1[s*HW +: HW]),.cmd_skip(g_skip[s*10 +: 10]),.cmd_nkeys(g_n1[s*NW +: NW]),
            .cmd_base2(g_base2[s*HW +: HW]),.cmd_nkeys2(g_n2[s*NW +: NW]),.busy(s_busy[s]),
            .req_v(r_v[s*NPC +:NPC]),.req_rdy(r_rdy[s*NPC +:NPC]),.req_addr(r_addr[s*NPC*AW +:NPC*AW]),
            .req_len(r_len[s*NPC*LENW +:NPC*LENW]),.req_tag(r_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_v(r_rsp_v[s*NPC +:NPC]),.rsp_rdy(r_rsp_rdy[s*NPC +:NPC]),.rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),.rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_valid(s_valid[s]),.o_ready(s_ready[s]),.o_kv(s_kv[s*16 +:16]),.o_key(s_key[s*16*544 +:16*544]),
            .cnt_keys_streamed(s_keys[s*48 +:48]),.cnt_hbm_beats(s_beats[s*48 +:48]));
    end endgenerate
    wire j_busy, j_fault, out_valid;
    wire [63:0] out_kv, out_ref;
    wire [3:0] out_last;
    wire [64*544-1:0] out_key;
    ot_hdc_v41x_idx_quarter_join qjoin (
        .clk(clk),.rst_n(rst_n),.cmd_v(scan_go),.cmd_nkeys(30'(scan_n)),.cmd_skip(g_skip),
        .busy(j_busy),.fault(j_fault),.i_valid(s_valid),.i_ready(s_ready),.i_kv(s_kv),.i_key(s_key),
        .o_valid(out_valid),.o_ready(1'b1),.o_kv(out_kv),.o_last(out_last),.o_key(out_key),.o_ref(out_ref));

    // ---------------- bench placement of the first keys (ring layout) ----------------
    task automatic put(input integer st, input longint sec, input [255:0] d, input [31:0] strb);
        longint idx;
        reg [255:0] w;
        begin
            idx = sec % MEM_WORDS;
            case (st)
                0: w = g_stack[0].hm.mem[idx]; 1: w = g_stack[1].hm.mem[idx];
                2: w = g_stack[2].hm.mem[idx]; default: w = g_stack[3].hm.mem[idx];
            endcase
            for (integer b = 0; b < 32; b = b + 1) if (strb[b]) w[8*b +: 8] = d[8*b +: 8];
            case (st)
                0: g_stack[0].hm.mem[idx] = w; 1: g_stack[1].hm.mem[idx] = w;
                2: g_stack[2].hm.mem[idx] = w; default: g_stack[3].hm.mem[idx] = w;
            endcase
        end
    endtask
    task automatic preload(input integer u, input integer n);
        integer p, q, qs, t;
        longint ub, cs, ss;
        reg [543:0] k;
        begin
            qs = (n / 32) * 8; ub = longint'(KB) + longint'(u) * UBLK;
            for (p = 0; p < n; p = p + 1) begin
                q = (p < qs) ? 0 : (p < 2 * qs) ? 1 : (p < 3 * qs) ? 2 : 3;
                t = p % C; k = keygen(u, p);
                cs = (ub + 17 * (t / 1024) + 1 + (t % 1024) / 64) * 128 + 2 * (t % 64);
                ss = (ub + 17 * (t / 1024)) * 128 + (t % 1024) / 8;
                put(q, cs, k[255:0], 32'hffffffff);
                put(q, cs + 1, k[511:256], 32'hffffffff);
                put(q, ss, 256'(k[543:512]) << (32 * (t % 8)), 32'hf << (4 * (t % 8)));
            end
        end
    endtask

    // ---------------- sequencer + checker ----------------
    // written keys: the writer's record for (user index i, position NX0_i + j)
    reg [543:0] wkey [0:1][0:63];
    integer n [0:1];
    integer n0 [0:1];
    integer uid [0:1];
    localparam [3:0] T_PRE=0, T_GO=1, T_EL=2, T_ACC=3, T_FENCE=4, T_S=5, T_RUN=6, T_NEXT=7, T_END=8;
    reg [3:0] t;
    integer cycle = 0, beats = 0, checked = 0, qs, exp_beats, cur = 0, sc = 0, el = 0, steps = 0, scans = 0;
    integer wrap_scans = 0, past1024 = 0, keys_checked = 0, keys_written = 0;
    longint rb_e;
    reg [543:0] want;
    initial begin t = T_PRE; su_go = 0; kv_we = 0; scan_go = 0; ubase_sec = 0; orow = 0; end
    always @(posedge clk) if (rst_n) begin
        cycle <= cycle + 1;
        scan_go <= 0; su_go <= 0; kv_we <= 0;
        if (p_fault || j_fault || g_fault || kwr_fault)
            $fatal(1, "fault port=%b join=%b geometry=%b writer=%b", p_fault, j_fault, g_fault, kwr_fault);
        if (w_v && w_rdy) begin
            if (w_ssec !== AW'((longint'(KB) + longint'(uid[cur]) * UBLK) * 128) || w_csec !== AW'(n[cur]) ||
                w_sslot !== 3'd0)
                $fatal(1, "record names block %0d row %0d, expected user %0d position %0d", w_ssec >> 7, w_csec,
                       uid[cur], n[cur]);
            wkey[cur][n[cur] - n0[cur]] <= {w_scales, w_codes};
            keys_written <= keys_written + 1;
        end
        case (t)
        T_PRE: begin
            uid[0] = UA; uid[1] = UB; n0[0] = NA0; n0[1] = NB0; n[0] = NA0; n[1] = NB0;
            preload(UA, NA0); preload(UB, NB0);
            cur <= 0; t <= T_GO;
        end
        T_GO: begin      // the SU's destination-3 store of one key: the writer latches row and user base
            ubase_sec <= AW'((longint'(KB) + longint'(uid[cur]) * UBLK) * 128);
            orow <= KAW'(n[cur]); su_go <= 1; el <= 0; t <= T_EL;
            if (n[cur] % C >= 1024) past1024 <= past1024 + 1;
        end
        T_EL: begin      // 128 elements, 8 lanes a cycle, at rb + (row / 16) kdim 16 + row mod 16 + 16 k
            ubase_sec <= {AW{1'b1}};                  // the latched base must be used, not the live input
            rb_e = longint'(n[cur] / 16) * 128 * 16 + n[cur] % 16;
            for (integer l = 0; l < 8; l = l + 1) begin
                kv_we[l] <= 1'b1;
                kv_waddr[l*KAW +: KAW] <= KAW'(rb_e + 16 * (el + l));
                kv_wdata[32*l +: 32] <= {elem(uid[cur], n[cur], el + l), 16'd0};
            end
            el <= el + 8;
            if (el + 8 == 128) t <= T_ACC;
        end
        T_ACC: if (w_v && w_rdy) begin n[cur] = n[cur] + 1; steps <= steps + 1; t <= T_FENCE; end
        T_FENCE: if (!p_busy && !w_v) begin sc <= 0; t <= T_S; end
        T_S: begin       // scan user sc at its count
            scan_base <= HW'(longint'(KB) + longint'(uid[sc]) * UBLK); scan_n <= NW'(n[sc]);
            scan_user <= 10'(uid[sc]);
            scan_go <= 1; beats <= 0; checked <= 0;
            qs = (n[sc] / 32) * 8; exp_beats = (n[sc] - 3 * qs + 15) / 16;
            if (n[sc] > C) wrap_scans <= wrap_scans + 1;
            t <= T_RUN;
        end
        T_RUN: begin
            if (out_valid) begin : chk
                integer hits, ql, pp, pos;
                hits = 0;
                for (integer a = 0; a < 4; a = a + 1) begin
                    ql = (a == 3) ? n[sc] - 3 * qs : qs;
                    if (out_last[a] !== ((ql == 0) ? (beats == 0) : (beats == (ql - 1) / 16))) $fatal(1, "last");
                    for (integer b = 0; b < 16; b = b + 1) begin
                        pp = beats * 16 + b;
                        if (out_kv[a*16+b] !== (pp < ql)) $fatal(1, "mask beat=%0d q=%0d lane=%0d", beats, a, b);
                        if (pp < ql) begin
                            pos = a * qs + pp;
                            want = (pos < n0[sc]) ? keygen(uid[sc], pos) : wkey[sc][pos - n0[sc]];
                            if (out_key[(a*16+b)*544 +: 544] !== want)
                                $fatal(1, "key user=%0d count=%0d position=%0d slot=%0d", uid[sc], n[sc], pos, pos % C);
                            if (out_ref[a*16+b] !== ref_key(want[543:512])) $fatal(1, "ref");
                            hits = hits + 1;
                        end else if (out_key[(a*16+b)*544 +: 544] !== 544'd0) $fatal(1, "padding");
                    end
                end
                beats <= beats + 1; checked <= checked + hits;
                if (beats + 1 == exp_beats) t <= T_NEXT;
            end
        end
        T_NEXT: begin
            if (checked != n[sc]) $fatal(1, "scan user %0d checked %0d of %0d", uid[sc], checked, n[sc]);
            scans <= scans + 1; keys_checked <= keys_checked + checked;
            if (sc == 0) begin sc <= 1; t <= T_S; end
            else if (n[0] == NA1 && n[1] == NB1) t <= T_END;
            else begin
                // alternate users; a user at its final count sits out
                if (cur == 0) cur <= (n[1] < NB1) ? 1 : 0; else cur <= (n[0] < NA1) ? 0 : 1;
                t <= T_GO;
            end
        end
        T_END: begin
            $display("W11_NAMING users=%0d,%0d counts=%0d,%0d steps=%0d writer_keys=%0d records=%0d migrations=%0d copied_sectors=%0d",
                     UA, UB, n[0], n[1], steps, kwr_keys, p_records, p_migs, p_copied);
            $display("W11_NAMING_SCANS scans=%0d keys_checked=%0d wrap_scans=%0d steps_slot_past_1024=%0d fifo_highwater=%0d",
                     scans, keys_checked, wrap_scans, past1024, p_hw);
            $display("W11_NAMING_PASS cycles=%0d", cycle);
            $finish;
        end
        default: ;
        endcase
    end
endmodule
