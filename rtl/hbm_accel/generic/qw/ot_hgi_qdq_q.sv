`timescale 1ns/1ps
`default_nettype none
// FUSED.QDQ_* B2 QUARTER (el1011-qdqtput, 2026-10-12): one QDQ engine per HBM B2 cluster, its wide VM read / write on the
// cluster's LOCAL VM slice 8-lane group (results/arch/hbm_b2_1012/SPEC.md sec 2a: lane b <-> local bank b = sector[2:0];
// the lanestation client protocol of ot_hgi_vm_lanechain: rq {v, sector 15} / rq_cr / rr {v, data 256} in order per lane,
// wq {v, sector 15, data 256, wmask 8} / wq_cr / wq_done, burst grant rg_req / rg_gnt, wg_req / wg_gnt).
// Throughput fix (AGENTS throughput gate: the packet unit ran 13.7x its price ceil(n/32)+8, the 32-lane wide engines
// 2.7-4.4x because every record waited for the previous one to drain):
//   * rate: one 32-FP32 beat (4 sectors on 4 consecutive local banks) a cycle into ONE decode core (ot_hgi_qw_dec3 = dxl/dbq/daq, or ot_hgi_qw_dec; the
//     closed hardened decode tile: same arithmetic as ot_hgi_quant_wide / the transport -> word-identical O);
//   * record OVERLAP: an RQ-deep record queue; the read walk of record k+1 is loaded on the cycle record k issues its last
//     beat (no drain between records); the header rides with each beat into the decode (the decode is per-beat clean);
//     in-order retire on per-lane write counters (a record retires when every lane's done counter passed the snapshot
//     taken at its last write) -> one done a record, in record order;
//   * hazards: at enqueue each record gets a dependency mask over the older in-flight records whose A / O word ranges
//     intersect its O / A / O ranges (RAW, WAR, WAW); its read walk starts only when those retired.  A record's own
//     in-place A == O is legal (a beat is read before it is written);
//   * shape class: the fast-path shapes of ot_hgi_quant_wide (QDQ header legal, A / O VM FP32 descriptors, inner stride
//     1, 8-word aligned bases / n / row strides, ends inside VM, A / O disjoint or identical).  Any other record FAULTS
//     (fail closed, retired in order with {fault, done}): the B2 compiler emits only this class (the packet transport,
//     its second decode core and the VM packet client are not part of the quarter).
// Front: face flops (pure) -> record binding (ot_hgi_quant_record) -> S1 capture -> S2 spans / flags -> S3 eligibility +
// ranges -> enqueue (dependency compares against the queue's registered ranges).  ret = {fault, done, ready}; ready is
// high while at most RQ - 4 records are accepted and not retired (4 = the records that can arrive before a lowered ready
// is seen through the face flops).
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 (lane-to-sector map; must FAIL); 2 = hazard masks ignored.
// q8b (2026-10-13, hierarchy rule + face-anchored seams): this module is WIRES ONLY.  Its logic lives in four hardened
// children with their own clock trees and a flop at every pin: ot_hgi_qdq_fr (rec -> S3, S face), ot_hgi_qdq_core (queue,
// hazards, read walk, wrq, retire; S band), ot_hgi_qdq_asm (beat queue, pops, beat placement; lane-pair | decoder gap)
// and ot_hgi_qdq_wr (result FIFO + SRAM, wwq, finish detection; N face), beside the lane-pair and decode tiles.
// Cycles added over q7: +1 record ingress (S3 pin flops), +1 pop -> decode (hq pin flops), +1 decode -> result FIFO
// (y pin flops), +1 last done -> ret (the N -> S finish pulse).  The reset chain is core -> asm -> {lane pairs, decode, wr}.
module ot_hgi_qdq_q #(
    parameter integer LQ  = 10,     // lane credits a lane (= the slice bank's wide-lane queue depth, 4 + 2 x 3 relay stages,
                                    // B2 SPEC v0.8 D-B2-12; 4 credits at 3 relays measured 1.29x)
    parameter integer LD  = 16,     // per-lane response FIFO (read round trip at 0.5 sector / lane / cycle; >= LQ)
    parameter integer NB  = 32,     // issued-beat FIFO (>= read round trip in beats; 16 caps S=3 at 18 cyc a 16-beat record)
    parameter integer OD  = 64,     // result FIFO beats (>= decode latency 26 + write round trip at S=3)
    parameter integer RQ  = 16,     // record queue
    parameter integer DEC3 = 1,     // decoder: 1 = ot_hgi_qw_dec3 (track B: dxl / dbq / daq tiles), 0 = ot_hgi_qw_dec (one tile)
    parameter integer SPANPIPE = 0, // opt-in: seven local span stages (+6 edges), exact 52-bit product
    parameter integer MUT = 0,
    parameter integer FINFLAGS = 0,
    parameter integer FRONTFAST = 0, // opt-in new mixed frontend physical composition
    parameter integer FASTFIN = 0 // explicit native candidate; new views required
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [682:0]      rec,          // {n_O, n_A, desc_O, desc_A, header, valid} (hgi_die_dispatch 'quant')
    output wire [2:0]        ret,          // {fault, done, ready}
    output wire [8*16-1:0]   wrq,
    input  wire [7:0]        wrq_cr,
    input  wire [8*257-1:0]  wrr,
    output wire [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    input  wire [7:0]        wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
`ifdef OT_HARD_CHILDREN
    initial if(FASTFIN!=0 || FRONTFAST!=0 || FINFLAGS!=0)$fatal(1,"FASTFIN requires source-matched new CORE/WR physical views; old closed hard children are not the candidate");
`endif
    wire s1_v, s3_v, nfault; wire [189:0] s3;
    wire [7:0] c_pop, e_push; wire [3:0] e_ovf; wire [8*256-1:0] hq; wire [3:0] lq_rst_n; wire dec_rst_n, asm_rst_n, wr_rst_n;
    wire d_v, vo, qfault, dfault; wire [17:0] d_hd; wire [1023:0] d_x; wire [511:0] y;
    wire [127:0] d_h = {d_hd[17:8], 46'd0, d_hd[7:0], 64'd0};   // the decode's only header fields (constants are wires)
    wire bp_v, a_fire, a_bad_c, a_bad_w, a_idle, m_v, w_wf, w_fin, w_bad, w_idle, c_act;
    wire [39:0] bp; wire [7:0] a_pop; wire [18:0] m;
`ifdef OT_HARD_CHILDREN
    ot_hgi_qdq_fr u_fr (
`else
    generate if(FRONTFAST!=0) begin:g_fast_front
    ot_hgi_qdq_fr_mix #(.ONE_ROW(1)) u_fr (
        .clk(clk), .rst_n(rst_n), .rec(rec), .s1_v(s1_v), .s3_v(s3_v), .s3(s3), .nfault(nfault));
    end else begin:g_general_front
    ot_hgi_qdq_fr #(.SPANPIPE(SPANPIPE)) u_fr (
