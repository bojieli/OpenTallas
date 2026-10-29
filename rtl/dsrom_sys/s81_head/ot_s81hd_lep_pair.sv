`timescale 1ns/1ps
`default_nettype none
// DIE-HEAD-9 LEP split (COORD 2026-10-28 06:30 ruling (4)): one PEER PAIR child
// of hd_lep0N = the existing g_lane[k] body of ot_s81hd_lep0N_core, unchanged:
// the K-side MU lane landing ot_s81_mu72_lnland_nst plus the safe8 collective
// lane dsfd_coll_lane_w_safe8_ntf, with their private n_* link (credit, data,
// rxv, flt) kept INSIDE the child.  Wrapper only: same instances, parameters
// and nets; 0 added cycles.  Selected by ot_s81hd_lep0N_core PAIR=1 (default 0
// keeps the original flat g_lane hierarchy).  Child faces: K side = k_* (to
// u_lep), collective side = coll_i/coll_o (the die collective pins).
// DIE-HEAD-21 lepwe (COORD HEAD-KITS-3 ruling 10-28 23:13): the landing is
// ot_s81hd_lnland_dw = ot_s81_mu72_lnland_nst with the K -> N writer's slot
// write enable decoded from the binary write count (slot s written iff
// wc[AW-1:0] == s) instead of the separate one-hot write_oh register.  The two
// are the same signal in every reachable state (write_oh resets to 0..01 with
// wc = 0 and both advance on the same edges: write_oh == 1 << wc[AW-1:0]), so
// every register, every slot write and every output is cycle-identical; no
// cycle, port or width change.  Each k_* input bit now feeds D slot flops whose
// write conditions are provably mutually exclusive in the netlist (decodes of
// the same two flops), i.e. face_guard land form hold_mux (D = 4), the declared
// face-register form; with the independent write_oh flops face_guard could not
// prove exclusivity (HEAD-KITS-3: 556 bits FAIL).  The N -> K direction (lane-
// internal inputs, no face) keeps ot_s81_mu72_land unchanged.
module ot_s81hd_lep_pair #(parameter [0:0] CHB=1'b1)(
 input  wire clk,rst_n,
 input  wire k_lo_v,output wire k_lo_r,input wire[552:0]k_lo_d,
 output wire k_li_v,input  wire k_li_r,output wire[552:0]k_li_d,
 input  wire k_rxv,output wire[2:0]k_flt,
 input  wire[513:0]coll_i,output wire[511:0]coll_o
);
 wire lv,lr,liv,lir,lrx;wire[552:0]ld,lid;wire[2:0]lf;
 ot_s81hd_lnland_dw u_land(
  .ck_k(clk),.ck_n(clk),.rs_k(rst_n),.rs_n(rst_n),
  .k_lo_v(k_lo_v),.k_lo_r(k_lo_r),.k_lo_d(k_lo_d),
  .k_li_v(k_li_v),.k_li_r(k_li_r),.k_li_d(k_li_d),
  .k_rxv(k_rxv),.k_flt(k_flt),
  .n_lo_v(lv),.n_lo_r(lr),.n_lo_d(ld),
  .n_li_v(liv),.n_li_r(lir),.n_li_d(lid),
  .n_rxv(lrx),.n_flt(lf));
 dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12))u_lane(
  .ck(clk),.rs(rst_n),.chb(CHB),
  .rx({coll_i[512],coll_i[513],coll_i[511:0],lrx}),
  .tx(coll_o),.lo_v(lv),.lo_r(lr),.lo_d(ld),
  .li_v(liv),.li_r(lir),.li_d(lid),.flt(lf));
endmodule

// ot_s81_mu72_lnland_nst (portfix178, MUT 0) with the K -> N bundle through ot_s81hd_mu72_land_dw.
module ot_s81hd_lnland_dw(
    input  wire         ck_k, ck_n, rs_k, rs_n,
    input  wire         k_lo_v,  input  wire [552:0] k_lo_d, output wire k_lo_r,
    output wire         k_li_v,  output wire [552:0] k_li_d, input  wire k_li_r,
    input  wire         k_rxv,   output wire [2:0]   k_flt,
    output wire         n_lo_v,  output wire [552:0] n_lo_d, input  wire n_lo_r,
    input  wire         n_li_v,  input  wire [552:0] n_li_d, output wire n_li_r,
    output wire         n_rxv,   input  wire [2:0]   n_flt
);
    wire [555:0] kn_i = {k_li_r, k_rxv, k_lo_v, k_lo_d}, kn_o;
    wire [557:0] nk_i = {n_flt, n_lo_r, n_li_v, n_li_d}, nk_o;
    ot_s81hd_mu72_land_dw #(.W(556)) u_kn (.ck_w(ck_k), .ck_r(ck_n), .rs_w(rs_k), .rs_r(rs_n), .i(kn_i), .o(kn_o));
    ot_s81_mu72_land #(.W(558)) u_nk (.ck_w(ck_n), .ck_r(ck_k), .rs_w(rs_n), .rs_r(rs_k), .i(nk_i), .o(nk_o));
    assign {n_li_r, n_rxv, n_lo_v, n_lo_d} = kn_o;
    assign {k_flt, k_lo_r, k_li_v, k_li_d} = nk_o;
