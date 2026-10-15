`timescale 1ns/1ps
// Q-FUNC: replay the ACTUAL constant reads of one core rank (OT_CROM_TRACE of a PASSing whole-token run) through the
// native SU-side path exactly as ot_qwen_native_memory_cluster wires it: per 8-lane group ot_qfd_su_cbuf_g_tp8 (local
// SRAM constant buffer, answer at strobe+5) filled from ot_qfd_crom_gr TP8 (48 real mask-ROM models, released masks
// from crom_native_masks.py, far latency 8). Reads are issued at the recorded edge spacing; every active lane must
// answer at exactly strobe+5 with the stage-image word; residency (st_rdy/st_rdy_stage) is asserted at each read and
// never waited on. Token start/stage are driven as the compiler's SU-side controller would; LEAD = reserved fill window.
module tb_crom8_r3_abi_replay;
parameter integer NMAX = 200000;
parameter integer LEAD = 400;
parameter integer MUT = 0;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg [63:0] re = 0; reg [1535:0] addr = 0; reg [5:0] stage = 0; reg tok_start = 0;
wire [4095:0] q; wire [7:0] fault; wire [15:0] code; wire [7:0] resident; wire [47:0] resident_stage;
// ABI variant (join960): the same recorded reads enter through the SU ca0..7 packing
// {stage[5:0], crom_addr[191:0], crom_re[7:0]} of qfd_sp_su64_sfu_glue_entries and return on cq0..7 of the
// join's actual provider qfd_native_crom8_tp8 (separate crom/cbuf clock entries driven in phase here).
wire [205:0] ca [0:7]; wire [511:0] cq [0:7];
genvar g;
generate for (g = 0; g < 8; g = g + 1) begin : g_pack
    assign ca[g] = {stage, addr[192*g +: 192], re[8*g +: 8]};
    assign q[512*g +: 512] = cq[g];
end endgenerate
wire any_fault;wire [9:0] cbr[0:7];wire [143:0] resident_tpos;wire [7:0] group_fault;
qfd_native_crom8_r3_tp8 #(.CROM_MUT(MUT==1),.RETURN_MUT(MUT==2)) u_dut (.crom_ck({8{clk}}), .cbuf_ck({8{clk}}), .rst_n(rst_n),
    .return_ck({8{clk}}),
    .cbc0({18'd0,tok_start,stage}), .cbc1({18'd0,tok_start,stage}), .cbc2({18'd0,tok_start,stage}), .cbc3({18'd0,tok_start,stage}), .cbc4({18'd0,tok_start,stage}), .cbc5({18'd0,tok_start,stage}), .cbc6({18'd0,tok_start,stage}), .cbc7({18'd0,tok_start,stage}),
    .cbr0(cbr[0]), .cbr1(cbr[1]), .cbr2(cbr[2]), .cbr3(cbr[3]), .cbr4(cbr[4]), .cbr5(cbr[5]), .cbr6(cbr[6]), .cbr7(cbr[7]),
    .constants_resident_tpos(resident_tpos),.group_fault(group_fault),
    .ca0(ca[0]), .ca1(ca[1]), .ca2(ca[2]), .ca3(ca[3]), .ca4(ca[4]), .ca5(ca[5]), .ca6(ca[6]), .ca7(ca[7]),
    .cq0(cq[0]), .cq1(cq[1]), .cq2(cq[2]), .cq3(cq[3]), .cq4(cq[4]), .cq5(cq[5]), .cq6(cq[6]), .cq7(cq[7]),
    .constants_resident(resident), .constants_resident_stage(resident_stage), .crom_fault_code(code), .fault(any_fault));
assign fault = {7'd0, any_fault};
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
            if (!(resident == 8'hff && resident_stage == {8{stage}} && resident_tpos == 144'd0)) begin
                rd_faults = rd_faults + 1;
                if (rd_faults < 5) $display("RESIDENCY read=%0d stage=%0d rdy=%h rs=%h", i, stage, resident, resident_stage);
            end
            for(integer gi=0;gi<8;gi=gi+1) if(cbr[gi] !== {code[2*gi+:2],group_fault[gi],resident_stage[6*gi+:6],resident[gi]})begin errors=errors+1;$display("CBR packing mismatch group=%0d",gi);end
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
    if (errors) $display("FAIL crom8_abi_replay errors=%0d residency=%0d reads=%0d", errors, rd_faults, n);
    else $display("PASS crom8_abi_replay reads=%0d edges=%0d exact_E5 R3_CBUF+CROM+actual_return3", n, cyc - t0);
    $finish;
end
endmodule
