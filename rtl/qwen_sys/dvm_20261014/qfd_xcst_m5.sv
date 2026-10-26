// MY-legal corridor station die masters (Q-COMPUTE-DIE r6 request 2026-10-15 06:20, PM-H-S pair-mirrored columns).
// Same RTL body as qfd_xcst_s / qfd_xcst_n (instantiated whole, no logic added); a distinct master name only because the
// physical view differs: every N/S face pin sits on M5 (12 mod 48 nm), none on M3.  On the ASAP7 lattice a tile whose
// vertical-axis pins use BOTH M3 (9 mod 36) and M5 (12 mod 48) has no legal MY origin for any width (MY maps the
// residues to -9 / -12: 6 vs 0 mod 12), so the closed qfd_xcst_s/n views (522 M3 + 518 M5 pins) cannot be mirrored.
// With M5-only N/S pins MY needs origin = 24 - W mod 48 = 0 mod 48 (W = 52.680) and R0 stays legal: one master for both.
module qfd_xcst_s_m5 #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    qfd_xcst_s #(.NW(NW), .AW(AW), .XOFF(XOFF)) u_xcst (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(a_d), .b_d(b_d),
        .tap_d(tap_d), .tie_hi(tie_hi), .tie_lo(tie_lo));
endmodule

module qfd_xcst_n_m5 #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    qfd_xcst_n #(.NW(NW), .AW(AW), .XOFF(XOFF)) u_xcst (.ck(ck), .rst_n(rst_n), .sidx(sidx), .b_d(b_d), .a_d(a_d),
        .tap_d(tap_d), .tie_hi(tie_hi), .tie_lo(tie_lo));
endmodule

// _my masters (2026-10-15 r6): M5-only N/S pins (the _m5 masters) congest the face (GRT-0116 twice: cut 0.49 on M5 plus a
// 4-layer via stack per pin on a 2-track lattice).  _my: every N/S pin on M3 (cut 0.37, no stacks) and width 52.686 um
// (= 18 mod 36 nm) so MY needs origin 18 - W = 0 mod 36, the same residue as R0: one master for both orientations.
module qfd_xcst_s_my #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    qfd_xcst_s #(.NW(NW), .AW(AW), .XOFF(XOFF)) u_xcst (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(a_d), .b_d(b_d),
        .tap_d(tap_d), .tie_hi(tie_hi), .tie_lo(tie_lo));
endmodule

module qfd_xcst_n_my #(parameter integer NW = 18, parameter integer AW = 24, parameter integer XOFF = 3) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d,
    output wire          tie_hi,
    output wire          tie_lo
);
    qfd_xcst_n #(.NW(NW), .AW(AW), .XOFF(XOFF)) u_xcst (.ck(ck), .rst_n(rst_n), .sidx(sidx), .b_d(b_d), .a_d(a_d),
        .tap_d(tap_d), .tie_hi(tie_hi), .tie_lo(tie_lo));
endmodule
