`timescale 1ns/1ps
module qkd_kvs_hroot_safe32__ot_pr_core (
    input wire ck,
    input wire rst_n,
    input wire [1:0] esh__stack,
    input wire [1117:0] i_ctl,
    output wire [779:0] o_pc,
    input wire [143:0] i_g,
    input wire [298:0] i_r,
    output wire [4:0] o_c0,
    output wire [4:0] o_c1,
    output wire [4:0] o_c2,
    output wire [4:0] o_c3,
    output wire [4:0] o_c4,
    output wire [4:0] o_c5,
    output wire [4:0] o_c6,
    output wire [4:0] o_c7,
    output wire [270:0] o_ch0,
    output wire [22:0] o_kg,
    output wire [143:0] o_ctl,
    output wire [298:0] o_emb
);
    wire [783:0] esh__h = i_ctl[783:0];
    wire [779:0] w_esh__d;
    wire [333:0] w_rly__fan;
    wire [143:0] w_rly__g;
    wire [298:0] w_rly__r;
    qkd_kv_es_fan_stack_safe32 #(.MUT(0)) u_esh (.ck(ck), .rst_n(rst_n), .stack(esh__stack), .h(esh__h), .d(w_esh__d));
    qkd_kv_stack_relays_s32 #(.HW(784), .FW(334), .GW(144), .RW(299)) u_rly (.ck(ck), .dn(i_ctl), .g_i(i_g), .r_i(i_r), .fan(w_rly__fan), .g(w_rly__g), .r(w_rly__r));
    assign o_pc = {w_esh__d};
    assign o_c0 = w_rly__fan[298:294];
    assign o_c1 = w_rly__fan[303:299];
    assign o_c2 = w_rly__fan[308:304];
    assign o_c3 = w_rly__fan[313:309];
    assign o_c4 = w_rly__fan[318:314];
    assign o_c5 = w_rly__fan[323:319];
    assign o_c6 = w_rly__fan[328:324];
    assign o_c7 = w_rly__fan[333:329];
    assign o_ch0 = {w_rly__fan[237:237], w_rly__fan[236:236], w_rly__fan[235:235], w_rly__fan[234:234], w_rly__fan[230:230], w_rly__fan[233:233], w_rly__fan[229:229], w_rly__fan[232:232], w_rly__fan[228:228], w_rly__fan[231:231], w_rly__fan[227:227], w_rly__fan[248:248], w_rly__fan[247:247], w_rly__fan[246:246], w_rly__fan[245:245], w_rly__fan[241:241], w_rly__fan[244:244], w_rly__fan[240:240], w_rly__fan[243:243], w_rly__fan[239:239], w_rly__fan[242:242], w_rly__fan[238:238], w_rly__fan[154:154], w_rly__fan[81:81], w_rly__fan[80:80], w_rly__fan[79:79], w_rly__fan[75:75], w_rly__fan[78:78], w_rly__fan[74:74], w_rly__fan[77:77], w_rly__fan[73:73], w_rly__fan[76:76], w_rly__fan[72:72], w_rly__fan[204:204], w_rly__fan[203:203], w_rly__fan[202:202], w_rly__fan[201:201], w_rly__fan[197:197], w_rly__fan[200:200], w_rly__fan[196:196], w_rly__fan[199:199], w_rly__fan[195:195], w_rly__fan[198:198], w_rly__fan[194:194], w_rly__fan[215:215], w_rly__fan[214:214], w_rly__fan[213:213], w_rly__fan[212:212], w_rly__fan[208:208], w_rly__fan[211:211], w_rly__fan[207:207], w_rly__fan[210:210], w_rly__fan[206:206], w_rly__fan[209:209], w_rly__fan[205:205], w_rly__fan[226:226], w_rly__fan[225:225], w_rly__fan[224:224], w_rly__fan[223:223], w_rly__fan[219:219], w_rly__fan[222:222], w_rly__fan[218:218], w_rly__fan[221:221], w_rly__fan[217:217], w_rly__fan[220:220], w_rly__fan[216:216], w_rly__fan[259:259], w_rly__fan[258:258], w_rly__fan[257:257], w_rly__fan[256:256], w_rly__fan[252:252], w_rly__fan[255:255], w_rly__fan[251:251], w_rly__fan[254:254], w_rly__fan[250:250], w_rly__fan[253:253], w_rly__fan[249:249], w_rly__fan[270:270], w_rly__fan[269:269], w_rly__fan[268:268], w_rly__fan[267:267], w_rly__fan[263:263], w_rly__fan[266:266], w_rly__fan[262:262], w_rly__fan[265:265], w_rly__fan[261:261], w_rly__fan[264:264], w_rly__fan[260:260], w_rly__fan[155:155], w_rly__fan[193:193], w_rly__fan[192:187], w_rly__fan[186:186], w_rly__fan[185:170], w_rly__fan[169:156], w_rly__fan[153:90], w_rly__fan[89:82], w_rly__fan[71:8], w_rly__fan[7:0]};
    assign o_kg = w_rly__fan[293:271];
    assign o_ctl = {w_rly__g[17:0], w_rly__g[35:18], w_rly__g[125:108], w_rly__g[143:126], w_rly__g[53:36], w_rly__g[71:54], w_rly__g[89:72], w_rly__g[107:90]};
    assign o_emb = w_rly__r;
endmodule
