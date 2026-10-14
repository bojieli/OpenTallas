`timescale 1ns/1ps
// Randomized frame EQUIVALENCE bench: ot_hgi_idx_ix2 (MUT) against the reference ot_hgi_idx_index_w (always MUT 0).
// Each adapter has its own behavioural 8-lane VM (same memory image, independent random latency / credits / grants)
// and its own behavioural selector (consumes fs / qb / kin, returns qb credits, emits the same to / co beats on its
// own toc / coc credits, then ev[0]).  Compared per frame: done / fault, fs, the kin beats in order, the 128 qb
// blocks in order, and the VM writes as a set (sector, masked data, mask, count).  ix2 only: every kin beat before
// the last qb block.  +MEAS=<rt>: fixed round trip, credits every cycle; prints FRONT (go -> last qb block) and
// BACK (last to / co beat -> done) of both adapters per shape.
module tb_vm8 #(parameter integer ID = 0, parameter integer LQ = 10) (
    input wire clk, input wire [127:0] wrq, output reg [7:0] wrq_cr, output reg [8*257-1:0] wrr, output reg rg_gnt,
    input wire [8*280-1:0] wwq, output reg [7:0] wwq_cr, output reg [7:0] wwq_done, output reg wg_gnt
);
    int rt = 8, jit = 8, meas = 0, cyc = 0, nw = 0, dup = 0, nrd = 0;
    int rq [8][$]; int rdue [8][$]; int wdue [8][$]; int last [8];
    logic [255:0] sh [int]; logic [7:0] shm [int];
    task automatic clear(); sh.delete(); shm.delete(); nw = 0; dup = 0; nrd = 0; endtask
    initial begin wrq_cr = 0; wrr = 0; rg_gnt = 0; wwq_cr = 0; wwq_done = 0; wg_gnt = 0; end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        rg_gnt <= meas != 0 || ($urandom_range(0, 7) != 0); wg_gnt <= meas != 0 || ($urandom_range(0, 7) != 0);
        for (int l = 0; l < 8; l++) begin
            automatic int d;
            wrq_cr[l] <= 1'b0; wrr[l*257 + 256] <= 1'b0; wwq_cr[l] <= 1'b0; wwq_done[l] <= 1'b0;
            if (wrq[l*16 + 15]) begin
                if (int'(wrq[l*16 +: 3]) != l) begin $display("VM%0d read lane %0d sector %0d", ID, l, wrq[l*16 +: 15]); $fatal; end
                d = cyc + rt - 1 + (jit != 0 ? $urandom_range(0, jit) : 0); if (d <= last[l]) d = last[l] + 1; last[l] = d;
                rq[l].push_back(int'(wrq[l*16 +: 15])); rdue[l].push_back(d); nrd++;
                if (rq[l].size() > LQ) begin $display("VM%0d read credit overrun lane %0d", ID, l); $fatal; end
            end
            if (rq[l].size() != 0 && rdue[l][0] <= cyc) begin
                wrr[l*257 +: 257] <= {1'b1, tb_hgi_idx_ix2_equiv.mem[rq[l][0]]}; wrq_cr[l] <= 1'b1;
                void'(rq[l].pop_front()); void'(rdue[l].pop_front());
            end
            if (wwq[l*280 + 279]) begin
                automatic int s = int'(wwq[l*280 + 264 +: 15]); automatic logic [7:0] m = wwq[l*280 +: 8];
                automatic logic [255:0] x = sh.exists(s) ? sh[s] : '0; automatic logic [7:0] mm = shm.exists(s) ? shm[s] : '0;
                if (s % 8 != l) begin $display("VM%0d write lane %0d sector %0d", ID, l, s); $fatal; end
                for (int w = 0; w < 8; w++) if (m[w]) begin if (mm[w]) dup++; x[w*32 +: 32] = wwq[l*280 + 8 + w*32 +: 32]; mm[w] = 1'b1; end
                sh[s] = x; shm[s] = mm; nw++;
                wdue[l].push_back(cyc + (meas != 0 ? 2 : $urandom_range(1, 12)));
                if (wdue[l].size() > LQ) begin $display("VM%0d write credit overrun lane %0d", ID, l); $fatal; end
            end
            if (wdue[l].size() != 0 && wdue[l][0] <= cyc) begin wwq_cr[l] <= 1'b1; wwq_done[l] <= 1'b1; void'(wdue[l].pop_front()); end
        end
    end
endmodule

module tb_sel #(parameter integer ID = 0) (
    input wire clk, input wire [89:0] fs, input wire [1047:0] qb, output reg qbr, input wire [344:0] kin,
    output reg [611:0] to, input wire toc, output reg [71:0] co, input wire coc, output reg [1:0] ev
);
    int meas = 0, cyc = 0, nfs = 0, t_qb = 0, t_kin = 0, t_beat = 0, ti = 0, ci = 0, tcred = 8, ccred = 8, qout = 0, evw = -1;
    logic [89:0] fs_d; logic [344:0] kins [$]; logic [1047:0] qbs [$]; int qdue [$]; bit evd;
    task automatic clear(); nfs = 0; kins.delete(); qbs.delete(); qdue.delete(); ti = 0; ci = 0; tcred = 8; ccred = 8; qout = 0;
        evw = -1; evd = 0; t_qb = 0; t_kin = 0; t_beat = 0; endtask
    initial begin qbr = 0; to = 0; co = 0; ev = 0; end
    always @(posedge clk) begin
        cyc <= cyc + 1; qbr <= 1'b0; to[0] <= 1'b0; co[0] <= 1'b0; ev <= 2'd0;
        if (fs[0]) begin fs_d = fs; nfs++; end
        if (kin[0]) begin kins.push_back(kin); t_kin = cyc; end
        if (toc) tcred++;
        if (coc) ccred++;
        if (qb[0]) begin
            qbs.push_back(qb); t_qb = cyc; qout++; qdue.push_back(cyc + (meas != 0 ? 0 : $urandom_range(0, 3)));
            if (qout > 4) begin $display("SEL%0d qb credit overrun", ID); $fatal; end
        end
        if (qdue.size() != 0 && qdue[0] <= cyc) begin qbr <= 1'b1; qout--; void'(qdue.pop_front()); end
        if (qbs.size() == 128 && !evd) begin
            if (ti < tb_hgi_idx_ix2_equiv.nto && tcred > 0 && (meas != 0 || $urandom_range(0, 2) != 0)) begin
                to <= tb_hgi_idx_ix2_equiv.tob[ti]; ti++; tcred--; t_beat = cyc + 1; end
            if (ci < tb_hgi_idx_ix2_equiv.nco && ccred > 0 && (meas != 0 || $urandom_range(0, 2) != 0)) begin
                co <= tb_hgi_idx_ix2_equiv.cob[ci]; ci++; ccred--; t_beat = cyc + 1; end
            if (ti == tb_hgi_idx_ix2_equiv.nto && ci == tb_hgi_idx_ix2_equiv.nco) begin
                if (evw < 0) evw = meas != 0 ? 0 : $urandom_range(0, 6);
                else if (evw == 0) begin ev[0] <= 1'b1; evd = 1; end else evw--;
            end
        end
    end
endmodule

module tb_hgi_idx_ix2_equiv #(parameter integer MUT = 0);
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    logic [255:0] mem [0:32767];
    logic [611:0] tob [0:127]; logic [71:0] cob [0:1023]; int nto = 0, nco = 0;
    reg go = 0; reg [11:0] k = 1; reg cand_en = 0, keep_en = 0; reg [31:0] n = 0; reg [6:0] rank = 0; reg [19:0] pos = 0;
    reg [17:0] a_base = 0, b_base = 0, c_base = 0, o_base = 0, r_base = 0, d_base = 0, d_stride = 0, c_stride = 0; reg [11:0] c_n = 0;
    reg has_r = 0;
    wire [1:0] done, fault, rg_req, wg_req, rg_gnt, wg_gnt, qbr, toc, coc;
    wire [127:0] wrq [0:1]; wire [7:0] wrq_cr [0:1], wwq_cr [0:1], wwq_done [0:1]; wire [8*257-1:0] wrr [0:1];
    wire [8*280-1:0] wwq [0:1]; wire [89:0] fs [0:1]; wire [1047:0] qb [0:1]; wire [344:0] kin [0:1];
    wire [611:0] to [0:1]; wire [71:0] co [0:1]; wire [1:0] ev [0:1];
    ot_hgi_idx_index_w #(.MUT(0), .DL(2), .LQ(10), .NL(8)) u_ref (.clk(clk), .rst_n(rst_n), .go_i(go), .k_i(k), .cand_en_i(cand_en),
        .keep_en_i(keep_en), .n_i(n), .rank_i(rank), .pos_i(pos), .a_base_i(a_base), .b_base_i(b_base), .c_base_i(c_base),
        .o_base_i(o_base), .r_base_i(r_base), .d_base_i(d_base), .d_stride_i(d_stride), .c_stride_i(c_stride), .c_n_i(c_n),
        .has_r_i(has_r), .done(done[0]), .fault(fault[0]), .wrq(wrq[0]), .wrq_cr(wrq_cr[0]), .wrr(wrr[0]), .rg_req(rg_req[0]),
        .rg_gnt(rg_gnt[0]), .wwq(wwq[0]), .wwq_cr(wwq_cr[0]), .wwq_done(wwq_done[0]), .wg_req(wg_req[0]), .wg_gnt(wg_gnt[0]),
        .fs(fs[0]), .qb(qb[0]), .qbr(qbr[0]), .kin(kin[0]), .to(to[0]), .toc(toc[0]), .co(co[0]), .coc(coc[0]), .ev(ev[0]));
    ot_hgi_idx_ix2 #(.MUT(MUT), .LQ(10), .NL(8)) u_ix2 (.clk(clk), .rst_n(rst_n), .go_i(go), .k_i(k), .cand_en_i(cand_en),
        .keep_en_i(keep_en), .n_i(n), .rank_i(rank), .pos_i(pos), .a_base_i(a_base), .b_base_i(b_base), .c_base_i(c_base),
        .o_base_i(o_base), .r_base_i(r_base), .d_base_i(d_base), .d_stride_i(d_stride), .c_stride_i(c_stride), .c_n_i(c_n),
        .has_r_i(has_r), .done(done[1]), .fault(fault[1]), .wrq(wrq[1]), .wrq_cr(wrq_cr[1]), .wrr(wrr[1]), .rg_req(rg_req[1]),
        .rg_gnt(rg_gnt[1]), .wwq(wwq[1]), .wwq_cr(wwq_cr[1]), .wwq_done(wwq_done[1]), .wg_req(wg_req[1]), .wg_gnt(wg_gnt[1]),
        .fs(fs[1]), .qb(qb[1]), .qbr(qbr[1]), .kin(kin[1]), .to(to[1]), .toc(toc[1]), .co(co[1]), .coc(coc[1]), .ev(ev[1]));
    tb_vm8 #(.ID(0)) vm0 (.clk(clk), .wrq(wrq[0]), .wrq_cr(wrq_cr[0]), .wrr(wrr[0]), .rg_gnt(rg_gnt[0]), .wwq(wwq[0]),
        .wwq_cr(wwq_cr[0]), .wwq_done(wwq_done[0]), .wg_gnt(wg_gnt[0]));
    tb_vm8 #(.ID(1)) vm1 (.clk(clk), .wrq(wrq[1]), .wrq_cr(wrq_cr[1]), .wrr(wrr[1]), .rg_gnt(rg_gnt[1]), .wwq(wwq[1]),
        .wwq_cr(wwq_cr[1]), .wwq_done(wwq_done[1]), .wg_gnt(wg_gnt[1]));
    tb_sel #(.ID(0)) s0 (.clk(clk), .fs(fs[0]), .qb(qb[0]), .qbr(qbr[0]), .kin(kin[0]), .to(to[0]), .toc(toc[0]), .co(co[0]),
        .coc(coc[0]), .ev(ev[0]));
    tb_sel #(.ID(1)) s1 (.clk(clk), .fs(fs[1]), .qb(qb[1]), .qbr(qbr[1]), .kin(kin[1]), .to(to[1]), .toc(toc[1]), .co(co[1]),
        .coc(coc[1]), .ev(ev[1]));
    int cyc = 0, t_go, t_end [2], res [2], nbad = 0, nframes = 0, nfault = 0, nkeepbits = 0, seed, frames, meas, shape;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        for (int d = 0; d < 2; d++) if ((done[d] || fault[d]) && res[d] == 0) begin res[d] = done[d] ? 1 : 2; t_end[d] = cyc; end
    end
    function automatic logic [255:0] rnd256(); logic [255:0] x; for (int w = 0; w < 8; w++) x[w*32 +: 32] = $urandom; return x; endfunction
    task automatic setw(input int wa, input logic [31:0] v); mem[wa >> 3][(wa & 7)*32 +: 32] = v; endtask
    // shape: 0 random, 1 L24 (keep_en, C 2,048, k 512), 2 L20 (cand_en, D 1,366, k 512), 3 L2 (neither, k 512)
    task automatic frame(input int sh, input int fno);
        automatic int ill = 0, ncand, okf = 1, cs;
        automatic string why = "";
        keep_en = sh == 1 || (sh == 0 && $urandom_range(0, 2) != 0); cand_en = sh == 2 || (sh == 0 && $urandom_range(0, 1) != 0);
        k = (sh != 0) ? 12'd512 : 12'($urandom_range(1, 512)); n = $urandom_range(1, 10944); pos = 20'($urandom);
        case ($urandom_range(0, 5)) 0: rank = 7'd0; 1: rank = 7'd95; default: rank = 7'($urandom_range(0, 95)); endcase
        has_r = (sh != 0) ? 1'b1 : 1'($urandom);
        c_n = (sh == 1) ? 12'd2048 : 12'($urandom_range(1, 2048));
        a_base = 18'((18'h0800 + $urandom_range(0, 1023)) * 8);
        b_base = 18'(18'h2000 * 8 + ((sh != 0) ? 0 : $urandom_range(0, 63)));
        c_base = 18'(18'h3000 * 8 + ((sh != 0) ? 0 : $urandom_range(0, 63)));
        c_stride = (sh != 0) ? 18'd2048 : 18'(64 * $urandom_range(32, 48));
        o_base = 18'(18'h5000 * 8 + ((sh != 0) ? 0 : $urandom_range(0, 63)));
        r_base = 18'(18'h6000 * 8 + ((sh != 0) ? 0 : $urandom_range(0, 63)));
        d_base = 18'(18'h7000 * 8 + ((sh != 0) ? 0 : $urandom_range(0, 63)));
        d_stride = (sh != 0) ? 18'd2048 : 18'($urandom_range(2048, 2111));
        if (sh == 0 && meas == 0 && $urandom_range(0, 29) == 0) begin ill = 1; if ($urandom_range(0, 1) != 0) k = 12'd0; else rank = 7'd100; end
        for (int s = 0; s < 520; s++) mem[int'(a_base >> 3) + s] = rnd256();
        for (int w = -8; w < 48; w++) setw(int'(b_base) + w, {16'($urandom), 16'd0});
        cs = int'(c_stride);
        for (int j = -8; j < 2056; j++) begin
            automatic logic [31:0] id; automatic int ordv = $urandom_range(0, 1367);
            case (meas != 0 ? 9 : $urandom_range(0, 9))                 // +MEAS: production-like sparse table (~1/96 owned)
                0, 1, 2, 3: id = 32'(ordv * 96 + int'(rank));
                4: id = 32'($urandom_range(1368, 2800) * 96 + int'(rank));
                5: id = {$urandom_range(0, 1) != 0 ? 12'($urandom) : 12'd1, 20'(ordv * 96 + int'(rank))};
                6: id = 32'(ordv * 96 + int'(rank)) ^ 32'd32;
                default: id = (meas != 0) ? 32'($urandom_range(0, 131327)) : {12'd0, 20'($urandom)};
            endcase
            setw(int'(c_base) + j, id);
            setw(int'(c_base) + cs + j, ($urandom_range(0, 4) == 0) ? 32'hFF80_0000 : ($urandom_range(0, 9) == 0) ? 32'h7F80_0000 : $urandom);
        end
        nto = (sh != 0) ? 36 : $urandom_range(1, 40);
        for (int i = 0; i < nto; i++) begin
            for (int w = 0; w < 20; w++) tob[i][w*32 +: 32] = $urandom;
            if (sh != 0 && i < 32) tob[i][19:4] = 16'hFFFF;
            tob[i][0] = 1'b1; tob[i][1] = i == nto - 1;
        end
        ncand = cand_en ? ((sh == 2) ? 683 : $urandom_range(1, 200)) : 0; nco = ncand;
        for (int i = 0; i < nco; i++) begin
            cob[i] = {$urandom, $urandom, 8'($urandom)}; cob[i][0] = 1'b1; cob[i][1] = i == nco - 1;
            if (sh == 2) cob[i][5:4] = 2'b11;
        end
        vm0.clear(); vm1.clear(); s0.clear(); s1.clear(); res[0] = 0; res[1] = 0;
        @(posedge clk); #0.1; go = 1; t_go = cyc; @(posedge clk); #0.1; go = 0;
        fork : w
            begin wait (res[0] != 0 && res[1] != 0); disable w; end
            begin repeat (60000) @(posedge clk); disable w; end
        join
        repeat (30) @(posedge clk);
        nframes++;
        if (res[0] == 0 || res[1] == 0) begin okf = 0; why = $sformatf("timeout ref=%0d ix2=%0d", res[0], res[1]); end
        else if (res[0] != res[1]) begin okf = 0; why = $sformatf("done/fault ref=%0d ix2=%0d", res[0], res[1]); end
        else if (res[0] == 2) begin nfault++; if (!ill) begin okf = 0; why = "unexpected fault"; end end
        else begin
            if (ill) begin okf = 0; why = "illegal operand not faulted"; end
            if (s0.nfs != 1 || s1.nfs != 1 || s0.fs_d !== s1.fs_d) begin okf = 0; why = {why, " fs"}; end
            if (s0.kins.size() != s1.kins.size() || s0.kins.size() != (keep_en ? 4 : 0)) begin okf = 0; why = {why, " kin-count"}; end
            else foreach (s0.kins[i]) begin
                if (s0.kins[i] !== s1.kins[i]) begin okf = 0; why = {why, $sformatf(" kin%0d", i)}; end
                nkeepbits += $countones(s0.kins[i][344:3]);
            end
            if (s0.qbs.size() != 128 || s1.qbs.size() != 128) begin okf = 0; why = {why, " qb-count"}; end
            else foreach (s0.qbs[i]) if (s0.qbs[i] !== s1.qbs[i]) begin okf = 0; why = {why, $sformatf(" qb%0d", i)}; break; end
            if (keep_en && s1.t_kin >= s1.t_qb) begin okf = 0; why = {why, " kin-after-last-qb"}; end
            if (vm0.nw != vm1.nw || vm0.sh.size() != vm1.sh.size() || vm0.dup != 0 || vm1.dup != 0) begin okf = 0;
                why = {why, $sformatf(" write-count %0d/%0d", vm0.nw, vm1.nw)}; end
            foreach (vm0.sh[s]) begin
                if (!vm1.sh.exists(s) || vm0.shm[s] !== vm1.shm[s]) begin okf = 0; why = {why, $sformatf(" wmask@%0d", s)}; break; end
                for (int w = 0; w < 8; w++) if (vm0.shm[s][w] && vm0.sh[s][w*32 +: 32] !== vm1.sh[s][w*32 +: 32]) begin
                    okf = 0; why = {why, $sformatf(" wdata@%0d.%0d", s, w)}; break; end
                if (!okf) break;
            end
        end
        if (!okf) begin nbad++; if (nbad <= 8) $display("IX2EQ FRAME %0d shape %0d keep %0d cand %0d rank %0d MISMATCH:%s", fno, sh, keep_en, cand_en, rank, why); end
        if (meas != 0) $display("IX2LAT shape=%0d rt=%0d ok=%0d front_ref=%0d front_ix2=%0d back_ref=%0d back_ix2=%0d total_ref=%0d total_ix2=%0d reads_ref=%0d reads_ix2=%0d",
            sh, meas, okf, s0.t_qb - t_go, s1.t_qb - t_go, t_end[0] - s0.t_beat, t_end[1] - s1.t_beat, t_end[0] - t_go, t_end[1] - t_go, vm0.nrd, vm1.nrd);
        if (res[0] != 1 || res[1] != 1) begin rst_n = 0; repeat (80) @(posedge clk); rst_n = 1; repeat (10) @(posedge clk); end
    endtask
    initial begin
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("FRAMES=%d", frames)) frames = 100;
        if (!$value$plusargs("MEAS=%d", meas)) meas = 0;
        void'($urandom(seed));
        if (meas != 0) begin vm0.rt = meas; vm1.rt = meas; vm0.jit = 0; vm1.jit = 0; vm0.meas = 1; vm1.meas = 1; s0.meas = 1; s1.meas = 1; end
        else begin vm0.rt = 4 + seed % 3 * 6; vm1.rt = vm0.rt; vm0.jit = 4 + seed % 5 * 3; vm1.jit = vm0.jit; end
        repeat (10) @(posedge clk); rst_n = 1; repeat (10) @(posedge clk);
        for (int f = 0; f < frames; f++) begin
            shape = (meas != 0) ? 1 + f % 3 : (f % 8 == 1) ? 1 : (f % 8 == 3) ? 2 : (f % 8 == 5) ? 3 : 0;
            frame(shape, f);
        end
        $display("IX2EQ MUT=%0d seed=%0d frames=%0d faults=%0d keepbits=%0d mismatches=%0d %s", MUT, seed, nframes, nfault, nkeepbits, nbad,
            nbad == 0 ? "PASS" : "FAIL");
        $finish;
    end
endmodule
