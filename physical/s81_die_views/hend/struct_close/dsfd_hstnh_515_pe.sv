`timescale 1ns/1ps
// struct-close 2026-10-09 (REVIEW_20261008 DR4, "-cl" line): dsfd_hstnh_515 common-clock hub station, POSEDGE form.
// Same ports and function as the m221pq glue master (physical/s81_die_views/hend/m221pq/dsfd_glue.sv): every di bit is
// captured at the rising edge of ck and dq comes straight from that flop (dq(t+1) = di(t)); 0 cycles.
// Why: the glue master builds the station from ot_fwd_link_stage on fck = ~ck (ot_fwd_clk_inv) with negedge flops.
// s81-dsfd-hstnh-515-s81tail-4cd6d205a-tc died in 4_1_cts hold repair (RSZ-0060 buffer cap, FF hold -384.7 on all 515
// dq outputs): OT_IOREF set vclk to "core_clk mean 603.1" = arrival_max_RISE at the flop clock pins, which for a sink
// behind the inverter is the FALLING ck edge (+T/2 = 416.7) plus the ~190 ps tree -> the output-min reference sat ~T/2
// late and every output needed ~400 ps of hold padding.  Plain posedge flops on ck remove the inverted sink (the io_ref
// edge bug itself is reported to the flow owner).  MUT 1 (bench mutant): bit 0 is not registered.
module dsfd_hstnh_515 #(parameter integer MUT = 0) (
    input wire [0:0] ck,
    input wire [514:0] di,
    output wire [514:0] dq
);
    reg [514:0] q;
    always @(posedge ck[0]) q <= di;
    assign dq = (MUT == 1) ? {q[514:1], di[0]} : q;
endmodule
