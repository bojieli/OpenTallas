`timescale 1ns/1ps
`default_nettype none
// FROZEN reference copy of ot_s81_fixed_issue at bf7c0023f (pre-n4), module renamed; used only by issue_diff_gate.sh.
// Native S81 command ABI: {slot,user10,pos21,tok21,arg24,op7}.
// Each calendar row is {done24,issue24,engine4,arg24}. Engine14=KIT,
// engine15=END. Three26-bit PW payloads load one actual76-bit storage row.
// Page3/address0 is BEGIN/SEAL: {seal,zero8,length8,start_phase2,stage7}.
// Command pin cycle0 is exactly one clock after job_v is sampled. Phase is
// the free-running clock index since reset; its physical serial relationship
// must be established by the measured die/startup contract.
// Two contexts may execute the same immutable calendar. No runtime signal
// changes an issue, KIT or END edge. Availability/completions only detect faults.
module ot_s81_fixed_issue_ref #(
 parameter integer NOPS=128, NENG=13, STAGE=0, OP_BASE=0,
 parameter [NENG-1:0] ENG_PRESENT=13'h1fff,
 parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire pw_v,input wire[6:0]pw_a,input wire[27:0]pw_d,
 input wire[7:0]prog_len,
 input wire job_v,input wire[9:0]job_user,input wire[20:0]job_pos,job_tok,
 output wire job_rdy,output wire busy,
 output reg job_done,job_kdone,output reg done_slot,output reg[20:0]kit_tok,
 output reg[NENG-1:0]cmd_v,output reg[NENG*84-1:0]cmd_d,
 input wire[NENG-1:0]engine_available,dn_v,
 input wire[NENG*8-1:0]dn_tag,
 output wire fault,output reg[3:0]fault_code,
 output reg[31:0]st_jobs,st_cmds,
 output wire[1:0]phase
);
 reg[75:0]mem[0:NOPS-1];
 reg[2:0]loaded[0:NOPS-1];
 reg[7:0]length_q;reg[1:0]phase_q,start_phase_q;
 reg begun,sealed,cfg_fault,run_fault,has_kit,validating;
 reg[7:0]scan_index,scan_native;reg scan_bad;reg[1:0]scan_ends,scan_kits;
 reg[23:0]scan_max_done,scan_end_cycle,scan_kit_cycle;
 reg[1:0]active;reg next_slot;
 reg[9:0]users[0:1];reg[20:0]positions[0:1],tokens[0:1];
 reg[23:0]age[0:1];reg[NOPS-1:0]pending[0:1];
 reg[NENG-1:0]dv_q;reg[NENG*8-1:0]dt_q;
 assign busy=|active;assign job_rdy=!active[next_slot];
 assign fault=cfg_fault|run_fault;assign phase=phase_q;
 integer i,s,e,n,op,slot,issued,max_done,end_count,kit_count;
 reg bad;reg[23:0]end_cycle,kit_cycle;reg[NENG-1:0]seen_cmd;
 reg[3:0]eng;reg[7:0]tag;
 reg[NENG-1:0]legit_done;
 // Fault code (S-ELEM-PQ 10-15, c9 route lint: age -> fault_code 40 levels / ~1,444 ps, s7 -> fault_code 39 levels):
 // each cycle's fault events are collected as flags (fev) and registered; fault_code takes the first registered
 // event one edge later in a fixed priority. run_fault/cfg_fault are unchanged (same edge). Engine availability
 // is checked after the row loop against the per-engine issue set (register-only cone; the input enters at one AND).
 reg[10:0]fev,fev_q;
 // Completion tag decode (S-ELEM-PQ 10-15): the c9 gate's synthesis stalled (>2,700 s, yosys SHARE) on the per-row
 // runtime part-select dt_q[8*eng+:8] unrolled over 2 slots x NOPS rows. Each engine's registered completion tag is
 // decoded once to one-hot ({slot, op}); a row then needs only its own constant tag bit per engine, AND-OR'd by the
 // row's engine one-hot. Same edge, same check (dv_q[eng] && tag == {s, op}).
 wire[255:0]tag_oh[0:NENG-1];
 genvar gto;
 generate for(gto=0;gto<NENG;gto=gto+1)begin:g_tag_oh
  assign tag_oh[gto]=dv_q[gto]?(256'd1<<dt_q[8*gto+:8]):256'd0;
 end endgenerate
 function automatic row_hit(input [3:0] e,input integer sl,input integer op);
  integer k;
  begin row_hit=1'b0;for(k=0;k<NENG;k=k+1)if(e==k)row_hit=row_hit|tag_oh[k][{sl[0],op[6:0]}];end
 endfunction
`ifndef SYNTHESIS
 initial begin
  if(NOPS<2||NOPS>128||NENG<1||NENG>14||STAGE<0||STAGE>127||OP_BASE<0||OP_BASE+NOPS>128)$fatal(1,"invalid native S81 issuer shape");
 end
`endif
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   length_q<=0;phase_q<=0;start_phase_q<=0;begun<=0;sealed<=0;cfg_fault<=0;run_fault<=0;
   validating<=0;scan_index<=0;scan_native<=0;scan_bad<=0;scan_ends<=0;scan_kits<=0;scan_max_done<=0;scan_end_cycle<=0;scan_kit_cycle<=0;
   active<=0;next_slot<=0;has_kit<=0;job_done<=0;job_kdone<=0;done_slot<=0;kit_tok<=0;
   fev_q<=0;st_jobs<=0;st_cmds<=0;dv_q<=0;dt_q<=0;
   for(i=0;i<NOPS;i=i+1)loaded[i]<=0;
   for(s=0;s<2;s=s+1)begin users[s]<=0;positions[s]<=0;tokens[s]<=0;age[s]<=0;pending[s]<=0;end
  end else begin
   phase_q<=phase_q+1'b1;dv_q<=dn_v;dt_q<=dn_tag;
   job_done<=0;job_kdone<=0;seen_cmd=0;legit_done=0;issued=0;fev=0;
   for(e=0;e<NENG;e=e+1)if(cmd_v[e])issued=issued+1;
   if(pw_v)begin
    if(busy||validating)begin cfg_fault<=1;fev[1]=1'b1;end
    else if(pw_d[27:26]==3)begin
     if(pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS)begin
      cfg_fault<=1;sealed<=0;fev[2]=1'b1;
     end else if(!pw_d[25])begin
      begun<=1;sealed<=0;length_q<=pw_d[16:9];start_phase_q<=pw_d[8:7];
      for(i=0;i<NOPS;i=i+1)loaded[i]<=0;
     end else begin
      // Fixed boot scan: one row per stream edge, independent of data.
      // This removes a 128-row max/reduction from the runtime clock path.
      validating<=1;sealed<=0;scan_index<=0;scan_native<=0;scan_ends<=0;scan_kits<=0;
      scan_max_done<=0;scan_end_cycle<=0;scan_kit_cycle<=0;
      scan_bad<=!begun||length_q!=pw_d[16:9]||start_phase_q!=pw_d[8:7]||prog_len!=length_q;
     end
    end else if(!begun||pw_a>=NOPS)begin cfg_fault<=1;fev[4]=1'b1;end
    else begin
     sealed<=0;
     case(pw_d[27:26])
      0:mem[pw_a][25:0]<=pw_d[25:0];
      1:mem[pw_a][51:26]<=pw_d[25:0];
      2:begin mem[pw_a][75:52]<=pw_d[23:0];if(pw_d[25:24]!=0)begin cfg_fault<=1;fev[4]=1'b1;end end
     endcase
     loaded[pw_a][pw_d[27:26]]<=1'b1;
    end
   end
   if(validating)begin
    bad=scan_bad;end_count=scan_ends;kit_count=scan_kits;n=scan_native;
    max_done=scan_max_done;end_cycle=scan_end_cycle;kit_cycle=scan_kit_cycle;
    if(scan_index<length_q)begin
     if(loaded[scan_index]!=3'b111)bad=1;
     eng=mem[scan_index][27:24];
     if(eng==15)begin end_count=end_count+1;end_cycle=mem[scan_index][51:28];if(mem[scan_index][75:52]!=0||mem[scan_index][23:0]!=0)bad=1;end
     else if(eng==14)begin kit_count=kit_count+1;kit_cycle=mem[scan_index][51:28];if(mem[scan_index][75:52]!=0||mem[scan_index][23:0]!=0)bad=1;end
     else if(eng>=NENG||!ENG_PRESENT[eng])bad=1;
     else begin
      n=n+1;if(mem[scan_index][75:52]<=mem[scan_index][51:28])bad=1;
      if(mem[scan_index][75:52]>max_done)max_done=mem[scan_index][75:52];
     end
    end
    scan_bad<=bad;scan_native<=8'(n);scan_ends<=end_count>2?2'd3:2'(end_count);scan_kits<=kit_count>2?2'd3:2'(kit_count);
    scan_max_done<=24'(max_done);scan_end_cycle<=end_cycle;scan_kit_cycle<=kit_cycle;
    if(scan_index==NOPS-1)begin
     validating<=0;
     if(end_count!=1||kit_count>1||n==0||end_cycle<=max_done||(kit_count==1&&kit_cycle>=end_cycle))bad=1;
     sealed<=!bad&&!cfg_fault;has_kit<=kit_count==1;
     if(bad)begin cfg_fault<=1;fev[3]=1'b1;end
    end else scan_index<=scan_index+1'b1;
   end
   if(job_v)begin
    if(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q))begin
     run_fault<=1;fev[5]=1'b1;
    end else begin
     active[next_slot]<=1;age[next_slot]<=0;pending[next_slot]<=0;
     users[next_slot]<=job_user;positions[next_slot]<=job_pos;tokens[next_slot]<=job_tok;
     next_slot<=~next_slot;st_jobs<=st_jobs+1;
    end
   end
   // Completions are verified against fixed rows below; no dynamic
   // op-indexed program read or completion-driven scheduling is required.
   for(s=0;s<2;s=s+1)if(active[s])begin
    age[s]<=age[s]+1'b1;
    if(age[s]==24'hffffff)begin run_fault<=1;fev[7]=1'b1;end
    for(i=0;i<NOPS;i=i+1)if(i<length_q)begin
     eng=mem[i][27:24];
     if(eng<14&&age[s]!=0&&mem[i][75:52]==age[s]-1'b1)begin
      if(!row_hit(eng,s,i+OP_BASE)||!pending[s][i])begin run_fault<=1;fev[8]=1'b1;end
      else begin legit_done[eng]=1;pending[s][i]<=0;end
     end
     if(age[s]==mem[i][51:28]+((MUT==1&&eng<14)?24'd1:24'd0))begin
      if(eng==15)begin active[s]<=0;job_done<=1;done_slot<=1'(s);if(!has_kit)begin job_kdone<=1;kit_tok<=tokens[s];end end
      else if(eng==14)begin job_kdone<=1;kit_tok<=tokens[s];end
      else if(eng<NENG&&ENG_PRESENT[eng])begin
       if(seen_cmd[eng])begin run_fault<=1;fev[9]=1'b1;end
       seen_cmd[eng]=1;
       pending[s][i]<=1;
      end else begin run_fault<=1;fev[10]=1'b1;end
     end
    end
   end
   if(|(seen_cmd&~engine_available))begin run_fault<=1;fev[9]=1'b1;end
   if(|(dv_q&~legit_done))begin run_fault<=1;fev[6]=1'b1;end
   fev_q<=fev;
   st_cmds<=st_cmds+issued;
  end
 end
 // fault_code: first registered event, priority = the former last-assignment order (6, 10, 9, 8, 7, 5, 3, 4, 2, 1).
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)fault_code<=0;
  else if(fault_code==0)begin
   if(fev_q[6])fault_code<=6;else if(fev_q[10])fault_code<=10;else if(fev_q[9])fault_code<=9;else if(fev_q[8])fault_code<=8;
   else if(fev_q[7])fault_code<=7;else if(fev_q[5])fault_code<=5;else if(fev_q[3])fault_code<=3;else if(fev_q[4])fault_code<=4;
   else if(fev_q[2])fault_code<=2;else if(fev_q[1])fault_code<=1;
  end
 end
 // A per-engine OR of compiler-exclusive events avoids a 256-row
 // procedural priority chain. Multiple matches still fault above; their
 // resulting payload is invalid and must be discarded with the job fault.
 genvar ge;
 generate for(ge=0;ge<NENG;ge=ge+1)begin:g_command
  reg[30:0]a0,a1;reg h0,h1,m0,m1;integer j;
  always @*begin
   a0=0;a1=0;h0=0;h1=0;
   m0=0;m1=0;
   for(j=0;j<NOPS;j=j+1)begin
    m0=j<length_q&&mem[j][27:24]==ge&&ENG_PRESENT[ge]&&active[0]&&age[0]==mem[j][51:28]+(MUT==1?24'd1:24'd0);
    m1=j<length_q&&mem[j][27:24]==ge&&ENG_PRESENT[ge]&&active[1]&&age[1]==mem[j][51:28]+(MUT==1?24'd1:24'd0);
    h0=h0|m0;h1=h1|m1;
    a0=a0|({31{m0}}&{mem[j][23:0],7'(j+OP_BASE)});a1=a1|({31{m1}}&{mem[j][23:0],7'(j+OP_BASE)});
   end
  end
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin cmd_v[ge]<=0;cmd_d[84*ge+:84]<=0;end
   else begin
    cmd_v[ge]<=h0|h1;
    cmd_d[84*ge+:84]<=({84{h0}}&{1'b0,(MUT==2?10'd0:users[0]),positions[0],tokens[0],a0})|
                          ({84{h1}}&{1'b1,(MUT==2?10'd0:users[1]),positions[1],tokens[1],a1});
   end
  end
 end endgenerate
endmodule
`default_nettype wire
