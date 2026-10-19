module tb_powerup;
 reg clk=0,rst_n=1;reg [15:0] a=16'hcafe,b=16'h5392;wire[15:0]y;
 ot_pg_canonical_xor16_1019 d(clk,rst_n,a,b,y);
 always #5 clk=~clk;
 integer k,checks=0;
 initial begin
   for(k=0;k<8;k=k+1) begin
     @(negedge clk);d.reset_first=k[0];d.reset_a=k[1];d.reset_b=k[2];
     d.a_q=16'hxxxx;d.b_q=16'hxxxx;d.y=16'hxxxx;
     #1 rst_n=0;
     // A real reset clock erases arbitrary data even if copy was already low.
     @(posedge clk);#1;
     if(y!==16'b0 || d.a_q!==16'b0 || d.b_q!==16'b0)
       $fatal(1,"POWERUP_ERASURE_FAILURE case=%0d",k);
     checks=checks+1;
     @(negedge clk);#1 rst_n=1;
     @(posedge clk);#1;if(d.reset_a!==0 || d.reset_b!==0 || y!==0)$fatal(1,"EARLY_RELEASE1");
     @(posedge clk);#1;if(d.reset_a!==1 || d.reset_b!==1 || y!==0)$fatal(1,"RELEASE2");
     @(posedge clk);#1;if(d.a_q!==a || d.b_q!==b || y!==0)$fatal(1,"CAPTURE3");
     @(posedge clk);#1;if(y!==(a^b))$fatal(1,"OUTPUT4");
     // Async assertion during operation clears output without a clock edge.
     #1 rst_n=0;#1;if(y!==0)$fatal(1,"RUNNING_ASYNC_ASSERT");
     #1 rst_n=1;repeat(5)@(posedge clk);
   end
   $display("POWERUP_PASS checks=%0d arbitrary51bits=X reset_cases=8 qualified_first_use_edge=3",checks);$finish;
 end
endmodule
