`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_wfc_crp + dsfd_wfc_cr2: the WFC kit's credit die ports as their OWN routed tile (fe-push-ds-1010, 2026-10-10;
// hardcore-1010 feasibility row dsfd_wfc_cr, RISK-high, "never routed").
//
// dsfd_wfc_cr (dsfd_wfc_kit_cr.sv, ds-1010 lat-audit) fixed the protocol (credit channels across the 9..13 hub stages) but
//   (e) landed link-in beats in ot_link_credit_rx DEPTH 24 x 513 FLOPS (12.3k) behind a 5-bit rp -> 24:1 x 513 read mux
//       (the coll ct crpb class, 3x deeper: rp -> 8:1 x 553 -> l_data enables, SS -185.8),
//   (c) fed the raw rst[0] / rsv[0] port into every credit FIFO (one port net clears the tile),
//   and wraps the whole kit, so it was never a routable block.
// Here the credit boundary is one tile, dsfd_wfc_crp, that sits in the WFC slab between the die's station chains and
// the kit (dsfd_wfc_src / dsfd_wfc_stg, closed elements, abutting on the N face):
//   link in   pin flops -> ot_fifo_sram_fwft (3 x ot_sram_1r1w_128x256 macros, DEPTH 32 >= LIN_D credits; 2-register
//             output buffer = the skid) -> kit.  No pointer-indexed flop array, no DEPTH:1 mux: the head leaves a
//             2:1 output-register select.  Credit pulse per pop from a kept flop.  Landing overflow = sticky fault.
//   link out  ot_link_credit_tx DFREE (send reaches only the l_valid flop, never a 513-bit enable), CRED LOUT_C.
//   VM write  ot_link_credit_tx DFREE, CRED VMW_C, + the unACKed-write cap WOUT_MAX of dsfd_wfc_cr (ckv domain).
//   VM read   ot_link_credit_tx DFREE, CRED VMR_C (ckv domain).
//   reset     one ot_rst_relay per clock domain (ck: landing / link out / kit copy; ckv: VM write / VM read / kit copy);
//             the kit's rst / rsv come from relay copies, so the kit releases after this tile (it adds its own
//             rstsyncs) and never sees i_ready from a tile still in reset.
//   clocks    the ck and ckv halves share no signal: no crossing in the tile (the kit's vmx owns the ratio CDC).
// The valid-only die ports (VM read response f_srq, capture start / done t_ks / f_kd, S0 cfg / token) do not pass
// through this tile (latency-insensitive, push-only; dsfd_wfc_cr2 wires them die <-> kit).  The VM write ACK f_swa is
// pin-flopped here (ckv) and drives both the cap counter and the kit (+1 slow cycle on the ACK, counted consistently).
// Cycles vs dsfd_wfc_cr: link in +1 (SRAM landing: pin flop -> array -> output register; an empty FIFO bypasses to the
// output register, so +1 on an idle link), VM ACK +1.  Exactness is transaction-level; bench below.
// Bench: tools/dsrom_wfc_kit_cr_bench.py cases crp_* (the kit at the real hub stages through dsfd_wfc_cr2), mutants
// WFC_CRP_MUT_LAND (landing data one beat late) and OT_LINK_DFREE_MUT (DFREE tx data lags its valid) must FAIL.
// ---------------------------------------------------------------------------
module ot_link_credit_rx_sram #(parameter integer W = 513, parameter integer DEPTH = 32, parameter integer MACRO = 2) (
    input wire clk, rst_n,
    input wire l_valid, input wire [W-1:0] l_data, (* keep *) output reg l_credit,
    output wire o_valid, input wire o_ready, output wire [W-1:0] o_data,
    output reg fault
);
    (* keep *) reg v_q;
    (* keep *) reg [W-1:0] d_q;
    wire hv, ovf; wire [W-1:0] head;
    wire pop = hv && o_ready;
`ifdef WFC_CRP_MUT_LAND
    // bench mutant: the landed data lags its valid by one beat
    reg [W-1:0] mut_q; always @(posedge clk) mut_q <= d_q;
    wire [W-1:0] wd = mut_q;
`else
    wire [W-1:0] wd = d_q;
`endif
    ot_fifo_sram_fwft #(.W(W), .DEPTH(DEPTH), .MACRO(MACRO)) u_f (.clk(clk), .rst_n(rst_n), .push(v_q), .wdata(wd),
        .pop(pop), .hv(hv), .head(head), .ovf(ovf));
    assign o_valid = hv; assign o_data = head;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; l_credit <= 1'b0; fault <= 1'b0; end
        else begin v_q <= l_valid; l_credit <= pop; if (ovf) fault <= 1'b1; end
    always @(posedge clk) d_q <= l_data;
endmodule

