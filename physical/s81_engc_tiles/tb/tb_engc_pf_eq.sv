`timescale 1ns/1ps
// el1011-ds-misc/engram 2026-10-11: LOCKSTEP bench of the all-tile prefetch path {T_WS write side -> T_PBB (bank 1,
// write transit) -> T_PBC (bank 0) -> T_PBC (bank 2); T_IO read request / decode / t_vm} against the HIER sub-function
// ot_dsrom_engram_prefetch_h, same write / read stimulus, VM read stream (out_v / data / ce / ue) compared in order,
// sticky fault compared at the end.  Phases: full sequential fill, then random write bursts / read bursts / mixed
// slot-disjoint traffic (reads never target a row written in the last 16 cycles: the tile write commit is later).
module tb_engc_pf_eq;
    reg ck = 0, rst = 0; always #0.5 ck = ~ck;
    reg wr_v = 0, rd_v = 0; reg [10:0] wr_addr = 0, rd_addr = 0; reg [511:0] wr_data = 0;
    // reference
    reg [1:0] rq = 0; always @(posedge ck or negedge rst) if (!rst) rq <= 0; else rq <= {rq[0], 1'b1};
    wire r_v, r_ce, r_ue, r_fault, r_wp; wire [511:0] r_d;
    ot_dsrom_engram_prefetch_h u_ref (.ck(ck), .rst_n(rq[1]), .wr_v(wr_v), .wr_addr(wr_addr), .wr_data(wr_data),
        .wr_pending(r_wp), .rd_v(rd_v), .rd_addr(rd_addr), .out_v(r_v), .out_data(r_d), .out_ce(r_ce), .out_ue(r_ue),
        .fault(r_fault));
    // tiles
    wire werr, werr_w; wire [5:0] w_oh, x0_oh, x1_oh, r0_oh, r1_oh, r2_oh; wire [7:0] w_a, x0_a, x1_a, r0_a, r1_a, r2_a;
    wire [255:0] b1_d, rd0, rd1, rd2w; wire [319:0] x_d, x0_d; wire [63:0] x1_d; wire [531:0] t_vm;
    wire [34:0] t_hq; wire [264:0] lk_hr; wire [8:0] c_done; wire [1:0] c_st; wire [2:0] cfg_o; wire [3:0] vrel_o;
    wire [17:0] jn_o;
    reg werr_r = 0; always @(posedge ck) werr_r <= werr;     // the T_WIN relay stage
    ot_engc_t_ws u_ws (.ck(ck), .rst(rst), .wr_v(wr_v), .wr_addr(wr_addr), .wr_data(wr_data), .werr(werr),
        .w_oh(w_oh), .w_a(w_a), .b1_d(b1_d), .x_d(x_d), .lk_hqv(1'b0), .lk_hqa(31'd0), .lk_hqt(3'd0), .t_hq(t_hq),
        .f_hr(265'd0), .lk_hr(lk_hr));
    ot_engc_t_pbb u_pb1 (.ck(ck), .rst(rst), .w_oh(w_oh), .w_a(w_a), .w_d(b1_d), .x_d(x_d),
        .x_oh(x0_oh), .x_a(x0_a), .x_do(x0_d), .r_oh(r1_oh), .r_a(r1_a), .r_d(rd1));
    ot_engc_t_pbc u_pb0 (.ck(ck), .rst(rst), .w_oh(x0_oh), .w_a(x0_a), .w_d(x0_d[255:0]), .x_d(x0_d[319:256]),
        .x_oh(x1_oh), .x_a(x1_a), .x_do(x1_d), .r_oh(r0_oh), .r_a(r0_a), .r_d(rd0));
    ot_engc_t_pbc u_pb2 (.ck(ck), .rst(rst), .w_oh(x1_oh), .w_a(x1_a), .w_d({192'd0, x1_d}), .x_d(64'd0),
        .x_oh(), .x_a(), .x_do(), .r_oh(r2_oh), .r_a(r2_a), .r_d(rd2w));
    ot_engc_t_io u_io (.ck(ck), .rst(rst), .c_cmd(85'd0), .c_done(c_done), .c_st(c_st), .f_cfg(3'd0), .cfg_o(cfg_o),
        .f_vm({3'd0, 1'b0, rd_addr, rd_v}), .t_vm(t_vm), .rdy_i(8'd0), .perr_i(8'd0), .vrel_o(vrel_o), .jn_o(jn_o),
        .wn_i(16'd0), .jf_i(1'b0), .werr_i(werr_r), .r0_oh(r0_oh), .r1_oh(r1_oh), .r2_oh(r2_oh), .r0_a(r0_a),
        .r1_a(r1_a), .r2_a(r2_a), .rd0(rd0), .rd1(rd1), .rd2(rd2w[63:0]));
    // stream compare
    reg [513:0] q [0:4095]; integer qh = 0, qt = 0, n = 0, bad = 0;
    always @(posedge ck) begin
        if (r_v) begin q[qt % 4096] <= {r_ue, r_ce, r_d}; qt <= qt + 1; end
        if (t_vm[0]) begin
            if (qh >= qt) begin bad = bad + 1; if (bad < 5) $display("MISMATCH extra tile output"); end
            else if (q[qh % 4096] !== {t_vm[514], t_vm[513], t_vm[512:1]}) begin
                bad = bad + 1; if (bad < 5) $display("MISMATCH read %0d", n); end
            qh = qh + 1; n = n + 1;
        end
    end
    integer i, ph, cyc, last_w [0:2047]; reg [10:0] a;
    function [10:0] ra(input integer x); ra = {x[10:8], 5'(x % 24), x[2:0]}; endfunction
    task tick; begin @(negedge ck); cyc = cyc + 1; end endtask
    initial begin
        cyc = 0; for (i = 0; i < 2048; i = i + 1) last_w[i] = -100;
        repeat (4) tick; rst = 1; repeat (6) tick;
        // fill
        for (i = 0; i < 1536; i = i + 1) begin
            wr_v = 1; wr_addr = {3'(i / 192), 5'((i % 192) / 8), 3'(i % 8)};
            wr_data = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                       $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            last_w[wr_addr] = cyc; tick;
        end
        wr_v = 0; repeat (20) tick;
        for (ph = 0; ph < 60; ph = ph + 1) begin
            for (i = 0; i < 200; i = i + 1) begin
                wr_v = 0; rd_v = 0;
                if ((ph % 3) != 1 && ($urandom % 4) != 0) begin       // write
                    wr_v = 1; wr_addr = ra($urandom); if (($urandom % 500) == 0) wr_addr[7:3] = 5'd27;   // rare address fault
                    wr_data = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                               $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
                    if (wr_addr[7:3] < 24) last_w[wr_addr] = cyc;
                end
                if ((ph % 3) != 0 && ($urandom % 3) != 0) begin       // read (never a row written < 16 cycles ago)
                    a = ra($urandom);
                    if (cyc - last_w[a] > 16 && !(wr_v && wr_addr == a)) begin rd_v = 1; rd_addr = a; end
                end
                tick;
            end
            wr_v = 0; rd_v = 0; repeat (20) tick;
        end
        repeat (40) tick;
        if (r_fault !== t_vm[515]) begin bad = bad + 1; $display("MISMATCH fault ref %b tiles %b", r_fault, t_vm[515]); end
        if (qh != qt) begin bad = bad + 1; $display("MISMATCH count ref %0d tiles %0d", qt, qh); end
        if (bad == 0 && n > 1000) $display("ENGC_PF_EQ PASS reads=%0d fault=%b", n, r_fault);
        else $display("ENGC_PF_EQ FAIL bad=%0d reads=%0d", bad, n);
        $finish;
    end
endmodule
