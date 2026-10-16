`timescale 1ns/1ps
// hgi-1010/g (2026-10-10): THROUGHPUT bench of the ATT unit die body ot_hgi_att_unit (derived from tb_hgi_att_unit):
// production record shapes (tools/hgi_adapters/att_tput_vectors.py), records back to back, at the r25 engine geometry
// (ATT_H 16 heads, ATT_NL 4 row lanes, ATT_TD 64; ATT_D head_dim), on the REAL HGI VM (ot_hgi_vm_unit NC 2).
// HBM lane model: +KLAT=n -> always ready, in order, one sector a cycle, each answered n cycles after its request
// (a pipelined HBM at the measured first access); no +KLAT -> the random-order stalling model of tb_hgi_att_unit.
// Prints per record "REC <case> <j> op <op> disp <cycle> ret <cycle>" and HGI_ATT_TPUT PASS / FAIL (exact VM words).
module tb_hgi_att_tput;
`ifndef ATT_H
 `define ATT_H 16
`endif
`ifndef ATT_D
 `define ATT_D 512
`endif
`ifndef ATT_NL
 `define ATT_NL 4
`endif
`ifndef ATT_TD
 `define ATT_TD 64
`endif
`ifndef ATT_PIPE
 `define ATT_PIPE 0
`endif
    `include "au_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [255:0] casem [0:NCASE-1]; reg [1215:0] recm [0:NREC-1]; reg [63:0] vmim [0:NVMI-1];
    reg [295:0] hbmm [0:NHBM-1]; reg [63:0] expm [0:NEXP-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/au_case.mem"}, casem); $readmemh({dir, "/au_rec.mem"}, recm);
        $readmemh({dir, "/au_vmi.mem"}, vmim); $readmemh({dir, "/au_hbm.mem"}, hbmm); $readmemh({dir, "/au_exp.mem"}, expm);
    end
    integer errors = 0, cyc = 0, seed = 7; always @(posedge clk) cyc <= cyc + 1;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 7; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
`ifdef ATT_TRACE
    always @(posedge clk) if (cyc % 20000 == 0) begin
        $display("TRACE cyc %0d st %0d scn %0d tb %0d sc_hold %0d sfr %0d sfw %0d vo_n %0d so_h %0d so_r %0d fi_row %0d co_row %0d blk0 %0d kv_v %0d",
            cyc, u.st, u.scn, u.tb, u.sc_hold, u.sfr, u.sfw, u.vo_n, u.so_h, u.so_r, u.fi_row, u.co_row, u.blk0, u.kv_v); $fflush; end
`endif
`ifdef MUT_RING
    localparam integer MR = 1;
`else
    localparam integer MR = 0;
`endif
`ifdef MUT_ROW
    localparam integer MROW = 1;
`else
    localparam integer MROW = 0;
`endif
`ifdef MUT_LANE
    localparam integer MLANE = 1;
