from pathlib import Path
q=Path('ring.sv').read_text()
s=q[:q.index(' wire[14:0]scc,lc;')]
s=s.replace('module tb_native_go_pair;','module tb_bf_source_pair;').replace('ot_s81sl_xs4 xs(','ot_s81sl_xs4 #(.INSTANCE("u_s_0S.u_sl.u_xg")) xs(')
s=s.replace('.st(2\'d0),.ri(66\'d0)',".st(so0),.ri(66'd0)")
s+=r''' 
 integer bad_status=0;
 wire rs;ot_dp_dly #(.W(1),.D(15)) reset15(.clk(clk),.d(crs),.q(rs));
 wire[14:0]cc0,lc,cc1;wire[282:0]xa0,ixa1,xa1,fxa;wire[265:0]xb0,ixb1,xb1,fxb;
 wire[535:0]p0,ip1,p1,fp;wire[1:0]so0,so1,back1,st,fst;
 ot_s81_sstn_base566 t0(.ck(clk),.rs(rs),.cci(cc),.xai(xa),.xbi(xb),.e0(bad_status?2'b11:2'b00),.e1(bad_status?2'b11:2'b00),.c0(2'd0),.c1(2'd0),.si(back1),.nf(1'b0),.cc(cc0),.xa(xa0),.xb(xb0),.so(so0));
 ot_s81_sstn_payload536 pld0(.ck(clk),.rs(rs),.i(x2),.o(p0));
 dsfd_rly_2_NW rb(.ck(clk),.rs(rs),.i(so1),.o(back1));
 dsfd_rly_15_SN rc0(.ck(clk),.rs(rs),.i(cc0),.o(lc));
 dsfd_rly_283_EW rx0(.ck(clk),.rs(rs),.i(xa0),.o(ixa1));
 dsfd_rly_266_EW ry0(.ck(clk),.rs(rs),.i(xb0),.o(ixb1));
 dsfd_rly_536_SW rp0(.ck(clk),.rs(rs),.i(p0),.o(ip1));
 ot_s81_sstn_base566 t1(.ck(clk),.rs(rs),.cci(lc),.xai(ixa1),.xbi(ixb1),.e0(fst),.e1(fst),.c0(st),.c1(st),.si(2'd0),.nf(fst[1]),.cc(cc1),.xa(xa1),.xb(xb1),.so(so1));
 ot_s81_sstn_payload536 pld1(.ck(clk),.rs(rs),.i(ip1),.o(p1));
 dsfd_rly_283_EW rx1(.ck(clk),.rs(rs),.i(xa1),.o(fxa));
 dsfd_rly_266_EW ry1(.ck(clk),.rs(rs),.i(xb1),.o(fxb));
 dsfd_rly_536_EN rp1(.ck(clk),.rs(rs),.i(p1),.o(fp));
 wire[11:0]a;wire[6:0]ce;wire[71:0]q[0:6];wire[53:0]cfg,fcfg;wire sg,fg;wire[37:0]prog,fprog;
 ot_s81_cfg7_seq_bfp #(.DELTA(0),.LAYOUT(1),.NROM(7),.NSEG(8),.PHW(10),.PINREG(1)) seq(.clk(clk),.rst_n(rs),.lc(cc1),.a(a),.ce0(ce[0]),.ce1(ce[1]),.ce2(ce[2]),.ce3(ce[3]),.ce4(ce[4]),.ce5(ce[5]),.ce6(ce[6]),.q0(q[0]),.q1(q[1]),.q2(q[2]),.q3(q[3]),.q4(q[4]),.q5(q[5]),.q6(q[6]),.cfg(cfg),.go_e(sg),.f_prog(prog),.st(st));
 genvar b;generate for(b=0;b<7;b=b+1)begin:cfgrom
 ot_rom_4096x72_m8 #(.INSTANCE($sformatf("u_f_0L01.u_r0.u_c1_%0d",b))) rom(.clk(clk),.ce_in(ce[b]),.addr_in(a),.rd_out(q[b]));end endgenerate
 dsfd_rly_54_WN rcfg(.ck(clk),.rs(rs),.i(cfg),.o(fcfg));
 dsfd_rly_38_WN rprog(.ck(clk),.rs(rs),.i(prog),.o(fprog));
 ot_dp_dly #(.W(1),.D(1)) d1go(.clk(clk),.d(sg),.q(fg));
 wire[775:0]c0,c1;wire qy0,qy1;wire[62:0]r0,r1;
 dsfd_bf_front_roots #(.INSTANCE("u_f_0L01.u_r0.u_e1")) front(.ck(clk),.io_clk(clk),.io_n(clk),.io_e(clk),.io_w(clk),.rs(rs),.cfg(fcfg),.f_prog(fprog),.go(fg),.x0(fxa),.x1(fxb),.xb_data({fxb[265:0],fxa[265:0],fp[535:44]}),.xb_meta(fp[43:0]),.qy0(qy0),.qy1(qy1),.c0(c0),.c1(c1),.st(fst));
 dsfd_bf_col #(.INSTANCE("u_f_0L01.u_r0.u_e1w"),.MB(0)) west(.ck(clk),.rs(rs),.ci(c0),.qy(qy0),.r(r0));
 dsfd_bf_col #(.INSTANCE("u_f_0L01.u_r0.u_e1e"),.MB(0)) east(.ck(clk),.rs(rs),.ci(c1),.qy(qy1),.r(r1));
 reg[8191:0]dir;integer fd,rc,n=0,ep=0,ti,ki,et[0:2047],ek[0:2047];reg[1103:0]ev[0:2047],v;
 initial begin void'($value$plusargs("bad_status=%d",bad_status));ring=1;T=1400;if(!$value$plusargs("OT_ROM_DIR=%s",dir))$fatal(1,"images");fd=$fopen({dir,"/producer.txt"},"r");if(!fd)$fatal(1,"producer");
 while(!$feof(fd))begin rc=$fscanf(fd,"%d %d %h\n",ti,ki,v);if(rc==3)begin et[n]=ti;ek[n]=ki;ev[n]=v;n++;end end $fclose(fd);end
 always@(negedge clk)begin cv=0;cb=0;rfv=0;rfs=0;rfd=0;if(cyc==15)rst_n=1;
 while(ep<n&&et[ep]==cyc)begin if(ek[ep]==0)begin cv=1;cb=ev[ep][275:0];end else begin rfv=1;rfs=ev[ep][276];rfd=ev[ep][275:0];end ep++;end end
 integer partials=0,goes=0;reg[62:0]r;
 always@(posedge clk)begin
 if(front.u_view.g_hc.u_front.go_pin)$display("BF_CORE_SAMPLE %0d",cyc+1);
 for(integer m=0;m<2;m++)begin r=m?r1:r0;if(r[0])$display("BF_PARTIAL_SAMPLE %0d side=%0d row=%0d seg=%0d n=%0d pos=%0d val=%08h err=%b",cyc+1,m,r[48:33],r[53:49],r[58:54],r[61:59],r[32:1],r[62]);end
 cyc++;#1;
 if(xv&&(xw[550]||xw[551]))$display("XS_CONTROL %0d cfg=%b go=%b",cyc,xw[551],xw[550]);
 if(sg)$display("BF_SEQ_GO %0d",cyc);
 if(fg)begin goes++;$display("BF_FRONT_GO %0d",cyc);end
 if(fprog[37])$display("BF_PROGRAMME %0d %h",cyc,fprog);
 if(r0[0]||r1[0])partials+=r0[0]+r1[0];
 if(cyc==T)begin $display("BF_END partials=%0d goes=%0d events=%0d consumed=%0d xf=%b sf=%b ringfault=%b cf=%b seq=%b front=%b cf_local=%b",partials,goes,n,ep,xf,sf,ringfault,rd[69],st[1],fst[1],cf.flt);$finish;end
 end
endmodule
'''
Path('tb.sv').write_text(s)
