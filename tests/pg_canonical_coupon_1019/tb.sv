module tb;
 reg clk=0,rst_n=1; reg [15:0] a=0,b=0; wire [15:0] y;
 ot_pg_canonical_xor16_1019 d(clk,rst_n,a,b,y);
 always #5 clk=~clk;
 reg r0=0,r1=0; reg [15:0] qa=0,qb=0,qy=0; integer checks=0,resets=0;
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin r0<=0;r1<=0;qa<=0;qb<=0;qy<=0; end
   else begin r0<=1;r1<=r0; if(!r1) begin qa<=0;qb<=0;qy<=0;end
        else begin qa<=a;qb<=b;qy<=qa^qb;end end
 end
 always @(negedge clk) begin
   if(y!==qy) $fatal(1,"MISMATCH checks=%0d y=%h expected=%h",checks,y,qy);
   checks=checks+1;
   a=$random; b=$random;
 end
 integer k,j;
 initial begin
   // Explicit arbitrary extra-copy startup. No observation before real reset.
   for(k=0;k<8;k=k+1) begin
     @(negedge clk); d.reset_first=k[0];d.u_reset_a.q=k[1];d.u_reset_b.q=k[2];
     #1 rst_n=0; resets=resets+1; #1;
     if(d.reset_first!==0 || d.reset_a!==0 || d.reset_b!==0 || y!==0)
       $fatal(1,"ASYNC_RESET_FAILURE");
     #11 rst_n=1;
     repeat(20) @(negedge clk);
   end
   for(j=0;j<2048;j=j+1) @(negedge clk);
   $display("PASS checks=%0d resets=%0d lanes=16 II=1 latency=2",checks,resets); $finish;
 end
endmodule
