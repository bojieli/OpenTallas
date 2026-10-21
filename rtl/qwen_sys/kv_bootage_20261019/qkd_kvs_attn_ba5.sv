`timescale 1ns/1ps
module qkd_kvs_attn_ba5 (
    input wire ck,
    input wire rst_n,
    input wire [0:0] ufs_WS,
    input wire [0:0] ufs_WN,
    input wire [0:0] ufs_ES,
    input wire [0:0] ufs_EN,
    input wire [0:0] ufh,
    input wire [0:0] ufp0,
    input wire [0:0] ufp1,
    input wire [0:0] uff,
    input wire [0:0] ufk_WS,
    input wire [0:0] ufk_WN,
    input wire [0:0] ufk_ES,
    input wire [0:0] ufk_EN,
    input wire [521:0] d2d__srx,
    input wire [547:0] d2d__rx_payload,
    input wire [0:0] d2d__att_tx_slot,
    input wire [3:0] d2d__att_tx_kind,
    input wire [4:0] d2d__att_tx_beat,
    input wire [533:0] fin,
    output wire [0:0] attn__tx_valid,
    output wire [547:0] attn__tx_payload,
    output wire [30:0] pvst,
    output wire [64:0] pvfst,
    output wire [164:0] ahs,
    output wire [536:0] prg,
    output wire [47:0] acal_WS,
    output wire [47:0] acal_WN,
    output wire [47:0] acal_ES,
    output wire [47:0] acal_EN,
    output wire [7:0] arh,
    input wire [108:0] i_ctl
);
    wire [7:0] attn_root__cfg_pv_lead = i_ctl[7:0];
    wire [7:0] attn_cal__cfg_cal__0 = i_ctl[15:8];
    wire [7:0] attn_cal__cfg_cal__2 = i_ctl[23:16];
    wire [7:0] attn_cal__cfg_cal__1 = i_ctl[31:24];
    wire [0:0] attn__fused_program_capability = i_ctl[32:32];
    wire [0:0] attn__authority_valid = i_ctl[33:33];
    wire [0:0] attn__issue = i_ctl[34:34];
    wire [0:0] attn__run = i_ctl[35:35];
    wire [13:0] attn_cal__ctx_t = i_ctl[49:36];
    wire [15:0] attn__authority_epoch = i_ctl[65:50];
    wire [17:0] attn__authority_position = i_ctl[83:66];
    wire [5:0] attn__authority_stage = i_ctl[89:84];
    wire [0:0] attn_cal__go = i_ctl[90:90];
    wire [17:0] attn__authority_token = i_ctl[108:91];
    wire [9:0] w_afr__unit_fault;
    wire [0:0] w_attn__tx_valid;
    wire [547:0] w_attn__tx_payload;
    wire [0:0] w_attn__request_valid;
    wire [15:0] w_attn__request_epoch;
    wire [5:0] w_attn__request_layer;
    wire [17:0] w_attn__request_position;
    wire [175:0] w_attn__request_calendar;
    wire [0:0] w_attn__q_valid;
    wire [4:0] w_attn__q_beat;
    wire [511:0] w_attn__q_data;
    wire [0:0] w_attn__result_reserved;
    wire [0:0] w_attn__busy;
    wire [0:0] w_attn__fault;
    wire [15:0] w_attn__age;
    wire [536:0] w_attn__prg_l;
    wire [175:0] w_attn_cal__cal;
    wire [15:0] w_attn_cal__rx_cmd;
    wire [15:0] w_attn_cal__tx_first;
    wire [15:0] w_attn_cal__end_age;
    wire [15:0] w_attn_cal__cal_epoch;
    wire [0:0] w_attn_cal__done;
    wire [0:0] w_attn_cal__valid;
    wire [0:0] w_attn_cal__fault;
    wire [0:0] w_attn_face__result_valid;
    wire [4:0] w_attn_face__result_beat;
    wire [511:0] w_attn_face__result_data;
    wire [15:0] w_attn_face__result_epoch;
    wire [5:0] w_attn_face__result_layer;
    wire [0:0] w_attn_face__result_done;
    wire [0:0] w_attn_face__service_fault;
    wire [0:0] w_attn_face__result_fault;
    wire [7:0] w_attn_face__hdr_l;
    wire [0:0] w_attn_root__request_ready;
    wire [0:0] w_attn_root__q_ready;
    wire [0:0] w_attn_root__running;
    wire [0:0] w_attn_root__start_qk;
    wire [0:0] w_attn_root__start_pv;
    wire [15:0] w_attn_root__age;
    wire [15:0] w_attn_root__ep;
    wire [5:0] w_attn_root__layer;
    wire [13:0] w_attn_root__ctx;
    wire [175:0] w_attn_root__cal;
    wire [31:0] w_attn_root__cycles;
    wire [0:0] w_attn_root__local_fault;
    wire [0:0] w_attn_root__io_fault;
    qkd_attn_fault_root #(.ND(8), .NC(4), .MUT(0)) u_afr (.ck(ck), .rst_n(rst_n), .d({uff, ufp1, ufp0, ufh, ufs_EN, ufs_ES, ufs_WN, ufs_WS}), .c({ufk_EN, ufk_ES, ufk_WN, ufk_WS}), .unit_fault(w_afr__unit_fault));
    qkd_native_attention_programme_ba4 #(.MUT(0), .LAND(1)) u_attn (.ck(ck), .rst_n(rst_n), .issue(attn__issue), .run(attn__run), .fused_program_capability(attn__fused_program_capability), .authority_valid(attn__authority_valid), .authority_epoch(attn__authority_epoch), .authority_token(attn__authority_token), .authority_position(attn__authority_position), .authority_stage(attn__authority_stage), .compiled_calendar(w_attn_cal__cal[175:0]), .compiled_rx_cmd(w_attn_cal__rx_cmd[15:0]), .compiled_tx_first(w_attn_cal__tx_first[15:0]), .compiled_end(w_attn_cal__end_age[15:0]), .rx_event(d2d__srx[0:0]), .rx_payload(d2d__rx_payload[547:0]), .tx_slot(d2d__att_tx_slot[0:0]), .tx_slot_kind(d2d__att_tx_kind[3:0]), .tx_slot_beat(d2d__att_tx_beat[4:0]), .tx_valid(w_attn__tx_valid), .tx_payload(w_attn__tx_payload), .request_valid(w_attn__request_valid), .request_ready(w_attn_root__request_ready[0:0]), .request_epoch(w_attn__request_epoch), .request_layer(w_attn__request_layer), .request_position(w_attn__request_position), .request_calendar(w_attn__request_calendar), .q_valid(w_attn__q_valid), .q_beat(w_attn__q_beat), .q_data(w_attn__q_data), .result_valid(w_attn_face__result_valid[0:0]), .result_beat(w_attn_face__result_beat[4:0]), .result_data(w_attn_face__result_data[511:0]), .result_epoch(w_attn_face__result_epoch[15:0]), .result_layer(w_attn_face__result_layer[5:0]), .result_done(w_attn_face__result_done[0:0]), .service_fault(w_attn_face__service_fault[0:0]), .result_reserved(w_attn__result_reserved), .busy(w_attn__busy), .fault(w_attn__fault), .age(w_attn__age), .prg_l(w_attn__prg_l));
    qkd_attn_cal_gen_b #(.G3S2(1), .RX_CMD(2), .STRETCH(1), .SERVICE_END(1777), .MUT(0), .D_QK(255), .D_RL(255), .F_DLY(127)) u_attn_cal (.ck(ck), .rst_n(rst_n), .cfg_cal({attn_cal__cfg_cal__0, attn_cal__cfg_cal__1, attn_cal__cfg_cal__2}), .go(attn_cal__go), .ctx_t(attn_cal__ctx_t), .epoch(attn__authority_epoch), .cal(w_attn_cal__cal), .rx_cmd(w_attn_cal__rx_cmd), .tx_first(w_attn_cal__tx_first), .end_age(w_attn_cal__end_age), .cal_epoch(w_attn_cal__cal_epoch), .done(w_attn_cal__done), .valid(w_attn_cal__valid), .fault(w_attn_cal__fault));
    qkd_attn_result_face_sc #(.NF(10), .RESULT_RELAY(0), .F_DLY(127), .CAL_PIPE(1), .MUT(0)) u_attn_face (.ck(ck), .rst_n(rst_n), .cfg_f_dly(attn_cal__cfg_cal__0), .running(w_attn_root__running[0:0]), .start_qk(w_attn_root__start_qk[0:0]), .age(w_attn_root__age[15:0]), .ep(w_attn_root__ep[15:0]), .layer(w_attn_root__layer[5:0]), .cal(w_attn_root__cal[175:0]), .root_local_fault(w_attn_root__local_fault[0:0]), .root_io_fault(w_attn_root__io_fault[0:0]), .f_valid(fin[0]), .f_beat(fin[5:1]), .f_data(fin[533:22]), .f_epoch(fin[21:6]), .unit_fault(w_afr__unit_fault[9:0]), .result_valid(w_attn_face__result_valid), .result_beat(w_attn_face__result_beat), .result_data(w_attn_face__result_data), .result_epoch(w_attn_face__result_epoch), .result_layer(w_attn_face__result_layer), .result_done(w_attn_face__result_done), .service_fault(w_attn_face__service_fault), .result_fault(w_attn_face__result_fault), .hdr_l(w_attn_face__hdr_l));
    qkd_attn_service_root_b #(.PV_LEAD(63), .CAL_PIPE(1), .MUT(0)) u_attn_root (.ck(ck), .rst_n(rst_n), .cfg_pv_lead(attn_root__cfg_pv_lead), .cfg_f_dly(attn_cal__cfg_cal__0), .request_valid(w_attn__request_valid[0:0]), .request_ready(w_attn_root__request_ready), .request_epoch(w_attn__request_epoch[15:0]), .request_layer(w_attn__request_layer[5:0]), .request_position(w_attn__request_position[17:0]), .fused_program_capability(attn__fused_program_capability), .request_calendar(w_attn__request_calendar[175:0]), .q_valid(w_attn__q_valid[0:0]), .q_beat(w_attn__q_beat[4:0]), .q_ready(w_attn_root__q_ready), .running(w_attn_root__running), .start_qk(w_attn_root__start_qk), .start_pv(w_attn_root__start_pv), .age(w_attn_root__age), .ep(w_attn_root__ep), .layer(w_attn_root__layer), .ctx(w_attn_root__ctx), .cal(w_attn_root__cal), .cycles(w_attn_root__cycles), .local_fault(w_attn_root__local_fault), .io_fault(w_attn_root__io_fault));
    assign attn__tx_valid = w_attn__tx_valid;
    assign attn__tx_payload = w_attn__tx_payload;
    assign pvst = {w_attn_root__ep, w_attn_root__ctx, w_attn_root__start_pv};
    assign pvfst = {w_attn_root__cal[175:128], w_attn_root__ep, w_attn_root__start_pv};
    assign ahs = {w_attn_root__cal[175:160], w_attn_root__cal[127:16], w_attn_root__ctx, w_attn_root__layer, w_attn_root__ep, w_attn_root__start_qk};
    assign prg = w_attn__prg_l;
    assign acal_WS = {w_attn_root__cal[15:0], w_attn_root__cal[47:32], w_attn_root__cal[31:16]};
    assign acal_WN = {w_attn_root__cal[15:0], w_attn_root__cal[47:32], w_attn_root__cal[31:16]};
    assign acal_ES = {w_attn_root__cal[15:0], w_attn_root__cal[47:32], w_attn_root__cal[31:16]};
    assign acal_EN = {w_attn_root__cal[15:0], w_attn_root__cal[47:32], w_attn_root__cal[31:16]};
    assign arh = w_attn_face__hdr_l;
endmodule
