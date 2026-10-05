`timescale 1ns/1ps
// Bench of ot_hdc_v41x_idx_hsum (the post-pool head-sum stage) against the
// golden: per key the IH per-head FP32 scores sc32 = dots_q4 (as the pooled
// block-dot engine delivers them) and the expected BF16 index score.
//   hs_w.mem  per token, IH lines: {q scale bytes[31:0], BF16 head weight}
//   hs_n.mem  per token, its key count
//   hs_k.mem  per key {ref, keep, faults[IH], scores[IH*32]}
//   hs_e.mem  per key {fault, score[15:0]}
// Keys stream back to back, NKT per cycle; +BUBBLE (1/16ths) inserts gaps.
module tb_hdc_v41x_idx_hsum #(
    parameter integer IH = 32,
    parameter integer NKT = 1,
    parameter integer MAXT = 4096,
    parameter integer MAXK = 1 << 18
) (input wire clk);
    localparam integer KW = 2 + IH + IH * 32;
    reg [47:0]   wm [0:MAXT*IH-1];
    reg [31:0]   nm [0:MAXT-1];
    reg [KW-1:0] km [0:MAXK-1];
    reg [16:0]   em [0:MAXK-1];
    integer ntok = 0, nkey = 0, bubble = 0;
    reg [31:0] seed = 32'h7777abcd;
    initial begin
        if (!$value$plusargs("NTOK=%d", ntok)) ntok = 0;
        if (!$value$plusargs("NKEY=%d", nkey)) nkey = 0;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        $readmemh("hs_w.mem", wm, 0, ntok * IH - 1);
        $readmemh("hs_n.mem", nm, 0, ntok - 1);
        $readmemh("hs_k.mem", km, 0, nkey - 1);
        $readmemh("hs_e.mem", em, 0, nkey - 1);
    end
    reg rst_n = 1'b0;
    reg w_v = 1'b0;
    reg [7:0] w_head = 0;
    reg [15:0] w_w = 0;
    reg [31:0] w_qsc = 0;
    reg [NKT-1:0] i_ref = 0;
    wire [47:0] cnt_ref;
    reg i_v = 1'b0;
    reg [NKT-1:0] i_kv = 0, i_keep = 0;
    reg [NKT*IH*32-1:0] i_score = 0;
    reg [NKT*IH-1:0] i_fault = 0;
    wire o_v;
    wire [NKT-1:0] o_kv, o_fault;
    wire [NKT*16-1:0] o_score;
    ot_hdc_v41x_idx_hsum #(.IH(IH), .NKT(NKT)) dut (.clk(clk), .rst_n(rst_n), .w_v(w_v), .w_head(w_head),
        .w_w(w_w), .w_qsc(w_qsc), .i_ref(i_ref), .cnt_refused(cnt_ref), .i_v(i_v), .i_kv(i_kv), .i_keep(i_keep), .i_score(i_score), .i_fault(i_fault), .o_v(o_v),
        .o_kv(o_kv), .o_score(o_score), .o_fault(o_fault));
    integer cyc = 0, st = 0, tok = 0, h = 0, kn = 0, kend = 0, kout = 0, errors = 0, faults = 0, j, nf, wait_c = 0;
    integer t_in = -1, lat = -1, beats = 0, span0 = -1, span1 = 0, span = 0;
    reg [16:0] e;
    reg [KW-1:0] kk;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        if (o_v) begin
            if (lat < 0 && t_in >= 0) lat = cyc - t_in;
            for (j = 0; j < NKT; j = j + 1)
                if (o_kv[j]) begin
                    e = em[kout];
                    if (e[16] ? !o_fault[j] : (o_fault[j] || o_score[16*j +: 16] != e[15:0])) begin
                        errors = errors + 1;
                        if (errors <= 10) $display("MISMATCH key %0d got %h f%0d exp %h", kout, o_score[16*j +: 16],
                                                   o_fault[j], e);
                    end else if (e[16]) faults = faults + 1;
                    kout = kout + 1;
                end
        end
        w_v <= 1'b0;
        i_v <= 1'b0;
        if (rst_n) case (st)
            0: if (tok >= ntok) st = 9;
               else begin
                   w_v <= 1'b1; w_head <= h[7:0]; {w_qsc, w_w} <= wm[tok * IH + h];
                   if (h == IH - 1) begin h = 0; st = 1; wait_c = 0; kend = kn + nm[tok]; span0 = -1; end
                   else h = h + 1;
               end
            1: begin                                   // weights settle
                   wait_c = wait_c + 1;
                   if (wait_c >= 3) st = 2;
               end
            2: if (kn >= kend) st = 3;
               else begin
                   seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5);
                   if (!(bubble > 0 && seed[7:4] < bubble)) begin
                       nf = (kend - kn >= NKT) ? NKT : kend - kn;
                       i_v <= 1'b1;
                       for (j = 0; j < NKT; j = j + 1) begin
                           kk = km[kn + j];
                           i_kv[j] <= (j < nf);
                           i_keep[j] <= (j < nf) && kk[KW-2];
                           i_ref[j] <= (j < nf) && kk[KW-1];
                           i_fault[IH*j +: IH] <= kk[IH*32 +: IH];
                           i_score[IH*32*j +: IH*32] <= kk[IH*32-1:0];
                       end
                       if (t_in < 0) t_in = cyc + 1;
                       if (span0 < 0) span0 = cyc;
                       span1 = cyc;
                       beats = beats + 1;
                       kn = kn + nf;
                   end
               end
            3: if (kout >= kend) begin span = span + span1 - span0 + 1; tok = tok + 1; st = 0; end
            default: begin
                $display("V41XHSUMCNT refused=%0d", cnt_ref);
                $display("V41XHSUM keys=%0d checked=%0d errors=%0d faults_expected_and_raised=%0d beats=%0d span=%0d latency=%0d cycles=%0d",
                         nkey, kout, errors, faults, beats, span, lat, cyc);
                $finish;
            end
        endcase
        if (cyc > 50000000) begin $display("V41XHSUM TIMEOUT"); $finish; end
    end
endmodule
