// S81 die relay master dsfd_rly_266_EW (x-site-pair xb relays, die lead 10-14): one register stage, 266 b in E / out W.
`default_nettype none
module dsfd_rly_266_EW (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);
    ot_s81_rly #(.W(266)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
