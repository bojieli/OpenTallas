module BUFx2_ASAP7_75t_R(input A,output Y);assign Y=A;endmodule
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,valid=0,credit=0;reg [17:0] address=0;
wire[17:0] aq18,an18;wire[11:0]aq12,an12;wire vq12,vn12,cq12,cn12,vq18,vn18,cq18,cn18;
ot_qwen_embedding_ingress_padded #(.AW(12)) a(clk,rst_n,address[11:0],valid,credit,aq12,an12,vq12,vn12,cq12,cn12);
ot_qwen_embedding_ingress_padded #(.AW(18)) b(clk,rst_n,address,valid,credit,aq18,an18,vq18,vn18,cq18,cn18);
initial begin
 for(integer i=0;i<60;i=i+1)begin
  @(negedge clk);address=$random;valid=$random;credit=$random;rst_n=(i%11!=0);
  @(posedge clk);#1;
  if(aq18!==address || an18!==~address || aq12!==address[11:0] || an12!==~address[11:0])$fatal(1,"address");
  if({vq12,vn12,cq12,cn12} !== (rst_n?{valid,~valid,credit,~credit}:4'b0101))$fatal(1,"control12");
  if({vq18,vn18,cq18,cn18} !== (rst_n?{valid,~valid,credit,~credit}:4'b0101))$fatal(1,"control18");
 end
 $display("PASS physical-cell synthesis branch Boolean/reset equivalence for both widths");$finish;
end
endmodule
