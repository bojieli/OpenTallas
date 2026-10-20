`timescale 1ns/1ps
// CTLM7 (2026-10-20): cycle-exact, depth-safe twin of ot_qfd_xpf_static_schedule
// (same ports, same parameters, same outputs on every edge; 0 added schedule
// edges).  The original evaluated, in one cycle, 32-bit record arithmetic
// (first_write >= arm+T+3), the serial table-good loop and a priority chain of
// sticky-fault if statements against the live 32-bit cycle counter
// (2927 ps / 95 levels, records[0][93] -> fault).  Here:
//  * every record-derived quantity is registered AT LOAD from cfg_data
//    (rec_ok = the first_write/arm check; X-1 and X==0 for arm, late-arm,
//    issue and first_write), so no adder sits in front of a compare;
//  * cycle matches are REGISTERED one-hot flags predicted one edge early
//    (next cycle == X  <=>  start ? X==0 : cycle == X-1), cycle > arm likewise;
//  * the stage/count record select is a registered one-hot (sel) captured at
//    start (records, count and stage_r are frozen while active: any cfg
//    request while active only faults);
//  * the sticky fault is fault | OR(all fault terms) built as a flat OR tree.
// Records stay flops (4 x 188 b = 752 b < 2 kb).
module ot_qfd_xpf_static_schedule_p #(
 parameter integer N=8, ARM_TRANSPORT_EDGES=0, MUT_LATE=0,
 parameter integer IW=(N<2)?1:$clog2(N)
)(
 input wire clk,rst_n,
 input wire cfg_v,input wire [IW-1:0] cfg_index,input wire [187:0] cfg_data,
 input wire cfg_clear,cfg_seal,input wire [IW:0] cfg_count,
 input wire start,stop,input wire [5:0] stage,
 input wire me_issue,input wire [11:0] me_pc,
 input wire su_issue,input wire [11:0] su_pc,
 input wire cp_issue,input wire [11:0] cp_pc,
 output wire image_ready,output reg [71:0] xpf,output reg fault,output reg active,output reg [31:0] cycle
);
 localparam [31:0] LATE=(MUT_LATE!=0)?32'd4:32'd0;
 localparam [31:0] TEDGE=ARM_TRANSPORT_EDGES+3;
 reg [187:0] records[0:N-1];
 reg [N-1:0] loaded,armed,issued;
 reg sealed;reg [IW:0] count;reg [5:0] stage_r;
 assign image_ready=sealed&&!fault;
 // load-time derived record state (no reset: valid whenever the record is)
 reg [N-1:0] rec_ok;                       // first_write >= arm + T + 3 (32-bit wrap, as the original)
 reg [31:0] al_m1[0:N-1],is_m1[0:N-1],fw_m1[0:N-1];
 reg [N-1:0] al_z,is_z,fw_z;
 // registered per-record cycle matches, valid while active
 reg [N-1:0] h_al,h_is,h_fw,gt_ar,sel;
 integer i,j;
 // ---------------------------------------------------------------- cfg-side
 wire cfg_any=cfg_v||cfg_clear||cfg_seal;
 wire [31:0] w_arm=cfg_data[123:92],w_iss=cfg_data[155:124],w_fw=cfg_data[187:156];
 wire [31:0] w_al=w_arm+LATE;
 // CTLM8: w_fw < (w_arm + TEDGE mod 2^32) without two serial carry chains: X0 = fw - arm - T and
 // X1 = X0 + 2^32 (34-b, one 3:2 + one carry tree each, in parallel); arm + T overflows 32 b <=> arm > 2^32-1-T
 localparam [33:0] NT0=34'h0-{2'b00,TEDGE}, NT1=NT0+34'h1_0000_0000;
 wire [33:0] xa={2'b00,w_fw}, xb=~{2'b00,w_arm};
 wire [33:0] xs0=xa^xb^NT0, xk0={((xa[32:0]&xb[32:0])|(xa[32:0]&NT0[32:0])|(xb[32:0]&NT0[32:0])),1'b1};
 wire [33:0] xs1=xa^xb^NT1, xk1={((xa[32:0]&xb[32:0])|(xa[32:0]&NT1[32:0])|(xb[32:0]&NT1[32:0])),1'b1};
 wire [33:0] x0,x1;
 ot_ks_add #(.W(34)) u_x0(.a(xs0),.b(xk0),.cin(1'b0),.s(x0));
 ot_ks_add #(.W(34)) u_x1(.a(xs1),.b(xk1),.cin(1'b0),.s(x1));
 wire w_ovf=w_arm>(32'hFFFF_FFFF-TEDGE);
 wire w_ok=!(w_ovf?x1[33]:x0[33]);   // == !(w_fw<w_arm+TEDGE)
 wire wr_ok=cfg_v&&!cfg_clear&&!active&&!sealed&&cfg_index<N&&cfg_data[0]&&cfg_data[85:84]!=0;
 // pair conflicts (record i vs any earlier j), registered from the exact next-state of the
 // records (they change only on an accepted write), so the seal check is a flat AND
 reg [187:0] rec_n[0:N-1];
 reg [N-1:0] rbad_n,rbad;
 always @* begin
  for(i=0;i<N;i=i+1)rec_n[i]=(rst_n&&wr_ok&&cfg_index==i)?cfg_data:records[i];
  for(i=0;i<N;i=i+1)begin
   rbad_n[i]=1'b0;
   for(j=0;j<i;j=j+1)
    if(rec_n[i][91:72]==rec_n[j][91:72]||
       (rec_n[i][91:86]==rec_n[j][91:86]&&rec_n[i][123:92]==rec_n[j][123:92]))rbad_n[i]=1'b1;
  end
 end
 always @(posedge clk)rbad<=rbad_n;
 reg good;reg [N-1:0] inn;
 always @* begin
  for(i=0;i<N;i=i+1)inn[i]=i<cfg_count;
  good=cfg_count!=0&&cfg_count<=N&&((inn&~(loaded&rec_ok&~rbad))==0);
 end
 wire f_cfg=cfg_any&&(active||(!cfg_clear&&(cfg_v?(sealed||cfg_index>=N||!cfg_data[0]||cfg_data[85:84]==0):(!good||sealed))));
 // ---------------------------------------------------------------- start
 wire st_ok=start&&!active&&sealed&&records[0][91:86]==stage;
 wire f_start=start&&!st_ok;
 // ---------------------------------------------------------------- arm pick (lowest index wins, as the original)
 wire [N-1:0] arm_hit=sel&h_al;
 reg have_arm;reg [IW-1:0] arm_pick;
 always @* begin
  have_arm=active&&(|arm_hit);arm_pick=0;
  for(i=N-1;i>=0;i=i-1)if(arm_hit[i])arm_pick=i;
 end
 // ---------------------------------------------------------------- active faults
 reg [N-1:0] f_rec,iss_ok,mon_hit,f_mon,f_stp;
 always @* begin
  for(i=0;i<N;i=i+1)begin
   iss_ok[i]=!((records[i][85:84]==1&&(!me_issue||me_pc!=records[i][83:72]))||
               (records[i][85:84]==2&&(!su_issue||su_pc!=records[i][83:72]))||
               (records[i][85:84]==3&&(!cp_issue||cp_pc!=records[i][83:72])));
   f_rec[i]=active&&sel[i]&&((gt_ar[i]&&!armed[i])||(h_is[i]&&!iss_ok[i])||(h_fw[i]&&!armed[i]));
   mon_hit[i]=sel[i]&&((me_issue&&records[i][85:84]==1&&me_pc==records[i][83:72])||
                       (su_issue&&records[i][85:84]==2&&su_pc==records[i][83:72])||
                       (cp_issue&&records[i][85:84]==3&&cp_pc==records[i][83:72]));
   f_mon[i]=mon_hit[i]&&(!h_is[i]||issued[i]);
   f_stp[i]=stop&&sel[i]&&(!armed[i]||!issued[i]);
  end
 end
 wire any_issue=me_issue||su_issue||cp_issue;
 wire f_inact=(any_issue||stop)&&!active;
 // when !active every monitor/stop term is already covered by f_inact, so the
 // per-record terms need sel/h_* only while active (where they are exact).
 wire f_any=f_cfg||f_start||f_inact||(active&&((|f_rec)||(any_issue&&(|f_mon))||(|f_stp)));
 // ---------------------------------------------------------------- next-cycle prediction
 wire [31:0] cyc_p1=cycle+1'b1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;armed<=0;issued<=0;sealed<=0;active<=0;count<=0;cycle<=0;stage_r<=0;xpf<=0;fault<=0;
   h_al<=0;h_is<=0;h_fw<=0;gt_ar<=0;sel<=0;end
  else begin
   xpf[0]<=0;
   if(f_any)fault<=1;
   // configuration (all requests while active only fault)
   if(cfg_any&&!active)begin
    if(cfg_clear)begin loaded<=0;sealed<=0;count<=0;end
    else if(cfg_v)begin
     if(wr_ok)begin records[cfg_index]<=cfg_data;loaded[cfg_index]<=1;end
    end else if(good&&!sealed)begin sealed<=1;count<=cfg_count;end
   end
   if(st_ok)begin
    active<=1;cycle<=0;stage_r<=stage;armed<=0;issued<=0;
    // a same-edge cfg_clear (accepted: not active) zeroes count before the original reads it
    for(i=0;i<N;i=i+1)sel[i]<=!(cfg_clear&&!active)&&(i<count)&&records[i][91:86]==stage;
   end
   if(active)begin
    cycle<=cyc_p1;
    if(have_arm)begin xpf<=records[arm_pick][71:0];armed[arm_pick]<=1;end
    for(i=0;i<N;i=i+1)if(sel[i]&&h_is[i]&&iss_ok[i])issued[i]<=1;
   end
   if(stop)active<=0;
   // flags for the NEXT cycle: start -> cycle 0; active -> cycle+1
   for(i=0;i<N;i=i+1)begin
    h_al[i]<=st_ok?al_z[i]:(cycle==al_m1[i]);
    h_is[i]<=st_ok?is_z[i]:(cycle==is_m1[i]);
    h_fw[i]<=st_ok?fw_z[i]:(cycle==fw_m1[i]);
    gt_ar[i]<=!st_ok&&(cycle>=records[i][123:92])&&(cycle!=32'hFFFFFFFF);
   end
  end
 end
 // load-time derived state follows the record write exactly
 always @(posedge clk)
  if(rst_n&&cfg_any&&!active&&!cfg_clear&&wr_ok)begin
   rec_ok[cfg_index]<=w_ok;
   al_m1[cfg_index]<=w_al-1'b1;is_m1[cfg_index]<=w_iss-1'b1;fw_m1[cfg_index]<=w_fw-1'b1;
   al_z[cfg_index]<=w_al==0;is_z[cfg_index]<=w_iss==0;fw_z[cfg_index]<=w_fw==0;
  end
endmodule
