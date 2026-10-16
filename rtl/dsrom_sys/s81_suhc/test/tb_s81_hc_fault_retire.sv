`timescale 1ns/1ps
// Actual CSEQ+CPIN+adapter, exact wrapper FF projection, optional actual static_c8 consumer.
// CONTROL ONLY: fixed writer completion and registered CCF fault are declared boundaries.
module tb_s81_hc_fault_retire;
 reg ck=0,cvk=0,fclk=0,rn=0;always #3 ck=~ck;always #4 cvk=~cvk;
 integer phase=0,relay=0,inject=-1,retire=600,mode=0,integrated=0,writer_gap=88,base_done=0;
 initial begin if($value$plusargs("PHASE=%d",phase))begin end#(phase);forever #3 fclk=~fclk;end
 integer cc=0,fc=0,vc=-1,cmd_at=-1,done_at=-1,kits=0;reg origin=0,rq=0,writer=0;
 reg[84:0] direct_cmd=0;wire[84:0] cmds[0:12];wire[84:0] command=integrated?cmds[2]:direct_cmd;
 wire[8:0] hd;wire[1:0] hs;wire[5:0]st;wire[53:0]kd;
 reg[35:0]pw=0;reg[52:0]ks=0;reg[34:0]image[0:63];integer nwords=0;
 ot_hc_fault_control_projection #(.HIER(1))hc(.ck(ck),.rst(rn),.c_cmd(command),.c_done(hd),.c_st(hs),
  .fault_boundary(relay?rq:origin),.writer_boundary(writer),.y_v(1'b0),.y_rdy(),.y_d(8192'd0),
  .rq_v(),.rq_row(),.rs_v(2'd0),.rs_d(1024'd0),.wq_v(),.wq_row(),.wq_mask(),.wq_d(),
  .t_tf0(),.t_tf1(),.t_tf2(),.f_tr0(0),.f_tr1(0),.f_tr2(0));
 dsfd_stage_seq_static_c8 #(.NOPS(4),.STAGE(7))seq(.ck(ck),.rst(rn),.ckv(cvk),.rsv(rn),
  .f_ks(ks),.t_kd(kd),.f_pw(pw),.f_plen(8'd3),.t_st(st),
  .c0(cmds[0]),.c1(cmds[1]),.c2(cmds[2]),.c3(cmds[3]),.c4(cmds[4]),.c5(cmds[5]),.c6(cmds[6]),.c7(cmds[7]),.c12(cmds[12]),
  .d0(9'd0),.d1(9'd0),.d2(hd),.d3(9'd0),.d4(9'd0),.d5(9'd0),.d6(9'd0),.d7(9'd0),.d12(9'd0),
  .s0(2'd2),.s1(2'd2),.s2(hs),.s3(2'd2),.s4(2'd2),.s5(2'd2),.s6(2'd2),.s7(2'd2),.s12(2'd2));
 reg kit_seen=0,fault_seen=0;wire status_fault=integrated?st[5]:hs[0];
 initial begin
  if($value$plusargs("RELAY=%d",relay))begin endif($value$plusargs("INJECT=%d",inject))begin end
  if($value$plusargs("RETIRE=%d",retire))begin endif($value$plusargs("MODE=%d",mode))begin end
  if($value$plusargs("INTEGRATED=%d",integrated))begin endif($value$plusargs("NWORDS=%d",nwords))begin end
  if($value$plusargs("BASE_DONE=%d",base_done))begin end
  if(integrated)$readmemh("hc_program.hex",image);
  #30;rn=1;
 end
 always @(negedge cvk)begin
  pw=0;ks=0;
  if(integrated&&vc>=10&&vc<10+nwords)pw={1'b1,image[vc-10]};
  if(integrated&&vc==199)ks={1'b1,10'd37,21'd21946,21'd1048575};
 end
 always @(posedge cvk)begin vc<=vc+1;#0.001;
  if(kd[53])begin kits=kits+1;kit_seen=1;$display("EVENT KIT cc=%0d vc=%0d t=%0.3f status=%h",cc,vc,$realtime,st);end
 end
 always @(posedge fclk)begin
  fc<=fc+1;
  if(rn&&cmd_at>=0&&fc+1==cmd_at+inject&&inject>=0)origin<=1;
  rq<=origin;
 end
 always @(posedge ck)begin
  cc<=cc+1;
  direct_cmd<=0;
  if(!integrated&&cc+1==40)direct_cmd<={1'b1,53'd0,24'h100500,7'd0};
  if(cmd_at>=0&&cc+1==cmd_at+writer_gap)writer<=1;else writer<=0;
  if(status_fault)fault_seen<=1;
  #0.001;
  if(command[84]&&cmd_at<0)begin cmd_at=cc;$display("EVENT CMD cc=%0d t=%0.3f",cc,$realtime);end
  if(hd[8])begin done_at=cc;if(!integrated)kit_seen=1;$display("EVENT DONE cc=%0d rel=%0d t=%0.3f status=%h",cc,cc-cmd_at,$realtime,hs);end
  $display("EDGE cc=%0d fc=%0d t=%0.3f origin=%0d input=%0d yfl=%0d nflt=%0d pflt=%0d wrapper=%0d internal=%0d ready=%0d run=%0d raw=%0d dd=%0d ndone=%0d done=%0d c8ef=%0d c8st=%h kit=%0d",
   cc,fc,$realtime,origin,(relay?rq:origin),hc.u_seq.yfl,hc.nflt,hc.flt,hs[0],hc.u_seq.fault,hc.u_seq.e_r,hc.u_seq.run,
   hc.u_seq.d_v,hc.u_seq.dd[8],hc.ndv,hd[8],seq.u_s.engine_fault,st,kd[53]);
  if(cmd_at>=0&&cc==cmd_at+retire)begin
   if(done_at<0||hc.u_seq.fault||!hc.u_seq.e_r||hc.u_seq.run)$fatal(1,"actual control invalid at fixed observer");
   if(integrated&&(kits!=1||seq.u_s.u_issue.fault))$fatal(1,"actual c8 KIT/calendar invalid kits=%0d code=%0d",kits,seq.u_s.code);
   if(inject>=0&&!status_fault)$fatal(1,"actual late fault missing at fixed observer");
   if(inject<0&&status_fault)$fatal(1,"unexpected baseline status fault");
   // Both modes are judged on this SAME compiled observer edge. Mutant claims
   // success from actual KIT alone; it must fail on the observed actual flag.
   if(mode!=0&&kit_seen&&status_fault)$fatal(1,"KIT_ONLY_MUTANT actual KIT accepted despite actual fault flag");
   if(!kit_seen)$fatal(1,"no actual KIT/done at fixed observer");
   $display("HC_FAULT_RETIRE PASS integrated=%0d phase=%0d relay=%0d inject=%0d seal=%0d done=%0d fault=%0d admitted=%0d",integrated,phase,relay,inject,retire,done_at-cmd_at,status_fault,!status_fault);
   $finish;
  end
 end
 initial begin #20000;$fatal(1,"control probe timeout");end
endmodule
