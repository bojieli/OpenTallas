`timescale 1ns/1ps
module tb_ctx_native32;
reg ck=0;always #1 ck=~ck;
reg rst_n=0,cv=0,co=0,opened=0;reg[35:0]hdr=0;reg[60:0]owner=0;
wire[96:0]a,b;reg[96:0]delay_a;always @(posedge ck)delay_a<=a;
qkd_embedding_ctx_start #(.NATIVE32(0)) u_a(.ck(ck),.rst_n(rst_n),.row_open(opened),.ctx_v(cv),.ctx_observed_v(co),.ctx_hdr(hdr),.ctx_owner(owner),.start(a[96]),.token(a[95:78]),.epoch(a[77:62]),.owner(a[61:1]),.fault(a[0]));
qkd_embedding_ctx_start #(.NATIVE32(1)) u_b(.ck(ck),.rst_n(rst_n),.row_open(opened),.ctx_v(cv),.ctx_observed_v(co),.ctx_hdr(hdr),.ctx_owner(owner),.start(b[96]),.token(b[95:78]),.epoch(b[77:62]),.owner(b[61:1]),.fault(b[0]));
integer checks=0,errors=0,warm=0,i,phase;integer token;
initial begin
 repeat(4)@(negedge ck);rst_n=1;
 for(i=0;i<10000;i=i+1)begin
  @(negedge ck);
  if(warm>16)begin checks=checks+1;if(delay_a!==b)begin errors=errors+1;if(errors<4)$display("DIFF i=%0d a=%h b=%h",i,a,b);end end
  if(!rst_n)warm=0;else warm=warm+1;
  phase=i%1000;rst_n=!(phase<4);cv=(phase>=32 && phase%128==32)||(phase>=36 && phase%128==36);
  co=1;opened=0;token=(phase-32)/128;
  hdr={5'd0,4'd12,6'd63,16'd17,5'd0};owner={2'd1,16'd17,6'd0,18'(token),13'd0,6'd0};
  if((i/1000)%4==1 && phase==48)begin cv=1;owner[36:19]=18'd99;end
  if((i/1000)%4==2 && phase==32)hdr[20:5]=16'd18;
  if((i/1000)%4==3 && phase==32)hdr[30:27]=4'd13;
  if(warm<16)cv=0;
 end
 if(errors)$fatal(1,"FAIL CTX_NATIVE32 checks=%0d errors=%0d",checks,errors);
 $display("PASS CTX_NATIVE32 checks=%0d errors=%0d",checks,errors);$finish;
end
endmodule
