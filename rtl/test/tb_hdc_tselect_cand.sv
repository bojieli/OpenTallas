`timescale 1ns/1ps
// Streaming check of rtl/hdc/v41/ot_hdc_tselect_cand.sv (with a behavioural
// line memory) against vectors from the golden's Model.candidate_blocks
// (tools/rtl_hdc_v41_cand_campaign.py).
//
// +IN=<file>   one beat per line: "<last> <pin> <k> <base hex> <lv hex>" then P "<value hex>"
// +EXP=<file>  per segment "S <count> <lines>" (lines = tselect lines the segment packs
//              into), then <count> lines "<block hex> <value hex> <ninf>" in block order
// +LATLOG=1    print "SEGLAT <seg> <input beats> <latency>" for every segment
// +OUT=<file>  optional: every emitted segment, same format as +EXP (beats = 0)
// +BUBBLE=<p>  percent of cycles the driver withholds a beat
// +GAP=<p>     percent of segments followed by an idle gap of up to 64 cycles
// +SEED=<n>    driver PRNG seed
//
// Each output beat must be packed (lanes 0..c-1 valid), every beat but a
// segment's last must be full, out_last must close each segment, and the
// latency from the last beat's accept to the out_last beat is recorded as
// (latency - 2 x lines), whose range the campaign checks.
module tb_hdc_tselect_cand
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer P  = 64;
    parameter integer W  = 64;
    parameter integer VW = 16;
    parameter integer IW = 17;
    parameter integer K  = 2048;
    parameter integer AW = 11;
    localparam integer KW = $clog2(K + 1);
    localparam integer EW = 1 + VW + IW;
    localparam integer MAXSEG = 1 << 18;

    reg              rst_n = 1'b0;
    reg              in_valid = 1'b0, in_last = 1'b0, in_pin = 1'b0;
    reg  [P-1:0]     in_lv = 0;
    reg  [P*VW-1:0]  in_val = 0;
    reg  [IW-1:0]    in_base = 0;
    reg  [KW-1:0]    in_k = 0;
    wire             in_ready, out_valid, out_last, busy, mem_we, mem_re;
    wire [W-1:0]     out_lv, out_ninf;
    wire [W*VW-1:0]  out_val;
    wire [W*IW-1:0]  out_idx;
    wire [AW-1:0]    mem_waddr, mem_raddr;
    wire [W*EW-1:0]  mem_wdata;
    reg  [W*EW-1:0]  mem_rdata;
    reg  [W*EW-1:0]  mem [0:(1 << AW) - 1];
    always @(posedge clk) begin
        if (mem_we) mem[mem_waddr] <= mem_wdata;
        if (mem_re) mem_rdata <= mem[mem_raddr];
    end

    ot_hdc_tselect_cand #(.P(P), .WB(W), .IW(IW), .K(K), .AW(AW)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_last(in_last),
        .in_pin(in_pin), .in_lv(in_lv), .in_val(in_val), .in_base(in_base), .in_k(in_k),
        .out_valid(out_valid), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re),
        .mem_raddr(mem_raddr), .mem_rdata(mem_rdata), .busy(busy));

    integer fin, fexp, fout, rc, i;
    integer bubble = 0, gap = 0, maxcyc = 400000000, latlog = 0;
    reg [31:0] rng = 32'h2545F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg [8*512-1:0] fname;
    integer cyc = 0;
    integer segs_in = 0, beats = 0, elems = 0, seg_beats = 0, idle_left = 0;
    reg     have = 1'b0, drv_done = 1'b0;
    reg [31:0] f_last, f_pin, f_k, f_base, t0;
    reg [P-1:0] f_lv;
    reg [P*VW-1:0] f_val;
    integer acc_cyc [0:MAXSEG-1];
    integer seg_nb  [0:MAXSEG-1];

    integer seg_out = 0, outputs = 0, errors = 0, exp_done = 0, left = 0, beats_out = 0;
    integer lat_min = 1 << 30, lat_max = -1, last_out_cyc = 0, ob;
    reg [31:0] e_cnt, e_nb, e_idx, e_val, e_ninf;

    task automatic fetch;
        begin
            rc = $fscanf(fin, "%d %d %d %h %h", f_last, f_pin, f_k, f_base, f_lv);
            if (rc != 5) have = 1'b0;
            else begin
                have = 1'b1;
                for (i = 0; i < P; i = i + 1) begin
                    rc = $fscanf(fin, " %h", t0);
                    f_val[VW*i +: VW] = t0[VW-1:0];
                end
            end
        end
    endtask

    task automatic next_segment;
        begin
            rc = $fscanf(fexp, "S %d %d\n", e_cnt, e_nb);
            if (rc != 2) exp_done = 1;
            else left = e_cnt;
        end
    endtask

    initial begin
        if (!$value$plusargs("IN=%s", fname)) begin $display("need +IN"); $finish; end
        fin = $fopen(fname, "r");
        if (!$value$plusargs("EXP=%s", fname)) begin $display("need +EXP"); $finish; end
        fexp = $fopen(fname, "r");
        fout = 0;
        if ($value$plusargs("OUT=%s", fname)) fout = $fopen(fname, "w");
        if (fin == 0 || fexp == 0) begin $display("cannot open vectors"); $finish; end
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("GAP=%d", gap)) gap = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 400000000;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        if (!$value$plusargs("LATLOG=%d", latlog)) latlog = 0;
        fetch;
        next_segment;
    end

    // -- driver ------------------------------------------------------------------------
    reg show;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n) begin
            if (in_valid && in_ready) begin
                beats = beats + 1;
                seg_beats = seg_beats + 1;
                for (i = 0; i < P; i = i + 1) elems = elems + in_lv[i];
                if (in_last) begin
                    acc_cyc[segs_in] = cyc;
                    seg_nb[segs_in] = seg_beats;
                    seg_beats = 0;
                    segs_in = segs_in + 1;
                    rng = xs(rng);
                    if ((rng % 100) < gap) begin rng = xs(rng); idle_left = rng % 65; end
                end
                fetch;
            end
            rng = xs(rng);
            show = have && idle_left == 0 && (rng % 100) >= bubble;
            if (idle_left > 0) idle_left = idle_left - 1;
            in_valid <= show;
            in_lv    <= f_lv;
            in_val   <= f_val;
            in_base  <= f_base[IW-1:0];
            in_pin   <= (f_pin != 0);
            in_last  <= (f_last != 0);
            in_k     <= f_k[KW-1:0];
            if (!have) drv_done <= 1'b1;
        end
    end

    // -- checker -----------------------------------------------------------------------
    reg packed_ok;
    integer c;
    always @(posedge clk) begin
        if (rst_n && out_valid) begin
            beats_out = beats_out + 1;
            last_out_cyc = cyc;
            c = 0; packed_ok = 1'b1;
            for (i = 0; i < W; i = i + 1) begin
                if (out_lv[i]) begin
                    if (c != i) packed_ok = 1'b0;
                    c = c + 1;
                end
            end
            if (!packed_ok || (!out_last && c != W)) begin
                if (errors < 20) $display("UNPACKED beat seg=%0d lv=%h last=%b", seg_out, out_lv, out_last);
                errors = errors + 1;
            end
            if (fout != 0 && c > 0)
                for (i = 0; i < c; i = i + 1)
                    $fwrite(fout, "%h %h %0d\n", out_idx[IW*i +: IW], out_val[VW*i +: VW], out_ninf[i]);
            for (i = 0; i < c; i = i + 1) begin
                outputs = outputs + 1;
                if (exp_done || left == 0) begin
                    if (errors < 20) $display("EXTRA output idx=%h seg=%0d", out_idx[IW*i +: IW], seg_out);
                    errors = errors + 1;
                end else begin
                    rc = $fscanf(fexp, "%h %h %d\n", e_idx, e_val, e_ninf);
                    left = left - 1;
                    if (out_idx[IW*i +: IW] !== e_idx[IW-1:0] || out_val[VW*i +: VW] !== e_val[VW-1:0] ||
                        out_ninf[i] !== e_ninf[0]) begin
                        if (errors < 20)
                            $display("MISMATCH seg=%0d lane=%0d got idx=%h val=%h ninf=%b expect idx=%h val=%h ninf=%0d",
                                     seg_out, i, out_idx[IW*i +: IW], out_val[VW*i +: VW], out_ninf[i],
                                     e_idx, e_val, e_ninf);
                        errors = errors + 1;
                    end
                end
            end
            if (out_last) begin
                if (left != 0 || exp_done) begin
                    if (errors < 20) $display("SHORT seg=%0d missing=%0d", seg_out, left);
                    errors = errors + 1;
                    while (left > 0) begin rc = $fscanf(fexp, "%h %h %d\n", e_idx, e_val, e_ninf); left = left - 1; end
                end
                if (fout != 0) $fwrite(fout, "E\n");
                if (latlog != 0) $display("SEGLAT %0d %0d %0d", seg_out, seg_nb[seg_out], cyc - 1 - acc_cyc[seg_out]);
                ob = cyc - 1 - acc_cyc[seg_out] - 2 * e_nb;
                if (ob < lat_min) lat_min = ob;
                if (ob > lat_max) lat_max = ob;
                seg_out = seg_out + 1;
                if (!exp_done) next_segment;
            end
        end
        if (drv_done && !busy && cyc > last_out_cyc + 64 && cyc > 64) begin
            $display("TSELCAND P=%0d W=%0d VW=%0d IW=%0d K=%0d segments=%0d beats=%0d elements=%0d outputs=%0d out_beats=%0d errors=%0d lat0_min=%0d lat0_max=%0d cycles=%0d",
                     P, W, VW, IW, K, segs_in, beats, elems, outputs, beats_out, errors, lat_min, lat_max, cyc);
            if (errors == 0 && seg_out == segs_in && exp_done) $display("PASS");
            else $display("FAIL seg_out=%0d exp_done=%0d", seg_out, exp_done);
            if (fout != 0) $fclose(fout);
            $finish;
        end
        if (cyc > maxcyc) begin $display("TIMEOUT segs_in=%0d seg_out=%0d", segs_in, seg_out); $finish; end
    end
endmodule
