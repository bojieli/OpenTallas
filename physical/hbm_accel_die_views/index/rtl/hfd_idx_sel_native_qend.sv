`default_nettype none
// Opt-in full T1 captured-SRAM selector with lossless quarter-end publication.
module hfd_idx_sel_native_qend(
 input wire ck,rst,
 input wire [89:0] fs,
 input wire [1047:0] qb,
 output wire qbr,
 input wire [344:0] kin,
 output wire [2283:0] qo,
 input wire [2439:0] si,
 output wire [3:0] sc,
 output wire [611:0] to,
 input wire toc,
 output wire [71:0] co,
 input wire coc,
 output wire [1:0] ev,
 output wire co_quarter_last
);
 hfd_idx_sel #(.T(1),.LA(7),.MEMV(1),.READLAT(2),.EXPOSE_QUARTER_LAST(1)) core(.*);
endmodule
`default_nettype wire
