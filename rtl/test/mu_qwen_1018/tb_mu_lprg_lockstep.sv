`timescale 1ns/1ps
// MU-ADOPT-HROOT 10-19: qkd_static_kv_layer_programme_mu identity.
//   ref  = the unchanged qkd_static_kv_layer_programme (boot 0..326)
//   mu0  = qkd_static_kv_layer_programme_mu #(MU 0)  (same boot)           -> every output equal to ref, every edge
//   mu1  = qkd_static_kv_layer_programme_mu #(MU 1)  (boot + 144 GAP words all 0, seal at 470), user 0 only
//          -> every output equal to ref on every edge from the first start (the latency user keeps its timeline)
// Random legal stage tables (SEED), 3 tokens back to back with idle gaps, cfg buses separate (MU seals later).
module tb_mu_lprg_lockstep;
 reg ck=0;always #0.5 ck=~ck;
 reg rst_n=0;
 reg we_r=0,we_m=0;reg[8:0]ad_r=0,ad_m=0;reg[63:0]da_r=0,da_m=0;
 reg start=0,av=1,auth=1;reg[15:0]pe=16'h5a5a,ae=0;reg[63:0]pd=64'h0123456789abcdef;reg[17:0]at=0,ap=0;reg[1:0]ag=0;
 `define OUTS(p) wire p``cg,p``kg,p``vg,p``ai,p``ar,p``ws,p``ls,p``ss,p``sd,p``q,p``cf,p``ac,p``dn,p``ft;wire[5:0]p``cs,p``st,p``ly;\
  wire[15:0]p``ep;wire[17:0]p``tk,p``ps;wire[13:0]p``ct;wire[1:0]p``gn;wire[7:0]p``fc;wire[31:0]p``age,p``tc;
 `OUTS(r_) `OUTS(a_) `OUTS(b_)
 `define CONN(p,we,ad,da) (.ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(ad),.cfg_data(da),.start(start),.authority_valid(av),\
  .programme_authorized(auth),.programme_epoch(pe),.programme_digest(pd),.authority_epoch(ae),.authority_token(at),\
  .authority_position(ap),.authority_generation(ag),.ctrl_go(p``cg),.kgo(p``kg),.vgo(p``vg),.attention_issue(p``ai),\
  .attention_run(p``ar),.writer_start(p``ws),.link_start(p``ls),.stage_start(p``ss),.stage_done(p``sd),\
  .expected_upstream_quiet(p``q),.completed_stage(p``cs),.stage(p``st),.layer(p``ly),.epoch(p``ep),.token(p``tk),\
  .position(p``ps),.ctx_t(p``ct),.generation(p``gn),.configured(p``cf),.active(p``ac),.done(p``dn),.fault(p``ft),\
  .fault_code(p``fc),.age(p``age),.token_cycles(p``tc))
 qkd_static_kv_layer_programme #(.MUT(0)) ref_ `CONN(r_,we_r,ad_r,da_r);
 qkd_static_kv_layer_programme_mu #(.MUT(0),.MU(0)) mu0 `CONN(a_,we_r,ad_r,da_r);
 qkd_static_kv_layer_programme_mu #(.MUT(0),.MU(1)) mu1 `CONN(b_,we_m,ad_m,da_m);
 wire[255:0] vr={r_cg,r_kg,r_vg,r_ai,r_ar,r_ws,r_ls,r_ss,r_sd,r_q,r_ac,r_dn,r_ft,r_cs,r_st,r_ly,r_ep,r_tk,r_ps,r_ct,r_gn,r_fc,r_age,r_tc};
 wire[255:0] va={a_cg,a_kg,a_vg,a_ai,a_ar,a_ws,a_ls,a_ss,a_sd,a_q,a_ac,a_dn,a_ft,a_cs,a_st,a_ly,a_ep,a_tk,a_ps,a_ct,a_gn,a_fc,a_age,a_tc};
 wire[255:0] vb={b_cg,b_kg,b_vg,b_ai,b_ar,b_ws,b_ls,b_ss,b_sd,b_q,b_ac,b_dn,b_ft,b_cs,b_st,b_ly,b_ep,b_tk,b_ps,b_ct,b_gn,b_fc,b_age,b_tc};
 integer cyc=0,cmp_a=0,cmp_b=0,bad_a=0,bad_b=0,ev=0,go=0;
 always @(posedge ck)cyc<=cyc+1;
 always @(negedge ck)begin
  if(rst_n&&r_cf&&a_cf)begin cmp_a=cmp_a+1;if(va!==vr||a_cf!==r_cf)begin bad_a=bad_a+1;if(bad_a<5)$display("MISMATCH mu0 cyc %0d ref %h mu0 %h",cyc,vr,va);end end
  if(go)begin cmp_b=cmp_b+1;if(vb!==vr)begin bad_b=bad_b+1;if(bad_b<5)$display("MISMATCH mu1 cyc %0d ref %h mu1 %h",cyc,vr,vb);end end
  if(r_cg|r_kg|r_vg|r_ai|r_ar|r_ws|r_ls|r_ss|r_sd)ev=ev+1;
 end
 reg[31:0]row[0:8];integer s,w,seed,tok,lim;reg[31:0]e;
 task wr_r(input[8:0]a,input[63:0]d);begin @(negedge ck);we_r=1;ad_r=a;da_r=d;@(negedge ck);we_r=0;end endtask
 task wr_m(input[8:0]a,input[63:0]d);begin @(negedge ck);we_m=1;ad_m=a;da_m=d;@(negedge ck);we_m=0;end endtask
 initial begin
  if(!$value$plusargs("SEED=%d",seed))seed=7;
  repeat(4)@(posedge ck);rst_n=1;repeat(3)@(posedge ck);
  for(s=0;s<36;s=s+1)begin
   e=32'd24+($urandom(seed+s)%48);                        // stage_end 24..71
   lim=e-1;                                                // roots in 3..e-2, quiet greatest, run >= issue+4
   row[0]=3+$urandom%(lim-12);row[1]=3+$urandom%(lim-12);row[2]=3+$urandom%(lim-12);row[3]=3+$urandom%(lim-12);
   row[4]=row[3]+4+$urandom%4;row[5]=3+$urandom%(lim-12);row[6]=3+$urandom%(lim-12);
   row[7]=e-1;row[8]=e;
   for(w=0;w<9;w=w+1)begin wr_r(9*s+w,{32'd0,row[w]});wr_m(9*s+w,{32'd0,row[w]});end
  end
  wr_r(324,pd);wr_m(324,pd);wr_r(325,{48'd0,pe});wr_m(325,{48'd0,pe});
  for(w=0;w<144;w=w+1)wr_m(326+w,64'd0);
  wr_r(326,64'h514b564c59523336);wr_m(470,64'h514b564c59523336);
  repeat(3)@(posedge ck);
  if(!(r_cf&&a_cf&&b_cf)||r_ft||a_ft||b_ft)begin $display("FAIL MU_LPRG_LOCKSTEP boot cf %b%b%b ft %b%b%b fc %h %h",r_cf,a_cf,b_cf,r_ft,a_ft,b_ft,r_fc,b_fc);$finish;end
  for(tok=0;tok<3;tok=tok+1)begin
   @(negedge ck);go=1;start=1;ae={14'(16'h1230+tok),2'd0};at=18'd1000+tok;ap=18'd8000+tok;ag=2'(tok);
   @(negedge ck);start=0;
   wait(r_dn);repeat(5+7*tok)@(posedge ck);
  end
  repeat(10)@(posedge ck);
  if(bad_a==0&&bad_b==0&&cmp_b>3000&&ev>3*36*4&&!r_ft&&!b_ft)
   $display("PASS MU_LPRG_LOCKSTEP seed=%0d mu0_cmp=%0d mu1_cmp=%0d events=%0d (MU0 == original; MU1 user 0 gap 0 == original)",seed,cmp_a,cmp_b,ev);
  else $display("FAIL MU_LPRG_LOCKSTEP bad_mu0=%0d bad_mu1=%0d cmp_b=%0d ev=%0d ft=%b%b",bad_a,bad_b,cmp_b,ev,r_ft,b_ft);
  $finish;
 end
 initial begin #400000;$display("FAIL MU_LPRG_LOCKSTEP timeout");$finish;end
endmodule
