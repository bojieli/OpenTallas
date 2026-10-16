`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// dsfd_wfc_cr: the WFC kit (dsfd_wfc_src / dsfd_wfc_stg, rtl/dsrom_sys/mtp/dsfd_wfc_kit.sv) with CREDIT die-facing
// ports (ds-1010 lat-audit, 2026-10-10; structural rule "pin stations + credits die-wide", rtl/common/ot_link_credit.sv).
//
// Why: on the S81 layer1 / layer1e dies the kit's die buses carry 9..13 registered hub stages (tools/s81/hub_stage_count.py
// on the x1b+rgap recipe: wfc -> vm 13, vm -> wfc 13 (layer1e 12 / 13), collective -> wfc 9, wfc -> collective 10,
// wfc -> capture 10, capture -> wfc 11).  The kit's link and VM request ports are valid / ready 2-entry skids: a ready that
// crosses N stations reaches the sender N cycles late, so the sender re-presents an accepted beat or overruns the skid
// (dup / drop).  (The pre-kit --wfc-hard dsfd_wfc binding was worse: the WFC's VM port is a FIXED 2-edge read, no
// valid, bound across 13 + 13 stages and the 0.9 / 1.2 GHz boundary.)  Here every valid / ready die port is a credit
// channel; the valid-only ports (VM read response f_srq {rv, rq}, write ACK pulse f_swa, core start / done) need no
// return path (vmx reserves response room before it requests: RQFREE, rq_n + r_out < RQ) and are latency-insensitive.
//   link in   f_liv f_lid -> ot_link_credit_rx (DEPTH LIN_D) -> kit; t_lic credit pulse back     (collective tx holds LIN_D)
//   link out  kit -> ot_link_credit_tx (CRED LOUT_C) -> t_lov t_lod; f_loc credit pulse in        (collective rx DEPTH LOUT_C)
//   VM write  kit -> ot_link_credit_tx (CRED VMW_C, ckv) -> t_swv t_swd; f_swc in                 (VM landing DEPTH VMW_C)
//   VM read   kit -> ot_link_credit_tx (CRED VMR_C, ckv) -> t_srv t_srd; f_src in                 (VM landing DEPTH VMR_C)
// Full rate needs depth >= forward + return stages + 4: link 9 + 10 + 4 = 23 -> 24; VM 13 + 13 + 4 = 30 -> 32.
// Fewer stages only idle credits (exact at any latency); a depth below the round trip only throttles.
// WOUT_MAX: unACKed VM writes are capped at 27 (vmx 5-bit wout 31 less its 2-entry write skid and ACK pin flop, less 1); with the 13 + 13 stage ACK round trip this throttles
// long write bursts (priced below the per-job write count; exactness first).
// t_ft = kit {proto, lnk | link-in landing fault, tok, vmx}.
// Bench: tools/dsrom_wfc_kit_cr_bench.py (the kit benches with the real stage counts on every die port; negatives: the
// plain kit's valid / ready across the same stages, and a far sender over-crediting the link-in landing).
// ---------------------------------------------------------------------------
module dsfd_wfc_cr #(parameter integer SOURCE = 0, parameter integer FLIT = 512, parameter integer NW = 21,
                     parameter integer USER_W = 10, parameter integer VWA = 15, parameter integer LAG = 0,
                     parameter integer LIN_D = 24, parameter integer LOUT_C = 24,
                     parameter integer VMW_C = 32, parameter integer VMR_C = 32, parameter integer WOUT_MAX = 27) (
    input  wire [0:0] ck, ckv, rst, rsv,
    input  wire [0:0] f_liv, input  wire [FLIT:0] f_lid, output wire [0:0] t_lic,
    output wire [0:0] t_lov, output wire [FLIT:0] t_lod, input  wire [0:0] f_loc,
    output wire [0:0] t_swv, output wire [VWA+FLIT-1:0] t_swd, input wire [0:0] f_swc, input wire [0:0] f_swa,
    output wire [0:0] t_srv, output wire [VWA-1:0] t_srd, input wire [0:0] f_src, input wire [FLIT:0] f_srq,
    output wire [USER_W+2*NW:0] t_ks, input wire [NW+32:0] f_kd,
    input  wire [2+USER_W+2*NW:0] f_c,             // SOURCE only (static configuration)
    output wire [USER_W+2*NW:0] t_tok,             // SOURCE only
    output wire [USER_W+2*NW-1:0] t_cfg,           // SOURCE only
    output wire [3:0] t_ft
);
    wire liv, lir, lov, lor, swv, swr, srv, srr, li_flt;
    wire [FLIT:0] lid, lod; wire [VWA+FLIT-1:0] swd; wire [VWA-1:0] srd; wire [3:0] kft;
    ot_link_credit_rx #(.W(FLIT + 1), .DEPTH(LIN_D)) u_li (.clk(ck[0]), .rst_n(rst[0]),
        .l_valid(f_liv[0]), .l_data(f_lid), .l_credit(t_lic[0]), .o_valid(liv), .o_ready(lir), .o_data(lid), .fault(li_flt));
    ot_link_credit_tx #(.W(FLIT + 1), .CRED(LOUT_C)) u_lo (.clk(ck[0]), .rst_n(rst[0]),
        .i_valid(lov), .i_ready(lor), .i_data(lod), .l_valid(t_lov[0]), .l_data(t_lod), .l_credit(f_loc[0]));
    // vmx counts its unACKed writes in a 5-bit wout (ot_dsrom_wfc_vmx: a START waits for wout == 0): at the die's
    // 13 + 13 stage write -> ACK round trip a credit window lets > 31 writes be unACKed, wout wraps, the START overtakes
    // its writes (bench cr_stg_* vmx fault / write-start order FAIL before this cap).  The wrapper caps unACKed writes
    // at WOUT_MAX (vmx unchanged: closed element).
    reg [5:0] wr_out;
    wire w_cap = wr_out < WOUT_MAX[5:0];
    wire swr_c;
    wire sw_go = swv && swr_c && w_cap;
    assign swr = swr_c && w_cap;
    always @(posedge ckv[0] or negedge rsv[0])
        if (!rsv[0]) wr_out <= 6'd0;
        else wr_out <= wr_out + {5'd0, sw_go} - {5'd0, f_swa[0]};
    ot_link_credit_tx #(.W(VWA + FLIT), .CRED(VMW_C)) u_sw (.clk(ckv[0]), .rst_n(rsv[0]),
        .i_valid(swv && w_cap), .i_ready(swr_c), .i_data(swd), .l_valid(t_swv[0]), .l_data(t_swd), .l_credit(f_swc[0]));
    ot_link_credit_tx #(.W(VWA), .CRED(VMR_C)) u_sr (.clk(ckv[0]), .rst_n(rsv[0]),
        .i_valid(srv), .i_ready(srr), .i_data(srd), .l_valid(t_srv[0]), .l_data(t_srd), .l_credit(f_src[0]));
    generate if (SOURCE) begin : g_src
        dsfd_wfc_src u_kit (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
            .f_liv(liv), .f_lid(lid), .t_lir(lir), .t_lov(lov), .t_lod(lod), .f_lor(lor),
            .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(f_swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(f_srq),
            .t_ks(t_ks), .f_kd(f_kd), .f_c(f_c), .t_tok(t_tok), .t_cfg(t_cfg), .t_ft(kft));
    end else begin : g_stg
        dsfd_wfc_stg #(.LAG(LAG)) u_kit (.ck(ck), .ckv(ckv), .rst(rst), .rsv(rsv),
            .f_liv(liv), .f_lid(lid), .t_lir(lir), .t_lov(lov), .t_lod(lod), .f_lor(lor),
            .t_swv(swv), .t_swd(swd), .f_swr(swr), .f_swa(f_swa), .t_srv(srv), .t_srd(srd), .f_srr(srr), .f_srq(f_srq),
            .t_ks(t_ks), .f_kd(f_kd), .t_ft(kft));
        assign t_tok = '0; assign t_cfg = '0;
    end endgenerate
    assign t_ft = {kft[3], kft[2] | li_flt, kft[1], kft[0]};
endmodule
