`timescale 1ns/1ps
module pc_chain_collar_good (
    input wire [0:0] ck,
    input wire  rst_n,
    input wire [1:0] cfg_stack,
    input wire [779:0] di,
    output wire [779:0] dout,
    output wire [287:0] land_es,
    input wire [260:0] land_er,
    output wire [287:0] wes,
    output wire [317:0] es_context,
    output wire  es_expected_valid,
    output wire [60:0] es_expected_identity,
    output wire [28:0] es_expected_address,
    output wire [4:0] es_expected_pc,
    output wire [1:0] es_expected_stack,
    output wire  emb_issue_v,
    output wire [17:0] emb_token,
    output wire [5:0] emb_word_index,
    output wire  emb_half,
    output wire  emb_scale,
    output wire [15:0] emb_epoch,
    output wire  emb_return_slot,
    output wire  capture_slot,
    output wire  transfer_slot,
    output wire  fault
);
    // KVSPC_COHERENT_INPUT_COLLAR: one coherent input/boot edge; no data resets.
    (* keep = 1, face_keep = 1 *) reg  pcin_rst_n;
    always @(posedge ck[0]) pcin_rst_n <= rst_n;
    (* keep = 1, face_keep = 1 *) reg [1:0] pcin_cfg_stack;
    always @(posedge ck[0]) pcin_cfg_stack <= cfg_stack;
    (* keep = 1, face_keep = 1 *) reg [779:0] pcin_di;
    always @(posedge ck[0]) pcin_di <= di;
    (* keep = 1, face_keep = 1 *) reg [260:0] pcin_land_er;
    always @(posedge ck[0]) pcin_land_er <= land_er;

    qkd_kv_pc_chain_station_b_p u_leaf (
        .ck(ck[0]),
        .rst_n(pcin_rst_n),
        .cfg_stack(pcin_cfg_stack),
        .di(pcin_di),
        .dout(dout),
        .land_es(land_es),
        .land_er(pcin_land_er),
        .wes(wes),
        .es_context(es_context),
        .es_expected_valid(es_expected_valid),
        .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address),
        .es_expected_pc(es_expected_pc),
        .es_expected_stack(es_expected_stack),
        .emb_issue_v(emb_issue_v),
        .emb_token(emb_token),
        .emb_word_index(emb_word_index),
        .emb_half(emb_half),
        .emb_scale(emb_scale),
        .emb_epoch(emb_epoch),
        .emb_return_slot(emb_return_slot),
        .capture_slot(capture_slot),
        .transfer_slot(transfer_slot),
        .fault(fault)
    );
endmodule
`timescale 1ns/1ps
module pc_chain_collar_badbit (
    input wire [0:0] ck,
    input wire  rst_n,
    input wire [1:0] cfg_stack,
    input wire [779:0] di,
    output wire [779:0] dout,
    output wire [287:0] land_es,
    input wire [260:0] land_er,
    output wire [287:0] wes,
    output wire [317:0] es_context,
    output wire  es_expected_valid,
    output wire [60:0] es_expected_identity,
    output wire [28:0] es_expected_address,
    output wire [4:0] es_expected_pc,
    output wire [1:0] es_expected_stack,
    output wire  emb_issue_v,
    output wire [17:0] emb_token,
    output wire [5:0] emb_word_index,
    output wire  emb_half,
    output wire  emb_scale,
    output wire [15:0] emb_epoch,
    output wire  emb_return_slot,
    output wire  capture_slot,
    output wire  transfer_slot,
    output wire  fault
);
    // KVSPC_COHERENT_INPUT_COLLAR: one coherent input/boot edge; no data resets.
    (* keep = 1, face_keep = 1 *) reg  pcin_rst_n;
    always @(posedge ck[0]) pcin_rst_n <= rst_n;
    (* keep = 1, face_keep = 1 *) reg [1:0] pcin_cfg_stack;
    always @(posedge ck[0]) pcin_cfg_stack <= cfg_stack;
    (* keep = 1, face_keep = 1 *) reg [779:0] pcin_di;
    always @(posedge ck[0]) pcin_di <= di ^ 780'd4;
    (* keep = 1, face_keep = 1 *) reg [260:0] pcin_land_er;
    always @(posedge ck[0]) pcin_land_er <= land_er;

    qkd_kv_pc_chain_station_b_p u_leaf (
        .ck(ck[0]),
        .rst_n(pcin_rst_n),
        .cfg_stack(pcin_cfg_stack),
        .di(pcin_di),
        .dout(dout),
        .land_es(land_es),
        .land_er(pcin_land_er),
        .wes(wes),
        .es_context(es_context),
        .es_expected_valid(es_expected_valid),
        .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address),
        .es_expected_pc(es_expected_pc),
        .es_expected_stack(es_expected_stack),
        .emb_issue_v(emb_issue_v),
        .emb_token(emb_token),
        .emb_word_index(emb_word_index),
        .emb_half(emb_half),
        .emb_scale(emb_scale),
        .emb_epoch(emb_epoch),
        .emb_return_slot(emb_return_slot),
        .capture_slot(capture_slot),
        .transfer_slot(transfer_slot),
        .fault(fault)
    );
