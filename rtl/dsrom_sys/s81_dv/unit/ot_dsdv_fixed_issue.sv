`timescale 1ns/1ps
`default_nettype none
// S81U-SEQ3 (2026-10-17): ot_dsdv_fixed_issue = ot_s81_fixed_issue (78c460fbe, unchanged there) with two timing-only
// restructurings for the dsdv_sh_sq leaf (gate 10607befb: 37-level scan_index -> fault_code stage, 2,048-b runtime
// part-select dt_q[8*eng+:8]).  Issue / KIT / END / command / completion-check edges are identical (lock-step vs the
// original in tb_dsdv_seq_host); only the boot seal scan's result lands later:
//   * completion check: {dv_q, dt_q} of the row's engine through a decoded constant-index select (one-hot compare +
//     AND-OR over NENG), not a runtime part-select;
//   * boot seal scan in three registered stages: S0 reads row scan_index into sc_row (the 128:1 row mux alone), S1
//     accumulates the row's checks into scan_* (one row an edge, as before), F evaluates the closing check from the
//     registered totals: the seal (or fault code 3, sticky) lands 2 edges after the original.  A PW word while any
//     stage is live faults (code 1) as one during the scan did.
// S81U-SEQ4 (gate4 @df8031f2c: scan_index[1] 10,119 loads = the 128:1 x 79-b row read as a $shiftx barrel; age ->
// fault_code 41 levels ~1,457 ps, TT -879 ps):
//   * S0 reads the row through a one-hot row pointer sc_oh (shifted one row an edge; AND-OR, ~79 loads a bit);
//   * completion compare registered one edge ahead: dm_q[s][i] = (row i's done cycle == age[s]) captured at t is
//     exactly the original's (mem[i].done == age[s]-1 && age[s] != 0) at t+1 while s stays active (age counts every
//     active edge; rows / length only change while idle); pending clears and the completion check use it;
//   * run-time fault detection (codes 6..10) registered: the flags are captured into rf_q and run_fault / fault_code
//     land one edge later (status only: no issue / KIT / END / command edge depends on run_fault).  Same-edge code
//     priority 6 > 10 > 9 > 8 > 7 (the original's last-statement order, rows folded); duplicate issue per engine
//     (code 9) by a two-hot tree over the engine's row matches instead of the seen_cmd row chain.
//   * gate5 7b7028b78 (TT -77 ps at cmd_d: age compare -> 128-row AND-OR in one stage): the ISSUE compare registered
//     one edge ahead too: im_q[s][i] = (row i's issue cycle (+MUT adj) == age[s] at the next edge), from the next age
//     (accept: 0, active: age + 1) and the next row value (a PW word written on this edge, the only way a row can
//     change while a job can start); command / KIT / END / pending use im_q && i < length_q && active[s].
// S81U-SEQ6 (gate6 e2c0d6208: TT -4.1 ps at im_q: the 24-b next-age increment age + 1 and the 24-b compare in one
//   stage): the next age is held in its own flop ag1[s] (= age[s] + 1 whenever read: loaded with 1 when the job is
//   accepted, together with age <= 0, and stepped with age while active), so im_q compares from a register.  Same
//   values on every edge (age's own increment is unchanged); issue / KIT / END / command edges unchanged.
// Native S81 command ABI: {slot,user10,pos21,tok21,arg24,op7}.
// Each calendar row is {done24,issue24,engine4,arg24}. Engine14=KIT,
// engine15=END. Three26-bit PW payloads load one actual76-bit storage row.
// Page3/address0 is BEGIN/SEAL: {seal,zero8,length8,start_phase2,stage7}.
// Command pin cycle0 is exactly one clock after job_v is sampled. Phase is
// the free-running clock index since reset; its physical serial relationship
// must be established by the measured die/startup contract.
// Two contexts may execute the same immutable calendar. No runtime signal
// changes an issue, KIT or END edge. Availability/completions only detect faults.
module ot_dsdv_fixed_issue #(
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
 reg[23:0]age[0:1],ag1[0:1];reg[NOPS-1:0]pending[0:1];
 reg[NENG-1:0]dv_q;reg[NENG*8-1:0]dt_q;
 assign busy=|active;assign job_rdy=!active[next_slot];
 assign fault=cfg_fault|run_fault;assign phase=phase_q;
 integer i,s,e,n,op,slot,issued,max_done,end_count,kit_count;
 reg bad;reg[23:0]end_cycle,kit_cycle;
 reg[3:0]eng;reg[7:0]tag;
 reg[NENG-1:0]legit_done;
 reg sc_v,sc_last,sc_in,sc_fin;reg[75:0]sc_row;reg[2:0]sc_ld;reg[8:0]dsel_r;
 reg[NOPS-1:0]sc_oh;reg[75:0]rd_row;reg[2:0]rd_ld;
 reg[NOPS-1:0]dm_q[0:1],im_q[0:1];reg[4:0]rf_q;reg f6,f7,f8,f9,f10;wire[NENG-1:0]dup;
 function automatic two_hot(input [255:0] v);
  reg[255:0]a,t;integer w,k;begin a=v;t=0;
   for(w=256;w>1;w=w/2)for(k=0;k<w/2;k=k+1)begin t[k]=t[2*k]|t[2*k+1]|(a[2*k]&a[2*k+1]);a[k]=a[2*k]|a[2*k+1];end
   two_hot=t[0];end
 endfunction
 function automatic [8:0] dsel(input [3:0] e,input [NENG-1:0] v,input [NENG*8-1:0] t);
  integer k;begin dsel=9'd0;for(k=0;k<NENG;k=k+1)dsel=dsel|({9{e==4'(k)}}&{v[k],t[8*k+:8]});end
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
   fault_code<=0;st_jobs<=0;st_cmds<=0;dv_q<=0;dt_q<=0;
   sc_v<=0;sc_last<=0;sc_in<=0;sc_fin<=0;rf_q<=0;
  end else begin
   phase_q<=phase_q+1'b1;dv_q<=dn_v;dt_q<=dn_tag;
   job_done<=0;job_kdone<=0;legit_done=0;issued=0;
   for(e=0;e<NENG;e=e+1)if(cmd_v[e])issued=issued+1;
   if(pw_v)begin
    if(busy||validating||sc_v||sc_fin)begin cfg_fault<=1;if(fault_code==0)fault_code<=1;end
    else if(pw_d[27:26]==3)begin
     if(pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS)begin
      cfg_fault<=1;sealed<=0;if(fault_code==0)fault_code<=2;
     end else if(!pw_d[25])begin
      begun<=1;sealed<=0;length_q<=pw_d[16:9];start_phase_q<=pw_d[8:7];
     end else begin
      // Fixed boot scan: one row per stream edge, independent of data.
      // This removes a 128-row max/reduction from the runtime clock path.
      validating<=1;sealed<=0;scan_index<=0;scan_native<=0;scan_ends<=0;scan_kits<=0;
      scan_max_done<=0;scan_end_cycle<=0;scan_kit_cycle<=0;
      scan_bad<=!begun||length_q!=pw_d[16:9]||start_phase_q!=pw_d[8:7]||prog_len!=length_q;
     end
    end else if(!begun||pw_a>=NOPS)begin cfg_fault<=1;if(fault_code==0)fault_code<=4;end
    else begin
     sealed<=0;
     if(pw_d[27:26]==2&&pw_d[25:24]!=0)begin cfg_fault<=1;if(fault_code==0)fault_code<=4;end
    end
   end
   // S0: read the row (the 128:1 row mux is this stage's only logic)
   sc_v<=validating;sc_fin<=sc_v&&sc_last;
   if(validating)begin
    sc_in<=scan_index<length_q;sc_last<=scan_index==NOPS-1;
    if(scan_index==NOPS-1)validating<=0;else scan_index<=scan_index+1'b1;
   end
   // S1: the registered row's checks accumulate into the scan totals
   if(sc_v)begin
    bad=scan_bad;end_count=scan_ends;kit_count=scan_kits;n=scan_native;
    max_done=scan_max_done;end_cycle=scan_end_cycle;kit_cycle=scan_kit_cycle;
    if(sc_in)begin
     if(sc_ld!=3'b111)bad=1;
     eng=sc_row[27:24];
     if(eng==15)begin end_count=end_count+1;end_cycle=sc_row[51:28];if(sc_row[75:52]!=0||sc_row[23:0]!=0)bad=1;end
     else if(eng==14)begin kit_count=kit_count+1;kit_cycle=sc_row[51:28];if(sc_row[75:52]!=0||sc_row[23:0]!=0)bad=1;end
     else if(eng>=NENG||!ENG_PRESENT[eng])bad=1;
     else begin
      n=n+1;if(sc_row[75:52]<=sc_row[51:28])bad=1;
      if(sc_row[75:52]>max_done)max_done=sc_row[75:52];
     end
    end
    scan_bad<=bad;scan_native<=8'(n);scan_ends<=end_count>2?2'd3:2'(end_count);scan_kits<=kit_count>2?2'd3:2'(kit_count);
    scan_max_done<=24'(max_done);scan_end_cycle<=end_cycle;scan_kit_cycle<=kit_cycle;
   end
   // F: the closing check from the registered totals (saturated counts: != 1 / > 1 as the original's exact counts)
   if(sc_fin)begin
    bad=scan_bad||scan_ends!=2'd1||scan_kits>2'd1||scan_native==0||scan_end_cycle<=scan_max_done||
        (scan_kits==2'd1&&scan_kit_cycle>=scan_end_cycle);
    sealed<=!bad&&!cfg_fault;has_kit<=scan_kits==2'd1;
    if(bad)begin cfg_fault<=1;if(fault_code==0)fault_code<=3;end
   end
   if(job_v)begin
    if(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q))begin
     run_fault<=1;if(fault_code==0)fault_code<=5;
    end else begin
     active[next_slot]<=1;
     next_slot<=~next_slot;st_jobs<=st_jobs+1;
    end
   end
   // Completions are verified against fixed rows below; no dynamic
   // op-indexed program read or completion-driven scheduling is required.
   // run-time faults: flags registered (rf_q), applied one edge later
   f6=0;f7=0;f8=0;f9=|dup;f10=0;
   if(|rf_q)begin run_fault<=1;if(fault_code==0)fault_code<=rf_q[0]?4'd6:rf_q[4]?4'd10:rf_q[3]?4'd9:rf_q[2]?4'd8:4'd7;end
   for(s=0;s<2;s=s+1)if(active[s])begin
    if(age[s]==24'hffffff)f7=1;
    for(i=0;i<NOPS;i=i+1)begin
     eng=mem[i][27:24];
     if(dm_q[s][i])begin
      dsel_r=dsel(eng,dv_q,dt_q);if(!dsel_r[8]||dsel_r[7:0]!={1'(s),7'(i+OP_BASE)}||!pending[s][i])f8=1;
      else legit_done[eng]=1;
     end
     if(i<length_q&&im_q[s][i])begin
      if(eng==15)begin active[s]<=0;job_done<=1;done_slot<=1'(s);if(!has_kit)begin job_kdone<=1;kit_tok<=tokens[s];end end
      else if(eng==14)begin job_kdone<=1;kit_tok<=tokens[s];end
      else if(eng<NENG&&ENG_PRESENT[eng])begin if(!engine_available[eng])f9=1;end
      else f10=1;
     end
    end
   end
   f6=|(dv_q&~legit_done);
   rf_q<={f10,f9,f8,f7,f6};
   st_cmds<=st_cmds+issued;
  end
 end

 // Datapath state without reset (S81U-SEQ3: off the reset net; 1,871 reset loads at gate 10607befb).  Every value is
 // (re)written before it is read: rows and loaded bits by BEGIN / PW words before the seal scan, the context fields,
 // age and pending bits at the job's accept (pending / age only read while the context is active).  Same conditions
 // and edges as the original's single reset block.
 wire pw_busy=busy||validating||sc_v||sc_fin;
 wire pw_hdr_bad=pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS;
 wire do_begin=pw_v&&!pw_busy&&pw_d[27:26]==3&&!pw_hdr_bad&&!pw_d[25];
 wire do_write=pw_v&&!pw_busy&&pw_d[27:26]!=3&&begun&&pw_a<NOPS;
 wire do_seal=pw_v&&!pw_busy&&pw_d[27:26]==3&&!pw_hdr_bad&&pw_d[25];
 integer i3;
 always @*begin rd_row=0;rd_ld=0;for(i3=0;i3<NOPS;i3=i3+1)begin rd_row=rd_row|({76{sc_oh[i3]}}&mem[i3]);rd_ld=rd_ld|({3{sc_oh[i3]}}&loaded[i3]);end end
 wire do_accept=job_v&&!(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q));
 integer i2,s2;reg[3:0]eng2;reg[8:0]d2;reg[75:0]rn;reg[23:0]an;
 always @(posedge clk)begin
  if(do_begin)for(i2=0;i2<NOPS;i2=i2+1)loaded[i2]<=0;
  if(do_write)begin
   case(pw_d[27:26])
    0:mem[pw_a][25:0]<=pw_d[25:0];
    1:mem[pw_a][51:26]<=pw_d[25:0];
    2:mem[pw_a][75:52]<=pw_d[23:0];
    default:;
   endcase
   loaded[pw_a][pw_d[27:26]]<=1'b1;
  end
  if(do_seal)sc_oh<={{(NOPS-1){1'b0}},1'b1};else if(validating)sc_oh<=sc_oh<<1;
  if(validating)begin sc_row<=rd_row;sc_ld<=rd_ld;end
  for(s2=0;s2<2;s2=s2+1)for(i2=0;i2<NOPS;i2=i2+1)begin
   rn=mem[i2];
   if(do_write&&pw_a==7'(i2))case(pw_d[27:26])0:rn[25:0]=pw_d[25:0];1:rn[51:26]=pw_d[25:0];2:rn[75:52]=pw_d[23:0];default:;endcase
   an=active[s2]?ag1[s2]:24'd0;
   im_q[s2][i2]<=an==rn[51:28]+((MUT==1&&rn[27:24]<14)?24'd1:24'd0);
  end
  for(s2=0;s2<2;s2=s2+1)for(i2=0;i2<NOPS;i2=i2+1)
   dm_q[s2][i2]<=active[s2]&&age[s2]!=24'hffffff&&i2<length_q&&mem[i2][27:24]<14&&mem[i2][75:52]==age[s2];
  if(do_accept)begin
   age[next_slot]<=0;ag1[next_slot]<=24'd1;pending[next_slot]<=0;
   users[next_slot]<=job_user;positions[next_slot]<=job_pos;tokens[next_slot]<=job_tok;
  end
  for(s2=0;s2<2;s2=s2+1)if(active[s2])begin
   age[s2]<=age[s2]+1'b1;ag1[s2]<=ag1[s2]+1'b1;
   for(i2=0;i2<NOPS;i2=i2+1)if(i2<length_q)begin
    eng2=mem[i2][27:24];
    if(dm_q[s2][i2])begin
     d2=dsel(eng2,dv_q,dt_q);
     if(d2[8]&&d2[7:0]=={1'(s2),7'(i2+OP_BASE)}&&pending[s2][i2])pending[s2][i2]<=0;
    end
    if(i2<length_q&&im_q[s2][i2]&&eng2<14&&eng2<NENG&&ENG_PRESENT[eng2])pending[s2][i2]<=1;
   end
  end
 end
 // A per-engine OR of compiler-exclusive events avoids a 256-row
 // procedural priority chain. Multiple matches still fault above; their
 // resulting payload is invalid and must be discarded with the job fault.
 genvar ge;
 generate for(ge=0;ge<NENG;ge=ge+1)begin:g_command
  reg[30:0]a0,a1;reg h0,h1,m0,m1;reg[255:0]mv;integer j;
  assign dup[ge]=two_hot(mv);
  always @*begin
   a0=0;a1=0;h0=0;h1=0;
   m0=0;m1=0;mv=0;
   for(j=0;j<NOPS;j=j+1)begin
    m0=j<length_q&&mem[j][27:24]==ge&&ENG_PRESENT[ge]&&active[0]&&im_q[0][j];
    m1=j<length_q&&mem[j][27:24]==ge&&ENG_PRESENT[ge]&&active[1]&&im_q[1][j];
    h0=h0|m0;h1=h1|m1;mv[j]=m0;mv[NOPS+j]=m1;
    a0=a0|({31{m0}}&{mem[j][23:0],7'(j+OP_BASE)});a1=a1|({31{m1}}&{mem[j][23:0],7'(j+OP_BASE)});
   end
  end
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)cmd_v[ge]<=0;
   else cmd_v[ge]<=h0|h1;
  end
  always @(posedge clk)begin
   begin
    cmd_d[84*ge+:84]<=({84{h0}}&{1'b0,(MUT==2?10'd0:users[0]),positions[0],tokens[0],a0})|
                          ({84{h1}}&{1'b1,(MUT==2?10'd0:users[1]),positions[1],tokens[1],a1});
   end
  end
 end endgenerate
endmodule
`default_nettype wire
