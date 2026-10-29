`timescale 1ns/1ps
module qkd_kvs_pc_h_head_p #(
    parameter KVSPC_INPUT_COLLAR = 0,
    parameter [4:0] PC = 0
) (
    input wire ck,
    input wire rst_n,
    input wire hck,
    input wire hrst_n,
    input wire [288:0] pc__pi,
    input wire [32:0] pc__ki,
    input wire [1:0] pc__cfg_stack,
    input wire [3:0] pc__front_hbm_data,
    input wire [3:0] pc__return_hbm_data,
    input wire [0:0] x__est__0_1,
    input wire [260:0] pc__land_er,
    input wire [287:0] pc__hes,
    output wire [0:0] pc__fo,
    output wire [260:0] pc__er,
    output wire [32:0] pc__ko,
    output wire [327:0] pc__po,
    output wire [0:0] pc__completion_v,
    output wire [0:0] pc__completion_we,
    output wire [287:0] pc__land_es,
    output wire [260:0] pc__her,
    output wire [0:0] pc__hcompletion_v,
    output wire [0:0] pc__hcompletion_we,
    input wire [127:0] i_grp,
    input wire [779:0] i_next,
    output wire [304:0] o_grp,
    output wire [298:0] o_next
,
    output wire [779:0] coupon_dout,
    output wire [287:0] coupon_land_es,
    output wire [287:0] coupon_wes,
    output wire [317:0] coupon_es_context,
    output wire  coupon_es_expected_valid,
    output wire [60:0] coupon_es_expected_identity,
    output wire [28:0] coupon_es_expected_address,
    output wire [4:0] coupon_es_expected_pc,
    output wire [1:0] coupon_es_expected_stack,
    output wire  coupon_emb_issue_v,
    output wire [17:0] coupon_emb_token,
    output wire [5:0] coupon_emb_word_index,
    output wire  coupon_emb_half,
    output wire  coupon_emb_scale,
    output wire [15:0] coupon_emb_epoch,
    output wire  coupon_emb_return_slot,
    output wire  coupon_capture_slot,
    output wire  coupon_transfer_slot,
    output wire  coupon_fault
);
    // KVSPC_NATIVE_INPUT_COLLAR: parent and physical sources must select exactly once.
    wire  pcin_native_hrst_n;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_hrst_n
        (* keep = 1, face_keep = 1 *) reg  pcin_hrst_n;
        always @(posedge ck) pcin_hrst_n <= hrst_n;
        assign pcin_native_hrst_n = pcin_hrst_n;
    end else begin
        assign pcin_native_hrst_n = hrst_n;
    end endgenerate
    wire [127:0] pcin_native_i_grp;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_i_grp
        (* keep = 1, face_keep = 1 *) reg [127:0] pcin_i_grp;
        always @(posedge ck) pcin_i_grp <= i_grp[127:0];
        assign pcin_native_i_grp = {pcin_i_grp[127], pcin_i_grp[126], pcin_i_grp[125], pcin_i_grp[124], pcin_i_grp[123], pcin_i_grp[122], pcin_i_grp[121], pcin_i_grp[120], pcin_i_grp[119], pcin_i_grp[118], pcin_i_grp[117], pcin_i_grp[116], pcin_i_grp[115], pcin_i_grp[114], pcin_i_grp[113], pcin_i_grp[112], pcin_i_grp[111], pcin_i_grp[110], pcin_i_grp[109], pcin_i_grp[108], pcin_i_grp[107], pcin_i_grp[106], pcin_i_grp[105], pcin_i_grp[104], pcin_i_grp[103], pcin_i_grp[102], pcin_i_grp[101], pcin_i_grp[100], pcin_i_grp[99], pcin_i_grp[98], pcin_i_grp[97], pcin_i_grp[96], pcin_i_grp[95], pcin_i_grp[94], pcin_i_grp[93], pcin_i_grp[92], pcin_i_grp[91], pcin_i_grp[90], pcin_i_grp[89], pcin_i_grp[88], pcin_i_grp[87], pcin_i_grp[86], pcin_i_grp[85], pcin_i_grp[84], pcin_i_grp[83], pcin_i_grp[82], pcin_i_grp[81], pcin_i_grp[80], pcin_i_grp[79], pcin_i_grp[78], pcin_i_grp[77], pcin_i_grp[76], pcin_i_grp[75], pcin_i_grp[74], pcin_i_grp[73], pcin_i_grp[72], pcin_i_grp[71], pcin_i_grp[70], pcin_i_grp[69], pcin_i_grp[68], pcin_i_grp[67], pcin_i_grp[66], pcin_i_grp[65], pcin_i_grp[64], pcin_i_grp[63], pcin_i_grp[62], pcin_i_grp[61], pcin_i_grp[60], pcin_i_grp[59], pcin_i_grp[58], pcin_i_grp[57], pcin_i_grp[56], pcin_i_grp[55], pcin_i_grp[54], pcin_i_grp[53], pcin_i_grp[52], pcin_i_grp[51], pcin_i_grp[50], pcin_i_grp[49], pcin_i_grp[48], pcin_i_grp[47], pcin_i_grp[46], pcin_i_grp[45], pcin_i_grp[44], pcin_i_grp[43], pcin_i_grp[42], pcin_i_grp[41], pcin_i_grp[40], pcin_i_grp[39], pcin_i_grp[38], pcin_i_grp[37], pcin_i_grp[36], pcin_i_grp[35], pcin_i_grp[34], pcin_i_grp[33], pcin_i_grp[32], pcin_i_grp[31], pcin_i_grp[30], pcin_i_grp[29], pcin_i_grp[28], pcin_i_grp[27], pcin_i_grp[26], pcin_i_grp[25], pcin_i_grp[24], pcin_i_grp[23], pcin_i_grp[22], pcin_i_grp[21], pcin_i_grp[20], pcin_i_grp[19], pcin_i_grp[18], pcin_i_grp[17], pcin_i_grp[16], pcin_i_grp[15], pcin_i_grp[14], pcin_i_grp[13], pcin_i_grp[12], pcin_i_grp[11], pcin_i_grp[10], pcin_i_grp[9], pcin_i_grp[8], pcin_i_grp[7], pcin_i_grp[6], pcin_i_grp[5], pcin_i_grp[4], pcin_i_grp[3], pcin_i_grp[2], pcin_i_grp[1], pcin_i_grp[0]};
    end else begin
        assign pcin_native_i_grp = i_grp;
    end endgenerate
    wire [1:0] pcin_native_pc__cfg_stack;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__cfg_stack
        (* keep = 1, face_keep = 1 *) reg [1:0] pcin_pc__cfg_stack;
        always @(posedge ck) pcin_pc__cfg_stack <= pc__cfg_stack[1:0];
        assign pcin_native_pc__cfg_stack = {pcin_pc__cfg_stack[1], pcin_pc__cfg_stack[0]};
    end else begin
        assign pcin_native_pc__cfg_stack = pc__cfg_stack;
    end endgenerate
    wire [288:0] pcin_native_pc__pi;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__pi
        (* keep = 1, face_keep = 1 *) reg [288:0] pcin_pc__pi;
        always @(posedge ck) pcin_pc__pi <= pc__pi[288:0];
        assign pcin_native_pc__pi = {pcin_pc__pi[288], pcin_pc__pi[287], pcin_pc__pi[286], pcin_pc__pi[285], pcin_pc__pi[284], pcin_pc__pi[283], pcin_pc__pi[282], pcin_pc__pi[281], pcin_pc__pi[280], pcin_pc__pi[279], pcin_pc__pi[278], pcin_pc__pi[277], pcin_pc__pi[276], pcin_pc__pi[275], pcin_pc__pi[274], pcin_pc__pi[273], pcin_pc__pi[272], pcin_pc__pi[271], pcin_pc__pi[270], pcin_pc__pi[269], pcin_pc__pi[268], pcin_pc__pi[267], pcin_pc__pi[266], pcin_pc__pi[265], pcin_pc__pi[264], pcin_pc__pi[263], pcin_pc__pi[262], pcin_pc__pi[261], pcin_pc__pi[260], pcin_pc__pi[259], pcin_pc__pi[258], pcin_pc__pi[257], pcin_pc__pi[256], pcin_pc__pi[255], pcin_pc__pi[254], pcin_pc__pi[253], pcin_pc__pi[252], pcin_pc__pi[251], pcin_pc__pi[250], pcin_pc__pi[249], pcin_pc__pi[248], pcin_pc__pi[247], pcin_pc__pi[246], pcin_pc__pi[245], pcin_pc__pi[244], pcin_pc__pi[243], pcin_pc__pi[242], pcin_pc__pi[241], pcin_pc__pi[240], pcin_pc__pi[239], pcin_pc__pi[238], pcin_pc__pi[237], pcin_pc__pi[236], pcin_pc__pi[235], pcin_pc__pi[234], pcin_pc__pi[233], pcin_pc__pi[232], pcin_pc__pi[231], pcin_pc__pi[230], pcin_pc__pi[229], pcin_pc__pi[228], pcin_pc__pi[227], pcin_pc__pi[226], pcin_pc__pi[225], pcin_pc__pi[224], pcin_pc__pi[223], pcin_pc__pi[222], pcin_pc__pi[221], pcin_pc__pi[220], pcin_pc__pi[219], pcin_pc__pi[218], pcin_pc__pi[217], pcin_pc__pi[216], pcin_pc__pi[215], pcin_pc__pi[214], pcin_pc__pi[213], pcin_pc__pi[212], pcin_pc__pi[211], pcin_pc__pi[210], pcin_pc__pi[209], pcin_pc__pi[208], pcin_pc__pi[207], pcin_pc__pi[206], pcin_pc__pi[205], pcin_pc__pi[204], pcin_pc__pi[203], pcin_pc__pi[202], pcin_pc__pi[201], pcin_pc__pi[200], pcin_pc__pi[199], pcin_pc__pi[198], pcin_pc__pi[197], pcin_pc__pi[196], pcin_pc__pi[195], pcin_pc__pi[194], pcin_pc__pi[193], pcin_pc__pi[192], pcin_pc__pi[191], pcin_pc__pi[190], pcin_pc__pi[189], pcin_pc__pi[188], pcin_pc__pi[187], pcin_pc__pi[186], pcin_pc__pi[185], pcin_pc__pi[184], pcin_pc__pi[183], pcin_pc__pi[182], pcin_pc__pi[181], pcin_pc__pi[180], pcin_pc__pi[179], pcin_pc__pi[178], pcin_pc__pi[177], pcin_pc__pi[176], pcin_pc__pi[175], pcin_pc__pi[174], pcin_pc__pi[173], pcin_pc__pi[172], pcin_pc__pi[171], pcin_pc__pi[170], pcin_pc__pi[169], pcin_pc__pi[168], pcin_pc__pi[167], pcin_pc__pi[166], pcin_pc__pi[165], pcin_pc__pi[164], pcin_pc__pi[163], pcin_pc__pi[162], pcin_pc__pi[161], pcin_pc__pi[160], pcin_pc__pi[159], pcin_pc__pi[158], pcin_pc__pi[157], pcin_pc__pi[156], pcin_pc__pi[155], pcin_pc__pi[154], pcin_pc__pi[153], pcin_pc__pi[152], pcin_pc__pi[151], pcin_pc__pi[150], pcin_pc__pi[149], pcin_pc__pi[148], pcin_pc__pi[147], pcin_pc__pi[146], pcin_pc__pi[145], pcin_pc__pi[144], pcin_pc__pi[143], pcin_pc__pi[142], pcin_pc__pi[141], pcin_pc__pi[140], pcin_pc__pi[139], pcin_pc__pi[138], pcin_pc__pi[137], pcin_pc__pi[136], pcin_pc__pi[135], pcin_pc__pi[134], pcin_pc__pi[133], pcin_pc__pi[132], pcin_pc__pi[131], pcin_pc__pi[130], pcin_pc__pi[129], pcin_pc__pi[128], pcin_pc__pi[127], pcin_pc__pi[126], pcin_pc__pi[125], pcin_pc__pi[124], pcin_pc__pi[123], pcin_pc__pi[122], pcin_pc__pi[121], pcin_pc__pi[120], pcin_pc__pi[119], pcin_pc__pi[118], pcin_pc__pi[117], pcin_pc__pi[116], pcin_pc__pi[115], pcin_pc__pi[114], pcin_pc__pi[113], pcin_pc__pi[112], pcin_pc__pi[111], pcin_pc__pi[110], pcin_pc__pi[109], pcin_pc__pi[108], pcin_pc__pi[107], pcin_pc__pi[106], pcin_pc__pi[105], pcin_pc__pi[104], pcin_pc__pi[103], pcin_pc__pi[102], pcin_pc__pi[101], pcin_pc__pi[100], pcin_pc__pi[99], pcin_pc__pi[98], pcin_pc__pi[97], pcin_pc__pi[96], pcin_pc__pi[95], pcin_pc__pi[94], pcin_pc__pi[93], pcin_pc__pi[92], pcin_pc__pi[91], pcin_pc__pi[90], pcin_pc__pi[89], pcin_pc__pi[88], pcin_pc__pi[87], pcin_pc__pi[86], pcin_pc__pi[85], pcin_pc__pi[84], pcin_pc__pi[83], pcin_pc__pi[82], pcin_pc__pi[81], pcin_pc__pi[80], pcin_pc__pi[79], pcin_pc__pi[78], pcin_pc__pi[77], pcin_pc__pi[76], pcin_pc__pi[75], pcin_pc__pi[74], pcin_pc__pi[73], pcin_pc__pi[72], pcin_pc__pi[71], pcin_pc__pi[70], pcin_pc__pi[69], pcin_pc__pi[68], pcin_pc__pi[67], pcin_pc__pi[66], pcin_pc__pi[65], pcin_pc__pi[64], pcin_pc__pi[63], pcin_pc__pi[62], pcin_pc__pi[61], pcin_pc__pi[60], pcin_pc__pi[59], pcin_pc__pi[58], pcin_pc__pi[57], pcin_pc__pi[56], pcin_pc__pi[55], pcin_pc__pi[54], pcin_pc__pi[53], pcin_pc__pi[52], pcin_pc__pi[51], pcin_pc__pi[50], pcin_pc__pi[49], pcin_pc__pi[48], pcin_pc__pi[47], pcin_pc__pi[46], pcin_pc__pi[45], pcin_pc__pi[44], pcin_pc__pi[43], pcin_pc__pi[42], pcin_pc__pi[41], pcin_pc__pi[40], pcin_pc__pi[39], pcin_pc__pi[38], pcin_pc__pi[37], pcin_pc__pi[36], pcin_pc__pi[35], pcin_pc__pi[34], pcin_pc__pi[33], pcin_pc__pi[32], pcin_pc__pi[31], pcin_pc__pi[30], pcin_pc__pi[29], pcin_pc__pi[28], pcin_pc__pi[27], pcin_pc__pi[26], pcin_pc__pi[25], pcin_pc__pi[24], pcin_pc__pi[23], pcin_pc__pi[22], pcin_pc__pi[21], pcin_pc__pi[20], pcin_pc__pi[19], pcin_pc__pi[18], pcin_pc__pi[17], pcin_pc__pi[16], pcin_pc__pi[15], pcin_pc__pi[14], pcin_pc__pi[13], pcin_pc__pi[12], pcin_pc__pi[11], pcin_pc__pi[10], pcin_pc__pi[9], pcin_pc__pi[8], pcin_pc__pi[7], pcin_pc__pi[6], pcin_pc__pi[5], pcin_pc__pi[4], pcin_pc__pi[3], pcin_pc__pi[2], pcin_pc__pi[1], pcin_pc__pi[0]};
    end else begin
        assign pcin_native_pc__pi = pc__pi;
    end endgenerate
    wire [0:0] pcin_native_x__est__0_1;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_x__est__0_1
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_x__est__0_1;
        always @(posedge ck) pcin_x__est__0_1 <= x__est__0_1[0:0];
        assign pcin_native_x__est__0_1 = {pcin_x__est__0_1[0]};
    end else begin
        assign pcin_native_x__est__0_1 = x__est__0_1;
    end endgenerate
    wire [287:0] pcin_native_pc__hes;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__hes
        (* keep = 1, face_keep = 1 *) reg [287:0] pcin_pc__hes;
        always @(posedge ck) pcin_pc__hes <= pc__hes[287:0];
        assign pcin_native_pc__hes = {pcin_pc__hes[287], pcin_pc__hes[286], pcin_pc__hes[285], pcin_pc__hes[284], pcin_pc__hes[283], pcin_pc__hes[282], pcin_pc__hes[281], pcin_pc__hes[280], pcin_pc__hes[279], pcin_pc__hes[278], pcin_pc__hes[277], pcin_pc__hes[276], pcin_pc__hes[275], pcin_pc__hes[274], pcin_pc__hes[273], pcin_pc__hes[272], pcin_pc__hes[271], pcin_pc__hes[270], pcin_pc__hes[269], pcin_pc__hes[268], pcin_pc__hes[267], pcin_pc__hes[266], pcin_pc__hes[265], pcin_pc__hes[264], pcin_pc__hes[263], pcin_pc__hes[262], pcin_pc__hes[261], pcin_pc__hes[260], pcin_pc__hes[259], pcin_pc__hes[258], pcin_pc__hes[257], pcin_pc__hes[256], pcin_pc__hes[255], pcin_pc__hes[254], pcin_pc__hes[253], pcin_pc__hes[252], pcin_pc__hes[251], pcin_pc__hes[250], pcin_pc__hes[249], pcin_pc__hes[248], pcin_pc__hes[247], pcin_pc__hes[246], pcin_pc__hes[245], pcin_pc__hes[244], pcin_pc__hes[243], pcin_pc__hes[242], pcin_pc__hes[241], pcin_pc__hes[240], pcin_pc__hes[239], pcin_pc__hes[238], pcin_pc__hes[237], pcin_pc__hes[236], pcin_pc__hes[235], pcin_pc__hes[234], pcin_pc__hes[233], pcin_pc__hes[232], pcin_pc__hes[231], pcin_pc__hes[230], pcin_pc__hes[229], pcin_pc__hes[228], pcin_pc__hes[227], pcin_pc__hes[226], pcin_pc__hes[225], pcin_pc__hes[224], pcin_pc__hes[223], pcin_pc__hes[222], pcin_pc__hes[221], pcin_pc__hes[220], pcin_pc__hes[219], pcin_pc__hes[218], pcin_pc__hes[217], pcin_pc__hes[216], pcin_pc__hes[215], pcin_pc__hes[214], pcin_pc__hes[213], pcin_pc__hes[212], pcin_pc__hes[211], pcin_pc__hes[210], pcin_pc__hes[209], pcin_pc__hes[208], pcin_pc__hes[207], pcin_pc__hes[206], pcin_pc__hes[205], pcin_pc__hes[204], pcin_pc__hes[203], pcin_pc__hes[202], pcin_pc__hes[201], pcin_pc__hes[200], pcin_pc__hes[199], pcin_pc__hes[198], pcin_pc__hes[197], pcin_pc__hes[196], pcin_pc__hes[195], pcin_pc__hes[194], pcin_pc__hes[193], pcin_pc__hes[192], pcin_pc__hes[191], pcin_pc__hes[190], pcin_pc__hes[189], pcin_pc__hes[188], pcin_pc__hes[187], pcin_pc__hes[186], pcin_pc__hes[185], pcin_pc__hes[184], pcin_pc__hes[183], pcin_pc__hes[182], pcin_pc__hes[181], pcin_pc__hes[180], pcin_pc__hes[179], pcin_pc__hes[178], pcin_pc__hes[177], pcin_pc__hes[176], pcin_pc__hes[175], pcin_pc__hes[174], pcin_pc__hes[173], pcin_pc__hes[172], pcin_pc__hes[171], pcin_pc__hes[170], pcin_pc__hes[169], pcin_pc__hes[168], pcin_pc__hes[167], pcin_pc__hes[166], pcin_pc__hes[165], pcin_pc__hes[164], pcin_pc__hes[163], pcin_pc__hes[162], pcin_pc__hes[161], pcin_pc__hes[160], pcin_pc__hes[159], pcin_pc__hes[158], pcin_pc__hes[157], pcin_pc__hes[156], pcin_pc__hes[155], pcin_pc__hes[154], pcin_pc__hes[153], pcin_pc__hes[152], pcin_pc__hes[151], pcin_pc__hes[150], pcin_pc__hes[149], pcin_pc__hes[148], pcin_pc__hes[147], pcin_pc__hes[146], pcin_pc__hes[145], pcin_pc__hes[144], pcin_pc__hes[143], pcin_pc__hes[142], pcin_pc__hes[141], pcin_pc__hes[140], pcin_pc__hes[139], pcin_pc__hes[138], pcin_pc__hes[137], pcin_pc__hes[136], pcin_pc__hes[135], pcin_pc__hes[134], pcin_pc__hes[133], pcin_pc__hes[132], pcin_pc__hes[131], pcin_pc__hes[130], pcin_pc__hes[129], pcin_pc__hes[128], pcin_pc__hes[127], pcin_pc__hes[126], pcin_pc__hes[125], pcin_pc__hes[124], pcin_pc__hes[123], pcin_pc__hes[122], pcin_pc__hes[121], pcin_pc__hes[120], pcin_pc__hes[119], pcin_pc__hes[118], pcin_pc__hes[117], pcin_pc__hes[116], pcin_pc__hes[115], pcin_pc__hes[114], pcin_pc__hes[113], pcin_pc__hes[112], pcin_pc__hes[111], pcin_pc__hes[110], pcin_pc__hes[109], pcin_pc__hes[108], pcin_pc__hes[107], pcin_pc__hes[106], pcin_pc__hes[105], pcin_pc__hes[104], pcin_pc__hes[103], pcin_pc__hes[102], pcin_pc__hes[101], pcin_pc__hes[100], pcin_pc__hes[99], pcin_pc__hes[98], pcin_pc__hes[97], pcin_pc__hes[96], pcin_pc__hes[95], pcin_pc__hes[94], pcin_pc__hes[93], pcin_pc__hes[92], pcin_pc__hes[91], pcin_pc__hes[90], pcin_pc__hes[89], pcin_pc__hes[88], pcin_pc__hes[87], pcin_pc__hes[86], pcin_pc__hes[85], pcin_pc__hes[84], pcin_pc__hes[83], pcin_pc__hes[82], pcin_pc__hes[81], pcin_pc__hes[80], pcin_pc__hes[79], pcin_pc__hes[78], pcin_pc__hes[77], pcin_pc__hes[76], pcin_pc__hes[75], pcin_pc__hes[74], pcin_pc__hes[73], pcin_pc__hes[72], pcin_pc__hes[71], pcin_pc__hes[70], pcin_pc__hes[69], pcin_pc__hes[68], pcin_pc__hes[67], pcin_pc__hes[66], pcin_pc__hes[65], pcin_pc__hes[64], pcin_pc__hes[63], pcin_pc__hes[62], pcin_pc__hes[61], pcin_pc__hes[60], pcin_pc__hes[59], pcin_pc__hes[58], pcin_pc__hes[57], pcin_pc__hes[56], pcin_pc__hes[55], pcin_pc__hes[54], pcin_pc__hes[53], pcin_pc__hes[52], pcin_pc__hes[51], pcin_pc__hes[50], pcin_pc__hes[49], pcin_pc__hes[48], pcin_pc__hes[47], pcin_pc__hes[46], pcin_pc__hes[45], pcin_pc__hes[44], pcin_pc__hes[43], pcin_pc__hes[42], pcin_pc__hes[41], pcin_pc__hes[40], pcin_pc__hes[39], pcin_pc__hes[38], pcin_pc__hes[37], pcin_pc__hes[36], pcin_pc__hes[35], pcin_pc__hes[34], pcin_pc__hes[33], pcin_pc__hes[32], pcin_pc__hes[31], pcin_pc__hes[30], pcin_pc__hes[29], pcin_pc__hes[28], pcin_pc__hes[27], pcin_pc__hes[26], pcin_pc__hes[25], pcin_pc__hes[24], pcin_pc__hes[23], pcin_pc__hes[22], pcin_pc__hes[21], pcin_pc__hes[20], pcin_pc__hes[19], pcin_pc__hes[18], pcin_pc__hes[17], pcin_pc__hes[16], pcin_pc__hes[15], pcin_pc__hes[14], pcin_pc__hes[13], pcin_pc__hes[12], pcin_pc__hes[11], pcin_pc__hes[10], pcin_pc__hes[9], pcin_pc__hes[8], pcin_pc__hes[7], pcin_pc__hes[6], pcin_pc__hes[5], pcin_pc__hes[4], pcin_pc__hes[3], pcin_pc__hes[2], pcin_pc__hes[1], pcin_pc__hes[0]};
    end else begin
        assign pcin_native_pc__hes = pc__hes;
    end endgenerate
    wire [779:0] pcin_native_i_next;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_i_next
        (* keep = 1, face_keep = 1 *) reg [779:0] pcin_i_next;
        always @(posedge ck) pcin_i_next <= i_next[779:0];
        assign pcin_native_i_next = {pcin_i_next[779], pcin_i_next[778], pcin_i_next[777], pcin_i_next[776], pcin_i_next[775], pcin_i_next[774], pcin_i_next[773], pcin_i_next[772], pcin_i_next[771], pcin_i_next[770], pcin_i_next[769], pcin_i_next[768], pcin_i_next[767], pcin_i_next[766], pcin_i_next[765], pcin_i_next[764], pcin_i_next[763], pcin_i_next[762], pcin_i_next[761], pcin_i_next[760], pcin_i_next[759], pcin_i_next[758], pcin_i_next[757], pcin_i_next[756], pcin_i_next[755], pcin_i_next[754], pcin_i_next[753], pcin_i_next[752], pcin_i_next[751], pcin_i_next[750], pcin_i_next[749], pcin_i_next[748], pcin_i_next[747], pcin_i_next[746], pcin_i_next[745], pcin_i_next[744], pcin_i_next[743], pcin_i_next[742], pcin_i_next[741], pcin_i_next[740], pcin_i_next[739], pcin_i_next[738], pcin_i_next[737], pcin_i_next[736], pcin_i_next[735], pcin_i_next[734], pcin_i_next[733], pcin_i_next[732], pcin_i_next[731], pcin_i_next[730], pcin_i_next[729], pcin_i_next[728], pcin_i_next[727], pcin_i_next[726], pcin_i_next[725], pcin_i_next[724], pcin_i_next[723], pcin_i_next[722], pcin_i_next[721], pcin_i_next[720], pcin_i_next[719], pcin_i_next[718], pcin_i_next[717], pcin_i_next[716], pcin_i_next[715], pcin_i_next[714], pcin_i_next[713], pcin_i_next[712], pcin_i_next[711], pcin_i_next[710], pcin_i_next[709], pcin_i_next[708], pcin_i_next[707], pcin_i_next[706], pcin_i_next[705], pcin_i_next[704], pcin_i_next[703], pcin_i_next[702], pcin_i_next[701], pcin_i_next[700], pcin_i_next[699], pcin_i_next[698], pcin_i_next[697], pcin_i_next[696], pcin_i_next[695], pcin_i_next[694], pcin_i_next[693], pcin_i_next[692], pcin_i_next[691], pcin_i_next[690], pcin_i_next[689], pcin_i_next[688], pcin_i_next[687], pcin_i_next[686], pcin_i_next[685], pcin_i_next[684], pcin_i_next[683], pcin_i_next[682], pcin_i_next[681], pcin_i_next[680], pcin_i_next[679], pcin_i_next[678], pcin_i_next[677], pcin_i_next[676], pcin_i_next[675], pcin_i_next[674], pcin_i_next[673], pcin_i_next[672], pcin_i_next[671], pcin_i_next[670], pcin_i_next[669], pcin_i_next[668], pcin_i_next[667], pcin_i_next[666], pcin_i_next[665], pcin_i_next[664], pcin_i_next[663], pcin_i_next[662], pcin_i_next[661], pcin_i_next[660], pcin_i_next[659], pcin_i_next[658], pcin_i_next[657], pcin_i_next[656], pcin_i_next[655], pcin_i_next[654], pcin_i_next[653], pcin_i_next[652], pcin_i_next[651], pcin_i_next[650], pcin_i_next[649], pcin_i_next[648], pcin_i_next[647], pcin_i_next[646], pcin_i_next[645], pcin_i_next[644], pcin_i_next[643], pcin_i_next[642], pcin_i_next[641], pcin_i_next[640], pcin_i_next[639], pcin_i_next[638], pcin_i_next[637], pcin_i_next[636], pcin_i_next[635], pcin_i_next[634], pcin_i_next[633], pcin_i_next[632], pcin_i_next[631], pcin_i_next[630], pcin_i_next[629], pcin_i_next[628], pcin_i_next[627], pcin_i_next[626], pcin_i_next[625], pcin_i_next[624], pcin_i_next[623], pcin_i_next[622], pcin_i_next[621], pcin_i_next[620], pcin_i_next[619], pcin_i_next[618], pcin_i_next[617], pcin_i_next[616], pcin_i_next[615], pcin_i_next[614], pcin_i_next[613], pcin_i_next[612], pcin_i_next[611], pcin_i_next[610], pcin_i_next[609], pcin_i_next[608], pcin_i_next[607], pcin_i_next[606], pcin_i_next[605], pcin_i_next[604], pcin_i_next[603], pcin_i_next[602], pcin_i_next[601], pcin_i_next[600], pcin_i_next[599], pcin_i_next[598], pcin_i_next[597], pcin_i_next[596], pcin_i_next[595], pcin_i_next[594], pcin_i_next[593], pcin_i_next[592], pcin_i_next[591], pcin_i_next[590], pcin_i_next[589], pcin_i_next[588], pcin_i_next[587], pcin_i_next[586], pcin_i_next[585], pcin_i_next[584], pcin_i_next[583], pcin_i_next[582], pcin_i_next[581], pcin_i_next[580], pcin_i_next[579], pcin_i_next[578], pcin_i_next[577], pcin_i_next[576], pcin_i_next[575], pcin_i_next[574], pcin_i_next[573], pcin_i_next[572], pcin_i_next[571], pcin_i_next[570], pcin_i_next[569], pcin_i_next[568], pcin_i_next[567], pcin_i_next[566], pcin_i_next[565], pcin_i_next[564], pcin_i_next[563], pcin_i_next[562], pcin_i_next[561], pcin_i_next[560], pcin_i_next[559], pcin_i_next[558], pcin_i_next[557], pcin_i_next[556], pcin_i_next[555], pcin_i_next[554], pcin_i_next[553], pcin_i_next[552], pcin_i_next[551], pcin_i_next[550], pcin_i_next[549], pcin_i_next[548], pcin_i_next[547], pcin_i_next[546], pcin_i_next[545], pcin_i_next[544], pcin_i_next[543], pcin_i_next[542], pcin_i_next[541], pcin_i_next[540], pcin_i_next[539], pcin_i_next[538], pcin_i_next[537], pcin_i_next[536], pcin_i_next[535], pcin_i_next[534], pcin_i_next[533], pcin_i_next[532], pcin_i_next[531], pcin_i_next[530], pcin_i_next[529], pcin_i_next[528], pcin_i_next[527], pcin_i_next[526], pcin_i_next[525], pcin_i_next[524], pcin_i_next[523], pcin_i_next[522], pcin_i_next[521], pcin_i_next[520], pcin_i_next[519], pcin_i_next[518], pcin_i_next[517], pcin_i_next[516], pcin_i_next[515], pcin_i_next[514], pcin_i_next[513], pcin_i_next[512], pcin_i_next[511], pcin_i_next[510], pcin_i_next[509], pcin_i_next[508], pcin_i_next[507], pcin_i_next[506], pcin_i_next[505], pcin_i_next[504], pcin_i_next[503], pcin_i_next[502], pcin_i_next[501], pcin_i_next[500], pcin_i_next[499], pcin_i_next[498], pcin_i_next[497], pcin_i_next[496], pcin_i_next[495], pcin_i_next[494], pcin_i_next[493], pcin_i_next[492], pcin_i_next[491], pcin_i_next[490], pcin_i_next[489], pcin_i_next[488], pcin_i_next[487], pcin_i_next[486], pcin_i_next[485], pcin_i_next[484], pcin_i_next[483], pcin_i_next[482], pcin_i_next[481], pcin_i_next[480], pcin_i_next[479], pcin_i_next[478], pcin_i_next[477], pcin_i_next[476], pcin_i_next[475], pcin_i_next[474], pcin_i_next[473], pcin_i_next[472], pcin_i_next[471], pcin_i_next[470], pcin_i_next[469], pcin_i_next[468], pcin_i_next[467], pcin_i_next[466], pcin_i_next[465], pcin_i_next[464], pcin_i_next[463], pcin_i_next[462], pcin_i_next[461], pcin_i_next[460], pcin_i_next[459], pcin_i_next[458], pcin_i_next[457], pcin_i_next[456], pcin_i_next[455], pcin_i_next[454], pcin_i_next[453], pcin_i_next[452], pcin_i_next[451], pcin_i_next[450], pcin_i_next[449], pcin_i_next[448], pcin_i_next[447], pcin_i_next[446], pcin_i_next[445], pcin_i_next[444], pcin_i_next[443], pcin_i_next[442], pcin_i_next[441], pcin_i_next[440], pcin_i_next[439], pcin_i_next[438], pcin_i_next[437], pcin_i_next[436], pcin_i_next[435], pcin_i_next[434], pcin_i_next[433], pcin_i_next[432], pcin_i_next[431], pcin_i_next[430], pcin_i_next[429], pcin_i_next[428], pcin_i_next[427], pcin_i_next[426], pcin_i_next[425], pcin_i_next[424], pcin_i_next[423], pcin_i_next[422], pcin_i_next[421], pcin_i_next[420], pcin_i_next[419], pcin_i_next[418], pcin_i_next[417], pcin_i_next[416], pcin_i_next[415], pcin_i_next[414], pcin_i_next[413], pcin_i_next[412], pcin_i_next[411], pcin_i_next[410], pcin_i_next[409], pcin_i_next[408], pcin_i_next[407], pcin_i_next[406], pcin_i_next[405], pcin_i_next[404], pcin_i_next[403], pcin_i_next[402], pcin_i_next[401], pcin_i_next[400], pcin_i_next[399], pcin_i_next[398], pcin_i_next[397], pcin_i_next[396], pcin_i_next[395], pcin_i_next[394], pcin_i_next[393], pcin_i_next[392], pcin_i_next[391], pcin_i_next[390], pcin_i_next[389], pcin_i_next[388], pcin_i_next[387], pcin_i_next[386], pcin_i_next[385], pcin_i_next[384], pcin_i_next[383], pcin_i_next[382], pcin_i_next[381], pcin_i_next[380], pcin_i_next[379], pcin_i_next[378], pcin_i_next[377], pcin_i_next[376], pcin_i_next[375], pcin_i_next[374], pcin_i_next[373], pcin_i_next[372], pcin_i_next[371], pcin_i_next[370], pcin_i_next[369], pcin_i_next[368], pcin_i_next[367], pcin_i_next[366], pcin_i_next[365], pcin_i_next[364], pcin_i_next[363], pcin_i_next[362], pcin_i_next[361], pcin_i_next[360], pcin_i_next[359], pcin_i_next[358], pcin_i_next[357], pcin_i_next[356], pcin_i_next[355], pcin_i_next[354], pcin_i_next[353], pcin_i_next[352], pcin_i_next[351], pcin_i_next[350], pcin_i_next[349], pcin_i_next[348], pcin_i_next[347], pcin_i_next[346], pcin_i_next[345], pcin_i_next[344], pcin_i_next[343], pcin_i_next[342], pcin_i_next[341], pcin_i_next[340], pcin_i_next[339], pcin_i_next[338], pcin_i_next[337], pcin_i_next[336], pcin_i_next[335], pcin_i_next[334], pcin_i_next[333], pcin_i_next[332], pcin_i_next[331], pcin_i_next[330], pcin_i_next[329], pcin_i_next[328], pcin_i_next[327], pcin_i_next[326], pcin_i_next[325], pcin_i_next[324], pcin_i_next[323], pcin_i_next[322], pcin_i_next[321], pcin_i_next[320], pcin_i_next[319], pcin_i_next[318], pcin_i_next[317], pcin_i_next[316], pcin_i_next[315], pcin_i_next[314], pcin_i_next[313], pcin_i_next[312], pcin_i_next[311], pcin_i_next[310], pcin_i_next[309], pcin_i_next[308], pcin_i_next[307], pcin_i_next[306], pcin_i_next[305], pcin_i_next[304], pcin_i_next[303], pcin_i_next[302], pcin_i_next[301], pcin_i_next[300], pcin_i_next[299], pcin_i_next[298], pcin_i_next[297], pcin_i_next[296], pcin_i_next[295], pcin_i_next[294], pcin_i_next[293], pcin_i_next[292], pcin_i_next[291], pcin_i_next[290], pcin_i_next[289], pcin_i_next[288], pcin_i_next[287], pcin_i_next[286], pcin_i_next[285], pcin_i_next[284], pcin_i_next[283], pcin_i_next[282], pcin_i_next[281], pcin_i_next[280], pcin_i_next[279], pcin_i_next[278], pcin_i_next[277], pcin_i_next[276], pcin_i_next[275], pcin_i_next[274], pcin_i_next[273], pcin_i_next[272], pcin_i_next[271], pcin_i_next[270], pcin_i_next[269], pcin_i_next[268], pcin_i_next[267], pcin_i_next[266], pcin_i_next[265], pcin_i_next[264], pcin_i_next[263], pcin_i_next[262], pcin_i_next[261], pcin_i_next[260], pcin_i_next[259], pcin_i_next[258], pcin_i_next[257], pcin_i_next[256], pcin_i_next[255], pcin_i_next[254], pcin_i_next[253], pcin_i_next[252], pcin_i_next[251], pcin_i_next[250], pcin_i_next[249], pcin_i_next[248], pcin_i_next[247], pcin_i_next[246], pcin_i_next[245], pcin_i_next[244], pcin_i_next[243], pcin_i_next[242], pcin_i_next[241], pcin_i_next[240], pcin_i_next[239], pcin_i_next[238], pcin_i_next[237], pcin_i_next[236], pcin_i_next[235], pcin_i_next[234], pcin_i_next[233], pcin_i_next[232], pcin_i_next[231], pcin_i_next[230], pcin_i_next[229], pcin_i_next[228], pcin_i_next[227], pcin_i_next[226], pcin_i_next[225], pcin_i_next[224], pcin_i_next[223], pcin_i_next[222], pcin_i_next[221], pcin_i_next[220], pcin_i_next[219], pcin_i_next[218], pcin_i_next[217], pcin_i_next[216], pcin_i_next[215], pcin_i_next[214], pcin_i_next[213], pcin_i_next[212], pcin_i_next[211], pcin_i_next[210], pcin_i_next[209], pcin_i_next[208], pcin_i_next[207], pcin_i_next[206], pcin_i_next[205], pcin_i_next[204], pcin_i_next[203], pcin_i_next[202], pcin_i_next[201], pcin_i_next[200], pcin_i_next[199], pcin_i_next[198], pcin_i_next[197], pcin_i_next[196], pcin_i_next[195], pcin_i_next[194], pcin_i_next[193], pcin_i_next[192], pcin_i_next[191], pcin_i_next[190], pcin_i_next[189], pcin_i_next[188], pcin_i_next[187], pcin_i_next[186], pcin_i_next[185], pcin_i_next[184], pcin_i_next[183], pcin_i_next[182], pcin_i_next[181], pcin_i_next[180], pcin_i_next[179], pcin_i_next[178], pcin_i_next[177], pcin_i_next[176], pcin_i_next[175], pcin_i_next[174], pcin_i_next[173], pcin_i_next[172], pcin_i_next[171], pcin_i_next[170], pcin_i_next[169], pcin_i_next[168], pcin_i_next[167], pcin_i_next[166], pcin_i_next[165], pcin_i_next[164], pcin_i_next[163], pcin_i_next[162], pcin_i_next[161], pcin_i_next[160], pcin_i_next[159], pcin_i_next[158], pcin_i_next[157], pcin_i_next[156], pcin_i_next[155], pcin_i_next[154], pcin_i_next[153], pcin_i_next[152], pcin_i_next[151], pcin_i_next[150], pcin_i_next[149], pcin_i_next[148], pcin_i_next[147], pcin_i_next[146], pcin_i_next[145], pcin_i_next[144], pcin_i_next[143], pcin_i_next[142], pcin_i_next[141], pcin_i_next[140], pcin_i_next[139], pcin_i_next[138], pcin_i_next[137], pcin_i_next[136], pcin_i_next[135], pcin_i_next[134], pcin_i_next[133], pcin_i_next[132], pcin_i_next[131], pcin_i_next[130], pcin_i_next[129], pcin_i_next[128], pcin_i_next[127], pcin_i_next[126], pcin_i_next[125], pcin_i_next[124], pcin_i_next[123], pcin_i_next[122], pcin_i_next[121], pcin_i_next[120], pcin_i_next[119], pcin_i_next[118], pcin_i_next[117], pcin_i_next[116], pcin_i_next[115], pcin_i_next[114], pcin_i_next[113], pcin_i_next[112], pcin_i_next[111], pcin_i_next[110], pcin_i_next[109], pcin_i_next[108], pcin_i_next[107], pcin_i_next[106], pcin_i_next[105], pcin_i_next[104], pcin_i_next[103], pcin_i_next[102], pcin_i_next[101], pcin_i_next[100], pcin_i_next[99], pcin_i_next[98], pcin_i_next[97], pcin_i_next[96], pcin_i_next[95], pcin_i_next[94], pcin_i_next[93], pcin_i_next[92], pcin_i_next[91], pcin_i_next[90], pcin_i_next[89], pcin_i_next[88], pcin_i_next[87], pcin_i_next[86], pcin_i_next[85], pcin_i_next[84], pcin_i_next[83], pcin_i_next[82], pcin_i_next[81], pcin_i_next[80], pcin_i_next[79], pcin_i_next[78], pcin_i_next[77], pcin_i_next[76], pcin_i_next[75], pcin_i_next[74], pcin_i_next[73], pcin_i_next[72], pcin_i_next[71], pcin_i_next[70], pcin_i_next[69], pcin_i_next[68], pcin_i_next[67], pcin_i_next[66], pcin_i_next[65], pcin_i_next[64], pcin_i_next[63], pcin_i_next[62], pcin_i_next[61], pcin_i_next[60], pcin_i_next[59], pcin_i_next[58], pcin_i_next[57], pcin_i_next[56], pcin_i_next[55], pcin_i_next[54], pcin_i_next[53], pcin_i_next[52], pcin_i_next[51], pcin_i_next[50], pcin_i_next[49], pcin_i_next[48], pcin_i_next[47], pcin_i_next[46], pcin_i_next[45], pcin_i_next[44], pcin_i_next[43], pcin_i_next[42], pcin_i_next[41], pcin_i_next[40], pcin_i_next[39], pcin_i_next[38], pcin_i_next[37], pcin_i_next[36], pcin_i_next[35], pcin_i_next[34], pcin_i_next[33], pcin_i_next[32], pcin_i_next[31], pcin_i_next[30], pcin_i_next[29], pcin_i_next[28], pcin_i_next[27], pcin_i_next[26], pcin_i_next[25], pcin_i_next[24], pcin_i_next[23], pcin_i_next[22], pcin_i_next[21], pcin_i_next[20], pcin_i_next[19], pcin_i_next[18], pcin_i_next[17], pcin_i_next[16], pcin_i_next[15], pcin_i_next[14], pcin_i_next[13], pcin_i_next[12], pcin_i_next[11], pcin_i_next[10], pcin_i_next[9], pcin_i_next[8], pcin_i_next[7], pcin_i_next[6], pcin_i_next[5], pcin_i_next[4], pcin_i_next[3], pcin_i_next[2], pcin_i_next[1], pcin_i_next[0]};
    end else begin
        assign pcin_native_i_next = i_next;
    end endgenerate
    wire [260:0] pcin_native_pc__land_er;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__land_er
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_pc__land_er;
        always @(posedge ck) pcin_pc__land_er <= pc__land_er[0:0];
        (* keep = 1, face_keep = 1 *) reg [260:259] pcin_pc__land_er_259;
        always @(posedge ck) pcin_pc__land_er_259 <= pc__land_er[260:259];
        assign pcin_native_pc__land_er = {pcin_pc__land_er_259[260], pcin_pc__land_er_259[259], pc__land_er[258], pc__land_er[257], pc__land_er[256], pc__land_er[255], pc__land_er[254], pc__land_er[253], pc__land_er[252], pc__land_er[251], pc__land_er[250], pc__land_er[249], pc__land_er[248], pc__land_er[247], pc__land_er[246], pc__land_er[245], pc__land_er[244], pc__land_er[243], pc__land_er[242], pc__land_er[241], pc__land_er[240], pc__land_er[239], pc__land_er[238], pc__land_er[237], pc__land_er[236], pc__land_er[235], pc__land_er[234], pc__land_er[233], pc__land_er[232], pc__land_er[231], pc__land_er[230], pc__land_er[229], pc__land_er[228], pc__land_er[227], pc__land_er[226], pc__land_er[225], pc__land_er[224], pc__land_er[223], pc__land_er[222], pc__land_er[221], pc__land_er[220], pc__land_er[219], pc__land_er[218], pc__land_er[217], pc__land_er[216], pc__land_er[215], pc__land_er[214], pc__land_er[213], pc__land_er[212], pc__land_er[211], pc__land_er[210], pc__land_er[209], pc__land_er[208], pc__land_er[207], pc__land_er[206], pc__land_er[205], pc__land_er[204], pc__land_er[203], pc__land_er[202], pc__land_er[201], pc__land_er[200], pc__land_er[199], pc__land_er[198], pc__land_er[197], pc__land_er[196], pc__land_er[195], pc__land_er[194], pc__land_er[193], pc__land_er[192], pc__land_er[191], pc__land_er[190], pc__land_er[189], pc__land_er[188], pc__land_er[187], pc__land_er[186], pc__land_er[185], pc__land_er[184], pc__land_er[183], pc__land_er[182], pc__land_er[181], pc__land_er[180], pc__land_er[179], pc__land_er[178], pc__land_er[177], pc__land_er[176], pc__land_er[175], pc__land_er[174], pc__land_er[173], pc__land_er[172], pc__land_er[171], pc__land_er[170], pc__land_er[169], pc__land_er[168], pc__land_er[167], pc__land_er[166], pc__land_er[165], pc__land_er[164], pc__land_er[163], pc__land_er[162], pc__land_er[161], pc__land_er[160], pc__land_er[159], pc__land_er[158], pc__land_er[157], pc__land_er[156], pc__land_er[155], pc__land_er[154], pc__land_er[153], pc__land_er[152], pc__land_er[151], pc__land_er[150], pc__land_er[149], pc__land_er[148], pc__land_er[147], pc__land_er[146], pc__land_er[145], pc__land_er[144], pc__land_er[143], pc__land_er[142], pc__land_er[141], pc__land_er[140], pc__land_er[139], pc__land_er[138], pc__land_er[137], pc__land_er[136], pc__land_er[135], pc__land_er[134], pc__land_er[133], pc__land_er[132], pc__land_er[131], pc__land_er[130], pc__land_er[129], pc__land_er[128], pc__land_er[127], pc__land_er[126], pc__land_er[125], pc__land_er[124], pc__land_er[123], pc__land_er[122], pc__land_er[121], pc__land_er[120], pc__land_er[119], pc__land_er[118], pc__land_er[117], pc__land_er[116], pc__land_er[115], pc__land_er[114], pc__land_er[113], pc__land_er[112], pc__land_er[111], pc__land_er[110], pc__land_er[109], pc__land_er[108], pc__land_er[107], pc__land_er[106], pc__land_er[105], pc__land_er[104], pc__land_er[103], pc__land_er[102], pc__land_er[101], pc__land_er[100], pc__land_er[99], pc__land_er[98], pc__land_er[97], pc__land_er[96], pc__land_er[95], pc__land_er[94], pc__land_er[93], pc__land_er[92], pc__land_er[91], pc__land_er[90], pc__land_er[89], pc__land_er[88], pc__land_er[87], pc__land_er[86], pc__land_er[85], pc__land_er[84], pc__land_er[83], pc__land_er[82], pc__land_er[81], pc__land_er[80], pc__land_er[79], pc__land_er[78], pc__land_er[77], pc__land_er[76], pc__land_er[75], pc__land_er[74], pc__land_er[73], pc__land_er[72], pc__land_er[71], pc__land_er[70], pc__land_er[69], pc__land_er[68], pc__land_er[67], pc__land_er[66], pc__land_er[65], pc__land_er[64], pc__land_er[63], pc__land_er[62], pc__land_er[61], pc__land_er[60], pc__land_er[59], pc__land_er[58], pc__land_er[57], pc__land_er[56], pc__land_er[55], pc__land_er[54], pc__land_er[53], pc__land_er[52], pc__land_er[51], pc__land_er[50], pc__land_er[49], pc__land_er[48], pc__land_er[47], pc__land_er[46], pc__land_er[45], pc__land_er[44], pc__land_er[43], pc__land_er[42], pc__land_er[41], pc__land_er[40], pc__land_er[39], pc__land_er[38], pc__land_er[37], pc__land_er[36], pc__land_er[35], pc__land_er[34], pc__land_er[33], pc__land_er[32], pc__land_er[31], pc__land_er[30], pc__land_er[29], pc__land_er[28], pc__land_er[27], pc__land_er[26], pc__land_er[25], pc__land_er[24], pc__land_er[23], pc__land_er[22], pc__land_er[21], pc__land_er[20], pc__land_er[19], pc__land_er[18], pc__land_er[17], pc__land_er[16], pc__land_er[15], pc__land_er[14], pc__land_er[13], pc__land_er[12], pc__land_er[11], pc__land_er[10], pc__land_er[9], pc__land_er[8], pc__land_er[7], pc__land_er[6], pc__land_er[5], pc__land_er[4], pc__land_er[3], pc__land_er[2], pc__land_er[1], pcin_pc__land_er[0]};
    end else begin
        assign pcin_native_pc__land_er = pc__land_er;
    end endgenerate
    wire  pcin_native_rst_n;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_rst_n
        (* keep = 1, face_keep = 1 *) reg  pcin_rst_n;
        always @(posedge ck) pcin_rst_n <= rst_n;
        assign pcin_native_rst_n = pcin_rst_n;
    end else begin
        assign pcin_native_rst_n = rst_n;
    end endgenerate
    wire [32:0] pcin_native_pc__ki;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__ki
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_pc__ki;
        always @(posedge ck) pcin_pc__ki <= pc__ki[0:0];
        (* keep = 1, face_keep = 1 *) reg [20:15] pcin_pc__ki_15;
        always @(posedge ck) pcin_pc__ki_15 <= pc__ki[20:15];
        (* keep = 1, face_keep = 1 *) reg [32:31] pcin_pc__ki_31;
        always @(posedge ck) pcin_pc__ki_31 <= pc__ki[32:31];
        assign pcin_native_pc__ki = {pcin_pc__ki_31[32], pcin_pc__ki_31[31], pc__ki[30], pc__ki[29], pc__ki[28], pc__ki[27], pc__ki[26], pc__ki[25], pc__ki[24], pc__ki[23], pc__ki[22], pc__ki[21], pcin_pc__ki_15[20], pcin_pc__ki_15[19], pcin_pc__ki_15[18], pcin_pc__ki_15[17], pcin_pc__ki_15[16], pcin_pc__ki_15[15], pc__ki[14], pc__ki[13], pc__ki[12], pc__ki[11], pc__ki[10], pc__ki[9], pc__ki[8], pc__ki[7], pc__ki[6], pc__ki[5], pc__ki[4], pc__ki[3], pc__ki[2], pc__ki[1], pcin_pc__ki[0]};
    end else begin
        assign pcin_native_pc__ki = pc__ki;
    end endgenerate

    qkd_kv_pc_chain_station_b_p u_actual_chain (
        .ck(ck),
        .rst_n(pcin_native_rst_n),
        .cfg_stack(pcin_native_pc__cfg_stack),
        .di(pcin_native_i_next),
        .dout(coupon_dout),
        .land_es(coupon_land_es),
        .land_er(pcin_native_pc__land_er),
        .wes(coupon_wes),
        .es_context(coupon_es_context),
        .es_expected_valid(coupon_es_expected_valid),
        .es_expected_identity(coupon_es_expected_identity),
        .es_expected_address(coupon_es_expected_address),
        .es_expected_pc(coupon_es_expected_pc),
        .es_expected_stack(coupon_es_expected_stack),
        .emb_issue_v(coupon_emb_issue_v),
        .emb_token(coupon_emb_token),
        .emb_word_index(coupon_emb_word_index),
        .emb_half(coupon_emb_half),
        .emb_scale(coupon_emb_scale),
        .emb_epoch(coupon_emb_epoch),
        .emb_return_slot(coupon_emb_return_slot),
        .capture_slot(coupon_capture_slot),
        .transfer_slot(coupon_transfer_slot),
        .fault(coupon_fault)
    );
endmodule
module qkd_kvs_pc_h_head_p_badbit #(
    parameter KVSPC_INPUT_COLLAR = 0,
    parameter [4:0] PC = 0
) (
    input wire ck,
    input wire rst_n,
    input wire hck,
    input wire hrst_n,
    input wire [288:0] pc__pi,
    input wire [32:0] pc__ki,
    input wire [1:0] pc__cfg_stack,
    input wire [3:0] pc__front_hbm_data,
    input wire [3:0] pc__return_hbm_data,
    input wire [0:0] x__est__0_1,
    input wire [260:0] pc__land_er,
    input wire [287:0] pc__hes,
    output wire [0:0] pc__fo,
    output wire [260:0] pc__er,
    output wire [32:0] pc__ko,
    output wire [327:0] pc__po,
    output wire [0:0] pc__completion_v,
    output wire [0:0] pc__completion_we,
    output wire [287:0] pc__land_es,
    output wire [260:0] pc__her,
    output wire [0:0] pc__hcompletion_v,
    output wire [0:0] pc__hcompletion_we,
    input wire [127:0] i_grp,
    input wire [779:0] i_next,
    output wire [304:0] o_grp,
    output wire [298:0] o_next
,
    output wire [779:0] coupon_dout,
    output wire [287:0] coupon_land_es,
    output wire [287:0] coupon_wes,
    output wire [317:0] coupon_es_context,
    output wire  coupon_es_expected_valid,
    output wire [60:0] coupon_es_expected_identity,
    output wire [28:0] coupon_es_expected_address,
    output wire [4:0] coupon_es_expected_pc,
    output wire [1:0] coupon_es_expected_stack,
    output wire  coupon_emb_issue_v,
    output wire [17:0] coupon_emb_token,
    output wire [5:0] coupon_emb_word_index,
    output wire  coupon_emb_half,
    output wire  coupon_emb_scale,
    output wire [15:0] coupon_emb_epoch,
    output wire  coupon_emb_return_slot,
    output wire  coupon_capture_slot,
    output wire  coupon_transfer_slot,
    output wire  coupon_fault
);
    // KVSPC_NATIVE_INPUT_COLLAR: parent and physical sources must select exactly once.
    wire  pcin_native_hrst_n;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_hrst_n
        (* keep = 1, face_keep = 1 *) reg  pcin_hrst_n;
        always @(posedge ck) pcin_hrst_n <= hrst_n;
        assign pcin_native_hrst_n = pcin_hrst_n;
    end else begin
        assign pcin_native_hrst_n = hrst_n;
    end endgenerate
    wire [127:0] pcin_native_i_grp;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_i_grp
        (* keep = 1, face_keep = 1 *) reg [127:0] pcin_i_grp;
        always @(posedge ck) pcin_i_grp <= i_grp[127:0];
        assign pcin_native_i_grp = {pcin_i_grp[127], pcin_i_grp[126], pcin_i_grp[125], pcin_i_grp[124], pcin_i_grp[123], pcin_i_grp[122], pcin_i_grp[121], pcin_i_grp[120], pcin_i_grp[119], pcin_i_grp[118], pcin_i_grp[117], pcin_i_grp[116], pcin_i_grp[115], pcin_i_grp[114], pcin_i_grp[113], pcin_i_grp[112], pcin_i_grp[111], pcin_i_grp[110], pcin_i_grp[109], pcin_i_grp[108], pcin_i_grp[107], pcin_i_grp[106], pcin_i_grp[105], pcin_i_grp[104], pcin_i_grp[103], pcin_i_grp[102], pcin_i_grp[101], pcin_i_grp[100], pcin_i_grp[99], pcin_i_grp[98], pcin_i_grp[97], pcin_i_grp[96], pcin_i_grp[95], pcin_i_grp[94], pcin_i_grp[93], pcin_i_grp[92], pcin_i_grp[91], pcin_i_grp[90], pcin_i_grp[89], pcin_i_grp[88], pcin_i_grp[87], pcin_i_grp[86], pcin_i_grp[85], pcin_i_grp[84], pcin_i_grp[83], pcin_i_grp[82], pcin_i_grp[81], pcin_i_grp[80], pcin_i_grp[79], pcin_i_grp[78], pcin_i_grp[77], pcin_i_grp[76], pcin_i_grp[75], pcin_i_grp[74], pcin_i_grp[73], pcin_i_grp[72], pcin_i_grp[71], pcin_i_grp[70], pcin_i_grp[69], pcin_i_grp[68], pcin_i_grp[67], pcin_i_grp[66], pcin_i_grp[65], pcin_i_grp[64], pcin_i_grp[63], pcin_i_grp[62], pcin_i_grp[61], pcin_i_grp[60], pcin_i_grp[59], pcin_i_grp[58], pcin_i_grp[57], pcin_i_grp[56], pcin_i_grp[55], pcin_i_grp[54], pcin_i_grp[53], pcin_i_grp[52], pcin_i_grp[51], pcin_i_grp[50], pcin_i_grp[49], pcin_i_grp[48], pcin_i_grp[47], pcin_i_grp[46], pcin_i_grp[45], pcin_i_grp[44], pcin_i_grp[43], pcin_i_grp[42], pcin_i_grp[41], pcin_i_grp[40], pcin_i_grp[39], pcin_i_grp[38], pcin_i_grp[37], pcin_i_grp[36], pcin_i_grp[35], pcin_i_grp[34], pcin_i_grp[33], pcin_i_grp[32], pcin_i_grp[31], pcin_i_grp[30], pcin_i_grp[29], pcin_i_grp[28], pcin_i_grp[27], pcin_i_grp[26], pcin_i_grp[25], pcin_i_grp[24], pcin_i_grp[23], pcin_i_grp[22], pcin_i_grp[21], pcin_i_grp[20], pcin_i_grp[19], pcin_i_grp[18], pcin_i_grp[17], pcin_i_grp[16], pcin_i_grp[15], pcin_i_grp[14], pcin_i_grp[13], pcin_i_grp[12], pcin_i_grp[11], pcin_i_grp[10], pcin_i_grp[9], pcin_i_grp[8], pcin_i_grp[7], pcin_i_grp[6], pcin_i_grp[5], pcin_i_grp[4], pcin_i_grp[3], pcin_i_grp[2], pcin_i_grp[1], pcin_i_grp[0]};
    end else begin
        assign pcin_native_i_grp = i_grp;
    end endgenerate
    wire [1:0] pcin_native_pc__cfg_stack;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__cfg_stack
        (* keep = 1, face_keep = 1 *) reg [1:0] pcin_pc__cfg_stack;
        always @(posedge ck) pcin_pc__cfg_stack <= pc__cfg_stack[1:0];
        assign pcin_native_pc__cfg_stack = {pcin_pc__cfg_stack[1], pcin_pc__cfg_stack[0]};
    end else begin
        assign pcin_native_pc__cfg_stack = pc__cfg_stack;
    end endgenerate
    wire [288:0] pcin_native_pc__pi;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__pi
        (* keep = 1, face_keep = 1 *) reg [288:0] pcin_pc__pi;
        always @(posedge ck) pcin_pc__pi <= pc__pi[288:0];
        assign pcin_native_pc__pi = {pcin_pc__pi[288], pcin_pc__pi[287], pcin_pc__pi[286], pcin_pc__pi[285], pcin_pc__pi[284], pcin_pc__pi[283], pcin_pc__pi[282], pcin_pc__pi[281], pcin_pc__pi[280], pcin_pc__pi[279], pcin_pc__pi[278], pcin_pc__pi[277], pcin_pc__pi[276], pcin_pc__pi[275], pcin_pc__pi[274], pcin_pc__pi[273], pcin_pc__pi[272], pcin_pc__pi[271], pcin_pc__pi[270], pcin_pc__pi[269], pcin_pc__pi[268], pcin_pc__pi[267], pcin_pc__pi[266], pcin_pc__pi[265], pcin_pc__pi[264], pcin_pc__pi[263], pcin_pc__pi[262], pcin_pc__pi[261], pcin_pc__pi[260], pcin_pc__pi[259], pcin_pc__pi[258], pcin_pc__pi[257], pcin_pc__pi[256], pcin_pc__pi[255], pcin_pc__pi[254], pcin_pc__pi[253], pcin_pc__pi[252], pcin_pc__pi[251], pcin_pc__pi[250], pcin_pc__pi[249], pcin_pc__pi[248], pcin_pc__pi[247], pcin_pc__pi[246], pcin_pc__pi[245], pcin_pc__pi[244], pcin_pc__pi[243], pcin_pc__pi[242], pcin_pc__pi[241], pcin_pc__pi[240], pcin_pc__pi[239], pcin_pc__pi[238], pcin_pc__pi[237], pcin_pc__pi[236], pcin_pc__pi[235], pcin_pc__pi[234], pcin_pc__pi[233], pcin_pc__pi[232], pcin_pc__pi[231], pcin_pc__pi[230], pcin_pc__pi[229], pcin_pc__pi[228], pcin_pc__pi[227], pcin_pc__pi[226], pcin_pc__pi[225], pcin_pc__pi[224], pcin_pc__pi[223], pcin_pc__pi[222], pcin_pc__pi[221], pcin_pc__pi[220], pcin_pc__pi[219], pcin_pc__pi[218], pcin_pc__pi[217], pcin_pc__pi[216], pcin_pc__pi[215], pcin_pc__pi[214], pcin_pc__pi[213], pcin_pc__pi[212], pcin_pc__pi[211], pcin_pc__pi[210], pcin_pc__pi[209], pcin_pc__pi[208], pcin_pc__pi[207], pcin_pc__pi[206], pcin_pc__pi[205], pcin_pc__pi[204], pcin_pc__pi[203], pcin_pc__pi[202], pcin_pc__pi[201], pcin_pc__pi[200], pcin_pc__pi[199], pcin_pc__pi[198], pcin_pc__pi[197], pcin_pc__pi[196], pcin_pc__pi[195], pcin_pc__pi[194], pcin_pc__pi[193], pcin_pc__pi[192], pcin_pc__pi[191], pcin_pc__pi[190], pcin_pc__pi[189], pcin_pc__pi[188], pcin_pc__pi[187], pcin_pc__pi[186], pcin_pc__pi[185], pcin_pc__pi[184], pcin_pc__pi[183], pcin_pc__pi[182], pcin_pc__pi[181], pcin_pc__pi[180], pcin_pc__pi[179], pcin_pc__pi[178], pcin_pc__pi[177], pcin_pc__pi[176], pcin_pc__pi[175], pcin_pc__pi[174], pcin_pc__pi[173], pcin_pc__pi[172], pcin_pc__pi[171], pcin_pc__pi[170], pcin_pc__pi[169], pcin_pc__pi[168], pcin_pc__pi[167], pcin_pc__pi[166], pcin_pc__pi[165], pcin_pc__pi[164], pcin_pc__pi[163], pcin_pc__pi[162], pcin_pc__pi[161], pcin_pc__pi[160], pcin_pc__pi[159], pcin_pc__pi[158], pcin_pc__pi[157], pcin_pc__pi[156], pcin_pc__pi[155], pcin_pc__pi[154], pcin_pc__pi[153], pcin_pc__pi[152], pcin_pc__pi[151], pcin_pc__pi[150], pcin_pc__pi[149], pcin_pc__pi[148], pcin_pc__pi[147], pcin_pc__pi[146], pcin_pc__pi[145], pcin_pc__pi[144], pcin_pc__pi[143], pcin_pc__pi[142], pcin_pc__pi[141], pcin_pc__pi[140], pcin_pc__pi[139], pcin_pc__pi[138], pcin_pc__pi[137], pcin_pc__pi[136], pcin_pc__pi[135], pcin_pc__pi[134], pcin_pc__pi[133], pcin_pc__pi[132], pcin_pc__pi[131], pcin_pc__pi[130], pcin_pc__pi[129], pcin_pc__pi[128], pcin_pc__pi[127], pcin_pc__pi[126], pcin_pc__pi[125], pcin_pc__pi[124], pcin_pc__pi[123], pcin_pc__pi[122], pcin_pc__pi[121], pcin_pc__pi[120], pcin_pc__pi[119], pcin_pc__pi[118], pcin_pc__pi[117], pcin_pc__pi[116], pcin_pc__pi[115], pcin_pc__pi[114], pcin_pc__pi[113], pcin_pc__pi[112], pcin_pc__pi[111], pcin_pc__pi[110], pcin_pc__pi[109], pcin_pc__pi[108], pcin_pc__pi[107], pcin_pc__pi[106], pcin_pc__pi[105], pcin_pc__pi[104], pcin_pc__pi[103], pcin_pc__pi[102], pcin_pc__pi[101], pcin_pc__pi[100], pcin_pc__pi[99], pcin_pc__pi[98], pcin_pc__pi[97], pcin_pc__pi[96], pcin_pc__pi[95], pcin_pc__pi[94], pcin_pc__pi[93], pcin_pc__pi[92], pcin_pc__pi[91], pcin_pc__pi[90], pcin_pc__pi[89], pcin_pc__pi[88], pcin_pc__pi[87], pcin_pc__pi[86], pcin_pc__pi[85], pcin_pc__pi[84], pcin_pc__pi[83], pcin_pc__pi[82], pcin_pc__pi[81], pcin_pc__pi[80], pcin_pc__pi[79], pcin_pc__pi[78], pcin_pc__pi[77], pcin_pc__pi[76], pcin_pc__pi[75], pcin_pc__pi[74], pcin_pc__pi[73], pcin_pc__pi[72], pcin_pc__pi[71], pcin_pc__pi[70], pcin_pc__pi[69], pcin_pc__pi[68], pcin_pc__pi[67], pcin_pc__pi[66], pcin_pc__pi[65], pcin_pc__pi[64], pcin_pc__pi[63], pcin_pc__pi[62], pcin_pc__pi[61], pcin_pc__pi[60], pcin_pc__pi[59], pcin_pc__pi[58], pcin_pc__pi[57], pcin_pc__pi[56], pcin_pc__pi[55], pcin_pc__pi[54], pcin_pc__pi[53], pcin_pc__pi[52], pcin_pc__pi[51], pcin_pc__pi[50], pcin_pc__pi[49], pcin_pc__pi[48], pcin_pc__pi[47], pcin_pc__pi[46], pcin_pc__pi[45], pcin_pc__pi[44], pcin_pc__pi[43], pcin_pc__pi[42], pcin_pc__pi[41], pcin_pc__pi[40], pcin_pc__pi[39], pcin_pc__pi[38], pcin_pc__pi[37], pcin_pc__pi[36], pcin_pc__pi[35], pcin_pc__pi[34], pcin_pc__pi[33], pcin_pc__pi[32], pcin_pc__pi[31], pcin_pc__pi[30], pcin_pc__pi[29], pcin_pc__pi[28], pcin_pc__pi[27], pcin_pc__pi[26], pcin_pc__pi[25], pcin_pc__pi[24], pcin_pc__pi[23], pcin_pc__pi[22], pcin_pc__pi[21], pcin_pc__pi[20], pcin_pc__pi[19], pcin_pc__pi[18], pcin_pc__pi[17], pcin_pc__pi[16], pcin_pc__pi[15], pcin_pc__pi[14], pcin_pc__pi[13], pcin_pc__pi[12], pcin_pc__pi[11], pcin_pc__pi[10], pcin_pc__pi[9], pcin_pc__pi[8], pcin_pc__pi[7], pcin_pc__pi[6], pcin_pc__pi[5], pcin_pc__pi[4], pcin_pc__pi[3], pcin_pc__pi[2], pcin_pc__pi[1], pcin_pc__pi[0]};
    end else begin
        assign pcin_native_pc__pi = pc__pi;
    end endgenerate
    wire [0:0] pcin_native_x__est__0_1;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_x__est__0_1
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_x__est__0_1;
        always @(posedge ck) pcin_x__est__0_1 <= x__est__0_1[0:0];
        assign pcin_native_x__est__0_1 = {pcin_x__est__0_1[0]};
    end else begin
        assign pcin_native_x__est__0_1 = x__est__0_1;
    end endgenerate
    wire [287:0] pcin_native_pc__hes;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__hes
        (* keep = 1, face_keep = 1 *) reg [287:0] pcin_pc__hes;
        always @(posedge ck) pcin_pc__hes <= pc__hes[287:0];
        assign pcin_native_pc__hes = {pcin_pc__hes[287], pcin_pc__hes[286], pcin_pc__hes[285], pcin_pc__hes[284], pcin_pc__hes[283], pcin_pc__hes[282], pcin_pc__hes[281], pcin_pc__hes[280], pcin_pc__hes[279], pcin_pc__hes[278], pcin_pc__hes[277], pcin_pc__hes[276], pcin_pc__hes[275], pcin_pc__hes[274], pcin_pc__hes[273], pcin_pc__hes[272], pcin_pc__hes[271], pcin_pc__hes[270], pcin_pc__hes[269], pcin_pc__hes[268], pcin_pc__hes[267], pcin_pc__hes[266], pcin_pc__hes[265], pcin_pc__hes[264], pcin_pc__hes[263], pcin_pc__hes[262], pcin_pc__hes[261], pcin_pc__hes[260], pcin_pc__hes[259], pcin_pc__hes[258], pcin_pc__hes[257], pcin_pc__hes[256], pcin_pc__hes[255], pcin_pc__hes[254], pcin_pc__hes[253], pcin_pc__hes[252], pcin_pc__hes[251], pcin_pc__hes[250], pcin_pc__hes[249], pcin_pc__hes[248], pcin_pc__hes[247], pcin_pc__hes[246], pcin_pc__hes[245], pcin_pc__hes[244], pcin_pc__hes[243], pcin_pc__hes[242], pcin_pc__hes[241], pcin_pc__hes[240], pcin_pc__hes[239], pcin_pc__hes[238], pcin_pc__hes[237], pcin_pc__hes[236], pcin_pc__hes[235], pcin_pc__hes[234], pcin_pc__hes[233], pcin_pc__hes[232], pcin_pc__hes[231], pcin_pc__hes[230], pcin_pc__hes[229], pcin_pc__hes[228], pcin_pc__hes[227], pcin_pc__hes[226], pcin_pc__hes[225], pcin_pc__hes[224], pcin_pc__hes[223], pcin_pc__hes[222], pcin_pc__hes[221], pcin_pc__hes[220], pcin_pc__hes[219], pcin_pc__hes[218], pcin_pc__hes[217], pcin_pc__hes[216], pcin_pc__hes[215], pcin_pc__hes[214], pcin_pc__hes[213], pcin_pc__hes[212], pcin_pc__hes[211], pcin_pc__hes[210], pcin_pc__hes[209], pcin_pc__hes[208], pcin_pc__hes[207], pcin_pc__hes[206], pcin_pc__hes[205], pcin_pc__hes[204], pcin_pc__hes[203], pcin_pc__hes[202], pcin_pc__hes[201], pcin_pc__hes[200], pcin_pc__hes[199], pcin_pc__hes[198], pcin_pc__hes[197], pcin_pc__hes[196], pcin_pc__hes[195], pcin_pc__hes[194], pcin_pc__hes[193], pcin_pc__hes[192], pcin_pc__hes[191], pcin_pc__hes[190], pcin_pc__hes[189], pcin_pc__hes[188], pcin_pc__hes[187], pcin_pc__hes[186], pcin_pc__hes[185], pcin_pc__hes[184], pcin_pc__hes[183], pcin_pc__hes[182], pcin_pc__hes[181], pcin_pc__hes[180], pcin_pc__hes[179], pcin_pc__hes[178], pcin_pc__hes[177], pcin_pc__hes[176], pcin_pc__hes[175], pcin_pc__hes[174], pcin_pc__hes[173], pcin_pc__hes[172], pcin_pc__hes[171], pcin_pc__hes[170], pcin_pc__hes[169], pcin_pc__hes[168], pcin_pc__hes[167], pcin_pc__hes[166], pcin_pc__hes[165], pcin_pc__hes[164], pcin_pc__hes[163], pcin_pc__hes[162], pcin_pc__hes[161], pcin_pc__hes[160], pcin_pc__hes[159], pcin_pc__hes[158], pcin_pc__hes[157], pcin_pc__hes[156], pcin_pc__hes[155], pcin_pc__hes[154], pcin_pc__hes[153], pcin_pc__hes[152], pcin_pc__hes[151], pcin_pc__hes[150], pcin_pc__hes[149], pcin_pc__hes[148], pcin_pc__hes[147], pcin_pc__hes[146], pcin_pc__hes[145], pcin_pc__hes[144], pcin_pc__hes[143], pcin_pc__hes[142], pcin_pc__hes[141], pcin_pc__hes[140], pcin_pc__hes[139], pcin_pc__hes[138], pcin_pc__hes[137], pcin_pc__hes[136], pcin_pc__hes[135], pcin_pc__hes[134], pcin_pc__hes[133], pcin_pc__hes[132], pcin_pc__hes[131], pcin_pc__hes[130], pcin_pc__hes[129], pcin_pc__hes[128], pcin_pc__hes[127], pcin_pc__hes[126], pcin_pc__hes[125], pcin_pc__hes[124], pcin_pc__hes[123], pcin_pc__hes[122], pcin_pc__hes[121], pcin_pc__hes[120], pcin_pc__hes[119], pcin_pc__hes[118], pcin_pc__hes[117], pcin_pc__hes[116], pcin_pc__hes[115], pcin_pc__hes[114], pcin_pc__hes[113], pcin_pc__hes[112], pcin_pc__hes[111], pcin_pc__hes[110], pcin_pc__hes[109], pcin_pc__hes[108], pcin_pc__hes[107], pcin_pc__hes[106], pcin_pc__hes[105], pcin_pc__hes[104], pcin_pc__hes[103], pcin_pc__hes[102], pcin_pc__hes[101], pcin_pc__hes[100], pcin_pc__hes[99], pcin_pc__hes[98], pcin_pc__hes[97], pcin_pc__hes[96], pcin_pc__hes[95], pcin_pc__hes[94], pcin_pc__hes[93], pcin_pc__hes[92], pcin_pc__hes[91], pcin_pc__hes[90], pcin_pc__hes[89], pcin_pc__hes[88], pcin_pc__hes[87], pcin_pc__hes[86], pcin_pc__hes[85], pcin_pc__hes[84], pcin_pc__hes[83], pcin_pc__hes[82], pcin_pc__hes[81], pcin_pc__hes[80], pcin_pc__hes[79], pcin_pc__hes[78], pcin_pc__hes[77], pcin_pc__hes[76], pcin_pc__hes[75], pcin_pc__hes[74], pcin_pc__hes[73], pcin_pc__hes[72], pcin_pc__hes[71], pcin_pc__hes[70], pcin_pc__hes[69], pcin_pc__hes[68], pcin_pc__hes[67], pcin_pc__hes[66], pcin_pc__hes[65], pcin_pc__hes[64], pcin_pc__hes[63], pcin_pc__hes[62], pcin_pc__hes[61], pcin_pc__hes[60], pcin_pc__hes[59], pcin_pc__hes[58], pcin_pc__hes[57], pcin_pc__hes[56], pcin_pc__hes[55], pcin_pc__hes[54], pcin_pc__hes[53], pcin_pc__hes[52], pcin_pc__hes[51], pcin_pc__hes[50], pcin_pc__hes[49], pcin_pc__hes[48], pcin_pc__hes[47], pcin_pc__hes[46], pcin_pc__hes[45], pcin_pc__hes[44], pcin_pc__hes[43], pcin_pc__hes[42], pcin_pc__hes[41], pcin_pc__hes[40], pcin_pc__hes[39], pcin_pc__hes[38], pcin_pc__hes[37], pcin_pc__hes[36], pcin_pc__hes[35], pcin_pc__hes[34], pcin_pc__hes[33], pcin_pc__hes[32], pcin_pc__hes[31], pcin_pc__hes[30], pcin_pc__hes[29], pcin_pc__hes[28], pcin_pc__hes[27], pcin_pc__hes[26], pcin_pc__hes[25], pcin_pc__hes[24], pcin_pc__hes[23], pcin_pc__hes[22], pcin_pc__hes[21], pcin_pc__hes[20], pcin_pc__hes[19], pcin_pc__hes[18], pcin_pc__hes[17], pcin_pc__hes[16], pcin_pc__hes[15], pcin_pc__hes[14], pcin_pc__hes[13], pcin_pc__hes[12], pcin_pc__hes[11], pcin_pc__hes[10], pcin_pc__hes[9], pcin_pc__hes[8], pcin_pc__hes[7], pcin_pc__hes[6], pcin_pc__hes[5], pcin_pc__hes[4], pcin_pc__hes[3], pcin_pc__hes[2], pcin_pc__hes[1], pcin_pc__hes[0]};
    end else begin
        assign pcin_native_pc__hes = pc__hes;
    end endgenerate
    wire [779:0] pcin_native_i_next;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_i_next
        (* keep = 1, face_keep = 1 *) reg [779:0] pcin_i_next;
        always @(posedge ck) pcin_i_next <= i_next[779:0] ^ 780'd4;
        assign pcin_native_i_next = {pcin_i_next[779], pcin_i_next[778], pcin_i_next[777], pcin_i_next[776], pcin_i_next[775], pcin_i_next[774], pcin_i_next[773], pcin_i_next[772], pcin_i_next[771], pcin_i_next[770], pcin_i_next[769], pcin_i_next[768], pcin_i_next[767], pcin_i_next[766], pcin_i_next[765], pcin_i_next[764], pcin_i_next[763], pcin_i_next[762], pcin_i_next[761], pcin_i_next[760], pcin_i_next[759], pcin_i_next[758], pcin_i_next[757], pcin_i_next[756], pcin_i_next[755], pcin_i_next[754], pcin_i_next[753], pcin_i_next[752], pcin_i_next[751], pcin_i_next[750], pcin_i_next[749], pcin_i_next[748], pcin_i_next[747], pcin_i_next[746], pcin_i_next[745], pcin_i_next[744], pcin_i_next[743], pcin_i_next[742], pcin_i_next[741], pcin_i_next[740], pcin_i_next[739], pcin_i_next[738], pcin_i_next[737], pcin_i_next[736], pcin_i_next[735], pcin_i_next[734], pcin_i_next[733], pcin_i_next[732], pcin_i_next[731], pcin_i_next[730], pcin_i_next[729], pcin_i_next[728], pcin_i_next[727], pcin_i_next[726], pcin_i_next[725], pcin_i_next[724], pcin_i_next[723], pcin_i_next[722], pcin_i_next[721], pcin_i_next[720], pcin_i_next[719], pcin_i_next[718], pcin_i_next[717], pcin_i_next[716], pcin_i_next[715], pcin_i_next[714], pcin_i_next[713], pcin_i_next[712], pcin_i_next[711], pcin_i_next[710], pcin_i_next[709], pcin_i_next[708], pcin_i_next[707], pcin_i_next[706], pcin_i_next[705], pcin_i_next[704], pcin_i_next[703], pcin_i_next[702], pcin_i_next[701], pcin_i_next[700], pcin_i_next[699], pcin_i_next[698], pcin_i_next[697], pcin_i_next[696], pcin_i_next[695], pcin_i_next[694], pcin_i_next[693], pcin_i_next[692], pcin_i_next[691], pcin_i_next[690], pcin_i_next[689], pcin_i_next[688], pcin_i_next[687], pcin_i_next[686], pcin_i_next[685], pcin_i_next[684], pcin_i_next[683], pcin_i_next[682], pcin_i_next[681], pcin_i_next[680], pcin_i_next[679], pcin_i_next[678], pcin_i_next[677], pcin_i_next[676], pcin_i_next[675], pcin_i_next[674], pcin_i_next[673], pcin_i_next[672], pcin_i_next[671], pcin_i_next[670], pcin_i_next[669], pcin_i_next[668], pcin_i_next[667], pcin_i_next[666], pcin_i_next[665], pcin_i_next[664], pcin_i_next[663], pcin_i_next[662], pcin_i_next[661], pcin_i_next[660], pcin_i_next[659], pcin_i_next[658], pcin_i_next[657], pcin_i_next[656], pcin_i_next[655], pcin_i_next[654], pcin_i_next[653], pcin_i_next[652], pcin_i_next[651], pcin_i_next[650], pcin_i_next[649], pcin_i_next[648], pcin_i_next[647], pcin_i_next[646], pcin_i_next[645], pcin_i_next[644], pcin_i_next[643], pcin_i_next[642], pcin_i_next[641], pcin_i_next[640], pcin_i_next[639], pcin_i_next[638], pcin_i_next[637], pcin_i_next[636], pcin_i_next[635], pcin_i_next[634], pcin_i_next[633], pcin_i_next[632], pcin_i_next[631], pcin_i_next[630], pcin_i_next[629], pcin_i_next[628], pcin_i_next[627], pcin_i_next[626], pcin_i_next[625], pcin_i_next[624], pcin_i_next[623], pcin_i_next[622], pcin_i_next[621], pcin_i_next[620], pcin_i_next[619], pcin_i_next[618], pcin_i_next[617], pcin_i_next[616], pcin_i_next[615], pcin_i_next[614], pcin_i_next[613], pcin_i_next[612], pcin_i_next[611], pcin_i_next[610], pcin_i_next[609], pcin_i_next[608], pcin_i_next[607], pcin_i_next[606], pcin_i_next[605], pcin_i_next[604], pcin_i_next[603], pcin_i_next[602], pcin_i_next[601], pcin_i_next[600], pcin_i_next[599], pcin_i_next[598], pcin_i_next[597], pcin_i_next[596], pcin_i_next[595], pcin_i_next[594], pcin_i_next[593], pcin_i_next[592], pcin_i_next[591], pcin_i_next[590], pcin_i_next[589], pcin_i_next[588], pcin_i_next[587], pcin_i_next[586], pcin_i_next[585], pcin_i_next[584], pcin_i_next[583], pcin_i_next[582], pcin_i_next[581], pcin_i_next[580], pcin_i_next[579], pcin_i_next[578], pcin_i_next[577], pcin_i_next[576], pcin_i_next[575], pcin_i_next[574], pcin_i_next[573], pcin_i_next[572], pcin_i_next[571], pcin_i_next[570], pcin_i_next[569], pcin_i_next[568], pcin_i_next[567], pcin_i_next[566], pcin_i_next[565], pcin_i_next[564], pcin_i_next[563], pcin_i_next[562], pcin_i_next[561], pcin_i_next[560], pcin_i_next[559], pcin_i_next[558], pcin_i_next[557], pcin_i_next[556], pcin_i_next[555], pcin_i_next[554], pcin_i_next[553], pcin_i_next[552], pcin_i_next[551], pcin_i_next[550], pcin_i_next[549], pcin_i_next[548], pcin_i_next[547], pcin_i_next[546], pcin_i_next[545], pcin_i_next[544], pcin_i_next[543], pcin_i_next[542], pcin_i_next[541], pcin_i_next[540], pcin_i_next[539], pcin_i_next[538], pcin_i_next[537], pcin_i_next[536], pcin_i_next[535], pcin_i_next[534], pcin_i_next[533], pcin_i_next[532], pcin_i_next[531], pcin_i_next[530], pcin_i_next[529], pcin_i_next[528], pcin_i_next[527], pcin_i_next[526], pcin_i_next[525], pcin_i_next[524], pcin_i_next[523], pcin_i_next[522], pcin_i_next[521], pcin_i_next[520], pcin_i_next[519], pcin_i_next[518], pcin_i_next[517], pcin_i_next[516], pcin_i_next[515], pcin_i_next[514], pcin_i_next[513], pcin_i_next[512], pcin_i_next[511], pcin_i_next[510], pcin_i_next[509], pcin_i_next[508], pcin_i_next[507], pcin_i_next[506], pcin_i_next[505], pcin_i_next[504], pcin_i_next[503], pcin_i_next[502], pcin_i_next[501], pcin_i_next[500], pcin_i_next[499], pcin_i_next[498], pcin_i_next[497], pcin_i_next[496], pcin_i_next[495], pcin_i_next[494], pcin_i_next[493], pcin_i_next[492], pcin_i_next[491], pcin_i_next[490], pcin_i_next[489], pcin_i_next[488], pcin_i_next[487], pcin_i_next[486], pcin_i_next[485], pcin_i_next[484], pcin_i_next[483], pcin_i_next[482], pcin_i_next[481], pcin_i_next[480], pcin_i_next[479], pcin_i_next[478], pcin_i_next[477], pcin_i_next[476], pcin_i_next[475], pcin_i_next[474], pcin_i_next[473], pcin_i_next[472], pcin_i_next[471], pcin_i_next[470], pcin_i_next[469], pcin_i_next[468], pcin_i_next[467], pcin_i_next[466], pcin_i_next[465], pcin_i_next[464], pcin_i_next[463], pcin_i_next[462], pcin_i_next[461], pcin_i_next[460], pcin_i_next[459], pcin_i_next[458], pcin_i_next[457], pcin_i_next[456], pcin_i_next[455], pcin_i_next[454], pcin_i_next[453], pcin_i_next[452], pcin_i_next[451], pcin_i_next[450], pcin_i_next[449], pcin_i_next[448], pcin_i_next[447], pcin_i_next[446], pcin_i_next[445], pcin_i_next[444], pcin_i_next[443], pcin_i_next[442], pcin_i_next[441], pcin_i_next[440], pcin_i_next[439], pcin_i_next[438], pcin_i_next[437], pcin_i_next[436], pcin_i_next[435], pcin_i_next[434], pcin_i_next[433], pcin_i_next[432], pcin_i_next[431], pcin_i_next[430], pcin_i_next[429], pcin_i_next[428], pcin_i_next[427], pcin_i_next[426], pcin_i_next[425], pcin_i_next[424], pcin_i_next[423], pcin_i_next[422], pcin_i_next[421], pcin_i_next[420], pcin_i_next[419], pcin_i_next[418], pcin_i_next[417], pcin_i_next[416], pcin_i_next[415], pcin_i_next[414], pcin_i_next[413], pcin_i_next[412], pcin_i_next[411], pcin_i_next[410], pcin_i_next[409], pcin_i_next[408], pcin_i_next[407], pcin_i_next[406], pcin_i_next[405], pcin_i_next[404], pcin_i_next[403], pcin_i_next[402], pcin_i_next[401], pcin_i_next[400], pcin_i_next[399], pcin_i_next[398], pcin_i_next[397], pcin_i_next[396], pcin_i_next[395], pcin_i_next[394], pcin_i_next[393], pcin_i_next[392], pcin_i_next[391], pcin_i_next[390], pcin_i_next[389], pcin_i_next[388], pcin_i_next[387], pcin_i_next[386], pcin_i_next[385], pcin_i_next[384], pcin_i_next[383], pcin_i_next[382], pcin_i_next[381], pcin_i_next[380], pcin_i_next[379], pcin_i_next[378], pcin_i_next[377], pcin_i_next[376], pcin_i_next[375], pcin_i_next[374], pcin_i_next[373], pcin_i_next[372], pcin_i_next[371], pcin_i_next[370], pcin_i_next[369], pcin_i_next[368], pcin_i_next[367], pcin_i_next[366], pcin_i_next[365], pcin_i_next[364], pcin_i_next[363], pcin_i_next[362], pcin_i_next[361], pcin_i_next[360], pcin_i_next[359], pcin_i_next[358], pcin_i_next[357], pcin_i_next[356], pcin_i_next[355], pcin_i_next[354], pcin_i_next[353], pcin_i_next[352], pcin_i_next[351], pcin_i_next[350], pcin_i_next[349], pcin_i_next[348], pcin_i_next[347], pcin_i_next[346], pcin_i_next[345], pcin_i_next[344], pcin_i_next[343], pcin_i_next[342], pcin_i_next[341], pcin_i_next[340], pcin_i_next[339], pcin_i_next[338], pcin_i_next[337], pcin_i_next[336], pcin_i_next[335], pcin_i_next[334], pcin_i_next[333], pcin_i_next[332], pcin_i_next[331], pcin_i_next[330], pcin_i_next[329], pcin_i_next[328], pcin_i_next[327], pcin_i_next[326], pcin_i_next[325], pcin_i_next[324], pcin_i_next[323], pcin_i_next[322], pcin_i_next[321], pcin_i_next[320], pcin_i_next[319], pcin_i_next[318], pcin_i_next[317], pcin_i_next[316], pcin_i_next[315], pcin_i_next[314], pcin_i_next[313], pcin_i_next[312], pcin_i_next[311], pcin_i_next[310], pcin_i_next[309], pcin_i_next[308], pcin_i_next[307], pcin_i_next[306], pcin_i_next[305], pcin_i_next[304], pcin_i_next[303], pcin_i_next[302], pcin_i_next[301], pcin_i_next[300], pcin_i_next[299], pcin_i_next[298], pcin_i_next[297], pcin_i_next[296], pcin_i_next[295], pcin_i_next[294], pcin_i_next[293], pcin_i_next[292], pcin_i_next[291], pcin_i_next[290], pcin_i_next[289], pcin_i_next[288], pcin_i_next[287], pcin_i_next[286], pcin_i_next[285], pcin_i_next[284], pcin_i_next[283], pcin_i_next[282], pcin_i_next[281], pcin_i_next[280], pcin_i_next[279], pcin_i_next[278], pcin_i_next[277], pcin_i_next[276], pcin_i_next[275], pcin_i_next[274], pcin_i_next[273], pcin_i_next[272], pcin_i_next[271], pcin_i_next[270], pcin_i_next[269], pcin_i_next[268], pcin_i_next[267], pcin_i_next[266], pcin_i_next[265], pcin_i_next[264], pcin_i_next[263], pcin_i_next[262], pcin_i_next[261], pcin_i_next[260], pcin_i_next[259], pcin_i_next[258], pcin_i_next[257], pcin_i_next[256], pcin_i_next[255], pcin_i_next[254], pcin_i_next[253], pcin_i_next[252], pcin_i_next[251], pcin_i_next[250], pcin_i_next[249], pcin_i_next[248], pcin_i_next[247], pcin_i_next[246], pcin_i_next[245], pcin_i_next[244], pcin_i_next[243], pcin_i_next[242], pcin_i_next[241], pcin_i_next[240], pcin_i_next[239], pcin_i_next[238], pcin_i_next[237], pcin_i_next[236], pcin_i_next[235], pcin_i_next[234], pcin_i_next[233], pcin_i_next[232], pcin_i_next[231], pcin_i_next[230], pcin_i_next[229], pcin_i_next[228], pcin_i_next[227], pcin_i_next[226], pcin_i_next[225], pcin_i_next[224], pcin_i_next[223], pcin_i_next[222], pcin_i_next[221], pcin_i_next[220], pcin_i_next[219], pcin_i_next[218], pcin_i_next[217], pcin_i_next[216], pcin_i_next[215], pcin_i_next[214], pcin_i_next[213], pcin_i_next[212], pcin_i_next[211], pcin_i_next[210], pcin_i_next[209], pcin_i_next[208], pcin_i_next[207], pcin_i_next[206], pcin_i_next[205], pcin_i_next[204], pcin_i_next[203], pcin_i_next[202], pcin_i_next[201], pcin_i_next[200], pcin_i_next[199], pcin_i_next[198], pcin_i_next[197], pcin_i_next[196], pcin_i_next[195], pcin_i_next[194], pcin_i_next[193], pcin_i_next[192], pcin_i_next[191], pcin_i_next[190], pcin_i_next[189], pcin_i_next[188], pcin_i_next[187], pcin_i_next[186], pcin_i_next[185], pcin_i_next[184], pcin_i_next[183], pcin_i_next[182], pcin_i_next[181], pcin_i_next[180], pcin_i_next[179], pcin_i_next[178], pcin_i_next[177], pcin_i_next[176], pcin_i_next[175], pcin_i_next[174], pcin_i_next[173], pcin_i_next[172], pcin_i_next[171], pcin_i_next[170], pcin_i_next[169], pcin_i_next[168], pcin_i_next[167], pcin_i_next[166], pcin_i_next[165], pcin_i_next[164], pcin_i_next[163], pcin_i_next[162], pcin_i_next[161], pcin_i_next[160], pcin_i_next[159], pcin_i_next[158], pcin_i_next[157], pcin_i_next[156], pcin_i_next[155], pcin_i_next[154], pcin_i_next[153], pcin_i_next[152], pcin_i_next[151], pcin_i_next[150], pcin_i_next[149], pcin_i_next[148], pcin_i_next[147], pcin_i_next[146], pcin_i_next[145], pcin_i_next[144], pcin_i_next[143], pcin_i_next[142], pcin_i_next[141], pcin_i_next[140], pcin_i_next[139], pcin_i_next[138], pcin_i_next[137], pcin_i_next[136], pcin_i_next[135], pcin_i_next[134], pcin_i_next[133], pcin_i_next[132], pcin_i_next[131], pcin_i_next[130], pcin_i_next[129], pcin_i_next[128], pcin_i_next[127], pcin_i_next[126], pcin_i_next[125], pcin_i_next[124], pcin_i_next[123], pcin_i_next[122], pcin_i_next[121], pcin_i_next[120], pcin_i_next[119], pcin_i_next[118], pcin_i_next[117], pcin_i_next[116], pcin_i_next[115], pcin_i_next[114], pcin_i_next[113], pcin_i_next[112], pcin_i_next[111], pcin_i_next[110], pcin_i_next[109], pcin_i_next[108], pcin_i_next[107], pcin_i_next[106], pcin_i_next[105], pcin_i_next[104], pcin_i_next[103], pcin_i_next[102], pcin_i_next[101], pcin_i_next[100], pcin_i_next[99], pcin_i_next[98], pcin_i_next[97], pcin_i_next[96], pcin_i_next[95], pcin_i_next[94], pcin_i_next[93], pcin_i_next[92], pcin_i_next[91], pcin_i_next[90], pcin_i_next[89], pcin_i_next[88], pcin_i_next[87], pcin_i_next[86], pcin_i_next[85], pcin_i_next[84], pcin_i_next[83], pcin_i_next[82], pcin_i_next[81], pcin_i_next[80], pcin_i_next[79], pcin_i_next[78], pcin_i_next[77], pcin_i_next[76], pcin_i_next[75], pcin_i_next[74], pcin_i_next[73], pcin_i_next[72], pcin_i_next[71], pcin_i_next[70], pcin_i_next[69], pcin_i_next[68], pcin_i_next[67], pcin_i_next[66], pcin_i_next[65], pcin_i_next[64], pcin_i_next[63], pcin_i_next[62], pcin_i_next[61], pcin_i_next[60], pcin_i_next[59], pcin_i_next[58], pcin_i_next[57], pcin_i_next[56], pcin_i_next[55], pcin_i_next[54], pcin_i_next[53], pcin_i_next[52], pcin_i_next[51], pcin_i_next[50], pcin_i_next[49], pcin_i_next[48], pcin_i_next[47], pcin_i_next[46], pcin_i_next[45], pcin_i_next[44], pcin_i_next[43], pcin_i_next[42], pcin_i_next[41], pcin_i_next[40], pcin_i_next[39], pcin_i_next[38], pcin_i_next[37], pcin_i_next[36], pcin_i_next[35], pcin_i_next[34], pcin_i_next[33], pcin_i_next[32], pcin_i_next[31], pcin_i_next[30], pcin_i_next[29], pcin_i_next[28], pcin_i_next[27], pcin_i_next[26], pcin_i_next[25], pcin_i_next[24], pcin_i_next[23], pcin_i_next[22], pcin_i_next[21], pcin_i_next[20], pcin_i_next[19], pcin_i_next[18], pcin_i_next[17], pcin_i_next[16], pcin_i_next[15], pcin_i_next[14], pcin_i_next[13], pcin_i_next[12], pcin_i_next[11], pcin_i_next[10], pcin_i_next[9], pcin_i_next[8], pcin_i_next[7], pcin_i_next[6], pcin_i_next[5], pcin_i_next[4], pcin_i_next[3], pcin_i_next[2], pcin_i_next[1], pcin_i_next[0]};
    end else begin
        assign pcin_native_i_next = i_next;
    end endgenerate
    wire [260:0] pcin_native_pc__land_er;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__land_er
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_pc__land_er;
        always @(posedge ck) pcin_pc__land_er <= pc__land_er[0:0];
        (* keep = 1, face_keep = 1 *) reg [260:259] pcin_pc__land_er_259;
        always @(posedge ck) pcin_pc__land_er_259 <= pc__land_er[260:259];
        assign pcin_native_pc__land_er = {pcin_pc__land_er_259[260], pcin_pc__land_er_259[259], pc__land_er[258], pc__land_er[257], pc__land_er[256], pc__land_er[255], pc__land_er[254], pc__land_er[253], pc__land_er[252], pc__land_er[251], pc__land_er[250], pc__land_er[249], pc__land_er[248], pc__land_er[247], pc__land_er[246], pc__land_er[245], pc__land_er[244], pc__land_er[243], pc__land_er[242], pc__land_er[241], pc__land_er[240], pc__land_er[239], pc__land_er[238], pc__land_er[237], pc__land_er[236], pc__land_er[235], pc__land_er[234], pc__land_er[233], pc__land_er[232], pc__land_er[231], pc__land_er[230], pc__land_er[229], pc__land_er[228], pc__land_er[227], pc__land_er[226], pc__land_er[225], pc__land_er[224], pc__land_er[223], pc__land_er[222], pc__land_er[221], pc__land_er[220], pc__land_er[219], pc__land_er[218], pc__land_er[217], pc__land_er[216], pc__land_er[215], pc__land_er[214], pc__land_er[213], pc__land_er[212], pc__land_er[211], pc__land_er[210], pc__land_er[209], pc__land_er[208], pc__land_er[207], pc__land_er[206], pc__land_er[205], pc__land_er[204], pc__land_er[203], pc__land_er[202], pc__land_er[201], pc__land_er[200], pc__land_er[199], pc__land_er[198], pc__land_er[197], pc__land_er[196], pc__land_er[195], pc__land_er[194], pc__land_er[193], pc__land_er[192], pc__land_er[191], pc__land_er[190], pc__land_er[189], pc__land_er[188], pc__land_er[187], pc__land_er[186], pc__land_er[185], pc__land_er[184], pc__land_er[183], pc__land_er[182], pc__land_er[181], pc__land_er[180], pc__land_er[179], pc__land_er[178], pc__land_er[177], pc__land_er[176], pc__land_er[175], pc__land_er[174], pc__land_er[173], pc__land_er[172], pc__land_er[171], pc__land_er[170], pc__land_er[169], pc__land_er[168], pc__land_er[167], pc__land_er[166], pc__land_er[165], pc__land_er[164], pc__land_er[163], pc__land_er[162], pc__land_er[161], pc__land_er[160], pc__land_er[159], pc__land_er[158], pc__land_er[157], pc__land_er[156], pc__land_er[155], pc__land_er[154], pc__land_er[153], pc__land_er[152], pc__land_er[151], pc__land_er[150], pc__land_er[149], pc__land_er[148], pc__land_er[147], pc__land_er[146], pc__land_er[145], pc__land_er[144], pc__land_er[143], pc__land_er[142], pc__land_er[141], pc__land_er[140], pc__land_er[139], pc__land_er[138], pc__land_er[137], pc__land_er[136], pc__land_er[135], pc__land_er[134], pc__land_er[133], pc__land_er[132], pc__land_er[131], pc__land_er[130], pc__land_er[129], pc__land_er[128], pc__land_er[127], pc__land_er[126], pc__land_er[125], pc__land_er[124], pc__land_er[123], pc__land_er[122], pc__land_er[121], pc__land_er[120], pc__land_er[119], pc__land_er[118], pc__land_er[117], pc__land_er[116], pc__land_er[115], pc__land_er[114], pc__land_er[113], pc__land_er[112], pc__land_er[111], pc__land_er[110], pc__land_er[109], pc__land_er[108], pc__land_er[107], pc__land_er[106], pc__land_er[105], pc__land_er[104], pc__land_er[103], pc__land_er[102], pc__land_er[101], pc__land_er[100], pc__land_er[99], pc__land_er[98], pc__land_er[97], pc__land_er[96], pc__land_er[95], pc__land_er[94], pc__land_er[93], pc__land_er[92], pc__land_er[91], pc__land_er[90], pc__land_er[89], pc__land_er[88], pc__land_er[87], pc__land_er[86], pc__land_er[85], pc__land_er[84], pc__land_er[83], pc__land_er[82], pc__land_er[81], pc__land_er[80], pc__land_er[79], pc__land_er[78], pc__land_er[77], pc__land_er[76], pc__land_er[75], pc__land_er[74], pc__land_er[73], pc__land_er[72], pc__land_er[71], pc__land_er[70], pc__land_er[69], pc__land_er[68], pc__land_er[67], pc__land_er[66], pc__land_er[65], pc__land_er[64], pc__land_er[63], pc__land_er[62], pc__land_er[61], pc__land_er[60], pc__land_er[59], pc__land_er[58], pc__land_er[57], pc__land_er[56], pc__land_er[55], pc__land_er[54], pc__land_er[53], pc__land_er[52], pc__land_er[51], pc__land_er[50], pc__land_er[49], pc__land_er[48], pc__land_er[47], pc__land_er[46], pc__land_er[45], pc__land_er[44], pc__land_er[43], pc__land_er[42], pc__land_er[41], pc__land_er[40], pc__land_er[39], pc__land_er[38], pc__land_er[37], pc__land_er[36], pc__land_er[35], pc__land_er[34], pc__land_er[33], pc__land_er[32], pc__land_er[31], pc__land_er[30], pc__land_er[29], pc__land_er[28], pc__land_er[27], pc__land_er[26], pc__land_er[25], pc__land_er[24], pc__land_er[23], pc__land_er[22], pc__land_er[21], pc__land_er[20], pc__land_er[19], pc__land_er[18], pc__land_er[17], pc__land_er[16], pc__land_er[15], pc__land_er[14], pc__land_er[13], pc__land_er[12], pc__land_er[11], pc__land_er[10], pc__land_er[9], pc__land_er[8], pc__land_er[7], pc__land_er[6], pc__land_er[5], pc__land_er[4], pc__land_er[3], pc__land_er[2], pc__land_er[1], pcin_pc__land_er[0]};
    end else begin
        assign pcin_native_pc__land_er = pc__land_er;
    end endgenerate
    wire  pcin_native_rst_n;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_rst_n
        (* keep = 1, face_keep = 1 *) reg  pcin_rst_n;
        always @(posedge ck) pcin_rst_n <= rst_n;
        assign pcin_native_rst_n = pcin_rst_n;
    end else begin
        assign pcin_native_rst_n = rst_n;
    end endgenerate
    wire [32:0] pcin_native_pc__ki;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__ki
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_pc__ki;
        always @(posedge ck) pcin_pc__ki <= pc__ki[0:0];
        (* keep = 1, face_keep = 1 *) reg [20:15] pcin_pc__ki_15;
        always @(posedge ck) pcin_pc__ki_15 <= pc__ki[20:15];
        (* keep = 1, face_keep = 1 *) reg [32:31] pcin_pc__ki_31;
        always @(posedge ck) pcin_pc__ki_31 <= pc__ki[32:31];
        assign pcin_native_pc__ki = {pcin_pc__ki_31[32], pcin_pc__ki_31[31], pc__ki[30], pc__ki[29], pc__ki[28], pc__ki[27], pc__ki[26], pc__ki[25], pc__ki[24], pc__ki[23], pc__ki[22], pc__ki[21], pcin_pc__ki_15[20], pcin_pc__ki_15[19], pcin_pc__ki_15[18], pcin_pc__ki_15[17], pcin_pc__ki_15[16], pcin_pc__ki_15[15], pc__ki[14], pc__ki[13], pc__ki[12], pc__ki[11], pc__ki[10], pc__ki[9], pc__ki[8], pc__ki[7], pc__ki[6], pc__ki[5], pc__ki[4], pc__ki[3], pc__ki[2], pc__ki[1], pcin_pc__ki[0]};
    end else begin
        assign pcin_native_pc__ki = pc__ki;
    end endgenerate

    qkd_kv_pc_chain_station_b_p u_actual_chain (
        .ck(ck),
        .rst_n(pcin_native_rst_n),
        .cfg_stack(pcin_native_pc__cfg_stack),
        .di(pcin_native_i_next),
        .dout(coupon_dout),
        .land_es(coupon_land_es),
        .land_er(pcin_native_pc__land_er),
        .wes(coupon_wes),
        .es_context(coupon_es_context),
        .es_expected_valid(coupon_es_expected_valid),
        .es_expected_identity(coupon_es_expected_identity),
        .es_expected_address(coupon_es_expected_address),
        .es_expected_pc(coupon_es_expected_pc),
        .es_expected_stack(coupon_es_expected_stack),
        .emb_issue_v(coupon_emb_issue_v),
        .emb_token(coupon_emb_token),
        .emb_word_index(coupon_emb_word_index),
        .emb_half(coupon_emb_half),
        .emb_scale(coupon_emb_scale),
        .emb_epoch(coupon_emb_epoch),
        .emb_return_slot(coupon_emb_return_slot),
        .capture_slot(coupon_capture_slot),
        .transfer_slot(coupon_transfer_slot),
        .fault(coupon_fault)
    );
endmodule
module qkd_kvs_pc_h_head_p_badreset #(
    parameter KVSPC_INPUT_COLLAR = 0,
    parameter [4:0] PC = 0
) (
    input wire ck,
    input wire rst_n,
    input wire hck,
    input wire hrst_n,
    input wire [288:0] pc__pi,
    input wire [32:0] pc__ki,
    input wire [1:0] pc__cfg_stack,
    input wire [3:0] pc__front_hbm_data,
    input wire [3:0] pc__return_hbm_data,
    input wire [0:0] x__est__0_1,
    input wire [260:0] pc__land_er,
    input wire [287:0] pc__hes,
    output wire [0:0] pc__fo,
    output wire [260:0] pc__er,
    output wire [32:0] pc__ko,
    output wire [327:0] pc__po,
    output wire [0:0] pc__completion_v,
    output wire [0:0] pc__completion_we,
    output wire [287:0] pc__land_es,
    output wire [260:0] pc__her,
    output wire [0:0] pc__hcompletion_v,
    output wire [0:0] pc__hcompletion_we,
    input wire [127:0] i_grp,
    input wire [779:0] i_next,
    output wire [304:0] o_grp,
    output wire [298:0] o_next
,
    output wire [779:0] coupon_dout,
    output wire [287:0] coupon_land_es,
    output wire [287:0] coupon_wes,
    output wire [317:0] coupon_es_context,
    output wire  coupon_es_expected_valid,
    output wire [60:0] coupon_es_expected_identity,
    output wire [28:0] coupon_es_expected_address,
    output wire [4:0] coupon_es_expected_pc,
    output wire [1:0] coupon_es_expected_stack,
    output wire  coupon_emb_issue_v,
    output wire [17:0] coupon_emb_token,
    output wire [5:0] coupon_emb_word_index,
    output wire  coupon_emb_half,
    output wire  coupon_emb_scale,
    output wire [15:0] coupon_emb_epoch,
    output wire  coupon_emb_return_slot,
    output wire  coupon_capture_slot,
    output wire  coupon_transfer_slot,
    output wire  coupon_fault
);
    // KVSPC_NATIVE_INPUT_COLLAR: parent and physical sources must select exactly once.
    wire  pcin_native_hrst_n;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_hrst_n
        (* keep = 1, face_keep = 1 *) reg  pcin_hrst_n;
        always @(posedge ck) pcin_hrst_n <= hrst_n;
        assign pcin_native_hrst_n = pcin_hrst_n;
    end else begin
        assign pcin_native_hrst_n = hrst_n;
    end endgenerate
    wire [127:0] pcin_native_i_grp;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_i_grp
        (* keep = 1, face_keep = 1 *) reg [127:0] pcin_i_grp;
        always @(posedge ck) pcin_i_grp <= i_grp[127:0];
        assign pcin_native_i_grp = {pcin_i_grp[127], pcin_i_grp[126], pcin_i_grp[125], pcin_i_grp[124], pcin_i_grp[123], pcin_i_grp[122], pcin_i_grp[121], pcin_i_grp[120], pcin_i_grp[119], pcin_i_grp[118], pcin_i_grp[117], pcin_i_grp[116], pcin_i_grp[115], pcin_i_grp[114], pcin_i_grp[113], pcin_i_grp[112], pcin_i_grp[111], pcin_i_grp[110], pcin_i_grp[109], pcin_i_grp[108], pcin_i_grp[107], pcin_i_grp[106], pcin_i_grp[105], pcin_i_grp[104], pcin_i_grp[103], pcin_i_grp[102], pcin_i_grp[101], pcin_i_grp[100], pcin_i_grp[99], pcin_i_grp[98], pcin_i_grp[97], pcin_i_grp[96], pcin_i_grp[95], pcin_i_grp[94], pcin_i_grp[93], pcin_i_grp[92], pcin_i_grp[91], pcin_i_grp[90], pcin_i_grp[89], pcin_i_grp[88], pcin_i_grp[87], pcin_i_grp[86], pcin_i_grp[85], pcin_i_grp[84], pcin_i_grp[83], pcin_i_grp[82], pcin_i_grp[81], pcin_i_grp[80], pcin_i_grp[79], pcin_i_grp[78], pcin_i_grp[77], pcin_i_grp[76], pcin_i_grp[75], pcin_i_grp[74], pcin_i_grp[73], pcin_i_grp[72], pcin_i_grp[71], pcin_i_grp[70], pcin_i_grp[69], pcin_i_grp[68], pcin_i_grp[67], pcin_i_grp[66], pcin_i_grp[65], pcin_i_grp[64], pcin_i_grp[63], pcin_i_grp[62], pcin_i_grp[61], pcin_i_grp[60], pcin_i_grp[59], pcin_i_grp[58], pcin_i_grp[57], pcin_i_grp[56], pcin_i_grp[55], pcin_i_grp[54], pcin_i_grp[53], pcin_i_grp[52], pcin_i_grp[51], pcin_i_grp[50], pcin_i_grp[49], pcin_i_grp[48], pcin_i_grp[47], pcin_i_grp[46], pcin_i_grp[45], pcin_i_grp[44], pcin_i_grp[43], pcin_i_grp[42], pcin_i_grp[41], pcin_i_grp[40], pcin_i_grp[39], pcin_i_grp[38], pcin_i_grp[37], pcin_i_grp[36], pcin_i_grp[35], pcin_i_grp[34], pcin_i_grp[33], pcin_i_grp[32], pcin_i_grp[31], pcin_i_grp[30], pcin_i_grp[29], pcin_i_grp[28], pcin_i_grp[27], pcin_i_grp[26], pcin_i_grp[25], pcin_i_grp[24], pcin_i_grp[23], pcin_i_grp[22], pcin_i_grp[21], pcin_i_grp[20], pcin_i_grp[19], pcin_i_grp[18], pcin_i_grp[17], pcin_i_grp[16], pcin_i_grp[15], pcin_i_grp[14], pcin_i_grp[13], pcin_i_grp[12], pcin_i_grp[11], pcin_i_grp[10], pcin_i_grp[9], pcin_i_grp[8], pcin_i_grp[7], pcin_i_grp[6], pcin_i_grp[5], pcin_i_grp[4], pcin_i_grp[3], pcin_i_grp[2], pcin_i_grp[1], pcin_i_grp[0]};
    end else begin
        assign pcin_native_i_grp = i_grp;
    end endgenerate
    wire [1:0] pcin_native_pc__cfg_stack;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__cfg_stack
        (* keep = 1, face_keep = 1 *) reg [1:0] pcin_pc__cfg_stack;
        always @(posedge ck) pcin_pc__cfg_stack <= pc__cfg_stack[1:0];
        assign pcin_native_pc__cfg_stack = {pcin_pc__cfg_stack[1], pcin_pc__cfg_stack[0]};
    end else begin
        assign pcin_native_pc__cfg_stack = pc__cfg_stack;
    end endgenerate
    wire [288:0] pcin_native_pc__pi;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__pi
        (* keep = 1, face_keep = 1 *) reg [288:0] pcin_pc__pi;
        always @(posedge ck) pcin_pc__pi <= pc__pi[288:0];
        assign pcin_native_pc__pi = {pcin_pc__pi[288], pcin_pc__pi[287], pcin_pc__pi[286], pcin_pc__pi[285], pcin_pc__pi[284], pcin_pc__pi[283], pcin_pc__pi[282], pcin_pc__pi[281], pcin_pc__pi[280], pcin_pc__pi[279], pcin_pc__pi[278], pcin_pc__pi[277], pcin_pc__pi[276], pcin_pc__pi[275], pcin_pc__pi[274], pcin_pc__pi[273], pcin_pc__pi[272], pcin_pc__pi[271], pcin_pc__pi[270], pcin_pc__pi[269], pcin_pc__pi[268], pcin_pc__pi[267], pcin_pc__pi[266], pcin_pc__pi[265], pcin_pc__pi[264], pcin_pc__pi[263], pcin_pc__pi[262], pcin_pc__pi[261], pcin_pc__pi[260], pcin_pc__pi[259], pcin_pc__pi[258], pcin_pc__pi[257], pcin_pc__pi[256], pcin_pc__pi[255], pcin_pc__pi[254], pcin_pc__pi[253], pcin_pc__pi[252], pcin_pc__pi[251], pcin_pc__pi[250], pcin_pc__pi[249], pcin_pc__pi[248], pcin_pc__pi[247], pcin_pc__pi[246], pcin_pc__pi[245], pcin_pc__pi[244], pcin_pc__pi[243], pcin_pc__pi[242], pcin_pc__pi[241], pcin_pc__pi[240], pcin_pc__pi[239], pcin_pc__pi[238], pcin_pc__pi[237], pcin_pc__pi[236], pcin_pc__pi[235], pcin_pc__pi[234], pcin_pc__pi[233], pcin_pc__pi[232], pcin_pc__pi[231], pcin_pc__pi[230], pcin_pc__pi[229], pcin_pc__pi[228], pcin_pc__pi[227], pcin_pc__pi[226], pcin_pc__pi[225], pcin_pc__pi[224], pcin_pc__pi[223], pcin_pc__pi[222], pcin_pc__pi[221], pcin_pc__pi[220], pcin_pc__pi[219], pcin_pc__pi[218], pcin_pc__pi[217], pcin_pc__pi[216], pcin_pc__pi[215], pcin_pc__pi[214], pcin_pc__pi[213], pcin_pc__pi[212], pcin_pc__pi[211], pcin_pc__pi[210], pcin_pc__pi[209], pcin_pc__pi[208], pcin_pc__pi[207], pcin_pc__pi[206], pcin_pc__pi[205], pcin_pc__pi[204], pcin_pc__pi[203], pcin_pc__pi[202], pcin_pc__pi[201], pcin_pc__pi[200], pcin_pc__pi[199], pcin_pc__pi[198], pcin_pc__pi[197], pcin_pc__pi[196], pcin_pc__pi[195], pcin_pc__pi[194], pcin_pc__pi[193], pcin_pc__pi[192], pcin_pc__pi[191], pcin_pc__pi[190], pcin_pc__pi[189], pcin_pc__pi[188], pcin_pc__pi[187], pcin_pc__pi[186], pcin_pc__pi[185], pcin_pc__pi[184], pcin_pc__pi[183], pcin_pc__pi[182], pcin_pc__pi[181], pcin_pc__pi[180], pcin_pc__pi[179], pcin_pc__pi[178], pcin_pc__pi[177], pcin_pc__pi[176], pcin_pc__pi[175], pcin_pc__pi[174], pcin_pc__pi[173], pcin_pc__pi[172], pcin_pc__pi[171], pcin_pc__pi[170], pcin_pc__pi[169], pcin_pc__pi[168], pcin_pc__pi[167], pcin_pc__pi[166], pcin_pc__pi[165], pcin_pc__pi[164], pcin_pc__pi[163], pcin_pc__pi[162], pcin_pc__pi[161], pcin_pc__pi[160], pcin_pc__pi[159], pcin_pc__pi[158], pcin_pc__pi[157], pcin_pc__pi[156], pcin_pc__pi[155], pcin_pc__pi[154], pcin_pc__pi[153], pcin_pc__pi[152], pcin_pc__pi[151], pcin_pc__pi[150], pcin_pc__pi[149], pcin_pc__pi[148], pcin_pc__pi[147], pcin_pc__pi[146], pcin_pc__pi[145], pcin_pc__pi[144], pcin_pc__pi[143], pcin_pc__pi[142], pcin_pc__pi[141], pcin_pc__pi[140], pcin_pc__pi[139], pcin_pc__pi[138], pcin_pc__pi[137], pcin_pc__pi[136], pcin_pc__pi[135], pcin_pc__pi[134], pcin_pc__pi[133], pcin_pc__pi[132], pcin_pc__pi[131], pcin_pc__pi[130], pcin_pc__pi[129], pcin_pc__pi[128], pcin_pc__pi[127], pcin_pc__pi[126], pcin_pc__pi[125], pcin_pc__pi[124], pcin_pc__pi[123], pcin_pc__pi[122], pcin_pc__pi[121], pcin_pc__pi[120], pcin_pc__pi[119], pcin_pc__pi[118], pcin_pc__pi[117], pcin_pc__pi[116], pcin_pc__pi[115], pcin_pc__pi[114], pcin_pc__pi[113], pcin_pc__pi[112], pcin_pc__pi[111], pcin_pc__pi[110], pcin_pc__pi[109], pcin_pc__pi[108], pcin_pc__pi[107], pcin_pc__pi[106], pcin_pc__pi[105], pcin_pc__pi[104], pcin_pc__pi[103], pcin_pc__pi[102], pcin_pc__pi[101], pcin_pc__pi[100], pcin_pc__pi[99], pcin_pc__pi[98], pcin_pc__pi[97], pcin_pc__pi[96], pcin_pc__pi[95], pcin_pc__pi[94], pcin_pc__pi[93], pcin_pc__pi[92], pcin_pc__pi[91], pcin_pc__pi[90], pcin_pc__pi[89], pcin_pc__pi[88], pcin_pc__pi[87], pcin_pc__pi[86], pcin_pc__pi[85], pcin_pc__pi[84], pcin_pc__pi[83], pcin_pc__pi[82], pcin_pc__pi[81], pcin_pc__pi[80], pcin_pc__pi[79], pcin_pc__pi[78], pcin_pc__pi[77], pcin_pc__pi[76], pcin_pc__pi[75], pcin_pc__pi[74], pcin_pc__pi[73], pcin_pc__pi[72], pcin_pc__pi[71], pcin_pc__pi[70], pcin_pc__pi[69], pcin_pc__pi[68], pcin_pc__pi[67], pcin_pc__pi[66], pcin_pc__pi[65], pcin_pc__pi[64], pcin_pc__pi[63], pcin_pc__pi[62], pcin_pc__pi[61], pcin_pc__pi[60], pcin_pc__pi[59], pcin_pc__pi[58], pcin_pc__pi[57], pcin_pc__pi[56], pcin_pc__pi[55], pcin_pc__pi[54], pcin_pc__pi[53], pcin_pc__pi[52], pcin_pc__pi[51], pcin_pc__pi[50], pcin_pc__pi[49], pcin_pc__pi[48], pcin_pc__pi[47], pcin_pc__pi[46], pcin_pc__pi[45], pcin_pc__pi[44], pcin_pc__pi[43], pcin_pc__pi[42], pcin_pc__pi[41], pcin_pc__pi[40], pcin_pc__pi[39], pcin_pc__pi[38], pcin_pc__pi[37], pcin_pc__pi[36], pcin_pc__pi[35], pcin_pc__pi[34], pcin_pc__pi[33], pcin_pc__pi[32], pcin_pc__pi[31], pcin_pc__pi[30], pcin_pc__pi[29], pcin_pc__pi[28], pcin_pc__pi[27], pcin_pc__pi[26], pcin_pc__pi[25], pcin_pc__pi[24], pcin_pc__pi[23], pcin_pc__pi[22], pcin_pc__pi[21], pcin_pc__pi[20], pcin_pc__pi[19], pcin_pc__pi[18], pcin_pc__pi[17], pcin_pc__pi[16], pcin_pc__pi[15], pcin_pc__pi[14], pcin_pc__pi[13], pcin_pc__pi[12], pcin_pc__pi[11], pcin_pc__pi[10], pcin_pc__pi[9], pcin_pc__pi[8], pcin_pc__pi[7], pcin_pc__pi[6], pcin_pc__pi[5], pcin_pc__pi[4], pcin_pc__pi[3], pcin_pc__pi[2], pcin_pc__pi[1], pcin_pc__pi[0]};
    end else begin
        assign pcin_native_pc__pi = pc__pi;
    end endgenerate
    wire [0:0] pcin_native_x__est__0_1;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_x__est__0_1
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_x__est__0_1;
        always @(posedge ck) pcin_x__est__0_1 <= x__est__0_1[0:0];
        assign pcin_native_x__est__0_1 = {pcin_x__est__0_1[0]};
    end else begin
        assign pcin_native_x__est__0_1 = x__est__0_1;
    end endgenerate
    wire [287:0] pcin_native_pc__hes;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__hes
        (* keep = 1, face_keep = 1 *) reg [287:0] pcin_pc__hes;
        always @(posedge ck) pcin_pc__hes <= pc__hes[287:0];
        assign pcin_native_pc__hes = {pcin_pc__hes[287], pcin_pc__hes[286], pcin_pc__hes[285], pcin_pc__hes[284], pcin_pc__hes[283], pcin_pc__hes[282], pcin_pc__hes[281], pcin_pc__hes[280], pcin_pc__hes[279], pcin_pc__hes[278], pcin_pc__hes[277], pcin_pc__hes[276], pcin_pc__hes[275], pcin_pc__hes[274], pcin_pc__hes[273], pcin_pc__hes[272], pcin_pc__hes[271], pcin_pc__hes[270], pcin_pc__hes[269], pcin_pc__hes[268], pcin_pc__hes[267], pcin_pc__hes[266], pcin_pc__hes[265], pcin_pc__hes[264], pcin_pc__hes[263], pcin_pc__hes[262], pcin_pc__hes[261], pcin_pc__hes[260], pcin_pc__hes[259], pcin_pc__hes[258], pcin_pc__hes[257], pcin_pc__hes[256], pcin_pc__hes[255], pcin_pc__hes[254], pcin_pc__hes[253], pcin_pc__hes[252], pcin_pc__hes[251], pcin_pc__hes[250], pcin_pc__hes[249], pcin_pc__hes[248], pcin_pc__hes[247], pcin_pc__hes[246], pcin_pc__hes[245], pcin_pc__hes[244], pcin_pc__hes[243], pcin_pc__hes[242], pcin_pc__hes[241], pcin_pc__hes[240], pcin_pc__hes[239], pcin_pc__hes[238], pcin_pc__hes[237], pcin_pc__hes[236], pcin_pc__hes[235], pcin_pc__hes[234], pcin_pc__hes[233], pcin_pc__hes[232], pcin_pc__hes[231], pcin_pc__hes[230], pcin_pc__hes[229], pcin_pc__hes[228], pcin_pc__hes[227], pcin_pc__hes[226], pcin_pc__hes[225], pcin_pc__hes[224], pcin_pc__hes[223], pcin_pc__hes[222], pcin_pc__hes[221], pcin_pc__hes[220], pcin_pc__hes[219], pcin_pc__hes[218], pcin_pc__hes[217], pcin_pc__hes[216], pcin_pc__hes[215], pcin_pc__hes[214], pcin_pc__hes[213], pcin_pc__hes[212], pcin_pc__hes[211], pcin_pc__hes[210], pcin_pc__hes[209], pcin_pc__hes[208], pcin_pc__hes[207], pcin_pc__hes[206], pcin_pc__hes[205], pcin_pc__hes[204], pcin_pc__hes[203], pcin_pc__hes[202], pcin_pc__hes[201], pcin_pc__hes[200], pcin_pc__hes[199], pcin_pc__hes[198], pcin_pc__hes[197], pcin_pc__hes[196], pcin_pc__hes[195], pcin_pc__hes[194], pcin_pc__hes[193], pcin_pc__hes[192], pcin_pc__hes[191], pcin_pc__hes[190], pcin_pc__hes[189], pcin_pc__hes[188], pcin_pc__hes[187], pcin_pc__hes[186], pcin_pc__hes[185], pcin_pc__hes[184], pcin_pc__hes[183], pcin_pc__hes[182], pcin_pc__hes[181], pcin_pc__hes[180], pcin_pc__hes[179], pcin_pc__hes[178], pcin_pc__hes[177], pcin_pc__hes[176], pcin_pc__hes[175], pcin_pc__hes[174], pcin_pc__hes[173], pcin_pc__hes[172], pcin_pc__hes[171], pcin_pc__hes[170], pcin_pc__hes[169], pcin_pc__hes[168], pcin_pc__hes[167], pcin_pc__hes[166], pcin_pc__hes[165], pcin_pc__hes[164], pcin_pc__hes[163], pcin_pc__hes[162], pcin_pc__hes[161], pcin_pc__hes[160], pcin_pc__hes[159], pcin_pc__hes[158], pcin_pc__hes[157], pcin_pc__hes[156], pcin_pc__hes[155], pcin_pc__hes[154], pcin_pc__hes[153], pcin_pc__hes[152], pcin_pc__hes[151], pcin_pc__hes[150], pcin_pc__hes[149], pcin_pc__hes[148], pcin_pc__hes[147], pcin_pc__hes[146], pcin_pc__hes[145], pcin_pc__hes[144], pcin_pc__hes[143], pcin_pc__hes[142], pcin_pc__hes[141], pcin_pc__hes[140], pcin_pc__hes[139], pcin_pc__hes[138], pcin_pc__hes[137], pcin_pc__hes[136], pcin_pc__hes[135], pcin_pc__hes[134], pcin_pc__hes[133], pcin_pc__hes[132], pcin_pc__hes[131], pcin_pc__hes[130], pcin_pc__hes[129], pcin_pc__hes[128], pcin_pc__hes[127], pcin_pc__hes[126], pcin_pc__hes[125], pcin_pc__hes[124], pcin_pc__hes[123], pcin_pc__hes[122], pcin_pc__hes[121], pcin_pc__hes[120], pcin_pc__hes[119], pcin_pc__hes[118], pcin_pc__hes[117], pcin_pc__hes[116], pcin_pc__hes[115], pcin_pc__hes[114], pcin_pc__hes[113], pcin_pc__hes[112], pcin_pc__hes[111], pcin_pc__hes[110], pcin_pc__hes[109], pcin_pc__hes[108], pcin_pc__hes[107], pcin_pc__hes[106], pcin_pc__hes[105], pcin_pc__hes[104], pcin_pc__hes[103], pcin_pc__hes[102], pcin_pc__hes[101], pcin_pc__hes[100], pcin_pc__hes[99], pcin_pc__hes[98], pcin_pc__hes[97], pcin_pc__hes[96], pcin_pc__hes[95], pcin_pc__hes[94], pcin_pc__hes[93], pcin_pc__hes[92], pcin_pc__hes[91], pcin_pc__hes[90], pcin_pc__hes[89], pcin_pc__hes[88], pcin_pc__hes[87], pcin_pc__hes[86], pcin_pc__hes[85], pcin_pc__hes[84], pcin_pc__hes[83], pcin_pc__hes[82], pcin_pc__hes[81], pcin_pc__hes[80], pcin_pc__hes[79], pcin_pc__hes[78], pcin_pc__hes[77], pcin_pc__hes[76], pcin_pc__hes[75], pcin_pc__hes[74], pcin_pc__hes[73], pcin_pc__hes[72], pcin_pc__hes[71], pcin_pc__hes[70], pcin_pc__hes[69], pcin_pc__hes[68], pcin_pc__hes[67], pcin_pc__hes[66], pcin_pc__hes[65], pcin_pc__hes[64], pcin_pc__hes[63], pcin_pc__hes[62], pcin_pc__hes[61], pcin_pc__hes[60], pcin_pc__hes[59], pcin_pc__hes[58], pcin_pc__hes[57], pcin_pc__hes[56], pcin_pc__hes[55], pcin_pc__hes[54], pcin_pc__hes[53], pcin_pc__hes[52], pcin_pc__hes[51], pcin_pc__hes[50], pcin_pc__hes[49], pcin_pc__hes[48], pcin_pc__hes[47], pcin_pc__hes[46], pcin_pc__hes[45], pcin_pc__hes[44], pcin_pc__hes[43], pcin_pc__hes[42], pcin_pc__hes[41], pcin_pc__hes[40], pcin_pc__hes[39], pcin_pc__hes[38], pcin_pc__hes[37], pcin_pc__hes[36], pcin_pc__hes[35], pcin_pc__hes[34], pcin_pc__hes[33], pcin_pc__hes[32], pcin_pc__hes[31], pcin_pc__hes[30], pcin_pc__hes[29], pcin_pc__hes[28], pcin_pc__hes[27], pcin_pc__hes[26], pcin_pc__hes[25], pcin_pc__hes[24], pcin_pc__hes[23], pcin_pc__hes[22], pcin_pc__hes[21], pcin_pc__hes[20], pcin_pc__hes[19], pcin_pc__hes[18], pcin_pc__hes[17], pcin_pc__hes[16], pcin_pc__hes[15], pcin_pc__hes[14], pcin_pc__hes[13], pcin_pc__hes[12], pcin_pc__hes[11], pcin_pc__hes[10], pcin_pc__hes[9], pcin_pc__hes[8], pcin_pc__hes[7], pcin_pc__hes[6], pcin_pc__hes[5], pcin_pc__hes[4], pcin_pc__hes[3], pcin_pc__hes[2], pcin_pc__hes[1], pcin_pc__hes[0]};
    end else begin
        assign pcin_native_pc__hes = pc__hes;
    end endgenerate
    wire [779:0] pcin_native_i_next;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_i_next
        (* keep = 1, face_keep = 1 *) reg [779:0] pcin_i_next;
        always @(posedge ck) pcin_i_next <= i_next[779:0];
        assign pcin_native_i_next = {pcin_i_next[779], pcin_i_next[778], pcin_i_next[777], pcin_i_next[776], pcin_i_next[775], pcin_i_next[774], pcin_i_next[773], pcin_i_next[772], pcin_i_next[771], pcin_i_next[770], pcin_i_next[769], pcin_i_next[768], pcin_i_next[767], pcin_i_next[766], pcin_i_next[765], pcin_i_next[764], pcin_i_next[763], pcin_i_next[762], pcin_i_next[761], pcin_i_next[760], pcin_i_next[759], pcin_i_next[758], pcin_i_next[757], pcin_i_next[756], pcin_i_next[755], pcin_i_next[754], pcin_i_next[753], pcin_i_next[752], pcin_i_next[751], pcin_i_next[750], pcin_i_next[749], pcin_i_next[748], pcin_i_next[747], pcin_i_next[746], pcin_i_next[745], pcin_i_next[744], pcin_i_next[743], pcin_i_next[742], pcin_i_next[741], pcin_i_next[740], pcin_i_next[739], pcin_i_next[738], pcin_i_next[737], pcin_i_next[736], pcin_i_next[735], pcin_i_next[734], pcin_i_next[733], pcin_i_next[732], pcin_i_next[731], pcin_i_next[730], pcin_i_next[729], pcin_i_next[728], pcin_i_next[727], pcin_i_next[726], pcin_i_next[725], pcin_i_next[724], pcin_i_next[723], pcin_i_next[722], pcin_i_next[721], pcin_i_next[720], pcin_i_next[719], pcin_i_next[718], pcin_i_next[717], pcin_i_next[716], pcin_i_next[715], pcin_i_next[714], pcin_i_next[713], pcin_i_next[712], pcin_i_next[711], pcin_i_next[710], pcin_i_next[709], pcin_i_next[708], pcin_i_next[707], pcin_i_next[706], pcin_i_next[705], pcin_i_next[704], pcin_i_next[703], pcin_i_next[702], pcin_i_next[701], pcin_i_next[700], pcin_i_next[699], pcin_i_next[698], pcin_i_next[697], pcin_i_next[696], pcin_i_next[695], pcin_i_next[694], pcin_i_next[693], pcin_i_next[692], pcin_i_next[691], pcin_i_next[690], pcin_i_next[689], pcin_i_next[688], pcin_i_next[687], pcin_i_next[686], pcin_i_next[685], pcin_i_next[684], pcin_i_next[683], pcin_i_next[682], pcin_i_next[681], pcin_i_next[680], pcin_i_next[679], pcin_i_next[678], pcin_i_next[677], pcin_i_next[676], pcin_i_next[675], pcin_i_next[674], pcin_i_next[673], pcin_i_next[672], pcin_i_next[671], pcin_i_next[670], pcin_i_next[669], pcin_i_next[668], pcin_i_next[667], pcin_i_next[666], pcin_i_next[665], pcin_i_next[664], pcin_i_next[663], pcin_i_next[662], pcin_i_next[661], pcin_i_next[660], pcin_i_next[659], pcin_i_next[658], pcin_i_next[657], pcin_i_next[656], pcin_i_next[655], pcin_i_next[654], pcin_i_next[653], pcin_i_next[652], pcin_i_next[651], pcin_i_next[650], pcin_i_next[649], pcin_i_next[648], pcin_i_next[647], pcin_i_next[646], pcin_i_next[645], pcin_i_next[644], pcin_i_next[643], pcin_i_next[642], pcin_i_next[641], pcin_i_next[640], pcin_i_next[639], pcin_i_next[638], pcin_i_next[637], pcin_i_next[636], pcin_i_next[635], pcin_i_next[634], pcin_i_next[633], pcin_i_next[632], pcin_i_next[631], pcin_i_next[630], pcin_i_next[629], pcin_i_next[628], pcin_i_next[627], pcin_i_next[626], pcin_i_next[625], pcin_i_next[624], pcin_i_next[623], pcin_i_next[622], pcin_i_next[621], pcin_i_next[620], pcin_i_next[619], pcin_i_next[618], pcin_i_next[617], pcin_i_next[616], pcin_i_next[615], pcin_i_next[614], pcin_i_next[613], pcin_i_next[612], pcin_i_next[611], pcin_i_next[610], pcin_i_next[609], pcin_i_next[608], pcin_i_next[607], pcin_i_next[606], pcin_i_next[605], pcin_i_next[604], pcin_i_next[603], pcin_i_next[602], pcin_i_next[601], pcin_i_next[600], pcin_i_next[599], pcin_i_next[598], pcin_i_next[597], pcin_i_next[596], pcin_i_next[595], pcin_i_next[594], pcin_i_next[593], pcin_i_next[592], pcin_i_next[591], pcin_i_next[590], pcin_i_next[589], pcin_i_next[588], pcin_i_next[587], pcin_i_next[586], pcin_i_next[585], pcin_i_next[584], pcin_i_next[583], pcin_i_next[582], pcin_i_next[581], pcin_i_next[580], pcin_i_next[579], pcin_i_next[578], pcin_i_next[577], pcin_i_next[576], pcin_i_next[575], pcin_i_next[574], pcin_i_next[573], pcin_i_next[572], pcin_i_next[571], pcin_i_next[570], pcin_i_next[569], pcin_i_next[568], pcin_i_next[567], pcin_i_next[566], pcin_i_next[565], pcin_i_next[564], pcin_i_next[563], pcin_i_next[562], pcin_i_next[561], pcin_i_next[560], pcin_i_next[559], pcin_i_next[558], pcin_i_next[557], pcin_i_next[556], pcin_i_next[555], pcin_i_next[554], pcin_i_next[553], pcin_i_next[552], pcin_i_next[551], pcin_i_next[550], pcin_i_next[549], pcin_i_next[548], pcin_i_next[547], pcin_i_next[546], pcin_i_next[545], pcin_i_next[544], pcin_i_next[543], pcin_i_next[542], pcin_i_next[541], pcin_i_next[540], pcin_i_next[539], pcin_i_next[538], pcin_i_next[537], pcin_i_next[536], pcin_i_next[535], pcin_i_next[534], pcin_i_next[533], pcin_i_next[532], pcin_i_next[531], pcin_i_next[530], pcin_i_next[529], pcin_i_next[528], pcin_i_next[527], pcin_i_next[526], pcin_i_next[525], pcin_i_next[524], pcin_i_next[523], pcin_i_next[522], pcin_i_next[521], pcin_i_next[520], pcin_i_next[519], pcin_i_next[518], pcin_i_next[517], pcin_i_next[516], pcin_i_next[515], pcin_i_next[514], pcin_i_next[513], pcin_i_next[512], pcin_i_next[511], pcin_i_next[510], pcin_i_next[509], pcin_i_next[508], pcin_i_next[507], pcin_i_next[506], pcin_i_next[505], pcin_i_next[504], pcin_i_next[503], pcin_i_next[502], pcin_i_next[501], pcin_i_next[500], pcin_i_next[499], pcin_i_next[498], pcin_i_next[497], pcin_i_next[496], pcin_i_next[495], pcin_i_next[494], pcin_i_next[493], pcin_i_next[492], pcin_i_next[491], pcin_i_next[490], pcin_i_next[489], pcin_i_next[488], pcin_i_next[487], pcin_i_next[486], pcin_i_next[485], pcin_i_next[484], pcin_i_next[483], pcin_i_next[482], pcin_i_next[481], pcin_i_next[480], pcin_i_next[479], pcin_i_next[478], pcin_i_next[477], pcin_i_next[476], pcin_i_next[475], pcin_i_next[474], pcin_i_next[473], pcin_i_next[472], pcin_i_next[471], pcin_i_next[470], pcin_i_next[469], pcin_i_next[468], pcin_i_next[467], pcin_i_next[466], pcin_i_next[465], pcin_i_next[464], pcin_i_next[463], pcin_i_next[462], pcin_i_next[461], pcin_i_next[460], pcin_i_next[459], pcin_i_next[458], pcin_i_next[457], pcin_i_next[456], pcin_i_next[455], pcin_i_next[454], pcin_i_next[453], pcin_i_next[452], pcin_i_next[451], pcin_i_next[450], pcin_i_next[449], pcin_i_next[448], pcin_i_next[447], pcin_i_next[446], pcin_i_next[445], pcin_i_next[444], pcin_i_next[443], pcin_i_next[442], pcin_i_next[441], pcin_i_next[440], pcin_i_next[439], pcin_i_next[438], pcin_i_next[437], pcin_i_next[436], pcin_i_next[435], pcin_i_next[434], pcin_i_next[433], pcin_i_next[432], pcin_i_next[431], pcin_i_next[430], pcin_i_next[429], pcin_i_next[428], pcin_i_next[427], pcin_i_next[426], pcin_i_next[425], pcin_i_next[424], pcin_i_next[423], pcin_i_next[422], pcin_i_next[421], pcin_i_next[420], pcin_i_next[419], pcin_i_next[418], pcin_i_next[417], pcin_i_next[416], pcin_i_next[415], pcin_i_next[414], pcin_i_next[413], pcin_i_next[412], pcin_i_next[411], pcin_i_next[410], pcin_i_next[409], pcin_i_next[408], pcin_i_next[407], pcin_i_next[406], pcin_i_next[405], pcin_i_next[404], pcin_i_next[403], pcin_i_next[402], pcin_i_next[401], pcin_i_next[400], pcin_i_next[399], pcin_i_next[398], pcin_i_next[397], pcin_i_next[396], pcin_i_next[395], pcin_i_next[394], pcin_i_next[393], pcin_i_next[392], pcin_i_next[391], pcin_i_next[390], pcin_i_next[389], pcin_i_next[388], pcin_i_next[387], pcin_i_next[386], pcin_i_next[385], pcin_i_next[384], pcin_i_next[383], pcin_i_next[382], pcin_i_next[381], pcin_i_next[380], pcin_i_next[379], pcin_i_next[378], pcin_i_next[377], pcin_i_next[376], pcin_i_next[375], pcin_i_next[374], pcin_i_next[373], pcin_i_next[372], pcin_i_next[371], pcin_i_next[370], pcin_i_next[369], pcin_i_next[368], pcin_i_next[367], pcin_i_next[366], pcin_i_next[365], pcin_i_next[364], pcin_i_next[363], pcin_i_next[362], pcin_i_next[361], pcin_i_next[360], pcin_i_next[359], pcin_i_next[358], pcin_i_next[357], pcin_i_next[356], pcin_i_next[355], pcin_i_next[354], pcin_i_next[353], pcin_i_next[352], pcin_i_next[351], pcin_i_next[350], pcin_i_next[349], pcin_i_next[348], pcin_i_next[347], pcin_i_next[346], pcin_i_next[345], pcin_i_next[344], pcin_i_next[343], pcin_i_next[342], pcin_i_next[341], pcin_i_next[340], pcin_i_next[339], pcin_i_next[338], pcin_i_next[337], pcin_i_next[336], pcin_i_next[335], pcin_i_next[334], pcin_i_next[333], pcin_i_next[332], pcin_i_next[331], pcin_i_next[330], pcin_i_next[329], pcin_i_next[328], pcin_i_next[327], pcin_i_next[326], pcin_i_next[325], pcin_i_next[324], pcin_i_next[323], pcin_i_next[322], pcin_i_next[321], pcin_i_next[320], pcin_i_next[319], pcin_i_next[318], pcin_i_next[317], pcin_i_next[316], pcin_i_next[315], pcin_i_next[314], pcin_i_next[313], pcin_i_next[312], pcin_i_next[311], pcin_i_next[310], pcin_i_next[309], pcin_i_next[308], pcin_i_next[307], pcin_i_next[306], pcin_i_next[305], pcin_i_next[304], pcin_i_next[303], pcin_i_next[302], pcin_i_next[301], pcin_i_next[300], pcin_i_next[299], pcin_i_next[298], pcin_i_next[297], pcin_i_next[296], pcin_i_next[295], pcin_i_next[294], pcin_i_next[293], pcin_i_next[292], pcin_i_next[291], pcin_i_next[290], pcin_i_next[289], pcin_i_next[288], pcin_i_next[287], pcin_i_next[286], pcin_i_next[285], pcin_i_next[284], pcin_i_next[283], pcin_i_next[282], pcin_i_next[281], pcin_i_next[280], pcin_i_next[279], pcin_i_next[278], pcin_i_next[277], pcin_i_next[276], pcin_i_next[275], pcin_i_next[274], pcin_i_next[273], pcin_i_next[272], pcin_i_next[271], pcin_i_next[270], pcin_i_next[269], pcin_i_next[268], pcin_i_next[267], pcin_i_next[266], pcin_i_next[265], pcin_i_next[264], pcin_i_next[263], pcin_i_next[262], pcin_i_next[261], pcin_i_next[260], pcin_i_next[259], pcin_i_next[258], pcin_i_next[257], pcin_i_next[256], pcin_i_next[255], pcin_i_next[254], pcin_i_next[253], pcin_i_next[252], pcin_i_next[251], pcin_i_next[250], pcin_i_next[249], pcin_i_next[248], pcin_i_next[247], pcin_i_next[246], pcin_i_next[245], pcin_i_next[244], pcin_i_next[243], pcin_i_next[242], pcin_i_next[241], pcin_i_next[240], pcin_i_next[239], pcin_i_next[238], pcin_i_next[237], pcin_i_next[236], pcin_i_next[235], pcin_i_next[234], pcin_i_next[233], pcin_i_next[232], pcin_i_next[231], pcin_i_next[230], pcin_i_next[229], pcin_i_next[228], pcin_i_next[227], pcin_i_next[226], pcin_i_next[225], pcin_i_next[224], pcin_i_next[223], pcin_i_next[222], pcin_i_next[221], pcin_i_next[220], pcin_i_next[219], pcin_i_next[218], pcin_i_next[217], pcin_i_next[216], pcin_i_next[215], pcin_i_next[214], pcin_i_next[213], pcin_i_next[212], pcin_i_next[211], pcin_i_next[210], pcin_i_next[209], pcin_i_next[208], pcin_i_next[207], pcin_i_next[206], pcin_i_next[205], pcin_i_next[204], pcin_i_next[203], pcin_i_next[202], pcin_i_next[201], pcin_i_next[200], pcin_i_next[199], pcin_i_next[198], pcin_i_next[197], pcin_i_next[196], pcin_i_next[195], pcin_i_next[194], pcin_i_next[193], pcin_i_next[192], pcin_i_next[191], pcin_i_next[190], pcin_i_next[189], pcin_i_next[188], pcin_i_next[187], pcin_i_next[186], pcin_i_next[185], pcin_i_next[184], pcin_i_next[183], pcin_i_next[182], pcin_i_next[181], pcin_i_next[180], pcin_i_next[179], pcin_i_next[178], pcin_i_next[177], pcin_i_next[176], pcin_i_next[175], pcin_i_next[174], pcin_i_next[173], pcin_i_next[172], pcin_i_next[171], pcin_i_next[170], pcin_i_next[169], pcin_i_next[168], pcin_i_next[167], pcin_i_next[166], pcin_i_next[165], pcin_i_next[164], pcin_i_next[163], pcin_i_next[162], pcin_i_next[161], pcin_i_next[160], pcin_i_next[159], pcin_i_next[158], pcin_i_next[157], pcin_i_next[156], pcin_i_next[155], pcin_i_next[154], pcin_i_next[153], pcin_i_next[152], pcin_i_next[151], pcin_i_next[150], pcin_i_next[149], pcin_i_next[148], pcin_i_next[147], pcin_i_next[146], pcin_i_next[145], pcin_i_next[144], pcin_i_next[143], pcin_i_next[142], pcin_i_next[141], pcin_i_next[140], pcin_i_next[139], pcin_i_next[138], pcin_i_next[137], pcin_i_next[136], pcin_i_next[135], pcin_i_next[134], pcin_i_next[133], pcin_i_next[132], pcin_i_next[131], pcin_i_next[130], pcin_i_next[129], pcin_i_next[128], pcin_i_next[127], pcin_i_next[126], pcin_i_next[125], pcin_i_next[124], pcin_i_next[123], pcin_i_next[122], pcin_i_next[121], pcin_i_next[120], pcin_i_next[119], pcin_i_next[118], pcin_i_next[117], pcin_i_next[116], pcin_i_next[115], pcin_i_next[114], pcin_i_next[113], pcin_i_next[112], pcin_i_next[111], pcin_i_next[110], pcin_i_next[109], pcin_i_next[108], pcin_i_next[107], pcin_i_next[106], pcin_i_next[105], pcin_i_next[104], pcin_i_next[103], pcin_i_next[102], pcin_i_next[101], pcin_i_next[100], pcin_i_next[99], pcin_i_next[98], pcin_i_next[97], pcin_i_next[96], pcin_i_next[95], pcin_i_next[94], pcin_i_next[93], pcin_i_next[92], pcin_i_next[91], pcin_i_next[90], pcin_i_next[89], pcin_i_next[88], pcin_i_next[87], pcin_i_next[86], pcin_i_next[85], pcin_i_next[84], pcin_i_next[83], pcin_i_next[82], pcin_i_next[81], pcin_i_next[80], pcin_i_next[79], pcin_i_next[78], pcin_i_next[77], pcin_i_next[76], pcin_i_next[75], pcin_i_next[74], pcin_i_next[73], pcin_i_next[72], pcin_i_next[71], pcin_i_next[70], pcin_i_next[69], pcin_i_next[68], pcin_i_next[67], pcin_i_next[66], pcin_i_next[65], pcin_i_next[64], pcin_i_next[63], pcin_i_next[62], pcin_i_next[61], pcin_i_next[60], pcin_i_next[59], pcin_i_next[58], pcin_i_next[57], pcin_i_next[56], pcin_i_next[55], pcin_i_next[54], pcin_i_next[53], pcin_i_next[52], pcin_i_next[51], pcin_i_next[50], pcin_i_next[49], pcin_i_next[48], pcin_i_next[47], pcin_i_next[46], pcin_i_next[45], pcin_i_next[44], pcin_i_next[43], pcin_i_next[42], pcin_i_next[41], pcin_i_next[40], pcin_i_next[39], pcin_i_next[38], pcin_i_next[37], pcin_i_next[36], pcin_i_next[35], pcin_i_next[34], pcin_i_next[33], pcin_i_next[32], pcin_i_next[31], pcin_i_next[30], pcin_i_next[29], pcin_i_next[28], pcin_i_next[27], pcin_i_next[26], pcin_i_next[25], pcin_i_next[24], pcin_i_next[23], pcin_i_next[22], pcin_i_next[21], pcin_i_next[20], pcin_i_next[19], pcin_i_next[18], pcin_i_next[17], pcin_i_next[16], pcin_i_next[15], pcin_i_next[14], pcin_i_next[13], pcin_i_next[12], pcin_i_next[11], pcin_i_next[10], pcin_i_next[9], pcin_i_next[8], pcin_i_next[7], pcin_i_next[6], pcin_i_next[5], pcin_i_next[4], pcin_i_next[3], pcin_i_next[2], pcin_i_next[1], pcin_i_next[0]};
    end else begin
        assign pcin_native_i_next = i_next;
    end endgenerate
    wire [260:0] pcin_native_pc__land_er;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__land_er
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_pc__land_er;
        always @(posedge ck) pcin_pc__land_er <= pc__land_er[0:0];
        (* keep = 1, face_keep = 1 *) reg [260:259] pcin_pc__land_er_259;
        always @(posedge ck) pcin_pc__land_er_259 <= pc__land_er[260:259];
        assign pcin_native_pc__land_er = {pcin_pc__land_er_259[260], pcin_pc__land_er_259[259], pc__land_er[258], pc__land_er[257], pc__land_er[256], pc__land_er[255], pc__land_er[254], pc__land_er[253], pc__land_er[252], pc__land_er[251], pc__land_er[250], pc__land_er[249], pc__land_er[248], pc__land_er[247], pc__land_er[246], pc__land_er[245], pc__land_er[244], pc__land_er[243], pc__land_er[242], pc__land_er[241], pc__land_er[240], pc__land_er[239], pc__land_er[238], pc__land_er[237], pc__land_er[236], pc__land_er[235], pc__land_er[234], pc__land_er[233], pc__land_er[232], pc__land_er[231], pc__land_er[230], pc__land_er[229], pc__land_er[228], pc__land_er[227], pc__land_er[226], pc__land_er[225], pc__land_er[224], pc__land_er[223], pc__land_er[222], pc__land_er[221], pc__land_er[220], pc__land_er[219], pc__land_er[218], pc__land_er[217], pc__land_er[216], pc__land_er[215], pc__land_er[214], pc__land_er[213], pc__land_er[212], pc__land_er[211], pc__land_er[210], pc__land_er[209], pc__land_er[208], pc__land_er[207], pc__land_er[206], pc__land_er[205], pc__land_er[204], pc__land_er[203], pc__land_er[202], pc__land_er[201], pc__land_er[200], pc__land_er[199], pc__land_er[198], pc__land_er[197], pc__land_er[196], pc__land_er[195], pc__land_er[194], pc__land_er[193], pc__land_er[192], pc__land_er[191], pc__land_er[190], pc__land_er[189], pc__land_er[188], pc__land_er[187], pc__land_er[186], pc__land_er[185], pc__land_er[184], pc__land_er[183], pc__land_er[182], pc__land_er[181], pc__land_er[180], pc__land_er[179], pc__land_er[178], pc__land_er[177], pc__land_er[176], pc__land_er[175], pc__land_er[174], pc__land_er[173], pc__land_er[172], pc__land_er[171], pc__land_er[170], pc__land_er[169], pc__land_er[168], pc__land_er[167], pc__land_er[166], pc__land_er[165], pc__land_er[164], pc__land_er[163], pc__land_er[162], pc__land_er[161], pc__land_er[160], pc__land_er[159], pc__land_er[158], pc__land_er[157], pc__land_er[156], pc__land_er[155], pc__land_er[154], pc__land_er[153], pc__land_er[152], pc__land_er[151], pc__land_er[150], pc__land_er[149], pc__land_er[148], pc__land_er[147], pc__land_er[146], pc__land_er[145], pc__land_er[144], pc__land_er[143], pc__land_er[142], pc__land_er[141], pc__land_er[140], pc__land_er[139], pc__land_er[138], pc__land_er[137], pc__land_er[136], pc__land_er[135], pc__land_er[134], pc__land_er[133], pc__land_er[132], pc__land_er[131], pc__land_er[130], pc__land_er[129], pc__land_er[128], pc__land_er[127], pc__land_er[126], pc__land_er[125], pc__land_er[124], pc__land_er[123], pc__land_er[122], pc__land_er[121], pc__land_er[120], pc__land_er[119], pc__land_er[118], pc__land_er[117], pc__land_er[116], pc__land_er[115], pc__land_er[114], pc__land_er[113], pc__land_er[112], pc__land_er[111], pc__land_er[110], pc__land_er[109], pc__land_er[108], pc__land_er[107], pc__land_er[106], pc__land_er[105], pc__land_er[104], pc__land_er[103], pc__land_er[102], pc__land_er[101], pc__land_er[100], pc__land_er[99], pc__land_er[98], pc__land_er[97], pc__land_er[96], pc__land_er[95], pc__land_er[94], pc__land_er[93], pc__land_er[92], pc__land_er[91], pc__land_er[90], pc__land_er[89], pc__land_er[88], pc__land_er[87], pc__land_er[86], pc__land_er[85], pc__land_er[84], pc__land_er[83], pc__land_er[82], pc__land_er[81], pc__land_er[80], pc__land_er[79], pc__land_er[78], pc__land_er[77], pc__land_er[76], pc__land_er[75], pc__land_er[74], pc__land_er[73], pc__land_er[72], pc__land_er[71], pc__land_er[70], pc__land_er[69], pc__land_er[68], pc__land_er[67], pc__land_er[66], pc__land_er[65], pc__land_er[64], pc__land_er[63], pc__land_er[62], pc__land_er[61], pc__land_er[60], pc__land_er[59], pc__land_er[58], pc__land_er[57], pc__land_er[56], pc__land_er[55], pc__land_er[54], pc__land_er[53], pc__land_er[52], pc__land_er[51], pc__land_er[50], pc__land_er[49], pc__land_er[48], pc__land_er[47], pc__land_er[46], pc__land_er[45], pc__land_er[44], pc__land_er[43], pc__land_er[42], pc__land_er[41], pc__land_er[40], pc__land_er[39], pc__land_er[38], pc__land_er[37], pc__land_er[36], pc__land_er[35], pc__land_er[34], pc__land_er[33], pc__land_er[32], pc__land_er[31], pc__land_er[30], pc__land_er[29], pc__land_er[28], pc__land_er[27], pc__land_er[26], pc__land_er[25], pc__land_er[24], pc__land_er[23], pc__land_er[22], pc__land_er[21], pc__land_er[20], pc__land_er[19], pc__land_er[18], pc__land_er[17], pc__land_er[16], pc__land_er[15], pc__land_er[14], pc__land_er[13], pc__land_er[12], pc__land_er[11], pc__land_er[10], pc__land_er[9], pc__land_er[8], pc__land_er[7], pc__land_er[6], pc__land_er[5], pc__land_er[4], pc__land_er[3], pc__land_er[2], pc__land_er[1], pcin_pc__land_er[0]};
    end else begin
        assign pcin_native_pc__land_er = pc__land_er;
    end endgenerate
    wire  pcin_native_rst_n;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_rst_n
        (* keep = 1, face_keep = 1 *) reg  pcin_rst_n;
        always @(posedge ck) pcin_rst_n <= 1'b1;
        assign pcin_native_rst_n = pcin_rst_n;
    end else begin
        assign pcin_native_rst_n = rst_n;
    end endgenerate
    wire [32:0] pcin_native_pc__ki;
    generate if (KVSPC_INPUT_COLLAR) begin : g_pcin_pc__ki
        (* keep = 1, face_keep = 1 *) reg [0:0] pcin_pc__ki;
        always @(posedge ck) pcin_pc__ki <= pc__ki[0:0];
        (* keep = 1, face_keep = 1 *) reg [20:15] pcin_pc__ki_15;
        always @(posedge ck) pcin_pc__ki_15 <= pc__ki[20:15];
        (* keep = 1, face_keep = 1 *) reg [32:31] pcin_pc__ki_31;
        always @(posedge ck) pcin_pc__ki_31 <= pc__ki[32:31];
        assign pcin_native_pc__ki = {pcin_pc__ki_31[32], pcin_pc__ki_31[31], pc__ki[30], pc__ki[29], pc__ki[28], pc__ki[27], pc__ki[26], pc__ki[25], pc__ki[24], pc__ki[23], pc__ki[22], pc__ki[21], pcin_pc__ki_15[20], pcin_pc__ki_15[19], pcin_pc__ki_15[18], pcin_pc__ki_15[17], pcin_pc__ki_15[16], pcin_pc__ki_15[15], pc__ki[14], pc__ki[13], pc__ki[12], pc__ki[11], pc__ki[10], pc__ki[9], pc__ki[8], pc__ki[7], pc__ki[6], pc__ki[5], pc__ki[4], pc__ki[3], pc__ki[2], pc__ki[1], pcin_pc__ki[0]};
    end else begin
        assign pcin_native_pc__ki = pc__ki;
    end endgenerate

    qkd_kv_pc_chain_station_b_p u_actual_chain (
        .ck(ck),
        .rst_n(pcin_native_rst_n),
        .cfg_stack(pcin_native_pc__cfg_stack),
        .di(pcin_native_i_next),
        .dout(coupon_dout),
        .land_es(coupon_land_es),
        .land_er(pcin_native_pc__land_er),
        .wes(coupon_wes),
        .es_context(coupon_es_context),
        .es_expected_valid(coupon_es_expected_valid),
        .es_expected_identity(coupon_es_expected_identity),
        .es_expected_address(coupon_es_expected_address),
        .es_expected_pc(coupon_es_expected_pc),
        .es_expected_stack(coupon_es_expected_stack),
        .emb_issue_v(coupon_emb_issue_v),
        .emb_token(coupon_emb_token),
        .emb_word_index(coupon_emb_word_index),
        .emb_half(coupon_emb_half),
        .emb_scale(coupon_emb_scale),
        .emb_epoch(coupon_emb_epoch),
        .emb_return_slot(coupon_emb_return_slot),
        .capture_slot(coupon_capture_slot),
        .transfer_slot(coupon_transfer_slot),
        .fault(coupon_fault)
    );
endmodule
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
qkd_kvs_pc_h_head_p #(.KVSPC_INPUT_COLLAR(1)) u_native (.ck(ck[0]), .rst_n(rst_n), .hck(ck[0]), .hrst_n(rst_n), .pc__pi('0), .pc__ki('0), .pc__cfg_stack(cfg_stack), .pc__front_hbm_data('0), .pc__return_hbm_data('0), .x__est__0_1('0), .pc__land_er(land_er), .pc__hes('0), .pc__fo(), .pc__er(), .pc__ko(), .pc__po(), .pc__completion_v(), .pc__completion_we(), .pc__land_es(), .pc__her(), .pc__hcompletion_v(), .pc__hcompletion_we(), .i_grp('0), .i_next(di), .o_grp(), .o_next(), .coupon_dout(dout), .coupon_land_es(land_es), .coupon_wes(wes), .coupon_es_context(es_context), .coupon_es_expected_valid(es_expected_valid), .coupon_es_expected_identity(es_expected_identity), .coupon_es_expected_address(es_expected_address), .coupon_es_expected_pc(es_expected_pc), .coupon_es_expected_stack(es_expected_stack), .coupon_emb_issue_v(emb_issue_v), .coupon_emb_token(emb_token), .coupon_emb_word_index(emb_word_index), .coupon_emb_half(emb_half), .coupon_emb_scale(emb_scale), .coupon_emb_epoch(emb_epoch), .coupon_emb_return_slot(emb_return_slot), .coupon_capture_slot(capture_slot), .coupon_transfer_slot(transfer_slot), .coupon_fault(fault));
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
qkd_kvs_pc_h_head_p_badbit #(.KVSPC_INPUT_COLLAR(1)) u_native (.ck(ck[0]), .rst_n(rst_n), .hck(ck[0]), .hrst_n(rst_n), .pc__pi('0), .pc__ki('0), .pc__cfg_stack(cfg_stack), .pc__front_hbm_data('0), .pc__return_hbm_data('0), .x__est__0_1('0), .pc__land_er(land_er), .pc__hes('0), .pc__fo(), .pc__er(), .pc__ko(), .pc__po(), .pc__completion_v(), .pc__completion_we(), .pc__land_es(), .pc__her(), .pc__hcompletion_v(), .pc__hcompletion_we(), .i_grp('0), .i_next(di), .o_grp(), .o_next(), .coupon_dout(dout), .coupon_land_es(land_es), .coupon_wes(wes), .coupon_es_context(es_context), .coupon_es_expected_valid(es_expected_valid), .coupon_es_expected_identity(es_expected_identity), .coupon_es_expected_address(es_expected_address), .coupon_es_expected_pc(es_expected_pc), .coupon_es_expected_stack(es_expected_stack), .coupon_emb_issue_v(emb_issue_v), .coupon_emb_token(emb_token), .coupon_emb_word_index(emb_word_index), .coupon_emb_half(emb_half), .coupon_emb_scale(emb_scale), .coupon_emb_epoch(emb_epoch), .coupon_emb_return_slot(emb_return_slot), .coupon_capture_slot(capture_slot), .coupon_transfer_slot(transfer_slot), .coupon_fault(fault));
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
qkd_kvs_pc_h_head_p_badreset #(.KVSPC_INPUT_COLLAR(1)) u_native (.ck(ck[0]), .rst_n(rst_n), .hck(ck[0]), .hrst_n(rst_n), .pc__pi('0), .pc__ki('0), .pc__cfg_stack(cfg_stack), .pc__front_hbm_data('0), .pc__return_hbm_data('0), .x__est__0_1('0), .pc__land_er(land_er), .pc__hes('0), .pc__fo(), .pc__er(), .pc__ko(), .pc__po(), .pc__completion_v(), .pc__completion_we(), .pc__land_es(), .pc__her(), .pc__hcompletion_v(), .pc__hcompletion_we(), .i_grp('0), .i_next(di), .o_grp(), .o_next(), .coupon_dout(dout), .coupon_land_es(land_es), .coupon_wes(wes), .coupon_es_context(es_context), .coupon_es_expected_valid(es_expected_valid), .coupon_es_expected_identity(es_expected_identity), .coupon_es_expected_address(es_expected_address), .coupon_es_expected_pc(es_expected_pc), .coupon_es_expected_stack(es_expected_stack), .coupon_emb_issue_v(emb_issue_v), .coupon_emb_token(emb_token), .coupon_emb_word_index(emb_word_index), .coupon_emb_half(emb_half), .coupon_emb_scale(emb_scale), .coupon_emb_epoch(emb_epoch), .coupon_emb_return_slot(emb_return_slot), .coupon_capture_slot(capture_slot), .coupon_transfer_slot(transfer_slot), .coupon_fault(fault));
endmodule

`timescale 1ns/1ps
module pc_chain_collar_default (
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
qkd_kvs_pc_h_head_p #(.KVSPC_INPUT_COLLAR(0)) u_native (.ck(ck[0]), .rst_n(rst_n), .hck(ck[0]), .hrst_n(rst_n), .pc__pi('0), .pc__ki('0), .pc__cfg_stack(cfg_stack), .pc__front_hbm_data('0), .pc__return_hbm_data('0), .x__est__0_1('0), .pc__land_er(land_er), .pc__hes('0), .pc__fo(), .pc__er(), .pc__ko(), .pc__po(), .pc__completion_v(), .pc__completion_we(), .pc__land_es(), .pc__her(), .pc__hcompletion_v(), .pc__hcompletion_we(), .i_grp('0), .i_next(di), .o_grp(), .o_next(), .coupon_dout(dout), .coupon_land_es(land_es), .coupon_wes(wes), .coupon_es_context(es_context), .coupon_es_expected_valid(es_expected_valid), .coupon_es_expected_identity(es_expected_identity), .coupon_es_expected_address(es_expected_address), .coupon_es_expected_pc(es_expected_pc), .coupon_es_expected_stack(es_expected_stack), .coupon_emb_issue_v(emb_issue_v), .coupon_emb_token(emb_token), .coupon_emb_word_index(emb_word_index), .coupon_emb_half(emb_half), .coupon_emb_scale(emb_scale), .coupon_emb_epoch(emb_epoch), .coupon_emb_return_slot(emb_return_slot), .coupon_capture_slot(capture_slot), .coupon_transfer_slot(transfer_slot), .coupon_fault(fault));
endmodule
