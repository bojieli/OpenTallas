`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B ROM TP8, track B (ONE die type: the KV die is merged into the ROM die), 2026-10-13: the merged-die KV
// sequencer (die master qkd_seq).
//
// On the two-die design the ROM end (ot_qkvd_rom_end: x3 / dc buffers, class split, ar / dh credit senders) and the KV
// sequencer (ot_qkvd_kv_seq) talked through two ot_qkvd_d2d adapters and the UCIe pair.  On the merged die the D2D
// pair is a wire (tools/qwen_rom_fulldie_b3r2.py KV_DROP / KV_SHORT), so the ROM-end faces end directly on the
// sequencer: this file is the existing sequencer + the ROM-end buffers WITHOUT the adapters.
//
// ROM-side faces (every word has valid, tag and credit; no same-cycle ready anywhere):
//   x3    {v, tag 11, d 512} in, x3_cr out.  tag[10:8] class: 001 Q (tag[5:0] beat), 010 KVN (tag[2:0] {v, g, half});
//         any other class is a sticky fault.  ONE credit pool of XS = 40 words = one layer (8 KVN + 32 Q, any order
//         inside the layer): the words split on arrival into the Q FIFO (depth XS) and the KVN FIFO (depth 8), a credit
//         returns per word the sequencer takes.  With layer-ordered traffic neither FIFO can overflow (the Q FIFO holds
//         at most XS words by the credit, the KVN FIFO at most 8: a word of layer n + 2 needs a word of layer n + 1
//         taken first, and layer n + 1's KVN words are the first it takes).
//   dc    {v, d 528} in, dc_cr out: the ROM sequencer's CTL words (ATTN / TOKEN / CSR_RSP), CD = 4 credits.
//   kvd   {kvd_v, kvd_kindk, kvd_pos 18, kvd_wbase 24} in (posted): the ROM sequencer's KV-op descriptor
//         (ot_qfd_seq_su_bi kvd_*).  A score descriptor (kindk = 1) LAUNCHES the layer's attention step: T = pos + 1,
//         layer = wbase[11:6] (K of layer l is block l of 64 words: rtl/qwen_sys/ot_qwen_sys_kv_svc.sv kvd_blk).  The
//         weighted-sum descriptor (kindk = 0) of the same position launches nothing (the near-HBM attention does both
//         passes); one for another position is a fault.  At most 2 launches wait (a third is a fault).  An ATTN word on
//         dc is accepted as well (the two-die format; the layer bench drives either).
//   ar    {v, d 519} out, ar_cr in: RES words {g, beat, 16 FP32} to the VM.  The attention hub has no ready, so a
//         layer starts only with all 64 of its RES credits in hand (OCR_AR = 64 = the VM's promise): no RES buffer.
//   dh    {v, d 528} out, dh_cr in: host-control words to the ROM sequencer (OCR_DH credits).
//   pw    {v, addr 10, data 64} out (posted): program writes to the ROM control tile (tt_ctlm pw_*).  A host-control
//         word with op 5 (tag[15:12]) is a program write {data[73:64] address, data[63:0] slice}: it leaves on pw and
//         is NOT forwarded on dh.
//   rflt  {fault, cause 8} out: sticky fault to the ROM sequencer (same fault as kst to the host).
// KV side: as ot_qkvd_kv_seq (attention start / T / layer / q beats, RES in, posted KV rows, stream commands, host,
// token), with FOUR registered copies of aq / kvn / kc (one per quadrant) and a CREDIT JOIN for the posted rows: each
// of the four landing write queues returns one credit per row; the sequencer's row credit returns when all four did.
// Gone on the merged die (no peer; contract v4 has no qkd_d2d / qfd_d2d_rom slot): the D2D faces c_* / u_* (slot rf /
// tf), d2d_fault / d2d_cause (slot d2df), and the embedding classes EMBQ / EMBD (slot gq / gr): the SU's embedding
// face ends on the gateway (KV_SHORT emb / emb_a / emb_cr -> qkd_embgw t_eq / r_ea / t_ecr).
//
// Structure (the hardened leaves of the qkd_seq cluster, rtl/physical/ot_qwen_kv_centre_slots.sv, are these bodies):
//   ot_qkvd_seq_m_ctl    control: FSM, CTL FIFO, tag FIFOs, launcher, RES path, host / token bridges, credit join
//   ot_qkvd_seq_m_store  x3 data storage (Q FIFO, KVN FIFO, the 8 KVN words), DW bits wide (cluster: 4 x 128)
//   ot_qkvd_seq_m_fan    one quadrant's pin registers (aq, kvn, kc out; credit and faults back)
// Latency against ot_qkvd_kv_seq: aq / kvn words + 4 cycles (control out, store in, store out, fan in, fan out),
// kc + 2, credits and faults back + 2.  Every hop is register -> wire -> register.
// MUT (bench only): 2 Q beats 0 / 1 swapped, 3 launcher layer + 1, 4 credit join = OR, 5 program write also on dh.
// ---------------------------------------------------------------------------------------------------------------------

// credit bridge with the program-write tap: as ot_qkvd_cbridge; a word with op 5 leaves on pw_* (no consumer credit)
module ot_qkvd_cbridge_pw #(
    parameter integer W  = 528,
    parameter integer D  = 4,
    parameter integer OC = 4,
    parameter integer FWD_PW = 0                  // mutant: the program write is forwarded as well
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_v,
    input  wire [W-1:0] in_d,
    output reg          in_cr,
    output reg          out_v,
    output reg  [W-1:0] out_d,
    input  wire         out_cr,
    output reg          pw_v,
    output reg  [9:0]   pw_addr,
    output reg  [63:0]  pw_data,
    output reg          fault
);
    reg         iv, cq;
    reg [W-1:0] id;
    always @(posedge clk) id <= in_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin iv <= 1'b0; cq <= 1'b0; end else begin iv <= in_v; cq <= out_cr; end
    wire         empty, full;
    wire [W-1:0] head;
    reg  [7:0]   oc;
    wire         is_pw = (head[W-1 -: 4] == 4'd5);
    wire         fwd   = !is_pw || (FWD_PW != 0);
    wire         pop   = !empty && (!fwd || oc != 0);
    ot_qkvd_fifo #(.W(W), .D(D)) u_q (.clk(clk), .rst_n(rst_n), .push(iv), .din(id), .pop(pop), .dout(head),
                                      .empty(empty), .full(full), .count());
    always @(posedge clk) begin
        if (pop && fwd) out_d <= head;
        if (pop && is_pw) begin pw_addr <= head[73:64]; pw_data <= head[63:0]; end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin out_v <= 1'b0; pw_v <= 1'b0; in_cr <= 1'b0; oc <= 8'(OC); fault <= 1'b0; end
        else begin
            out_v <= pop && fwd;
            pw_v  <= pop && is_pw;
            in_cr <= pop;
            oc <= oc - ((pop && fwd) ? 8'd1 : 8'd0) + (cq ? 8'd1 : 8'd0);
            if (iv && full && !pop) fault <= 1'b1;
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_ctl #(
    parameter integer W      = 528,
    parameter integer XS     = 40,                // x3 credits = Q FIFO depth (one layer: 8 KVN + 32 Q)
    parameter integer KD     = 8,
    parameter integer CD     = 4,
    parameter integer HCD    = 4,
    parameter integer TKC    = 4,
    parameter integer KWC    = 4,                 // row credits of each landing write queue
    parameter integer OCR_AR = 64,                // RES credits of the VM (>= 64: one layer)
    parameter integer OCR_DH = 4,
    parameter integer KDESC  = 1,
    parameter integer KD_PMID = 0,
    parameter integer KD_PTOK = 0,
    parameter integer MUT    = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // ROM side
    input  wire          x3_v,
    input  wire [10:0]   x3_tag,
    output reg           x3_cr,
    input  wire          dc_v,
    input  wire [W-1:0]  dc_d,
    output reg           dc_cr,
    input  wire [43:0]   kvd,                     // {v, kindk, pos 18, wbase 24}
    output reg           ar_v,
    output reg  [518:0]  ar_d,
    input  wire          ar_cr,
    output wire          dh_v,
    output wire [W-1:0]  dh_d,
    input  wire          dh_cr,
    output wire          pw_v,
    output wire [9:0]    pw_addr,
    output wire [63:0]   pw_data,
    output reg           rflt,
    output reg  [7:0]    rflt_cause,
    // store control
    output reg           s_qpop,
    output reg           s_kpop,
    output reg  [2:0]    s_kidx,
    output reg           s_kwgo,
    output reg  [1:0]    s_kwn,
    // fan control: two registered copies (0 = W quadrants, 1 = E quadrants)
    (* keep = "true", dont_touch = "true" *) output reg  [2*28-1:0] f_aqm,                 // {start, T 14, layer 6, q valid, beat 6}
    (* keep = "true", dont_touch = "true" *) output reg  [2*23-1:0] f_kwm,                 // {v, vg 2, t 14, layer 6}
    (* keep = "true", dont_touch = "true" *) output reg  [2*33-1:0] f_kc,                  // {v, d 32}
    input  wire [3:0]    f_cr,                    // row credit of quadrant k (through its fan)
    input  wire [3:0]    f_af,
    input  wire [3:0]    f_mf,
    // attention hub
    output reg           hs,                      // start, the cycle the fans' aq start leaves
    input  wire          a_out_valid,
    input  wire          a_out_g,
    input  wire [5:0]    a_out_beat,
    input  wire [511:0]  a_out_data,
    input  wire          a_hub_fault,
    // host
    input  wire          hc_v,
    input  wire [W-1:0]  hc_d,
    output wire          hc_cr,
    output wire          tok_v,
    output wire [W-1:0]  tok_d,
    input  wire          tok_cr,
    output reg           fault,
    output reg  [8:0]    fault_cause
);
    // ---- boundary capture ----
    reg           xv, cv, kv, ov, og, ucq, hfq;
    reg  [10:0]   xt;
    reg  [W-1:0]  cd;
    reg  [42:0]   kr;
    reg  [5:0]    ob;
    reg  [511:0]  od;
    reg  [3:0]    crq, afq, mfq;
    always @(posedge clk) begin xt <= x3_tag; cd <= dc_d; kr <= kvd[42:0]; ob <= a_out_beat; od <= a_out_data; og <= a_out_g; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin xv <= 1'b0; cv <= 1'b0; kv <= 1'b0; ov <= 1'b0; ucq <= 1'b0; hfq <= 1'b0; crq <= 4'd0; afq <= 4'd0; mfq <= 4'd0; end
        else begin xv <= x3_v; cv <= dc_v; kv <= kvd[43]; ov <= a_out_valid; ucq <= ar_cr; hfq <= a_hub_fault; crq <= f_cr; afq <= f_af; mfq <= f_mf; end
    // ---- CTL FIFO, x3 tag FIFOs (the data words sit in the store, pushed and popped in step) ----
    wire          x_q  = (xt[10:8] == 3'b001), x_kv = (xt[10:8] == 3'b010);
    wire [2:0]    ib_empty, ib_full;
    wire [W-1:0]  ctl_w;
    wire [5:0]    q_tag;
    wire [2:0]    k_tag;
    reg  [2:0]    ib_pop;
    ot_qkvd_fifo #(.W(W), .D(CD)) u_ctl (.clk(clk), .rst_n(rst_n), .push(cv), .din(cd), .pop(ib_pop[0]),
        .dout(ctl_w), .empty(ib_empty[0]), .full(ib_full[0]), .count());
    ot_qkvd_fifo #(.W(6), .D(XS)) u_qt (.clk(clk), .rst_n(rst_n), .push(xv && x_q), .din(xt[5:0]), .pop(ib_pop[1]),
        .dout(q_tag), .empty(ib_empty[1]), .full(ib_full[1]), .count());
    ot_qkvd_fifo #(.W(3), .D(KD)) u_kt (.clk(clk), .rst_n(rst_n), .push(xv && x_kv), .din(xt[2:0]), .pop(ib_pop[2]),
        .dout(k_tag), .empty(ib_empty[2]), .full(ib_full[2]), .count());
    // ---- host words (-> dh, program writes -> pw) and non-ATTN CTL words (-> host) ----
    wire hc_f, tk_f, tk_icr;
    ot_qkvd_cbridge_pw #(.W(W), .D(HCD), .OC(OCR_DH), .FWD_PW(MUT == 5 ? 1 : 0)) u_hc (.clk(clk), .rst_n(rst_n), .in_v(hc_v),
        .in_d(hc_d), .in_cr(hc_cr), .out_v(dh_v), .out_d(dh_d), .out_cr(dh_cr), .pw_v(pw_v), .pw_addr(pw_addr),
        .pw_data(pw_data), .fault(hc_f));
    reg          tk_in_v;
    reg  [W-1:0] tk_in_d;
    ot_qkvd_cbridge #(.W(W), .D(4), .OC(TKC)) u_tk (.clk(clk), .rst_n(rst_n), .in_v(tk_in_v), .in_d(tk_in_d),
        .in_cr(tk_icr), .out_v(tok_v), .out_d(tok_d), .out_cr(tok_cr), .fault(tk_f));
    reg  [2:0]   tk_c;
    // ---- launcher: score descriptors -> ATTN {T, layer} ----
    reg  [19:0]  lq0, lq1;                  // {T 14, layer 6}
    reg  [1:0]   ln;
    reg  [17:0]  lp;
    reg          lp_v, f_kq, f_kvd;
    wire         k_kind = kr[42];
    wire [17:0]  k_pos  = kr[41:24];
    wire [23:0]  k_wb   = kr[23:0];
    wire         l_push = kv && k_kind;
    wire [5:0]   l_lay  = (MUT == 3) ? k_wb[11:6] + 6'd1 : k_wb[11:6];
    wire [19:0]  l_w    = {k_pos[13:0] + 14'd1, l_lay};
    // ---- layer state ----
    localparam [2:0] S_IDLE = 3'd0, S_KV = 3'd1, S_ST = 3'd2, S_Q = 3'd3, S_RUN = 3'd4;
    reg [2:0]   st;
    reg [5:0]   layer;
    reg [13:0]  a_T;
    reg         a_start, a_q_valid;
    reg [5:0]   a_q_beat;
    reg [3:0]   kv_n;
    reg [5:0]   q_n;
    reg [6:0]   r_n;
    reg [2:0]   kw_n;
    reg [7:0]   kwc, uc0;
    reg         kw_go, kwq, kvw_v;
    reg [1:0]   kvw_vg;
    reg [13:0]  kvw_t;
    reg [5:0]   kvw_layer;
    reg         f_res, f_ord, f_row, f_pend, f_kw, f_ib, f_x, f_xovr, f_join;
    wire        c_attn = (ctl_w[527:524] == 4'd1);
    wire        l_take = (st == S_IDLE) && (ln != 2'd0);
    always @* begin
        ib_pop = 3'd0;
        if (!ib_empty[0] && ((st == S_IDLE && !l_take && c_attn) || (!c_attn && tk_c != 0))) ib_pop[0] = 1'b1;
        // (the previous layer's four rows are all posted before its KVN words are replaced: ot_qkvd_kv_seq dropped the
        //  unposted rows when the row credits were late)
        if (st == S_KV && kv_n < 4'd8 && !ib_empty[2] && kw_n == 3'd4) ib_pop[2] = 1'b1;
        if (st == S_Q && !ib_empty[1]) ib_pop[1] = 1'b1;
    end
    wire        go    = l_take || (st == S_IDLE && ib_pop[0] && c_attn);
    wire [13:0] go_T  = l_take ? lq0[19:6] : ctl_w[13:0];
    wire [5:0]  go_L  = l_take ? lq0[5:0]  : ctl_w[21:16];
    always @(posedge clk) begin
        tk_in_d <= ctl_w;
        if (ib_pop[1]) a_q_beat <= (MUT == 2 && q_tag < 6'd2) ? (q_tag ^ 6'd1) : q_tag;
        if (ov) ar_d <= {og, ob, od};
        if (kw_go) begin kvw_vg <= kw_n[1:0]; kvw_t <= a_T - 1'b1; kvw_layer <= layer; end
        s_kidx <= k_tag;
        s_kwn  <= kw_n[1:0];
    end
    // ---- stream descriptors to the HBM controllers (as ot_qkvd_kv_seq KDESC) ----
    wire        kd_fault, kd_v;
    wire [31:0] kd_d;
    generate if (KDESC != 0) begin : g_kd
        ot_qkvd_kv_desc #(.NL(36)) u_kd (.clk(clk), .rst_n(rst_n), .p_mid_init(20'(KD_PMID)), .p_tok_init(20'(KD_PTOK)),
            .attn_v(go), .attn_layer(go_L), .attn_T(go_T),
            .done_v(st == S_RUN && ov && r_n == 7'd63), .k_v(kd_v), .k_d(kd_d), .k_ready(1'b1), .fault(kd_fault));
    end else begin : g_nkd
        assign kd_v = 1'b0; assign kd_d = 32'd0; assign kd_fault = 1'b0;
    end endgenerate
    always @(posedge clk) f_kc[31:0] <= kd_d;
    always @(posedge clk) f_kc[33 +: 32] <= kd_d;
    // ---- credit join of the four landing write queues ----
    reg  [2:0]  jc [0:3];
    wire [3:0]  jnz = {jc[3] != 0, jc[2] != 0, jc[1] != 0, jc[0] != 0};
    wire        jn  = (MUT == 4) ? |jnz : &jnz;
    // ---- outputs to the fans: the sequencer's own registers + one stage, then the pin copies ----
    reg  [27:0] aq1;
    reg  [22:0] kw1;
    reg  [2:0]  hsd;
    always @(posedge clk) begin
        aq1[26:7] <= {a_T, layer}; aq1[5:0] <= a_q_beat;
        f_aqm[26:7] <= aq1[26:7]; f_aqm[5:0] <= aq1[5:0];
        f_aqm[28+26 -: 20] <= aq1[26:7]; f_aqm[28 +: 6] <= aq1[5:0];
        kw1[21:0] <= {kvw_vg, kvw_t, kvw_layer};
        f_kwm[21:0] <= kw1[21:0]; f_kwm[23 +: 22] <= kw1[21:0];
    end
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; layer <= 0; kv_n <= 0; q_n <= 0; r_n <= 0; a_start <= 1'b0; a_T <= 14'd0; a_q_valid <= 1'b0;
            x3_cr <= 1'b0; dc_cr <= 1'b0; uc0 <= 8'(OCR_AR); ar_v <= 1'b0; tk_in_v <= 1'b0; tk_c <= 3'd4;
            kw_n <= 3'd4; kwc <= 8'(KWC); kw_go <= 1'b0; kvw_v <= 1'b0; kwq <= 1'b0;
            s_qpop <= 1'b0; s_kpop <= 1'b0; s_kwgo <= 1'b0; hs <= 1'b0; hsd <= 3'd0;
            aq1[27] <= 1'b0; aq1[6] <= 1'b0; f_aqm[27] <= 1'b0; f_aqm[6] <= 1'b0; f_aqm[55] <= 1'b0; f_aqm[34] <= 1'b0;
            kw1[22] <= 1'b0; f_kwm[22] <= 1'b0; f_kwm[45] <= 1'b0; f_kc[32] <= 1'b0; f_kc[65] <= 1'b0;
            lq0 <= 20'd0; lq1 <= 20'd0; ln <= 2'd0; lp <= 18'd0; lp_v <= 1'b0; f_kq <= 1'b0; f_kvd <= 1'b0;
            for (i = 0; i < 4; i = i + 1) jc[i] <= 3'd0;
            f_res <= 1'b0; f_ord <= 1'b0; f_kw <= 1'b0; f_ib <= 1'b0; f_row <= 1'b0; f_pend <= 1'b0; f_x <= 1'b0;
            f_xovr <= 1'b0; f_join <= 1'b0; fault <= 1'b0; fault_cause <= 9'd0; rflt <= 1'b0; rflt_cause <= 8'd0;
        end else begin
            x3_cr <= ib_pop[1] | ib_pop[2];
            dc_cr <= ib_pop[0];
            s_qpop <= ib_pop[1]; s_kpop <= ib_pop[2]; s_kwgo <= kw_go;
            a_start <= 1'b0;
            a_q_valid <= ib_pop[1];
            tk_in_v <= ib_pop[0] && !c_attn;
            tk_c <= tk_c - ((ib_pop[0] && !c_attn) ? 3'd1 : 3'd0) + (tk_icr ? 3'd1 : 3'd0);
            // launcher queue
            if (l_push) begin
                lp <= k_pos; lp_v <= 1'b1;
                if (k_wb[23:12] != 12'd0 || k_pos[17:14] != 4'd0) f_kvd <= 1'b1;
                if (ln == 2'd2 && !l_take) f_kq <= 1'b1;
            end
            if (kv && !k_kind && (!lp_v || k_pos != lp)) f_kvd <= 1'b1;
            case ({l_push && !(ln == 2'd2 && !l_take), l_take})
                2'b10: begin if (ln == 2'd0) lq0 <= l_w; else lq1 <= l_w; ln <= ln + 2'd1; end
                2'b01: begin lq0 <= lq1; ln <= ln - 2'd1; end
                2'b11: begin if (ln == 2'd1) lq0 <= l_w; else begin lq0 <= lq1; lq1 <= l_w; end end
                default: ;
            endcase
            case (st)
                S_IDLE: if (go) begin
                    a_T <= go_T; layer <= go_L; kv_n <= 0; q_n <= 0; r_n <= 0; st <= S_KV;
                end
                S_KV: begin
                    if (ib_pop[2]) kv_n <= kv_n + 1'b1;
                    // the hub has no ready: the layer starts with all of its 64 RES credits in hand
                    if (kv_n == 4'd8 && uc0 >= 8'd64) begin st <= S_ST; a_start <= 1'b1; kw_n <= 3'd0; end
                end
                S_ST: st <= S_Q;           // start leads the first q beat by one cycle (the stack's contract)
                S_Q: begin
                    if (ib_pop[1]) begin
                        if (q_tag != q_n) f_ord <= 1'b1;
                        q_n <= q_n + 1'b1;
                        if (q_n == 6'd31) st <= S_RUN;
                    end
                end
                S_RUN: if (ov && r_n == 7'd63) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
            if (ov) r_n <= r_n + 1'b1;
            ar_v <= ov;
            if (ov && uc0 == 0) f_res <= 1'b1;
            uc0 <= uc0 - (ov ? 8'd1 : 8'd0) + (ucq ? 8'd1 : 8'd0);
            // KV write: post the four rows of the new position, one per (joined) credit
            kw_go <= (kw_n < 3'd4) && (kwc != 0) && !kw_go;
            if (kw_go) kw_n <= kw_n + 1'b1;
            kvw_v <= kw_go;
            kwc <= kwc - (kw_go ? 8'd1 : 8'd0) + (kwq ? 8'd1 : 8'd0);
            kwq <= jn;
            for (i = 0; i < 4; i = i + 1) begin
                jc[i] <= jc[i] + (crq[i] ? 3'd1 : 3'd0) - ((jn && jc[i] != 0) ? 3'd1 : 3'd0);
                if (crq[i] && jc[i] == 3'd7) f_join <= 1'b1;
            end
            // pin copies
            aq1[27] <= a_start; aq1[6] <= a_q_valid;
            f_aqm[27] <= aq1[27]; f_aqm[6] <= aq1[6]; f_aqm[55] <= aq1[27]; f_aqm[34] <= aq1[6];
            kw1[22] <= kvw_v; f_kwm[22] <= kw1[22]; f_kwm[45] <= kw1[22];
            f_kc[32] <= kd_v; f_kc[65] <= kd_v;
            hsd <= {hsd[1:0], a_start}; hs <= hsd[2];
            // faults
            if (ib_full[0] && cv && !ib_pop[0]) f_ib <= 1'b1;
            if (xv && ((x_q && ib_full[1] && !ib_pop[1]) || (x_kv && ib_full[2] && !ib_pop[2]))) f_xovr <= 1'b1;
            if (xv && !x_q && !x_kv) f_x <= 1'b1;
            if (kwq && kwc == 8'(KWC)) f_kw <= 1'b1;
            f_row <= f_row | (|mfq); f_pend <= f_pend | hfq | (|afq);
            fault_cause <= {f_x | f_xovr | f_kq | f_kvd, tk_f, hc_f, f_join, kd_fault, f_kw | f_row | f_pend, f_ord, f_res, f_ib};
            fault <= |{f_x, f_xovr, f_kq, f_kvd, tk_f, hc_f, f_join, f_kw, f_row, f_pend, f_ord, f_res, f_ib, kd_fault};
            rflt_cause <= {f_res, f_ord, f_ib, kd_fault, f_kvd, f_kq, f_xovr, f_x};
            rflt <= |{f_x, f_xovr, f_kq, f_kvd, tk_f, hc_f, f_join, f_kw, f_row, f_pend, f_ord, f_res, f_ib, kd_fault};
        end
    end
`ifndef SYNTHESIS
    initial begin
        if (OCR_AR < 64) $error("ot_qkvd_seq_m_ctl: OCR_AR must cover one layer (64 RES words)");
        if (XS < 40) $error("ot_qkvd_seq_m_ctl: XS must cover one layer (8 KVN + 32 Q)");
    end
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// x3 data storage, DW bits of the 512-b word: Q FIFO (XS), KVN FIFO (KD) and the eight KVN words of the layer.  The
// control's tag FIFOs move in step: pushes are decoded here from the word's own valid / class (same pins, same edge),
// pops arrive registered from the control.  q and kw leave as two registered copies (W / E fans).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_store #(
    parameter integer DW = 512,
    parameter integer XS = 40,
    parameter integer KD = 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            x_v,
    input  wire [2:0]      x_cls,
    input  wire [DW-1:0]   x_d,
    input  wire            qpop,
    input  wire            kpop,
    input  wire [2:0]      kidx,
    input  wire            kwgo,
    input  wire [1:0]      kwn,
    (* keep = "true", dont_touch = "true" *) output reg  [2*DW-1:0] q,                  // copy c at [c*DW +: DW]
    (* keep = "true", dont_touch = "true" *) output reg  [4*DW-1:0] kw                  // copy c at [c*2*DW +: 2*DW] = {word {vg, 1}, word {vg, 0}}
);
    reg          xv, qp, kp, kg;
    reg [2:0]    xc, ki;
    reg [1:0]    kn;
    reg [DW-1:0] xd;
    always @(posedge clk) begin xc <= x_cls; xd <= x_d; ki <= kidx; kn <= kwn; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin xv <= 1'b0; qp <= 1'b0; kp <= 1'b0; kg <= 1'b0; end
        else begin xv <= x_v; qp <= qpop; kp <= kpop; kg <= kwgo; end
    wire [DW-1:0] qh, kh;
    ot_qkvd_fifo #(.W(DW), .D(XS)) u_q (.clk(clk), .rst_n(rst_n), .push(xv && xc == 3'b001), .din(xd), .pop(qp),
        .dout(qh), .empty(), .full(), .count());
    ot_qkvd_fifo #(.W(DW), .D(KD)) u_k (.clk(clk), .rst_n(rst_n), .push(xv && xc == 3'b010), .din(xd), .pop(kp),
        .dout(kh), .empty(), .full(), .count());
    reg [DW-1:0] kvn [0:7];
    always @(posedge clk) begin
        if (kp) kvn[ki] <= kh;
        if (qp) q <= {2{qh}};
        if (kg) kw <= {2{kvn[{kn, 1'b1}], kvn[{kn, 1'b0}]}};
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// One quadrant's pin registers: aq / kvn / kc out (capture, then launch at the face), row credit and the two fault
// bits back (capture at the face, then launch toward the control).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_seq_m_fan #(
    parameter integer HD = 128
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [27:0]        aqm,
    input  wire [511:0]       q,
    input  wire [22:0]        kwm,
    input  wire [HD*8-1:0]    kw,
    input  wire [32:0]        kc_i,
    output wire [539:0]       aq,              // {start, T 14, layer 6, q valid, beat 6, data 512}
    output wire [HD*8+22:0]   kvn,             // {v, vg 2, t 14, layer 6, row}
    output wire [32:0]        kc,              // {v, d 32}
    input  wire               kvn_cr,
    input  wire               af,
    input  wire               mf,
    output reg                cr_o,
    output reg                af_o,
    output reg                mf_o
);
    reg [27:0]      am, am2;
    reg [511:0]     qd, qd2;
    reg [22:0]      km, km2;
    reg [HD*8-1:0]  kd, kd2;
    reg [32:0]      kq, kq2;
    reg             c1, a1, m1;
    always @(posedge clk) begin
        am[26:7] <= aqm[26:7]; am[5:0] <= aqm[5:0]; am2[26:7] <= am[26:7]; am2[5:0] <= am[5:0];
        qd <= q; qd2 <= qd; km[21:0] <= kwm[21:0]; km2[21:0] <= km[21:0]; kd <= kw; kd2 <= kd;
        kq[31:0] <= kc_i[31:0]; kq2[31:0] <= kq[31:0];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            am[27] <= 1'b0; am[6] <= 1'b0; am2[27] <= 1'b0; am2[6] <= 1'b0; km[22] <= 1'b0; km2[22] <= 1'b0;
            kq[32] <= 1'b0; kq2[32] <= 1'b0; c1 <= 1'b0; a1 <= 1'b0; m1 <= 1'b0; cr_o <= 1'b0; af_o <= 1'b0; mf_o <= 1'b0;
        end else begin
            am[27] <= aqm[27]; am[6] <= aqm[6]; am2[27] <= am[27]; am2[6] <= am[6]; km[22] <= kwm[22]; km2[22] <= km[22];
            kq[32] <= kc_i[32]; kq2[32] <= kq[32]; c1 <= kvn_cr; a1 <= af; m1 <= mf; cr_o <= c1; af_o <= a1; mf_o <= m1;
        end
    assign aq  = {am2[27:6], am2[5:0], qd2};
    assign kvn = {km2, kd2};
    assign kc  = kq2;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The flat merged-die sequencer (reference of the cluster; the layer bench runs through it).  Quadrant k: 0 WS, 1 WN,
