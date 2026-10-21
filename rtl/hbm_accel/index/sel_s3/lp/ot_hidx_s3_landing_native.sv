// Equal-age selector reset copies; control-only, no extra reset edge.
`default_nettype none
(* keep_hierarchy = "yes" *) module ot_hidx_s3_reset_copy(input wire ck,d,output reg q);
 (* keep *) reg rq;
 always @(posedge ck) rq <= d;
 always @* q = rq;
endmodule
`default_nettype wire
