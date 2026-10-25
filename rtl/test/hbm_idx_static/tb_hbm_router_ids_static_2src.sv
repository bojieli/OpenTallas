`timescale 1ns/1ps
`default_nettype none
// Minimum arithmetic producer -> actual CQ write -> collector. VM supplies FP32 scores,
// never result IDs. No fixture/host ID injection. Native VM timing closure is a separate gate.
module tb_hbm_router_ids_static_2src;
 parameter integer SMUT=0, PAIR=0;
 parameter integer XRT=0,COLLAR=0;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,go=0,run_v=0;reg[7:0]layer=0;reg[155:0]rec=0;
 wire[135:0]rq;reg[2055:0]rr=0;wire[337:0]cq;wire[1:0]seq;
 wire[337:0]cq_raw;wire[1:0]seq_raw;reg[337:0]cq_pin=0;reg[1:0]seq_pin=0;
 reg go_pin=0;reg[155:0]rec_pin=0;
 wire[155:0]er=COLLAR?rec_pin:rec;
 always @(posedge clk)begin go_pin<=go;rec_pin<=rec;cq_pin<=cq_raw;seq_pin<=seq_raw;end
 assign cq=COLLAR?cq_pin:cq_raw;assign seq=COLLAR?seq_pin:seq_raw;
 wire busy,done,ef;wire iv,cf;wire[7:0]il;wire[53:0]ids;wire[15:0]cohort;
 integer mutant=0,seen=0,expected_layer=0,pass=0,run_number=0;
 reg desc_we=0;reg[255:0]desc=0;wire irunning,idone,ifault,ireserve,istart;
 wire[14:0]irow;wire[31:0]ibase;reg pdone=0;
 reg[135:0]pipe[0:8];reg[337:0]late=0;
 wire[337:0]chosen=mutant==3?late:cq;
 reg[337:0]tap;
 always @*begin
  tap=chosen;
  if(mutant==2)begin tap[48+:32]=chosen[80+:32];tap[80+:32]=chosen[48+:32];end
 end
 ot_hbm_idx_topk_static #(.RT_EXTRA(XRT)) dut(.clk(clk),.rst_n(rn),.sid(2'd0),.go(COLLAR?go_pin:go),.k(er[3:0]),.order(er[4]),
  .n(er[24:5]),.m(er[44:25]),.a_mirror(er[45]),.a_base(er[63:46]),.a_str(er[81:64]),
  .o_mirror(er[82]),.o_base(er[100:83]),.o_str(er[118:101]),.has_r(er[119]),
  .r_base(er[137:120]),.r_str(er[155:138]),.vm_rq(rq),.vm_rr(rr),.cq(cq_raw),.cq_seq(seq_raw),
  .cr(274'd0),.busy(busy),.done(done),.fault(ef));
 ot_hbm_router_ids_static_2src #(.XRT(XRT),.GO_DELAY(COLLAR),.CQ_DELAY(COLLAR),.MUT(SMUT)) collect(.clk(clk),.rst_n(rn),
  .run_v(run_v&&(PAIR||run_number%2==0)),.run_layer(mutant==1?layer+8'd1:layer),
  .run1_v(run_v&&(PAIR||run_number%2==1)),.run1_layer(layer),.topk_go(go),.topk_rec(rec),
  .cq(tap),.cq_seq(seq),.ids_v(iv),.ids_layer(il),.ids(ids),.ids_cohort(cohort),.fault(cf));
 ot_hbm_svc_sm_issuer_rel #(.ID_COHORT(1)) issuer(.clk(clk),.rst_n(rn),.desc_we(desc_we),.desc_addr(8'd0),.desc_data(desc),
  .run_v(run_v),.run_base(8'd0),.run_count(9'd1),.run_layer(layer),
  .ids_v((iv&&!(mutant==4&&cohort>1))||(mutant==6&&run_v&&seen>0)),.ids_layer(il),.ids(ids),
  .ids_cohort(mutant==5&&cohort>1?cohort-16'd1:cohort),.running(irunning),.run_done(idone),.fault(ifault),
  .reserve_v(ireserve),.reserve_ready(1'b1),.reserve_base(ibase),.reserve_row_base(irow),.reserve_total(),.reserve_bank(),
  .reserve_epoch(),.reserve_rows(),.reserve_tag_base(),.block_ready(4'hf),.cache_ready(2'b11),.cache_owned(2'b0),
  .start_v(),.start_bank(),.start_epoch(),.program_start_v(istart),.program_start_base(),.program_start_limit(),
  .program_start_loops(),.program_start_ctx(),.program_done(pdone));
 always @(posedge clk)pdone<=istart;
 always @(negedge clk)if(rn&&ireserve)begin
  if(irow!=47||ibase[9:7]!=2)$fatal(1,"ROUTER_IDS_2SRC golden expert address wrong row%0d slot%0d",irow,ibase[9:7]);
  pass=pass+1;
 end
 // Fixed request->FP32 score return. Every score is produced from its word address,
 // so the engine must compare all 384 real words to find the six largest.
 integer b,p,w,index;
 always @(posedge clk)begin
  late<=cq;
  pipe[0]<=rq;
  for(p=1;p<9;p=p+1)pipe[p]<=pipe[p-1];
  rr<=0;
  for(b=0;b<8;b=b+1)if(pipe[5+XRT][17*b+16])begin
   rr[257*b+256]<=1;
   for(w=0;w<8;w=w+1)begin
    index=(int'(pipe[5+XRT][17*b+:15])-256)*8+w;
    rr[257*b+32*w+:32]<=32'h3f800000+32'(index*1024);
   end
  end
 end
 always @(negedge clk)if(rn&&iv)begin
  if(il!=expected_layer)$fatal(1,"ROUTER_IDS_2SRC wrong layer %0d expected %0d",il,expected_layer);
  for(integer x=0;x<6;x=x+1)if(ids[9*x+:9]!=9'(378+x))
   $fatal(1,"ROUTER_IDS_2SRC wrong actual TOPK id[%0d]=%0d",x,ids[9*x+:9]);
  seen=seen+1;
  run_number=run_number+1;
  if(cohort!=run_number)$fatal(1,"ROUTER_IDS_2SRC stale cohort %0d expected %0d",cohort,run_number);
 end
 always @(negedge clk)if(cq[337])$display("CQ t=%0t age=%0d due=%0d packet=%h idsbad=%b",$time,collect.u_base.age,collect.u_base.due,cq,collect.u_base.bad_ids);
 always @(posedge cf)$display("COLLECTFAULT t=%0t age=%0d due=%0d packet=%h active=%b used=%b",$time,collect.u_base.age,collect.u_base.due,collect.u_base.packet,collect.u_base.active,collect.u_base.used);
 initial begin
  if($value$plusargs("mutant=%d",mutant))begin end
  for(integer x=0;x<9;x=x+1)pipe[x]=0;
  repeat(4)@(negedge clk);rn=1;repeat(5)@(negedge clk);
  desc[255:240]=16'h5d15;desc[71:65]=1;desc[102:92]=1;desc[118:103]=1;
  desc[142:119]=200;desc[172:158]=1;desc[176:173]=1;
  desc_we=1;@(negedge clk);desc_we=0;repeat(4)@(negedge clk);
  // Four launches including same-layer successive tokens and changed layer; one reset between groups.
  for(integer r=0;r<4;r=r+1)begin
   layer=r<2?8'd2:8'd14;expected_layer=layer;
   run_v=1;@(negedge clk);run_v=0;repeat(3)@(negedge clk);
   rec=0;rec[3:0]=6;rec[4]=1;rec[24:5]=384;rec[44:25]=1;
   rec[63:46]=18'h800;rec[81:64]=384;rec[100:83]=18'hc00;rec[118:101]=6;
   go=1;@(negedge clk);go=0;
   repeat(240)@(negedge clk);
   if(cf)$fatal(1,"ROUTER_IDS_2SRC collector fault mutant%0d",mutant);
   if(ifault)$fatal(1,"ROUTER_IDS_2SRC issuer identity/schedule fault mutant%0d",mutant);
   if(seen!=r+1)$fatal(1,"ROUTER_IDS_2SRC missing result %0d",seen);
   repeat(20)@(negedge clk);
   if(r==1)begin
    rn=0;run_number=0;repeat(4)@(negedge clk);rn=1;repeat(5)@(negedge clk);
    desc_we=1;@(negedge clk);desc_we=0;repeat(4)@(negedge clk);
   end
  end
  if(pass!=4)$fatal(1,"ROUTER_IDS_2SRC missing expert address checks %0d",pass);
  $display("ROUTER_IDS_2SRC PASS actual_TOPK_runs=%0d six_ids_each=1 repeated_layer_cohorts=1 reset_reload=1 expert_reserves=%0d",seen,pass);
  $finish;
 end
endmodule
`default_nettype wire
