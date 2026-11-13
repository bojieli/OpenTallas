`timescale 1ns/1ps
// HARD-QC-FORMS-1 11-13 (R-RTL-6 lock-step bench, 0-cycle form OT_QC_SWREG): qfd_dv_s8s_sram_delay OREG 1 == OREG 0 on
// EVERY edge (q, bit for bit), through cold reset and a warm reset, for D = 3, 4 and 14.  +N=1 (expect NEW one edge
// late) must FAIL; -DTB_MUT (NEW with MUT 1: read address off by one) must FAIL.  bank64 / kept_valid are bench models.
module qfd_dv_sram_bank64 #(parameter integer W = 514) (input wire clk, input wire r_ce_in, input wire [4:0] r_addr_in, output reg [W-1:0] rd_out,
    input wire w_ce_in, input wire [4:0] w_addr_in, input wire [W-1:0] wd_in, input wire [W-1:0] w_mask_in);
    reg [W-1:0] m [0:31];
    always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= wd_in; end
endmodule
module qfd_dv_kept_valid #(parameter integer ID = 0) (input wire ck, rst_n, d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
module tb_swreg;
    localparam integer W = 97;
    reg ck = 0; always #0.4165 ck = ~ck;
    reg rst_n = 0; reg [W-1:0] d = 0; integer N = 0, errs = 0, cmp = 0, nz = 0, i, k;
    wire [W-1:0] qo [0:2]; wire [W-1:0] qn [0:2]; reg [W-1:0] qh [0:2];
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : g_d
        localparam integer D = (g == 0) ? 3 : (g == 1) ? 4 : 14;
        qfd_dv_s8s_sram_delay #(.W(W), .D(D)) u_old (.ck(ck), .rst_n(rst_n), .d(d), .q(qo[g]));
`ifdef TB_MUT
        qfd_dv_s8s_sram_delay #(.W(W), .D(D), .OREG(1), .MUT(1)) u_new (.ck(ck), .rst_n(rst_n), .d(d), .q(qn[g]));
`else
        qfd_dv_s8s_sram_delay #(.W(W), .D(D), .OREG(1)) u_new (.ck(ck), .rst_n(rst_n), .d(d), .q(qn[g]));
`endif
    end endgenerate
    reg [31:0] h;
    always @(negedge ck) begin
        h = $random; d = {4{h}};
        for (i = 0; i < 3; i = i + 1) begin
            if (qn[i] !== ((N == 0) ? qo[i] : qh[i])) begin errs = errs + 1; if (errs < 5) $display("SWREG_MISMATCH t=%0t D-index %0d", $time, i); end
            if (qo[i] != 0) nz = nz + 1; qh[i] = qo[i];
        end
        cmp = cmp + 1;
    end
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 0;
        for (i = 0; i < 3; i = i + 1) qh[i] = 0;
        repeat (5) @(posedge ck); rst_n = 1; repeat (200) @(posedge ck);
        #0.1 rst_n = 0; repeat (3) @(posedge ck); #0.2 rst_n = 1; repeat (200) @(posedge ck);
        if (errs == 0 && nz > 900) $display("SWREG_LOCKSTEP PASS N=%0d edges %0d nonzero %0d", N, cmp, nz);
        else $display("SWREG_LOCKSTEP FAIL N=%0d errs %0d nonzero %0d", N, errs, nz);
        $finish;
    end
endmodule
