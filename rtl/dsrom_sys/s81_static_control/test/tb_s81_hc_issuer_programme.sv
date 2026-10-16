`timescale 1ns/1ps
module tb_s81_hc_issuer_programme;
 reg sc=0,dc=0,rn=0,pv=0,jv=0;reg[6:0]pa=0;reg[27:0]pd=0;
 initial begin #12;forever begin sc=1;#3;sc=0;#3;end end
 initial begin #12;forever begin dc=1;#4;dc=0;#4;end end
 wire[12:0]cv;wire[1091:0]cd;wire[8:0]sd;wire[1:0]phase;wire ifault,pfault,jdone;
 wire[84:0]hc;wire[31:0]da,ssa,sra,yt;wire[639:0]post;
 reg[8:0]serial_done=0;
 ot_s81_fixed_issue #(.NOPS(8),.STAGE(7),.ENG_PRESENT(13'b100))u_issue(
 .clk(sc),.rst_n(rn),.pw_v(pv),.pw_a(pa),.pw_d(pd),.prog_len(8'd7),.job_v(jv),
 .job_user(10'd37),.job_pos(21'd111),.job_tok(21'd222),.job_rdy(),.busy(),.job_done(jdone),
 .job_kdone(),.done_slot(),.kit_tok(),.cmd_v(cv),.cmd_d(cd),.engine_available(13'b100),
 .dn_v({10'b0,sd[8],2'b0}),.dn_tag({80'b0,sd[7:0],16'b0}),.fault(ifault),.fault_code(),.st_jobs(),.st_cmds(),.phase(phase));
 ot_s81_hc_programme_endpoint #(.RAW_ROM_CLOCK(1))u_endpoint(
 .stream_ck(sc),.stream_rst_n(rn),.serial_ck(dc),.serial_rst_n(rn),.rom_ck(sc),
 .c2({cv[2],cd[168+:84]}),.hc_command(hc),.hc_done_age(da),.hc_ss_age(ssa),.hc_scalar_age(sra),.hc_y_tag(yt),
 .hc_post_ages(post),.serial_done(serial_done),.stream_done(sd),.fault(pfault));
 reg[34:0]pw[0:22];integer i,j,st=-1,dt=-1,launch=-1,seen=0,dones=0,ended=0;
 integer return_age=-1;reg[7:0]saved_tag;
 initial begin
  rn=1;#1;rn=0;#9;rn=1;
  $readmemh("program.hex",pw);
  repeat(3)@(negedge sc);
  for(i=0;i<23;i=i+1)begin pv=1;pa=pw[i][34:28];pd=pw[i][27:0];@(negedge sc);end
  pv=0;repeat(12)@(negedge sc);
  while(phase!=0)@(negedge sc);
  jv=1;@(negedge sc);jv=0;
  repeat(180)@(negedge sc);
  if(seen!=6||dones!=6||ended!=1||ifault||pfault)$fatal(1,"actual issuer/profile composition failed commands%0d dones%0d END%0d issuerfault%0d sourcefault%0d",seen,dones,ended,ifault,pfault);
  $display("HC_ISSUER_PROGRAMME PASS actualPWissuer sixkindcommands6 metadata144 fixededges6 completions6 END1");$finish;
 end
 always @(posedge sc)if(rn)begin st=st+1;if(jv)launch=st;#1;if(sd[8])dones=dones+1;if(jdone)ended=ended+1;end
 // Declared HC public completion boundary only: this test contains no HC
 // arithmetic and is not native HC/chip qualification. The actual HC owner
 // supplies source-pinned six-kind durations for the separate native replay.
 always @(posedge dc)if(rn)begin
  dt=dt+1;serial_done<=0;
  if(hc[84])begin return_age=1;saved_tag={hc[83],hc[6:0]};end
  else if(return_age>0)begin
   if(return_age==7)begin serial_done<={1'b1,saved_tag};return_age=-1;end
   else return_age=return_age+1;
  end
  #1;
  if(hc[84])begin
   if(dt!=(launch/4)*3+17+18*seen)$fatal(1,"actual issue source edge moved");
   if(hc[83:0]!=={1'b0,10'd37,21'd111,21'd222,24'((seen<<20)+seen*32),7'(seen)})$fatal(1,"actual PW command identity moved");
   if(yt!==32'h81c00000+seen*32||da!==32'h81c00003+seen*32)$fatal(1,"actual ROM profile fields moved");
   for(j=0;j<20;j=j+1)if(post[32*j+:32]!==32'h81c00004+seen*32+j)$fatal(1,"actual ROM POST profile moved");
   seen=seen+1;
  end
 end
 initial begin #10000;$fatal(1,"lost actual issuer programme");end
endmodule