endmodule
`timescale 1ns/1ps
module pc_chain_collar_badreset (
    input wire [0:0] ck,
    input wire  rst_n,
    input wire [1:0] cfg_stack,
    input wire [779:0] di,
    output wire [779:0] dout,
    output wire [287:0] land_es,
    input wire [260:0] land_er,
    output wire [287:0] wes,
    output wire [317:0] es_context,
    output wire  es_expected_valid,
    output wire [60:0] es_expected_identity,
    output wire [28:0] es_expected_address,
    output wire [4:0] es_expected_pc,
    output wire [1:0] es_expected_stack,
    output wire  emb_issue_v,
    output wire [17:0] emb_token,
    output wire [5:0] emb_word_index,
    output wire  emb_half,
    output wire  emb_scale,
    output wire [15:0] emb_epoch,
    output wire  emb_return_slot,
    output wire  capture_slot,
    output wire  transfer_slot,
    output wire  fault
);
    // KVSPC_COHERENT_INPUT_COLLAR: one coherent input/boot edge; no data resets.
    (* keep = 1, face_keep = 1 *) reg  pcin_rst_n;
    always @(posedge ck[0]) pcin_rst_n <= 1'b1;
    (* keep = 1, face_keep = 1 *) reg [1:0] pcin_cfg_stack;
    always @(posedge ck[0]) pcin_cfg_stack <= cfg_stack;
    (* keep = 1, face_keep = 1 *) reg [779:0] pcin_di;
    always @(posedge ck[0]) pcin_di <= di;
    (* keep = 1, face_keep = 1 *) reg [260:0] pcin_land_er;
    always @(posedge ck[0]) pcin_land_er <= land_er;

    qkd_kv_pc_chain_station_b_p u_leaf (
        .ck(ck[0]),
        .rst_n(pcin_rst_n),
        .cfg_stack(pcin_cfg_stack),
        .di(pcin_di),
        .dout(dout),
        .land_es(land_es),
        .land_er(pcin_land_er),
        .wes(wes),
        .es_context(es_context),
        .es_expected_valid(es_expected_valid),
        .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address),
        .es_expected_pc(es_expected_pc),
        .es_expected_stack(es_expected_stack),
        .emb_issue_v(emb_issue_v),
        .emb_token(emb_token),
        .emb_word_index(emb_word_index),
        .emb_half(emb_half),
        .emb_scale(emb_scale),
        .emb_epoch(emb_epoch),
        .emb_return_slot(emb_return_slot),
        .capture_slot(capture_slot),
        .transfer_slot(transfer_slot),
        .fault(fault)
    );
endmodule
