`timescale 1ns/1ps
// HBM-VMEARLY-IDX 2026-10-19: compiler EARLY ISSUE of the IDX.INDEX operand reads (VM -> query store) at the d4g GEN2c
// budget, on the UNCHANGED as-built RTL: operand reader ot_hbm_idx_vm_query_static_n12 #(VM_RT_EXTRA 171) on the actual VM
// banks (ot_vms_bank_static) behind the faces pin flop and per-bank die lanes padded to the budget (as tb_vm_query_n12_lat
// n12_dir), feeding the consumer = the query quantiser + query store ot_hbm_idx_query_static_core (one store slot).
// The bench is the COMPILER: every read, frame_start, emit (= operand USE) and producer VM write sits on a static edge from
// the constants below; nothing waits on data / ready / credits.
//   R = 4 back-to-back INDEX operand records (32 heads x 4 FP32 blocks of 1,024 b + 2 head-weight sectors each);
//   record 2 DEPENDS on a VM write: a producer rewrites rows 0..63 (record 0's rows) and the weight row 258 during
//   record 1, so its reads may issue only after the producer retired (RAW).
// Calendar (all edges static; LB = read issue -> block at the consumer, QL = block -> first legal emit (14 = the query store rule ">=14 edges after the last head block"), G = use pacing):
//   record i reads: weight descriptor at A_i, query descriptors A_i+1 .. A_i+128 (head-major); head h is used (emit) at
//   U_i,h = A_i + 4h + 4 + LB + QL, paced G edges apart; frame_start(i) at F_i = U_i-1,31 + 1 (the store is free).
//   ISSUE_AHEAD 0 (today):   A_i = U_i-1,31 + 1                         (issue after the previous record retired)
//   ISSUE_AHEAD 1 (early):   A_i = max(RAW_i, F_i - LB)                 (the read lands as the store frees: NBUF = 1
//                            is enough because a record's last use precedes its end; slot = the store, static)
//   RAW_i = producer's last VM write + PW (bank pin flop + commit) for record 2, 0 otherwise.
// Exposed edges of record i (i > 0) = first use(i) - last use(i-1) - G (the gap beyond the steady use pacing).
// MUT 0 pass; 1 slot ignored: record i+1 issued as soon as the reader is free (A_i + 130), frame_start just before its
//   landing -> the live store of record i is cleared / overwritten (must FAIL: fault or data); 2 RAW ignored: the
//   dependent record issued at F - LB before the producer retired -> stale rows (must FAIL: data); 3 ISSUE_AHEAD ignored:
//   EXPECT 1 but the calendar runs ISSUE_AHEAD 0 (must FAIL: exposure check).
module tb_idx_vme_n12;
`ifndef VMRT
`define VMRT 171
`endif
`ifndef IA
`define IA 0
`endif
`ifndef MUT
`define MUT 0
`endif
`ifndef LB
`define LB 183
`endif
`ifndef QL
`define QL 14
`endif
`ifndef G
`define G 4
`endif
 localparam integer MUT=`MUT, R=4, MAXD=256, LB=`LB, QL=`QL, G=`G, PW=5;
 localparam integer EXPECT=(MUT==3)?1:`IA;          // the ISSUE_AHEAD the bench checks
 localparam integer IA=(MUT==3)?0:`IA;               // the ISSUE_AHEAD the calendar runs
 localparam integer TOT=`VMRT-3;                     // bank lanes rq + rr (excluding the faces pin flop), as n12_dir
 function automatic integer lq(input integer b); lq=60+3*b; endfunction
 function automatic integer lr(input integer b); lr=TOT-lq(b); endfunction
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,weight_slot=0,query_slot=0;reg[6:0]query_index=0;
 reg[15:0]weight_sector=0,query_sector=0;
 wire[135:0]vm_rq;wire[2055:0]vm_rr;wire block_v;wire[4:0]block_head;wire[1:0]block_number;
 wire[1023:0]block_data;wire[15:0]head_weight;wire operand_fault;
 reg[2247:0]wr=0;wire[143:0]status;
 ot_hbm_idx_vm_query_static_n12 #(.VM_RT_EXTRA(`VMRT)) operand(.clk(clk),.rst_n(rst_n),.sid(2'd0),.weight_slot(weight_slot),
  .query_slot(query_slot),.query_index(query_index),.weight_sector(weight_sector),.query_sector(query_sector),.vm_rq(vm_rq),.vm_rr(vm_rr),
  .block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),.fault(operand_fault));
 for(genvar b=0;b<8;b=b+1)begin:bank
  reg[16:0]q[0:MAXD];reg[256:0]r[0:MAXD];reg[16:0]pin_rq;reg[280:0]pin_wq;
  wire[256:0]rr_bank;
  initial begin for(integer d=0;d<=MAXD;d=d+1)begin q[d]=0;r[d]=0;end pin_rq=0;pin_wq=0;end
  always @(posedge clk)begin
   q[0]<=vm_rq[b*17+:17];r[0]<=rr_bank;
   for(integer d=1;d<=MAXD;d=d+1)begin q[d]<=q[d-1];r[d]<=r[d-1];end
  end
  wire[16:0]lane_rq=q[lq(b)-1];
  always @(posedge clk)begin pin_rq<=rst_n?lane_rq:17'd0;pin_wq<=wr[b*281+:281];end
  assign vm_rr[b*257+:257]=r[lr(b)-1];
  wire done,dqd,kqd,xd,x2d;wire[275:0]eg;wire[265:0]pr;
  ot_vms_bank_static #(.RG(1),.WG(1))mem(.clk(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'd0),.rslot_v(pin_rq[16]),.rslot(1'b0),
   .wslot_v(pin_wq[280]),.wslot(3'd0),.rq(pin_rq),.rr(rr_bank),.wq(pin_wq),.wq_done(done),
   .dq(281'd0),.dq_done(dqd),.kq(281'd0),.kq_done(kqd),.xq(276'd0),.xq_done(xd),.xq2(276'd0),.xq2_done(x2d),.eg(eg),.pq(285'd0),.pr(pr),.status(status[b*18+:18]));
 end
 reg frame_start=0,emit_v=0;reg[4:0]emit_head=0;
 wire ql_v;wire[7:0]ql_head;wire[511:0]ql_codes;wire[31:0]ql_sc;wire[15:0]ql_w;wire query_fault;
 ot_hbm_idx_query_static_core quant(.clk(clk),.clk_quant(clk),.clk_quant_delay(clk),.clk_bank({4{clk}}),.rst_n(rst_n),.frame_start(frame_start),
  .block_v(block_v),.block_head(block_head),.block_number(block_number),.block_data(block_data),.head_weight(head_weight),
  .emit_v(emit_v),.emit_head(emit_head),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.fault(query_fault));
 reg[1023:0]x[0:R*128-1];reg[559:0]gold[0:R*32-1];
 // ---- static calendar (the compiler), computed before reset release
 integer A[0:R-1],F[0:R-1],U[0:R-1][0:31],RAW[0:R-1],QROW[0:R-1];
 integer PSTART,PLAST,T0;
 integer cycle=0;
 always @(posedge clk)cycle<=cycle+1;
 // ---- observation
 integer fb=-1,blocks=0,uses=0,errors=0,lb_bad=0,first_use[0:R-1],last_use[0:R-1],cur_rec=0,cur_use=0;
 integer blk_seen[0:R-1];
 reg[63:0]digest=64'h0;
 integer exp_issue[0:R*128-1];
 always @(negedge clk)begin
  if(rst_n&&block_v===1'b1)begin
   // block of record/descriptor: the record is the one whose read window this landing belongs to (static)
   integer rr_,jj;rr_=-1;jj=-1;
   for(integer i=0;i<R;i=i+1)if(cycle>=A[i]+1+LB && cycle<=A[i]+128+LB)begin rr_=i;jj=cycle-(A[i]+1+LB);end
   blocks++;if(fb<0)fb=cycle-A[0]-1;
   if(rr_<0)lb_bad++;
   else begin
    blk_seen[rr_]++;
    if({block_head,block_number}!==7'(jj))lb_bad++;
    if(block_data!==x[rr_*128+jj]||head_weight!==16'h3f00+16'(32*rr_)+16'(block_head))errors++;
   end
  end
  if(ql_v===1'b1)begin
   uses++;
   if({ql_w,ql_sc,ql_codes}!==gold[cur_rec*32+ql_head])errors++;
   digest={digest[62:0],digest[63]}^{ql_w,ql_sc[15:0],ql_codes[31:0]}^{32'h0,ql_codes[511:480]};
   if(cur_use==0)first_use[cur_rec]=cycle;
   last_use[cur_rec]=cycle;
   cur_use++;if(cur_use==32)begin cur_use=0;cur_rec++;end
  end
 end
 // ---- driver: one static table lookup per edge
 task automatic drive(input integer c);
  weight_slot=0;query_slot=0;frame_start=0;emit_v=0;wr=0;
  for(integer i=0;i<R;i=i+1)begin
   if(c==F[i])frame_start=1;
   if(c==A[i])begin weight_slot=1;weight_sector=16'((256+i)*8);end
   if(c>A[i]&&c<=A[i]+128)begin query_slot=1;query_index=7'(c-A[i]-1);query_sector=16'(QROW[i]*8);end
   for(integer h=0;h<32;h=h+1)if(c==U[i][h])begin emit_v=1;emit_head=5'(h);end
  end
  // producer of record 2: rows 0..63 (record 0's rows) at PSTART.., weight row 258 at PLAST
  if(c>=PSTART&&c<PSTART+64)vmrow(c-PSTART,2,c-PSTART);
  if(c==PLAST)vmw(258,2);
 endtask
 task automatic vmrow(input integer row,input integer rec,input integer rel);   // q rows of record rec
  reg[255:0]d;
  for(integer b=0;b<8;b=b+1)begin
   d=x[rec*128+(rel*8+b)/4][((rel*8+b)%4)*256+:256];
   wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),d,8'hff};
  end
 endtask
 task automatic vmw(input integer row,input integer rec);                       // head-weight row of record rec
  reg[255:0]d;
  for(integer b=0;b<2;b=b+1)begin
   for(integer w=0;w<16;w=w+1)d[w*16+:16]=16'h3f00+16'(32*rec+16*b+w);
   wr[b*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),d,8'hff};
  end
 endtask
 integer exposed[0:R-1];integer exp_ok,raw_bound;
 initial begin
  $readmemh("query.hex",x);$readmemh("gold.hex",gold);
  for(integer i=0;i<R;i=i+1)begin blk_seen[i]=0;first_use[i]=-1;last_use[i]=-1;RAW[i]=0;end
  QROW[0]=0;QROW[1]=64;QROW[2]=0;QROW[3]=192;
  T0=4+3*64+4+8;                                     // preload: records 0, 1, 3 rows + weights, then the first record
  // record 0 at T0; record i>0 from the calendar rule
  A[0]=T0;F[0]=T0-2;
  for(integer i=0;i<R;i=i+1)begin
   if(i>0)begin
    F[i]=U[i-1][31]+1;
    if(i==2)begin
     // producer: its last write retires late enough that RAW binds the early issue (stale rows if ignored)
     PLAST=F[i]-LB+150-PW;PSTART=PLAST-64;RAW[i]=PLAST+PW;
    end
    if(MUT==1)A[i]=A[i-1]+130;
    else if(IA==0)A[i]=U[i-1][31]+1;
    else if(MUT==2&&i==2)A[i]=F[i]-LB;
    else A[i]=(RAW[i]>F[i]-LB)?RAW[i]:F[i]-LB;
    if(IA==0&&A[i]<RAW[i])A[i]=RAW[i];
    if(MUT==1)F[i]=A[i]+LB-1;
   end
   for(integer h=0;h<32;h=h+1)begin
    U[i][h]=A[i]+4*h+4+LB+QL;
    if(h>0&&U[i][h]<U[i][h-1]+G)U[i][h]=U[i][h-1]+G;
   end
  end
  // ---- run
  repeat(4)@(negedge clk);rst_n=1;
  for(integer row=0;row<64;row=row+1)begin vmrow(row,0,row);@(negedge clk);end
  for(integer row=0;row<64;row=row+1)begin vmrow(64+row,1,row);@(negedge clk);end
  for(integer row=0;row<64;row=row+1)begin vmrow(192+row,3,row);@(negedge clk);end
  wr=0;vmw(256,0);@(negedge clk);wr=0;vmw(257,1);@(negedge clk);wr=0;vmw(259,3);@(negedge clk);wr=0;
  while(cycle<A[0]-2)@(negedge clk);
  while(cycle<=U[R-1][31]+8)begin drive(cycle);@(negedge clk);end
  weight_slot=0;query_slot=0;emit_v=0;wr=0;repeat(8)@(negedge clk);
  exp_ok=1;
  for(integer i=1;i<R;i=i+1)begin
   exposed[i]=first_use[i]-last_use[i-1]-G;
   raw_bound=(i==2);
   // EXPECT 1: an independent record exposes only the consumer's store latency (QL + 5 - G); the dependent one exposes
   // exactly RAW + LB + 4 + QL - its predecessor's last use - G (RAW-bound, nothing more)
   if(EXPECT==1&&!raw_bound&&exposed[i]>QL+5-G)exp_ok=0;
   if(EXPECT==1&&raw_bound&&exposed[i]!=RAW[i]+LB+QL+5-last_use[i-1]-G)exp_ok=0;
   if(EXPECT==0&&exposed[i]<LB)exp_ok=0;
  end
  $display("IDX_VME_N12 MUT%0d IA%0d EXPECT%0d vmrt%0d LB%0d QL%0d G%0d blocks%0d uses%0d errors%0d lb_bad%0d fault%0d exposed_r1 %0d exposed_r2_dep %0d exposed_r3 %0d raw_r2 %0d A %0d %0d %0d %0d last_use %0d %0d %0d %0d span %0d lb_meas %0d digest %016h",
   MUT,IA,EXPECT,`VMRT,LB,QL,G,blocks,uses,errors,lb_bad,(operand_fault!==1'b0)||(query_fault!==1'b0)||(|status),
   exposed[1],exposed[2],exposed[3],RAW[2],A[0],A[1],A[2],A[3],last_use[0],last_use[1],last_use[2],last_use[3],
   last_use[R-1]-first_use[0],fb,digest);
  if(errors||lb_bad||(operand_fault!==1'b0)||(query_fault!==1'b0)||(|status)||blocks!=128*R||uses!=32*R)begin
   $display("IDX_VME_N12 FAIL data/fault");$fatal(1,"IDX early issue: data / fault / landing mismatch");
  end
  if(!exp_ok)begin $display("IDX_VME_N12 FAIL exposure");$fatal(1,"IDX early issue: exposure check");end
  $display("IDX_VME_N12 PASS");
  $finish;
 end
endmodule