module dsfd_wfc_crp #(parameter integer FLIT = 512, parameter integer VWA = 15, parameter bit OSKID = 0,
                      parameter integer LIN_D = 24, parameter integer LAND_D = 32, parameter integer LOUT_C = 24,
                      parameter integer VMW_C = 32, parameter integer VMR_C = 32, parameter integer WOUT_MAX = 27) (
    input  wire [0:0] ck, ckv, rst, rsv,
    // die side (station chains)
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lic,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_loc,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swc, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [VWA-1:0] t_srd, input wire [0:0] f_src,
    // kit side (abutting dsfd_wfc_src / dsfd_wfc_stg valid / ready ports)
    output wire [0:0] t_kliv, output wire [FLIT:0] t_klid, input wire [0:0] f_klir,
    input  wire [0:0] f_klov, input  wire [FLIT:0] f_klod, output wire [0:0] t_klor,
    input  wire [0:0] f_kswv, input  wire [VWA+FLIT-1:0] f_kswd, output wire [0:0] t_kswr, output wire [0:0] t_kswa,
    input  wire [0:0] f_ksrv, input  wire [VWA-1:0] f_ksrd, output wire [0:0] t_ksrr,
    output wire [0:0] t_krst, t_krsv,
    output wire [0:0] t_ft                       // link-in landing overflow (sticky, from a flop)
);
    initial if (LIN_D > LAND_D) $fatal(1, "dsfd_wfc_crp: LIN_D credits exceed the landing depth");
    wire [2:0] rn, sn;
    ot_rst_relay #(.REGIONS(3)) u_rf (.clk(ck[0]), .rst_n_in(rst[0]), .rst_n(rn));
    ot_rst_relay #(.REGIONS(3)) u_rs (.clk(ckv[0]), .rst_n_in(rsv[0]), .rst_n(sn));
    assign t_krst = rn[2]; assign t_krsv = sn[2];
    // ---- fast (ck) half --------------------------------------------------------------------------------------------
    // OSKID (mtp-wfc 2026-10-10): the kit's ready f_klir drove the landing FIFO's pop and its read-issue count arithmetic
    // (74 generic gate levels pin -> register, rtl_boundary).  A registered 2-entry output skid (ot_dsrom_mtp_skid OREG:
    // in_ready from a flop) takes the pin; the FIFO pops on the skid's registered ready.  +1 cycle on link in.
    wire li_v, li_r; wire [FLIT:0] li_d;
    ot_link_credit_rx_sram #(.W(FLIT + 1), .DEPTH(LAND_D), .MACRO(2)) u_li (.clk(ck[0]), .rst_n(rn[0]),
        .l_valid(f_liv[0]), .l_data(f_lid), .l_credit(t_lic[0]), .o_valid(li_v), .o_ready(li_r),
        .o_data(li_d), .fault(t_ft[0]));
    generate if (OSKID) begin : g_oskid
        ot_dsrom_mtp_skid #(.W(FLIT + 1), .OREG(1)) u_os (.clk(ck[0]), .rst_n(rn[0]), .in_valid(li_v), .in_ready(li_r),
            .in_data(li_d), .out_valid(t_kliv[0]), .out_ready(f_klir[0]), .out_data(t_klid));
    end else begin : g_direct
        assign t_kliv[0] = li_v; assign li_r = f_klir[0]; assign t_klid = li_d;
    end endgenerate
    ot_link_credit_tx #(.W(FLIT + 1), .CRED(LOUT_C), .DFREE(1)) u_lo (.clk(ck[0]), .rst_n(rn[1]),
        .i_valid(f_klov[0]), .i_ready(t_klor[0]), .i_data(f_klod), .l_valid(t_lov[0]), .l_data(t_lod), .l_credit(f_loc[0]));
    // ---- serial (ckv) half -----------------------------------------------------------------------------------------
    (* keep *) reg swa_q;
    always @(posedge ckv[0] or negedge sn[0]) if (!sn[0]) swa_q <= 1'b0; else swa_q <= f_swa[0];
    assign t_kswa = swa_q;
    reg [5:0] wr_out;
    wire w_cap = wr_out < WOUT_MAX[5:0];
    wire swr_c;
    // OSKID: the kit's VM-write valid also reached the unACKed-write count and the credit tx counter (20 levels):
    // a registered 2-entry skid takes f_kswv / f_kswd and drives t_kswr from a flop
    wire kw_v; wire [VWA+FLIT-1:0] kw_d; wire kw_r = swr_c && w_cap;
    generate if (OSKID) begin : g_iskid
        ot_dsrom_mtp_skid #(.W(VWA + FLIT), .OREG(1)) u_is (.clk(ckv[0]), .rst_n(sn[0]), .in_valid(f_kswv[0]),
            .in_ready(t_kswr[0]), .in_data(f_kswd), .out_valid(kw_v), .out_ready(kw_r), .out_data(kw_d));
    end else begin : g_idirect
        assign kw_v = f_kswv[0]; assign kw_d = f_kswd; assign t_kswr = kw_r;
    end endgenerate
    wire sw_go = kw_v && kw_r;
    always @(posedge ckv[0] or negedge sn[0])
        if (!sn[0]) wr_out <= 6'd0;
        else wr_out <= wr_out + {5'd0, sw_go} - {5'd0, swa_q};
    ot_link_credit_tx #(.W(VWA + FLIT), .CRED(VMW_C), .DFREE(1)) u_sw (.clk(ckv[0]), .rst_n(sn[0]),
        .i_valid(kw_v && w_cap), .i_ready(swr_c), .i_data(kw_d), .l_valid(t_swv[0]), .l_data(t_swd), .l_credit(f_swc[0]));
    ot_link_credit_tx #(.W(VWA), .CRED(VMR_C), .DFREE(1)) u_sr (.clk(ckv[0]), .rst_n(sn[1]),
        .i_valid(f_ksrv[0]), .i_ready(t_ksrr[0]), .i_data(f_ksrd), .l_valid(t_srv[0]), .l_data(t_srd), .l_credit(f_src[0]));
