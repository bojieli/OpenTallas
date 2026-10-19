`timescale 1ns/1ps
`default_nettype none
// S81-SAFE-FIX/SH (2026-10-19): ot_dsdv_walk_issue -- the dsdv_sh_sq calendar issuer rebuilt as an ORDERED WALKER over
// SRAM, replacing ot_dsdv_fixed_issue's associative calendar (SAFE-DESIGN item 5: the 128 x 76-b calendar sat in 9,728
// flops, every row compared against both contexts' ages every edge (512 x 24-b compares) and folded through 10 x 31-b
// 128-row AND-OR trees; the leaf was wire-bound: trial GRT overflow 285,158 at 48 % util, M2 106 %).
//
// Calendar contract (compiler: tools/s81_dv/dv_layer_compile.py finish(); checked by the boot seal scan, code 3):
//   * rows i < length are in STRICTLY increasing issue order (KIT and END included; END is therefore the last row):
//     at most one calendar row per issue edge per context;
//   * per engine, the done cycle is strictly increasing in row order (fixed per-engine done latency satisfies it);
//   * at most 8 commands of one engine outstanding (issued, done not yet checked) per context (= the svc tag queue's
//     depth in dsdv_sh_sq); a ninth is a run-time fault (code 10).
// For every calendar that meets the contract the issue / KIT / END / command / completion-check edges, payloads and fault
// codes are those of ot_dsdv_fixed_issue (lock-step vs ot_s81_fixed_issue in tb_dsdv_seq_host).
//
// Structure (no runtime-indexed flop array, no row-parallel compare):
//   * the calendar is written by the PW words into TWO identical 1R1W SRAM copies (one read port per context; the caller
//     instantiates ot_sram_1r1w_128x256 x 2, rows on wd/rd [75:0] = the macro's W-face pins); the boot seal scan reads
//     copy 0, one row an edge, as before (S0 read / S1 accumulate / F closing check);
//   * per context: the current row C (76 b) and its index p; the SRAM read port always holds row p + 1, so a row that
//     issues is replaced by the next one on the same edge (C <= rd, address p + 2).  An idle context reads row 0, so
//     an accept loads C = row 0 at once.  Issue = (age == C.issue): one 24-b compare per context;
//   * per context and present engine: an 8-deep FIFO of {done 24, op 7} pushed at issue, checked (one edge after
//     age == done, as dm_q was) against the registered completion {dv_q, dt_q} and popped.
// MUT is not used here (dsdv_sh_sq instantiates the issuer with MUT 0).
module ot_dsdv_walk_issue #(
 parameter integer NOPS=128, NENG=5, STAGE=0, OP_BASE=0,
 parameter [NENG-1:0] ENG_PRESENT=5'b10111,
 parameter integer QD=8
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
 output wire[1:0]phase,
 // calendar SRAM copies (caller-instantiated 1R1W, read latency 1)
 output wire cal_w_ce,output wire[6:0]cal_w_addr,output wire[75:0]cal_wd,cal_wm,
 output wire[6:0]cal_r_addr0,cal_r_addr1,
 input wire[75:0]cal_rd0,cal_rd1
);
 localparam integer QA=$clog2(QD);
 reg[2:0]loaded[0:NOPS-1];
 reg[7:0]length_q;reg[1:0]phase_q,start_phase_q;
 reg begun,sealed,cfg_fault,run_fault,has_kit,validating;
 reg[7:0]scan_index,scan_native;reg scan_bad;reg[1:0]scan_ends,scan_kits;
 reg[23:0]scan_max_done,scan_end_cycle,scan_kit_cycle;
 reg scan_first;reg[23:0]scan_pi;reg[NENG-1:0]scan_seen;reg[23:0]scan_ld[0:NENG-1];
 reg[1:0]active;reg next_slot;
 reg[9:0]users[0:1];reg[20:0]positions[0:1],tokens[0:1];
 reg[23:0]age[0:1],agp[0:1];reg[1:0]actp;
 reg[75:0]crow[0:1];reg[6:0]cp[0:1],cp1[0:1],cp2[0:1];
 reg[NENG-1:0]dv_q;reg[NENG*8-1:0]dt_q;
 assign busy=|active;assign job_rdy=!active[next_slot];
 assign fault=cfg_fault|run_fault;assign phase=phase_q;
 integer i,s,e,end_count,kit_count,n,max_done;
 reg bad;reg[23:0]end_cycle,kit_cycle;
 reg[3:0]eng;
 reg sc_v,sc_last,sc_in,sc_fin;reg[2:0]sc_ld;
 reg[NOPS-1:0]sc_oh;reg[2:0]rd_ld;
 reg[4:0]rf_q;reg f6,f7,f9,f10;
 wire[75:0]sc_row=cal_rd0;                    // S1 row = the copy-0 read latched at the S0 edge
 // seal scan: per-engine done order against the earlier rows (scan_seen / scan_ld)
 wire ord_bad=sc_row[27:24]<NENG&&scan_seen[sc_row[27:24]]&&sc_row[75:52]<=scan_ld[sc_row[27:24]];
 // ---- the walker: hit = the current row issues on this edge
 wire[1:0]hit;wire[3:0]heng[0:1];
 genvar gs;
 generate for(gs=0;gs<2;gs=gs+1)begin:g_hit
  assign hit[gs]=active[gs]&&age[gs]==crow[gs][51:28];
  assign heng[gs]=crow[gs][27:24];
 end endgenerate
 wire do_accept=job_v&&!(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q));
 wire[1:0]acc={do_accept&&next_slot,do_accept&&!next_slot};
 wire[1:0]ends={hit[1]&&heng[1]==4'd15,hit[0]&&heng[0]==4'd15};
 // next read address: active next edge -> p_next + 1, idle -> 0 (row 0 ready for an accept); scan owns copy 0
 wire[6:0]ra0=acc[0]?7'd1:(active[0]&&!ends[0])?(hit[0]?cp2[0]:cp1[0]):7'd0;
 wire[6:0]ra1=acc[1]?7'd1:(active[1]&&!ends[1])?(hit[1]?cp2[1]:cp1[1]):7'd0;
 assign cal_r_addr0=validating?scan_index[6:0]:ra0;
 assign cal_r_addr1=ra1;
 // ---- completion FIFOs {done 24, op 7}, one per context and present engine (QD deep, flat ring buffers)
 wire[NENG-1:0]chk0,chk1,good0,good1,bad0,bad1,full0,full1;
 wire[NENG-1:0]legit_done=good0|good1;
 wire f8w=|(bad0|bad1);
 genvar fs,fe;
 generate for(fs=0;fs<2;fs=fs+1)begin:g_fs for(fe=0;fe<NENG;fe=fe+1)begin:g_fe
  if(ENG_PRESENT[fe])begin:g_q
   reg[QD*31-1:0]q;reg[QA-1:0]w,r;reg[QA:0]n;
   wire[30:0]h=q[r*31+:31];
   wire c=actp[fs]&&agp[fs]!=24'hffffff&&n!=0&&h[30:7]==agp[fs];
   wire ok=dv_q[fe]&&dt_q[8*fe+:8]=={1'(fs),h[6:0]};
   wire ps=hit[fs]&&heng[fs]==4'(fe);
   wire fl=n==QD[QA:0];
   always @(posedge clk)begin
    if(acc[fs])begin w<=0;r<=0;n<=0;end
    else begin
     if(ps&&!fl)begin q[w*31+:31]<={crow[fs][75:52],7'(cp[fs]+7'(OP_BASE))};w<=w+1'b1;end
     if(c)r<=r+1'b1;
     n<=n+((ps&&!fl)?1'b1:1'b0)-(c?1'b1:1'b0);
    end
   end
   if(fs==0)begin assign chk0[fe]=c;assign good0[fe]=c&&ok;assign bad0[fe]=c&&!ok;assign full0[fe]=fl;end
   else begin assign chk1[fe]=c;assign good1[fe]=c&&ok;assign bad1[fe]=c&&!ok;assign full1[fe]=fl;end
  end else begin:g_n
   if(fs==0)begin assign chk0[fe]=0;assign good0[fe]=0;assign bad0[fe]=0;assign full0[fe]=0;end
   else begin assign chk1[fe]=0;assign good1[fe]=0;assign bad1[fe]=0;assign full1[fe]=0;end
  end
 end end endgenerate
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
   fault_code<=0;st_jobs<=0;st_cmds<=0;dv_q<=0;dt_q<=0;actp<=0;
   sc_v<=0;sc_last<=0;sc_in<=0;sc_fin<=0;rf_q<=0;
  end else begin
   phase_q<=phase_q+1'b1;dv_q<=dn_v;dt_q<=dn_tag;actp<=active;
   job_done<=0;job_kdone<=0;
   if(pw_v)begin
    if(busy||validating||sc_v||sc_fin)begin cfg_fault<=1;if(fault_code==0)fault_code<=1;end
    else if(pw_d[27:26]==3)begin
     if(pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS)begin
      cfg_fault<=1;sealed<=0;if(fault_code==0)fault_code<=2;
     end else if(!pw_d[25])begin
      begun<=1;sealed<=0;length_q<=pw_d[16:9];start_phase_q<=pw_d[8:7];
     end else begin
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
   // S0: the copy-0 read of row scan_index (address = scan_index while validating)
   sc_v<=validating;sc_fin<=sc_v&&sc_last;
   if(validating)begin
    sc_in<=scan_index<length_q;sc_last<=scan_index==NOPS-1;
    if(scan_index==NOPS-1)validating<=0;else scan_index<=scan_index+1'b1;
   end
   // S1: the row's checks (original + walker order: issue strictly increasing, per-engine done strictly increasing)
   if(sc_v)begin
    bad=scan_bad;end_count=scan_ends;kit_count=scan_kits;n=scan_native;
    max_done=scan_max_done;end_cycle=scan_end_cycle;kit_cycle=scan_kit_cycle;
    if(sc_in)begin
     if(sc_ld!=3'b111)bad=1;
     if(!scan_first&&sc_row[51:28]<=scan_pi)bad=1;
     if(ord_bad)bad=1;
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
   if(sc_fin)begin
    bad=scan_bad||scan_ends!=2'd1||scan_kits>2'd1||scan_native==0||scan_end_cycle<=scan_max_done||
        (scan_kits==2'd1&&scan_kit_cycle>=scan_end_cycle);
    sealed<=!bad&&!cfg_fault;has_kit<=scan_kits==2'd1;
    if(bad)begin cfg_fault<=1;if(fault_code==0)fault_code<=3;end
   end
   if(job_v)begin
    if(!do_accept)begin run_fault<=1;if(fault_code==0)fault_code<=5;end
    else begin active[next_slot]<=1;next_slot<=~next_slot;st_jobs<=st_jobs+1;end
   end
   // run-time faults: flags registered (rf_q), applied one edge later (priority 6 > 10 > 9 > 8 > 7 as before)
   f6=0;f7=0;f9=0;f10=0;
   if(|rf_q)begin run_fault<=1;if(fault_code==0)fault_code<=rf_q[0]?4'd6:rf_q[4]?4'd10:rf_q[3]?4'd9:rf_q[2]?4'd8:4'd7;end
   for(s=0;s<2;s=s+1)if(active[s])begin
    if(age[s]==24'hffffff)f7=1;
    if(hit[s])begin
     eng=heng[s];
     if(eng==15)begin active[s]<=0;job_done<=1;done_slot<=1'(s);if(!has_kit)begin job_kdone<=1;kit_tok<=tokens[s];end end
     else if(eng==14)begin job_kdone<=1;kit_tok<=tokens[s];end
     else if(eng<NENG&&ENG_PRESENT[eng])begin
      if(!engine_available[eng])f9=1;
      if(s==0?full0[eng]:full1[eng])f10=1;
     end
     else f10=1;
    end
   end
   if(hit[0]&&hit[1]&&heng[0]==heng[1]&&heng[0]<14)f9=1;
   f6=|(dv_q&~legit_done);
   rf_q<={f10,f9,f8w,f7,f6};
   n=0;for(e=0;e<NENG;e=e+1)if(cmd_v[e])n=n+1;
   st_cmds<=st_cmds+n;
  end
 end
 // ---- datapath state without reset (written before read, as in ot_dsdv_fixed_issue)
 wire pw_busy=busy||validating||sc_v||sc_fin;
 wire pw_hdr_bad=pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS;
 wire do_begin=pw_v&&!pw_busy&&pw_d[27:26]==3&&!pw_hdr_bad&&!pw_d[25];
 wire do_write=pw_v&&!pw_busy&&pw_d[27:26]!=3&&begun&&pw_a<NOPS;
 wire do_seal=pw_v&&!pw_busy&&pw_d[27:26]==3&&!pw_hdr_bad&&pw_d[25];
 assign cal_w_ce=do_write;assign cal_w_addr=pw_a;
 assign cal_wd=pw_d[27:26]==2'd0 ? {50'd0,pw_d[25:0]}:pw_d[27:26]==2'd1 ? {24'd0,pw_d[25:0],26'd0}:{pw_d[23:0],52'd0};
 assign cal_wm=pw_d[27:26]==2'd0 ? {50'd0,{26{1'b1}}}:pw_d[27:26]==2'd1 ? {24'd0,{26{1'b1}},26'd0}:{{24{1'b1}},52'd0};
 integer i3;
 always @*begin rd_ld=0;for(i3=0;i3<NOPS;i3=i3+1)rd_ld=rd_ld|({3{sc_oh[i3]}}&loaded[i3]);end
 integer i2,s2;
 always @(posedge clk)begin
  if(do_begin)for(i2=0;i2<NOPS;i2=i2+1)loaded[i2]<=0;
  if(do_write)loaded[pw_a][pw_d[27:26]]<=1'b1;
  if(do_seal)sc_oh<={{(NOPS-1){1'b0}},1'b1};else if(validating)sc_oh<=sc_oh<<1;
  if(validating)sc_ld<=rd_ld;
  if(do_seal)scan_first<=1'b1;
  if(sc_v&&sc_in)begin
   scan_first<=1'b0;scan_pi<=sc_row[51:28];
   if(sc_row[27:24]<NENG)begin scan_seen[sc_row[27:24]]<=1'b1;scan_ld[sc_row[27:24]]<=sc_row[75:52];end
  end
  if(do_seal)scan_seen<=0;
  for(s2=0;s2<2;s2=s2+1)begin
   agp[s2]<=age[s2];
   if(acc[s2])begin
    age[s2]<=0;crow[s2]<=s2==0?cal_rd0:cal_rd1;cp[s2]<=7'd0;cp1[s2]<=7'd1;cp2[s2]<=7'd2;
    users[s2]<=job_user;positions[s2]<=job_pos;tokens[s2]<=job_tok;
   end else if(active[s2])begin
    age[s2]<=age[s2]+1'b1;
    if(hit[s2])begin crow[s2]<=s2==0?cal_rd0:cal_rd1;cp[s2]<=cp1[s2];cp1[s2]<=cp2[s2];cp2[s2]<=cp2[s2]+7'd1;end
   end
  end
 end
 // commands: straight from the walker's current rows
 genvar ge;
 generate for(ge=0;ge<NENG;ge=ge+1)begin:g_command
  wire h0=ENG_PRESENT[ge]&&hit[0]&&heng[0]==4'(ge);
  wire h1=ENG_PRESENT[ge]&&hit[1]&&heng[1]==4'(ge);
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)cmd_v[ge]<=0;
   else cmd_v[ge]<=h0|h1;
  end
  always @(posedge clk)
   cmd_d[84*ge+:84]<=({84{h0}}&{1'b0,users[0],positions[0],tokens[0],crow[0][23:0],7'(cp[0]+7'(OP_BASE))})|
                      ({84{h1}}&{1'b1,users[1],positions[1],tokens[1],crow[1][23:0],7'(cp[1]+7'(OP_BASE))});
 end endgenerate
endmodule
`default_nettype wire
