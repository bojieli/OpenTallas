`timescale 1ns/1ps
// HC COEFFICIENT CHAIN on real RTL, one layer, both blocks, driven by the ACTUAL fixed issuer (engine 11) from a compiled
// calendar (done = issue + 1 + pin-to-pin). Real: ot_s81_fixed_issue, ot_s81_hcx_chain_seq, 4 x dsfd_sp_hcx_projection
// (ranks 0..3: controller + prefetch + [HLAYOUT transpose] + 6 resident-ROM HCP leaves each = the 24 mix rows),
// ot_s81_hcx_gatherpack, ot_s81_hcx_post_gain_native (post mode; 4 real parameter ROMs). The H rows are the layer's
// released HC residuals (BF16) in the VM; ranks 1..3 read the same rows (TP4 dies hold the replicated residual).
// DECLARED BOUNDARIES (not die-qualified): ideal registered VM (RL/WL 4) instead of dsfd_sp_vm; the TP4 raw gather is
// bench transport delivering each rank's 6-word record into gatherpack's compiled slots (collective-to-HC glue, OPEN);
// peer ranks' commands = rank 0's command (each die's issuer runs the same compiled row).
// Checked: the four coefficient rows == the snapshot's pre/post/comb (hu_exp, independent golden), issuer/chain/leaf
// faults 0, every completion on its compiled edge. CAL=1 prints the measured offsets instead (no verdict).
// Modes: HLAYOUT (1 = h_rows VM layout), MUT_POST (post core mutant) -> FAIL.
module tb_s81_hcx_chain #(parameter integer HLAYOUT=1,MUT_POST=0,CAL=0,FAST=0,
  PROJ_DONE=1,G_OFF=2000,GP_DONE=24,POST_TOG=2030,POST_SEEN=1,DONE_OFF=4000,ISSUE0=200,ISSUE1=4400,LAYER=1);
 localparam real TS=0.8333, TV=1.1111;
 reg ck=0,ckv=0;always #(TS/2) ck=~ck;always #(TV/2) ckv=~ckv;
 integer cyc=0;always @(posedge ck)cyc<=cyc+1;
 reg rst_n=0;initial begin while(cyc<1000)@(negedge ck);rst_n=1;end
 reg srst_n=0;initial begin while(cyc<1000)@(negedge ck);@(negedge ckv);srst_n=1;end
 string dir;
 // ---------------- fixed issuer
 reg pv=0;reg[6:0]pa=0;reg[27:0]pd=0;reg[34:0]pm[0:15];
 wire[12:0]cv;wire[1091:0]cd;wire is_fault;wire[3:0]is_code;wire[1:0]is_phase;
 wire[8:0]x_done;wire[1:0]x_st;
 ot_s81_fixed_issue #(.NOPS(3),.NENG(13),.STAGE(0),.OP_BASE(2),.ENG_PRESENT(13'h800))iss(
  .clk(ck),.rst_n(rst_n),.pw_v(pv),.pw_a(pa),.pw_d(pd),.prog_len(8'd3),
  .job_v(cyc==1250),.job_user(10'd0),.job_pos(21'd0),.job_tok(21'd1000),
  .job_rdy(),.busy(),.job_done(),.job_kdone(),.done_slot(),.kit_tok(),.cmd_v(cv),.cmd_d(cd),
  .engine_available({1'b0,x_st[1],11'b0}),.dn_v({1'b0,x_done[8],11'b0}),.dn_tag({8'b0,x_done[7:0],88'b0}),
  .fault(is_fault),.fault_code(is_code),.st_jobs(),.st_cmds(),.phase(is_phase));
 wire[84:0]c9={cv[11],cd[84*11+:84]};   // engine 11 = HC projection chain (static sequencer ABI)
 // ---------------- chain sequencer (port 9)
 wire[84:0]p_cmd;wire[8:0]p_done[0:3];wire[1:0]p_st[0:3];
 wire g_start,g_done,g_fault,s_start,s_ffn,s_done,s_fault;wire[13:0]g_raw,s_raw,s_coef;wire[5:0]s_layer;
 ot_s81_hcx_chain_seq #(.PROJ_DONE(PROJ_DONE),.G_OFF(G_OFF),.GP_DONE(GP_DONE),.POST_TOG(POST_TOG),.POST_SEEN(POST_SEEN),.DONE_OFF(DONE_OFF))
  chain(.ck(ck),.rst_n(rst_n),.skv(ckv),.srst_n(srst_n),.c_cmd(c9),.c_done(x_done),.c_st(x_st),
  .p_cmd(p_cmd),.p_done(p_done[0]),.p_st(p_st[0]),.g_start(g_start),.g_raw_base(g_raw),.g_done(g_done),.g_fault(g_fault),
  .s_start(s_start),.s_ffn(s_ffn),.s_layer(s_layer),.s_raw_base(s_raw),.s_coef_base(s_coef),.s_done(s_done),.s_fault(s_fault));
 // ---------------- bench VM (ideal, registered RL/WL 4)
 reg[511:0]vm[0:16383];
 wire[7:0]rq_v[0:3];wire[111:0]rq_row[0:3];reg[7:0]rv_p[0:3][0:3];reg[4095:0]rd_p[0:3][0:3];
 wire raw_v[0:3];wire[191:0]raw_d[0:3];
 genvar r;
 generate for(r=0;r<4;r=r+1)begin:g_rank
  dsfd_sp_hcx_projection #(.RANK(r),.RL(4),.FAST_CYC(FAST),.HLAYOUT(HLAYOUT))u(
   .cck(ck),.crst_n(rst_n),.skctl(ckv),.srst_n(srst_n),.sk_leaf({6{ckv}}),.c_cmd(p_cmd),.c_done(p_done[r]),.c_st(p_st[r]),
   .rq_v(rq_v[r]),.rq_row(rq_row[r]),.rs_v(rv_p[r][3]),.rs_d(rd_p[r][3]),.t_raw_v(raw_v[r]),.t_raw_d(raw_d[r]));
`ifdef OT_HCX_ROM_HIERLOAD
  for (genvar l = 0; l < 6; l++) for (genvar b = 0; b < 8; b++) for (genvar m = 0; m < 4; m++) for (genvar pg = 0; pg < 2; pg++) begin : g_ld
   initial begin string rd; #1;
    if ($value$plusargs("OT_ROM_DIR=%s", rd))
     $readmemh($sformatf("%s/hcx_r%0d_p%0d_b%0d_l%0d_p%0d.viamap.hex", rd, r, l, b, m, pg), u.g_leaf[l].leaf.g_bank[b].g_rom[m].g_page[pg].rom.arr);
   end
  end
