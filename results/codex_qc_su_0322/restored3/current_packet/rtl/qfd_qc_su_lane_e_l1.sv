// Generated exact grouping of five bind.py leaves; zero added cycles.
`default_nettype none
module qfd_qc_su_lane_e_l1 (input wire clk, input wire rst_n,
    input wire [759:0] c_i, output wire [247:0] c_o);
    wire w_u_exp1_fault;
    wire w_u_exp1_vo;
    wire [31:0] w_u_exp1_y;
    wire [23:0] w_u_head1_crom_addr;
    wire w_u_head1_crom_re;
    wire [23:0] w_u_head1_kv_waddr;
    wire [31:0] w_u_head1_kv_wdata;
    wire w_u_head1_kv_we;
    wire w_u_head1_l_fault;
    wire w_u_head1_l_last;
    wire [31:0] w_u_head1_l_out;
    wire w_u_head1_l_ov;
    wire [23:0] w_u_head1_l_raddr;
    wire [1:0] w_u_head1_l_red;
    wire w_u_head1_l_redsq;
    wire w_u_head1_retire;
    wire w_u_head1_sx_exp_v;
    wire [31:0] w_u_head1_sx_exp_x;
    wire w_u_head1_sx_rcp_v;
    wire [31:0] w_u_head1_sx_rcp_x;
    wire w_u_head1_sx_rsq_v;
    wire [31:0] w_u_head1_sx_rsq_x;
    wire [23:0] w_u_head1_va_addr;
    wire w_u_head1_va_re;
    wire [23:0] w_u_head1_vb_addr;
    wire w_u_head1_vb_re;
    wire [23:0] w_u_head1_vc_addr;
    wire w_u_head1_vc_re;
    wire [23:0] w_u_head1_vm_waddr;
    wire [31:0] w_u_head1_vm_wdata;
    wire w_u_head1_vm_we;
    wire [23:0] w_u_head1_wrom_addr;
    wire w_u_head1_wrom_re;
    wire w_u_lrly1_c_accept;
    wire [2:0] w_u_lrly1_c_ad;
    wire [23:0] w_u_lrly1_c_asi;
    wire w_u_lrly1_c_asrc;
    wire [23:0] w_u_lrly1_c_bsi;
    wire w_u_lrly1_c_bsrc;
    wire [2:0] w_u_lrly1_c_cls;
    wire [63:0] w_u_lrly1_c_crom;
    wire [23:0] w_u_lrly1_c_csi;
    wire w_u_lrly1_c_csrc;
    wire [23:0] w_u_lrly1_c_cura;
    wire [23:0] w_u_lrly1_c_curb;
    wire [23:0] w_u_lrly1_c_curc;
    wire [23:0] w_u_lrly1_c_curd;
    wire [23:0] w_u_lrly1_c_dsi;
    wire [1:0] w_u_lrly1_c_dst;
    wire w_u_lrly1_c_emit0;
    wire [18:0] w_u_lrly1_c_fin_th;
    wire [17:0] w_u_lrly1_c_i;
    wire w_u_lrly1_c_ilast;
    wire [31:0] w_u_lrly1_c_imm1;
    wire [31:0] w_u_lrly1_c_imm2;
    wire [2:0] w_u_lrly1_c_isfu;
    wire w_u_lrly1_c_live;
    wire [1:0] w_u_lrly1_c_ma;
    wire [1:0] w_u_lrly1_c_mb;
    wire w_u_lrly1_c_mc;
    wire w_u_lrly1_c_md;
    wire [1:0] w_u_lrly1_c_red;
    wire w_u_lrly1_c_redsq;
    wire [23:0] w_u_lrly1_c_rrow;
    wire [31:0] w_u_lrly1_c_va;
    wire [31:0] w_u_lrly1_c_vb;
    wire [31:0] w_u_lrly1_c_vc;
    wire [255:0] w_u_lrly1_c_wrom;
    wire [23:0] w_u_lrly1_crom_addr;
    wire w_u_lrly1_crom_re;
    wire w_u_lrly1_h_rst_n;
    wire [23:0] w_u_lrly1_kv_waddr;
    wire [31:0] w_u_lrly1_kv_wdata;
    wire w_u_lrly1_kv_we;
    wire w_u_lrly1_l_fault;
    wire w_u_lrly1_l_last;
    wire [31:0] w_u_lrly1_l_out;
    wire w_u_lrly1_l_ov;
    wire [23:0] w_u_lrly1_l_raddr;
    wire [1:0] w_u_lrly1_l_red;
    wire w_u_lrly1_l_redsq;
    wire w_u_lrly1_retire;
    wire [23:0] w_u_lrly1_va_addr;
    wire w_u_lrly1_va_re;
    wire [23:0] w_u_lrly1_vb_addr;
    wire w_u_lrly1_vb_re;
    wire [23:0] w_u_lrly1_vc_addr;
    wire w_u_lrly1_vc_re;
    wire [23:0] w_u_lrly1_vm_waddr;
    wire [31:0] w_u_lrly1_vm_wdata;
    wire w_u_lrly1_vm_we;
    wire [23:0] w_u_lrly1_wrom_addr;
    wire w_u_lrly1_wrom_re;
    wire w_u_rcp1_fault;
    wire w_u_rcp1_vo;
    wire [31:0] w_u_rcp1_y;
    wire w_u_rsq1_fault;
    wire w_u_rsq1_vo;
    wire [31:0] w_u_rsq1_y;
    wire [765:0] x_su_c_i_q;
    wire [764:0] x_su_c_p1_i_q;
    assign x_su_c_i_q[0] = c_i[0];
    assign x_su_c_i_q[1] = c_i[1];
    assign x_su_c_i_q[2] = c_i[2];
    assign x_su_c_i_q[3] = c_i[3];
    assign x_su_c_i_q[4] = c_i[4];
    assign x_su_c_i_q[5] = c_i[5];
    assign x_su_c_i_q[6] = c_i[6];
    assign x_su_c_i_q[7] = c_i[7];
    assign x_su_c_i_q[8] = c_i[8];
    assign x_su_c_i_q[9] = c_i[9];
    assign x_su_c_i_q[10] = c_i[10];
    assign x_su_c_i_q[11] = c_i[11];
    assign x_su_c_i_q[12] = c_i[12];
    assign x_su_c_i_q[13] = c_i[13];
    assign x_su_c_i_q[14] = c_i[14];
    assign x_su_c_i_q[15] = c_i[15];
    assign x_su_c_i_q[16] = c_i[16];
    assign x_su_c_i_q[17] = c_i[17];
    assign x_su_c_i_q[18] = c_i[18];
    assign x_su_c_i_q[19] = c_i[19];
    assign x_su_c_i_q[20] = c_i[20];
    assign x_su_c_i_q[21] = c_i[21];
    assign x_su_c_i_q[22] = c_i[22];
    assign x_su_c_i_q[23] = c_i[23];
    assign x_su_c_i_q[24] = c_i[24];
    assign x_su_c_i_q[25] = c_i[25];
    assign x_su_c_i_q[26] = c_i[26];
    assign x_su_c_i_q[27] = c_i[27];
    assign x_su_c_i_q[28] = c_i[28];
    assign x_su_c_i_q[29] = c_i[29];
    assign x_su_c_i_q[30] = c_i[30];
    assign x_su_c_i_q[31] = c_i[31];
    assign x_su_c_i_q[32] = c_i[32];
    assign x_su_c_i_q[33] = c_i[33];
    assign x_su_c_i_q[34] = c_i[34];
    assign x_su_c_i_q[35] = c_i[35];
    assign x_su_c_i_q[36] = c_i[36];
    assign x_su_c_i_q[37] = c_i[37];
    assign x_su_c_i_q[38] = c_i[38];
    assign x_su_c_i_q[39] = c_i[39];
    assign x_su_c_i_q[40] = c_i[40];
    assign x_su_c_i_q[41] = c_i[41];
    assign x_su_c_i_q[42] = c_i[42];
    assign x_su_c_i_q[43] = c_i[43];
    assign x_su_c_i_q[44] = c_i[44];
    assign x_su_c_i_q[45] = c_i[45];
    assign x_su_c_i_q[46] = c_i[46];
    assign x_su_c_i_q[47] = c_i[47];
    assign x_su_c_i_q[48] = c_i[48];
    assign x_su_c_i_q[49] = c_i[49];
    assign x_su_c_i_q[50] = c_i[50];
    assign x_su_c_i_q[51] = c_i[51];
    assign x_su_c_i_q[52] = c_i[52];
    assign x_su_c_i_q[53] = c_i[53];
    assign x_su_c_i_q[54] = c_i[54];
    assign x_su_c_i_q[55] = c_i[55];
    assign x_su_c_i_q[56] = c_i[56];
    assign x_su_c_i_q[57] = c_i[57];
    assign x_su_c_i_q[58] = c_i[58];
    assign x_su_c_i_q[59] = c_i[59];
    assign x_su_c_i_q[60] = c_i[60];
    assign x_su_c_i_q[61] = c_i[61];
    assign x_su_c_i_q[62] = c_i[62];
    assign x_su_c_i_q[63] = c_i[63];
    assign x_su_c_i_q[64] = c_i[64];
    assign x_su_c_i_q[65] = c_i[65];
    assign x_su_c_i_q[66] = c_i[66];
    assign x_su_c_i_q[67] = c_i[67];
    assign x_su_c_i_q[68] = c_i[68];
    assign x_su_c_i_q[69] = c_i[69];
    assign x_su_c_i_q[70] = c_i[70];
    assign x_su_c_i_q[71] = c_i[71];
    assign x_su_c_i_q[72] = c_i[72];
    assign x_su_c_i_q[73] = c_i[73];
    assign x_su_c_i_q[74] = c_i[74];
    assign x_su_c_i_q[75] = c_i[75];
    assign x_su_c_i_q[76] = c_i[76];
    assign x_su_c_i_q[77] = c_i[77];
    assign x_su_c_i_q[78] = c_i[78];
    assign x_su_c_i_q[79] = c_i[79];
    assign x_su_c_i_q[80] = c_i[80];
    assign x_su_c_i_q[81] = c_i[81];
    assign x_su_c_i_q[82] = c_i[82];
    assign x_su_c_i_q[83] = c_i[83];
    assign x_su_c_i_q[84] = c_i[84];
    assign x_su_c_i_q[85] = c_i[85];
    assign x_su_c_i_q[86] = c_i[86];
    assign x_su_c_i_q[87] = c_i[87];
    assign x_su_c_i_q[88] = c_i[88];
    assign x_su_c_i_q[89] = c_i[89];
    assign x_su_c_i_q[90] = c_i[90];
    assign x_su_c_i_q[91] = c_i[91];
    assign x_su_c_i_q[92] = c_i[92];
    assign x_su_c_i_q[93] = c_i[93];
    assign x_su_c_i_q[94] = c_i[94];
    assign x_su_c_i_q[95] = c_i[95];
    assign x_su_c_i_q[96] = c_i[96];
    assign x_su_c_i_q[97] = c_i[97];
    assign x_su_c_i_q[98] = c_i[98];
    assign x_su_c_i_q[99] = c_i[99];
    assign x_su_c_i_q[100] = c_i[100];
    assign x_su_c_i_q[101] = c_i[101];
    assign x_su_c_i_q[102] = c_i[102];
    assign x_su_c_i_q[103] = c_i[103];
    assign x_su_c_i_q[104] = c_i[104];
    assign x_su_c_i_q[105] = c_i[105];
    assign x_su_c_i_q[106] = c_i[106];
    assign x_su_c_i_q[107] = c_i[107];
    assign x_su_c_i_q[108] = c_i[108];
    assign x_su_c_i_q[109] = c_i[109];
    assign x_su_c_i_q[110] = c_i[110];
    assign x_su_c_i_q[111] = c_i[111];
    assign x_su_c_i_q[112] = c_i[112];
    assign x_su_c_i_q[113] = c_i[113];
    assign x_su_c_i_q[114] = c_i[114];
    assign x_su_c_i_q[115] = c_i[115];
    assign x_su_c_i_q[116] = c_i[116];
    assign x_su_c_i_q[117] = c_i[117];
    assign x_su_c_i_q[118] = c_i[118];
    assign x_su_c_i_q[119] = c_i[119];
    assign x_su_c_i_q[120] = c_i[120];
    assign x_su_c_i_q[121] = c_i[121];
    assign x_su_c_i_q[122] = c_i[122];
    assign x_su_c_i_q[123] = c_i[123];
    assign x_su_c_i_q[124] = c_i[124];
    assign x_su_c_i_q[125] = c_i[125];
    assign x_su_c_i_q[126] = c_i[126];
    assign x_su_c_i_q[127] = c_i[127];
    assign x_su_c_i_q[128] = c_i[128];
    assign x_su_c_i_q[129] = c_i[129];
    assign x_su_c_i_q[130] = c_i[130];
    assign x_su_c_i_q[131] = c_i[131];
    assign x_su_c_i_q[132] = c_i[132];
    assign x_su_c_i_q[133] = c_i[133];
    assign x_su_c_i_q[134] = c_i[134];
    assign x_su_c_i_q[135] = c_i[135];
    assign x_su_c_i_q[136] = c_i[136];
    assign x_su_c_i_q[137] = c_i[137];
    assign x_su_c_i_q[138] = c_i[138];
    assign x_su_c_i_q[139] = c_i[139];
    assign x_su_c_i_q[140] = c_i[140];
    assign x_su_c_i_q[141] = c_i[141];
    assign x_su_c_i_q[142] = c_i[142];
    assign x_su_c_i_q[143] = c_i[143];
    assign x_su_c_i_q[144] = c_i[144];
    assign x_su_c_i_q[145] = c_i[145];
    assign x_su_c_i_q[146] = c_i[146];
    assign x_su_c_i_q[147] = c_i[147];
    assign x_su_c_i_q[148] = c_i[148];
    assign x_su_c_i_q[149] = c_i[149];
    assign x_su_c_i_q[150] = c_i[150];
    assign x_su_c_i_q[151] = c_i[151];
    assign x_su_c_i_q[152] = c_i[152];
    assign x_su_c_i_q[153] = c_i[153];
    assign x_su_c_i_q[154] = c_i[154];
    assign x_su_c_i_q[155] = c_i[155];
    assign x_su_c_i_q[156] = c_i[156];
    assign x_su_c_i_q[157] = c_i[157];
    assign x_su_c_i_q[158] = c_i[158];
    assign x_su_c_i_q[159] = c_i[159];
    assign x_su_c_i_q[160] = c_i[160];
    assign x_su_c_i_q[161] = c_i[161];
    assign x_su_c_i_q[162] = c_i[162];
    assign x_su_c_i_q[163] = c_i[163];
    assign x_su_c_i_q[164] = c_i[164];
    assign x_su_c_i_q[165] = c_i[165];
    assign x_su_c_i_q[166] = c_i[166];
    assign x_su_c_i_q[167] = c_i[167];
    assign x_su_c_i_q[168] = c_i[168];
    assign x_su_c_i_q[169] = c_i[169];
    assign x_su_c_i_q[170] = c_i[170];
    assign x_su_c_i_q[171] = c_i[171];
    assign x_su_c_i_q[172] = c_i[172];
    assign x_su_c_i_q[173] = c_i[173];
    assign x_su_c_i_q[174] = c_i[174];
    assign x_su_c_i_q[175] = c_i[175];
    assign x_su_c_i_q[176] = c_i[176];
    assign x_su_c_i_q[177] = c_i[177];
    assign x_su_c_i_q[178] = c_i[178];
    assign x_su_c_i_q[179] = c_i[179];
    assign x_su_c_i_q[180] = c_i[180];
    assign x_su_c_i_q[181] = c_i[181];
    assign x_su_c_i_q[182] = c_i[182];
    assign x_su_c_i_q[183] = c_i[183];
    assign x_su_c_i_q[184] = c_i[184];
    assign x_su_c_i_q[185] = c_i[185];
    assign x_su_c_i_q[186] = c_i[186];
    assign x_su_c_i_q[187] = c_i[187];
    assign x_su_c_i_q[188] = c_i[188];
    assign x_su_c_i_q[189] = c_i[189];
    assign x_su_c_i_q[190] = c_i[190];
    assign x_su_c_i_q[191] = c_i[191];
    assign x_su_c_i_q[192] = c_i[192];
    assign x_su_c_i_q[193] = c_i[193];
    assign x_su_c_i_q[194] = c_i[194];
    assign x_su_c_i_q[195] = c_i[195];
    assign x_su_c_i_q[196] = c_i[196];
    assign x_su_c_i_q[197] = c_i[197];
    assign x_su_c_i_q[198] = c_i[198];
    assign x_su_c_i_q[199] = c_i[199];
    assign x_su_c_i_q[200] = c_i[200];
    assign x_su_c_i_q[201] = c_i[201];
    assign x_su_c_i_q[202] = c_i[202];
    assign x_su_c_i_q[203] = c_i[203];
    assign x_su_c_i_q[204] = c_i[204];
    assign x_su_c_i_q[205] = c_i[205];
    assign x_su_c_i_q[206] = c_i[206];
    assign x_su_c_i_q[207] = c_i[207];
    assign x_su_c_i_q[208] = c_i[208];
    assign x_su_c_i_q[209] = c_i[209];
    assign x_su_c_i_q[210] = c_i[210];
    assign x_su_c_i_q[211] = c_i[211];
    assign x_su_c_i_q[212] = c_i[212];
    assign x_su_c_i_q[213] = c_i[213];
    assign x_su_c_i_q[214] = c_i[214];
    assign x_su_c_i_q[215] = c_i[215];
    assign x_su_c_i_q[216] = c_i[216];
    assign x_su_c_i_q[217] = c_i[217];
    assign x_su_c_i_q[218] = c_i[218];
    assign x_su_c_i_q[219] = c_i[219];
    assign x_su_c_i_q[220] = c_i[220];
    assign x_su_c_i_q[221] = c_i[221];
    assign x_su_c_i_q[222] = c_i[222];
    assign x_su_c_i_q[223] = c_i[223];
    assign x_su_c_i_q[224] = c_i[224];
    assign x_su_c_i_q[225] = c_i[225];
    assign x_su_c_i_q[226] = c_i[226];
    assign x_su_c_i_q[227] = c_i[227];
    assign x_su_c_i_q[228] = c_i[228];
    assign x_su_c_i_q[229] = c_i[229];
    assign x_su_c_i_q[230] = c_i[230];
    assign x_su_c_i_q[231] = c_i[231];
    assign x_su_c_i_q[232] = c_i[232];
    assign x_su_c_i_q[233] = c_i[233];
    assign x_su_c_i_q[234] = c_i[234];
    assign x_su_c_i_q[235] = c_i[235];
    assign x_su_c_i_q[236] = c_i[236];
    assign x_su_c_i_q[237] = c_i[237];
    assign x_su_c_i_q[238] = c_i[238];
    assign x_su_c_i_q[239] = c_i[239];
    assign x_su_c_i_q[240] = c_i[240];
    assign x_su_c_i_q[241] = c_i[241];
    assign x_su_c_i_q[242] = c_i[242];
    assign x_su_c_i_q[243] = c_i[243];
    assign x_su_c_i_q[244] = c_i[244];
    assign x_su_c_i_q[245] = c_i[245];
    assign x_su_c_i_q[246] = c_i[246];
    assign x_su_c_i_q[247] = c_i[247];
    assign x_su_c_i_q[248] = c_i[248];
    assign x_su_c_i_q[249] = c_i[249];
    assign x_su_c_i_q[250] = c_i[250];
    assign x_su_c_i_q[251] = c_i[251];
    assign x_su_c_i_q[252] = c_i[252];
    assign x_su_c_i_q[253] = c_i[253];
    assign x_su_c_i_q[254] = c_i[254];
    assign x_su_c_i_q[255] = c_i[255];
    assign x_su_c_i_q[256] = c_i[256];
    assign x_su_c_i_q[257] = c_i[257];
    assign x_su_c_i_q[258] = c_i[258];
    assign x_su_c_i_q[259] = c_i[259];
    assign x_su_c_i_q[260] = c_i[260];
    assign x_su_c_i_q[261] = c_i[261];
    assign x_su_c_i_q[262] = c_i[262];
    assign x_su_c_i_q[263] = c_i[263];
    assign x_su_c_i_q[264] = c_i[264];
    assign x_su_c_i_q[265] = c_i[265];
    assign x_su_c_i_q[266] = c_i[266];
    assign x_su_c_i_q[267] = c_i[267];
    assign x_su_c_i_q[268] = c_i[268];
    assign x_su_c_i_q[269] = c_i[269];
    assign x_su_c_i_q[270] = c_i[270];
    assign x_su_c_i_q[271] = c_i[271];
    assign x_su_c_i_q[272] = c_i[272];
    assign x_su_c_i_q[273] = c_i[273];
    assign x_su_c_i_q[274] = c_i[274];
    assign x_su_c_i_q[275] = c_i[275];
    assign x_su_c_i_q[276] = c_i[276];
    assign x_su_c_i_q[277] = c_i[277];
    assign x_su_c_i_q[278] = c_i[278];
    assign x_su_c_i_q[279] = c_i[279];
    assign x_su_c_i_q[280] = c_i[280];
    assign x_su_c_i_q[281] = c_i[281];
    assign x_su_c_i_q[282] = c_i[282];
    assign x_su_c_i_q[283] = c_i[283];
    assign x_su_c_i_q[284] = c_i[284];
    assign x_su_c_i_q[285] = c_i[285];
    assign x_su_c_i_q[286] = c_i[286];
    assign x_su_c_i_q[287] = c_i[287];
    assign x_su_c_i_q[288] = c_i[288];
    assign x_su_c_i_q[289] = c_i[289];
    assign x_su_c_i_q[290] = c_i[290];
    assign x_su_c_i_q[291] = c_i[291];
    assign x_su_c_i_q[292] = c_i[292];
    assign x_su_c_i_q[293] = c_i[293];
    assign x_su_c_i_q[294] = c_i[294];
    assign x_su_c_i_q[295] = c_i[295];
    assign x_su_c_i_q[296] = c_i[296];
    assign x_su_c_i_q[297] = c_i[297];
    assign x_su_c_i_q[298] = c_i[298];
    assign x_su_c_i_q[299] = c_i[299];
    assign x_su_c_i_q[300] = c_i[300];
    assign x_su_c_i_q[301] = c_i[301];
    assign x_su_c_i_q[302] = c_i[302];
    assign x_su_c_i_q[303] = c_i[303];
    assign x_su_c_i_q[304] = c_i[304];
    assign x_su_c_i_q[305] = c_i[305];
    assign x_su_c_i_q[306] = c_i[306];
    assign x_su_c_i_q[307] = c_i[307];
    assign x_su_c_i_q[308] = c_i[308];
    assign x_su_c_i_q[309] = c_i[309];
    assign x_su_c_i_q[310] = c_i[310];
    assign x_su_c_i_q[311] = c_i[311];
    assign x_su_c_i_q[312] = c_i[312];
    assign x_su_c_i_q[313] = c_i[313];
    assign x_su_c_i_q[314] = c_i[314];
    assign x_su_c_i_q[315] = c_i[315];
    assign x_su_c_i_q[316] = c_i[316];
    assign x_su_c_i_q[317] = c_i[317];
    assign x_su_c_i_q[318] = c_i[318];
    assign x_su_c_i_q[319] = c_i[319];
    assign x_su_c_i_q[320] = c_i[320];
    assign x_su_c_i_q[321] = c_i[321];
    assign x_su_c_i_q[322] = c_i[322];
    assign x_su_c_i_q[323] = c_i[323];
    assign x_su_c_i_q[324] = c_i[324];
    assign x_su_c_i_q[325] = c_i[325];
    assign x_su_c_i_q[326] = c_i[326];
    assign x_su_c_i_q[327] = c_i[327];
    assign x_su_c_i_q[328] = c_i[328];
    assign x_su_c_i_q[329] = c_i[329];
    assign x_su_c_i_q[330] = c_i[330];
    assign x_su_c_i_q[331] = c_i[331];
    assign x_su_c_i_q[332] = c_i[332];
    assign x_su_c_i_q[333] = c_i[333];
    assign x_su_c_i_q[334] = c_i[334];
    assign x_su_c_i_q[335] = c_i[335];
    assign x_su_c_i_q[336] = c_i[336];
    assign x_su_c_i_q[337] = c_i[337];
    assign x_su_c_i_q[338] = c_i[338];
    assign x_su_c_i_q[339] = c_i[339];
    assign x_su_c_i_q[340] = c_i[340];
    assign x_su_c_i_q[341] = c_i[341];
    assign x_su_c_i_q[342] = c_i[342];
    assign x_su_c_i_q[343] = c_i[343];
    assign x_su_c_i_q[344] = c_i[344];
    assign x_su_c_i_q[345] = c_i[345];
    assign x_su_c_i_q[346] = c_i[346];
    assign x_su_c_i_q[347] = c_i[347];
    assign x_su_c_i_q[348] = c_i[348];
    assign x_su_c_i_q[349] = c_i[349];
    assign x_su_c_i_q[350] = c_i[350];
    assign x_su_c_i_q[351] = c_i[351];
    assign x_su_c_i_q[352] = c_i[352];
    assign x_su_c_i_q[353] = c_i[353];
    assign x_su_c_i_q[354] = c_i[354];
    assign x_su_c_i_q[355] = c_i[355];
    assign x_su_c_i_q[356] = c_i[356];
    assign x_su_c_i_q[357] = c_i[357];
    assign x_su_c_i_q[358] = c_i[358];
    assign x_su_c_i_q[359] = c_i[359];
    assign x_su_c_i_q[360] = c_i[360];
    assign x_su_c_i_q[361] = c_i[361];
    assign x_su_c_i_q[362] = c_i[362];
    assign x_su_c_i_q[363] = c_i[363];
    assign x_su_c_i_q[364] = c_i[364];
    assign x_su_c_i_q[365] = c_i[365];
    assign x_su_c_i_q[366] = c_i[366];
    assign x_su_c_i_q[367] = c_i[367];
    assign x_su_c_i_q[368] = c_i[368];
    assign x_su_c_i_q[369] = c_i[369];
    assign x_su_c_i_q[370] = c_i[370];
    assign x_su_c_i_q[371] = c_i[371];
    assign x_su_c_i_q[372] = c_i[372];
    assign x_su_c_i_q[373] = c_i[373];
    assign x_su_c_i_q[374] = c_i[374];
    assign x_su_c_i_q[375] = c_i[375];
    assign x_su_c_i_q[376] = c_i[376];
    assign x_su_c_i_q[377] = c_i[377];
    assign x_su_c_i_q[378] = c_i[378];
    assign x_su_c_i_q[379] = c_i[379];
    assign x_su_c_i_q[380] = c_i[380];
    assign x_su_c_i_q[381] = c_i[381];
    assign x_su_c_i_q[382] = c_i[382];
    assign x_su_c_i_q[383] = c_i[383];
    assign x_su_c_i_q[384] = c_i[384];
    assign x_su_c_i_q[385] = c_i[385];
    assign x_su_c_i_q[386] = c_i[386];
    assign x_su_c_i_q[387] = c_i[387];
    assign x_su_c_i_q[388] = c_i[388];
    assign x_su_c_i_q[389] = c_i[389];
    assign x_su_c_i_q[390] = c_i[390];
    assign x_su_c_i_q[391] = c_i[391];
    assign x_su_c_i_q[392] = c_i[392];
    assign x_su_c_i_q[393] = c_i[393];
    assign x_su_c_i_q[394] = c_i[394];
    assign x_su_c_i_q[395] = c_i[395];
    assign x_su_c_i_q[396] = c_i[396];
    assign x_su_c_i_q[397] = c_i[397];
    assign x_su_c_i_q[398] = c_i[398];
    assign x_su_c_i_q[399] = c_i[399];
    assign x_su_c_i_q[400] = c_i[400];
    assign x_su_c_i_q[401] = c_i[401];
    assign x_su_c_i_q[402] = c_i[402];
    assign x_su_c_i_q[403] = c_i[403];
    assign x_su_c_i_q[404] = c_i[404];
    assign x_su_c_i_q[405] = c_i[405];
    assign x_su_c_i_q[406] = c_i[406];
    assign x_su_c_i_q[407] = c_i[407];
    assign x_su_c_i_q[408] = c_i[408];
    assign x_su_c_i_q[409] = c_i[409];
    assign x_su_c_i_q[410] = c_i[410];
    assign x_su_c_i_q[411] = c_i[411];
    assign x_su_c_i_q[412] = c_i[412];
    assign x_su_c_i_q[413] = c_i[413];
    assign x_su_c_i_q[414] = c_i[414];
    assign x_su_c_i_q[415] = c_i[415];
    assign x_su_c_i_q[416] = c_i[416];
    assign x_su_c_i_q[417] = c_i[417];
    assign x_su_c_i_q[418] = c_i[418];
    assign x_su_c_i_q[419] = c_i[419];
    assign x_su_c_i_q[420] = c_i[420];
    assign x_su_c_i_q[421] = c_i[421];
    assign x_su_c_i_q[422] = c_i[422];
    assign x_su_c_i_q[423] = c_i[423];
    assign x_su_c_i_q[424] = c_i[424];
    assign x_su_c_i_q[425] = c_i[425];
    assign x_su_c_i_q[426] = c_i[426];
    assign x_su_c_i_q[427] = c_i[427];
    assign x_su_c_i_q[428] = c_i[428];
    assign x_su_c_i_q[429] = c_i[429];
    assign x_su_c_i_q[430] = c_i[430];
    assign x_su_c_i_q[431] = c_i[431];
    assign x_su_c_i_q[432] = c_i[432];
    assign x_su_c_i_q[433] = c_i[433];
    assign x_su_c_i_q[434] = c_i[434];
    assign x_su_c_i_q[435] = c_i[435];
    assign x_su_c_i_q[436] = c_i[436];
    assign x_su_c_i_q[437] = c_i[437];
    assign x_su_c_i_q[438] = c_i[438];
    assign x_su_c_i_q[439] = c_i[439];
    assign x_su_c_i_q[440] = c_i[440];
    assign x_su_c_i_q[441] = c_i[441];
    assign x_su_c_i_q[442] = c_i[442];
    assign x_su_c_i_q[443] = c_i[443];
    assign x_su_c_i_q[444] = c_i[444];
    assign x_su_c_i_q[445] = c_i[445];
    assign x_su_c_i_q[446] = c_i[446];
    assign x_su_c_i_q[447] = c_i[447];
    assign x_su_c_i_q[448] = c_i[448];
    assign x_su_c_i_q[449] = c_i[449];
    assign x_su_c_i_q[450] = c_i[450];
    assign x_su_c_i_q[451] = c_i[451];
    assign x_su_c_i_q[452] = c_i[452];
    assign x_su_c_i_q[453] = c_i[453];
    assign x_su_c_i_q[454] = c_i[454];
    assign x_su_c_i_q[455] = c_i[455];
    assign x_su_c_i_q[456] = c_i[456];
    assign x_su_c_i_q[457] = c_i[457];
    assign x_su_c_i_q[458] = c_i[458];
    assign x_su_c_i_q[459] = c_i[459];
    assign x_su_c_i_q[460] = c_i[460];
    assign x_su_c_i_q[461] = c_i[461];
    assign x_su_c_i_q[462] = c_i[462];
    assign x_su_c_i_q[463] = c_i[463];
    assign x_su_c_i_q[464] = c_i[464];
    assign x_su_c_i_q[465] = c_i[465];
    assign x_su_c_i_q[466] = c_i[466];
    assign x_su_c_i_q[467] = c_i[467];
    assign x_su_c_i_q[468] = c_i[468];
    assign x_su_c_i_q[469] = c_i[469];
    assign x_su_c_i_q[470] = c_i[470];
    assign x_su_c_i_q[471] = c_i[471];
    assign x_su_c_i_q[472] = c_i[472];
    assign x_su_c_i_q[473] = c_i[473];
    assign x_su_c_i_q[474] = c_i[474];
    assign x_su_c_i_q[475] = c_i[475];
    assign x_su_c_i_q[476] = c_i[476];
    assign x_su_c_i_q[477] = c_i[477];
    assign x_su_c_i_q[478] = c_i[478];
    assign x_su_c_i_q[479] = c_i[479];
    assign x_su_c_i_q[480] = c_i[480];
    assign x_su_c_i_q[481] = c_i[481];
    assign x_su_c_i_q[482] = c_i[482];
    assign x_su_c_i_q[483] = c_i[483];
    assign x_su_c_i_q[484] = c_i[484];
    assign x_su_c_i_q[485] = c_i[485];
    assign x_su_c_i_q[486] = c_i[486];
    assign x_su_c_i_q[487] = c_i[487];
    assign x_su_c_i_q[488] = c_i[488];
    assign x_su_c_i_q[489] = c_i[489];
    assign x_su_c_i_q[490] = c_i[490];
    assign x_su_c_i_q[491] = c_i[491];
    assign x_su_c_i_q[492] = c_i[492];
    assign x_su_c_i_q[493] = c_i[493];
    assign x_su_c_i_q[494] = c_i[494];
    assign x_su_c_i_q[495] = c_i[495];
    assign x_su_c_i_q[496] = c_i[496];
    assign x_su_c_i_q[497] = c_i[497];
    assign x_su_c_i_q[498] = c_i[498];
    assign x_su_c_i_q[499] = c_i[499];
    assign x_su_c_i_q[500] = c_i[500];
    assign x_su_c_i_q[501] = c_i[501];
    assign x_su_c_i_q[502] = c_i[502];
    assign x_su_c_i_q[504] = c_i[503];
    assign x_su_c_i_q[603] = c_i[504];
    assign x_su_c_i_q[604] = c_i[505];
    assign x_su_c_i_q[605] = c_i[506];
    assign x_su_c_i_q[606] = c_i[507];
    assign x_su_c_i_q[607] = c_i[508];
    assign x_su_c_i_q[608] = c_i[509];
    assign x_su_c_i_q[609] = c_i[510];
    assign x_su_c_i_q[610] = c_i[511];
    assign x_su_c_i_q[611] = c_i[512];
    assign x_su_c_i_q[612] = c_i[513];
    assign x_su_c_i_q[613] = c_i[514];
    assign x_su_c_i_q[614] = c_i[515];
    assign x_su_c_i_q[615] = c_i[516];
    assign x_su_c_i_q[616] = c_i[517];
    assign x_su_c_i_q[617] = c_i[518];
    assign x_su_c_i_q[618] = c_i[519];
    assign x_su_c_i_q[619] = c_i[520];
    assign x_su_c_i_q[620] = c_i[521];
    assign x_su_c_i_q[621] = c_i[522];
    assign x_su_c_i_q[622] = c_i[523];
    assign x_su_c_i_q[623] = c_i[524];
    assign x_su_c_i_q[624] = c_i[525];
    assign x_su_c_i_q[625] = c_i[526];
    assign x_su_c_i_q[626] = c_i[527];
    assign x_su_c_i_q[627] = c_i[528];
    assign x_su_c_i_q[628] = c_i[529];
    assign x_su_c_i_q[629] = c_i[530];
    assign x_su_c_i_q[630] = c_i[531];
    assign x_su_c_i_q[631] = c_i[532];
    assign x_su_c_i_q[632] = c_i[533];
    assign x_su_c_i_q[633] = c_i[534];
    assign x_su_c_i_q[634] = c_i[535];
    assign x_su_c_i_q[635] = c_i[536];
    assign x_su_c_i_q[636] = c_i[537];
    assign x_su_c_i_q[637] = c_i[538];
    assign x_su_c_i_q[638] = c_i[539];
    assign x_su_c_i_q[639] = c_i[540];
    assign x_su_c_i_q[640] = c_i[541];
    assign x_su_c_i_q[641] = c_i[542];
    assign x_su_c_i_q[642] = c_i[543];
    assign x_su_c_i_q[643] = c_i[544];
    assign x_su_c_i_q[644] = c_i[545];
    assign x_su_c_i_q[645] = c_i[546];
    assign x_su_c_i_q[646] = c_i[547];
    assign x_su_c_i_q[647] = c_i[548];
    assign x_su_c_i_q[648] = c_i[549];
    assign x_su_c_i_q[649] = c_i[550];
    assign x_su_c_i_q[650] = c_i[551];
    assign x_su_c_i_q[651] = c_i[552];
    assign x_su_c_i_q[652] = c_i[553];
    assign x_su_c_i_q[653] = c_i[554];
    assign x_su_c_i_q[654] = c_i[555];
    assign x_su_c_i_q[655] = c_i[556];
    assign x_su_c_i_q[656] = c_i[557];
    assign x_su_c_i_q[657] = c_i[558];
    assign x_su_c_i_q[658] = c_i[559];
    assign x_su_c_i_q[659] = c_i[560];
    assign x_su_c_i_q[660] = c_i[561];
    assign x_su_c_i_q[661] = c_i[562];
    assign x_su_c_i_q[662] = c_i[563];
    assign x_su_c_i_q[663] = c_i[564];
    assign x_su_c_i_q[664] = c_i[565];
    assign x_su_c_i_q[665] = c_i[566];
    assign x_su_c_i_q[666] = c_i[567];
    assign x_su_c_i_q[667] = c_i[568];
    assign x_su_c_i_q[668] = c_i[569];
    assign x_su_c_i_q[669] = c_i[570];
    assign x_su_c_i_q[670] = c_i[571];
    assign x_su_c_i_q[671] = c_i[572];
    assign x_su_c_i_q[672] = c_i[573];
    assign x_su_c_i_q[673] = c_i[574];
    assign x_su_c_i_q[674] = c_i[575];
    assign x_su_c_i_q[675] = c_i[576];
    assign x_su_c_i_q[676] = c_i[577];
    assign x_su_c_i_q[677] = c_i[578];
    assign x_su_c_i_q[678] = c_i[579];
    assign x_su_c_i_q[679] = c_i[580];
    assign x_su_c_i_q[680] = c_i[581];
    assign x_su_c_i_q[681] = c_i[582];
    assign x_su_c_i_q[682] = c_i[583];
    assign x_su_c_i_q[683] = c_i[584];
    assign x_su_c_i_q[684] = c_i[585];
    assign x_su_c_i_q[685] = c_i[586];
    assign x_su_c_i_q[686] = c_i[587];
    assign x_su_c_i_q[687] = c_i[588];
    assign x_su_c_i_q[688] = c_i[589];
    assign x_su_c_i_q[689] = c_i[590];
    assign x_su_c_i_q[690] = c_i[591];
    assign x_su_c_i_q[691] = c_i[592];
    assign x_su_c_i_q[692] = c_i[593];
    assign x_su_c_i_q[693] = c_i[594];
    assign x_su_c_i_q[694] = c_i[595];
    assign x_su_c_i_q[695] = c_i[596];
    assign x_su_c_i_q[696] = c_i[597];
    assign x_su_c_i_q[697] = c_i[598];
    assign x_su_c_i_q[698] = c_i[599];
    assign x_su_c_p1_i_q[157] = c_i[600];
    assign x_su_c_p1_i_q[158] = c_i[601];
    assign x_su_c_p1_i_q[159] = c_i[602];
    assign x_su_c_p1_i_q[160] = c_i[603];
    assign x_su_c_p1_i_q[161] = c_i[604];
    assign x_su_c_p1_i_q[162] = c_i[605];
    assign x_su_c_p1_i_q[163] = c_i[606];
    assign x_su_c_p1_i_q[164] = c_i[607];
    assign x_su_c_p1_i_q[165] = c_i[608];
    assign x_su_c_p1_i_q[166] = c_i[609];
    assign x_su_c_p1_i_q[167] = c_i[610];
    assign x_su_c_p1_i_q[168] = c_i[611];
    assign x_su_c_p1_i_q[169] = c_i[612];
    assign x_su_c_p1_i_q[170] = c_i[613];
    assign x_su_c_p1_i_q[171] = c_i[614];
    assign x_su_c_p1_i_q[172] = c_i[615];
    assign x_su_c_p1_i_q[173] = c_i[616];
    assign x_su_c_p1_i_q[174] = c_i[617];
    assign x_su_c_p1_i_q[175] = c_i[618];
    assign x_su_c_p1_i_q[176] = c_i[619];
    assign x_su_c_p1_i_q[177] = c_i[620];
    assign x_su_c_p1_i_q[178] = c_i[621];
    assign x_su_c_p1_i_q[179] = c_i[622];
    assign x_su_c_p1_i_q[180] = c_i[623];
    assign x_su_c_p1_i_q[181] = c_i[624];
    assign x_su_c_p1_i_q[182] = c_i[625];
    assign x_su_c_p1_i_q[183] = c_i[626];
    assign x_su_c_p1_i_q[184] = c_i[627];
    assign x_su_c_p1_i_q[185] = c_i[628];
    assign x_su_c_p1_i_q[186] = c_i[629];
    assign x_su_c_p1_i_q[187] = c_i[630];
    assign x_su_c_p1_i_q[188] = c_i[631];
    assign x_su_c_p1_i_q[285] = c_i[632];
    assign x_su_c_p1_i_q[286] = c_i[633];
    assign x_su_c_p1_i_q[287] = c_i[634];
    assign x_su_c_p1_i_q[288] = c_i[635];
    assign x_su_c_p1_i_q[289] = c_i[636];
    assign x_su_c_p1_i_q[290] = c_i[637];
    assign x_su_c_p1_i_q[291] = c_i[638];
    assign x_su_c_p1_i_q[292] = c_i[639];
    assign x_su_c_p1_i_q[293] = c_i[640];
    assign x_su_c_p1_i_q[294] = c_i[641];
    assign x_su_c_p1_i_q[295] = c_i[642];
    assign x_su_c_p1_i_q[296] = c_i[643];
    assign x_su_c_p1_i_q[297] = c_i[644];
    assign x_su_c_p1_i_q[298] = c_i[645];
    assign x_su_c_p1_i_q[299] = c_i[646];
    assign x_su_c_p1_i_q[300] = c_i[647];
    assign x_su_c_p1_i_q[301] = c_i[648];
    assign x_su_c_p1_i_q[302] = c_i[649];
    assign x_su_c_p1_i_q[303] = c_i[650];
    assign x_su_c_p1_i_q[304] = c_i[651];
    assign x_su_c_p1_i_q[305] = c_i[652];
    assign x_su_c_p1_i_q[306] = c_i[653];
    assign x_su_c_p1_i_q[307] = c_i[654];
    assign x_su_c_p1_i_q[308] = c_i[655];
    assign x_su_c_p1_i_q[309] = c_i[656];
    assign x_su_c_p1_i_q[310] = c_i[657];
    assign x_su_c_p1_i_q[311] = c_i[658];
    assign x_su_c_p1_i_q[312] = c_i[659];
    assign x_su_c_p1_i_q[313] = c_i[660];
    assign x_su_c_p1_i_q[314] = c_i[661];
    assign x_su_c_p1_i_q[315] = c_i[662];
    assign x_su_c_p1_i_q[316] = c_i[663];
    assign x_su_c_p1_i_q[413] = c_i[664];
    assign x_su_c_p1_i_q[414] = c_i[665];
    assign x_su_c_p1_i_q[415] = c_i[666];
    assign x_su_c_p1_i_q[416] = c_i[667];
    assign x_su_c_p1_i_q[417] = c_i[668];
    assign x_su_c_p1_i_q[418] = c_i[669];
    assign x_su_c_p1_i_q[419] = c_i[670];
    assign x_su_c_p1_i_q[420] = c_i[671];
    assign x_su_c_p1_i_q[421] = c_i[672];
    assign x_su_c_p1_i_q[422] = c_i[673];
    assign x_su_c_p1_i_q[423] = c_i[674];
    assign x_su_c_p1_i_q[424] = c_i[675];
    assign x_su_c_p1_i_q[425] = c_i[676];
    assign x_su_c_p1_i_q[426] = c_i[677];
    assign x_su_c_p1_i_q[427] = c_i[678];
    assign x_su_c_p1_i_q[428] = c_i[679];
    assign x_su_c_p1_i_q[429] = c_i[680];
    assign x_su_c_p1_i_q[430] = c_i[681];
    assign x_su_c_p1_i_q[431] = c_i[682];
    assign x_su_c_p1_i_q[432] = c_i[683];
    assign x_su_c_p1_i_q[433] = c_i[684];
    assign x_su_c_p1_i_q[434] = c_i[685];
    assign x_su_c_p1_i_q[435] = c_i[686];
    assign x_su_c_p1_i_q[436] = c_i[687];
    assign x_su_c_p1_i_q[437] = c_i[688];
    assign x_su_c_p1_i_q[438] = c_i[689];
    assign x_su_c_p1_i_q[439] = c_i[690];
    assign x_su_c_p1_i_q[440] = c_i[691];
    assign x_su_c_p1_i_q[441] = c_i[692];
    assign x_su_c_p1_i_q[442] = c_i[693];
    assign x_su_c_p1_i_q[443] = c_i[694];
    assign x_su_c_p1_i_q[444] = c_i[695];
    assign x_su_c_p1_i_q[541] = c_i[696];
    assign x_su_c_p1_i_q[542] = c_i[697];
    assign x_su_c_p1_i_q[543] = c_i[698];
    assign x_su_c_p1_i_q[544] = c_i[699];
    assign x_su_c_p1_i_q[545] = c_i[700];
    assign x_su_c_p1_i_q[546] = c_i[701];
    assign x_su_c_p1_i_q[547] = c_i[702];
    assign x_su_c_p1_i_q[548] = c_i[703];
    assign x_su_c_p1_i_q[549] = c_i[704];
    assign x_su_c_p1_i_q[550] = c_i[705];
    assign x_su_c_p1_i_q[551] = c_i[706];
    assign x_su_c_p1_i_q[552] = c_i[707];
    assign x_su_c_p1_i_q[553] = c_i[708];
    assign x_su_c_p1_i_q[554] = c_i[709];
    assign x_su_c_p1_i_q[555] = c_i[710];
    assign x_su_c_p1_i_q[556] = c_i[711];
    assign x_su_c_p1_i_q[557] = c_i[712];
    assign x_su_c_p1_i_q[558] = c_i[713];
    assign x_su_c_p1_i_q[559] = c_i[714];
    assign x_su_c_p1_i_q[560] = c_i[715];
    assign x_su_c_p1_i_q[561] = c_i[716];
    assign x_su_c_p1_i_q[562] = c_i[717];
    assign x_su_c_p1_i_q[563] = c_i[718];
    assign x_su_c_p1_i_q[564] = c_i[719];
    assign x_su_c_p1_i_q[565] = c_i[720];
    assign x_su_c_p1_i_q[566] = c_i[721];
    assign x_su_c_p1_i_q[567] = c_i[722];
    assign x_su_c_p1_i_q[568] = c_i[723];
    assign x_su_c_p1_i_q[569] = c_i[724];
    assign x_su_c_p1_i_q[570] = c_i[725];
    assign x_su_c_p1_i_q[571] = c_i[726];
    assign x_su_c_p1_i_q[572] = c_i[727];
    assign x_su_c_p1_i_q[669] = c_i[728];
    assign x_su_c_p1_i_q[670] = c_i[729];
    assign x_su_c_p1_i_q[671] = c_i[730];
    assign x_su_c_p1_i_q[672] = c_i[731];
    assign x_su_c_p1_i_q[673] = c_i[732];
    assign x_su_c_p1_i_q[674] = c_i[733];
    assign x_su_c_p1_i_q[675] = c_i[734];
    assign x_su_c_p1_i_q[676] = c_i[735];
    assign x_su_c_p1_i_q[677] = c_i[736];
    assign x_su_c_p1_i_q[678] = c_i[737];
    assign x_su_c_p1_i_q[679] = c_i[738];
    assign x_su_c_p1_i_q[680] = c_i[739];
    assign x_su_c_p1_i_q[681] = c_i[740];
    assign x_su_c_p1_i_q[682] = c_i[741];
    assign x_su_c_p1_i_q[683] = c_i[742];
    assign x_su_c_p1_i_q[684] = c_i[743];
    assign x_su_c_p1_i_q[685] = c_i[744];
    assign x_su_c_p1_i_q[686] = c_i[745];
    assign x_su_c_p1_i_q[687] = c_i[746];
    assign x_su_c_p1_i_q[688] = c_i[747];
    assign x_su_c_p1_i_q[689] = c_i[748];
    assign x_su_c_p1_i_q[690] = c_i[749];
    assign x_su_c_p1_i_q[691] = c_i[750];
    assign x_su_c_p1_i_q[692] = c_i[751];
    assign x_su_c_p1_i_q[693] = c_i[752];
    assign x_su_c_p1_i_q[694] = c_i[753];
    assign x_su_c_p1_i_q[695] = c_i[754];
    assign x_su_c_p1_i_q[696] = c_i[755];
    assign x_su_c_p1_i_q[697] = c_i[756];
    assign x_su_c_p1_i_q[698] = c_i[757];
    assign x_su_c_p1_i_q[699] = c_i[758];
    assign x_su_c_p1_i_q[700] = c_i[759];
    assign c_o[0] = w_u_lrly1_crom_addr[0];
    assign c_o[1] = w_u_lrly1_crom_addr[1];
    assign c_o[2] = w_u_lrly1_crom_addr[2];
    assign c_o[3] = w_u_lrly1_crom_addr[3];
    assign c_o[4] = w_u_lrly1_crom_addr[4];
    assign c_o[5] = w_u_lrly1_crom_addr[5];
    assign c_o[6] = w_u_lrly1_crom_addr[6];
    assign c_o[7] = w_u_lrly1_crom_addr[7];
    assign c_o[8] = w_u_lrly1_crom_addr[8];
    assign c_o[9] = w_u_lrly1_crom_addr[9];
    assign c_o[10] = w_u_lrly1_crom_addr[10];
    assign c_o[11] = w_u_lrly1_crom_addr[11];
    assign c_o[12] = w_u_lrly1_crom_addr[12];
    assign c_o[13] = w_u_lrly1_crom_addr[13];
    assign c_o[14] = w_u_lrly1_crom_addr[14];
    assign c_o[15] = w_u_lrly1_crom_addr[15];
    assign c_o[16] = w_u_lrly1_crom_addr[16];
    assign c_o[17] = w_u_lrly1_crom_addr[17];
    assign c_o[18] = w_u_lrly1_crom_addr[18];
    assign c_o[19] = w_u_lrly1_crom_addr[19];
    assign c_o[20] = w_u_lrly1_crom_addr[20];
    assign c_o[21] = w_u_lrly1_crom_addr[21];
    assign c_o[22] = w_u_lrly1_crom_addr[22];
    assign c_o[23] = w_u_lrly1_crom_addr[23];
    assign c_o[24] = w_u_lrly1_crom_re;
    assign c_o[25] = w_u_lrly1_kv_waddr[0];
    assign c_o[26] = w_u_lrly1_kv_waddr[1];
    assign c_o[27] = w_u_lrly1_kv_waddr[2];
    assign c_o[28] = w_u_lrly1_kv_waddr[3];
    assign c_o[29] = w_u_lrly1_kv_waddr[4];
    assign c_o[30] = w_u_lrly1_kv_waddr[5];
    assign c_o[31] = w_u_lrly1_kv_waddr[6];
    assign c_o[32] = w_u_lrly1_kv_waddr[7];
    assign c_o[33] = w_u_lrly1_kv_waddr[8];
    assign c_o[34] = w_u_lrly1_kv_waddr[9];
    assign c_o[35] = w_u_lrly1_kv_waddr[10];
    assign c_o[36] = w_u_lrly1_kv_waddr[11];
    assign c_o[37] = w_u_lrly1_kv_waddr[12];
    assign c_o[38] = w_u_lrly1_kv_waddr[13];
    assign c_o[39] = w_u_lrly1_kv_waddr[14];
    assign c_o[40] = w_u_lrly1_kv_waddr[15];
    assign c_o[41] = w_u_lrly1_kv_waddr[16];
    assign c_o[42] = w_u_lrly1_kv_waddr[17];
    assign c_o[43] = w_u_lrly1_kv_waddr[18];
    assign c_o[44] = w_u_lrly1_kv_waddr[19];
    assign c_o[45] = w_u_lrly1_kv_waddr[20];
    assign c_o[46] = w_u_lrly1_kv_waddr[21];
    assign c_o[47] = w_u_lrly1_kv_waddr[22];
    assign c_o[48] = w_u_lrly1_kv_waddr[23];
    assign c_o[49] = w_u_lrly1_kv_wdata[0];
    assign c_o[50] = w_u_lrly1_kv_wdata[1];
    assign c_o[51] = w_u_lrly1_kv_wdata[2];
    assign c_o[52] = w_u_lrly1_kv_wdata[3];
    assign c_o[53] = w_u_lrly1_kv_wdata[4];
    assign c_o[54] = w_u_lrly1_kv_wdata[5];
    assign c_o[55] = w_u_lrly1_kv_wdata[6];
    assign c_o[56] = w_u_lrly1_kv_wdata[7];
    assign c_o[57] = w_u_lrly1_kv_wdata[8];
    assign c_o[58] = w_u_lrly1_kv_wdata[9];
    assign c_o[59] = w_u_lrly1_kv_wdata[10];
    assign c_o[60] = w_u_lrly1_kv_wdata[11];
    assign c_o[61] = w_u_lrly1_kv_wdata[12];
    assign c_o[62] = w_u_lrly1_kv_wdata[13];
    assign c_o[63] = w_u_lrly1_kv_wdata[14];
    assign c_o[64] = w_u_lrly1_kv_wdata[15];
    assign c_o[65] = w_u_lrly1_kv_wdata[16];
    assign c_o[66] = w_u_lrly1_kv_wdata[17];
    assign c_o[67] = w_u_lrly1_kv_wdata[18];
    assign c_o[68] = w_u_lrly1_kv_wdata[19];
    assign c_o[69] = w_u_lrly1_kv_wdata[20];
    assign c_o[70] = w_u_lrly1_kv_wdata[21];
    assign c_o[71] = w_u_lrly1_kv_wdata[22];
    assign c_o[72] = w_u_lrly1_kv_wdata[23];
    assign c_o[73] = w_u_lrly1_kv_wdata[24];
    assign c_o[74] = w_u_lrly1_kv_wdata[25];
    assign c_o[75] = w_u_lrly1_kv_wdata[26];
    assign c_o[76] = w_u_lrly1_kv_wdata[27];
    assign c_o[77] = w_u_lrly1_kv_wdata[28];
    assign c_o[78] = w_u_lrly1_kv_wdata[29];
    assign c_o[79] = w_u_lrly1_kv_wdata[30];
    assign c_o[80] = w_u_lrly1_kv_wdata[31];
    assign c_o[81] = w_u_lrly1_kv_we;
    assign c_o[82] = w_u_lrly1_l_fault;
    assign c_o[83] = w_u_lrly1_l_out[0];
    assign c_o[84] = w_u_lrly1_l_out[1];
    assign c_o[85] = w_u_lrly1_l_out[2];
    assign c_o[86] = w_u_lrly1_l_out[3];
    assign c_o[87] = w_u_lrly1_l_out[4];
    assign c_o[88] = w_u_lrly1_l_out[5];
    assign c_o[89] = w_u_lrly1_l_out[6];
    assign c_o[90] = w_u_lrly1_l_out[7];
    assign c_o[91] = w_u_lrly1_l_out[8];
    assign c_o[92] = w_u_lrly1_l_out[9];
    assign c_o[93] = w_u_lrly1_l_out[10];
    assign c_o[94] = w_u_lrly1_l_out[11];
    assign c_o[95] = w_u_lrly1_l_out[12];
    assign c_o[96] = w_u_lrly1_l_out[13];
    assign c_o[97] = w_u_lrly1_l_out[14];
    assign c_o[98] = w_u_lrly1_l_out[15];
    assign c_o[99] = w_u_lrly1_l_out[16];
    assign c_o[100] = w_u_lrly1_l_out[17];
    assign c_o[101] = w_u_lrly1_l_out[18];
    assign c_o[102] = w_u_lrly1_l_out[19];
    assign c_o[103] = w_u_lrly1_l_out[20];
    assign c_o[104] = w_u_lrly1_l_out[21];
    assign c_o[105] = w_u_lrly1_l_out[22];
    assign c_o[106] = w_u_lrly1_l_out[23];
    assign c_o[107] = w_u_lrly1_l_out[24];
    assign c_o[108] = w_u_lrly1_l_out[25];
    assign c_o[109] = w_u_lrly1_l_out[26];
    assign c_o[110] = w_u_lrly1_l_out[27];
    assign c_o[111] = w_u_lrly1_l_out[28];
    assign c_o[112] = w_u_lrly1_l_out[29];
    assign c_o[113] = w_u_lrly1_l_out[30];
    assign c_o[114] = w_u_lrly1_l_out[31];
    assign c_o[115] = w_u_lrly1_l_ov;
    assign c_o[116] = w_u_lrly1_va_addr[0];
    assign c_o[117] = w_u_lrly1_va_addr[1];
    assign c_o[118] = w_u_lrly1_va_addr[2];
    assign c_o[119] = w_u_lrly1_va_addr[3];
    assign c_o[120] = w_u_lrly1_va_addr[4];
    assign c_o[121] = w_u_lrly1_va_addr[5];
    assign c_o[122] = w_u_lrly1_va_addr[6];
    assign c_o[123] = w_u_lrly1_va_addr[7];
    assign c_o[124] = w_u_lrly1_va_addr[8];
    assign c_o[125] = w_u_lrly1_va_addr[9];
    assign c_o[126] = w_u_lrly1_va_addr[10];
    assign c_o[127] = w_u_lrly1_va_addr[11];
    assign c_o[128] = w_u_lrly1_va_addr[12];
    assign c_o[129] = w_u_lrly1_va_addr[13];
    assign c_o[130] = w_u_lrly1_va_addr[14];
    assign c_o[131] = w_u_lrly1_va_addr[15];
    assign c_o[132] = w_u_lrly1_va_addr[16];
    assign c_o[133] = w_u_lrly1_va_addr[17];
    assign c_o[134] = w_u_lrly1_va_addr[18];
    assign c_o[135] = w_u_lrly1_va_addr[19];
    assign c_o[136] = w_u_lrly1_va_addr[20];
    assign c_o[137] = w_u_lrly1_va_addr[21];
    assign c_o[138] = w_u_lrly1_va_addr[22];
    assign c_o[139] = w_u_lrly1_va_addr[23];
    assign c_o[140] = w_u_lrly1_va_re;
    assign c_o[141] = w_u_lrly1_vb_addr[0];
    assign c_o[142] = w_u_lrly1_vb_addr[1];
    assign c_o[143] = w_u_lrly1_vb_addr[2];
    assign c_o[144] = w_u_lrly1_vb_addr[3];
    assign c_o[145] = w_u_lrly1_vb_addr[4];
    assign c_o[146] = w_u_lrly1_vb_addr[5];
    assign c_o[147] = w_u_lrly1_vb_addr[6];
    assign c_o[148] = w_u_lrly1_vb_addr[7];
    assign c_o[149] = w_u_lrly1_vb_addr[8];
    assign c_o[150] = w_u_lrly1_vb_addr[9];
    assign c_o[151] = w_u_lrly1_vb_addr[10];
    assign c_o[152] = w_u_lrly1_vb_addr[11];
    assign c_o[153] = w_u_lrly1_vb_addr[12];
    assign c_o[154] = w_u_lrly1_vb_addr[13];
    assign c_o[155] = w_u_lrly1_vb_addr[14];
    assign c_o[156] = w_u_lrly1_vb_addr[15];
    assign c_o[157] = w_u_lrly1_vb_addr[16];
    assign c_o[158] = w_u_lrly1_vb_addr[17];
    assign c_o[159] = w_u_lrly1_vb_addr[18];
    assign c_o[160] = w_u_lrly1_vb_addr[19];
    assign c_o[161] = w_u_lrly1_vb_addr[20];
    assign c_o[162] = w_u_lrly1_vb_addr[21];
    assign c_o[163] = w_u_lrly1_vb_addr[22];
    assign c_o[164] = w_u_lrly1_vb_addr[23];
    assign c_o[165] = w_u_lrly1_vb_re;
    assign c_o[166] = w_u_lrly1_vc_addr[0];
    assign c_o[167] = w_u_lrly1_vc_addr[1];
    assign c_o[168] = w_u_lrly1_vc_addr[2];
    assign c_o[169] = w_u_lrly1_vc_addr[3];
    assign c_o[170] = w_u_lrly1_vc_addr[4];
    assign c_o[171] = w_u_lrly1_vc_addr[5];
    assign c_o[172] = w_u_lrly1_vc_addr[6];
    assign c_o[173] = w_u_lrly1_vc_addr[7];
    assign c_o[174] = w_u_lrly1_vc_addr[8];
    assign c_o[175] = w_u_lrly1_vc_addr[9];
    assign c_o[176] = w_u_lrly1_vc_addr[10];
    assign c_o[177] = w_u_lrly1_vc_addr[11];
    assign c_o[178] = w_u_lrly1_vc_addr[12];
    assign c_o[179] = w_u_lrly1_vc_addr[13];
    assign c_o[180] = w_u_lrly1_vc_addr[14];
    assign c_o[181] = w_u_lrly1_vc_addr[15];
    assign c_o[182] = w_u_lrly1_vc_addr[16];
    assign c_o[183] = w_u_lrly1_vc_addr[17];
    assign c_o[184] = w_u_lrly1_vc_addr[18];
    assign c_o[185] = w_u_lrly1_vc_addr[19];
    assign c_o[186] = w_u_lrly1_vc_addr[20];
    assign c_o[187] = w_u_lrly1_vc_addr[21];
    assign c_o[188] = w_u_lrly1_vc_addr[22];
    assign c_o[189] = w_u_lrly1_vc_addr[23];
    assign c_o[190] = w_u_lrly1_vc_re;
    assign c_o[191] = w_u_lrly1_vm_waddr[0];
    assign c_o[192] = w_u_lrly1_vm_waddr[1];
    assign c_o[193] = w_u_lrly1_vm_waddr[2];
    assign c_o[194] = w_u_lrly1_vm_waddr[3];
    assign c_o[195] = w_u_lrly1_vm_waddr[4];
    assign c_o[196] = w_u_lrly1_vm_waddr[5];
    assign c_o[197] = w_u_lrly1_vm_waddr[6];
    assign c_o[198] = w_u_lrly1_vm_waddr[7];
    assign c_o[199] = w_u_lrly1_vm_waddr[8];
    assign c_o[200] = w_u_lrly1_vm_waddr[9];
    assign c_o[201] = w_u_lrly1_vm_waddr[10];
    assign c_o[202] = w_u_lrly1_vm_waddr[11];
    assign c_o[203] = w_u_lrly1_vm_waddr[12];
    assign c_o[204] = w_u_lrly1_vm_waddr[13];
    assign c_o[205] = w_u_lrly1_vm_waddr[14];
    assign c_o[206] = w_u_lrly1_vm_waddr[15];
    assign c_o[207] = w_u_lrly1_vm_waddr[16];
    assign c_o[208] = w_u_lrly1_vm_waddr[17];
    assign c_o[209] = w_u_lrly1_vm_waddr[18];
    assign c_o[210] = w_u_lrly1_vm_waddr[19];
    assign c_o[211] = w_u_lrly1_vm_waddr[20];
    assign c_o[212] = w_u_lrly1_vm_waddr[21];
    assign c_o[213] = w_u_lrly1_vm_waddr[22];
    assign c_o[214] = w_u_lrly1_vm_waddr[23];
    assign c_o[215] = w_u_lrly1_vm_wdata[0];
    assign c_o[216] = w_u_lrly1_vm_wdata[1];
    assign c_o[217] = w_u_lrly1_vm_wdata[2];
    assign c_o[218] = w_u_lrly1_vm_wdata[3];
    assign c_o[219] = w_u_lrly1_vm_wdata[4];
    assign c_o[220] = w_u_lrly1_vm_wdata[5];
    assign c_o[221] = w_u_lrly1_vm_wdata[6];
    assign c_o[222] = w_u_lrly1_vm_wdata[7];
    assign c_o[223] = w_u_lrly1_vm_wdata[8];
    assign c_o[224] = w_u_lrly1_vm_wdata[9];
    assign c_o[225] = w_u_lrly1_vm_wdata[10];
    assign c_o[226] = w_u_lrly1_vm_wdata[11];
    assign c_o[227] = w_u_lrly1_vm_wdata[12];
    assign c_o[228] = w_u_lrly1_vm_wdata[13];
    assign c_o[229] = w_u_lrly1_vm_wdata[14];
    assign c_o[230] = w_u_lrly1_vm_wdata[15];
    assign c_o[231] = w_u_lrly1_vm_wdata[16];
    assign c_o[232] = w_u_lrly1_vm_wdata[17];
    assign c_o[233] = w_u_lrly1_vm_wdata[18];
    assign c_o[234] = w_u_lrly1_vm_wdata[19];
    assign c_o[235] = w_u_lrly1_vm_wdata[20];
    assign c_o[236] = w_u_lrly1_vm_wdata[21];
    assign c_o[237] = w_u_lrly1_vm_wdata[22];
    assign c_o[238] = w_u_lrly1_vm_wdata[23];
    assign c_o[239] = w_u_lrly1_vm_wdata[24];
    assign c_o[240] = w_u_lrly1_vm_wdata[25];
    assign c_o[241] = w_u_lrly1_vm_wdata[26];
    assign c_o[242] = w_u_lrly1_vm_wdata[27];
    assign c_o[243] = w_u_lrly1_vm_wdata[28];
    assign c_o[244] = w_u_lrly1_vm_wdata[29];
    assign c_o[245] = w_u_lrly1_vm_wdata[30];
    assign c_o[246] = w_u_lrly1_vm_wdata[31];
    assign c_o[247] = w_u_lrly1_vm_we;
    ot_hdc_sfu_exp_t u_u_exp1 (
        .clk(clk),
        .fault(w_u_exp1_fault),
        .rst_n(rst_n),
        .v(w_u_head1_sx_exp_v[0]),
        .vo(w_u_exp1_vo),
        .x(w_u_head1_sx_exp_x[31:0]),
        .y(w_u_exp1_y)
    );
    qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .MEMORY_READ_EXTRA(0)) u_u_head1 (
        .accept(w_u_lrly1_c_accept[0]),
        .ad(w_u_lrly1_c_ad[2:0]),
        .asi(w_u_lrly1_c_asi[23:0]),
        .asrc(w_u_lrly1_c_asrc[0]),
        .bsi(w_u_lrly1_c_bsi[23:0]),
        .bsrc(w_u_lrly1_c_bsrc[0]),
        .clk(clk),
        .cls(w_u_lrly1_c_cls[2:0]),
        .crom_addr(w_u_head1_crom_addr),
        .crom_q(w_u_lrly1_c_crom[63:0]),
        .crom_re(w_u_head1_crom_re),
        .csi(w_u_lrly1_c_csi[23:0]),
        .csrc(w_u_lrly1_c_csrc[0]),
        .cura0(w_u_lrly1_c_cura[23:0]),
        .curb0(w_u_lrly1_c_curb[23:0]),
        .curc0(w_u_lrly1_c_curc[23:0]),
        .curd0(w_u_lrly1_c_curd[23:0]),
        .dsi(w_u_lrly1_c_dsi[23:0]),
        .dst(w_u_lrly1_c_dst[1:0]),
        .emit0(w_u_lrly1_c_emit0[0]),
        .fin_th(w_u_lrly1_c_fin_th[18:0]),
        .i(w_u_lrly1_c_i[17:0]),
        .i_last_r(w_u_lrly1_c_ilast[0]),
        .i_sfu(w_u_lrly1_c_isfu[2:0]),
        .imm1(w_u_lrly1_c_imm1[31:0]),
        .imm2(w_u_lrly1_c_imm2[31:0]),
        .kv_waddr(w_u_head1_kv_waddr),
        .kv_wdata(w_u_head1_kv_wdata),
        .kv_we(w_u_head1_kv_we),
        .l_fault(w_u_head1_l_fault),
        .l_last(w_u_head1_l_last),
        .l_out(w_u_head1_l_out),
        .l_ov(w_u_head1_l_ov),
        .l_raddr(w_u_head1_l_raddr),
        .l_red(w_u_head1_l_red),
        .l_redsq(w_u_head1_l_redsq),
        .live(w_u_lrly1_c_live[0]),
        .ma(w_u_lrly1_c_ma[1:0]),
        .mb(w_u_lrly1_c_mb[1:0]),
        .mc(w_u_lrly1_c_mc[0]),
        .md(w_u_lrly1_c_md[0]),
        .red(w_u_lrly1_c_red[1:0]),
        .redsq(w_u_lrly1_c_redsq[0]),
        .retire(w_u_head1_retire),
        .rrow(w_u_lrly1_c_rrow[23:0]),
        .rst_n(rst_n),
        .sx_exp_v(w_u_head1_sx_exp_v),
        .sx_exp_x(w_u_head1_sx_exp_x),
        .sx_rcp_v(w_u_head1_sx_rcp_v),
        .sx_rcp_x(w_u_head1_sx_rcp_x),
        .sx_rsq_v(w_u_head1_sx_rsq_v),
        .sx_rsq_x(w_u_head1_sx_rsq_x),
        .sy_exp_f(w_u_exp1_fault[0]),
        .sy_exp_vo(w_u_exp1_vo[0]),
        .sy_exp_y(w_u_exp1_y[31:0]),
        .sy_rcp_f(w_u_rcp1_fault[0]),
        .sy_rcp_y(w_u_rcp1_y[31:0]),
        .sy_rsq_f(w_u_rsq1_fault[0]),
        .sy_rsq_y(w_u_rsq1_y[31:0]),
        .va_addr(w_u_head1_va_addr),
        .va_q(w_u_lrly1_c_va[31:0]),
        .va_re(w_u_head1_va_re),
        .vb_addr(w_u_head1_vb_addr),
        .vb_q(w_u_lrly1_c_vb[31:0]),
        .vb_re(w_u_head1_vb_re),
        .vc_addr(w_u_head1_vc_addr),
        .vc_q(w_u_lrly1_c_vc[31:0]),
        .vc_re(w_u_head1_vc_re),
        .vm_waddr(w_u_head1_vm_waddr),
        .vm_wdata(w_u_head1_vm_wdata),
        .vm_we(w_u_head1_vm_we),
        .wrom_addr(w_u_head1_wrom_addr),
        .wrom_q(w_u_lrly1_c_wrom[255:0]),
        .wrom_re(w_u_head1_wrom_re)
    );
    qfd_dv_s5_lrly u_u_lrly1 (
        .c_accept(w_u_lrly1_c_accept),
        .c_ad(w_u_lrly1_c_ad),
        .c_asi(w_u_lrly1_c_asi),
        .c_asrc(w_u_lrly1_c_asrc),
        .c_bsi(w_u_lrly1_c_bsi),
        .c_bsrc(w_u_lrly1_c_bsrc),
        .c_cls(w_u_lrly1_c_cls),
        .c_crom(w_u_lrly1_c_crom),
        .c_csi(w_u_lrly1_c_csi),
        .c_csrc(w_u_lrly1_c_csrc),
        .c_cura(w_u_lrly1_c_cura),
        .c_curb(w_u_lrly1_c_curb),
        .c_curc(w_u_lrly1_c_curc),
        .c_curd(w_u_lrly1_c_curd),
        .c_dsi(w_u_lrly1_c_dsi),
        .c_dst(w_u_lrly1_c_dst),
        .c_emit0(w_u_lrly1_c_emit0),
        .c_fin_th(w_u_lrly1_c_fin_th),
        .c_i(w_u_lrly1_c_i),
        .c_ilast(w_u_lrly1_c_ilast),
        .c_imm1(w_u_lrly1_c_imm1),
        .c_imm2(w_u_lrly1_c_imm2),
        .c_isfu(w_u_lrly1_c_isfu),
        .c_live(w_u_lrly1_c_live),
        .c_ma(w_u_lrly1_c_ma),
        .c_mb(w_u_lrly1_c_mb),
        .c_mc(w_u_lrly1_c_mc),
        .c_md(w_u_lrly1_c_md),
        .c_red(w_u_lrly1_c_red),
        .c_redsq(w_u_lrly1_c_redsq),
        .c_rrow(w_u_lrly1_c_rrow),
        .c_va(w_u_lrly1_c_va),
        .c_vb(w_u_lrly1_c_vb),
        .c_vc(w_u_lrly1_c_vc),
        .c_wrom(w_u_lrly1_c_wrom),
        .ck(clk),
        .cr_q({x_su_c_p1_i_q[572:541], x_su_c_p1_i_q[700:669]}),
        .crom_addr(w_u_lrly1_crom_addr),
        .crom_re(w_u_lrly1_crom_re),
        .gb(x_su_c_i_q[499:0]),
        .gv(x_su_c_i_q[502:500]),
        .h_crom_addr(w_u_head1_crom_addr[23:0]),
        .h_crom_re(w_u_head1_crom_re[0]),
        .h_kv_waddr(w_u_head1_kv_waddr[23:0]),
        .h_kv_wdata(w_u_head1_kv_wdata[31:0]),
        .h_kv_we(w_u_head1_kv_we[0]),
        .h_l_fault(w_u_head1_l_fault[0]),
        .h_l_last(w_u_head1_l_last[0]),
        .h_l_out(w_u_head1_l_out[31:0]),
        .h_l_ov(w_u_head1_l_ov[0]),
        .h_l_raddr(w_u_head1_l_raddr[23:0]),
        .h_l_red(w_u_head1_l_red[1:0]),
        .h_l_redsq(w_u_head1_l_redsq[0]),
        .h_retire(w_u_head1_retire[0]),
        .h_rst_n(w_u_lrly1_h_rst_n),
        .h_va_addr(w_u_head1_va_addr[23:0]),
        .h_va_re(w_u_head1_va_re[0]),
        .h_vb_addr(w_u_head1_vb_addr[23:0]),
        .h_vb_re(w_u_head1_vb_re[0]),
        .h_vc_addr(w_u_head1_vc_addr[23:0]),
        .h_vc_re(w_u_head1_vc_re[0]),
        .h_vm_waddr(w_u_head1_vm_waddr[23:0]),
        .h_vm_wdata(w_u_head1_vm_wdata[31:0]),
        .h_vm_we(w_u_head1_vm_we[0]),
        .h_wrom_addr(w_u_head1_wrom_addr[23:0]),
        .h_wrom_re(w_u_head1_wrom_re[0]),
        .kv_waddr(w_u_lrly1_kv_waddr),
        .kv_wdata(w_u_lrly1_kv_wdata),
        .kv_we(w_u_lrly1_kv_we),
        .l_fault(w_u_lrly1_l_fault),
        .l_last(w_u_lrly1_l_last),
        .l_out(w_u_lrly1_l_out),
        .l_ov(w_u_lrly1_l_ov),
        .l_raddr(w_u_lrly1_l_raddr),
        .l_red(w_u_lrly1_l_red),
        .l_redsq(w_u_lrly1_l_redsq),
        .lv1(x_su_c_i_q[504]),
        .pd1(x_su_c_i_q[698:603]),
        .retire(w_u_lrly1_retire),
        .rst_n(rst_n),
        .va_addr(w_u_lrly1_va_addr),
        .va_q(x_su_c_p1_i_q[188:157]),
        .va_re(w_u_lrly1_va_re),
        .vb_addr(w_u_lrly1_vb_addr),
        .vb_q(x_su_c_p1_i_q[316:285]),
        .vb_re(w_u_lrly1_vb_re),
        .vc_addr(w_u_lrly1_vc_addr),
        .vc_q(x_su_c_p1_i_q[444:413]),
        .vc_re(w_u_lrly1_vc_re),
        .vm_waddr(w_u_lrly1_vm_waddr),
        .vm_wdata(w_u_lrly1_vm_wdata),
        .vm_we(w_u_lrly1_vm_we),
        .wrom_addr(w_u_lrly1_wrom_addr),
        .wrom_re(w_u_lrly1_wrom_re)
    );
    ot_hdc_sfu_rcp_t u_u_rcp1 (
        .clk(clk),
        .fault(w_u_rcp1_fault),
        .rst_n(rst_n),
        .v(w_u_head1_sx_rcp_v[0]),
        .vo(w_u_rcp1_vo),
        .x(w_u_head1_sx_rcp_x[31:0]),
        .y(w_u_rcp1_y)
    );
    ot_hdc_sfu_rsq_t u_u_rsq1 (
        .clk(clk),
        .fault(w_u_rsq1_fault),
        .rst_n(rst_n),
        .v(w_u_head1_sx_rsq_v[0]),
        .vo(w_u_rsq1_vo),
        .x(w_u_head1_sx_rsq_x[31:0]),
        .y(w_u_rsq1_y)
    );
endmodule
`default_nettype wire
