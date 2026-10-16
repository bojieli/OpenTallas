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
//
// Issue structure v2 (S-ELEM-PQ/SSEQ 2026-10-16, measured cause: the c8/c10
// localtree3 CTS views hold TT reg->reg -751 ps (boot scan), -668 ps (length/age
// -> 26 per-engine x per-slot 128-row command OR trees -> cmd_d) and -508 ps
// (busy -> 9,728 PW write enables); the c9 n5 route carrying the same 26 trees
// overflowed GRT uniformly over the whole tile). Calendar contract (compiler
// enforced, tools/s81_static_control/program.py; runtime fault 9 otherwise):
//  * at most ONE row of a context issues on any edge (KIT/END included), and
//  * one command in flight per engine per context (next issue >= previous done).
// Hence each context needs ONE 128-row reduction tree of {done,engine,arg,op}
// (2 trees instead of 26) whose row hits are registered one edge ahead
// (age+1 compare; identical issue edges), and one completion expectation per
// engine per context replaces 256 per-row completion comparators. The PW row
// write is registered one edge after its unchanged accept/fault decision, and
// the boot scan registers each row before accumulating (seal -> armed 130
// edges, was 128). Command/KIT/END/fault edges of every legal calendar are
// unchanged.
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
 // Boot-only scan pipeline: the addressed row and its loaded tag are captured
 // first, accumulated one edge later; final bounds use a separate flush edge.
 reg[75:0]scan_row_q;reg[2:0]scan_loaded_q;reg scan_active_q,scan_row_valid;
 // PW row write, registered after the unchanged accept / fault decision.
 reg wr_q;reg[6:0]wr_a_q;reg[1:0]wr_p_q;reg[25:0]wr_d_q;
 reg[1:0]active;reg next_slot;
 reg[9:0]users[0:1];reg[20:0]positions[0:1],tokens[0:1];
 reg[23:0]age[0:1],age_n[0:1];
 wire[NOPS-1:0]hit0,hit1;
 reg[NENG-1:0]dv_q;reg[NENG*8-1:0]dt_q;
 assign busy=|active;assign job_rdy=!active[next_slot];
 assign fault=cfg_fault|run_fault;assign phase=phase_q;
 integer i,s,e,n,issued,max_done,end_count,kit_count;
 reg bad,accept;reg[23:0]end_cycle,kit_cycle;
 reg[3:0]eng;

 // ---- one registered-hit reduction tree per context -------------------------
 // Row payload {op7,done24,engine4,arg24}; with <= 1 hit per context the OR of
 // the gated payloads is the hit row. any/multiple are balanced-tree carries.
 localparam integer PW_ROW=59;
 localparam integer TL=2**$clog2(NOPS);
 wire[PW_ROW-1:0]sel_row[0:1];
 wire[1:0]sel_any,sel_mult;
 genvar gs,gr,gt;
 generate for(gs=0;gs<2;gs=gs+1)begin:g_tree
  wire[2*TL-1:1]t_any,t_mult;
  wire[PW_ROW*2*TL-1:0]t_pay;
  assign t_pay[PW_ROW-1:0]={PW_ROW{1'b0}};
  for(gt=0;gt<TL;gt=gt+1)begin:g_leaf
   if(gt<NOPS)begin
    wire h=gs?hit1[gt]:hit0[gt];
    assign t_any[TL+gt]=h;
    assign t_pay[PW_ROW*(TL+gt)+:PW_ROW]={PW_ROW{h}}&{7'(gt+OP_BASE),mem[gt][75:52],mem[gt][27:24],mem[gt][23:0]};
   end else begin
    assign t_any[TL+gt]=1'b0;assign t_pay[PW_ROW*(TL+gt)+:PW_ROW]={PW_ROW{1'b0}};
   end
   assign t_mult[TL+gt]=1'b0;
  end
  for(gt=1;gt<TL;gt=gt+1)begin:g_node
   assign t_any[gt]=t_any[2*gt]|t_any[2*gt+1];
   assign t_mult[gt]=t_mult[2*gt]|t_mult[2*gt+1]|(t_any[2*gt]&t_any[2*gt+1]);
   assign t_pay[PW_ROW*gt+:PW_ROW]=t_pay[PW_ROW*2*gt+:PW_ROW]|t_pay[PW_ROW*(2*gt+1)+:PW_ROW];
  end
  assign sel_any[gs]=t_any[1]&active[gs];
  assign sel_mult[gs]=t_mult[1]&active[gs];
  assign sel_row[gs]=t_pay[PW_ROW+:PW_ROW];
 end endgenerate
 wire[6:0]sel_op[0:1];wire[23:0]sel_done[0:1],sel_arg[0:1];wire[3:0]sel_eng[0:1];
 assign {sel_op[0],sel_done[0],sel_eng[0],sel_arg[0]}=sel_row[0];
 assign {sel_op[1],sel_done[1],sel_eng[1],sel_arg[1]}=sel_row[1];
 // A context with two hits on one edge violates the calendar contract: it
 // dispatches nothing and faults (code 9) instead of emitting a merged row.
 wire[1:0]sel_ok=sel_any&~sel_mult;
 wire[NENG-1:0]m0,m1,raw0,raw1;
 genvar ge;
 generate for(ge=0;ge<NENG;ge=ge+1)begin:g_dec
  assign raw0[ge]=sel_any[0]&&sel_eng[0]==ge&&ENG_PRESENT[ge];
  assign raw1[ge]=sel_any[1]&&sel_eng[1]==ge&&ENG_PRESENT[ge];
  assign m0[ge]=raw0[ge]&sel_ok[0];assign m1[ge]=raw1[ge]&sel_ok[1];
 end endgenerate
 wire[1:0]sel_end={sel_ok[1]&&sel_eng[1]==15,sel_ok[0]&&sel_eng[0]==15};
 wire[1:0]sel_kit={sel_ok[1]&&sel_eng[1]==14,sel_ok[0]&&sel_eng[0]==14};
 wire[1:0]sel_absent={sel_any[1]&&sel_eng[1]<14&&(sel_eng[1]>=NENG||!ENG_PRESENT[sel_eng[1]]),
                      sel_any[0]&&sel_eng[0]<14&&(sel_eng[0]>=NENG||!ENG_PRESENT[sel_eng[0]])};
 // A context with two row hits on one edge reports on every engine's collision bit.
 wire[NENG-1:0]engine_bad=(raw0&raw1)|((raw0|raw1)&~engine_available)|{NENG{|sel_mult}};

 // ---- per-engine completion expectation (one in flight per engine/context) ---
 // Loaded on the issue edge; due is registered on the edge age==done, and the
 // registered dn pins are checked on the next edge, exactly when the original
 // per-row checker compared completion_age==done.
 wire[NENG-1:0]good0,good1,bad0,bad1;
 generate for(ge=0;ge<NENG;ge=ge+1)begin:g_exp
  for(gs=0;gs<2;gs=gs+1)begin:g_ctx
   reg v,due;reg[23:0]dn;reg[6:0]op,op_due;
   wire load=(gs?m1[ge]:m0[ge]);
   wire chk=due;
   wire good=chk&&dv_q[ge]&&dt_q[8*ge+:8]=={1'(gs),op_due};
   always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin v<=0;due<=0;dn<=0;op<=0;op_due<=0;end
    else begin
     due<=active[gs]&&v&&age[gs]==dn;op_due<=op;
     if(active[gs]&&v&&age[gs]==dn)v<=0;
     if(load)begin v<=1;dn<=gs?sel_done[1]:sel_done[0];op<=gs?sel_op[1]:sel_op[0];end
     if(job_v&&next_slot==gs&&accept)begin v<=0;due<=0;end
    end
   end
   if(gs==0)begin assign good0[ge]=good;assign bad0[ge]=chk&&!good;end
   else begin assign good1[ge]=good;assign bad1[ge]=chk&&!good;end
  end
 end endgenerate
 wire[NENG-1:0]legitimate=good0|good1;
 reg completion_bad_q,absent_bad_q;
 reg[NENG-1:0]engine_bad_q;
 reg overflow_q,unexpected_q;

 // ---- row hits one edge ahead ----------------------------------------------
 always @*begin
  accept=!(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q)||pw_v||wr_q);
 end
 generate for(gs=0;gs<2;gs=gs+1)begin:g_hit
  for(gr=0;gr<NOPS;gr=gr+1)begin:g_row
   wire[3:0]re=mem[gr][27:24];wire[23:0]ri=mem[gr][51:28];
   wire live=gr<length_q;
   wire start=job_v&&accept&&next_slot==gs;
   // MUT=1 (negative bench witness): native commands one edge late.
   wire late=(MUT==1&&re<14);
   wire nxt=late?(ri==age[gs]):(ri==age_n[gs]);
   wire first=late?1'b0:(ri==24'd0);
   reg h;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)h<=1'b0;
    else h<=live&&(start?first:(active[gs]&&nxt));
   if(gs==0)begin:g0 assign hit0[gr]=h;end else begin:g1 assign hit1[gr]=h;end
  end
 end endgenerate

 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   length_q<=0;phase_q<=0;start_phase_q<=0;begun<=0;sealed<=0;cfg_fault<=0;run_fault<=0;
   validating<=0;scan_index<=0;scan_native<=0;scan_bad<=0;scan_ends<=0;scan_kits<=0;scan_max_done<=0;scan_end_cycle<=0;scan_kit_cycle<=0;
   scan_row_q<=0;scan_loaded_q<=0;scan_active_q<=0;scan_row_valid<=0;
   wr_q<=0;wr_a_q<=0;wr_p_q<=0;wr_d_q<=0;
   active<=0;next_slot<=0;has_kit<=0;job_done<=0;job_kdone<=0;done_slot<=0;kit_tok<=0;
   fault_code<=0;st_jobs<=0;st_cmds<=0;dv_q<=0;dt_q<=0;
   for(i=0;i<NOPS;i=i+1)loaded[i]<=0;
   for(s=0;s<2;s=s+1)begin users[s]<=0;positions[s]<=0;tokens[s]<=0;age[s]<=0;age_n[s]<=0;end
  end else begin
   phase_q<=phase_q+1'b1;dv_q<=dn_v;dt_q<=dn_tag;
   job_done<=0;job_kdone<=0;issued=0;wr_q<=0;
   for(e=0;e<NENG;e=e+1)if(cmd_v[e])issued=issued+1;
   // Registered row write: accepted on the previous edge by the original rules.
   if(wr_q)begin
    case(wr_p_q)
     0:mem[wr_a_q][25:0]<=wr_d_q;
     1:mem[wr_a_q][51:26]<=wr_d_q;
     default:mem[wr_a_q][75:52]<=wr_d_q[23:0];
    endcase
    loaded[wr_a_q][wr_p_q]<=1'b1;
   end
   if(pw_v)begin
    if(busy||validating)begin cfg_fault<=1;if(fault_code==0)fault_code<=1;end
    else if(pw_d[27:26]==3)begin
     if(pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS)begin
      cfg_fault<=1;sealed<=0;if(fault_code==0)fault_code<=2;
     end else if(!pw_d[25])begin
      begun<=1;sealed<=0;length_q<=pw_d[16:9];start_phase_q<=pw_d[8:7];
      // Clears after a row write landing on this edge (that row preceded BEGIN).
      for(i=0;i<NOPS;i=i+1)loaded[i]<=0;
     end else begin
      // Fixed boot scan: one row per stream edge, independent of data.
      validating<=1;sealed<=0;scan_index<=0;scan_native<=0;scan_ends<=0;scan_kits<=0;
      scan_max_done<=0;scan_end_cycle<=0;scan_kit_cycle<=0;scan_row_valid<=0;
      scan_bad<=!begun||length_q!=pw_d[16:9]||start_phase_q!=pw_d[8:7]||prog_len!=length_q;
     end
    end else if(!begun||pw_a>=NOPS)begin cfg_fault<=1;if(fault_code==0)fault_code<=4;end
    else begin
     sealed<=0;wr_q<=1;wr_a_q<=pw_a;wr_p_q<=pw_d[27:26];wr_d_q<=pw_d[25:0];
     if(pw_d[27:26]==2&&pw_d[25:24]!=0)begin cfg_fault<=1;if(fault_code==0)fault_code<=4;end
    end
   end
   if(validating)begin
    if(scan_index<NOPS)begin
     scan_row_q<=mem[scan_index];scan_loaded_q<=loaded[scan_index];
     scan_active_q<=scan_index<length_q;scan_row_valid<=1;
    end else scan_row_valid<=0;
    scan_index<=scan_index+1'b1;
    bad=scan_bad;end_count=scan_ends;kit_count=scan_kits;n=scan_native;
    max_done=scan_max_done;end_cycle=scan_end_cycle;kit_cycle=scan_kit_cycle;
    if(scan_row_valid&&scan_active_q)begin
     if(scan_loaded_q!=3'b111)bad=1;
     eng=scan_row_q[27:24];
     if(eng==15)begin end_count=end_count+1;end_cycle=scan_row_q[51:28];if(scan_row_q[75:52]!=0||scan_row_q[23:0]!=0)bad=1;end
     else if(eng==14)begin kit_count=kit_count+1;kit_cycle=scan_row_q[51:28];if(scan_row_q[75:52]!=0||scan_row_q[23:0]!=0)bad=1;end
     else if(eng>=NENG||!ENG_PRESENT[eng])bad=1;
     else begin
      n=n+1;if(scan_row_q[75:52]<=scan_row_q[51:28])bad=1;
      if(scan_row_q[75:52]>max_done)max_done=scan_row_q[75:52];
     end
    end
    scan_bad<=bad;scan_native<=8'(n);scan_ends<=end_count>2?2'd3:2'(end_count);scan_kits<=kit_count>2?2'd3:2'(kit_count);
    scan_max_done<=24'(max_done);scan_end_cycle<=end_cycle;scan_kit_cycle<=kit_cycle;
    if(scan_index==NOPS+1)begin
     validating<=0;
     // Every row result has committed; final 24-bit bounds stay out of the
     // 128-row read / accumulate cone.
     bad=scan_bad||scan_ends!=1||scan_kits>1||scan_native==0||scan_end_cycle<=scan_max_done||
         (scan_kits==1&&scan_kit_cycle>=scan_end_cycle);
     sealed<=!bad&&!cfg_fault;has_kit<=scan_kits==1;
     if(bad)begin cfg_fault<=1;if(fault_code==0)fault_code<=3;end
    end
   end
   if(job_v)begin
    if(!accept)begin
     run_fault<=1;if(fault_code==0)fault_code<=5;
    end else begin
     active[next_slot]<=1;age[next_slot]<=0;age_n[next_slot]<=24'd1;
     users[next_slot]<=job_user;positions[next_slot]<=job_pos;tokens[next_slot]<=job_tok;
     next_slot<=~next_slot;st_jobs<=st_jobs+1;
    end
   end
   for(s=0;s<2;s=s+1)if(active[s])begin
    age[s]<=age[s]+1'b1;age_n[s]<=age_n[s]+1'b1;
    if(sel_end[s])begin active[s]<=0;job_done<=1;done_slot<=1'(s);if(!has_kit)begin job_kdone<=1;kit_tok<=tokens[s];end end
    else if(sel_kit[s])begin job_kdone<=1;kit_tok<=tokens[s];end
   end
   // Diagnostics are a separate registered tree; they never gate a calendar edge.
   if(overflow_q||completion_bad_q||absent_bad_q||(|engine_bad_q)||unexpected_q)begin
    run_fault<=1;
    if(fault_code==0)begin
     if(overflow_q)fault_code<=7;
     else if(completion_bad_q)fault_code<=8;
     else if(|engine_bad_q)fault_code<=9;
     else if(absent_bad_q)fault_code<=10;
     else fault_code<=6;
    end
   end
   st_cmds<=st_cmds+issued;
  end
 end
 // MUT=3 suppresses runtime diagnostic capture as a negative bench witness.
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin completion_bad_q<=0;absent_bad_q<=0;engine_bad_q<=0;unexpected_q<=0;overflow_q<=0;end
  else if(MUT!=3)begin
   completion_bad_q<=|(bad0|bad1);absent_bad_q<=|sel_absent;engine_bad_q<=engine_bad;
   unexpected_q<=|(dv_q&~legitimate);
   overflow_q<=(active[0]&&age[0]==24'hffffff)||(active[1]&&age[1]==24'hffffff);
  end
 end
 genvar gc;
 generate for(gc=0;gc<NENG;gc=gc+1)begin:g_command
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin cmd_v[gc]<=0;cmd_d[84*gc+:84]<=0;end
   else begin
    cmd_v[gc]<=m0[gc]|m1[gc];
    cmd_d[84*gc+:84]<=({84{m0[gc]}}&{1'b0,(MUT==2?10'd0:users[0]),positions[0],tokens[0],sel_arg[0],sel_op[0]})|
                      ({84{m1[gc]}}&{1'b1,(MUT==2?10'd0:users[1]),positions[1],tokens[1],sel_arg[1],sel_op[1]});
   end
  end
 end endgenerate
endmodule
`default_nettype wire
