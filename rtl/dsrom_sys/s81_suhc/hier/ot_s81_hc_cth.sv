`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cth (el1011-s81hc-ctile, 2026-10-12): the HALF = 1 column sub-tile of the HC slab (dsfd_sp_hc HIER=2),
// split into hard tiles of <= ~15k clock sinks each.  Cycle-for-cycle the same pins and bus timing as
// ot_s81_hc_ctile #(.HALF(1)) (that module's header holds the protocol); this file only moves the logic:
//   ctfn / ctfs  forward bus, N / S strips: ctfn = reset relay, fv / fd pin flops, y-shift register; ctfs = RLY - 1
//         relays + out flops (the cross-slot stage fdm -> relay is wire only, so no flop-to-flop wire > ~500 um);
//         ctfx (centre band) duplicates the fv / fd control + slot-data pin flops as the slot-wide broadcast (fv, fdx),
//         so ctfn's faces carry only the through bus.  Reset: ctfn's first rst stage (rst_c) is relayed to every tile,
//         which adds one flop (same 2-cycle rst_in -> rst_n latency; no slot-long single-cycle reset net).
//   ctnl  x16, one per norm lane (bank j = h row % 4, group l): the lane's slice of the bank's resident h rows
//         (group l, 2 slots x NV), its gain words, hc_pre mix -> square, x wait line, scale, y, and chain adder l of the
//         bank's chunk chain (+ the HALF carry at lane 0); registered zero-gated read ports for hc_post (hpr) and the
//         return's h rows (hrq, read one stage ahead).  bank / lane / tid / last are strap PINS captured in flops: one
//         hardened master serves all 16 lanes of every sub-tile; no strap fans out.
//   ctpl  x8, hc_post group g output lanes {2h, 2h+1} (ot_dsrom_su_hcpost sliced) + its coefficient words and the
//         write-back counters; in_r = OR of the 4 banks' zero-gated group-g reads.
//   ctra / ctrb (ot_s81_hc_ctrs split by return slots, centre band) / ctrn  return bus (ctrn = RLY - 2 relays + out flops, rdm -> ctrn wire only): rv / rd pin flops, a stage for the far tile's originated slots, the merge stage (y rows from
//         ybuf, partial packet from psb, h rows from the banks' hrq), out flops.  The merge sits one stage later than
//         in ot_s81_hc_ctile and the relay one stage earlier (needs RLY >= 2): same 2 + RLY registers a hop, and every
//         merged source is one register later (faults / hc_post flags registered at their tile), so rv / rd are
//         cycle-identical.
// Every signal crossing between these tiles leaves a flop.  ctq: the norm/scale timing sequencer, replicated in ctn
// and ctr (a few hundred flops each) instead of a cross-tile strobe tree.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cth #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer RLY = 2, CNL_PIN = 0, CHAIN_STEP = AL, LANE_SPECIALIZE = 0
) (
    input  wire                       clk,
    input  wire                       rst_in,
    output wire                       rst_out,
    input  wire [7:0]                 tid,
    input  wire                       last,
    input  wire [S_RD+4:0]            fv_in,
    input  wire [FDW-1:0]             fd_in,
    output wire [S_RD+4:0]            fv_out,
    output wire [FDW-1:0]             fd_out,
    input  wire [S_RT+3:0]            rv_in,
    input  wire [RDW-1:0]             rd_in,
    output wire [S_RT+3:0]            rv_out,
    output wire [RDW-1:0]             rd_out,
    output wire [127:0]               cy_out,
    input  wire [127:0]               cy_in
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    localparam integer RDW = S_RT + 8 * S_RT + 16 * S_RT + 8 + 512 * S_RT;
`ifndef SYNTHESIS
    initial if (LANE_SPECIALIZE && !CNL_PIN) $fatal(1,"cth LANE_SPECIALIZE requires CNL_PIN");
    initial if (RLY < 2 || GS != 8) $fatal(1, "ot_s81_hc_cth: RLY >= 2 (the return merge takes a relay stage), GS 8");
