`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-EMB2 2026-10-19 (K.STA.EMB): reference body of the KV-die singleton tile kvs_emb for the MU build with the
// allocation-owned fill start (die generator flag OT_KV_EMB_CTX=1 must emit this body; tools/qwen_kv_die/kv_static_die.py
// owner = KV-GEN9).  Same children and boot / return faces as the generated qkd_kvs_emb (qkd_kvs_tiles_hroot_ff_k[_mu].sv);
// differences:
//   - d2d__svc[173:0] is gone: the fill no longer reads the kind-15 RESULT (svc[24] / svc[109:92] / svc[89:74]);
//   - i_ctx[98:0] = the die fork of the HOST record face {record_tx_v, record_tx_observed_v, record_tx[547:512],
//     record_tx[60:0]} (HOST -> d2d port-1 bus; kind-12 CONTEXT carries the allocation owner O61);
//   - qkd_embedding_ctx_start drives join4_cal start, row_tx fill_*, and px_st / px_tok / px_tep for the fan root (the
//     fan root's emb_start moves from the d2d svc[24] relay branch to px_st, so its start, token and epoch leave one
//     register together);
//   - emb_fault = ctx_start | join | row_tx sticky faults (previously internal; owner of the health sink: KV-HEALTH).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_kvs_emb_ctx #(parameter integer NATIVE32 = 0, parameter integer PIPE_JOIN = 0, parameter integer ROPE=0, parameter integer ROPE_DELAY=1024) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [98:0]   i_ctx,
    input  wire [0:0]    d2d__emb_tx_slot,
    output wire [0:0]    rowtx__emb_tx_v,
    output wire [547:0]  rowtx__emb_tx_payload,
    output wire [0:0]    px_st,
    output wire [17:0]   px_tok,
    output wire [15:0]   px_tep,
    output wire [0:0]    emb_fault,
    input  wire [72:0]   i_ctl,
    input  wire [298:0]  i_hroot_WS,
    input  wire [298:0]  i_hroot_WN,
    input  wire [298:0]  i_hroot_ES,
    input  wire [298:0]  i_hroot_EN
);
    wire st;
    wire [60:0] accepted_owner;
    reg [12:0] position;
    reg [15:0] rope_count;
    reg rope_pending, rope_start;
    reg [17:0] rope_id;
    reg [15:0] rope_epoch;
    wire [3:0] start_local;
    // Metadata uses independently kept start copies on the original retire edge.
    always @(posedge ck)begin
      if(start_local[1] && ROPE)rope_id<=18'd151936+{8'd0,accepted_owner[18:9]};
      if(start_local[2] && ROPE)begin position<=accepted_owner[18:6];rope_epoch<=tep;end
    end
    always @(posedge ck or negedge rst_n)
      if(!rst_n)begin rope_count<=0;rope_pending<=0;rope_start<=0;end
      else begin
        rope_start<=0;
        if(start_local[3] && ROPE)begin
          rope_count<=16'(ROPE_DELAY-2);rope_pending<=1;
        end else if(rope_pending)begin
          if(rope_count==0)begin rope_start<=1;rope_pending<=0;end
          else rope_count<=rope_count-1;
        end
      end
    wire sweep_start=st|rope_start;
    reg rope_phase;
    always @(posedge ck or negedge rst_n)
      if(!rst_n)rope_phase<=0;
      else if(start_local[3])rope_phase<=0;else if(rope_start)rope_phase<=1;
    wire [17:0] tok;
    wire [15:0] tep;
    wire        cf, jf, rf, row_open;
    wire        w_v, w_scale;
    wire [511:0] w_data;
    wire [17:0] w_token;
    wire [5:0]  w_index;
    wire [15:0] w_epoch;
    qkd_embedding_ctx_start #(.NATIVE32(NATIVE32),.MIN_GAP(ROPE?74:66)) u_ctx (.ck(ck), .rst_n(rst_n), .row_open(row_open), .ctx_v(i_ctx[98]), .ctx_observed_v(i_ctx[97]),
        .ctx_hdr(i_ctx[96:61]), .ctx_owner(i_ctx[60:0]), .start(st), .start_local(start_local), .token(tok), .epoch(tep), .owner(accepted_owner), .fault(cf));
    qkd_embedding_static_join4_cal #(.MUT(0), .NATIVE32(NATIVE32), .PIPE_JOIN(PIPE_JOIN)) u_join (.ck(ck), .rst_n(rst_n), .up0(i_hroot_WS), .up1(i_hroot_WN),
        .up2(i_hroot_ES), .up3(i_hroot_EN), .start(sweep_start), .rope_sweep(ROPE && rope_start), .cfg_we(i_ctl[72]), .cfg_addr(i_ctl[7:0]), .cfg_data(i_ctl[71:8]),
        .word_v(w_v), .word_data(w_data), .word_token(w_token), .word_index(w_index), .word_scale(w_scale),
        .word_epoch(w_epoch), .fault(jf));
    generate if(ROPE)begin:g_rope
    qkd_embedding_row_tx_rope u_rowtx (.ck(ck),.rst_n(rst_n),.fill_begin(st),.fill_token(tok),.fill_epoch(tep),
        .fill_position(accepted_owner[18:6]),.word_v(w_v),.word_data(w_data),.word_token(w_token),
        .word_index(w_index),.word_scale(w_scale),.word_epoch(w_epoch),.emb_tx_slot(d2d__emb_tx_slot[0]),
        .emb_tx_v(rowtx__emb_tx_v),.emb_tx_payload(rowtx__emb_tx_payload),.fault(rf),.row_ready(),.row_open(row_open));
    end else begin:g_legacy
    qkd_embedding_row_tx_ctx u_rowtx (.ck(ck), .rst_n(rst_n), .fill_begin(st), .fill_token(tok), .fill_epoch(tep),
        .word_v(w_v), .word_data(w_data), .word_token(w_token), .word_index(w_index), .word_scale(w_scale),
        .word_epoch(w_epoch), .emb_tx_slot(d2d__emb_tx_slot[0]), .emb_tx_v(rowtx__emb_tx_v), .emb_tx_payload(rowtx__emb_tx_payload),
        .fault(rf), .row_ready(), .row_open(row_open));
    end endgenerate
    assign px_st = sweep_start;
    assign px_tok = (!st&&(rope_start||rope_phase))?rope_id:tok;
    assign px_tep = (!st&&(rope_start||rope_phase))?rope_epoch:tep;
    assign emb_fault = cf | jf | rf;
endmodule
