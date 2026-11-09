`timescale 1ns/1ps
`ifndef OT_SVC_HV
// S81-SVCRS R5 (11-08): heads per svc engine pass; -DOT_SVC_H8 builds the half-width (8-head, two-pass) slice
`ifdef OT_SVC_H8
`define OT_SVC_HV 8
`else
`define OT_SVC_HV 16
`endif
`endif
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVC (2026-10-17, S81-DV p4h; S81U-SVC4: p4j): dsdv_svc_rs, the REGIONAL SERVICE SLICE (x16 on the 2 x 8 grid above
// the regional controllers dsfd_ctrl_rg2; sid = rsv_NN = 2 column + row, row 1 upper).  One master core dsdv_svc_rs_c;
// two port variants (p4b rule: no open or tied ports on a hardened slice):
//   dsdv_svc_rs_entry the p4j q / P.V ENTRY slices rsv_05 (W half, columns 0-3) and rsv_11 (E half, columns 4-7), under
//                     the slice-column voids: the host endpoint of the half -- job descriptor j / jd, q stream, host
//                     writes hw / hc, the half's fault and its P.V words (pv) come in / go out here (ot_s81_svc_job)
//   dsdv_svc_rs       the other 14 slices (incl. the chain roots rsv_07 / rsv_09, where the q.k fold sits): the stream
//                     arrives on the parent face, status and P.V leave on it
// p4j edges (svc_rs_tree.py): tq = dn stream parent -> child (incl. entry -> chain root 05 -> 07, 11 -> 09); tp = up +
// P.V return child -> parent; tr_07_05 / tr_09_11 = the return lane on the chain-root -> entry edge (`ro` on 07 / 09,
// `ri` on 05 / 11); the q.k partials entry -> root and the fold 07 <-> 09 ride the score exchange (svc_rs_embed.py).
// Content of a slice (one regional clock; every input lands in a flop, every output leaves one):
//   2 x dsfd_svc_pc    (closed, unchanged) the slice's two pseudo-channel faces, abutted to its dsfd_ctrl_rg2
//   dsdv_svc_att       the attention share of head-dim tile t (D = 32 engine, S = 1) + its 2-PC HBM service
//                      (window writer / reader, owned-row fetch, host sector writes, slot-addressed landing)
//   dsdv_svc_sx        the score exchange (q.k balanced 16-tile tree node, scatter, SM-head tap)
//   SE row assembler   the tap's 4 rows x 1 head a beat -> 16-score SE operand rows for the head's SM
//   ot_s81_su_sms     the slice's SM share (S81U-2 smq tap + head subtree; head = tile t): SE rows from the assembler,
//                      parameter / SO rows from SMJ frames, its write rows leave on the SM face
//   dn / up trees      neighbour-only broadcast of {q, hw} from the half's entry (upper row both ways, down each column)
//                      and the reduce of {all done, fault, host credits, host acks} back to it (svc_rs_tree.py role ROM:
//                      parent face, child faces, compiled GO delay gd); 5 cycles a hop (centre register, relay, out pin
//                      flop | in pin flop, relay), as the score exchange
//   hs status          the controller status face hs of the slice's ctrl_rg2 (dsfd_svc_hs's rule, fault half)
// Ports per lanes/S81U-SVC.md: HBM rq 2 x 341 / rk, wd, rv 2 / r_data 2 x 256, r_tag 2 x 17, r_beat 2 x 4 / hs 2;
// score lanes (gather 2,132 b + v, scatter 1,076 b + v) and stream lanes (dn 805 b, up 14 b) on N / E / S / W;
//   P.V return tree    ri / ro (513 b + v a face): the owner slices' P.V words travel child -> parent to the entry in
//                      compiled windows (att drain slot rs_pvslot); every hop 5 cycles; two valid words in one cycle or a
//                      word on a face that is not a child are sticky faults (never arbitrated)
// SM face w_v / w_a 14 / w_m 16 / w_d 512 + status.
// P PATH (TOK-S81-GAPS/SVCP 10-19, die gap G9; GO frame [47:32] PIO != 0, else legacy = PV frame from the host q):
//   the SM's SE e rows (16 FP32 exp of head g = tile, one per 16 positions) are rounded to BF16 (RNE, hdc_golden.to_bf16)
//   into pbuf (40 x 256 b) as they leave the SM.  From share cycle PIO the slice injects one P BEAT every 2 cycles into its
//   score-exchange leaf (beat k = rows 4k .. 4k + 3: head lane g = {P bf16, 16'h0}, every other lane +0, flags 0, row
//   mask = rows < T); the exchange's balanced gather adds x + 0 (exact), so the fold root rsv_09 sees all 16 heads x 4
//   rows a beat (rt).  The root packs the PV frame (header type 5, len ceil(T / 2), the job tag, then word w = rows 2w,
//   2w + 1 x 16 heads BF16) -- one word a cycle -- into its P.V return node: up to its entry rsv_11 (tr_09_11) and across
//   the centre (pout = W face, the abutted lane pr_09_07) to the W chain root rsv_07 (pin = E face), which forwards it to
//   rsv_05 (tr_07_05).  In the P window (share cycles [PIO, PVO)) an entry puts the return-tree words on its dn stream
//   instead of its pv pins: every slice of both halves receives the PV frame exactly as from the host (the owners'
//   p FIFO / static p feed are unchanged).  The tap beats of the P window do not enter the SE assembler.  Static: no
//   credit / ready; sticky fault (lf) on a P beat whose e row is not in pbuf at its cycle, a P beat colliding with an
//   engine score beat, a root beat off the 2-cycle cadence or with a non-BF16 / flagged lane, a pbuf overflow, an
//   injected word colliding with a host q word.  The SO (normalised o) rows go to the on-die SO target (S81-SMWIRE below).
// S81-SMWIRE (10-19): the face is INTERNAL -- the slice's SO target
//   dsdv_sm_so_target (4 SRAM 32x64, tools/s81_dv/sm_target/MODEL.md) takes it; its config comes from the job's SOT
//   q frame (dsdv_svc_sot, type 14), its gather beats leave as 3 words each on this slice's P.V return tree (dsdv_sm_gw,
//   merged with the P.V words: two words in one cycle is the existing fault), its fault joins the slice fault and its
//   booked retire joins the slice done (no END before every configured head retired cleanly).  The entry stamps
//   the booked gather window on the 48 spare bits of its pv lane (pv_x, dsdv_sm_gx).  The w_* ports stay on the core
//   for bench observation only (wrappers expose them under RS_OBS); SMT = 0 builds the pre-SMWIRE slice.
// Entry only: j 33 in, jd 2 out, q 515 in, hw 292 in, hc 9 out, fault out, P.V pv_v + pv_d 513 out.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_rs_c #(
    parameter bit ENTRY = 0,
    parameter integer MUT = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer PV_IDENTITY = 0, parameter bit SMT = 1,
    // S81-P9-FACE (10-23): face mask {SO, SI, GO, GI, RO, RI, UO, UI, DO, DI}, 4 b each, bit f = face N / E / S / W
    // (tools/s81_dv/svc_rs/svc_rs_faces.py from the role ROMs).  A face whose bit is 0 has no flop, relay or logic in
    // this core (generate): its input is never read, its output is constant 0 and the port variant
    // (dsdv_svc_rs_fv.sv) does not carry it.  All ones (default) = the pre-mask slice, unchanged.
    parameter logic [39:0] FM = {40{1'b1}},
    // S81-SVCRS R5 (11-08): heads per engine pass (dsdv_svc_att H).  16 = today's slice; 8 = the half-width slice
    // (32 hcores, 8-head merges, gather lanes 1,076 b, two passes per 16-head op; dsdv_svc_att header).  The default
    // comes from `OT_SVC_HV (-DOT_SVC_H8 = 8, else 16), so every port variant / wrapper builds either form unchanged.
    parameter integer H = `OT_SVC_HV
) (
    input  wire              ck,
    input  wire              rst,
    input  wire [3:0]        sid,
    // half host endpoint (ENTRY only)
    input  wire [32:0]       j,
    output wire [1:0]        jd,
    input  wire [514:0]      q,
    input  wire [291:0]      hw,
    output reg  [8:0]        hc,
    output wire              fault,
    output reg  [1:0]        st_rg,        // region status {fault, live} of the half's controllers (ENTRY only)
    // stream tree faces {W, S, E, N} = [3:0]
    input  wire [4*805-1:0]  dn_i,
    output wire [4*805-1:0]  dn_o,
    input  wire [4*16-1:0]   up_i,         // {rg fault, rg live, done, fault, cr 6, ack 6} a face
    output wire [4*16-1:0]   up_o,
    // P.V return tree faces {W, S, E, N}: {d 513, v}
    input  wire [4*514-1:0]  ri,
    output wire [4*514-1:0]  ro,
    // score lanes
    input  wire [3:0]        gi_v,
    input  wire [4*(H*132+20)-1:0] gi_d,
    output wire [3:0]        go_v,
    output wire [4*(H*132+20)-1:0] go_d,
    input  wire [3:0]        si_v,
    input  wire [4*1076-1:0] si_d,
    output wire [3:0]        so_v,
    output wire [4*1076-1:0] so_d,
    // HBM faces (2 PCs)
    output wire [2*341-1:0]  rq,
    input  wire [1:0]        rk, wd, rv,
    input  wire [2*256-1:0]  r_data,
    input  wire [2*17-1:0]   r_tag,
    input  wire [2*4-1:0]    r_beat,
    input  wire [1:0]        hs,
    // P.V out (ENTRY only: the half's return tree root)
    output reg               pv_v,
    output reg  [512:0]      pv_d,
    output wire [47:0]       pv_x,         // S81-SMWIRE: SO gather-word stamp of the pv word (ENTRY only, else 0)
    // SM face
    output wire              w_v,
    output wire [13:0]       w_a,
    output wire [15:0]       w_m,
    output wire [511:0]      w_d,
    output wire [11:0]       w_st              // {o_rjid 8, o_den, o_alive, o_fo, o_fu}
`ifdef RS_OBS
    // bench observation only (hierarchical bench build: the slice is a hier block): {rt_v, rt_d, se_v, se_d, a_fc, lf}
    , output wire [H*132+566:0] obs
`endif
);

// EXPLICIT INTERFACE TEST DOUBLE ONLY. No mission/arithmetic/physical qualification.
endmodule
