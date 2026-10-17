# OT_CLOCK_ENTRY_DOMAIN_API_VERSION 1
# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.
set ::ot_ce_leaf_roots 1
set ::ot_ce_related_data 0
set ::ot_ce_refs [dict create ]
set ::ot_ce_counts [dict create ]
set ::ot_ce_domains [dict create {core} {clock core_clk io_budget_ps 166.667 inputs {{stream_rst_n} {sm_stream} {vm_v} {vm_bank} {vm_epoch} {vm_row} {vm_col} {wbw_v} {wbw_base} {wbw_total}} outputs {{fill_v} {fill_bank} {fill_slot} {fill_epoch} {fill_data} {fault}}} {hbm} {clock ot_io_hbm io_budget_ps 204.8 inputs {{hbm_rst_n} {sm_hbm} {g_k_v} {g_k_addr} {g_k_len} {g_k_tag} {g_k_we} {g_k_wdata} {g_k_wstrb} {g_kr_rdy} {c_k_rdy} {c_k_wr_done} {c_kr_v} {c_kr_tag} {c_kr_beat} {c_kr_data} {w_k_v} {w_k_addr} {w_k_wdata}} outputs {{g_k_rdy} {g_k_wr_done} {g_kr_v} {g_kr_tag} {g_kr_beat} {g_kr_data} {c_k_v} {c_k_addr} {c_k_len} {c_k_tag} {c_k_we} {c_k_wdata} {c_k_wstrb} {c_kr_rdy} {w_k_rdy} {w_k_wr_done}}}]
set ::ot_ce_source_domains [dict create {stream_clk} {core} {hbm_clk} {hbm}]
set ::ot_ce_explicit_domains 1
set ::ot_ce_cts_roots {{stream_clk} {hbm_clk}}
set ::ot_ce_ports {{stream_clk} {hbm_clk}}
set ::ot_ag_fifo_domains [dict create {lane[0].u_fill} {hbm core} {lane[1].u_fill} {hbm core} {lane[2].u_fill} {hbm core} {lane[3].u_fill} {hbm core} {u_cmd} {core hbm} {u_fault_cdc.u_status} {hbm core} {u_wcmd} {core hbm}]
set ::ot_ag_pointer_msb [dict create {lane[0].u_fill} 3 {lane[1].u_fill} 3 {lane[2].u_fill} 3 {lane[3].u_fill} 3 {u_cmd} 2 {u_fault_cdc.u_status} 2 {u_wcmd} 2]
set ::ot_ag_targets [dict create {lane[0].u_fill} {{278} {{fill_bank[0]}} {256} {{fill_slot[0]}} {257} {{fill_slot[1]}} {258} {{fill_slot[2]}} {259} {{fill_slot[3]}} {260} {{fill_slot[4]}} {261} {{fill_slot[5]}} {262} {{fill_epoch[0]}} {263} {{fill_epoch[1]}} {264} {{fill_epoch[2]}} {265} {{fill_epoch[3]}} {266} {{fill_epoch[4]}} {267} {{fill_epoch[5]}} {268} {{fill_epoch[6]}} {269} {{fill_epoch[7]}} {270} {{fill_epoch[8]}} {271} {{fill_epoch[9]}} {272} {{fill_epoch[10]}} {273} {{fill_epoch[11]}} {274} {{fill_epoch[12]}} {275} {{fill_epoch[13]}} {276} {{fill_epoch[14]}} {277} {{fill_epoch[15]}} {0} {{fill_data[0]}} {1} {{fill_data[1]}} {2} {{fill_data[2]}} {3} {{fill_data[3]}} {4} {{fill_data[4]}} {5} {{fill_data[5]}} {6} {{fill_data[6]}} {7} {{fill_data[7]}} {8} {{fill_data[8]}} {9} {{fill_data[9]}} {10} {{fill_data[10]}} {11} {{fill_data[11]}} {12} {{fill_data[12]}} {13} {{fill_data[13]}} {14} {{fill_data[14]}} {15} {{fill_data[15]}} {16} {{fill_data[16]}} {17} {{fill_data[17]}} {18} {{fill_data[18]}} {19} {{fill_data[19]}} {20} {{fill_data[20]}} {21} {{fill_data[21]}} {22} {{fill_data[22]}} {23} {{fill_data[23]}} {24} {{fill_data[24]}} {25} {{fill_data[25]}} {26} {{fill_data[26]}} {27} {{fill_data[27]}} {28} {{fill_data[28]}} {29} {{fill_data[29]}} {30} {{fill_data[30]}} {31} {{fill_data[31]}} {32} {{fill_data[32]}} {33} {{fill_data[33]}} {34} {{fill_data[34]}} {35} {{fill_data[35]}} {36} {{fill_data[36]}} {37} {{fill_data[37]}} {38} {{fill_data[38]}} {39} {{fill_data[39]}} {40} {{fill_data[40]}} {41} {{fill_data[41]}} {42} {{fill_data[42]}} {43} {{fill_data[43]}} {44} {{fill_data[44]}} {45} {{fill_data[45]}} {46} {{fill_data[46]}} {47} {{fill_data[47]}} {48} {{fill_data[48]}} {49} {{fill_data[49]}} {50} {{fill_data[50]}} {51} {{fill_data[51]}} {52} {{fill_data[52]}} {53} {{fill_data[53]}} {54} {{fill_data[54]}} {55} {{fill_data[55]}} {56} {{fill_data[56]}} {57} {{fill_data[57]}} {58} {{fill_data[58]}} {59} {{fill_data[59]}} {60} {{fill_data[60]}} {61} {{fill_data[61]}} {62} {{fill_data[62]}} {63} {{fill_data[63]}} {64} {{fill_data[64]}} {65} {{fill_data[65]}} {66} {{fill_data[66]}} {67} {{fill_data[67]}} {68} {{fill_data[68]}} {69} {{fill_data[69]}} {70} {{fill_data[70]}} {71} {{fill_data[71]}} {72} {{fill_data[72]}} {73} {{fill_data[73]}} {74} {{fill_data[74]}} {75} {{fill_data[75]}} {76} {{fill_data[76]}} {77} {{fill_data[77]}} {78} {{fill_data[78]}} {79} {{fill_data[79]}} {80} {{fill_data[80]}} {81} {{fill_data[81]}} {82} {{fill_data[82]}} {83} {{fill_data[83]}} {84} {{fill_data[84]}} {85} {{fill_data[85]}} {86} {{fill_data[86]}} {87} {{fill_data[87]}} {88} {{fill_data[88]}} {89} {{fill_data[89]}} {90} {{fill_data[90]}} {91} {{fill_data[91]}} {92} {{fill_data[92]}} {93} {{fill_data[93]}} {94} {{fill_data[94]}} {95} {{fill_data[95]}} {96} {{fill_data[96]}} {97} {{fill_data[97]}} {98} {{fill_data[98]}} {99} {{fill_data[99]}} {100} {{fill_data[100]}} {101} {{fill_data[101]}} {102} {{fill_data[102]}} {103} {{fill_data[103]}} {104} {{fill_data[104]}} {105} {{fill_data[105]}} {106} {{fill_data[106]}} {107} {{fill_data[107]}} {108} {{fill_data[108]}} {109} {{fill_data[109]}} {110} {{fill_data[110]}} {111} {{fill_data[111]}} {112} {{fill_data[112]}} {113} {{fill_data[113]}} {114} {{fill_data[114]}} {115} {{fill_data[115]}} {116} {{fill_data[116]}} {117} {{fill_data[117]}} {118} {{fill_data[118]}} {119} {{fill_data[119]}} {120} {{fill_data[120]}} {121} {{fill_data[121]}} {122} {{fill_data[122]}} {123} {{fill_data[123]}} {124} {{fill_data[124]}} {125} {{fill_data[125]}} {126} {{fill_data[126]}} {127} {{fill_data[127]}} {128} {{fill_data[128]}} {129} {{fill_data[129]}} {130} {{fill_data[130]}} {131} {{fill_data[131]}} {132} {{fill_data[132]}} {133} {{fill_data[133]}} {134} {{fill_data[134]}} {135} {{fill_data[135]}} {136} {{fill_data[136]}} {137} {{fill_data[137]}} {138} {{fill_data[138]}} {139} {{fill_data[139]}} {140} {{fill_data[140]}} {141} {{fill_data[141]}} {142} {{fill_data[142]}} {143} {{fill_data[143]}} {144} {{fill_data[144]}} {145} {{fill_data[145]}} {146} {{fill_data[146]}} {147} {{fill_data[147]}} {148} {{fill_data[148]}} {149} {{fill_data[149]}} {150} {{fill_data[150]}} {151} {{fill_data[151]}} {152} {{fill_data[152]}} {153} {{fill_data[153]}} {154} {{fill_data[154]}} {155} {{fill_data[155]}} {156} {{fill_data[156]}} {157} {{fill_data[157]}} {158} {{fill_data[158]}} {159} {{fill_data[159]}} {160} {{fill_data[160]}} {161} {{fill_data[161]}} {162} {{fill_data[162]}} {163} {{fill_data[163]}} {164} {{fill_data[164]}} {165} {{fill_data[165]}} {166} {{fill_data[166]}} {167} {{fill_data[167]}} {168} {{fill_data[168]}} {169} {{fill_data[169]}} {170} {{fill_data[170]}} {171} {{fill_data[171]}} {172} {{fill_data[172]}} {173} {{fill_data[173]}} {174} {{fill_data[174]}} {175} {{fill_data[175]}} {176} {{fill_data[176]}} {177} {{fill_data[177]}} {178} {{fill_data[178]}} {179} {{fill_data[179]}} {180} {{fill_data[180]}} {181} {{fill_data[181]}} {182} {{fill_data[182]}} {183} {{fill_data[183]}} {184} {{fill_data[184]}} {185} {{fill_data[185]}} {186} {{fill_data[186]}} {187} {{fill_data[187]}} {188} {{fill_data[188]}} {189} {{fill_data[189]}} {190} {{fill_data[190]}} {191} {{fill_data[191]}} {192} {{fill_data[192]}} {193} {{fill_data[193]}} {194} {{fill_data[194]}} {195} {{fill_data[195]}} {196} {{fill_data[196]}} {197} {{fill_data[197]}} {198} {{fill_data[198]}} {199} {{fill_data[199]}} {200} {{fill_data[200]}} {201} {{fill_data[201]}} {202} {{fill_data[202]}} {203} {{fill_data[203]}} {204} {{fill_data[204]}} {205} {{fill_data[205]}} {206} {{fill_data[206]}} {207} {{fill_data[207]}} {208} {{fill_data[208]}} {209} {{fill_data[209]}} {210} {{fill_data[210]}} {211} {{fill_data[211]}} {212} {{fill_data[212]}} {213} {{fill_data[213]}} {214} {{fill_data[214]}} {215} {{fill_data[215]}} {216} {{fill_data[216]}} {217} {{fill_data[217]}} {218} {{fill_data[218]}} {219} {{fill_data[219]}} {220} {{fill_data[220]}} {221} {{fill_data[221]}} {222} {{fill_data[222]}} {223} {{fill_data[223]}} {224} {{fill_data[224]}} {225} {{fill_data[225]}} {226} {{fill_data[226]}} {227} {{fill_data[227]}} {228} {{fill_data[228]}} {229} {{fill_data[229]}} {230} {{fill_data[230]}} {231} {{fill_data[231]}} {232} {{fill_data[232]}} {233} {{fill_data[233]}} {234} {{fill_data[234]}} {235} {{fill_data[235]}} {236} {{fill_data[236]}} {237} {{fill_data[237]}} {238} {{fill_data[238]}} {239} {{fill_data[239]}} {240} {{fill_data[240]}} {241} {{fill_data[241]}} {242} {{fill_data[242]}} {243} {{fill_data[243]}} {244} {{fill_data[244]}} {245} {{fill_data[245]}} {246} {{fill_data[246]}} {247} {{fill_data[247]}} {248} {{fill_data[248]}} {249} {{fill_data[249]}} {250} {{fill_data[250]}} {251} {{fill_data[251]}} {252} {{fill_data[252]}} {253} {{fill_data[253]}} {254} {{fill_data[254]}} {255} {{fill_data[255]}}} {lane[1].u_fill} {{278} {{fill_bank[1]}} {256} {{fill_slot[6]}} {257} {{fill_slot[7]}} {258} {{fill_slot[8]}} {259} {{fill_slot[9]}} {260} {{fill_slot[10]}} {261} {{fill_slot[11]}} {262} {{fill_epoch[16]}} {263} {{fill_epoch[17]}} {264} {{fill_epoch[18]}} {265} {{fill_epoch[19]}} {266} {{fill_epoch[20]}} {267} {{fill_epoch[21]}} {268} {{fill_epoch[22]}} {269} {{fill_epoch[23]}} {270} {{fill_epoch[24]}} {271} {{fill_epoch[25]}} {272} {{fill_epoch[26]}} {273} {{fill_epoch[27]}} {274} {{fill_epoch[28]}} {275} {{fill_epoch[29]}} {276} {{fill_epoch[30]}} {277} {{fill_epoch[31]}} {0} {{fill_data[256]}} {1} {{fill_data[257]}} {2} {{fill_data[258]}} {3} {{fill_data[259]}} {4} {{fill_data[260]}} {5} {{fill_data[261]}} {6} {{fill_data[262]}} {7} {{fill_data[263]}} {8} {{fill_data[264]}} {9} {{fill_data[265]}} {10} {{fill_data[266]}} {11} {{fill_data[267]}} {12} {{fill_data[268]}} {13} {{fill_data[269]}} {14} {{fill_data[270]}} {15} {{fill_data[271]}} {16} {{fill_data[272]}} {17} {{fill_data[273]}} {18} {{fill_data[274]}} {19} {{fill_data[275]}} {20} {{fill_data[276]}} {21} {{fill_data[277]}} {22} {{fill_data[278]}} {23} {{fill_data[279]}} {24} {{fill_data[280]}} {25} {{fill_data[281]}} {26} {{fill_data[282]}} {27} {{fill_data[283]}} {28} {{fill_data[284]}} {29} {{fill_data[285]}} {30} {{fill_data[286]}} {31} {{fill_data[287]}} {32} {{fill_data[288]}} {33} {{fill_data[289]}} {34} {{fill_data[290]}} {35} {{fill_data[291]}} {36} {{fill_data[292]}} {37} {{fill_data[293]}} {38} {{fill_data[294]}} {39} {{fill_data[295]}} {40} {{fill_data[296]}} {41} {{fill_data[297]}} {42} {{fill_data[298]}} {43} {{fill_data[299]}} {44} {{fill_data[300]}} {45} {{fill_data[301]}} {46} {{fill_data[302]}} {47} {{fill_data[303]}} {48} {{fill_data[304]}} {49} {{fill_data[305]}} {50} {{fill_data[306]}} {51} {{fill_data[307]}} {52} {{fill_data[308]}} {53} {{fill_data[309]}} {54} {{fill_data[310]}} {55} {{fill_data[311]}} {56} {{fill_data[312]}} {57} {{fill_data[313]}} {58} {{fill_data[314]}} {59} {{fill_data[315]}} {60} {{fill_data[316]}} {61} {{fill_data[317]}} {62} {{fill_data[318]}} {63} {{fill_data[319]}} {64} {{fill_data[320]}} {65} {{fill_data[321]}} {66} {{fill_data[322]}} {67} {{fill_data[323]}} {68} {{fill_data[324]}} {69} {{fill_data[325]}} {70} {{fill_data[326]}} {71} {{fill_data[327]}} {72} {{fill_data[328]}} {73} {{fill_data[329]}} {74} {{fill_data[330]}} {75} {{fill_data[331]}} {76} {{fill_data[332]}} {77} {{fill_data[333]}} {78} {{fill_data[334]}} {79} {{fill_data[335]}} {80} {{fill_data[336]}} {81} {{fill_data[337]}} {82} {{fill_data[338]}} {83} {{fill_data[339]}} {84} {{fill_data[340]}} {85} {{fill_data[341]}} {86} {{fill_data[342]}} {87} {{fill_data[343]}} {88} {{fill_data[344]}} {89} {{fill_data[345]}} {90} {{fill_data[346]}} {91} {{fill_data[347]}} {92} {{fill_data[348]}} {93} {{fill_data[349]}} {94} {{fill_data[350]}} {95} {{fill_data[351]}} {96} {{fill_data[352]}} {97} {{fill_data[353]}} {98} {{fill_data[354]}} {99} {{fill_data[355]}} {100} {{fill_data[356]}} {101} {{fill_data[357]}} {102} {{fill_data[358]}} {103} {{fill_data[359]}} {104} {{fill_data[360]}} {105} {{fill_data[361]}} {106} {{fill_data[362]}} {107} {{fill_data[363]}} {108} {{fill_data[364]}} {109} {{fill_data[365]}} {110} {{fill_data[366]}} {111} {{fill_data[367]}} {112} {{fill_data[368]}} {113} {{fill_data[369]}} {114} {{fill_data[370]}} {115} {{fill_data[371]}} {116} {{fill_data[372]}} {117} {{fill_data[373]}} {118} {{fill_data[374]}} {119} {{fill_data[375]}} {120} {{fill_data[376]}} {121} {{fill_data[377]}} {122} {{fill_data[378]}} {123} {{fill_data[379]}} {124} {{fill_data[380]}} {125} {{fill_data[381]}} {126} {{fill_data[382]}} {127} {{fill_data[383]}} {128} {{fill_data[384]}} {129} {{fill_data[385]}} {130} {{fill_data[386]}} {131} {{fill_data[387]}} {132} {{fill_data[388]}} {133} {{fill_data[389]}} {134} {{fill_data[390]}} {135} {{fill_data[391]}} {136} {{fill_data[392]}} {137} {{fill_data[393]}} {138} {{fill_data[394]}} {139} {{fill_data[395]}} {140} {{fill_data[396]}} {141} {{fill_data[397]}} {142} {{fill_data[398]}} {143} {{fill_data[399]}} {144} {{fill_data[400]}} {145} {{fill_data[401]}} {146} {{fill_data[402]}} {147} {{fill_data[403]}} {148} {{fill_data[404]}} {149} {{fill_data[405]}} {150} {{fill_data[406]}} {151} {{fill_data[407]}} {152} {{fill_data[408]}} {153} {{fill_data[409]}} {154} {{fill_data[410]}} {155} {{fill_data[411]}} {156} {{fill_data[412]}} {157} {{fill_data[413]}} {158} {{fill_data[414]}} {159} {{fill_data[415]}} {160} {{fill_data[416]}} {161} {{fill_data[417]}} {162} {{fill_data[418]}} {163} {{fill_data[419]}} {164} {{fill_data[420]}} {165} {{fill_data[421]}} {166} {{fill_data[422]}} {167} {{fill_data[423]}} {168} {{fill_data[424]}} {169} {{fill_data[425]}} {170} {{fill_data[426]}} {171} {{fill_data[427]}} {172} {{fill_data[428]}} {173} {{fill_data[429]}} {174} {{fill_data[430]}} {175} {{fill_data[431]}} {176} {{fill_data[432]}} {177} {{fill_data[433]}} {178} {{fill_data[434]}} {179} {{fill_data[435]}} {180} {{fill_data[436]}} {181} {{fill_data[437]}} {182} {{fill_data[438]}} {183} {{fill_data[439]}} {184} {{fill_data[440]}} {185} {{fill_data[441]}} {186} {{fill_data[442]}} {187} {{fill_data[443]}} {188} {{fill_data[444]}} {189} {{fill_data[445]}} {190} {{fill_data[446]}} {191} {{fill_data[447]}} {192} {{fill_data[448]}} {193} {{fill_data[449]}} {194} {{fill_data[450]}} {195} {{fill_data[451]}} {196} {{fill_data[452]}} {197} {{fill_data[453]}} {198} {{fill_data[454]}} {199} {{fill_data[455]}} {200} {{fill_data[456]}} {201} {{fill_data[457]}} {202} {{fill_data[458]}} {203} {{fill_data[459]}} {204} {{fill_data[460]}} {205} {{fill_data[461]}} {206} {{fill_data[462]}} {207} {{fill_data[463]}} {208} {{fill_data[464]}} {209} {{fill_data[465]}} {210} {{fill_data[466]}} {211} {{fill_data[467]}} {212} {{fill_data[468]}} {213} {{fill_data[469]}} {214} {{fill_data[470]}} {215} {{fill_data[471]}} {216} {{fill_data[472]}} {217} {{fill_data[473]}} {218} {{fill_data[474]}} {219} {{fill_data[475]}} {220} {{fill_data[476]}} {221} {{fill_data[477]}} {222} {{fill_data[478]}} {223} {{fill_data[479]}} {224} {{fill_data[480]}} {225} {{fill_data[481]}} {226} {{fill_data[482]}} {227} {{fill_data[483]}} {228} {{fill_data[484]}} {229} {{fill_data[485]}} {230} {{fill_data[486]}} {231} {{fill_data[487]}} {232} {{fill_data[488]}} {233} {{fill_data[489]}} {234} {{fill_data[490]}} {235} {{fill_data[491]}} {236} {{fill_data[492]}} {237} {{fill_data[493]}} {238} {{fill_data[494]}} {239} {{fill_data[495]}} {240} {{fill_data[496]}} {241} {{fill_data[497]}} {242} {{fill_data[498]}} {243} {{fill_data[499]}} {244} {{fill_data[500]}} {245} {{fill_data[501]}} {246} {{fill_data[502]}} {247} {{fill_data[503]}} {248} {{fill_data[504]}} {249} {{fill_data[505]}} {250} {{fill_data[506]}} {251} {{fill_data[507]}} {252} {{fill_data[508]}} {253} {{fill_data[509]}} {254} {{fill_data[510]}} {255} {{fill_data[511]}}} {lane[2].u_fill} {{278} {{fill_bank[2]}} {256} {{fill_slot[12]}} {257} {{fill_slot[13]}} {258} {{fill_slot[14]}} {259} {{fill_slot[15]}} {260} {{fill_slot[16]}} {261} {{fill_slot[17]}} {262} {{fill_epoch[32]}} {263} {{fill_epoch[33]}} {264} {{fill_epoch[34]}} {265} {{fill_epoch[35]}} {266} {{fill_epoch[36]}} {267} {{fill_epoch[37]}} {268} {{fill_epoch[38]}} {269} {{fill_epoch[39]}} {270} {{fill_epoch[40]}} {271} {{fill_epoch[41]}} {272} {{fill_epoch[42]}} {273} {{fill_epoch[43]}} {274} {{fill_epoch[44]}} {275} {{fill_epoch[45]}} {276} {{fill_epoch[46]}} {277} {{fill_epoch[47]}} {0} {{fill_data[512]}} {1} {{fill_data[513]}} {2} {{fill_data[514]}} {3} {{fill_data[515]}} {4} {{fill_data[516]}} {5} {{fill_data[517]}} {6} {{fill_data[518]}} {7} {{fill_data[519]}} {8} {{fill_data[520]}} {9} {{fill_data[521]}} {10} {{fill_data[522]}} {11} {{fill_data[523]}} {12} {{fill_data[524]}} {13} {{fill_data[525]}} {14} {{fill_data[526]}} {15} {{fill_data[527]}} {16} {{fill_data[528]}} {17} {{fill_data[529]}} {18} {{fill_data[530]}} {19} {{fill_data[531]}} {20} {{fill_data[532]}} {21} {{fill_data[533]}} {22} {{fill_data[534]}} {23} {{fill_data[535]}} {24} {{fill_data[536]}} {25} {{fill_data[537]}} {26} {{fill_data[538]}} {27} {{fill_data[539]}} {28} {{fill_data[540]}} {29} {{fill_data[541]}} {30} {{fill_data[542]}} {31} {{fill_data[543]}} {32} {{fill_data[544]}} {33} {{fill_data[545]}} {34} {{fill_data[546]}} {35} {{fill_data[547]}} {36} {{fill_data[548]}} {37} {{fill_data[549]}} {38} {{fill_data[550]}} {39} {{fill_data[551]}} {40} {{fill_data[552]}} {41} {{fill_data[553]}} {42} {{fill_data[554]}} {43} {{fill_data[555]}} {44} {{fill_data[556]}} {45} {{fill_data[557]}} {46} {{fill_data[558]}} {47} {{fill_data[559]}} {48} {{fill_data[560]}} {49} {{fill_data[561]}} {50} {{fill_data[562]}} {51} {{fill_data[563]}} {52} {{fill_data[564]}} {53} {{fill_data[565]}} {54} {{fill_data[566]}} {55} {{fill_data[567]}} {56} {{fill_data[568]}} {57} {{fill_data[569]}} {58} {{fill_data[570]}} {59} {{fill_data[571]}} {60} {{fill_data[572]}} {61} {{fill_data[573]}} {62} {{fill_data[574]}} {63} {{fill_data[575]}} {64} {{fill_data[576]}} {65} {{fill_data[577]}} {66} {{fill_data[578]}} {67} {{fill_data[579]}} {68} {{fill_data[580]}} {69} {{fill_data[581]}} {70} {{fill_data[582]}} {71} {{fill_data[583]}} {72} {{fill_data[584]}} {73} {{fill_data[585]}} {74} {{fill_data[586]}} {75} {{fill_data[587]}} {76} {{fill_data[588]}} {77} {{fill_data[589]}} {78} {{fill_data[590]}} {79} {{fill_data[591]}} {80} {{fill_data[592]}} {81} {{fill_data[593]}} {82} {{fill_data[594]}} {83} {{fill_data[595]}} {84} {{fill_data[596]}} {85} {{fill_data[597]}} {86} {{fill_data[598]}} {87} {{fill_data[599]}} {88} {{fill_data[600]}} {89} {{fill_data[601]}} {90} {{fill_data[602]}} {91} {{fill_data[603]}} {92} {{fill_data[604]}} {93} {{fill_data[605]}} {94} {{fill_data[606]}} {95} {{fill_data[607]}} {96} {{fill_data[608]}} {97} {{fill_data[609]}} {98} {{fill_data[610]}} {99} {{fill_data[611]}} {100} {{fill_data[612]}} {101} {{fill_data[613]}} {102} {{fill_data[614]}} {103} {{fill_data[615]}} {104} {{fill_data[616]}} {105} {{fill_data[617]}} {106} {{fill_data[618]}} {107} {{fill_data[619]}} {108} {{fill_data[620]}} {109} {{fill_data[621]}} {110} {{fill_data[622]}} {111} {{fill_data[623]}} {112} {{fill_data[624]}} {113} {{fill_data[625]}} {114} {{fill_data[626]}} {115} {{fill_data[627]}} {116} {{fill_data[628]}} {117} {{fill_data[629]}} {118} {{fill_data[630]}} {119} {{fill_data[631]}} {120} {{fill_data[632]}} {121} {{fill_data[633]}} {122} {{fill_data[634]}} {123} {{fill_data[635]}} {124} {{fill_data[636]}} {125} {{fill_data[637]}} {126} {{fill_data[638]}} {127} {{fill_data[639]}} {128} {{fill_data[640]}} {129} {{fill_data[641]}} {130} {{fill_data[642]}} {131} {{fill_data[643]}} {132} {{fill_data[644]}} {133} {{fill_data[645]}} {134} {{fill_data[646]}} {135} {{fill_data[647]}} {136} {{fill_data[648]}} {137} {{fill_data[649]}} {138} {{fill_data[650]}} {139} {{fill_data[651]}} {140} {{fill_data[652]}} {141} {{fill_data[653]}} {142} {{fill_data[654]}} {143} {{fill_data[655]}} {144} {{fill_data[656]}} {145} {{fill_data[657]}} {146} {{fill_data[658]}} {147} {{fill_data[659]}} {148} {{fill_data[660]}} {149} {{fill_data[661]}} {150} {{fill_data[662]}} {151} {{fill_data[663]}} {152} {{fill_data[664]}} {153} {{fill_data[665]}} {154} {{fill_data[666]}} {155} {{fill_data[667]}} {156} {{fill_data[668]}} {157} {{fill_data[669]}} {158} {{fill_data[670]}} {159} {{fill_data[671]}} {160} {{fill_data[672]}} {161} {{fill_data[673]}} {162} {{fill_data[674]}} {163} {{fill_data[675]}} {164} {{fill_data[676]}} {165} {{fill_data[677]}} {166} {{fill_data[678]}} {167} {{fill_data[679]}} {168} {{fill_data[680]}} {169} {{fill_data[681]}} {170} {{fill_data[682]}} {171} {{fill_data[683]}} {172} {{fill_data[684]}} {173} {{fill_data[685]}} {174} {{fill_data[686]}} {175} {{fill_data[687]}} {176} {{fill_data[688]}} {177} {{fill_data[689]}} {178} {{fill_data[690]}} {179} {{fill_data[691]}} {180} {{fill_data[692]}} {181} {{fill_data[693]}} {182} {{fill_data[694]}} {183} {{fill_data[695]}} {184} {{fill_data[696]}} {185} {{fill_data[697]}} {186} {{fill_data[698]}} {187} {{fill_data[699]}} {188} {{fill_data[700]}} {189} {{fill_data[701]}} {190} {{fill_data[702]}} {191} {{fill_data[703]}} {192} {{fill_data[704]}} {193} {{fill_data[705]}} {194} {{fill_data[706]}} {195} {{fill_data[707]}} {196} {{fill_data[708]}} {197} {{fill_data[709]}} {198} {{fill_data[710]}} {199} {{fill_data[711]}} {200} {{fill_data[712]}} {201} {{fill_data[713]}} {202} {{fill_data[714]}} {203} {{fill_data[715]}} {204} {{fill_data[716]}} {205} {{fill_data[717]}} {206} {{fill_data[718]}} {207} {{fill_data[719]}} {208} {{fill_data[720]}} {209} {{fill_data[721]}} {210} {{fill_data[722]}} {211} {{fill_data[723]}} {212} {{fill_data[724]}} {213} {{fill_data[725]}} {214} {{fill_data[726]}} {215} {{fill_data[727]}} {216} {{fill_data[728]}} {217} {{fill_data[729]}} {218} {{fill_data[730]}} {219} {{fill_data[731]}} {220} {{fill_data[732]}} {221} {{fill_data[733]}} {222} {{fill_data[734]}} {223} {{fill_data[735]}} {224} {{fill_data[736]}} {225} {{fill_data[737]}} {226} {{fill_data[738]}} {227} {{fill_data[739]}} {228} {{fill_data[740]}} {229} {{fill_data[741]}} {230} {{fill_data[742]}} {231} {{fill_data[743]}} {232} {{fill_data[744]}} {233} {{fill_data[745]}} {234} {{fill_data[746]}} {235} {{fill_data[747]}} {236} {{fill_data[748]}} {237} {{fill_data[749]}} {238} {{fill_data[750]}} {239} {{fill_data[751]}} {240} {{fill_data[752]}} {241} {{fill_data[753]}} {242} {{fill_data[754]}} {243} {{fill_data[755]}} {244} {{fill_data[756]}} {245} {{fill_data[757]}} {246} {{fill_data[758]}} {247} {{fill_data[759]}} {248} {{fill_data[760]}} {249} {{fill_data[761]}} {250} {{fill_data[762]}} {251} {{fill_data[763]}} {252} {{fill_data[764]}} {253} {{fill_data[765]}} {254} {{fill_data[766]}} {255} {{fill_data[767]}}} {lane[3].u_fill} {{278} {{fill_bank[3]}} {256} {{fill_slot[18]}} {257} {{fill_slot[19]}} {258} {{fill_slot[20]}} {259} {{fill_slot[21]}} {260} {{fill_slot[22]}} {261} {{fill_slot[23]}} {262} {{fill_epoch[48]}} {263} {{fill_epoch[49]}} {264} {{fill_epoch[50]}} {265} {{fill_epoch[51]}} {266} {{fill_epoch[52]}} {267} {{fill_epoch[53]}} {268} {{fill_epoch[54]}} {269} {{fill_epoch[55]}} {270} {{fill_epoch[56]}} {271} {{fill_epoch[57]}} {272} {{fill_epoch[58]}} {273} {{fill_epoch[59]}} {274} {{fill_epoch[60]}} {275} {{fill_epoch[61]}} {276} {{fill_epoch[62]}} {277} {{fill_epoch[63]}} {0} {{fill_data[768]}} {1} {{fill_data[769]}} {2} {{fill_data[770]}} {3} {{fill_data[771]}} {4} {{fill_data[772]}} {5} {{fill_data[773]}} {6} {{fill_data[774]}} {7} {{fill_data[775]}} {8} {{fill_data[776]}} {9} {{fill_data[777]}} {10} {{fill_data[778]}} {11} {{fill_data[779]}} {12} {{fill_data[780]}} {13} {{fill_data[781]}} {14} {{fill_data[782]}} {15} {{fill_data[783]}} {16} {{fill_data[784]}} {17} {{fill_data[785]}} {18} {{fill_data[786]}} {19} {{fill_data[787]}} {20} {{fill_data[788]}} {21} {{fill_data[789]}} {22} {{fill_data[790]}} {23} {{fill_data[791]}} {24} {{fill_data[792]}} {25} {{fill_data[793]}} {26} {{fill_data[794]}} {27} {{fill_data[795]}} {28} {{fill_data[796]}} {29} {{fill_data[797]}} {30} {{fill_data[798]}} {31} {{fill_data[799]}} {32} {{fill_data[800]}} {33} {{fill_data[801]}} {34} {{fill_data[802]}} {35} {{fill_data[803]}} {36} {{fill_data[804]}} {37} {{fill_data[805]}} {38} {{fill_data[806]}} {39} {{fill_data[807]}} {40} {{fill_data[808]}} {41} {{fill_data[809]}} {42} {{fill_data[810]}} {43} {{fill_data[811]}} {44} {{fill_data[812]}} {45} {{fill_data[813]}} {46} {{fill_data[814]}} {47} {{fill_data[815]}} {48} {{fill_data[816]}} {49} {{fill_data[817]}} {50} {{fill_data[818]}} {51} {{fill_data[819]}} {52} {{fill_data[820]}} {53} {{fill_data[821]}} {54} {{fill_data[822]}} {55} {{fill_data[823]}} {56} {{fill_data[824]}} {57} {{fill_data[825]}} {58} {{fill_data[826]}} {59} {{fill_data[827]}} {60} {{fill_data[828]}} {61} {{fill_data[829]}} {62} {{fill_data[830]}} {63} {{fill_data[831]}} {64} {{fill_data[832]}} {65} {{fill_data[833]}} {66} {{fill_data[834]}} {67} {{fill_data[835]}} {68} {{fill_data[836]}} {69} {{fill_data[837]}} {70} {{fill_data[838]}} {71} {{fill_data[839]}} {72} {{fill_data[840]}} {73} {{fill_data[841]}} {74} {{fill_data[842]}} {75} {{fill_data[843]}} {76} {{fill_data[844]}} {77} {{fill_data[845]}} {78} {{fill_data[846]}} {79} {{fill_data[847]}} {80} {{fill_data[848]}} {81} {{fill_data[849]}} {82} {{fill_data[850]}} {83} {{fill_data[851]}} {84} {{fill_data[852]}} {85} {{fill_data[853]}} {86} {{fill_data[854]}} {87} {{fill_data[855]}} {88} {{fill_data[856]}} {89} {{fill_data[857]}} {90} {{fill_data[858]}} {91} {{fill_data[859]}} {92} {{fill_data[860]}} {93} {{fill_data[861]}} {94} {{fill_data[862]}} {95} {{fill_data[863]}} {96} {{fill_data[864]}} {97} {{fill_data[865]}} {98} {{fill_data[866]}} {99} {{fill_data[867]}} {100} {{fill_data[868]}} {101} {{fill_data[869]}} {102} {{fill_data[870]}} {103} {{fill_data[871]}} {104} {{fill_data[872]}} {105} {{fill_data[873]}} {106} {{fill_data[874]}} {107} {{fill_data[875]}} {108} {{fill_data[876]}} {109} {{fill_data[877]}} {110} {{fill_data[878]}} {111} {{fill_data[879]}} {112} {{fill_data[880]}} {113} {{fill_data[881]}} {114} {{fill_data[882]}} {115} {{fill_data[883]}} {116} {{fill_data[884]}} {117} {{fill_data[885]}} {118} {{fill_data[886]}} {119} {{fill_data[887]}} {120} {{fill_data[888]}} {121} {{fill_data[889]}} {122} {{fill_data[890]}} {123} {{fill_data[891]}} {124} {{fill_data[892]}} {125} {{fill_data[893]}} {126} {{fill_data[894]}} {127} {{fill_data[895]}} {128} {{fill_data[896]}} {129} {{fill_data[897]}} {130} {{fill_data[898]}} {131} {{fill_data[899]}} {132} {{fill_data[900]}} {133} {{fill_data[901]}} {134} {{fill_data[902]}} {135} {{fill_data[903]}} {136} {{fill_data[904]}} {137} {{fill_data[905]}} {138} {{fill_data[906]}} {139} {{fill_data[907]}} {140} {{fill_data[908]}} {141} {{fill_data[909]}} {142} {{fill_data[910]}} {143} {{fill_data[911]}} {144} {{fill_data[912]}} {145} {{fill_data[913]}} {146} {{fill_data[914]}} {147} {{fill_data[915]}} {148} {{fill_data[916]}} {149} {{fill_data[917]}} {150} {{fill_data[918]}} {151} {{fill_data[919]}} {152} {{fill_data[920]}} {153} {{fill_data[921]}} {154} {{fill_data[922]}} {155} {{fill_data[923]}} {156} {{fill_data[924]}} {157} {{fill_data[925]}} {158} {{fill_data[926]}} {159} {{fill_data[927]}} {160} {{fill_data[928]}} {161} {{fill_data[929]}} {162} {{fill_data[930]}} {163} {{fill_data[931]}} {164} {{fill_data[932]}} {165} {{fill_data[933]}} {166} {{fill_data[934]}} {167} {{fill_data[935]}} {168} {{fill_data[936]}} {169} {{fill_data[937]}} {170} {{fill_data[938]}} {171} {{fill_data[939]}} {172} {{fill_data[940]}} {173} {{fill_data[941]}} {174} {{fill_data[942]}} {175} {{fill_data[943]}} {176} {{fill_data[944]}} {177} {{fill_data[945]}} {178} {{fill_data[946]}} {179} {{fill_data[947]}} {180} {{fill_data[948]}} {181} {{fill_data[949]}} {182} {{fill_data[950]}} {183} {{fill_data[951]}} {184} {{fill_data[952]}} {185} {{fill_data[953]}} {186} {{fill_data[954]}} {187} {{fill_data[955]}} {188} {{fill_data[956]}} {189} {{fill_data[957]}} {190} {{fill_data[958]}} {191} {{fill_data[959]}} {192} {{fill_data[960]}} {193} {{fill_data[961]}} {194} {{fill_data[962]}} {195} {{fill_data[963]}} {196} {{fill_data[964]}} {197} {{fill_data[965]}} {198} {{fill_data[966]}} {199} {{fill_data[967]}} {200} {{fill_data[968]}} {201} {{fill_data[969]}} {202} {{fill_data[970]}} {203} {{fill_data[971]}} {204} {{fill_data[972]}} {205} {{fill_data[973]}} {206} {{fill_data[974]}} {207} {{fill_data[975]}} {208} {{fill_data[976]}} {209} {{fill_data[977]}} {210} {{fill_data[978]}} {211} {{fill_data[979]}} {212} {{fill_data[980]}} {213} {{fill_data[981]}} {214} {{fill_data[982]}} {215} {{fill_data[983]}} {216} {{fill_data[984]}} {217} {{fill_data[985]}} {218} {{fill_data[986]}} {219} {{fill_data[987]}} {220} {{fill_data[988]}} {221} {{fill_data[989]}} {222} {{fill_data[990]}} {223} {{fill_data[991]}} {224} {{fill_data[992]}} {225} {{fill_data[993]}} {226} {{fill_data[994]}} {227} {{fill_data[995]}} {228} {{fill_data[996]}} {229} {{fill_data[997]}} {230} {{fill_data[998]}} {231} {{fill_data[999]}} {232} {{fill_data[1000]}} {233} {{fill_data[1001]}} {234} {{fill_data[1002]}} {235} {{fill_data[1003]}} {236} {{fill_data[1004]}} {237} {{fill_data[1005]}} {238} {{fill_data[1006]}} {239} {{fill_data[1007]}} {240} {{fill_data[1008]}} {241} {{fill_data[1009]}} {242} {{fill_data[1010]}} {243} {{fill_data[1011]}} {244} {{fill_data[1012]}} {245} {{fill_data[1013]}} {246} {{fill_data[1014]}} {247} {{fill_data[1015]}} {248} {{fill_data[1016]}} {249} {{fill_data[1017]}} {250} {{fill_data[1018]}} {251} {{fill_data[1019]}} {252} {{fill_data[1020]}} {253} {{fill_data[1021]}} {254} {{fill_data[1022]}} {255} {{fill_data[1023]}}} {u_cmd} {{0} {{cm_col[0]} {cmd_q[0]} {lane[0].col[1]} {lane[0].vm_addr[8]} {lane[1].col[1]} {lane[1].vm_addr[8]} {lane[2].col[1]} {lane[2].vm_addr[8]} {lane[3].col[1]} {lane[3].vm_addr[8]}} {1} {{cm_col[1]} {cmd_q[1]} {lane[0].col[2]} {lane[0].vm_addr[9]} {lane[1].col[2]} {lane[1].vm_addr[9]} {lane[2].col[2]} {lane[2].vm_addr[9]} {lane[3].col[2]} {lane[3].vm_addr[9]}} {2} {{cm_col[2]} {cmd_q[2]} {lane[0].col[3]} {lane[0].vm_addr[10]} {lane[1].col[3]} {lane[1].vm_addr[10]} {lane[2].col[3]} {lane[2].vm_addr[10]} {lane[3].col[3]} {lane[3].vm_addr[10]}} {3} {{cm_col[3]} {cmd_q[3]} {lane[0].col[4]} {lane[0].vm_addr[11]} {lane[1].col[4]} {lane[1].vm_addr[11]} {lane[2].col[4]} {lane[2].vm_addr[11]} {lane[3].col[4]} {lane[3].vm_addr[11]}} {4} {{cm_row[0]} {cmd_q[4]} {lane[0].bhi5[3]} {lane[0].vm_addr[15]} {lane[1].bhi5[3]} {lane[1].vm_addr[15]} {lane[2].bhi5[3]} {lane[2].vm_addr[15]} {lane[3].bhi5[3]} {lane[3].vm_addr[15]}} {5} {{cm_row[1]} {cmd_q[5]} {lane[0].bhi5[4]} {lane[0].vm_addr[16]} {lane[1].bhi5[4]} {lane[1].vm_addr[16]} {lane[2].bhi5[4]} {lane[2].vm_addr[16]} {lane[3].bhi5[4]} {lane[3].vm_addr[16]}} {6} {{cm_row[2]} {cmd_q[6]} {lane[0].vm_addr[17]} {lane[1].vm_addr[17]} {lane[2].vm_addr[17]} {lane[3].vm_addr[17]}} {7} {{cm_row[3]} {cmd_q[7]} {lane[0].vm_addr[18]} {lane[1].vm_addr[18]} {lane[2].vm_addr[18]} {lane[3].vm_addr[18]}} {8} {{cm_row[4]} {cmd_q[8]} {lane[0].vm_addr[19]} {lane[1].vm_addr[19]} {lane[2].vm_addr[19]} {lane[3].vm_addr[19]}} {9} {{cm_row[5]} {cmd_q[9]} {lane[0].vm_addr[20]} {lane[1].vm_addr[20]} {lane[2].vm_addr[20]} {lane[3].vm_addr[20]}} {10} {{cm_row[6]} {cmd_q[10]} {lane[0].vm_addr[21]} {lane[1].vm_addr[21]} {lane[2].vm_addr[21]} {lane[3].vm_addr[21]}} {11} {{cm_row[7]} {cmd_q[11]} {lane[0].vm_addr[22]} {lane[1].vm_addr[22]} {lane[2].vm_addr[22]} {lane[3].vm_addr[22]}} {12} {{cm_row[8]} {cmd_q[12]} {lane[0].vm_addr[23]} {lane[1].vm_addr[23]} {lane[2].vm_addr[23]} {lane[3].vm_addr[23]}} {13} {{cm_row[9]} {cmd_q[13]} {lane[0].vm_addr[24]} {lane[1].vm_addr[24]} {lane[2].vm_addr[24]} {lane[3].vm_addr[24]}} {14} {{cm_row[10]} {cmd_q[14]} {lane[0].vm_addr[25]} {lane[1].vm_addr[25]} {lane[2].vm_addr[25]} {lane[3].vm_addr[25]}} {15} {{cm_row[11]} {cmd_q[15]} {lane[0].vm_addr[26]} {lane[1].vm_addr[26]} {lane[2].vm_addr[26]} {lane[3].vm_addr[26]}} {16} {{cm_row[12]} {cmd_q[16]} {lane[0].vm_addr[27]} {lane[1].vm_addr[27]} {lane[2].vm_addr[27]} {lane[3].vm_addr[27]}} {17} {{cm_row[13]} {cmd_q[17]} {lane[0].vm_addr[28]} {lane[1].vm_addr[28]} {lane[2].vm_addr[28]} {lane[3].vm_addr[28]}} {18} {{cm_row[14]} {cmd_q[18]} {lane[0].vm_addr[29]} {lane[1].vm_addr[29]} {lane[2].vm_addr[29]} {lane[3].vm_addr[29]}} {19} {{cm_epoch[0]} {cmd_q[19]} {lane[0].f_d[262]} {lane[0].vm_tag[4]} {lane[1].f_d[262]} {lane[1].vm_tag[4]} {lane[2].f_d[262]} {lane[2].vm_tag[4]} {lane[3].f_d[262]} {lane[3].vm_tag[4]}} {20} {{cm_epoch[1]} {cmd_q[20]} {lane[0].f_d[263]} {lane[0].vm_tag[5]} {lane[1].f_d[263]} {lane[1].vm_tag[5]} {lane[2].f_d[263]} {lane[2].vm_tag[5]} {lane[3].f_d[263]} {lane[3].vm_tag[5]}} {21} {{cm_epoch[2]} {cmd_q[21]} {lane[0].f_d[264]} {lane[0].vm_tag[6]} {lane[1].f_d[264]} {lane[1].vm_tag[6]} {lane[2].f_d[264]} {lane[2].vm_tag[6]} {lane[3].f_d[264]} {lane[3].vm_tag[6]}} {22} {{cm_epoch[3]} {cmd_q[22]} {lane[0].f_d[265]} {lane[0].vm_tag[7]} {lane[1].f_d[265]} {lane[1].vm_tag[7]} {lane[2].f_d[265]} {lane[2].vm_tag[7]} {lane[3].f_d[265]} {lane[3].vm_tag[7]}} {23} {{cm_epoch[4]} {cmd_q[23]} {lane[0].f_d[266]} {lane[0].vm_tag[8]} {lane[1].f_d[266]} {lane[1].vm_tag[8]} {lane[2].f_d[266]} {lane[2].vm_tag[8]} {lane[3].f_d[266]} {lane[3].vm_tag[8]}} {24} {{cm_epoch[5]} {cmd_q[24]} {lane[0].f_d[267]} {lane[0].vm_tag[9]} {lane[1].f_d[267]} {lane[1].vm_tag[9]} {lane[2].f_d[267]} {lane[2].vm_tag[9]} {lane[3].f_d[267]} {lane[3].vm_tag[9]}} {25} {{cm_epoch[6]} {cmd_q[25]} {lane[0].f_d[268]} {lane[0].vm_tag[10]} {lane[1].f_d[268]} {lane[1].vm_tag[10]} {lane[2].f_d[268]} {lane[2].vm_tag[10]} {lane[3].f_d[268]} {lane[3].vm_tag[10]}} {26} {{cm_epoch[7]} {cmd_q[26]} {lane[0].f_d[269]} {lane[0].vm_tag[11]} {lane[1].f_d[269]} {lane[1].vm_tag[11]} {lane[2].f_d[269]} {lane[2].vm_tag[11]} {lane[3].f_d[269]} {lane[3].vm_tag[11]}} {27} {{cm_epoch[8]} {cmd_q[27]} {lane[0].f_d[270]} {lane[0].vm_tag[12]} {lane[1].f_d[270]} {lane[1].vm_tag[12]} {lane[2].f_d[270]} {lane[2].vm_tag[12]} {lane[3].f_d[270]} {lane[3].vm_tag[12]}} {28} {{cm_epoch[9]} {cmd_q[28]} {lane[0].f_d[271]} {lane[0].vm_tag[13]} {lane[1].f_d[271]} {lane[1].vm_tag[13]} {lane[2].f_d[271]} {lane[2].vm_tag[13]} {lane[3].f_d[271]} {lane[3].vm_tag[13]}} {29} {{cm_epoch[10]} {cmd_q[29]} {lane[0].f_d[272]} {lane[0].vm_tag[14]} {lane[1].f_d[272]} {lane[1].vm_tag[14]} {lane[2].f_d[272]} {lane[2].vm_tag[14]} {lane[3].f_d[272]} {lane[3].vm_tag[14]}} {30} {{cm_epoch[11]} {cmd_q[30]} {lane[0].f_d[273]} {lane[0].vm_tag[15]} {lane[1].f_d[273]} {lane[1].vm_tag[15]} {lane[2].f_d[273]} {lane[2].vm_tag[15]} {lane[3].f_d[273]} {lane[3].vm_tag[15]}} {31} {{cm_epoch[12]} {cmd_q[31]} {lane[0].f_d[274]} {lane[1].f_d[274]} {lane[2].f_d[274]} {lane[3].f_d[274]}} {32} {{cm_epoch[13]} {cmd_q[32]} {lane[0].f_d[275]} {lane[1].f_d[275]} {lane[2].f_d[275]} {lane[3].f_d[275]}} {33} {{cm_epoch[14]} {cmd_q[33]} {lane[0].f_d[276]} {lane[1].f_d[276]} {lane[2].f_d[276]} {lane[3].f_d[276]}} {34} {{cm_epoch[15]} {cmd_q[34]} {lane[0].f_d[277]} {lane[1].f_d[277]} {lane[2].f_d[277]} {lane[3].f_d[277]}} {35} {{cm_bank} {cmd_q[35]} {lane[0].f_d[278]} {lane[0].vm_tag[16]} {lane[1].f_d[278]} {lane[1].vm_tag[16]} {lane[2].f_d[278]} {lane[2].vm_tag[16]} {lane[3].f_d[278]} {lane[3].vm_tag[16]}}} {u_fault_cdc.u_status} {{0} {{hfault_stream} {u_fault_cdc.dst_fault} {u_fault_cdc.sticky}}} {u_wcmd} {{44} {{wc_base[0]} {wcmd_q[44]} {wend_q[0]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[1]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[2]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {32} {{wend_q[0]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[1]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[2]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {45} {{wc_base[1]} {wcmd_q[45]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[1]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[2]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {33} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[1]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[2]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {34} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[2]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {46} {{wc_base[2]} {wcmd_q[46]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[2]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {35} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {47} {{wc_base[3]} {wcmd_q[47]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[3]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {48} {{wc_base[4]} {wcmd_q[48]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {36} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[4]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {49} {{wc_base[5]} {wcmd_q[49]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {37} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[5]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {38} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {50} {{wc_base[6]} {wcmd_q[50]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[6]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {51} {{wc_base[7]} {wcmd_q[51]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {39} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[7]} {wend_q[8]} {wend_q[9]}} {40} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[8]} {wend_q[9]}} {52} {{wc_base[8]} {wcmd_q[52]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[8]} {wend_q[9]}} {53} {{wc_base[9]} {wcmd_q[53]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[9]}} {41} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]} {wend_q[9]}} {54} {{wc_base[10]} {wcmd_q[54]} {wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {42} {{wend_q[10]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {43} {{wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {55} {{wc_base[11]} {wcmd_q[55]} {wend_q[11]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {56} {{wc_base[12]} {wcmd_q[56]} {wend_q[12]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {57} {{wc_base[13]} {wcmd_q[57]} {wend_q[13]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {58} {{wc_base[14]} {wcmd_q[58]} {wend_q[14]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {59} {{wc_base[15]} {wcmd_q[59]} {wend_q[15]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {60} {{wc_base[16]} {wcmd_q[60]} {wend_q[16]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {61} {{wc_base[17]} {wcmd_q[61]} {wend_q[17]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {62} {{wc_base[18]} {wcmd_q[62]} {wend_q[18]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {63} {{wc_base[19]} {wcmd_q[63]} {wend_q[19]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {64} {{wc_base[20]} {wcmd_q[64]} {wend_q[20]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {65} {{wc_base[21]} {wcmd_q[65]} {wend_q[21]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {66} {{wc_base[22]} {wcmd_q[66]} {wend_q[22]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {67} {{wc_base[23]} {wcmd_q[67]} {wend_q[23]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {68} {{wc_base[24]} {wcmd_q[68]} {wend_q[24]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {69} {{wc_base[25]} {wcmd_q[69]} {wend_q[25]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {70} {{wc_base[26]} {wcmd_q[70]} {wend_q[26]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {71} {{wc_base[27]} {wcmd_q[71]} {wend_q[27]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {72} {{wc_base[28]} {wcmd_q[72]} {wend_q[28]} {wend_q[29]} {wend_q[30]}} {73} {{wc_base[29]} {wcmd_q[73]} {wend_q[29]} {wend_q[30]}} {0} {{lane[0].wn[0]} {wcmd_q[0]}} {1} {{lane[0].wn[1]} {wcmd_q[1]}} {2} {{lane[0].wn[2]} {wcmd_q[2]}} {3} {{lane[0].wn[3]} {wcmd_q[3]}} {4} {{lane[0].wn[4]} {wcmd_q[4]}} {5} {{lane[0].wn[5]} {wcmd_q[5]}} {6} {{lane[0].wn[6]} {wcmd_q[6]}} {7} {{lane[0].wn[7]} {wcmd_q[7]}} {8} {{lane[1].wn[0]} {wcmd_q[8]}} {9} {{lane[1].wn[1]} {wcmd_q[9]}} {10} {{lane[1].wn[2]} {wcmd_q[10]}} {11} {{lane[1].wn[3]} {wcmd_q[11]}} {12} {{lane[1].wn[4]} {wcmd_q[12]}} {13} {{lane[1].wn[5]} {wcmd_q[13]}} {14} {{lane[1].wn[6]} {wcmd_q[14]}} {15} {{lane[1].wn[7]} {wcmd_q[15]}} {16} {{lane[2].wn[0]} {wcmd_q[16]}} {17} {{lane[2].wn[1]} {wcmd_q[17]}} {18} {{lane[2].wn[2]} {wcmd_q[18]}} {19} {{lane[2].wn[3]} {wcmd_q[19]}} {20} {{lane[2].wn[4]} {wcmd_q[20]}} {21} {{lane[2].wn[5]} {wcmd_q[21]}} {22} {{lane[2].wn[6]} {wcmd_q[22]}} {23} {{lane[2].wn[7]} {wcmd_q[23]}} {24} {{lane[3].wn[0]} {wcmd_q[24]}} {25} {{lane[3].wn[1]} {wcmd_q[25]}} {26} {{lane[3].wn[2]} {wcmd_q[26]}} {27} {{lane[3].wn[3]} {wcmd_q[27]}} {28} {{lane[3].wn[4]} {wcmd_q[28]}} {29} {{lane[3].wn[5]} {wcmd_q[29]}} {30} {{lane[3].wn[6]} {wcmd_q[30]}} {31} {{lane[3].wn[7]} {wcmd_q[31]}}}]
set ::ot_ag_outputs [dict create {lane[0].u_fill} {} {lane[1].u_fill} {} {lane[2].u_fill} {} {lane[3].u_fill} {} {u_cmd} {} {u_fault_cdc.u_status} {} {u_wcmd} {}]
set ::ot_ag_primitive 0

# Source fingerprint is checked by the generator before this audited profile is
# emitted. Fail if mapping loses public register identities; never guess names.
set ::ot_ag_seen {}
proc ot_ag_public_nets {cell} {
  set result {}
  foreach p [get_pins -quiet -of_objects [get_cells $cell]] {
    if {[get_property $p direction] ne "output"} continue
    foreach net [get_nets -quiet -of_objects $p] {
      lappend result [string map {\\ {}} [get_full_name $net]]
    }
  }
  return $result
}
proc ot_ag_role {cell} {
  set roles {}
  foreach name [ot_ag_public_nets $cell] {
    dict for {scope domains} $::ot_ag_fifo_domains {
      if {$scope eq ""} {set local $name} else {
        set prefix "$scope."
        if {[string first $prefix $name]!=0} continue
        set local [string range $name [string length $prefix] end]
      }
      if {[regexp {^(wr_gray|rd_gray|wr_gray_r1|rd_gray_w1|wr_online|rd_online|wr_online_r1|rd_online_w1)(?:\[([0-9]+)\])?$} $local unused role index]} {
        if {$index eq ""} {set index 0}
        dict set roles [list $scope $role $index] 1
      }
      # The reviewed Gray pointer's MSB is exactly the binary pointer MSB.
      # Synthesis may keep only the binary public alias on that shared flop.
      # Lower binary bits are never admitted by this source-derived alias rule.
      if {[regexp {^(wr|rd)_bin\[([0-9]+)\]$} $local unused direction index] && $index == [dict get $::ot_ag_pointer_msb $scope]} {
        dict set roles [list $scope ${direction}_gray $index] 1
      }
      if {[regexp {^mem\[[0-9]+\](?:\[([0-9]+)\])?$} $local unused payload_bit]} {
        if {$payload_bit eq ""} {set payload_bit 0}
        dict set roles [list $scope payload $payload_bit] 1
      }
    }
  }
  if {[dict size $roles] != 1} {return {}}
  return [lindex [dict keys $roles] 0]
}
proc ot_ag_data_pin {pin} {
  return [expr {[lindex [split [get_full_name $pin] /] end] eq "D" && [get_property $pin direction] eq "input"}]
}
proc ot_ag_target {scope source_bit cell pin} {
  if {![ot_ag_data_pin $pin] || ![dict exists $::ot_ag_targets $scope $source_bit]} {return 0}
  set allowed [dict get $::ot_ag_targets $scope $source_bit]
  foreach name [ot_ag_public_nets $cell] {
    if {$name in $allowed} {return 1}
  }
  return 0
}
proc ot_ag_async_control {pin} {
  # Reset recovery/removal stays timed. A FIFO data/pointer publication must
  # never acquire an async-control exception by sharing a legitimate D target.
  foreach start [get_fanin -flat -startpoints_only -to $pin] {
    set cell [get_cells -quiet -of_objects $start]
    if {[llength $cell]!=1} continue
    if {[llength [ot_ag_role [get_full_name $cell]]]} {
      error "OT_ASYNC_GRAY: FIFO publication drives asynchronous control [get_full_name $pin]"
    }
  }
}
proc ot_ag_bound {start target} {
  # OpenSTA graph startpoints are register clock pins; exceptions and path
  # queries must begin at the actual launch register, not a clock input pin.
  set launch [get_cells -quiet -of_objects $start]
  if {[llength $launch] != 1} {error "OT_ASYNC_GRAY: missing unique launch register"}
  # Bound ALL Gray bits within the faster source period minus setup uncertainty;
  # this also bounds inter-bit skew below a source cycle. Payload is held by the
  # verified FIFO protocol, and receives the same conservative datapath budget.
  # No exception applies to any other path or either synchronizer's second stage.
  set_max_delay -ignore_clock_latency 773.333 -from $launch -to $target
  set_min_delay -ignore_clock_latency 0.0 -from $launch -to $target
  foreach kind {max min} {
    set paths [find_timing_paths -from $launch -to $target -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
    if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" && ![info exists ::ot_mm_active]} {
      puts "OT_ASYNC_GRAY PATH_DEFERRED [get_full_name $start] -> [get_full_name $target] $kind (strict at sign-off)"
      continue
    }
    if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
      error "OT_ASYNC_GRAY: missing finite bounded $kind path [get_full_name $start] -> [get_full_name $target]"
    }
  }
}
proc ot_ag_crossing {start pin source target source_domain target_domain} {
  lassign [ot_ag_role $source] scope sr source_bit
  if {![ot_ag_data_pin $pin]} {error "OT_ASYNC_GRAY: cross-domain control pin [get_full_name $pin]"}
  lassign [ot_ag_role $target] target_scope tr target_bit
  if {$sr eq "" || ![dict exists $::ot_ag_fifo_domains $scope]} {
    error "OT_ASYNC_GRAY: unapproved actual crossing $source -> $target"
  }
  lassign [dict get $::ot_ag_fifo_domains $scope] writer reader
  set permitted 0
  if {$scope eq $target_scope && $source_bit eq $target_bit} {
    if {[list $sr $tr] in {{wr_gray wr_gray_r1} {wr_online wr_online_r1}} && $source_domain eq $writer && $target_domain eq $reader} {set permitted 1}
    if {[list $sr $tr] in {{rd_gray rd_gray_w1} {rd_online rd_online_w1}} && $source_domain eq $reader && $target_domain eq $writer} {set permitted 1}
  }
  if {$sr eq "payload" && $source_domain eq $writer && $target_domain eq $reader && [ot_ag_target $scope $source_bit $target $pin]} {set permitted 1}
  if {!$permitted} {error "OT_ASYNC_GRAY: unapproved actual crossing $source -> $target ($scope $sr -> $target_scope $tr)"}
  ot_ag_bound $start $pin
  dict incr ::ot_ag_seen [list $scope $sr]
  puts "OT_ASYNC_GRAY BOUNDED $source -> $target"
}
proc ot_ag_payload {start port source name source_domain target_domain} {
  lassign [ot_ag_role $source] scope role source_bit
  if {$role ne "payload" || ![dict exists $::ot_ag_fifo_domains $scope]} {return 0}
  lassign [dict get $::ot_ag_fifo_domains $scope] writer reader
  if {$source_domain ne $writer || $target_domain ne $reader ||
      ![dict exists $::ot_ag_outputs $scope $source_bit] ||
      $name ni [dict get $::ot_ag_outputs $scope $source_bit]} {return 0}
  ot_ag_bound $start $port
  dict incr ::ot_ag_seen [list $scope payload]
  return 1
}
proc ot_ag_complete {} {
  dict for {scope domains} $::ot_ag_fifo_domains {
    foreach role {wr_gray rd_gray wr_online rd_online} {
      if {![dict exists $::ot_ag_seen [list $scope $role]]} {error "OT_ASYNC_GRAY: missing actual audited crossing $scope $role"}
    }
  }
  if {$::ot_ag_primitive && ![dict exists $::ot_ag_seen [list {} payload]]} {error "OT_ASYNC_GRAY: missing primitive payload crossing"}
  puts "OT_ASYNC_GRAY STRUCTURAL_PASS $::ot_ag_seen (bounded CDC; no physical closure claim)"
}


# Constants are proved from actual OpenDB connectivity and the loaded Liberty
# output functions. Cell/port names, case analysis and timing-graph constant
# pruning are never proofs. A cell output is constant when every loaded corner
# gives its master the same Liberty function and that function is a literal, or a
# combinational expression whose every variable is an input pin of the same
# instance on a net with no input port and exactly one driver that is itself
# constant (TIEHI/TIELO prove themselves through their literal function; a
# synthesis buffer/inverter or any gate of constants follows). Registers never
# qualify; unknown or unparsable functions fail closed.
proc ot_ce_constant_net {net seen remaining} {
  if {$remaining <= 0 || $net in {"" NULL}} {return 0}
  foreach port [$net getBTerms] {if {[$port getIoType] ne "OUTPUT"} {return 0}}
  set drivers {}
  foreach pin [$net getITerms] {if {[$pin isOutputSignal]} {lappend drivers $pin}}
  if {[llength $drivers] != 1} {return 0}
  return [ot_ce_constant_iterm [lindex $drivers 0] $seen $remaining]
}
proc ot_ce_constant_iterm {pin seen remaining} {
  if {$remaining <= 0 || ![$pin isOutputSignal]} {return 0}
  set inst [$pin getInst];set name "[$inst getName]/[[$pin getMTerm] getName]"
  if {[dict exists $seen $name]} {return 0}
  if {[info exists ::ot_ce_const_memo] && [dict exists $::ot_ce_const_memo $name]} {return [dict get $::ot_ce_const_memo $name]}
  dict set seen $name 1
  set result [ot_ce_constant_iterm_eval $inst $pin $seen $remaining]
  dict set ::ot_ce_const_memo $name $result
  return $result
}
proc ot_ce_constant_iterm_eval {inst pin seen remaining} {
  if {[info exists ::ot_ce_register_cells] && [dict exists $::ot_ce_register_cells [$inst getName]]} {return 0}
  set master [[$inst getMaster] getName];set output [[$pin getMTerm] getName]
  set functions {};set matched 0
  foreach library [get_libs -quiet *] {
    set cell [$library find_liberty_cell $master]
    if {$cell in {"" NULL}} continue
    set lp [$cell find_liberty_port $output]
    if {$lp in {"" NULL} || [sta::liberty_port_direction $lp] ne "output"} {return 0}
    dict set functions [string map {" " "" "\t" "" "\n" ""} [$lp function]] 1
    incr matched
  }
  if {!$matched || [dict size $functions] != 1} {return 0}
  set function [lindex [dict keys $functions] 0]
  if {$function in {0 1}} {return 1}
  if {$function eq "" || ![regexp {^[A-Za-z0-9_!'*&+|^()]+$} $function]} {return 0}
  set inputs [lsort -unique [regexp -all -inline {[A-Za-z_][A-Za-z0-9_]*} $function]]
  if {![llength $inputs]} {return 0}
  foreach input $inputs {
    set in [$inst findITerm $input]
    if {$in in {"" NULL} || ![$in isInputSignal]} {return 0}
    if {![ot_ce_constant_net [$in getNet] $seen [expr {$remaining-1}]]} {return 0}
  }
  return 1
}
# Timing startpoint -> constant proof. An output-port startpoint is followed to
# its net driver; an input port is never constant.
proc ot_ce_constant_cone {start} {
  set block [ord::get_db_block]
  if {[sta::object_type $start] eq "Port" || ([sta::object_type $start] eq "Pin" && [$start is_top_level_port])} {
    set port [$block findBTerm [get_full_name $start]]
    if {$port in {"" NULL} || [$port getIoType] ne "OUTPUT"} {return 0}
    return [ot_ce_constant_net [$port getNet] {} 64]
  }
  if {[sta::object_type $start] ne "Pin"} {return 0}
  set inst [$block findInst [get_full_name [$start instance]]]
  if {$inst in {"" NULL}} {return 0}
  set pin [$inst findITerm [get_property $start lib_pin_name]]
  if {$pin in {"" NULL}} {return 0}
  return [ot_ce_constant_iterm $pin {} 64]
}
# Classification is immutable during one ownership validation. Memoize only
# in the caller's local dictionary; no STA object/classification survives it.
proc ot_ce_startpoint_class {start purpose memo_name} {
  upvar 1 $memo_name memo
  set name [get_full_name $start]
  set key [list $purpose [sta::object_type $start] $name]
  if {[dict exists $memo $key]} {return [dict get $memo $key]}
  if {$purpose eq "input" && [llength [get_ports -quiet $name]]} {
    set result [list port $name]
  } elseif {$purpose eq "output" && [sta::object_type $start] eq "Pin" && [$start is_top_level_port]} {
    set result [list top_pin $name]
  } else {
    set result [list cell [get_full_name [get_cells -quiet -of_objects $start]]]
  }
  dict set memo $key $result
  return $result
}
# A multi-root leaf contains independent synchronous datapaths. Domain declarations
# are checked against the real synthesized timing graph, not trusted as metadata.
proc ot_ce_leaf_ownership {inputs outputs} {
  set expected {}
  dict for {domain info} $::ot_ce_domains {lappend expected [dict get $info clock]}
  for {set i 0} {$i < [llength $::ot_ce_ports]} {incr i} {lappend expected ot_entry_$i}
  set actual {}
  foreach c [all_clocks] {lappend actual [get_full_name $c]}
  if {[lsort $actual] ne [lsort $expected]} {error "OT_MULTI_ROOT: undeclared clock alias or relationship"}
  set ::ot_ag_seen {}
  set cells {}; set clocks {}; set crossing_pairs {}; set domain_roots {}
  foreach root $::ot_ce_ports {
    set domain [dict get $::ot_ce_source_domains $root]
    dict set domain_roots $domain $root
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $root]]
    foreach pin [all_registers -clock [get_full_name $clock] -clock_pins] {
      set cell [get_full_name [get_cells -of_objects $pin]]
      if {[dict exists $cells $cell]} { error "OT_MULTI_ROOT: duplicate clock ownership $cell" }
      dict set cells $cell $domain
    }
  }
  foreach pin [all_registers -clock_pins] {
    set cell [get_full_name [get_cells -of_objects $pin]]
    if {![dict exists $cells $cell]} { error "OT_MULTI_ROOT: unowned register $cell" }
  }
  set ::ot_ce_register_cells {}
  foreach r [all_registers -cells] {dict set ::ot_ce_register_cells [get_full_name $r] 1}
  set ::ot_ce_const_memo {}
  set startpoint_classes {}
  # OpenSTA's -data_pins population includes asynchronous clear/preset
  # controls. Classify these from the actual loaded Liberty sequential arcs,
  # never from port names or reset_ports. They retain recovery/removal timing;
  # only ordinary synchronous D/control paths require data-domain ownership.
  set async_pins {}
  foreach pin [all_registers -async_pins] {dict set async_pins [get_full_name $pin] 1}
  foreach pin [all_registers -data_pins] {
    if {[dict exists $async_pins [get_full_name $pin]]} {ot_ag_async_control $pin; continue}
    set cell [get_full_name [get_cells -of_objects $pin]]
    set expected [dict get $cells $cell]
    foreach start [get_fanin -flat -startpoints_only -to $pin] {
      lassign [ot_ce_startpoint_class $start input startpoint_classes] source_kind source
      if {$source_kind eq "port"} {
        set name [get_full_name $start]
        if {![dict exists $inputs $name] || [dict get $inputs $name] ne $expected} {
          error "OT_MULTI_ROOT: input $name has wrong domain for $cell"
        }
      } else {
        if {![dict exists $cells $source]} {
          if {[ot_ce_constant_cone $start]} {
            puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> [get_full_name $pin]"
            continue
          }
          error "OT_MULTI_ROOT: unowned data path $source -> $cell"
        }
        set source_domain [dict get $cells $source]
        if {$source_domain ne $expected} {
          ot_ag_crossing $start $pin $source $cell $source_domain $expected
          continue
          dict set crossing_pairs [list $source_domain $expected] 1
        }
      }
    }
  }
  dict for {name domain} $outputs {
    foreach start [get_fanin -flat -startpoints_only -to [get_ports $name]] {
      # A die-strap tie output (contract v1.2 tie_hi/tie_lo), possibly
      # synthesis-buffered, has no clock and no data domain to own; it must be
      # proved constant above. Registers and ports keep their domain checks.
      lassign [ot_ce_startpoint_class $start output startpoint_classes] source_kind source
      if {$source_kind eq "top_pin"} {
        if {[ot_ce_constant_cone $start]} {
          puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> $name"
          continue
        }
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain [get_full_name $start]"
      }
      if {![dict exists $cells $source] && [ot_ce_constant_cone $start]} {
        puts "OT_MULTI_ROOT LIBERTY_CONSTANT [get_full_name $start] -> $name"
        continue
      }
      if {![dict exists $cells $source] || [dict get $cells $source] ne $domain} {
        if {[dict exists $cells $source] && [ot_ag_payload $start [get_ports $name] $source $name [dict get $cells $source] $domain]} {continue}
        error "OT_MULTI_ROOT: output $name has wrong or unregistered source domain $source"
      }
    }
  }
  dict for {pair unused} $crossing_pairs {
    lassign $pair source_domain target_domain
    set source_root [dict get $domain_roots $source_domain]
    set target_root [dict get $domain_roots $target_domain]
    set from [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $source_root] -clock_pins]
    set to {}
    foreach pin [all_registers -clock ot_entry_[lsearch -exact $::ot_ce_ports $target_root] -data_pins] {
      if {![dict exists $async_pins [get_full_name $pin]]} {lappend to $pin}
    }
    foreach kind {max min} {
      set paths [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1]
      if {![llength $paths] && [info exists ::env(OT_HOLD_MM)] && $::env(OT_HOLD_MM) eq "1" &&
          ![info exists ::ot_mm_active]} {
        # Multi-mode route/gate (tools/orfs_hold_mm.tcl): this SDC is being read into mode ss BEFORE any scene is
        # defined, so the unscened default scene has no clocks and no path can be found yet.  The crossing population
        # above is structural (actual fanin) and unchanged; the finite-path proof runs strictly in every single-scene
        # read (non-MM stages, corner_sta / sign-off), which carries the timing claim.
        puts "OT_MULTI_ROOT RELATED_PATH_DEFERRED $source_domain -> $target_domain $kind (multi-mode read before scene definition; strict at sign-off)"
        continue
      }
      if {![llength $paths] || ![ot_ce_finite [get_property [lindex $paths 0] slack]]} {
        error "OT_MULTI_ROOT: related crossing lacks actual finite $kind STA path $source_domain -> $target_domain"
      }
      puts "OT_MULTI_ROOT RELATED_PATH $source_domain -> $target_domain $kind slack=[get_property [lindex $paths 0] slack] (ordinary synchronous timing retained)"
    }
  }
  ot_ag_complete
  puts "OT_MULTI_ROOT OWNERSHIP PASS roots=[llength $::ot_ce_cts_roots] registers=[dict size $cells] inputs=[dict size $inputs] outputs=[dict size $outputs] async_control_pins=[dict size $async_pins]"
}

proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  # WC is a scene label, not an actual library corner: option-B overlays WC
  # with TT. Bind the reference to actual loaded child Liberty objects.
  set found {}; set clock_cells {}
  # Physical-only taps/endcaps have no Liberty association. The clock corner
  # belongs to actual sequential clock sinks, not every physical instance.
  foreach pin [all_registers -clock_pins] {
    set cell [get_cells -quiet -of_objects $pin]
    if {[llength $cell] != 1 || $cell eq "NULL"} {error "OT_MULTI_ROOT: clock sink lacks one actual sequential cell"}
    dict set clock_cells [get_full_name $cell] $cell
  }
  if {![dict size $clock_cells]} {error "OT_MULTI_ROOT: no actual sequential cells for corner inference"}
  foreach cell [dict values $clock_cells] {
    set master [get_property $cell ref_name]
    set libcells [get_lib_cells -quiet -of_objects $cell]
    if {![llength $libcells] || "NULL" in $libcells} { error "OT_MULTI_ROOT: actual sequential cell $master has no loaded Liberty association" }
    foreach lc $libcells {
      set full [get_full_name $lc]
      if {![regexp -nocase {_(tt|ff|ss)/|_(tt|ff|ss)_} $full -> corner alt]} { error "OT_ENTRIES: unknown actual Liberty corner $full" }
      if {$corner eq ""} {set corner $alt}
      dict set found [string tolower $corner] 1
    }
  }
  if {[dict size $found] == 1} { return [lindex [dict keys $found] 0] }
  # A multi-mode database needs its actual setup corner or BC scene shim.
  if {[info exists ::env(OT_MM_SETUP_CORNER)]} {
    switch -nocase -- $::env(OT_MM_SETUP_CORNER) {
      TC - tt {set corner tt} BC - ff {set corner ff} WC - ss {set corner ss}
      default { error "OT_ENTRIES: unknown actual setup corner" }
    }
    if {[dict exists $found $corner]} { return $corner }
  }
  error "OT_ENTRIES: ambiguous actual loaded child corners [dict keys $found]"
}
# get_property pin arrival_max_rise is a DATA arrival query. On a clock-only
# macro pin it returns an infinity sentinel even with a finite propagated clock
# path. Read propagated clock tags in the current scene and remove the
# source waveform edge time; falling-edge-only registers include that phase.
proc ot_ce_finite {value} {
  return [expr {[string is double -strict $value] && ![regexp -nocase {inf|nan} $value]}]
}
proc ot_ce_clock_wire {pin clock} {
  set scene [get_property [sta::cmd_scene] name]
  set clock_name [get_full_name $clock]
  set by_transition [dict create rise {} fall {}]
  set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2 || ![ot_ce_finite [lindex $waveform 0]] ||
      ![ot_ce_finite [lindex $waveform 1]]} {
    error "OT_ENTRIES: invalid source clock waveform $clock_name"
  }
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach transition {rise fall} marker {^ v} {
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        # Sink transition and source clock edge are distinct (inverting trees).
        # Exclude data, ideal, other-scene and other-clock paths as before.
        set tag [$path tag]
        set edge [lindex $tag 4]
        if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${marker}max" ||
            [lindex $tag 3] ne $clock_name || $edge ni {^ v} ||
            [string first "(clock prop)" $tag] < 0} continue
        set arrival [sta::time_sta_ui [$path arrival]]
        if {![ot_ce_finite $arrival]} {
          $paths finish
          error "OT_ENTRIES: nonfinite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
        }
        set phase [lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]
        dict lappend by_transition $transition [expr {$arrival - $phase}]
      }
      $paths finish
    }
  }
  # Preserve the rising pin-transition reference. An inverted/negedge clock
  # may associate it with the falling source edge; remove that actual phase.
  # Fall-only pins remain measurable. Multiple same-transition tags fail.
  set values [dict get $by_transition rise]
  if {![llength $values]} {set values [dict get $by_transition fall]}
  if {[llength $values] != 1} {
    # Synthesis/floorplan have no extracted entry wire. This is solely a finite
    # pre-CTS diagnostic reference; routed gates must measure a clock path.
    if {![llength $values] && [info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
        (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
      puts "OT_ENTRIES PRE_CTS_ZERO_WIRE [get_full_name $pin] scene=$scene"
      return 0.0
    }
    error "OT_ENTRIES: missing unique finite propagated clock arrival on [get_full_name $pin] scene=$scene clock=$clock_name"
  }
  return [lindex $values 0]
}
# Match ck_insertion.py's exported insertion.json boundary population: input
# timing endpoints plus output timing launch registers, intersected with this root.
proc ot_ce_boundary_cells {} {
  set boundary {}
  set inputs [all_inputs -no_clocks]
  if {[llength $inputs]} {
    foreach path [find_timing_paths -path_delay max -from $inputs -to [all_registers -data_pins] -group_path_count 200000 -endpoint_path_count 1] {
      dict set boundary [regsub {/[^/]+$} [get_full_name [get_property $path endpoint]] {}] 1
    }
  }
  if {[llength [all_outputs]]} {
    foreach path [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_outputs] -group_path_count 200000 -endpoint_path_count 100000] {
      dict set boundary [regsub {/[^/]+$} [get_full_name [get_property $path startpoint]] {}] 1
    }
  }
  return $boundary
}
proc ot_ce_boundary_pins {pins boundary_cells} {
  set regs {}; set boundary {}
  foreach pin $pins {dict set regs [regsub {/[^/]+$} [get_full_name $pin] {}] $pin}
  dict for {name unused} $boundary_cells {
    if {[dict exists $regs $name]} {dict set boundary $name [dict get $regs $name]}
  }
  return [dict values $boundary]
}

proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  # Wires-only parents have no CTS tree to set this flag for us.
  # Ideal clocks silently report zero network arrival despite real entry wires.
  set_propagated_clock [get_clocks ot_entry_*]
  # Before CTS, a standard-cell root is still one unbuffered high-fanout
  # net. Propagating that net invents multi-ns skew and clock-pin slew;
  # its delay is not the tree that CTS will build. Keep only these declared
  # CTS roots ideal during the explicit pre-CTS diagnostic. Raw macro and
  # hardened-child entries retain actual entry-wire propagation. Routed
  # require-wire checks always propagate and measure every physical root.
  if {[info exists ::ot_ref_pre_cts] && $::ot_ref_pre_cts &&
      (![info exists ::ot_ce_require_wire] || !$::ot_ce_require_wire)} {
    foreach name $::ot_ce_cts_roots {
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      unset_propagated_clock $clock
      puts "OT_ENTRIES PRE_CTS_IDEAL_CTS_ROOT $name"
    }
  }
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || $name in $::ot_ce_cts_roots || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set wire [ot_ce_clock_wire $pin $clock]
      if {![ot_ce_finite $wire]} { error "OT_ENTRIES: nonfinite entry wire clock arrival on [get_full_name $pin]" }
      if {abs($wire) < 1.0e-9 && [info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
        # A zero arrival is admissible only if actual source and child pin are
        # physically coincident. Missing parasitics/ideal clocks cannot qualify.
        if {![llength [info commands ord::get_db_block]]} { error "OT_ENTRIES: zero wire lacks physical source/pin proof" }
        set block [ord::get_db_block]
        set bt [$block findBTerm $name]
        set it [$block findITerm [get_full_name $pin]]
        if {$bt eq "NULL" || $it eq "NULL"} { error "OT_ENTRIES: missing physical source/child clock pin" }
        set pb [$bt getBBox]; set ib [$it getBBox]
        set distance [expr {(abs(([$pb xMin]+[$pb xMax])-([$ib xMin]+[$ib xMax])) + abs(([$pb yMin]+[$pb yMax])-([$ib yMin]+[$ib yMax]))) / 2.0 / [$block getDbUnitsPerMicron]}]
        if {$distance > 0.001} { error "OT_ENTRIES: zero clock wire arrival despite $distance um source/pin separation on $name" }
        puts "OT_ENTRIES ZERO_WIRE_PROVEN $name [get_full_name $pin] distance=$distance"
      }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      set domain [dict get $::ot_ce_source_domains $name]
      set vc [get_clocks [dict get $::ot_ce_domains $domain clock]]
      if {abs([get_property $vc period]-[get_property $clock period])>0.001} { error "OT_ENTRIES: domain/source period mismatch $name" }
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean $domain]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  # Source latencies are zero for this whole measurement loop, and no STA
  # constraints/netlist change until rows are complete. Query the same bounded
  # boundary population once per apply/current corner, never across calls.
  set boundary_cells {}; set boundary_cells_ready 0
  # Each glue root owns a real CTS tree. Measure every propagated standard-cell
  # clock sink in the current scene; never substitute a declared/common phase.
  foreach name $::ot_ce_cts_roots {
    set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
    set pins [all_registers -clock [get_full_name $clock] -clock_pins]
    if {![llength $pins]} { error "OT_HYBRID: glue root $name has no actual sequential clock sinks" }
    set arrivals {}; set measured {}; set total 0.0
    foreach pin $pins {
      set cell [get_cells -of_objects $pin]
      set master [get_property $cell ref_name]
      if {[dict exists $::ot_ce_counts $master]} { error "OT_HYBRID: CTS root $name reaches a hard child" }
      set arrival [ot_ce_clock_wire $pin $clock]
      lappend arrivals $arrival
      dict set measured [get_full_name $pin] $arrival
      set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set tree_mean [expr {$total / [llength $arrivals]}]
    set mean $tree_mean
    if {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire && $mean <= 0} {
      error "OT_HYBRID: glue root $name lacks a positive actual propagated CTS insertion"
    }
    if {[llength $arrivals] > 15000 && ($tree_mean > 300 || $hi-$lo > 80)} {
      error "OT_HYBRID: glue root $name exceeds measured large-root insertion/spread limits"
    }
    if {!$boundary_cells_ready} {
      set boundary_cells [ot_ce_boundary_cells]; set boundary_cells_ready 1
    }
    set boundary [ot_ce_boundary_pins $pins $boundary_cells]
    set scope boundary
    if {![llength $boundary]} { set boundary $pins; set scope all_internal_only }
    set arrivals {}; set total 0.0
    foreach pin $boundary {
      set arrival [dict get $measured [get_full_name $pin]]
      lappend arrivals $arrival; set total [expr {$total + $arrival}]
    }
    set arrivals [lsort -real $arrivals]
    set lo [lindex $arrivals 0]; set hi [lindex $arrivals end]
    set mean [expr {$total / [llength $arrivals]}]
    if {[llength $pins] > 15000 && $mean > 300} {
      error "OT_HYBRID: glue root $name exceeds boundary insertion limit"
    }
    set domain [dict get $::ot_ce_source_domains $name]
    lappend rows [list [get_ports $name] [lindex $pins 0] 0 $lo $mean $hi $clock $mean $domain]
    dict set seen $name 1
    puts "OT_HYBRID CTS_MEASURE $corner $name sinks=[llength $pins] reference_scope=$scope boundary_sinks=[llength $boundary] min=$lo mean=$mean max=$hi all_mean=$tree_mean"
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}; set domain_low {}; set domain_high {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean domain
    # Physical source level includes the entry wire, not just the hard
    # child's internal insertion. Only a TT scene measures the TT wire.
    # Other physical scenes conservatively reserve the deep pair budget;
    # they must not guess TT wire delay from FF/SS or an ideal zero arrival.
    set deep [expr {$ttmean > 300}]
    set level_basis "zero-wire diagnostic"
    if {$corner eq "tt"} {
      set deep [expr {$ttmean + $wire > 300}]
      set level_basis "TT timing-graph entry arrival + child R (physical proof required for route/signoff)"
    } elseif {[info exists ::ot_ce_require_wire] && $::ot_ce_require_wire} {
      set deep 1
      set level_basis "TT wire level not measured in this scene; conservative210ps setup"
    }
    if {$deep} { lappend highclocks $clock } else { lappend lowclocks $clock }
    puts "OT_ENTRIES LEVEL [get_full_name $p] deep=$deep basis=$level_basis"
    set latency [expr {$ref - $wire - $mean}]
    if {![ot_ce_finite $ref] || ![ot_ce_finite $latency]} { error "OT_ENTRIES: nonfinite reference/source latency on [get_full_name $p]" }
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    dict lappend domain_low $domain [expr {$ref + $lo - $mean}]
    dict lappend domain_high $domain [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  # H1 authoritative pair_check.HOLD_TREE =50ps hold margin+50ps die skew (hold 100, setup 150).
  # Each deep tile has its own earlier trunk tap. The authoritative TREE
  # pair budget uses150ps die skew when either reference exceeds300ps,
  # including deep-to-deep pairs (pair_check.SKEW_DEEP) (setup 210).
  # S-ELEM-PQ 2026-10-15: a register pair on ONE glue CTS root of this tile shares one die tap and one
  # propagated standard-cell tree whose real skew STA already sees, so it is timed like every single-root
  # tile (base uncertainty); the die-skew reserve applies to every pair of DIFFERENT entries and to hard-
  # child entries (dsfd_bf_front_static: the uniform rule put hold 100 / setup 210 on all 12,276 core-root
  # paths -> 15,826 hold endpoints, 119k buffers).
  set ot_ce_glue {}
  foreach name $::ot_ce_cts_roots { lappend ot_ce_glue [get_full_name [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]] }
  set ot_ce_high {}
  foreach c $highclocks { lappend ot_ce_high [get_full_name $c] }
  foreach a [get_clocks ot_entry_*] {
    foreach b [get_clocks ot_entry_*] {
      set an [get_full_name $a]; set bn [get_full_name $b]
      if {$an eq $bn && $an in $ot_ce_glue} { continue }
      set_clock_uncertainty -setup [expr {($an in $ot_ce_high || $bn in $ot_ce_high) ? 210 : 150}] -from $a -to $b
      set_clock_uncertainty -hold 100 -from $a -to $b
    }
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set covered_in {}; set covered_out {}
  dict for {domain info} $::ot_ce_domains {
    if {![dict exists $domain_low $domain]} { error "OT_ENTRIES: domain $domain has no actual child clock pins" }
    set dlmin [lindex [lsort -real [dict get $domain_low $domain]] 0]
    set dlmax [lindex [lsort -real [dict get $domain_high $domain]] end]
    set vc [get_clocks [dict get $info clock]]
    set budget [dict get $info io_budget_ps]
    # Optional composition-derived output budget (domain "io_budget": {"out": f}, f >= 0.2): the outside share of the
    # cycle on this domain's outputs; larger = a TIGHTER launch (flop -> pin) inside the child, never a relaxation.
    set budget_out [expr {[dict exists $info io_budget_out_ps] ? [dict get $info io_budget_out_ps] : $budget}]
    set inputs {}; set outputs {}
    foreach pattern [dict get $info inputs] {
      set match [get_ports -quiet $pattern -filter "direction == input"]
      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\[*\]} $pattern] -filter "direction == input"]}
      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown input $pattern"}
      foreach p $match {
        set n [get_full_name $p]
        if {$n in $::ot_ce_ports} continue
        if {[dict exists $covered_in $n]} { error "OT_ENTRIES: input $n has duplicate IO domains" }
        dict set covered_in $n $domain; lappend inputs $p
      }
    }
    foreach pattern [dict get $info outputs] {
      set match [get_ports -quiet $pattern -filter "direction == output"]
      if {$::ot_ce_leaf_roots && ![llength $match]} {set match [get_ports -quiet [format {%s\[*\]} $pattern] -filter "direction == output"]}
      if {$::ot_ce_leaf_roots && ![llength $match]} {error "OT_MULTI_ROOT: unknown output $pattern"}
      foreach p $match {
        set n [get_full_name $p]
        if {[dict exists $covered_out $n]} { error "OT_ENTRIES: output $n has duplicate IO domains" }
        dict set covered_out $n $domain; lappend outputs $p
      }
    }
    if {[llength $inputs]} {
      set_input_delay [expr {$budget+$dlmax+$sk}] -max -clock $vc $inputs
      set_input_delay [expr {$dlmin-$hki}] -min -clock $vc $inputs
    }
    if {[llength $outputs]} {
      set_output_delay [expr {$budget_out-$dlmax+$sk}] -max -clock $vc $outputs
      set_output_delay [expr {-$dlmin-$hk}] -min -clock $vc $outputs
    }
    if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
      foreach pattern [split $::env(OT_IO_INTER) ","] {
        foreach p [get_ports -quiet $pattern] {
          set n [get_full_name $p]
          if {[dict exists $covered_in $n] && [dict get $covered_in $n] eq $domain} {
            set_input_delay [expr {$budget+$dlmax+150}] -max -clock $vc $p
          }
          if {[dict exists $covered_out $n] && [dict get $covered_out $n] eq $domain} {
            set_output_delay [expr {$budget_out-$dlmax+150}] -max -clock $vc $p
          }
        }
      }
    }
    puts "OT_ENTRIES DOMAIN $domain [get_property $vc period]ps IO[llength $inputs]/[llength $outputs] boundary=$dlmin..$dlmax"
  }
  if {[dict size $covered_in] != [llength [all_inputs -no_clocks]] || [dict size $covered_out] != [llength [all_outputs]]} {
    error "OT_ENTRIES: incomplete actual IO domain coverage (resets must also have a domain)"
  }
  if {$::ot_ce_leaf_roots} { ot_ce_leaf_ownership $covered_in $covered_out }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