`endif

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [S_RD+4:0] fv;
    wire [FXW-1:0]  fdx;
    wire [S_RD+4:0] fv_local;
    wire [FXW-1:0] fdx_local;
    wire [S_RD+4:0] fvm;
    wire [FDW-1:0]  fdm;
    wire            rst_c;                     // ctfn's first reset stage -> one relay flop in every tile
    ot_s81_hc_ctfn #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD)) u_fn (
        .clk(clk), .rst_in(rst_in), .rst_c(rst_c), .fv_in(fv_in), .fd_in(fd_in), .fvm(fvm), .fdm(fdm));
    generate if (CNL_PIN) begin : g_captured_broadcast
        ot_s81_hc_ctfx_cap #(.S_RD(S_RD)) u_fx (
            .clk(clk), .rst_in(rst_c), .fv_in(fv_in), .fd_in(fd_in[FXW-1:0]), .fv(fv), .fdx(fdx),
            .fv_local(fv_local), .fdx_local(fdx_local));
    end else begin : g_legacy_broadcast
    ot_s81_hc_ctfx #(.S_RD(S_RD)) u_fx (
        .clk(clk), .rst_in(rst_c), .fv_in(fv_in), .fd_in(fd_in[FXW-1:0]), .fv(fv), .fdx(fdx));
        assign fv_local = fv;
        assign fdx_local = fdx;
    end endgenerate
    ot_s81_hc_ctfs #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .RLY(RLY)) u_fs (
        .clk(clk), .rst_in(rst_c), .rst_out(rst_out), .fvm(fvm), .fdm(fdm), .fv_out(fv_out), .fd_out(fd_out));
    wire [16*S_RT-1:0]  rq_q;
    wire                hs_run;
    wire [15:0]         hs_c;
    // One physical source per horizontal CTNL column, same registered epoch.
    wire [16*S_RT-1:0] rq_col [0:3];
    wire [3:0] hs_run_col;
    wire [15:0] hs_c_col [0:3];
    assign rq_col[0] = rq_q;
    assign hs_run_col[0] = hs_run;
    assign hs_c_col[0] = hs_c;
    wire [16*64-1:0]    hpr;                       // lane tile n = 4 bank + group
    wire [16*64*S_RT-1:0] hrq;
    wire [16*16-1:0]    yb;
    wire [16*32-1:0]    sq, acc, cyo;
    wire [15:0]         nflt;
    wire [7:0]          hov, pwb, phs, hnz_d, pflt_d, hov_d;
    wire [8*16-1:0]     pob;
    wire [8*32-1:0]     hpo;                       // lane-pair tile m = 2 group + half
    genvar j, l, m;
    generate for (j = 0; j < 4; j = j + 1) begin : g_b
        for (l = 0; l < 4; l = l + 1) begin : g_l
            localparam integer n = 4 * j + l;
            if (!LANE_SPECIALIZE) begin : g_dynamic_lane
            ot_s81_hc_ctnl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fdx),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
            end else begin : g_fixed_lane
                localparam integer P_BITS=lane_payload_width(l);
                wire [O_D+S_RD*P_BITS-1:0] fd_lane;
                assign fd_lane[O_D-1:0]=fdx[O_D-1:0];
                for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
                    for(genvar pb=0;pb<P_BITS;pb=pb+1) begin : g_payload
                        localparam integer RAW_BIT=lane_payload_index(l,pb);
                        assign fd_lane[O_D+rp*P_BITS+pb]=fdx[O_D+rp*512+RAW_BIT];
                    end
                end
                if (l==0) begin : g_l0
            ot_s81_hc_ctnl_l0 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==1) begin : g_l1
            ot_s81_hc_ctnl_l1 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==2) begin : g_l2
            ot_s81_hc_ctnl_l2 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
                else if (l==3) begin : g_l3
            ot_s81_hc_ctnl_l3 #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .RLY(RLY), .PIN_STAGE(CNL_PIN), .CHAIN_STEP(CHAIN_STEP)) u_n (
                .clk(clk), .rst_in(rst_c), .tid(tid), .bank(j[1:0]), .lane(l[1:0]), .last(last), .fv(fv), .fdx(fd_lane),
                .wb_v(hov[2 * l]), .wb_en(pwb[2 * l]), .wb_hs(phs[2 * l]), .wb_ob(pob[16 * (2 * l) +: 16]),
                .wb_d(hpo[64 * l +: 64]), .rq_q(rq_col[l]), .hs_run(hs_run_col[l]), .hs_c(hs_c_col[l]),
                .hpr(hpr[64 * n +: 64]), .hrq(hrq[64 * S_RT * n +: 64 * S_RT]),
                .cy_in(cy_in[32 * j +: 32]), .acc_in(l == 0 ? 32'd0 : acc[32 * (n > 0 ? n - 1 : 0) +: 32]),
                .sqn_in(l == 3 ? 32'd0 : sq[32 * (n < 15 ? n + 1 : 15) +: 32]),
                .sq_out(sq[32 * n +: 32]), .acc_out(acc[32 * n +: 32]), .cy_out(cyo[32 * n +: 32]),
                .yb(yb[16 * n +: 16]), .flt(nflt[n]));
                end
            end
        end
        assign cy_out[32 * j +: 32] = cyo[32 * (4 * j + 2) +: 32];
    end endgenerate
    generate for (m = 0; m < 8; m = m + 1) begin : g_p
        ot_s81_hc_ctpl #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .WIN(WIN), .WOUT(WOUT), .ML(ML), .AL(AL), .PIN_STAGE(1)) u_p (
            .clk(clk), .rst_in(rst_c), .grp(m[2:1]), .half(m[0]), .fv(fv_local), .fdx(fdx_local),
            .hpr({hpr[64 * (12 + m / 2) +: 64], hpr[64 * (8 + m / 2) +: 64], hpr[64 * (4 + m / 2) +: 64], hpr[64 * (m / 2) +: 64]}),
            .hov(hov[m]), .pwb(pwb[m]), .phs(phs[m]), .pob(pob[16 * m +: 16]), .hpo(hpo[32 * m +: 32]),
            .hov_d(hov_d[m]), .hnz_d(hnz_d[m]), .pflt_d(pflt_d[m]));
    end endgenerate
    wire [4*32-1:0] cs = {acc[32 * 15 +: 32], acc[32 * 11 +: 32], acc[32 * 7 +: 32], acc[32 * 3 +: 32]};
    wire [S_RT+3:0] rvm;
    wire [RDW-1:0]  rdm;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, WA = P_D + 512 * SH;
    wire [8*64*SH-1:0] hqa_n, hqa_s, hqb_n, hqb_s;
    genvar q;
    generate for (j = 0; j < 8; j = j + 1) begin : g_hq
        for (q = 0; q < SH; q = q + 1) begin : g_s
            assign hqa_n[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * j + 64 * q +: 64];
            assign hqa_s[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * (j + 8) + 64 * q +: 64];
            assign hqb_n[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * j + 64 * (q + SH) +: 64];
            assign hqb_s[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * (j + 8) + 64 * (q + SH) +: 64];
        end
    end endgenerate
    ot_s81_hc_ctra #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(CNL_PIN)) u_ra (
        .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local[O_D-1:0]), .rv_in(rv_in),
        .rd_in(rd_in[WA-1:0]), .rvm(rvm), .rdm(rdm[WA-1:0]), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c),
        .rq_q_c1(rq_col[1]), .rq_q_c2(rq_col[2]), .rq_q_c3(rq_col[3]),
        .hs_run_c1(hs_run_col[1]), .hs_run_c2(hs_run_col[2]), .hs_run_c3(hs_run_col[3]),
        .hs_c_c1(hs_c_col[1]), .hs_c_c2(hs_c_col[2]), .hs_c_c3(hs_c_col[3]),
        .hrq_n(hqa_n), .hrq_s(hqa_s), .yb_n(yb[0 +: 128]), .yb_s(yb[128 +: 128]), .cs(cs),
        .nflt_n(nflt[7:0]), .nflt_s(nflt[15:8]), .hov_d(hov_d[0]),
        .hnz_n({hnz_d[6], hnz_d[4], hnz_d[2], hnz_d[0]}), .hnz_s({hnz_d[7], hnz_d[5], hnz_d[3], hnz_d[1]}),
        .pflt_n({pflt_d[6], pflt_d[4], pflt_d[2], pflt_d[0]}), .pflt_s({pflt_d[7], pflt_d[5], pflt_d[3], pflt_d[1]}));
    ot_s81_hc_ctrb #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(CNL_PIN)) u_rb (
        .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local[O_D-1:0]), .rv_in(rv_in),
        .rdh_in(rd_in[P_D-1:0]), .rdd_in(rd_in[RDW-1 -: 512 * SH + 128]), .rdm(rdm[RDW-1 -: 512 * SH]),
        .hrq_n(hqb_n), .hrq_s(hqb_s), .yb_n(yb[0 +: 128]), .yb_s(yb[128 +: 128]));
    ot_s81_hc_ctrn #(.S_RT(S_RT), .RDW(RDW), .RLY(RLY)) u_rn (
        .clk(clk), .rst_in(rst_c), .rvm(rvm), .rdm(rdm), .rv_out(rv_out), .rd_out(rd_out));
endmodule

// ------------------------------------------------------------------------------------------------ forward bus tiles
// ctfn (N strip): reset relay, fv / fd pin flops, y-shift register fdm; exports the pin flops (fv, fdx) to the slot.
// ctfs (S strip): the RLY - 1 relay stages and the out flops.  fdm -> relay is the one cross-slot stage (wire only, no
// logic between the two flops); fd_out at the S face abuts the next slot's N face.  Same registers as the single
// strip (ot_s81_hc_ctile: pin, y-shift, RLY - 1 relays, out), now spread N -> S.
module ot_s81_hc_ctfn #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FDW-1:0]     fd_in,
    output wire               rst_c,                 // first reset stage, relayed to every tile of the slot
    output reg  [S_RD+4:0]    fvm,
    output reg  [FDW-1:0]     fdm
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32, GT = GS / 2;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    assign rst_c = rr[0];
    reg [S_RD+4:0] fv;
    reg [FDW-1:0]  fd;
    // the y-beat select drives every y-field bit of fdm (~2.8k muxes across the 576 um strip): NYR replicated pin flops
    // of fv[S_RD], one per y-field slice (same input pin, same cycle), instead of one flop with > 5k loads
    localparam integer NYR = 16, YSL = (YW + NYR - 1) / NYR;
    (* keep *) reg [NYR-1:0] ysel;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; fvm <= 0; ysel <= 0; end
        else begin fv <= fv_in; fvm <= fv; ysel <= {NYR{fv_in[S_RD]}}; end
    wire [YW-1:0] ysh = fd[O_D +: YW] >> (GT * 32);                        // y beat: next tile's slice to 0
    integer yb;
    always @(posedge clk) begin
        fd <= fd_in;
        fdm <= fd;
        for (yb = 0; yb < YW; yb = yb + 1)
            if (ysel[yb / YSL]) fdm[O_D + yb] <= ysh[yb];
    end
endmodule

// ctfx (centre band): duplicate fv / fd control + slot-data pin flops, the slot-wide broadcast source (fv, fdx) for
// ctnl / ctpl / ctrs.  Same input pins, same cycle as ctfn's pin flops (fd_in fans to both at the die): ctfn's N face
// keeps only the through bus (fd_in in, fvm / fdm out S), so no face carries > ~3k pins.
module ot_s81_hc_ctfx #(
    parameter integer S_RD = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FXW-1:0]     fd_in,
    output reg  [S_RD+4:0]    fv,
    output reg  [FXW-1:0]     fdx
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    reg rr;
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    always @(posedge clk or negedge rst_n) if (!rst_n) fv <= 0; else fv <= fv_in;
    always @(posedge clk) fdx <= fd_in;
endmodule

// Serial production broadcast owns both first-stage and local-epoch capture registers.
// The original ot_s81_hc_ctfx remains the CNL_PIN=0 master; this is a distinct physical leaf.
module ot_s81_hc_ctfx_cap #(parameter integer S_RD = 2) (
    input wire clk,
    input wire rst_in,
    input wire [S_RD+4:0] fv_in,
    input wire [FXW-1:0] fd_in,
    output reg [S_RD+4:0] fv,
    output reg [FXW-1:0] fdx,
    output reg [S_RD+4:0] fv_local,
    output reg [FXW-1:0] fdx_local
);
    localparam integer O_D = 5 + S_RD*16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD*512;
    reg rr;
    always @(posedge clk) rr <= rst_in;
    always @(posedge clk or negedge rr) if (!rr) fv <= 0; else fv <= fv_in;
    always @(posedge clk) fdx <= fd_in;
    // Match the former region register's reset epoch exactly: incoming rst_c, not rr.
    always @(posedge clk or negedge rst_in) if (!rst_in) fv_local <= 0; else fv_local <= fv;
    always @(posedge clk) fdx_local <= fdx;
endmodule

module ot_s81_hc_ctfs #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, RLY = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    output wire               rst_out,
    input  wire [S_RD+4:0]    fvm,
    input  wire [FDW-1:0]     fdm,
    output reg  [S_RD+4:0]    fv_out,
    output reg  [FDW-1:0]     fd_out
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD;
    reg rr;                                              // regional reset relay: rst_in = ctfn's first stage
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    assign rst_out = rr;
    wire [S_RD+4:0] fvm_d;
    wire [FDW-1:0]  fdm_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fv_out <= 0;
        else fv_out <= fvm_d;
    always @(posedge clk) fd_out <= fdm_d;
    ot_hdc_delay #(.W(S_RD + 5), .D(RLY - 1), .RESET(1)) u_fvr (.clk(clk), .rst_n(rst_n), .d(fvm), .q(fvm_d));
    ot_hdc_delay #(.W(FDW), .D(RLY - 1)) u_fdr (.clk(clk), .rst_n(rst_n), .d(fdm), .q(fdm_d));
endmodule

// ------------------------------------------------------------------------------------------------ norm/scale sequencer
module ot_s81_hc_ctq #(
    parameter integer NG = 256, D = 5120, S_RD = 2, ML = 5, AL = 4, CHAIN_STEP = AL
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [S_RD+4:0] fv,
    input  wire [FXW-1:0]  fdx,
    output reg             n_hs, n_cs,
    output reg  [1:0]      n_gs,
    output reg             mx_v,
    output wire            x_v,
    output wire [7:0]      xi,
    output wire [ML+7*CHAIN_STEP:0] vs,
    output wire [7:0]      si,
    output reg  [31:0]     rh,
    output reg  [7:0]      sc_i,
    output reg             b_v,
    output wire [2*ML+1:0] vy,
    output wire [7:0]      wi,
    output wire [7:0]      yi
);
    localparam integer O_NG = 5 + S_RD * 16 + 20, O_NV = O_NG + 6, O_R = O_NV + 8, O_D = O_R + 32 + 1;
    localparam integer FXW = O_D + S_RD * 512;
    localparam integer N = 4 * NG, NV = D / N, LM = ML, LA = AL;
    localparam integer DM = LM + 3 * LA + 1, DS = LM + 7 * CHAIN_STEP, DY = 2 * LM + 1;
    // vector indices are < NV (5 at NG 256): the wait lines carry IW bits, not 8 (the root never sends nv_i >= NV)
    localparam integer IW = (NV > 1) ? $clog2(NV) : 1;
    wire ng_v = fv[S_RD+1], nv_v = fv[S_RD+2], r_v = fv[S_RD+3];
    always @(posedge clk) if (ng_v) begin n_hs <= fdx[O_NG]; n_cs <= fdx[O_NG + 1]; n_gs <= fdx[O_NG + 2 +: 2]; end
    reg [IW-1:0] mx_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) mx_v <= 1'b0; else mx_v <= nv_v;
    always @(posedge clk) if (nv_v) mx_i <= fdx[O_NV +: IW];
    wire [DM:0] vm;
    wire [IW-1:0] xn, sn, wn, yn;
    ot_hdc_vline #(.D(DM)) u_vm (.clk(clk), .rst_n(rst_n), .v(mx_v), .vd(vm));
    ot_hdc_delay #(.W(IW), .D(DM)) u_xi (.clk(clk), .rst_n(rst_n), .d(mx_i), .q(xn));
    assign x_v = vm[DM];
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rst_n), .v(x_v), .vd(vs));
    ot_hdc_delay #(.W(IW), .D(DS)) u_si (.clk(clk), .rst_n(rst_n), .d(xn), .q(sn));
    reg          sc_run;
    reg [IW-1:0] sc;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sc_run <= 1'b0; sc <= 0; end
        else if (r_v) begin sc_run <= 1'b1; sc <= 0; end
        else if (sc_run) begin if (sc == NV - 1) sc_run <= 1'b0; sc <= sc + 1'b1; end
    always @(*) sc_i = {{(8 - IW){1'b0}}, sc};
    always @(posedge clk) if (r_v) rh <= fdx[O_R +: 32];
    always @(posedge clk or negedge rst_n) if (!rst_n) b_v <= 1'b0; else b_v <= sc_run;
    ot_hdc_vline #(.D(DY)) u_vy (.clk(clk), .rst_n(rst_n), .v(b_v), .vd(vy));
    ot_hdc_delay #(.W(IW), .D(LM)) u_wi (.clk(clk), .rst_n(rst_n), .d(sc), .q(wn));
    reg [IW-1:0] bi;
    always @(posedge clk) bi <= sc;
    ot_hdc_delay #(.W(IW), .D(DY)) u_yi (.clk(clk), .rst_n(rst_n), .d(bi), .q(yn));
    assign xi = {{(8 - IW){1'b0}}, xn};
    assign si = {{(8 - IW){1'b0}}, sn};
    assign wi = {{(8 - IW){1'b0}}, wn};
    assign yi = {{(8 - IW){1'b0}}, yn};
endmodule

// ------------------------------------------------------------------------------------------------ norm lane tile
// One norm lane (bank bq, lane lq of the half-octet: slab lane bq * 4 + lq) = adder position lq of the bank's chunk
// chain.  Holds the lane's slice of the bank's resident h rows (group lq: 4 copies BF16 x 2 slots x NV), its gain
// words, mix -> square, x wait line, scale, y.  Chain (ot_s81_hc_ctile g_half): adder kk = lq; near half: operand
// = next lane's square (sqn_in, delayed LA kk), fires vs[LM + LA kk] (lane 3 idle); far half: operand = own square
// delayed LA (kk + 3), fires vs[LM + LA (kk + 3)]; acc[0] = (far ? carry : own square) at lane 0, else acc_in.
// Straps bank / lane / tid / last are pins captured in flops: one master for all 16 lanes of every sub-tile.
module ot_s81_hc_ctnl #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2, PIN_STAGE = 0, CHAIN_STEP = AL, FIXED_LANE = -1
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer GT = GS / 2, N = 4 * NG, NV = D / N, PPR = NG / 8, LM = ML, LA = AL;
    localparam integer DS = LM + 7 * CHAIN_STEP, DY = 2 * LM + 1;

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    function automatic [31:0] bf16(input [31:0] x);
        reg [32:0] s;
        begin s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]}; bf16 = {s[31:16], 16'd0}; end
    endfunction
    reg rr;                                              // regional reset relay: rst_in = ctfn's first stage
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    // Every dynamic command boundary is captured as a coherent transaction.
    wire [S_RD+4:0] fvq;
    wire [FXW-1:0] fdxq;
    wire wb_vq, wb_enq, wb_hsq, hs_runq;
    wire [15:0] wb_obq, hs_cq;
    wire [63:0] wb_dq;
    wire [16*S_RT-1:0] rq_qq;
    generate if (PIN_STAGE) begin : g_pin
        reg [S_RD+4:0] v;
        wire [FXW-1:0] d;
        for(genvar fb=0;fb<FXW;fb=fb+1) begin : g_fd
            if(FIXED_LANE<0 || fb<O_D || lane_payload_needed(FIXED_LANE,(fb-O_D)%512)) begin : g_capture
                reg q;
                always @(posedge clk) q<=fdx[fb];
                assign d[fb]=q;
            end else begin : g_unused
                assign d[fb]=1'b0;
            end
        end
        reg wv;
        reg [81:0] w;
        reg [16*S_RT+16:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin v <= 0; wv <= 0; end
            else begin v <= fv; wv <= wb_v; end
        end
        always @(posedge clk) begin
            w <= {wb_en,wb_hs,wb_ob,wb_d};
            r <= {rq_q,hs_run,hs_c};
        end
        assign fvq=v; assign fdxq=d;
        assign wb_vq=wv;
        assign {wb_enq,wb_hsq,wb_obq,wb_dq}=w;
        assign {rq_qq,hs_runq,hs_cq}=r;
    end else begin : g_nopin
        assign fvq=fv; assign fdxq=fdx;
        assign {wb_vq,wb_enq,wb_hsq,wb_obq,wb_dq}={wb_v,wb_en,wb_hs,wb_ob,wb_d};
        assign {rq_qq,hs_runq,hs_cq}={rq_q,hs_run,hs_c};
    end endgenerate
    reg [7:0] tq;
    reg [1:0] bq, lq_cfg;
    wire [1:0] lq=(FIXED_LANE>=0)?2'(FIXED_LANE):lq_cfg;
    reg       laq, hs_sl, farq, l0q, l3q;
    always @(posedge clk) begin
        tq <= tid; bq <= bank; lq_cfg <= lane; laq <= last; farq <= tid[0]; l0q <= (FIXED_LANE>=0) ? (FIXED_LANE==0) : (lane==0);
        l3q <= (FIXED_LANE>=0) ? (FIXED_LANE==3) : (lane==3);
    end
    wire [S_RD-1:0] rd_v = fvq[S_RD-1:0];
    wire pb_v = fvq[S_RD], nv_v = fvq[S_RD+2], hs_v = fvq[S_RD+4];
    wire [1:0] rd_k = fdxq[O_RK +: 2];
    wire       rd_s = fdxq[O_RS];
    wire [1:0] rd_g = fdxq[O_RG +: 2];
    wire       pb_hs = fdxq[O_PB + 2];
    wire [15:0] pb_b = fdxq[O_PB + 4 +: 16];
    wire [7:0]  nv_i = fdxq[O_NV +: 8];
    always @(posedge clk) if (hs_v) hs_sl <= fdxq[O_HS];

    reg [63:0]  hb [0:2*NV-1];                           // group lq of bank bq's h rows
    reg [31:0]  gt [0:4*NV-1];                           // lane gain words
    reg [127:0] cf_pre [0:1];
    integer s, k;
    always @(posedge clk) begin
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s]) begin : one
                reg [15:0] c, g0, l0, rb, g;
                c = fdxq[O_RC + 16 * s +: 16];
                if (rd_k == 2'd0) begin
                    rb = c / PPR; g0 = c % PPR;
                    for (k = 0; k < 8; k = k + 1)
                        if (g0 * (8 / GT) + k / GT == tq && rb % 4 == bq && k % GT == lq)
                            hb[rd_s * NV + rb / 4] <= fdxq[O_D + 512 * s + 64 * k +: 64];
                end else if (rd_k == 2'd1) begin
                    l0 = (16 * c) % N;
                    g = (l0 % NG) / GT;
                    for (k = 0; k < 16; k = k + 1)
                        if (g + k / GT == tq && l0 / NG == bq && k % GT == lq)
                            gt[rd_g * NV + (16 * c) / N] <= fdxq[O_D + 512 * s + 32 * k +: 32];
                end else if (rd_k == 2'd2) begin
                    if (c != 0) cf_pre[rd_s] <= fdxq[O_D + 512 * s +: 128];
                end
            end
        if (wb_vq && wb_enq && wb_obq % 4 == bq) hb[wb_hsq * NV + wb_obq / 4] <= wb_dq;
    end
    always @(posedge clk) if (pb_v) hpr <= (pb_b % 4 == bq) ? hb[pb_hs * NV + pb_b / 4] : 64'd0;
    always @(posedge clk) begin : rdh
        reg [15:0] qx, b;
        for (s = 0; s < S_RT; s = s + 1) begin
            qx = laq ? hs_cq + s : rq_qq[16 * s +: 16];
            b = (8 * qx) / NG;
            hrq[64 * s +: 64] <= (b % 4 == bq) ? hb[hs_sl * NV + b / 4] : 64'd0;
        end
    end

    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [DY:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP)) u_q (.clk(clk), .rst_n(rst_n), .fv(fvq), .fdx(fdxq),
        .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v), .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i),
        .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    reg [63:0] mx_h;
    always @(posedge clk) if (nv_v) mx_h <= hb[n_hs * NV + nv_i];
    wire [31:0] xl, p, qq, sq;
    wire [4:0]  f;
    ot_dsrom_su_norm_mix #(.LM(LM), .LA(LA)) u_mix (.clk(clk), .rst_n(rst_n), .v(mx_v),
        .h0({mx_h[0 +: 16], 16'h0000}), .h1({mx_h[16 +: 16], 16'h0000}), .h2({mx_h[32 +: 16], 16'h0000}),
        .h3({mx_h[48 +: 16], 16'h0000}), .pre(cf_pre[n_cs]), .x(xl), .fault(f[0]));
    reg [31:0] xb [0:NV-1];
    reg [31:0] xo_r, wo_r, yr;
    always @(posedge clk) if (x_v) xb[xi] <= xl;
    always @(posedge clk) xo_r <= xb[sc_i];
    always @(posedge clk) wo_r <= gt[n_gs * NV + wi];
    ot_hdc_qmul_lat #(LM) u_sq (clk, rst_n, x_v, xl, xl, sq, f[1]);
    ot_hdc_qmul_lat #(LM) u_xr (clk, rst_n, b_v, xo_r, rh, p, f[2]);
    ot_hdc_qmul_lat #(LM) u_w  (clk, rst_n, vy[LM], wo_r, p, qq, f[3]);
    always @(posedge clk) yr <= bf16(qq);
    assign yb = yr[31:16];
    assign sq_out = sq;
    // Registered chain ingress plus the five-cut exact adder: effective step 1+5=6.
    // All raw sources share the ingress edge, including local square and octet carry.
    wire [31:0] cyd;
    reg [31:0] cyq;
    always @(posedge clk) cyq <= cy_in;
    ot_hdc_delay #(.W(32), .D(RLY)) u_cy (.clk(clk), .rst_n(rst_n), .d(cyq), .q(cyd));
    wire [31:0] aq, nq, oq, cq;
    generate if (PIN_STAGE) begin : g_chain_pin
        reg [31:0] ar,nr,orr,cr;
        always @(posedge clk) begin ar<=acc_in; nr<=sqn_in; orr<=sq; cr<=cyd; end
        assign aq=ar; assign nq=nr; assign oq=orr; assign cq=cr;
    end else begin : g_chain_nopin
        assign aq=acc_in; assign nq=sqn_in; assign oq=sq; assign cq=cyd;
    end endgenerate
    reg [31:0] dl [1:6*CHAIN_STEP];
    integer t;
    always @(posedge clk) begin
        dl[1] <= farq ? oq : nq;
        for (t=2;t<=6*CHAIN_STEP;t=t+1) dl[t]<=dl[t-1];
    end
    reg [31:0] dn,df;
    reg fire;
    always @(*) begin
        case(lq) 0:dn=nq; 1:dn=dl[CHAIN_STEP]; 2:dn=dl[2*CHAIN_STEP]; default:dn=0; endcase
        case(lq) 0:df=dl[3*CHAIN_STEP]; 1:df=dl[4*CHAIN_STEP];
                 2:df=dl[5*CHAIN_STEP]; default:df=dl[6*CHAIN_STEP]; endcase
        case(lq) 0:fire=farq ? vs[LM+3*CHAIN_STEP] : vs[LM];
                 1:fire=farq ? vs[LM+4*CHAIN_STEP] : vs[LM+CHAIN_STEP];
                 2:fire=farq ? vs[LM+5*CHAIN_STEP] : vs[LM+2*CHAIN_STEP];
                 default:fire=farq ? vs[LM+6*CHAIN_STEP] : 1'b0; endcase
    end
    wire [31:0] acc_a=l0q ? (farq ? cq : oq) : aq;
    generate if (PIN_STAGE) begin : g_chain6
        reg fire_q;
        always @(posedge clk or negedge rst_n)
            if(!rst_n) fire_q<=0; else fire_q<=fire;
        wire [1:0] err;
        wire vo;
        ot_hdc_fp32_add_f12_l5x u_a
            (.clk(clk),.rst_n(rst_n),.valid_in(fire_q),.a(acc_a),.b(farq?df:dn),
             .y(acc_out),.err(err),.valid_out(vo));
        assign f[4]=vo && (err!=0);
    end else begin : g_chain_legacy
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk,rst_n,fire,acc_a,farq?df:dn,acc_out,f[4]);
    end endgenerate
`ifndef SYNTHESIS
    initial if (FIXED_LANE>=4 || (FIXED_LANE>=0 && GS!=8)) $fatal(1,"ctnl FIXED_LANE requires0..3/GS8");
    initial if (PIN_STAGE && CHAIN_STEP != 6)
        $fatal(1,"ctnl PIN_STAGE requires CHAIN_STEP=6");