// 2 ES, 3 EN.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_seq_merged #(
    parameter integer HD     = 128,
    parameter integer W      = 528,
    parameter integer XS     = 40,
    parameter integer KD     = 8,
    parameter integer CD     = 4,
    parameter integer HCD    = 4,
    parameter integer TKC    = 4,
    parameter integer KWC    = 4,
    parameter integer OCR_AR = 64,
    parameter integer OCR_DH = 4,
    parameter integer KDESC  = 1,
    parameter integer KD_PMID = 0,
    parameter integer KD_PTOK = 0,
    parameter integer MUT    = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x3_v,
    input  wire [10:0]        x3_tag,
    input  wire [511:0]       x3_d,
    output wire               x3_cr,
    input  wire               dc_v,
    input  wire [W-1:0]       dc_d,
    output wire               dc_cr,
    input  wire [43:0]        kvd,
    output wire               ar_v,
    output wire [518:0]       ar_d,
    input  wire               ar_cr,
    output wire               dh_v,
    output wire [W-1:0]       dh_d,
    input  wire               dh_cr,
    output wire               pw_v,
    output wire [9:0]         pw_addr,
    output wire [63:0]        pw_data,
    output wire               rflt,
    output wire [7:0]         rflt_cause,
    output wire [4*540-1:0]   aq,
    output wire [4*(HD*8+23)-1:0] kvn,
    input  wire [3:0]         kvn_cr,
    output wire [4*33-1:0]    kc,
    input  wire [3:0]         af,
    input  wire [3:0]         mf,
    output wire               hs,
    input  wire               a_out_valid,
    input  wire               a_out_g,
    input  wire [5:0]         a_out_beat,
    input  wire [511:0]       a_out_data,
    input  wire               a_hub_fault,
    input  wire               hc_v,
    input  wire [W-1:0]       hc_d,
    output wire               hc_cr,
    output wire               tok_v,
    output wire [W-1:0]       tok_d,
    input  wire               tok_cr,
    output wire               fault,
    output wire [8:0]         fault_cause
);
    wire          s_qpop, s_kpop, s_kwgo;
    wire [2:0]    s_kidx;
    wire [1:0]    s_kwn;
    wire [2*28-1:0] f_aqm;
    wire [2*23-1:0] f_kwm;
    wire [2*33-1:0] f_kc;
    wire [3:0]    f_cr, f_af, f_mf;
    wire [2*512-1:0]  sq;
    wire [4*512-1:0]  skw;
    ot_qkvd_seq_m_ctl #(.W(W), .XS(XS), .KD(KD), .CD(CD), .HCD(HCD), .TKC(TKC), .KWC(KWC), .OCR_AR(OCR_AR), .OCR_DH(OCR_DH),
                        .KDESC(KDESC), .KD_PMID(KD_PMID), .KD_PTOK(KD_PTOK), .MUT(MUT)) u_ctl (
        .clk(clk), .rst_n(rst_n), .x3_v(x3_v), .x3_tag(x3_tag), .x3_cr(x3_cr), .dc_v(dc_v), .dc_d(dc_d), .dc_cr(dc_cr),
        .kvd(kvd), .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .dh_v(dh_v), .dh_d(dh_d), .dh_cr(dh_cr), .pw_v(pw_v),
        .pw_addr(pw_addr), .pw_data(pw_data), .rflt(rflt), .rflt_cause(rflt_cause), .s_qpop(s_qpop), .s_kpop(s_kpop),
        .s_kidx(s_kidx), .s_kwgo(s_kwgo), .s_kwn(s_kwn), .f_aqm(f_aqm), .f_kwm(f_kwm), .f_kc(f_kc), .f_cr(f_cr),
        .f_af(f_af), .f_mf(f_mf), .hs(hs), .a_out_valid(a_out_valid), .a_out_g(a_out_g), .a_out_beat(a_out_beat),
        .a_out_data(a_out_data), .a_hub_fault(a_hub_fault), .hc_v(hc_v), .hc_d(hc_d), .hc_cr(hc_cr), .tok_v(tok_v),
        .tok_d(tok_d), .tok_cr(tok_cr), .fault(fault), .fault_cause(fault_cause));
    ot_qkvd_seq_m_store #(.DW(512), .XS(XS), .KD(KD)) u_st (.clk(clk), .rst_n(rst_n), .x_v(x3_v), .x_cls(x3_tag[10:8]),
        .x_d(x3_d), .qpop(s_qpop), .kpop(s_kpop), .kidx(s_kidx), .kwgo(s_kwgo), .kwn(s_kwn), .q(sq), .kw(skw));
    genvar k;
    generate for (k = 0; k < 4; k = k + 1) begin : g_fan
        ot_qkvd_seq_m_fan #(.HD(HD)) u_f (.clk(clk), .rst_n(rst_n), .aqm(f_aqm[28*(k/2) +: 28]), .q(sq[512*(k/2) +: 512]),
            .kwm(f_kwm[23*(k/2) +: 23]), .kw(skw[1024*(k/2) +: 1024]), .kc_i(f_kc[33*(k/2) +: 33]),
            .aq(aq[540*k +: 540]), .kvn(kvn[(HD*8+23)*k +: HD*8+23]), .kc(kc[33*k +: 33]), .kvn_cr(kvn_cr[k]),
            .af(af[k]), .mf(mf[k]), .cr_o(f_cr[k]), .af_o(f_af[k]), .mf_o(f_mf[k]));
    end endgenerate
endmodule
