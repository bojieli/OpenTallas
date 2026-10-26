`timescale 1ns/1ps
module tb_seqhost_timing;
 reg ck=0;always #0.5 ck=~ck;
 reg rst_n=0;reg[514:0]f_host=0;reg[52:0]f_ks=0;
 wire[275:0]vo_n,vo_s;wire[76:0]t_host;wire[53:0]t_kd;
 wire cw_v;wire[9:0]cw_a;wire[255:0]cw_d;
 dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(0),.STATIC_KS6(0)) dut(
 .ck(ck),.rst_n(rst_n),.tap_k(8'd0),.sink_k(8'd0),.vi_s(276'd0),.vi_n(276'd0),.vo_s(vo_s),.vo_n(vo_n),
 .select_hbe(1'b0),.hbe_f_host(515'd0),.starter_f_ks(53'd0),.hbe_ks_slot(3'd0),
 .f_host(f_host),.t_host(t_host),.f_lf(4'b0101),.f_ks(f_ks),.t_kd(t_kd),
 .sid_ri(1'b0),.vid_ri(1'b0),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hc_w(9'd0),.s_hc_e(9'd0),
 .st_rg_w(2'b01),.st_rg_e(2'b01),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.mu_rt_7n(32'd0),.mu_rt_0n(32'd0));
 wire[4:0]cmd_v=dut.u_seqhost.u.u_u.u_l1.cv;
 wire[419:0]cmd_d=dut.u_seqhost.u.u_u.u_l1.cd;
 wire job_accept=dut.u_seqhost.u.u_u.u_l1.u_iss.do_accept;
 wire[1:0]phase=dut.u_seqhost.u.u_u.u_l1.u_iss.phase_q;
 reg[185:0]templ[0:3];integer cyc=0,errors=0,job=-1,ks_edge=-1,accept_edge=-1,cmd_edge[0:4];
 integer counts_n=0,counts_s=0,counts_g=0,kits=0,jobs=0;reg[275:0]expect_n[0:3],expect_s[0:3];
 integer pending_n[0:3],pending_s[0:3],next_n=0,next_s=0;
 integer mut_payload=0,launch_phase=0;reg[9:0]expect_cwa;reg[255:0]expect_cwd;
 function[514:0]csr(input[7:0]idx,input[511:0]data);reg[511:0]d;begin d=data;d[7:0]=idx;csr={2'd0,d,1'b1};end endfunction
 task host(input[514:0]word_);begin @(negedge ck);f_host=word_;@(negedge ck);f_host=0;repeat(7)@(negedge ck);end endtask
 task pw(input integer a,input[27:0]v);reg[511:0]d;begin d=0;d[102:96]=a;d[59:32]=v;host(csr(8'h10,d));end endtask
 task row(input integer index,input integer eng,iss,done_,arg_);reg[75:0]r;integer k;begin
 r={24'(done_),24'(iss),4'(eng),24'(arg_)};for(k=0;k<3;k=k+1)pw(index,{2'(k),r[26*k+:26]});end endtask
 function[275:0]word(input[185:0]t,input[83:0]c);reg[185:0]p;begin p=t;
 if(c[15:14]==1)p[134+:52]=c[82:31];if(c[15:14]==2)p[165+:21]=c[72:52];
 word=0;word[0]=1;word[12:9]=4;word[21+:186]=p;end endfunction
 always @(posedge ck)begin
  cyc=cyc+1;
  if(rst_n&&f_ks[52])begin ks_edge=cyc;jobs=jobs+1;$display("SEQ_KS job=%0d edge=%0d phase=%0d",job,cyc,phase);end
  if(rst_n&&job_accept)begin accept_edge=cyc;$display("SEQ_ACCEPT job=%0d edge=%0d ks_delta=%0d",job,cyc,cyc-ks_edge);end
  #0.01;
  if(rst_n)begin
   for(integer e=0;e<5;e=e+1)if(cmd_v[e])begin
    cmd_edge[e]=cyc;$display("SEQ_CMD job=%0d eng=%0d op=%0d edge=%0d ks_delta=%0d accept_delta=%0d",job,e,cmd_d[e*84+:7],cyc,cyc-ks_edge,cyc-accept_edge);
    if(e==0)begin expect_n[next_n]=word(templ[cmd_d[e*84+7+:7]],cmd_d[e*84+:84]);pending_n[next_n]=cyc;next_n=next_n+1;end
    if(e==2)begin expect_cwa={2'b10,7'd0,cmd_d[2*84+14]};expect_cwd={214'd0,templ[cmd_d[2*84+7+:7]][41:0]};end
    if(e==1)begin expect_s[next_s]=word(templ[cmd_d[e*84+7+:7]],cmd_d[e*84+:84]);pending_s[next_s]=cyc;next_s=next_s+1;end
   end
   if(vo_n[0])begin
    if(counts_n>=next_n||vo_n!==(expect_n[counts_n]^(mut_payload?276'd1<<30:276'd0)))begin errors=errors+1;$display("SEQ_BAD north edge=%0d",cyc);end
    $display("SEQ_OUT job=%0d port=vo_n edge=%0d command_delta=%0d ks_delta=%0d word=%h",job,cyc,cyc-pending_n[counts_n],cyc-ks_edge,vo_n);
    counts_n=counts_n+1;
   end
   if(vo_s[0])begin
    if(counts_s>=next_s||vo_s!==(expect_s[counts_s]^(mut_payload?276'd1<<30:276'd0)))begin errors=errors+1;$display("SEQ_BAD south edge=%0d",cyc);end
    $display("SEQ_OUT job=%0d port=vo_s edge=%0d command_delta=%0d ks_delta=%0d word=%h",job,cyc,cyc-pending_s[counts_s],cyc-ks_edge,vo_s);
    counts_s=counts_s+1;
   end
   if(cw_v)begin if(cw_a!==expect_cwa||cw_d!==expect_cwd)begin errors=errors+1;$display("SEQ_BAD CW payload");end counts_g=counts_g+1;$display("SEQ_CW job=%0d edge=%0d command_delta=%0d a=%0d d=%h",job,cyc,cyc-cmd_edge[2],cw_a,cw_d);end
   if(t_kd[53])begin if(t_kd!=={1'b1,21'(77+job),10'(31+job),21'(55+job),1'b0})begin errors=errors+1;$display("SEQ_BAD KIT payload got=%h",t_kd);end kits=kits+1;$display("SEQ_KIT job=%0d edge=%0d ks_delta=%0d",job,cyc,cyc-ks_edge);end
   if(t_host[75])begin errors=errors+1;if(errors<5)$display("SEQ_FAULT edge=%0d status=%h iss_code=%0d sealed=%b cfg=%b run=%b",cyc,t_host,dut.u_seqhost.u.u_u.u_l1.u_iss.fault_code,dut.u_seqhost.u.u_u.u_l1.u_iss.sealed,dut.u_seqhost.u.u_u.u_l1.u_iss.cfg_fault,dut.u_seqhost.u.u_u.u_l1.u_iss.run_fault);end
  end
 end
 integer i;reg[511:0]d;
 initial begin
  if($value$plusargs("mut_payload=%d",mut_payload))begin end
  if($value$plusargs("phase=%d",launch_phase))begin end
  for(i=0;i<4;i=i+1)begin templ[i]={26'h128910+i,32'hfedcba98+i,64'hffeeddccbbaa9988,64'h0706050403020100+i};end
  repeat(30)@(negedge ck);rst_n=1;repeat(80)@(negedge ck);
  d=0;d[39:32]=6;host(csr(8'h11,d));pw(0,(28'd3<<26)|(28'd6<<9));
  row(0,0,12,17,0);row(1,1,24,29,1|(1<<7));row(2,0,36,41,2|(2<<7));row(3,2,48,53,3);
  row(4,14,72,0,0);row(5,15,100,0,0);pw(0,(28'd3<<26)|(28'd1<<25)|(28'd6<<9));
  for(i=0;i<4;i=i+1)begin d=0;d[14:8]=i;d[16+:186]=templ[i];host(csr(8'h13,d));end
  // Configure the actual always-present MU tracker. Gaps152 are the
  // static start spacing; RL79 is the measured diagnostic KIT offset for
  // this calendar (KIT issue72), not an unmeasured compiler default.
  d=0;d[57:32]=(26'd1<<25)|26'd152;host(csr(8'h15,d));
  d=0;d[57:32]=(26'd1<<25)|26'd152;host(csr(8'h15,d));
  d=0;d[57:32]=(26'd1<<25)|(26'd1<<24)|26'd79;host(csr(8'h15,d));
  for(i=0;i<8;i=i+1)begin
   d=0;d[57:32]=(26'd1<<25)|26'(i)|26'((i%4)<<9);host(csr(8'h16,d));
   d=0;d[57:32]=(26'd1<<25)|(26'd1<<21)|26'(8+i);host(csr(8'h16,d));
   d=0;d[57:32]=(26'd1<<25)|(26'd2<<21);host(csr(8'h16,d));
   d=0;d[57:32]=(26'd1<<25)|(26'd2<<21)|26'd1;host(csr(8'h16,d));
  end
  repeat(250)@(negedge ck);
  for(i=0;i<2;i=i+1)begin
   job=i;while(phase!=2'(launch_phase))@(negedge ck);
   f_ks={1'b1,10'(31+i),21'(77+i),21'(55+i)};@(negedge ck);f_ks=0;
   repeat(150)@(negedge ck);
  end
  repeat(30)@(negedge ck);
  if(jobs!=2||counts_n!=4||counts_s!=2||counts_g!=2||kits!=2)errors=errors+1;
  $display("SEQ_TIMING jobs=%0d north=%0d south=%0d gunit=%0d kits=%0d errors=%0d",jobs,counts_n,counts_s,counts_g,kits,errors);
  if(errors==0)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
