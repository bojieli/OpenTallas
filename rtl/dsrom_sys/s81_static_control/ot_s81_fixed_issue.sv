`timescale 1ns/1ps
`default_nettype none
// Native S81 command ABI: {slot,user10,pos21,tok21,arg24,op7}.
// Each calendar row is {done24,issue24,engine4,arg24}. Engine14=KIT,
// engine15=END. Three26-bit PW payloads load one actual76-bit storage row.
// Page3/address0 is BEGIN/SEAL: {seal,zero8,length8,start_phase2,stage7}.
// Command pin cycle0 is exactly one clock after job_v is sampled. Phase is
// the free-running clock index since reset; its physical serial relationship
// must be established by the measured die/startup contract.
// Two contexts may execute the same immutable calendar. No runtime signal
// changes an issue, KIT or END edge. Availability/completions only detect faults.
module ot_s81_fixed_issue #(
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
 reg bad;reg[23:0]end_cycle,kit_cycle;wire[NENG-1:0]seen_cmd;
 reg[3:0]eng;reg[7:0]tag;
 wire[NENG-1:0]legit_done,duplicate_issue;
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
// Parallel row event cones. No procedural variable-index write or row-priority
 // path feeds the sticky runtime fault. Every row retains its original calendar.
 wire[NOPS-1:0]issue_at[0:1],done_at[0:1],done_ok[0:1];
 reg[NOPS-1:0]iss_q[0:1],dne_q[0:1];
 // age_n: the value age[s] takes on this edge (start -> 0, running -> +1, else held); start_n: slot s starts on this edge.
 wire start_ok=job_v&&!(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q)||pw_v);
 wire[1:0]start_n={start_ok&&next_slot,start_ok&&!next_slot};
 wire[23:0]age_n[0:1];
 assign age_n[0]=start_n[0]?24'd0:active[0]?age[0]+1'b1:age[0];
 assign age_n[1]=start_n[1]?24'd0:active[1]?age[1]+1'b1:age[1];
 genvar ps,pr,pe,pt;
 generate for(ps=0;ps<2;ps=ps+1)begin:g_events_slot
  for(pr=0;pr<NOPS;pr=pr+1)begin:g_row
   wire[3:0]re=mem[pr][27:24];
   // Registered one-edge-ahead row hits (c9 n4): the 24-bit calendar compares run against the value age takes on
   // this edge (age_n), so every runtime event cone starts at a flop.  iss_q(t) == (age(t) == issue + adj) and
   // dne_q(t) == (age(t) != 0 && done == age(t) - 1) exactly, because mem/length cannot change while a slot runs
   // (writes while busy fault and are dropped; a write on the start edge is a run fault, see job_v below).
   assign issue_at[ps][pr]=active[ps]&&iss_q[ps][pr];
   assign done_at[ps][pr]=active[ps]&&dne_q[ps][pr];
   // Row completion hit: the row's own constant {slot, op} bit of every engine's one-hot tag, selected by the row's
   // engine (explicit nets; a function call in a continuous assignment would not track tag_oh).
   wire[NENG-1:0]hv;
   for(pt=0;pt<NENG;pt=pt+1)begin:g_hv
    assign hv[pt]=tag_oh[pt][ps*128+((pr+OP_BASE)&127)];
   end
   assign done_ok[ps][pr]=(re<NENG)&&hv[re]&&pending[ps][pr];
  end
 end
 for(pe=0;pe<NENG;pe=pe+1)begin:g_events_engine
  localparam integer LEAVES=1<<$clog2(2*NOPS);
  wire[2*NOPS-1:0]ih,dh;
  for(pr=0;pr<NOPS;pr=pr+1)begin:g_row
   assign ih[pr]=issue_at[0][pr]&&mem[pr][27:24]==pe&&ENG_PRESENT[pe];
   assign ih[NOPS+pr]=issue_at[1][pr]&&mem[pr][27:24]==pe&&ENG_PRESENT[pe];
   assign dh[pr]=done_at[0][pr]&&done_ok[0][pr]&&mem[pr][27:24]==pe;
   assign dh[NOPS+pr]=done_at[1][pr]&&done_ok[1][pr]&&mem[pr][27:24]==pe;
  end
  wire[2*LEAVES-1:1]any_hit,multi_hit;
  for(pt=0;pt<LEAVES;pt=pt+1)begin:g_leaf
   if(pt<2*NOPS)assign any_hit[LEAVES+pt]=ih[pt];
   else assign any_hit[LEAVES+pt]=1'b0;
   assign multi_hit[LEAVES+pt]=1'b0;
  end
  for(pt=1;pt<LEAVES;pt=pt+1)begin:g_reduce
   assign any_hit[pt]=any_hit[2*pt]|any_hit[2*pt+1];
   assign multi_hit[pt]=multi_hit[2*pt]|multi_hit[2*pt+1]|
                         (any_hit[2*pt]&any_hit[2*pt+1]);
  end
  assign seen_cmd[pe]=any_hit[1];
  assign duplicate_issue[pe]=multi_hit[1];
  assign legit_done[pe]=|dh;
 end endgenerate
 wire bad_completion=|(done_at[0]&~done_ok[0])|||(done_at[1]&~done_ok[1]);
 genvar hs,hr;
 generate for(hs=0;hs<2;hs=hs+1)begin:g_hit_slot
  for(hr=0;hr<NOPS;hr=hr+1)begin:g_hit_row
   always @(posedge clk or negedge rst_n)
    if(!rst_n)begin iss_q[hs][hr]<=1'b0;dne_q[hs][hr]<=1'b0;end
    else begin
     iss_q[hs][hr]<=hr<length_q&&age_n[hs]==mem[hr][51:28]+((MUT==1&&mem[hr][27:24]<14)?24'd1:24'd0);
     // age_n != 0 and age_n - 1 == age when the slot keeps running; a starting slot has age_n == 0 (no completion).
     dne_q[hs][hr]<=hr<length_q&&mem[hr][27:24]<14&&!start_n[hs]&&age[hs]!=24'hffffff&&mem[hr][75:52]==age[hs];
    end
  end
 end endgenerate
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
   job_done<=0;job_kdone<=0;issued=0;fev=0;
   for(e=0;e<NENG;e=e+1)if(cmd_v[e])issued=issued+1;
   if(pw_v)begin
    if(busy||validating)begin fev[1]=1'b1;end
    else if(pw_d[27:26]==3)begin
     if(pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS)begin
      sealed<=0;fev[2]=1'b1;
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
    end else if(!begun||pw_a>=NOPS)begin fev[4]=1'b1;end
    else begin
     sealed<=0;
     case(pw_d[27:26])
      0:mem[pw_a][25:0]<=pw_d[25:0];
      1:mem[pw_a][51:26]<=pw_d[25:0];
      2:begin mem[pw_a][75:52]<=pw_d[23:0];if(pw_d[25:24]!=0)begin fev[4]=1'b1;end end
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
     if(bad)begin fev[3]=1'b1;end
    end else scan_index<=scan_index+1'b1;
   end
   if(job_v)begin
    if(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q)||pw_v)begin
     fev[5]=1'b1;
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
    if(age[s]==24'hffffff)begin fev[7]=1'b1;end
    for(i=0;i<NOPS;i=i+1)if(i<length_q)begin
     eng=mem[i][27:24];
     if(done_at[s][i]&&done_ok[s][i])pending[s][i]<=0;
     if(issue_at[s][i])begin
      if(eng==15)begin active[s]<=0;job_done<=1;done_slot<=1'(s);if(!has_kit)begin job_kdone<=1;kit_tok<=tokens[s];end end
      else if(eng==14)begin job_kdone<=1;kit_tok<=tokens[s];end
      else if(eng<NENG&&ENG_PRESENT[eng])begin
       pending[s][i]<=1;
      end else begin fev[10]=1'b1;end
     end
    end
   end
   if((|duplicate_issue)||(|(seen_cmd&~engine_available)))begin fev[9]=1'b1;end
   if(bad_completion)fev[8]=1'b1;
   if(|(dv_q&~legit_done))begin fev[6]=1'b1;end
   run_fault<=run_fault|(|fev[10:5]);
   cfg_fault<=cfg_fault|(|fev[4:1]);
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
    m0=issue_at[0][j]&&mem[j][27:24]==ge&&ENG_PRESENT[ge];
    m1=issue_at[1][j]&&mem[j][27:24]==ge&&ENG_PRESENT[ge];
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
