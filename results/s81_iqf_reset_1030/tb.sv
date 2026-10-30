`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg arst_n=0;reg [15:0] payload=16'h1597;reg valid=0;
wire t5,t12,t13,t14,short14;actual_iqf_reset rt(clk,arst_n,t5,t12,t13,t14,short14);
wire [15:0] a,b,c;wire av,bv,cv;
ot_dp_st #(.W(16)) oldc(clk,t5,payload,valid,a,av);
ot_dp_st #(.W(16)) localc(clk,t14,payload,valid,b,bv);
ot_dp_st #(.W(16)) mutant(clk,short14,payload,valid,c,cv);
integer cyc,checks=0,mut=0,errs=0;
initial begin
 for(cyc=0;cyc<12000;cyc=cyc+1)begin
  @(negedge clk);
  if(cyc>=64)begin
   checks=checks+1;
   if((t5!==t12)||(t5!==t13)||(t5!==t14)||(a!==b)||(av!==bv))begin errs=errs+1;$display("MISMATCH cycle=%0d resets=%b%b%b%b flags=%b%b",cyc,t5,t12,t13,t14,av,bv);end
   if(av!==cv)mut=mut+1;
  end
  #37;
  payload={payload[14:0],payload[15]^payload[13]^payload[12]^payload[10]};valid=payload[2];
  if(cyc<64)arst_n=0;
  else if(cyc%193<64)arst_n=0;
  else if(cyc%211==100)arst_n=1'bx;
  else arst_n=1;
 end
 $display("IQF_RESET checks=%0d errors=%0d mutant_caught=%0d cycles_added=0",checks,errs,mut);
 if(errs!=0||mut==0)$fatal(1,"FAIL");$finish;
end
endmodule
