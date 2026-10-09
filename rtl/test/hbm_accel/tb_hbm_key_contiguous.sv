`timescale 1ns/1ps
module tb_hbm_key_contiguous;
reg clk=0,rst_n=0; always #5 clk=~clk;
reg[19:0] pos=0;reg[6:0] die=0;reg rv=0,shv=0;reg[4351:0] data_=0,shadow=0;
wire ready,wv,fence;wire[1:0] stk;wire[4:0] pc,bank,col;wire[18:0] row;wire[255:0] wd;wire[15:0] issued,acked;
reg[5:0] ack=0;integer count=0,expsec,spc,sj,st,ord,off,rank,kind_,i,j,checks=0;
ot_hbm_accel_dskv_wb #(.ENABLE(1),.ALL_STACKS(1),.KEY_CONTIGUOUS(1)) dut(
.clk(clk),.rst_n(rst_n),.die(die),.pos(pos),.row_v(rv),.row_kind(2'd2),.row_slot(6'd3),.row_r2(1'b0),.row_data(data_),.row_r(ready),
.sh_v(shv),.sh_slot(3'd3),.sh_data(shadow),.wq_v(wv),.wq_pc(pc),.wq_bank(bank),.wq_row(row),.wq_col(col),.wq_data(wd),.wq_r(1'b1),.wq_stk(stk),.ack_n(ack),.issued(issued),.acked(acked),.fence_ok(fence));
initial begin
repeat(3) @(negedge clk);rst_n=1;
for(ord=0;ord<1366;ord=ord+1) begin
 rank=(ord*37)%96;
 for(off=0;off<8;off=off+1)begin
  if(8*(96*ord+rank)+off<1048576)begin
  @(negedge clk);shv=1;for(i=0;i<544;i=i+1)shadow[i*8+:8]=8'(i+ord);
  @(negedge clk);shv=0;pos=20'(8*(96*ord+rank)+off);die=7'(rank);
  for(i=0;i<68;i=i+1)data_[i*8+:8]=8'(i+off+13);
  rv=1;@(posedge clk);while(!ready)@(posedge clk);@(negedge clk);rv=0;count=0;
  while(!fence)begin
   if(wv)begin
    expsec=17*(ord%342)+(68*off)/32+count;st=ord/342;spc=expsec%32;sj=expsec/32;
    if(stk!=st||pc!=spc||bank!={3'(sj>>7),2'(sj)}||col!=5'(sj>>2)||row!=4006+(sj>>10))$fatal(1,"address ord=%0d off=%0d",ord,off);
    for(j=0;j<32;j=j+1)begin
     i=32*((68*off)/32+count)+j;
     if(i>=68*off&&i<68*(off+1))begin if(wd[j*8+:8]!=8'(i-68*off+off+13))$fatal(1,"new byte");end
     else if(wd[j*8+:8]!=8'(i+ord))$fatal(1,"shadow byte");
    end
    count=count+1;checks=checks+1;
   end
   ack=wv?1:0;@(negedge clk);
  end
  ack=0;if(count!=((68*off+67)/32-(68*off)/32+1))$fatal(1,"count");
  end
 end
end
$display("PASS_HBM_KEY_CONTIGUOUS sectors=%0d",checks);$finish;
end
initial begin #10000000;$display("DBG ord=%0d off=%0d issued=%0d acked=%0d count=%0d st=%0d rv=%0d",ord,off,issued,acked,count,dut.on.st,rv);$fatal(1,"timeout");end
endmodule