`endif
        .clk(clk), .rst_n(rst_n), .rec(rec), .s1_v(s1_v), .s3_v(s3_v), .s3(s3), .nfault(nfault));
`ifndef OT_HARD_CHILDREN
    end endgenerate
`endif
`ifdef OT_HARD_CHILDREN
    ot_hgi_qdq_core u_core (
`else
    ot_hgi_qdq_core #(.LQ(LQ), .LD(LD), .NB(NB), .RQ(RQ), .SPANPIPE(SPANPIPE), .MUT(MUT), .FIN_BYPASS(FASTFIN)) u_core (
`endif
        .clk(clk), .rst_n(rst_n), .i_s1_v(s1_v), .i_s3_v(s3_v), .i_s3(s3), .i_nfault(nfault), .ret(ret), .wrq(wrq),
        .wrq_cr(wrq_cr), .rg_req(rg_req), .rg_gnt(rg_gnt), .asm_rst_n(asm_rst_n), .bp_v(bp_v), .bp(bp), .i_pop(a_pop),
        .i_fire(a_fire), .i_abad(a_bad_c), .i_aidle(a_idle), .o_act(c_act), .i_fin(w_fin), .i_wbad(w_bad), .i_widle(w_idle));
`ifdef OT_HARD_CHILDREN
    ot_hgi_qdq_asm u_asm (
`else
    ot_hgi_qdq_asm #(.LD(LD), .NB(NB), .OD(OD), .MUT(MUT)) u_asm (
`endif
        .clk(clk), .rst_n(asm_rst_n), .bp_v(bp_v), .bp(bp), .hq_p0(hq[511:0]), .hq_p1(hq[1023:512]),
        .hq_p2(hq[1535:1024]), .hq_p3(hq[2047:1536]), .e_push(e_push), .e_ovf(e_ovf), .c_pop(c_pop),
        .lq_rst_n(lq_rst_n), .dec_rst_n(dec_rst_n), .wr_rst_n(wr_rst_n), .d_v(d_v), .d_hd(d_hd), .d_x(d_x), .o_pop(a_pop),
        .o_fire(a_fire), .o_bad_c(a_bad_c), .o_idle(a_idle), .m_v(m_v), .m(m), .o_bad_w(a_bad_w), .i_wf(w_wf));
`ifdef OT_HARD_CHILDREN
    ot_hgi_qdq_wr u_wr (
`else
    ot_hgi_qdq_wr #(.LQ(LQ), .OD(OD), .RQ(RQ), .ACK_LOOKAHEAD(FASTFIN),.ACK_FLAGS(FINFLAGS)) u_wr (
`endif
        .clk(clk), .rst_n(wr_rst_n), .m_v(m_v), .m(m), .i_bad(a_bad_w), .vo(vo), .qfault(qfault), .dfault(dfault), .y(y),
        .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .wg_req(wg_req), .wg_gnt(wg_gnt), .i_act(c_act), .o_wf(w_wf),
        .o_fin(w_fin), .o_bad(w_bad), .o_idle(w_idle));
    genvar gp;
    generate for (gp = 0; gp < 4; gp = gp + 1) begin : g_lq
        ot_hgi_qdq_lq u_lq (.clk(clk), .rst_n(lq_rst_n[gp]), .wrr(wrr[gp*2*257 +: 2*257]), .c_pop(c_pop[gp*2 +: 2]),
            .hq(hq[gp*512 +: 512]), .e_push(e_push[gp*2 +: 2]), .e_ovf(e_ovf[gp]));
    end endgenerate
    generate if (DEC3 != 0) begin : g_d3
        // track B (decoder of record, coordinator 10-12): three hardened tiles dxl / dbq / daq, same ports and timing
        ot_hgi_qw_dec3 u_dec (.clk(clk), .rst_n(dec_rst_n), .v(d_v), .header(d_h), .x(d_x), .vo(vo), .y(y), .fault(qfault),
            .decode_fault(dfault));
    end else begin : g_d1
        ot_hgi_qw_dec u_dec (.clk(clk), .rst_n(dec_rst_n), .v(d_v), .header(d_h), .x(d_x), .vo(vo), .y(y), .fault(qfault),
            .decode_fault(dfault));
    end endgenerate
    initial if (LD != 16) $fatal(1, "ot_hgi_qdq_q: LD = 16 (= the hardened ot_hgi_qdq_lq default)");
endmodule
`default_nettype wire
