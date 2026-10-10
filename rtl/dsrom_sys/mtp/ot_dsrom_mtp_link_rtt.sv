`timescale 1ns/1ps
// Default-off RTT-aware successor. Existing ot_dsrom_mtp_lrx is byte-identical.
// FORWARD_HOPS / RETURN_HOPS must be actual registered relay counts. One grant
// is reserved for each cycle through return relays + tx rq + tx valid + forward
// relays + rx pin capture; the original no-relay history is exactly three.
module ot_dsrom_mtp_lrx_rtt #(
    parameter integer W=513, D=4, SEL=0,
    parameter bit ENABLE_RTT=0,
    parameter integer FORWARD_HOPS=0, RETURN_HOPS=0
) (
    input wire clk, rst_n, l_valid,
    output wire l_ready,
    input wire [W-1:0] l_data,
    output wire c_valid,
    input wire c_ready,
    output wire [W-1:0] c_data
);
    generate if (ENABLE_RTT) begin: g_rtt
        ot_dsrom_mtp_lrx_rtt_core #(.W(W),.D(D),.SEL(SEL),
            .FORWARD_HOPS(FORWARD_HOPS),.RETURN_HOPS(RETURN_HOPS)) u_rx
            (.clk(clk),.rst_n(rst_n),.l_valid(l_valid),.l_ready(l_ready),
             .l_data(l_data),.c_valid(c_valid),.c_ready(c_ready),.c_data(c_data));
    end else begin: g_legacy
        ot_dsrom_mtp_lrx #(.W(W),.D(D),.SEL(SEL)) u_rx
            (.clk(clk),.rst_n(rst_n),.l_valid(l_valid),.l_ready(l_ready),
             .l_data(l_data),.c_valid(c_valid),.c_ready(c_ready),.c_data(c_data));
    end endgenerate
endmodule

module ot_dsrom_mtp_lrx_rtt_core #(parameter integer W = 513, parameter integer D = 4, parameter integer SEL = 0,
    parameter integer FORWARD_HOPS = 0, RETURN_HOPS = 0) (
    input  wire         clk, rst_n,
    input  wire         l_valid,
    output wire         l_ready,
    input  wire [W-1:0] l_data,
    output wire         c_valid,
    input  wire         c_ready,
    output wire [W-1:0] c_data
);
    localparam integer ACTUAL_HISTORY = FORWARD_HOPS + RETURN_HOPS + 3;
`ifdef OT_MTP_NEG_SHORT_RTT
    localparam integer H = ACTUAL_HISTORY > 3 ? 3 : 2;
`else
    localparam integer H = ACTUAL_HISTORY;
`endif
    localparam integer CB = $clog2(D + ACTUAL_HISTORY + 2);
    initial begin
        if (D < 2 || FORWARD_HOPS < 0 || RETURN_HOPS < 0) $fatal(1, "invalid MTP link dimensions");
    end
    reg live;
    always @(posedge clk) live <= rst_n;
    reg pv; reg [W-1:0] pd;
    always @(posedge clk) begin pv <= l_valid; pd <= l_data; end   // pin flops
    wire pvl = pv && live;
    reg [W-1:0] q [0:D-1];
    reg [D-1:0] wp, rp;                  // one-hot write / read slot
    reg [CB-1:0] cnt;
    reg [H-1:0] grants;
    assign l_ready = grants[0];
    wire ne = cnt != 0;
    reg [W-1:0] qh;
    integer i, j;   // one loop variable per always block
    always @(*) begin
        qh = {W{1'b0}};
        for (j = 0; j < D; j = j + 1) if (rp[j]) qh = qh | q[j];
    end
    assign c_valid = ne || pvl;
    assign c_data = ne ? qh : pd;
    wire pop  = c_valid && c_ready;
    wire popq = pop && ne;
    wire push = pvl && (ne || !c_ready);  // the pin flit, unless taken straight from the pin flop
    wire [CB-1:0] cnt_n = cnt + {{(CB-1){1'b0}}, push} - {{(CB-1){1'b0}}, popq};
    always @(posedge clk)                // the slot write is enabled from registers only
        for (i = 0; i < D; i = i + 1) if (pvl && wp[i]) q[i] <= pd;
    // SEL: next state for c_ready = 0 (push = pvl, no pop) and c_ready = 1 (push = pvl && ne, pop = ne), from
    // registers only; c_ready selects.  Identical function to the cnt_n form.
    // Every still-in-flight grant owns one FIFO reservation. Balanced popcount
    // preserves the exact integer sum without a linear H-adder control path.
    localparam integer N = 1 << $clog2(H);
    wire [CB-1:0] sum [1:2*N-1];
    genvar g;
    generate for (g=0; g<N; g=g+1) begin: g_leaf
        if (g<H) assign sum[N+g] = {{(CB-1){1'b0}}, grants[g]};
        else assign sum[N+g] = {CB{1'b0}};
    end
    for (g=1; g<N; g=g+1) begin: g_sum
        assign sum[g] = sum[2*g] + sum[2*g+1];
    end endgenerate
    wire [CB-1:0] infl = sum[1];
    wire [CB-1:0] cnt_s0 = cnt + {{(CB-1){1'b0}}, pvl};
    wire [CB-1:0] cnt_s1 = cnt + {{(CB-1){1'b0}}, pvl && ne} - {{(CB-1){1'b0}}, ne};
    wire rdy_s0 = (cnt_s0 + infl) <= CB'(D - 1);
    wire rdy_s1 = (cnt_s1 + infl) <= CB'(D - 1);
    wire [D-1:0] wp_s0 = pvl ? {wp[D-2:0], wp[D-1]} : wp;
    wire [D-1:0] wp_s1 = (pvl && ne) ? {wp[D-2:0], wp[D-1]} : wp;
    wire [D-1:0] rp_s1 = ne ? {rp[D-2:0], rp[D-1]} : rp;
    always @(posedge clk)
        if (!live) begin
            cnt <= 0; grants <= '0;
            wp <= {{(D-1){1'b0}}, 1'b1}; rp <= {{(D-1){1'b0}}, 1'b1};
        end else if (SEL) begin
            cnt <= c_ready ? cnt_s1 : cnt_s0;
            grants <= {grants[H-2:0], c_ready ? rdy_s1 : rdy_s0};
            wp  <= c_ready ? wp_s1 : wp_s0;
            rp  <= c_ready ? rp_s1 : rp;
        end else begin
            cnt <= cnt_n;
            grants <= {grants[H-2:0], (cnt_n + infl) <= CB'(D - 1)};
            if (push) wp <= {wp[D-2:0], wp[D-1]};
            if (popq) rp <= {rp[D-2:0], rp[D-1]};
        end
`ifndef SYNTHESIS
    always @(posedge clk) if (live && push && cnt == CB'(D)) begin
        $display("LINK_REG FAIL: receive FIFO overflow (a flit arrived without a grant)");
        $fatal(1, "LINK_REG overflow");
    end
`endif
endmodule
