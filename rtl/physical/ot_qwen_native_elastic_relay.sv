`timescale 1ns/1ps
// Opt-in finite elastic native SQ/CQ relay. Arithmetic and beat order unchanged.
// ENABLE=0 retains the original TAP0 registered forward/two-stage credit relay.
// ENABLE=1 terminates the local credit loop in DEPTH registers, then launches
// through separately owned transmit pin flops. The consumer's readiness is
// internal; WFREE keeps it out of the wide receive write-enable path.
module ot_qwen_native_elastic_relay #(
    parameter integer W=546, DEPTH=8, OCRED=8, ENABLE=0
)(
    input wire clk, rst_n,
    input wire i_v, input wire [W-1:0] i_d, output wire i_cr,
    output wire o_v, output wire [W-1:0] o_d, input wire o_cr,
    output wire fault
);
    generate if(!ENABLE) begin:g_legacy
        wire [W:0] forward;
        ot_qwen_die_station #(.DW(W+1),.TAP(0)) u(
            .clk(clk),.rst_n(rst_n),.a_d({i_v,i_d}),.a_r(i_cr),
            .b_d(forward),.b_r(o_cr),.t_d(),.t_r(1'b1),.c_d(),.c_r(1'b1));
        assign {o_v,o_d}=forward;
        assign fault=1'b0;
    end else begin:g_elastic
        wire local_rst_n;
        ot_reset_sync reset_release(.clk(clk),.async_rst_n(rst_n),.sync_rst_n(local_rst_n));
        wire valid, ready, rf; wire [W-1:0] data;
        ot_link_credit_rx #(.W(W),.DEPTH(DEPTH),.OREG(0),.WFREE(1)) rx(
            .clk(clk),.rst_n(local_rst_n),.l_valid(i_v),.l_data(i_d),.l_credit(i_cr),
            .o_valid(valid),.o_ready(ready),.o_data(data),.fault(rf));
        // One owning o_cr pin flop, shared only after capture. Separately
        // capturing the same pin for a monitor would defeat pin ownership.
        // Data pins load freely; only o_v marks a meaningful output word.
        localparam integer CB=$clog2(OCRED+1)+1;
        reg cr_q, cf, fault_q, ov_q; reg [CB-1:0] cred;
        (* keep *) reg [W-1:0] od_q;
        assign ready=cred!=0;
        assign o_v=ov_q;assign o_d=od_q;
        wire send=valid && ready;
        wire [CB-1:0] next_credit=cred+cr_q-send;
        always @(posedge clk or negedge local_rst_n)
            if(!local_rst_n) begin cr_q<=0;cf<=0;fault_q<=0;cred<=OCRED;ov_q<=0;end
            else begin
                cr_q<=o_cr; cred<=next_credit;
                ov_q<=send;
                cf<=cf || next_credit>OCRED;
                fault_q<=fault_q || rf || cf;
            end
        assign fault=fault_q;
        always @(posedge clk) od_q<=data;
    end endgenerate
endmodule
