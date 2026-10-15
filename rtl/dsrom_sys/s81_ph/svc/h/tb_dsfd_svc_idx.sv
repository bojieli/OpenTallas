`timescale 1ns/1ps
// CLAUDE s81-svcq-1011 [svcq-idx]: transaction-level exact gate + throughput bench of ot_s81_svcq_idx (one S81 svc
// slab's index reader, stack ST) on the golden vectors of tools/s81_svcq/idx_vectors.py (hdc_golden_v41 Model.indexer
// chunk8 arithmetic, W11 ring layout).  The stack is the timing-faithful refresh-aware model ot_hdc_v41x_idx_hbm
// (32 PCs, REFPB 3, QD 64, RQD 32, at the 1.2 GHz stream clock CLK_PS 833) preloaded with the user's ring image
// (exactly tb_w11_idx_ring_naming's placement).  The bench is the VM: it sends a foreign frame, an IDX_Q addressed to
// another quadrant (mask bit 0 clear: must be skipped) and the real IDX_Q, valid-only with random gaps; x is drained
// with random back-pressure.  Checked: HDR (type, tag, base = q Qs - skip % 16, k, qslot); every BEAT's lane-valid
// mask = exactly the quarter's positions (lane i = cur + i, cur += 16), every valid lane's BF16 score bit-exact,
// last on exactly the final beat, nothing after it, no fault.  Prints SVCQIDX ... verdict=PASS|FAIL.
// CLAUDE s81die-1011/ctrl svch: the same gate on the hardened TILE dsfd_svc_idx (its 32 A credit lanes served by
// a per-PC lane adapter = the quadrant PC slice's contract: request receiver FIFO, issue only with landing room
// reserved (DRA 64 beats), valid-only responses, landing credits back) -> the same HBM model.
module tb_dsfd_svc_idx (input wire clk);
    parameter integer ST = 3;
    parameter integer NKEYMAX = 65536;
    parameter integer MAXCYC = 400000;
    localparam integer NPC = 32, AW = 30, TAGW = 16, LENW = 4, BEATW = 4, DW = 256;
    localparam integer RSB = 64, RTAIL = 32, C = RSB * 1024 + RTAIL, UBLK = RSB * 17 + 2, MEM_WORDS = 279040;
    reg [31:0] cfg [0:15];
    reg [511:0] qm [0:63];
    reg [543:0] km [0:NKEYMAX-1];
    reg [16:0] em [0:NKEYMAX-1];
    reg [1023:0] dir;
    integer seed = 1, gap = 15, xbp = 20;
    integer N, KB, USER, K, QS0, L, SKIP;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        if ($value$plusargs("seed=%d", seed)) ;
        if ($value$plusargs("gap=%d", gap)) ;
        if ($value$plusargs("xbp=%d", xbp)) ;
        $readmemh({dir, "/cfg.hex"}, cfg);
        $readmemh({dir, "/q.hex"}, qm);
        $readmemh({dir, "/keys.hex"}, km);
        $readmemh({dir, "/exp.hex"}, em);
        N = cfg[0]; KB = cfg[1]; USER = cfg[2]; K = cfg[3]; QS0 = cfg[5]; L = cfg[6]; SKIP = cfg[7];
        if (cfg[4] != ST) begin $display("SVCQIDX case ST %0d != bench ST %0d verdict=FAIL", cfg[4], ST); $finish; end
        void'($urandom(seed));
    end
    reg rst_n = 0;
    integer cyc = 0;
    // ---------------- DUT + HBM ----------------
    reg q_v = 0; reg [511:0] q_d = 0;
    wire [NPC-1:0] req_v, req_rdy, rsp_v, rsp_rdy, wr_done;
    wire [NPC*AW-1:0] req_addr; wire [NPC*LENW-1:0] req_len; wire [NPC*TAGW-1:0] req_tag, rsp_tag;
    wire [NPC*BEATW-1:0] rsp_beat; wire [NPC*DW-1:0] rsp_data;
    wire x_v; wire [511:0] x_d; reg x_r = 0; wire busy, fault; wire [7:0] fault_code;
    wire [NPC-1:0] aq_v, aq_c, ar_c; reg [NPC-1:0] ar_v; wire [NPC*50-1:0] aq_d; reg [NPC*276-1:0] ar_d;
    wire fo;
    assign busy = 1'b0; assign fault = fo; assign fault_code = 8'd0;
    dsfd_svc_idx #(.ST(ST)) dut (.ck(clk), .rst(rst_n), .q({1'b0, 1'b1, q_d, q_v}), .a1_v(), .a1_d(), .a1_r(1'b1),
        .x_v(x_v), .x_d(x_d), .x_r(x_r), .aq_v(aq_v), .aq_d(aq_d), .aq_c(aq_c), .ar_v(ar_v), .ar_d(ar_d), .ar_c(ar_c), .fo(fo));
    genvar gpp;
    generate for (gpp = 0; gpp < NPC; gpp = gpp + 1) begin : g_ad
        localparam integer NR = (gpp / 8 == 0) ? 7 : (gpp / 8 == 3) ? 8 : 3;
        wire o_v; wire [49:0] o_d; wire ovf; integer resv = 0;
        wire room = resv + o_d[49:46] <= 64;
        ot_s81_svch_crx #(.W(50), .DEPTH(2 * NR + 8)) u_rx (.clk(clk), .rst_n(rst_n), .i_v(aq_v[gpp]), .i_d(aq_d[gpp*50 +: 50]),
            .o_v(o_v), .o_r(req_rdy[gpp] && room), .o_d(o_d), .c_out(aq_c[gpp]), .ovf(ovf));
        assign req_v[gpp] = o_v && room;
        assign req_addr[gpp*AW +: AW] = o_d[45:16]; assign req_len[gpp*LENW +: LENW] = o_d[49:46];
        assign req_tag[gpp*TAGW +: TAGW] = o_d[15:0];
        assign rsp_rdy[gpp] = 1'b1;
        always @(posedge clk) begin
            ar_v[gpp] <= rsp_v[gpp];
            ar_d[gpp*276 +: 276] <= {rsp_tag[gpp*TAGW +: TAGW], rsp_beat[gpp*BEATW +: BEATW], rsp_data[gpp*DW +: DW]};
            resv = resv + ((req_v[gpp] && req_rdy[gpp]) ? 32'(o_d[49:46]) : 0) - 32'(ar_c[gpp]);
        end
    end endgenerate
    ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .DW(DW), .MEM_WORDS(MEM_WORDS), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
                          .QD(64), .RQD(32), .CLK_PS(833), .REFPB(3), .MEM_MODE(0)) hm (
        .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len),
        .req_tag(req_tag), .req_we({NPC{1'b0}}), .req_wdata({NPC*DW{1'b0}}), .req_wstrb({NPC*DW/8{1'b0}}),
        .wr_done(wr_done), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data));

    // ---------------- ring image (tb_w11_idx_ring_naming placement) ----------------
    integer reqs_out_of_region = 0;
    task automatic place();
        integer i, p, t; longint ub, cs, ss; reg [255:0] w;
        begin
            ub = longint'(KB) + longint'(USER) * UBLK;
            for (i = 0; i < L; i = i + 1) begin
                p = QS0 + i; t = p % C;
                cs = (ub + 17 * (t / 1024) + 1 + (t % 1024) / 64) * 128 + 2 * (t % 64);
                ss = (ub + 17 * (t / 1024)) * 128 + (t % 1024) / 8;
                hm.mem[cs % MEM_WORDS] = km[i][255:0];
                hm.mem[(cs + 1) % MEM_WORDS] = km[i][511:256];
                w = hm.mem[ss % MEM_WORDS];
                w[32 * (t % 8) +: 32] = km[i][543:512];
                hm.mem[ss % MEM_WORDS] = w;
            end
        end
    endtask

    // ---------------- q frames ----------------
    reg [511:0] qw [0:200];
    integer nq = 0, qi = 0;
    function automatic [511:0] hdr(input [3:0] typ, input [3:0] mask, input [11:0] len, input [448:0] spec);
        hdr = {typ, 1'b0, mask, 8'hc3, 3'd0, len, 21'd0, 10'(USER), spec};
    endfunction
    task automatic build();
        reg [448:0] sp; integer i;
        begin
            qw[nq] = hdr(4'd1, 4'b0001, 12'd3, 449'd0); nq = nq + 1;          // another engine's frame
            for (i = 0; i < 3; i = i + 1) begin qw[nq] = {16{32'hdead0000 + i}}; nq = nq + 1; end
            sp = 0; sp[32:0] = 33'd7; sp[65:56] = 10'd9;
            qw[nq] = hdr(4'd4, 4'b0010, 12'd64, sp); nq = nq + 1;            // IDX_Q for another quadrant
            for (i = 0; i < 64; i = i + 1) begin qw[nq] = ~qm[i]; nq = nq + 1; end
            sp = 0; sp[32:0] = 33'(N); sp[55:33] = 23'(KB); sp[65:56] = 10'(K);
            qw[nq] = hdr(4'd4, 4'b0001, 12'd64, sp); nq = nq + 1;
            for (i = 0; i < 64; i = i + 1) begin qw[nq] = qm[i]; nq = nq + 1; end
        end
    endtask

    // ---------------- checker ----------------
    integer words = 0, beats = 0, exp_beats, checked = 0, errs = 0, lastn = 0, after_last = 0, hdr_ok = 0;
    integer cur, base_exp, first_beat_cyc = -1, last_cyc = -1, idx_hdr_cyc = -1, keys_valid = 0;
    integer i, p, done_cyc = -1;
    reg [15:0] lv_exp;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 1) begin place(); build(); end
        if (cyc == 3) rst_n <= 1;
        q_v <= 0;
        if (rst_n && cyc > 8 && qi < nq && ($urandom % 100) >= gap) begin
            q_v <= 1; q_d <= qw[qi];
            if (qi == nq - 65) idx_hdr_cyc = cyc;
            qi = qi + 1;
        end
        x_r <= ($urandom % 100) >= xbp;
        if (x_v && x_r) begin
            words = words + 1;
            if (lastn > 0) after_last = after_last + 1;
            if (words == 1) begin
                base_exp = QS0 - (SKIP % 16);
                if (L == 0) base_exp = QS0;
                if (x_d[511:508] == 4'd1 && x_d[507:500] == 8'hc3 && x_d[19:0] == 20'(base_exp) && x_d[29:20] == 10'(K) &&
                    x_d[31:30] == 2'(ST) && x_d[499:32] == 0) hdr_ok = 1;
                else begin errs = errs + 1; $display("HDR bad: %h (exp base %0d)", x_d[63:0], base_exp); end
                cur = x_d[19:0];
            end else begin
                if (x_d[511:508] != 4'd2 || x_d[507:500] != 8'hc3 || x_d[499:273] != 0) begin
                    errs = errs + 1; if (errs < 8) $display("BEAT format bad at word %0d", words);
                end
                if (first_beat_cyc < 0) first_beat_cyc = cyc;
                last_cyc = cyc;
                for (i = 0; i < 16; i = i + 1) begin
                    p = cur + i;
                    lv_exp[i] = (p >= QS0) && (p < QS0 + L);
                end
                if (x_d[271:256] !== lv_exp) begin
                    errs = errs + 1; if (errs < 8) $display("LANES beat %0d cur %0d got %04x exp %04x", beats, cur, x_d[271:256], lv_exp);
                end
                for (i = 0; i < 16; i = i + 1) if (lv_exp[i]) begin
                    p = cur + i - QS0; checked = checked + 1; keys_valid = keys_valid + 1;
                    if (x_d[16*i +: 16] !== em[p][15:0] || em[p][16]) begin
                        errs = errs + 1;
                        if (errs < 8) $display("SCORE pos %0d got %04x exp %04x f%0d", cur + i, x_d[16*i +: 16], em[p][15:0], em[p][16]);
                    end
                end
                exp_beats = (L == 0) ? 1 : ((QS0 + L - cur + 15) / 16 == 1 ? 1 : 0);
                if (x_d[272] != ((L == 0) || (cur + 16 >= QS0 + L))) begin
                    errs = errs + 1; $display("LAST flag wrong at beat %0d cur %0d", beats, cur);
                end
                if (x_d[272]) begin lastn = lastn + 1; done_cyc = cyc; end
                beats = beats + 1; cur = cur + 16;
            end
        end
        if ((lastn > 0 && cyc > done_cyc + 300) || (beats > 0 && beats >= ((L == 0) ? 1 : (L + SKIP % 16 + 15) / 16) && cyc > last_cyc + 2000) || cyc >= MAXCYC || (fault && cyc > 50 && done_cyc < 0 && words == 0 && cyc > 20000)) begin
            exp_beats = (L == 0) ? 1 : (QS0 + L - (QS0 - SKIP % 16) + 15) / 16;
            $display("SVCQIDX ST=%0d N=%0d L=%0d qstart=%0d skip=%0d hdr_ok=%0d beats=%0d exp_beats=%0d keys_checked=%0d errors=%0d lasts=%0d after_last=%0d fault=%0d fault_code=%02x busy=%0d idxq_hdr=%0d first_beat=%0d last_beat=%0d scan_cycles=%0d keys_per_cycle=%0.3f cycles=%0d timeout=%0d verdict=%s",
                     ST, N, L, QS0, SKIP, hdr_ok, beats, exp_beats, checked, errs, lastn, after_last, fault, fault_code, busy,
                     idx_hdr_cyc, first_beat_cyc, last_cyc, last_cyc - idx_hdr_cyc,
                     (last_cyc > idx_hdr_cyc) ? real'(L) / real'(last_cyc - idx_hdr_cyc) : 0.0, cyc, cyc >= MAXCYC,
                     (hdr_ok && errs == 0 && lastn == 1 && after_last == 0 && beats == exp_beats && checked == L && !fault &&
                      cyc < MAXCYC) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
