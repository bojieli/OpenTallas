module ot_s81_hc_cpad_split #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6, RET_EXTRA = 1, PHYS_CLK = 0, PIN_CAPTURE = 1, RETURN_CAPTURE = 1
) (
    input  wire                 sk, srs,
    input  wire [3:0]           sk_leaf,
    input  wire [RDW-1:0]       crd_i,
    output wire [RDW-1:0]       crd_o,
    input  wire [FVW-1:0]       fv_i,
    input  wire [FSW-1:0]       fd_i,
    output wire [FVW-1:0]       fv_o,
    output wire [FSW-1:0]       fd_o
);
    // the comb's geometry (identical to ot_s81_hc_comb; defaults = the hardened NG 256 HIER=1 configuration)
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD + RET_EXTRA * (NP - L1) * (HALF ? 2 : 1);                         // return: relay + send + capture + padding
    // No assembly data/valid flop: each hard child's first/last flop is its boundary.
    // FV transfers one stage into CCF; return transfers one R6 stage into the two-face middle pad.
    localparam integer F0 = (FP-2-PIN_CAPTURE > 8) ? 8 : FP-2-PIN_CAPTURE;
    localparam integer F1 = FP-2-F0-PIN_CAPTURE;
    localparam integer R0_BASE = (RP-2 > 6) ? 6 : RP-2;
    localparam integer RCAP = (R0_BASE > 0) ? RETURN_CAPTURE : 0;
    localparam integer R0 = R0_BASE-RCAP;
    localparam integer R1 = RP-2-R0_BASE;
    wire [FVW-1:0] fm;
    wire [FSW-1:0] dm;
    wire [RDW-1:0] rpin, rm;
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_pad_f8 u_f8 (
`else
    ot_s81_hc_pad_f8 #(.FW(FSW),.VW(FVW),.DEPTH(F0)) u_f8 (
`endif
        .sk(PHYS_CLK ? sk_leaf[0] : sk),.srs(srs),.v_i(fv_i),.d_i(fd_i),.v_o(fm),.d_o(dm));
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_pad_fv4fd5r2 u_f5r1 (
`else
    ot_s81_hc_pad_fv4fd5r2 #(.FW(FSW),.VW(FVW),.RW(RDW),.DEPTH(F1+PIN_CAPTURE),.VDEPTH(F1),.RDEPTH(1+RCAP)) u_f5r1 (
`endif
        .sk(PHYS_CLK ? sk_leaf[1] : sk),.srs(srs),.v_i(fm),.d_i(dm),.v_o(fv_o),.d_o(fd_o),.r_i(crd_i),.r_o(rpin));
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_pad_r5 u_r6 (
`else
    ot_s81_hc_pad_r5 #(.W(RDW),.DEPTH(R0)) u_r6 (
`endif
        .sk(PHYS_CLK ? sk_leaf[2] : sk),.srs(srs),.d_i(rpin),.d_o(rm));
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_pad_r5 u_r5 (
`else
    ot_s81_hc_pad_r5 #(.W(RDW),.DEPTH(R1)) u_r5 (
`endif
        .sk(PHYS_CLK ? sk_leaf[3] : sk),.srs(srs),.d_i(rm),.d_o(crd_o));
`ifndef SYNTHESIS
    initial begin
        if (F0<0 || F1<0 || R0<0 || R1<0) $fatal(1,"pad split requires nonnegative soft relay depths");
`ifdef OT_S81_HC_PAD_HARD
        if(NG!=256 || HALF!=1 || RLY!=2 || RF!=5 || RT!=1 || RET_EXTRA!=1 ||
           S_RD!=2 || S_RT!=4 || DW!=6 || F0!=8 || F1!=4 || RETURN_CAPTURE!=1 || RCAP!=1 || R0!=5 || R1!=5)
            $fatal(1,"pad hard views require exact production depth/width tuple");
`endif
    end
`endif
endmodule

module ot_s81_hc_ccr_align #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6, RET_EXTRA = 1, PHYS_CLK = 0, PIN_CAPTURE = 1
) (
    input  wire                 sk, srs,
    input  wire [1:0]           sk_leaf,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd,
    output wire [RDW-1:0]       crd_o,         // stage 0 (the capture), on to ot_s81_hc_cpad
    output wire [RVW-1:0]       crv_o,         // stage RP-1
    output wire [7:0]           cpi_o,         // stage RP-1: the row's PI byte
    output wire [NE1*32-1:0]    ex1_o          // stage RP-1: the subtree exports
);
    // the comb's geometry (identical to ot_s81_hc_comb; defaults = the hardened NG 256 HIER=1 configuration)
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD + RET_EXTRA * (NP - L1) * (HALF ? 2 : 1);                         // return: relay + send + capture + padding
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
    localparam integer L0 = NP, L2 = NP;
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
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL, c);
    endfunction
    localparam integer NE0_ = necnt(0), NE1_ = necnt(1), NE2_ = necnt(2);
    localparam integer NE0 = (NE0_ > 0) ? NE0_ : 1, NE1 = (NE1_ > 0) ? NE1_ : 1, NE2 = (NE2_ > 0) ? NE2_ : 1;
    localparam integer NIM_ = NE0_ + NE1_ + NE2_, NIM = (NIM_ > 0) ? NIM_ : 1;
    // Preserve the existing HALF1/RLY2/RET_EXTRA0 hardened core exactly.
    localparam integer EXTRA = RET_EXTRA*(NP-L1)*(HALF ? 2 : 1);
    wire [RVW-1:0] mv;
    wire [7:0] mp;
    wire [NE1*32-1:0] me;
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_ccr u_core (
`else
    ot_s81_hc_ccr #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_WR(S_WR),.S_RT(S_RT),
       .ML(ML),.AL(AL),.MUT(MUT),.AMUT(AMUT),.RF(4),.RT(RT),.RW(RW),.YD(YD),
       .HALF(HALF),.RLY(RLY),.DW(DW),.RET_EXTRA(0)) u_core (
`endif
       .sk(PHYS_CLK ? sk_leaf[0] : sk),.srs(srs),.ch_rv(ch_rv),.ch_rd(ch_rd),.crd_o(crd_o),.crv_o(mv),.cpi_o(mp),.ex1_o(me));
    generate if(EXTRA>0)begin:g_meta
`ifdef OT_S81_HC_PAD_HARD
       ot_s81_hc_pad_meta2 u_m (
`else
       ot_s81_hc_pad_meta2 #(.VW(RVW),.EW(NE1*32),.DEPTH(EXTRA)) u_m (
`endif
          .sk(PHYS_CLK ? sk_leaf[1] : sk),.srs(srs),.v_i(mv),.p_i(mp),.e_i(me),.v_o(crv_o),.p_o(cpi_o),.e_o(ex1_o));
    end else begin:g_direct
       assign crv_o=mv;assign cpi_o=mp;assign ex1_o=me;
    end endgenerate
`ifndef SYNTHESIS
`ifdef OT_S81_HC_PAD_HARD
    initial if(NG!=256 || HALF!=1 || RLY!=2 || RF!=5 || RT!=1 || RET_EXTRA!=1 ||
        S_RD!=2 || S_RT!=4 || DW!=6 || NE1*32!=512 || EXTRA!=2)
        $fatal(1,"CCR core/meta hard views require production width/depth tuple");
`endif
`endif
endmodule
