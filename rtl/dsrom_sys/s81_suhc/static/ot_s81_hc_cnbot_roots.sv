// Candidate wires-only parent; all existing child arithmetic and stages preserved.
module ot_s81_hc_cnbot_roots #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, NT_K = 67
) (
    input  wire                 sk,
    input wire [7:0] sk_leaf,
    input  wire                 srs,
    input  wire [3*FVW-1:0]     f_fv,          // per chain: far tile fv_out
    input  wire [3*8-1:0]       f_nv,          // per chain: far tile fd_out[O_NV +: 8]
    input  wire [O_D-1:0]       f_fc0,         // chain 0: far tile fd_out control word
    input  wire [S_RD*32-1:0]   f_eps0,        // chain 0: eps bits of the read slots
    input  wire [3*DLW-1:0]     dl,            // per chain: partial lane
    output wire [3*33-1:0]      ul,            // per chain: scale lane
    output wire                 flt
);
    localparam integer FVW = S_RD + 5, SW = 137, DLW = 2 * SW + 1;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, O_NG = 5 + S_RD * 16 + 20;
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, NL = 4 * NS, LT = $clog2(NL);
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer B0 = 0, B1 = NP, B2 = NP + L1;
    function automatic integer lev(input integer n);
        integer t;
        begin t = 0; while ((n >> (t + 1)) > 0) t = t + 1; lev = LT - t; end
    endfunction
    function automatic integer owner(input integer n);
        integer k, sz, s0;
        begin
            k = lev(n); sz = 1 << k; s0 = ((n << k) - NL) % NS;
            owner = 3;
            if (sz <= NS) begin
                if (L0 > 0 && s0 >= B0 && s0 + sz <= B0 + L0) owner = 0;
                else if (L1 > 0 && s0 >= B1 && s0 + sz <= B1 + L1) owner = 1;
                else if (L2 > 0 && s0 >= B2 && s0 + sz <= B2 + L2) owner = 2;
            end
        end
    endfunction
    function automatic integer expd(input integer n, input integer c);
        expd = (owner(n) == c) && (c != 3) && (n == 1 || owner(n / 2) != c);
    endfunction
    function automatic integer exidx(input integer n, input integer c);
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + expd(m, c); exidx = t; end
    endfunction
    localparam integer NE0_ = exidx(2 * NL, 0), NE1_ = exidx(2 * NL, 1), NE2_ = exidx(2 * NL, 2);
    localparam integer NE0 = (NE0_ > 0) ? NE0_ : 1, NE1 = (NE1_ > 0) ? NE1_ : 1, NE2 = (NE2_ > 0) ? NE2_ : 1;
    localparam integer NEM = (NE0 > NE1) ? ((NE0 > NE2) ? NE0 : NE2) : ((NE1 > NE2) ? NE1 : NE2);
    function automatic integer hlf(input integer n);
        hlf = (((n << lev(n)) - NL) / NS) / 2;
    endfunction
    function automatic integer exh(input integer n, input integer c, input integer h);   // index among half h's exports
        integer m, t;
        begin t = 0; for (m = 1; m < n; m = m + 1) t = t + (expd(m, c) && hlf(m) == h); exh = t; end
    endfunction
    function automatic integer neh(input integer c, input integer h);
        neh = (exh(2 * NL, c, h) > 0) ? exh(2 * NL, c, h) : 1;
    endfunction
    wire [2:0] rv, cf, fb;
    wire [7:0] pc [0:2];
    wire [NEM*32-1:0] xf [0:2];                          // per chain: the full export vector in heap order
    wire [NEM*32-1:0] xa [0:2], xb [0:2];                // per chain: bank-half exports
    genvar c, n;
    generate
        for (c = 0; c < 3; c = c + 1) begin : g_c
            localparam integer NA = neh(c, 0), NB = neh(c, 1);
            wire [DLW-1:0] dlc = dl[c * DLW +: DLW];
            // the lane split by bank half: slot q = {data 128, vector 3, octet 5, v} -> {data 64 of the half, tags 9}
            wire [2*73:0]   dla = {dlc[DLW-1], dlc[SW + 9 +: 64], dlc[SW +: 9], dlc[9 +: 64], dlc[0 +: 9]};
            wire [2*73-1:0] dlb = {dlc[SW + 73 +: 64], dlc[SW +: 9], dlc[73 +: 64], dlc[0 +: 9]};
            ot_s81_hc_cncla #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .AL(AL), .C(c), .NT_K(NT_K)) u_a (.sk(sk_leaf[2*c]),
                .srs(srs), .f_fv(f_fv[c * FVW +: FVW]), .f_nv(f_nv[c * 8 +: 8]), .dl(dla), .flt_b(fb[c]), .rvt(rv[c]), .pi(pc[c]),
                .ex(xa[c][NA*32-1:0]), .flt(cf[c]));
            ot_s81_hc_cnclb #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .AL(AL), .C(c), .NT_K(NT_K)) u_b (.sk(sk_leaf[2*c+1]),
                .srs(srs), .f_fv(f_fv[c * FVW +: FVW]), .f_nv(f_nv[c * 8 +: 8]), .dl(dlb), .ex(xb[c][NB*32-1:0]), .flt(fb[c]));
            if (NA < NEM) begin : g_pa
                assign xa[c][NEM*32-1:NA*32] = {((NEM - NA) * 32){1'b0}};
            end
            if (NB < NEM) begin : g_pb
                assign xb[c][NEM*32-1:NB*32] = {((NEM - NB) * 32){1'b0}};
            end
            for (n = 1; n < 2 * NL; n = n + 1) begin : g_x
                if (expd(n, c)) begin : g_e
                    if (hlf(n) == 0) begin : g_ha
                        assign xf[c][32 * exidx(n, c) +: 32] = xa[c][32 * exh(n, c, 0) +: 32];
                    end else begin : g_hb
                        assign xf[c][32 * exidx(n, c) +: 32] = xb[c][32 * exh(n, c, 1) +: 32];
                    end
                end
            end
            if (exidx(2 * NL, c) < NEM) begin : g_pf
                assign xf[c][NEM*32-1:exidx(2 * NL, c)*32] = {((NEM - exidx(2 * NL, c)) * 32){1'b0}};
            end
        end
    endgenerate
    wire [NE0*32-1:0] x0 = xf[0][NE0*32-1:0];
    wire [NE1*32-1:0] x1 = xf[1][NE1*32-1:0];
    wire [NE2*32-1:0] x2 = xf[2][NE2*32-1:0];
    wire [7:0] p0 = pc[0], p1 = pc[1], p2 = pc[2];
    wire ngo; // cnrsq owns this registered launch; the region wrapper contains no state.
    wire        ss_v, tflt;
    wire [31:0] ss;
    ot_s81_hc_cntree #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL),
                       .HALF(1), .RLY(2), .RF(4), .DW(6)) u_tr (
        .sk(sk_leaf[6]), .srs(srs), .w_rvt(rv[0]), .e_rvt(rv[2]), .w_pi(p0), .e_pi(p2), .w_ex(x0), .e_ex(x2),
        .c_rvt(rv[1]), .c_pi(p1), .c_ex(x1), .ngo_i(ngo), .ss_v(ss_v), .ss(ss), .tflt(tflt));
    ot_s81_hc_cnrsq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL)) u_rsq (.sk(sk_leaf[7]), .srs(srs), .f_fv(f_fv[0 +: FVW]),
        .f_fc(f_fc0), .f_eps(f_eps0), .ss_v(ss_v), .ss(ss), .tflt(tflt), .cflt(cf), .ul(ul), .flt(flt), .ngo(ngo));
endmodule
