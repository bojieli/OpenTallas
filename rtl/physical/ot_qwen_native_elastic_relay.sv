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
        wire valid, ready, rf; wire [W-1:0] data;
        ot_link_credit_rx #(.W(W),.DEPTH(DEPTH),.OREG(0),.WFREE(1)) rx(
            .clk(clk),.rst_n(rst_n),.l_valid(i_v),.l_data(i_d),.l_credit(i_cr),
            .o_valid(valid),.o_ready(ready),.o_data(data),.fault(rf));
        ot_link_credit_tx #(.W(W),.CRED(OCRED)) tx(
            .clk(clk),.rst_n(rst_n),.i_valid(valid),.i_ready(ready),.i_data(data),
            .l_valid(o_v),.l_data(o_d),.l_credit(o_cr));
        // Monitor the same captured credit/send accounting as tx. Overflow
        // remains visible; this never manufactures credits or suppresses data.
        localparam integer CB=$clog2(OCRED+1)+1;
        reg cr_q, cf, fault_q; reg [CB-1:0] cred;
        wire send=valid && ready;
        wire [CB-1:0] next_credit=cred+cr_q-send;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) begin cr_q<=0;cf<=0;fault_q<=0;cred<=OCRED;end
            else begin
                cr_q<=o_cr; cred<=next_credit;
                cf<=cf || next_credit>OCRED;
                fault_q<=fault_q || rf || cf;
            end
        assign fault=fault_q;
    end endgenerate
endmodule
