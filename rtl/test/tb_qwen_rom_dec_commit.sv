`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,start=0;reg [1023:0] mem[0:127];
reg [1023:0] q[0:1];
wire [1:0] re,done,accept,bad;
wire [11:0] addr[0:1];wire [877:0] dec[0:1];
wire [17:0] nt[0:1];wire [31:0] nv[0:1],cyc[0:1];
integer mode=0,wall=0,i,j,n[0:1],mbusy[0:1],sbusy[0:1],mcount[0:1],scount[0:1];
reg [17:0] ai[0:1];reg [31:0] av[0:1];reg aa[0:1];
reg [877:0] evt[0:1][0:127];
reg [877:0] held;
integer targets=0,reserves=0,blocked=0,pending_age=0,reset_seen=0;
`include "ot_hdc_isa.svh"
wire mr0=mbusy[0]==0,sr0=sbusy[0]==0;
wire mr1=mbusy[1]==0,sr1=sbusy[1]==0;
// ME clock enable and memory service may withdraw after reservation.
wire gate1=!(mode==1 && b.am_issue_pending && pending_age<2);
decode_component #(.DEC_LA(0)) a(.clk(clk),.rst_n(rst_n),.start(start),.token(24),.pos(8191),
 .me_ready(mr0),.me_idle(mr0),.su_ready(sr0),.su_idle(sr0),.me_en(1'b1),.kv_ok(1'b1),.w_ok(1'b1),.emb_ok(1'b1),.kv_write_drained(1'b1),
 .me_progress(mr0?16'd1024:16'd0),.su_progress(sr0?16'd1024:16'd0),.su_rows(sr0?16'd1024:16'd0),
 .am_idx(ai[0]),.am_val(av[0]),.am_any(aa[0]),.prog_q(q[0]),.prog_re(re[0]),.prog_addr(addr[0]),.done(done[0]),.next_token(nt[0]),.next_val(nv[0]),.cycles(cyc[0]),.decoded(dec[0]),.accepted(accept[0]),.invalid_at_load(bad[0]));
decode_component #(.DEC_LA(1),.DEC_LA_BOUND(1),.DEC_LA_CHASE_Q(1),.DEC_LA_COUNT_LA(1),.DEC_LA_AM_COMMIT(1)) b(.clk(clk),.rst_n(rst_n),.start(start),.token(24),.pos(8191),
 .me_ready(mr1),.me_idle(mr1),.su_ready(sr1),.su_idle(sr1),.me_en(gate1),.kv_ok(gate1),.w_ok(gate1),.emb_ok(1'b1),.kv_write_drained(1'b1),
 .me_progress(mr1?16'd1024:16'd0),.su_progress(sr1?16'd1024:16'd0),.su_rows(sr1?16'd1024:16'd0),
 .am_idx(ai[1]),.am_val(av[1]),.am_any(aa[1]),.prog_q(q[1]),.prog_re(re[1]),.prog_addr(addr[1]),.done(done[1]),.next_token(nt[1]),.next_val(nv[1]),.cycles(cyc[1]),.decoded(dec[1]),.accepted(accept[1]),.invalid_at_load(bad[1]));
always @(posedge clk) begin
 wall=wall+1;
 for(j=0;j<2;j=j+1) begin
  if(re[j]) q[j]<=mem[addr[j]%128];
  if(!rst_n) begin n[j]=0;mbusy[j]=0;sbusy[j]=0;mcount[j]=0;scount[j]=0;ai[j]=0;av[j]=0;aa[j]=0;end
  else begin
   if(mbusy[j]>0) begin
    if(mbusy[j]==1) begin
     ai[j]<=mcount[j]%17;
     case(mcount[j]%6)
      0:av[j]<=32'hbf800000;1:av[j]<=32'h00000000;2:av[j]<=32'h80000000;
      3:av[j]<=32'h3f800000;4:av[j]<=32'h3f800000;5:av[j]<=32'h40000000;
     endcase
     aa[j]<=mcount[j]%5!=0;
    end
    mbusy[j]<=mbusy[j]-1;
   end
   if(sbusy[j]>0) sbusy[j]<=sbusy[j]-1;
   if(accept[j]) begin
    evt[j][n[j]]=dec[j];n[j]=n[j]+1;
    if(j==0 ? a.me_go : b.me_go) begin mbusy[j]<=6;mcount[j]<=mcount[j]+1;end
    else begin sbusy[j]<=4;scount[j]<=scount[j]+1;end
   end
  end
 end
 if(!rst_n) begin targets=0;reserves=0;blocked=0;pending_age<=0;end
 else begin
  if(b.am_reserve) begin reserves=reserves+1;held=dec[1];end
  if(b.am_issue_pending) begin
   if(dec[1]!==held || !b.nx_v || b.fin) $fatal(1,"held descriptor/END violation");
   if(b.am_commit && !b.am_issue_eligible) $fatal(1,"stale barrier/chase/wait qualification");
   if(!gate1) begin
    if(accept[1]) $fatal(1,"commit while live gate withdrew");
    blocked=blocked+1;
   end
   pending_age<=pending_age+1;
  end else pending_age<=0;
  if(b.am_commit) targets=targets+1;
 end
