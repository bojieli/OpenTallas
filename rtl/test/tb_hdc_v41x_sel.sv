`timescale 1ns/1ps
// Performance + exactness bench of rtl/hdc/v41x/ot_hdc_v41x_sel.sv (Q quarters, one
// behavioural 1R1W line memory per quarter) against vectors from the golden's
// topk_lowest_index (tools/rtl_hdc_v41x_sel_campaign.py).
//
// +PFX=<path>   quarter q's stimulus <path>.in<q>, expected output <path>.exp<q>
//   .in<q>      one beat per line: "<last> <k> <lv hex>" then W "<value hex> <index hex>"
//               (a segment of quarter q ends with its last=1 beat)
//   .exp<q>     per segment "S <count> <beats>", then <count> lines "<index hex> <value hex> <ninf>"
// +BUBBLE=<pct> input valid dropped with this probability (default 0: full rate)
// +ORDY=<pct>   out_ready low with this probability (default 0)
// +SEED, +MAXCYC
//
// Per segment the bench drives every quarter at full rate (all quarters start together),
// replays the whole segment on each rep_req pulse, checks every output beat (packed, in
// order, equal to the expected list, out_last on the last beat) and prints
//   SEG <n> tail=<edges> first=<accept edge> last=<accept edge> ovf=<0/1> stall=<cycles>
//       nhead=<q0,q1,..> n2=<..> n3=<..>
// where tail = (edge that registers the last quarter's out_last beat) - (edge that
// accepted the segment's final in_last), and stall counts cycles in which a quarter had
// a beat ready inside its first-pass ingest window but in_ready was low.  The summary
// line starts with V41XSEL.
module tb_hdc_v41x_sel
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer Q    = 4;
    parameter integer W    = 16;
    parameter integer IW   = 20;
    parameter integer K    = 512;
    parameter integer AW   = 8;
    parameter integer DG   = 4;
    parameter integer OD   = 4;
    parameter integer MAXB = 8192;                 // beats per quarter per segment
    localparam integer KW = $clog2(K + 1);
    localparam integer EW = 17 + IW;

    reg                rst_n = 1'b0;
    reg  [Q-1:0]       in_valid = 0, in_last = 0, out_ready = 0;
    reg  [Q*W-1:0]     in_lv = 0;
    reg  [Q*W*16-1:0]  in_val = 0;
    reg  [Q*W*IW-1:0]  in_idx = 0;
    reg  [KW-1:0]      in_k = 0;
    wire [Q-1:0]       in_ready, out_valid, out_last, mem_we, mem_re;
    wire               rep_req, ovf, busy;
    wire [Q*W-1:0]     out_lv, out_ninf;
    wire [Q*W*16-1:0]  out_val;
    wire [Q*W*IW-1:0]  out_idx;
    wire [Q*AW-1:0]    mem_waddr, mem_raddr;
    wire [Q*W*EW-1:0]  mem_wdata;
    reg  [Q*W*EW-1:0]  mem_rdata;
    wire [Q*3*(AW+1)-1:0] stats;
    reg  [W*EW-1:0]    mem [0:Q*(1 << AW) - 1];
    integer mq;
    always @(posedge clk) begin
        for (mq = 0; mq < Q; mq = mq + 1) begin
            if (mem_we[mq]) mem[mq * (1 << AW) + mem_waddr[AW*mq +: AW]] <= mem_wdata[W*EW*mq +: W*EW];
            if (mem_re[mq]) mem_rdata[W*EW*mq +: W*EW] <= mem[mq * (1 << AW) + mem_raddr[AW*mq +: AW]];
        end
    end

    ot_hdc_v41x_sel #(.Q(Q), .W(W), .IW(IW), .K(K), .AW(AW), .DG(DG), .OD(OD)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .in_last(in_last),
        .in_lv(in_lv), .in_val(in_val), .in_idx(in_idx), .in_k(in_k),
        .out_valid(out_valid), .out_ready(out_ready), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf),
        .mem_we(mem_we), .mem_waddr(mem_waddr), .mem_wdata(mem_wdata), .mem_re(mem_re),
        .mem_raddr(mem_raddr), .mem_rdata(mem_rdata), .rep_req(rep_req), .ovf(ovf), .busy(busy), .stats(stats));

    // -- segment buffers ---------------------------------------------------------------------
    reg [W-1:0]    b_lv  [0:Q*MAXB-1];
    reg [W*16-1:0] b_val [0:Q*MAXB-1];
    reg [W*IW-1:0] b_idx [0:Q*MAXB-1];
    integer        nb [0:Q-1];
    integer        pos [0:Q-1];
    integer        olast_seen [0:Q-1];
    reg [31:0]     seg_k;
    integer fin [0:Q-1];
    integer fexp [0:Q-1];
    integer rc, i, q, fd, j;
    integer bubble = 0, ordy = 0, maxcyc = 2000000000;
    reg [31:0] rng = 32'h2545F491;
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    reg [8*512-1:0] pfx, fname;
    reg [31:0] t0, t1, t2;
    reg [W-1:0] lvtmp;
    reg [W*16-1:0] vtmp;
    reg [W*IW-1:0] itmp;
    integer have_seg;
    integer elems = 0, beats_in = 0, nsegs = 0, errors = 0, outputs = 0, beats_out = 0;

    task automatic load_segment;
        integer qq, bb, last_, done_;
        begin
            have_seg = 1;
            for (qq = 0; qq < Q; qq = qq + 1) begin
                bb = 0; done_ = 0;
                while (!done_) begin
                    rc = $fscanf(fin[qq], "%d %d %h", t0, t1, t2);
                    if (rc != 3) begin have_seg = 0; done_ = 1; end
                    else begin
                        last_ = t0; seg_k = t1; lvtmp = t2[W-1:0];
                        for (j = 0; j < W; j = j + 1) begin
                            rc = $fscanf(fin[qq], " %h %h", t0, t1);
                            vtmp[16*j +: 16] = t0[15:0];
                            itmp[IW*j +: IW] = t1[IW-1:0];
                            if (lvtmp[j]) elems = elems + 1;
                        end
                        if (bb >= MAXB) begin $display("segment longer than MAXB"); $finish; end
                        b_lv[qq*MAXB + bb] = lvtmp; b_val[qq*MAXB + bb] = vtmp; b_idx[qq*MAXB + bb] = itmp;
                        bb = bb + 1;
                        if (last_ != 0) done_ = 1;
                    end
                end
                nb[qq] = bb; beats_in = beats_in + bb;
            end
        end
    endtask

    // expected lists of the current segment
    reg [31:0] e_cnt, e_nb;
    integer    left [0:Q-1];
    integer    qdone [0:Q-1];
    task automatic next_expect(input integer qi);
        begin
            rc = $fscanf(fexp[qi], "S %d %d\n", e_cnt, e_nb);
            if (rc != 2) begin $display("expected file short for quarter %0d", qi); errors = errors + 1; left[qi] = 0; end
            else left[qi] = e_cnt;
        end
    endtask

    initial begin
        if (!$value$plusargs("PFX=%s", pfx)) begin $display("need +PFX"); $finish; end
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("ORDY=%d", ordy)) ordy = 0;
        if (!$value$plusargs("MAXCYC=%d", maxcyc)) maxcyc = 2000000000;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
        for (q = 0; q < Q; q = q + 1) begin
            $sformat(fname, "%0s.in%0d", pfx, q);
            fd = $fopen(fname, "r"); fin[q] = fd;
            $sformat(fname, "%0s.exp%0d", pfx, q);
            fd = $fopen(fname, "r"); fexp[q] = fd;
            if (fin[q] == 0 || fexp[q] == 0) begin $display("cannot open vectors for quarter %0d", q); $finish; end
        end
    end

    // -- driver / checker ----------------------------------------------------------------------------
    integer cyc = 0;
    localparam [2:0] D_LOAD = 3'd0, D_RUN = 3'd1, D_END = 3'd2;
    reg [2:0] dst = D_LOAD;
    integer sending [0:Q-1];
    integer first_pass;
    integer t_first, t_last, t_out, stall, seg_ovf, tail_min, tail_max, ovf_segs, nrep;
    integer stall_tot = 0;
    reg [Q-1:0] qlast;
    reg [W-1:0] olv;
    integer lanes, ok_pref;
    reg [31:0] x_idx, x_val, x_ninf;

    initial begin tail_min = 1 << 30; tail_max = -1; ovf_segs = 0; end

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc > maxcyc) begin $display("TIMEOUT at cycle %0d", cyc); errors = errors + 1; dst = D_END; end
        // output ready for the next edge
        for (q = 0; q < Q; q = q + 1) begin
            rng = xs(rng);
            out_ready[q] <= !(ordy > 0 && (rng % 100) < ordy);
        end
        if (rst_n) begin
            // -- accepted inputs on this edge
            for (q = 0; q < Q; q = q + 1) begin
                if (in_valid[q] && in_ready[q]) begin
                    if (first_pass && pos[q] == 0 && t_first < 0) t_first = cyc;
                    pos[q] = pos[q] + 1;
                    if (in_last[q]) begin
                        sending[q] = 0;
                        if (first_pass) begin qlast[q] = 1'b1; if (cyc > t_last) t_last = cyc; end
                    end
                end else if (in_valid[q] && !in_ready[q] && first_pass && pos[q] > 0 && !qlast[q]) begin
                    stall = stall + 1;
                end
            end
            // -- outputs taken on this edge
            for (q = 0; q < Q; q = q + 1) begin
                if (out_valid[q] && out_ready[q] && dst == D_RUN) begin
                    beats_out = beats_out + 1;
                    olv = out_lv[W*q +: W];
                    lanes = 0; ok_pref = 1;
                    for (j = 0; j < W; j = j + 1) begin
                        if (olv[j]) begin
                            if (lanes != j) ok_pref = 0;
                            lanes = lanes + 1;
                        end
                    end
                    if (!ok_pref) begin errors = errors + 1; $display("E seg %0d q %0d: output lanes not packed", nsegs, q); end
                    if (!out_last[q] && lanes != W) begin errors = errors + 1; $display("E seg %0d q %0d: short non-last beat", nsegs, q); end
                    for (j = 0; j < W; j = j + 1) if (olv[j]) begin
                        outputs = outputs + 1;
                        if (left[q] <= 0) begin
                            errors = errors + 1;
                            if (errors < 20) $display("E seg %0d q %0d: extra output idx %0h", nsegs, q, out_idx[W*IW*q + IW*j +: IW]);
                        end else begin
                            rc = $fscanf(fexp[q], "%h %h %d\n", x_idx, x_val, x_ninf);
                            left[q] = left[q] - 1;
                            if (out_idx[W*IW*q + IW*j +: IW] != x_idx[IW-1:0] || out_val[W*16*q + 16*j +: 16] != x_val[15:0] ||
                                out_ninf[W*q + j] != x_ninf[0]) begin
                                errors = errors + 1;
                                if (errors < 20) $display("E seg %0d q %0d: got %0h/%0h/%0d want %0h/%0h/%0d", nsegs, q,
                                    out_idx[W*IW*q + IW*j +: IW], out_val[W*16*q + 16*j +: 16], out_ninf[W*q + j],
                                    x_idx, x_val, x_ninf);
                            end
                        end
                    end
                    if (out_last[q]) begin
                        if (left[q] != 0) begin
                            errors = errors + 1;
                            if (errors < 20) $display("E seg %0d q %0d: %0d outputs missing", nsegs, q, left[q]);
                            while (left[q] > 0) begin rc = $fscanf(fexp[q], "%h %h %d\n", x_idx, x_val, x_ninf); left[q] = left[q] - 1; end
                        end
                        qdone[q] = 1;
                    end
                end
            end
            // tail: the edge that registered the last quarter's out_last beat is the edge before the
            // first edge at which it is visible
            for (q = 0; q < Q; q = q + 1)
                if (dst == D_RUN && out_valid[q] && out_last[q] && !olast_seen[q]) begin
                    olast_seen[q] = 1;
                    if (cyc - 1 > t_out) t_out = cyc - 1;
                end
            if (dst == D_RUN && rep_req) begin
                nrep = nrep + 1; first_pass = 0;
                for (q = 0; q < Q; q = q + 1) begin pos[q] = 0; sending[q] = 1; end
            end
            if (dst == D_RUN && ovf) seg_ovf = 1;
            // -- segment complete
            if (dst == D_RUN) begin
                j = 1;
                for (q = 0; q < Q; q = q + 1) if (!qdone[q]) j = 0;
                if (j) begin
                    $write("SEG %0d tail=%0d first=%0d last=%0d ovf=%0d rep=%0d stall=%0d k=%0d nhead=", nsegs,
                           t_out - t_last, t_first, t_last, seg_ovf, nrep, stall, seg_k);
                    for (q = 0; q < Q; q = q + 1) $write("%0d%s", stats[3*(AW+1)*q +: AW+1], q + 1 < Q ? "," : "");
                    $write(" n2=");
                    for (q = 0; q < Q; q = q + 1) $write("%0d%s", stats[3*(AW+1)*q + AW+1 +: AW+1], q + 1 < Q ? "," : "");
                    $write(" n3=");
                    for (q = 0; q < Q; q = q + 1) $write("%0d%s", stats[3*(AW+1)*q + 2*(AW+1) +: AW+1], q + 1 < Q ? "," : "");
                    $write("\n");
                    if (t_out - t_last < tail_min) tail_min = t_out - t_last;
                    if (t_out - t_last > tail_max) tail_max = t_out - t_last;
                    if (seg_ovf) ovf_segs = ovf_segs + 1;
                    stall_tot = stall_tot + stall;
                    nsegs = nsegs + 1;
                    dst = D_LOAD;
                end
            end
            if (dst == D_LOAD) begin
                load_segment;
                if (!have_seg) dst = D_END;
                else begin
                    for (q = 0; q < Q; q = q + 1) begin
                        pos[q] = 0; sending[q] = 1; qdone[q] = 0; olast_seen[q] = 0; next_expect(q);
                    end
                    qlast = 0; first_pass = 1; t_first = -1; t_last = -1; t_out = -1; stall = 0; seg_ovf = 0; nrep = 0;
                    dst = D_RUN;
                end
            end
            if (dst == D_END && !busy) begin
                $display("V41XSEL Q=%0d W=%0d IW=%0d K=%0d AW=%0d segments=%0d beats=%0d elements=%0d outputs=%0d out_beats=%0d errors=%0d tail_min=%0d tail_max=%0d ovf_segs=%0d stall=%0d cycles=%0d",
                         Q, W, IW, K, AW, nsegs, beats_in, elems, outputs, beats_out, errors, tail_min, tail_max, ovf_segs,
                         stall_tot, cyc);
                if (errors == 0) $display("PASS"); else $display("FAIL");
                $finish;
            end
            // -- drive the next beat of every quarter
            for (q = 0; q < Q; q = q + 1) begin
                rng = xs(rng);
                if (dst == D_RUN && sending[q] && pos[q] < nb[q] && !(bubble > 0 && (rng % 100) < bubble)) begin
                    in_valid[q] <= 1'b1;
                    in_last[q]  <= (pos[q] == nb[q] - 1);
                    in_lv[W*q +: W] <= b_lv[q*MAXB + pos[q]];
                    in_val[W*16*q +: W*16] <= b_val[q*MAXB + pos[q]];
                    in_idx[W*IW*q +: W*IW] <= b_idx[q*MAXB + pos[q]];
                end else begin
                    in_valid[q] <= 1'b0; in_last[q] <= 1'b0;
                end
            end
            in_k <= seg_k[KW-1:0];
        end
    end
endmodule
