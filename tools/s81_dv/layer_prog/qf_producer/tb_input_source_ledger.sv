`timescale 1ps/1ps
// Private raw-qnorm source: original FP32 CTLs only; no g/return/Q stimulus.
module tb_input_source_ledger;
reg clk=0,rst_n=0;always #417 clk=~clk;
integer n=-1,err=0,nq=0,nw=0,mut=0;localparam integer ORIGIN=32;
reg ev=0;reg [1103:0] eb=0;wire fx,fp,fs,fq,fr,fxs;
reg [185:0] ctl[0:12000];reg [12000:0] ctlv=0;reg [531:0] gold[0:19];
string dir;integer fd,rc,at;reg [185:0] payload;
wire [4:0] cv,swv;wire [159:0] cd;wire [49:0] swa;wire [39:0] swm;wire [1279:0] swd;
wire is_v;wire [159:0] is_d;wire [2:0] cid;wire [1103:0] cib;
wire lo_v;wire [255:0] lo_d;wire lov;wire [255:0] lod;
ot_s81sl_xr #(.HB(1)) xr(.clk(clk),.rst_n(rst_n),.sid(4'd6),.dl_ev(ev),.dl_e(eb),
 .dl_wv(1'b0),.dl_w(1104'd0),.dl_vv(1'b0),.dl_vb(276'd0),.ci_dir(cid),.ci_b(cib),
 .bi(1104'd0),.bo(),.c_v(cv),.c_d(cd),.sw_v(swv),.sw_a(swa),.sw_m(swm),.sw_d(swd),
 .lo_v({2'd0,lov,2'd0}),.lo_d({512'd0,lod,512'd0}),.p_v(5'd0),.p_d(160'd0),
 .e_v(5'd0),.e_c(10'd0),.e_d(480'd0),.eg_v(1'b0),.eg_c(2'd0),.eg_d(32'd0),
 .x_rbv(1'b0),.x_rbd(32'd0),.is_v(is_v),.is_d(is_d),.fault(fx));
wire c_v,sw_v;wire[159:0]c_d;wire[9:0]sw_a;wire[7:0]sw_m;wire[255:0]sw_d;
ot_s81sl_rly #(.W(436),.D(4)) dn(.clk(clk),
 .d({cv[2],cd,swv[2],swa[20+:10],swm[16+:8],swd[512+:256]}),
 .q({c_v,c_d,sw_v,sw_a,sw_m,sw_d}));
ot_s81sl_rly #(.W(257),.D(4)) up_lo(.clk(clk),.d({lo_v,lo_d}),.q({lov,lod}));
wire s_v;wire[159:0]s_d;wire x_rv,x_qv,x_wv;wire[9:0]x_ra,x_wa;wire[7:0]x_wm;wire[255:0]x_qd,x_wd;
wire u_v,um_v,um_q,um_b;wire[2:0]u_i;wire[255:0]u;wire[7:0]um_i;
wire swv_,swvi,swfi;wire[255:0]swd_;wire[31:0]sww,swl;wire[63:0]swri;
wire rav,ravi,rafi,rfv,rff;wire[31:0]rax,rfmx;wire[30:0]rfu,rfu2,rari;
wire mv,mq,mb;wire[7:0]mi;
    ot_s81sl_vp u_p (.clk(clk), .rst_n(rst_n), .c_v(c_v), .c_d(c_d), .sw_v(sw_v), .sw_a(sw_a), .sw_m(sw_m), .sw_d(sw_d),
        .cw_v(2'b00), .cw_a(24'd0), .cw_d(64'd0), .lo_v(lo_v), .lo_d(lo_d),
        .s_v(s_v), .s_d(s_d), .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .hw_v(), .hw_j(), .hw_hf(), .hw_d(), .hr_v(), .hr_j(), .hr_hf(), .hq_v(1'b0), .hq_d(256'd0),
        .n_go(), .n_pre(), .m_v(mv), .m_q(mq), .m_b(mb), .m_i(mi), .wl_v(), .wl_i(), .wl_d(), .fault(fp));
    ot_s81sl_vs #(.MUT(0)) u_s (.clk(clk), .rst_n(rst_n), .s_v(s_v), .s_d({s_d[159:64], s_d[62], s_d[60:0]}),
        .x_rv(x_rv), .x_ra(x_ra), .x_qv(x_qv), .x_qd(x_qd), .x_wv(x_wv), .x_wa(x_wa), .x_wm(x_wm), .x_wd(x_wd),
        .u_v(u_v), .u_i(u_i), .u(u), .um_v(um_v), .um_q(um_q), .um_b(um_b), .um_i(um_i),
        .sw_v(swv_), .sw_d(swd_), .sw_w(sww), .sw_lim(swl), .sw_vi(swvi), .sw_ri(swri), .sw_fi(swfi),
        .ra_v(rav), .ra_x(rax), .ra_vi(ravi), .ra_ri(rari), .ra_fi(rafi),
        .ve_rv(),.ve_rc(),.ve_rh(),.ve_rk(),.ve_rw(),.ve_pv(1'b0),.ve_pc(2'd0),.ve_phh(32'd0),.ve_pkk(32'd0),.ve_pdd(32'd0),
        .ve_av(),.ve_ac(),.ve_ah(),.ve_aval(),.ve_ag(),.ve_ov(1'b0),.ve_oc(2'd0),.ve_oy(128'd0),.ve_fi(1'b0),
        .e_v(),.e_c(),.e_d(),.g_v(1'b0),.g_c(2'd0),.g_d(32'd0),.fault(fs));
    ot_s81sl_vsw u_w (.clk(clk), .rst_n(rst_n), .i_v(swv_), .i_d(swd_), .i_w(sww), .i_lim(swl), .o_v(swvi), .o_d(swri), .o_f(swfi));
    dsfd_su_t_rxsf u_rf (.ck(clk), .rst(rst_n), .i_v(rav), .i_x(rax), .o_v(rfv), .o_u(rfu), .o_u2(rfu2), .o_mx(rfmx), .o_f(rff));
    dsfd_su_t_rxsb u_rb (.ck(clk), .rst(rst_n), .i_v(rfv), .i_u(rfu), .i_u2(rfu2), .i_mx(rfmx), .i_f(rff), .o_v(ravi), .o_r(rari), .o_f(rafi));

wire xf_v,xf_s;wire[275:0]xf;wire xfv,xfs;wire[275:0]xfd;
ot_s81sl_vq #(.AQ_XMEM(2)) vq(.clk(clk),.rst_n(rst_n),.y_v(1'b0),.y_i(3'd0),.y(128'd0),
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
  if(u_p.wv[0]||u_p.wv[1])begin nw++;$display("RAW_WRITE t=%0d banks=%b",n-ORIGIN,u_p.wv);end
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
  probe_finish();
  if(err)$fatal(1,"INPUT_SOURCE_LEDGER_FAIL errors=%0d",err);
  $display("INPUT_SOURCE_LEDGER_SOURCE_PASS raw1280 codes1280 scales40 sourcewrites320 gathers20 actualepochs15");$finish;
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


wire[6605:0]input_words;wire[6599:0]actual_input_pins;wire[5:0]actual_pins_valid;wire[5:0]input_faults;
reg[1100:0]late_actual_source;always @(posedge clk)late_actual_source<=actual_source_word;
selected_input_cone input_cone(.clk(clk),.rst_n(rst_n),.source_word(mut==10?late_actual_source:actual_source_word),.observed(input_words),.observed_pins(actual_input_pins),.pins_valid(actual_pins_valid),.faults(input_faults));
reg[1100:0]source_history[0:12000];integer nsources=0;integer nsamples[0:5];reg[31:0]age_mask[0:5];integer probe_errors=0;
initial for(integer f=0;f<6;f++)begin nsamples[f]=0;age_mask[f]=32'hffffffff;end
always @(posedge clk)begin:source_stamp
 integer t;t=($time/834)-ORIGIN;
 #2;
 if(t>=0 && t<=12000)source_history[t]=actual_source_word;
 if(t>=1300 && t<11800 && actual_source_word[0])begin nsources++;$display("SOURCE_INPUT_WORD t=%0d word=%h",t,actual_source_word);end
end
always @(posedge clk)begin:observe_input
 integer t;reg[31:0]age_candidates;reg[1100:0]word;
 t=($time/834)-ORIGIN;
 #3;
 if(t>=1300 && t<11800)begin
  for(integer f=0;f<6;f++)begin
   word=input_words[1101*f+:1101];
   if(word[0])begin
    age_candidates=0;
    for(integer age=0;age<32;age++)if(t>=age && source_history[t-age]===word)age_candidates[age]=1;
    nsamples[f]++;age_mask[f]=age_mask[f]&age_candidates;
    $display("CFIFO_INPUT_WORD t=%0d frame=%0d age_candidates=%h fault=%b word=%h",t,f,age_candidates,input_faults[f],word);
    if(age_candidates==0)begin probe_errors++;$display("INPUT_WORD_HAS_NO_REAL_SOURCE_MATCH");end
   end
  end
 end
end
function automatic[1099:0]pin_shape(input[1100:0]w);
 pin_shape={w[283]&w[0],w[282:1],w[549:284],w[564:552],w[551]&w[0],w[550]&w[0],w[1100:570],w[569]&w[0],w[568:566],w[565]&w[0]};
endfunction
integer pin_samples[0:5];reg[31:0]pin_age_mask[0:5];
initial for(integer f=0;f<6;f++)begin pin_samples[f]=0;pin_age_mask[f]=32'hffffffff;end
always @(posedge clk)begin:observe_pins
 integer t;reg[31:0]pin_candidates;
 t=($time/834)-ORIGIN;#3;
 if(t>=1300 && t<11800)for(integer f=0;f<6;f++)if(actual_pins_valid[f])begin
  pin_candidates=0;
  for(integer age=0;age<32;age++)if(t>=age && pin_shape(source_history[t-age])===actual_input_pins[1100*f+:1100])pin_candidates[age]=1;
  pin_samples[f]++;pin_age_mask[f]&=pin_candidates;
  $display("CFIFO_REGISTERED_PINS t=%0d frame=%0d candidates=%h",t,f,pin_candidates);
  if(pin_candidates==0)probe_errors++;
 end
end
task probe_finish;
 begin
  for(integer f=0;f<6;f++)begin
   $display("REGISTERED_PIN_RESULT frame=%0d samples=%0d age_mask=%h",f,pin_samples[f],pin_age_mask[f]);
   if(pin_samples[f]!=nsources||pin_age_mask[f]!=(f%3==0?32'h800:f%3==1?32'h200:32'h1000))probe_errors++;
   $display("INPUT_BOUNDARY_RESULT frame=%0d source_events=%0d samples=%0d ages=%h faults=%b",f,nsources,nsamples[f],age_mask[f],input_faults[f]);
   if(nsamples[f]!=nsources||nsources==0||age_mask[f]!=(f%3==0?32'h400:f%3==1?32'h100:32'h800)||input_faults[f])probe_errors++;
  end
  if(probe_errors)begin err+=probe_errors;$display("INPUT_BOUNDARY_OBSERVATION_FAIL errors=%0d",probe_errors);end
  else $display("INPUT_BOUNDARY_OBSERVATION_PASS no_numericframe_or_nativephase_claim");
 end
endtask

always @(posedge input_cone.ingress_u_f_3L01.xk[0])begin:clock_3L01_0
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L01.g_lane[0].u_l.wc;rc_pre=input_cone.ingress_u_f_3L01.g_lane[0].u_l.rc;rs_pre=input_cone.ingress_u_f_3L01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L01 lane=0 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L01.lk[0+:3],rs_pre,input_cone.ingress_u_f_3L01.rsync,wc_pre,input_cone.ingress_u_f_3L01.g_lane[0].u_l.wc,rc_pre,input_cone.ingress_u_f_3L01.g_lane[0].u_l.rc,input_cone.ingress_u_f_3L01.g_lane[0].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L01.xk[1])begin:clock_3L01_1
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L01.g_lane[1].u_l.wc;rc_pre=input_cone.ingress_u_f_3L01.g_lane[1].u_l.rc;rs_pre=input_cone.ingress_u_f_3L01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L01 lane=1 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L01.lk[3+:3],rs_pre,input_cone.ingress_u_f_3L01.rsync,wc_pre,input_cone.ingress_u_f_3L01.g_lane[1].u_l.wc,rc_pre,input_cone.ingress_u_f_3L01.g_lane[1].u_l.rc,input_cone.ingress_u_f_3L01.g_lane[1].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L01.xk[2])begin:clock_3L01_2
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L01.g_lane[2].u_l.wc;rc_pre=input_cone.ingress_u_f_3L01.g_lane[2].u_l.rc;rs_pre=input_cone.ingress_u_f_3L01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L01 lane=2 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L01.lk[6+:3],rs_pre,input_cone.ingress_u_f_3L01.rsync,wc_pre,input_cone.ingress_u_f_3L01.g_lane[2].u_l.wc,rc_pre,input_cone.ingress_u_f_3L01.g_lane[2].u_l.rc,input_cone.ingress_u_f_3L01.g_lane[2].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L01.xk[3])begin:clock_3L01_3
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L01.g_lane[3].u_l.wc;rc_pre=input_cone.ingress_u_f_3L01.g_lane[3].u_l.rc;rs_pre=input_cone.ingress_u_f_3L01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L01 lane=3 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L01.lk[9+:3],rs_pre,input_cone.ingress_u_f_3L01.rsync,wc_pre,input_cone.ingress_u_f_3L01.g_lane[3].u_l.wc,rc_pre,input_cone.ingress_u_f_3L01.g_lane[3].u_l.rc,input_cone.ingress_u_f_3L01.g_lane[3].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L02.xk[0])begin:clock_3L02_0
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L02.g_lane[0].u_l.wc;rc_pre=input_cone.ingress_u_f_3L02.g_lane[0].u_l.rc;rs_pre=input_cone.ingress_u_f_3L02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L02 lane=0 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L02.lk[0+:3],rs_pre,input_cone.ingress_u_f_3L02.rsync,wc_pre,input_cone.ingress_u_f_3L02.g_lane[0].u_l.wc,rc_pre,input_cone.ingress_u_f_3L02.g_lane[0].u_l.rc,input_cone.ingress_u_f_3L02.g_lane[0].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L02.xk[1])begin:clock_3L02_1
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L02.g_lane[1].u_l.wc;rc_pre=input_cone.ingress_u_f_3L02.g_lane[1].u_l.rc;rs_pre=input_cone.ingress_u_f_3L02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L02 lane=1 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L02.lk[3+:3],rs_pre,input_cone.ingress_u_f_3L02.rsync,wc_pre,input_cone.ingress_u_f_3L02.g_lane[1].u_l.wc,rc_pre,input_cone.ingress_u_f_3L02.g_lane[1].u_l.rc,input_cone.ingress_u_f_3L02.g_lane[1].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L02.xk[2])begin:clock_3L02_2
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L02.g_lane[2].u_l.wc;rc_pre=input_cone.ingress_u_f_3L02.g_lane[2].u_l.rc;rs_pre=input_cone.ingress_u_f_3L02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L02 lane=2 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L02.lk[6+:3],rs_pre,input_cone.ingress_u_f_3L02.rsync,wc_pre,input_cone.ingress_u_f_3L02.g_lane[2].u_l.wc,rc_pre,input_cone.ingress_u_f_3L02.g_lane[2].u_l.rc,input_cone.ingress_u_f_3L02.g_lane[2].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L02.xk[3])begin:clock_3L02_3
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L02.g_lane[3].u_l.wc;rc_pre=input_cone.ingress_u_f_3L02.g_lane[3].u_l.rc;rs_pre=input_cone.ingress_u_f_3L02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L02 lane=3 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L02.lk[9+:3],rs_pre,input_cone.ingress_u_f_3L02.rsync,wc_pre,input_cone.ingress_u_f_3L02.g_lane[3].u_l.wc,rc_pre,input_cone.ingress_u_f_3L02.g_lane[3].u_l.rc,input_cone.ingress_u_f_3L02.g_lane[3].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L03.xk[0])begin:clock_3L03_0
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L03.g_lane[0].u_l.wc;rc_pre=input_cone.ingress_u_f_3L03.g_lane[0].u_l.rc;rs_pre=input_cone.ingress_u_f_3L03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L03 lane=0 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L03.lk[0+:3],rs_pre,input_cone.ingress_u_f_3L03.rsync,wc_pre,input_cone.ingress_u_f_3L03.g_lane[0].u_l.wc,rc_pre,input_cone.ingress_u_f_3L03.g_lane[0].u_l.rc,input_cone.ingress_u_f_3L03.g_lane[0].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L03.xk[1])begin:clock_3L03_1
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L03.g_lane[1].u_l.wc;rc_pre=input_cone.ingress_u_f_3L03.g_lane[1].u_l.rc;rs_pre=input_cone.ingress_u_f_3L03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L03 lane=1 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L03.lk[3+:3],rs_pre,input_cone.ingress_u_f_3L03.rsync,wc_pre,input_cone.ingress_u_f_3L03.g_lane[1].u_l.wc,rc_pre,input_cone.ingress_u_f_3L03.g_lane[1].u_l.rc,input_cone.ingress_u_f_3L03.g_lane[1].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L03.xk[2])begin:clock_3L03_2
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L03.g_lane[2].u_l.wc;rc_pre=input_cone.ingress_u_f_3L03.g_lane[2].u_l.rc;rs_pre=input_cone.ingress_u_f_3L03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L03 lane=2 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L03.lk[6+:3],rs_pre,input_cone.ingress_u_f_3L03.rsync,wc_pre,input_cone.ingress_u_f_3L03.g_lane[2].u_l.wc,rc_pre,input_cone.ingress_u_f_3L03.g_lane[2].u_l.rc,input_cone.ingress_u_f_3L03.g_lane[2].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3L03.xk[3])begin:clock_3L03_3
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3L03.g_lane[3].u_l.wc;rc_pre=input_cone.ingress_u_f_3L03.g_lane[3].u_l.rc;rs_pre=input_cone.ingress_u_f_3L03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3L03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3L03 lane=3 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3L03.lk[9+:3],rs_pre,input_cone.ingress_u_f_3L03.rsync,wc_pre,input_cone.ingress_u_f_3L03.g_lane[3].u_l.wc,rc_pre,input_cone.ingress_u_f_3L03.g_lane[3].u_l.rc,input_cone.ingress_u_f_3L03.g_lane[3].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R01.xk[0])begin:clock_3R01_0
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R01.g_lane[0].u_l.wc;rc_pre=input_cone.ingress_u_f_3R01.g_lane[0].u_l.rc;rs_pre=input_cone.ingress_u_f_3R01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R01 lane=0 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R01.lk[0+:3],rs_pre,input_cone.ingress_u_f_3R01.rsync,wc_pre,input_cone.ingress_u_f_3R01.g_lane[0].u_l.wc,rc_pre,input_cone.ingress_u_f_3R01.g_lane[0].u_l.rc,input_cone.ingress_u_f_3R01.g_lane[0].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R01.xk[1])begin:clock_3R01_1
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R01.g_lane[1].u_l.wc;rc_pre=input_cone.ingress_u_f_3R01.g_lane[1].u_l.rc;rs_pre=input_cone.ingress_u_f_3R01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R01 lane=1 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R01.lk[3+:3],rs_pre,input_cone.ingress_u_f_3R01.rsync,wc_pre,input_cone.ingress_u_f_3R01.g_lane[1].u_l.wc,rc_pre,input_cone.ingress_u_f_3R01.g_lane[1].u_l.rc,input_cone.ingress_u_f_3R01.g_lane[1].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R01.xk[2])begin:clock_3R01_2
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R01.g_lane[2].u_l.wc;rc_pre=input_cone.ingress_u_f_3R01.g_lane[2].u_l.rc;rs_pre=input_cone.ingress_u_f_3R01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R01 lane=2 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R01.lk[6+:3],rs_pre,input_cone.ingress_u_f_3R01.rsync,wc_pre,input_cone.ingress_u_f_3R01.g_lane[2].u_l.wc,rc_pre,input_cone.ingress_u_f_3R01.g_lane[2].u_l.rc,input_cone.ingress_u_f_3R01.g_lane[2].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R01.xk[3])begin:clock_3R01_3
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R01.g_lane[3].u_l.wc;rc_pre=input_cone.ingress_u_f_3R01.g_lane[3].u_l.rc;rs_pre=input_cone.ingress_u_f_3R01.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R01.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R01 lane=3 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R01.lk[9+:3],rs_pre,input_cone.ingress_u_f_3R01.rsync,wc_pre,input_cone.ingress_u_f_3R01.g_lane[3].u_l.wc,rc_pre,input_cone.ingress_u_f_3R01.g_lane[3].u_l.rc,input_cone.ingress_u_f_3R01.g_lane[3].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R02.xk[0])begin:clock_3R02_0
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R02.g_lane[0].u_l.wc;rc_pre=input_cone.ingress_u_f_3R02.g_lane[0].u_l.rc;rs_pre=input_cone.ingress_u_f_3R02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R02 lane=0 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R02.lk[0+:3],rs_pre,input_cone.ingress_u_f_3R02.rsync,wc_pre,input_cone.ingress_u_f_3R02.g_lane[0].u_l.wc,rc_pre,input_cone.ingress_u_f_3R02.g_lane[0].u_l.rc,input_cone.ingress_u_f_3R02.g_lane[0].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R02.xk[1])begin:clock_3R02_1
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R02.g_lane[1].u_l.wc;rc_pre=input_cone.ingress_u_f_3R02.g_lane[1].u_l.rc;rs_pre=input_cone.ingress_u_f_3R02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R02 lane=1 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R02.lk[3+:3],rs_pre,input_cone.ingress_u_f_3R02.rsync,wc_pre,input_cone.ingress_u_f_3R02.g_lane[1].u_l.wc,rc_pre,input_cone.ingress_u_f_3R02.g_lane[1].u_l.rc,input_cone.ingress_u_f_3R02.g_lane[1].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R02.xk[2])begin:clock_3R02_2
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R02.g_lane[2].u_l.wc;rc_pre=input_cone.ingress_u_f_3R02.g_lane[2].u_l.rc;rs_pre=input_cone.ingress_u_f_3R02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R02 lane=2 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R02.lk[6+:3],rs_pre,input_cone.ingress_u_f_3R02.rsync,wc_pre,input_cone.ingress_u_f_3R02.g_lane[2].u_l.wc,rc_pre,input_cone.ingress_u_f_3R02.g_lane[2].u_l.rc,input_cone.ingress_u_f_3R02.g_lane[2].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R02.xk[3])begin:clock_3R02_3
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R02.g_lane[3].u_l.wc;rc_pre=input_cone.ingress_u_f_3R02.g_lane[3].u_l.rc;rs_pre=input_cone.ingress_u_f_3R02.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R02.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R02 lane=3 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R02.lk[9+:3],rs_pre,input_cone.ingress_u_f_3R02.rsync,wc_pre,input_cone.ingress_u_f_3R02.g_lane[3].u_l.wc,rc_pre,input_cone.ingress_u_f_3R02.g_lane[3].u_l.rc,input_cone.ingress_u_f_3R02.g_lane[3].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R03.xk[0])begin:clock_3R03_0
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R03.g_lane[0].u_l.wc;rc_pre=input_cone.ingress_u_f_3R03.g_lane[0].u_l.rc;rs_pre=input_cone.ingress_u_f_3R03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R03 lane=0 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R03.lk[0+:3],rs_pre,input_cone.ingress_u_f_3R03.rsync,wc_pre,input_cone.ingress_u_f_3R03.g_lane[0].u_l.wc,rc_pre,input_cone.ingress_u_f_3R03.g_lane[0].u_l.rc,input_cone.ingress_u_f_3R03.g_lane[0].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R03.xk[1])begin:clock_3R03_1
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R03.g_lane[1].u_l.wc;rc_pre=input_cone.ingress_u_f_3R03.g_lane[1].u_l.rc;rs_pre=input_cone.ingress_u_f_3R03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R03 lane=1 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R03.lk[3+:3],rs_pre,input_cone.ingress_u_f_3R03.rsync,wc_pre,input_cone.ingress_u_f_3R03.g_lane[1].u_l.wc,rc_pre,input_cone.ingress_u_f_3R03.g_lane[1].u_l.rc,input_cone.ingress_u_f_3R03.g_lane[1].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R03.xk[2])begin:clock_3R03_2
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R03.g_lane[2].u_l.wc;rc_pre=input_cone.ingress_u_f_3R03.g_lane[2].u_l.rc;rs_pre=input_cone.ingress_u_f_3R03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R03 lane=2 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R03.lk[6+:3],rs_pre,input_cone.ingress_u_f_3R03.rsync,wc_pre,input_cone.ingress_u_f_3R03.g_lane[2].u_l.wc,rc_pre,input_cone.ingress_u_f_3R03.g_lane[2].u_l.rc,input_cone.ingress_u_f_3R03.g_lane[2].u_l.warm);
end
always @(posedge input_cone.ingress_u_f_3R03.xk[3])begin:clock_3R03_3
 integer edge_t,wc_pre,rc_pre;time edge_ps;reg rs_pre;
 edge_t=($time/834)-ORIGIN;edge_ps=$time;wc_pre=input_cone.ingress_u_f_3R03.g_lane[3].u_l.wc;rc_pre=input_cone.ingress_u_f_3R03.g_lane[3].u_l.rc;rs_pre=input_cone.ingress_u_f_3R03.rsync;
 #4;
 if(edge_t<40 || input_cone.ingress_u_f_3R03.xw_[0])
 $display("INPUT_CLOCK_TUPLE frame=3R03 lane=3 time_ps=%0t phase_ps=%0d root_t=%0d K=%0d rs_pre=%b rs_post=%b wc_pre=%0d wc_post=%0d rc_pre=%0d rc_post=%0d warm=%b",edge_ps,edge_ps%834,edge_t,input_cone.ingress_u_f_3R03.lk[9+:3],rs_pre,input_cone.ingress_u_f_3R03.rsync,wc_pre,input_cone.ingress_u_f_3R03.g_lane[3].u_l.wc,rc_pre,input_cone.ingress_u_f_3R03.g_lane[3].u_l.rc,input_cone.ingress_u_f_3R03.g_lane[3].u_l.warm);
end

// Diagnostic faults operate on actual source/route wires only; baseline is exact.
initial begin
 wait(n==ORIGIN+1590);#10;
 if(mut==7)begin
  force input_cone.nx_f_3L03_l0_fck[1]=1'b0;
  @(posedge clk);#10;release input_cone.nx_f_3L03_l0_fck[1];
 end
 if(mut==8)force input_cone.w_x_f_3L03_l0_dst[100]=1'b0;
 if(mut==9)force input_cone.w_x_f_3L03_l0_dst=input_cone.w_x_f_3L03_l1_dst;
 if(mut==11)force input_cone.nx_f_3L03_l0_fck[1]=clk;
end

endmodule
