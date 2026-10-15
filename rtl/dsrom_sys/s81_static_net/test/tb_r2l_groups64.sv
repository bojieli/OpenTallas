`timescale 1ns/1ps
module tb_r2l_groups64 #(parameter integer PHASE=0,MUT=0);
 reg wc=0,rc=0,rst=0;reg [513:0] di=0;wire [514:0] actual,expected;
 integer n=0,checks=0,errors=0,epoch=0;reg enabled=0;
 always #0.416667 wc=~wc;
 initial begin #(PHASE*0.027777);forever #0.555556 rc=~rc;end
 dsfd_r2l_groups64 #(.MUT(MUT)) dut(.ck({9{rc}}),.fi({8{wc}}),.rs(rst),.di0(di),.o(actual));
 dsfd_r2l_vr_512x1__hcol flat(.ck(rc),.fi0(wc),.rs(rst),.di0(di),.o(expected));
 reg [31:0] rng=32'h71514921;reg [511:0] payload;integer k;
 always @(posedge wc)begin
  if(enabled)begin
   for(k=0;k<16;k=k+1)begin rng=(rng>>1)^((rng[0])?32'h80200003:0);payload[32*k+:32]=rng;end
   di<={payload,(n%4!=3),1'b1};n<=n+1;
  end else begin di<=0;n<=0;end
 end
 always @(negedge rc)if(enabled && expected[513])begin
  checks=checks+1;
  if(actual!==expected)begin errors=errors+1;if(errors<3)$display("MISMATCH phase%0d epoch%0d got%h expected%h",PHASE,epoch,actual,expected);end
 end
 initial begin
  for(epoch=0;epoch<4;epoch=epoch+1)begin
   enabled=0;rst=0;repeat(8+epoch)@(negedge rc);rst=1;
   repeat(8)@(negedge rc);enabled=1;repeat(1000)@(negedge rc);
   enabled=0;repeat(12)@(negedge rc);
  end
  if(errors || checks<3900)$fatal(1,"R2L_GROUPS_FAIL checks=%0d errors=%0d",checks,errors);
  $display("R2L_GROUPS_PASS checks=%0d epochs=4 phase=%0d zero_added_edges=1",checks,PHASE);$finish;
 end
endmodule
