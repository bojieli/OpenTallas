`timescale 1ns/1ps
// S81/H23 (2026-10-24): exact bench of dsdv_svc_att IK_ROW (q frame type 15, attn.idx.newkey) + OWN_ROW regression.
// One dsdv_svc_att is run 16 times (sid = 0..15, reset between runs) on the SAME q stream: NIK IK_ROW frames (random
// position p over [0, 2^20) -- half of them >= 2^16 so the j[15:12] term of the region hash matters --, random region
// base KB, codes and scales) interleaved with NOW OWN_ROW frames (tile 3), back to back and with gaps.  A PC model
// returns the request credit (qrk) 3 edges and the write done (qwd) 5 edges after each issued request.
// GOLDEN (independent of the RTL, = tb_dsdv_idx_rg3's HBM preload of the compiler layout): key p -> j = p >> 4,
// i = p & 15, rg = i ^ hj(j), g = j >> 4, PC = g & 1, n = g >> 1, c = j & 15, a = KB + 34 n; codes[255:0] -> a + 2c,
// codes[511:256] -> a + 2c + 1 (full strobe), scales -> sector a + 32 + (c >> 3), bytes 4 (c & 7) .. +3.  Only slice
// sid == rg writes.  OWN_ROW golden = the svc_att window ring rule (every slice, its tile's block).
// PASS = for every sid the multiset of issued write requests {PC, addr, strobe, data} equals the golden exactly, every
// IK key is written by exactly one sid (3 writes), no fault in the clean phase, and a final IK_ROW frame of len 2
// raises fault bit 16 (frame check).  +nik= +now= +seed=.
module tb_dsdv_svc_att_ik;
    localparam integer TILE = 3;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [3:0] sid = 0;
    reg q_v = 0; reg [511:0] q_d = 0;
    wire [2*341-1:0] qrq; reg [1:0] qrk = 0, qwd = 0;
    wire fault; wire [31:0] fault_code;
    dsdv_svc_att #(.MUT(`TB_MUT)) dut (
        .clk(clk), .rst_n(rst_n), .sid(sid), .tile(4'(TILE)), .gd(8'd4), .pvs(8'd255), .root(1'b0),
        .q_v(q_v), .q_d(q_d), .hw_v(1'b0), .hw_d(291'd0),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(2'b00), .qr_data(512'd0), .qr_tag(34'd0), .qr_beat(8'd0),
        .l_v(), .l_d(), .pv_ov(), .pv_od(), .sm_st(), .sm_kind(), .sm_jid(), .sm_rv(), .sm_rp(), .sm_rj(), .sm_rd(),
        .go_o(), .tjob_o(), .done(), .tagj(), .hcr(), .hack(), .fault(fault), .fault_code(fault_code),
        .pio_o(), .pvo_o(), .jc_o(), .st_o());

    integer NIK = 96, NOW = 24, SEED = 1;
    // stimulus
    reg [511:0] fw [0:4095]; reg fv [0:4095]; integer nw = 0;
    // golden write list: {sid 4, pc 1, addr 30, strb 32, data 256}
    typedef struct packed { logic [3:0] s; logic pc; logic [29:0] a; logic [31:0] st; logic [255:0] d; } wr_t;
    wr_t gold [$]; wr_t seen [$];
    function automatic [3:0] hj(input [15:0] j); hj = j[3:0] ^ j[7:4] ^ j[11:8] ^ j[15:12]; endfunction
    function automatic [31:0] rnd32(); rnd32 = $urandom(); endfunction
    function automatic [511:0] rnd512(); reg [511:0] x; for (int k = 0; k < 16; k++) x[32*k +: 32] = $urandom(); rnd512 = x; endfunction
    task automatic push(input [511:0] w); fw[nw] = w; fv[nw] = 1'b1; nw++; endtask
    task automatic gap(input integer n); for (int k = 0; k < n; k++) begin fw[nw] = '0; fv[nw] = 1'b0; nw++; end endtask
    function automatic [511:0] hdr(input [3:0] ty, input [11:0] len); reg [511:0] h; h = '0; h[511:508] = ty; h[503] = 1'b1;
        h[491:480] = len; hdr = h; endfunction
    integer n_ik_hi = 0;
    task automatic build();
        reg [29:0] wb; integer nik = 0, now = 0;
        wb = 30'h1000;
        // CFG (window ring base for the OWN_ROW frames)
        begin reg [511:0] h; h = hdr(4'd12, 12'd0); h[29:0] = wb; push(h); end
        while (nik < NIK || now < NOW) begin
            if (nik < NIK && (now >= NOW || ($urandom % 3) != 0)) begin
                reg [511:0] h, c; reg [20:0] p; reg [29:0] kb; reg [31:0] sc;
                integer j, i, rg, g, pcl, n, cc; reg [29:0] a;
                p = 21'($urandom % (1 << 20)); if (nik % 2 == 1) p[19:16] = 4'(1 + $urandom % 15);
                if (p >= 21'h10000) n_ik_hi++;
                kb = 30'(64 + 4096 * ($urandom % 8)); sc = rnd32(); c = rnd512();
                h = hdr(4'd15, 12'd1); h[29:0] = kb; h[63:32] = sc; h[479:459] = p; h[458:449] = 10'($urandom % 1024);
                push(h); push(c);
                j = p >> 4; i = p & 15; rg = i ^ hj(16'(j)); g = j >> 4; pcl = g & 1; n = g >> 1; cc = j & 15;
                a = 30'(kb + 34 * n);
                gold.push_back('{s: 4'(rg), pc: 1'(pcl), a: a + 30'(2 * cc), st: 32'hffffffff, d: c[255:0]});
                gold.push_back('{s: 4'(rg), pc: 1'(pcl), a: a + 30'(2 * cc + 1), st: 32'hffffffff, d: c[511:256]});
                gold.push_back('{s: 4'(rg), pc: 1'(pcl), a: a + 30'(32 + (cc >> 3)), st: 32'hf << (4 * (cc & 7)),
                                 d: 256'(sc) << (32 * (cc & 7))});
                nik++;
            end else begin
                reg [511:0] h, blk; reg [6:0] sl; reg [9:0] u; reg [29:0] ring;
                sl = 7'($urandom); u = 10'($urandom % 16); ring = wb + 30'(u) * 30'd68;
                h = hdr(4'd3, 12'd16); h[465:459] = sl; h[479:466] = 14'($urandom); h[458:449] = u;
                push(h);
                for (int b = 0; b < 16; b++) begin reg [511:0] w; w = rnd512(); if (b == TILE) blk = w; push(w); end
                for (int s = 0; s < 16; s++) begin
                    gold.push_back('{s: 4'(s), pc: sl[0], a: ring + 30'(sl[6:1]), st: 32'hffffffff, d: blk[255:0]});
                    gold.push_back('{s: 4'(s), pc: sl[5], a: ring + 30'd64 + 30'(sl[6]), st: 32'd1 << sl[4:0],
                                     d: 256'(blk[263:256]) << (8 * sl[4:0])});
                end
                now++;
            end
            if (($urandom % 4) == 0) gap(1 + $urandom % 3);
        end
        gap(64);
    endtask

    // PC model: credit / write-done returns
    reg [1:0] crq [0:7]; reg [1:0] wdq [0:7]; integer cyc = 0;
    initial for (int k = 0; k < 8; k++) begin crq[k] = 0; wdq[k] = 0; end
    always @(posedge clk) begin
        reg [1:0] v, w;
        for (int pc = 0; pc < 2; pc++) begin v[pc] = qrq[341*pc]; w[pc] = qrq[341*pc] && qrq[341*pc + 1]; end
        crq[(cyc + 3) % 8] = crq[(cyc + 3) % 8] | v; wdq[(cyc + 5) % 8] = wdq[(cyc + 5) % 8] | w;
        qrk <= crq[cyc % 8]; qwd <= wdq[cyc % 8]; crq[cyc % 8] = 0; wdq[cyc % 8] = 0;
        if (rst_n) for (int pc = 0; pc < 2; pc++) if (qrq[341*pc] && qrq[341*pc + 1]) begin
            reg [340:0] r; r = qrq[341*pc +: 341];
            // wr_req = {d 256, strb 32, tag 17, len 4, addr 30, we, v}
            seen.push_back('{s: sid, pc: 1'(pc), a: r[31:2], st: r[84:53], d: r[340:85]});
        end
        cyc++;
    end

    integer run_fault = 0, err = 0, extra = 0, missing = 0, own_err = 0, neg_ok = 0;
    initial begin
        void'($value$plusargs("nik=%d", NIK)); void'($value$plusargs("now=%d", NOW)); void'($value$plusargs("seed=%d", SEED));
        void'($urandom(SEED));
        build();
        for (int s = 0; s < 16; s++) begin
            sid = 4'(s); rst_n = 0; q_v = 0; q_d = '0;
            repeat (6) @(posedge clk);
            #0.2 rst_n = 1;
            repeat (4) @(posedge clk);
            for (int k = 0; k < nw; k++) begin #0.2; q_v = fv[k]; q_d = fw[k]; @(posedge clk); end
            #0.2 q_v = 0; q_d = '0;
            repeat (40) @(posedge clk);
            if (fault) begin run_fault++; $display("SVCIK_FAULT sid %0d code %08x", s, fault_code); end
        end
        // compare multisets
        begin
            int cnt [wr_t];
            foreach (gold[k]) cnt[gold[k]]++;
            foreach (seen[k]) begin
                if (cnt.exists(seen[k]) && cnt[seen[k]] > 0) cnt[seen[k]]--;
                else begin extra++; if (extra <= 5) $display("SVCIK_EXTRA sid %0d pc %0d a %h st %h", seen[k].s, seen[k].pc, seen[k].a, seen[k].st); end
            end
            foreach (cnt[k]) if (cnt[k] != 0) begin missing += cnt[k]; if (missing <= 5) $display("SVCIK_MISSING sid %0d pc %0d a %h st %h", k.s, k.pc, k.a, k.st); end
        end
        // ownership: IK writes = 3 a key in total (OW writes: 2 a frame a slice)
        if (seen.size() != 3 * NIK + 32 * NOW) own_err = 1;
        // negative directed check: IK_ROW with len 2 must raise fault bit 16
        sid = 4'd0; rst_n = 0; repeat (4) @(posedge clk); #0.2 rst_n = 1; repeat (2) @(posedge clk);
        #0.2 q_v = 1; q_d = hdr(4'd15, 12'd2); @(posedge clk); #0.2 q_d = '0; @(posedge clk); @(posedge clk);
        #0.2 q_v = 0; repeat (6) @(posedge clk);
        neg_ok = fault_code[16];
        err = run_fault + extra + missing + own_err + (neg_ok ? 0 : 1);
        $display("SVCIK nik %0d (p>=2^16 %0d) now %0d words %0d writes_gold %0d writes_seen %0d extra %0d missing %0d run_faults %0d own_err %0d neg_len_fault %0d mut %0d verdict=%s",
                 NIK, n_ik_hi, NOW, nw, gold.size(), seen.size(), extra, missing, run_fault, own_err, neg_ok, `TB_MUT, err == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
