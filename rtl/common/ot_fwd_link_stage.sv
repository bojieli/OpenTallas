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
            if(!rst_n)v<=0;else begin v<=i_v;d<=i_d;end
        end
        assign fclk_o=~fclk_i;assign o_v=v;assign o_d=d;
    end else begin:disabled
        assign fclk_o=0;assign o_v=0;assign o_d=0;
    end endgenerate
endmodule
