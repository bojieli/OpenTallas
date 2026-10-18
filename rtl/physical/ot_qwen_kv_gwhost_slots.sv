// Qwen ROM TP8 die (track B, KV merged): slot cells of the KV-centre masters qkd_embgw (embedding gateway) and qkd_host
// (host / control port), contract results/arch/hier_contract_1012/qwen_rom_tp8.json (v4b), el1013-qwen-embgw-host
// 2026-10-13.  Each cell is WIRING ONLY around its body: no logic and no flop is added or removed here.
// Packing tables are LSB-FIRST (the first field is bit 0).  A bundle with a bit against the flow is two ports on the
// same face: x (with the flow) + x_cr (the credit, against it).  Bits of a contract bundle that have no body port are
// NOT ports of the cell and are NOT tied off: they are posted as contract questions (el1011-qwen-tp8.log).
//
// ---- qkd_embgw: body ot_qkvd_embgw_m (the unchanged gateway ot_qfd_emb_gw + its merged-die link side) -------------
//   r_ea[25:0]      in   { ea_v, ea_kind, ea_addr[23:0] }                       SU embedding request (W, M5)
//   t_ecr           out  { ea_cr }                                              one credit a request retired
//   t_eq[512:0]     out  { eq_v, eq_d[511:0] }                                  one 512-b response word a request
//   emr_<q>[519:0]  in   { v, data[511:0], sequence[3:0], poison, kind[1:0] }   strip q -> gateway word
//   emr_<q>_cr      in   { strip q consumed one gateway word }                  (travels WITH emr: the strip's i_cr)
//   emf_<q>[287:0]  out  { v, data[280:0], sequence[3:0], kind[1:0] }           gateway -> strip q word
//   emf_<q>_cr      out  { the gateway took one emr_<q> word }                  (travels WITH emf: the strip's o_cr)
//   hb[282:0]       in   { v, end, E[24:0], data[255:0] }                       boot words from qkd_host (NEW bundle)
//   hb_cr           out  { one boot word sent on }                              credit, against hb
//   est[12:0]       out  { emb_ready, fault, cause[10:0] }                      status to qkd_host (NEW bundle)
//   <q> = WS, WN, ES, EN = stack 0, 1, 2, 3 (tools/qwen_kv_die/kv_die.py STACKS order; the landing strip's stack strap
//   st[1:0] must be the same index).  kind: emr 0 CODE / 1 SCALE / 2 STATUS; emf 0 FETCH / 1 BOOT_WR / 2 BOOT_END.
//   Against the landing leaf as built (qkd_land_emb, branch el1013-qwen-kvstrips: emf / emr [529:0] = {credit, 5'b0,
//   {tag 11, data 512}, v}): v = bit 0 and data[j] = bit 1 + j on both sides; sequence = land [516:513]; emr poison =
//   land emr[520]; kind = land [522:521]; credit = land [529].  Land bits [528:524] (always 0), [523] (the link class
//   bit: constant 1, class = queue on this hop), [519:517] (always 0) and emf [512:282] (data[511:281], zero in every
//   gateway word) have no body port on this side.
//   Contract bundles with NO body port (questions posted): gq[529:0], gr[529:0] (the EMBQ / EMBD classes through the
//   sequencer: the SU face ends here directly), t_eq[1023:513] (the 1,024-b ingress: the body answers 512 b a word).
// OT_QKD_SLOT_MUT (bench mutant only, never synthesized): t_eq data bits 100 and 101 swapped (a packing fault).
module qkd_embgw (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [25:0]   r_ea,
    output wire          t_ecr,
    output wire [512:0]  t_eq,
    input  wire [519:0]  emr_WS,
    input  wire          emr_WS_cr,
    output wire [287:0]  emf_WS,
    output wire          emf_WS_cr,
    input  wire [519:0]  emr_WN,
    input  wire          emr_WN_cr,
    output wire [287:0]  emf_WN,
    output wire          emf_WN_cr,
    input  wire [519:0]  emr_ES,
    input  wire          emr_ES_cr,
    output wire [287:0]  emf_ES,
    output wire          emf_ES_cr,
    input  wire [519:0]  emr_EN,
    input  wire          emr_EN_cr,
    output wire [287:0]  emf_EN,
    output wire          emf_EN_cr,
    input  wire [282:0]  hb,
    output wire          hb_cr,
    output wire [12:0]   est
);
    wire [519:0] emr [0:3];
    wire [287:0] emf [0:3];
    assign emr[0] = emr_WS; assign emr[1] = emr_WN; assign emr[2] = emr_ES; assign emr[3] = emr_EN;
    assign emf_WS = emf[0]; assign emf_WN = emf[1]; assign emf_ES = emf[2]; assign emf_EN = emf[3];
    wire [3:0]       lr_v, lr_p, lt_v, lt_cr;
    wire [7:0]       lr_k, lt_k;
    wire [15:0]      lr_s, lt_s;
    wire [4*512-1:0] lr_d;
    wire [4*281-1:0] lt_d;
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_lk
        assign lr_v[q]             = emr[q][0];
        assign lr_d[512*q +: 512]  = emr[q][512:1];
        assign lr_s[4*q +: 4]      = emr[q][516:513];
        assign lr_p[q]             = emr[q][517];
        assign lr_k[2*q +: 2]      = emr[q][519:518];
        assign emf[q]              = {lt_k[2*q +: 2], lt_s[4*q +: 4], lt_d[281*q +: 281], lt_v[q]};
    end endgenerate
    wire         eq_v;
    wire [511:0] eq_d;
    wire [12:0]  st;
    // HEADQ 1 (Q-KVFIX 0130): registered request-FIFO head in the gateway (setup fix, 0 added cycles, same answers)
`ifdef OT_QKD_HEADQ_MUT
    localparam integer BODY_MUT = 6;            // bench mutant only: stale head register
`else
    localparam integer BODY_MUT = 0;
`endif
    ot_qkvd_embgw_m #(.RQD(32), .OD(4), .TXC(4), .BD(4), .MUT(BODY_MUT), .HEADQ(1)) u_body (
        .ck(ck), .rst_n(rst_n),
        .ea_v(r_ea[0]), .ea_kind(r_ea[1]), .ea_addr(r_ea[25:2]), .ea_cr(t_ecr), .eq_v(eq_v), .eq_d(eq_d),
        .lr_v(lr_v), .lr_k(lr_k), .lr_p(lr_p), .lr_s(lr_s), .lr_d(lr_d),
        .lr_cr({emr_EN_cr, emr_ES_cr, emr_WN_cr, emr_WS_cr}),
        .lt_v(lt_v), .lt_k(lt_k), .lt_s(lt_s), .lt_d(lt_d),
        .lt_cr({emf_EN_cr, emf_ES_cr, emf_WN_cr, emf_WS_cr}),
        .hb_v(hb[0]), .hb_end(hb[1]), .hb_e(hb[26:2]), .hb_d(hb[282:27]), .hb_cr(hb_cr),
        .st(st));
`ifdef OT_QKD_SLOT_MUT
    assign t_eq = {eq_d[511:102], eq_d[100], eq_d[101], eq_d[99:0], eq_v};
`else
    assign t_eq = {eq_d, eq_v};
`endif
    assign est = {st[12:2], st[1], st[0]};
endmodule
