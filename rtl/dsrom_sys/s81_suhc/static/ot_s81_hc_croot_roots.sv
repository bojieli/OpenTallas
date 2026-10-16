// Source-current candidate only; unchanged real arithmetic/storage, no parent state.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crootr (s81-suhc-hier-1011; v2 4-tile split 2026-10-12, [hc-crootr] PHYSICAL SPEC in
// el1011-s81-suhc-hier-1011.log): the S half of a split outer column root (dsfd_sp_hc CSPLIT=1), slot 575.992 x 640
// beside the combine tile; its N neighbour ot_s81_hc_crooty holds the pins and the y FIFO.  v1 was ONE tile (34.6k
// flops on one clock root over 576 x 641 um, the y slice crossing the whole height in one cycle).  v2 is a WIRES-ONLY
// wrapper (same ports, so the slab composition is unchanged) of four hard tiles the die places in the slot:
//   ot_s81_hc_crootr_f  forward: full-height column on the far face; fd relays (RF), y pin flop + RF-4 y relays
//                       (mid-height), the chain output flop where the y slice joins (S face), p_req, ch_rst
//   ot_s81_hc_crootr_t  tree: the chain's subtrees (ot_s81_hc_stree OWN C) behind their own packet capture (the moved
//                       ex relay), s_ex; also the comb forward seam capture fd_c / fv_c (registered feed-through)
//   ot_s81_hc_crootr_r  return: capture, RT relays, s_rv / s_rd (S + comb faces); the packet slice to the tree
//   ot_s81_hc_crootr_w  writes: capture, RW relays, p_w (comb + N faces); p_flt -> s_flt
// Cycle counts at the wrapper ports are v1's with RF = 5 (one y relay at mid-height; dsfd_sp_hc passes the comb the
// matching RF), except the tree's add-fault flag, which reaches s_rv one cycle later (event-based).
// The y slice of a POST beat is requested at the forward capture (p_req) and lands (p_y) 3 cycles after p_req.
// PQ 1 (2026-10-13 r10, pin-register form of T_fwd; production default): p_req is LC bits, one pin flop per y slice
// leaf (ot_s81_hc_cryys k takes p_req[k]), fed from the FIRST fv relay (the W-face capture of f_fv), so the request
// leaves one cycle later than in the PQ 0 form; the cycle is taken back from the mid-height y relay (RF - 5 relays, 0 at
// RF 5): the y slice runs N pin flop -> chain output flop inside the tile.  Wrapper-port cycle counts are unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crootr_roots #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 5, RT = 1, RW = 1
) (
    input  wire                 sk,
    input wire [3:0] sk_leaf,
    input  wire                 srs,
    // the pin / FIFO tile above
    output wire [LC-1:0]        p_req,                    // one copy per y slice leaf
    input  wire [YS-1:0]        p_y,
    output wire [4*WSL-1:0]     p_w,
    input  wire                 p_flt,
    // combine tile seam
    input  wire [FVW-1:0]       s_fv,
    input  wire [FSW-1:0]       s_fd,
    input  wire [4*WSL-1:0]     s_w,
    output wire [RVW-1:0]       s_rv,
    output wire [RDW-1:0]       s_rd,
    output wire [NEX*32-1:0]    s_ex,
    output wire                 s_flt,
    // column chain C
    output wire                 ch_rst,
    output wire [FVW-1:0]       ch_fv,
    output wire [FDW-1:0]       ch_fd,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer NL = 4 * NS;
    localparam integer LT = $clog2(NL);
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
    function automatic integer necnt(input integer c);
        necnt = exidx(2 * NL, c);
    endfunction
    function automatic integer imoff(input integer c);
        integer t, cc;
        begin t = 0; for (cc = 0; cc < c; cc = cc + 1) t = t + necnt(cc); imoff = t; end
    endfunction
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_PI = S_RT + 24 * S_RT, P_D = P_PI + 8, RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer YS = LC * GS * 32;
    localparam integer NEX_ = necnt(C);
    localparam integer NEX = (NEX_ > 0) ? NEX_ : 1;
    localparam integer PKW = NP * 128;
`ifndef SYNTHESIS
    initial if (RF < 4 || RT < 1 || RW < 0) $fatal(1, "ot_s81_hc_crootr: needs RF >= 4 (y pin flop + RF-4 relays), RT >= 1");
`endif
    // ---------------------------------------------------------------- tile-to-tile seams (die-level, registered)
    wire [FVW-1:0] f_fv;                                 // T_tree fv_c / fd_c -> T_fwd (the comb seam capture)
    wire [FSW-1:0] f_fd;
    wire           t_v;                                  // T_ret rv_c[S_RT] / rd_c packet slice -> T_tree
    wire [PKW-1:0] t_pk;
    wire           t_flt;                                // T_tree registered add fault -> T_ret
`ifdef OT_S81_HC_CROOTR_HARD
 `define OT_HCR_P
`else
 `define OT_HCR_P #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .AL(AL), .C(C), .RF(RF), .RT(RT), .RW(RW))
`endif
    ot_s81_hc_crootr_f `OT_HCR_P u_f (.sk(sk_leaf[0]), .srs(srs), .f_fv(f_fv), .f_fd(f_fd), .p_req(p_req), .p_y(p_y),
        .ch_rst(ch_rst), .ch_fv(ch_fv), .ch_fd(ch_fd));
    ot_s81_hc_crootr_t `OT_HCR_P u_t (.sk(sk_leaf[1]), .srs(srs), .s_fv(s_fv), .s_fd(s_fd), .f_fv(f_fv), .f_fd(f_fd),
        .t_v(t_v), .t_pk(t_pk), .s_ex(s_ex), .t_flt(t_flt));
    ot_s81_hc_crootr_r `OT_HCR_P u_r (.sk(sk_leaf[2]), .srs(srs), .ch_rv(ch_rv), .ch_rd(ch_rd), .t_v(t_v), .t_pk(t_pk),
        .t_flt(t_flt), .s_rv(s_rv), .s_rd(s_rd));
    ot_s81_hc_crootr_w `OT_HCR_P u_w (.sk(sk_leaf[3]), .srs(srs), .s_w(s_w), .p_w(p_w), .p_flt(p_flt), .s_flt(s_flt));
 `undef OT_HCR_P
endmodule


`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_crooty (s81-suhc-hier-1011, 2026-10-11): the N half of a split outer column root (structural variant of
// ot_s81_hc_croot, dsfd_sp_hc CSPLIT=1): 575.992 x 200, beside the centre pin tile.  It owns the slab pins over its
// third of the face -- chain C's y slice and four VM write slots -- and the y slice FIFO.  Below it, ot_s81_hc_crootr
// (the chain root) asks for each POST beat's slice (p_req) and gets it back registered (p_y) three cycles later; the
// write slots come down from it (p_w) into pin flops.  Every crossing registered both sides.
// v3 (2026-10-12, [hc-crooty]): split into two hard tiles, each with its own clock root and reset relay -- v2's one
// root over ~18.4k flops + 11 SRAM macros (575.992 x 300.24) never converged hold.  ot_s81_hc_crooty_y (far side, above
// crootr's forward column): y_s -> yp -> yp2 -> SRAM FIFO -> p_y, p_req, yacc, p_flt (~14.1k flops + 11 macros);
// ot_s81_hc_crooty_w (comb side, above crootr's T_wr): p_w -> w_c -> wq_* (~4.3k flops).  The two paths share nothing
// but sk/srs, so the cut is cycle-neutral; this wrapper is wires only and keeps the v2 port list.
// v7 (2026-10-13, [s81hc-1013 r8]): YLEAF 1 (production): the y path is LC identical hard slice leaves ot_s81_hc_cryys
// (one per GS * 32 = 256-bit slice, each with its own clock root, reset relay and copy of the FIFO control; the store
// is 16 x 256 flops, no SRAM), wired here (ot_s81_hc_crooty_yl, wires only).  ot_s81_hc_crooty_y with its 11 SRAM
// macros failed global route six times in its 369.36-um slot (macro data pins on the vertical macro edges: every bit
// turns through a 20-um channel, cut 0.95-1.46 of the channel tracks); it stays as the lockstep reference (YLEAF 0).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crooty_roots #(
    parameter integer FIFO_SLICE = 256,
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, C = 0, YD = 16,
    parameter integer YLEAF = 1
) (
    input  wire                 sk,
    input wire [LC:0] sk_leaf,
    input  wire                 srs,
    input  wire [YS-1:0]        y_s,
    output wire [3:0]           wq_v,
    output wire [4*14-1:0]      wq_row,
    output wire [4*16-1:0]      wq_mask,
    output wire [4*512-1:0]     wq_d,
    input  wire                 yacc,
    input  wire [LC-1:0]        p_req,                    // one copy per y slice leaf (crootr_f pin flops)
    input  wire [4*WSL-1:0]     p_w,
    output wire [YS-1:0]        p_y,
    output wire                 p_flt
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer YS = LC * GS * 32;
    localparam integer WSL = 1 + 14 + 16 + 512;                  // a write slot {v, row, mask, d}
    generate if (YLEAF != 0) begin : g_yl
        ot_s81_hc_crooty_yl_roots #(.NG(NG), .NCOL(NCOL), .GS(GS), .C(C), .YD(YD)) u_y (.sk_leaf(sk_leaf[LC:1]),.sk(sk), .srs(srs),
            .y_s(y_s), .yacc(yacc), .p_req(p_req), .p_y(p_y), .p_flt(p_flt));
    end else begin : g_ym
        ot_s81_hc_crooty_y #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .C(C), .YD(YD), .FIFO_SLICE(FIFO_SLICE)) u_y (.sk(sk), .srs(srs),
            .y_s(y_s), .yacc(yacc), .p_req(p_req[0]), .p_y(p_y), .p_flt(p_flt));
    end endgenerate
    ot_s81_hc_crooty_w #(.NG(NG), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .C(C), .YD(YD)) u_w (.sk(sk_leaf[0]), .srs(srs),
        .p_w(p_w), .wq_v(wq_v), .wq_row(wq_row), .wq_mask(wq_mask), .wq_d(wq_d));
    initial if(YLEAF!=1 || NG!=256 || GS!=8 || (C!=0 && C!=2))
        $fatal(1,"outer root requires actual eleven Y leaves and writer");
endmodule


module ot_s81_hc_crooty_yl_roots #(
    parameter integer NG = 256, NCOL = 3, GS = 8, C = 0, YD = 16
) (
    input  wire                 sk,
    input wire [LC-1:0] sk_leaf,
    input  wire                 srs,
    input  wire [YS-1:0]        y_s,
    input  wire                 yacc,
    input  wire [LC-1:0]        p_req,                    // leaf f takes p_req[f]
    output wire [YS-1:0]        p_y,
    output wire                 p_flt
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L0 = NP, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, L2 = NP;
    localparam integer LC = (C == 0) ? L0 : (C == 1) ? L1 : L2;
    localparam integer SW = GS * 32;
    localparam integer YS = LC * SW;
    wire [LC-1:0] flt;
    genvar f;
    generate for (f = 0; f < LC; f = f + 1) begin : g_f
`ifdef OT_S81_HC_CRYYS_HARD
        if (SW != 256 || YD != 16) begin : g_bad initial $fatal(1, "ot_s81_hc_cryys hard view is W 256 / YD 16"); end
        ot_s81_hc_cryys u_s (.sk(sk_leaf[f]), .srs(srs), .y_s(y_s[f*SW +: SW]), .yacc(yacc), .p_req(p_req[f]),
            .p_y(p_y[f*SW +: SW]), .p_flt(flt[f]));
`else
        ot_s81_hc_cryys #(.W(SW), .YD(YD)) u_s (.sk(sk_leaf[f]), .srs(srs), .y_s(y_s[f*SW +: SW]), .yacc(yacc), .p_req(p_req[f]),
            .p_y(p_y[f*SW +: SW]), .p_flt(flt[f]));
`endif
    end endgenerate
    assign p_flt = flt[0];                        // every leaf holds the same occupancy state
endmodule

