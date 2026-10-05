`timescale 1ns/1ps
// Check of rtl/hdc/v41x/ot_dsrom_su_bias_select.sv (bias add + ot_hdc_select_tree) against vectors from the
// golden's add(scores, bias) + topk_lowest_index (tools/dsrom_su_routeract.py); a copy of
// rtl/test/tb_hdc_select_tree.sv with a bias per lane and the adder's LA cycles.
//
// +IN=<file>   per beat a line "B <last>", then W lines "<score hex> <index hex> <lane valid> <bias hex>"
// +EXP=<file>  per segment "S <count>", then <count> lines "<index hex> <ninf>" in the
//              order the unit must return them (slot 0 first)
// +BUBBLE=<p>  percent of cycles the driver withholds a beat
// +SEED=<n>    driver PRNG seed
//
// Every result slot is compared; slots >= count must be empty; each result must
// arrive exactly LAT edges after its segment's last beat was accepted.  Reports
// first-accept -> result edges of the first segment (span0) for the cycle record.
module tb_dsrom_su_bias_select
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
    parameter integer IW = 9;
    parameter integer W = 64;
    parameter integer NB = 8;
    parameter integer ORDER = 1;
    parameter integer LA = 4;
    localparam integer LAT = LA + 1 + 6 + 4 * $clog2(W / 8) + 1 + 4 * $clog2(NB) + (ORDER != 0 ? 6 : 0);
    localparam integer MAXSEG = 1 << 16;

    reg              rst_n = 1'b0;
    reg              in_valid = 1'b0, in_last = 1'b0;
    reg [W-1:0]      in_lv = 0;
    reg [W*32-1:0]   in_val = 0, in_bias = 0;
    wire             out_fault;
    reg [W*IW-1:0]   in_idx = 0;
    wire             out_valid;
    wire [K-1:0]     out_v, out_ninf;
    wire [K*IW-1:0]  out_idx;
    ot_dsrom_su_bias_select #(.K(K), .VW(VW), .IW(IW), .W(W), .NB(NB), .ORDER(ORDER), .LA(LA)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_last(in_last), .in_lv(in_lv),
        .in_val(in_val), .in_bias(in_bias), .in_idx(in_idx), .out_valid(out_valid), .out_v(out_v),
        .out_idx(out_idx), .out_ninf(out_ninf), .out_fault(out_fault));

    integer fin, fexp, rc, l;
    integer bubble = 0;
    reg [31:0] rng = 32'h2545F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg [8*512-1:0] fname;
    integer cyc = 0;
    integer segs_in = 0, beats = 0, first_acc = -1;
    reg     have = 1'b0, drv_done = 1'b0, seg_open = 1'b0;
    reg [31:0] f_last, f_val, f_idx, f_lv, f_bias;
    reg [W*32-1:0] b_val, b_bias;
    reg [W*IW-1:0] b_idx;
    reg [W-1:0]    b_lv;
    reg            b_last;
    integer acc_cyc [0:MAXSEG-1];
    integer seg_first [0:MAXSEG-1];

    integer seg_out = 0, errors = 0, lat_min = 1 << 30, lat_max = -1, last_out_cyc = 0, span0 = -1;
    reg [31:0] e_idx, e_ninf, e_cnt;

    task automatic fetch;
        begin
            rc = $fscanf(fin, "B %d\n", f_last);
            if (rc != 1) have = 1'b0;
            else begin
                have = 1'b1;
                b_last = (f_last != 0);
                for (l = 0; l < W; l = l + 1) begin
                    rc = $fscanf(fin, "%h %h %d %h\n", f_val, f_idx, f_lv, f_bias);
                    b_val[32*l +: 32] = f_val;
                    b_bias[32*l +: 32] = f_bias;
                    b_idx[IW*l +: IW] = f_idx[IW-1:0];
                    b_lv[l] = (f_lv != 0);
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
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        fetch;
    end

    // -- driver: in_valid is accepted on every edge (no backpressure) -------------------
    reg show;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n) begin
            if (in_valid) begin
                beats = beats + 1;
                if (!seg_open) begin seg_first[segs_in] = cyc; seg_open = 1'b1; end
                if (in_last) begin
                    acc_cyc[segs_in] = cyc;
                    segs_in = segs_in + 1;
                    seg_open = 1'b0;
                end
                fetch;
            end
            rng = xs(rng);
            show = have && (rng % 100) >= bubble;
            in_valid <= show;
            in_last  <= b_last;
            in_lv    <= b_lv;
            in_val   <= b_val;
            in_bias  <= b_bias;
            in_idx   <= b_idx;
            if (!have) drv_done <= 1'b1;
        end
    end

    // -- checker -----------------------------------------------------------------------
    integer s;
    always @(posedge clk) begin
        if (rst_n && out_valid) begin
            last_out_cyc = cyc;
            rc = $fscanf(fexp, "S %d\n", e_cnt);
            if (rc != 1) begin
                if (errors < 20) $display("EXTRA result at cycle %0d", cyc);
                errors = errors + 1;
            end else begin
                if (cyc - 1 - acc_cyc[seg_out] < lat_min) lat_min = cyc - 1 - acc_cyc[seg_out];
                if (cyc - 1 - acc_cyc[seg_out] > lat_max) lat_max = cyc - 1 - acc_cyc[seg_out];
                if (seg_out == 0) span0 = cyc - seg_first[0];
                for (s = 0; s < K; s = s + 1) begin
                    if (s < e_cnt) begin
                        rc = $fscanf(fexp, "%h %d\n", e_idx, e_ninf);
                        if (!out_v[s] || out_idx[IW*s +: IW] !== e_idx[IW-1:0] || out_ninf[s] !== e_ninf[0]) begin
                            if (errors < 20)
                                $display("MISMATCH seg=%0d slot=%0d got v=%b idx=%h ninf=%b expect idx=%h ninf=%0d",
                                         seg_out, s, out_v[s], out_idx[IW*s +: IW], out_ninf[s], e_idx, e_ninf);
                            errors = errors + 1;
                        end
                    end else if (out_v[s]) begin
                        if (errors < 20) $display("MISMATCH seg=%0d slot=%0d valid, expected empty", seg_out, s);
                        errors = errors + 1;
                    end
                end
            end
            seg_out = seg_out + 1;
        end
        if (drv_done && cyc > last_out_cyc + LAT + 16 && cyc > 64) begin
            $display("BIASSEL fault=%0d", out_fault);
            $display("SELTREE K=%0d VW=%0d IW=%0d W=%0d NB=%0d ORDER=%0d segments=%0d beats=%0d results=%0d errors=%0d lat_min=%0d lat_max=%0d lat_expect=%0d span0=%0d cycles=%0d",
                     K, VW, IW, W, NB, ORDER, segs_in, beats, seg_out, errors, lat_min, lat_max, LAT, span0, cyc);
            if (errors == 0 && !out_fault && seg_out == segs_in && segs_in > 0 && lat_min == LAT && lat_max == LAT)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (cyc > 50000000) begin $display("TIMEOUT"); $finish; end
    end
endmodule
