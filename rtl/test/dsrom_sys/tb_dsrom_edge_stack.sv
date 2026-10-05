`timescale 1ns/1ps
// One EDGE INDEX SCORER stack element (ot_dsrom_edge_stack: the qualified
// streaming score slices + the streamed local top-K), keys in, candidate list
// out, against tools/hdc_golden_v41.py (tools/dsrom_edge_scorer_campaign.py score):
//   every key's BF16 score (and fault) is checked at the score array's output,
//   and the stack's candidate list (its exact local top-K, ascending position)
//   at the link.
//
//   st_q.mem  per query IH lines {w[15:0], scales[NB*8], codes[NB*128]}
//   st_n.mem  per query {beats[31:0]}
//   st_k.mem  per beat {kv[LI], keep[LI], key[LI*NB*136]} (stack-local order)
//   st_e.mem  per beat slot {fault, score[15:0]} (the golden's)
//   st_c.mem  per query the candidate count, then per candidate {position[IW], score[15:0]}
// Plusargs: NQ, NBEAT, NSLOT (= NBEAT*LI), NCAND (lines of st_c.mem), STACK,
// RATE (keys/cycle the HBM service offers, credit model; 0 = every cycle).
module tb_dsrom_edge_stack #(
    parameter integer NSL = 4, NK = 4, NB = 4, IH = 32, IW = 20, K = 512,
    parameter integer FPL = 7, FML = 5, QL = 5, MACRO = 0, CONTIGUOUS = 0,
    parameter integer MAXQ = 64, MAXB = 1 << 15, MAXC = 1 << 15
) (input wire clk);
    localparam integer LI = NSL * NK;
    localparam integer KB = NB * 136;
    localparam integer QW = 16 + NB * 8 + NB * 128;
    reg [QW-1:0]        qm [0:MAXQ*IH-1];
    reg [IW:0]          layouts [0:MAXQ-1];
    reg [31:0]          nm [0:MAXQ-1];
    reg [2*LI+LI*KB-1:0] km [0:MAXB-1];
    reg [16:0]          em [0:MAXB*LI-1];
    reg [IW+16-1:0]     cm [0:MAXC-1];
    integer nq = 0, nbeat = 0, nslot = 0, ncand = 0, stack = 0, rate = 11;
    initial begin
        if (!$value$plusargs("NQ=%d", nq)) nq = 0;
        if (!$value$plusargs("NBEAT=%d", nbeat)) nbeat = 0;
        if (!$value$plusargs("NCAND=%d", ncand)) ncand = 0;
        if (!$value$plusargs("STACK=%d", stack)) stack = 0;
        if (!$value$plusargs("RATE=%d", rate)) rate = 11;
        $readmemh("st_q.mem", qm, 0, nq * IH - 1);
        $readmemh("st_n.mem", nm, 0, nq - 1);
        if (CONTIGUOUS) $readmemh("st_layout.mem", layouts, 0, nq - 1);
        $readmemh("st_k.mem", km, 0, nbeat - 1);
        $readmemh("st_e.mem", em, 0, nbeat * LI - 1);
        $readmemh("st_c.mem", cm, 0, ncand - 1);
    end

    reg               rst_n = 1'b0, start = 1'b0;
    reg               ql_v = 1'b0;
    wire              ql_ready;
    reg  [7:0]        ql_head = 0;
    reg  [NB*128-1:0] ql_codes = 0;
    reg  [NB*8-1:0]   ql_sc = 0;
    reg  [15:0]       ql_w = 0;
    reg               k_valid = 1'b0, k_last = 1'b0;
    wire              k_ready;
    reg  [IW-1:0]     k_first = 0;
    reg  [LI-1:0]     k_kv = 0, k_keep = 0;
    reg  [LI*KB-1:0]  k_key = 0;
    wire              c_valid, c_last, fault, busy;
    wire [15:0]       c_lv;
    wire [16*16-1:0]  c_val;
    wire [16*IW-1:0]  c_idx;
    wire [31:0]       st_folds, st_pass, st_stall;
    ot_dsrom_edge_stack #(.NSL(NSL), .NK(NK), .NB(NB), .IH(IH), .IW(IW), .K(K), .FPL(FPL), .FML(FML), .QL(QL),
                          .LO(16), .MACRO(MACRO), .CONTIGUOUS(CONTIGUOUS)) dut (
        .clk(clk), .rst_n(rst_n), .stack_id(stack[1:0]), .start(start), .layout_n(layouts[q]), .layout_installed(1'b1),
        .ql_v(ql_v), .ql_ready(ql_ready), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
        .k_valid(k_valid), .k_ready(k_ready), .k_last(k_last), .k_first(k_first), .k_kv(k_kv),
        .k_keep(k_keep), .k_ref({LI{1'b0}}), .k_key(k_key),
        .c_valid(c_valid), .c_ready(1'b1), .c_last(c_last), .c_lv(c_lv), .c_val(c_val), .c_idx(c_idx),
        .fault(fault), .busy(busy), .st_folds(st_folds), .st_pass(st_pass), .st_stall(st_stall));

    // score monitor at the array output
    wire              s_go = dut.s_valid && dut.s_ready;
    integer           eslot = 0, serr = 0, sfault = 0, schk = 0;
    integer           i;
    always @(posedge clk) if (rst_n && s_go) begin
        for (i = 0; i < LI; i = i + 1) if (dut.s_kv[i]) begin
            if (dut.s_score[16*i +: 16] != em[eslot + i][15:0] || dut.s_fault[i] != em[eslot + i][16]) begin
                if (serr < 8) $display("STSCOREMISMATCH slot=%0d got %h/%0d exp %h/%0d", eslot + i,
                                       dut.s_score[16*i +: 16], dut.s_fault[i], em[eslot + i][15:0], em[eslot + i][16]);
                serr = serr + 1;
            end
            schk = schk + 1;
            sfault = sfault + dut.s_fault[i];
        end
        eslot = eslot + LI;
    end

    // driver / checker
    integer cyc = 0, q = 0, qh = 0, b = 0, bq = 0, nbq = 0, cc = 0, cexp = 0, cgot = 0, cerr = 0, credit = 0;
    integer phase = 0, t_start = 0, t_first = -1, t_last = -1, t_cand = -1;
    reg [31:0] rng = 32'h13579bdf;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        start <= 1'b0;
        ql_v <= 1'b0;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc > 400000000) begin $display("STTIMEOUT"); $finish; end
        case (phase)
            0: if (rst_n && cyc > 16) begin
                   if (q == nq) begin
                       $display("STDONE queries=%0d checked=%0d score_errors=%0d faults=%0d cand_errors=%0d",
                                q, schk, serr, sfault, cerr);
                       $finish;
                   end
                   start <= 1'b1; qh = 0; phase = 1; t_start = cyc; t_first = -1; t_last = -1; t_cand = -1;
                   nbq = nm[q]; bq = 0; credit = 0;
                   cexp = cm[cc][31:0]; cc = cc + 1; cgot = 0;
               end
            1: if (ql_ready || (ql_v && qh > 0)) begin       // q load, one head per cycle
                   if (qh < IH) begin
                       ql_v <= 1'b1; ql_head <= qh[7:0];
                       {ql_w, ql_sc, ql_codes} <= qm[q*IH + qh];
                       qh = qh + 1;
                   end else phase = 2;
               end
            2: begin
                   if (k_valid && k_ready) begin
                       if (t_first < 0) t_first = cyc;
                       if (k_last) t_last = cyc;
                       bq = bq + 1; b = b + 1;
                   end
                   if (rate > 0 && credit < 2 * LI) credit = credit + rate;
                   if (k_valid && !k_ready) ;
                   else if (bq < nbq && (rate == 0 || credit >= LI)) begin
                       k_valid <= 1'b1;
                       {k_kv, k_keep, k_key} <= km[b];
                       k_first <= bq * LI;
                       k_last <= (bq == nbq - 1);
                       if (rate > 0) credit = credit - LI;
                   end else k_valid <= 1'b0;
                   if (c_valid) begin
                       for (i = 0; i < 16; i = i + 1) if (c_lv[i]) begin
                           if (cgot >= cexp || c_idx[IW*i +: IW] != cm[cc + cgot][IW+15:16] ||
                               c_val[16*i +: 16] != cm[cc + cgot][15:0]) begin
                               if (cerr < 8) $display("STCANDMISMATCH q=%0d n=%0d got %h/%h exp %h/%h", q, cgot,
                                                      c_idx[IW*i +: IW], c_val[16*i +: 16], cm[cc + cgot][IW+15:16],
                                                      cm[cc + cgot][15:0]);
                               cerr = cerr + 1;
                           end
                           cgot = cgot + 1;
                       end
                       if (c_last) begin
                           t_cand = cyc;
                           if (cgot != cexp) begin cerr = cerr + 1; $display("STCANDCOUNT q=%0d got %0d exp %0d", q, cgot, cexp); end
                           $display("STQ q=%0d beats=%0d start=%0d first=%0d last=%0d cand=%0d folds=%0d pass=%0d stall=%0d fault=%0d",
                                    q, nbq, t_start, t_first, t_last, t_cand, st_folds, st_pass, st_stall, fault);
                           cc = cc + cexp;
                           q = q + 1;
                           phase = 3;
                       end
                   end
               end
            3: if (!busy) phase = 0;
            default: phase = 0;
        endcase
    end
endmodule
