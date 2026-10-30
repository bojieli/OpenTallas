module ot_dp_clk_landing_cas_small #(
    parameter integer W        = 1,
    parameter integer DEPTH    = 4,   // power of two >= 4
    parameter integer GUARD_LO = 0,
    parameter integer GUARD_HI = DEPTH, // <= DEPTH; MESO-RECONCILE-1: default DEPTH (4 was wrong at DEPTH 8)
    parameter integer ARM      = 2 * DEPTH + 4, // receiver cycles after the first valid word before guards are trusted
    // MESO-RECONCILE-1 ready-timeout: fault if the crossing is not armed TIMEOUT receiver cycles after rst_n release
    // (0 = off).  In the window the first valid word (sender count 0) is consumed at receiver count max(K, 0), seen one
    // count later, armed ARM counts after that: armed by count max(K,0) + ARM + 2.  The default adds 2*DEPTH + 6 counts
    // of slack, so it never fires in the window (proven, fv_ca2 A_ALL); a lag below the window (no valid word is ever
    // consumed: never ready, previously no fault) now raises fault (fv_ca2 A_TMO).
    // strap form: K is any value of strap_k, so the timeout covers the largest, 2^KW - 1 (D4 91, D8 171 cycles)
    parameter integer TIMEOUT  = (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 2 * DEPTH + 8,
    parameter bit CONTROL_STATUS_COPY = 0 // appended to preserve positional parameters
) (
    input  wire         fclk,
    input  wire         t_rst_n,     // sender start, forwarded with fclk (synchronous to fclk)
    input  wire         clk,
    input  wire         rst_n,       // receiver start (count origin), synchronous to clk
    input  wire [$clog2(DEPTH)+3:0] strap_k,  // K mod 2^(log2(DEPTH)+4), quasi-static strap (tied at the parent)
    input  wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg          ready,
    output wire         fault
`ifdef OT_MESO_CA_FV
   ,input  wire [DEPTH-1:0] fv_recent, fv_now,
    input  wire [W+3:0]     fv_any
`endif
);
    localparam integer RW = W;
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(ARM + 1);
    localparam integer TCW = $clog2(TIMEOUT + 2);
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_q;
    assign q = ring_q[W-1:0];
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
    wire armed = seen && (arm_cnt == CW'(ARM));
    reg fault_state;
    reg [TCW-1:0] tmo_cnt;          // receiver cycles since rst_n release while not armed (saturates at TIMEOUT)
`ifdef OT_MESO_CA_MUTANT_NO_TIMEOUT
    wire tmo = 1'b0;                // MUTANT: ready-timeout disabled
`else
    wire tmo = (TIMEOUT > 0) && !armed && (tmo_cnt == TCW'(TIMEOUT));
`endif
    wire trip = (armed && (!rv || !lap_ok || !glo_ok || !ghi_ok)) || tmo;
    wire fault_next = fault_state || trip;
    ot_dp_landing_fault_port u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    always @(posedge clk) begin
        if (!rst_n) begin
            seen <= 0; arm_cnt <= 0; ready <= 0; fault_state <= 0; tmo_cnt <= 0;
        end else begin
            if (!armed && tmo_cnt != TCW'(TIMEOUT)) tmo_cnt <= tmo_cnt + 1'b1;
            if (rv) seen <= 1;
            if (seen && arm_cnt != CW'(ARM)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    ot_meso_ring_ca #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI),
                      .CONTROL_STATUS_COPY(CONTROL_STATUS_COPY)) u_ring (
        .tclk(fclk), .t_rst_n(t_rst_n), .t_d({{(RW-W){1'b0}}, d}), .rclk(clk), .r_rst_n(rst_n), .k_s(strap_k),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok), .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
`ifdef OT_MESO_CA_FV
       ,.fv_recent(fv_recent), .fv_now(fv_now), .fv_any(fv_any)
`endif
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "count-aligned landing requires a nonempty bundle");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $fatal(1, "DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_HI > DEPTH || GUARD_HI < GUARD_LO + 2) $fatal(1, "need 0 <= GUARD_LO, GUARD_LO+2 <= GUARD_HI <= DEPTH");
        if (TIMEOUT != 0 && TIMEOUT < (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 3) $fatal(1, "strap TIMEOUT below 2^KW - 1 + ARM + 3 would fire in the window");
    end
`endif
endmodule