
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,reserve_v=0,step_v=0,l2_ready=0,commit_v=0;
reg [2:0] rslot=0,sslot=0;reg [35:0] rrows=0;
reg [31:0] scales=0;reg [15:0] repoch=41;
reg [1023:0] w=0,x=0;reg [3:0] cid=0;reg [17:0] crow=0;reg [15:0] cep=0;
wire [2:0] phase;wire rready,sready,lv,fault;wire [3:0] lid;
wire [17:0] lrow;wire [15:0] lep;wire [31:0] ld;wire [4:0] credits;
ot_gpu_qwen_gu64_l2 #(.ENABLE_GU64_L2(1)) d(.clk(clk),.rst_n(rst_n),
.issue_phase(phase),.reserve_v(reserve_v),.reserve_ready(rready),.reserve_slot(rslot),
.reserve_rows(rrows),.reserve_scales_bf16(scales),.reserve_epoch(repoch),
.step_v(step_v),.step_ready(sready),.step_slot(sslot),.weights_i8(w),.x_bf16(x),
.l2_v(lv),.l2_ready(l2_ready),.l2_id(lid),.l2_row(lrow),.l2_epoch(lep),.l2_data(ld),
.commit_v(commit_v),.commit_id(cid),.commit_row(crow),.commit_epoch(cep),
.free_row_credits(credits),.fault(fault));
reg [1023:0] wm[0:1023],xm[0:1023];reg [15:0] sm[0:31];
reg [3:0] qid[0:15];reg [17:0] qrow[0:15];reg [15:0] qep[0:15];reg [31:0] qdata[0:15];
reg [31:0] actual_l2[0:31];integer counts[0:7];
integer wave,i,j,ix,cycle=0,steps,accepted,committed,age,bubbles,stalls,waits;
reg positive=1,held=0;reg [69:0] held_packet;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
always @(posedge clk) begin
cycle=cycle+1;
if(rst_n && positive) begin
 if(lv && l2_ready) begin
  if(accepted>=16) $fatal(1,"too many L2 sends");
  qid[accepted]=lid;qrow[accepted]=lrow;qep[accepted]=lep;qdata[accepted]=ld;
  accepted=accepted+1;
 end
 if(commit_v) begin
  // These are real writes of the accepted RTL-scaled packet, not fixtures.
  ix=(cep==41) ? crow-250 : crow-506+16;
  if(ix<0 || ix>=32) $fatal(1,"bad actual L2 address");
  actual_l2[ix]=qdata[15-committed];
  $display("COMMITTED %d %d %h %d",crow,cep,actual_l2[ix],cycle);
  committed=committed+1;
 end
end
#1;if(rst_n && positive && fault) $fatal(1,"phase/credit/scale fault");
end
initial begin
$readmemh("weights.hex",wm);$readmemh("x.hex",xm);$readmemh("scales.hex",sm);
repeat(4) tick;rst_n=1;
for(wave=0;wave<2;wave=wave+1) begin
 steps=0;accepted=0;committed=0;age=0;bubbles=0;stalls=0;waits=0;held=0;
 repoch=41+wave;
 for(i=0;i<8;i=i+1) begin
  counts[i]=0;rslot=i;rrows[17:0]=(wave==0?250:506)+2*i;
  rrows[35:18]=(wave==0?251:507)+2*i;
  scales={sm[wave*16+2*i+1],sm[wave*16+2*i]};
  reserve_v=1;if(!rready) begin #1;if(!rready) $fatal(1,"reservation missing");end
  tick;reserve_v=0;
 end
 if(credits!=0) $fatal(1,"credits not reserved before first");
 while(committed<16) begin
  step_v=0;commit_v=0;sslot=phase;
  if(counts[phase]<64) begin
   // A missing memory return creates a real clock bubble, not tag advancement.
   if(cycle%11==3 || cycle%37<8) bubbles=bubbles+1;
   else begin
    j=wave*512+counts[phase]*8+phase;w=wm[j];x=xm[j];
    step_v=1;#1;if(!sready) $fatal(1,"phase issue not ready");
    counts[phase]=counts[phase]+1;steps=steps+1;
   end
  end
  if(steps==512) age=age+1;
  // Fill all16 result entries before releasing this output backpressure.
  l2_ready=(age>100 && cycle%13>=3);
  if(lv && !l2_ready) begin
   if(held && held_packet!={lid,lrow,lep,ld}) $fatal(1,"unstable stalled result");
   held=1;held_packet={lid,lrow,lep,ld};stalls=stalls+1;
  end else held=0;
  if(accepted==16 && committed==0 && credits!=0) $fatal(1,"send released credit before commit");
  // Finite actual L2 write pipeline: delay, reorder and backpressure writes.
  if(accepted==16 && age>130 && cycle%7>=2) begin
   cid=qid[15-committed];crow=qrow[15-committed];cep=qep[15-committed];commit_v=1;
  end else if(accepted>committed) waits=waits+1;
  tick;
 end
 step_v=0;commit_v=0;l2_ready=0;tick;
 if(credits!=16) $fatal(1,"credits did not follow both actual commits");
 $display("STATS epoch=%d steps=%d memory_bubbles=%d result_stalls=%d commit_wait_cycles=%d final_cycle=%d",repoch,steps,bubbles,stalls,waits,cycle);
end
repeat(160) tick;if(fault) $fatal(1,"late fault");
positive=0;
// A caller cannot issue before it owns both result credits.
rst_n=0;repeat(3) tick;rst_n=1;sslot=phase;step_v=1;tick;step_v=0;
if(!fault) $fatal(1,"missing reservation accepted");
rst_n=0;repeat(3) tick;rst_n=1;reserve_v=1;rslot=0;rrows={18'd901,18'd900};tick;reserve_v=0;
sslot=phase^1;step_v=1;tick;step_v=0;
if(!fault) $fatal(1,"wrong actual clock phase accepted");
rst_n=0;repeat(3) tick;rst_n=1;reserve_v=1;tick;reserve_v=0;
commit_v=1;cid=0;crow=900;cep=repoch+1;tick;commit_v=0;
if(!fault) $fatal(1,"stale/premature L2 commit accepted");
$display("COMPLETE GU64_L2 rows=32 epochs=2 trailing=160 negatives=3");$finish;
end
initial begin #60000;$fatal(1,"TIMEOUT");end
endmodule
