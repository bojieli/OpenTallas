`timescale 1ns/1ps
`default_nettype none
// S81-SAFE-FIX/SH (2026-10-19): ot_dsdv_walk_issue -- the dsdv_sh_sq calendar issuer rebuilt as an ORDERED WALKER over
// SRAM, replacing ot_dsdv_fixed_issue's associative calendar (SAFE-DESIGN item 5: the 128 x 76-b calendar sat in 9,728
// flops, every row compared against both contexts' ages every edge (512 x 24-b compares) and folded through 10 x 31-b
// 128-row AND-OR trees; the leaf was wire-bound: trial GRT overflow 285,158 at 48 % util, M2 106 %).
//
// Calendar contract (compiler: tools/s81_dv/dv_layer_compile.py finish(); checked by the boot seal scan, code 3):
//   * rows i < length are in non-decreasing issue order with AT MOST TWO rows on one edge (KIT and END included; END
//     is the last row, alone on its edge); one row per engine per edge (as before, code 9);
//   * per engine, the done cycle is strictly increasing in row order (fixed per-engine done latency satisfies it);
//   * at most 8 commands of one engine outstanding (issued, done not yet checked) per context (= the svc tag queue's
//     depth in dsdv_sh_sq); a ninth is a run-time fault (code 10).
// For every calendar that meets the contract the issue / KIT / END / command / completion-check edges, payloads and fault
// codes are those of ot_dsdv_fixed_issue (lock-step vs ot_s81_fixed_issue in tb_dsdv_seq_host).
//
// Structure (no runtime-indexed flop array, no row-parallel compare):
//   * the calendar is written by the PW words into TWO identical 1R1W SRAM copies (one read port per context; the caller
//     instantiates ot_sram_1r1w_128x256 x 2) as ROW PAIRS: word w = {row 2w + 1 [151:76], row 2w [75:0]}, written with
//     a field mask; the boot seal scan reads copy 0, one row an edge, as before (S0 read / S1 accumulate / F check);
//   * per context: the current pair word CW (index k), the next word NW (k + 1) in a register, and a half pointer h;
//     the SRAM read port holds word k + 2 and feeds only NW (no logic behind the macro output).  The next row A = CW[h] and the one after it B = (h ? NW.lo : CW.hi): A issues when age == A.issue, B with it
//     when B.issue == age too (two rows an edge, any alignment); CW <= NW <= rd (address k + 3) once both halves are used,
//     so one pair read an edge always keeps up.  Word 0 is kept from the seal scan (W0) and an idle context reads word 1,
//     so an accept loads CW / NW at once.  The seal scan row is registered once (S0b) before its checks;
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
 output wire cal_w_ce,output wire[6:0]cal_w_addr,output wire[151:0]cal_wd,cal_wm,
 output wire[6:0]cal_r_addr0,cal_r_addr1,
 input wire[151:0]cal_rd0,cal_rd1
);
 localparam integer QA=$clog2(QD);
 reg[2:0]loaded[0:NOPS-1];
 reg[7:0]length_q;reg[1:0]phase_q,start_phase_q;
 reg begun,sealed,cfg_fault,run_fault,has_kit,validating;
 reg[7:0]scan_index,scan_native;reg scan_bad;reg[1:0]scan_ends,scan_kits;
 reg[23:0]scan_max_done,scan_end_cycle,scan_kit_cycle;
 reg scan_first,scan_eq;reg[3:0]scan_pe;reg[23:0]scan_pi;reg[NENG-1:0]scan_seen;reg[23:0]scan_ld[0:NENG-1];
 reg[1:0]active;reg next_slot;
 reg[9:0]users[0:1];reg[20:0]positions[0:1],tokens[0:1];
 reg[23:0]age[0:1],agp[0:1];reg[1:0]actp;
 reg[151:0]cw[0:1],nwr[0:1],w0;reg[5:0]ck[0:1],ck2[0:1],ck3[0:1];reg[1:0]hh;
 reg[NENG-1:0]dv_q;reg[NENG*8-1:0]dt_q;
 assign busy=|active;assign job_rdy=!active[next_slot];
 assign fault=cfg_fault|run_fault;assign phase=phase_q;
 integer i,s,e,r,end_count,kit_count,n,max_done;
 reg bad;reg[23:0]end_cycle,kit_cycle;
 reg[3:0]eng;
 reg sc_v,sc_last,sc_in,sc_fin,sc_r,sc_in0,sc_last0,sc_i1;reg[2:0]sc_ld,sc_ld0;
 reg[NOPS-1:0]sc_oh;reg[2:0]rd_ld;
 reg[4:0]rf_q;reg f6,f7,f9,f10;
 reg sc_half;reg[75:0]sc_row;                  // S1 row: the copy-0 pair read (S0), registered (S0b), then checked (S1)
 // seal scan: per-engine done order against the earlier rows (scan_seen / scan_ld)
 wire ord_bad=sc_row[27:24]<NENG&&scan_seen[sc_row[27:24]]&&sc_row[75:52]<=scan_ld[sc_row[27:24]];
 // ---- the walker: A = the next row, B = the row after it; hitA / hitB = they issue on this edge
 wire[151:0]nw[0:1];assign nw[0]=cal_rd0;assign nw[1]=cal_rd1;   // SRAM out -> nwr only
 wire[75:0]ra[0:1],rb[0:1];wire[1:0]hit,hitb;wire[3:0]heng[0:1],beng[0:1];wire[6:0]opa[0:1],opb[0:1];wire[1:0]adv;
 genvar gs;
 generate for(gs=0;gs<2;gs=gs+1)begin:g_hit
  assign ra[gs]=hh[gs]?cw[gs][151:76]:cw[gs][75:0];
  assign rb[gs]=hh[gs]?nwr[gs][75:0]:cw[gs][151:76];
  assign heng[gs]=ra[gs][27:24];assign beng[gs]=rb[gs][27:24];
  assign hit[gs]=active[gs]&&age[gs]==ra[gs][51:28];
  assign hitb[gs]=hit[gs]&&heng[gs]!=4'd15&&rb[gs][51:28]==ra[gs][51:28];
  assign opa[gs]={ck[gs],hh[gs]};assign opb[gs]={ck[gs],hh[gs]}+7'd1;
  assign adv[gs]=hh[gs]?hit[gs]:hitb[gs];            // both halves of CW used -> CW <= N
 end endgenerate
 wire[15:0]ue[0:1];wire[1:0]dup_in;
 generate for(gs=0;gs<2;gs=gs+1)begin:g_ue
  assign ue[gs]=(hit[gs]?(16'd1<<heng[gs]):16'd0)|(hitb[gs]?(16'd1<<beng[gs]):16'd0);
  assign dup_in[gs]=hitb[gs]&&heng[gs]==beng[gs]&&heng[gs]<14;
 end endgenerate
 wire do_accept=job_v&&!(!sealed||cfg_fault||active[next_slot]||prog_len!=length_q||((phase_q+2'd1)!=start_phase_q));
 wire[1:0]acc={do_accept&&next_slot,do_accept&&!next_slot};
 wire[1:0]ends={hit[1]&&heng[1]==4'd15,hit[0]&&heng[0]==4'd15};
 // next read address (pair word): active next edge -> k_next + 1, idle -> 0 (word 0 ready for an accept); scan owns copy 0
 wire[5:0]rw0=acc[0]?6'd2:(active[0]&&!ends[0])?(adv[0]?ck3[0]:ck2[0]):6'd1;
 wire[5:0]rw1=acc[1]?6'd2:(active[1]&&!ends[1])?(adv[1]?ck3[1]:ck2[1]):6'd1;
 assign cal_r_addr0=validating?{1'b0,scan_index[6:1]}:{1'b0,rw0};
 assign cal_r_addr1={1'b0,rw1};
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
   wire pa=hit[fs]&&heng[fs]==4'(fe),pb=hitb[fs]&&beng[fs]==4'(fe);
   wire ps=pa|pb;
   wire fl=n==QD[QA:0];
   always @(posedge clk)begin
    if(acc[fs])begin w<=0;r<=0;n<=0;end
    else begin
     if(ps&&!fl)begin q[w*31+:31]<=pa?{ra[fs][75:52],7'(opa[fs]+7'(OP_BASE))}:{rb[fs][75:52],7'(opb[fs]+7'(OP_BASE))};w<=w+1'b1;end
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
   sc_v<=0;sc_last<=0;sc_in<=0;sc_fin<=0;rf_q<=0;sc_r<=0;sc_in0<=0;sc_last0<=0;
  end else begin
   phase_q<=phase_q+1'b1;dv_q<=dn_v;dt_q<=dn_tag;actp<=active;
   job_done<=0;job_kdone<=0;
   if(pw_v)begin
    if(busy||validating||sc_r||sc_v||sc_fin)begin cfg_fault<=1;if(fault_code==0)fault_code<=1;end
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
   sc_r<=validating;sc_v<=sc_r;sc_fin<=sc_v&&sc_last;sc_in<=sc_in0;sc_last<=sc_last0;
   if(validating)begin
    sc_in0<=scan_index<length_q;sc_last0<=scan_index==NOPS-1;
    if(scan_index==NOPS-1)validating<=0;else scan_index<=scan_index+1'b1;
   end
   // S1: the row's checks (original + walker order: issue non-decreasing, <= 2 rows an edge on different engines,
   // per-engine done strictly increasing)
   if(sc_v)begin
    bad=scan_bad;end_count=scan_ends;kit_count=scan_kits;n=scan_native;
    max_done=scan_max_done;end_cycle=scan_end_cycle;kit_cycle=scan_kit_cycle;
    if(sc_in)begin
     if(sc_ld!=3'b111)bad=1;
     if(!scan_first&&(sc_row[51:28]<scan_pi||(sc_row[51:28]==scan_pi&&(scan_eq||sc_row[27:24]==scan_pe))))bad=1;
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
    for(r=0;r<2;r=r+1)if(r==0?hit[s]:hitb[s])begin
     eng=r==0?heng[s]:beng[s];
     if(eng==15)begin active[s]<=0;job_done<=1;done_slot<=1'(s);if(!has_kit)begin job_kdone<=1;kit_tok<=tokens[s];end end
     else if(eng==14)begin job_kdone<=1;kit_tok<=tokens[s];end
     else if(eng<NENG&&ENG_PRESENT[eng])begin
      if(!engine_available[eng])f9=1;
      if(s==0?full0[eng]:full1[eng])f10=1;
     end
     else f10=1;
    end
   end
   // duplicate issue: one engine twice on one edge (A / B of a context, or both contexts)
   if(|(ue[0]&ue[1]&16'(ENG_PRESENT))||dup_in[0]||dup_in[1])f9=1;
   f6=|(dv_q&~legit_done);
   rf_q<={f10,f9,f8w,f7,f6};
   n=0;for(e=0;e<NENG;e=e+1)if(cmd_v[e])n=n+1;
   st_cmds<=st_cmds+n;
  end
 end
 // ---- datapath state without reset (written before read, as in ot_dsdv_fixed_issue)
 wire pw_busy=busy||validating||sc_r||sc_v||sc_fin;
 wire pw_hdr_bad=pw_a!=0||pw_d[24:17]!=0||pw_d[6:0]!=7'(STAGE)||pw_d[16:9]==0||pw_d[16:9]>NOPS;
 wire do_begin=pw_v&&!pw_busy&&pw_d[27:26]==3&&!pw_hdr_bad&&!pw_d[25];
 wire do_write=pw_v&&!pw_busy&&pw_d[27:26]!=3&&begun&&pw_a<NOPS;
 wire do_seal=pw_v&&!pw_busy&&pw_d[27:26]==3&&!pw_hdr_bad&&pw_d[25];
 wire[75:0]wd76=pw_d[27:26]==2'd0 ? {50'd0,pw_d[25:0]}:pw_d[27:26]==2'd1 ? {24'd0,pw_d[25:0],26'd0}:{pw_d[23:0],52'd0};
 wire[75:0]wm76=pw_d[27:26]==2'd0 ? {50'd0,{26{1'b1}}}:pw_d[27:26]==2'd1 ? {24'd0,{26{1'b1}},26'd0}:{{24{1'b1}},52'd0};
 assign cal_w_ce=do_write;assign cal_w_addr={1'b0,pw_a[6:1]};
 assign cal_wd=pw_a[0]?{wd76,76'd0}:{76'd0,wd76};assign cal_wm=pw_a[0]?{wm76,76'd0}:{76'd0,wm76};
 integer i3;
 always @*begin rd_ld=0;for(i3=0;i3<NOPS;i3=i3+1)rd_ld=rd_ld|({3{sc_oh[i3]}}&loaded[i3]);end
 integer i2,s2;
 always @(posedge clk)begin
  if(do_begin)for(i2=0;i2<NOPS;i2=i2+1)loaded[i2]<=0;
  if(do_write)loaded[pw_a][pw_d[27:26]]<=1'b1;
  if(do_seal)sc_oh<={{(NOPS-1){1'b0}},1'b1};else if(validating)sc_oh<=sc_oh<<1;
  if(validating)begin sc_ld0<=rd_ld;sc_half<=scan_index[0];sc_i1<=scan_index==8'd1;end
  sc_ld<=sc_ld0;sc_row<=sc_half?cal_rd0[151:76]:cal_rd0[75:0];
  if(sc_r&&sc_i1)w0<=cal_rd0;                    // word 0 (rows 0 / 1): an accept loads it into CW
  if(do_seal)scan_first<=1'b1;
  if(sc_v&&sc_in)begin
   scan_first<=1'b0;scan_pi<=sc_row[51:28];scan_pe<=sc_row[27:24];scan_eq<=!scan_first&&sc_row[51:28]==scan_pi;
   if(sc_row[27:24]<NENG)begin scan_seen[sc_row[27:24]]<=1'b1;scan_ld[sc_row[27:24]]<=sc_row[75:52];end
  end
  if(do_seal)scan_seen<=0;
  for(s2=0;s2<2;s2=s2+1)begin
   agp[s2]<=age[s2];
   if(acc[s2])begin
    age[s2]<=0;cw[s2]<=w0;nwr[s2]<=nw[s2];ck[s2]<=6'd0;ck2[s2]<=6'd2;ck3[s2]<=6'd3;hh[s2]<=1'b0;
    users[s2]<=job_user;positions[s2]<=job_pos;tokens[s2]<=job_tok;
   end else if(active[s2])begin
    age[s2]<=age[s2]+1'b1;
    if(adv[s2])begin cw[s2]<=nwr[s2];nwr[s2]<=nw[s2];ck[s2]<=ck[s2]+6'd1;ck2[s2]<=ck3[s2];ck3[s2]<=ck3[s2]+6'd1;end
    if(hit[s2]&&!hitb[s2])hh[s2]<=~hh[s2];
   end
  end
 end
 // commands: straight from the walker's current rows
 genvar ge;
 generate for(ge=0;ge<NENG;ge=ge+1)begin:g_command
  wire a0=ENG_PRESENT[ge]&&hit[0]&&heng[0]==4'(ge),b0=ENG_PRESENT[ge]&&hitb[0]&&beng[0]==4'(ge);
  wire a1=ENG_PRESENT[ge]&&hit[1]&&heng[1]==4'(ge),b1=ENG_PRESENT[ge]&&hitb[1]&&beng[1]==4'(ge);
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)cmd_v[ge]<=0;
   else cmd_v[ge]<=a0|b0|a1|b1;
  end
  always @(posedge clk)
   cmd_d[84*ge+:84]<=({84{a0}}&{1'b0,users[0],positions[0],tokens[0],ra[0][23:0],7'(opa[0]+7'(OP_BASE))})|
                      ({84{b0}}&{1'b0,users[0],positions[0],tokens[0],rb[0][23:0],7'(opb[0]+7'(OP_BASE))})|
                      ({84{a1}}&{1'b1,users[1],positions[1],tokens[1],ra[1][23:0],7'(opa[1]+7'(OP_BASE))})|
                      ({84{b1}}&{1'b1,users[1],positions[1],tokens[1],rb[1][23:0],7'(opb[1]+7'(OP_BASE))});
 end endgenerate
endmodule
`default_nettype wire
