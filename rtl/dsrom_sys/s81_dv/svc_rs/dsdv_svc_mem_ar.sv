`timescale 1ns/1ps
// DIE-S81-85 form A (3) (11-09): a small behavioral array as generated 1R1W SRAM macros, cycle-exact.
//   SYNC = 0: equal to a COMBINATIONAL read of a flop array, rd = mem[ra_q], where ra_q is the read pointer register and
//             ra_n its D input (the address of the NEXT cycle).  The macro reads ra_n at every edge; a write at the same
//             edge to ra_n is bypassed (the macro model is read-first), so rd also shows a write of the cycle before.
//             Zero added cycles.  Needs >= 1 clock edge with the pointer in reset (S81 holds rst_n >= 64 clk).
//   SYNC = 1: equal to `q <= mem[ra]` (read-first, old data on a same-edge write): rd = macro rd_out, ra = this edge.
//   Out-of-range (>= DEPTH) writes are dropped and reads return 0, as the flop array in Verilator.
//   MACRO 0: ot_sram_1r1w_32x128_m1_r0c0 (DEPTH <= 32), 1: ot_sram_1r1w_160x256_m1_r0c0 (DEPTH <= 160); W split into
//   ceil(W / macro width) macros side by side, full-word writes.
//   MUT (bench negative controls): 1 = no write bypass, 2 = macro read at the current pointer (one cycle late).
module dsdv_svc_mem_ar #(
    parameter integer W = 512,
    parameter integer DEPTH = 32,
    parameter integer AW = 5,
    parameter integer MACRO = 0,
    parameter integer SYNC = 0,
    parameter integer MUT = 0
)(
    input  wire          clk,
    input  wire [AW-1:0] ra_n,
    input  wire          we,
    input  wire [AW-1:0] wa,
    input  wire [W-1:0]  wd,
    output wire [W-1:0]  rd
);
    localparam integer MW = (MACRO == 1) ? 256 : 128;
    localparam integer MAW = (MACRO == 1) ? 8 : 5;
    localparam integer MD = (MACRO == 1) ? 160 : 32;
    localparam integer N = (W + MW - 1) / MW;
    reg [AW-1:0] ra_q;
    reg byp_v;
    reg [W-1:0] byp_d;
    wire w_ok = we && (32'(wa) < DEPTH);
    wire [AW-1:0] ra_m = (MUT == 2) ? ra_q : ra_n;
    wire [N*MW-1:0] wdp = (N*MW)'(wd);
    wire [N*MW-1:0] rdp;
    genvar g;
    generate
        if (DEPTH > MD || AW > MAW) begin : g_bad
            $error("dsdv_svc_mem_ar: DEPTH / AW exceed the macro");
        end
        for (g = 0; g < N; g = g + 1) begin : g_m
            if (MACRO == 1) begin : g_160
                ot_sram_1r1w_160x256_m1_r0c0 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(MAW'(ra_m)), .rd_out(rdp[g*MW +: MW]),
                    .w_ce_in(w_ok), .w_addr_in(MAW'(wa)), .wd_in(wdp[g*MW +: MW]), .w_mask_in({MW{1'b1}}));
            end else begin : g_32
                ot_sram_1r1w_32x128_m1_r0c0 u_mem (
                    .clk(clk), .r_ce_in(1'b1), .r_addr_in(MAW'(ra_m)), .rd_out(rdp[g*MW +: MW]),
                    .w_ce_in(w_ok), .w_addr_in(MAW'(wa)), .wd_in(wdp[g*MW +: MW]), .w_mask_in({MW{1'b1}}));
            end
        end
        if (SYNC != 0) begin : g_sync
            always @(posedge clk) ra_q <= ra_n;
            assign rd = (32'(ra_q) >= DEPTH) ? {W{1'b0}} : rdp[W-1:0];
        end else begin : g_ar
            always @(posedge clk) begin
                ra_q <= ra_n;
                byp_v <= (MUT != 1) && w_ok && wa == ra_n;
                byp_d <= wd;
            end
            assign rd = (32'(ra_q) >= DEPTH) ? {W{1'b0}} : byp_v ? byp_d : rdp[W-1:0];
        end
    endgenerate
`ifdef OT_SVC_MEM_COV
    // bench coverage (sim only): writes, pointer moves, reads that return a written entry
    integer cov_w = 0, cov_mv = 0, cov_rd = 0, cov_byp = 0;
    always @(posedge clk) begin
        if (w_ok) cov_w <= cov_w + 1;
        if (ra_n != ra_q) cov_mv <= cov_mv + 1;
        if (cov_w > 0 && rd != 0) cov_rd <= cov_rd + 1;
        if (byp_v) cov_byp <= cov_byp + 1;
    end
    final $display("MEM_COV %m writes=%0d ptr_moves=%0d nonzero_reads=%0d bypass=%0d", cov_w, cov_mv, cov_rd, cov_byp);
`endif
endmodule