endmodule

// ot_s81_mu72_land (D4/K2, CHUNK_BITS 8, +3 destination edges) with the writer ot_s81hd_land_vector_dw_w.
module ot_s81hd_mu72_land_dw #(parameter integer W=1)(
    input wire ck_w, ck_r, rs_w, rs_r,
    input wire [W-1:0] i, output wire [W-1:0] o
);
    localparam integer N=(W+7)/8;
    wire [N-1:0] rw, rr;
    wire [4*W-1:0] bank;
    wire [11:0] epo;
    wire [4*N-1:0] vld;
    ot_pl_land_reset_forest #(.DEPTH(3),.LEAVES(N),.ROOT_LOADS(2)) u_rw(
        .ck(ck_w),.d(rs_w),.q(rw));
    ot_pl_land_reset_forest #(.DEPTH(3),.LEAVES(N),.ROOT_LOADS(2)) u_rr(
        .ck(ck_r),.d(rs_r),.q(rr));
    ot_s81hd_land_vector_dw_w #(.W(W),.D(4),.CHUNK_BITS(8)) u_w(
        .ck(ck_w),.rsi(rw),.i(i),.bank(bank),.epo(epo),.vld(vld));
    ot_pl_land_vector_reset_r #(.W(W),.D(4),.K(2),.CHUNK_BITS(8)) u_r(
        .ck(ck_r),.rsi(rr),.bank(bank),.epo(epo),.vld(vld),.o(o));
endmodule

// ot_pl_land_vector_reset_kw_w with ot_s81hd_land_local_dw chunks (same ports, bank layout, epoch/valid ages).
module ot_s81hd_land_vector_dw_w #(
    parameter integer W=1073,D=4,CHUNK_BITS=24,
    parameter integer AW=(D<=2)?1:$clog2(D),
    parameter integer CHUNKS=(W+CHUNK_BITS-1)/CHUNK_BITS
)(
    input wire ck,input wire [CHUNKS-1:0] rsi,input wire [W-1:0] i,
    output wire [D*W-1:0] bank,output wire [D*(AW+1)-1:0] epo,
    output wire [D*CHUNKS-1:0] vld
);
    generate if(W<1 || CHUNK_BITS<1 || CHUNK_BITS>24 || CHUNKS!=(W+CHUNK_BITS-1)/CHUNK_BITS) begin:g_invalid_shape
        OT_LAND_VECTOR_DW_REQUIRES_EXACT_CHUNKS u_bad();
    end endgenerate
    generate for(genvar c=0;c<CHUNKS;c=c+1) begin:g_chunk
        localparam integer CW=(W-c*CHUNK_BITS<CHUNK_BITS)?W-c*CHUNK_BITS:CHUNK_BITS;
        wire [D*CW-1:0] cb;
        wire [D*(AW+1)-1:0] ce;
        (* keep_hierarchy="yes" *) ot_s81hd_land_local_dw #(.W(CW),.D(D)) u_local(
            .ck(ck),.rsi(rsi[c]),.i(i[c*CHUNK_BITS+:CW]),.bank(cb),.epo(ce),.vld(vld[c*D+:D]));
        for(genvar s=0;s<D;s=s+1) begin:g_slot
            assign bank[s*W+c*CHUNK_BITS+:CW]=cb[s*CW+:CW];
        end
        if(c==0) begin:g_tags assign epo=ce;end
    end endgenerate
endmodule

// ot_pl_land_local_kw with the slot write enable decoded from the write count: slot s is written iff
// wc[AW-1:0] == s (one write per edge, exactly one slot).  write_oh is kept (valid update, as ot_pl_land_local_kw);
// in every reachable state write_oh == 1 << wc[AW-1:0], so the slot writes are those of ot_pl_land_local_kw.
// D must be 1 << AW (D = 4 here).
module ot_s81hd_land_local_dw #(
    parameter integer W = 24, D = 4,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input wire ck, rsi,
    input wire [W-1:0] i,
    output wire [D*W-1:0] bank,
    output wire [D*(AW+1)-1:0] epo,
    output wire [D-1:0] vld
);
    generate if (D != (1 << AW)) begin:g_invalid_depth
        OT_S81HD_LAND_LOCAL_DW_REQUIRES_POW2_DEPTH u_bad();
    end endgenerate
    reg rq;
    reg [AW:0] wc;
    (* keep *) reg [D-1:0] write_oh;
    reg [D-1:0] valid;
    reg [W-1:0] data [0:D-1];
    reg [AW:0] epoch [0:D-1];
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) begin wc <= 0; write_oh <= {{(D-1){1'b0}},1'b1}; valid <= 0; end
        else begin
            wc <= wc + 1'b1;
            write_oh <= {write_oh[D-2:0], write_oh[D-1]};
            valid <= valid | write_oh;
        end
    genvar s;
    generate for (s=0;s<D;s=s+1) begin:g_slot
        wire we = (wc[AW-1:0] == s);
        always @(posedge ck) if (we) begin data[s] <= i; epoch[s] <= wc; end
        assign bank[s*W+:W] = data[s];
        assign epo[s*(AW+1)+:AW+1] = epoch[s];
    end endgenerate
    assign vld = valid;
endmodule
`default_nettype wire
