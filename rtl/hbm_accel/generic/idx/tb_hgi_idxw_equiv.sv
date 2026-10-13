`timescale 1ps/1ps
// el1013-idx-tiles: transaction-exact equivalence bench of the TILED wide adapter ot_hgi_idx_index_wt against the flat
// reference ot_hgi_idx_index_w (NL = 8).  Each DUT has its own instance of the same behavioural environment (VM wide
// read / write lanes with randomised reply delay and LQ credits, req / grant, selector with qbr / toc / coc credits)
// with the same seed; the frame content (command, memory, to / co beats) is generated once and shared.
// Compared per frame (non-fault frames): the wrq sector sequence of every read lane, the fs / qb / kin beat sequences,
// the wwq (sector, mask, masked data) sequence of every write lane and output stream (O, R, D ids, D values; the
// interleave of two streams on one lane depends on beat timing and is not specified), done / fault.
// Runtime-fault frames (ev[1], non-zero weight low half) compare the fault only, then both DUTs are reset (the
// reference is not re-startable after a mid-frame fault).  Rules checked in the environment: lane credits (LQ), 4 qb
// credits, the lane of each sector, fs first, every kin beat before the last query block.
// MUT applies to the tiled DUT only (1, 2 inherited; 11 divider stage, 12 pointer copy, 13 credit seam: must FAIL).
module idxw_env #(parameter integer LQ = 8) (
    input  wire clk, input wire erst,
    input  wire [127:0] wrq, output reg [7:0] wrq_cr, output reg [8*257-1:0] wrr, input wire rg_req, output reg rg_gnt,
    input  wire [8*280-1:0] wwq, output reg [7:0] wwq_cr, output reg [7:0] wwq_done, input wire wg_req, output reg wg_gnt,
    input  wire [89:0] fs, input wire [1047:0] qb, output reg qbr, input wire [344:0] kin,
    output reg [611:0] to, input wire toc, output reg [71:0] co, input wire coc, output reg [1:0] ev,
    input  wire done, input wire fault);
    integer now = 0, err = 0, l, w, s;
    reg [31:0] lf = 32'h1234_5678;
    function automatic integer rnd(input integer n);
        begin lf = lf ^ (lf << 13); lf = lf ^ (lf >> 17); lf = lf ^ (lf << 5); rnd = integer'(lf % 32'(n)); end
    endfunction
    // logs
    integer nrq [0:7]; reg [14:0] rq_log [0:7][0:1023];
    integer nfs, nqb, nkin, ndone, nfault, t_done, kin_at_last;
    reg [89:0] fs_log [0:3]; reg [1047:0] qb_log [0:255]; reg [344:0] kin_log [0:7];
    integer nw [0:7][0:3]; reg [278:0] w_log [0:7][0:3][0:255];
    // VM read lanes
    reg [14:0] q_sec [0:7][0:63]; integer q_t [0:7][0:63]; integer qh [0:7], qn [0:7], q_last [0:7];
    // VM write lanes: credit / done return times
    integer wc_t [0:7][0:63], wd_t [0:7][0:63], wch [0:7], wcn [0:7], wdh [0:7], wdn [0:7], wc_last [0:7], wd_last [0:7], wout [0:7];
    // selector
    integer qbr_t [0:15], qbh, qbn, qb_last, qb_out, ti, ci, tcred, ccred, ev_cnt, fcyc, rgc, wgc;
    reg sel_on, ev_sent;
    reg [255:0] d; reg [7:0] m; reg [14:0] sec;
    task automatic clear_logs;
        begin
            for (l = 0; l < 8; l = l + 1) begin nrq[l] = 0; for (s = 0; s < 4; s = s + 1) nw[l][s] = 0; end
            nfs = 0; nqb = 0; nkin = 0; ndone = 0; nfault = 0; t_done = 0; kin_at_last = 0;
            sel_on = 0; ev_sent = 0; ti = 0; ci = 0; tcred = 8; ccred = 8; ev_cnt = -1; fcyc = 0;
        end
    endtask
    task automatic hard_reset;
        begin
            clear_logs();
            for (l = 0; l < 8; l = l + 1) begin qh[l] = 0; qn[l] = 0; q_last[l] = 0; wch[l] = 0; wcn[l] = 0; wdh[l] = 0; wdn[l] = 0;
                wc_last[l] = 0; wd_last[l] = 0; wout[l] = 0; end
            qbh = 0; qbn = 0; qb_last = 0; qb_out = 0; rgc = 0; wgc = 0;
        end
    endtask
    initial begin hard_reset(); wrq_cr = 0; wrr = 0; rg_gnt = 0; wwq_cr = 0; wwq_done = 0; wg_gnt = 0; qbr = 0; to = 0; co = 0; ev = 0; end
    always @(posedge clk) begin
        now = now + 1;
        wrq_cr <= 8'd0; wwq_cr <= 8'd0; wwq_done <= 8'd0; qbr <= 1'b0; to[0] <= 1'b0; co[0] <= 1'b0; ev <= 2'b00;
        for (l = 0; l < 8; l = l + 1) wrr[l*257 + 256] <= 1'b0;
        if (erst) begin hard_reset(); rg_gnt <= 1'b0; wg_gnt <= 1'b0; end
        else begin
            // ---- read lanes
            for (l = 0; l < 8; l = l + 1) begin
                if (qn[l] > 0 && q_t[l][qh[l] % 64] <= now) begin
                    sec = q_sec[l][qh[l] % 64];
                    for (w = 0; w < 8; w = w + 1) wrr[l*257 + 32*w +: 32] <= tb_hgi_idxw_equiv.mem[{sec, 3'(w)}];
                    wrr[l*257 + 256] <= 1'b1; wrq_cr[l] <= 1'b1; qh[l] = qh[l] + 1; qn[l] = qn[l] - 1;
                end
                if (wrq[l*16 + 15]) begin
                    sec = wrq[l*16 +: 15];
                    if (sec[2:0] != 3'(l)) begin err = err + 1; $display("ENV wrong read lane %0d sec %0d", l, sec); end
                    if (qn[l] >= LQ) begin err = err + 1; $display("ENV read credit overrun lane %0d", l); end
                    if (!rg_gnt) begin err = err + 1; $display("ENV read without grant"); end
                    q_sec[l][(qh[l] + qn[l]) % 64] = sec;
                    q_last[l] = (now + tb_hgi_idxw_equiv.f_rt + rnd(3) > q_last[l] + 1) ? now + tb_hgi_idxw_equiv.f_rt + rnd(3) : q_last[l] + 1;
                    q_t[l][(qh[l] + qn[l]) % 64] = q_last[l]; qn[l] = qn[l] + 1;
                    if (nrq[l] < 1024) rq_log[l][nrq[l]] = sec;
                    nrq[l] = nrq[l] + 1;
                end
            end
            if (!rg_req) begin rg_gnt <= 1'b0; rgc = rnd(4); end else if (rgc > 0) rgc = rgc - 1; else rg_gnt <= 1'b1;
            if (!wg_req) begin wg_gnt <= 1'b0; wgc = rnd(4); end else if (wgc > 0) wgc = wgc - 1; else wg_gnt <= 1'b1;
            // ---- write lanes
            for (l = 0; l < 8; l = l + 1) begin
                if (wcn[l] > 0 && wc_t[l][wch[l] % 64] <= now) begin wwq_cr[l] <= 1'b1; wch[l] = wch[l] + 1; wcn[l] = wcn[l] - 1; wout[l] = wout[l] - 1; end
                if (wdn[l] > 0 && wd_t[l][wdh[l] % 64] <= now) begin wwq_done[l] <= 1'b1; wdh[l] = wdh[l] + 1; wdn[l] = wdn[l] - 1; end
                if (wwq[l*280 + 279]) begin
                    sec = wwq[l*280 + 264 +: 15]; d = wwq[l*280 + 8 +: 256]; m = wwq[l*280 +: 8];
                    for (w = 0; w < 8; w = w + 1) if (!m[w]) d[w*32 +: 32] = 32'd0;
                    s = integer'(sec >> 10) - 8;
                    if (sec[2:0] != 3'(l) || s < 0 || s > 3) begin err = err + 1; $display("ENV bad write lane %0d sec %0d", l, sec); s = 0; end
                    if (wout[l] >= LQ) begin err = err + 1; $display("ENV write credit overrun lane %0d", l); end
                    if (!wg_gnt) begin err = err + 1; $display("ENV write without grant"); end
                    if (nw[l][s] < 256) w_log[l][s][nw[l][s]] = {sec, d, m};
                    nw[l][s] = nw[l][s] + 1; wout[l] = wout[l] + 1;
                    wc_last[l] = (now + 1 + rnd(4) > wc_last[l] + 1) ? now + 1 + rnd(4) : wc_last[l] + 1;
                    wc_t[l][(wch[l] + wcn[l]) % 64] = wc_last[l]; wcn[l] = wcn[l] + 1;
                    wd_last[l] = (now + 3 + rnd(8) > wd_last[l] + 1) ? now + 3 + rnd(8) : wd_last[l] + 1;
                    wd_t[l][(wdh[l] + wdn[l]) % 64] = wd_last[l]; wdn[l] = wdn[l] + 1;
                end
            end
            // ---- selector
            if (sel_on) fcyc = fcyc + 1;
            if (fs[0]) begin
                if (nfs < 4) fs_log[nfs] = fs;
                nfs = nfs + 1; sel_on = 1; fcyc = 0;
                if (nqb != 0) begin err = err + 1; $display("ENV qb before fs"); end
            end
            if (qbn > 0 && qbr_t[qbh % 16] <= now) begin qbr <= 1'b1; qbh = qbh + 1; qbn = qbn - 1; qb_out = qb_out - 1; end
            if (qb[0]) begin
                if (nqb < 256) qb_log[nqb] = qb;
                nqb = nqb + 1;
                if (nfs == 0) begin err = err + 1; $display("ENV qb without fs"); end
                if (qb_out >= 4) begin err = err + 1; $display("ENV qb credit overrun"); end
                if (nqb == 128) kin_at_last = nkin;
                qb_out = qb_out + 1;
                qb_last = (now + 1 + rnd(tb_hgi_idxw_equiv.f_qd) > qb_last + 1) ? now + 1 + rnd(tb_hgi_idxw_equiv.f_qd) : qb_last + 1;
                qbr_t[(qbh + qbn) % 16] = qb_last; qbn = qbn + 1;
            end
            if (kin[0]) begin if (nkin < 8) kin_log[nkin] = kin; nkin = nkin + 1; end
            if (toc) tcred = tcred + 1;
            if (coc) ccred = ccred + 1;
            if (sel_on && nqb >= tb_hgi_idxw_equiv.f_tstart && ti < tb_hgi_idxw_equiv.nto && tcred > 0 && rnd(4) != 0) begin
                to <= tb_hgi_idxw_equiv.to_b[ti]; ti = ti + 1; tcred = tcred - 1;
            end
            if (sel_on && nqb >= tb_hgi_idxw_equiv.f_tstart && ci < tb_hgi_idxw_equiv.nco && ccred > 0 && rnd(3) != 0) begin
                co <= tb_hgi_idxw_equiv.co_b[ci]; ci = ci + 1; ccred = ccred - 1;
            end
            if (sel_on && !ev_sent && nqb == 128 && ti == tb_hgi_idxw_equiv.nto && ci == tb_hgi_idxw_equiv.nco) begin
                if (ev_cnt < 0) ev_cnt = 2 + rnd(8);
                else if (ev_cnt == 0) begin ev[0] <= 1'b1; ev_sent = 1; end
                else ev_cnt = ev_cnt - 1;
            end
            if (sel_on && tb_hgi_idxw_equiv.f_evf >= 0 && fcyc == tb_hgi_idxw_equiv.f_evf) ev[1] <= 1'b1;
            if (done) begin ndone = ndone + 1; t_done = now; sel_on = 0; end
            if (fault) begin nfault = nfault + 1; t_done = now; sel_on = 0; end
        end
    end
endmodule

module tb_hgi_idxw_equiv;
    parameter integer MUT = 0, LQ = 8, RDL = 2;      // RDL: landing depth of the REFERENCE (2 = as shipped)
    reg clk = 0; always #416 clk = ~clk;
    reg rst_n = 0, erst = 1;
    reg [31:0] mem [0:262143];
    // shared frame content
    integer f_rt = 2, f_qd = 3, f_tstart = 0, f_evf = -1, nto = 0, nco = 0;
    reg [611:0] to_b [0:63]; reg [71:0] co_b [0:1023];
    reg go = 0; reg [11:0] k = 0; reg cand_en = 0, keep_en = 0, has_r = 0; reg [31:0] n = 0; reg [6:0] rank = 0; reg [19:0] pos = 0;
    reg [17:0] a_base = 0, b_base = 0, c_base = 0, o_base = 0, r_base = 0, d_base = 0, d_stride = 0, c_stride = 0; reg [11:0] c_n = 0;
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : u
        wire done, fault, rg_req, rg_gnt, wg_req, wg_gnt, qbr, toc, coc;
        wire [127:0] wrq; wire [7:0] wrq_cr, wwq_cr, wwq_done; wire [8*257-1:0] wrr; wire [8*280-1:0] wwq;
        wire [89:0] fs; wire [1047:0] qb; wire [344:0] kin; wire [611:0] to; wire [71:0] co; wire [1:0] ev;
        if (g == 0) begin : r
            ot_hgi_idx_index_w #(.NL(8), .LQ(LQ), .DL(RDL)) dut (.clk(clk), .rst_n(rst_n), .go_i(go), .k_i(k), .cand_en_i(cand_en),
                .keep_en_i(keep_en), .n_i(n), .rank_i(rank), .pos_i(pos), .a_base_i(a_base), .b_base_i(b_base), .c_base_i(c_base),
                .o_base_i(o_base), .r_base_i(r_base), .d_base_i(d_base), .d_stride_i(d_stride), .c_stride_i(c_stride), .c_n_i(c_n),
                .has_r_i(has_r), .done(done), .fault(fault), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .rg_req(rg_req), .rg_gnt(rg_gnt),
                .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .wg_req(wg_req), .wg_gnt(wg_gnt), .fs(fs), .qb(qb), .qbr(qbr),
                .kin(kin), .to(to), .toc(toc), .co(co), .coc(coc), .ev(ev));
        end else begin : t
            ot_hgi_idx_index_wt #(.MUT(MUT), .LQ(LQ)) dut (.clk(clk), .rst_n(rst_n), .go_i(go), .k_i(k), .cand_en_i(cand_en),
                .keep_en_i(keep_en), .n_i(n), .rank_i(rank), .pos_i(pos), .a_base_i(a_base), .b_base_i(b_base), .c_base_i(c_base),
                .o_base_i(o_base), .r_base_i(r_base), .d_base_i(d_base), .d_stride_i(d_stride), .c_stride_i(c_stride), .c_n_i(c_n),
                .has_r_i(has_r), .done(done), .fault(fault), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .rg_req(rg_req), .rg_gnt(rg_gnt),
                .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .wg_req(wg_req), .wg_gnt(wg_gnt), .fs(fs), .qb(qb), .qbr(qbr),
                .kin(kin), .to(to), .toc(toc), .co(co), .coc(coc), .ev(ev));
        end
        idxw_env #(.LQ(LQ)) env (.clk(clk), .erst(erst), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .rg_req(rg_req), .rg_gnt(rg_gnt),
            .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .wg_req(wg_req), .wg_gnt(wg_gnt), .fs(fs), .qb(qb), .qbr(qbr),
            .kin(kin), .to(to), .toc(toc), .co(co), .coc(coc), .ev(ev), .done(done), .fault(fault));
    end endgenerate
    `define E0 u[0].env
    `define E1 u[1].env
    reg [31:0] rs = 32'h9E37_79B9;
    function automatic integer rnd(input integer nn);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); rnd = integer'(rs % 32'(nn)); end
    endfunction
    function automatic [31:0] r32(input integer dummy);
        begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); r32 = rs; end
    endfunction
    integer nfr, seed, f, i, j, l, s, x, kind, bad = 0, fbad, t0, w, kept, fkept, cyc = 0, wait_n, verbose;
    integer tot_rq = 0, tot_qb = 0, tot_kin = 0, tot_w = 0, tot_fs = 0, tot_kept = 0, nok = 0, nflt = 0, cyc_r = 0, cyc_t = 0, dmax = -1000000, dmin = 1000000;
    integer keepf_n = 0, candf_n = 0, hasr_n = 0, rtf, lanes_left;
    always @(posedge clk) cyc <= cyc + 1;
    task automatic fail(input string what);
        begin fbad = fbad + 1; if (fbad <= 6) $display("MISMATCH frame %0d: %s", f, what); end
    endtask
    initial begin
        if (!$value$plusargs("NFR=%d", nfr)) nfr = 40;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("VERBOSE=%d", verbose)) verbose = 0;
        rs = 32'h9E37_79B9 ^ (32'(seed) * 32'd2654435761); if (rs == 0) rs = 32'd1;
        for (i = 0; i < 262144; i = i + 1) mem[i] = 32'hDEAD_0000 + 32'(i);
        repeat (6) @(negedge clk); rst_n = 1; erst = 0; repeat (8) @(negedge clk);
        for (f = 0; f < nfr; f = f + 1) begin
            // ---------------- frame content
            kind = rnd(16);                 // 0..10 normal, 11 start fault, 12 weight fault, 13 ev fault, 14 L24 shape, 15 small
            keep_en = rnd(4) != 0; cand_en = rnd(3) != 0; has_r = rnd(4) != 0;
            k = 12'(1 + rnd(512)); n = 32'(1 + rnd(10944)); rank = 7'(rnd(96)); pos = 20'(r32(0));
            a_base = 18'h01000 + 18'(8 * rnd(256)); b_base = 18'h03000 + 18'(rnd(64)); c_base = 18'h06000 + 18'(rnd(64));
            o_base = 18'h10000 + 18'(rnd(4096)); r_base = 18'h12000 + 18'(rnd(4096)); d_base = 18'h14000 + 18'(rnd(4096));
            d_stride = 18'h02000;
            case (rnd(6)) 0: c_stride = 18'd32; 1: c_stride = 18'd96; 2: c_stride = 18'd4096; default: c_stride = 18'd2048; endcase
            c_n = 12'(1 + rnd(c_stride > 18'd2048 ? 2048 : integer'(c_stride)));
            if (kind == 14) begin keep_en = 1; cand_en = 1; has_r = 1; k = 12'd512; c_stride = 18'd2048; c_n = 12'd2040; end
            if (kind == 15) begin k = 12'(1 + rnd(8)); c_n = 12'(1 + rnd(8)); end
            f_rt = 1 + rnd(10); f_qd = 1 + rnd(6); f_tstart = rnd(129); f_evf = -1; rtf = 0;
            for (i = 0; i < 4096; i = i + 1) mem[a_base + 18'(i)] = r32(0);
            for (i = 0; i < 32; i = i + 1) mem[b_base + 18'(i)] = {16'(r32(0)), 16'd0};
            // candidate table (and its surroundings, to exercise the range test): id = 96 * ord + rank mostly
            for (i = -64; i < 2048 + 64; i = i + 1) if (i < integer'(c_stride) + 64) begin
                x = rnd(1500);
                mem[c_base + 18'(i)] = 32'(96 * x + ((rnd(3) != 0) ? integer'(rank) : rnd(96))) | ((rnd(40) == 0) ? 32'h0010_0000 : 32'd0);
            end
            for (i = -64; i < 2048 + 64; i = i + 1)
                mem[c_base + c_stride + 18'(i)] = (rnd(10) == 0) ? 32'hFF80_0000 : (32'h3F00_0000 + 32'(rnd(1 << 20)));
            if (kind == 11) case (rnd(5))
                0: k = (rnd(2) != 0) ? 12'd0 : 12'(513 + rnd(1000)); 1: n = 32'd10945 + 32'(rnd(1000)); 2: rank = 7'(96 + rnd(32));
                3: a_base = a_base + 18'(1 + rnd(7)); default: begin keep_en = 1; c_stride = c_stride + 18'(1 + rnd(31)); end
            endcase
            if (kind == 12) begin mem[b_base + 18'(rnd(32))][15:0] = 16'(1 + rnd(65535)); rtf = 1; end
            if (kind == 13) begin f_evf = 10 + rnd(90); rtf = 1; end
            // selector beats: to = {idx20 x16, val16 x16, ninf16, lv16, q2, last, v}
            lanes_left = integer'(k); nto = 0;
            while (lanes_left > 0 && nto < 60) begin
                to_b[nto] = {r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0),
                             r32(0), r32(0), r32(0), r32(0), r32(0), r32(0), r32(0)};
                to_b[nto][0] = 1'b1; to_b[nto][1] = 1'b0;
                case (rnd(4)) 0: to_b[nto][19:4] = 16'(r32(0)); 1: to_b[nto][19:4] = 16'h00FF; default: to_b[nto][19:4] = 16'hFFFF; endcase
                for (j = 0; j < 16; j = j + 1) if (to_b[nto][4 + j]) lanes_left = lanes_left - 1;
                nto = nto + 1;
            end
            if (nto == 0) begin to_b[0] = 612'd1; nto = 1; end
            to_b[nto - 1][1] = 1'b1;
            nco = cand_en ? 1 + rnd(kind == 14 ? 1000 : 120) : 0;
            for (i = 0; i < nco; i = i + 1) begin co_b[i] = {r32(0), r32(0), r32(0)}; co_b[i][0] = 1'b1; co_b[i][1] = (i == nco - 1); end
            // ---------------- run
            `E0.clear_logs(); `E1.clear_logs();
            @(negedge clk); go = 1; t0 = cyc; @(negedge clk); go = 0;
            wait_n = 0;
            while ((`E0.ndone + `E0.nfault == 0 || `E1.ndone + `E1.nfault == 0) && wait_n < 60000) begin @(negedge clk); wait_n = wait_n + 1; end
            repeat (40) @(negedge clk);
            // ---------------- compare
            fbad = 0; fkept = 0;
            if (wait_n >= 60000) fail($sformatf("timeout (ref done %0d fault %0d, tiled done %0d fault %0d)", `E0.ndone, `E0.nfault, `E1.ndone, `E1.nfault));
            if (`E0.ndone != `E1.ndone || `E0.nfault != `E1.nfault) fail($sformatf("done/fault ref %0d/%0d tiled %0d/%0d", `E0.ndone, `E0.nfault, `E1.ndone, `E1.nfault));
            if (`E0.err != 0 || `E1.err != 0) fail($sformatf("environment rule errors ref %0d tiled %0d", `E0.err, `E1.err));
            if ((kind == 11 || rtf != 0) != (`E0.nfault != 0)) fail("reference fault expectation");
            if (`E0.nfault == 0 && fbad == 0) begin
                for (l = 0; l < 8; l = l + 1) begin
                    if (`E0.nrq[l] != `E1.nrq[l]) fail($sformatf("wrq count lane %0d: %0d vs %0d", l, `E0.nrq[l], `E1.nrq[l]));
                    else for (i = 0; i < `E0.nrq[l]; i = i + 1) if (`E0.rq_log[l][i] !== `E1.rq_log[l][i]) fail($sformatf("wrq lane %0d #%0d", l, i));
                    tot_rq = tot_rq + `E0.nrq[l];
                    for (s = 0; s < 4; s = s + 1) begin
                        if (`E0.nw[l][s] != `E1.nw[l][s]) fail($sformatf("wwq count lane %0d stream %0d: %0d vs %0d", l, s, `E0.nw[l][s], `E1.nw[l][s]));
                        else for (i = 0; i < `E0.nw[l][s]; i = i + 1) if (`E0.w_log[l][s][i] !== `E1.w_log[l][s][i])
                            fail($sformatf("wwq lane %0d stream %0d #%0d: %h vs %h", l, s, i, `E0.w_log[l][s][i][278:256], `E1.w_log[l][s][i][278:256]));
                        tot_w = tot_w + `E0.nw[l][s];
                    end
                end
                if (`E0.nfs != 1 || `E1.nfs != 1 || `E0.fs_log[0] !== `E1.fs_log[0]) fail("fs");
                if (`E0.nqb != 128 || `E1.nqb != 128) fail($sformatf("qb count %0d vs %0d", `E0.nqb, `E1.nqb));
                else for (i = 0; i < 128; i = i + 1) if (`E0.qb_log[i] !== `E1.qb_log[i]) fail($sformatf("qb #%0d", i));
                if (`E0.nkin != `E1.nkin || `E0.nkin != (keep_en ? 4 : 0)) fail($sformatf("kin count %0d vs %0d", `E0.nkin, `E1.nkin));
                else for (i = 0; i < `E0.nkin; i = i + 1) begin
                    if (`E0.kin_log[i] !== `E1.kin_log[i]) fail($sformatf("kin #%0d", i));
                    for (j = 3; j < 345; j = j + 1) fkept = fkept + integer'(`E0.kin_log[i][j]);
                end
                if (keep_en && (`E0.kin_at_last != 4 || `E1.kin_at_last != 4)) fail("last query block before the kin beats");
                tot_fs = tot_fs + 1; tot_qb = tot_qb + 128; tot_kin = tot_kin + `E0.nkin; tot_kept = tot_kept + fkept;
                nok = nok + 1; cyc_r = cyc_r + (`E0.t_done - t0); cyc_t = cyc_t + (`E1.t_done - t0);
                if (`E1.t_done - `E0.t_done > dmax) dmax = `E1.t_done - `E0.t_done;
                if (`E1.t_done - `E0.t_done < dmin) dmin = `E1.t_done - `E0.t_done;
                keepf_n = keepf_n + integer'(keep_en); candf_n = candf_n + integer'(cand_en); hasr_n = hasr_n + integer'(has_r);
            end else if (`E0.nfault != 0) nflt = nflt + 1;
            if (verbose != 0 || fbad != 0)
                $display("FRAME %0d kind %0d keep %0d cand %0d r %0d k %0d c_n %0d c_stride %0d rt %0d: ref %0d cyc, tiled %0d cyc, kept %0d, bad %0d",
                         f, kind, keep_en, cand_en, has_r, k, c_n, c_stride, f_rt, `E0.t_done - t0, `E1.t_done - t0, fkept, fbad);
            bad = bad + fbad;
            if (bad > 40) f = nfr;
            if (rtf != 0 || fbad != 0) begin        // the reference is not re-startable after a mid-frame fault
                rst_n = 0; erst = 1; repeat (6) @(negedge clk); rst_n = 1; erst = 0; repeat (8) @(negedge clk);
                `E0.err = 0; `E1.err = 0;
            end
        end
        $display("IDXW_EQUIV_STATS MUT=%0d RDL=%0d seed=%0d frames=%0d ok=%0d fault=%0d keep_frames=%0d cand_frames=%0d r_frames=%0d wrq=%0d fs=%0d qb=%0d kin=%0d wwq=%0d kept_bits=%0d cyc_ref=%0d cyc_tiled=%0d delta_min=%0d delta_max=%0d",
                 MUT, RDL, seed, nfr, nok, nflt, keepf_n, candf_n, hasr_n, tot_rq, tot_fs, tot_qb, tot_kin, tot_w, tot_kept, cyc_r, cyc_t, dmin, dmax);
        if (bad == 0 && tot_kept > 0 && nok > 0) $display("IDXW_EQUIV PASS"); else $display("IDXW_EQUIV FAIL mismatches=%0d kept_bits=%0d", bad, tot_kept);
        $finish;
    end
endmodule
