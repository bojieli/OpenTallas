`timescale 1ns/1ps
module tb_vm_service_slice;
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,w_v=0,w_bank=0;reg[6:0]w_addr=0;reg[255:0]w_data=0;
 reg[1:0]r_v=0;reg[13:0]r_addr=0;wire[1:0]rv;wire[511:0]rd;
 vm_service_slice #(.NM(1)) dut(.*);
 reg[255:0] golden[0:1][0:127];reg[1:0]ev[0:2];reg[511:0]ed[0:2];
 integer errors=0,reads=0,writes=0,cycles=0;
 function automatic[255:0] pattern(input integer bank,row,version);
  for(integer j=0;j<8;j=j+1)pattern[j*32+:32]=32'h91a3405b^(bank<<23)^(row<<8)^(version<<1)^j;
 endfunction
 task automatic step;
  begin
   @(posedge clk);
   if(rst_n)begin
    for(integer b=0;b<2;b=b+1)begin
     if(r_v[b]&&w_v&&w_bank==b&&r_addr[b*7+:7]==w_addr)$fatal(1,"fixture read/write collision");
     if(r_v[b])begin ed[0][b*256+:256]=golden[b][r_addr[b*7+:7]];reads=reads+1;end
    end
    ev[0]=r_v;
    if(w_v)begin golden[w_bank][w_addr]=w_data;writes=writes+1;end
   end else ev[0]=0;
   #0.1;
   if(rv!==ev[2])begin errors=errors+1;$display("valid cycle%0d got%0b expected%0b",cycles,rv,ev[2]);end
   for(integer b=0;b<2;b=b+1)if(ev[2][b]&&rd[b*256+:256]!==ed[2][b*256+:256])begin
    errors=errors+1;if(errors<6)$display("data cycle%0d bank%0d",cycles,b);
   end
   ed[2]=ed[1];ed[1]=ed[0];ev[2]=ev[1];ev[1]=ev[0];cycles=cycles+1;
   @(negedge clk);
  end
 endtask
 initial begin
  for(integer k=0;k<3;k=k+1)begin ev[k]=0;ed[k]=0;end
  step();step();rst_n=1;
  // Write every physical row first; no dependence on macro zero initialisation.
  for(integer n=0;n<256;n=n+1)begin w_v=1;w_bank=n%2;w_addr=n/2;w_data=pattern(n%2,n/2,0);step();end
  w_v=0;step();step();
  // Full simultaneous 2R+1W for 2048 cycles, with repeated row wrapping.
  for(integer n=0;n<2048;n=n+1)begin
   w_v=1;w_bank=n%2;w_addr=7'(n/2);w_data=pattern(n%2,(n/2)%128,n+1);
   r_v=3;r_addr={7'((n/2+17)%128),7'((n/2+23)%128)};step();
  end
  w_v=0;r_v=0;repeat(4)step();
  $display("SERVICE_SLICE reads=%0d writes=%0d cycles=%0d errors=%0d",reads,writes,cycles,errors);
  if(errors)$fatal(1,"SERVICE_SLICE FAIL");$finish;
 end
endmodule
