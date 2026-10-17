// Candidate only: existing delay/core arithmetic, independent real child roots.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cpad (s81-suhc-hier-1011 comb v2, 2026-10-11): the centre chain's pad registers (hard tile, bottom row).
// Pure delay: the return rows crd stages 1 .. RP-1 (stage 0 = the ot_s81_hc_ccr capture, stage RP = the
// ot_s81_hc_crx capture) and the forward bus fv / fd stages 2 .. FP-1 (stage 1 = ot_s81_hc_cseq's centre copy,
// stage FP = the ot_s81_hc_ccf capture).  The first stage of each line is the input capture, the last the output.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cpad_roots20 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6, RET_EXTRA = 1,
    // FWD_TRIM (HC-COMB 2026-10-16, opt-in, default 0): forward pad stages removed from u_f5r1 because the CCF successor
    // ot_s81_hc_ccf_bankpipe adds exactly FWD_TRIM (= 2) public edges; ch_fv / ch_fd / the centre round trip keep the
    // old cycle (0 calendar cost).  Only the y push moves FWD_TRIM edges later relative to its pop (HC bench checked).
    parameter integer FWD_TRIM = 0
) (
    input  wire                 sk, srs,
    input wire [3:0] sk_pad,
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
    localparam integer F0 = (FP-2 > 8) ? 8 : FP-2;
    localparam integer F1 = FP-2-FWD_TRIM-F0;
    // HC-COMB-3 2026-10-16: ot_s81_hc_ccr now registers crd twice (W-pin capture + E-pin output, CCR_OREG = 1; native
    // audit of the closed single crd flop: launch 279.7 / capture 257.1 ps, one flop cannot sit at both faces), so the
    // return pad chain is one stage shorter: R0 = R1 = 5, both on the closed ot_s81_hc_pad_r5 master (r6 retired).
    localparam integer CCR_OREG = 1;
    // OT_S81_HC_PAD_RP2 (HC-COL 10-16, retcol a4b): RET_EXTRA 2 (CNL_PIN 1 + RETCOL_HQ 1) makes the centre return two
    // stages deeper (RP 13 -> 15): the hard return pad is then two closed ot_s81_hc_pad_r6 masters (6 + 6, was r5 + r5)
    // and the CCR meta pad two closed ot_s81_hc_pad_meta2 masters in series (4, was 2).  Without the define nothing moves.
`ifdef OT_S81_HC_PAD_RP2
    localparam integer RCAP = 6;
`else
    localparam integer RCAP = 5;
`endif
    localparam integer R1 = (RP-2-CCR_OREG > RCAP) ? RCAP : RP-2-CCR_OREG;
    localparam integer R0 = RP-2-CCR_OREG-R1;
    wire [FVW-1:0] fm;
    wire [FSW-1:0] dm;
    wire [RDW-1:0] rpin, rm;
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_pad_f8 u_f8 (
`else
    ot_s81_hc_pad_f8 #(.FW(FSW),.VW(FVW),.DEPTH(F0)) u_f8 (
`endif
        .sk(sk_pad[0]),.srs(srs),.v_i(fv_i),.d_i(fd_i),.v_o(fm),.d_o(dm));
`ifdef OT_S81_HC_PAD_HARD
    ot_s81_hc_pad_f5r1 u_f5r1 (
`else
    ot_s81_hc_pad_f5r1 #(.FW(FSW),.VW(FVW),.RW(RDW),.DEPTH(F1)) u_f5r1 (
`endif
        .sk(sk_pad[1]),.srs(srs),.v_i(fm),.d_i(dm),.v_o(fv_o),.d_o(fd_o),.r_i(crd_i),.r_o(rpin));
`ifdef OT_S81_HC_PAD_HARD
`ifdef OT_S81_HC_PAD_RP2
    ot_s81_hc_pad_r6 u_r6 (
`else
    ot_s81_hc_pad_r5 u_r6 (
`endif
`else
    ot_s81_hc_pad_r6 #(.W(RDW),.DEPTH(R0)) u_r6 (
`endif
        .sk(sk_pad[2]),.srs(srs),.d_i(rpin),.d_o(rm));
`ifdef OT_S81_HC_PAD_HARD
`ifdef OT_S81_HC_PAD_RP2
    ot_s81_hc_pad_r6 u_r5 (
`else
    ot_s81_hc_pad_r5 u_r5 (
`endif
`else
    ot_s81_hc_pad_r5 #(.W(RDW),.DEPTH(R1)) u_r5 (
`endif
        .sk(sk_pad[3]),.srs(srs),.d_i(rm),.d_o(crd_o));
`ifndef SYNTHESIS
    initial begin
        if (F0<0 || F1<0 || R0<0 || R1<0) $fatal(1,"pad split requires nonnegative soft relay depths");
`ifdef OT_S81_HC_PAD_HARD
`ifdef OT_S81_HC_PAD_RP2
        if(NG!=256 || HALF!=1 || RLY!=2 || RF!=5 || RT!=1 || RET_EXTRA!=2 ||
           S_RD!=2 || S_RT!=4 || DW!=6 || F0!=8 || F1!=5 || R0!=6 || R1!=6)
            $fatal(1,"pad hard views (RP2) require exact production depth/width tuple: RET_EXTRA 2, return 6 + 6");
`else
        if(NG!=256 || HALF!=1 || RLY!=2 || RF!=5 || RT!=1 || RET_EXTRA!=1 ||
           S_RD!=2 || S_RT!=4 || DW!=6 || F0!=8 || F1!=5 || R0!=5 || R1!=5)
            $fatal(1,"pad hard views require exact production depth/width tuple");
`endif
`endif
    end
`endif
endmodule

module ot_s81_hc_ccr_roots20 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 5, RT = 1, RW = 2, YD = 16, HALF = 1, RLY = 2, DW = 6, RET_EXTRA = 1
) (
    input  wire                 sk, srs,
    input wire [1:0] sk_return,
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
       .sk(sk_return[0]),.srs(srs),.ch_rv(ch_rv),.ch_rd(ch_rd),.crd_o(crd_o),.crv_o(mv),.cpi_o(mp),.ex1_o(me));
    generate if(EXTRA>0)begin:g_meta
`ifdef OT_S81_HC_PAD_HARD
`ifdef OT_S81_HC_PAD_RP2
       wire [RVW-1:0] mv2; wire [7:0] mp2; wire [NE1*32-1:0] me2;
       ot_s81_hc_pad_meta2 u_m (
          .sk(sk_return[1]),.srs(srs),.v_i(mv),.p_i(mp),.e_i(me),.v_o(mv2),.p_o(mp2),.e_o(me2));
       ot_s81_hc_pad_meta2 u_m2 (
          .sk(sk_return[1]),.srs(srs),.v_i(mv2),.p_i(mp2),.e_i(me2),.v_o(crv_o),.p_o(cpi_o),.e_o(ex1_o));
`else
       ot_s81_hc_pad_meta2 u_m (
          .sk(sk_return[1]),.srs(srs),.v_i(mv),.p_i(mp),.e_i(me),.v_o(crv_o),.p_o(cpi_o),.e_o(ex1_o));
`endif
`else
       ot_s81_hc_pad_meta2 #(.VW(RVW),.EW(NE1*32),.DEPTH(EXTRA)) u_m (
          .sk(sk_return[1]),.srs(srs),.v_i(mv),.p_i(mp),.e_i(me),.v_o(crv_o),.p_o(cpi_o),.e_o(ex1_o));
`endif
    end else begin:g_direct
       assign crv_o=mv;assign cpi_o=mp;assign ex1_o=me;
    end endgenerate
`ifndef SYNTHESIS
`ifdef OT_S81_HC_PAD_HARD
`ifdef OT_S81_HC_PAD_RP2
    initial if(NG!=256 || HALF!=1 || RLY!=2 || RF!=5 || RT!=1 || RET_EXTRA!=2 ||
        S_RD!=2 || S_RT!=4 || DW!=6 || NE1*32!=512 || EXTRA!=4)
        $fatal(1,"CCR core/meta hard views (RP2) require production width/depth tuple: RET_EXTRA 2, meta 2 x meta2");
`else
    initial if(NG!=256 || HALF!=1 || RLY!=2 || RF!=5 || RT!=1 || RET_EXTRA!=1 ||
        S_RD!=2 || S_RT!=4 || DW!=6 || NE1*32!=512 || EXTRA!=2)
        $fatal(1,"CCR core/meta hard views require production width/depth tuple");
`endif
`endif
`endif
endmodule
