// S81 die relay master dsfd_rly_266_EW (x-site-pair xb relays, die lead 10-14): one register stage, 266 b in E / out W.
// LANE S81-B 10-17: reset pin register (RSREG=1, rs1s56 / dvrly form) -- native audit of v3 (f96151f35) failed rs capture
// 271.7 ps (rs fanned out to every data flop); initialization only, data path unchanged.
`default_nettype none
module dsfd_rly_266_EW (input wire ck, input wire rs, input wire [265:0] i, output wire [265:0] o);
    ot_s81_rly #(.W(266), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
