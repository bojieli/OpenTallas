`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B ROM TP8 die (track B), KV landing strip qkd_land / qkd_land_n (el1013-qwen-kvstrips 2026-10-13).
// The 172.776 x 12,141.312 strip slot (one 26,789-flop KV merge + one 39,613-flop embedding engine + the landing
// crossbar that had no RTL) becomes hardened leaves, each with its own clock root (core clock):
//   32 x qkd_land_pc   one a pseudo-channel (E half of the strip, 86.4 x 172.8 beside the PC's CDC and controller leaf)
//    8 x qkd_land_grp  one a row engine (W half, 86.4 x 302.4 at the middle of its four PCs)
//    1 x qkd_land_emb  the embedding strip engine ot_qkvd_emb_strip_c (N end)
// SLOT ORDER (die contract, requested with these masters): a KV row (layer, g, v, t) is 4 sectors at the same PC-local
// index j on the logical PCs {q, G} = 8 q + G, G = t[2:0] = its row engine (CONTRACT map v2).  The four PCs of an engine
// must sit together, so strip slot 4 i + q hosts logical PC {q, G(i)} (i = 0..7 from the S end; G(i) is the die lead's
// choice, e.g. 4 5 0 1 2 3 6 7 puts every group beside its engine's rq / rs pins).  The physical PC of slot s stays s
// (qkd_ctrl_pc strap pc = s: refresh phase / row slot); the LOGICAL index is the strap lpc of qkd_land_pc (and the lane
// strap of the write-queue leaf).
//
// READ PATH (the landing crossbar, new).  Each PC streams its layer region in index order j = 0..1,023 (the stream
// order of ot_hbm_r14_stream_pc_*; tb_hbm_stream_bw CONS 1) through its CDC (credit landing, LCRED 6):
//   qkd_land_pc: pin flops -> 6-word queue -> the word {data 256, j 10, layer 6} to its group under 4 credits;
//   qkd_land_grp: per PC a 4-word queue; when the four heads are there (they must agree on {layer, j}: fault if not):
//     * the layer after the current one (its stream may land before lt) -> the row waits
//     * any other layer than the current one, or position t >= T     -> the row is dropped (stale tail / beyond T)
//     * the oldest row request the KV merge released is for index j -> the 1,024-b row goes to the merge (h_rsp)
//     * that request is for a later index                            -> the row is dropped (not requested)
//     * that request is for an earlier index                         -> fault (the engines ask in stream order)
//     one row a cycle either way; the engine side (rq / rs, the write-then-read fence, the kept rows) is
//     ot_qkvd_kv_merge #(.E(1)) UNCHANGED.  Position of row j in group G of stack S:
//     t = {j[6:3], S, j[7], j[2:0], G} (j = {v, g, t[6], t[12:9], t[5:3]}).
// EMBEDDING (ot_qkvd_emb_strip_c, see its header): a down chain (static commands / POPs), an up chain (popped
// beats), a 32-b credit chain and the strip's fault chain run N <-> S through the 32 qkd_land_pc leaves by abutment
// (one flop a leaf, 378 um a hop); each leaf drives its PC's static port (es) and keeps its 8-beat return FIFO.
// Every port of every leaf is a flop at the pin (inputs captured with no logic, outputs driven from a register).
// ---------------------------------------------------------------------------------------------------------------------

// ---- one pseudo-channel: CDC landing port, group port, embedding static port and chains ----------------------------
// li  [281:0] in   E  CDC co minus l_pop: {l_data 256, l_row 8, l_sec 17, l_v}   lp out E  l_pop (credit, one a word)
// cf          in   E  CDC c_fault
// gw  [272:0] out  W  to qkd_land_grp: {data 256, j 10, layer 6, v}              gc in  W  credit (one a word taken)
// es  [287:0] out  E  static command to qkd_ctrl_pc      er [260:0] in E  {fault_core, s_credit, beat 258, e_v}
// dni  [297:0] in N / dno out S   down chain;   upi [261:0] in S / upo out N   up chain
// cri [31:0]  in S / cro out N   credit chain (bit = logical PC);   fi in S / fo out N   fault chain
// lpc [4:0]   strap: the logical PC {q, G}
// MUT (bench): 1 = the landed word's j bit 0 inverted towards the group; 2 = POP answered with the newest beat.
module qkd_land_pc #(
    parameter integer LCRED = 6,           // the CDC's landing credit (ot_qwen_stream4_cdc_pc MARGIN 1)
    parameter integer GC    = 4,           // credits of the group port
    parameter integer PFD   = 8,           // return beats kept: the engine queues 4 tokens, a PC holds <= 4 code + 4 scale beats
    parameter integer MUT   = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [4:0]   lpc,
    input  wire [281:0] li,
    output reg          lp,
    input  wire         cf,
    output reg  [272:0] gw,
    input  wire         gc,
    output reg  [287:0] es,
    input  wire [260:0] er,
    input  wire [297:0] dni,
    output reg  [297:0] dno,
    input  wire [261:0] upi,
    output reg  [261:0] upo,
    input  wire [31:0]  cri,
    output reg  [31:0]  cro,
    input  wire         fi,
    output reg          fo
);
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [4:0] lpc_q;                                // strap through a pin flop
    always @(posedge ck) lpc_q <= lpc;
    // ---- landing: pin flops, queue, group port -----------------------------------------------------------------------
    (* keep *) reg         lv_q, gc_q, cf_q;
    (* keep *) reg [271:0] lw_q;                               // {data, j, layer}
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin lv_q <= 1'b0; gc_q <= 1'b0; cf_q <= 1'b0; end
        else begin lv_q <= li[0]; gc_q <= gc; cf_q <= cf; end
    // l_sec = {layer 6, j[9:7], 1'b0, j[6:0]} (qkd_ctrl_pc)
    always @(posedge ck) lw_q <= {li[281:26], li[11:9], li[7:1], li[17:12]};
    localparam integer QA = $clog2(LCRED);
    reg [271:0] lq [0:LCRED-1];
    reg [QA-1:0] lqw, lqr;
    reg [QA:0]   lqn;
    reg [2:0]    gcr;
    reg          f_land;
    wire         l_take = lqn != 0 && gcr != 3'd0;
    wire [271:0] l_head = lq[lqr];
    always @(posedge ck) if (lv_q) lq[lqw] <= lw_q;
    always @(posedge ck) if (l_take) gw[272:1] <= (MUT == 1) ? (l_head ^ 272'd64) : l_head;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin lqw <= 0; lqr <= 0; lqn <= 0; gcr <= 3'(GC); lp <= 1'b0; gw[0] <= 1'b0; f_land <= 1'b0; end
        else begin
            if (lv_q) begin lqw <= (lqw == QA'(LCRED - 1)) ? {QA{1'b0}} : lqw + 1'b1; if (lqn == (QA+1)'(LCRED) && !l_take) f_land <= 1'b1; end
            if (l_take) lqr <= (lqr == QA'(LCRED - 1)) ? {QA{1'b0}} : lqr + 1'b1;
            lqn <= lqn + {{QA{1'b0}}, lv_q} - {{QA{1'b0}}, l_take};
            gcr <= gcr - {2'd0, l_take} + {2'd0, gc_q};
            lp <= l_take; gw[0] <= l_take;
        end
    // ---- embedding: chains, static port, return FIFO -----------------------------------------------------------------
    (* keep *) reg [297:0] dni_q;
    (* keep *) reg [261:0] upi_q;
    (* keep *) reg [31:0]  cri_q;
    (* keep *) reg [260:0] er_q;
    (* keep *) reg         fi_q;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin dni_q[0] <= 1'b0; upi_q[0] <= 1'b0; cri_q <= 32'd0; er_q[0] <= 1'b0; er_q[260:259] <= 2'd0; fi_q <= 1'b0; end
        else begin dni_q[0] <= dni[0]; upi_q[0] <= upi[0]; cri_q <= cri; er_q[0] <= er[0]; er_q[260:259] <= er[260:259]; fi_q <= fi; end
    always @(posedge ck) begin dni_q[297:1] <= dni[297:1]; upi_q[261:1] <= upi[261:1]; er_q[258:1] <= er[258:1]; end
    wire d_v = dni_q[0], d_pop = dni_q[1], d_bc = dni_q[2];
    wire d_me = d_v && (dni_q[7:3] == lpc_q);
    localparam integer PA = $clog2(PFD);
    reg [257:0] rf [0:PFD-1];
    reg [PA:0]  rfw, rfr;
    reg [2:0]   pq [0:3];                                      // POPs waiting for their beat: {tag 2, side}, in order
    reg [2:0]   pqw, pqr;
    reg         f_emb;
    wire        pp = pqw != pqr;
    wire        pq_full = pqw[1:0] == pqr[1:0] && pqw[2] != pqr[2];
    wire        r_ne = rfw != rfr;
    wire        r_full = rfw[PA-1:0] == rfr[PA-1:0] && rfw[PA] != rfr[PA];
    wire        u_go = pp && r_ne && !upi_q[0];                 // answer when no farther beat is passing
    wire [PA-1:0] r_sel = (MUT == 2) ? rfw[PA-1:0] - 1'b1 : rfr[PA-1:0];
    always @(posedge ck) begin
        dno[297:1] <= dni_q[297:1];
        es[287:1] <= {dni_q[10:9], dni_q[15:11], dni_q[20:16], dni_q[39:21], dni_q[295:40]};   // {w_v, s_we, bank, col, row, w_d}
        if (er_q[0]) rf[rfw[PA-1:0]] <= er_q[258:1];
        if (upi_q[0]) upo[261:1] <= upi_q[261:1]; else upo[261:1] <= {rf[r_sel], pq[pqr[1:0]]};
        if (d_me && d_pop) pq[pqw[1:0]] <= {dni_q[297:296], dni_q[8]};
    end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin
            dno[0] <= 1'b0; es[0] <= 1'b0; upo[0] <= 1'b0; cro <= 32'd0; fo <= 1'b0; rfw <= 0; rfr <= 0; pqw <= 3'd0; pqr <= 3'd0; f_emb <= 1'b0;
        end else begin
            dno[0] <= d_v;
            es[0] <= d_v && !d_pop && (d_bc || dni_q[7:3] == lpc_q);
            if (er_q[0]) begin rfw <= rfw + 1'b1; if (r_full) f_emb <= 1'b1; end
            if (d_me && d_pop) begin pqw <= pqw + 3'd1; if (pq_full) f_emb <= 1'b1; end
            if (u_go) begin rfr <= rfr + 1'b1; pqr <= pqr + 3'd1; end
            upo[0] <= upi_q[0] | u_go;
            cro <= cri_q | ({31'd0, er_q[259]} << lpc_q);
            fo <= fi_q | cf_q | er_q[260] | f_land | f_emb;
        end
endmodule

// ---- one row engine's landing: four PC ports, the row matcher, the KV merge slice ----------------------------------
// gw0..3 [272:0] in E / gc0..3 out E      the four qkd_land_pc of the group (q = 0..3: row[256 q +: 256])
// rq [15:0] in W = {req_t 13, req_g, req_v, req_valid}      rs [1024:0] out W = {row 1024, rsp_valid}      (qkd_ectl rq / rs)
// lt [20:0] in  = {lay_idx 6, lay_T 14, lay_start}          kn [1046:0] in = {kvw_d 1024, kvw_layer 6, kvw_t 14, kvw_vg 2, kvw_v}
// g [2:0], s [1:0] straps (row engine / stack);  fi in / fo out: fault chain
// MUT (bench): 1 = ot_qkvd_kv_merge MUT 1 (no merge); 2 = rows beyond T are not dropped; 3 = unrequested rows are delivered.
module qkd_land_grp #(
    parameter integer DQ  = 32,            // the engine's outstanding-row credit (qkd_ectl DQ)
    parameter integer GC  = 4,
    parameter integer NL  = 36,            // layers a token (the layer after NL - 1 is 0)
    parameter integer EPOCH = 0,          // requests carry layer parity; legacy frozen masters remain 16-bit
    parameter integer RH  = 0,            // 1: merge request / pending-tag queues read from a head register (cycle-identical)
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    g,
    input  wire [1:0]    s,
    input  wire [272:0]  gw0,
    input  wire [272:0]  gw1,
    input  wire [272:0]  gw2,
    input  wire [272:0]  gw3,
    output wire          gc0,
    output wire          gc1,
    output wire          gc2,
    output wire          gc3,
    input  wire [15+EPOCH:0] rq,
    output wire [1024:0] rs,
    input  wire [20:0]   lt,
    input  wire [1046:0] kn,
    input  wire          fi,
    output reg           fo
);
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [2:0] g_q;                                  // straps through pin flops
    (* keep *) reg [1:0] s_q;
    always @(posedge ck) begin g_q <= g; s_q <= s; end
    reg  [3:0]   gc;
    assign {gc3, gc2, gc1, gc0} = gc;
    wire [272:0] gw [0:3];
    assign gw[0] = gw0; assign gw[1] = gw1; assign gw[2] = gw2; assign gw[3] = gw3;
    // ---- per PC: pin flops and a GC-word queue -----------------------------------------------------------------------
    localparam integer GA = $clog2(GC);
    wire [3:0]   hv, qovf;
    wire [271:0] hw [0:3];
    wire         take;
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_pc
        (* keep *) reg         v_q;
        (* keep *) reg [271:0] w_q;
        always @(posedge ck or negedge rn_q) if (!rn_q) v_q <= 1'b0; else v_q <= gw[q][0];
        always @(posedge ck) w_q <= gw[q][272:1];
        reg [271:0]  m [0:GC-1];
        reg [GA-1:0] wp, rp;
        reg [GA:0]   n;
        always @(posedge ck) if (v_q) m[wp] <= w_q;
        always @(posedge ck or negedge rn_q)
            if (!rn_q) begin wp <= 0; rp <= 0; n <= 0; end
            else begin
                if (v_q) wp <= wp + 1'b1;
                if (take) rp <= rp + 1'b1;
                n <= n + {{GA{1'b0}}, v_q} - {{GA{1'b0}}, take};
            end
        assign hv[q] = n != 0;
        assign hw[q] = m[rp];
        assign qovf[q] = v_q && n == (GA+1)'(GC) && !take;
    end endgenerate
    // ---- layer context (the merge keeps its own copy) and the released requests ----------------------------------------
    reg          ls_q, cur_v;
    reg [13:0]   T_q, T_cur;
    reg [5:0]    L_q, L_cur, L_nxt;
    always @(posedge ck) begin T_q <= lt[14:1]; L_q <= lt[20:15]; end
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin ls_q <= 1'b0; cur_v <= 1'b0; T_cur <= 14'd0; L_cur <= 6'd0; L_nxt <= 6'd0; end
        else begin
            ls_q <= lt[0];
            if (ls_q) begin cur_v <= 1'b1; T_cur <= T_q; L_cur <= L_q; L_nxt <= (L_q == 6'(NL - 1)) ? 6'd0 : L_q + 6'd1; end
        end
    wire         h_req_valid, h_req_v, h_req_g, m_fault;
    wire [12:0]  h_req_t;
    wire [9:0]   rq_j = {h_req_v, h_req_g, h_req_t[6], h_req_t[12:9], h_req_t[5:3]};
    localparam integer RA = $clog2(DQ);
    reg [9:0]    rqm [0:DQ-1];
    reg [RA-1:0] rw, rr;
    reg [RA:0]   rn;
    wire         r_any = rn != 0;
    wire [9:0]   r_j = rqm[rr];
    // ---- the row at the four heads -----------------------------------------------------------------------------------
    wire         all = &hv;
    wire [5:0]   h_l = hw[0][5:0];
    wire [9:0]   h_j = hw[0][15:6];
    wire         agree = hw[1][15:0] == hw[0][15:0] && hw[2][15:0] == hw[0][15:0] && hw[3][15:0] == hw[0][15:0];
    wire [12:0]  h_t = {h_j[6:3], s_q, h_j[7], h_j[2:0], g_q};
    // a row of the layer that starts next (its stream may land before lt) WAITS; any other layer is a stale tail
    wire         cur    = cur_v && h_l == L_cur;
    wire         stale  = cur_v && h_l != L_cur && h_l != L_nxt;
    wire         beyond = {1'b0, h_t} >= T_cur && MUT != 2;
    wire         hit    = r_any && r_j == h_j;
    wire         early  = r_any && r_j > h_j && MUT != 3;      // the row is not asked for
    wire         late   = r_any && r_j < h_j;                  // the request's row has passed
    wire         deliver = all && agree && cur && !beyond && (hit || (MUT == 3 && r_any && !late));
    wire         drop    = all && agree && (stale || (cur && (beyond || early)));
    assign take = deliver || drop;
    reg          f_grp;
    (* keep *) reg fi_q;
    always @(posedge ck or negedge rn_q) if (!rn_q) fi_q <= 1'b0; else fi_q <= fi;
    always @(posedge ck) if (h_req_valid) rqm[rw] <= rq_j;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin rw <= 0; rr <= 0; rn <= 0; gc <= 4'd0; f_grp <= 1'b0; fo <= 1'b0; end
        else begin
            if (h_req_valid) rw <= rw + 1'b1;
            if (deliver) rr <= rr + 1'b1;
            rn <= rn + {{RA{1'b0}}, h_req_valid} - {{RA{1'b0}}, deliver};
            gc <= {4{take}};
            if ((all && !agree) || (all && agree && cur && !beyond && late) || (|qovf) || (h_req_valid && rn == (RA+1)'(DQ)) || epoch_fault)
                f_grp <= 1'b1;
            fo <= fi_q | f_grp | m_fault;
        end
    // STATIC layer context (owner rule 2026-10-14 18:59: compiler-scheduled cycles, no runtime hold / readiness wait).
    // The compiler issues lt so that it reaches the lt pin no later than the edge the layer's first request reaches the
    // rq pin (and after the previous layer's last request has been answered). The request is pin-registered and goes straight to the
    // merge; bit 16 (layer parity) is CHECKED against the registered current context: a request that arrives before its
    // layer's lt (or a previous-layer request after it) latches the sticky group fault. It never waits, so a schedule
    // error cannot silently stretch the timeline or be attributed to the wrong layer. (f2cf210f4's 128-entry hold queue,
    // a readiness wait, is withdrawn.)
    wire [15:0] rq_release;
    wire epoch_fault;
    generate if (EPOCH != 0) begin : g_epoch_check
        (* keep *) reg v_pin;
        (* keep *) reg [15:0] d_pin;
        always @(posedge ck) d_pin <= rq[16:1];
        always @(posedge ck or negedge rn_q)
            if (!rn_q) v_pin <= 1'b0; else v_pin <= rq[0];
        assign rq_release = {d_pin[14:0], v_pin};
        assign epoch_fault = v_pin && (!cur_v || ls_q || d_pin[15] != L_cur[0]) && MUT != 4;
    end else begin : g_legacy_request
        assign rq_release = rq[15:0];
        assign epoch_fault = 1'b0;
    end endgenerate
    // ---- the KV merge slice (requests, fence, kept rows, merged response): unchanged module ---------------------------
    wire [1023:0] h_row = {hw[3][271:16], hw[2][271:16], hw[1][271:16], hw[0][271:16]};
    wire          e_rsp_valid;
    wire [1023:0] e_rsp_data;
    ot_qkvd_kv_merge #(.HD(128), .E(1), .DQ(DQ), .RH(RH), .MUT(MUT == 1 ? 1 : 0)) u_m (
        .clk(ck), .rst_n(rn_q), .lay_start(lt[0]), .lay_T(lt[14:1]), .lay_idx(lt[20:15]),
        .kvw_v(kn[0]), .kvw_vg(kn[2:1]), .kvw_t(kn[16:3]), .kvw_layer(kn[22:17]), .kvw_d(kn[1046:23]),
        .e_req_valid(rq_release[0]), .e_req_v(rq_release[1]), .e_req_g(rq_release[2]), .e_req_t(rq_release[15:3]),
        .h_req_valid(h_req_valid), .h_req_v(h_req_v), .h_req_g(h_req_g), .h_req_t(h_req_t),
        .h_rsp_valid(deliver), .h_rsp_data(h_row), .e_rsp_valid(e_rsp_valid), .e_rsp_data(e_rsp_data), .fault(m_fault));
    assign rs = {e_rsp_data, e_rsp_valid};
endmodule

// ---- the strip's embedding engine and chain ends -------------------------------------------------------------------
// emf [529:0] in  = {o_cr (the gateway took a word of emr), 5'b0, i_d 523 = {tag 11, data 512}, i_v}   (die bus W + 2)
// emr [529:0] out = {i_cr (this engine took a word of emf), 5'b0, o_d 523, o_v}
// dno [297:0] out S: down chain;  upi [261:0] in S: up chain;  cri [31:0] in S: credit chain;  fi in S: the PC leaves'
// fault chain;  gfi in S: the group leaves' fault chain;  mf out: the strip's fault;  st [1:0] strap: the stack
module qkd_land_emb #(
    parameter integer MUT = 0
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [1:0]   st,
    input  wire [529:0] emf,
    output wire [529:0] emr,
    output wire [297:0] dno,
    input  wire [261:0] upi,
    input  wire [31:0]  cri,
    input  wire         fi,
    input  wire         gfi,
    output reg          mf
);
    (* keep *) reg rn_q;
    always @(posedge ck) rn_q <= rst_n;
    (* keep *) reg [1:0] st_q;                                 // strap through a pin flop
    always @(posedge ck) st_q <= st;
    (* keep *) reg         iv_q, ocr_q, fi_q, gfi_q;
    (* keep *) reg [522:0] id_q;
    (* keep *) reg [261:0] upi_q;
    (* keep *) reg [31:0]  cri_q;
    always @(posedge ck or negedge rn_q)
        if (!rn_q) begin iv_q <= 1'b0; ocr_q <= 1'b0; fi_q <= 1'b0; gfi_q <= 1'b0; upi_q[0] <= 1'b0; cri_q <= 32'd0; end
        else begin iv_q <= emf[0]; ocr_q <= emf[529]; fi_q <= fi; gfi_q <= gfi; upi_q[0] <= upi[0]; cri_q <= cri; end
    always @(posedge ck) begin id_q <= emf[523:1]; upi_q[261:1] <= upi[261:1]; end
    wire         o_v, e_fault, ecf;
    wire [522:0] o_d;
    // the stack is a strap: the engine is built for stack 0 and the two address checks that use STK are made here
    ot_qkvd_emb_strip_c #(.STK(0), .MUT(MUT)) u_e (
        .clk(ck), .rst_n(rn_q), .i_v(iv_q), .i_d(id_q), .i_cr(ecf), .o_v(o_v), .o_d(o_d), .o_cr(ocr_q),
        .dn(dno), .s_cr(cri_q), .up(upi_q), .fault(e_fault), .fault_code(), .ce_cnt(), .ue_info(), .stk(st_q));
    assign emr = {ecf, 5'd0, o_d, o_v};
    always @(posedge ck or negedge rn_q) if (!rn_q) mf <= 1'b0; else mf <= fi_q | gfi_q | e_fault;
endmodule
