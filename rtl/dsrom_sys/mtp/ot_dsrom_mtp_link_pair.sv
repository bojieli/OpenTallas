`timescale 1ns/1ps
// ot_dsrom_mtp_lrx / ot_dsrom_mtp_ltx: the closed WFC's registered link pair (ot_rom_pkg_ctrl_wfc_lrx / _ltx in
// rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv, commit-identical logic, renamed so the MTP blocks synthesise without the
// WFC source).  Grant protocol: the receiver's l_ready is a grant from a flop; a granted flit is launched by the
// sender from its flop two cycles later; the receiver counts the grants in flight (LINK_DEPTH = round trip).
module ot_dsrom_mtp_lrx #(parameter integer W = 513, parameter integer D = 4, parameter integer SEL = 0) (
    input  wire         clk, rst_n,
    input  wire         l_valid,
    output wire         l_ready,
    input  wire [W-1:0] l_data,
    output wire         c_valid,
    input  wire         c_ready,
    output wire [W-1:0] c_data
);
    localparam integer CB = $clog2(D + 1) + 2;
    reg live;
    always @(posedge clk) live <= rst_n;
    reg pv; reg [W-1:0] pd;
    always @(posedge clk) begin pv <= l_valid; pd <= l_data; end   // pin flops
    wire pvl = pv && live;
    reg [W-1:0] q [0:D-1];
    reg [D-1:0] wp, rp;                  // one-hot write / read slot
    reg [CB-1:0] cnt;
    reg rdy, r1, r2;
    assign l_ready = rdy;
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
`ifdef OT_MTP_NEG_LINK
    wire [CB-1:0] infl = {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1};                                  // negative control
`else
    wire [CB-1:0] infl = {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1} + {{(CB-1){1'b0}}, r2};
`endif
    wire [CB-1:0] cnt_s0 = cnt + {{(CB-1){1'b0}}, pvl};
    wire [CB-1:0] cnt_s1 = cnt + {{(CB-1){1'b0}}, pvl && ne} - {{(CB-1){1'b0}}, ne};
    wire rdy_s0 = (cnt_s0 + infl) <= CB'(D - 1);
    wire rdy_s1 = (cnt_s1 + infl) <= CB'(D - 1);
    wire [D-1:0] wp_s0 = pvl ? {wp[D-2:0], wp[D-1]} : wp;
    wire [D-1:0] wp_s1 = (pvl && ne) ? {wp[D-2:0], wp[D-1]} : wp;
    wire [D-1:0] rp_s1 = ne ? {rp[D-2:0], rp[D-1]} : rp;
    always @(posedge clk)
        if (!live) begin
            cnt <= 0; rdy <= 1'b0; r1 <= 1'b0; r2 <= 1'b0;
            wp <= {{(D-1){1'b0}}, 1'b1}; rp <= {{(D-1){1'b0}}, 1'b1};
        end else if (SEL) begin
            cnt <= c_ready ? cnt_s1 : cnt_s0;
            rdy <= c_ready ? rdy_s1 : rdy_s0;
            wp  <= c_ready ? wp_s1 : wp_s0;
            rp  <= c_ready ? rp_s1 : rp;
            r1 <= rdy; r2 <= r1;
        end else begin
            cnt <= cnt_n;
`ifdef OT_MTP_NEG_LINK
            rdy <= (cnt_n + {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1}) <= CB'(D - 1);   // negative control: forgets a grant in flight
`else
            rdy <= (cnt_n + {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1} + {{(CB-1){1'b0}}, r2}) <= CB'(D - 1);
`endif
            r1 <= rdy; r2 <= r1;
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

module ot_dsrom_mtp_ltx #(parameter integer W = 513) (
    input  wire         clk, rst_n,
    input  wire         c_valid,
    output wire         c_ready,
    input  wire [W-1:0] c_data,
    output wire         l_valid,
    input  wire         l_ready,
    output wire [W-1:0] l_data
);
    reg live, rq, v;
    reg [W-1:0] d;
    always @(posedge clk) live <= rst_n;
    always @(posedge clk) rq <= l_ready;                 // pin flop: the receiver's grant
    assign c_ready = rq && live;                         // one flit per grant
    always @(posedge clk) begin v <= c_valid && c_ready; d <= c_data; end
    assign l_valid = v; assign l_data = d;
endmodule
