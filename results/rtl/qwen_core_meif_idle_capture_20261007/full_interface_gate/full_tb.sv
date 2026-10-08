`timescale 1ns/1ps
module tb #(parameter NEG=0, STALL=0);
reg clk=0; always #5 clk=~clk; reg rst_n=0,start=0; integer cycle=0,i,j; reg [1023:0] mem[0:64];
`include "ot_hdc_isa.svh"
always @(posedge clk) cycle<=cycle+1;
reg [1023:0] pq0=0; integer bm0=0,bs0=0,nm0=0,ns0=0,nd0=0,mh0=0,held0=0;
wire [0:0] o0_5;
wire [17:0] o0_6;
wire [31:0] o0_7;
wire [31:0] o0_8;
wire [0:0] o0_9;
wire [0:0] o0_10;
wire [11:0] o0_11;
wire [0:0] o0_13;
wire [23:0] o0_14;
wire [0:0] o0_16;
wire [23:0] o0_17;
wire [0:0] o0_18;
wire [47:0] o0_19;
wire [1151:0] o0_20;
wire [0:0] o0_22;
wire [23:0] o0_23;
wire [0:0] o0_25;
wire [17:0] o0_26;
wire [63:0] o0_28;
wire [1535:0] o0_29;
wire [0:0] o0_31;
wire [63:0] o0_32;
wire [1535:0] o0_33;
wire [2047:0] o0_34;
wire [0:0] o0_36;
wire [63:0] o0_37;
wire [1535:0] o0_38;
wire [63:0] o0_40;
wire [1535:0] o0_41;
wire [63:0] o0_43;
wire [1535:0] o0_44;
wire [47:0] o0_46;
wire [1151:0] o0_47;
wire [767:0] o0_48;
wire [24575:0] o0_49;
wire [63:0] o0_50;
wire [1535:0] o0_51;
wire [2047:0] o0_52;
wire [0:0] o0_53;
wire [23:0] o0_54;
wire [31:0] o0_55;
wire [0:0] o0_56;
wire [23:0] o0_57;
wire [15:0] o0_58;
wire [511:0] o0_59;
wire [0:0] o0_60;
wire [0:0] o0_61;
wire [23:0] o0_62;
wire [23:0] o0_63;
wire [23:0] o0_64;
wire [23:0] o0_65;
wire [23:0] o0_66;
wire [3:0] o0_67;
wire [2:0] o0_68;
wire [17:0] o0_69;
wire [17:0] o0_70;
wire [17:0] o0_71;
wire [0:0] o0_72;
wire [17:0] o0_73;
wire [0:0] o0_75;
wire [0:0] o0_76;
wire [23:0] o0_77;
wire [23:0] o0_78;
wire [17:0] o0_79;
wire [17:0] o0_80;
wire [17:0] o0_81;
wire [2047:0] o0_82;
wire [49151:0] o0_83;
wire [0:0] o0_85;
wire [378:0] o0_86;
wire [65535:0] o0_87;
wire [0:0] o0_93;
wire [0:0] o0_97;
wire [23:0] o0_98;
wire [0:0] o0_99;
wire [23:0] o0_100;
wire [65535:0] o0_105;
wire [24575:0] o0_111;
wire [12287:0] o0_113;
wire [0:0] o0_116;
wire [23:0] o0_130;
wire [23:0] o0_131;
wire [23:0] o0_132;
wire [23:0] o0_133;
wire [0:0] o0_134;
wire [23:0] o0_135;
wire [23:0] o0_136;
wire [23:0] o0_137;
wire [17:0] o0_138;
wire [3:0] o0_139;
wire [0:0] o0_140;
wire [0:0] o0_141;
wire [23:0] o0_142;
wire [23:0] o0_143;
wire [0:0] o0_144;
wire [23:0] o0_145;
wire [17:0] o0_146;
wire [0:0] o0_147;
wire [23:0] o0_148;
wire [23:0] o0_149;
wire [17:0] o0_150;
wire [2:0] o0_151;
wire [23:0] o0_152;
wire [0:0] o0_153;
wire [0:0] o0_154;
wire [0:0] o0_156;
wire [0:0] o0_157;
wire [255:0] o0_162;
wire [2047:0] o0_168;
wire [2047:0] o0_171;
wire [2047:0] o0_174;
wire [0:0] o0_178;
wire [2:0] o0_189;
wire [23:0] o0_190;
wire [0:0] o0_191;
wire [1:0] o0_192;
wire [23:0] o0_193;
wire [17:0] o0_194;
wire [17:0] o0_195;
wire [0:0] o0_196;
wire [0:0] o0_197;
wire [1:0] o0_198;
wire [1:0] o0_199;
wire [31:0] o0_200;
wire [31:0] o0_201;
wire [1:0] o0_202;
wire [23:0] o0_203;
wire [23:0] o0_204;
wire [23:0] o0_205;
wire [0:0] o0_206;
wire [23:0] o0_207;
wire [23:0] o0_208;
wire [23:0] o0_209;
wire [0:0] o0_210;
wire [23:0] o0_211;
wire [23:0] o0_212;
wire [23:0] o0_213;
wire [0:0] o0_214;
wire [23:0] o0_215;
wire [23:0] o0_216;
wire [2:0] o0_217;
wire [23:0] o0_218;
wire [0:0] o0_219;
wire [4095:0] o0_222;
wire [0:0] o0_224;
core0 d0(.\clk (clk),
.\rst_n (rst_n),
.\start (start),
.\token (18'd7),
.\pos (18'd8191),
.\done (o0_5),
.\next_token (o0_6),
.\next_val (o0_7),
.\cycles (o0_8),
.\fault (o0_9),
.\prog_re (o0_10),
.\prog_addr (o0_11),
.\prog_q (pq0),
.\wrom_re (o0_13),
.\wrom_addr (o0_14),
.\wrom_q (1572864'd0),
.\int8_wrom_re (o0_16),
.\int8_wrom_addr (o0_17),
.\scale_re (o0_18),
.\scale_gre (o0_19),
.\scale_addr (o0_20),
.\scale_q (12288'd0),
.\embed_code_re (o0_22),
.\embed_code_addr (o0_23),
.\embed_code_q (512'd0),
.\embed_scale_re (o0_25),
.\embed_scale_addr (o0_26),
.\embed_scale_q (16'd0),
.\crom_re (o0_28),
.\crom_addr (o0_29),
.\crom_q (4096'd0),
.\kv_re (o0_31),
.\kv_we (o0_32),
.\kv_waddr (o0_33),
.\kv_wdata (o0_34),
.\kv_write_drained (drain0),
.\kv_write_flush (o0_36),
.\va_re (o0_37),
.\va_addr (o0_38),
.\va_q (2048'd0),
.\vb_re (o0_40),
.\vb_addr (o0_41),
.\vb_q (2048'd0),
.\vc_re (o0_43),
.\vc_addr (o0_44),
.\vc_q (2048'd0),
.\vw_me_we (o0_46),
.\vw_me_addr (o0_47),
.\vw_me_mask (o0_48),
.\vw_me_data (o0_49),
.\vw_su_we (o0_50),
.\vw_su_addr (o0_51),
.\vw_su_data (o0_52),
.\vw_rd_we (o0_53),
.\vw_rd_addr (o0_54),
.\vw_rd_data (o0_55),
.\vw_mx_we (o0_56),
.\vw_mx_addr (o0_57),
.\vw_mx_mask (o0_58),
.\vw_mx_data (o0_59),
.\me_ov (o0_60),
.\kvd_v (o0_61),
.\kvd_wbase (o0_62),
.\kvd_ts (o0_63),
.\kvd_ks (o0_64),
.\kvd_js (o0_65),
.\kvd_wcs (o0_66),
.\kvd_split (o0_67),
.\kvd_jsh (o0_68),
.\kvd_tiles (o0_69),
.\kvd_k (o0_70),
.\kvd_nout (o0_71),
.\kvd_kindk (o0_72),
.\kvd_pos (o0_73),
.\kv_ok (1'b1),
.\wrom_su (o0_75),
.\wd_v (o0_76),
.\wd_wbase (o0_77),
.\wd_sbase (o0_78),
.\wd_tiles (o0_79),
.\wd_k (o0_80),
.\wd_nout (o0_81),
.\vx_re (o0_82),
.\vx_addr (o0_83),
.\vx_q (65536'd0),
.\tgo (o0_85),
.\tb (o0_86),
.\xl_d (o0_87),
.\t_lvl (24576'd0),
.\fab_fault (1'd0),
.\w_ok (1'b1),
.\emb_ok (1'b1),
.\me_mem_ok ((!d0.me_go && mh0==0)),
.\me_clk_en (o0_93),
.\u_wrom_port.wrom_su (1'd0),
.\u_wrom_port.wrom_re (1'd0),
.\u_wrom_port.wrom_addr (24'd0),
.\u_wrom_port.su_wrom_re (o0_97),
.\u_wrom_port.su_wrom_addr (o0_98),
.\u_wrom_port.me_wrom_re (o0_99),
.\u_wrom_port.me_wrom_addr (o0_100),
.\u_wrom_port.int8_wrom_re (1'd0),
.\u_wrom_port.int8_wrom_addr (24'd0),
.\u_me.xl_d (65536'd0),
.\u_me.x_re (2048'd0),
.\u_me.x_q (o0_105),
.\u_me.x_addr (49152'd0),
.\u_me.wrom_re (1'd0),
.\u_me.wrom_addr (24'd0),
.\u_me.tgo (1'd0),
.\u_me.tb (379'd0),
.\u_me.t_lvl (o0_111),
.\u_me.scale_re (1'd0),
.\u_me.scale_q (o0_113),
.\u_me.scale_gre (48'd0),
.\u_me.scale_addr (1152'd0),
.\u_me.rst_n (o0_116),
.\u_me.ready (((bm0==0) && (!STALL || cycle%7!=0))),
.\u_me.progress (16'hffff),
.\u_me.ov (1'd0),
.\u_me.o_we (48'd0),
.\u_me.o_mask (768'd0),
.\u_me.o_data (24576'd0),
.\u_me.o_addr (1152'd0),
.\u_me.mx_we (1'd0),
.\u_me.mx_mask (16'd0),
.\u_me.mx_data (512'd0),
.\u_me.mx_addr (24'd0),
.\u_me.kv_re (1'd0),
.\u_me.idle ((bm0==0)),
.\u_me.i_xks (o0_130),
.\u_me.i_xjs (o0_131),
.\u_me.i_xcs (o0_132),
.\u_me.i_xbase (o0_133),
.\u_me.i_wsrc (o0_134),
.\u_me.i_wcs (o0_135),
.\u_me.i_wbase (o0_136),
.\u_me.i_ts (o0_137),
.\u_me.i_tiles (o0_138),
.\u_me.i_split (o0_139),
.\u_me.i_round (o0_140),
.\u_me.i_rmax (o0_141),
.\u_me.i_ots (o0_142),
.\u_me.i_ojs (o0_143),
.\u_me.i_oen (o0_144),
.\u_me.i_obase (o0_145),
.\u_me.i_nout (o0_146),
.\u_me.i_mmode (o0_147),
.\u_me.i_mbase (o0_148),
.\u_me.i_ks (o0_149),
.\u_me.i_k (o0_150),
.\u_me.i_jsh (o0_151),
.\u_me.i_js (o0_152),
.\u_me.i_amax (o0_153),
.\u_me.go (o0_154),
.\u_me.fault (1'd0),
.\u_me.fab_fault (o0_156),
.\u_me.clk (o0_157),
.\u_me.am_val (32'h3f800000),
.\u_me.am_idx (18'd7),
.\u_me.am_any (1'b1),
.\g_vsu.u_su.wrom_re (1'd0),
.\g_vsu.u_su.wrom_q (o0_162),
.\g_vsu.u_su.wrom_addr (24'd0),
.\g_vsu.u_su.vm_we (64'd0),
.\g_vsu.u_su.vm_wdata (2048'd0),
.\g_vsu.u_su.vm_waddr (1536'd0),
.\g_vsu.u_su.vc_re (64'd0),
.\g_vsu.u_su.vc_q (o0_168),
.\g_vsu.u_su.vc_addr (1536'd0),
.\g_vsu.u_su.vb_re (64'd0),
.\g_vsu.u_su.vb_q (o0_171),
.\g_vsu.u_su.vb_addr (1536'd0),
.\g_vsu.u_su.va_re (64'd0),
.\g_vsu.u_su.va_q (o0_174),
.\g_vsu.u_su.va_addr (1536'd0),
.\g_vsu.u_su.rt_inflight (8'd0),
.\g_vsu.u_su.rt_active (1'd0),
.\g_vsu.u_su.rst_n (o0_178),
.\g_vsu.u_su.red_we (1'd0),
.\g_vsu.u_su.red_data (32'd0),
.\g_vsu.u_su.red_addr (24'd0),
.\g_vsu.u_su.ready (((bs0==0) && (!STALL || cycle%11!=0))),
.\g_vsu.u_su.progress_rows (16'hffff),
.\g_vsu.u_su.progress (16'hffff),
.\g_vsu.u_su.kv_we (kvw_input0),
.\g_vsu.u_su.kv_wdata (2048'd0),
.\g_vsu.u_su.kv_waddr (1536'd0),
.\g_vsu.u_su.idle ((bs0==0)),
.\g_vsu.u_su.i_sfu (o0_189),
.\g_vsu.u_su.i_rso (o0_190),
.\g_vsu.u_su.i_redsq (o0_191),
.\g_vsu.u_su.i_red (o0_192),
.\g_vsu.u_su.i_rbase (o0_193),
.\g_vsu.u_su.i_nout (o0_194),
.\g_vsu.u_su.i_nin (o0_195),
.\g_vsu.u_su.i_md (o0_196),
.\g_vsu.u_su.i_mc (o0_197),
.\g_vsu.u_su.i_mb (o0_198),
.\g_vsu.u_su.i_ma (o0_199),
.\g_vsu.u_su.i_imm2 (o0_200),
.\g_vsu.u_su.i_imm1 (o0_201),
.\g_vsu.u_su.i_dst (o0_202),
.\g_vsu.u_su.i_dso (o0_203),
.\g_vsu.u_su.i_dsi (o0_204),
.\g_vsu.u_su.i_dbase (o0_205),
.\g_vsu.u_su.i_csrc (o0_206),
.\g_vsu.u_su.i_cso (o0_207),
.\g_vsu.u_su.i_csi (o0_208),
.\g_vsu.u_su.i_cbase (o0_209),
.\g_vsu.u_su.i_bsrc (o0_210),
.\g_vsu.u_su.i_bso (o0_211),
.\g_vsu.u_su.i_bsi (o0_212),
.\g_vsu.u_su.i_bbase (o0_213),
.\g_vsu.u_su.i_asrc (o0_214),
.\g_vsu.u_su.i_aso (o0_215),
.\g_vsu.u_su.i_asi (o0_216),
.\g_vsu.u_su.i_ad (o0_217),
.\g_vsu.u_su.i_abase (o0_218),
.\g_vsu.u_su.go (o0_219),
.\g_vsu.u_su.fault (1'd0),
.\g_vsu.u_su.crom_re (64'd0),
.\g_vsu.u_su.crom_q (o0_222),
.\g_vsu.u_su.crom_addr (1536'd0),
.\g_vsu.u_su.clk (o0_224));

wire [63:0] kvw0=(bs0==2)?(64'h1<<((ns0-1)%64)):64'd0;
wire [63:0] kvw_input0=kvw0;
wire drain0,brfault0,rv0,wv0;wire[23:0] rs0,ws0;wire[255:0] wd0;
reg response0=0;reg[255:0] memory0=0,rd0=0;integer writes0=0;
wire mrdy0=!STALL || cycle%5!=0;
wire mwdy0=!STALL || cycle%7!=0;
wire[23:0] addr0=24'd4096+(ns0-1);
ot_hdc_qwen_kv_vector_bridge #(.SW(64),.AW(24),.FIFO_BEATS(16),.MAX_KV_OP_ELEMS(64),.V0_ELEMENT(4096)) br0(
.clk(clk),.rst_n(rst_n),.core_we(kvw0),.core_addr({64{addr0}}),.core_data({64{32'h3f800000}}),.drained(drain0),
.fl_v(1'b0),.fl_word_addr(24'd0),.fl_word_data(128'd0),.flush(o0_36),
.mem_r_v(rv0),.mem_r_ready(mrdy0),.mem_r_sector(rs0),.mem_r_resp_v(response0),.mem_r_resp_data(rd0),
.mem_w_v(wv0),.mem_w_ready(mwdy0),.mem_w_sector(ws0),.mem_w_data(wd0),.fault(brfault0));
always @(posedge clk) begin
 if(!rst_n) begin response0<=0;memory0<=0;rd0<=0;writes0<=0;end
 else begin
 response0<=rv0&&mrdy0;if(rv0&&mrdy0) begin if(rs0!=128) $fatal(1,"read sector");rd0<=memory0;end
 if(wv0&&mwdy0) begin if(ws0!=128) $fatal(1,"write sector");memory0<=wd0;writes0<=writes0+1;end
 if(brfault0) $fatal(1,"bridge fault");
 end
end
reg [378:0] nmevents0[0:63];
reg [455:0] nsevents0[0:63];
always @(posedge clk) begin if(o0_10) pq0<=mem[o0_11%65];
if(!rst_n) begin bm0<=0;bs0<=0;nm0=0;ns0=0;nd0=0;mh0<=0;held0<=0;end else begin if(d0.me_go)mh0<=4;else if(mh0>0)mh0<=mh0-1;if(d0.me_gop && !d0.me_en)held0<=held0+1;
if(bm0>0) bm0<=bm0-1; if(bs0>0) bs0<=bs0-1;
if(o0_5) nd0=nd0+1;
if(o0_154 && d0.me_en) begin if(bm0!=0) $fatal(1,"duplicate acceptance d=0 unit=u_me");
nmevents0[nm0]={o0_153,o0_152,o0_151,o0_150,o0_149,o0_148,o0_147,o0_146,o0_145,o0_144,o0_143,o0_142,o0_141,o0_140,o0_139,o0_138,o0_137,o0_136,o0_135,o0_134,o0_133,o0_132,o0_131,o0_130} ^ ((NEG==1 && 0==1 && nm0==7) ? 379'd1 : 379'd0);
nm0=nm0+1;bm0<=5+(nm0%3);end
if(o0_219) begin if(bs0!=0) $fatal(1,"duplicate acceptance d=0 unit=g_vsu.u_su");
nsevents0[ns0]={o0_218,o0_217,o0_216,o0_215,o0_214,o0_213,o0_212,o0_211,o0_210,o0_209,o0_208,o0_207,o0_206,o0_205,o0_204,o0_203,o0_202,o0_201,o0_200,o0_199,o0_198,o0_197,o0_196,o0_195,o0_194,o0_193,o0_192,o0_191,o0_190,o0_189} ^ ((NEG==1 && 0==1 && ns0==7) ? 456'd1 : 456'd0);
ns0=ns0+1;bs0<=5+(ns0%3);end
end end
reg [1023:0] pq1=0; integer bm1=0,bs1=0,nm1=0,ns1=0,nd1=0,mh1=0,held1=0;
wire [0:0] o1_5;
wire [17:0] o1_6;
wire [31:0] o1_7;
wire [31:0] o1_8;
wire [0:0] o1_9;
wire [0:0] o1_10;
wire [11:0] o1_11;
wire [0:0] o1_13;
wire [23:0] o1_14;
wire [0:0] o1_16;
wire [23:0] o1_17;
wire [0:0] o1_18;
wire [47:0] o1_19;
wire [1151:0] o1_20;
wire [0:0] o1_22;
wire [23:0] o1_23;
wire [0:0] o1_25;
wire [17:0] o1_26;
wire [63:0] o1_28;
wire [1535:0] o1_29;
wire [0:0] o1_31;
wire [63:0] o1_32;
wire [1535:0] o1_33;
wire [2047:0] o1_34;
wire [0:0] o1_36;
wire [63:0] o1_37;
wire [1535:0] o1_38;
wire [63:0] o1_40;
wire [1535:0] o1_41;
wire [63:0] o1_43;
wire [1535:0] o1_44;
wire [47:0] o1_46;
wire [1151:0] o1_47;
wire [767:0] o1_48;
wire [24575:0] o1_49;
wire [63:0] o1_50;
wire [1535:0] o1_51;
wire [2047:0] o1_52;
wire [0:0] o1_53;
wire [23:0] o1_54;
wire [31:0] o1_55;
wire [0:0] o1_56;
wire [23:0] o1_57;
wire [15:0] o1_58;
wire [511:0] o1_59;
wire [0:0] o1_60;
wire [0:0] o1_61;
wire [23:0] o1_62;
wire [23:0] o1_63;
wire [23:0] o1_64;
wire [23:0] o1_65;
wire [23:0] o1_66;
wire [3:0] o1_67;
wire [2:0] o1_68;
wire [17:0] o1_69;
wire [17:0] o1_70;
wire [17:0] o1_71;
wire [0:0] o1_72;
wire [17:0] o1_73;
wire [0:0] o1_75;
wire [0:0] o1_76;
wire [23:0] o1_77;
wire [23:0] o1_78;
wire [17:0] o1_79;
wire [17:0] o1_80;
wire [17:0] o1_81;
wire [2047:0] o1_82;
wire [49151:0] o1_83;
wire [0:0] o1_85;
wire [378:0] o1_86;
wire [65535:0] o1_87;
wire [0:0] o1_93;
wire [0:0] o1_97;
wire [23:0] o1_98;
wire [0:0] o1_99;
wire [23:0] o1_100;
wire [65535:0] o1_105;
wire [24575:0] o1_111;
wire [12287:0] o1_113;
wire [0:0] o1_116;
wire [23:0] o1_130;
wire [23:0] o1_131;
wire [23:0] o1_132;
wire [23:0] o1_133;
wire [0:0] o1_134;
wire [23:0] o1_135;
wire [23:0] o1_136;
wire [23:0] o1_137;
wire [17:0] o1_138;
wire [3:0] o1_139;
wire [0:0] o1_140;
wire [0:0] o1_141;
wire [23:0] o1_142;
wire [23:0] o1_143;
wire [0:0] o1_144;
wire [23:0] o1_145;
wire [17:0] o1_146;
wire [0:0] o1_147;
wire [23:0] o1_148;
wire [23:0] o1_149;
wire [17:0] o1_150;
wire [2:0] o1_151;
wire [23:0] o1_152;
wire [0:0] o1_153;
wire [0:0] o1_154;
wire [0:0] o1_156;
wire [0:0] o1_157;
wire [255:0] o1_162;
wire [2047:0] o1_168;
wire [2047:0] o1_171;
wire [2047:0] o1_174;
wire [0:0] o1_178;
wire [2:0] o1_189;
wire [23:0] o1_190;
wire [0:0] o1_191;
wire [1:0] o1_192;
wire [23:0] o1_193;
wire [17:0] o1_194;
wire [17:0] o1_195;
wire [0:0] o1_196;
wire [0:0] o1_197;
wire [1:0] o1_198;
wire [1:0] o1_199;
wire [31:0] o1_200;
wire [31:0] o1_201;
wire [1:0] o1_202;
wire [23:0] o1_203;
wire [23:0] o1_204;
wire [23:0] o1_205;
wire [0:0] o1_206;
wire [23:0] o1_207;
wire [23:0] o1_208;
wire [23:0] o1_209;
wire [0:0] o1_210;
wire [23:0] o1_211;
wire [23:0] o1_212;
wire [23:0] o1_213;
wire [0:0] o1_214;
wire [23:0] o1_215;
wire [23:0] o1_216;
wire [2:0] o1_217;
wire [23:0] o1_218;
wire [0:0] o1_219;
wire [4095:0] o1_222;
wire [0:0] o1_224;
core1 d1(.\clk (clk),
.\rst_n (rst_n),
.\start (start),
.\token (18'd7),
.\pos (18'd8191),
.\done (o1_5),
.\next_token (o1_6),
.\next_val (o1_7),
.\cycles (o1_8),
.\fault (o1_9),
.\prog_re (o1_10),
.\prog_addr (o1_11),
.\prog_q (pq1),
.\wrom_re (o1_13),
.\wrom_addr (o1_14),
.\wrom_q (1572864'd0),
.\int8_wrom_re (o1_16),
.\int8_wrom_addr (o1_17),
.\scale_re (o1_18),
.\scale_gre (o1_19),
.\scale_addr (o1_20),
.\scale_q (12288'd0),
.\embed_code_re (o1_22),
.\embed_code_addr (o1_23),
.\embed_code_q (512'd0),
.\embed_scale_re (o1_25),
.\embed_scale_addr (o1_26),
.\embed_scale_q (16'd0),
.\crom_re (o1_28),
.\crom_addr (o1_29),
.\crom_q (4096'd0),
.\kv_re (o1_31),
.\kv_we (o1_32),
.\kv_waddr (o1_33),
.\kv_wdata (o1_34),
.\kv_write_drained (drain1),
.\kv_write_flush (o1_36),
.\va_re (o1_37),
.\va_addr (o1_38),
.\va_q (2048'd0),
.\vb_re (o1_40),
.\vb_addr (o1_41),
.\vb_q (2048'd0),
.\vc_re (o1_43),
.\vc_addr (o1_44),
.\vc_q (2048'd0),
.\vw_me_we (o1_46),
.\vw_me_addr (o1_47),
.\vw_me_mask (o1_48),
.\vw_me_data (o1_49),
.\vw_su_we (o1_50),
.\vw_su_addr (o1_51),
.\vw_su_data (o1_52),
.\vw_rd_we (o1_53),
.\vw_rd_addr (o1_54),
.\vw_rd_data (o1_55),
.\vw_mx_we (o1_56),
.\vw_mx_addr (o1_57),
.\vw_mx_mask (o1_58),
.\vw_mx_data (o1_59),
.\me_ov (o1_60),
.\kvd_v (o1_61),
.\kvd_wbase (o1_62),
.\kvd_ts (o1_63),
.\kvd_ks (o1_64),
.\kvd_js (o1_65),
.\kvd_wcs (o1_66),
.\kvd_split (o1_67),
.\kvd_jsh (o1_68),
.\kvd_tiles (o1_69),
.\kvd_k (o1_70),
.\kvd_nout (o1_71),
.\kvd_kindk (o1_72),
.\kvd_pos (o1_73),
.\kv_ok (1'b1),
.\wrom_su (o1_75),
.\wd_v (o1_76),
.\wd_wbase (o1_77),
.\wd_sbase (o1_78),
.\wd_tiles (o1_79),
.\wd_k (o1_80),
.\wd_nout (o1_81),
.\vx_re (o1_82),
.\vx_addr (o1_83),
.\vx_q (65536'd0),
.\tgo (o1_85),
.\tb (o1_86),
.\xl_d (o1_87),
.\t_lvl (24576'd0),
.\fab_fault (1'd0),
.\w_ok (1'b1),
.\emb_ok (1'b1),
.\me_mem_ok ((!d1.me_go && mh1==0)),
.\me_clk_en (o1_93),
.\u_wrom_port.wrom_su (1'd0),
.\u_wrom_port.wrom_re (1'd0),
.\u_wrom_port.wrom_addr (24'd0),
.\u_wrom_port.su_wrom_re (o1_97),
.\u_wrom_port.su_wrom_addr (o1_98),
.\u_wrom_port.me_wrom_re (o1_99),
.\u_wrom_port.me_wrom_addr (o1_100),
.\u_wrom_port.int8_wrom_re (1'd0),
.\u_wrom_port.int8_wrom_addr (24'd0),
.\u_me.xl_d (65536'd0),
.\u_me.x_re (2048'd0),
.\u_me.x_q (o1_105),
.\u_me.x_addr (49152'd0),
.\u_me.wrom_re (1'd0),
.\u_me.wrom_addr (24'd0),
.\u_me.tgo (1'd0),
.\u_me.tb (379'd0),
.\u_me.t_lvl (o1_111),
.\u_me.scale_re (1'd0),
.\u_me.scale_q (o1_113),
.\u_me.scale_gre (48'd0),
.\u_me.scale_addr (1152'd0),
.\u_me.rst_n (o1_116),
.\u_me.ready (((bm1==0) && (!STALL || cycle%7!=0))),
.\u_me.progress (16'hffff),
.\u_me.ov (1'd0),
.\u_me.o_we (48'd0),
.\u_me.o_mask (768'd0),
.\u_me.o_data (24576'd0),
.\u_me.o_addr (1152'd0),
.\u_me.mx_we (1'd0),
.\u_me.mx_mask (16'd0),
.\u_me.mx_data (512'd0),
.\u_me.mx_addr (24'd0),
.\u_me.kv_re (1'd0),
.\u_me.idle ((bm1==0)),
.\u_me.i_xks (o1_130),
.\u_me.i_xjs (o1_131),
.\u_me.i_xcs (o1_132),
.\u_me.i_xbase (o1_133),
.\u_me.i_wsrc (o1_134),
.\u_me.i_wcs (o1_135),
.\u_me.i_wbase (o1_136),
.\u_me.i_ts (o1_137),
.\u_me.i_tiles (o1_138),
.\u_me.i_split (o1_139),
.\u_me.i_round (o1_140),
.\u_me.i_rmax (o1_141),
.\u_me.i_ots (o1_142),
.\u_me.i_ojs (o1_143),
.\u_me.i_oen (o1_144),
.\u_me.i_obase (o1_145),
.\u_me.i_nout (o1_146),
.\u_me.i_mmode (o1_147),
.\u_me.i_mbase (o1_148),
.\u_me.i_ks (o1_149),
.\u_me.i_k (o1_150),
.\u_me.i_jsh (o1_151),
.\u_me.i_js (o1_152),
.\u_me.i_amax (o1_153),
.\u_me.go (o1_154),
.\u_me.fault (1'd0),
.\u_me.fab_fault (o1_156),
.\u_me.clk (o1_157),
.\u_me.am_val (32'h3f800000),
.\u_me.am_idx (18'd7),
.\u_me.am_any (1'b1),
.\g_vsu.u_su.wrom_re (1'd0),
.\g_vsu.u_su.wrom_q (o1_162),
.\g_vsu.u_su.wrom_addr (24'd0),
.\g_vsu.u_su.vm_we (64'd0),
.\g_vsu.u_su.vm_wdata (2048'd0),
.\g_vsu.u_su.vm_waddr (1536'd0),
.\g_vsu.u_su.vc_re (64'd0),
.\g_vsu.u_su.vc_q (o1_168),
.\g_vsu.u_su.vc_addr (1536'd0),
.\g_vsu.u_su.vb_re (64'd0),
.\g_vsu.u_su.vb_q (o1_171),
.\g_vsu.u_su.vb_addr (1536'd0),
.\g_vsu.u_su.va_re (64'd0),
.\g_vsu.u_su.va_q (o1_174),
.\g_vsu.u_su.va_addr (1536'd0),
.\g_vsu.u_su.rt_inflight (8'd0),
.\g_vsu.u_su.rt_active (1'd0),
.\g_vsu.u_su.rst_n (o1_178),
.\g_vsu.u_su.red_we (1'd0),
.\g_vsu.u_su.red_data (32'd0),
.\g_vsu.u_su.red_addr (24'd0),
.\g_vsu.u_su.ready (((bs1==0) && (!STALL || cycle%11!=0))),
.\g_vsu.u_su.progress_rows (16'hffff),
.\g_vsu.u_su.progress (16'hffff),
.\g_vsu.u_su.kv_we (kvw_input1),
.\g_vsu.u_su.kv_wdata (2048'd0),
.\g_vsu.u_su.kv_waddr (1536'd0),
.\g_vsu.u_su.idle ((bs1==0)),
.\g_vsu.u_su.i_sfu (o1_189),
.\g_vsu.u_su.i_rso (o1_190),
.\g_vsu.u_su.i_redsq (o1_191),
.\g_vsu.u_su.i_red (o1_192),
.\g_vsu.u_su.i_rbase (o1_193),
.\g_vsu.u_su.i_nout (o1_194),
.\g_vsu.u_su.i_nin (o1_195),
.\g_vsu.u_su.i_md (o1_196),
.\g_vsu.u_su.i_mc (o1_197),
.\g_vsu.u_su.i_mb (o1_198),
.\g_vsu.u_su.i_ma (o1_199),
.\g_vsu.u_su.i_imm2 (o1_200),
.\g_vsu.u_su.i_imm1 (o1_201),
.\g_vsu.u_su.i_dst (o1_202),
.\g_vsu.u_su.i_dso (o1_203),
.\g_vsu.u_su.i_dsi (o1_204),
.\g_vsu.u_su.i_dbase (o1_205),
.\g_vsu.u_su.i_csrc (o1_206),
.\g_vsu.u_su.i_cso (o1_207),
.\g_vsu.u_su.i_csi (o1_208),
.\g_vsu.u_su.i_cbase (o1_209),
.\g_vsu.u_su.i_bsrc (o1_210),
.\g_vsu.u_su.i_bso (o1_211),
.\g_vsu.u_su.i_bsi (o1_212),
.\g_vsu.u_su.i_bbase (o1_213),
.\g_vsu.u_su.i_asrc (o1_214),
.\g_vsu.u_su.i_aso (o1_215),
.\g_vsu.u_su.i_asi (o1_216),
.\g_vsu.u_su.i_ad (o1_217),
.\g_vsu.u_su.i_abase (o1_218),
.\g_vsu.u_su.go (o1_219),
.\g_vsu.u_su.fault (1'd0),
.\g_vsu.u_su.crom_re (64'd0),
.\g_vsu.u_su.crom_q (o1_222),
.\g_vsu.u_su.crom_addr (1536'd0),
.\g_vsu.u_su.clk (o1_224));

wire [63:0] kvw1=(bs1==2)?(64'h1<<((ns1-1)%64)):64'd0;
wire [63:0] kvw_input1=kvw1;
wire drain1,brfault1,rv1,wv1;wire[23:0] rs1,ws1;wire[255:0] wd1;
reg response1=0;reg[255:0] memory1=0,rd1=0;integer writes1=0;
wire mrdy1=!STALL || cycle%5!=0;
wire mwdy1=!STALL || cycle%7!=0;
wire[23:0] addr1=24'd4096+(ns1-1);
ot_hdc_qwen_kv_vector_bridge #(.SW(64),.AW(24),.FIFO_BEATS(16),.MAX_KV_OP_ELEMS(64),.V0_ELEMENT(4096)) br1(
.clk(clk),.rst_n(rst_n),.core_we(kvw1),.core_addr({64{addr1}}),.core_data({64{32'h3f800000}}),.drained(drain1),
.fl_v(1'b0),.fl_word_addr(24'd0),.fl_word_data(128'd0),.flush(o1_36),
.mem_r_v(rv1),.mem_r_ready(mrdy1),.mem_r_sector(rs1),.mem_r_resp_v(response1),.mem_r_resp_data(rd1),
.mem_w_v(wv1),.mem_w_ready(mwdy1),.mem_w_sector(ws1),.mem_w_data(wd1),.fault(brfault1));
always @(posedge clk) begin
 if(!rst_n) begin response1<=0;memory1<=0;rd1<=0;writes1<=0;end
 else begin
 response1<=rv1&&mrdy1;if(rv1&&mrdy1) begin if(rs1!=128) $fatal(1,"read sector");rd1<=memory1;end
 if(wv1&&mwdy1) begin if(ws1!=128) $fatal(1,"write sector");memory1<=wd1;writes1<=writes1+1;end
 if(brfault1) $fatal(1,"bridge fault");
 end
end
reg [378:0] nmevents1[0:63];
reg [455:0] nsevents1[0:63];
always @(posedge clk) begin if(o1_10) pq1<=mem[o1_11%65];
if(!rst_n) begin bm1<=0;bs1<=0;nm1=0;ns1=0;nd1=0;mh1<=0;held1<=0;end else begin if(d1.me_go)mh1<=4;else if(mh1>0)mh1<=mh1-1;if(d1.me_gop && !d1.me_en)held1<=held1+1;
if(bm1>0) bm1<=bm1-1; if(bs1>0) bs1<=bs1-1;
if(o1_5) nd1=nd1+1;
if(o1_154 && d1.me_en) begin if(bm1!=0) $fatal(1,"duplicate acceptance d=1 unit=u_me");
nmevents1[nm1]={o1_153,o1_152,o1_151,o1_150,o1_149,o1_148,o1_147,o1_146,o1_145,o1_144,o1_143,o1_142,o1_141,o1_140,o1_139,o1_138,o1_137,o1_136,o1_135,o1_134,o1_133,o1_132,o1_131,o1_130} ^ ((NEG==1 && 1==1 && nm1==7) ? 379'd1 : 379'd0);
nm1=nm1+1;bm1<=5+(nm1%3);end
if(o1_219) begin if(bs1!=0) $fatal(1,"duplicate acceptance d=1 unit=g_vsu.u_su");
nsevents1[ns1]={o1_218,o1_217,o1_216,o1_215,o1_214,o1_213,o1_212,o1_211,o1_210,o1_209,o1_208,o1_207,o1_206,o1_205,o1_204,o1_203,o1_202,o1_201,o1_200,o1_199,o1_198,o1_197,o1_196,o1_195,o1_194,o1_193,o1_192,o1_191,o1_190,o1_189} ^ ((NEG==1 && 1==1 && ns1==7) ? 456'd1 : 456'd0);
ns1=ns1+1;bs1<=5+(ns1%3);end
end end
initial begin
for(i=0;i<65;i=i+1) mem[i]=0;
for(i=0;i<64;i=i+1) begin
mem[i][O_UNIT+:W_UNIT]=(i%2)+1;mem[i][O_BARRIER]=i%5==0;mem[i][O_WAIT_ME]=i%7==0;mem[i][O_WAIT_SU]=i%7==0;
mem[i][O_ME_NOUT+:W_ME_NOUT]=1;mem[i][O_ME_TILES+:W_ME_TILES]=1;mem[i][O_ME_K+:W_ME_K]=1;mem[i][O_ME_WBASE+:W_ME_WBASE]=i*17;mem[i][O_ME_AMAX]=1;mem[i][O_ME_AMC]=i!=0;mem[i][O_ME_ROW0+:W_ME_ROW0]=i*17;
mem[i][O_SU_NOUT+:W_SU_NOUT]=1;mem[i][O_SU_NIN+:W_SU_NIN]=1;mem[i][O_DST+:W_DST]=2;end
repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);start=1;@(negedge clk);start=0;
repeat(20) @(negedge clk);rst_n=0;repeat(4) @(negedge clk);rst_n=1;repeat(4) @(negedge clk);start=1;@(negedge clk);start=0;
wait(nd0>0 && nd1>0);wait(drain0 && drain1);repeat(4) @(negedge clk);
if(memory0!=={32{8'h38}} || memory1!=={32{8'h38}}) $fatal(1,"KV final memory mismatch");
if(held0<32||held1<32)$fatal(1,"missing held-ME coverage");
if(nm0!=32 ||nm1!=32 ||ns0!=32 ||ns1!=32) $fatal(1,"counts ME%0d/%0d SU%0d/%0d",nm0,nm1,ns0,ns1);
for(j=0;j<32;j=j+1) begin if(nmevents0[j]!==nmevents1[j]) $fatal(1,"ME event mismatch %0d",j); if(nsevents0[j]!==nsevents1[j]) $fatal(1,"SU event mismatch %0d",j);end
if(o0_6!==o1_6 || o0_7!==o1_7) $fatal(1,"END result mismatch");
$display("CYCLES base=%0d candidate=%0d KVwrites=%0d/%0d heldME=%0d/%0d",o0_8,o1_8,writes0,writes1,held0,held1);
$display("PASS full controller FB3 BOUND AMQ NXREG MEIF SUIF PINREG: ME32 SU32 fields exact; no duplicate acceptance; reset abort; END");$finish;end
initial begin repeat(10000) @(posedge clk);$display("DBG nm %d/%d ns %d/%d st %d/%d nx %b/%b fault %b/%b kv %b/%b",nm0,nm1,ns0,ns1,d0.st,d1.st,d0.nx_v,d1.nx_v,d0.fault,d1.fault,d0.kv_ok_i,d1.kv_ok_i);$fatal(1,"liveness");end
endmodule
module ICGx1_ASAP7_75t_R(input CLK,ENA,SE, output GCLK);reg en;always @(*) if(!CLK) en=ENA|SE;assign GCLK=CLK&en;endmodule