`endif
    always @(posedge clk) cy_out <= acc_out;
    always @(posedge clk or negedge rst_n) if (!rst_n) flt <= 1'b0; else flt <= |f;
endmodule

// ------------------------------------------------------------------------------------------------ hc_post lane-pair tile
// Element group gq (of the half-octet's 4), output lanes k = 2 hq, 2 hq + 1: ot_dsrom_su_hcpost sliced (the op words'
// WIN traverse + latch, the group's WIN in-wire + x register, 2 ot_dsrom_su_hcpost_lane, the WOUT out-wire), with its
// slice of the coefficient words and the write-back counters.  r: OR of the 4 banks' zero-gated group-gq reads.
module ot_s81_hc_ctpl #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, WIN = 2, WOUT = 2, ML = 5, AL = 4,
    parameter integer PIN_STAGE = 0
) (
    input  wire                clk,
    input  wire                rst_in,
    input  wire [1:0]          grp,
    input  wire                half,
    input  wire [S_RD+4:0]     fv,
    input  wire [FXW-1:0]      fdx,
    input  wire [4*64-1:0]     hpr,                  // banks 0..3, group gq
    output wire                hov,
    output reg                 pwb, phs,
    output reg  [15:0]         pob,
    output wire [31:0]         hpo,                  // its 2 outputs, BF16
    output reg                 hov_d, hnz_d, pflt_d
);
    localparam integer O_RK = 0, O_RS = 2, O_RC = 5, O_PB = O_RC + S_RD * 16, O_D = O_PB + 20 + 6 + 8 + 32 + 1;
    localparam integer FXW = O_D + S_RD * 512;
    reg rr;                                              // regional reset relay: rst_in = ctfn's first stage
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    reg [1:0] gq;
    reg       hq;
    always @(posedge clk) begin gq <= grp; hq <= half; end
    // The physical variant consumes one existing WIN relay as the pin stage.
    // No added arithmetic latency: both data and coefficient-go keep their original latch edges.
    localparam integer WPIPE = WIN - PIN_STAGE;
    wire [S_RD+4:0] fvq;
    wire [FXW-1:0] fdq;
    wire [255:0] hprq;
    generate if (PIN_STAGE) begin : g_pin
        reg [S_RD+4:0] vq;
        reg [FXW-1:0] dq;
        reg [255:0] rq;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) vq <= 0; else vq <= fv;
        always @(posedge clk) begin dq <= fdx; rq <= hpr; end
        assign fvq = vq;
        assign fdq = dq;
        assign hprq = rq;
    end else begin : g_nopin
        assign fvq = fv;
        assign fdq = fdx;
        assign hprq = hpr;
    end endgenerate
`ifndef SYNTHESIS
    initial if (PIN_STAGE && WIN < 2)
        $fatal(1, "ot_s81_hc_ctpl PIN_STAGE requires WIN >= 2");