`else
    localparam integer MLANE = 0;
`endif
    localparam integer SPRL = `ATT_D * 4 / 32;
    reg rst_n = 0; reg [1215:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire hq_v; reg hq_rdy = 0; wire [34:0] hq_addr; wire [7:0] hq_tag;
    reg hr_v = 0; reg [7:0] hr_tag = 0; reg [255:0] hr_data = 0;
    // PIPE = 2 row lanes: the HBM side (one request = one beat of up to NL rows; lane (s, l) returns sector l of slot
    // s's row in order).  Die bandwidth model: a beat's sectors leave no earlier than KLAT after the request and the die
    // delivers at most BWS sectors a cycle (+BWS, default 99 = 3,166.7 B/cycle / 32 B).
    wire wq_v, wq_rdy = 1'b1; wire [`ATT_NL-1:0] wq_sv; wire [`ATT_NL*40-1:0] wq_row; wire [7:0] wq_nsec;
    reg [`ATT_NL*SPRL-1:0] wl_v = 0; reg [`ATT_NL*SPRL*256-1:0] wl_d = 0;
    ot_hgi_att_unit #(.H(`ATT_H), .D(`ATT_D), .TD(`ATT_TD), .NL(`ATT_NL), .PIPE(`ATT_PIPE), .MUT_RING(MR), .MUT_ROW(MROW), .MUT_LANE(MLANE)) u (
        .wq_v(wq_v), .wq_rdy(wq_rdy), .wq_sv(wq_sv), .wq_row(wq_row), .wq_nsec(wq_nsec), .wl_v(wl_v), .wl_d(wl_d),.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_c(cur[895:640]), .rec_o(cur[1151:896]),
        .rec_n_b(cur[1172:1152]), .rec_n_c(cur[1193:1173]), .rec_pos1(cur[1214:1194]), .rec_done(done),
        .rec_fault(fault), .halted(halted), .vmq(uq), .vmr(ur), .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr),
        .hq_tag(hq_tag), .hr_v(hr_v), .hr_tag(hr_tag), .hr_data(hr_data));
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status());
    reg [255:0] hbm [longint];
    // row-lane model state: a FIFO of beats {release cycle, slot mask, row addresses, nsec}
    longint bq_t [$]; reg [`ATT_NL-1:0] bq_m [$]; reg [`ATT_NL*40-1:0] bq_r [$]; reg [7:0] bq_n [$];
    integer bws = 99; longint bw_next = 0, lane_secs = 0; real bw_acc = 0;
    initial if (!$value$plusargs("BWS=%d", bws)) bws = 99;
    always @(posedge clk) begin : lanes_model
        longint t; integer s_, l_, nrow;
        wl_v <= 0;
        if (rst_n && wq_v && wq_rdy) begin
            nrow = 0; for (s_ = 0; s_ < `ATT_NL; s_ = s_ + 1) nrow = nrow + wq_sv[s_];
            // the die's bandwidth: this beat's sectors take nrow * nsec / BWS cycles of the shared bus
            if (bw_acc < cyc) bw_acc = cyc;                       // bw_acc: when the shared bus is next free
            bw_acc = bw_acc + (nrow * wq_nsec) * 1.0 / bws;
            t = cyc + ((klat >= 0) ? klat : 40);
            if (t < $rtoi(bw_acc)) t = $rtoi(bw_acc);
            bq_t.push_back(t); bq_m.push_back(wq_sv); bq_r.push_back(wq_row); bq_n.push_back(wq_nsec);
        end
        if (bq_t.size() > 0 && cyc >= bq_t[0]) begin
            for (s_ = 0; s_ < `ATT_NL; s_ = s_ + 1) if (bq_m[0][s_])
                for (l_ = 0; l_ < bq_n[0]; l_ = l_ + 1) begin
                    wl_v[s_ * SPRL + l_] <= 1'b1;
                    wl_d[(s_ * SPRL + l_) * 256 +: 256] <= hbm.exists((bq_r[0][s_ * 40 +: 40] >> 5) + l_) ? hbm[(bq_r[0][s_ * 40 +: 40] >> 5) + l_] : 256'd0;
                    lane_secs = lane_secs + 1;
                end
            void'(bq_t.pop_front()); void'(bq_m.pop_front()); void'(bq_r.pop_front()); void'(bq_n.pop_front());
        end
    end
    reg [42:0] rq [$]; reg [42:0] cq; integer pk, lat = 0, klat = -1; longint rt [$];
    initial if (!$value$plusargs("KLAT=%d", klat)) klat = -1;
    always @(posedge clk) begin
        hq_rdy <= (klat >= 0) ? 1'b1 : (($random(seed) & 3) != 0);
        if (rst_n && hq_v && hq_rdy) begin rq.push_back({hq_tag, hq_addr}); rt.push_back(cyc); end
        hr_v <= 1'b0;
        if (klat >= 0) begin
            if (rq.size() > 0 && cyc >= rt[0] + klat) begin
                cq = rq.pop_front(); void'(rt.pop_front());
                hr_v <= 1'b1; hr_tag <= cq[42:35]; hr_data <= hbm.exists(cq[34:0]) ? hbm[cq[34:0]] : 256'd0;
            end
        end else begin
            if (lat > 0) lat = lat - 1;
            else if (rq.size() > 0 && ($random(seed) & 3) != 0) begin
                pk = $unsigned($random(seed)) % rq.size(); cq = rq[pk]; rq.delete(pk); rt.delete(pk);
                hr_v <= 1'b1; hr_tag <= cq[42:35]; hr_data <= hbm.exists(cq[34:0]) ? hbm[cq[34:0]] : 256'd0;
                lat = $unsigned($random(seed)) % 3;
            end
        end
    end
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    integer nd, nf;
    always @(posedge clk) begin if (rst_n && done) nd = nd + 1; if (rst_n && fault) nf = nf + 1; end
    integer td, c, j, t, r0, nr, v0, nv, h0, nh, e0, ne, t0, words = 0, cerr, c_lo = 0, c_hi = NCASE, c_st = 1; reg [31:0] qd;
    initial begin
        if ($value$plusargs("FIRST=%d", c_lo)) ; if ($value$plusargs("LAST=%d", c_hi)) ; if ($value$plusargs("STEP=%d", c_st)) ;
        repeat (3) @(posedge clk);
        for (c = c_lo; c < c_hi && c < NCASE; c = c + c_st) begin
            r0 = casem[c][255:224]; nr = casem[c][223:192]; v0 = casem[c][191:160]; nv = casem[c][159:128];
            h0 = casem[c][127:96]; nh = casem[c][95:64]; e0 = casem[c][63:32]; ne = casem[c][31:0];
            rst_n = 0; hbm.delete(); rq.delete(); rt.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][295:256]] = hbmm[h0 + j][255:0];
            for (j = 0; j < nv; j = j + 1) vm_req(1'b1, vmim[v0 + j][63:32], vmim[v0 + j][31:0], qd);
            nd = 0; nf = 0; t0 = cyc;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); td = cyc; #0.1 rec_v = 0;
                t = 0; while (nd <= j && nf == 0 && t < 40000000) begin @(posedge clk); t = t + 1; end
                $display("REC %0d %0d op %0d disp %0d ret %0d", c, j, cur[123:118], td, cyc); $fflush;
            end
            if (nd != nr || nf != 0) begin $display("ERR case %0d: done %0d of %0d, faults %0d (state %0d)", c, nd, nr, nf, u.st); errors = errors + 1; end
            cerr = 0;
            for (j = 0; j < ne; j = j + 1) begin
                vm_req(1'b0, expm[e0 + j][63:32], 0, qd);
                if (qd !== expm[e0 + j][31:0]) begin
                    if (cerr < 6) $display("ERR case %0d VM[%0d] = %h expected %h", c, expm[e0 + j][63:32], qd, expm[e0 + j][31:0]);
                    cerr = cerr + 1; end
            end
            errors = errors + cerr; words = words + ne;
            $display("case %0d: %0d records in %0d cycles, %0d words, %0d wrong", c, nr, cyc - t0, ne, cerr); $fflush;
        end
        $display("summary: ATT tput cases %0d..%0d step %0d, %0d VM words checked", c_lo, c_hi, c_st, words);
        if (errors == 0) $display("HGI_ATT_TPUT PASS"); else $display("HGI_ATT_TPUT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
