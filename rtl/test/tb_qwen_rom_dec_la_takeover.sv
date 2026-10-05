`timescale 1ns/1ps
module tb #(parameter VPOS=1, POSITION=8187, BOUNDED=0, CHASEQ=0, COUNTLA=0);
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start=0;
reg [17:0] token=3,pos=POSITION;
reg [1023:0] mem[0:64];
reg [1023:0] q0=0,q1=0;
wire re0,re1,done0,done1,accept0,accept1,bad0,bad1;
wire [11:0] addr0,addr1;
wire [877:0] dec0,dec1;
wire [17:0] next0,next1;
wire [31:0] val0,val1,cycles0,cycles1;
reg [17:0] am_idx=0;
reg [31:0] am_val=0;
reg am_any=0;
integer am_events=0;
// A producer result is stable until the next ME issue. Include equal keys,
// negative values and signed zeros; comparison remains the original okey.
always @(negedge clk) if(rst_n && accept0 && a.me_go) begin
 am_idx<=cycle%17;
 case(am_events%6)
  0:am_val<=32'hbf800000;
  1:am_val<=32'h00000000;
  2:am_val<=32'h80000000;
  3:am_val<=32'h3f800000;
  4:am_val<=32'h3f800000;
  5:am_val<=32'h40000000;
 endcase
 am_any<=am_events%5!=0;
 am_events<=am_events+1;
end
reg [877:0] events0[0:63],events1[0:63];
integer cycle=0,n0=0,n1=0,invalid0=0,invalid1=0,i,v;
wire ready=cycle%7!=0;
wire idle=cycle%11!=0;
wire [15:0] progress=cycle%32;
`include "ot_hdc_isa.svh"
decode_component #(.DEC_LA(0),.VPOS(VPOS)) a(.clk(clk),.rst_n(rst_n),.start(start),.token(token),.pos(pos),.me_ready(ready),.me_idle(idle),.su_ready(ready),.su_idle(idle),.me_progress(progress),.su_progress(progress),.su_rows(progress),.am_idx(am_idx),.am_val(am_val),.am_any(am_any),.next_token(next0),.next_val(val0),.cycles(cycles0),.prog_q(q0),.prog_re(re0),.prog_addr(addr0),.done(done0),.decoded(dec0),.accepted(accept0),.invalid_at_load(bad0));
decode_component #(.DEC_LA(1),.VPOS(VPOS),.DEC_LA_BOUND(BOUNDED),.DEC_LA_CHASE_Q(CHASEQ),.DEC_LA_COUNT_LA(COUNTLA)) b(.clk(clk),.rst_n(rst_n),.start(start),.token(token),.pos(pos),.me_ready(ready),.me_idle(idle),.su_ready(ready),.su_idle(idle),.me_progress(progress),.su_progress(progress),.su_rows(progress),.am_idx(am_idx),.am_val(am_val),.am_any(am_any),.next_token(next1),.next_val(val1),.cycles(cycles1),.prog_q(q1),.prog_re(re1),.prog_addr(addr1),.done(done1),.decoded(dec1),.accepted(accept1),.invalid_at_load(bad1));
always @(posedge clk) begin
 cycle<=cycle+1;
 if(re0) q0<=mem[addr0%65];
 if(re1) q1<=mem[addr1%65];
 if(!rst_n) begin n0=0;n1=0;invalid0=0;invalid1=0;end
 else begin
  if(COUNTLA != 0 && cycles0 !== cycles1) $fatal(1,"cycle counter mismatch edge=%d %h/%h",cycle,cycles0,cycles1);
  if(accept0 !== accept1 || re0 !== re1 || (re0 && addr0 !== addr1) || bad0 !== bad1 || done0 !== done1)
    $fatal(1,"cycle-visible instruction protocol mismatch cycle=%0d",cycle);
  if(accept0 && dec0 !== dec1) $fatal(1,"same-edge decoded878 mismatch cycle=%0d",cycle);
  if(accept0) begin events0[n0]=dec0;n0=n0+1;end
  if(accept1) begin events1[n1]=dec1;n1=n1+1;end
  if(bad0) invalid0=invalid0+1;
  if(bad1) invalid1=invalid1+1;
 end
