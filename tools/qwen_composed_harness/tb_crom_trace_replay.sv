`timescale 1ns/1ps
// Q-FUNC: replay the ACTUAL constant reads of one core rank (OT_CROM_TRACE of a PASSing whole-token run) through the
// native SU-side path exactly as ot_qwen_native_memory_cluster wires it: per 8-lane group ot_qfd_su_cbuf_g_tp8 (local
// SRAM constant buffer, answer at strobe+5) filled from ot_qfd_crom_gr TP8 (48 real mask-ROM models, released masks
// from crom_native_masks.py, far latency 8). Reads are issued at the recorded edge spacing; every active lane must
// answer at exactly strobe+5 with the stage-image word; residency (st_rdy/st_rdy_stage) is asserted at each read and
// never waited on. Token start/stage are driven as the compiler's SU-side controller would; LEAD = reserved fill window.
module tb_crom_trace_replay;
parameter integer NMAX = 200000;
parameter integer LEAD = 400;
parameter integer MUT = 0;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg [63:0] re = 0; reg [1535:0] addr = 0; reg [5:0] stage = 0; reg tok_start = 0;
wire [4095:0] q; wire [7:0] fault; wire [15:0] code; wire [7:0] resident; wire [47:0] resident_stage;
genvar g;
generate for (g = 0; g < 8; g = g + 1) begin : g_crom
    wire [7:0] far_re; wire [191:0] far_addr; wire [5:0] far_stage; wire [511:0] far_q; wire far_fault; wire [1:0] far_code;
    ot_qfd_su_cbuf_g_tp8 u_cbuf (.clk(clk), .rst_n(rst_n), .crom_re(re[8*g +: 8]), .crom_addr(addr[192*g +: 192]),
        .crom_stage(stage), .crom_q(q[512*g +: 512]), .stage(stage), .tok_start(tok_start), .tpos(18'd0), .grp(3'(g)),
        .st_rdy(resident[g]), .st_rdy_stage(resident_stage[6*g +: 6]), .f_re(far_re), .f_addr(far_addr),
        .f_stage(far_stage), .f_q(far_q), .f_fault(far_fault), .f_lat(5'd8), .fault(fault[g]), .fault_code(code[2*g +: 2]));
    ot_qfd_crom_gr #(.TP(8), .IMG_LB(8*g), .MUT(MUT)) u_rom (.clk(clk), .rst_n(rst_n), .crom_re(far_re),
        .crom_addr(far_addr), .crom_stage(far_stage), .crom_lb(6'(8*g)), .crom_q(far_q), .fault(far_fault),
        .fault_code(far_code));
end endgenerate
reg [63:0] hdr [0:NMAX-1];
reg [63:0] msk [0:NMAX-1];
reg [23:0] ad  [0:NMAX*64-1];
reg [63:0] ex  [0:NMAX*64-1];
reg [1023:0] vdir;
integer n, i, l, errors = 0, rd_faults = 0, chk = 0, issued = 0;
longint cyc = 0, t0, e0;
// pending checks: read i answers at cycle due[i]
longint due [0:NMAX-1];
integer head = 0;
initial begin
    if (!$value$plusargs("V=%s", vdir) || !$value$plusargs("N=%d", n)) begin $display("FAIL args"); $finish; end
    if (n > NMAX) begin $display("FAIL N > NMAX"); $finish; end
    $readmemh({vdir, "/rd_hdr.hex"}, hdr); $readmemh({vdir, "/rd_mask.hex"}, msk);
    $readmemh({vdir, "/rd_addr.hex"}, ad); $readmemh({vdir, "/rd_exp.hex"}, ex);
    repeat (4) @(negedge clk); rst_n = 1; repeat (12) @(negedge clk);
    stage = 6'(hdr[0][5:0]); tok_start = 1; @(negedge clk); tok_start = 0;
    repeat (LEAD) @(negedge clk);
    cyc = 0; t0 = 0; e0 = longint'(hdr[0][63:8]);
    i = 0;
    while (i < n || head < issued) begin
        // check answers due now (strobe + 5)
        while (head < issued && due[head] == cyc) begin
            for (l = 0; l < 64; l = l + 1) if (msk[head][l] && q[64*l +: 64] !== ex[64*head + l]) begin
                errors = errors + 1;
                if (errors < 10) $display("MISMATCH read=%0d edge=%0d stage=%0d lane=%0d addr=%0d got=%h exp=%h", head,
                    hdr[head][63:8], hdr[head][5:0], l, ad[64*head + l], q[64*l +: 64], ex[64*head + l]);
            end
            chk = chk + 1; head = head + 1;
        end
        re = 0;
        if (i < n && longint'(hdr[i][63:8]) - e0 + t0 == cyc) begin
            if (6'(hdr[i][5:0]) != stage) begin
                stage = 6'(hdr[i][5:0]);   // stage switch at the recorded edge (prefetch of the next stage is the buffer's)
            end
            if (!(resident == 8'hff && resident_stage == {8{stage}})) begin
                rd_faults = rd_faults + 1;
                if (rd_faults < 5) $display("RESIDENCY read=%0d stage=%0d rdy=%h rs=%h", i, stage, resident, resident_stage);
            end
            re = msk[i];
            for (l = 0; l < 64; l = l + 1) addr[24*l +: 24] = ad[64*i + l];
            due[i] = cyc + 5; issued = issued + 1; i = i + 1;
        end else if (i < n && longint'(hdr[i][63:8]) - e0 + t0 < cyc) begin
            $display("FAIL trace edges not increasing at read %0d", i); $finish;
        end
        @(negedge clk); cyc = cyc + 1;
    end
    if (|fault) begin errors = errors + 1; $display("FAULT codes=%h", code); end
    if (rd_faults) errors = errors + rd_faults;
    if (chk != n) begin errors = errors + 1; $display("FAIL checked %0d of %0d", chk, n); end
    if (errors) $display("FAIL crom_trace_replay errors=%0d residency=%0d reads=%0d", errors, rd_faults, n);
    else $display("PASS crom_trace_replay reads=%0d edges=%0d exact_E5 native_cbuf+crom_gr", n, cyc - t0);
    $finish;
end
endmodule
