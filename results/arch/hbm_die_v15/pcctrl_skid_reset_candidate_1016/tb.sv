module tb;
 parameter integer WIDTH=340,MUT=0;
 reg clk=0,rst_n=0,iv=0,ordy=0; reg[WIDTH-1:0]data=0;
 wire gr,gv,cr,cv;wire[WIDTH-1:0]gd,cd;
 golden_skid #(.WIDTH(WIDTH)) g(clk,rst_n,iv,gr,data,gv,ordy,gd);
 candidate_skid #(.WIDTH(WIDTH),.MUT(MUT)) c(clk,rst_n,iv,cr,data,cv,ordy,cd);
 always #5 clk=~clk;
 integer seed=32'h57a91f2a,i,j,transfers=0,stalls=0,resets=0;
 always @(negedge clk)begin
  if(rst_n)begin
   if(gr!==cr||gv!==cv) $fatal(1,"VALID_READY mismatch");
   if(gv && gd!==cd) $fatal(1,"VALID_PAYLOAD mismatch");
   if(gv&&ordy) transfers=transfers+1;
   if(gv&&!ordy) stalls=stalls+1;
  end
 end
 initial begin
  repeat(3) @(negedge clk);#1;rst_n=1;
  for(i=0;i<20000;i=i+1)begin
   @(negedge clk);#1;
   iv=($random(seed)&7)!=0;ordy=($random(seed)&7)>3;
   for(j=0;j<WIDTH;j=j+1)data[j]=$random(seed)&1;
   if(i%997==996)begin rst_n=0;resets=resets+1;end
   if(i%997==0)rst_n=1;
  end
  iv=0;ordy=1;repeat(4)@(negedge clk);
  if(transfers<1000||stalls<1000||resets<10)$fatal(1,"insufficient coverage");
  $display("SKID_SPLIT_CANDIDATE PASS WIDTH=%0d transfers=%0d stalled=%0d resets=%0d",WIDTH,transfers,stalls,resets);$finish;
 end
endmodule
