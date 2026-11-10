`timescale 1ns/1ps
// DIE-S81-85 form A read-data retime (11-09, -DOT_SVC_ATT_RDPIPE): dsdv_svc_mem_la with a REGISTERED read word.
// The u_att SEL scanner (sw word -> sid_g -> g_own / f_full -> sw_step -> sw_r / sw_i / fq_w / sel_held) had the macro
// clk->q (269 ps) in front of the whole decision: TT pre-route sel_held -142 / -157, sw_r -97, fq_w -93 at 833 ps.
// Here rd is a flop H that always holds the CURRENT entry rp, so the scanner starts at a flop; 0 added cycles (the
// read is cycle-exact with the flop array sw[rp]).
//   N = the entry rp + 1: two generated 1R1W banks (even / odd entries) read, at every edge, the rows of parity b among
//       {rp + 1, rp + 2} of the pointer before the edge; the new pointer is rp or rp + 1, so N = the bank of parity
//       (rp + 1)[0] (+ a same-edge write bypass: read-first macros).
//   H <= (write to entry rp_n at this edge) ? wd : (rp_n != rp) ? N : H        (rp_n = the pointer's D input)
// The pointer's next-state cone drives only the H load select, never a macro address (the address is the rp flop + 1/2).
// H is the flop-array word whenever the entry is readable: after a reset the pointer is 0 and the first write to entry
// 0 loads H; a stale H is never read while the FIFO is empty (the scanner is gated by sw_have).
//   DEPTH = 2^AW (pointer wraps), each bank DEPTH / 2 <= 32 entries on ot_sram_1r1w_32x128_m1_r0c0.
//   MUT (bench negative controls): 1 = no write capture into H (the compensation dropped), 2 = N from the wrong bank.
module dsdv_svc_mem_lr #(
    parameter integer W = 512,
    parameter integer AW = 5,
    parameter integer MUT = 0
)(
    input  wire          clk,
    input  wire [AW-1:0] rp,
    input  wire [AW-1:0] rp_n,
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [W-1:0]  wd,
    output wire [W-1:0]  rd
);
    localparam integer MW = 128;
    localparam integer N = (W + MW - 1) / MW;
    localparam integer RW = AW - 1;
    wire [AW-1:0] rp1 = rp + 1'b1;
    wire [AW-1:0] rp2 = rp + 2'd2;
    reg  [1:0] byp_v;
    reg  [W-1:0] byp_d [0:1];
    wire [N*MW-1:0] wdp = (N*MW)'(wd);
    wire [N*MW-1:0] rdb [0:1];
    reg  [W-1:0] h;
    genvar b, g;
    generate
        if (RW > 5) begin : g_bad
            $error("dsdv_svc_mem_lr: bank deeper than the 32-entry macro");
        end
        for (b = 0; b < 2; b = b + 1) begin : g_b
            wire [RW-1:0] row = (rp1[0] == 1'(b)) ? rp1[AW-1:1] : rp2[AW-1:1];
            wire bw = we && wa[0] == 1'(b);
            for (g = 0; g < N; g = g + 1) begin : g_m
                ot_sram_1r1w_32x128_m1_r0c0 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(5'(row)), .rd_out(rdb[b][g*MW +: MW]),
                    .w_ce_in(bw), .w_addr_in(5'(wa[AW-1:1])), .wd_in(wdp[g*MW +: MW]), .w_mask_in({MW{1'b1}}));
            end
            always @(posedge clk) begin
                byp_v[b] <= bw && wa[AW-1:1] == row;
                byp_d[b] <= wd;
            end
        end
    endgenerate
    wire nsel = (MUT == 2) ? rp[0] : rp1[0];
    wire [W-1:0] n_w = byp_v[nsel] ? byp_d[nsel] : rdb[nsel][W-1:0];
    always @(posedge clk)
        if (MUT != 1 && we && wa == rp_n) h <= wd;
        else if (rp_n != rp) h <= n_w;
    assign rd = h;
`ifdef OT_SVC_MEM_COV
    integer cov_w = 0, cov_mv = 0, cov_rd = 0, cov_byp = 0;
    always @(posedge clk) begin
        if (we) cov_w <= cov_w + 1;
        if (rp_n != rp) cov_mv <= cov_mv + 1;
        if (cov_w > 0 && rd != 0) cov_rd <= cov_rd + 1;
        if (byp_v != 0 || (we && wa == rp_n)) cov_byp <= cov_byp + 1;
    end
    final $display("MEM_COV %m writes=%0d ptr_moves=%0d nonzero_reads=%0d bypass=%0d", cov_w, cov_mv, cov_rd, cov_byp);
`endif
`ifndef SYNTHESIS
    always @(posedge clk) if (rp_n != rp && rp_n != rp + 1'b1 && $time > 20)
        $display("dsdv_svc_mem_lr %m: pointer stepped by more than 1 (%0d -> %0d)", rp, rp_n);
`endif
endmodule