`endif
    wire [S_RD-1:0] rd_v = fvq[S_RD-1:0];
    wire pb_v = fvq[S_RD];
    wire [1:0] rd_k = fdq[O_RK +: 2];
    wire       rd_s = fdq[O_RS];
    wire pb_go = fdq[O_PB], pb_wb = fdq[O_PB + 1], pb_hs = fdq[O_PB + 2], pb_cs = fdq[O_PB + 3];
    // coefficient words of lanes k0 = 2 hq, k0 + 1: comb c[j][k] = word 4 j + k, post[k]
    reg [8*32-1:0] cf_comb [0:1];
    reg [2*32-1:0] cf_post [0:1];
    integer s, j, e;
    generate if (!PIN_STAGE) begin : g_legacy_cf
    always @(posedge clk)
        for (s = 0; s < S_RD; s = s + 1)
            if (rd_v[s] && rd_k == 2'd2) begin
                if (fdq[O_RC + 16 * s +: 16] == 16'd0) begin
                    for (j = 0; j < 4; j = j + 1)
                        for (e = 0; e < 2; e = e + 1)
                            cf_comb[rd_s][32 * (2 * j + e) +: 32] <= hq ? fdq[O_D + 512 * s + 32 * (4 * j + 2 + e) +: 32]
                                                                         : fdq[O_D + 512 * s + 32 * (4 * j + e) +: 32];
                end else
                    cf_post[rd_s] <= hq ? fdq[O_D + 512 * s + 128 + 64 +: 64] : fdq[O_D + 512 * s + 128 +: 64];
            end
    end else begin : g_staged_cf
        // Separate row decode/half selection from the slot-bank write mux.
        // Slot writes are two cycles after the raw interface; the original no-rewrite
        // op window below remains enforced on the raw interface, before either stage.
        wire [2:0] ctl [0:S_RD-1][0:9];
        reg [255:0] cd [0:S_RD-1];
        reg [63:0] pd [0:S_RD-1];
        integer ps, pj, pe, pw;
        genvar cp, cw;
        for (cp = 0; cp < S_RD; cp = cp + 1) begin : g_cp
            for (cw = 0; cw < 10; cw = cw + 1) begin : g_cw
                // One kept control driver per 32-bit word, <=32 state-D loads.
                ot_s81_hc_ctpl_ctl_ff u_ctl (.clk(clk), .rst_n(rst_n),
                    .d({rd_s,
                        rd_v[cp] && rd_k == 2'd2 && fdq[O_RC+16*cp +: 16] != 0,
                        rd_v[cp] && rd_k == 2'd2 && fdq[O_RC+16*cp +: 16] == 0}),
                    .q(ctl[cp][cw]));
            end
        end
        always @(posedge clk) begin
            for (ps = 0; ps < S_RD; ps = ps + 1) begin
                for (pj = 0; pj < 4; pj = pj + 1)
                    for (pe = 0; pe < 2; pe = pe + 1)
                        cd[ps][32*(2*pj+pe) +: 32] <= hq
                            ? fdq[O_D+512*ps+32*(4*pj+2+pe) +: 32]
                            : fdq[O_D+512*ps+32*(4*pj+pe) +: 32];
                pd[ps] <= hq ? fdq[O_D+512*ps+192 +: 64] : fdq[O_D+512*ps+128 +: 64];
            end
            // Preserve simultaneous-write priority: higher s wins, as in the legacy loop.
            for (ps = 0; ps < S_RD; ps = ps + 1) begin
                for (pw = 0; pw < 8; pw = pw + 1)
                    if (ctl[ps][pw][0]) cf_comb[ctl[ps][pw][2]][32*pw +: 32] <= cd[ps][32*pw +: 32];
                for (pw = 0; pw < 2; pw = pw + 1)
                    if (ctl[ps][8+pw][1]) cf_post[ctl[ps][8+pw][2]][32*pw +: 32] <= pd[ps][32*pw +: 32];
            end
        end
    end endgenerate
    reg            hp_go, hp_in_v, hp_cs;
    reg [31:0]     hp_y;
    always @(posedge clk or negedge rst_n) if (!rst_n) hp_in_v <= 1'b0; else hp_in_v <= pb_v;
    always @(posedge clk) begin
        hp_go <= pb_v && pb_go;
        if (pb_v) begin
            case (gq) 2'd0: hp_y <= fdq[O_D +: 32]; 2'd1: hp_y <= fdq[O_D + 32 +: 32];
                      2'd2: hp_y <= fdq[O_D + 64 +: 32]; default: hp_y <= fdq[O_D + 96 +: 32]; endcase
            hp_cs <= pb_cs;
            if (pb_go) begin pwb <= pb_wb; phs <= pb_hs; pob <= 16'd0; end
        end
        if (hov) pob <= pob + 16'd1;
    end
    // op words (ot_dsrom_su_hcpost u_wop / c_r / p_r): in the single tile the go's comb / post words traverse the WIN
    // hub stages as 320 data bits.  Here the coefficient words are already resident in this tile, so only the go and
    // its 1-bit slot select traverse WIN; c_r / p_r latch the selected slot at the same cycle.  Identical as long as
    // the selected slot is not rewritten between the go and the latch (WIN + 1 cycles; the root double-buffers the
    // two slots, so a write targets the idle one) -- checked below in simulation.
    wire           w_v;
    wire           w_cs;
    ot_dsrom_su_hcpost_wire #(.W(1), .D(WPIPE)) u_wop (.clk(clk), .rst_n(rst_n), .v(hp_go), .d(hp_cs), .vq(w_v), .q(w_cs));
    reg [8*32-1:0] c_r;
    reg [2*32-1:0] p_r;
    always @(posedge clk) if (w_v) begin c_r <= cf_comb[w_cs]; p_r <= cf_post[w_cs]; end
`ifndef SYNTHESIS
    // the latch-time read equals the go-time read unless the selected slot is written in between
    reg [WIN:0] pend_v;
    reg [WIN:0] pend_s;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pend_v <= 0; pend_s <= 0; end
        else begin
            pend_v <= {pend_v[WIN-1:0], (fv[S_RD] && fdx[O_PB])};
            pend_s <= {pend_s[WIN-1:0], fdx[O_PB+3]};
        end
    integer ck;
    always @(posedge clk)                    // writes at the go edge and the WIN edges after it change the latched words
        if (rst_n)
            for (s = 0; s < S_RD; s = s + 1)
                if (fv[s] && fdx[O_RK +: 2] == 2'd2) begin
                    if ((fv[S_RD] && fdx[O_PB]) && fdx[O_PB+3] == fdx[O_RS])
                        $error("ot_s81_hc_ctpl: coefficient slot %0d written at its go", fdx[O_RS]);
                    for (ck = 0; ck < WIN; ck = ck + 1)
                        if (pend_v[ck] && pend_s[ck] == fdx[O_RS])
                            $error("ot_s81_hc_ctpl: coefficient slot %0d written %0d cycles after its go", fdx[O_RS], ck + 1);
                end
`endif
    // the group (ot_dsrom_su_hcpost_group, lanes k0, k0 + 1)
    wire [63:0]  hr = hprq[0 +: 64] | hprq[64 +: 64] | hprq[128 +: 64] | hprq[192 +: 64];
    wire [127:0] r  = {hr[48 +: 16], 16'h0000, hr[32 +: 16], 16'h0000, hr[16 +: 16], 16'h0000, hr[0 +: 16], 16'h0000};
    wire         b_v;
    wire [159:0] b_d;
    ot_dsrom_su_hcpost_wire #(.W(160), .D(WPIPE)) u_win (.clk(clk), .rst_n(rst_n), .v(hp_in_v), .d({hp_y, r}), .vq(b_v), .q(b_d));
    reg          x_v;
    reg  [159:0] x_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) x_v <= 1'b0; else x_v <= b_v;
    always @(posedge clk) x_d <= b_d;
    wire [63:0] l_o;
    wire [1:0]  l_v, l_f;
    genvar k;
    generate for (k = 0; k < 2; k = k + 1) begin : g_k
        ot_dsrom_su_hcpost_lane #(.ML(ML), .AL(AL)) u (
            .clk(clk), .rst_n(rst_n), .v(x_v),
            .r0(x_d[0 +: 32]), .r1(x_d[32 +: 32]), .r2(x_d[64 +: 32]), .r3(x_d[96 +: 32]), .y(x_d[128 +: 32]),
            .c0(c_r[32*(0+k) +: 32]), .c1(c_r[32*(2+k) +: 32]), .c2(c_r[32*(4+k) +: 32]), .c3(c_r[32*(6+k) +: 32]),
            .p(p_r[32*k +: 32]), .vo(l_v[k]), .o(l_o[32*k +: 32]), .fault(l_f[k]));
    end endgenerate
    wire [63:0] o;
    ot_dsrom_su_hcpost_wire #(.W(64), .D(WOUT)) u_wout (.clk(clk), .rst_n(rst_n), .v(l_v[0]), .d(l_o), .vq(hov), .q(o));
    assign hpo = {o[48 +: 16], o[16 +: 16]};
    wire nz = (|o[0 +: 16]) | (|o[32 +: 16]);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin hov_d <= 1'b0; hnz_d <= 1'b0; pflt_d <= 1'b0; end
        else begin hov_d <= hov; hnz_d <= hov & nz; pflt_d <= |l_f; end
endmodule

// Keep this module in SYNTH_KEEP_MODULES so per-word control replicas do not merge.
module ot_s81_hc_ctpl_ctl_ff (
    input wire clk, rst_n,
    input wire [2:0] d,
    output reg [2:0] q
);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) q <= 0; else q <= d;
endmodule


// ------------------------------------------------------------------------------------------------ return bus tiles
// ctrs (S strip): rv / rd pin flops, the far tile's originated slots, the merge stage (ybuf, psb, the banks' hrq) and
// the norm/scale sequencer copy.  ctrn (N strip): the RLY - 2 relay stages and the out flops.  rdm -> (relay | out) is
// the one cross-slot stage (wire only); rd_out at the N face abuts the previous slot's S face.  Same registers as the
// single strip ctr: pin, origination, merge, RLY - 2 relays, out.
module ot_s81_hc_ctrs #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [FXW-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [RDW-1:0]         rd_in,
    output reg  [S_RT+3:0]        rvm,
    output reg  [RDW-1:0]         rdm,
    output wire [16*S_RT-1:0]     rq_q,               // pin-flop row fields for the banks' h reads
    output reg                    hs_run,
    output reg  [15:0]            hs_c,
    input  wire [16*64*S_RT-1:0]  hrq,                // lane tile n = 4 bank + group
    input  wire [16*16-1:0]       yb,
    input  wire [4*32-1:0]        cs,
    input  wire [15:0]            nflt,
    input  wire                   hov_d,
    input  wire [7:0]             hnz_d, pflt_d           // per ctpl tile, ORed here (no die-level gate)
);
    localparam integer O_HS = 5 + S_RD * 16 + 20 + 6 + 8 + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, GT = GS / 2, N = 4 * NG, NV = D / N, NT = 4 * GT;
    localparam integer NR = D / NG, HROWS = NR * NG / 8, YROWS = N / 32, LM = ML, LA = AL;
    localparam integer DS = LM + 7 * CHAIN_STEP, DY = 2 * LM + 1;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    reg rr;                                              // regional reset relay: rst_in = ctfn's first stage
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    reg [7:0] tq;
    reg       lq, farq;
    always @(posedge clk) begin tq <= tid; lq <= last; farq <= tid[0]; end
    wire ng_v = fv[S_RD+1], hs_v = fv[S_RD+4];

    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [DY:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP)) u_q (.clk(clk), .rst_n(rst_n), .fv(fv), .fdx(fdx),
        .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v), .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i),
        .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    integer s, k, qd, q;
    reg [127:0] psb [0:NV-1];
    always @(posedge clk) if (vs[DS]) psb[si] <= cs;
    reg [NT*16-1:0] ybuf [0:NV-1];
    always @(posedge clk) if (vy[DY]) ybuf[yi] <= yb;

    // far tile: return slot origination (ot_s81_hc_ctile)
    reg        po_v;  reg [7:0] po_i;
    always @(posedge clk or negedge rst_n) if (!rst_n) po_v <= 1'b0; else po_v <= vs[DS] && lq;
    always @(posedge clk) po_i <= si;
    reg  y_d1;
    always @(posedge clk or negedge rst_n) if (!rst_n) y_d1 <= 1'b0; else y_d1 <= vy[DY];
    reg [7:0]  oq_rdy, o_v;
    reg [15:0] o_r;
    reg  [S_RT-1:0]    g_v, g_t;
    reg  [8*S_RT-1:0]  g_i;
    reg  [16*S_RT-1:0] g_q;
    always @(*) begin
        g_v = 0; g_t = 0; g_i = 0; g_q = 0;
        if (lq) begin
            if (hs_run) begin
                for (s = 0; s < S_RT; s = s + 1)
                    if (hs_c + s < HROWS) begin g_v[s] = 1'b1; g_t[s] = 1'b1; g_q[16 * s +: 16] = hs_c + s; end
            end else if (o_v < oq_rdy) begin
                for (s = 0; s < S_RT; s = s + 1)
                    if (o_r + s < YROWS) begin g_v[s] = 1'b1; g_i[8 * s +: 8] = o_v; g_q[16 * s +: 16] = o_r + s; end
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin oq_rdy <= 0; o_v <= 0; o_r <= 0; hs_run <= 1'b0; hs_c <= 0; end
        else begin
            if (ng_v) begin oq_rdy <= 0; o_v <= 0; o_r <= 0; end
            else begin
                if (y_d1) oq_rdy <= oq_rdy + 8'd1;
                if (!hs_run && o_v < oq_rdy) begin
                    if (o_r + S_RT >= YROWS) begin o_r <= 0; o_v <= o_v + 8'd1; end
                    else o_r <= o_r + S_RT;
                end
            end
            if (hs_v) begin hs_run <= 1'b1; hs_c <= 0; end
            else if (hs_run) begin hs_c <= hs_c + S_RT; if (hs_c + S_RT >= HROWS) hs_run <= 1'b0; end
        end
    end

    // stage 1: pin flops; stage 2: the far tile's originated slots; stage 3: merge; then 2 + RLY - 3 relays + out
    reg [S_RT+3:0] rvq, rv2;
    reg [RDW-1:0]  rdq, rd2;
    wire [S_RT+3:0] rv_merge;
    wire [RDW-1:0] rd_merge;
    generate if (READ_STAGE) begin : g_read_relay
        reg [S_RT+3:0] v;
        reg [RDW-1:0] d;
        always @(posedge clk or negedge rst_n) if (!rst_n) v<=0; else v<=rv2;
        always @(posedge clk) d<=rd2;
        assign rv_merge=v; assign rd_merge=d;
    end else begin : g_read_legacy
        assign rv_merge=rv2; assign rd_merge=rd2;
    end endgenerate
    assign rq_q = rdq[P_Q +: 16 * S_RT];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rvq <= 0; rv2 <= 0; rvm <= 0; end
        else begin
            rvq <= rv_in;
            rv2[S_RT-1:0] <= lq ? g_v : rvq[S_RT-1:0];
            rv2[S_RT]     <= lq ? po_v : rvq[S_RT];
            rv2[S_RT+1]   <= !lq && rvq[S_RT+1];
            rv2[S_RT+2]   <= rvq[S_RT+2];
            rv2[S_RT+3]   <= rvq[S_RT+3];
            rvm[S_RT:0]   <= rv_merge[S_RT:0];
            rvm[S_RT+1]   <= rv_merge[S_RT+1] | (lq && hov_d);
            rvm[S_RT+2]   <= rv_merge[S_RT+2] | (|pflt_d) | (|nflt);
            rvm[S_RT+3]   <= rv_merge[S_RT+3] | (|hnz_d);
        end
    always @(posedge clk) begin : orig
        reg [RDW-1:0] o;
        o = lq ? {RDW{1'b0}} : rdq;
        if (lq) begin o[P_T +: S_RT] = g_t; o[P_I +: 8 * S_RT] = g_i; o[P_Q +: 16 * S_RT] = g_q; o[P_PI +: 8] = po_i; end
        rdq <= rd_in;
        rd2 <= o;
    end
    reg [256*S_RT-1:0] hrd;                                          // slot s, group l: OR of the 4 banks
    integer ss, ll;
    always @(*)
        for (ss = 0; ss < S_RT; ss = ss + 1)
            for (ll = 0; ll < 4; ll = ll + 1)
                hrd[256 * ss + 64 * ll +: 64] = hrq[64 * S_RT * ll + 64 * ss +: 64] | hrq[64 * S_RT * (4 + ll) + 64 * ss +: 64] |
                                                hrq[64 * S_RT * (8 + ll) + 64 * ss +: 64] | hrq[64 * S_RT * (12 + ll) + 64 * ss +: 64];
    always @(posedge clk) begin : mrg
        reg [RDW-1:0] o;
        o = rd_merge;
        if (rv_merge[S_RT] && farq) begin                                     // the far half owns the octet's slot
            if (NP > 1) o[P_D + 128 +: (NP > 1 ? NP - 1 : 1) * 128] = o[P_D +: (NP > 1 ? NP - 1 : 1) * 128];
            o[P_D +: 128] = psb[o[P_PI +: 8]];
        end
        for (s = 0; s < S_RT; s = s + 1)
            if (rv_merge[s]) begin : sl
                reg [7:0] vi;
                reg [15:0] qx, g, g0, b;
                reg [NT*16-1:0] yr;
                reg [255:0] hr;
                vi = o[P_I + 8 * s +: 8]; qx = o[P_Q + 16 * s +: 16];
                if (!o[P_T + s]) begin
                    yr = ybuf[vi];
                    g = ((32 * qx) % NG) / GT; b = (32 * qx) / NG;
                    for (k = 0; k < 32; k = k + 1)
                        for (qd = 0; qd < N / NG; qd = qd + 1)
                            if ((NG >= 32 ? g + k / GT : (k % NG) / GT) == tq && (NG >= 32 ? b : b + k / NG) == qd)
                                o[P_D + 512 * s + 16 * k +: 16] = yr[16 * (qd * GT + k % GT) +: 16];
                end else begin
                    g0 = ((8 * qx) % NG) / 8;
                    hr = hrd[256 * s +: 256];
                    for (k = 0; k < 8; k = k + 1)
                        if (g0 * (8 / GT) + k / GT == tq)
                            o[P_D + 512 * s + 64 * k +: 64] = hr[64 * (k % GT) +: 64];
                end
            end
        rdm <= o;
    end
endmodule

// ctra / ctrb (centre band, two full-width strips): ot_s81_hc_ctrs split by return slots so neither face carries more
// than ~2.5k pins.  ctra owns rv, the header, slots 0..S_RT/2-1 (incl. the far tile's psb insert into slot 0), rq_q and
// the hs counters it exports; ctrb owns slots S_RT/2..S_RT-1.  Both replicate the sequencer (ctq), the origination
// counters and ybuf (a few k flops) so nothing crosses between them; ctrb takes the rd_in header and the 128 data bits
// the far tile's 128-bit psb insert shifts into its first slot.  fdx: only the control word (bits < O_D) is read.
// Lanes n < 8 (rows above the band) drive the *_n ports on the N face, n >= 8 the *_s ports on the S face.
module ot_s81_hc_ctra #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [WA-1:0]          rd_in,
    output wire [S_RT+3:0]        rvm,
    output wire [WA-1:0]          rdm,
    output wire [16*S_RT-1:0]     rq_q,
    output wire                   hs_run,
    output wire [15:0]            hs_c,
    output wire [16*S_RT-1:0]     rq_q_c1, rq_q_c2, rq_q_c3,
    output wire                  hs_run_c1, hs_run_c2, hs_run_c3,
    output wire [15:0]           hs_c_c1, hs_c_c2, hs_c_c3,
    input  wire [8*64*SH-1:0]     hrq_n, hrq_s,     // [lane n (or n - 8)][slot s] 64 b
    input  wire [8*16-1:0]        yb_n, yb_s,
    input  wire [4*32-1:0]        cs,
    input  wire [7:0]             nflt_n, nflt_s,
    input  wire                   hov_d,
    input  wire [3:0]             hnz_n, hnz_s, pflt_n, pflt_s   // ctpl half 0 (N) / half 1 (S), group g
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT, WA = P_D + 512 * SH;
    wire [RDW-1:0] rdm_w;
    wire [16*64*S_RT-1:0] hrq;
    genvar n, q;
    generate for (n = 0; n < 8; n = n + 1) begin : g_h
        for (q = 0; q < SH; q = q + 1) begin : g_s
            assign hrq[64 * S_RT * n + 64 * q +: 64]       = hrq_n[64 * (SH * n + q) +: 64];
            assign hrq[64 * S_RT * (n + 8) + 64 * q +: 64] = hrq_s[64 * (SH * n + q) +: 64];
            assign hrq[64 * S_RT * n + 64 * (q + SH) +: 64] = 64'd0;
            assign hrq[64 * S_RT * (n + 8) + 64 * (q + SH) +: 64] = 64'd0;
        end
    end endgenerate
    wire [7:0] hnz = {hnz_s[3], hnz_n[3], hnz_s[2], hnz_n[2], hnz_s[1], hnz_n[1], hnz_s[0], hnz_n[0]};
    wire [7:0] pfl = {pflt_s[3], pflt_n[3], pflt_s[2], pflt_n[2], pflt_s[1], pflt_n[1], pflt_s[0], pflt_n[0]};
    ot_s81_hc_ctrs #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(READ_STAGE)) u (
        .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx({{(FXW - O_D){1'b0}}, fdx}),
        .rv_in(rv_in), .rd_in({{(RDW - WA){1'b0}}, rd_in}), .rvm(rvm), .rdm(rdm_w), .rq_q(rq_q), .hs_run(hs_run),
        .hs_c(hs_c), .hrq(hrq), .yb({yb_s, yb_n}), .cs(cs), .nflt({nflt_s, nflt_n}), .hov_d(hov_d), .hnz_d(hnz),
        .pflt_d(pfl));
    assign rdm = rdm_w[WA-1:0];
    // Aliases of genuine registered state; pin_reg_split creates one kept
    // launch flop per physical pin. Parent columns consume every copy.
    assign rq_q_c1 = rq_q;
    assign rq_q_c2 = rq_q;
    assign rq_q_c3 = rq_q;
    assign hs_run_c1 = hs_run;
    assign hs_run_c2 = hs_run;
    assign hs_run_c3 = hs_run;
    assign hs_c_c1 = hs_c;
    assign hs_c_c2 = hs_c;
    assign hs_c_c3 = hs_c;
endmodule

module ot_s81_hc_ctrb #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, CHAIN_STEP = AL, READ_STAGE = 0
) (
    input  wire                   clk,
    input  wire                   rst_in,
    input  wire [7:0]             tid,
    input  wire                   last,
    input  wire [S_RD+4:0]        fv,
    input  wire [O_D-1:0]         fdx,
    input  wire [S_RT+3:0]        rv_in,
    input  wire [P_D-1:0]         rdh_in,           // rd_in header
    input  wire [WB-1:0]          rdd_in,           // rd_in data bits [512 SH - 128, 512 S_RT)
    output wire [512*SH-1:0]      rdm,              // rdm data slots SH .. S_RT-1
    input  wire [8*64*SH-1:0]     hrq_n, hrq_s,     // [lane][slot s - SH] 64 b
    input  wire [8*16-1:0]        yb_n, yb_s
);
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD * 512;
    localparam integer SH = S_RT / 2, P_D = S_RT + 8 * S_RT + 16 * S_RT + 8, RDW = P_D + 512 * S_RT;
    localparam integer WB = 512 * SH + 128;
    wire [RDW-1:0] rdm_w;
    wire [16*64*S_RT-1:0] hrq;
    genvar n, q;
    generate for (n = 0; n < 8; n = n + 1) begin : g_h
        for (q = 0; q < SH; q = q + 1) begin : g_s
            assign hrq[64 * S_RT * n + 64 * q +: 64]       = 64'd0;
            assign hrq[64 * S_RT * (n + 8) + 64 * q +: 64] = 64'd0;
            assign hrq[64 * S_RT * n + 64 * (q + SH) +: 64] = hrq_n[64 * (SH * n + q) +: 64];
            assign hrq[64 * S_RT * (n + 8) + 64 * (q + SH) +: 64] = hrq_s[64 * (SH * n + q) +: 64];
        end
    end endgenerate
    ot_s81_hc_ctrs #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP), .READ_STAGE(READ_STAGE)) u (
        .clk(clk), .rst_in(rst_in), .tid(tid), .last(last), .fv(fv), .fdx({{(FXW - O_D){1'b0}}, fdx}),
        .rv_in(rv_in), .rd_in({rdd_in, {(512 * SH - 128){1'b0}}, rdh_in}), .rvm(), .rdm(rdm_w), .rq_q(), .hs_run(),
        .hs_c(), .hrq(hrq), .yb({yb_s, yb_n}), .cs(128'd0), .nflt(16'd0), .hov_d(1'b0), .hnz_d(8'd0), .pflt_d(8'd0));
    assign rdm = rdm_w[RDW-1 -: 512 * SH];
endmodule

module ot_s81_hc_ctrn #(
    parameter integer S_RT = 4, RDW = 2156, RLY = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RT+3:0]    rvm,
    input  wire [RDW-1:0]     rdm,
    output reg  [S_RT+3:0]    rv_out,
    output reg  [RDW-1:0]     rd_out
);
    reg rr;                                              // regional reset relay: rst_in = ctfn's first stage
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    wire [S_RT+3:0] rv_out_d;
    wire [RDW-1:0]  rd_out_d;
    ot_hdc_delay #(.W(S_RT + 4), .D(RLY - 2), .RESET(1)) u_rvr (.clk(clk), .rst_n(rst_n), .d(rvm), .q(rv_out_d));
    ot_hdc_delay #(.W(RDW), .D(RLY - 2)) u_rdr (.clk(clk), .rst_n(rst_n), .d(rdm), .q(rd_out_d));
    always @(posedge clk or negedge rst_n) if (!rst_n) rv_out <= 0; else rv_out <= rv_out_d;
    always @(posedge clk) rd_out <= rd_out_d;
endmodule

// Fixed lane-position hard masters: packed command payload is a static wire gather.
module ot_s81_hc_ctnl_l0 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2, PIN_STAGE = 1, CHAIN_STEP = 6
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_D=72+16*S_RD, P_BITS=256, FXW=O_D+S_RD*P_BITS,
                       FULL_FXW=O_D+S_RD*512;

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [FULL_FXW-1:0] fdx_full;
    assign fdx_full[O_D-1:0]=fdx[O_D-1:0];
    for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
        for(genvar b=0;b<512;b=b+1) begin : g_expand
            if(lane_payload_needed(0,b)) begin : g_keep
                localparam integer PBIT=lane_payload_rank(0,b);
                assign fdx_full[O_D+rp*512+b]=fdx[O_D+rp*P_BITS+PBIT];
            end else begin : g_unused
                assign fdx_full[O_D+rp*512+b]=1'b0;
            end
        end
    end
    ot_s81_hc_ctnl #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
        .ML(ML),.AL(AL),.RLY(RLY),.PIN_STAGE(PIN_STAGE),.CHAIN_STEP(CHAIN_STEP),.FIXED_LANE(0)) u_core
        (.fdx(fdx_full),.*);
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_in && lane!=2'd0) $error("fixed HC lane0 identity mismatch");
`endif
endmodule

module ot_s81_hc_ctnl_l1 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2, PIN_STAGE = 1, CHAIN_STEP = 6
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_D=72+16*S_RD, P_BITS=288, FXW=O_D+S_RD*P_BITS,
                       FULL_FXW=O_D+S_RD*512;

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [FULL_FXW-1:0] fdx_full;
    assign fdx_full[O_D-1:0]=fdx[O_D-1:0];
    for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
        for(genvar b=0;b<512;b=b+1) begin : g_expand
            if(lane_payload_needed(1,b)) begin : g_keep
                localparam integer PBIT=lane_payload_rank(1,b);
                assign fdx_full[O_D+rp*512+b]=fdx[O_D+rp*P_BITS+PBIT];
            end else begin : g_unused
                assign fdx_full[O_D+rp*512+b]=1'b0;
            end
        end
    end
    ot_s81_hc_ctnl #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
        .ML(ML),.AL(AL),.RLY(RLY),.PIN_STAGE(PIN_STAGE),.CHAIN_STEP(CHAIN_STEP),.FIXED_LANE(1)) u_core
        (.fdx(fdx_full),.*);
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_in && lane!=2'd1) $error("fixed HC lane1 identity mismatch");
`endif
endmodule

module ot_s81_hc_ctnl_l2 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2, PIN_STAGE = 1, CHAIN_STEP = 6
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_D=72+16*S_RD, P_BITS=352, FXW=O_D+S_RD*P_BITS,
                       FULL_FXW=O_D+S_RD*512;

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [FULL_FXW-1:0] fdx_full;
    assign fdx_full[O_D-1:0]=fdx[O_D-1:0];
    for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
        for(genvar b=0;b<512;b=b+1) begin : g_expand
            if(lane_payload_needed(2,b)) begin : g_keep
                localparam integer PBIT=lane_payload_rank(2,b);
                assign fdx_full[O_D+rp*512+b]=fdx[O_D+rp*P_BITS+PBIT];
            end else begin : g_unused
                assign fdx_full[O_D+rp*512+b]=1'b0;
            end
        end
    end
    ot_s81_hc_ctnl #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
        .ML(ML),.AL(AL),.RLY(RLY),.PIN_STAGE(PIN_STAGE),.CHAIN_STEP(CHAIN_STEP),.FIXED_LANE(2)) u_core
        (.fdx(fdx_full),.*);
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_in && lane!=2'd2) $error("fixed HC lane2 identity mismatch");
`endif
endmodule

