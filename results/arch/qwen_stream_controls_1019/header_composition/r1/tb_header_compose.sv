`timescale 1ns/1fs
module tb_stream; integer MUT=0; initial if(!$value$plusargs("MUT=%d",MUT)) MUT=0;
 reg diag_logged=0;reg ck=0,rst=0;always #0.416666666 ck=~ck;
 reg[3:0] prior_sid=0;wire[3:0] sid;reg[1:0] dir=0;reg[27:0] tag=0;reg cfg=0;reg[1087:0] rawsw=0,rawse=0;reg[1087:0] sw=0,se=0;reg[7:0] we=0;reg[191:0] addr=0;reg[255:0] data=0;

 integer PHASE=0;reg ck_w=0;
 initial begin if(!$value$plusargs("PHASE=%d",PHASE)) PHASE=0;#(0.416666666+PHASE/1000.0);ck_w=1;forever #0.416666666 ck_w=~ck_w;end
 wire[4351:0] sw_bank,se_bank;wire[11:0] sw_epo,se_epo;wire[183:0] sw_vld,se_vld;
 wire[1087:0] sw_read,se_read;
 ot_pl_land_chunk_w #(.W(1088),.D(4),.CHUNK_BITS(24)) u_ww(.ck(ck_w),.rsi(rst),.i(rawsw),.bank(sw_bank),.epo(sw_epo),.vld(sw_vld));
 ot_pl_land_chunk_w #(.W(1088),.D(4),.CHUNK_BITS(24)) u_we(.ck(ck_w),.rsi(rst),.i(rawse),.bank(se_bank),.epo(se_epo),.vld(se_vld));
 ot_pl_land_chunk_r #(.W(1088),.D(4),.K(2),.CHUNK_BITS(24)) u_rw(.ck(ck),.rsi(rst),.bank(sw_bank),.epo(sw_epo),.vld(sw_vld),.o(sw_read));
 ot_pl_land_chunk_r #(.W(1088),.D(4),.K(2),.CHUNK_BITS(24)) u_re(.ck(ck),.rsi(rst),.bank(se_bank),.epo(se_epo),.vld(se_vld),.o(se_read));
 reg[115:0] cmd_i=0,cmd_q=0;reg[3:0] sid_q=0;
 wire setid=cmd_q[0]&&cmd_q[3:1]==3'd7;assign sid=sid_q;
 always @(posedge ck or negedge rst) if(!rst)begin sw<=0;se<=0;cmd_q<=0;sid_q<=0;end else begin sw<=sw_read;se<=se_read;cmd_q<=cmd_i;if(setid)sid_q<=cmd_q[7:4];end
 wire[95:0] sw_hdr;wire[49:0] se_hdr;reg[95:0] sw_hdr_old=0;reg[49:0] se_hdr_old=0;
 always @(posedge ck)begin sw_hdr_old<=sw_hdr;se_hdr_old<=se_hdr;end
 wire[6:0] capture_resets={7{rst}} | (MUT==7 ? 7'b1 : 7'b0);
 qfd_dv_stream_header_producer u_header(.ck(ck),.rst_read({5{rst}}),.rst_capture(capture_resets),.sw_bank(sw_bank),.se_bank(se_bank),.sw_epo(sw_epo),.se_epo(se_epo),.sw_vld(sw_vld),.se_vld(se_vld),.sw_i_copies(sw_hdr),.se_i_copies(se_hdr));
 wire[95:0] sw_feed;wire[49:0] se_feed=MUT==5 ? se_hdr_old : se_hdr;
 for(genvar k=0;k<96;k=k+1)begin:g_feed
  assign sw_feed[k]=(MUT==5 ? sw_hdr_old[k] : sw_hdr[k]) ^ ((MUT==1)&&(k>=6));
 end
 integer header_checks=0;
 wire[1087:0] le,lw,qe,qw;wire lv,qv,lbad,qbad,lf,qf,ltw,qtw;
 wire[1:0] lk,qk;wire[23:0] la,qa,lxa,qxa;wire[1023:0] ld,qd,lxd,qxd;
 qfd_dv_stream u_l(.ck(ck),.rst_n(rst),.sid(sid),.cfg_v(cfg),.cfg_dir(dir),.cfg_tag(tag),
 .sw_i(sw),.se_i(se),.so_e(le),.so_w(lw),.xw_we(we),.xw_addr(addr),.xw_data(data),
 .tw_we(ltw),.tw_kind(lk),.tw_addr(la),.tw_data(ld),.xt_v(lv),.xt_a(lxa),.xt_d(lxd),.xt_bad(lbad),.fault(lf));
 qfd_dv_stream_controls u_q(.rst_n_copies({(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst),(MUT==3 ? 1'b1 : rst)}),.cfg_v_copies({cfg,cfg}),.sw_i_copies(sw_feed),.se_i_copies(se_feed),.xw_we_copies({we[7],we[7],we[6],we[6],we[5],we[5],we[4],we[4],we[7],we[6],we[5],we[4],we[3],we[2],we[1],we[7],we[7],we[6],we[6],we[5],we[5],we[4],we[4],we[2],we[0]}),.xw_addr_copies({addr[170],addr[98],addr[74],addr[50],addr[26],addr[2]}),.ck(ck),.rst_n(rst),.sid(MUT==4 ? prior_sid : (sid ^ (MUT==2 ? 4'd1 : 4'd0))),.cfg_v(cfg),.cfg_dir(dir),.cfg_tag(tag),
 .sw_i(sw),.se_i(se),.so_e(qe),.so_w(qw),.xw_we(we),.xw_addr(addr),.xw_data(data),
 .tw_we(qtw),.tw_kind(qk),.tw_addr(qa),.tw_data(qd),.xt_v(qv),.xt_a(qxa),.xt_d(qxd),.xt_bad(qbad),.fault(qf));
 reg[31:0] seed=32'h76dc563a;integer cycle=0,age=0;
 function automatic[31:0] step(input[31:0] x);
  reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);step=y^(y<<5);end
 endfunction
 always @(negedge ck) begin
  rst=!(cycle<8||(cycle>=700&&cycle<708));cfg=rst&&(age==17||cycle%31==0);prior_sid=sid;cmd_i={108'd0,4'(cycle%16),4'hf};dir=2'(cycle%4);tag=28'(cycle*12345);
  for(integer b=0;b<1088;b=b+1) begin
   if(b%32==0) seed=step(seed);rawsw[b]=seed[b%32];seed=step(seed);rawse[b]=seed[b%32];
  end
  rawsw[1087]=rst&&age>=20&&cycle%5==0;rawse[1087]=rst&&age>=20&&cycle%7==0;
  rawsw[1086:1084]=3'(cycle%4);rawse[1086:1084]=3'((cycle+1)%4);
  rawsw[1083:1080]=4'(cycle%16);rawse[1083:1080]=4'((cycle+5)%16);
  we=(rst&&age>=20)?((cycle%256<192)?8'hff:8'(seed)):0;
  for(integer l=0;l<8;l=l+1) begin
   addr[24*l+:24]=24'((((age-20)/8)<<6)|(((age-20)%8)*8+l));
   if(cycle%256>=192) begin seed=step(seed);addr[24*l+:6]=seed[5:0];end
   seed=step(seed);data[32*l+:32]=seed;
  end
 end
 always @(posedge ck) begin
  cycle=cycle+1;if(!rst) age=0;else age=age+1;
  #0.001;
  if(sw_hdr[0] !== sw[1084]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit0 MUT%0d",cycle,MUT);
  if(sw_hdr[1] !== sw[1084]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit1 MUT%0d",cycle,MUT);
  if(sw_hdr[2] !== sw[1085]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit2 MUT%0d",cycle,MUT);
  if(sw_hdr[3] !== sw[1085]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit3 MUT%0d",cycle,MUT);
  if(sw_hdr[4] !== sw[1086]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit4 MUT%0d",cycle,MUT);
  if(sw_hdr[5] !== sw[1086]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit5 MUT%0d",cycle,MUT);
  if(sw_hdr[6] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit6 MUT%0d",cycle,MUT);
  if(sw_hdr[7] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit7 MUT%0d",cycle,MUT);
  if(sw_hdr[8] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit8 MUT%0d",cycle,MUT);
  if(sw_hdr[9] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit9 MUT%0d",cycle,MUT);
  if(sw_hdr[10] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit10 MUT%0d",cycle,MUT);
  if(sw_hdr[11] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit11 MUT%0d",cycle,MUT);
  if(sw_hdr[12] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit12 MUT%0d",cycle,MUT);
  if(sw_hdr[13] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit13 MUT%0d",cycle,MUT);
  if(sw_hdr[14] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit14 MUT%0d",cycle,MUT);
  if(sw_hdr[15] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit15 MUT%0d",cycle,MUT);
  if(sw_hdr[16] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit16 MUT%0d",cycle,MUT);
  if(sw_hdr[17] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit17 MUT%0d",cycle,MUT);
  if(sw_hdr[18] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit18 MUT%0d",cycle,MUT);
  if(sw_hdr[19] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit19 MUT%0d",cycle,MUT);
  if(sw_hdr[20] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit20 MUT%0d",cycle,MUT);
  if(sw_hdr[21] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit21 MUT%0d",cycle,MUT);
  if(sw_hdr[22] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit22 MUT%0d",cycle,MUT);
  if(sw_hdr[23] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit23 MUT%0d",cycle,MUT);
  if(sw_hdr[24] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit24 MUT%0d",cycle,MUT);
  if(sw_hdr[25] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit25 MUT%0d",cycle,MUT);
  if(sw_hdr[26] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit26 MUT%0d",cycle,MUT);
  if(sw_hdr[27] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit27 MUT%0d",cycle,MUT);
  if(sw_hdr[28] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit28 MUT%0d",cycle,MUT);
  if(sw_hdr[29] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit29 MUT%0d",cycle,MUT);
  if(sw_hdr[30] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit30 MUT%0d",cycle,MUT);
  if(sw_hdr[31] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit31 MUT%0d",cycle,MUT);
  if(sw_hdr[32] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit32 MUT%0d",cycle,MUT);
  if(sw_hdr[33] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit33 MUT%0d",cycle,MUT);
  if(sw_hdr[34] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit34 MUT%0d",cycle,MUT);
  if(sw_hdr[35] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit35 MUT%0d",cycle,MUT);
  if(sw_hdr[36] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit36 MUT%0d",cycle,MUT);
  if(sw_hdr[37] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit37 MUT%0d",cycle,MUT);
  if(sw_hdr[38] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit38 MUT%0d",cycle,MUT);
  if(sw_hdr[39] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit39 MUT%0d",cycle,MUT);
  if(sw_hdr[40] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit40 MUT%0d",cycle,MUT);
  if(sw_hdr[41] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit41 MUT%0d",cycle,MUT);
  if(sw_hdr[42] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit42 MUT%0d",cycle,MUT);
  if(sw_hdr[43] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit43 MUT%0d",cycle,MUT);
  if(sw_hdr[44] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit44 MUT%0d",cycle,MUT);
  if(sw_hdr[45] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit45 MUT%0d",cycle,MUT);
  if(sw_hdr[46] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit46 MUT%0d",cycle,MUT);
  if(sw_hdr[47] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit47 MUT%0d",cycle,MUT);
  if(sw_hdr[48] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit48 MUT%0d",cycle,MUT);
  if(sw_hdr[49] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit49 MUT%0d",cycle,MUT);
  if(sw_hdr[50] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit50 MUT%0d",cycle,MUT);
  if(sw_hdr[51] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit51 MUT%0d",cycle,MUT);
  if(sw_hdr[52] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit52 MUT%0d",cycle,MUT);
  if(sw_hdr[53] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit53 MUT%0d",cycle,MUT);
  if(sw_hdr[54] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit54 MUT%0d",cycle,MUT);
  if(sw_hdr[55] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit55 MUT%0d",cycle,MUT);
  if(sw_hdr[56] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit56 MUT%0d",cycle,MUT);
  if(sw_hdr[57] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit57 MUT%0d",cycle,MUT);
  if(sw_hdr[58] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit58 MUT%0d",cycle,MUT);
  if(sw_hdr[59] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit59 MUT%0d",cycle,MUT);
  if(sw_hdr[60] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit60 MUT%0d",cycle,MUT);
  if(sw_hdr[61] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit61 MUT%0d",cycle,MUT);
  if(sw_hdr[62] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit62 MUT%0d",cycle,MUT);
  if(sw_hdr[63] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit63 MUT%0d",cycle,MUT);
  if(sw_hdr[64] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit64 MUT%0d",cycle,MUT);
  if(sw_hdr[65] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit65 MUT%0d",cycle,MUT);
  if(sw_hdr[66] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit66 MUT%0d",cycle,MUT);
  if(sw_hdr[67] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit67 MUT%0d",cycle,MUT);
  if(sw_hdr[68] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit68 MUT%0d",cycle,MUT);
  if(sw_hdr[69] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit69 MUT%0d",cycle,MUT);
  if(sw_hdr[70] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit70 MUT%0d",cycle,MUT);
  if(sw_hdr[71] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit71 MUT%0d",cycle,MUT);
  if(sw_hdr[72] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit72 MUT%0d",cycle,MUT);
  if(sw_hdr[73] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit73 MUT%0d",cycle,MUT);
  if(sw_hdr[74] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit74 MUT%0d",cycle,MUT);
  if(sw_hdr[75] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit75 MUT%0d",cycle,MUT);
  if(sw_hdr[76] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit76 MUT%0d",cycle,MUT);
  if(sw_hdr[77] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit77 MUT%0d",cycle,MUT);
  if(sw_hdr[78] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit78 MUT%0d",cycle,MUT);
  if(sw_hdr[79] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit79 MUT%0d",cycle,MUT);
  if(sw_hdr[80] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit80 MUT%0d",cycle,MUT);
  if(sw_hdr[81] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit81 MUT%0d",cycle,MUT);
  if(sw_hdr[82] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit82 MUT%0d",cycle,MUT);
  if(sw_hdr[83] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit83 MUT%0d",cycle,MUT);
  if(sw_hdr[84] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit84 MUT%0d",cycle,MUT);
  if(sw_hdr[85] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit85 MUT%0d",cycle,MUT);
  if(sw_hdr[86] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit86 MUT%0d",cycle,MUT);
  if(sw_hdr[87] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit87 MUT%0d",cycle,MUT);
  if(sw_hdr[88] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit88 MUT%0d",cycle,MUT);
  if(sw_hdr[89] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit89 MUT%0d",cycle,MUT);
  if(sw_hdr[90] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit90 MUT%0d",cycle,MUT);
  if(sw_hdr[91] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit91 MUT%0d",cycle,MUT);
  if(sw_hdr[92] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit92 MUT%0d",cycle,MUT);
  if(sw_hdr[93] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit93 MUT%0d",cycle,MUT);
  if(sw_hdr[94] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit94 MUT%0d",cycle,MUT);
  if(sw_hdr[95] !== sw[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portsw bit95 MUT%0d",cycle,MUT);
  if(se_hdr[0] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit0 MUT%0d",cycle,MUT);
  if(se_hdr[1] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit1 MUT%0d",cycle,MUT);
  if(se_hdr[2] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit2 MUT%0d",cycle,MUT);
  if(se_hdr[3] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit3 MUT%0d",cycle,MUT);
  if(se_hdr[4] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit4 MUT%0d",cycle,MUT);
  if(se_hdr[5] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit5 MUT%0d",cycle,MUT);
  if(se_hdr[6] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit6 MUT%0d",cycle,MUT);
  if(se_hdr[7] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit7 MUT%0d",cycle,MUT);
  if(se_hdr[8] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit8 MUT%0d",cycle,MUT);
  if(se_hdr[9] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit9 MUT%0d",cycle,MUT);
  if(se_hdr[10] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit10 MUT%0d",cycle,MUT);
  if(se_hdr[11] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit11 MUT%0d",cycle,MUT);
  if(se_hdr[12] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit12 MUT%0d",cycle,MUT);
  if(se_hdr[13] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit13 MUT%0d",cycle,MUT);
  if(se_hdr[14] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit14 MUT%0d",cycle,MUT);
  if(se_hdr[15] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit15 MUT%0d",cycle,MUT);
  if(se_hdr[16] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit16 MUT%0d",cycle,MUT);
  if(se_hdr[17] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit17 MUT%0d",cycle,MUT);
  if(se_hdr[18] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit18 MUT%0d",cycle,MUT);
  if(se_hdr[19] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit19 MUT%0d",cycle,MUT);
  if(se_hdr[20] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit20 MUT%0d",cycle,MUT);
  if(se_hdr[21] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit21 MUT%0d",cycle,MUT);
  if(se_hdr[22] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit22 MUT%0d",cycle,MUT);
  if(se_hdr[23] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit23 MUT%0d",cycle,MUT);
  if(se_hdr[24] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit24 MUT%0d",cycle,MUT);
  if(se_hdr[25] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit25 MUT%0d",cycle,MUT);
  if(se_hdr[26] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit26 MUT%0d",cycle,MUT);
  if(se_hdr[27] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit27 MUT%0d",cycle,MUT);
  if(se_hdr[28] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit28 MUT%0d",cycle,MUT);
  if(se_hdr[29] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit29 MUT%0d",cycle,MUT);
  if(se_hdr[30] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit30 MUT%0d",cycle,MUT);
  if(se_hdr[31] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit31 MUT%0d",cycle,MUT);
  if(se_hdr[32] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit32 MUT%0d",cycle,MUT);
  if(se_hdr[33] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit33 MUT%0d",cycle,MUT);
  if(se_hdr[34] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit34 MUT%0d",cycle,MUT);
  if(se_hdr[35] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit35 MUT%0d",cycle,MUT);
  if(se_hdr[36] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit36 MUT%0d",cycle,MUT);
  if(se_hdr[37] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit37 MUT%0d",cycle,MUT);
  if(se_hdr[38] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit38 MUT%0d",cycle,MUT);
  if(se_hdr[39] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit39 MUT%0d",cycle,MUT);
  if(se_hdr[40] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit40 MUT%0d",cycle,MUT);
  if(se_hdr[41] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit41 MUT%0d",cycle,MUT);
  if(se_hdr[42] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit42 MUT%0d",cycle,MUT);
  if(se_hdr[43] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit43 MUT%0d",cycle,MUT);
  if(se_hdr[44] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit44 MUT%0d",cycle,MUT);
  if(se_hdr[45] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit45 MUT%0d",cycle,MUT);
  if(se_hdr[46] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit46 MUT%0d",cycle,MUT);
  if(se_hdr[47] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit47 MUT%0d",cycle,MUT);
  if(se_hdr[48] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit48 MUT%0d",cycle,MUT);
  if(se_hdr[49] !== se[1087]) $fatal(1,"HEADER_CAPTURE_MISMATCH cycle%0d portse bit49 MUT%0d",cycle,MUT);
  header_checks=header_checks+146;

  if(!rst && {qe[1087],qw[1087],qtw,qv,qbad,qf} !== {le[1087],lw[1087],ltw,lv,lbad,lf}) $fatal(1,"STREAM_RESET_MISMATCH cycle%0d MUT%0d",cycle,MUT);
  if(age>=20 && !diag_logged && {le,lw,ltw,lk,la,ld,lv,lxa,lxd,lbad,lf}!=={qe,qw,qtw,qk,qa,qd,qv,qxa,qxd,qbad,qf}) begin
   diag_logged=1;
   $display("STRICT_INITIAL_DIAGNOSTIC cycle%0d tw_v%0b/%0b x_v%0b/%0b relaydiff%0b controldiff%0b twdatadiff%0b xdatadiff%0b MUT%0d",cycle,ltw,qtw,lv,qv,{le,lw}!=={qe,qw},{ltw,lv,lbad,lf}!=={qtw,qv,qbad,qf},{lk,la,ld}!=={qk,qa,qd},{lxa,lxd}!=={qxa,qxd},MUT);
  end
  if(age>=20 && ({le,lw,ltw,lv,lbad,lf}!=={qe,qw,qtw,qv,qbad,qf} ||
     (ltw && {lk,la,ld}!=={qk,qa,qd}) || (lv && {lxa,lxd}!=={qxa,qxd})))
   $fatal(1,"STREAM_EQ_MISMATCH cycle%0d MUT%0d",cycle,MUT);
  if(cycle==10000) begin $display("STREAM_HEADER_NATIVE_COMPOSE PASS edges10000 resets2 actualLPread/corecapture/SETID checks%0d phase%0d allcontrols+validpayload",header_checks,PHASE);$finish;end
 end
endmodule
