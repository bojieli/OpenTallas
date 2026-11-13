`timescale 1ps/1ps
// Native dated producer/control and selected NB2 arithmetic/EF feedback, controlled common clock/reset.
module tb_native_go_pair;
 reg clk=0; always begin #416 clk=1; #417 clk=0; end
 reg rst_n=0; integer cyc=0,T=2000,gb=1,fix_tag=0,bad_tag=0,ring=0,transport_mode=0;
 reg cv=0; reg[275:0] cb=0;
 wire iv,xf; wire[159:0] id;
 ot_s81sl_xrt1 xr(.clk(clk),.rst_n(rst_n),.sid(4'd0),
   .dl_ev(1'b0),.dl_e('0),.dl_wv(1'b0),.dl_w('0),.dl_vv(cv),.dl_vb(cb[275:1]),
   .lo_v(5'd0),.lo_d('0),.p_v(5'd0),.p_d('0),.e_v(5'd0),.e_c('0),.e_d('0),
   .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),
   .is_v(iv),.is_d(id),.fault(xf));
 reg[2:0]dgv=0;reg[20:0]dgi=0;reg[3071:0]dgd=0;
 reg rfv=0,rfs=0;reg[275:0]rfd=0;wire[2:0]rgv,rgfam;wire[20:0]rgi;wire[3071:0]rgd;wire ringfault;
 // Actual selected xg producer: native ring header/fragment decode generates gather family.
 ot_s81sl_rstopt_xo gather_ring(.clk(clk),.rst_n(rst_n),.sid(4'd0),.ri_w(1104'd0),.ri_e(1104'd0),.ro_e(),.ro_w(),
 .vi(276'd0),.vo(),.xf_v({2'd0,rfv,2'd0}),.xf_s({2'd0,rfs,2'd0}),.xf({552'd0,rfd,552'd0}),
 .nx_wi(),.nx_ei(),.nx_eo(173'd0),.nx_wo(173'd0),.dl_ev(),.dl_e(),.dl_wv(),.dl_w(),.dl_vv(),.dl_vb(),
 .ci_dir(3'd0),.ci_b(1104'd0),.g_v(rgv),.g_fam(rgfam),.g_idx(rgi),.g_d(rgd),.fault(ringfault));
 wire[2:0]gv=ring?rgv:dgv,gfam=ring?rgfam:3'd0;wire[20:0]gi=ring?rgi:dgi;wire[3071:0]gd=ring?rgd:dgd;
 wire xv,sf;wire[1100:0]xw;
 // XS4-CORE 11-13 (HARD-S81-DSDV-1): face rule, one pin per kept capture copy / own port flop; value-preserving, 0 cycles
 ot_s81sl_xs4 xs(.clk(clk),.rst_n(rst_n),.g_v({21{gv}}),.g_fam({21{gfam}}),.g_idx({21{gi}}),.g_d(gd),
   .is_v({2{iv}}),.is_d(id),.xw_v(xv),.xw_d(xw),.fault(sf));
 reg[1:0]mk=0;always@(posedge clk)if(!rst_n)mk<=0;else mk<={mk[0],1'b1};
 wire[1103:0]word0={xw[1100:565],xw[0],mk[1],xw[564:0],mk[1]};
 // Actual current bind_ev2 x_W0_in: all four 276-bit lanes have41 bound stages.
 reg[1103:0]transport[0:46];integer k;
 always@(posedge clk)begin transport[0]<=word0;for(k=1;k<47;k=k+1)transport[k]<=transport[k-1];end
 // Disabled test-only age recipes: strict EV2 asbuilt ages lane0/1/2/3=46/41/45/47.
 wire[1103:0]w=transport_mode==1?{transport[46][1103:828],transport[44][827:552],transport[40][551:276],transport[45][275:0]}:
                  transport_mode==2?{transport[40][1103:276],transport[41][275:0]}:transport[40];wire crs;wire[14:0]cc;wire[282:0]xa;wire[265:0]xb;wire[535:0]x2;wire[69:0]rd;
 // Controlled L3 profile: forwarded clocks open after the regional reset release.
 reg gate=0;always@(negedge clk)gate<=crs;wire fclk=clk&gate;
 dsfd_cfifo_crs4 #(.LFACE(0),.LGATE(0)) cf(.cr(clk),.cr_s(clk),.rst(rst_n),.rs(crs),
   .xl0(w[275:0]),.xl1(w[551:276]),.xl2(w[827:552]),.xl3(w[1103:828]),.xk({4{fclk}}),
   .lk(12'b010010010010),.cc(cc),.xa(xa),.xb(xb),.x2(x2),.st(2'd0),.ri(66'd0),.rd(rd));
 wire[14:0]scc,lc;wire[282:0]sxa,rxa;wire[265:0]sxb,rxb;wire[1:0]st,unused_so;
 ot_s81_sstn_base566 station(.ck(clk),.rs(crs),.cci(cc),.xai(xa),.xbi(xb),
   .e0(ef),.e1(2'b11),.c0(st),.c1(2'd0),.si(2'd0),.nf(1'b0),
   .cc(scc),.xa(sxa),.xb(sxb),.so(unused_so));
 dsfd_rly_15_SN relay_cc(.ck(clk),.rs(crs),.i(scc),.o(lc));
 dsfd_rly_283_EW relay_xa(.ck(clk),.rs(crs),.i(sxa),.o(rxa));
 dsfd_rly_266_EW relay_xb(.ck(clk),.rs(crs),.i(sxb),.o(rxb));
 wire[11:0]a;wire[6:0]ce;wire[71:0]q[0:6];wire[53:0]cfg,ocfg;wire sg,og;wire[1:0]tag;
 wire[282:0]oxa;wire[265:0]oxb;
 wire bf0,sf0,wk0,busy0,qf0,bf1,sf1,wk1,busy1,qf1;
 wire[1:0]ef=gb?{bf1,sf1}:{bf0,sf0};
 ot_s81_cfg7_seq #(.AW(15),.CW(25),.LAYOUT(1),.NROM(7),.NSEG(8),.PHW(10),.PINREG(1),.PQ(1)) seq(
   .clk(clk),.rst_n(crs),.lc(lc),.a(a),.ce0(ce[0]),.ce1(ce[1]),.ce2(ce[2]),.ce3(ce[3]),.ce4(ce[4]),.ce5(ce[5]),.ce6(ce[6]),
   .q0(q[0][47:0]),.q1(q[1][47:0]),.q2(q[2][47:0]),.q3(q[3][47:0]),.q4(q[4][47:0]),.q5(q[5][47:0]),.q6(q[6][47:0]),
   .cfg(cfg),.go_e(sg),.go_tag(tag),.ef(ef),.st(st));
 genvar b;generate for(b=0;b<7;b=b+1)begin:cfgrom
   ot_rom_4096x72_m8 #(.INSTANCE($sformatf("u_f_0L01.u_r0.u_c0_%0d",b))) rom(.clk(clk),.ce_in(ce[b]),.addr_in(a),.rd_out(q[b]));
 end endgenerate
 dsfd_qbank_S bank(.ck(clk),.rs(crs),.i_cfg(cfg),.i_go(sg),.i_x0(rxa),.i_x1(rxb),.o_cfg(ocfg),.o_go(og),.o_x0(oxa),.o_x1(oxb));
 // DISABLED robust tag retime: four reset-free FF, parallel to qbank_S two-edge GO.
 reg[1:0]tag_d1,tag_d2;always@(posedge clk)begin tag_d1<=tag;tag_d2<=tag_d1;end
 // Secondary conditional hold candidate: two FF; no spacing-independent claim.
 reg[1:0]held_tag;always@(posedge clk)if(sg)held_tag<=tag;
 wire[1:0]selected_tag=(fix_tag==1?tag_d2:(fix_tag==2?held_tag:tag)) ^ (bad_tag?2'b01:2'b00);
 wire[1:0]pv0,pv1,err0,err1;wire[63:0]val0,val1;wire[31:0]row0,row1;wire[9:0]seg0,seg1,n0,n1;wire[5:0]pos0,pos1;
 ot_v41_rom_elem_q_qxpq_w10_gb #(.CGR(0),.EARLY(1),.FAST(1),.FRONT_PAR(0),.MTP(1),.NB(2),.PP(1),.PQ(1),.QM(5),.QPIPE(1),.QP_CAP(0),.QP_CSAM(10),.QP_P1(1),.QP_XS(1),.QS(5),.QTIMING_FIX(1),.QW(0),.QX(10),.QY(1),.QZ(1),.QZ_NE(4),.QZ_NS(8),.RSTP(1),.INSTANCE("u_f_0L01.u_r0.u_e0"),.GO_BOUNDARY(0)) q0(
 .clk(clk),.rst_n(crs),.cfg_v(ocfg[53]),.cfg_a(ocfg[4:0]),.cfg_d(ocfg[52:5]),.go(og),.go_tag(selected_tag),
 .xs_v(oxa[282]),.xs_p(oxa[276:269]),.xs_b(oxa[268:266]),.xs_pos(oxa[279:277]),
 .xs_q0(oxa[255:0]),.xs_e0(oxa[265:256]),.xs_q1(oxb[255:0]),.xs_e1(oxb[265:256]),
 .walking(wk0),.bank_free(bf0),.sh_free(sf0),.busy(busy0),.fault(qf0),
 .pv(pv0),.pval(val0),.prow(row0),.pseg(seg0),.pnseg(n0),.perr(err0),.ppos(pos0));
 ot_v41_rom_elem_q_qxpq_w10_gb #(.CGR(0),.EARLY(1),.FAST(1),.FRONT_PAR(0),.MTP(1),.NB(2),.PP(1),.PQ(1),.QM(5),.QPIPE(1),.QP_CAP(0),.QP_CSAM(10),.QP_P1(1),.QP_XS(1),.QS(5),.QTIMING_FIX(1),.QW(0),.QX(10),.QY(1),.QZ(1),.QZ_NE(4),.QZ_NS(8),.RSTP(1),.INSTANCE("u_f_0L01.u_r0.u_e0"),.GO_BOUNDARY(1)) q1(
 .clk(clk),.rst_n(crs),.cfg_v(ocfg[53]),.cfg_a(ocfg[4:0]),.cfg_d(ocfg[52:5]),.go(og),.go_tag(selected_tag),
 .xs_v(oxa[282]),.xs_p(oxa[276:269]),.xs_b(oxa[268:266]),.xs_pos(oxa[279:277]),
 .xs_q0(oxa[255:0]),.xs_e0(oxa[265:256]),.xs_q1(oxb[255:0]),.xs_e1(oxb[265:256]),
 .walking(wk1),.bank_free(bf1),.sh_free(sf1),.busy(busy1),.fault(qf1),
 .pv(pv1),.pval(val1),.prow(row1),.pseg(seg1),.pnseg(n1),.perr(err1),.ppos(pos1));
 wire core_go=gb?q1.go_e_in:q0.go_e_in;wire[1:0]core_tag=gb?q1.go_tag_e_in:q0.go_tag_e_in;
 wire[1:0]pv=gb?pv1:pv0,perr=gb?err1:err0;wire[63:0]pval=gb?val1:val0;wire[31:0]prow=gb?row1:row0;
 wire[9:0]pseg=gb?seg1:seg0,pnseg=gb?n1:n0;wire[5:0]ppos=gb?pos1:pos0;
 wire qfault=gb?qf1:qf0,walking=gb?wk1:wk0,qbusy=gb?busy1:busy0;
 reg[8191:0]dir;integer fd,rc,n=0,ep=0,ti,ki,j,et[0:1023],ek[0:1023];reg[1030:0]ev[0:1023],v;
 initial begin
  void'($value$plusargs("T=%d",T));void'($value$plusargs("gb=%d",gb));void'($value$plusargs("fix_tag=%d",fix_tag));void'($value$plusargs("bad_tag=%d",bad_tag));void'($value$plusargs("ring=%d",ring));void'($value$plusargs("transport_mode=%d",transport_mode));
  $display("TRANSPORT_PROFILE mode=%0d lane0=%0d lane1=41 lane2=%0d lane3=%0d",transport_mode,transport_mode==1?46:(transport_mode==2?42:41),transport_mode==1?45:41,transport_mode==1?47:41);
  if(!$value$plusargs("OT_ROM_DIR=%s",dir))$fatal(1,"missing images");fd=$fopen({dir,"/producer.txt"},"r");if(!fd)$fatal(1,"missing programme");
  while(!$feof(fd))begin rc=$fscanf(fd,"%d %d %h\n",ti,ki,v);if(rc==3)begin et[n]=ti;ek[n]=ki;ev[n]=v;n=n+1;end end $fclose(fd);
 end
 always@(negedge clk)begin
  cv=0;cb=0;dgv=0;dgi=0;dgd=0;rfv=0;rfs=0;rfd=0;if(cyc==15)rst_n=1;
  while(ep<n&&et[ep]==cyc)begin
   if(ek[ep]==0)begin cv=1;cb=ev[ep][275:0];$display("SOURCE_CTL %0d %h",cyc,cb);end
   else if(ek[ep]==1)begin dgv[0]=1;dgi[6:0]=ev[ep][1030:1024];dgd[1023:0]=ev[ep][1023:0];end
   else if(ek[ep]==2)begin rfv=1;rfs=ev[ep][276];rfd=ev[ep][275:0];end
   ep=ep+1;
  end
 end
 integer cfgwords=0,goes=0,streams=0,lastcfg=-1,partials=0;reg[4:0]last_status=0;reg seen_xs_fault=0;
 always@(posedge clk)begin
  cyc=cyc+1;#1;
  if(ring&&sf&&!seen_xs_fault)begin seen_xs_fault=1;$display("XS_FAULT_DETAIL %0d issuer=%b calendar=%b control=%b write=%b read=%b output=%b",cyc,xs.is_fault,xs.cal_fault,xs.ctl_fault,xs.wr_fault,xs.rd_fault,xs.lx_fault);end
  if(ring&&rgv[0])$display("RING_GATHER %0d family=%0d index=%0d data=%h",cyc,rgfam[0],rgi[6:0],rgd[1023:0]);
  if(iv)$display("ISSUER_PIN %0d %h",cyc,id);
  if(xv&&(xw[550]||xw[551]))$display("XS_CONTROL %0d cfg=%b go=%b",cyc,xw[551],xw[550]);
  if(cfg[53])begin cfgwords=cfgwords+1;lastcfg=cyc;$display("CFG_WORD %0d %h",cyc,cfg);end
  if(sg)$display("SEQUENCER_GO %0d tag=%0d st=%0d",cyc,tag,st);
  if(og)$display("RAW_Q_GO %0d direct_tag=%0d held_tag=%0d",cyc,tag,held_tag);
  if(core_go)begin goes=goes+1;$display("CORE_GO %0d tag=%0d last_cfg=%0d st=%0d",cyc,core_tag,lastcfg,st);end
  if(oxa[282])begin streams=streams+1;$display("STREAM %0d %h%h",cyc,oxa,oxb);end
  for(integer mb=0;mb<2;mb=mb+1)if(pv[mb])begin
   partials=partials+1;$display("PAIR_RET %0d mb=%0d row=%0d seg=%0d n=%0d pos=%0d val=%08h err=%b",cyc,mb,prow[16*mb+:16],pseg[5*mb+:5],pnseg[5*mb+:5],ppos[3*mb+:3],pval[32*mb+:32],perr[mb]);
  end
  if({qfault,qbusy,walking,ef}!=last_status)begin last_status={qfault,qbusy,walking,ef};$display("Q_FEEDBACK %0d fault=%b busy=%b walk=%b bank_free=%b sh_free=%b",cyc,qfault,qbusy,walking,ef[1],ef[0]);end
  if(cyc==T)begin $display("RING_END enabled=%0d fault=%b",ring,ringfault);$display("PAIR_END partials=%0d q_fault=%b busy=%b walking=%b bank_free=%b sh_free=%b",partials,qfault,qbusy,walking,ef[1],ef[0]); $display("NATIVE_GO_END events=%0d consumed=%0d gos=%0d cfg_words=%0d streams=%0d xr_fault=%b xs_fault=%b cf_fault=%b seq_fault=%b",n,ep,goes,cfgwords,streams,xf,sf,rd[69],st[1]);$finish;end
 end
endmodule
