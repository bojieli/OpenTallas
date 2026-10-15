// tools/hbm_hub_quarter_gen.py --hub: hfd_hc_hub (band glue of the tiled hfd_hc quarter, conservative-1011)
`timescale 1ns/1ps
module hfd_hc_hub (
    input  wire clk,
    input  wire rst,
    input  wire [1023:0] f_sfu,
    output wire [1023:0] t_sfu,
    output wire [161:0] hb0,
    output wire [161:0] hb1,
    output wire [161:0] hb2,
    output wire [161:0] hb3,
    input  wire [255:0] hq0,
    input  wire [255:0] hq1,
    input  wire [255:0] hq2,
    input  wire [255:0] hq3
);
    (* keep *) reg [1:0] rst_q;  always @(posedge clk) rst_q <= {rst_q[0], rst};
    (* keep *) reg [1023:0] fi;  always @(posedge clk) fi <= f_sfu;
    wire [161:0] bsrc;
    assign bsrc[161] = rst_q[1];
    assign bsrc[0] = fi[0] ^ fi[161] ^ fi[322] ^ fi[483] ^ fi[644] ^ fi[805] ^ fi[966];
    assign bsrc[1] = fi[1] ^ fi[162] ^ fi[323] ^ fi[484] ^ fi[645] ^ fi[806] ^ fi[967];
    assign bsrc[2] = fi[2] ^ fi[163] ^ fi[324] ^ fi[485] ^ fi[646] ^ fi[807] ^ fi[968];
    assign bsrc[3] = fi[3] ^ fi[164] ^ fi[325] ^ fi[486] ^ fi[647] ^ fi[808] ^ fi[969];
    assign bsrc[4] = fi[4] ^ fi[165] ^ fi[326] ^ fi[487] ^ fi[648] ^ fi[809] ^ fi[970];
    assign bsrc[5] = fi[5] ^ fi[166] ^ fi[327] ^ fi[488] ^ fi[649] ^ fi[810] ^ fi[971];
    assign bsrc[6] = fi[6] ^ fi[167] ^ fi[328] ^ fi[489] ^ fi[650] ^ fi[811] ^ fi[972];
    assign bsrc[7] = fi[7] ^ fi[168] ^ fi[329] ^ fi[490] ^ fi[651] ^ fi[812] ^ fi[973];
    assign bsrc[8] = fi[8] ^ fi[169] ^ fi[330] ^ fi[491] ^ fi[652] ^ fi[813] ^ fi[974];
    assign bsrc[9] = fi[9] ^ fi[170] ^ fi[331] ^ fi[492] ^ fi[653] ^ fi[814] ^ fi[975];
    assign bsrc[10] = fi[10] ^ fi[171] ^ fi[332] ^ fi[493] ^ fi[654] ^ fi[815] ^ fi[976];
    assign bsrc[11] = fi[11] ^ fi[172] ^ fi[333] ^ fi[494] ^ fi[655] ^ fi[816] ^ fi[977];
    assign bsrc[12] = fi[12] ^ fi[173] ^ fi[334] ^ fi[495] ^ fi[656] ^ fi[817] ^ fi[978];
    assign bsrc[13] = fi[13] ^ fi[174] ^ fi[335] ^ fi[496] ^ fi[657] ^ fi[818] ^ fi[979];
    assign bsrc[14] = fi[14] ^ fi[175] ^ fi[336] ^ fi[497] ^ fi[658] ^ fi[819] ^ fi[980];
    assign bsrc[15] = fi[15] ^ fi[176] ^ fi[337] ^ fi[498] ^ fi[659] ^ fi[820] ^ fi[981];
    assign bsrc[16] = fi[16] ^ fi[177] ^ fi[338] ^ fi[499] ^ fi[660] ^ fi[821] ^ fi[982];
    assign bsrc[17] = fi[17] ^ fi[178] ^ fi[339] ^ fi[500] ^ fi[661] ^ fi[822] ^ fi[983];
    assign bsrc[18] = fi[18] ^ fi[179] ^ fi[340] ^ fi[501] ^ fi[662] ^ fi[823] ^ fi[984];
    assign bsrc[19] = fi[19] ^ fi[180] ^ fi[341] ^ fi[502] ^ fi[663] ^ fi[824] ^ fi[985];
    assign bsrc[20] = fi[20] ^ fi[181] ^ fi[342] ^ fi[503] ^ fi[664] ^ fi[825] ^ fi[986];
    assign bsrc[21] = fi[21] ^ fi[182] ^ fi[343] ^ fi[504] ^ fi[665] ^ fi[826] ^ fi[987];
    assign bsrc[22] = fi[22] ^ fi[183] ^ fi[344] ^ fi[505] ^ fi[666] ^ fi[827] ^ fi[988];
    assign bsrc[23] = fi[23] ^ fi[184] ^ fi[345] ^ fi[506] ^ fi[667] ^ fi[828] ^ fi[989];
    assign bsrc[24] = fi[24] ^ fi[185] ^ fi[346] ^ fi[507] ^ fi[668] ^ fi[829] ^ fi[990];
    assign bsrc[25] = fi[25] ^ fi[186] ^ fi[347] ^ fi[508] ^ fi[669] ^ fi[830] ^ fi[991];
    assign bsrc[26] = fi[26] ^ fi[187] ^ fi[348] ^ fi[509] ^ fi[670] ^ fi[831] ^ fi[992];
    assign bsrc[27] = fi[27] ^ fi[188] ^ fi[349] ^ fi[510] ^ fi[671] ^ fi[832] ^ fi[993];
    assign bsrc[28] = fi[28] ^ fi[189] ^ fi[350] ^ fi[511] ^ fi[672] ^ fi[833] ^ fi[994];
    assign bsrc[29] = fi[29] ^ fi[190] ^ fi[351] ^ fi[512] ^ fi[673] ^ fi[834] ^ fi[995];
    assign bsrc[30] = fi[30] ^ fi[191] ^ fi[352] ^ fi[513] ^ fi[674] ^ fi[835] ^ fi[996];
    assign bsrc[31] = fi[31] ^ fi[192] ^ fi[353] ^ fi[514] ^ fi[675] ^ fi[836] ^ fi[997];
    assign bsrc[32] = fi[32] ^ fi[193] ^ fi[354] ^ fi[515] ^ fi[676] ^ fi[837] ^ fi[998];
    assign bsrc[33] = fi[33] ^ fi[194] ^ fi[355] ^ fi[516] ^ fi[677] ^ fi[838] ^ fi[999];
    assign bsrc[34] = fi[34] ^ fi[195] ^ fi[356] ^ fi[517] ^ fi[678] ^ fi[839] ^ fi[1000];
    assign bsrc[35] = fi[35] ^ fi[196] ^ fi[357] ^ fi[518] ^ fi[679] ^ fi[840] ^ fi[1001];
    assign bsrc[36] = fi[36] ^ fi[197] ^ fi[358] ^ fi[519] ^ fi[680] ^ fi[841] ^ fi[1002];
    assign bsrc[37] = fi[37] ^ fi[198] ^ fi[359] ^ fi[520] ^ fi[681] ^ fi[842] ^ fi[1003];
    assign bsrc[38] = fi[38] ^ fi[199] ^ fi[360] ^ fi[521] ^ fi[682] ^ fi[843] ^ fi[1004];
    assign bsrc[39] = fi[39] ^ fi[200] ^ fi[361] ^ fi[522] ^ fi[683] ^ fi[844] ^ fi[1005];
    assign bsrc[40] = fi[40] ^ fi[201] ^ fi[362] ^ fi[523] ^ fi[684] ^ fi[845] ^ fi[1006];
    assign bsrc[41] = fi[41] ^ fi[202] ^ fi[363] ^ fi[524] ^ fi[685] ^ fi[846] ^ fi[1007];
    assign bsrc[42] = fi[42] ^ fi[203] ^ fi[364] ^ fi[525] ^ fi[686] ^ fi[847] ^ fi[1008];
    assign bsrc[43] = fi[43] ^ fi[204] ^ fi[365] ^ fi[526] ^ fi[687] ^ fi[848] ^ fi[1009];
    assign bsrc[44] = fi[44] ^ fi[205] ^ fi[366] ^ fi[527] ^ fi[688] ^ fi[849] ^ fi[1010];
    assign bsrc[45] = fi[45] ^ fi[206] ^ fi[367] ^ fi[528] ^ fi[689] ^ fi[850] ^ fi[1011];
    assign bsrc[46] = fi[46] ^ fi[207] ^ fi[368] ^ fi[529] ^ fi[690] ^ fi[851] ^ fi[1012];
    assign bsrc[47] = fi[47] ^ fi[208] ^ fi[369] ^ fi[530] ^ fi[691] ^ fi[852] ^ fi[1013];
    assign bsrc[48] = fi[48] ^ fi[209] ^ fi[370] ^ fi[531] ^ fi[692] ^ fi[853] ^ fi[1014];
    assign bsrc[49] = fi[49] ^ fi[210] ^ fi[371] ^ fi[532] ^ fi[693] ^ fi[854] ^ fi[1015];
    assign bsrc[50] = fi[50] ^ fi[211] ^ fi[372] ^ fi[533] ^ fi[694] ^ fi[855] ^ fi[1016];
    assign bsrc[51] = fi[51] ^ fi[212] ^ fi[373] ^ fi[534] ^ fi[695] ^ fi[856] ^ fi[1017];
    assign bsrc[52] = fi[52] ^ fi[213] ^ fi[374] ^ fi[535] ^ fi[696] ^ fi[857] ^ fi[1018];
    assign bsrc[53] = fi[53] ^ fi[214] ^ fi[375] ^ fi[536] ^ fi[697] ^ fi[858] ^ fi[1019];
    assign bsrc[54] = fi[54] ^ fi[215] ^ fi[376] ^ fi[537] ^ fi[698] ^ fi[859] ^ fi[1020];
    assign bsrc[55] = fi[55] ^ fi[216] ^ fi[377] ^ fi[538] ^ fi[699] ^ fi[860] ^ fi[1021];
    assign bsrc[56] = fi[56] ^ fi[217] ^ fi[378] ^ fi[539] ^ fi[700] ^ fi[861] ^ fi[1022];
    assign bsrc[57] = fi[57] ^ fi[218] ^ fi[379] ^ fi[540] ^ fi[701] ^ fi[862] ^ fi[1023];
    assign bsrc[58] = fi[58] ^ fi[219] ^ fi[380] ^ fi[541] ^ fi[702] ^ fi[863];
    assign bsrc[59] = fi[59] ^ fi[220] ^ fi[381] ^ fi[542] ^ fi[703] ^ fi[864];
    assign bsrc[60] = fi[60] ^ fi[221] ^ fi[382] ^ fi[543] ^ fi[704] ^ fi[865];
    assign bsrc[61] = fi[61] ^ fi[222] ^ fi[383] ^ fi[544] ^ fi[705] ^ fi[866];
    assign bsrc[62] = fi[62] ^ fi[223] ^ fi[384] ^ fi[545] ^ fi[706] ^ fi[867];
    assign bsrc[63] = fi[63] ^ fi[224] ^ fi[385] ^ fi[546] ^ fi[707] ^ fi[868];
    assign bsrc[64] = fi[64] ^ fi[225] ^ fi[386] ^ fi[547] ^ fi[708] ^ fi[869];
    assign bsrc[65] = fi[65] ^ fi[226] ^ fi[387] ^ fi[548] ^ fi[709] ^ fi[870];
    assign bsrc[66] = fi[66] ^ fi[227] ^ fi[388] ^ fi[549] ^ fi[710] ^ fi[871];
    assign bsrc[67] = fi[67] ^ fi[228] ^ fi[389] ^ fi[550] ^ fi[711] ^ fi[872];
    assign bsrc[68] = fi[68] ^ fi[229] ^ fi[390] ^ fi[551] ^ fi[712] ^ fi[873];
    assign bsrc[69] = fi[69] ^ fi[230] ^ fi[391] ^ fi[552] ^ fi[713] ^ fi[874];
    assign bsrc[70] = fi[70] ^ fi[231] ^ fi[392] ^ fi[553] ^ fi[714] ^ fi[875];
    assign bsrc[71] = fi[71] ^ fi[232] ^ fi[393] ^ fi[554] ^ fi[715] ^ fi[876];
    assign bsrc[72] = fi[72] ^ fi[233] ^ fi[394] ^ fi[555] ^ fi[716] ^ fi[877];
    assign bsrc[73] = fi[73] ^ fi[234] ^ fi[395] ^ fi[556] ^ fi[717] ^ fi[878];
    assign bsrc[74] = fi[74] ^ fi[235] ^ fi[396] ^ fi[557] ^ fi[718] ^ fi[879];
    assign bsrc[75] = fi[75] ^ fi[236] ^ fi[397] ^ fi[558] ^ fi[719] ^ fi[880];
    assign bsrc[76] = fi[76] ^ fi[237] ^ fi[398] ^ fi[559] ^ fi[720] ^ fi[881];
    assign bsrc[77] = fi[77] ^ fi[238] ^ fi[399] ^ fi[560] ^ fi[721] ^ fi[882];
    assign bsrc[78] = fi[78] ^ fi[239] ^ fi[400] ^ fi[561] ^ fi[722] ^ fi[883];
    assign bsrc[79] = fi[79] ^ fi[240] ^ fi[401] ^ fi[562] ^ fi[723] ^ fi[884];
    assign bsrc[80] = fi[80] ^ fi[241] ^ fi[402] ^ fi[563] ^ fi[724] ^ fi[885];
    assign bsrc[81] = fi[81] ^ fi[242] ^ fi[403] ^ fi[564] ^ fi[725] ^ fi[886];
    assign bsrc[82] = fi[82] ^ fi[243] ^ fi[404] ^ fi[565] ^ fi[726] ^ fi[887];
    assign bsrc[83] = fi[83] ^ fi[244] ^ fi[405] ^ fi[566] ^ fi[727] ^ fi[888];
    assign bsrc[84] = fi[84] ^ fi[245] ^ fi[406] ^ fi[567] ^ fi[728] ^ fi[889];
    assign bsrc[85] = fi[85] ^ fi[246] ^ fi[407] ^ fi[568] ^ fi[729] ^ fi[890];
    assign bsrc[86] = fi[86] ^ fi[247] ^ fi[408] ^ fi[569] ^ fi[730] ^ fi[891];
    assign bsrc[87] = fi[87] ^ fi[248] ^ fi[409] ^ fi[570] ^ fi[731] ^ fi[892];
    assign bsrc[88] = fi[88] ^ fi[249] ^ fi[410] ^ fi[571] ^ fi[732] ^ fi[893];
    assign bsrc[89] = fi[89] ^ fi[250] ^ fi[411] ^ fi[572] ^ fi[733] ^ fi[894];
    assign bsrc[90] = fi[90] ^ fi[251] ^ fi[412] ^ fi[573] ^ fi[734] ^ fi[895];
    assign bsrc[91] = fi[91] ^ fi[252] ^ fi[413] ^ fi[574] ^ fi[735] ^ fi[896];
    assign bsrc[92] = fi[92] ^ fi[253] ^ fi[414] ^ fi[575] ^ fi[736] ^ fi[897];
    assign bsrc[93] = fi[93] ^ fi[254] ^ fi[415] ^ fi[576] ^ fi[737] ^ fi[898];
    assign bsrc[94] = fi[94] ^ fi[255] ^ fi[416] ^ fi[577] ^ fi[738] ^ fi[899];
    assign bsrc[95] = fi[95] ^ fi[256] ^ fi[417] ^ fi[578] ^ fi[739] ^ fi[900];
    assign bsrc[96] = fi[96] ^ fi[257] ^ fi[418] ^ fi[579] ^ fi[740] ^ fi[901];
    assign bsrc[97] = fi[97] ^ fi[258] ^ fi[419] ^ fi[580] ^ fi[741] ^ fi[902];
    assign bsrc[98] = fi[98] ^ fi[259] ^ fi[420] ^ fi[581] ^ fi[742] ^ fi[903];
    assign bsrc[99] = fi[99] ^ fi[260] ^ fi[421] ^ fi[582] ^ fi[743] ^ fi[904];
    assign bsrc[100] = fi[100] ^ fi[261] ^ fi[422] ^ fi[583] ^ fi[744] ^ fi[905];
    assign bsrc[101] = fi[101] ^ fi[262] ^ fi[423] ^ fi[584] ^ fi[745] ^ fi[906];
    assign bsrc[102] = fi[102] ^ fi[263] ^ fi[424] ^ fi[585] ^ fi[746] ^ fi[907];
    assign bsrc[103] = fi[103] ^ fi[264] ^ fi[425] ^ fi[586] ^ fi[747] ^ fi[908];
    assign bsrc[104] = fi[104] ^ fi[265] ^ fi[426] ^ fi[587] ^ fi[748] ^ fi[909];
    assign bsrc[105] = fi[105] ^ fi[266] ^ fi[427] ^ fi[588] ^ fi[749] ^ fi[910];
    assign bsrc[106] = fi[106] ^ fi[267] ^ fi[428] ^ fi[589] ^ fi[750] ^ fi[911];
    assign bsrc[107] = fi[107] ^ fi[268] ^ fi[429] ^ fi[590] ^ fi[751] ^ fi[912];
    assign bsrc[108] = fi[108] ^ fi[269] ^ fi[430] ^ fi[591] ^ fi[752] ^ fi[913];
    assign bsrc[109] = fi[109] ^ fi[270] ^ fi[431] ^ fi[592] ^ fi[753] ^ fi[914];
    assign bsrc[110] = fi[110] ^ fi[271] ^ fi[432] ^ fi[593] ^ fi[754] ^ fi[915];
    assign bsrc[111] = fi[111] ^ fi[272] ^ fi[433] ^ fi[594] ^ fi[755] ^ fi[916];
    assign bsrc[112] = fi[112] ^ fi[273] ^ fi[434] ^ fi[595] ^ fi[756] ^ fi[917];
    assign bsrc[113] = fi[113] ^ fi[274] ^ fi[435] ^ fi[596] ^ fi[757] ^ fi[918];
    assign bsrc[114] = fi[114] ^ fi[275] ^ fi[436] ^ fi[597] ^ fi[758] ^ fi[919];
    assign bsrc[115] = fi[115] ^ fi[276] ^ fi[437] ^ fi[598] ^ fi[759] ^ fi[920];
    assign bsrc[116] = fi[116] ^ fi[277] ^ fi[438] ^ fi[599] ^ fi[760] ^ fi[921];
    assign bsrc[117] = fi[117] ^ fi[278] ^ fi[439] ^ fi[600] ^ fi[761] ^ fi[922];
    assign bsrc[118] = fi[118] ^ fi[279] ^ fi[440] ^ fi[601] ^ fi[762] ^ fi[923];
    assign bsrc[119] = fi[119] ^ fi[280] ^ fi[441] ^ fi[602] ^ fi[763] ^ fi[924];
    assign bsrc[120] = fi[120] ^ fi[281] ^ fi[442] ^ fi[603] ^ fi[764] ^ fi[925];
    assign bsrc[121] = fi[121] ^ fi[282] ^ fi[443] ^ fi[604] ^ fi[765] ^ fi[926];
    assign bsrc[122] = fi[122] ^ fi[283] ^ fi[444] ^ fi[605] ^ fi[766] ^ fi[927];
    assign bsrc[123] = fi[123] ^ fi[284] ^ fi[445] ^ fi[606] ^ fi[767] ^ fi[928];
    assign bsrc[124] = fi[124] ^ fi[285] ^ fi[446] ^ fi[607] ^ fi[768] ^ fi[929];
    assign bsrc[125] = fi[125] ^ fi[286] ^ fi[447] ^ fi[608] ^ fi[769] ^ fi[930];
    assign bsrc[126] = fi[126] ^ fi[287] ^ fi[448] ^ fi[609] ^ fi[770] ^ fi[931];
    assign bsrc[127] = fi[127] ^ fi[288] ^ fi[449] ^ fi[610] ^ fi[771] ^ fi[932];
    assign bsrc[128] = fi[128] ^ fi[289] ^ fi[450] ^ fi[611] ^ fi[772] ^ fi[933];
    assign bsrc[129] = fi[129] ^ fi[290] ^ fi[451] ^ fi[612] ^ fi[773] ^ fi[934];
    assign bsrc[130] = fi[130] ^ fi[291] ^ fi[452] ^ fi[613] ^ fi[774] ^ fi[935];
    assign bsrc[131] = fi[131] ^ fi[292] ^ fi[453] ^ fi[614] ^ fi[775] ^ fi[936];
    assign bsrc[132] = fi[132] ^ fi[293] ^ fi[454] ^ fi[615] ^ fi[776] ^ fi[937];
    assign bsrc[133] = fi[133] ^ fi[294] ^ fi[455] ^ fi[616] ^ fi[777] ^ fi[938];
    assign bsrc[134] = fi[134] ^ fi[295] ^ fi[456] ^ fi[617] ^ fi[778] ^ fi[939];
    assign bsrc[135] = fi[135] ^ fi[296] ^ fi[457] ^ fi[618] ^ fi[779] ^ fi[940];
    assign bsrc[136] = fi[136] ^ fi[297] ^ fi[458] ^ fi[619] ^ fi[780] ^ fi[941];
    assign bsrc[137] = fi[137] ^ fi[298] ^ fi[459] ^ fi[620] ^ fi[781] ^ fi[942];
    assign bsrc[138] = fi[138] ^ fi[299] ^ fi[460] ^ fi[621] ^ fi[782] ^ fi[943];
    assign bsrc[139] = fi[139] ^ fi[300] ^ fi[461] ^ fi[622] ^ fi[783] ^ fi[944];
    assign bsrc[140] = fi[140] ^ fi[301] ^ fi[462] ^ fi[623] ^ fi[784] ^ fi[945];
    assign bsrc[141] = fi[141] ^ fi[302] ^ fi[463] ^ fi[624] ^ fi[785] ^ fi[946];
    assign bsrc[142] = fi[142] ^ fi[303] ^ fi[464] ^ fi[625] ^ fi[786] ^ fi[947];
    assign bsrc[143] = fi[143] ^ fi[304] ^ fi[465] ^ fi[626] ^ fi[787] ^ fi[948];
    assign bsrc[144] = fi[144] ^ fi[305] ^ fi[466] ^ fi[627] ^ fi[788] ^ fi[949];
    assign bsrc[145] = fi[145] ^ fi[306] ^ fi[467] ^ fi[628] ^ fi[789] ^ fi[950];
    assign bsrc[146] = fi[146] ^ fi[307] ^ fi[468] ^ fi[629] ^ fi[790] ^ fi[951];
    assign bsrc[147] = fi[147] ^ fi[308] ^ fi[469] ^ fi[630] ^ fi[791] ^ fi[952];
    assign bsrc[148] = fi[148] ^ fi[309] ^ fi[470] ^ fi[631] ^ fi[792] ^ fi[953];
    assign bsrc[149] = fi[149] ^ fi[310] ^ fi[471] ^ fi[632] ^ fi[793] ^ fi[954];
    assign bsrc[150] = fi[150] ^ fi[311] ^ fi[472] ^ fi[633] ^ fi[794] ^ fi[955];
    assign bsrc[151] = fi[151] ^ fi[312] ^ fi[473] ^ fi[634] ^ fi[795] ^ fi[956];
    assign bsrc[152] = fi[152] ^ fi[313] ^ fi[474] ^ fi[635] ^ fi[796] ^ fi[957];
    assign bsrc[153] = fi[153] ^ fi[314] ^ fi[475] ^ fi[636] ^ fi[797] ^ fi[958];
    assign bsrc[154] = fi[154] ^ fi[315] ^ fi[476] ^ fi[637] ^ fi[798] ^ fi[959];
    assign bsrc[155] = fi[155] ^ fi[316] ^ fi[477] ^ fi[638] ^ fi[799] ^ fi[960];
    assign bsrc[156] = fi[156] ^ fi[317] ^ fi[478] ^ fi[639] ^ fi[800] ^ fi[961];
    assign bsrc[157] = fi[157] ^ fi[318] ^ fi[479] ^ fi[640] ^ fi[801] ^ fi[962];
    assign bsrc[158] = fi[158] ^ fi[319] ^ fi[480] ^ fi[641] ^ fi[802] ^ fi[963];
    assign bsrc[159] = fi[159] ^ fi[320] ^ fi[481] ^ fi[642] ^ fi[803] ^ fi[964];
    assign bsrc[160] = fi[160] ^ fi[321] ^ fi[482] ^ fi[643] ^ fi[804] ^ fi[965];
    wire [161:0] hs0 = bsrc;
    (* keep *) reg [161:0] hbr0;
    always @(posedge clk) hbr0 <= hs0;
    assign hb0 = hbr0;
    wire [161:0] hs1 = {bsrc[161], bsrc[149:0], bsrc[160:150]};
    (* keep *) reg [161:0] hbr1;
`ifdef OT_HC_HUB_MUT
    always @(posedge clk) hbr1 <= {hs1[161:1], ~hs1[0]};   // MUTANT: chain 1 fold bit 0 inverted
`else
    always @(posedge clk) hbr1 <= hs1;
`endif
    assign hb1 = hbr1;
    wire [161:0] hs2 = {bsrc[161], bsrc[138:0], bsrc[160:139]};
    (* keep *) reg [161:0] hbr2;
    always @(posedge clk) hbr2 <= hs2;
    assign hb2 = hbr2;
    wire [161:0] hs3 = {bsrc[161], bsrc[127:0], bsrc[160:128]};
    (* keep *) reg [161:0] hbr3;
    always @(posedge clk) hbr3 <= hs3;
    assign hb3 = hbr3;
    (* keep *) reg [255:0] hqi0;  always @(posedge clk) hqi0 <= hq0;
    (* keep *) reg [255:0] hqi1;  always @(posedge clk) hqi1 <= hq1;
    (* keep *) reg [255:0] hqi2;  always @(posedge clk) hqi2 <= hq2;
    (* keep *) reg [255:0] hqi3;  always @(posedge clk) hqi3 <= hq3;
    (* keep *) reg [1023:0] to;  always @(posedge clk) to <= {hqi3, hqi2, hqi1, hqi0};
    assign t_sfu = to;
endmodule
