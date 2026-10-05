// Default-off candidate. Capture on incoming clock falling edge; the forwarded
// output clock is inverted, so the following stage's falling capture is the
// opposite half-cycle. Timing must use the actual generated clock waveform.
module ot_fwd_link_stage #(
    parameter integer W=512,
    parameter bit ENABLE=0,
    parameter integer SPAN_NM=430560
)(input wire fclk_i, input wire rst_n,
  input wire i_v, input wire [W-1:0] i_d,
  output wire fclk_o, output wire o_v, output wire [W-1:0] o_d);
    initial if(SPAN_NM<=0 || SPAN_NM>430560)$error("forwarded span exceeds modeled reach");
    generate if(ENABLE)begin:active
        reg v;reg [W-1:0] d;
        always @(negedge fclk_i)begin
            if(!rst_n)v<=0;else v<=i_v;
            d<=i_d;   // data needs no reset hold (o_v qualifies it): no W-wide reset enable on the capture flops
        end
        // The forwarded clock is a real cell (kept hierarchy): flattened, yosys would fold the inversion into the next
        // stage's flops and the flow would balance both stages on one tree (a synchronous span, not a forwarded clock).
        ot_fwd_clk_inv u_fwd_inv(.a(fclk_i), .y(fclk_o));
        assign o_v=v;assign o_d=d;
    end else begin:disabled
        assign fclk_o=0;assign o_v=0;assign o_d=0;
    end endgenerate
endmodule

// Forwarding inverter of ot_fwd_link_stage: the root of the next stage's own clock subtree (the forwarded clock travels
// beside its bus from here).  keep_hierarchy keeps it a cell through synthesis.
(* keep_hierarchy *)
module ot_fwd_clk_inv(input wire a, output wire y);
    assign y = ~a;
endmodule
