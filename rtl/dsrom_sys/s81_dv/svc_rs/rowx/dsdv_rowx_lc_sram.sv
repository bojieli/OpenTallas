`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-ROWX3 (2026-10-26): LANDED CROSSING of the rank-order row transport (one per receiving link port of
// dsdv_rowx_xm).  The incoming beat lands in a pin flop, then in a D-deep landing FIFO; the consumer pops on ITS OWN
// static slot schedule (never on arrival), so the arrival may jitter by up to the landing depth without changing any
// downstream cycle.  No credit, no ready: a pop from an empty FIFO (the word missed its booked slot) and a push into a
// full one are sticky faults (checks only, they never reschedule) -- the compiler books the pop
// >= the worst-case arrival + 2 (pin flop + FIFO write).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_rowx_lc_sram #(parameter integer W = 512, parameter integer D = 16, parameter integer MUT_BYPASS = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [W-1:0]  i_d,
    input  wire          pop,
    output wire [W-1:0]  o_d,          // FIFO head (valid when the pop is in its booked slot)
    output reg           f_late,       // sticky: pop with nothing landed
    output reg           f_ovf         // sticky: landing FIFO overflow
);
    localparam integer AW = $clog2(D);
    initial begin
        if (D < 2 || D > 32 || (1 << AW) != D || W < 1) $fatal(1,"ROWX SRAM LC requires power-of-two depth2..32 and W>0");
    end
    reg iv; reg [W-1:0] id;                                  // pin flops
    always @(posedge clk or negedge rst_n) if (!rst_n) iv <= 1'b0; else iv <= i_v;
    always @(posedge clk) id <= i_d;
    // One read-before-write 32x512 macro per 512-bit word slice. Rows D..31
    // are unused; this mechanism supports the production W1024/D16 FIFO.
    localparam integer NB = (W+511)/512;
    wire [NB*512-1:0] macro_d;
    wire [NB*512-1:0] padded_id = {{(NB*512-W){1'b0}}, id};
    reg [AW-1:0] wp, rp; reg [AW:0] n;
    wire emp = n == 0, ful = n == (AW+1)'(D);
    wire do_pop = pop && !emp, do_push = iv && (!ful || do_pop);
    wire [AW-1:0] rp_next = do_pop ? ((rp == AW'(D-1)) ? '0 : rp + 1'b1) : rp;
    reg bypass;
    reg [W-1:0] bypass_d;
    always @(posedge clk) begin
        bypass <= do_push && wp == rp_next && MUT_BYPASS == 0;
        bypass_d <= id;
    end
    genvar k;
    generate for(k=0;k<NB;k=k+1) begin:g_mem
        ot_sram_1r1w_32x512_m1 u_m (
            .clk(clk), .r_ce_in(1'b1), .r_addr_in(5'(rp_next)), .rd_out(macro_d[512*k+:512]),
            .w_ce_in(do_push), .w_addr_in(5'(wp)), .wd_in(padded_id[512*k+:512]), .w_mask_in(16'hffff));
    end endgenerate
    // Forward an empty push and a last-pop+push to preserve the new head in
    // the very same cycle; no extra pop or output register is introduced.
    assign o_d = emp ? {W{1'b0}} : bypass ? bypass_d : macro_d[W-1:0];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= 0; rp <= 0; n <= 0; f_late <= 1'b0; f_ovf <= 1'b0; end
        else begin
            if (do_push) wp <= (wp == AW'(D - 1)) ? '0 : wp + 1'b1;
            if (do_pop)  rp <= (rp == AW'(D - 1)) ? '0 : rp + 1'b1;
            n <= n + (AW+1)'(do_push) - (AW+1)'(do_pop);
            if (pop && emp) f_late <= 1'b1;
            if (iv && ful && !do_pop) f_ovf <= 1'b1;
        end
endmodule
