`timescale 1ns/1ps
`default_nettype none
module tb;
 reg clk=0; always #0.4165 clk=~clk;
 reg rst_n=0,ea=0,eb=1;reg[616:0]da=0;reg[569:0]db=0;
 reg[616:0]ra;reg[569:0]rb;reg rea,reb;
 always @(posedge clk)begin ra<=da;rb<=db;end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin rea<=0;reb<=0;end else begin rea<=ea;reb<=eb;end
 wire[1279:0] packed_d={93'd0,db,da};wire[1279:0]packed_q;
 hbm_payload_bank1024 b0(clk,packed_d[1023:0],packed_q[1023:0]);
 hbm_payload_bank256 b1(clk,packed_d[1279:1024],packed_q[1279:1024]);
 reg qa_epoch,qb_epoch;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin qa_epoch<=0;qb_epoch<=0;end else begin qa_epoch<=ea;qb_epoch<=eb;end
 integer mut=0,n=0,k=0,checks=0,errors=0; reg[31:0]lfsr=32'h983712ab;
 reg[1186:0]observed;
 initial begin
  if($value$plusargs("MUT=%d",mut))begin end
  for(n=0;n<360;n=n+1)begin
   @(negedge clk);
   for(k=0;k<617;k=k+1)begin lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};da[k]=lfsr[0];end
   for(k=0;k<570;k=k+1)begin lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};db[k]=lfsr[0];end
   ea=n%3!=0;eb=n%5!=0;rst_n=n%17!=0;
   @(posedge clk);#0.050;
   observed=packed_q[1186:0];
   if(mut==1)observed={observed[1185:0],observed[1186]};
   if(mut==2&&!rst_n)observed=0;
   checks=checks+3;
   if(observed!=={rb,ra})errors=errors+1;
   if(qa_epoch!==rea)errors=errors+1;
   if((mut==3?qb_epoch^1'b1:qb_epoch)!==reb)errors=errors+1;
  end
  $display("PAYLOAD_BANK MUT=%0d checks=%0d errors=%0d",mut,checks,errors);
  if(errors!=0)$fatal(1,"bank lockstep failed");$finish;
 end
endmodule
`default_nettype wire
