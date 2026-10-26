module dsfd_rly_1_WN(input ck, rs, i, output o); ot_s81_rly #(.W(1)) u(.ck(ck), .rs(rs), .i(i), .o(o)); endmodule
module ICGx4_ASAP7_75t_R(input CLK, ENA, SE, output GCLK); reg en_l; /* verilator lint_off COMBDLY */ always_latch if (!CLK) en_l = ENA | SE; /* verilator lint_on COMBDLY */ assign GCLK = CLK & en_l; endmodule
// dv_flight_sim (S81-LBGAP/G1, bench side): F whole periods of lane flight between the last relay station and its
// landing.  The word is delayed F edges of the lane clock and the lane clock reaches the landing F edges late: its first
// edge carries the word of hop-0 gate edge G, as the silicon ck_f edge 0 does (LANDING-CONTRACT L3).
module dv_flight_sim #(parameter integer W = 1, parameter integer F = 0) (
    input  wire ck_in, input wire rs, input wire [W-1:0] i_in, output wire ck_out, output wire [W-1:0] i_out);
    generate if (F == 0) begin : g0
        assign ck_out = ck_in; assign i_out = i_in;
    end else begin : gf
        reg [W-1:0] d [0:F-1];
        reg [31:0] n = 0;
        reg en_l = 1'b0;
        integer k;
        always @(posedge ck_in) begin
            d[0] <= i_in;
            for (k = 1; k < F; k = k + 1) d[k] <= d[k - 1];
        end
        // the flight count starts with the lane clock's first real edge: the time-0 settle of an idle-high (inverted,
        // half-cycle) lane clock is not an edge (rs kept on the port for the record; the wire delay ignores it)
        always @(posedge ck_in)
            if ($time > 0 && n < F) n <= n + 1;
        /* verilator lint_off COMBDLY */
        always_latch if (!ck_in) en_l = (n >= F);
        /* verilator lint_on COMBDLY */
        assign ck_out = ck_in & en_l;
        assign i_out = d[F - 1];
    end endgenerate
endmodule
