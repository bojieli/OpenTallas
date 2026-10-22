`timescale 1ns/1ps
// Bounded real L2 WKV producer pair. All clocks have explicitly common phase.
// No physical route age, full D512 residency or arithmetic launch is inferred.
module cap_sukv_endpoint #(parameter integer SID=5, KV=0)(
 input wire clk,rst_n,input wire[1103:0] line,input wire[1103:0] link,
 output wire[1103:0] roe,input wire[1:0] capv,input wire[23:0] capa,input wire[63:0] capd,
 input wire probe_v,input wire[9:0] probe_a,output wire probe_qv,output wire[255:0] probe_qd,
 output wire kvdone,output wire fault);
 wire de,dw,dv;wire[1103:0] e,w,ci,ro_w;wire[275:0] v,vo;wire[2:0]dir;
 wire[4:0] cv,swv,lov;wire[159:0]cd;wire[49:0]swa;wire[39:0]swm;wire[1279:0]swd,lod;
 wire rf,xf,pf,kf,kbusy;wire pcv,pswv,lv,sv,xrv,xqv,xwv;wire[159:0]pcd,sd;
 wire[9:0]pswa,xra,xwa;wire[7:0]pswm,xwm;wire[255:0]pswd,ld,xqd,xwd;
 wire[1:0]cwv;wire[23:0]cwa;wire[63:0]cwd;wire[67:0]udn;wire[409:0]uup;
 ot_s81sl_rstopt r(.clk(clk),.rst_n(rst_n),.sid(4'(SID)),.ri_w(line|link),.ri_e(1104'd0),.ro_e(roe),.ro_w(ro_w),
 .vi(276'd0),.vo(vo),.xf_v(5'd0),.xf_s(5'd0),.xf(1380'd0),.nx_eo(173'd0),.nx_wo(173'd0),
 .dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(v),.ci_dir(dir),.ci_b(ci),.fault(rf));
 ot_s81sl_xrt x(.clk(clk),.rst_n(rst_n),.sid(4'(SID)),.dl_ev(de),.dl_e(e),.dl_wv(dw),.dl_w(w),.dl_vv(dv),.dl_vb(v),
 .ci_dir(dir),.ci_b(ci),.bi(1104'd0),.c_v(cv),.c_d(cd),.sw_v(swv),.sw_a(swa),.sw_m(swm),.sw_d(swd),
 .lo_v(lov),.lo_d(lod),.p_v(5'd0),.p_d(160'd0),.e_v(5'd0),.e_c(10'd0),.e_d(480'd0),
 .eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),.x_rbv(1'b0),.x_rbd(32'd0),.fault(xf));
 // Exact production W594 down and W667 up records, DL4; leaf0 only.
 ot_s81sl_rly #(.W(594),.D(4)) dn(.clk(clk),.d({cv[0],cd,swv[0],swa[9:0],swm[7:0],swd[255:0],capv,capa,capd,68'd0}),
 .q({pcv,pcd,pswv,pswa,pswm,pswd,cwv,cwa,cwd,udn}));
 ot_s81sl_rly #(.W(667),.D(4)) up(.clk(clk),.d({lv,ld,410'd0}),.q({lov[0],lod[255:0],uup}));
 assign lov[4:1]=0;assign lod[1279:256]=0;
 wire krv,kwv;wire[9:0]kra,kwa;wire[7:0]kwm;wire[255:0]kwd;
 assign xrv=kbusy?krv:probe_v;assign xra=kbusy?kra:probe_a;
 assign xwv=kbusy?kwv:1'b0;assign xwa=kwa;assign xwm=kwm;assign xwd=kwd;
 assign probe_qv=xqv&&!kbusy;assign probe_qd=xqd;
 ot_s81sl_vp u(.clk(clk),.rst_n(rst_n),.c_v(pcv),.c_d(pcd),.sw_v(pswv),.sw_a(pswa),.sw_m(pswm),.sw_d(pswd),
 .cw_v(cwv),.cw_a(cwa),.cw_d(cwd),.lo_v(lv),.lo_d(ld),.s_v(sv),.s_d(sd),.x_rv(xrv),.x_ra(xra),.x_qv(xqv),.x_qd(xqd),
 .x_wv(xwv),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd),.hq_v(1'b0),.hq_d(256'd0),.fault(pf));
 generate if(KV)begin:gk
 ot_s81sl_kv_leaf #(.CNIK(1),.CP(1)) k(.clk(clk),.rst_n(rst_n),.c_v(sv),.c_d(sd),.busy(kbusy),.done(kvdone),.fault(kf),
 .x_rv(krv),.x_ra(kra),.x_qv(xqv&&kbusy),.x_qd(xqd),.x_wv(kwv),.x_wa(kwa),.x_wm(kwm),.x_wd(kwd));
 end else begin assign kbusy=0;assign kvdone=0;assign kf=0;assign krv=0;assign kra=0;assign kwv=0;assign kwa=0;assign kwm=0;assign kwd=0;end endgenerate
 assign fault=rf|xf|pf|kf;
endmodule

module tb_cap_sukv;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0;integer cyc=0,mut=0,bad=0,cap_count=0,got_pair=0,gk_done=0;
 reg[8191:0]dir;reg[127:0]gain[0:131];reg[255:0]expect_pair[0:0];reg[159:0]capcfg[0:0],gk_command[0:0];
 reg[2:0]gv=0;reg[20:0]gi=0;reg[3071:0]gd=0;reg iv=0;reg[159:0]id=0;
 wire xv,xf;wire[1100:0]xw;reg[1:0]mk=0;
 ot_s81sl_xs4 xs(.clk(clk),.rst_n(rst_n),.g_v(gv),.g_fam(3'd0),.g_idx(gi),.g_d(gd),.is_v(iv),.is_d(id),.xw_v(xv),.xw_d(xw),.fault(xf));
 always @(posedge clk)if(!rst_n)mk<=0;else mk<={mk[0],1'b1};
 wire[1103:0]x={xw[1100:565],xw[0],mk[1],xw[564:0],mk[1]};
 reg[1:0]gs=0;always @(posedge clk or negedge rst_n)if(!rst_n)gs<=0;else gs<={gs[0],1'b1};
 reg gl=0;always @(negedge clk)gl<=gs[1];wire xkg=clk&gl;
 wire[69:0]ret0,ret1;wire[1103:0]xo0,xo1;wire[3:0]xok0,xok1;
 col_h9_l4_lp #(.INSTANCE("f")) f(.ck_r0(clk),.ck_r1(clk),.ck_r2(clk),.rst_n(rst_n),.x(x),.xk({4{xkg}}),.lk({4{3'd2}}),.xo(xo0),.xok(xok0),.ret(ret0));
 col_h9_l4_lp #(.INSTANCE("f2")) f2(.ck_r0(clk),.ck_r1(clk),.ck_r2(clk),.rst_n(rst_n),.x(x),.xk({4{xkg}}),.lk({4{3'd4}}),.xo(xo1),.xok(xok1),.ret(ret1));
 reg cfgv=0;reg[159:0]cfgd=0;wire[5:0]sv;wire[71:0]sa;wire[191:0]sd;wire[3:0]nv;wire[47:0]na;wire[127:0]nd;wire cf;
 ot_s81sl_capc5r cap(.rt_w({ret1,ret0,70'd1,70'd1}),.rt_e({4{70'd1}}),.cfg_v(cfgv),.cfg_d(cfgd),
 .cw_s_v(sv),.cw_s_a(sa),.cw_s_d(sd),.cw_n_v(nv),.cw_n_a(na),.cw_n_d(nd),.fault(cf),
 .ck_rt(clk),.ck_cw(clk),.ck_ce(clk),.ck_rn(clk),.ck_rs(clk),
 .rst_n_rt(rst_n),.rst_n_cw(rst_n),.rst_n_ce(rst_n),.rst_n_rn(rst_n),.rst_n_rs(rst_n));
 wire[1079:0]cb;wire[11:0]ce;wire[47:0]cv;wire[269:0]co;
 ot_pl_land_n32_chunk_w #(.W(270),.D(4),.CHUNK_BITS(24)) cw(.ck(clk),.rsi(rst_n),.i({sv,sa,sd}),.bank(cb),.epo(ce),.vld(cv));
 ot_pl_land_chunk_r #(.W(270),.D(4),.K(2),.CHUNK_BITS(24)) cr(.ck(clk),.rsi(rst_n),.bank(cb),.epo(ce),.vld(cv),.o(co));
 wire[5:0]lsv=co[269:264];wire[71:0]lsa=co[263:192];wire[191:0]lsd=co[191:0];
 reg[1103:0]line0=0,line1=0;wire[1103:0]ro0,ro1;reg pr=0;wire pq;wire[255:0]pqd;wire dk,sk;wire[1:0]fault;
 cap_sukv_endpoint #(.SID(5)) src(.clk(clk),.rst_n(rst_n),.line(line0),.link(1104'd0),.roe(ro0),.capv(lsv[1:0]),.capa(lsa[23:0]),.capd(lsd[63:0]),
 .probe_v(1'b0),.probe_a(10'd0),.probe_qv(),.probe_qd(),.kvdone(sk),.fault(fault[0]));
 // Bench calendar reproduces selected seam G=R0 at the landing core.
 // External kit reset releases two edges before core reset; no physical epoch is inferred.
 reg[1:0]land_reset_calendar=0;
 always @(posedge clk or negedge rst_n)if(!rst_n)land_reset_calendar<=0;else land_reset_calendar<={land_reset_calendar[0],1'b1};
 reg lane_gate=0;always @(negedge clk)lane_gate<=land_reset_calendar[1];
 wire lane_ck=clk&lane_gate;
 wire[1103:0]land_input=ro0^((mut&&ro0[0]&&ro0[3:1]==4)?(1104'd1<<52):1104'd0);
 wire[1103:0]link;wire[3:0]land_fault;
 genvar ln;generate for(ln=0;ln<4;ln++)begin:seam
 dsfd_dvland_276 l(.ck_f(lane_ck),.i(land_input[276*ln+:276]),.ck(clk),.rs(land_reset_calendar[1]),.k(3'd2),.o(link[276*ln+:276]),.fault(land_fault[ln]));
 end endgenerate
 cap_sukv_endpoint #(.SID(7),.KV(1)) dst(.clk(clk),.rst_n(rst_n),.line(line1),.link(link),.roe(ro1),.capv(2'd0),.capa(24'd0),.capd(64'd0),
 .probe_v(pr),.probe_a(10'd692),.probe_qv(pq),.probe_qd(pqd),.kvdone(dk),.fault(fault[1]));
 function automatic[1103:0]ctl(input integer sid,target,input[159:0]body);
 reg[185:0]p;begin p=0;p[15:0]=16'd1<<sid;p[20:16]=target;p[25:21]=(target==0||target==5)?1:0;p[185:26]=body;
 ctl=0;ctl[0]=1;ctl[8:4]=1;ctl[21+:186]=p;end endfunction
 integer fd,rc,nev=0,ep=0,et[0:511],ek[0:511],ti,ki,j;reg[1030:0]eh[0:511],hi;reg[159:0]body;
 initial begin
 void'($value$plusargs("MUT=%d",mut));if(!$value$plusargs("OT_ROM_DIR=%s",dir))$fatal;
 $readmemh({dir,"/capture.hex"},capcfg);$readmemh({dir,"/gain.hex"},gain);$readmemh({dir,"/gk_command.hex"},gk_command);$readmemh({dir,"/expect_pair.hex"},expect_pair);
 fd=$fopen({dir,"/dense_stim.txt"},"r");while(!$feof(fd))begin rc=$fscanf(fd,"%d %d %h\n",ti,ki,hi);if(rc==3)begin et[nev]=ti;ek[nev]=ki;eh[nev]=hi;nev++;end end $fclose(fd);
 end
 always @(negedge clk)begin
 gv=0;gi=0;gd=0;iv=0;id=0;cfgv=0;line0=0;line1=0;pr=0;
 if(cyc==15)rst_n=1;if(cyc==150)begin cfgv=1;cfgd=capcfg[0];end
 while(ep<nev&&et[ep]==cyc)begin if(ek[ep]==0)begin iv=1;id=eh[ep][159:0];end else begin gv[0]=1;gi[6:0]=eh[ep][1030:1024];gd[1023:0]=eh[ep][1023:0];end ep++;end
 if(cyc>=500&&cyc<632)begin j=cyc-500;body=0;body[9:0]=(j<4)?528+j:896+j-4;body[13:10]=15;body[141:14]=gain[j];line1=ctl(7,5,body);end
 if(cyc==3300)begin body=0;body[3:0]=1;body[6:4]=4;body[11:7]=1;body[27:12]=128;body[40:31]=692;line0=ctl(5,4,body);end
 if(cyc==3309)begin body=6|(2<<4)|(1<<24);line0=ctl(5,0,body);end
 if(cyc==3450)pr=1;
 if(cyc==3500)begin body=gk_command[0];line1=ctl(7,0,body);end
 end
 always @(posedge clk)begin
 cyc<=cyc+1;
 for(integer p=0;p<2;p++)if(sv[p])begin cap_count++;
 $display("EV CAP_WRITE %0d %0d %08h",cyc,sa[12*p+:12],sd[32*p+:32]);end
 if(dst.pswv && dst.pswa==692)$display("JSON {\"record\":\"event\",\"kind\":\"CARRIAGE_WRITE\",\"edge\":%0d,\"instance\":\"dst.u\",\"owner\":\"L2.attn.kv_norm.sumsq\",\"job\":\"L2_WKV_PAIR0\",\"rank\":0,\"source_native_row\":2,\"target_row\":692,\"mask8\":\"%02h\",\"word256\":\"%064h\"}",cyc,dst.pswm,dst.pswd);
 if(pq)begin got_pair++;if(pqd!==expect_pair[0])begin bad++;$display("PAIR_MISMATCH got=%064h expected=%064h",pqd,expect_pair[0]);end end
 if(dst.sv && dst.sd[3:0]==15)$display("JSON {\"record\":\"event\",\"kind\":\"DISPATCH_CAPTURE\",\"command_kind\":\"GK\",\"edge\":%0d,\"instance\":\"dst.gk.k\",\"owner\":\"L2.attn.kv_norm.sumsq\",\"job\":\"L2_KV_GAIN0\",\"gain_set\":0,\"gain_epoch\":1}",cyc);
 if(dk)begin gk_done++;$display("EV GK_DONE %0d",cyc);
 $display("JSON {\"record\":\"event\",\"kind\":\"GK_DONE\",\"command_kind\":\"GK\",\"edge\":%0d,\"instance\":\"dst.gk.k\",\"owner\":\"L2.attn.kv_norm.sumsq\",\"job\":\"L2_KV_GAIN0\",\"gain_set\":0,\"gain_epoch\":1}",cyc);end
 if(cyc==4900)begin
 $display("JSON {\"record\":\"event\",\"kind\":\"RUN_END\",\"edge\":%0d,\"instance\":\"tb_cap_sukv\",\"future_consumer_lease\":null}",cyc);
 if(cap_count!=8||got_pair!=1||gk_done!=1||ep!=nev||xf||cf||(|fault)||(|land_fault)||ret0[69]||ret1[69])bad++;
 $display("CAP_SUKV_END cap=%0d pair=%0d gain=%0d bad=%0d faults=%b xs=%b capfault=%b",cap_count,got_pair,gk_done,bad,fault,xf,cf);
 if(bad)$fatal(1,"CAP_SUKV_FAIL");$display("CAP_SUKV_PASS");$finish;end
 end
endmodule

module cap_vp_probe(input wire clk,rst_n,input wire[1:0]wv,input wire[8:0]wa0,wa1,input wire[127:0]wd0,wd1,wm0,wm1,input wire re0,re1,input wire[9:0]ra0,ra1,input wire qv,input wire[255:0]qd,input wire lo_v,input wire[255:0]lo_d);
 integer edge_n=0,readid=0;integer rq[$];
 always @(posedge clk)begin
 edge_n<=edge_n+1;
 if(rst_n)begin
 if(wv[0])$display("JSON {\"record\":\"event\",\"kind\":\"SRAM_COMMIT\",\"edge\":%0d,\"instance\":\"%m\",\"row\":%0d,\"mask\":\"%032h\",\"word128\":\"%032h\"}",edge_n,2*wa0,wm0,wd0);
 if(wv[1])$display("JSON {\"record\":\"event\",\"kind\":\"SRAM_COMMIT\",\"edge\":%0d,\"instance\":\"%m\",\"row\":%0d,\"mask\":\"%032h\",\"word128\":\"%032h\"}",edge_n,2*wa1+1,wm1,wd1);
 if(re0||re1)$display("JSON {\"record\":\"event\",\"kind\":\"READ_REQUEST\",\"edge\":%0d,\"sram_sample_edge\":%0d,\"instance\":\"%m\",\"row0\":%0d,\"row1\":%0d,\"bank0\":%0d,\"bank1\":%0d}",edge_n,edge_n,ra0,ra1,re0,re1);
 if(qv||lo_v)$display("JSON {\"record\":\"event\",\"kind\":\"READ_READY\",\"edge\":%0d,\"instance\":\"%m\",\"word256\":\"%064h\"}",edge_n,qv?qd:lo_d);
 end end
endmodule
bind ot_s81sl_vp cap_vp_probe proof(.clk(clk),.rst_n(rst_n),.wv(wv),.wa0(wa[0]),.wa1(wa[1]),.wd0(wd[0]),.wd1(wd[1]),.wm0(wm[0]),.wm1(wm[1]),.re0(re_e),.re1(re_o),.ra0(ra_e),.ra1(ra_o),.qv(x_qv),.qd(x_qd),.lo_v(lo_v),.lo_d(lo_d));
