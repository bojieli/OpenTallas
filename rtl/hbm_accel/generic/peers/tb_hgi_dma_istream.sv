`timescale 1ns/1ps
// hgi-1010/c 2026-10-10: the INDEXED ROW STREAM through the DMA unit (spec 3.3, the stream form of DMA.LOAD: A indexed with
// n_sel = N_FROM_VM): record -> ot_hgi_dma_record (stream detect, is_cmd) -> ot_hgi_dma_engines (I-list reader on the VM
// client, then the DMA front with FRONT = 1 or the per-row mover sequencer with FRONT = 0) -> the REAL HGI VM
// (ot_hgi_vm_unit NC 2 WP 32 WDIRECT 1: client 0 = the DMA unit, client 1 = this bench).  HBM: an svc-stream model (FRONT 1:
// per-stack requests, per-lane beats, credits) and a kport-lane model (the mover), both answering hb(byte address).
// The bench writes the I table (ids, unaligned start, duplicates, ids >= 2^16) and the count into VM, sends the record
// with the CP's effective A base (abase + id_0 x dyn_mul) and checks every destination word (the decode of the HBM row of
// id_e) plus untouched words between and after the rows.  Cases: FP32 1-sector rows, BF16 4-sector rows, FP8 rows.
// MUT_IL (engines): the reader skips list position 1: must FAIL.  Prints ISTREAM PASS / FATAL.
module tb_hgi_dma_istream;
    parameter integer FRONT = 1;
    parameter integer MUT_IL = 0;
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    function automatic [7:0] hb(input longint a);
        longint x;
        begin x = a ^ (a >> 31); x = x * 64'h9E3779B97F4A7C15; x = x ^ (x >> 29); x = x * 64'hBF58476D1CE4E5B9; hb = 8'(x >> 40); end
    endfunction
    // ---- DMA unit
    reg rec_v = 0; reg [127:0] hdr = 0; reg [255:0] ra = 0, ro = 0; reg [20:0] nA = 0, nO = 0; reg [31:0] il = 0;
    wire rec_rdy, done, fault, halted, wq;
    wire mv_v, mv_rdy, mv_done, mv_fault, mv_src, mv_pdone, mv_fdone, fence_v, fence_rdy, fence_done, is_v, is_rdy;
    wire [226:0] mv; wire [207:0] is_cmd;
    ot_hgi_dma_record #(.LEGACY(0)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(hdr), .rec_a(ra), .rec_o(ro), .rec_n_a(nA), .rec_n_o(nO), .rec_pos1(21'd1), .rec_ilist(il),
        .rec_done(done), .rec_fault(fault), .halted(halted), .wr_quiet(wq),
        .lg_mv_v(1'b0), .lg_mv_rdy(), .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(),
        .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault), .mv_src(mv_src), .mv_pdone(mv_pdone),
        .mv_fdone(mv_fdone), .is_v(is_v), .is_rdy(is_rdy), .is_cmd(is_cmd), .fence_v(fence_v), .fence_rdy(fence_rdy),
        .fence_done(fence_done));
    wire k_req_v, k_req_we, k_rsp_rdy; reg k_req_rdy = 0, k_rsp_v = 0; reg [255:0] k_rsp_d = 0;
    wire [36:0] k_a; wire [255:0] k_wd; wire [31:0] k_ws; wire [15:0] k_tag;
    wire [337:0] vmq; wire [273:0] vmr0, vmr1; reg [337:0] tq = 0;
    wire [4*51-1:0] dq; reg [3:0] dq_rdy = 4'hF; reg [32*270-1:0] dd = 0; wire [31:0] dd_cr;
    wire [32*280-1:0] wl; wire [31:0] wl_done;
    ot_hgi_dma_engines #(.FRONT(FRONT), .SBIT(20), .STACK_BYTES(36'd1048576), .MUT_IL(MUT_IL)) u_eng (.clk(clk), .rst_n(rst_n),
        .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault), .mv_src(mv_src), .mv_pdone(mv_pdone),
        .mv_fdone(mv_fdone), .is_v(is_v), .is_rdy(is_rdy), .is_cmd(is_cmd), .fence_v(fence_v), .fence_rdy(fence_rdy),
        .fence_done(fence_done), .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_a),
        .k_req_wdata(k_wd), .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(1'b0),
        .k_rsp_data(k_rsp_d), .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb),
        .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .vr2q(), .vr2r(8257'd0),
        .vmq(vmq), .vmr(vmr0), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr), .wl(wl), .wl_done(wl_done));
    ot_hgi_vm_unit #(.NC(2), .WP(32), .WDIRECT(1)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, vmq}), .cr({vmr1, vmr0}), .status(),
        .wq(wl), .wq_done(wl_done));
    // ---- kport lane model (the mover): in order, latency 6, reads only (a stream is a LOAD)
    // hgi-1010/c: the mover's four HBM read lanes (bursts, in order a lane) on tb_hgi_rlanes over this bench's memory
    wire [3:0] r_req_v, r_req_rdy, r_rsp_v, r_rsp_rdy, r_rsp_last; wire [4*37-1:0] r_req_addr, la; wire [15:0] r_req_len;
    wire [63:0] r_req_tag, r_rsp_tag; wire [1023:0] r_rsp_data, r_req_wdata; wire [3:0] r_req_we, r_rsp_we; wire [127:0] r_req_wstrb; reg [1023:0] ld; integer hgen = 0; wire [3:0] wv; wire [4*37-1:0] wa; wire [1023:0] wd; wire [127:0] ws;
    always @(posedge clk) hgen <= hgen + 1;
    tb_hgi_rlanes #(.LAT(6)) u_rl (.clk(clk), .rst_n(rst_n), .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr),
        .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag),
        .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .la(la), .ld(ld), .wv(wv), .wa(wa), .wd(wd), .ws(ws));
    always @(la or hgen) for (integer l = 0; l < 4; l = l + 1) for (integer b = 0; b < 32; b = b + 1)
        ld[l*256 + 8*b +: 8] = hb(longint'(la[l*37 +: 37]) + b);
    reg [36:0] kq [0:63]; integer kh = 0, kt = 0, kdue [0:63];
    always @(posedge clk) begin
        k_rsp_v <= 0;
        if (rst_n && k_req_v && k_req_rdy) begin
            if (k_req_we) $fatal(1, "FATAL: a write on the lane during a stream");
            kq[kt % 64] = k_a; kdue[kt % 64] = cyc + 6; kt = kt + 1;
        end
        if (kh < kt && kdue[kh % 64] <= cyc) begin
            for (integer b = 0; b < 32; b = b + 1) k_rsp_d[8*b +: 8] <= hb(longint'(kq[kh % 64]) + b);
            k_rsp_v <= 1; kh = kh + 1;
        end
        k_req_rdy <= (kt - kh) < 32;
    end
    // ---- svc stream model (FRONT 1): per stack a request queue, per lane beats in idx order, credit 16 a lane
    reg [49:0] rq [0:3][0:63]; integer rqh [0:3], rqn [0:3], nx [0:3], cr [0:31], lh [0:31], lt [0:31];
    reg [269:0] lb [0:31][0:255];
    initial for (integer i = 0; i < 32; i = i + 1) begin cr[i] = 16; lh[i] = 0; lt[i] = 0; end
    initial for (integer s = 0; s < 4; s = s + 1) begin rqh[s] = 0; rqn[s] = 0; nx[s] = 0; end
    always @(posedge clk) if (rst_n) begin
        dd <= 0;
        for (integer s = 0; s < 4; s = s + 1) begin
            if (dq[s*51 + 50] && dq_rdy[s]) begin rq[s][(rqh[s] + rqn[s]) % 64] = dq[s*51 +: 50]; rqn[s] = rqn[s] + 1; end
            for (integer k = 0; k < 8 && rqn[s] > 0; k = k + 1) begin : sch
                reg [49:0] r; reg [255:0] sd; longint a; integer l;
                r = rq[s][rqh[s] % 64];
                a = longint'(r[36:0]) + 32 * nx[s];
                for (integer b = 0; b < 32; b = b + 1) sd[8*b +: 8] = hb(a + b);
                l = s * 8 + (nx[s] % 8);
                lb[l][lt[l] % 256] = {1'b1, 1'b0, r[49:46], 8'(nx[s]), sd}; lt[l] = lt[l] + 1;
                nx[s] = nx[s] + 1;
                if (nx[s] == int'(r[45:37])) begin nx[s] = 0; rqh[s] = rqh[s] + 1; rqn[s] = rqn[s] - 1; end
            end
        end
        for (integer i = 0; i < 32; i = i + 1) begin
            if (dd_cr[i]) cr[i] = cr[i] + 1;
            if (lt[i] > lh[i] && cr[i] > 0) begin dd[i*270 +: 270] <= lb[i][lh[i] % 256]; lh[i] = lh[i] + 1; cr[i] = cr[i] - 1; end
        end
    end
    // ---- bench VM client (one request at a time)
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!vmr1[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 1000) $fatal(1, "FATAL: VM client timeout");
            qd = vmr1[32 * word[2:0] +: 32];
        end
    endtask
    // reference decode
    function automatic [31:0] f32(input real v);
        reg [63:0] d;
        begin d = $realtobits(v); f32 = (d[62:0] == 63'd0) ? {d[63], 31'd0} : {d[63], 8'(d[62:52] - 11'd1023 + 11'd127), d[51:29]}; end
    endfunction
    function automatic [31:0] e4(input [7:0] c);
        real v; integer e, m; reg [31:0] r;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 15 && m == 7) e4 = 32'h7FC00000;
            else begin
                v = (e == 0) ? (m / 8.0) * (2.0 ** -6) : (1.0 + m / 8.0) * (2.0 ** (e - 7));
                r = f32(v); r[31] = c[7]; if (v == 0.0) r = {c[7], 31'd0}; e4 = r;
            end
        end
    endfunction
    integer errs = 0;
    reg [31:0] ids [0:255];
    task automatic run(input [2:0] f, input longint abase, input longint mul, input integer n, input integer dbase,
                       input integer dstr, input integer cnt, input integer ibase, input longint idmax);
        integer es, i, o, t0, e0; longint a; reg [31:0] want, qd;
        begin
            es = (f == 0 || f == 5) ? 4 : (f == 1) ? 2 : 1; e0 = errs;
            for (i = 0; i < cnt; i = i + 1) begin
                ids[i] = 32'($urandom % idmax);
                if (i == 1) ids[i] = 32'(idmax - 1);
                if (i > 2 && ($urandom % 6) == 0) ids[i] = ids[i - 1];
                vm_req(1, ibase + i, ids[i], qd);
            end
            vm_req(1, ibase + 64, cnt, qd);                              // row 1 of I (stride 64): the count (the CP reads it)
            for (o = 0; o < cnt + 1; o = o + 1) for (i = 0; i < n + 8; i = i + 8) vm_req(1, dbase + o * dstr + i, 32'hDEAD0000 + o, qd);
            // record: unit 8 op 0 (LOAD), operands A, O, I
            hdr = 0; hdr[127:124] = 4'd8; hdr[123:118] = 6'd0; hdr[93] = 1; hdr[97] = 1; hdr[99] = 1;
            ra = 0; ra[1:0] = 2'd0; ra[4:2] = f; ra[6] = 1'b1; ra[47:8] = 40'(abase + longint'(ids[0]) * mul); ra[67:48] = 20'(cnt);
            ra[87:68] = 20'd1; ra[200:174] = 27'(mul); ra[206:201] = 6'd63;
            ro = 0; ro[1:0] = 2'd1; ro[4:2] = 3'd0; ro[47:8] = 40'(dbase); ro[67:48] = 20'(n); ro[87:68] = 20'(cnt + 1); ro[119:88] = 32'(dstr);
            nA = 21'(cnt); nO = 21'(n); il = 32'(ibase);
            $display("ISTREAM f %0d: record at cycle %0d", f, cyc);
            @(negedge clk); rec_v = 1; t0 = cyc; while (!rec_rdy) begin @(negedge clk); if (cyc - t0 > 20000) $fatal(1, "FATAL: record never accepted"); end
            @(posedge clk); #0.1 rec_v = 0; t0 = cyc;
            while (!done && !fault && cyc - t0 < 100000) @(posedge clk);
            if (!done || fault) begin $display("FATAL: stream f %0d: done %0d fault %0d", f, done, fault); errs = errs + 1; end
            repeat (8) @(negedge clk);
            for (o = 0; o < cnt; o = o + 1) for (i = 0; i < n; i = i + 1) begin
                a = abase + longint'(ids[o]) * mul + i * es;
                case (f)
                    1: want = {hb(a + 1), hb(a), 16'd0};
                    2: want = e4(hb(a));
                    default: want = {hb(a + 3), hb(a + 2), hb(a + 1), hb(a)};
                endcase
                vm_req(0, dbase + o * dstr + i, 0, qd);
                if (qd !== want) begin
                    if (errs < 8) $display("FATAL: f %0d row %0d (id %0d) elem %0d: %h want %h", f, o, ids[o], i, qd, want);
                    errs = errs + 1;
                end
            end
            vm_req(0, dbase + cnt * dstr, 0, qd);                        // the row after the list is untouched
            if (qd !== 32'hDEAD0000 + cnt) begin $display("FATAL: f %0d: row %0d written", f, cnt); errs = errs + 1; end
            if (dstr > n) begin vm_req(0, dbase + n, 0, qd); if (qd !== 32'hDEAD0000) begin $display("FATAL: gap written"); errs = errs + 1; end end
            $display("ISTREAM f %0d rows %0d n %0d: %0d cycles, %0d errors", f, cnt, n, cyc - t0, errs - e0);
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        run(0, 64'h40, 32, 8, 4096, 16, 21, 1003, 30000);          // FP32 one-sector rows, ids up to 2^15, list at an odd word
        run(1, 64'h0, 128, 64, 8192, 64, 12, 2048 + 5, 6000);      // BF16 4-sector rows, row gap 0
        run(2, 64'h400, 1024, 512, 16384, 512, 6, 3000, 900);      // FP8 16-sector rows -> 4 x 16 VM sectors
        if (errs == 0) $display("ISTREAM PASS FRONT %0d", FRONT); else $display("FATAL ISTREAM errors=%0d FRONT %0d", errs, FRONT);
        $finish;
    end
endmodule
