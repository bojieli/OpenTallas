`timescale 1ns/1ps
// DIE-S81-85 form A (3) (11-09): a combinationally-read flop array whose read pointer steps by 0 or 1 a cycle, as two
// generated 1R1W macro banks (even / odd entries), cycle-exact and with NO logic between the pointer's next-state cone
// and the macro address: at every edge bank b reads the entry of parity b among {rp, rp + 1} (rp = the CURRENT pointer
// register), so next cycle both candidates are held and rd = the bank of the new pointer's parity.  Writes at the same
// edge to a row being read are bypassed (read-first macros).  Used where the pointer's advance depends on the data read
// (u_att SEL scanner: sw rd -> g_own / f_full -> sw_step -> sw_r), which as dsdv_svc_mem_ar would put macro clk->q +
// the scanner decision in front of the macro address (TT pre-route -107 ps at 833 ps).  0 added cycles.
//   DEPTH = 2^AW (pointer wraps), each bank DEPTH / 2 <= 32 entries on ot_sram_1r1w_32x128_m1_r0c0.
//   MUT (bench negative controls): 1 = no write bypass, 2 = bank chosen by the previous pointer.
module dsdv_svc_mem_la #(
    parameter integer W = 512,
    parameter integer AW = 5,
    parameter integer MUT = 0
)(
    input  wire          clk,
    input  wire [AW-1:0] rp,
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [W-1:0]  wd,
    output wire [W-1:0]  rd
);
    localparam integer MW = 128;
    localparam integer N = (W + MW - 1) / MW;
    localparam integer RW = AW - 1;
    wire [AW-1:0] rp1 = rp + 1'b1;
    reg  [AW-1:0] rp_q;
    reg  [1:0] byp_v;
    reg  [W-1:0] byp_d [0:1];
    wire [N*MW-1:0] wdp = (N*MW)'(wd);
    wire [N*MW-1:0] rdb [0:1];
    genvar b, g;
    generate
        if (RW > 5) begin : g_bad
            $error("dsdv_svc_mem_la: bank deeper than the 32-entry macro");
        end
        for (b = 0; b < 2; b = b + 1) begin : g_b
            wire [RW-1:0] row = (rp[0] == 1'(b)) ? rp[AW-1:1] : rp1[AW-1:1];
            wire bw = we && wa[0] == 1'(b);
            for (g = 0; g < N; g = g + 1) begin : g_m
                ot_sram_1r1w_32x128_m1_r0c0 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(5'(row)), .rd_out(rdb[b][g*MW +: MW]),
                    .w_ce_in(bw), .w_addr_in(5'(wa[AW-1:1])), .wd_in(wdp[g*MW +: MW]), .w_mask_in({MW{1'b1}}));
            end
            always @(posedge clk) begin
                byp_v[b] <= (MUT != 1) && bw && wa[AW-1:1] == row;
                byp_d[b] <= wd;
            end
        end
    endgenerate
    always @(posedge clk) rp_q <= rp;
    wire sel = (MUT == 2) ? rp_q[0] : rp[0];
    assign rd = byp_v[sel] ? byp_d[sel] : rdb[sel][W-1:0];
`ifndef SYNTHESIS
    always @(posedge clk) if (rp != rp_q && rp != rp_q + 1'b1 && $time > 20)
        $display("dsdv_svc_mem_la %m: pointer stepped by more than 1 (%0d -> %0d)", rp_q, rp);
`endif
endmodule