end
// Keep stimulus/status changes clear of the sampling edge.
task launch;
 begin @(negedge clk);rst_n=0;start=0;repeat(3) @(negedge clk);rst_n=1;start=1;@(negedge clk);start=0;end
endtask
task check_run(input integer expected);
 begin
  wait(done[0]);wait(done[1]);@(negedge clk);
  if(n[0]!=expected || n[1]!=expected) $fatal(1,"event counts %d/%d",n[0],n[1]);
  for(i=0;i<expected;i=i+1) if(evt[0][i]!==evt[1][i]) $fatal(1,"descriptor878 mismatch %d",i);
  if(nt[0]!==nt[1] || nv[0]!==nv[1]) $fatal(1,"argmax END differs %h/%h %h/%h",nt[0],nt[1],nv[0],nv[1]);
  if(reserves!=targets) $fatal(1,"reserve/commit count mismatch");
  if(cyc[1]-cyc[0] != targets+blocked) $fatal(1,"priced cycle mismatch %d/%d targets%0d blocked%0d",cyc[0],cyc[1],targets,blocked);
  $display("PASS mode=%0d events=%0d reserve/commit=%0d baseline_cycles=%0d candidate_cycles=%0d delta=%0d live_gate_wait=%0d token=%h value=%h",mode,expected,targets,cyc[0],cyc[1],cyc[1]-cyc[0],blocked,nt[1],nv[1]);
 end
endtask
initial begin
 for(i=0;i<128;i=i+1) mem[i]=0;
 $readmemh("selected_head_program.hex",mem,0,7);
 launch();check_run(7);
 mode=1;launch();check_run(7);
 // Abort a live reservation, then rerun actual selected head without stale commit.
 mode=2;launch();wait(b.am_issue_pending);@(negedge clk);rst_n=0;reset_seen=1;
 repeat(3) @(negedge clk);
 if(b.am_issue_pending || accept[1]) $fatal(1,"reset failed to cancel pending");
 launch();check_run(7);
 // Independent legal producers exercise mixed units, barrier/wait/chase,
 // non-target ME, signed zeros/ties and multiple chunk accumulations.
 for(i=0;i<48;i=i+1) begin
  mem[i]=0;mem[i][O_UNIT+:W_UNIT]=(i%3==0)?2:1;
  mem[i][O_BARRIER]=1;mem[i][O_CHASE]=i%2;mem[i][O_CHASE_N+:W_CHASE_N]=64;
  mem[i][O_WAIT_ME]=i%5==0;mem[i][O_WAIT_SU]=i%7==0;
  mem[i][O_ME_AMAX]=i%4!=0;mem[i][O_ME_AMC]=i!=1;
  mem[i][O_ME_ROW0+:W_ME_ROW0]=i*17;
  mem[i][O_ME_K+:W_ME_K]=17+i;mem[i][O_A_BASE+:W_A_BASE]=i*97;
 end
 mem[48]=0;mode=3;launch();check_run(48);
 $display("PASS registered issue/commit actual P8191 head + mixed descriptors/ready/chase/barrier/reset pending; reset_seen=%0d",reset_seen);$finish;
end
initial begin repeat(6000) @(posedge clk);$fatal(1,"functional component did not complete");end
endmodule