module ot_s81_hc_ctnl_l3 #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, ML = 5, AL = 4, RLY = 2, PIN_STAGE = 1, CHAIN_STEP = 6
) (
    input  wire                  clk,
    input  wire                  rst_in,
    input  wire [7:0]            tid,
    input  wire [1:0]            bank,
    input  wire [1:0]            lane,
    input  wire                  last,
    input  wire [S_RD+4:0]       fv,
    input  wire [FXW-1:0]        fdx,
    input  wire                  wb_v, wb_en, wb_hs,  // hc_post write back (ctpl flops)
    input  wire [15:0]           wb_ob,
    input  wire [63:0]           wb_d,                // group lq's 4 hc_post outputs, BF16
    input  wire [16*S_RT-1:0]    rq_q,                // return pin flops (ctr): row field
    input  wire                  hs_run,
    input  wire [15:0]           hs_c,
    output reg  [63:0]           hpr,                 // hc_post row read, group lq (zero unless this bank)
    output reg  [64*S_RT-1:0]    hrq,                 // return h row reads, group lq (zero unless this bank)
    input  wire [31:0]           cy_in,               // octet carry (lane 0)
    input  wire [31:0]           acc_in,              // chain: previous lane's adder output
    input  wire [31:0]           sqn_in,              // chain: next lane's square
    output wire [31:0]           sq_out,
    output wire [31:0]           acc_out,
    output reg  [31:0]           cy_out,              // registered acc_out (the octet carry at lane 2)
    output wire [15:0]           yb,
    output reg                   flt
);
    localparam integer O_D=72+16*S_RD, P_BITS=288, FXW=O_D+S_RD*P_BITS,
                       FULL_FXW=O_D+S_RD*512;

    // Constant bit maps: HLOAD64-bit lane words, GAIN32-bit lane words, shared pre128.
    function automatic integer lane_payload_width(input integer ln);
        begin case(ln) 0:lane_payload_width=256; 1:lane_payload_width=288;
              2:lane_payload_width=352; default:lane_payload_width=288; endcase end
    endfunction
    function automatic integer lane_payload_needed(input integer ln,input integer bitno);
        integer g;
        begin
            lane_payload_needed=(bitno<128) ||
                (bitno>=64*ln && bitno<64*ln+64) ||
                (bitno>=64*(ln+4) && bitno<64*(ln+4)+64);
            for(g=0;g<4;g=g+1)
                if(bitno>=32*(ln+4*g) && bitno<32*(ln+4*g)+32)
                    lane_payload_needed=1;
        end
    endfunction
    function automatic integer lane_payload_rank(input integer ln,input integer bitno);
        integer b;
        begin lane_payload_rank=0;
            for(b=0;b<bitno;b=b+1) lane_payload_rank=lane_payload_rank+lane_payload_needed(ln,b);
        end
    endfunction
    function automatic integer lane_payload_index(input integer ln,input integer packedbit);
        integer b,c;
        begin lane_payload_index=0;c=0;
            for(b=0;b<512;b=b+1) if(lane_payload_needed(ln,b)) begin
                if(c==packedbit) lane_payload_index=b;
                c=c+1;
            end
        end
    endfunction
    wire [FULL_FXW-1:0] fdx_full;
    assign fdx_full[O_D-1:0]=fdx[O_D-1:0];
    for(genvar rp=0;rp<S_RD;rp=rp+1) begin : g_read_port
        for(genvar b=0;b<512;b=b+1) begin : g_expand
            if(lane_payload_needed(3,b)) begin : g_keep
                localparam integer PBIT=lane_payload_rank(3,b);
                assign fdx_full[O_D+rp*512+b]=fdx[O_D+rp*P_BITS+PBIT];
            end else begin : g_unused
                assign fdx_full[O_D+rp*512+b]=1'b0;
            end
        end
    end
    ot_s81_hc_ctnl #(.NG(NG),.D(D),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.S_RT(S_RT),
        .ML(ML),.AL(AL),.RLY(RLY),.PIN_STAGE(PIN_STAGE),.CHAIN_STEP(CHAIN_STEP),.FIXED_LANE(3)) u_core
        (.fdx(fdx_full),.*);
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_in && lane!=2'd3) $error("fixed HC lane3 identity mismatch");
`endif
endmodule
