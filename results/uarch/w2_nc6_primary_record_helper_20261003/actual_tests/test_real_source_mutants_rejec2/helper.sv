`timescale 1ps/1ps
// Default-off typed wire view of existing 182/219 sealed primary records.
// CURRENT status comes from same-word codec seal/padding checks; no cached clean.
// No new state, normal release, repair, count credit or owner retirement is implemented.
module ot_w2_nc6_primary_record_view #(parameter bit OPT_PROTECTION=0) (
 input wire [9635:0] current_payload,
 input wire [218:0] current_clean,current_ce,current_bad,
 output wire [334:0] held_request,
 output wire [0:0] held_request_clean,
 output wire [296:0] held_read_query,
 output wire [0:0] held_read_query_clean,
 output wire [40:0] held_write_query,
 output wire [0:0] held_write_query_clean,
 output wire [299:0] held_read_delivery,
 output wire [0:0] held_read_delivery_clean,
 output wire [782:0] journal,
 output wire [8:0] journal_clean,
 output wire [767:0] correction,
 output wire [7:0] correction_clean,
 output wire [389:0] query_pipeline,
 output wire [5:0] query_pipeline_clean,
 output wire [29:0] write_selection,
 output wire [5:0] write_selection_clean,
 output wire [78:0] scheduler,
 output wire [0:0] scheduler_clean,
 output wire [2:0] round_robin,
 output wire [0:0] round_robin_clean,
 output wire primary_clean,primary_ce,primary_bad
);
generate if (OPT_PROTECTION) begin:g_enabled
wire [218:0] qualified = current_clean & ~(current_ce | current_bad);
// request_holder[0] global words 96,97,98,99,100,101,102,103
assign held_request[0 +: 335] = {current_payload[4532 +: 27], current_payload[4488 +: 44], current_payload[4444 +: 44], current_payload[4400 +: 44], current_payload[4356 +: 44], current_payload[4312 +: 44], current_payload[4268 +: 44], current_payload[4224 +: 44]};
assign held_request_clean[0] = qualified[96] & qualified[97] & qualified[98] & qualified[99] & qualified[100] & qualified[101] & qualified[102] & qualified[103];
// read_query[0] global words 104,105,106,107,108,109,110
assign held_read_query[0 +: 297] = {current_payload[4840 +: 33], current_payload[4796 +: 44], current_payload[4752 +: 44], current_payload[4708 +: 44], current_payload[4664 +: 44], current_payload[4620 +: 44], current_payload[4576 +: 44]};
assign held_read_query_clean[0] = qualified[104] & qualified[105] & qualified[106] & qualified[107] & qualified[108] & qualified[109] & qualified[110];
// write_query[0] global words 111
assign held_write_query[0 +: 41] = current_payload[4884 +: 41];
assign held_write_query_clean[0] = qualified[111];
// read_delivery[0] global words 112,113,114,115,116,117,118
assign held_read_delivery[0 +: 300] = {current_payload[5192 +: 36], current_payload[5148 +: 44], current_payload[5104 +: 44], current_payload[5060 +: 44], current_payload[5016 +: 44], current_payload[4972 +: 44], current_payload[4928 +: 44]};
assign held_read_delivery_clean[0] = qualified[112] & qualified[113] & qualified[114] & qualified[115] & qualified[116] & qualified[117] & qualified[118];
// prepared_write[0] global words 169,170
assign journal[0 +: 87] = {current_payload[7480 +: 43], current_payload[7436 +: 44]};
assign journal_clean[0] = qualified[169] & qualified[170];
// prepared_write[1] global words 171,172
assign journal[87 +: 87] = {current_payload[7568 +: 43], current_payload[7524 +: 44]};
assign journal_clean[1] = qualified[171] & qualified[172];
// prepared_write[2] global words 173,174
assign journal[174 +: 87] = {current_payload[7656 +: 43], current_payload[7612 +: 44]};
assign journal_clean[2] = qualified[173] & qualified[174];
// prepared_write[3] global words 175,176
assign journal[261 +: 87] = {current_payload[7744 +: 43], current_payload[7700 +: 44]};
assign journal_clean[3] = qualified[175] & qualified[176];
// prepared_write[4] global words 177,178
assign journal[348 +: 87] = {current_payload[7832 +: 43], current_payload[7788 +: 44]};
assign journal_clean[4] = qualified[177] & qualified[178];
// prepared_write[5] global words 179,180
assign journal[435 +: 87] = {current_payload[7920 +: 43], current_payload[7876 +: 44]};
assign journal_clean[5] = qualified[179] & qualified[180];
// prepared_write[6] global words 181,182
assign journal[522 +: 87] = {current_payload[8008 +: 43], current_payload[7964 +: 44]};
assign journal_clean[6] = qualified[181] & qualified[182];
// prepared_write[7] global words 183,184
assign journal[609 +: 87] = {current_payload[8096 +: 43], current_payload[8052 +: 44]};
assign journal_clean[7] = qualified[183] & qualified[184];
// prepared_write[8] global words 185,186
assign journal[696 +: 87] = {current_payload[8184 +: 43], current_payload[8140 +: 44]};
assign journal_clean[8] = qualified[185] & qualified[186];
// correction_context[0] global words 145,146,147
assign correction[0 +: 96] = {current_payload[6468 +: 8], current_payload[6424 +: 44], current_payload[6380 +: 44]};
assign correction_clean[0] = qualified[145] & qualified[146] & qualified[147];
// correction_context[1] global words 148,149,150
assign correction[96 +: 96] = {current_payload[6600 +: 8], current_payload[6556 +: 44], current_payload[6512 +: 44]};
assign correction_clean[1] = qualified[148] & qualified[149] & qualified[150];
// correction_context[2] global words 151,152,153
assign correction[192 +: 96] = {current_payload[6732 +: 8], current_payload[6688 +: 44], current_payload[6644 +: 44]};
assign correction_clean[2] = qualified[151] & qualified[152] & qualified[153];
// correction_context[3] global words 154,155,156
assign correction[288 +: 96] = {current_payload[6864 +: 8], current_payload[6820 +: 44], current_payload[6776 +: 44]};
assign correction_clean[3] = qualified[154] & qualified[155] & qualified[156];
// correction_context[4] global words 157,158,159
assign correction[384 +: 96] = {current_payload[6996 +: 8], current_payload[6952 +: 44], current_payload[6908 +: 44]};
assign correction_clean[4] = qualified[157] & qualified[158] & qualified[159];
// correction_context[5] global words 160,161,162
assign correction[480 +: 96] = {current_payload[7128 +: 8], current_payload[7084 +: 44], current_payload[7040 +: 44]};
assign correction_clean[5] = qualified[160] & qualified[161] & qualified[162];
// correction_context[6] global words 163,164,165
assign correction[576 +: 96] = {current_payload[7260 +: 8], current_payload[7216 +: 44], current_payload[7172 +: 44]};
assign correction_clean[6] = qualified[163] & qualified[164] & qualified[165];
// correction_context[7] global words 166,167,168
assign correction[672 +: 96] = {current_payload[7392 +: 8], current_payload[7348 +: 44], current_payload[7304 +: 44]};
assign correction_clean[7] = qualified[166] & qualified[167] & qualified[168];
// query_pipeline[0] global words 133,134
assign query_pipeline[0 +: 65] = {current_payload[5896 +: 21], current_payload[5852 +: 44]};
assign query_pipeline_clean[0] = qualified[133] & qualified[134];
// query_pipeline[1] global words 135,136
assign query_pipeline[65 +: 65] = {current_payload[5984 +: 21], current_payload[5940 +: 44]};
assign query_pipeline_clean[1] = qualified[135] & qualified[136];
// query_pipeline[2] global words 137,138
assign query_pipeline[130 +: 65] = {current_payload[6072 +: 21], current_payload[6028 +: 44]};
assign query_pipeline_clean[2] = qualified[137] & qualified[138];
// query_pipeline[3] global words 139,140
assign query_pipeline[195 +: 65] = {current_payload[6160 +: 21], current_payload[6116 +: 44]};
assign query_pipeline_clean[3] = qualified[139] & qualified[140];
// query_pipeline[4] global words 141,142
assign query_pipeline[260 +: 65] = {current_payload[6248 +: 21], current_payload[6204 +: 44]};
assign query_pipeline_clean[4] = qualified[141] & qualified[142];
// query_pipeline[5] global words 143,144
assign query_pipeline[325 +: 65] = {current_payload[6336 +: 21], current_payload[6292 +: 44]};
assign query_pipeline_clean[5] = qualified[143] & qualified[144];
// write_selection[0] global words 119
assign write_selection[0 +: 5] = current_payload[5236 +: 5];
assign write_selection_clean[0] = qualified[119];
// write_selection[1] global words 120
assign write_selection[5 +: 5] = current_payload[5280 +: 5];
assign write_selection_clean[1] = qualified[120];
// write_selection[2] global words 121
assign write_selection[10 +: 5] = current_payload[5324 +: 5];
assign write_selection_clean[2] = qualified[121];
// write_selection[3] global words 122
assign write_selection[15 +: 5] = current_payload[5368 +: 5];
assign write_selection_clean[3] = qualified[122];
// write_selection[4] global words 123
assign write_selection[20 +: 5] = current_payload[5412 +: 5];
assign write_selection_clean[4] = qualified[123];
// write_selection[5] global words 124
assign write_selection[25 +: 5] = current_payload[5456 +: 5];
assign write_selection_clean[5] = qualified[124];
// protected_scheduler[0] global words 187,188
assign scheduler[0 +: 79] = {current_payload[8272 +: 35], current_payload[8228 +: 44]};
assign scheduler_clean[0] = qualified[187] & qualified[188];
// round_robin[0] global words 131
assign round_robin[0 +: 3] = current_payload[5764 +: 3];
assign round_robin_clean[0] = qualified[131];
localparam [218:0] PRIMARY_MASK = 219'h000000017ffffffffffffe81fffffffffffffffffffffffffffffff;
assign primary_clean = (qualified & PRIMARY_MASK) == PRIMARY_MASK;
assign primary_ce = |(current_ce & PRIMARY_MASK);
assign primary_bad = |(current_bad & PRIMARY_MASK);
end else begin:g_disabled
assign held_request = '0;
assign held_request_clean = '0;
assign held_read_query = '0;
assign held_read_query_clean = '0;
assign held_write_query = '0;
assign held_write_query_clean = '0;
assign held_read_delivery = '0;
assign held_read_delivery_clean = '0;
assign journal = '0;
assign journal_clean = '0;
assign correction = '0;
assign correction_clean = '0;
assign query_pipeline = '0;
assign query_pipeline_clean = '0;
assign write_selection = '0;
assign write_selection_clean = '0;
assign scheduler = '0;
assign scheduler_clean = '0;
assign round_robin = '0;
assign round_robin_clean = '0;
assign primary_clean=1'b0; assign primary_ce=1'b0; assign primary_bad=1'b0;
end endgenerate
endmodule
