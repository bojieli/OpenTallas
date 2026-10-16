// S-NET+FILL 2026-10-16: relay flow variants the die asked for (c26b GEN --rly-face-pins kit_requests,
// /srv/opentallas-scratch/claude/s81-die-iter/c26b/a_real/relay_face_audit.json: dsfd_rly_283_WN 753 instances, gain up
// to 103.8 um; dsfd_rly_283_WW 467 instances, gain up to 106.0 um).  Same body as the closed 283 standards (one register
// stage, ot_s81_rly RSREG=1); only the pin faces differ: <in face><out face>, WW = U master (in and out on W).
`default_nettype none
module dsfd_rly_283_WN (input wire ck, input wire rs, input wire [282:0] i, output wire [282:0] o);
    ot_s81_rly #(.W(283), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
module dsfd_rly_283_WW (input wire ck, input wire rs, input wire [282:0] i, output wire [282:0] o);
    ot_s81_rly #(.W(283), .RSREG(1)) u (.ck(ck), .rs(rs), .i(i), .o(o));
endmodule
`default_nettype wire
