`timescale 1ns/1ps
module tb_join_fan32;
reg ck=0;always #1 ck=~ck;reg rst_n=0,slot=0,v=0,half=0,scale=0;
reg[255:0] data=0;reg[17:0]token=0;reg[5:0]idx=0;reg[15:0]epoch=0;
wire[554:0]a,b;reg[554:0]delay_a;always @(posedge ck)delay_a<=a;
qkd_embedding_static_join u_a(.ck(ck),.rst_n(rst_n),.beat_slot(slot),.beat_v(v),.beat_data(data),.beat_token(token),.beat_word(idx),.beat_half(half),.beat_scale(scale),.beat_epoch(epoch),.word_v(a[554]),.word_data(a[553:42]),.word_token(a[41:24]),.word_index(a[23:18]),.word_scale(a[17]),.word_epoch(a[16:1]),.fault(a[0]));
qkd_embedding_static_join_fan32 u_b(.ck(ck),.rst_n(rst_n),.beat_slot(slot),.beat_v(v),.beat_data(data),.beat_token(token),.beat_word(idx),.beat_half(half),.beat_scale(scale),.beat_epoch(epoch),.word_v(b[554]),.word_data(b[553:42]),.word_token(b[41:24]),.word_index(b[23:18]),.word_scale(b[17]),.word_epoch(b[16:1]),.fault(b[0]));
integer checks=0;integer errors=0;integer i,j;integer warm=0;
initial begin
 repeat(4)@(negedge ck);rst_n=1;
 for(i=0;i<16000;i=i+1)begin
  @(negedge ck);
  if(warm>8)begin checks=checks+1;if(delay_a!==b)begin errors=errors+1;if(errors<4)$display("DIFF i=%0d a=%h b=%h",i,delay_a,b);end end
  if(!rst_n)warm=0;else warm=warm+1;
  for(j=0;j<256;j=j+1)data[j]=$random;
  slot=(i%3!=2);v=slot;half=(i%3==1);scale=(i%61==60);token=18'(i/3);idx=6'(i/3);epoch=16'(i/192);
  if(i>12000)begin slot=$random;v=$random;half=$random;scale=$random;token=$random;end
  rst_n=!(i==8000||i==8001||i==8002||i==8003);
 end
 if(errors)$fatal(1,"FAIL JOIN_FAN32 checks=%0d errors=%0d",checks,errors);
 $display("PASS JOIN_FAN32 delay=1 checks=%0d errors=%0d",checks,errors);$finish;
end
endmodule
