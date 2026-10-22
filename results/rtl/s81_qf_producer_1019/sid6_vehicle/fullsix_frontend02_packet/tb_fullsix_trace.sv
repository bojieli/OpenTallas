`timescale 1ps/1ps
// Private raw-qnorm source: original FP32 CTLs only; no g/return/Q stimulus.
module tb_fullsix_trace;
reg clk=0,rst_n=0;always #417 clk=~clk;
integer n=-1,err=0,nq=0,nw=0,mut=0;localparam integer ORIGIN=32;
reg ev=0;reg [1103:0] eb=0;wire fx,fp,fs,fq,fr,fxs;
reg [185:0] ctl[0:12000];reg [12000:0] ctlv=0;reg [531:0] gold[0:19];
string dir;integer fd,rc,at;reg [185:0] payload;
wire [4:0] cv,swv;wire [159:0] cd;wire [49:0] swa;wire [39:0] swm;wire [1279:0] swd;
wire cap_cfg_v;wire[159:0]cap_cfg_d;
wire is_v;wire [159:0] is_d;wire [2:0] cid;wire [1103:0] cib;
wire lo_v;wire [255:0] lo_d;wire lov;wire [255:0] lod;
ot_s81sl_xr #(.HB(1)) xr(.clk(clk),.rst_n(rst_n),.sid(4'd6),.dl_ev(ev),.dl_e(eb),
 .dl_wv(1'b0),.dl_w(1104'd0),.dl_vv(1'b0),.dl_vb(276'd0),.ci_dir(cid),.ci_b(cib),
 .bi(1104'd0),.bo(),.c_v(cv),.c_d(cd),.sw_v(swv),.sw_a(swa),.sw_m(swm),.sw_d(swd),
 .lo_v({2'd0,lov,2'd0}),.lo_d({512'd0,lod,512'd0}),.p_v(5'd0),.p_d(160'd0),
 .e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),
 .x_rbv(1'b0),.x_rbd(32'd0),.is_v(is_v),.is_d(is_d),.cfg_v(cap_cfg_v),.cfg_d(cap_cfg_d),.fault(fx));
wire[9:0]cw_v;wire[119:0]cw_a;wire[319:0]cw_d;
wire[1:0]cw2_v;wire[23:0]cw2_a;wire[63:0]cw2_d;
wire c_v,sw_v;wire[159:0]c_d;wire[9:0]sw_a;wire[7:0]sw_m;wire[255:0]sw_d;
ot_s81sl_rly #(.W(526),.D(4)) dn(.clk(clk),
 .d({cw_v[4+:2],cw_a[48+:24],cw_d[128+:64],cv[2],cd,swv[2],swa[20+:10],swm[16+:8],swd[512+:256]}),
 .q({cw2_v,cw2_a,cw2_d,c_v,c_d,sw_v,sw_a,sw_m,sw_d}));
ot_s81sl_rly #(.W(257),.D(4)) up_lo(.clk(clk),.d({lo_v,lo_d}),.q({lov,lod}));
wire s_v;wire[159:0]s_d;wire x_rv,x_qv,x_wv;wire[9:0]x_ra,x_wa;wire[7:0]x_wm;wire[255:0]x_qd,x_wd;
wire u_v,um_v,um_q,um_b;wire[2:0]u_i;wire[255:0]u;wire[7:0]um_i;
wire swv_,swvi,swfi;wire[255:0]swd_;wire[31:0]sww,swl;wire[63:0]swri;
wire rav,ravi,rafi,rfv,rff;wire[31:0]rax,rari,rfu,rfu2,rfmx;
wire mv,mq,mb;wire[7:0]mi;
    ot_s81sl_vp u_p (.clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(cw2_v), .cw_a(cw2_a), .cw_d(cw2_d), .lo_v(lo_v), .lo_d(lo_d),
        .s_v(s_v), .s_d(s_d), .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .hw_v(), .hw_j(), .hw_hf(), .hw_d(), .hr_v(), .hr_j(), .hr_hf(), .hq_v(1'b0), .hq_d(256'd0),
        .n_go(), .n_pre(), .m_v(mv), .m_q(mq), .m_b(mb), .m_i(mi), .wl_v(), .wl_i(), .wl_d(), .fault(fp));
    ot_s81sl_vs #(.MUT(0)) u_s (.clk(clk), .rst_n(rst_n), .s_v(s_v), .s_d(s_d),
        .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .u_v(u_v), .u_i(u_i), .u(u), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .sw_v(swv_), .sw_d(swd_), .sw_w(sww), .sw_lim(swl), .sw_vi(swvi), .sw_ri(swri), .sw_fi(swfi),
        .ra_v(rav), .ra_x(rax), .ra_vi(ravi), .ra_ri(rari), .ra_fi(rafi),
        .ve_rv(),.ve_rc(),.ve_rh(),.ve_rk(),.ve_rw(),.ve_pv(1'b0),.ve_pc(2'd0),.ve_phh(32'd0),.ve_pkk(32'd0),.ve_pdd(32'd0),
        .ve_av(),.ve_ac(),.ve_ah(),.ve_aval(),.ve_ag(),.ve_ov(1'b0),.ve_oc(2'd0),.ve_oy(256'd0),.ve_fi(1'b0),
        .e_v(),.e_c(),.e_d(),.g_v(1'b0),.g_c(2'd0),.g_d(32'd0),.fault(fs));
    ot_s81sl_vsw u_w (.clk(clk), .rst_n(rst_n), .i_v(swv_), .i_d(swd_), .i_w(sww), .i_lim(swl), .o_v(swvi), .o_d(swri), .o_f(swfi));
    dsfd_su_t_rxsf u_rf (.ck(clk), .rst(rst_n), .i_v(rav), .i_x(rax), .o_v(rfv), .o_u(rfu), .o_u2(rfu2), .o_mx(rfmx), .o_f(rff));
    dsfd_su_t_rxsb u_rb (.ck(clk), .rst(rst_n), .i_v(rfv), .i_u(rfu), .i_u2(rfu2), .i_mx(rfmx), .i_f(rff), .o_v(ravi), .o_r(rari), .o_f(rafi));

wire xf_v,xf_s;wire[275:0]xf;wire xfv,xfs;wire[275:0]xfd;
ot_s81sl_vq #(.AQ_XMEM(2)) vq(.clk(clk),.rst_n(rst_n),.y_v(1'b0),.y_i(3'd0),.y(256'd0),
 .u_v(u_v),.u_i(u_i),.u(u),.sid(4'd6),.k(3'd2),.m_v(mv),.m_q(mq),.m_b(mb),.m_i(mi),
 .um_v(um_v),.um_q(um_q),.um_b(um_b),.um_i(um_i),.xf_v(xf_v),.xf_s(xf_s),.xf(xf),.fault(fq));
ot_s81sl_rly #(.W(278),.D(4)) up_x(.clk(clk),.d({xf_v,xf_s,xf}),.q({xfv,xfs,xfd}));
wire[1100:0]actual_source_word;wire[2:0]gv,gfam;wire[20:0]gi;wire[3071:0]gd;
ot_s81sl_rstop ring(.clk(clk),.rst_n(rst_n),.sid(4'd6),.ri_w(1104'd0),.ri_e(1104'd0),
 .ro_e(),.ro_w(),.vi(276'd0),.vo(),.xf_v({2'd0,xfv,2'd0}),.xf_s({2'd0,xfs,2'd0}),
 .xf({552'd0,xfd,552'd0}),.nx_wi(),.nx_ei(),.nx_eo(173'd0),.nx_wo(173'd0),
 .dl_ev(),.dl_e(),.dl_wv(),.dl_w(),.dl_vv(),.dl_vb(),.ci_dir(3'd0),.ci_b(1104'd0),
 .g_v(gv),.g_fam(gfam),.g_idx(gi),.g_d(gd),.fault(fr));
ot_s81sl_xs xs(.clk(clk),.rst_n(rst_n),.g_v(gv),.g_fam(gfam),.g_idx(gi),.g_d(gd),
 .is_v(is_v),.is_d(is_d),.xw_v(),.xw_d(actual_source_word),.fault(fxs));
integer current_epoch=-1,gos=0,ends=0,gws=0,writes=0,lastcommit=-1;
integer reads[0:14];reg[31:0]expected_reads[0:14];
function automatic[255:0] qword(input integer blk);
 qword=gold[blk/2]>>(266*(blk%2));
endfunction
function automatic[9:0] qexp(input integer blk);
 qexp=gold[blk/2]>>(256+266*(blk%2));
endfunction
reg prevg0=0,prevg1=0;reg[255:0]prevd0,prevd1;reg[9:0]preve0,preve1;
integer bi0,bi1;reg curg0,curg1;
initial begin
 for(integer e=0;e<15;e++)reads[e]=0;
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"NO_DIR");
 rc=$value$plusargs("MUT=%d",mut);
 for(integer j=0;j<12001;j++)ctl[j]=0;
 $readmemh({dir,"/expected_xq.mem"},gold);
 $readmemh({dir,"/expected_reads.mem"},expected_reads);
 fd=$fopen({dir,"/source_ctl.txt"},"r");if(!fd)$fatal(1,"NO_CTL");
 rc=$fscanf(fd,"%d %h\n",at,payload);
 while(rc==2)begin ctl[at+16]=payload;ctlv[at+16]=1;rc=$fscanf(fd,"%d %h\n",at,payload);end
end
always @(negedge clk)begin
 if(n==8)rst_n=1;
 ev=0;eb=0;
 if(mut==6 && n==ORIGIN+1300)rst_n=0;
 if(mut==6 && n==ORIGIN+1310)rst_n=1;
 if(n+1>=ORIGIN-16 && n+1<=ORIGIN+11984 && ctlv[n+1-ORIGIN+16])begin
  ev=1;eb[0]=1;eb[21+:186]=ctl[n+1-ORIGIN+16];
  if(mut==1 && n+1==ORIGIN+128)eb[91]=~eb[91]; // actual raw-state bit corruption
  if(mut==2 && n+1==ORIGIN+128)ev=0; // actual missing row write
  if(mut==3 && n+1==ORIGIN+128)eb[21+:16]=16'h0080; // foreign destination
 end
 if(mut==4 && n+1==ORIGIN+1800)begin
  ev=1;eb[0]=1;eb[21+:186]=(186'(1)<<6)|(186'(2)<<16)|(186'(1)<<146);
 end
end
always @(posedge clk)begin
 n=n+1;
 if(xs.o_go)begin current_epoch=xs.o_ph;gos++;$display("ACTUAL_GO t=%0d epoch=%0d",n-ORIGIN,current_epoch);end
 if(xs.cal_action[72])begin ends++;$display("ACTUAL_END t=%0d epoch=%0d valid=%h",n-ORIGIN,current_epoch,xs.tq_v[0]);end
 if(xs.o_gw)begin gws++;$display("ACTUAL_GW t=%0d fam=%b parity=%b",n-ORIGIN,xs.o_gw_fam,xs.o_gw_par);end
 curg0=xs.r1_qg[0];curg1=xs.r1_qg[1];bi0=xs.r1_ei0;bi1=xs.r1_ei1;
 if(curg0||curg1)begin
  if(current_epoch<0||current_epoch>14)err++;else reads[current_epoch]++;
  $display("ACTUAL_QREAD t=%0d epoch=%0d gates=%b blocks=%0d,%0d parity=%b source=%0d,%0d valid=%b%b",n-ORIGIN,current_epoch,xs.r1_qg,bi0,bi1,xs.r1_qpar,xs.q_s0,xs.q_s1,xs.q_v0,xs.q_v1);
  if(xs.r1_qpar||xs.wpar_q)err++;
  if(curg0 && (!xs.q_v0||xs.q_s0!=0||bi0>=40||xs.ex[bi0]!==qexp(bi0)))err++;
  if(curg1 && (!xs.q_v1||xs.q_s1!=0||bi1>=40||xs.ex[bi1]!==qexp(bi1)))err++;
 end
 if(n>=ORIGIN && n<ORIGIN+11900)begin
  if((u_p.wv[0]||u_p.wv[1]) && n<ORIGIN+1300)begin nw++;$display("RAW_WRITE t=%0d banks=%b",n-ORIGIN,u_p.wv);end
  if(c_v)$display("VP_CMD_PIN t=%0d",n-ORIGIN);
 end
 #1;
 if(prevg0 && (xs.hq0!==prevd0||xs.he0!==preve0))begin err++;$display("RETAINED_QOUTPUT_MISMATCH half0 t=%0d",n-ORIGIN);end
 if(prevg1 && (xs.hq1!==prevd1||xs.he1!==preve1))begin err++;$display("RETAINED_QOUTPUT_MISMATCH half1 t=%0d",n-ORIGIN);end
 prevg0=curg0;prevg1=curg1;
 if(curg0)begin prevd0=qword(bi0);preve0=qexp(bi0);end
 if(curg1)begin prevd1=qword(bi1);preve1=qexp(bi1);end
 if(n>=ORIGIN && n<ORIGIN+11900)begin
  if(u_v)$display("RAW_SUBBEAT t=%0d i=%0d",n-ORIGIN,u_i);
  if(um_v)$display("MODE t=%0d idx=%0d",n-ORIGIN,um_i);
  if(xf_v)$display("XQ_FRAGMENT t=%0d first=%b",n-ORIGIN,xf_s);
  if(gv[0])begin
   $display("QNORM_GATHER t=%0d order=%0d idx=%0d data=%0133h",n-ORIGIN,nq,gi[6:0],gd[531:0]);
   if(nq>=20 || gi[6:0]!=nq || gfam[0] || gd[531:0]!==gold[nq])begin err++;$display("QNORM_SOURCE_MISMATCH");end
   if(nq<20 && n-ORIGIN!=384+46*nq)begin err++;$display("QNORM_SOURCE_AGE_MISMATCH model=%0d actual=%0d",384+46*nq,n-ORIGIN);end
   nq++;
  end
 end
 if(n==ORIGIN+11900)begin
  if(nw!=320||nq!=20||fx||fp||fs||fq||fr||fxs)begin err++;$display("QNORM_SOURCE_COUNTS writes%0d gather%0d faults%b%b%b%b%b%b",nw,nq,fx,fp,fs,fq,fr,fxs);end
  if(xs.tq_v[0][19:0]!==20'hfffff)begin err++;$display("QNORM_SOURCE_MISSING_XS_JOIN");end
  for(integer e=0;e<15;e++)begin
   $display("EPOCH_READ_COUNTS epoch=%0d actual=%0d expected=%0d",e,reads[e],expected_reads[e]);
   if(reads[e]!=expected_reads[e])err++;
  end
  if(gos!=15||ends!=15||gws!=1||writes!=40||lastcommit!=1260||xs.wpar_q!=0)begin
   err++;$display("RETAINED_CONTROL_MISMATCH gos%0d ends%0d gws%0d macwrites%0d lastcommit%0d",gos,ends,gws,writes,lastcommit);
  end
  $display("FULLSIX_SOURCE_CHECK errors=%0d rawwrites=%0d gathers=%0d epochs=%0d",err,nw,nq,gos);
  $display("FULLSIX_PREPARATORY_TRACE_END CAPfault=%b landfaults=%b otherVPfaults=%b no_numeric_PASS nativephase_NULL",cap_fault,return_landing_fault,other_vp_fault);
  if(err)$fatal(1,"FULLSIX_RAW_SOURCE_FAIL errors=%0d",err);
  $finish;
 end
end

generate for(genvar m=0;m<8;m++)begin:mon_macro
 integer beat,half,addr,blk;reg wr,rd;reg[255:0]wd,rdgold;
 always @(posedge clk)begin
  wr=xs.mw_e[0][m];rd=xs.mr_e[m];addr=xs.mw_a[0][m];beat=xs.gi[0];half=(m>>1)&1;
  if(wr)begin
   writes++;lastcommit=($time/834)-ORIGIN;
   wd=gold[beat]>>(266*half);
   $display("XS_MACRO_COMMIT t=%0d macro=%0d beat=%0d row=%0d",n-ORIGIN,m,beat,addr);
   if(beat>=20||addr!=40+2*(beat/8)+((beat>>1)&1)||xs.mw_m[0][m]!=={256{1'b1}}||xs.mw_d[0][m]!==wd)err++;
  end
  if(rd)begin
   blk=(xs.r1_qg[0] && xs.r1_qm0==m)?xs.r1_ei0:xs.r1_ei1;rdgold=qword(blk);
   if(xs.mr_a[m]!=xs.r1_qrow)err++;
  end
  #1;
  if(wr && xs.g_bank[0].g_mac[m].u_mem.word_read(addr)!==wd)err++;
  if(rd && xs.mrd[0][m]!==rdgold)begin err++;$display("XS_MACRO_READ_MISMATCH macro=%0d t=%0d block=%0d",m,n-ORIGIN,blk);end
 end
end endgenerate

// First trace retains the actual CAP reset state. No host-selected tag/rbase.
// CFG and drain faults are recorded and remain failures; no numeric qualification.
wire[559:0]frame_return,cap_return;wire[3:0]return_landing_fault;
wire cap_fault;wire[4:0]other_vp_fault;
selected_fullsix_cone fullcone(.clk(clk),.rst_n(rst_n),.source_word(actual_source_word),.rt(frame_return),.return_landing_fault(return_landing_fault));
ot_s81sl_rly #(.W(560),.D(6)) dr(.clk(clk),.d(frame_return),.q(cap_return));
ot_s81sl_cap cap(.clk(clk),.rst_n(rst_n),.rt_w(cap_return[279:0]),.rt_e(cap_return[559:280]),
 .cfg_v(cap_cfg_v),.cfg_d(cap_cfg_d),.cw_s_v(cw_v[5:0]),.cw_s_a(cw_a[71:0]),.cw_s_d(cw_d[191:0]),
 .cw_n_v(cw_v[9:6]),.cw_n_a(cw_a[119:72]),.cw_n_d(cw_d[319:192]),.fault(cap_fault));
assign other_vp_fault[2]=fp;
if (1) begin:leaf0
 wire cvk,swvk;wire[159:0]cdk;wire[9:0]swak;wire[7:0]swmk;wire[255:0]swdk;
 wire[1:0]cwvk;wire[23:0]cwak;wire[63:0]cwdk;
 ot_s81sl_rly #(.W(526),.D(4)) dl(.clk(clk),
 .d({cw_v[0+:2],cw_a[0+:24],cw_d[0+:64],cv[0],cd,swv[0],swa[0+:10],swm[0+:8],swd[0+:256]}),
 .q({cwvk,cwak,cwdk,cvk,cdk,swvk,swak,swmk,swdk}));
 ot_s81sl_vp u_p(.clk(clk),.rst_n(rst_n),.c_v(cvk),.c_d(cdk),.sw_v(swvk),.sw_a(swak),.sw_m(swmk),.sw_d(swdk),
 .cw_v(cwvk),.cw_a(cwak),.cw_d(cwdk),.lo_v(),.lo_d(),.s_v(),.s_d(),.x_rv(1'b0),.x_ra(10'd0),.x_qv(),.x_qd(),
 .x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),.hw_v(),.hw_j(),.hw_hf(),.hw_d(),.hr_v(),.hr_j(),.hr_hf(),
 .hq_v(1'b0),.hq_d(256'd0),.n_go(),.n_pre(),.m_v(),.m_q(),.m_b(),.m_i(),.wl_v(),.wl_i(),.wl_d(),.fault(other_vp_fault[0]));
 end
always @(posedge clk)if(rst_n && (leaf0.u_p.cwv_c!=0||leaf0.u_p.cv_c||leaf0.u_p.re_e||leaf0.u_p.re_o||leaf0.u_p.fault))
 $display("VP_DRAIN t=%0d leaf=0 cw=%b cwa=%h cmd=%b srun=%b reads=%b%b raddr=%0d,%0d fault=%b",($time/834)-ORIGIN,leaf0.u_p.cwv_c,leaf0.u_p.cwa_c,leaf0.u_p.cv_c,leaf0.u_p.srun,leaf0.u_p.re_o,leaf0.u_p.re_e,leaf0.u_p.ra_e,leaf0.u_p.ra_o,leaf0.u_p.fault);
always @(posedge clk)if(rst_n && leaf0.u_p.wv[0])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=0 bank=0 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf0.u_p.wa[0],leaf0.u_p.wm[0],leaf0.u_p.wd[0],leaf0.u_p.cwv_c,leaf0.u_p.wcol);
end
always @(posedge clk)if(rst_n && leaf0.u_p.wv[1])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=0 bank=1 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf0.u_p.wa[1],leaf0.u_p.wm[1],leaf0.u_p.wd[1],leaf0.u_p.cwv_c,leaf0.u_p.wcol);
end
if (1) begin:leaf1
 wire cvk,swvk;wire[159:0]cdk;wire[9:0]swak;wire[7:0]swmk;wire[255:0]swdk;
 wire[1:0]cwvk;wire[23:0]cwak;wire[63:0]cwdk;
 ot_s81sl_rly #(.W(526),.D(4)) dl(.clk(clk),
 .d({cw_v[2+:2],cw_a[24+:24],cw_d[64+:64],cv[1],cd,swv[1],swa[10+:10],swm[8+:8],swd[256+:256]}),
 .q({cwvk,cwak,cwdk,cvk,cdk,swvk,swak,swmk,swdk}));
 ot_s81sl_vp u_p(.clk(clk),.rst_n(rst_n),.c_v(cvk),.c_d(cdk),.sw_v(swvk),.sw_a(swak),.sw_m(swmk),.sw_d(swdk),
 .cw_v(cwvk),.cw_a(cwak),.cw_d(cwdk),.lo_v(),.lo_d(),.s_v(),.s_d(),.x_rv(1'b0),.x_ra(10'd0),.x_qv(),.x_qd(),
 .x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),.hw_v(),.hw_j(),.hw_hf(),.hw_d(),.hr_v(),.hr_j(),.hr_hf(),
 .hq_v(1'b0),.hq_d(256'd0),.n_go(),.n_pre(),.m_v(),.m_q(),.m_b(),.m_i(),.wl_v(),.wl_i(),.wl_d(),.fault(other_vp_fault[1]));
 end
always @(posedge clk)if(rst_n && (leaf1.u_p.cwv_c!=0||leaf1.u_p.cv_c||leaf1.u_p.re_e||leaf1.u_p.re_o||leaf1.u_p.fault))
 $display("VP_DRAIN t=%0d leaf=1 cw=%b cwa=%h cmd=%b srun=%b reads=%b%b raddr=%0d,%0d fault=%b",($time/834)-ORIGIN,leaf1.u_p.cwv_c,leaf1.u_p.cwa_c,leaf1.u_p.cv_c,leaf1.u_p.srun,leaf1.u_p.re_o,leaf1.u_p.re_e,leaf1.u_p.ra_e,leaf1.u_p.ra_o,leaf1.u_p.fault);
always @(posedge clk)if(rst_n && leaf1.u_p.wv[0])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=1 bank=0 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf1.u_p.wa[0],leaf1.u_p.wm[0],leaf1.u_p.wd[0],leaf1.u_p.cwv_c,leaf1.u_p.wcol);
end
always @(posedge clk)if(rst_n && leaf1.u_p.wv[1])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=1 bank=1 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf1.u_p.wa[1],leaf1.u_p.wm[1],leaf1.u_p.wd[1],leaf1.u_p.cwv_c,leaf1.u_p.wcol);
end
always @(posedge clk)if(rst_n && (u_p.cwv_c!=0||u_p.cv_c||u_p.re_e||u_p.re_o||u_p.fault))
 $display("VP_DRAIN t=%0d leaf=2 cw=%b cwa=%h cmd=%b srun=%b reads=%b%b raddr=%0d,%0d fault=%b",($time/834)-ORIGIN,u_p.cwv_c,u_p.cwa_c,u_p.cv_c,u_p.srun,u_p.re_o,u_p.re_e,u_p.ra_e,u_p.ra_o,u_p.fault);
always @(posedge clk)if(rst_n && u_p.wv[0])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=2 bank=0 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,u_p.wa[0],u_p.wm[0],u_p.wd[0],u_p.cwv_c,u_p.wcol);
end
always @(posedge clk)if(rst_n && u_p.wv[1])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=2 bank=1 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,u_p.wa[1],u_p.wm[1],u_p.wd[1],u_p.cwv_c,u_p.wcol);
end
if (1) begin:leaf3
 wire cvk,swvk;wire[159:0]cdk;wire[9:0]swak;wire[7:0]swmk;wire[255:0]swdk;
 wire[1:0]cwvk;wire[23:0]cwak;wire[63:0]cwdk;
 ot_s81sl_rly #(.W(526),.D(4)) dl(.clk(clk),
 .d({cw_v[6+:2],cw_a[72+:24],cw_d[192+:64],cv[3],cd,swv[3],swa[30+:10],swm[24+:8],swd[768+:256]}),
 .q({cwvk,cwak,cwdk,cvk,cdk,swvk,swak,swmk,swdk}));
 ot_s81sl_vp u_p(.clk(clk),.rst_n(rst_n),.c_v(cvk),.c_d(cdk),.sw_v(swvk),.sw_a(swak),.sw_m(swmk),.sw_d(swdk),
 .cw_v(cwvk),.cw_a(cwak),.cw_d(cwdk),.lo_v(),.lo_d(),.s_v(),.s_d(),.x_rv(1'b0),.x_ra(10'd0),.x_qv(),.x_qd(),
 .x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),.hw_v(),.hw_j(),.hw_hf(),.hw_d(),.hr_v(),.hr_j(),.hr_hf(),
 .hq_v(1'b0),.hq_d(256'd0),.n_go(),.n_pre(),.m_v(),.m_q(),.m_b(),.m_i(),.wl_v(),.wl_i(),.wl_d(),.fault(other_vp_fault[3]));
 end
always @(posedge clk)if(rst_n && (leaf3.u_p.cwv_c!=0||leaf3.u_p.cv_c||leaf3.u_p.re_e||leaf3.u_p.re_o||leaf3.u_p.fault))
 $display("VP_DRAIN t=%0d leaf=3 cw=%b cwa=%h cmd=%b srun=%b reads=%b%b raddr=%0d,%0d fault=%b",($time/834)-ORIGIN,leaf3.u_p.cwv_c,leaf3.u_p.cwa_c,leaf3.u_p.cv_c,leaf3.u_p.srun,leaf3.u_p.re_o,leaf3.u_p.re_e,leaf3.u_p.ra_e,leaf3.u_p.ra_o,leaf3.u_p.fault);
always @(posedge clk)if(rst_n && leaf3.u_p.wv[0])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=3 bank=0 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf3.u_p.wa[0],leaf3.u_p.wm[0],leaf3.u_p.wd[0],leaf3.u_p.cwv_c,leaf3.u_p.wcol);
end
always @(posedge clk)if(rst_n && leaf3.u_p.wv[1])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=3 bank=1 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf3.u_p.wa[1],leaf3.u_p.wm[1],leaf3.u_p.wd[1],leaf3.u_p.cwv_c,leaf3.u_p.wcol);
end
if (1) begin:leaf4
 wire cvk,swvk;wire[159:0]cdk;wire[9:0]swak;wire[7:0]swmk;wire[255:0]swdk;
 wire[1:0]cwvk;wire[23:0]cwak;wire[63:0]cwdk;
 ot_s81sl_rly #(.W(526),.D(4)) dl(.clk(clk),
 .d({cw_v[8+:2],cw_a[96+:24],cw_d[256+:64],cv[4],cd,swv[4],swa[40+:10],swm[32+:8],swd[1024+:256]}),
 .q({cwvk,cwak,cwdk,cvk,cdk,swvk,swak,swmk,swdk}));
 ot_s81sl_vp u_p(.clk(clk),.rst_n(rst_n),.c_v(cvk),.c_d(cdk),.sw_v(swvk),.sw_a(swak),.sw_m(swmk),.sw_d(swdk),
 .cw_v(cwvk),.cw_a(cwak),.cw_d(cwdk),.lo_v(),.lo_d(),.s_v(),.s_d(),.x_rv(1'b0),.x_ra(10'd0),.x_qv(),.x_qd(),
 .x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),.hw_v(),.hw_j(),.hw_hf(),.hw_d(),.hr_v(),.hr_j(),.hr_hf(),
 .hq_v(1'b0),.hq_d(256'd0),.n_go(),.n_pre(),.m_v(),.m_q(),.m_b(),.m_i(),.wl_v(),.wl_i(),.wl_d(),.fault(other_vp_fault[4]));
 end
always @(posedge clk)if(rst_n && (leaf4.u_p.cwv_c!=0||leaf4.u_p.cv_c||leaf4.u_p.re_e||leaf4.u_p.re_o||leaf4.u_p.fault))
 $display("VP_DRAIN t=%0d leaf=4 cw=%b cwa=%h cmd=%b srun=%b reads=%b%b raddr=%0d,%0d fault=%b",($time/834)-ORIGIN,leaf4.u_p.cwv_c,leaf4.u_p.cwa_c,leaf4.u_p.cv_c,leaf4.u_p.srun,leaf4.u_p.re_o,leaf4.u_p.re_e,leaf4.u_p.ra_e,leaf4.u_p.ra_o,leaf4.u_p.fault);
always @(posedge clk)if(rst_n && leaf4.u_p.wv[0])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=4 bank=0 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf4.u_p.wa[0],leaf4.u_p.wm[0],leaf4.u_p.wd[0],leaf4.u_p.cwv_c,leaf4.u_p.wcol);
end
always @(posedge clk)if(rst_n && leaf4.u_p.wv[1])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf=4 bank=1 row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,leaf4.u_p.wa[1],leaf4.u_p.wm[1],leaf4.u_p.wd[1],leaf4.u_p.cwv_c,leaf4.u_p.wcol);
end
reg[31:0]cap_prev=0;
always @(posedge clk)begin
 if(rst_n)begin
  if(cap_cfg_v)$display("ACTUAL_CAP_CFG t=%0d body=%h",($time/834)-ORIGIN,cap_cfg_d);
  for(integer l=0;l<6;l++)begin
   if(frame_return[70*l+1])$display("FRAME_RETURN t=%0d lane=%0d word=%h",($time/834)-ORIGIN,l,frame_return[70*l+:70]);
   if(cap_return[70*l+1])$display("CAP_ARR t=%0d lane=%0d word=%h",($time/834)-ORIGIN,l,cap_return[70*l+:70]);
  end
  if(cap.g_hard.u_rt.fa_v||cap.g_hard.u_rt.fb_v||cap.g_hard.u_rt.any_open||cap_prev!={cap.g_hard.u_rt.fcause,cap.g_hard.u_rt.any_open,15'd0})begin
   $display("CAP_LIFETIME t=%0d fa=%b/%h fb=%b/%h open=%b f5=%b f6=%b f7=%b f8=%b f9=%b f11=%b causes=%h rbase=%h rcnt=%0d",($time/834)-ORIGIN,
   cap.g_hard.u_rt.fa_v,cap.g_hard.u_rt.fa_t,cap.g_hard.u_rt.fb_v,cap.g_hard.u_rt.fb_t,cap.g_hard.u_rt.any_open,
   cap.g_hard.u_rt.f5,cap.g_hard.u_rt.f6,cap.g_hard.u_rt.f7,cap.g_hard.u_rt.f8,cap.g_hard.u_rt.f9,cap.g_hard.u_rt.f11,cap.g_hard.u_rt.fcause,cap.g_hard.u_rt.c_rbase,cap.g_hard.u_rt.c_rcnt);
  end
  cap_prev={cap.g_hard.u_rt.fcause,cap.g_hard.u_rt.any_open,15'd0};
  if(|cw_v)$display("ACTUAL_CW t=%0d valid=%h addr=%h data=%h",($time/834)-ORIGIN,cw_v,cw_a,cw_d);
 end
end
if (1) begin:observe_u_f_3L01_q0
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e0.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e0.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e0.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s0.lc[0]||fullcone.u_f_3L01.u_s0.go_x||fullcone.u_f_3L01.u_s0.go_e||fullcone.u_f_3L01.u_s0.cfg[0]||fullcone.u_f_3L01.u_s0.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q0 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s0.lc,fullcone.u_f_3L01.u_s0.go_x,fullcone.u_f_3L01.u_s0.tag,fullcone.u_f_3L01.u_s0.go_e,fullcone.u_f_3L01.u_s0.go_tag,fullcone.u_f_3L01.u_s0.ef,fullcone.u_f_3L01.u_s0.st);
   if(fullcone.u_f_3L01.u_e0.go||oldgo||fullcone.u_f_3L01.u_e0.cfg_v||prevstate!={fullcone.u_f_3L01.u_e0.bank_free,fullcone.u_f_3L01.u_e0.sh_free,fullcone.u_f_3L01.u_e0.u_e.walk_busy,fullcone.u_f_3L01.u_e0.u_e.u_pq.walking,fullcone.u_f_3L01.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e0.u_e.u_pq.settle,fullcone.u_f_3L01.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e0.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q0 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e0.go,fullcone.u_f_3L01.u_e0.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e0.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e0.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e0.bank_free,fullcone.u_f_3L01.u_e0.sh_free,fullcone.u_f_3L01.u_e0.u_e.walk_busy,fullcone.u_f_3L01.u_e0.u_e.u_pq.walking,fullcone.u_f_3L01.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e0.u_e.u_pq.settle,fullcone.u_f_3L01.u_e0.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e0.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e0.cfg_v,fullcone.u_f_3L01.u_e0.cfg_a,fullcone.u_f_3L01.u_e0.cfg_d,fullcone.u_f_3L01.u_e0.u_e.u_pq.swap,fullcone.u_f_3L01.u_e0.fault);
   prevstate={fullcone.u_f_3L01.u_e0.bank_free,fullcone.u_f_3L01.u_e0.sh_free,fullcone.u_f_3L01.u_e0.u_e.walk_busy,fullcone.u_f_3L01.u_e0.u_e.u_pq.walking,fullcone.u_f_3L01.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e0.u_e.u_pq.settle,fullcone.u_f_3L01.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e0.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e0.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q0 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e0.pv,fullcone.u_f_3L01.u_e0.prow,fullcone.u_f_3L01.u_e0.pval,fullcone.u_f_3L01.u_e0.pseg,fullcone.u_f_3L01.u_e0.pnseg,fullcone.u_f_3L01.u_e0.perr,fullcone.u_f_3L01.u_e0.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q0 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e0.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q2
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e2.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e2.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e2.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s2.lc[0]||fullcone.u_f_3L01.u_s2.go_x||fullcone.u_f_3L01.u_s2.go_e||fullcone.u_f_3L01.u_s2.cfg[0]||fullcone.u_f_3L01.u_s2.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q2 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s2.lc,fullcone.u_f_3L01.u_s2.go_x,fullcone.u_f_3L01.u_s2.tag,fullcone.u_f_3L01.u_s2.go_e,fullcone.u_f_3L01.u_s2.go_tag,fullcone.u_f_3L01.u_s2.ef,fullcone.u_f_3L01.u_s2.st);
   if(fullcone.u_f_3L01.u_e2.go||oldgo||fullcone.u_f_3L01.u_e2.cfg_v||prevstate!={fullcone.u_f_3L01.u_e2.bank_free,fullcone.u_f_3L01.u_e2.sh_free,fullcone.u_f_3L01.u_e2.u_e.walk_busy,fullcone.u_f_3L01.u_e2.u_e.u_pq.walking,fullcone.u_f_3L01.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e2.u_e.u_pq.settle,fullcone.u_f_3L01.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e2.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q2 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e2.go,fullcone.u_f_3L01.u_e2.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e2.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e2.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e2.bank_free,fullcone.u_f_3L01.u_e2.sh_free,fullcone.u_f_3L01.u_e2.u_e.walk_busy,fullcone.u_f_3L01.u_e2.u_e.u_pq.walking,fullcone.u_f_3L01.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e2.u_e.u_pq.settle,fullcone.u_f_3L01.u_e2.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e2.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e2.cfg_v,fullcone.u_f_3L01.u_e2.cfg_a,fullcone.u_f_3L01.u_e2.cfg_d,fullcone.u_f_3L01.u_e2.u_e.u_pq.swap,fullcone.u_f_3L01.u_e2.fault);
   prevstate={fullcone.u_f_3L01.u_e2.bank_free,fullcone.u_f_3L01.u_e2.sh_free,fullcone.u_f_3L01.u_e2.u_e.walk_busy,fullcone.u_f_3L01.u_e2.u_e.u_pq.walking,fullcone.u_f_3L01.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e2.u_e.u_pq.settle,fullcone.u_f_3L01.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e2.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e2.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q2 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e2.pv,fullcone.u_f_3L01.u_e2.prow,fullcone.u_f_3L01.u_e2.pval,fullcone.u_f_3L01.u_e2.pseg,fullcone.u_f_3L01.u_e2.pnseg,fullcone.u_f_3L01.u_e2.perr,fullcone.u_f_3L01.u_e2.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q2 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e2.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q3
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e3.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e3.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e3.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s3.lc[0]||fullcone.u_f_3L01.u_s3.go_x||fullcone.u_f_3L01.u_s3.go_e||fullcone.u_f_3L01.u_s3.cfg[0]||fullcone.u_f_3L01.u_s3.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q3 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s3.lc,fullcone.u_f_3L01.u_s3.go_x,fullcone.u_f_3L01.u_s3.tag,fullcone.u_f_3L01.u_s3.go_e,fullcone.u_f_3L01.u_s3.go_tag,fullcone.u_f_3L01.u_s3.ef,fullcone.u_f_3L01.u_s3.st);
   if(fullcone.u_f_3L01.u_e3.go||oldgo||fullcone.u_f_3L01.u_e3.cfg_v||prevstate!={fullcone.u_f_3L01.u_e3.bank_free,fullcone.u_f_3L01.u_e3.sh_free,fullcone.u_f_3L01.u_e3.u_e.walk_busy,fullcone.u_f_3L01.u_e3.u_e.u_pq.walking,fullcone.u_f_3L01.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e3.u_e.u_pq.settle,fullcone.u_f_3L01.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e3.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q3 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e3.go,fullcone.u_f_3L01.u_e3.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e3.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e3.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e3.bank_free,fullcone.u_f_3L01.u_e3.sh_free,fullcone.u_f_3L01.u_e3.u_e.walk_busy,fullcone.u_f_3L01.u_e3.u_e.u_pq.walking,fullcone.u_f_3L01.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e3.u_e.u_pq.settle,fullcone.u_f_3L01.u_e3.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e3.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e3.cfg_v,fullcone.u_f_3L01.u_e3.cfg_a,fullcone.u_f_3L01.u_e3.cfg_d,fullcone.u_f_3L01.u_e3.u_e.u_pq.swap,fullcone.u_f_3L01.u_e3.fault);
   prevstate={fullcone.u_f_3L01.u_e3.bank_free,fullcone.u_f_3L01.u_e3.sh_free,fullcone.u_f_3L01.u_e3.u_e.walk_busy,fullcone.u_f_3L01.u_e3.u_e.u_pq.walking,fullcone.u_f_3L01.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e3.u_e.u_pq.settle,fullcone.u_f_3L01.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e3.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e3.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q3 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e3.pv,fullcone.u_f_3L01.u_e3.prow,fullcone.u_f_3L01.u_e3.pval,fullcone.u_f_3L01.u_e3.pseg,fullcone.u_f_3L01.u_e3.pnseg,fullcone.u_f_3L01.u_e3.perr,fullcone.u_f_3L01.u_e3.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q3 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e3.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q4
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e4.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e4.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e4.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s4.lc[0]||fullcone.u_f_3L01.u_s4.go_x||fullcone.u_f_3L01.u_s4.go_e||fullcone.u_f_3L01.u_s4.cfg[0]||fullcone.u_f_3L01.u_s4.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q4 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s4.lc,fullcone.u_f_3L01.u_s4.go_x,fullcone.u_f_3L01.u_s4.tag,fullcone.u_f_3L01.u_s4.go_e,fullcone.u_f_3L01.u_s4.go_tag,fullcone.u_f_3L01.u_s4.ef,fullcone.u_f_3L01.u_s4.st);
   if(fullcone.u_f_3L01.u_e4.go||oldgo||fullcone.u_f_3L01.u_e4.cfg_v||prevstate!={fullcone.u_f_3L01.u_e4.bank_free,fullcone.u_f_3L01.u_e4.sh_free,fullcone.u_f_3L01.u_e4.u_e.walk_busy,fullcone.u_f_3L01.u_e4.u_e.u_pq.walking,fullcone.u_f_3L01.u_e4.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e4.u_e.u_pq.settle,fullcone.u_f_3L01.u_e4.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e4.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e4.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e4.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q4 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e4.go,fullcone.u_f_3L01.u_e4.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e4.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e4.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e4.bank_free,fullcone.u_f_3L01.u_e4.sh_free,fullcone.u_f_3L01.u_e4.u_e.walk_busy,fullcone.u_f_3L01.u_e4.u_e.u_pq.walking,fullcone.u_f_3L01.u_e4.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e4.u_e.u_pq.settle,fullcone.u_f_3L01.u_e4.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e4.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e4.cfg_v,fullcone.u_f_3L01.u_e4.cfg_a,fullcone.u_f_3L01.u_e4.cfg_d,fullcone.u_f_3L01.u_e4.u_e.u_pq.swap,fullcone.u_f_3L01.u_e4.fault);
   prevstate={fullcone.u_f_3L01.u_e4.bank_free,fullcone.u_f_3L01.u_e4.sh_free,fullcone.u_f_3L01.u_e4.u_e.walk_busy,fullcone.u_f_3L01.u_e4.u_e.u_pq.walking,fullcone.u_f_3L01.u_e4.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e4.u_e.u_pq.settle,fullcone.u_f_3L01.u_e4.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e4.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e4.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e4.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e4.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q4 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e4.pv,fullcone.u_f_3L01.u_e4.prow,fullcone.u_f_3L01.u_e4.pval,fullcone.u_f_3L01.u_e4.pseg,fullcone.u_f_3L01.u_e4.pnseg,fullcone.u_f_3L01.u_e4.perr,fullcone.u_f_3L01.u_e4.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q4 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e4.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q6
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e6.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e6.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e6.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s6.lc[0]||fullcone.u_f_3L01.u_s6.go_x||fullcone.u_f_3L01.u_s6.go_e||fullcone.u_f_3L01.u_s6.cfg[0]||fullcone.u_f_3L01.u_s6.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q6 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s6.lc,fullcone.u_f_3L01.u_s6.go_x,fullcone.u_f_3L01.u_s6.tag,fullcone.u_f_3L01.u_s6.go_e,fullcone.u_f_3L01.u_s6.go_tag,fullcone.u_f_3L01.u_s6.ef,fullcone.u_f_3L01.u_s6.st);
   if(fullcone.u_f_3L01.u_e6.go||oldgo||fullcone.u_f_3L01.u_e6.cfg_v||prevstate!={fullcone.u_f_3L01.u_e6.bank_free,fullcone.u_f_3L01.u_e6.sh_free,fullcone.u_f_3L01.u_e6.u_e.walk_busy,fullcone.u_f_3L01.u_e6.u_e.u_pq.walking,fullcone.u_f_3L01.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e6.u_e.u_pq.settle,fullcone.u_f_3L01.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e6.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q6 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e6.go,fullcone.u_f_3L01.u_e6.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e6.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e6.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e6.bank_free,fullcone.u_f_3L01.u_e6.sh_free,fullcone.u_f_3L01.u_e6.u_e.walk_busy,fullcone.u_f_3L01.u_e6.u_e.u_pq.walking,fullcone.u_f_3L01.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e6.u_e.u_pq.settle,fullcone.u_f_3L01.u_e6.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e6.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e6.cfg_v,fullcone.u_f_3L01.u_e6.cfg_a,fullcone.u_f_3L01.u_e6.cfg_d,fullcone.u_f_3L01.u_e6.u_e.u_pq.swap,fullcone.u_f_3L01.u_e6.fault);
   prevstate={fullcone.u_f_3L01.u_e6.bank_free,fullcone.u_f_3L01.u_e6.sh_free,fullcone.u_f_3L01.u_e6.u_e.walk_busy,fullcone.u_f_3L01.u_e6.u_e.u_pq.walking,fullcone.u_f_3L01.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e6.u_e.u_pq.settle,fullcone.u_f_3L01.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e6.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e6.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q6 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e6.pv,fullcone.u_f_3L01.u_e6.prow,fullcone.u_f_3L01.u_e6.pval,fullcone.u_f_3L01.u_e6.pseg,fullcone.u_f_3L01.u_e6.pnseg,fullcone.u_f_3L01.u_e6.perr,fullcone.u_f_3L01.u_e6.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q6 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e6.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q7
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e7.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e7.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e7.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s7.lc[0]||fullcone.u_f_3L01.u_s7.go_x||fullcone.u_f_3L01.u_s7.go_e||fullcone.u_f_3L01.u_s7.cfg[0]||fullcone.u_f_3L01.u_s7.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q7 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s7.lc,fullcone.u_f_3L01.u_s7.go_x,fullcone.u_f_3L01.u_s7.tag,fullcone.u_f_3L01.u_s7.go_e,fullcone.u_f_3L01.u_s7.go_tag,fullcone.u_f_3L01.u_s7.ef,fullcone.u_f_3L01.u_s7.st);
   if(fullcone.u_f_3L01.u_e7.go||oldgo||fullcone.u_f_3L01.u_e7.cfg_v||prevstate!={fullcone.u_f_3L01.u_e7.bank_free,fullcone.u_f_3L01.u_e7.sh_free,fullcone.u_f_3L01.u_e7.u_e.walk_busy,fullcone.u_f_3L01.u_e7.u_e.u_pq.walking,fullcone.u_f_3L01.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e7.u_e.u_pq.settle,fullcone.u_f_3L01.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e7.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q7 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e7.go,fullcone.u_f_3L01.u_e7.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e7.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e7.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e7.bank_free,fullcone.u_f_3L01.u_e7.sh_free,fullcone.u_f_3L01.u_e7.u_e.walk_busy,fullcone.u_f_3L01.u_e7.u_e.u_pq.walking,fullcone.u_f_3L01.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e7.u_e.u_pq.settle,fullcone.u_f_3L01.u_e7.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e7.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e7.cfg_v,fullcone.u_f_3L01.u_e7.cfg_a,fullcone.u_f_3L01.u_e7.cfg_d,fullcone.u_f_3L01.u_e7.u_e.u_pq.swap,fullcone.u_f_3L01.u_e7.fault);
   prevstate={fullcone.u_f_3L01.u_e7.bank_free,fullcone.u_f_3L01.u_e7.sh_free,fullcone.u_f_3L01.u_e7.u_e.walk_busy,fullcone.u_f_3L01.u_e7.u_e.u_pq.walking,fullcone.u_f_3L01.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e7.u_e.u_pq.settle,fullcone.u_f_3L01.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e7.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e7.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q7 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e7.pv,fullcone.u_f_3L01.u_e7.prow,fullcone.u_f_3L01.u_e7.pval,fullcone.u_f_3L01.u_e7.pseg,fullcone.u_f_3L01.u_e7.pnseg,fullcone.u_f_3L01.u_e7.perr,fullcone.u_f_3L01.u_e7.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q7 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e7.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q8
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e8.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e8.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e8.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s8.lc[0]||fullcone.u_f_3L01.u_s8.go_x||fullcone.u_f_3L01.u_s8.go_e||fullcone.u_f_3L01.u_s8.cfg[0]||fullcone.u_f_3L01.u_s8.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q8 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s8.lc,fullcone.u_f_3L01.u_s8.go_x,fullcone.u_f_3L01.u_s8.tag,fullcone.u_f_3L01.u_s8.go_e,fullcone.u_f_3L01.u_s8.go_tag,fullcone.u_f_3L01.u_s8.ef,fullcone.u_f_3L01.u_s8.st);
   if(fullcone.u_f_3L01.u_e8.go||oldgo||fullcone.u_f_3L01.u_e8.cfg_v||prevstate!={fullcone.u_f_3L01.u_e8.bank_free,fullcone.u_f_3L01.u_e8.sh_free,fullcone.u_f_3L01.u_e8.u_e.walk_busy,fullcone.u_f_3L01.u_e8.u_e.u_pq.walking,fullcone.u_f_3L01.u_e8.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e8.u_e.u_pq.settle,fullcone.u_f_3L01.u_e8.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e8.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e8.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e8.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q8 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e8.go,fullcone.u_f_3L01.u_e8.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e8.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e8.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e8.bank_free,fullcone.u_f_3L01.u_e8.sh_free,fullcone.u_f_3L01.u_e8.u_e.walk_busy,fullcone.u_f_3L01.u_e8.u_e.u_pq.walking,fullcone.u_f_3L01.u_e8.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e8.u_e.u_pq.settle,fullcone.u_f_3L01.u_e8.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e8.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e8.cfg_v,fullcone.u_f_3L01.u_e8.cfg_a,fullcone.u_f_3L01.u_e8.cfg_d,fullcone.u_f_3L01.u_e8.u_e.u_pq.swap,fullcone.u_f_3L01.u_e8.fault);
   prevstate={fullcone.u_f_3L01.u_e8.bank_free,fullcone.u_f_3L01.u_e8.sh_free,fullcone.u_f_3L01.u_e8.u_e.walk_busy,fullcone.u_f_3L01.u_e8.u_e.u_pq.walking,fullcone.u_f_3L01.u_e8.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e8.u_e.u_pq.settle,fullcone.u_f_3L01.u_e8.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e8.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e8.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e8.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e8.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q8 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e8.pv,fullcone.u_f_3L01.u_e8.prow,fullcone.u_f_3L01.u_e8.pval,fullcone.u_f_3L01.u_e8.pseg,fullcone.u_f_3L01.u_e8.pnseg,fullcone.u_f_3L01.u_e8.perr,fullcone.u_f_3L01.u_e8.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q8 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e8.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q9
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e9.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e9.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e9.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s9.lc[0]||fullcone.u_f_3L01.u_s9.go_x||fullcone.u_f_3L01.u_s9.go_e||fullcone.u_f_3L01.u_s9.cfg[0]||fullcone.u_f_3L01.u_s9.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q9 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s9.lc,fullcone.u_f_3L01.u_s9.go_x,fullcone.u_f_3L01.u_s9.tag,fullcone.u_f_3L01.u_s9.go_e,fullcone.u_f_3L01.u_s9.go_tag,fullcone.u_f_3L01.u_s9.ef,fullcone.u_f_3L01.u_s9.st);
   if(fullcone.u_f_3L01.u_e9.go||oldgo||fullcone.u_f_3L01.u_e9.cfg_v||prevstate!={fullcone.u_f_3L01.u_e9.bank_free,fullcone.u_f_3L01.u_e9.sh_free,fullcone.u_f_3L01.u_e9.u_e.walk_busy,fullcone.u_f_3L01.u_e9.u_e.u_pq.walking,fullcone.u_f_3L01.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e9.u_e.u_pq.settle,fullcone.u_f_3L01.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e9.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q9 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e9.go,fullcone.u_f_3L01.u_e9.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e9.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e9.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e9.bank_free,fullcone.u_f_3L01.u_e9.sh_free,fullcone.u_f_3L01.u_e9.u_e.walk_busy,fullcone.u_f_3L01.u_e9.u_e.u_pq.walking,fullcone.u_f_3L01.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e9.u_e.u_pq.settle,fullcone.u_f_3L01.u_e9.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e9.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e9.cfg_v,fullcone.u_f_3L01.u_e9.cfg_a,fullcone.u_f_3L01.u_e9.cfg_d,fullcone.u_f_3L01.u_e9.u_e.u_pq.swap,fullcone.u_f_3L01.u_e9.fault);
   prevstate={fullcone.u_f_3L01.u_e9.bank_free,fullcone.u_f_3L01.u_e9.sh_free,fullcone.u_f_3L01.u_e9.u_e.walk_busy,fullcone.u_f_3L01.u_e9.u_e.u_pq.walking,fullcone.u_f_3L01.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e9.u_e.u_pq.settle,fullcone.u_f_3L01.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e9.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e9.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q9 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e9.pv,fullcone.u_f_3L01.u_e9.prow,fullcone.u_f_3L01.u_e9.pval,fullcone.u_f_3L01.u_e9.pseg,fullcone.u_f_3L01.u_e9.pnseg,fullcone.u_f_3L01.u_e9.perr,fullcone.u_f_3L01.u_e9.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q9 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e9.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q11
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e11.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e11.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e11.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s11.lc[0]||fullcone.u_f_3L01.u_s11.go_x||fullcone.u_f_3L01.u_s11.go_e||fullcone.u_f_3L01.u_s11.cfg[0]||fullcone.u_f_3L01.u_s11.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q11 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s11.lc,fullcone.u_f_3L01.u_s11.go_x,fullcone.u_f_3L01.u_s11.tag,fullcone.u_f_3L01.u_s11.go_e,fullcone.u_f_3L01.u_s11.go_tag,fullcone.u_f_3L01.u_s11.ef,fullcone.u_f_3L01.u_s11.st);
   if(fullcone.u_f_3L01.u_e11.go||oldgo||fullcone.u_f_3L01.u_e11.cfg_v||prevstate!={fullcone.u_f_3L01.u_e11.bank_free,fullcone.u_f_3L01.u_e11.sh_free,fullcone.u_f_3L01.u_e11.u_e.walk_busy,fullcone.u_f_3L01.u_e11.u_e.u_pq.walking,fullcone.u_f_3L01.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e11.u_e.u_pq.settle,fullcone.u_f_3L01.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e11.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q11 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e11.go,fullcone.u_f_3L01.u_e11.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e11.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e11.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e11.bank_free,fullcone.u_f_3L01.u_e11.sh_free,fullcone.u_f_3L01.u_e11.u_e.walk_busy,fullcone.u_f_3L01.u_e11.u_e.u_pq.walking,fullcone.u_f_3L01.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e11.u_e.u_pq.settle,fullcone.u_f_3L01.u_e11.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e11.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e11.cfg_v,fullcone.u_f_3L01.u_e11.cfg_a,fullcone.u_f_3L01.u_e11.cfg_d,fullcone.u_f_3L01.u_e11.u_e.u_pq.swap,fullcone.u_f_3L01.u_e11.fault);
   prevstate={fullcone.u_f_3L01.u_e11.bank_free,fullcone.u_f_3L01.u_e11.sh_free,fullcone.u_f_3L01.u_e11.u_e.walk_busy,fullcone.u_f_3L01.u_e11.u_e.u_pq.walking,fullcone.u_f_3L01.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e11.u_e.u_pq.settle,fullcone.u_f_3L01.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e11.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e11.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q11 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e11.pv,fullcone.u_f_3L01.u_e11.prow,fullcone.u_f_3L01.u_e11.pval,fullcone.u_f_3L01.u_e11.pseg,fullcone.u_f_3L01.u_e11.pnseg,fullcone.u_f_3L01.u_e11.perr,fullcone.u_f_3L01.u_e11.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q11 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e11.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q12
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e12.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e12.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e12.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s12.lc[0]||fullcone.u_f_3L01.u_s12.go_x||fullcone.u_f_3L01.u_s12.go_e||fullcone.u_f_3L01.u_s12.cfg[0]||fullcone.u_f_3L01.u_s12.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q12 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s12.lc,fullcone.u_f_3L01.u_s12.go_x,fullcone.u_f_3L01.u_s12.tag,fullcone.u_f_3L01.u_s12.go_e,fullcone.u_f_3L01.u_s12.go_tag,fullcone.u_f_3L01.u_s12.ef,fullcone.u_f_3L01.u_s12.st);
   if(fullcone.u_f_3L01.u_e12.go||oldgo||fullcone.u_f_3L01.u_e12.cfg_v||prevstate!={fullcone.u_f_3L01.u_e12.bank_free,fullcone.u_f_3L01.u_e12.sh_free,fullcone.u_f_3L01.u_e12.u_e.walk_busy,fullcone.u_f_3L01.u_e12.u_e.u_pq.walking,fullcone.u_f_3L01.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e12.u_e.u_pq.settle,fullcone.u_f_3L01.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e12.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q12 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e12.go,fullcone.u_f_3L01.u_e12.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e12.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e12.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e12.bank_free,fullcone.u_f_3L01.u_e12.sh_free,fullcone.u_f_3L01.u_e12.u_e.walk_busy,fullcone.u_f_3L01.u_e12.u_e.u_pq.walking,fullcone.u_f_3L01.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e12.u_e.u_pq.settle,fullcone.u_f_3L01.u_e12.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e12.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e12.cfg_v,fullcone.u_f_3L01.u_e12.cfg_a,fullcone.u_f_3L01.u_e12.cfg_d,fullcone.u_f_3L01.u_e12.u_e.u_pq.swap,fullcone.u_f_3L01.u_e12.fault);
   prevstate={fullcone.u_f_3L01.u_e12.bank_free,fullcone.u_f_3L01.u_e12.sh_free,fullcone.u_f_3L01.u_e12.u_e.walk_busy,fullcone.u_f_3L01.u_e12.u_e.u_pq.walking,fullcone.u_f_3L01.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e12.u_e.u_pq.settle,fullcone.u_f_3L01.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e12.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e12.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q12 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e12.pv,fullcone.u_f_3L01.u_e12.prow,fullcone.u_f_3L01.u_e12.pval,fullcone.u_f_3L01.u_e12.pseg,fullcone.u_f_3L01.u_e12.pnseg,fullcone.u_f_3L01.u_e12.perr,fullcone.u_f_3L01.u_e12.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q12 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e12.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q13
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e13.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e13.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e13.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s13.lc[0]||fullcone.u_f_3L01.u_s13.go_x||fullcone.u_f_3L01.u_s13.go_e||fullcone.u_f_3L01.u_s13.cfg[0]||fullcone.u_f_3L01.u_s13.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q13 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s13.lc,fullcone.u_f_3L01.u_s13.go_x,fullcone.u_f_3L01.u_s13.tag,fullcone.u_f_3L01.u_s13.go_e,fullcone.u_f_3L01.u_s13.go_tag,fullcone.u_f_3L01.u_s13.ef,fullcone.u_f_3L01.u_s13.st);
   if(fullcone.u_f_3L01.u_e13.go||oldgo||fullcone.u_f_3L01.u_e13.cfg_v||prevstate!={fullcone.u_f_3L01.u_e13.bank_free,fullcone.u_f_3L01.u_e13.sh_free,fullcone.u_f_3L01.u_e13.u_e.walk_busy,fullcone.u_f_3L01.u_e13.u_e.u_pq.walking,fullcone.u_f_3L01.u_e13.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e13.u_e.u_pq.settle,fullcone.u_f_3L01.u_e13.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e13.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e13.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e13.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q13 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e13.go,fullcone.u_f_3L01.u_e13.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e13.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e13.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e13.bank_free,fullcone.u_f_3L01.u_e13.sh_free,fullcone.u_f_3L01.u_e13.u_e.walk_busy,fullcone.u_f_3L01.u_e13.u_e.u_pq.walking,fullcone.u_f_3L01.u_e13.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e13.u_e.u_pq.settle,fullcone.u_f_3L01.u_e13.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e13.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e13.cfg_v,fullcone.u_f_3L01.u_e13.cfg_a,fullcone.u_f_3L01.u_e13.cfg_d,fullcone.u_f_3L01.u_e13.u_e.u_pq.swap,fullcone.u_f_3L01.u_e13.fault);
   prevstate={fullcone.u_f_3L01.u_e13.bank_free,fullcone.u_f_3L01.u_e13.sh_free,fullcone.u_f_3L01.u_e13.u_e.walk_busy,fullcone.u_f_3L01.u_e13.u_e.u_pq.walking,fullcone.u_f_3L01.u_e13.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e13.u_e.u_pq.settle,fullcone.u_f_3L01.u_e13.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e13.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e13.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e13.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e13.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q13 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e13.pv,fullcone.u_f_3L01.u_e13.prow,fullcone.u_f_3L01.u_e13.pval,fullcone.u_f_3L01.u_e13.pseg,fullcone.u_f_3L01.u_e13.pnseg,fullcone.u_f_3L01.u_e13.perr,fullcone.u_f_3L01.u_e13.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q13 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e13.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L01_q14
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L01.u_e14.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L01.u_e14.u_e.go_e;oldtag=fullcone.u_f_3L01.u_e14.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L01.u_s14.lc[0]||fullcone.u_f_3L01.u_s14.go_x||fullcone.u_f_3L01.u_s14.go_e||fullcone.u_f_3L01.u_s14.cfg[0]||fullcone.u_f_3L01.u_s14.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L01_q14 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L01.u_s14.lc,fullcone.u_f_3L01.u_s14.go_x,fullcone.u_f_3L01.u_s14.tag,fullcone.u_f_3L01.u_s14.go_e,fullcone.u_f_3L01.u_s14.go_tag,fullcone.u_f_3L01.u_s14.ef,fullcone.u_f_3L01.u_s14.st);
   if(fullcone.u_f_3L01.u_e14.go||oldgo||fullcone.u_f_3L01.u_e14.cfg_v||prevstate!={fullcone.u_f_3L01.u_e14.bank_free,fullcone.u_f_3L01.u_e14.sh_free,fullcone.u_f_3L01.u_e14.u_e.walk_busy,fullcone.u_f_3L01.u_e14.u_e.u_pq.walking,fullcone.u_f_3L01.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e14.u_e.u_pq.settle,fullcone.u_f_3L01.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e14.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L01_q14 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L01.u_e14.go,fullcone.u_f_3L01.u_e14.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L01.u_e14.u_e.u_pq.otag[0],fullcone.u_f_3L01.u_e14.u_e.u_pq.otag[1],fullcone.u_f_3L01.u_e14.bank_free,fullcone.u_f_3L01.u_e14.sh_free,fullcone.u_f_3L01.u_e14.u_e.walk_busy,fullcone.u_f_3L01.u_e14.u_e.u_pq.walking,fullcone.u_f_3L01.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e14.u_e.u_pq.settle,fullcone.u_f_3L01.u_e14.u_e.u_pq.gcnt[0],fullcone.u_f_3L01.u_e14.u_e.u_pq.gcnt[1],fullcone.u_f_3L01.u_e14.cfg_v,fullcone.u_f_3L01.u_e14.cfg_a,fullcone.u_f_3L01.u_e14.cfg_d,fullcone.u_f_3L01.u_e14.u_e.u_pq.swap,fullcone.u_f_3L01.u_e14.fault);
   prevstate={fullcone.u_f_3L01.u_e14.bank_free,fullcone.u_f_3L01.u_e14.sh_free,fullcone.u_f_3L01.u_e14.u_e.walk_busy,fullcone.u_f_3L01.u_e14.u_e.u_pq.walking,fullcone.u_f_3L01.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L01.u_e14.u_e.u_pq.settle,fullcone.u_f_3L01.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3L01.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L01.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L01.u_e14.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L01.u_e14.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L01_q14 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L01.u_e14.pv,fullcone.u_f_3L01.u_e14.prow,fullcone.u_f_3L01.u_e14.pval,fullcone.u_f_3L01.u_e14.pseg,fullcone.u_f_3L01.u_e14.pnseg,fullcone.u_f_3L01.u_e14.perr,fullcone.u_f_3L01.u_e14.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L01_q14 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L01.u_e14.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q0
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e0.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e0.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s0.lc[0]||fullcone.u_f_3L02.u_f.u_s0.go_x||fullcone.u_f_3L02.u_f.u_s0.go_e||fullcone.u_f_3L02.u_f.u_s0.cfg[0]||fullcone.u_f_3L02.u_f.u_s0.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q0 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s0.lc,fullcone.u_f_3L02.u_f.u_s0.go_x,fullcone.u_f_3L02.u_f.u_s0.tag,fullcone.u_f_3L02.u_f.u_s0.go_e,fullcone.u_f_3L02.u_f.u_s0.go_tag,fullcone.u_f_3L02.u_f.u_s0.ef,fullcone.u_f_3L02.u_f.u_s0.st);
   if(fullcone.u_f_3L02.u_f.u_e0.go||oldgo||fullcone.u_f_3L02.u_f.u_e0.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e0.bank_free,fullcone.u_f_3L02.u_f.u_e0.sh_free,fullcone.u_f_3L02.u_f.u_e0.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q0 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e0.go,fullcone.u_f_3L02.u_f.u_e0.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e0.bank_free,fullcone.u_f_3L02.u_f.u_e0.sh_free,fullcone.u_f_3L02.u_f.u_e0.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e0.cfg_v,fullcone.u_f_3L02.u_f.u_e0.cfg_a,fullcone.u_f_3L02.u_f.u_e0.cfg_d,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e0.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e0.bank_free,fullcone.u_f_3L02.u_f.u_e0.sh_free,fullcone.u_f_3L02.u_f.u_e0.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e0.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q0 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e0.pv,fullcone.u_f_3L02.u_f.u_e0.prow,fullcone.u_f_3L02.u_f.u_e0.pval,fullcone.u_f_3L02.u_f.u_e0.pseg,fullcone.u_f_3L02.u_f.u_e0.pnseg,fullcone.u_f_3L02.u_f.u_e0.perr,fullcone.u_f_3L02.u_f.u_e0.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q0 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e0.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q1
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e1.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e1.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s1.lc[0]||fullcone.u_f_3L02.u_f.u_s1.go_x||fullcone.u_f_3L02.u_f.u_s1.go_e||fullcone.u_f_3L02.u_f.u_s1.cfg[0]||fullcone.u_f_3L02.u_f.u_s1.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q1 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s1.lc,fullcone.u_f_3L02.u_f.u_s1.go_x,fullcone.u_f_3L02.u_f.u_s1.tag,fullcone.u_f_3L02.u_f.u_s1.go_e,fullcone.u_f_3L02.u_f.u_s1.go_tag,fullcone.u_f_3L02.u_f.u_s1.ef,fullcone.u_f_3L02.u_f.u_s1.st);
   if(fullcone.u_f_3L02.u_f.u_e1.go||oldgo||fullcone.u_f_3L02.u_f.u_e1.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e1.bank_free,fullcone.u_f_3L02.u_f.u_e1.sh_free,fullcone.u_f_3L02.u_f.u_e1.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q1 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e1.go,fullcone.u_f_3L02.u_f.u_e1.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e1.bank_free,fullcone.u_f_3L02.u_f.u_e1.sh_free,fullcone.u_f_3L02.u_f.u_e1.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e1.cfg_v,fullcone.u_f_3L02.u_f.u_e1.cfg_a,fullcone.u_f_3L02.u_f.u_e1.cfg_d,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e1.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e1.bank_free,fullcone.u_f_3L02.u_f.u_e1.sh_free,fullcone.u_f_3L02.u_f.u_e1.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e1.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q1 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e1.pv,fullcone.u_f_3L02.u_f.u_e1.prow,fullcone.u_f_3L02.u_f.u_e1.pval,fullcone.u_f_3L02.u_f.u_e1.pseg,fullcone.u_f_3L02.u_f.u_e1.pnseg,fullcone.u_f_3L02.u_f.u_e1.perr,fullcone.u_f_3L02.u_f.u_e1.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q1 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e1.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q2
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e2.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e2.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s2.lc[0]||fullcone.u_f_3L02.u_f.u_s2.go_x||fullcone.u_f_3L02.u_f.u_s2.go_e||fullcone.u_f_3L02.u_f.u_s2.cfg[0]||fullcone.u_f_3L02.u_f.u_s2.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q2 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s2.lc,fullcone.u_f_3L02.u_f.u_s2.go_x,fullcone.u_f_3L02.u_f.u_s2.tag,fullcone.u_f_3L02.u_f.u_s2.go_e,fullcone.u_f_3L02.u_f.u_s2.go_tag,fullcone.u_f_3L02.u_f.u_s2.ef,fullcone.u_f_3L02.u_f.u_s2.st);
   if(fullcone.u_f_3L02.u_f.u_e2.go||oldgo||fullcone.u_f_3L02.u_f.u_e2.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e2.bank_free,fullcone.u_f_3L02.u_f.u_e2.sh_free,fullcone.u_f_3L02.u_f.u_e2.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q2 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e2.go,fullcone.u_f_3L02.u_f.u_e2.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e2.bank_free,fullcone.u_f_3L02.u_f.u_e2.sh_free,fullcone.u_f_3L02.u_f.u_e2.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e2.cfg_v,fullcone.u_f_3L02.u_f.u_e2.cfg_a,fullcone.u_f_3L02.u_f.u_e2.cfg_d,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e2.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e2.bank_free,fullcone.u_f_3L02.u_f.u_e2.sh_free,fullcone.u_f_3L02.u_f.u_e2.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e2.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q2 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e2.pv,fullcone.u_f_3L02.u_f.u_e2.prow,fullcone.u_f_3L02.u_f.u_e2.pval,fullcone.u_f_3L02.u_f.u_e2.pseg,fullcone.u_f_3L02.u_f.u_e2.pnseg,fullcone.u_f_3L02.u_f.u_e2.perr,fullcone.u_f_3L02.u_f.u_e2.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q2 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e2.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q3
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e3.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e3.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s3.lc[0]||fullcone.u_f_3L02.u_f.u_s3.go_x||fullcone.u_f_3L02.u_f.u_s3.go_e||fullcone.u_f_3L02.u_f.u_s3.cfg[0]||fullcone.u_f_3L02.u_f.u_s3.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q3 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s3.lc,fullcone.u_f_3L02.u_f.u_s3.go_x,fullcone.u_f_3L02.u_f.u_s3.tag,fullcone.u_f_3L02.u_f.u_s3.go_e,fullcone.u_f_3L02.u_f.u_s3.go_tag,fullcone.u_f_3L02.u_f.u_s3.ef,fullcone.u_f_3L02.u_f.u_s3.st);
   if(fullcone.u_f_3L02.u_f.u_e3.go||oldgo||fullcone.u_f_3L02.u_f.u_e3.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e3.bank_free,fullcone.u_f_3L02.u_f.u_e3.sh_free,fullcone.u_f_3L02.u_f.u_e3.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q3 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e3.go,fullcone.u_f_3L02.u_f.u_e3.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e3.bank_free,fullcone.u_f_3L02.u_f.u_e3.sh_free,fullcone.u_f_3L02.u_f.u_e3.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e3.cfg_v,fullcone.u_f_3L02.u_f.u_e3.cfg_a,fullcone.u_f_3L02.u_f.u_e3.cfg_d,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e3.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e3.bank_free,fullcone.u_f_3L02.u_f.u_e3.sh_free,fullcone.u_f_3L02.u_f.u_e3.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e3.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q3 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e3.pv,fullcone.u_f_3L02.u_f.u_e3.prow,fullcone.u_f_3L02.u_f.u_e3.pval,fullcone.u_f_3L02.u_f.u_e3.pseg,fullcone.u_f_3L02.u_f.u_e3.pnseg,fullcone.u_f_3L02.u_f.u_e3.perr,fullcone.u_f_3L02.u_f.u_e3.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q3 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e3.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q5
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e5.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e5.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s5.lc[0]||fullcone.u_f_3L02.u_f.u_s5.go_x||fullcone.u_f_3L02.u_f.u_s5.go_e||fullcone.u_f_3L02.u_f.u_s5.cfg[0]||fullcone.u_f_3L02.u_f.u_s5.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q5 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s5.lc,fullcone.u_f_3L02.u_f.u_s5.go_x,fullcone.u_f_3L02.u_f.u_s5.tag,fullcone.u_f_3L02.u_f.u_s5.go_e,fullcone.u_f_3L02.u_f.u_s5.go_tag,fullcone.u_f_3L02.u_f.u_s5.ef,fullcone.u_f_3L02.u_f.u_s5.st);
   if(fullcone.u_f_3L02.u_f.u_e5.go||oldgo||fullcone.u_f_3L02.u_f.u_e5.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e5.bank_free,fullcone.u_f_3L02.u_f.u_e5.sh_free,fullcone.u_f_3L02.u_f.u_e5.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q5 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e5.go,fullcone.u_f_3L02.u_f.u_e5.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e5.bank_free,fullcone.u_f_3L02.u_f.u_e5.sh_free,fullcone.u_f_3L02.u_f.u_e5.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e5.cfg_v,fullcone.u_f_3L02.u_f.u_e5.cfg_a,fullcone.u_f_3L02.u_f.u_e5.cfg_d,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e5.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e5.bank_free,fullcone.u_f_3L02.u_f.u_e5.sh_free,fullcone.u_f_3L02.u_f.u_e5.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e5.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q5 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e5.pv,fullcone.u_f_3L02.u_f.u_e5.prow,fullcone.u_f_3L02.u_f.u_e5.pval,fullcone.u_f_3L02.u_f.u_e5.pseg,fullcone.u_f_3L02.u_f.u_e5.pnseg,fullcone.u_f_3L02.u_f.u_e5.perr,fullcone.u_f_3L02.u_f.u_e5.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q5 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e5.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q6
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e6.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e6.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s6.lc[0]||fullcone.u_f_3L02.u_f.u_s6.go_x||fullcone.u_f_3L02.u_f.u_s6.go_e||fullcone.u_f_3L02.u_f.u_s6.cfg[0]||fullcone.u_f_3L02.u_f.u_s6.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q6 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s6.lc,fullcone.u_f_3L02.u_f.u_s6.go_x,fullcone.u_f_3L02.u_f.u_s6.tag,fullcone.u_f_3L02.u_f.u_s6.go_e,fullcone.u_f_3L02.u_f.u_s6.go_tag,fullcone.u_f_3L02.u_f.u_s6.ef,fullcone.u_f_3L02.u_f.u_s6.st);
   if(fullcone.u_f_3L02.u_f.u_e6.go||oldgo||fullcone.u_f_3L02.u_f.u_e6.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e6.bank_free,fullcone.u_f_3L02.u_f.u_e6.sh_free,fullcone.u_f_3L02.u_f.u_e6.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q6 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e6.go,fullcone.u_f_3L02.u_f.u_e6.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e6.bank_free,fullcone.u_f_3L02.u_f.u_e6.sh_free,fullcone.u_f_3L02.u_f.u_e6.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e6.cfg_v,fullcone.u_f_3L02.u_f.u_e6.cfg_a,fullcone.u_f_3L02.u_f.u_e6.cfg_d,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e6.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e6.bank_free,fullcone.u_f_3L02.u_f.u_e6.sh_free,fullcone.u_f_3L02.u_f.u_e6.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e6.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q6 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e6.pv,fullcone.u_f_3L02.u_f.u_e6.prow,fullcone.u_f_3L02.u_f.u_e6.pval,fullcone.u_f_3L02.u_f.u_e6.pseg,fullcone.u_f_3L02.u_f.u_e6.pnseg,fullcone.u_f_3L02.u_f.u_e6.perr,fullcone.u_f_3L02.u_f.u_e6.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q6 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e6.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q7
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e7.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e7.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s7.lc[0]||fullcone.u_f_3L02.u_f.u_s7.go_x||fullcone.u_f_3L02.u_f.u_s7.go_e||fullcone.u_f_3L02.u_f.u_s7.cfg[0]||fullcone.u_f_3L02.u_f.u_s7.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q7 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s7.lc,fullcone.u_f_3L02.u_f.u_s7.go_x,fullcone.u_f_3L02.u_f.u_s7.tag,fullcone.u_f_3L02.u_f.u_s7.go_e,fullcone.u_f_3L02.u_f.u_s7.go_tag,fullcone.u_f_3L02.u_f.u_s7.ef,fullcone.u_f_3L02.u_f.u_s7.st);
   if(fullcone.u_f_3L02.u_f.u_e7.go||oldgo||fullcone.u_f_3L02.u_f.u_e7.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e7.bank_free,fullcone.u_f_3L02.u_f.u_e7.sh_free,fullcone.u_f_3L02.u_f.u_e7.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q7 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e7.go,fullcone.u_f_3L02.u_f.u_e7.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e7.bank_free,fullcone.u_f_3L02.u_f.u_e7.sh_free,fullcone.u_f_3L02.u_f.u_e7.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e7.cfg_v,fullcone.u_f_3L02.u_f.u_e7.cfg_a,fullcone.u_f_3L02.u_f.u_e7.cfg_d,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e7.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e7.bank_free,fullcone.u_f_3L02.u_f.u_e7.sh_free,fullcone.u_f_3L02.u_f.u_e7.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e7.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q7 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e7.pv,fullcone.u_f_3L02.u_f.u_e7.prow,fullcone.u_f_3L02.u_f.u_e7.pval,fullcone.u_f_3L02.u_f.u_e7.pseg,fullcone.u_f_3L02.u_f.u_e7.pnseg,fullcone.u_f_3L02.u_f.u_e7.perr,fullcone.u_f_3L02.u_f.u_e7.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q7 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e7.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q9
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e9.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e9.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s9.lc[0]||fullcone.u_f_3L02.u_f.u_s9.go_x||fullcone.u_f_3L02.u_f.u_s9.go_e||fullcone.u_f_3L02.u_f.u_s9.cfg[0]||fullcone.u_f_3L02.u_f.u_s9.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q9 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s9.lc,fullcone.u_f_3L02.u_f.u_s9.go_x,fullcone.u_f_3L02.u_f.u_s9.tag,fullcone.u_f_3L02.u_f.u_s9.go_e,fullcone.u_f_3L02.u_f.u_s9.go_tag,fullcone.u_f_3L02.u_f.u_s9.ef,fullcone.u_f_3L02.u_f.u_s9.st);
   if(fullcone.u_f_3L02.u_f.u_e9.go||oldgo||fullcone.u_f_3L02.u_f.u_e9.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e9.bank_free,fullcone.u_f_3L02.u_f.u_e9.sh_free,fullcone.u_f_3L02.u_f.u_e9.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q9 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e9.go,fullcone.u_f_3L02.u_f.u_e9.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e9.bank_free,fullcone.u_f_3L02.u_f.u_e9.sh_free,fullcone.u_f_3L02.u_f.u_e9.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e9.cfg_v,fullcone.u_f_3L02.u_f.u_e9.cfg_a,fullcone.u_f_3L02.u_f.u_e9.cfg_d,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e9.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e9.bank_free,fullcone.u_f_3L02.u_f.u_e9.sh_free,fullcone.u_f_3L02.u_f.u_e9.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e9.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q9 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e9.pv,fullcone.u_f_3L02.u_f.u_e9.prow,fullcone.u_f_3L02.u_f.u_e9.pval,fullcone.u_f_3L02.u_f.u_e9.pseg,fullcone.u_f_3L02.u_f.u_e9.pnseg,fullcone.u_f_3L02.u_f.u_e9.perr,fullcone.u_f_3L02.u_f.u_e9.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q9 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e9.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q10
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e10.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e10.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s10.lc[0]||fullcone.u_f_3L02.u_f.u_s10.go_x||fullcone.u_f_3L02.u_f.u_s10.go_e||fullcone.u_f_3L02.u_f.u_s10.cfg[0]||fullcone.u_f_3L02.u_f.u_s10.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q10 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s10.lc,fullcone.u_f_3L02.u_f.u_s10.go_x,fullcone.u_f_3L02.u_f.u_s10.tag,fullcone.u_f_3L02.u_f.u_s10.go_e,fullcone.u_f_3L02.u_f.u_s10.go_tag,fullcone.u_f_3L02.u_f.u_s10.ef,fullcone.u_f_3L02.u_f.u_s10.st);
   if(fullcone.u_f_3L02.u_f.u_e10.go||oldgo||fullcone.u_f_3L02.u_f.u_e10.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e10.bank_free,fullcone.u_f_3L02.u_f.u_e10.sh_free,fullcone.u_f_3L02.u_f.u_e10.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q10 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e10.go,fullcone.u_f_3L02.u_f.u_e10.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e10.bank_free,fullcone.u_f_3L02.u_f.u_e10.sh_free,fullcone.u_f_3L02.u_f.u_e10.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e10.cfg_v,fullcone.u_f_3L02.u_f.u_e10.cfg_a,fullcone.u_f_3L02.u_f.u_e10.cfg_d,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e10.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e10.bank_free,fullcone.u_f_3L02.u_f.u_e10.sh_free,fullcone.u_f_3L02.u_f.u_e10.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e10.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q10 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e10.pv,fullcone.u_f_3L02.u_f.u_e10.prow,fullcone.u_f_3L02.u_f.u_e10.pval,fullcone.u_f_3L02.u_f.u_e10.pseg,fullcone.u_f_3L02.u_f.u_e10.pnseg,fullcone.u_f_3L02.u_f.u_e10.perr,fullcone.u_f_3L02.u_f.u_e10.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q10 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e10.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q11
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e11.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e11.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s11.lc[0]||fullcone.u_f_3L02.u_f.u_s11.go_x||fullcone.u_f_3L02.u_f.u_s11.go_e||fullcone.u_f_3L02.u_f.u_s11.cfg[0]||fullcone.u_f_3L02.u_f.u_s11.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q11 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s11.lc,fullcone.u_f_3L02.u_f.u_s11.go_x,fullcone.u_f_3L02.u_f.u_s11.tag,fullcone.u_f_3L02.u_f.u_s11.go_e,fullcone.u_f_3L02.u_f.u_s11.go_tag,fullcone.u_f_3L02.u_f.u_s11.ef,fullcone.u_f_3L02.u_f.u_s11.st);
   if(fullcone.u_f_3L02.u_f.u_e11.go||oldgo||fullcone.u_f_3L02.u_f.u_e11.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e11.bank_free,fullcone.u_f_3L02.u_f.u_e11.sh_free,fullcone.u_f_3L02.u_f.u_e11.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q11 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e11.go,fullcone.u_f_3L02.u_f.u_e11.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e11.bank_free,fullcone.u_f_3L02.u_f.u_e11.sh_free,fullcone.u_f_3L02.u_f.u_e11.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e11.cfg_v,fullcone.u_f_3L02.u_f.u_e11.cfg_a,fullcone.u_f_3L02.u_f.u_e11.cfg_d,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e11.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e11.bank_free,fullcone.u_f_3L02.u_f.u_e11.sh_free,fullcone.u_f_3L02.u_f.u_e11.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e11.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q11 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e11.pv,fullcone.u_f_3L02.u_f.u_e11.prow,fullcone.u_f_3L02.u_f.u_e11.pval,fullcone.u_f_3L02.u_f.u_e11.pseg,fullcone.u_f_3L02.u_f.u_e11.pnseg,fullcone.u_f_3L02.u_f.u_e11.perr,fullcone.u_f_3L02.u_f.u_e11.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q11 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e11.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q12
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e12.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e12.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s12.lc[0]||fullcone.u_f_3L02.u_f.u_s12.go_x||fullcone.u_f_3L02.u_f.u_s12.go_e||fullcone.u_f_3L02.u_f.u_s12.cfg[0]||fullcone.u_f_3L02.u_f.u_s12.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q12 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s12.lc,fullcone.u_f_3L02.u_f.u_s12.go_x,fullcone.u_f_3L02.u_f.u_s12.tag,fullcone.u_f_3L02.u_f.u_s12.go_e,fullcone.u_f_3L02.u_f.u_s12.go_tag,fullcone.u_f_3L02.u_f.u_s12.ef,fullcone.u_f_3L02.u_f.u_s12.st);
   if(fullcone.u_f_3L02.u_f.u_e12.go||oldgo||fullcone.u_f_3L02.u_f.u_e12.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e12.bank_free,fullcone.u_f_3L02.u_f.u_e12.sh_free,fullcone.u_f_3L02.u_f.u_e12.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q12 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e12.go,fullcone.u_f_3L02.u_f.u_e12.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e12.bank_free,fullcone.u_f_3L02.u_f.u_e12.sh_free,fullcone.u_f_3L02.u_f.u_e12.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e12.cfg_v,fullcone.u_f_3L02.u_f.u_e12.cfg_a,fullcone.u_f_3L02.u_f.u_e12.cfg_d,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e12.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e12.bank_free,fullcone.u_f_3L02.u_f.u_e12.sh_free,fullcone.u_f_3L02.u_f.u_e12.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e12.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q12 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e12.pv,fullcone.u_f_3L02.u_f.u_e12.prow,fullcone.u_f_3L02.u_f.u_e12.pval,fullcone.u_f_3L02.u_f.u_e12.pseg,fullcone.u_f_3L02.u_f.u_e12.pnseg,fullcone.u_f_3L02.u_f.u_e12.perr,fullcone.u_f_3L02.u_f.u_e12.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q12 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e12.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L02_q14
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L02.u_f.u_e14.u_e.go_e;oldtag=fullcone.u_f_3L02.u_f.u_e14.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L02.u_f.u_s14.lc[0]||fullcone.u_f_3L02.u_f.u_s14.go_x||fullcone.u_f_3L02.u_f.u_s14.go_e||fullcone.u_f_3L02.u_f.u_s14.cfg[0]||fullcone.u_f_3L02.u_f.u_s14.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L02_q14 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_s14.lc,fullcone.u_f_3L02.u_f.u_s14.go_x,fullcone.u_f_3L02.u_f.u_s14.tag,fullcone.u_f_3L02.u_f.u_s14.go_e,fullcone.u_f_3L02.u_f.u_s14.go_tag,fullcone.u_f_3L02.u_f.u_s14.ef,fullcone.u_f_3L02.u_f.u_s14.st);
   if(fullcone.u_f_3L02.u_f.u_e14.go||oldgo||fullcone.u_f_3L02.u_f.u_e14.cfg_v||prevstate!={fullcone.u_f_3L02.u_f.u_e14.bank_free,fullcone.u_f_3L02.u_f.u_e14.sh_free,fullcone.u_f_3L02.u_f.u_e14.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L02_q14 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L02.u_f.u_e14.go,fullcone.u_f_3L02.u_f.u_e14.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.otag[0],fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.otag[1],fullcone.u_f_3L02.u_f.u_e14.bank_free,fullcone.u_f_3L02.u_f.u_e14.sh_free,fullcone.u_f_3L02.u_f.u_e14.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.gcnt[0],fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.gcnt[1],fullcone.u_f_3L02.u_f.u_e14.cfg_v,fullcone.u_f_3L02.u_f.u_e14.cfg_a,fullcone.u_f_3L02.u_f.u_e14.cfg_d,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.swap,fullcone.u_f_3L02.u_f.u_e14.fault);
   prevstate={fullcone.u_f_3L02.u_f.u_e14.bank_free,fullcone.u_f_3L02.u_f.u_e14.sh_free,fullcone.u_f_3L02.u_f.u_e14.u_e.walk_busy,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.walking,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.settle,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L02.u_f.u_e14.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L02_q14 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L02.u_f.u_e14.pv,fullcone.u_f_3L02.u_f.u_e14.prow,fullcone.u_f_3L02.u_f.u_e14.pval,fullcone.u_f_3L02.u_f.u_e14.pseg,fullcone.u_f_3L02.u_f.u_e14.pnseg,fullcone.u_f_3L02.u_f.u_e14.perr,fullcone.u_f_3L02.u_f.u_e14.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L02_q14 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L02.u_f.u_e14.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q0
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e0.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e0.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e0.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s0.lc[0]||fullcone.u_f_3L03.u_s0.go_x||fullcone.u_f_3L03.u_s0.go_e||fullcone.u_f_3L03.u_s0.cfg[0]||fullcone.u_f_3L03.u_s0.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q0 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s0.lc,fullcone.u_f_3L03.u_s0.go_x,fullcone.u_f_3L03.u_s0.tag,fullcone.u_f_3L03.u_s0.go_e,fullcone.u_f_3L03.u_s0.go_tag,fullcone.u_f_3L03.u_s0.ef,fullcone.u_f_3L03.u_s0.st);
   if(fullcone.u_f_3L03.u_e0.go||oldgo||fullcone.u_f_3L03.u_e0.cfg_v||prevstate!={fullcone.u_f_3L03.u_e0.bank_free,fullcone.u_f_3L03.u_e0.sh_free,fullcone.u_f_3L03.u_e0.u_e.walk_busy,fullcone.u_f_3L03.u_e0.u_e.u_pq.walking,fullcone.u_f_3L03.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e0.u_e.u_pq.settle,fullcone.u_f_3L03.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e0.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q0 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e0.go,fullcone.u_f_3L03.u_e0.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e0.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e0.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e0.bank_free,fullcone.u_f_3L03.u_e0.sh_free,fullcone.u_f_3L03.u_e0.u_e.walk_busy,fullcone.u_f_3L03.u_e0.u_e.u_pq.walking,fullcone.u_f_3L03.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e0.u_e.u_pq.settle,fullcone.u_f_3L03.u_e0.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e0.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e0.cfg_v,fullcone.u_f_3L03.u_e0.cfg_a,fullcone.u_f_3L03.u_e0.cfg_d,fullcone.u_f_3L03.u_e0.u_e.u_pq.swap,fullcone.u_f_3L03.u_e0.fault);
   prevstate={fullcone.u_f_3L03.u_e0.bank_free,fullcone.u_f_3L03.u_e0.sh_free,fullcone.u_f_3L03.u_e0.u_e.walk_busy,fullcone.u_f_3L03.u_e0.u_e.u_pq.walking,fullcone.u_f_3L03.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e0.u_e.u_pq.settle,fullcone.u_f_3L03.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e0.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e0.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q0 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e0.pv,fullcone.u_f_3L03.u_e0.prow,fullcone.u_f_3L03.u_e0.pval,fullcone.u_f_3L03.u_e0.pseg,fullcone.u_f_3L03.u_e0.pnseg,fullcone.u_f_3L03.u_e0.perr,fullcone.u_f_3L03.u_e0.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q0 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e0.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q1
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e1.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e1.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e1.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s1.lc[0]||fullcone.u_f_3L03.u_s1.go_x||fullcone.u_f_3L03.u_s1.go_e||fullcone.u_f_3L03.u_s1.cfg[0]||fullcone.u_f_3L03.u_s1.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q1 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s1.lc,fullcone.u_f_3L03.u_s1.go_x,fullcone.u_f_3L03.u_s1.tag,fullcone.u_f_3L03.u_s1.go_e,fullcone.u_f_3L03.u_s1.go_tag,fullcone.u_f_3L03.u_s1.ef,fullcone.u_f_3L03.u_s1.st);
   if(fullcone.u_f_3L03.u_e1.go||oldgo||fullcone.u_f_3L03.u_e1.cfg_v||prevstate!={fullcone.u_f_3L03.u_e1.bank_free,fullcone.u_f_3L03.u_e1.sh_free,fullcone.u_f_3L03.u_e1.u_e.walk_busy,fullcone.u_f_3L03.u_e1.u_e.u_pq.walking,fullcone.u_f_3L03.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e1.u_e.u_pq.settle,fullcone.u_f_3L03.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e1.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q1 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e1.go,fullcone.u_f_3L03.u_e1.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e1.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e1.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e1.bank_free,fullcone.u_f_3L03.u_e1.sh_free,fullcone.u_f_3L03.u_e1.u_e.walk_busy,fullcone.u_f_3L03.u_e1.u_e.u_pq.walking,fullcone.u_f_3L03.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e1.u_e.u_pq.settle,fullcone.u_f_3L03.u_e1.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e1.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e1.cfg_v,fullcone.u_f_3L03.u_e1.cfg_a,fullcone.u_f_3L03.u_e1.cfg_d,fullcone.u_f_3L03.u_e1.u_e.u_pq.swap,fullcone.u_f_3L03.u_e1.fault);
   prevstate={fullcone.u_f_3L03.u_e1.bank_free,fullcone.u_f_3L03.u_e1.sh_free,fullcone.u_f_3L03.u_e1.u_e.walk_busy,fullcone.u_f_3L03.u_e1.u_e.u_pq.walking,fullcone.u_f_3L03.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e1.u_e.u_pq.settle,fullcone.u_f_3L03.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e1.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e1.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q1 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e1.pv,fullcone.u_f_3L03.u_e1.prow,fullcone.u_f_3L03.u_e1.pval,fullcone.u_f_3L03.u_e1.pseg,fullcone.u_f_3L03.u_e1.pnseg,fullcone.u_f_3L03.u_e1.perr,fullcone.u_f_3L03.u_e1.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q1 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e1.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q2
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e2.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e2.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e2.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s2.lc[0]||fullcone.u_f_3L03.u_s2.go_x||fullcone.u_f_3L03.u_s2.go_e||fullcone.u_f_3L03.u_s2.cfg[0]||fullcone.u_f_3L03.u_s2.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q2 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s2.lc,fullcone.u_f_3L03.u_s2.go_x,fullcone.u_f_3L03.u_s2.tag,fullcone.u_f_3L03.u_s2.go_e,fullcone.u_f_3L03.u_s2.go_tag,fullcone.u_f_3L03.u_s2.ef,fullcone.u_f_3L03.u_s2.st);
   if(fullcone.u_f_3L03.u_e2.go||oldgo||fullcone.u_f_3L03.u_e2.cfg_v||prevstate!={fullcone.u_f_3L03.u_e2.bank_free,fullcone.u_f_3L03.u_e2.sh_free,fullcone.u_f_3L03.u_e2.u_e.walk_busy,fullcone.u_f_3L03.u_e2.u_e.u_pq.walking,fullcone.u_f_3L03.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e2.u_e.u_pq.settle,fullcone.u_f_3L03.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e2.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q2 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e2.go,fullcone.u_f_3L03.u_e2.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e2.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e2.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e2.bank_free,fullcone.u_f_3L03.u_e2.sh_free,fullcone.u_f_3L03.u_e2.u_e.walk_busy,fullcone.u_f_3L03.u_e2.u_e.u_pq.walking,fullcone.u_f_3L03.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e2.u_e.u_pq.settle,fullcone.u_f_3L03.u_e2.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e2.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e2.cfg_v,fullcone.u_f_3L03.u_e2.cfg_a,fullcone.u_f_3L03.u_e2.cfg_d,fullcone.u_f_3L03.u_e2.u_e.u_pq.swap,fullcone.u_f_3L03.u_e2.fault);
   prevstate={fullcone.u_f_3L03.u_e2.bank_free,fullcone.u_f_3L03.u_e2.sh_free,fullcone.u_f_3L03.u_e2.u_e.walk_busy,fullcone.u_f_3L03.u_e2.u_e.u_pq.walking,fullcone.u_f_3L03.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e2.u_e.u_pq.settle,fullcone.u_f_3L03.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e2.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e2.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q2 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e2.pv,fullcone.u_f_3L03.u_e2.prow,fullcone.u_f_3L03.u_e2.pval,fullcone.u_f_3L03.u_e2.pseg,fullcone.u_f_3L03.u_e2.pnseg,fullcone.u_f_3L03.u_e2.perr,fullcone.u_f_3L03.u_e2.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q2 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e2.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q3
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e3.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e3.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e3.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s3.lc[0]||fullcone.u_f_3L03.u_s3.go_x||fullcone.u_f_3L03.u_s3.go_e||fullcone.u_f_3L03.u_s3.cfg[0]||fullcone.u_f_3L03.u_s3.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q3 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s3.lc,fullcone.u_f_3L03.u_s3.go_x,fullcone.u_f_3L03.u_s3.tag,fullcone.u_f_3L03.u_s3.go_e,fullcone.u_f_3L03.u_s3.go_tag,fullcone.u_f_3L03.u_s3.ef,fullcone.u_f_3L03.u_s3.st);
   if(fullcone.u_f_3L03.u_e3.go||oldgo||fullcone.u_f_3L03.u_e3.cfg_v||prevstate!={fullcone.u_f_3L03.u_e3.bank_free,fullcone.u_f_3L03.u_e3.sh_free,fullcone.u_f_3L03.u_e3.u_e.walk_busy,fullcone.u_f_3L03.u_e3.u_e.u_pq.walking,fullcone.u_f_3L03.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e3.u_e.u_pq.settle,fullcone.u_f_3L03.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e3.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q3 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e3.go,fullcone.u_f_3L03.u_e3.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e3.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e3.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e3.bank_free,fullcone.u_f_3L03.u_e3.sh_free,fullcone.u_f_3L03.u_e3.u_e.walk_busy,fullcone.u_f_3L03.u_e3.u_e.u_pq.walking,fullcone.u_f_3L03.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e3.u_e.u_pq.settle,fullcone.u_f_3L03.u_e3.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e3.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e3.cfg_v,fullcone.u_f_3L03.u_e3.cfg_a,fullcone.u_f_3L03.u_e3.cfg_d,fullcone.u_f_3L03.u_e3.u_e.u_pq.swap,fullcone.u_f_3L03.u_e3.fault);
   prevstate={fullcone.u_f_3L03.u_e3.bank_free,fullcone.u_f_3L03.u_e3.sh_free,fullcone.u_f_3L03.u_e3.u_e.walk_busy,fullcone.u_f_3L03.u_e3.u_e.u_pq.walking,fullcone.u_f_3L03.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e3.u_e.u_pq.settle,fullcone.u_f_3L03.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e3.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e3.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q3 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e3.pv,fullcone.u_f_3L03.u_e3.prow,fullcone.u_f_3L03.u_e3.pval,fullcone.u_f_3L03.u_e3.pseg,fullcone.u_f_3L03.u_e3.pnseg,fullcone.u_f_3L03.u_e3.perr,fullcone.u_f_3L03.u_e3.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q3 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e3.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q5
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e5.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e5.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e5.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s5.lc[0]||fullcone.u_f_3L03.u_s5.go_x||fullcone.u_f_3L03.u_s5.go_e||fullcone.u_f_3L03.u_s5.cfg[0]||fullcone.u_f_3L03.u_s5.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q5 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s5.lc,fullcone.u_f_3L03.u_s5.go_x,fullcone.u_f_3L03.u_s5.tag,fullcone.u_f_3L03.u_s5.go_e,fullcone.u_f_3L03.u_s5.go_tag,fullcone.u_f_3L03.u_s5.ef,fullcone.u_f_3L03.u_s5.st);
   if(fullcone.u_f_3L03.u_e5.go||oldgo||fullcone.u_f_3L03.u_e5.cfg_v||prevstate!={fullcone.u_f_3L03.u_e5.bank_free,fullcone.u_f_3L03.u_e5.sh_free,fullcone.u_f_3L03.u_e5.u_e.walk_busy,fullcone.u_f_3L03.u_e5.u_e.u_pq.walking,fullcone.u_f_3L03.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e5.u_e.u_pq.settle,fullcone.u_f_3L03.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e5.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q5 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e5.go,fullcone.u_f_3L03.u_e5.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e5.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e5.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e5.bank_free,fullcone.u_f_3L03.u_e5.sh_free,fullcone.u_f_3L03.u_e5.u_e.walk_busy,fullcone.u_f_3L03.u_e5.u_e.u_pq.walking,fullcone.u_f_3L03.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e5.u_e.u_pq.settle,fullcone.u_f_3L03.u_e5.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e5.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e5.cfg_v,fullcone.u_f_3L03.u_e5.cfg_a,fullcone.u_f_3L03.u_e5.cfg_d,fullcone.u_f_3L03.u_e5.u_e.u_pq.swap,fullcone.u_f_3L03.u_e5.fault);
   prevstate={fullcone.u_f_3L03.u_e5.bank_free,fullcone.u_f_3L03.u_e5.sh_free,fullcone.u_f_3L03.u_e5.u_e.walk_busy,fullcone.u_f_3L03.u_e5.u_e.u_pq.walking,fullcone.u_f_3L03.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e5.u_e.u_pq.settle,fullcone.u_f_3L03.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e5.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e5.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q5 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e5.pv,fullcone.u_f_3L03.u_e5.prow,fullcone.u_f_3L03.u_e5.pval,fullcone.u_f_3L03.u_e5.pseg,fullcone.u_f_3L03.u_e5.pnseg,fullcone.u_f_3L03.u_e5.perr,fullcone.u_f_3L03.u_e5.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q5 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e5.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q6
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e6.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e6.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e6.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s6.lc[0]||fullcone.u_f_3L03.u_s6.go_x||fullcone.u_f_3L03.u_s6.go_e||fullcone.u_f_3L03.u_s6.cfg[0]||fullcone.u_f_3L03.u_s6.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q6 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s6.lc,fullcone.u_f_3L03.u_s6.go_x,fullcone.u_f_3L03.u_s6.tag,fullcone.u_f_3L03.u_s6.go_e,fullcone.u_f_3L03.u_s6.go_tag,fullcone.u_f_3L03.u_s6.ef,fullcone.u_f_3L03.u_s6.st);
   if(fullcone.u_f_3L03.u_e6.go||oldgo||fullcone.u_f_3L03.u_e6.cfg_v||prevstate!={fullcone.u_f_3L03.u_e6.bank_free,fullcone.u_f_3L03.u_e6.sh_free,fullcone.u_f_3L03.u_e6.u_e.walk_busy,fullcone.u_f_3L03.u_e6.u_e.u_pq.walking,fullcone.u_f_3L03.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e6.u_e.u_pq.settle,fullcone.u_f_3L03.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e6.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q6 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e6.go,fullcone.u_f_3L03.u_e6.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e6.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e6.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e6.bank_free,fullcone.u_f_3L03.u_e6.sh_free,fullcone.u_f_3L03.u_e6.u_e.walk_busy,fullcone.u_f_3L03.u_e6.u_e.u_pq.walking,fullcone.u_f_3L03.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e6.u_e.u_pq.settle,fullcone.u_f_3L03.u_e6.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e6.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e6.cfg_v,fullcone.u_f_3L03.u_e6.cfg_a,fullcone.u_f_3L03.u_e6.cfg_d,fullcone.u_f_3L03.u_e6.u_e.u_pq.swap,fullcone.u_f_3L03.u_e6.fault);
   prevstate={fullcone.u_f_3L03.u_e6.bank_free,fullcone.u_f_3L03.u_e6.sh_free,fullcone.u_f_3L03.u_e6.u_e.walk_busy,fullcone.u_f_3L03.u_e6.u_e.u_pq.walking,fullcone.u_f_3L03.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e6.u_e.u_pq.settle,fullcone.u_f_3L03.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e6.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e6.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q6 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e6.pv,fullcone.u_f_3L03.u_e6.prow,fullcone.u_f_3L03.u_e6.pval,fullcone.u_f_3L03.u_e6.pseg,fullcone.u_f_3L03.u_e6.pnseg,fullcone.u_f_3L03.u_e6.perr,fullcone.u_f_3L03.u_e6.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q6 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e6.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q7
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e7.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e7.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e7.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s7.lc[0]||fullcone.u_f_3L03.u_s7.go_x||fullcone.u_f_3L03.u_s7.go_e||fullcone.u_f_3L03.u_s7.cfg[0]||fullcone.u_f_3L03.u_s7.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q7 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s7.lc,fullcone.u_f_3L03.u_s7.go_x,fullcone.u_f_3L03.u_s7.tag,fullcone.u_f_3L03.u_s7.go_e,fullcone.u_f_3L03.u_s7.go_tag,fullcone.u_f_3L03.u_s7.ef,fullcone.u_f_3L03.u_s7.st);
   if(fullcone.u_f_3L03.u_e7.go||oldgo||fullcone.u_f_3L03.u_e7.cfg_v||prevstate!={fullcone.u_f_3L03.u_e7.bank_free,fullcone.u_f_3L03.u_e7.sh_free,fullcone.u_f_3L03.u_e7.u_e.walk_busy,fullcone.u_f_3L03.u_e7.u_e.u_pq.walking,fullcone.u_f_3L03.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e7.u_e.u_pq.settle,fullcone.u_f_3L03.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e7.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q7 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e7.go,fullcone.u_f_3L03.u_e7.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e7.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e7.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e7.bank_free,fullcone.u_f_3L03.u_e7.sh_free,fullcone.u_f_3L03.u_e7.u_e.walk_busy,fullcone.u_f_3L03.u_e7.u_e.u_pq.walking,fullcone.u_f_3L03.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e7.u_e.u_pq.settle,fullcone.u_f_3L03.u_e7.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e7.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e7.cfg_v,fullcone.u_f_3L03.u_e7.cfg_a,fullcone.u_f_3L03.u_e7.cfg_d,fullcone.u_f_3L03.u_e7.u_e.u_pq.swap,fullcone.u_f_3L03.u_e7.fault);
   prevstate={fullcone.u_f_3L03.u_e7.bank_free,fullcone.u_f_3L03.u_e7.sh_free,fullcone.u_f_3L03.u_e7.u_e.walk_busy,fullcone.u_f_3L03.u_e7.u_e.u_pq.walking,fullcone.u_f_3L03.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e7.u_e.u_pq.settle,fullcone.u_f_3L03.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e7.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e7.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q7 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e7.pv,fullcone.u_f_3L03.u_e7.prow,fullcone.u_f_3L03.u_e7.pval,fullcone.u_f_3L03.u_e7.pseg,fullcone.u_f_3L03.u_e7.pnseg,fullcone.u_f_3L03.u_e7.perr,fullcone.u_f_3L03.u_e7.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q7 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e7.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q9
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e9.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e9.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e9.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s9.lc[0]||fullcone.u_f_3L03.u_s9.go_x||fullcone.u_f_3L03.u_s9.go_e||fullcone.u_f_3L03.u_s9.cfg[0]||fullcone.u_f_3L03.u_s9.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q9 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s9.lc,fullcone.u_f_3L03.u_s9.go_x,fullcone.u_f_3L03.u_s9.tag,fullcone.u_f_3L03.u_s9.go_e,fullcone.u_f_3L03.u_s9.go_tag,fullcone.u_f_3L03.u_s9.ef,fullcone.u_f_3L03.u_s9.st);
   if(fullcone.u_f_3L03.u_e9.go||oldgo||fullcone.u_f_3L03.u_e9.cfg_v||prevstate!={fullcone.u_f_3L03.u_e9.bank_free,fullcone.u_f_3L03.u_e9.sh_free,fullcone.u_f_3L03.u_e9.u_e.walk_busy,fullcone.u_f_3L03.u_e9.u_e.u_pq.walking,fullcone.u_f_3L03.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e9.u_e.u_pq.settle,fullcone.u_f_3L03.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e9.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q9 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e9.go,fullcone.u_f_3L03.u_e9.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e9.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e9.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e9.bank_free,fullcone.u_f_3L03.u_e9.sh_free,fullcone.u_f_3L03.u_e9.u_e.walk_busy,fullcone.u_f_3L03.u_e9.u_e.u_pq.walking,fullcone.u_f_3L03.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e9.u_e.u_pq.settle,fullcone.u_f_3L03.u_e9.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e9.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e9.cfg_v,fullcone.u_f_3L03.u_e9.cfg_a,fullcone.u_f_3L03.u_e9.cfg_d,fullcone.u_f_3L03.u_e9.u_e.u_pq.swap,fullcone.u_f_3L03.u_e9.fault);
   prevstate={fullcone.u_f_3L03.u_e9.bank_free,fullcone.u_f_3L03.u_e9.sh_free,fullcone.u_f_3L03.u_e9.u_e.walk_busy,fullcone.u_f_3L03.u_e9.u_e.u_pq.walking,fullcone.u_f_3L03.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e9.u_e.u_pq.settle,fullcone.u_f_3L03.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e9.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e9.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q9 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e9.pv,fullcone.u_f_3L03.u_e9.prow,fullcone.u_f_3L03.u_e9.pval,fullcone.u_f_3L03.u_e9.pseg,fullcone.u_f_3L03.u_e9.pnseg,fullcone.u_f_3L03.u_e9.perr,fullcone.u_f_3L03.u_e9.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q9 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e9.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q10
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e10.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e10.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e10.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s10.lc[0]||fullcone.u_f_3L03.u_s10.go_x||fullcone.u_f_3L03.u_s10.go_e||fullcone.u_f_3L03.u_s10.cfg[0]||fullcone.u_f_3L03.u_s10.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q10 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s10.lc,fullcone.u_f_3L03.u_s10.go_x,fullcone.u_f_3L03.u_s10.tag,fullcone.u_f_3L03.u_s10.go_e,fullcone.u_f_3L03.u_s10.go_tag,fullcone.u_f_3L03.u_s10.ef,fullcone.u_f_3L03.u_s10.st);
   if(fullcone.u_f_3L03.u_e10.go||oldgo||fullcone.u_f_3L03.u_e10.cfg_v||prevstate!={fullcone.u_f_3L03.u_e10.bank_free,fullcone.u_f_3L03.u_e10.sh_free,fullcone.u_f_3L03.u_e10.u_e.walk_busy,fullcone.u_f_3L03.u_e10.u_e.u_pq.walking,fullcone.u_f_3L03.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e10.u_e.u_pq.settle,fullcone.u_f_3L03.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e10.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q10 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e10.go,fullcone.u_f_3L03.u_e10.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e10.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e10.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e10.bank_free,fullcone.u_f_3L03.u_e10.sh_free,fullcone.u_f_3L03.u_e10.u_e.walk_busy,fullcone.u_f_3L03.u_e10.u_e.u_pq.walking,fullcone.u_f_3L03.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e10.u_e.u_pq.settle,fullcone.u_f_3L03.u_e10.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e10.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e10.cfg_v,fullcone.u_f_3L03.u_e10.cfg_a,fullcone.u_f_3L03.u_e10.cfg_d,fullcone.u_f_3L03.u_e10.u_e.u_pq.swap,fullcone.u_f_3L03.u_e10.fault);
   prevstate={fullcone.u_f_3L03.u_e10.bank_free,fullcone.u_f_3L03.u_e10.sh_free,fullcone.u_f_3L03.u_e10.u_e.walk_busy,fullcone.u_f_3L03.u_e10.u_e.u_pq.walking,fullcone.u_f_3L03.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e10.u_e.u_pq.settle,fullcone.u_f_3L03.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e10.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e10.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q10 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e10.pv,fullcone.u_f_3L03.u_e10.prow,fullcone.u_f_3L03.u_e10.pval,fullcone.u_f_3L03.u_e10.pseg,fullcone.u_f_3L03.u_e10.pnseg,fullcone.u_f_3L03.u_e10.perr,fullcone.u_f_3L03.u_e10.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q10 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e10.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q11
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e11.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e11.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e11.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s11.lc[0]||fullcone.u_f_3L03.u_s11.go_x||fullcone.u_f_3L03.u_s11.go_e||fullcone.u_f_3L03.u_s11.cfg[0]||fullcone.u_f_3L03.u_s11.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q11 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s11.lc,fullcone.u_f_3L03.u_s11.go_x,fullcone.u_f_3L03.u_s11.tag,fullcone.u_f_3L03.u_s11.go_e,fullcone.u_f_3L03.u_s11.go_tag,fullcone.u_f_3L03.u_s11.ef,fullcone.u_f_3L03.u_s11.st);
   if(fullcone.u_f_3L03.u_e11.go||oldgo||fullcone.u_f_3L03.u_e11.cfg_v||prevstate!={fullcone.u_f_3L03.u_e11.bank_free,fullcone.u_f_3L03.u_e11.sh_free,fullcone.u_f_3L03.u_e11.u_e.walk_busy,fullcone.u_f_3L03.u_e11.u_e.u_pq.walking,fullcone.u_f_3L03.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e11.u_e.u_pq.settle,fullcone.u_f_3L03.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e11.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q11 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e11.go,fullcone.u_f_3L03.u_e11.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e11.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e11.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e11.bank_free,fullcone.u_f_3L03.u_e11.sh_free,fullcone.u_f_3L03.u_e11.u_e.walk_busy,fullcone.u_f_3L03.u_e11.u_e.u_pq.walking,fullcone.u_f_3L03.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e11.u_e.u_pq.settle,fullcone.u_f_3L03.u_e11.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e11.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e11.cfg_v,fullcone.u_f_3L03.u_e11.cfg_a,fullcone.u_f_3L03.u_e11.cfg_d,fullcone.u_f_3L03.u_e11.u_e.u_pq.swap,fullcone.u_f_3L03.u_e11.fault);
   prevstate={fullcone.u_f_3L03.u_e11.bank_free,fullcone.u_f_3L03.u_e11.sh_free,fullcone.u_f_3L03.u_e11.u_e.walk_busy,fullcone.u_f_3L03.u_e11.u_e.u_pq.walking,fullcone.u_f_3L03.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e11.u_e.u_pq.settle,fullcone.u_f_3L03.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e11.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e11.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q11 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e11.pv,fullcone.u_f_3L03.u_e11.prow,fullcone.u_f_3L03.u_e11.pval,fullcone.u_f_3L03.u_e11.pseg,fullcone.u_f_3L03.u_e11.pnseg,fullcone.u_f_3L03.u_e11.perr,fullcone.u_f_3L03.u_e11.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q11 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e11.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q12
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e12.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e12.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e12.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s12.lc[0]||fullcone.u_f_3L03.u_s12.go_x||fullcone.u_f_3L03.u_s12.go_e||fullcone.u_f_3L03.u_s12.cfg[0]||fullcone.u_f_3L03.u_s12.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q12 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s12.lc,fullcone.u_f_3L03.u_s12.go_x,fullcone.u_f_3L03.u_s12.tag,fullcone.u_f_3L03.u_s12.go_e,fullcone.u_f_3L03.u_s12.go_tag,fullcone.u_f_3L03.u_s12.ef,fullcone.u_f_3L03.u_s12.st);
   if(fullcone.u_f_3L03.u_e12.go||oldgo||fullcone.u_f_3L03.u_e12.cfg_v||prevstate!={fullcone.u_f_3L03.u_e12.bank_free,fullcone.u_f_3L03.u_e12.sh_free,fullcone.u_f_3L03.u_e12.u_e.walk_busy,fullcone.u_f_3L03.u_e12.u_e.u_pq.walking,fullcone.u_f_3L03.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e12.u_e.u_pq.settle,fullcone.u_f_3L03.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e12.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q12 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e12.go,fullcone.u_f_3L03.u_e12.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e12.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e12.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e12.bank_free,fullcone.u_f_3L03.u_e12.sh_free,fullcone.u_f_3L03.u_e12.u_e.walk_busy,fullcone.u_f_3L03.u_e12.u_e.u_pq.walking,fullcone.u_f_3L03.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e12.u_e.u_pq.settle,fullcone.u_f_3L03.u_e12.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e12.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e12.cfg_v,fullcone.u_f_3L03.u_e12.cfg_a,fullcone.u_f_3L03.u_e12.cfg_d,fullcone.u_f_3L03.u_e12.u_e.u_pq.swap,fullcone.u_f_3L03.u_e12.fault);
   prevstate={fullcone.u_f_3L03.u_e12.bank_free,fullcone.u_f_3L03.u_e12.sh_free,fullcone.u_f_3L03.u_e12.u_e.walk_busy,fullcone.u_f_3L03.u_e12.u_e.u_pq.walking,fullcone.u_f_3L03.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e12.u_e.u_pq.settle,fullcone.u_f_3L03.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e12.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e12.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q12 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e12.pv,fullcone.u_f_3L03.u_e12.prow,fullcone.u_f_3L03.u_e12.pval,fullcone.u_f_3L03.u_e12.pseg,fullcone.u_f_3L03.u_e12.pnseg,fullcone.u_f_3L03.u_e12.perr,fullcone.u_f_3L03.u_e12.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q12 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e12.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3L03_q14
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3L03.u_e14.u_e.u_pq.wbank;oldgo=fullcone.u_f_3L03.u_e14.u_e.go_e;oldtag=fullcone.u_f_3L03.u_e14.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3L03.u_s14.lc[0]||fullcone.u_f_3L03.u_s14.go_x||fullcone.u_f_3L03.u_s14.go_e||fullcone.u_f_3L03.u_s14.cfg[0]||fullcone.u_f_3L03.u_s14.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3L03_q14 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3L03.u_s14.lc,fullcone.u_f_3L03.u_s14.go_x,fullcone.u_f_3L03.u_s14.tag,fullcone.u_f_3L03.u_s14.go_e,fullcone.u_f_3L03.u_s14.go_tag,fullcone.u_f_3L03.u_s14.ef,fullcone.u_f_3L03.u_s14.st);
   if(fullcone.u_f_3L03.u_e14.go||oldgo||fullcone.u_f_3L03.u_e14.cfg_v||prevstate!={fullcone.u_f_3L03.u_e14.bank_free,fullcone.u_f_3L03.u_e14.sh_free,fullcone.u_f_3L03.u_e14.u_e.walk_busy,fullcone.u_f_3L03.u_e14.u_e.u_pq.walking,fullcone.u_f_3L03.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e14.u_e.u_pq.settle,fullcone.u_f_3L03.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e14.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3L03_q14 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3L03.u_e14.go,fullcone.u_f_3L03.u_e14.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3L03.u_e14.u_e.u_pq.otag[0],fullcone.u_f_3L03.u_e14.u_e.u_pq.otag[1],fullcone.u_f_3L03.u_e14.bank_free,fullcone.u_f_3L03.u_e14.sh_free,fullcone.u_f_3L03.u_e14.u_e.walk_busy,fullcone.u_f_3L03.u_e14.u_e.u_pq.walking,fullcone.u_f_3L03.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e14.u_e.u_pq.settle,fullcone.u_f_3L03.u_e14.u_e.u_pq.gcnt[0],fullcone.u_f_3L03.u_e14.u_e.u_pq.gcnt[1],fullcone.u_f_3L03.u_e14.cfg_v,fullcone.u_f_3L03.u_e14.cfg_a,fullcone.u_f_3L03.u_e14.cfg_d,fullcone.u_f_3L03.u_e14.u_e.u_pq.swap,fullcone.u_f_3L03.u_e14.fault);
   prevstate={fullcone.u_f_3L03.u_e14.bank_free,fullcone.u_f_3L03.u_e14.sh_free,fullcone.u_f_3L03.u_e14.u_e.walk_busy,fullcone.u_f_3L03.u_e14.u_e.u_pq.walking,fullcone.u_f_3L03.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3L03.u_e14.u_e.u_pq.settle,fullcone.u_f_3L03.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3L03.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3L03.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3L03.u_e14.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3L03.u_e14.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3L03_q14 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3L03.u_e14.pv,fullcone.u_f_3L03.u_e14.prow,fullcone.u_f_3L03.u_e14.pval,fullcone.u_f_3L03.u_e14.pseg,fullcone.u_f_3L03.u_e14.pnseg,fullcone.u_f_3L03.u_e14.perr,fullcone.u_f_3L03.u_e14.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3L03_q14 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3L03.u_e14.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q0
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e0.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e0.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e0.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s0.lc[0]||fullcone.u_f_3R01.u_s0.go_x||fullcone.u_f_3R01.u_s0.go_e||fullcone.u_f_3R01.u_s0.cfg[0]||fullcone.u_f_3R01.u_s0.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q0 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s0.lc,fullcone.u_f_3R01.u_s0.go_x,fullcone.u_f_3R01.u_s0.tag,fullcone.u_f_3R01.u_s0.go_e,fullcone.u_f_3R01.u_s0.go_tag,fullcone.u_f_3R01.u_s0.ef,fullcone.u_f_3R01.u_s0.st);
   if(fullcone.u_f_3R01.u_e0.go||oldgo||fullcone.u_f_3R01.u_e0.cfg_v||prevstate!={fullcone.u_f_3R01.u_e0.bank_free,fullcone.u_f_3R01.u_e0.sh_free,fullcone.u_f_3R01.u_e0.u_e.walk_busy,fullcone.u_f_3R01.u_e0.u_e.u_pq.walking,fullcone.u_f_3R01.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e0.u_e.u_pq.settle,fullcone.u_f_3R01.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e0.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q0 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e0.go,fullcone.u_f_3R01.u_e0.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e0.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e0.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e0.bank_free,fullcone.u_f_3R01.u_e0.sh_free,fullcone.u_f_3R01.u_e0.u_e.walk_busy,fullcone.u_f_3R01.u_e0.u_e.u_pq.walking,fullcone.u_f_3R01.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e0.u_e.u_pq.settle,fullcone.u_f_3R01.u_e0.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e0.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e0.cfg_v,fullcone.u_f_3R01.u_e0.cfg_a,fullcone.u_f_3R01.u_e0.cfg_d,fullcone.u_f_3R01.u_e0.u_e.u_pq.swap,fullcone.u_f_3R01.u_e0.fault);
   prevstate={fullcone.u_f_3R01.u_e0.bank_free,fullcone.u_f_3R01.u_e0.sh_free,fullcone.u_f_3R01.u_e0.u_e.walk_busy,fullcone.u_f_3R01.u_e0.u_e.u_pq.walking,fullcone.u_f_3R01.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e0.u_e.u_pq.settle,fullcone.u_f_3R01.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e0.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e0.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q0 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e0.pv,fullcone.u_f_3R01.u_e0.prow,fullcone.u_f_3R01.u_e0.pval,fullcone.u_f_3R01.u_e0.pseg,fullcone.u_f_3R01.u_e0.pnseg,fullcone.u_f_3R01.u_e0.perr,fullcone.u_f_3R01.u_e0.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q0 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e0.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q2
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e2.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e2.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e2.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s2.lc[0]||fullcone.u_f_3R01.u_s2.go_x||fullcone.u_f_3R01.u_s2.go_e||fullcone.u_f_3R01.u_s2.cfg[0]||fullcone.u_f_3R01.u_s2.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q2 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s2.lc,fullcone.u_f_3R01.u_s2.go_x,fullcone.u_f_3R01.u_s2.tag,fullcone.u_f_3R01.u_s2.go_e,fullcone.u_f_3R01.u_s2.go_tag,fullcone.u_f_3R01.u_s2.ef,fullcone.u_f_3R01.u_s2.st);
   if(fullcone.u_f_3R01.u_e2.go||oldgo||fullcone.u_f_3R01.u_e2.cfg_v||prevstate!={fullcone.u_f_3R01.u_e2.bank_free,fullcone.u_f_3R01.u_e2.sh_free,fullcone.u_f_3R01.u_e2.u_e.walk_busy,fullcone.u_f_3R01.u_e2.u_e.u_pq.walking,fullcone.u_f_3R01.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e2.u_e.u_pq.settle,fullcone.u_f_3R01.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e2.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q2 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e2.go,fullcone.u_f_3R01.u_e2.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e2.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e2.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e2.bank_free,fullcone.u_f_3R01.u_e2.sh_free,fullcone.u_f_3R01.u_e2.u_e.walk_busy,fullcone.u_f_3R01.u_e2.u_e.u_pq.walking,fullcone.u_f_3R01.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e2.u_e.u_pq.settle,fullcone.u_f_3R01.u_e2.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e2.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e2.cfg_v,fullcone.u_f_3R01.u_e2.cfg_a,fullcone.u_f_3R01.u_e2.cfg_d,fullcone.u_f_3R01.u_e2.u_e.u_pq.swap,fullcone.u_f_3R01.u_e2.fault);
   prevstate={fullcone.u_f_3R01.u_e2.bank_free,fullcone.u_f_3R01.u_e2.sh_free,fullcone.u_f_3R01.u_e2.u_e.walk_busy,fullcone.u_f_3R01.u_e2.u_e.u_pq.walking,fullcone.u_f_3R01.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e2.u_e.u_pq.settle,fullcone.u_f_3R01.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e2.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e2.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q2 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e2.pv,fullcone.u_f_3R01.u_e2.prow,fullcone.u_f_3R01.u_e2.pval,fullcone.u_f_3R01.u_e2.pseg,fullcone.u_f_3R01.u_e2.pnseg,fullcone.u_f_3R01.u_e2.perr,fullcone.u_f_3R01.u_e2.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q2 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e2.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q3
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e3.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e3.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e3.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s3.lc[0]||fullcone.u_f_3R01.u_s3.go_x||fullcone.u_f_3R01.u_s3.go_e||fullcone.u_f_3R01.u_s3.cfg[0]||fullcone.u_f_3R01.u_s3.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q3 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s3.lc,fullcone.u_f_3R01.u_s3.go_x,fullcone.u_f_3R01.u_s3.tag,fullcone.u_f_3R01.u_s3.go_e,fullcone.u_f_3R01.u_s3.go_tag,fullcone.u_f_3R01.u_s3.ef,fullcone.u_f_3R01.u_s3.st);
   if(fullcone.u_f_3R01.u_e3.go||oldgo||fullcone.u_f_3R01.u_e3.cfg_v||prevstate!={fullcone.u_f_3R01.u_e3.bank_free,fullcone.u_f_3R01.u_e3.sh_free,fullcone.u_f_3R01.u_e3.u_e.walk_busy,fullcone.u_f_3R01.u_e3.u_e.u_pq.walking,fullcone.u_f_3R01.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e3.u_e.u_pq.settle,fullcone.u_f_3R01.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e3.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q3 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e3.go,fullcone.u_f_3R01.u_e3.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e3.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e3.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e3.bank_free,fullcone.u_f_3R01.u_e3.sh_free,fullcone.u_f_3R01.u_e3.u_e.walk_busy,fullcone.u_f_3R01.u_e3.u_e.u_pq.walking,fullcone.u_f_3R01.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e3.u_e.u_pq.settle,fullcone.u_f_3R01.u_e3.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e3.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e3.cfg_v,fullcone.u_f_3R01.u_e3.cfg_a,fullcone.u_f_3R01.u_e3.cfg_d,fullcone.u_f_3R01.u_e3.u_e.u_pq.swap,fullcone.u_f_3R01.u_e3.fault);
   prevstate={fullcone.u_f_3R01.u_e3.bank_free,fullcone.u_f_3R01.u_e3.sh_free,fullcone.u_f_3R01.u_e3.u_e.walk_busy,fullcone.u_f_3R01.u_e3.u_e.u_pq.walking,fullcone.u_f_3R01.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e3.u_e.u_pq.settle,fullcone.u_f_3R01.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e3.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e3.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q3 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e3.pv,fullcone.u_f_3R01.u_e3.prow,fullcone.u_f_3R01.u_e3.pval,fullcone.u_f_3R01.u_e3.pseg,fullcone.u_f_3R01.u_e3.pnseg,fullcone.u_f_3R01.u_e3.perr,fullcone.u_f_3R01.u_e3.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q3 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e3.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q4
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e4.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e4.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e4.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s4.lc[0]||fullcone.u_f_3R01.u_s4.go_x||fullcone.u_f_3R01.u_s4.go_e||fullcone.u_f_3R01.u_s4.cfg[0]||fullcone.u_f_3R01.u_s4.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q4 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s4.lc,fullcone.u_f_3R01.u_s4.go_x,fullcone.u_f_3R01.u_s4.tag,fullcone.u_f_3R01.u_s4.go_e,fullcone.u_f_3R01.u_s4.go_tag,fullcone.u_f_3R01.u_s4.ef,fullcone.u_f_3R01.u_s4.st);
   if(fullcone.u_f_3R01.u_e4.go||oldgo||fullcone.u_f_3R01.u_e4.cfg_v||prevstate!={fullcone.u_f_3R01.u_e4.bank_free,fullcone.u_f_3R01.u_e4.sh_free,fullcone.u_f_3R01.u_e4.u_e.walk_busy,fullcone.u_f_3R01.u_e4.u_e.u_pq.walking,fullcone.u_f_3R01.u_e4.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e4.u_e.u_pq.settle,fullcone.u_f_3R01.u_e4.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e4.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e4.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e4.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q4 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e4.go,fullcone.u_f_3R01.u_e4.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e4.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e4.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e4.bank_free,fullcone.u_f_3R01.u_e4.sh_free,fullcone.u_f_3R01.u_e4.u_e.walk_busy,fullcone.u_f_3R01.u_e4.u_e.u_pq.walking,fullcone.u_f_3R01.u_e4.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e4.u_e.u_pq.settle,fullcone.u_f_3R01.u_e4.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e4.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e4.cfg_v,fullcone.u_f_3R01.u_e4.cfg_a,fullcone.u_f_3R01.u_e4.cfg_d,fullcone.u_f_3R01.u_e4.u_e.u_pq.swap,fullcone.u_f_3R01.u_e4.fault);
   prevstate={fullcone.u_f_3R01.u_e4.bank_free,fullcone.u_f_3R01.u_e4.sh_free,fullcone.u_f_3R01.u_e4.u_e.walk_busy,fullcone.u_f_3R01.u_e4.u_e.u_pq.walking,fullcone.u_f_3R01.u_e4.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e4.u_e.u_pq.settle,fullcone.u_f_3R01.u_e4.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e4.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e4.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e4.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e4.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q4 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e4.pv,fullcone.u_f_3R01.u_e4.prow,fullcone.u_f_3R01.u_e4.pval,fullcone.u_f_3R01.u_e4.pseg,fullcone.u_f_3R01.u_e4.pnseg,fullcone.u_f_3R01.u_e4.perr,fullcone.u_f_3R01.u_e4.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q4 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e4.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q6
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e6.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e6.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e6.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s6.lc[0]||fullcone.u_f_3R01.u_s6.go_x||fullcone.u_f_3R01.u_s6.go_e||fullcone.u_f_3R01.u_s6.cfg[0]||fullcone.u_f_3R01.u_s6.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q6 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s6.lc,fullcone.u_f_3R01.u_s6.go_x,fullcone.u_f_3R01.u_s6.tag,fullcone.u_f_3R01.u_s6.go_e,fullcone.u_f_3R01.u_s6.go_tag,fullcone.u_f_3R01.u_s6.ef,fullcone.u_f_3R01.u_s6.st);
   if(fullcone.u_f_3R01.u_e6.go||oldgo||fullcone.u_f_3R01.u_e6.cfg_v||prevstate!={fullcone.u_f_3R01.u_e6.bank_free,fullcone.u_f_3R01.u_e6.sh_free,fullcone.u_f_3R01.u_e6.u_e.walk_busy,fullcone.u_f_3R01.u_e6.u_e.u_pq.walking,fullcone.u_f_3R01.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e6.u_e.u_pq.settle,fullcone.u_f_3R01.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e6.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q6 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e6.go,fullcone.u_f_3R01.u_e6.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e6.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e6.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e6.bank_free,fullcone.u_f_3R01.u_e6.sh_free,fullcone.u_f_3R01.u_e6.u_e.walk_busy,fullcone.u_f_3R01.u_e6.u_e.u_pq.walking,fullcone.u_f_3R01.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e6.u_e.u_pq.settle,fullcone.u_f_3R01.u_e6.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e6.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e6.cfg_v,fullcone.u_f_3R01.u_e6.cfg_a,fullcone.u_f_3R01.u_e6.cfg_d,fullcone.u_f_3R01.u_e6.u_e.u_pq.swap,fullcone.u_f_3R01.u_e6.fault);
   prevstate={fullcone.u_f_3R01.u_e6.bank_free,fullcone.u_f_3R01.u_e6.sh_free,fullcone.u_f_3R01.u_e6.u_e.walk_busy,fullcone.u_f_3R01.u_e6.u_e.u_pq.walking,fullcone.u_f_3R01.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e6.u_e.u_pq.settle,fullcone.u_f_3R01.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e6.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e6.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q6 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e6.pv,fullcone.u_f_3R01.u_e6.prow,fullcone.u_f_3R01.u_e6.pval,fullcone.u_f_3R01.u_e6.pseg,fullcone.u_f_3R01.u_e6.pnseg,fullcone.u_f_3R01.u_e6.perr,fullcone.u_f_3R01.u_e6.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q6 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e6.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q7
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e7.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e7.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e7.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s7.lc[0]||fullcone.u_f_3R01.u_s7.go_x||fullcone.u_f_3R01.u_s7.go_e||fullcone.u_f_3R01.u_s7.cfg[0]||fullcone.u_f_3R01.u_s7.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q7 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s7.lc,fullcone.u_f_3R01.u_s7.go_x,fullcone.u_f_3R01.u_s7.tag,fullcone.u_f_3R01.u_s7.go_e,fullcone.u_f_3R01.u_s7.go_tag,fullcone.u_f_3R01.u_s7.ef,fullcone.u_f_3R01.u_s7.st);
   if(fullcone.u_f_3R01.u_e7.go||oldgo||fullcone.u_f_3R01.u_e7.cfg_v||prevstate!={fullcone.u_f_3R01.u_e7.bank_free,fullcone.u_f_3R01.u_e7.sh_free,fullcone.u_f_3R01.u_e7.u_e.walk_busy,fullcone.u_f_3R01.u_e7.u_e.u_pq.walking,fullcone.u_f_3R01.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e7.u_e.u_pq.settle,fullcone.u_f_3R01.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e7.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q7 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e7.go,fullcone.u_f_3R01.u_e7.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e7.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e7.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e7.bank_free,fullcone.u_f_3R01.u_e7.sh_free,fullcone.u_f_3R01.u_e7.u_e.walk_busy,fullcone.u_f_3R01.u_e7.u_e.u_pq.walking,fullcone.u_f_3R01.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e7.u_e.u_pq.settle,fullcone.u_f_3R01.u_e7.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e7.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e7.cfg_v,fullcone.u_f_3R01.u_e7.cfg_a,fullcone.u_f_3R01.u_e7.cfg_d,fullcone.u_f_3R01.u_e7.u_e.u_pq.swap,fullcone.u_f_3R01.u_e7.fault);
   prevstate={fullcone.u_f_3R01.u_e7.bank_free,fullcone.u_f_3R01.u_e7.sh_free,fullcone.u_f_3R01.u_e7.u_e.walk_busy,fullcone.u_f_3R01.u_e7.u_e.u_pq.walking,fullcone.u_f_3R01.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e7.u_e.u_pq.settle,fullcone.u_f_3R01.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e7.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e7.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q7 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e7.pv,fullcone.u_f_3R01.u_e7.prow,fullcone.u_f_3R01.u_e7.pval,fullcone.u_f_3R01.u_e7.pseg,fullcone.u_f_3R01.u_e7.pnseg,fullcone.u_f_3R01.u_e7.perr,fullcone.u_f_3R01.u_e7.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q7 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e7.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q8
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e8.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e8.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e8.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s8.lc[0]||fullcone.u_f_3R01.u_s8.go_x||fullcone.u_f_3R01.u_s8.go_e||fullcone.u_f_3R01.u_s8.cfg[0]||fullcone.u_f_3R01.u_s8.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q8 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s8.lc,fullcone.u_f_3R01.u_s8.go_x,fullcone.u_f_3R01.u_s8.tag,fullcone.u_f_3R01.u_s8.go_e,fullcone.u_f_3R01.u_s8.go_tag,fullcone.u_f_3R01.u_s8.ef,fullcone.u_f_3R01.u_s8.st);
   if(fullcone.u_f_3R01.u_e8.go||oldgo||fullcone.u_f_3R01.u_e8.cfg_v||prevstate!={fullcone.u_f_3R01.u_e8.bank_free,fullcone.u_f_3R01.u_e8.sh_free,fullcone.u_f_3R01.u_e8.u_e.walk_busy,fullcone.u_f_3R01.u_e8.u_e.u_pq.walking,fullcone.u_f_3R01.u_e8.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e8.u_e.u_pq.settle,fullcone.u_f_3R01.u_e8.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e8.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e8.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e8.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q8 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e8.go,fullcone.u_f_3R01.u_e8.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e8.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e8.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e8.bank_free,fullcone.u_f_3R01.u_e8.sh_free,fullcone.u_f_3R01.u_e8.u_e.walk_busy,fullcone.u_f_3R01.u_e8.u_e.u_pq.walking,fullcone.u_f_3R01.u_e8.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e8.u_e.u_pq.settle,fullcone.u_f_3R01.u_e8.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e8.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e8.cfg_v,fullcone.u_f_3R01.u_e8.cfg_a,fullcone.u_f_3R01.u_e8.cfg_d,fullcone.u_f_3R01.u_e8.u_e.u_pq.swap,fullcone.u_f_3R01.u_e8.fault);
   prevstate={fullcone.u_f_3R01.u_e8.bank_free,fullcone.u_f_3R01.u_e8.sh_free,fullcone.u_f_3R01.u_e8.u_e.walk_busy,fullcone.u_f_3R01.u_e8.u_e.u_pq.walking,fullcone.u_f_3R01.u_e8.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e8.u_e.u_pq.settle,fullcone.u_f_3R01.u_e8.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e8.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e8.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e8.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e8.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q8 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e8.pv,fullcone.u_f_3R01.u_e8.prow,fullcone.u_f_3R01.u_e8.pval,fullcone.u_f_3R01.u_e8.pseg,fullcone.u_f_3R01.u_e8.pnseg,fullcone.u_f_3R01.u_e8.perr,fullcone.u_f_3R01.u_e8.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q8 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e8.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q9
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e9.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e9.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e9.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s9.lc[0]||fullcone.u_f_3R01.u_s9.go_x||fullcone.u_f_3R01.u_s9.go_e||fullcone.u_f_3R01.u_s9.cfg[0]||fullcone.u_f_3R01.u_s9.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q9 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s9.lc,fullcone.u_f_3R01.u_s9.go_x,fullcone.u_f_3R01.u_s9.tag,fullcone.u_f_3R01.u_s9.go_e,fullcone.u_f_3R01.u_s9.go_tag,fullcone.u_f_3R01.u_s9.ef,fullcone.u_f_3R01.u_s9.st);
   if(fullcone.u_f_3R01.u_e9.go||oldgo||fullcone.u_f_3R01.u_e9.cfg_v||prevstate!={fullcone.u_f_3R01.u_e9.bank_free,fullcone.u_f_3R01.u_e9.sh_free,fullcone.u_f_3R01.u_e9.u_e.walk_busy,fullcone.u_f_3R01.u_e9.u_e.u_pq.walking,fullcone.u_f_3R01.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e9.u_e.u_pq.settle,fullcone.u_f_3R01.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e9.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q9 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e9.go,fullcone.u_f_3R01.u_e9.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e9.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e9.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e9.bank_free,fullcone.u_f_3R01.u_e9.sh_free,fullcone.u_f_3R01.u_e9.u_e.walk_busy,fullcone.u_f_3R01.u_e9.u_e.u_pq.walking,fullcone.u_f_3R01.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e9.u_e.u_pq.settle,fullcone.u_f_3R01.u_e9.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e9.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e9.cfg_v,fullcone.u_f_3R01.u_e9.cfg_a,fullcone.u_f_3R01.u_e9.cfg_d,fullcone.u_f_3R01.u_e9.u_e.u_pq.swap,fullcone.u_f_3R01.u_e9.fault);
   prevstate={fullcone.u_f_3R01.u_e9.bank_free,fullcone.u_f_3R01.u_e9.sh_free,fullcone.u_f_3R01.u_e9.u_e.walk_busy,fullcone.u_f_3R01.u_e9.u_e.u_pq.walking,fullcone.u_f_3R01.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e9.u_e.u_pq.settle,fullcone.u_f_3R01.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e9.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e9.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q9 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e9.pv,fullcone.u_f_3R01.u_e9.prow,fullcone.u_f_3R01.u_e9.pval,fullcone.u_f_3R01.u_e9.pseg,fullcone.u_f_3R01.u_e9.pnseg,fullcone.u_f_3R01.u_e9.perr,fullcone.u_f_3R01.u_e9.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q9 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e9.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q11
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e11.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e11.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e11.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s11.lc[0]||fullcone.u_f_3R01.u_s11.go_x||fullcone.u_f_3R01.u_s11.go_e||fullcone.u_f_3R01.u_s11.cfg[0]||fullcone.u_f_3R01.u_s11.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q11 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s11.lc,fullcone.u_f_3R01.u_s11.go_x,fullcone.u_f_3R01.u_s11.tag,fullcone.u_f_3R01.u_s11.go_e,fullcone.u_f_3R01.u_s11.go_tag,fullcone.u_f_3R01.u_s11.ef,fullcone.u_f_3R01.u_s11.st);
   if(fullcone.u_f_3R01.u_e11.go||oldgo||fullcone.u_f_3R01.u_e11.cfg_v||prevstate!={fullcone.u_f_3R01.u_e11.bank_free,fullcone.u_f_3R01.u_e11.sh_free,fullcone.u_f_3R01.u_e11.u_e.walk_busy,fullcone.u_f_3R01.u_e11.u_e.u_pq.walking,fullcone.u_f_3R01.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e11.u_e.u_pq.settle,fullcone.u_f_3R01.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e11.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q11 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e11.go,fullcone.u_f_3R01.u_e11.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e11.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e11.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e11.bank_free,fullcone.u_f_3R01.u_e11.sh_free,fullcone.u_f_3R01.u_e11.u_e.walk_busy,fullcone.u_f_3R01.u_e11.u_e.u_pq.walking,fullcone.u_f_3R01.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e11.u_e.u_pq.settle,fullcone.u_f_3R01.u_e11.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e11.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e11.cfg_v,fullcone.u_f_3R01.u_e11.cfg_a,fullcone.u_f_3R01.u_e11.cfg_d,fullcone.u_f_3R01.u_e11.u_e.u_pq.swap,fullcone.u_f_3R01.u_e11.fault);
   prevstate={fullcone.u_f_3R01.u_e11.bank_free,fullcone.u_f_3R01.u_e11.sh_free,fullcone.u_f_3R01.u_e11.u_e.walk_busy,fullcone.u_f_3R01.u_e11.u_e.u_pq.walking,fullcone.u_f_3R01.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e11.u_e.u_pq.settle,fullcone.u_f_3R01.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e11.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e11.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q11 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e11.pv,fullcone.u_f_3R01.u_e11.prow,fullcone.u_f_3R01.u_e11.pval,fullcone.u_f_3R01.u_e11.pseg,fullcone.u_f_3R01.u_e11.pnseg,fullcone.u_f_3R01.u_e11.perr,fullcone.u_f_3R01.u_e11.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q11 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e11.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q12
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e12.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e12.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e12.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s12.lc[0]||fullcone.u_f_3R01.u_s12.go_x||fullcone.u_f_3R01.u_s12.go_e||fullcone.u_f_3R01.u_s12.cfg[0]||fullcone.u_f_3R01.u_s12.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q12 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s12.lc,fullcone.u_f_3R01.u_s12.go_x,fullcone.u_f_3R01.u_s12.tag,fullcone.u_f_3R01.u_s12.go_e,fullcone.u_f_3R01.u_s12.go_tag,fullcone.u_f_3R01.u_s12.ef,fullcone.u_f_3R01.u_s12.st);
   if(fullcone.u_f_3R01.u_e12.go||oldgo||fullcone.u_f_3R01.u_e12.cfg_v||prevstate!={fullcone.u_f_3R01.u_e12.bank_free,fullcone.u_f_3R01.u_e12.sh_free,fullcone.u_f_3R01.u_e12.u_e.walk_busy,fullcone.u_f_3R01.u_e12.u_e.u_pq.walking,fullcone.u_f_3R01.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e12.u_e.u_pq.settle,fullcone.u_f_3R01.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e12.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q12 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e12.go,fullcone.u_f_3R01.u_e12.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e12.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e12.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e12.bank_free,fullcone.u_f_3R01.u_e12.sh_free,fullcone.u_f_3R01.u_e12.u_e.walk_busy,fullcone.u_f_3R01.u_e12.u_e.u_pq.walking,fullcone.u_f_3R01.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e12.u_e.u_pq.settle,fullcone.u_f_3R01.u_e12.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e12.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e12.cfg_v,fullcone.u_f_3R01.u_e12.cfg_a,fullcone.u_f_3R01.u_e12.cfg_d,fullcone.u_f_3R01.u_e12.u_e.u_pq.swap,fullcone.u_f_3R01.u_e12.fault);
   prevstate={fullcone.u_f_3R01.u_e12.bank_free,fullcone.u_f_3R01.u_e12.sh_free,fullcone.u_f_3R01.u_e12.u_e.walk_busy,fullcone.u_f_3R01.u_e12.u_e.u_pq.walking,fullcone.u_f_3R01.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e12.u_e.u_pq.settle,fullcone.u_f_3R01.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e12.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e12.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q12 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e12.pv,fullcone.u_f_3R01.u_e12.prow,fullcone.u_f_3R01.u_e12.pval,fullcone.u_f_3R01.u_e12.pseg,fullcone.u_f_3R01.u_e12.pnseg,fullcone.u_f_3R01.u_e12.perr,fullcone.u_f_3R01.u_e12.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q12 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e12.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q13
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e13.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e13.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e13.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s13.lc[0]||fullcone.u_f_3R01.u_s13.go_x||fullcone.u_f_3R01.u_s13.go_e||fullcone.u_f_3R01.u_s13.cfg[0]||fullcone.u_f_3R01.u_s13.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q13 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s13.lc,fullcone.u_f_3R01.u_s13.go_x,fullcone.u_f_3R01.u_s13.tag,fullcone.u_f_3R01.u_s13.go_e,fullcone.u_f_3R01.u_s13.go_tag,fullcone.u_f_3R01.u_s13.ef,fullcone.u_f_3R01.u_s13.st);
   if(fullcone.u_f_3R01.u_e13.go||oldgo||fullcone.u_f_3R01.u_e13.cfg_v||prevstate!={fullcone.u_f_3R01.u_e13.bank_free,fullcone.u_f_3R01.u_e13.sh_free,fullcone.u_f_3R01.u_e13.u_e.walk_busy,fullcone.u_f_3R01.u_e13.u_e.u_pq.walking,fullcone.u_f_3R01.u_e13.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e13.u_e.u_pq.settle,fullcone.u_f_3R01.u_e13.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e13.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e13.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e13.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q13 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e13.go,fullcone.u_f_3R01.u_e13.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e13.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e13.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e13.bank_free,fullcone.u_f_3R01.u_e13.sh_free,fullcone.u_f_3R01.u_e13.u_e.walk_busy,fullcone.u_f_3R01.u_e13.u_e.u_pq.walking,fullcone.u_f_3R01.u_e13.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e13.u_e.u_pq.settle,fullcone.u_f_3R01.u_e13.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e13.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e13.cfg_v,fullcone.u_f_3R01.u_e13.cfg_a,fullcone.u_f_3R01.u_e13.cfg_d,fullcone.u_f_3R01.u_e13.u_e.u_pq.swap,fullcone.u_f_3R01.u_e13.fault);
   prevstate={fullcone.u_f_3R01.u_e13.bank_free,fullcone.u_f_3R01.u_e13.sh_free,fullcone.u_f_3R01.u_e13.u_e.walk_busy,fullcone.u_f_3R01.u_e13.u_e.u_pq.walking,fullcone.u_f_3R01.u_e13.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e13.u_e.u_pq.settle,fullcone.u_f_3R01.u_e13.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e13.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e13.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e13.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e13.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q13 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e13.pv,fullcone.u_f_3R01.u_e13.prow,fullcone.u_f_3R01.u_e13.pval,fullcone.u_f_3R01.u_e13.pseg,fullcone.u_f_3R01.u_e13.pnseg,fullcone.u_f_3R01.u_e13.perr,fullcone.u_f_3R01.u_e13.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q13 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e13.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R01_q14
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R01.u_e14.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R01.u_e14.u_e.go_e;oldtag=fullcone.u_f_3R01.u_e14.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R01.u_s14.lc[0]||fullcone.u_f_3R01.u_s14.go_x||fullcone.u_f_3R01.u_s14.go_e||fullcone.u_f_3R01.u_s14.cfg[0]||fullcone.u_f_3R01.u_s14.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R01_q14 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R01.u_s14.lc,fullcone.u_f_3R01.u_s14.go_x,fullcone.u_f_3R01.u_s14.tag,fullcone.u_f_3R01.u_s14.go_e,fullcone.u_f_3R01.u_s14.go_tag,fullcone.u_f_3R01.u_s14.ef,fullcone.u_f_3R01.u_s14.st);
   if(fullcone.u_f_3R01.u_e14.go||oldgo||fullcone.u_f_3R01.u_e14.cfg_v||prevstate!={fullcone.u_f_3R01.u_e14.bank_free,fullcone.u_f_3R01.u_e14.sh_free,fullcone.u_f_3R01.u_e14.u_e.walk_busy,fullcone.u_f_3R01.u_e14.u_e.u_pq.walking,fullcone.u_f_3R01.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e14.u_e.u_pq.settle,fullcone.u_f_3R01.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e14.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R01_q14 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R01.u_e14.go,fullcone.u_f_3R01.u_e14.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R01.u_e14.u_e.u_pq.otag[0],fullcone.u_f_3R01.u_e14.u_e.u_pq.otag[1],fullcone.u_f_3R01.u_e14.bank_free,fullcone.u_f_3R01.u_e14.sh_free,fullcone.u_f_3R01.u_e14.u_e.walk_busy,fullcone.u_f_3R01.u_e14.u_e.u_pq.walking,fullcone.u_f_3R01.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e14.u_e.u_pq.settle,fullcone.u_f_3R01.u_e14.u_e.u_pq.gcnt[0],fullcone.u_f_3R01.u_e14.u_e.u_pq.gcnt[1],fullcone.u_f_3R01.u_e14.cfg_v,fullcone.u_f_3R01.u_e14.cfg_a,fullcone.u_f_3R01.u_e14.cfg_d,fullcone.u_f_3R01.u_e14.u_e.u_pq.swap,fullcone.u_f_3R01.u_e14.fault);
   prevstate={fullcone.u_f_3R01.u_e14.bank_free,fullcone.u_f_3R01.u_e14.sh_free,fullcone.u_f_3R01.u_e14.u_e.walk_busy,fullcone.u_f_3R01.u_e14.u_e.u_pq.walking,fullcone.u_f_3R01.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R01.u_e14.u_e.u_pq.settle,fullcone.u_f_3R01.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3R01.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R01.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R01.u_e14.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R01.u_e14.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R01_q14 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R01.u_e14.pv,fullcone.u_f_3R01.u_e14.prow,fullcone.u_f_3R01.u_e14.pval,fullcone.u_f_3R01.u_e14.pseg,fullcone.u_f_3R01.u_e14.pnseg,fullcone.u_f_3R01.u_e14.perr,fullcone.u_f_3R01.u_e14.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R01_q14 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R01.u_e14.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q0
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e0.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e0.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s0.lc[0]||fullcone.u_f_3R02.u_f.u_s0.go_x||fullcone.u_f_3R02.u_f.u_s0.go_e||fullcone.u_f_3R02.u_f.u_s0.cfg[0]||fullcone.u_f_3R02.u_f.u_s0.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q0 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s0.lc,fullcone.u_f_3R02.u_f.u_s0.go_x,fullcone.u_f_3R02.u_f.u_s0.tag,fullcone.u_f_3R02.u_f.u_s0.go_e,fullcone.u_f_3R02.u_f.u_s0.go_tag,fullcone.u_f_3R02.u_f.u_s0.ef,fullcone.u_f_3R02.u_f.u_s0.st);
   if(fullcone.u_f_3R02.u_f.u_e0.go||oldgo||fullcone.u_f_3R02.u_f.u_e0.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e0.bank_free,fullcone.u_f_3R02.u_f.u_e0.sh_free,fullcone.u_f_3R02.u_f.u_e0.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q0 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e0.go,fullcone.u_f_3R02.u_f.u_e0.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e0.bank_free,fullcone.u_f_3R02.u_f.u_e0.sh_free,fullcone.u_f_3R02.u_f.u_e0.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e0.cfg_v,fullcone.u_f_3R02.u_f.u_e0.cfg_a,fullcone.u_f_3R02.u_f.u_e0.cfg_d,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e0.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e0.bank_free,fullcone.u_f_3R02.u_f.u_e0.sh_free,fullcone.u_f_3R02.u_f.u_e0.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e0.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q0 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e0.pv,fullcone.u_f_3R02.u_f.u_e0.prow,fullcone.u_f_3R02.u_f.u_e0.pval,fullcone.u_f_3R02.u_f.u_e0.pseg,fullcone.u_f_3R02.u_f.u_e0.pnseg,fullcone.u_f_3R02.u_f.u_e0.perr,fullcone.u_f_3R02.u_f.u_e0.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q0 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e0.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q1
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e1.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e1.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s1.lc[0]||fullcone.u_f_3R02.u_f.u_s1.go_x||fullcone.u_f_3R02.u_f.u_s1.go_e||fullcone.u_f_3R02.u_f.u_s1.cfg[0]||fullcone.u_f_3R02.u_f.u_s1.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q1 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s1.lc,fullcone.u_f_3R02.u_f.u_s1.go_x,fullcone.u_f_3R02.u_f.u_s1.tag,fullcone.u_f_3R02.u_f.u_s1.go_e,fullcone.u_f_3R02.u_f.u_s1.go_tag,fullcone.u_f_3R02.u_f.u_s1.ef,fullcone.u_f_3R02.u_f.u_s1.st);
   if(fullcone.u_f_3R02.u_f.u_e1.go||oldgo||fullcone.u_f_3R02.u_f.u_e1.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e1.bank_free,fullcone.u_f_3R02.u_f.u_e1.sh_free,fullcone.u_f_3R02.u_f.u_e1.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q1 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e1.go,fullcone.u_f_3R02.u_f.u_e1.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e1.bank_free,fullcone.u_f_3R02.u_f.u_e1.sh_free,fullcone.u_f_3R02.u_f.u_e1.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e1.cfg_v,fullcone.u_f_3R02.u_f.u_e1.cfg_a,fullcone.u_f_3R02.u_f.u_e1.cfg_d,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e1.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e1.bank_free,fullcone.u_f_3R02.u_f.u_e1.sh_free,fullcone.u_f_3R02.u_f.u_e1.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e1.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q1 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e1.pv,fullcone.u_f_3R02.u_f.u_e1.prow,fullcone.u_f_3R02.u_f.u_e1.pval,fullcone.u_f_3R02.u_f.u_e1.pseg,fullcone.u_f_3R02.u_f.u_e1.pnseg,fullcone.u_f_3R02.u_f.u_e1.perr,fullcone.u_f_3R02.u_f.u_e1.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q1 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e1.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q2
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e2.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e2.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s2.lc[0]||fullcone.u_f_3R02.u_f.u_s2.go_x||fullcone.u_f_3R02.u_f.u_s2.go_e||fullcone.u_f_3R02.u_f.u_s2.cfg[0]||fullcone.u_f_3R02.u_f.u_s2.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q2 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s2.lc,fullcone.u_f_3R02.u_f.u_s2.go_x,fullcone.u_f_3R02.u_f.u_s2.tag,fullcone.u_f_3R02.u_f.u_s2.go_e,fullcone.u_f_3R02.u_f.u_s2.go_tag,fullcone.u_f_3R02.u_f.u_s2.ef,fullcone.u_f_3R02.u_f.u_s2.st);
   if(fullcone.u_f_3R02.u_f.u_e2.go||oldgo||fullcone.u_f_3R02.u_f.u_e2.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e2.bank_free,fullcone.u_f_3R02.u_f.u_e2.sh_free,fullcone.u_f_3R02.u_f.u_e2.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q2 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e2.go,fullcone.u_f_3R02.u_f.u_e2.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e2.bank_free,fullcone.u_f_3R02.u_f.u_e2.sh_free,fullcone.u_f_3R02.u_f.u_e2.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e2.cfg_v,fullcone.u_f_3R02.u_f.u_e2.cfg_a,fullcone.u_f_3R02.u_f.u_e2.cfg_d,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e2.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e2.bank_free,fullcone.u_f_3R02.u_f.u_e2.sh_free,fullcone.u_f_3R02.u_f.u_e2.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e2.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q2 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e2.pv,fullcone.u_f_3R02.u_f.u_e2.prow,fullcone.u_f_3R02.u_f.u_e2.pval,fullcone.u_f_3R02.u_f.u_e2.pseg,fullcone.u_f_3R02.u_f.u_e2.pnseg,fullcone.u_f_3R02.u_f.u_e2.perr,fullcone.u_f_3R02.u_f.u_e2.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q2 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e2.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q3
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e3.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e3.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s3.lc[0]||fullcone.u_f_3R02.u_f.u_s3.go_x||fullcone.u_f_3R02.u_f.u_s3.go_e||fullcone.u_f_3R02.u_f.u_s3.cfg[0]||fullcone.u_f_3R02.u_f.u_s3.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q3 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s3.lc,fullcone.u_f_3R02.u_f.u_s3.go_x,fullcone.u_f_3R02.u_f.u_s3.tag,fullcone.u_f_3R02.u_f.u_s3.go_e,fullcone.u_f_3R02.u_f.u_s3.go_tag,fullcone.u_f_3R02.u_f.u_s3.ef,fullcone.u_f_3R02.u_f.u_s3.st);
   if(fullcone.u_f_3R02.u_f.u_e3.go||oldgo||fullcone.u_f_3R02.u_f.u_e3.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e3.bank_free,fullcone.u_f_3R02.u_f.u_e3.sh_free,fullcone.u_f_3R02.u_f.u_e3.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q3 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e3.go,fullcone.u_f_3R02.u_f.u_e3.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e3.bank_free,fullcone.u_f_3R02.u_f.u_e3.sh_free,fullcone.u_f_3R02.u_f.u_e3.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e3.cfg_v,fullcone.u_f_3R02.u_f.u_e3.cfg_a,fullcone.u_f_3R02.u_f.u_e3.cfg_d,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e3.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e3.bank_free,fullcone.u_f_3R02.u_f.u_e3.sh_free,fullcone.u_f_3R02.u_f.u_e3.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e3.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q3 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e3.pv,fullcone.u_f_3R02.u_f.u_e3.prow,fullcone.u_f_3R02.u_f.u_e3.pval,fullcone.u_f_3R02.u_f.u_e3.pseg,fullcone.u_f_3R02.u_f.u_e3.pnseg,fullcone.u_f_3R02.u_f.u_e3.perr,fullcone.u_f_3R02.u_f.u_e3.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q3 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e3.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q5
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e5.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e5.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s5.lc[0]||fullcone.u_f_3R02.u_f.u_s5.go_x||fullcone.u_f_3R02.u_f.u_s5.go_e||fullcone.u_f_3R02.u_f.u_s5.cfg[0]||fullcone.u_f_3R02.u_f.u_s5.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q5 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s5.lc,fullcone.u_f_3R02.u_f.u_s5.go_x,fullcone.u_f_3R02.u_f.u_s5.tag,fullcone.u_f_3R02.u_f.u_s5.go_e,fullcone.u_f_3R02.u_f.u_s5.go_tag,fullcone.u_f_3R02.u_f.u_s5.ef,fullcone.u_f_3R02.u_f.u_s5.st);
   if(fullcone.u_f_3R02.u_f.u_e5.go||oldgo||fullcone.u_f_3R02.u_f.u_e5.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e5.bank_free,fullcone.u_f_3R02.u_f.u_e5.sh_free,fullcone.u_f_3R02.u_f.u_e5.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q5 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e5.go,fullcone.u_f_3R02.u_f.u_e5.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e5.bank_free,fullcone.u_f_3R02.u_f.u_e5.sh_free,fullcone.u_f_3R02.u_f.u_e5.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e5.cfg_v,fullcone.u_f_3R02.u_f.u_e5.cfg_a,fullcone.u_f_3R02.u_f.u_e5.cfg_d,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e5.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e5.bank_free,fullcone.u_f_3R02.u_f.u_e5.sh_free,fullcone.u_f_3R02.u_f.u_e5.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e5.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q5 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e5.pv,fullcone.u_f_3R02.u_f.u_e5.prow,fullcone.u_f_3R02.u_f.u_e5.pval,fullcone.u_f_3R02.u_f.u_e5.pseg,fullcone.u_f_3R02.u_f.u_e5.pnseg,fullcone.u_f_3R02.u_f.u_e5.perr,fullcone.u_f_3R02.u_f.u_e5.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q5 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e5.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q6
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e6.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e6.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s6.lc[0]||fullcone.u_f_3R02.u_f.u_s6.go_x||fullcone.u_f_3R02.u_f.u_s6.go_e||fullcone.u_f_3R02.u_f.u_s6.cfg[0]||fullcone.u_f_3R02.u_f.u_s6.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q6 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s6.lc,fullcone.u_f_3R02.u_f.u_s6.go_x,fullcone.u_f_3R02.u_f.u_s6.tag,fullcone.u_f_3R02.u_f.u_s6.go_e,fullcone.u_f_3R02.u_f.u_s6.go_tag,fullcone.u_f_3R02.u_f.u_s6.ef,fullcone.u_f_3R02.u_f.u_s6.st);
   if(fullcone.u_f_3R02.u_f.u_e6.go||oldgo||fullcone.u_f_3R02.u_f.u_e6.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e6.bank_free,fullcone.u_f_3R02.u_f.u_e6.sh_free,fullcone.u_f_3R02.u_f.u_e6.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q6 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e6.go,fullcone.u_f_3R02.u_f.u_e6.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e6.bank_free,fullcone.u_f_3R02.u_f.u_e6.sh_free,fullcone.u_f_3R02.u_f.u_e6.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e6.cfg_v,fullcone.u_f_3R02.u_f.u_e6.cfg_a,fullcone.u_f_3R02.u_f.u_e6.cfg_d,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e6.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e6.bank_free,fullcone.u_f_3R02.u_f.u_e6.sh_free,fullcone.u_f_3R02.u_f.u_e6.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e6.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q6 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e6.pv,fullcone.u_f_3R02.u_f.u_e6.prow,fullcone.u_f_3R02.u_f.u_e6.pval,fullcone.u_f_3R02.u_f.u_e6.pseg,fullcone.u_f_3R02.u_f.u_e6.pnseg,fullcone.u_f_3R02.u_f.u_e6.perr,fullcone.u_f_3R02.u_f.u_e6.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q6 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e6.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q7
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e7.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e7.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s7.lc[0]||fullcone.u_f_3R02.u_f.u_s7.go_x||fullcone.u_f_3R02.u_f.u_s7.go_e||fullcone.u_f_3R02.u_f.u_s7.cfg[0]||fullcone.u_f_3R02.u_f.u_s7.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q7 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s7.lc,fullcone.u_f_3R02.u_f.u_s7.go_x,fullcone.u_f_3R02.u_f.u_s7.tag,fullcone.u_f_3R02.u_f.u_s7.go_e,fullcone.u_f_3R02.u_f.u_s7.go_tag,fullcone.u_f_3R02.u_f.u_s7.ef,fullcone.u_f_3R02.u_f.u_s7.st);
   if(fullcone.u_f_3R02.u_f.u_e7.go||oldgo||fullcone.u_f_3R02.u_f.u_e7.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e7.bank_free,fullcone.u_f_3R02.u_f.u_e7.sh_free,fullcone.u_f_3R02.u_f.u_e7.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q7 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e7.go,fullcone.u_f_3R02.u_f.u_e7.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e7.bank_free,fullcone.u_f_3R02.u_f.u_e7.sh_free,fullcone.u_f_3R02.u_f.u_e7.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e7.cfg_v,fullcone.u_f_3R02.u_f.u_e7.cfg_a,fullcone.u_f_3R02.u_f.u_e7.cfg_d,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e7.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e7.bank_free,fullcone.u_f_3R02.u_f.u_e7.sh_free,fullcone.u_f_3R02.u_f.u_e7.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e7.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q7 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e7.pv,fullcone.u_f_3R02.u_f.u_e7.prow,fullcone.u_f_3R02.u_f.u_e7.pval,fullcone.u_f_3R02.u_f.u_e7.pseg,fullcone.u_f_3R02.u_f.u_e7.pnseg,fullcone.u_f_3R02.u_f.u_e7.perr,fullcone.u_f_3R02.u_f.u_e7.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q7 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e7.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q9
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e9.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e9.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s9.lc[0]||fullcone.u_f_3R02.u_f.u_s9.go_x||fullcone.u_f_3R02.u_f.u_s9.go_e||fullcone.u_f_3R02.u_f.u_s9.cfg[0]||fullcone.u_f_3R02.u_f.u_s9.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q9 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s9.lc,fullcone.u_f_3R02.u_f.u_s9.go_x,fullcone.u_f_3R02.u_f.u_s9.tag,fullcone.u_f_3R02.u_f.u_s9.go_e,fullcone.u_f_3R02.u_f.u_s9.go_tag,fullcone.u_f_3R02.u_f.u_s9.ef,fullcone.u_f_3R02.u_f.u_s9.st);
   if(fullcone.u_f_3R02.u_f.u_e9.go||oldgo||fullcone.u_f_3R02.u_f.u_e9.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e9.bank_free,fullcone.u_f_3R02.u_f.u_e9.sh_free,fullcone.u_f_3R02.u_f.u_e9.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q9 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e9.go,fullcone.u_f_3R02.u_f.u_e9.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e9.bank_free,fullcone.u_f_3R02.u_f.u_e9.sh_free,fullcone.u_f_3R02.u_f.u_e9.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e9.cfg_v,fullcone.u_f_3R02.u_f.u_e9.cfg_a,fullcone.u_f_3R02.u_f.u_e9.cfg_d,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e9.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e9.bank_free,fullcone.u_f_3R02.u_f.u_e9.sh_free,fullcone.u_f_3R02.u_f.u_e9.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e9.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q9 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e9.pv,fullcone.u_f_3R02.u_f.u_e9.prow,fullcone.u_f_3R02.u_f.u_e9.pval,fullcone.u_f_3R02.u_f.u_e9.pseg,fullcone.u_f_3R02.u_f.u_e9.pnseg,fullcone.u_f_3R02.u_f.u_e9.perr,fullcone.u_f_3R02.u_f.u_e9.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q9 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e9.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q10
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e10.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e10.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s10.lc[0]||fullcone.u_f_3R02.u_f.u_s10.go_x||fullcone.u_f_3R02.u_f.u_s10.go_e||fullcone.u_f_3R02.u_f.u_s10.cfg[0]||fullcone.u_f_3R02.u_f.u_s10.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q10 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s10.lc,fullcone.u_f_3R02.u_f.u_s10.go_x,fullcone.u_f_3R02.u_f.u_s10.tag,fullcone.u_f_3R02.u_f.u_s10.go_e,fullcone.u_f_3R02.u_f.u_s10.go_tag,fullcone.u_f_3R02.u_f.u_s10.ef,fullcone.u_f_3R02.u_f.u_s10.st);
   if(fullcone.u_f_3R02.u_f.u_e10.go||oldgo||fullcone.u_f_3R02.u_f.u_e10.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e10.bank_free,fullcone.u_f_3R02.u_f.u_e10.sh_free,fullcone.u_f_3R02.u_f.u_e10.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q10 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e10.go,fullcone.u_f_3R02.u_f.u_e10.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e10.bank_free,fullcone.u_f_3R02.u_f.u_e10.sh_free,fullcone.u_f_3R02.u_f.u_e10.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e10.cfg_v,fullcone.u_f_3R02.u_f.u_e10.cfg_a,fullcone.u_f_3R02.u_f.u_e10.cfg_d,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e10.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e10.bank_free,fullcone.u_f_3R02.u_f.u_e10.sh_free,fullcone.u_f_3R02.u_f.u_e10.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e10.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q10 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e10.pv,fullcone.u_f_3R02.u_f.u_e10.prow,fullcone.u_f_3R02.u_f.u_e10.pval,fullcone.u_f_3R02.u_f.u_e10.pseg,fullcone.u_f_3R02.u_f.u_e10.pnseg,fullcone.u_f_3R02.u_f.u_e10.perr,fullcone.u_f_3R02.u_f.u_e10.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q10 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e10.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q11
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e11.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e11.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s11.lc[0]||fullcone.u_f_3R02.u_f.u_s11.go_x||fullcone.u_f_3R02.u_f.u_s11.go_e||fullcone.u_f_3R02.u_f.u_s11.cfg[0]||fullcone.u_f_3R02.u_f.u_s11.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q11 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s11.lc,fullcone.u_f_3R02.u_f.u_s11.go_x,fullcone.u_f_3R02.u_f.u_s11.tag,fullcone.u_f_3R02.u_f.u_s11.go_e,fullcone.u_f_3R02.u_f.u_s11.go_tag,fullcone.u_f_3R02.u_f.u_s11.ef,fullcone.u_f_3R02.u_f.u_s11.st);
   if(fullcone.u_f_3R02.u_f.u_e11.go||oldgo||fullcone.u_f_3R02.u_f.u_e11.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e11.bank_free,fullcone.u_f_3R02.u_f.u_e11.sh_free,fullcone.u_f_3R02.u_f.u_e11.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q11 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e11.go,fullcone.u_f_3R02.u_f.u_e11.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e11.bank_free,fullcone.u_f_3R02.u_f.u_e11.sh_free,fullcone.u_f_3R02.u_f.u_e11.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e11.cfg_v,fullcone.u_f_3R02.u_f.u_e11.cfg_a,fullcone.u_f_3R02.u_f.u_e11.cfg_d,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e11.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e11.bank_free,fullcone.u_f_3R02.u_f.u_e11.sh_free,fullcone.u_f_3R02.u_f.u_e11.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e11.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q11 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e11.pv,fullcone.u_f_3R02.u_f.u_e11.prow,fullcone.u_f_3R02.u_f.u_e11.pval,fullcone.u_f_3R02.u_f.u_e11.pseg,fullcone.u_f_3R02.u_f.u_e11.pnseg,fullcone.u_f_3R02.u_f.u_e11.perr,fullcone.u_f_3R02.u_f.u_e11.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q11 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e11.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q12
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e12.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e12.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s12.lc[0]||fullcone.u_f_3R02.u_f.u_s12.go_x||fullcone.u_f_3R02.u_f.u_s12.go_e||fullcone.u_f_3R02.u_f.u_s12.cfg[0]||fullcone.u_f_3R02.u_f.u_s12.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q12 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s12.lc,fullcone.u_f_3R02.u_f.u_s12.go_x,fullcone.u_f_3R02.u_f.u_s12.tag,fullcone.u_f_3R02.u_f.u_s12.go_e,fullcone.u_f_3R02.u_f.u_s12.go_tag,fullcone.u_f_3R02.u_f.u_s12.ef,fullcone.u_f_3R02.u_f.u_s12.st);
   if(fullcone.u_f_3R02.u_f.u_e12.go||oldgo||fullcone.u_f_3R02.u_f.u_e12.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e12.bank_free,fullcone.u_f_3R02.u_f.u_e12.sh_free,fullcone.u_f_3R02.u_f.u_e12.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q12 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e12.go,fullcone.u_f_3R02.u_f.u_e12.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e12.bank_free,fullcone.u_f_3R02.u_f.u_e12.sh_free,fullcone.u_f_3R02.u_f.u_e12.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e12.cfg_v,fullcone.u_f_3R02.u_f.u_e12.cfg_a,fullcone.u_f_3R02.u_f.u_e12.cfg_d,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e12.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e12.bank_free,fullcone.u_f_3R02.u_f.u_e12.sh_free,fullcone.u_f_3R02.u_f.u_e12.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e12.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q12 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e12.pv,fullcone.u_f_3R02.u_f.u_e12.prow,fullcone.u_f_3R02.u_f.u_e12.pval,fullcone.u_f_3R02.u_f.u_e12.pseg,fullcone.u_f_3R02.u_f.u_e12.pnseg,fullcone.u_f_3R02.u_f.u_e12.perr,fullcone.u_f_3R02.u_f.u_e12.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q12 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e12.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R02_q14
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R02.u_f.u_e14.u_e.go_e;oldtag=fullcone.u_f_3R02.u_f.u_e14.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R02.u_f.u_s14.lc[0]||fullcone.u_f_3R02.u_f.u_s14.go_x||fullcone.u_f_3R02.u_f.u_s14.go_e||fullcone.u_f_3R02.u_f.u_s14.cfg[0]||fullcone.u_f_3R02.u_f.u_s14.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R02_q14 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_s14.lc,fullcone.u_f_3R02.u_f.u_s14.go_x,fullcone.u_f_3R02.u_f.u_s14.tag,fullcone.u_f_3R02.u_f.u_s14.go_e,fullcone.u_f_3R02.u_f.u_s14.go_tag,fullcone.u_f_3R02.u_f.u_s14.ef,fullcone.u_f_3R02.u_f.u_s14.st);
   if(fullcone.u_f_3R02.u_f.u_e14.go||oldgo||fullcone.u_f_3R02.u_f.u_e14.cfg_v||prevstate!={fullcone.u_f_3R02.u_f.u_e14.bank_free,fullcone.u_f_3R02.u_f.u_e14.sh_free,fullcone.u_f_3R02.u_f.u_e14.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R02_q14 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R02.u_f.u_e14.go,fullcone.u_f_3R02.u_f.u_e14.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.otag[0],fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.otag[1],fullcone.u_f_3R02.u_f.u_e14.bank_free,fullcone.u_f_3R02.u_f.u_e14.sh_free,fullcone.u_f_3R02.u_f.u_e14.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.gcnt[0],fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.gcnt[1],fullcone.u_f_3R02.u_f.u_e14.cfg_v,fullcone.u_f_3R02.u_f.u_e14.cfg_a,fullcone.u_f_3R02.u_f.u_e14.cfg_d,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.swap,fullcone.u_f_3R02.u_f.u_e14.fault);
   prevstate={fullcone.u_f_3R02.u_f.u_e14.bank_free,fullcone.u_f_3R02.u_f.u_e14.sh_free,fullcone.u_f_3R02.u_f.u_e14.u_e.walk_busy,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.walking,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.settle,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R02.u_f.u_e14.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R02_q14 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R02.u_f.u_e14.pv,fullcone.u_f_3R02.u_f.u_e14.prow,fullcone.u_f_3R02.u_f.u_e14.pval,fullcone.u_f_3R02.u_f.u_e14.pseg,fullcone.u_f_3R02.u_f.u_e14.pnseg,fullcone.u_f_3R02.u_f.u_e14.perr,fullcone.u_f_3R02.u_f.u_e14.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R02_q14 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R02.u_f.u_e14.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q0
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e0.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e0.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e0.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s0.lc[0]||fullcone.u_f_3R03.u_s0.go_x||fullcone.u_f_3R03.u_s0.go_e||fullcone.u_f_3R03.u_s0.cfg[0]||fullcone.u_f_3R03.u_s0.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q0 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s0.lc,fullcone.u_f_3R03.u_s0.go_x,fullcone.u_f_3R03.u_s0.tag,fullcone.u_f_3R03.u_s0.go_e,fullcone.u_f_3R03.u_s0.go_tag,fullcone.u_f_3R03.u_s0.ef,fullcone.u_f_3R03.u_s0.st);
   if(fullcone.u_f_3R03.u_e0.go||oldgo||fullcone.u_f_3R03.u_e0.cfg_v||prevstate!={fullcone.u_f_3R03.u_e0.bank_free,fullcone.u_f_3R03.u_e0.sh_free,fullcone.u_f_3R03.u_e0.u_e.walk_busy,fullcone.u_f_3R03.u_e0.u_e.u_pq.walking,fullcone.u_f_3R03.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e0.u_e.u_pq.settle,fullcone.u_f_3R03.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e0.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q0 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e0.go,fullcone.u_f_3R03.u_e0.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e0.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e0.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e0.bank_free,fullcone.u_f_3R03.u_e0.sh_free,fullcone.u_f_3R03.u_e0.u_e.walk_busy,fullcone.u_f_3R03.u_e0.u_e.u_pq.walking,fullcone.u_f_3R03.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e0.u_e.u_pq.settle,fullcone.u_f_3R03.u_e0.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e0.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e0.cfg_v,fullcone.u_f_3R03.u_e0.cfg_a,fullcone.u_f_3R03.u_e0.cfg_d,fullcone.u_f_3R03.u_e0.u_e.u_pq.swap,fullcone.u_f_3R03.u_e0.fault);
   prevstate={fullcone.u_f_3R03.u_e0.bank_free,fullcone.u_f_3R03.u_e0.sh_free,fullcone.u_f_3R03.u_e0.u_e.walk_busy,fullcone.u_f_3R03.u_e0.u_e.u_pq.walking,fullcone.u_f_3R03.u_e0.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e0.u_e.u_pq.settle,fullcone.u_f_3R03.u_e0.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e0.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e0.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e0.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e0.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q0 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e0.pv,fullcone.u_f_3R03.u_e0.prow,fullcone.u_f_3R03.u_e0.pval,fullcone.u_f_3R03.u_e0.pseg,fullcone.u_f_3R03.u_e0.pnseg,fullcone.u_f_3R03.u_e0.perr,fullcone.u_f_3R03.u_e0.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q0 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e0.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q1
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e1.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e1.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e1.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s1.lc[0]||fullcone.u_f_3R03.u_s1.go_x||fullcone.u_f_3R03.u_s1.go_e||fullcone.u_f_3R03.u_s1.cfg[0]||fullcone.u_f_3R03.u_s1.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q1 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s1.lc,fullcone.u_f_3R03.u_s1.go_x,fullcone.u_f_3R03.u_s1.tag,fullcone.u_f_3R03.u_s1.go_e,fullcone.u_f_3R03.u_s1.go_tag,fullcone.u_f_3R03.u_s1.ef,fullcone.u_f_3R03.u_s1.st);
   if(fullcone.u_f_3R03.u_e1.go||oldgo||fullcone.u_f_3R03.u_e1.cfg_v||prevstate!={fullcone.u_f_3R03.u_e1.bank_free,fullcone.u_f_3R03.u_e1.sh_free,fullcone.u_f_3R03.u_e1.u_e.walk_busy,fullcone.u_f_3R03.u_e1.u_e.u_pq.walking,fullcone.u_f_3R03.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e1.u_e.u_pq.settle,fullcone.u_f_3R03.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e1.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q1 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e1.go,fullcone.u_f_3R03.u_e1.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e1.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e1.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e1.bank_free,fullcone.u_f_3R03.u_e1.sh_free,fullcone.u_f_3R03.u_e1.u_e.walk_busy,fullcone.u_f_3R03.u_e1.u_e.u_pq.walking,fullcone.u_f_3R03.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e1.u_e.u_pq.settle,fullcone.u_f_3R03.u_e1.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e1.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e1.cfg_v,fullcone.u_f_3R03.u_e1.cfg_a,fullcone.u_f_3R03.u_e1.cfg_d,fullcone.u_f_3R03.u_e1.u_e.u_pq.swap,fullcone.u_f_3R03.u_e1.fault);
   prevstate={fullcone.u_f_3R03.u_e1.bank_free,fullcone.u_f_3R03.u_e1.sh_free,fullcone.u_f_3R03.u_e1.u_e.walk_busy,fullcone.u_f_3R03.u_e1.u_e.u_pq.walking,fullcone.u_f_3R03.u_e1.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e1.u_e.u_pq.settle,fullcone.u_f_3R03.u_e1.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e1.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e1.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e1.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e1.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q1 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e1.pv,fullcone.u_f_3R03.u_e1.prow,fullcone.u_f_3R03.u_e1.pval,fullcone.u_f_3R03.u_e1.pseg,fullcone.u_f_3R03.u_e1.pnseg,fullcone.u_f_3R03.u_e1.perr,fullcone.u_f_3R03.u_e1.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q1 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e1.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q2
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e2.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e2.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e2.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s2.lc[0]||fullcone.u_f_3R03.u_s2.go_x||fullcone.u_f_3R03.u_s2.go_e||fullcone.u_f_3R03.u_s2.cfg[0]||fullcone.u_f_3R03.u_s2.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q2 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s2.lc,fullcone.u_f_3R03.u_s2.go_x,fullcone.u_f_3R03.u_s2.tag,fullcone.u_f_3R03.u_s2.go_e,fullcone.u_f_3R03.u_s2.go_tag,fullcone.u_f_3R03.u_s2.ef,fullcone.u_f_3R03.u_s2.st);
   if(fullcone.u_f_3R03.u_e2.go||oldgo||fullcone.u_f_3R03.u_e2.cfg_v||prevstate!={fullcone.u_f_3R03.u_e2.bank_free,fullcone.u_f_3R03.u_e2.sh_free,fullcone.u_f_3R03.u_e2.u_e.walk_busy,fullcone.u_f_3R03.u_e2.u_e.u_pq.walking,fullcone.u_f_3R03.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e2.u_e.u_pq.settle,fullcone.u_f_3R03.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e2.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q2 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e2.go,fullcone.u_f_3R03.u_e2.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e2.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e2.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e2.bank_free,fullcone.u_f_3R03.u_e2.sh_free,fullcone.u_f_3R03.u_e2.u_e.walk_busy,fullcone.u_f_3R03.u_e2.u_e.u_pq.walking,fullcone.u_f_3R03.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e2.u_e.u_pq.settle,fullcone.u_f_3R03.u_e2.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e2.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e2.cfg_v,fullcone.u_f_3R03.u_e2.cfg_a,fullcone.u_f_3R03.u_e2.cfg_d,fullcone.u_f_3R03.u_e2.u_e.u_pq.swap,fullcone.u_f_3R03.u_e2.fault);
   prevstate={fullcone.u_f_3R03.u_e2.bank_free,fullcone.u_f_3R03.u_e2.sh_free,fullcone.u_f_3R03.u_e2.u_e.walk_busy,fullcone.u_f_3R03.u_e2.u_e.u_pq.walking,fullcone.u_f_3R03.u_e2.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e2.u_e.u_pq.settle,fullcone.u_f_3R03.u_e2.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e2.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e2.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e2.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e2.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q2 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e2.pv,fullcone.u_f_3R03.u_e2.prow,fullcone.u_f_3R03.u_e2.pval,fullcone.u_f_3R03.u_e2.pseg,fullcone.u_f_3R03.u_e2.pnseg,fullcone.u_f_3R03.u_e2.perr,fullcone.u_f_3R03.u_e2.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q2 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e2.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q3
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e3.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e3.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e3.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s3.lc[0]||fullcone.u_f_3R03.u_s3.go_x||fullcone.u_f_3R03.u_s3.go_e||fullcone.u_f_3R03.u_s3.cfg[0]||fullcone.u_f_3R03.u_s3.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q3 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s3.lc,fullcone.u_f_3R03.u_s3.go_x,fullcone.u_f_3R03.u_s3.tag,fullcone.u_f_3R03.u_s3.go_e,fullcone.u_f_3R03.u_s3.go_tag,fullcone.u_f_3R03.u_s3.ef,fullcone.u_f_3R03.u_s3.st);
   if(fullcone.u_f_3R03.u_e3.go||oldgo||fullcone.u_f_3R03.u_e3.cfg_v||prevstate!={fullcone.u_f_3R03.u_e3.bank_free,fullcone.u_f_3R03.u_e3.sh_free,fullcone.u_f_3R03.u_e3.u_e.walk_busy,fullcone.u_f_3R03.u_e3.u_e.u_pq.walking,fullcone.u_f_3R03.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e3.u_e.u_pq.settle,fullcone.u_f_3R03.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e3.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q3 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e3.go,fullcone.u_f_3R03.u_e3.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e3.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e3.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e3.bank_free,fullcone.u_f_3R03.u_e3.sh_free,fullcone.u_f_3R03.u_e3.u_e.walk_busy,fullcone.u_f_3R03.u_e3.u_e.u_pq.walking,fullcone.u_f_3R03.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e3.u_e.u_pq.settle,fullcone.u_f_3R03.u_e3.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e3.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e3.cfg_v,fullcone.u_f_3R03.u_e3.cfg_a,fullcone.u_f_3R03.u_e3.cfg_d,fullcone.u_f_3R03.u_e3.u_e.u_pq.swap,fullcone.u_f_3R03.u_e3.fault);
   prevstate={fullcone.u_f_3R03.u_e3.bank_free,fullcone.u_f_3R03.u_e3.sh_free,fullcone.u_f_3R03.u_e3.u_e.walk_busy,fullcone.u_f_3R03.u_e3.u_e.u_pq.walking,fullcone.u_f_3R03.u_e3.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e3.u_e.u_pq.settle,fullcone.u_f_3R03.u_e3.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e3.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e3.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e3.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e3.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q3 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e3.pv,fullcone.u_f_3R03.u_e3.prow,fullcone.u_f_3R03.u_e3.pval,fullcone.u_f_3R03.u_e3.pseg,fullcone.u_f_3R03.u_e3.pnseg,fullcone.u_f_3R03.u_e3.perr,fullcone.u_f_3R03.u_e3.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q3 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e3.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q5
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e5.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e5.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e5.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s5.lc[0]||fullcone.u_f_3R03.u_s5.go_x||fullcone.u_f_3R03.u_s5.go_e||fullcone.u_f_3R03.u_s5.cfg[0]||fullcone.u_f_3R03.u_s5.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q5 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s5.lc,fullcone.u_f_3R03.u_s5.go_x,fullcone.u_f_3R03.u_s5.tag,fullcone.u_f_3R03.u_s5.go_e,fullcone.u_f_3R03.u_s5.go_tag,fullcone.u_f_3R03.u_s5.ef,fullcone.u_f_3R03.u_s5.st);
   if(fullcone.u_f_3R03.u_e5.go||oldgo||fullcone.u_f_3R03.u_e5.cfg_v||prevstate!={fullcone.u_f_3R03.u_e5.bank_free,fullcone.u_f_3R03.u_e5.sh_free,fullcone.u_f_3R03.u_e5.u_e.walk_busy,fullcone.u_f_3R03.u_e5.u_e.u_pq.walking,fullcone.u_f_3R03.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e5.u_e.u_pq.settle,fullcone.u_f_3R03.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e5.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q5 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e5.go,fullcone.u_f_3R03.u_e5.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e5.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e5.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e5.bank_free,fullcone.u_f_3R03.u_e5.sh_free,fullcone.u_f_3R03.u_e5.u_e.walk_busy,fullcone.u_f_3R03.u_e5.u_e.u_pq.walking,fullcone.u_f_3R03.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e5.u_e.u_pq.settle,fullcone.u_f_3R03.u_e5.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e5.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e5.cfg_v,fullcone.u_f_3R03.u_e5.cfg_a,fullcone.u_f_3R03.u_e5.cfg_d,fullcone.u_f_3R03.u_e5.u_e.u_pq.swap,fullcone.u_f_3R03.u_e5.fault);
   prevstate={fullcone.u_f_3R03.u_e5.bank_free,fullcone.u_f_3R03.u_e5.sh_free,fullcone.u_f_3R03.u_e5.u_e.walk_busy,fullcone.u_f_3R03.u_e5.u_e.u_pq.walking,fullcone.u_f_3R03.u_e5.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e5.u_e.u_pq.settle,fullcone.u_f_3R03.u_e5.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e5.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e5.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e5.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e5.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q5 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e5.pv,fullcone.u_f_3R03.u_e5.prow,fullcone.u_f_3R03.u_e5.pval,fullcone.u_f_3R03.u_e5.pseg,fullcone.u_f_3R03.u_e5.pnseg,fullcone.u_f_3R03.u_e5.perr,fullcone.u_f_3R03.u_e5.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q5 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e5.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q6
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e6.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e6.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e6.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s6.lc[0]||fullcone.u_f_3R03.u_s6.go_x||fullcone.u_f_3R03.u_s6.go_e||fullcone.u_f_3R03.u_s6.cfg[0]||fullcone.u_f_3R03.u_s6.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q6 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s6.lc,fullcone.u_f_3R03.u_s6.go_x,fullcone.u_f_3R03.u_s6.tag,fullcone.u_f_3R03.u_s6.go_e,fullcone.u_f_3R03.u_s6.go_tag,fullcone.u_f_3R03.u_s6.ef,fullcone.u_f_3R03.u_s6.st);
   if(fullcone.u_f_3R03.u_e6.go||oldgo||fullcone.u_f_3R03.u_e6.cfg_v||prevstate!={fullcone.u_f_3R03.u_e6.bank_free,fullcone.u_f_3R03.u_e6.sh_free,fullcone.u_f_3R03.u_e6.u_e.walk_busy,fullcone.u_f_3R03.u_e6.u_e.u_pq.walking,fullcone.u_f_3R03.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e6.u_e.u_pq.settle,fullcone.u_f_3R03.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e6.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q6 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e6.go,fullcone.u_f_3R03.u_e6.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e6.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e6.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e6.bank_free,fullcone.u_f_3R03.u_e6.sh_free,fullcone.u_f_3R03.u_e6.u_e.walk_busy,fullcone.u_f_3R03.u_e6.u_e.u_pq.walking,fullcone.u_f_3R03.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e6.u_e.u_pq.settle,fullcone.u_f_3R03.u_e6.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e6.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e6.cfg_v,fullcone.u_f_3R03.u_e6.cfg_a,fullcone.u_f_3R03.u_e6.cfg_d,fullcone.u_f_3R03.u_e6.u_e.u_pq.swap,fullcone.u_f_3R03.u_e6.fault);
   prevstate={fullcone.u_f_3R03.u_e6.bank_free,fullcone.u_f_3R03.u_e6.sh_free,fullcone.u_f_3R03.u_e6.u_e.walk_busy,fullcone.u_f_3R03.u_e6.u_e.u_pq.walking,fullcone.u_f_3R03.u_e6.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e6.u_e.u_pq.settle,fullcone.u_f_3R03.u_e6.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e6.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e6.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e6.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e6.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q6 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e6.pv,fullcone.u_f_3R03.u_e6.prow,fullcone.u_f_3R03.u_e6.pval,fullcone.u_f_3R03.u_e6.pseg,fullcone.u_f_3R03.u_e6.pnseg,fullcone.u_f_3R03.u_e6.perr,fullcone.u_f_3R03.u_e6.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q6 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e6.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q7
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e7.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e7.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e7.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s7.lc[0]||fullcone.u_f_3R03.u_s7.go_x||fullcone.u_f_3R03.u_s7.go_e||fullcone.u_f_3R03.u_s7.cfg[0]||fullcone.u_f_3R03.u_s7.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q7 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s7.lc,fullcone.u_f_3R03.u_s7.go_x,fullcone.u_f_3R03.u_s7.tag,fullcone.u_f_3R03.u_s7.go_e,fullcone.u_f_3R03.u_s7.go_tag,fullcone.u_f_3R03.u_s7.ef,fullcone.u_f_3R03.u_s7.st);
   if(fullcone.u_f_3R03.u_e7.go||oldgo||fullcone.u_f_3R03.u_e7.cfg_v||prevstate!={fullcone.u_f_3R03.u_e7.bank_free,fullcone.u_f_3R03.u_e7.sh_free,fullcone.u_f_3R03.u_e7.u_e.walk_busy,fullcone.u_f_3R03.u_e7.u_e.u_pq.walking,fullcone.u_f_3R03.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e7.u_e.u_pq.settle,fullcone.u_f_3R03.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e7.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q7 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e7.go,fullcone.u_f_3R03.u_e7.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e7.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e7.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e7.bank_free,fullcone.u_f_3R03.u_e7.sh_free,fullcone.u_f_3R03.u_e7.u_e.walk_busy,fullcone.u_f_3R03.u_e7.u_e.u_pq.walking,fullcone.u_f_3R03.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e7.u_e.u_pq.settle,fullcone.u_f_3R03.u_e7.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e7.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e7.cfg_v,fullcone.u_f_3R03.u_e7.cfg_a,fullcone.u_f_3R03.u_e7.cfg_d,fullcone.u_f_3R03.u_e7.u_e.u_pq.swap,fullcone.u_f_3R03.u_e7.fault);
   prevstate={fullcone.u_f_3R03.u_e7.bank_free,fullcone.u_f_3R03.u_e7.sh_free,fullcone.u_f_3R03.u_e7.u_e.walk_busy,fullcone.u_f_3R03.u_e7.u_e.u_pq.walking,fullcone.u_f_3R03.u_e7.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e7.u_e.u_pq.settle,fullcone.u_f_3R03.u_e7.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e7.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e7.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e7.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e7.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q7 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e7.pv,fullcone.u_f_3R03.u_e7.prow,fullcone.u_f_3R03.u_e7.pval,fullcone.u_f_3R03.u_e7.pseg,fullcone.u_f_3R03.u_e7.pnseg,fullcone.u_f_3R03.u_e7.perr,fullcone.u_f_3R03.u_e7.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q7 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e7.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q9
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e9.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e9.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e9.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s9.lc[0]||fullcone.u_f_3R03.u_s9.go_x||fullcone.u_f_3R03.u_s9.go_e||fullcone.u_f_3R03.u_s9.cfg[0]||fullcone.u_f_3R03.u_s9.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q9 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s9.lc,fullcone.u_f_3R03.u_s9.go_x,fullcone.u_f_3R03.u_s9.tag,fullcone.u_f_3R03.u_s9.go_e,fullcone.u_f_3R03.u_s9.go_tag,fullcone.u_f_3R03.u_s9.ef,fullcone.u_f_3R03.u_s9.st);
   if(fullcone.u_f_3R03.u_e9.go||oldgo||fullcone.u_f_3R03.u_e9.cfg_v||prevstate!={fullcone.u_f_3R03.u_e9.bank_free,fullcone.u_f_3R03.u_e9.sh_free,fullcone.u_f_3R03.u_e9.u_e.walk_busy,fullcone.u_f_3R03.u_e9.u_e.u_pq.walking,fullcone.u_f_3R03.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e9.u_e.u_pq.settle,fullcone.u_f_3R03.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e9.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q9 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e9.go,fullcone.u_f_3R03.u_e9.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e9.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e9.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e9.bank_free,fullcone.u_f_3R03.u_e9.sh_free,fullcone.u_f_3R03.u_e9.u_e.walk_busy,fullcone.u_f_3R03.u_e9.u_e.u_pq.walking,fullcone.u_f_3R03.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e9.u_e.u_pq.settle,fullcone.u_f_3R03.u_e9.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e9.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e9.cfg_v,fullcone.u_f_3R03.u_e9.cfg_a,fullcone.u_f_3R03.u_e9.cfg_d,fullcone.u_f_3R03.u_e9.u_e.u_pq.swap,fullcone.u_f_3R03.u_e9.fault);
   prevstate={fullcone.u_f_3R03.u_e9.bank_free,fullcone.u_f_3R03.u_e9.sh_free,fullcone.u_f_3R03.u_e9.u_e.walk_busy,fullcone.u_f_3R03.u_e9.u_e.u_pq.walking,fullcone.u_f_3R03.u_e9.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e9.u_e.u_pq.settle,fullcone.u_f_3R03.u_e9.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e9.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e9.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e9.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e9.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q9 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e9.pv,fullcone.u_f_3R03.u_e9.prow,fullcone.u_f_3R03.u_e9.pval,fullcone.u_f_3R03.u_e9.pseg,fullcone.u_f_3R03.u_e9.pnseg,fullcone.u_f_3R03.u_e9.perr,fullcone.u_f_3R03.u_e9.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q9 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e9.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q10
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e10.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e10.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e10.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s10.lc[0]||fullcone.u_f_3R03.u_s10.go_x||fullcone.u_f_3R03.u_s10.go_e||fullcone.u_f_3R03.u_s10.cfg[0]||fullcone.u_f_3R03.u_s10.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q10 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s10.lc,fullcone.u_f_3R03.u_s10.go_x,fullcone.u_f_3R03.u_s10.tag,fullcone.u_f_3R03.u_s10.go_e,fullcone.u_f_3R03.u_s10.go_tag,fullcone.u_f_3R03.u_s10.ef,fullcone.u_f_3R03.u_s10.st);
   if(fullcone.u_f_3R03.u_e10.go||oldgo||fullcone.u_f_3R03.u_e10.cfg_v||prevstate!={fullcone.u_f_3R03.u_e10.bank_free,fullcone.u_f_3R03.u_e10.sh_free,fullcone.u_f_3R03.u_e10.u_e.walk_busy,fullcone.u_f_3R03.u_e10.u_e.u_pq.walking,fullcone.u_f_3R03.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e10.u_e.u_pq.settle,fullcone.u_f_3R03.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e10.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q10 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e10.go,fullcone.u_f_3R03.u_e10.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e10.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e10.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e10.bank_free,fullcone.u_f_3R03.u_e10.sh_free,fullcone.u_f_3R03.u_e10.u_e.walk_busy,fullcone.u_f_3R03.u_e10.u_e.u_pq.walking,fullcone.u_f_3R03.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e10.u_e.u_pq.settle,fullcone.u_f_3R03.u_e10.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e10.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e10.cfg_v,fullcone.u_f_3R03.u_e10.cfg_a,fullcone.u_f_3R03.u_e10.cfg_d,fullcone.u_f_3R03.u_e10.u_e.u_pq.swap,fullcone.u_f_3R03.u_e10.fault);
   prevstate={fullcone.u_f_3R03.u_e10.bank_free,fullcone.u_f_3R03.u_e10.sh_free,fullcone.u_f_3R03.u_e10.u_e.walk_busy,fullcone.u_f_3R03.u_e10.u_e.u_pq.walking,fullcone.u_f_3R03.u_e10.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e10.u_e.u_pq.settle,fullcone.u_f_3R03.u_e10.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e10.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e10.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e10.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e10.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q10 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e10.pv,fullcone.u_f_3R03.u_e10.prow,fullcone.u_f_3R03.u_e10.pval,fullcone.u_f_3R03.u_e10.pseg,fullcone.u_f_3R03.u_e10.pnseg,fullcone.u_f_3R03.u_e10.perr,fullcone.u_f_3R03.u_e10.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q10 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e10.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q11
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e11.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e11.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e11.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s11.lc[0]||fullcone.u_f_3R03.u_s11.go_x||fullcone.u_f_3R03.u_s11.go_e||fullcone.u_f_3R03.u_s11.cfg[0]||fullcone.u_f_3R03.u_s11.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q11 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s11.lc,fullcone.u_f_3R03.u_s11.go_x,fullcone.u_f_3R03.u_s11.tag,fullcone.u_f_3R03.u_s11.go_e,fullcone.u_f_3R03.u_s11.go_tag,fullcone.u_f_3R03.u_s11.ef,fullcone.u_f_3R03.u_s11.st);
   if(fullcone.u_f_3R03.u_e11.go||oldgo||fullcone.u_f_3R03.u_e11.cfg_v||prevstate!={fullcone.u_f_3R03.u_e11.bank_free,fullcone.u_f_3R03.u_e11.sh_free,fullcone.u_f_3R03.u_e11.u_e.walk_busy,fullcone.u_f_3R03.u_e11.u_e.u_pq.walking,fullcone.u_f_3R03.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e11.u_e.u_pq.settle,fullcone.u_f_3R03.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e11.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q11 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e11.go,fullcone.u_f_3R03.u_e11.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e11.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e11.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e11.bank_free,fullcone.u_f_3R03.u_e11.sh_free,fullcone.u_f_3R03.u_e11.u_e.walk_busy,fullcone.u_f_3R03.u_e11.u_e.u_pq.walking,fullcone.u_f_3R03.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e11.u_e.u_pq.settle,fullcone.u_f_3R03.u_e11.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e11.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e11.cfg_v,fullcone.u_f_3R03.u_e11.cfg_a,fullcone.u_f_3R03.u_e11.cfg_d,fullcone.u_f_3R03.u_e11.u_e.u_pq.swap,fullcone.u_f_3R03.u_e11.fault);
   prevstate={fullcone.u_f_3R03.u_e11.bank_free,fullcone.u_f_3R03.u_e11.sh_free,fullcone.u_f_3R03.u_e11.u_e.walk_busy,fullcone.u_f_3R03.u_e11.u_e.u_pq.walking,fullcone.u_f_3R03.u_e11.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e11.u_e.u_pq.settle,fullcone.u_f_3R03.u_e11.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e11.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e11.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e11.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e11.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q11 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e11.pv,fullcone.u_f_3R03.u_e11.prow,fullcone.u_f_3R03.u_e11.pval,fullcone.u_f_3R03.u_e11.pseg,fullcone.u_f_3R03.u_e11.pnseg,fullcone.u_f_3R03.u_e11.perr,fullcone.u_f_3R03.u_e11.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q11 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e11.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q12
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e12.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e12.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e12.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s12.lc[0]||fullcone.u_f_3R03.u_s12.go_x||fullcone.u_f_3R03.u_s12.go_e||fullcone.u_f_3R03.u_s12.cfg[0]||fullcone.u_f_3R03.u_s12.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q12 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s12.lc,fullcone.u_f_3R03.u_s12.go_x,fullcone.u_f_3R03.u_s12.tag,fullcone.u_f_3R03.u_s12.go_e,fullcone.u_f_3R03.u_s12.go_tag,fullcone.u_f_3R03.u_s12.ef,fullcone.u_f_3R03.u_s12.st);
   if(fullcone.u_f_3R03.u_e12.go||oldgo||fullcone.u_f_3R03.u_e12.cfg_v||prevstate!={fullcone.u_f_3R03.u_e12.bank_free,fullcone.u_f_3R03.u_e12.sh_free,fullcone.u_f_3R03.u_e12.u_e.walk_busy,fullcone.u_f_3R03.u_e12.u_e.u_pq.walking,fullcone.u_f_3R03.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e12.u_e.u_pq.settle,fullcone.u_f_3R03.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e12.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q12 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e12.go,fullcone.u_f_3R03.u_e12.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e12.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e12.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e12.bank_free,fullcone.u_f_3R03.u_e12.sh_free,fullcone.u_f_3R03.u_e12.u_e.walk_busy,fullcone.u_f_3R03.u_e12.u_e.u_pq.walking,fullcone.u_f_3R03.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e12.u_e.u_pq.settle,fullcone.u_f_3R03.u_e12.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e12.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e12.cfg_v,fullcone.u_f_3R03.u_e12.cfg_a,fullcone.u_f_3R03.u_e12.cfg_d,fullcone.u_f_3R03.u_e12.u_e.u_pq.swap,fullcone.u_f_3R03.u_e12.fault);
   prevstate={fullcone.u_f_3R03.u_e12.bank_free,fullcone.u_f_3R03.u_e12.sh_free,fullcone.u_f_3R03.u_e12.u_e.walk_busy,fullcone.u_f_3R03.u_e12.u_e.u_pq.walking,fullcone.u_f_3R03.u_e12.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e12.u_e.u_pq.settle,fullcone.u_f_3R03.u_e12.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e12.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e12.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e12.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e12.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q12 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e12.pv,fullcone.u_f_3R03.u_e12.prow,fullcone.u_f_3R03.u_e12.pval,fullcone.u_f_3R03.u_e12.pseg,fullcone.u_f_3R03.u_e12.pnseg,fullcone.u_f_3R03.u_e12.perr,fullcone.u_f_3R03.u_e12.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q12 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e12.u_e.u_pq.otag[oldbank]);
 end
end
if (1) begin:observe_u_f_3R03_q14
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank=fullcone.u_f_3R03.u_e14.u_e.u_pq.wbank;oldgo=fullcone.u_f_3R03.u_e14.u_e.go_e;oldtag=fullcone.u_f_3R03.u_e14.u_e.go_tag_e;
  if(rst_n)begin
   if(fullcone.u_f_3R03.u_s14.lc[0]||fullcone.u_f_3R03.u_s14.go_x||fullcone.u_f_3R03.u_s14.go_e||fullcone.u_f_3R03.u_s14.cfg[0]||fullcone.u_f_3R03.u_s14.st!=0)
    $display("CFG7_TRACE t=%0d id=u_f_3R03_q14 lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,fullcone.u_f_3R03.u_s14.lc,fullcone.u_f_3R03.u_s14.go_x,fullcone.u_f_3R03.u_s14.tag,fullcone.u_f_3R03.u_s14.go_e,fullcone.u_f_3R03.u_s14.go_tag,fullcone.u_f_3R03.u_s14.ef,fullcone.u_f_3R03.u_s14.st);
   if(fullcone.u_f_3R03.u_e14.go||oldgo||fullcone.u_f_3R03.u_e14.cfg_v||prevstate!={fullcone.u_f_3R03.u_e14.bank_free,fullcone.u_f_3R03.u_e14.sh_free,fullcone.u_f_3R03.u_e14.u_e.walk_busy,fullcone.u_f_3R03.u_e14.u_e.u_pq.walking,fullcone.u_f_3R03.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e14.u_e.u_pq.settle,fullcone.u_f_3R03.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e14.u_e.u_pq.fault,4'd0})
    $display("Q_LIFETIME t=%0d id=u_f_3R03_q14 go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    fullcone.u_f_3R03.u_e14.go,fullcone.u_f_3R03.u_e14.go_tag,oldgo,oldtag,oldbank,fullcone.u_f_3R03.u_e14.u_e.u_pq.otag[0],fullcone.u_f_3R03.u_e14.u_e.u_pq.otag[1],fullcone.u_f_3R03.u_e14.bank_free,fullcone.u_f_3R03.u_e14.sh_free,fullcone.u_f_3R03.u_e14.u_e.walk_busy,fullcone.u_f_3R03.u_e14.u_e.u_pq.walking,fullcone.u_f_3R03.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e14.u_e.u_pq.settle,fullcone.u_f_3R03.u_e14.u_e.u_pq.gcnt[0],fullcone.u_f_3R03.u_e14.u_e.u_pq.gcnt[1],fullcone.u_f_3R03.u_e14.cfg_v,fullcone.u_f_3R03.u_e14.cfg_a,fullcone.u_f_3R03.u_e14.cfg_d,fullcone.u_f_3R03.u_e14.u_e.u_pq.swap,fullcone.u_f_3R03.u_e14.fault);
   prevstate={fullcone.u_f_3R03.u_e14.bank_free,fullcone.u_f_3R03.u_e14.sh_free,fullcone.u_f_3R03.u_e14.u_e.walk_busy,fullcone.u_f_3R03.u_e14.u_e.u_pq.walking,fullcone.u_f_3R03.u_e14.u_e.u_pq.sh_full,fullcone.u_f_3R03.u_e14.u_e.u_pq.settle,fullcone.u_f_3R03.u_e14.u_e.u_pq.wbank,(fullcone.u_f_3R03.u_e14.u_e.u_pq.gcnt[0]==0),(fullcone.u_f_3R03.u_e14.u_e.u_pq.gcnt[1]==0),fullcone.u_f_3R03.u_e14.u_e.u_pq.fault,4'd0};
   if(|fullcone.u_f_3R03.u_e14.pv)$display("ACTUAL_PAIR_PV t=%0d id=u_f_3R03_q14 valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,fullcone.u_f_3R03.u_e14.pv,fullcone.u_f_3R03.u_e14.prow,fullcone.u_f_3R03.u_e14.pval,fullcone.u_f_3R03.u_e14.pseg,fullcone.u_f_3R03.u_e14.pnseg,fullcone.u_f_3R03.u_e14.perr,fullcone.u_f_3R03.u_e14.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id=u_f_3R03_q14 bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,fullcone.u_f_3R03.u_e14.u_e.u_pq.otag[oldbank]);
 end
end
endmodule