end
generate if(BOUNDED != 0) begin : g_check_bound
 initial if(b.LA_LO_W != 9) $fatal(1,"bounded-state parameter not selected");
end endgenerate
generate if(CHASEQ != 0) begin : g_check_chaseq
 always @(posedge clk) if(rst_n && b.nx_v && b.d_chase_n !== b.la_chase_q)
  $fatal(1,"registered NEXT chase count not selected");
end endgenerate
generate if(COUNTLA != 0) begin : g_check_counter
 task coherent_seed(input [31:0] seed);
  begin
   @(negedge clk);
   a.cycles=seed;b.cycles=seed;
   b.la_cycle_carry={(&seed[23:0]),(&seed[15:0]),(&seed[7:0])};
   repeat(4) @(negedge clk);
  end
 endtask
 initial begin
  wait(cycle>=40 && rst_n && a.st==a.S_RUN && b.st==b.S_RUN);
  coherent_seed(32'h000000fe);
  coherent_seed(32'h0000fffe);
  coherent_seed(32'h00fffffe);
  coherent_seed(32'hfffffffe);
  $display("PASS counter lookahead full32bit carry8/16/24/wrap coherent-state probes");
 end
 always @(negedge clk) if(rst_n && b.la_cycle_carry !== {(&b.cycles[23:0]),(&b.cycles[15:0]),(&b.cycles[7:0])})
  $fatal(1,"counter carry-cache invariant mismatch count=%h flags=%b",b.cycles,b.la_cycle_carry);
end endgenerate
initial begin
 for(i=0;i<64;i=i+1) begin
  for(v=0;v<32;v=v+1) mem[i][v*32+:32]=$random;
  mem[i][O_UNIT+:W_UNIT]=(i%2)+1;
  mem[i][O_BARRIER]=i%5==0;
  mem[i][O_CHASE]=i%3==0;mem[i][O_CHASE_N+:W_CHASE_N]=(i%3==0) ? i%8 : (16'hffff-i);mem[i][O_CHASE_ROWS]=i%2;mem[i][O_WAIT_ME]=0;mem[i][O_WAIT_SU]=0;
  mem[i][O_ME_SPLIT+:W_ME_SPLIT]=i%16;
  mem[i][O_ME_AMAX]=1;
  mem[i][O_ME_AMC]=i!=0;
  mem[i][O_ME_ROW0+:W_ME_ROW0]=i*17;
  mem[i][O_ME_D_TILES+:W_ME_D_TILES]=6;
  mem[i][900+:3]=i%8;
 end
 mem[64]=0;
 repeat(3) @(negedge clk);rst_n=1;start=1;
 @(negedge clk);start=0;
 repeat(20) @(negedge clk);rst_n=0;
 repeat(3) @(negedge clk);rst_n=1;start=1;
 @(negedge clk);start=0;
 wait(done0);wait(done1);@(negedge clk);
 if(n0!=64 || n1!=64 || invalid0!=16 || invalid1!=16) $fatal(1,"counts %d %d invalid %d %d",n0,n1,invalid0,invalid1);
 if(next0!==next1 || val0!==val1 || cycles0!==cycles1)
  $fatal(1,"actual chunked argmax END mismatch token=%h/%h val=%h/%h cycles=%d/%d",next0,next1,val0,val1,cycles0,cycles1);
 if(am_events<8 || a.run_any!==1'b1) $fatal(1,"argmax accumulation not exercised events=%d",am_events);
 for(i=0;i<64;i=i+1) if(events0[i]!==events1[i]) $fatal(1,"decoded event mismatch %d",i);
 $display("PASS DEC_LA actual chunked argmax/END equal token/value/cycles, zero-edge ordered64 full decoded fields; VPOS offsets8/splits16/stalls/barriers/END; invalid16");$finish;
end
initial begin repeat(2000) @(posedge clk);$fatal(1,"component liveness failure");end
endmodule
