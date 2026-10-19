module qkd_kvs_emb (
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
    input wire [298:0] i_hroot_EN
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
    qkd_embedding_static_join4_cal #(.MUT(0)) u_join (.ck(ck), .rst_n(rst_n), .up0(join__up0), .up1(join__up1), .up2(join__up2), .up3(join__up3), .start(d2d__svc[24:24]), .cfg_we(join__cfg_we), .cfg_addr(join__cfg_addr), .cfg_data(join__cfg_data), .word_v(w_join__word_v), .word_data(w_join__word_data), .word_token(w_join__word_token), .word_index(w_join__word_index), .word_scale(w_join__word_scale), .word_epoch(w_join__word_epoch), .fault(w_join__fault));
    qkd_embedding_row_tx u_rowtx (.ck(ck), .rst_n(rst_n), .fill_begin(d2d__svc[24:24]), .fill_token(d2d__svc[109:92]), .fill_epoch(d2d__svc[89:74]), .word_v(w_join__word_v[0:0]), .word_data(w_join__word_data[511:0]), .word_token(w_join__word_token[17:0]), .word_index(w_join__word_index[5:0]), .word_scale(w_join__word_scale[0:0]), .word_epoch(w_join__word_epoch[15:0]), .emb_tx_slot(d2d__emb_tx_slot[0:0]), .emb_tx_v(w_rowtx__emb_tx_v), .emb_tx_payload(w_rowtx__emb_tx_payload), .fault(w_rowtx__fault), .row_ready(w_rowtx__row_ready));
    assign rowtx__emb_tx_v = w_rowtx__emb_tx_v;
    assign rowtx__emb_tx_payload = w_rowtx__emb_tx_payload;
    assign px_tok = d2d__svc[109:92];
    assign px_tep = d2d__svc[89:74];
endmodule
