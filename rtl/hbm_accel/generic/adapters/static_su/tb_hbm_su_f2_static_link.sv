`timescale 1ns/1ps
module tb_hbm_su_f2_static_link;
 parameter MUT_ROUTE=0,MUT_REUSE=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [543:0]rq=0;reg[8991:0]wq=0;
 wire[543:0]vrq;wire[8991:0]vwq;
 reg[8223:0]rr=0;wire[8223:0]sr;
 reg[3:0]load=0;reg[1023:0]operand=0;reg[31:0]replay=0;
 wire[3:0]fault;
 ot_hbm_su_f2_static_link #(.RD_LAT(3),.MUT_ROUTE(MUT_ROUTE),.MUT_REUSE(MUT_REUSE))d(
 .quarter_clk({4{clk}}),.rst_n(rst_n),.su_rq(rq),.su_wq(wq),.vm_rq(vrq),.vm_wq(vwq),.vm_rr(rr),.su_rr(sr),
 .operand_load(load),.operand_data(operand),.operand_replay(replay),.fault(fault));
 reg[8223:0]pipe[0:2];integer j,i,q,b,c,errors=0,checks=0;
 reg[543:0]exrq;reg[8991:0]exwq;reg[8223:0]exrr;
 function automatic[255:0]data(input integer x);integer k;begin for(k=0;k<8;k=k+1)data[k*32+:32]=32'(x*31+k);end endfunction
 function automatic[15:0]addr(input integer quadrant,input integer bank,input integer row);
 addr=(16'(quadrant)<<13)|(16'(row%1024)<<3)|16'(bank);
 endfunction
 always @(posedge clk)begin
  if(!rst_n)begin for(j=0;j<3;j=j+1)pipe[j]<=0;end
  else begin
   for(j=1;j<3;j=j+1)pipe[j]<=pipe[j-1];
   for(j=0;j<32;j=j+1)begin
    pipe[0][j*257+:257]<={vrq[j*17+16],data(vrq[j*17+:16])};
   end
  end
 end
 always @*rr=pipe[2];
 task check;begin #1;
  for(i=0;i<32;i=i+1)begin
   checks=checks+1;
   if(vrq[i*17+:17]!==exrq[i*17+:17])errors=errors+1;
   if(vwq[i*281+:281]!==exwq[i*281+:281])errors=errors+1;
   if(sr[i*257+256]!==exrr[i*257+256]||(exrr[i*257+256]&&sr[i*257+:256]!==exrr[i*257+:256]))errors=errors+1;
  end
 end endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  // Load four distinct broadcast sectors before full-rate replay.
  load=15;for(q=0;q<4;q=q+1)operand[q*256+:256]=data(10000+q);
  @(negedge clk);load=0;
  for(c=0;c<257;c=c+1)begin
   for(q=0;q<4;q=q+1)for(b=0;b<8;b=b+1)begin
    i=q*8+b;
    rq[i*17+:17]={1'(c%7!=0),addr(q,b,c)};
    if(c%11==0)rq[i*17+:16]=addr(0,b,c)|16'h8000;
    replay[i]=((c+b)%3==0);
    wq[i*281+:281]={1'(c%5!=0),addr(q,b,c+17),data(c*32+i),8'(1<<((c+b)%8))};
    exwq[i*281+:281]=wq[i*281+:281];
    if(replay[i]&&wq[i*281+280])exwq[i*281+8+:256]=data(10000+q);
   end
   exrq=rq;exrr=rr;
   @(posedge clk);check();@(negedge clk);
  end
  rq=0;wq=0;replay=0;exrq=0;exwq=0;
  repeat(8)begin exrr=rr;@(posedge clk);check();@(negedge clk);end
  if(fault!==0)errors=errors+1;
  // Deliberately missed response must be detected without stalling or replay.
  force rr=0;
  rq[16:0]={1'b1,addr(0,0,1)};
  @(negedge clk);rq=0;
  repeat(7)@(negedge clk);
  if(fault[0]!==1)errors=errors+1;
  release rr;
  // Fresh reset invalidates reuse, so a replay before load is an error.
  rst_n=0;repeat(2)@(negedge clk);rst_n=1;
  replay=1;wq[280:0]={1'b1,addr(0,0,1),256'd0,8'hff};
  @(negedge clk);if(fault[0]!==1)errors=errors+1;
  // Wrong native owner/bank must fault all four quarters on that edge.
  rst_n=0;wq=0;replay=0;repeat(2)@(negedge clk);rst_n=1;
  for(q=0;q<4;q=q+1)rq[(q*8)*17+:17]={1'b1,addr(q,1,8)};
  @(negedge clk);if(fault!==4'b1111)errors=errors+1;
  if(errors)$fatal(1,"F2_STATIC FAIL checks=%0d errors=%0d",checks,errors);
  $display("F2_STATIC PASS checks=%0d full_rate_edges=257 missed_response_detected invalid_reuse_detected",checks);$finish;
 end
endmodule
