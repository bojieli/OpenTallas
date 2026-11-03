module ot_dp_landing_origin_s #(
    parameter integer PADW = 1,
    // Optional retained DATA-state copies for the forwarded START face flops.
    // Their D/clock/reset match the existing stages; latency and sampling stay exact.
    parameter integer FWD_COPY = 0
) (
    input  wire            clk,
    input  wire            rst_raw_n,
    input  wire            p_start,
    input  wire            strap_efall,
    input  wire [PADW-1:0] strap_pad,
    output wire            start,
    // DIE-HEAD-10 FSTART out: D-side of start (start_d(t) == start(t+1) while rst_raw_n is high).  The wrapper's
    // dedicated face flop per forwarded start pin (d = start_d, same clk / raw reset) equals start every cycle:
    // 0 added cycles, proven by results/die_head_1028/die_head_10_fstart/fv_start_o.sh; internal loads keep start
    output wire            start_d
);
    localparam integer PADMAX = (1 << PADW) - 1;
    (* async_reg = "true" *) reg s0, s1, sf;
    reg s2;
    always @(negedge clk) sf <= p_start;
    wire s_in = strap_efall ? sf : p_start;
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    reg [PADMAX-1:0] pd;
    always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PADMAX'({pd, s2});
    wire [PADMAX:0] taps = {pd, s2};
    assign start = taps[strap_pad];
    // one tap earlier: taps_e[j] is the D-side of taps[j] (taps_e[0] = s1 -> s2, taps_e[j] = taps[j-1])
    wire [PADMAX:0] taps_e = {taps[PADMAX-1:0], s1};
`ifdef OT_ORIGIN_MUTANT_LATE
    assign start_d = taps[strap_pad];     // MUTANT (fv only): one cycle late
`else
    generate if (FWD_COPY != 0) begin : g_export
        wire [PADMAX-1:0] export_q;
        for (genvar k = 0; k < PADMAX; k = k + 1) begin : g_copy
            wire d;
            if (k == 0) assign d = s1;
            else if (k == 1) assign d = s2;
            else assign d = pd[k-2];
`ifdef OT_ORIGIN_EXPORT_MUTANT_LATE
            wire copy_d;
            if (k == 0) assign copy_d = s2; else assign copy_d = d;
`else
            wire copy_d = d;
`endif
            (* keep = "true" *) ot_dp_origin_export_ff u_copy (
                .clk(clk), .rst_raw_n(rst_raw_n), .d(copy_d), .q(export_q[k]));
        end
        wire [PADMAX:0] export_taps = {export_q, s1};
        assign start_d = export_taps[strap_pad];
    end else begin : g_shared_export
        assign start_d = taps_e[strap_pad];
    end endgenerate
`endif
`ifndef SYNTHESIS
    initial if (PADW < 1 || PADW > 4) $fatal(1, "origin strap PADW must be 1..4");
`endif
endmodule
