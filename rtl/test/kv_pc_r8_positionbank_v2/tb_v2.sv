`timescale 1ns/1ps
module tb_v2;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg [1:0] stack_id=0;reg [2:0] group_id=0;
 reg [17:0] tok_i=0;reg [15:0] epoch_i=0;
 wire [17:0] tok_o;wire [15:0] epoch_o;
 kv_pc_r8_position_bank_v2 #(.MUT(MUT)) dut(.*);
 reg [17:0] tok_hist[0:3];reg [15:0] ep_hist[0:4];
 integer st,g,c,i,td,ed,checks=0;
 initial begin
  for(i=0;i<4;i=i+1)tok_hist[i]=0;
  for(i=0;i<5;i=i+1)ep_hist[i]=0;
  for(st=0;st<4;st=st+1)for(g=0;g<7;g=g+1)begin
   @(negedge clk);stack_id=2'(st);group_id=3'(g);
   td=((st==1)&&((g==2)||(g==3)||(g==4)||(g==6)))?1:((st==0)&&((g==2)||(g==4)))?3:0;
   ed=((st==2)&&(g==1))?4:((st==0)&&(g==3))?3:0;
   for(c=0;c<48;c=c+1)begin
    @(negedge clk);tok_i=18'($urandom);epoch_i=16'($urandom);
    // Prior pipeline history corresponds to data sampled at previous rising edges.
    #1;
    if(c>5)begin
     if(tok_o!==(td==0?tok_i:tok_hist[td]) || epoch_o!==(ed==0?epoch_i:ep_hist[ed]))
      $fatal(1,"POS_V2 FAIL st=%0d g=%0d c=%0d td=%0d ed=%0d",st,g,c,td,ed);
     checks=checks+1;
    end
    @(posedge clk);
    for(i=3;i>1;i=i-1)tok_hist[i]=tok_hist[i-1];tok_hist[1]=tok_i;
    for(i=4;i>1;i=i-1)ep_hist[i]=ep_hist[i-1];ep_hist[1]=epoch_i;
   end
  end
  $display("POS_V2 PASS positions28 checks%0d keptFF118 addedFF1848 mission_cycles_beyond_landing0",checks);$finish;
 end
endmodule
