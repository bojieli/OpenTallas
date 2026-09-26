`timescale 1ns/1ps
// Streaming check of rtl/hdc/v41/ot_hdc_tselect_q.sv (Q quarters, one behavioural
// line memory per quarter) against vectors from the golden's topk_lowest_index
// (tools/rtl_hdc_v41_tselect_campaign.py).
//
// +PFX=<path>   quarter q's stimulus is <path>.in<q>, its expected output <path>.exp<q>;
//               with +OUT=1 its emitted output goes to <path>.out<q>
//   .in<q>      one beat per line: "<last> <k> <lv hex>" then W "<value hex> <index hex>"
//   .exp<q>     per segment "S <count> <beats>", then <count> lines "<index hex> <value hex> <ninf>"
// +BUBBLE, +GAP, +SEED as tb_hdc_tselect.
//
// Every quarter's output must be packed, full except its last beat, closed by
// out_last, and equal to its expected list; the latency of each segment is
// (last quarter's out_last) - (last quarter's final accept) - 2 x (longest
// quarter's beats), whose range the campaign checks.
module tb_hdc_tselect_q
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer Q  = 4;
    parameter integer W  = 16;
    parameter integer VW = 16;
    parameter integer IW = 16;
    parameter integer K  = 512;
    parameter integer AW = 10;
    localparam integer KW = $clog2(K + 1);
    localparam integer EW = 1 + VW + IW;
    localparam integer MAXSEG = 1 << 16;

    reg                rst_n = 1'b0;
    reg  [Q-1:0]       in_valid = 0, in_last = 0;
    reg  [Q*W-1:0]     in_lv = 0;
    reg  [Q*W*VW-1:0]  in_val = 0;
    reg  [Q*W*IW-1:0]  in_idx = 0;
    reg  [KW-1:0]      in_k = 0;
    wire [Q-1:0]       in_ready, out_valid, out_last, mem_we, mem_re;
    wire               busy;
    wire [Q*W-1:0]     out_lv, out_ninf;
    wire [Q*W*VW-1:0]  out_val;
    wire [Q*W*IW-1:0]  out_idx;
    wire [Q*AW-1:0]    mem_waddr, mem_raddr;
    wire [Q*W*EW-1:0]  mem_wdata;
    reg  [Q*W*EW-1:0]  mem_rdata;
    reg  [W*EW-1:0]    mem [0:Q*(1 << AW) - 1];
    integer mq;
    always @(posedge clk) begin
        for (mq = 0; mq < Q; mq = mq + 1) begin
            if (mem_we[mq]) mem[mq * (1 << AW) + mem_waddr[AW*mq +: AW]] <= mem_wdata[W*EW*mq +: W*EW];
            if (mem_re[mq]) mem_rdata[W*EW*mq +: W*EW] <= mem[mq * (1 << AW) + mem_raddr[AW*mq +: AW]];
        end
    end

    ot_hdc_tselect_q #(.Q(Q), .W(W), .VW(VW), .IW(IW), .K(K), .AW(AW)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_last(in_last),
        .in_lv(in_lv), .in_val(in_val), .in_idx(in_idx), .in_k(in_k),
        .out_valid(out_valid), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re),
        .mem_raddr(mem_raddr), .mem_rdata(mem_rdata), .busy(busy));

    integer fin [0:Q-1];
    integer fexp [0:Q-1];
    integer fout [0:Q-1];
    integer rc, i, q, fd;
    integer bubble = 0, gap = 0, maxcyc = 400000000, dump = 0;
    reg [31:0] rng = 32'h2545F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg [8*512-1:0] pfx, fname;
    integer cyc = 0;
    integer beats = 0, elems = 0, idle_left = 0, errors = 0, outputs = 0, beats_out = 0;
    reg [Q-1:0]    have, show;
    reg [31:0]     f_last [0:Q-1];
    reg [31:0]     f_k [0:Q-1];
    reg [W-1:0]    f_lv [0:Q-1];
    reg [W*VW-1:0] f_val [0:Q-1];
    reg [W*IW-1:0] f_idx [0:Q-1];
    reg [31:0] t0, t1;
    integer segq [0:Q-1];          // segments delivered by quarter q
    integer nbq  [0:Q-1];          // beats of the current segment of quarter q
    integer lastacc [0:MAXSEG-1];
    integer nbmax [0:MAXSEG-1];
    integer olast [0:MAXSEG-1];
    integer soq  [0:Q-1];          // segment quarter q is emitting
    integer left [0:Q-1];
    integer qdone [0:Q-1];
    reg [31:0] e_cnt, e_nb, e_idx, e_val, e_ninf;
    integer segs_done = 0, nsegs_total = 0;

    task automatic fetch(input integer qi);
        begin
            fd = fin[qi];
            rc = $fscanf(fd, "%d %d %h", f_last[qi], f_k[qi], f_lv[qi]);
            if (rc != 3) have[qi] = 1'b0;
            else begin
                have[qi] = 1'b1;
                for (i = 0; i < W; i = i + 1) begin
                    rc = $fscanf(fd, " %h %h", t0, t1);
                    f_val[qi][VW*i +: VW] = t0[VW-1:0];
                    f_idx[qi][IW*i +: IW] = t1[IW-1:0];
                end
            end
        end
    endtask

    task automatic next_segment(input integer qi);
        begin
            fd = fexp[qi];
            rc = $fscanf(fd, "S %d %d\n", e_cnt, e_nb);
            if (rc != 2) qdone[qi] = 1;
            else left[qi] = e_cnt;
        end
    endtask

    initial begin
        if (!$value$plusargs("PFX=%s", pfx)) begin $display("need +PFX"); $finish; end
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("GAP=%d", gap)) gap = 0;
        if (!$value$plusargs("OUT=%d", dump)) dump = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 400000000;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        for (q = 0; q < Q; q = q + 1) begin
            $sformat(fname, "%0s.in%0d", pfx, q);
            fd = $fopen(fname, "r"); fin[q] = fd;
            $sformat(fname, "%0s.exp%0d", pfx, q);
            fd = $fopen(fname, "r"); fexp[q] = fd;
            fout[q] = 0;
            if (dump != 0) begin $sformat(fname, "%0s.out%0d", pfx, q); fd = $fopen(fname, "w"); fout[q] = fd; end
            if (fin[q] == 0 || fexp[q] == 0) begin $display("cannot open vectors for quarter %0d", q); $finish; end
            segq[q] = 0; nbq[q] = 0; soq[q] = 0; left[q] = 0; qdone[q] = 0;
            fetch(q);
            next_segment(q);
        end
        for (i = 0; i < MAXSEG; i = i + 1) begin lastacc[i] = 0; nbmax[i] = 0; olast[i] = 0; end
    end

    // -- driver ----------------------------------------------------------------------------
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (rst_n) begin
            for (q = 0; q < Q; q = q + 1) begin
                if (in_valid[q] && in_ready[q]) begin
                    beats = beats + 1;
                    nbq[q] = nbq[q] + 1;
                    for (i = 0; i < W; i = i + 1) elems = elems + in_lv[W*q + i];
                    if (in_last[q]) begin
                        if (cyc > lastacc[segq[q]]) lastacc[segq[q]] = cyc;
                        if (nbq[q] > nbmax[segq[q]]) nbmax[segq[q]] = nbq[q];
                        nbq[q] = 0;
                        segq[q] = segq[q] + 1;
                        if (q == 0) begin
                            rng = xs(rng);
                            if ((rng % 100) < gap) begin rng = xs(rng); idle_left = rng % 65; end
                        end
                    end
                    fetch(q);
                end
                rng = xs(rng);
                show[q] = have[q] && idle_left == 0 && (rng % 100) >= bubble;
            end
            if (idle_left > 0) idle_left = idle_left - 1;
            for (q = 0; q < Q; q = q + 1) begin
                in_valid[q]            <= show[q];
                in_lv[W*q +: W]        <= f_lv[q];
                in_val[W*VW*q +: W*VW] <= f_val[q];
                in_idx[W*IW*q +: W*IW] <= f_idx[q];
                in_last[q]             <= (f_last[q] != 0);
                if (q == 0) in_k <= f_k[0][KW-1:0];
            end
        end
    end

    // -- checker ---------------------------------------------------------------------------
    reg packed_ok;
    integer c, last_out_cyc = 0, lat_min = 1 << 30, lat_max = -1, ob, s;
    always @(posedge clk) begin
        if (rst_n) begin
            for (q = 0; q < Q; q = q + 1) begin
                if (out_valid[q]) begin
                    beats_out = beats_out + 1;
                    last_out_cyc = cyc;
                    c = 0; packed_ok = 1'b1;
                    for (i = 0; i < W; i = i + 1)
                        if (out_lv[W*q + i]) begin if (c != i) packed_ok = 1'b0; c = c + 1; end
                    if (!packed_ok || (!out_last[q] && c != W)) begin
                        if (errors < 20) $display("UNPACKED q=%0d seg=%0d lv=%h", q, soq[q], out_lv[W*q +: W]);
                        errors = errors + 1;
                    end
                    for (i = 0; i < c; i = i + 1) begin
                        outputs = outputs + 1;
                        if (fout[q] != 0)
                            begin fd = fout[q]; $fwrite(fd, "%h %h %0d\n", out_idx[W*IW*q + IW*i +: IW], out_val[W*VW*q + VW*i +: VW],
                                    out_ninf[W*q + i]); end
                        if (qdone[q] || left[q] == 0) begin
                            if (errors < 20) $display("EXTRA q=%0d seg=%0d idx=%h", q, soq[q], out_idx[W*IW*q + IW*i +: IW]);
                            errors = errors + 1;
                        end else begin
                            fd = fexp[q];
                            rc = $fscanf(fd, "%h %h %d\n", e_idx, e_val, e_ninf);
                            left[q] = left[q] - 1;
                            if (out_idx[W*IW*q + IW*i +: IW] !== e_idx[IW-1:0] ||
                                out_val[W*VW*q + VW*i +: VW] !== e_val[VW-1:0] || out_ninf[W*q + i] !== e_ninf[0]) begin
                                if (errors < 20)
                                    $display("MISMATCH q=%0d seg=%0d lane=%0d got idx=%h val=%h expect idx=%h val=%h",
                                             q, soq[q], i, out_idx[W*IW*q + IW*i +: IW], out_val[W*VW*q + VW*i +: VW],
                                             e_idx, e_val);
                                errors = errors + 1;
                            end
                        end
                    end
                    if (out_last[q]) begin
                        if (left[q] != 0 || qdone[q]) begin
                            if (errors < 20) $display("SHORT q=%0d seg=%0d missing=%0d", q, soq[q], left[q]);
                            errors = errors + 1;
                            while (left[q] > 0) begin
                                fd = fexp[q]; rc = $fscanf(fd, "%h %h %d\n", e_idx, e_val, e_ninf); left[q] = left[q] - 1;
                            end
                        end
                        if (fout[q] != 0) begin fd = fout[q]; $fwrite(fd, "E\n"); end
                        if (cyc > olast[soq[q]]) olast[soq[q]] = cyc;
                        soq[q] = soq[q] + 1;
                        if (!qdone[q]) next_segment(q);
                    end
                end
            end
        end
        if (rst_n && have == 0 && !busy && cyc > last_out_cyc + 64 && cyc > 64) begin
            for (s = 0; s < segq[0]; s = s + 1) begin
                ob = olast[s] - 1 - lastacc[s] - 2 * nbmax[s];
                if (ob < lat_min) lat_min = ob;
                if (ob > lat_max) lat_max = ob;
            end
            c = 1;
            for (q = 0; q < Q; q = q + 1) if (soq[q] != segq[q] || !qdone[q]) c = 0;
            $display("TSELECTQ Q=%0d W=%0d VW=%0d IW=%0d K=%0d segments=%0d beats=%0d elements=%0d outputs=%0d out_beats=%0d errors=%0d lat0_min=%0d lat0_max=%0d cycles=%0d",
                     Q, W, VW, IW, K, segq[0], beats, elems, outputs, beats_out, errors, lat_min, lat_max, cyc);
            if (errors == 0 && c) $display("PASS");
            else $display("FAIL");
            for (q = 0; q < Q; q = q + 1) if (fout[q] != 0) begin fd = fout[q]; $fclose(fd); end
            $finish;
        end
        if (cyc > maxcyc) begin $display("TIMEOUT"); $finish; end
    end
endmodule
