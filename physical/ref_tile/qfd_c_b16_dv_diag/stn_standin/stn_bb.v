// DIAGNOSTIC stand-in blackboxes of the station masters (stn_standin.py); never bind
(* blackbox *) module qfd_c_stn516 (
    input wire [515:0] d,
    input wire ck,
    output wire [515:0] q
);
endmodule
(* blackbox *) module qfd_c_stn514 (
    input wire [513:0] d,
    input wire ck,
    output wire [513:0] q
);
endmodule
(* blackbox *) module qfd_c_xstn (
    input wire [515:0] b_d,
    input wire ck,
    input wire rst_n,
    input wire [2:0] sidx,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
endmodule
(* blackbox *) module qfd_c_xstnw (
    input wire [515:0] b_d,
    input wire ck,
    input wire rst_n,
    input wire [2:0] sidx,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
endmodule