endmodule

// dsfd_wfc_cr2: same die ports as dsfd_wfc_cr; the credit boundary is the routed dsfd_wfc_crp tile, the kit is the
// closed kit master.  (Composition for the exact gate and the slab binding; not itself a routed block.)
module dsfd_wfc_cr2 #(parameter bit OSKID = 0, parameter integer SOURCE = 0, parameter integer FLIT = 512, parameter integer NW = 21,
                      parameter integer USER_W = 10, parameter integer VWA = 15, parameter integer LAG = 0,
                      parameter integer LIN_D = 24, parameter integer LAND_D = 32, parameter integer LOUT_C = 24,
                      parameter integer VMW_C = 32, parameter integer VMR_C = 32, parameter integer WOUT_MAX = 27) (
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lic,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_loc,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swc, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [VWA-1:0] t_srd, input wire [0:0] f_src, input wire [FLIT:0] f_srq,
    output wire [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    input  wire [2+USER_W+2*NW:0] f_c,
    output wire [USER_W+2*NW:0] t_tok,
    output wire [USER_W+2*NW-1:0] t_cfg,
    output wire [3:0] t_ft
);
    wire liv, lir, lov, lor, swv, swr, swa, srv, srr, krst, krsv, li_flt;
    wire [FLIT:0] lid, lod; wire [VWA+FLIT-1:0] swd; wire [VWA-1:0] srd; wire [3:0] kft;
    dsfd_wfc_crp #(.FLIT(FLIT), .VWA(VWA), .LIN_D(LIN_D), .LAND_D(LAND_D), .LOUT_C(LOUT_C), .VMW_C(VMW_C), .VMR_C(VMR_C),
                   .WOUT_MAX(WOUT_MAX), .OSKID(OSKID)) u_crp (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
        .f_liv(f_liv), .f_lid(f_lid), .t_lic(t_lic), .t_lov(t_lov), .t_lod(t_lod), .f_loc(f_loc),
        .t_swv(t_swv), .t_swd(t_swd), .f_swc(f_swc), .f_swa(f_swa), .t_srv(t_srv), .t_srd(t_srd), .f_src(f_src),
        .t_kliv(liv), .t_klid(lid), .f_klir(lir), .f_klov(lov), .f_klod(lod), .t_klor(lor),
        .f_kswv(swv), .f_kswd(swd), .t_kswr(swr), .t_kswa(swa), .f_ksrv(srv), .f_ksrd(srd), .t_ksrr(srr),
        .t_krst(krst), .t_krsv(krsv), .t_ft(li_flt));
    generate if (SOURCE) begin : g_src
        dsfd_wfc_src u_kit (.ck(ck), .ckv(ckv), .rst(krst), .rsv(krsv),
            .f_liv(liv), .f_lid(lid), .t_lir(lir), .t_lov(lov), .t_lod(lod), .f_lor(lor),
            .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(f_srq),
            .t_ks(t_ks), .f_kd(f_kd), .f_c(f_c), .t_tok(t_tok), .t_cfg(t_cfg), .t_ft(kft));
    end else begin : g_stg
        dsfd_wfc_stg #(.LAG(LAG)) u_kit (.ck(ck), .ckv(ckv), .rst(krst), .rsv(krsv),
            .f_liv(liv), .f_lid(lid), .t_lir(lir), .t_lov(lov), .t_lod(lod), .f_lor(lor),
            .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(f_srq),
            .t_ks(t_ks), .f_kd(f_kd), .t_ft(kft));
        assign t_tok = '0; assign t_cfg = '0;
    end endgenerate
    assign t_ft = {kft[3], kft[2] | li_flt, kft[1], kft[0]};
endmodule
