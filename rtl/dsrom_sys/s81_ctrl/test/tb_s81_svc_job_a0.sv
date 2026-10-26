`timescale 1ns/1ps
module tb_s81_svc_job_a0;
parameter integer MUT=0, SEED=1;
reg ck=0, rn=0; always #1 ck=~ck;
reg [32:0] jc=0;reg [514:0] q=0;reg [512:0] ad=0;
wire [1:0] da,db;wire [514:0] qa,qb;
ot_s81_svc_job g(.ck(ck),.rs_n(rn),.j_cmd(jc),.j_dn(da),.q(q),.core_q(qa),.ad({513'd0,ad}),.xd({512'd0,1'b0,1'b1}),.od({512'd0,1'b0,1'b1}));
ot_s81_svc_job_a0 #(.MUT(MUT)) d(.ck(ck),.rs_n(rn),.j_cmd(jc),.j_dn(db),.q(q),.core_q(qb),.ad(ad));
integer checks=0,errors=0,done=0,passed=0,clean_done=0,k,j,seed=SEED;reg[511:0] word;
always @(posedge ck) begin
 if(rn&&qa[0])passed=passed+1;
 #0.1;
 if(rn)begin
 checks=checks+1;
 if({da,qa}!={db,qb})begin errors=errors+1;if(errors<4)$display("MISMATCH cycle%0d dn%h/%h",checks,da,db);end
 if(da[0])done=done+1;

 end
end
task tick; begin @(negedge ck);end endtask
task reset;begin rn=0;jc=0;q=0;ad=0;repeat(4)tick;rn=1;repeat(3)tick;end endtask
initial begin
 reset;
 // Native absent-channel endpoint: one query and a0 END for every job.
 for(k=0;k<64;k=k+1)begin
  if(k%8==0)reset;
  jc={1'b1,24'd129,8'(k)};tick;jc=0;repeat(3)tick;
  word=0;word[502:495]=8'(k);q={2'b00,word,1'b1};tick;q=0;repeat(3)tick;
  word=0;word[507]=1;word[502:495]=8'(k);word[505:503]=0;ad={word,1'b1};tick;ad=0;repeat(6)tick;
  if(da[1])begin errors=errors+1;$display("UNEXPECTED_FAULT job%0d",k);end
 end
 clean_done=done;
 // An unarmed query must be dropped. The missing-job mutant forwards it.
 reset;word=0;word[502:495]=8'h91;q={2'b00,word,1'b1};tick;q=0;repeat(4)tick;
 // Arbitrary malformed frames compare fault handling as well as retained output payload.
 for(j=0;j<16;j=j+1)begin
  reset;
  for(k=0;k<64;k=k+1)begin
   jc={$random(seed),$random(seed)};q={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
   ad=q[512:0];tick;
  end
 end
 if(errors==0&&clean_done==64&&passed>=64)$display("SVC_JOB_A0 PASS checks%0d done%0d passed%0d",checks,done,passed);
 else $display("SVC_JOB_A0 FAIL checks%0d errors%0d done%0d passed%0d",checks,errors,done,passed);
 $finish;
end
endmodule
