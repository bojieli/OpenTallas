`timescale 1ns/1ps
module tb_cal_native32;
reg ck=0;always #1 ck=~ck;
reg rst_n=0,start=0,cfg_we=0;reg[7:0]cfg_addr=0;reg[63:0]cfg_data=0;
reg[298:0] up0=0,up1=0,up2=0,up3=0;
wire [554:0] a,b;
qkd_embedding_static_join4_cal #(.NATIVE32(0)) u_a(.ck(ck),.rst_n(rst_n),.start(start),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.up0(up0),.up1(up1),.up2(up2),.up3(up3),.word_v(a[554]),.word_data(a[553:42]),.word_token(a[41:24]),.word_index(a[23:18]),.word_scale(a[17]),.word_epoch(a[16:1]),.fault(a[0]));
qkd_embedding_static_join4_cal #(.NATIVE32(1)) u_b(.ck(ck),.rst_n(rst_n),.start(start),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.up0(up0),.up1(up1),.up2(up2),.up3(up3),.word_v(b[554]),.word_data(b[553:42]),.word_token(b[41:24]),.word_index(b[23:18]),.word_scale(b[17]),.word_epoch(b[16:1]),.fault(b[0]));
integer checks=0;integer errors=0;integer i,j;
initial begin
 repeat(4)@(negedge ck);rst_n=1;
 for(i=0;i<10000;i=i+1)begin
  @(negedge ck);
  if(i>8)begin checks=checks+1;if(a!==b)begin errors=errors+1;if(errors<5)$display("DIFF cycle=%0d a=%h b=%h",i,a,b);end end
  start=(i%512==40);cfg_we=(i%512<16 && i%2==0);cfg_addr=(i%16)/2;
  cfg_data={2'd1,38'd0,8'd4,16'(50+(i%16)*8)};
  for(j=0;j<299;j=j+1)begin up0[j]=$random;up1[j]=$random;up2[j]=$random;up3[j]=$random;end
  if(i%11!=0)begin up0[0]=0;up1[0]=0;up2[0]=0;up3[0]=0;end
  rst_n=!(i==5000||i==5001||i==5002||i==5003);
 end
 if(errors)$fatal(1,"FAIL CAL_NATIVE32 checks=%0d errors=%0d",checks,errors);
 $display("PASS CAL_NATIVE32 checks=%0d errors=%0d",checks,errors);$finish;
end
endmodule
