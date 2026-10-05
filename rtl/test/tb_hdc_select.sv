`timescale 1ns/1ps
// Streaming check of rtl/hdc/v41/ot_hdc_select.sv against vectors from the
// golden's topk_lowest_index (tools/rtl_hdc_v41_select_campaign.py).
//
// +IN=<file>   one element per line: "<value hex> <index hex> <last> <k>"
// +EXP=<file>  per segment "S <count>", then <count> lines "<index hex> <ninf>"
//              in the order the unit must emit them
// +BUBBLE=<p>  percent of cycles the driver withholds an element
// +GAP=<p>     percent of segments followed by an idle gap of up to 4K cycles
// +SEED=<n>    driver PRNG seed
//
// Every output is compared in order; out_last must mark exactly each
// segment's final index; the first output of every non-empty segment must
// arrive exactly LAT cycles after its last element was accepted.
module tb_hdc_select
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer K = 6;
    parameter integer VW = 32;
    parameter integer IW = 16;
    parameter integer ORDER = 1;
    localparam integer KW = $clog2(K + 1);
    // edges from the one that accepts the last element to the one that registers
    // the first output (the checker samples that output one edge later)
    localparam integer LAT = K + 2 + (ORDER != 0 ? K : 0);
    localparam integer MAXSEG = 1 << 20;

    reg          rst_n = 1'b0;
    reg          in_valid = 1'b0, in_last = 1'b0;
    reg [VW-1:0] in_val = 0;
    reg [IW-1:0] in_idx = 0;
    reg [KW-1:0] in_k = 0;
    wire         in_ready, out_valid, out_last, out_ninf, busy;
    wire [IW-1:0] out_idx;
    ot_hdc_select #(.K(K), .VW(VW), .IW(IW), .ORDER(ORDER)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_last(in_last),
        .in_val(in_val), .in_idx(in_idx), .in_k(in_k), .out_valid(out_valid), .out_last(out_last),
        .out_idx(out_idx), .out_ninf(out_ninf), .busy(busy));

    integer fin, fexp, rc;
    integer bubble = 0, gap = 0, maxcyc = 200000000;
    reg [31:0] rng = 32'h2545F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg [8*512-1:0] fname;
    integer cyc = 0;
    integer segs_in = 0, elems = 0, stall = 0, idle_left = 0;
    reg     have = 1'b0, eof = 1'b0, drv_done = 1'b0;
    reg [31:0] f_val, f_idx, f_last, f_k;
    integer acc_cyc [0:MAXSEG-1];

    // checker state
    integer seg_out = 0, left = 0, first_pend = 0, outputs = 0, errors = 0, exp_done = 0;
    integer lat_min = 1 << 30, lat_max = -1, last_out_cyc = 0;
    reg [31:0] e_idx, e_ninf, e_cnt;
    reg [8*8-1:0] tag;

    task automatic fetch;
        begin
            rc = $fscanf(fin, "%h %h %d %d\n", f_val, f_idx, f_last, f_k);
            if (rc != 4) begin eof = 1'b1; have = 1'b0; end
            else have = 1'b1;
        end
    endtask

    // next segment header with a nonzero count (count-0 segments emit nothing)
    task automatic next_segment;
        begin
            left = 0;
            while (left == 0 && !exp_done) begin
                rc = $fscanf(fexp, "S %d\n", e_cnt);
                if (rc != 1) exp_done = 1;
                else begin
                    left = e_cnt; first_pend = (e_cnt != 0);
                    if (e_cnt == 0) seg_out = seg_out + 1;
                end
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("IN=%s", fname)) begin $display("need +IN"); $finish; end
        fin = $fopen(fname, "r");
        if (!$value$plusargs("EXP=%s", fname)) begin $display("need +EXP"); $finish; end
        fexp = $fopen(fname, "r");
        if (fin == 0 || fexp == 0) begin $display("cannot open vectors"); $finish; end
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("GAP=%d", gap)) gap = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 200000000;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        fetch;
        next_segment;
    end

    // -- driver ------------------------------------------------------------------------
    reg show;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n) begin
            if (in_valid && !in_ready) stall = stall + 1;
            if (in_valid && in_ready) begin
                elems = elems + 1;
                if (in_last) begin
                    acc_cyc[segs_in] = cyc;
                    segs_in = segs_in + 1;
                    rng = xs(rng);
                    if ((rng % 100) < gap) begin rng = xs(rng); idle_left = rng % (4 * K + 1); end
                end
                fetch;
            end
            rng = xs(rng);
            show = have && idle_left == 0 && (rng % 100) >= bubble;
            if (idle_left > 0) idle_left = idle_left - 1;
            // hold a withheld-but-presented element (valid must not drop once shown
            // is not required by the unit; the driver may withdraw it freely)
            in_valid <= show;
            in_val   <= f_val[VW-1:0];
            in_idx   <= f_idx[IW-1:0];
            in_last  <= (f_last != 0);
            in_k     <= f_k[KW-1:0];
            if (!have) drv_done <= 1'b1;
        end
    end

    // -- checker -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst_n && out_valid) begin
            outputs = outputs + 1;
            last_out_cyc = cyc;
            if (exp_done || left == 0) begin
                if (errors < 20) $display("EXTRA output idx=%h at cycle %0d", out_idx, cyc);
                errors = errors + 1;
            end else begin
                rc = $fscanf(fexp, "%h %d\n", e_idx, e_ninf);
                if (first_pend) begin
                    first_pend = 0;
                    if (cyc - 1 - acc_cyc[seg_out] < lat_min) lat_min = cyc - 1 - acc_cyc[seg_out];
                    if (cyc - 1 - acc_cyc[seg_out] > lat_max) lat_max = cyc - 1 - acc_cyc[seg_out];
                end
                left = left - 1;
                if (out_idx !== e_idx[IW-1:0] || out_ninf !== e_ninf[0] || out_last !== (left == 0)) begin
                    if (errors < 20)
                        $display("MISMATCH seg=%0d got idx=%h ninf=%b last=%b expect idx=%h ninf=%0d last=%0d",
                                 seg_out, out_idx, out_ninf, out_last, e_idx, e_ninf, left == 0);
                    errors = errors + 1;
                end
                if (left == 0) begin
                    seg_out = seg_out + 1;
                    next_segment;
                end
            end
        end
        if (drv_done && exp_done && !busy && cyc > last_out_cyc + 4 * K + 16 && cyc > 64) begin
            $display("SELECT K=%0d VW=%0d IW=%0d ORDER=%0d segments=%0d elements=%0d outputs=%0d errors=%0d lat_min=%0d lat_max=%0d lat_expect=%0d cycles=%0d stall_cycles=%0d",
                     K, VW, IW, ORDER, segs_in, elems, outputs, errors, lat_min, lat_max, LAT, cyc, stall);
            if (errors == 0 && seg_out == segs_in && (outputs == 0 || (lat_min == LAT && lat_max == LAT)))
                $display("PASS");
            else
                $display("FAIL seg_out=%0d", seg_out);
            $finish;
        end
        if (cyc > maxcyc) begin $display("TIMEOUT segs_in=%0d seg_out=%0d left=%0d exp_done=%0d drv_done=%0d busy=%0d", segs_in, seg_out, left, exp_done, drv_done, busy); $finish; end
    end
endmodule
