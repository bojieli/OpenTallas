module qkd_kvs_emb_rope (
    input wire ck,
    input wire rst_n,
    input wire [173:0] d2d__svc,
    input wire [0:0] d2d__emb_tx_slot,
    output wire [0:0] rowtx__emb_tx_v,
    output wire [547:0] rowtx__emb_tx_payload,
    output wire [17:0] px_tok,
    output wire [15:0] px_tep,
    input wire [72:0] i_ctl,
    input wire [298:0] i_hroot_WS,
    input wire [298:0] i_hroot_WN,
    input wire [298:0] i_hroot_ES,
    input wire [298:0] i_hroot_EN,
    input wire [551:0] i_head_record,
    output wire [173:0] o_ctx_svc,
    output wire [0:0] emb_fault
);
    wire [7:0] join__cfg_addr = i_ctl[7:0];
    wire [63:0] join__cfg_data = i_ctl[71:8];
    wire [0:0] join__cfg_we = i_ctl[72:72];
    wire [298:0] join__up3 = i_hroot_EN[298:0];
    wire [298:0] join__up2 = i_hroot_ES[298:0];
    wire [298:0] join__up1 = i_hroot_WN[298:0];
    wire [298:0] join__up0 = i_hroot_WS[298:0];
    wire [0:0] w_join__word_v;
    wire [511:0] w_join__word_data;
    wire [17:0] w_join__word_token;
    wire [5:0] w_join__word_index;
    wire [0:0] w_join__word_scale;
    wire [15:0] w_join__word_epoch;
    wire [0:0] w_join__fault;
    wire [0:0] w_rowtx__emb_tx_v;
    wire [547:0] w_rowtx__emb_tx_payload;
    wire [0:0] w_rowtx__fault;
    wire [0:0] w_rowtx__row_ready;
    wire w_rope_start, w_rope_fault;
    wire [17:0] w_rope_token;
    wire [15:0] w_rope_epoch;
    qkd_kvs_emb_ctx #(.NATIVE32(1), .PIPE_JOIN(1), .ROPE(1), .FIX_ROPE_SLOT_GUARD(1), .ROPE_DELAY(1024), .OVL(0)) u_context (.ck(ck), .rst_n(rst_n), .i_ctx({i_head_record[3],i_head_record[3],i_head_record[551:516],i_head_record[64:4]}), .head_rx_user(2'd0), .emb_tx_user(2'd0), .kvn_ctx_fault(1'b0), .ovl_adm_done(1'b0), .d2d__emb_tx_slot(d2d__emb_tx_slot), .i_ctl(i_ctl), .i_hroot_WS(i_hroot_WS), .i_hroot_WN(i_hroot_WN), .i_hroot_ES(i_hroot_ES), .i_hroot_EN(i_hroot_EN), .rowtx__emb_tx_v(w_rowtx__emb_tx_v), .rowtx__emb_tx_payload(w_rowtx__emb_tx_payload), .px_st(w_rope_start), .px_tok(w_rope_token), .px_tep(w_rope_epoch), .emb_fault(w_rope_fault));
    assign rowtx__emb_tx_v = w_rowtx__emb_tx_v;
    assign rowtx__emb_tx_payload = w_rowtx__emb_tx_payload;
    assign px_tok = w_rope_token;
    assign px_tep = w_rope_epoch;
    assign o_ctx_svc = {d2d__svc[173:110],w_rope_token,d2d__svc[91:90],w_rope_epoch,d2d__svc[73:25],w_rope_start,d2d__svc[23:0]};
    assign emb_fault = w_rope_fault;
endmodule
