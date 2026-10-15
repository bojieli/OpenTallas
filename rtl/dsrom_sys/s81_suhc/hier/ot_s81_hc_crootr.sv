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
module ot_s81_hc_crootr #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 5, RT = 1, RW = 1
) (
    input  wire                 sk,
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
    ot_s81_hc_crootr_f `OT_HCR_P u_f (.sk(sk), .srs(srs), .f_fv(f_fv), .f_fd(f_fd), .p_req(p_req), .p_y(p_y),
        .ch_rst(ch_rst), .ch_fv(ch_fv), .ch_fd(ch_fd));
    ot_s81_hc_crootr_t `OT_HCR_P u_t (.sk(sk), .srs(srs), .s_fv(s_fv), .s_fd(s_fd), .f_fv(f_fv), .f_fd(f_fd),
        .t_v(t_v), .t_pk(t_pk), .s_ex(s_ex), .t_flt(t_flt));
    ot_s81_hc_crootr_r `OT_HCR_P u_r (.sk(sk), .srs(srs), .ch_rv(ch_rv), .ch_rd(ch_rd), .t_v(t_v), .t_pk(t_pk),
        .t_flt(t_flt), .s_rv(s_rv), .s_rd(s_rd));
    ot_s81_hc_crootr_w `OT_HCR_P u_w (.sk(sk), .srs(srs), .s_w(s_w), .p_w(p_w), .p_flt(p_flt), .s_flt(s_flt));
 `undef OT_HCR_P
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// T_fwd: far-face column, full height.  f_fv/f_fd (T_tree's seam capture) -> RF relays -> ch_fv/ch_fd (S face); the y
// slice: p_y pin flop (N rows) -> RF-4 relays (mid-height) -> joins the data field at a POST beat in the chain output flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crootr_f #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 5, RT = 1, RW = 1,
    parameter integer PQ = 1,                             // 1 pin-register form (routed); 0 the v2 form (lockstep reference)
    parameter integer NPR = 16                            // PQ 1: kept replicas of the POST select (pop) at the chain output flop
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [FVW-1:0]       f_fv,
    input  wire [FSW-1:0]       f_fd,
    (* keep = "true" *) output reg [LC-1:0] p_req,        // LC pin flops, copy k at the p_req pin of y slice leaf k
    input  wire [YS-1:0]        p_y,
    output wire                 ch_rst,
    output reg  [FVW-1:0]       ch_fv,
    output reg  [FDW-1:0]       ch_fd
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
    reg [1:0] rr;
    always @(posedge sk) rr <= {rr[0], srs};
    wire rs_n = rr[1];                                   // tile-local reset relay: no flop of the tile sees the srs pin
    assign ch_rst = rr[1];
`ifndef SYNTHESIS
    initial if (PQ != 0 && RF < 5) $fatal(1, "ot_s81_hc_crootr_f: PQ 1 needs RF >= 5 (request pin flop + y pin flop + RF-5 relays)");
`endif
    reg  [YS-1:0] ydq;
    always @(posedge sk) ydq <= p_y;                              // y pin flop (N face)
    wire [YS-1:0] yr;
    ot_hdc_delay #(.W(YS), .D(RF - 4 - (PQ != 0 ? 1 : 0))) u_ry (.clk(sk), .rst_n(rs_n), .d(ydq), .q(yr));   // y relay(s); none at PQ 1 / RF 5
    wire [FVW-1:0] fv_1, fv_r;
    wire [FSW-1:0] fd_r;
    ot_hdc_delay #(.W(FVW), .D(1), .RESET(1)) u_rfv0 (.clk(sk), .rst_n(rs_n), .d(f_fv), .q(fv_1));          // W-face capture
    ot_hdc_delay #(.W(FSW), .D(RF)) u_rfd (.clk(sk), .rst_n(rs_n), .d(f_fd), .q(fd_r));
    // v5 (2026-10-14, s81-elemB): the POST select fanned out from ONE line flop to the FDD-bit chain output mux across the
    // 276-um S face (routed v4: SS -325 ps u_rfv.line -> ch_fd).  At PQ 1 the last fv relay stage also writes NPR kept
    // copies of the select bit (same cycle, same reset); copy k selects the k-th contiguous FDD/NPR slice of ch_fd.
    localparam integer NPQ = (PQ != 0) ? NPR : 1;
    wire [NPQ-1:0] popv;
    generate
        if (PQ != 0) begin : g_popr
            wire [FVW-1:0] fv_m;
            ot_hdc_delay #(.W(FVW), .D(RF - 2), .RESET(1)) u_rfv (.clk(sk), .rst_n(rs_n), .d(fv_1), .q(fv_m));
            reg [FVW-1:0] fv_l;
            (* keep = "true" *) reg [NPQ-1:0] popq;
            always @(posedge sk or negedge rs_n)
                if (!rs_n) begin fv_l <= {FVW{1'b0}}; popq <= {NPQ{1'b0}}; end
`ifdef OT_S81_HC_CRRF_MUT3
                else begin fv_l <= fv_m; popq <= {NPQ{fv_m[S_RD]}} & ~({{(NPQ-1){1'b0}}, 1'b1} << (NPQ - 1)); end   // negative control: last replica stuck
`else
                else begin fv_l <= fv_m; popq <= {NPQ{fv_m[S_RD]}}; end
`endif
            assign fv_r = fv_l;
            assign popv = popq;
        end else begin : g_pop1
            ot_hdc_delay #(.W(FVW), .D(RF - 1), .RESET(1)) u_rfv (.clk(sk), .rst_n(rs_n), .d(fv_1), .q(fv_r));
            assign popv = fv_r[S_RD];
        end
    endgenerate
    wire pop = fv_r[S_RD];                                        // a POST beat: the chain's y slice joins it
    wire [FDD-1:0] dsel;                                          // the chain output data field: y slice at POST, else fd
    genvar gi;
    generate
        for (gi = 0; gi < FDD; gi = gi + 1) begin : g_dsel
            wire yb = (gi < YS) ? yr[(gi < YS) ? gi : 0] : 1'b0;
            wire fb = (gi < S_RD * 512) ? fd_r[O_D + ((gi < S_RD * 512) ? gi : 0)] : 1'b0;
            assign dsel[gi] = popv[(gi * NPQ) / FDD] ? yb : fb;
        end
    endgenerate
`ifdef OT_S81_HC_CRRF_MUT1
    wire prq_d = f_fv[S_RD];                                      // negative control: the request one cycle early
`else
    wire prq_d = (PQ != 0) ? fv_1[S_RD] : f_fv[S_RD];             // PQ 1: from the W-face capture, registered at the pins
`endif
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin ch_fv <= 0; p_req <= {LC{1'b0}}; end
        else begin
            ch_fv <= fv_r;
`ifdef OT_S81_HC_CRRF_MUT2
            p_req <= {LC{prq_d}} & ~((PQ != 0 ? {{(LC-1){1'b0}}, 1'b1} : {LC{1'b0}}) << (LC / 2));   // negative control (PQ 1 only): one slice never asked
`else
            p_req <= {LC{prq_d}};                                 // the slice arrives (p_y, ydq[, yr]) RF cycles after f_fv
`endif
        end
    always @(posedge sk) begin
        ch_fd[O_D-1:0] <= fd_r[O_D-1:0];
        ch_fd[O_D +: FDD] <= dsel;
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// T_tree: middle of the comb-side column.  The chain's subtrees behind their own packet capture (t_pk from T_ret's rd_c:
// this capture is the v1 ex relay moved in front of the tree), RT-1 relays, the s_ex send flop (comb face); the comb
// forward seam capture fd_c / fv_c, sent on to T_fwd (registered feed-through).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crootr_t #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 5, RT = 1, RW = 1
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [FVW-1:0]       s_fv,
    input  wire [FSW-1:0]       s_fd,
    output reg  [FVW-1:0]       f_fv,
    output reg  [FSW-1:0]       f_fd,
    input  wire                 t_v,
    input  wire [PKW-1:0]       t_pk,
    output reg  [NEX*32-1:0]    s_ex,
    output reg                  t_flt
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
    reg [1:0] rr;
    always @(posedge sk) rr <= {rr[0], srs};
    wire rs_n = rr[1];                                   // tile-local reset relay: no flop of the tile sees the srs pin
    always @(posedge sk or negedge rs_n) if (!rs_n) f_fv <= 0; else f_fv <= s_fv;
    always @(posedge sk) f_fd <= s_fd;
    reg            v_q;
    reg  [PKW-1:0] pk_q;
    always @(posedge sk or negedge rs_n) if (!rs_n) v_q <= 1'b0; else v_q <= t_v;
    always @(posedge sk) pk_q <= t_pk;
    wire [NEX*32-1:0] ex, ex_r;
    wire              tf;
    ot_s81_hc_stree #(.NS(NS), .NP(NP), .LA(AL), .OWN(C)) u_tree (.clk(sk), .rst_n(rs_n), .v(v_q), .pk(pk_q),
        .im(32'd0), .ex(ex), .r_v(), .r(), .fault(tf));
    ot_hdc_delay #(.W(NEX * 32), .D(RT - 1)) u_rex (.clk(sk), .rst_n(rs_n), .d(ex), .q(ex_r));
    always @(posedge sk) s_ex <= ex_r;
    always @(posedge sk or negedge rs_n) if (!rs_n) t_flt <= 1'b0; else t_flt <= tf;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// T_ret: S end of the comb-side column.  ch_rv/ch_rd capture (S face) -> RT relays -> s_rv/s_rd (comb face); the packet
// slice and its valid leave north to T_tree; the tree's add fault (t_flt) joins the valid word at the send flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crootr_r #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 5, RT = 1, RW = 1
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [RVW-1:0]       ch_rv,
    input  wire [RDW-1:0]       ch_rd,
    output wire                 t_v,
    output wire [PKW-1:0]       t_pk,
    input  wire                 t_flt,
    output reg  [RVW-1:0]       s_rv,
    output reg  [RDW-1:0]       s_rd
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
    reg [1:0] rr;
    always @(posedge sk) rr <= {rr[0], srs};
    wire rs_n = rr[1];                                   // tile-local reset relay: no flop of the tile sees the srs pin
    reg  [RVW-1:0] rv_c;
    reg  [RDW-1:0] rd_c;
    always @(posedge sk or negedge rs_n) if (!rs_n) rv_c <= 0; else rv_c <= ch_rv;
    always @(posedge sk) rd_c <= ch_rd;
    assign t_v  = rv_c[S_RT];
    assign t_pk = rd_c[P_D +: PKW];
    wire [RVW-1:0] rv_r;
    wire [RDW-1:0] rd_r;
    ot_hdc_delay #(.W(RVW), .D(RT), .RESET(1)) u_rrv (.clk(sk), .rst_n(rs_n), .d(rv_c), .q(rv_r));
    ot_hdc_delay #(.W(RDW), .D(RT)) u_rrd (.clk(sk), .rst_n(rs_n), .d(rd_c), .q(rd_r));
    always @(posedge sk or negedge rs_n)
        if (!rs_n) s_rv <= 0;
        else s_rv <= {rv_r[RVW-1], rv_r[RVW-2] | t_flt, rv_r[RVW-3:0]};       // tree add faults join the chain's
    always @(posedge sk) s_rd <= rd_r;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// T_wr: N end of the comb-side column.  s_w capture (comb face) -> RW relays -> p_w pin-tile flops (N face); p_flt -> s_flt.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_crootr_w #(
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, AL = 4, C = 0,
    parameter integer RF = 5, RT = 1, RW = 1
) (
    input  wire                 sk,
    input  wire                 srs,
    input  wire [4*WSL-1:0]     s_w,
    output reg  [4*WSL-1:0]     p_w,
    input  wire                 p_flt,
    output reg                  s_flt
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
    reg [1:0] rr;
    always @(posedge sk) rr <= {rr[0], srs};
    wire rs_n = rr[1];                                   // tile-local reset relay: no flop of the tile sees the srs pin
    reg pfl;
    always @(posedge sk or negedge rs_n) if (!rs_n) begin pfl <= 1'b0; s_flt <= 1'b0; end else begin pfl <= p_flt; s_flt <= pfl; end
    reg  [4*WSL-1:0] w_c;
    always @(posedge sk) w_c <= s_w;
    wire [4*WSL-1:0] w_r;
    ot_hdc_delay #(.W(4 * WSL), .D(RW)) u_rw (.clk(sk), .rst_n(rs_n), .d(w_c), .q(w_r));
    always @(posedge sk) p_w <= w_r;
endmodule