`endif
  always @(posedge ckv)begin
   rv_p[r][0]<=rq_v[r];
   for(integer p=0;p<8;p=p+1)rd_p[r][0][512*p+:512]<=vm[rq_row[r][14*p+:14]];
   for(integer i=1;i<4;i=i+1)begin rv_p[r][i]<=rv_p[r][i-1];rd_p[r][i]<=rd_p[r][i-1];end
  end
 end endgenerate
 // ---------------- TP4 raw gather: bench transport (declared glue) into gatherpack's compiled rank slots
 reg[191:0]rawq[0:3];reg rawseen[0:3];integer raw_age[0:3];
 integer cmd_cyc=-1,errs=0;
 always @(posedge ckv)for(integer q=0;q<4;q=q+1)if(raw_v[q])begin rawq[q]<=raw_d[q];rawseen[q]<=1;raw_age[q]<=cyc-cmd_cyc;end
 reg iv=0;reg[1:0]irank=0;reg[511:0]id=0;integer gk=0,gq;
 always @(posedge ck)begin
  iv<=0;
  if(g_start)gk<=1;else if(gk>0&&gk<16)gk<=gk+1;else gk<=0;
  if(g_start||gk==4||gk==8||gk==12)begin
   gq=g_start?0:gk/4;
   if(!rawseen[gq])begin errs++;$display("ERR raw record of rank %0d not present at its gather slot",gq);end
   iv<=1;irank<=2'(gq);id<='1;id[191:0]<=rawq[gq];rawseen[gq]<=0;
  end
 end
 wire gwv;wire[13:0]gwa;wire[15:0]gwm;wire[511:0]gwd;reg[3:0]gc=0;reg[13:0]ga_p[0:3];reg[511:0]gd_p[0:3];
 ot_s81_hcx_gatherpack gp(.clk(ck),.rst_n(rst_n),.start(g_start),.raw_base_row(g_raw),.i_v(iv),.i_rank(irank),.i_d(id),
  .wq_v(gwv),.wq_row(gwa),.wq_mask(gwm),.wq_d(gwd),.wq_commit(gc[3]),.done(g_done),.fault(g_fault));
 always @(posedge ck)begin
  gc<={gc[2:0],gwv};ga_p[0]<=gwa;gd_p[0]<=gwd;for(integer i=1;i<4;i=i+1)begin ga_p[i]<=ga_p[i-1];gd_p[i]<=gd_p[i-1];end
  if(gc[3])vm[ga_p[3]]<=gd_p[3];
 end
 // ---------------- post (serial clock)
 wire srv,swv;wire[13:0]sra,swa;wire[15:0]swm;wire[511:0]swd;reg[3:0]sv_p=0,sc=0;reg[511:0]sd_p[0:3];
 reg[13:0]sa_p[0:3];reg[15:0]sm_p[0:3];reg[511:0]sw_p[0:3];reg[31:0]eps[0:0];
 ot_s81_hcx_post_gain_native #(.MUT_POST(MUT_POST))post(.clk(ckv),.rst_n(srst_n),.start(s_start),.gain_mode(1'b0),.gain_draft(1'b0),
  .ffn(s_ffn),.raw_base_row(s_raw),.coef_base_row(s_coef),.gain_base_row(14'd4096),.layer_idx(s_layer),.norm_eps(eps[0]),
  .compiled_cycles(16'd540),.done(s_done),.rq_v(srv),.rq_row(sra),.rs_v(sv_p[3]),.rs_d(sd_p[3]),
  .wq_v(swv),.wq_row(swa),.wq_mask(swm),.wq_d(swd),.wq_commit(sc[3]),.fault(s_fault));
 always @(posedge ckv)begin
  sv_p<={sv_p[2:0],srv};sd_p[0]<=vm[sra];for(integer i=1;i<4;i=i+1)sd_p[i]<=sd_p[i-1];
  sc<={sc[2:0],swv};sa_p[0]<=swa;sm_p[0]<=swm;sw_p[0]<=swd;
  for(integer i=1;i<4;i=i+1)begin sa_p[i]<=sa_p[i-1];sm_p[i]<=sm_p[i-1];sw_p[i]<=sw_p[i-1];end
  if(sc[3])for(integer w=0;w<16;w=w+1)if(sm_p[3][w])vm[sa_p[3]][32*w+:32]<=sw_p[3][32*w+:32];
 end
 // ---------------- measurement
 integer ncmd=0,pd_age=-1,gd_age=-1,ss_age=-1,sd_age=-1,cd_age=-1,first_fault=-1,ccmd=-1,cdone=-1,cphase=-1;
 always @(posedge ck)begin
  if(c9[84])begin cmd_cyc=cyc;ncmd++;cphase=g_rank[0].u.controller.phase;if(ccmd<0)ccmd=cyc;end
  if(p_done[0][8])pd_age=cyc-cmd_cyc;
  if(g_done)gd_age=cyc-cmd_cyc;
  if(x_done[8])begin cd_age=cyc-cmd_cyc;if(cdone<0)cdone=cyc;end
  if(chain.dsync2!=chain.dseen)sd_age=cyc-cmd_cyc;
  for(integer q=1;q<4;q=q+1)if(p_done[q]!==p_done[0])begin errs++;$display("ERR rank %0d completion differs from rank 0",q);end
  if((is_fault||x_st[0])&&first_fault<0)begin first_fault=cyc;
   $display("FAULT cyc=%0d issuer=%0d code=%0d chain_cfault=%0d post_fault=%0d gp_fault=%0d proj_st=%b%b%b%b leaf=%b ctl_cfault=%0d ctl_sfault=%0d phase_at_cmd=%0d",
    cyc,is_fault,is_code,chain.cfault,s_fault,g_fault,p_st[0],p_st[1],p_st[2],p_st[3],g_rank[0].u.lf,
    g_rank[0].u.controller.cfault,g_rank[0].u.controller.sfault,cphase);end
  if(g_rank[0].u.controller.esync2!=g_rank[0].u.controller.eseen)
   $display("CAL controller_return ctick=%0d -> FAST_CYC=%0d",g_rank[0].u.controller.ctick,g_rank[0].u.controller.ctick+2);
 end
 always @(posedge ckv)if(s_start)ss_age=cyc-cmd_cyc;
 // post restart bound: the reused HC unit's record-ready (rec_rdy) after a block; a start while it is low faults the post
 reg prdy_q=1;always @(posedge ckv)begin prdy_q<=post.post.ready;
  if(post.post.ready&&!prdy_q)$display("CAL post_ready_rise age(ck)=%0d after cmd %0d",cyc-cmd_cyc,ncmd);
  if(!post.post.ready&&prdy_q)$display("CAL post_ready_fall age(ck)=%0d after cmd %0d",cyc-cmd_cyc,ncmd);end
 reg[511:0]hm[0:1279],want[0:3];
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");
  $readmemh({dir,"/h.mem"},hm);$readmemh({dir,"/want.mem"},want);$readmemh({dir,"/eps.mem"},eps);$readmemh({dir,"/program.mem"},pm);
  for(integer i=0;i<16384;i=i+1)vm[i]=0;
  for(integer i=0;i<1280;i=i+1)vm[i]=hm[i];
  for(integer q=0;q<4;q=q+1)rawseen[q]=0;
  while(cyc<1010)@(negedge ck);
  for(integer i=0;i<11;i=i+1)begin pv=1;pa=pm[i][34:28];pd=pm[i][27:0];@(negedge ck);pv=0;@(negedge ck);end
  while(cyc<1250+ISSUE1+DONE_OFF+400)@(negedge ck);
  $display("HCX_CHAIN commands=%0d cmd_phase=%0d proj_done_age=%0d raw_age=%0d,%0d,%0d,%0d gp_done_age=%0d post_start_age(ck)=%0d post_seen_age=%0d chain_done_age=%0d first_cmd=%0d first_done=%0d cmd_to_done=%0d",
   ncmd,cphase,pd_age,raw_age[0],raw_age[1],raw_age[2],raw_age[3],gd_age,ss_age,sd_age,cd_age,ccmd,cdone,cdone-ccmd);
  if(CAL)begin $display("HCX_CHAIN CAL (no verdict)");$finish;end
  for(integer b=0;b<4;b=b+1)for(integer w=0;w<16;w=w+1)if(vm[2560+b][32*w+:32]!==want[b][32*w+:32])begin
   errs++;if(errs<12)$display("ERR coef row %0d word %0d got %08h want %08h",2560+b,w,vm[2560+b][32*w+:32],want[b][32*w+:32]);end
  $display("HCX_CHAIN coef_words_bad=%0d issuer_fault=%0d code=%0d chain_fault=%0d ncmd=%0d",errs,is_fault,is_code,x_st[0],ncmd);
  if(errs||is_fault||x_st[0]||ncmd!=2)$fatal(1,"HCX_CHAIN FAIL");
  $display("HCX_CHAIN PASS layer%0d attn+ffn 4 coefficient rows exact, fixed issuer, compiled done",LAYER);$finish;
 end
endmodule
