`timescale 1ps/1ps
module tb_qwen_s4_numeric_memory;
reg hclk=0,por=0;always #512 hclk=~hclk;
reg [127:0] rv=0,cv=0,we=0,hcv=0;
reg [383:0] op=0,cred=0;
reg [639:0] bank=0,cbank=0,col=0;
reg [2431:0] row=0;
reg [3071:0] sec=0;
reg [32767:0] dat=0;
reg [1151:0] tag=0;
wire [127:0] lv,av;wire [2175:0] ls;wire [1023:0] lr;
wire [32767:0] ld;wire [1151:0] at;wire fault;wire [15:0] code;
ot_qwen_s4_numeric_memory dut(.hclk(hclk),.rst_n(por),.row_v(rv),.col_v(cv),.col_we(we),.row_op(op),.row_bank(bank),.col_bank(cbank),.col_col(col),.row_row(row),.h_cv(hcv),.h_csec(sec),.h_cdata(dat),.h_ctag(tag),.cred_ret(cred),.h_lv(lv),.h_av(av),.h_lsec(ls),.h_lrow(lr),.h_ldata(ld),.h_atag(at),.phy_fault(fault),.fault_code(code));
localparam integer BASE=35*131072,LAST=36*131072-1;
localparam [255:0] WRDATA=256'hfedcba98765432100123456789abcdef00112233445566778899aabbccddeeff;
localparam [255:0] LASTDATA=256'hffffffff00000000aaaaaaaa55555555123456789abcdef0deadbeef01234567;
integer ack=0,landing=0;
always @(negedge hclk)begin
 if(av[0])begin
  if(at[8:0]!=9'h183||dut.mem[BASE]!=WRDATA||dut.hcyc<27)$fatal(1,"actual WR ACK/capture/deadline mismatch");
  ack=ack+1;
 end
 if(lv[0])begin
  if(ls[16:0]!=0||lr[7:0]!=35||ld[255:0]!=WRDATA)$fatal(1,"last-layer WR->RD mismatch");
  landing=landing+1;
 end
 if(lv[127])begin
  if(ls[127*17+:17]!=131071||lr[127*8+:8]!=35||ld[127*256+:256]!=LASTDATA)$fatal(1,"last full-extent word mismatch");
  landing=landing+1;
 end
end
task automatic edge_at(input integer n);
 do @(negedge hclk);while(dut.hcyc<n);
endtask
initial begin
 dut.mem[BASE]=0;dut.mem[LAST]=LASTDATA;
 repeat(3)@(negedge hclk);por=1;
 edge_at(1);rv[0]=1;rv[127]=1;op[0+:3]=1;op[127*3+:3]=1;bank[127*5+:5]=31;row[0+:19]=35;row[127*19+:19]=35;
 @(negedge hclk);rv=0;
 edge_at(11);cv[0]=1;we[0]=1;
 @(negedge hclk);cv=0;we=0;hcv[0]=1;sec[23:0]=BASE;dat[255:0]=WRDATA;tag[8:0]=9'h183;
 @(negedge hclk);hcv=0;
 edge_at(28);cv[0]=1;cv[127]=1;cbank[127*5+:5]=31;col[127*5+:5]=31;
 @(negedge hclk);cv=0;
 edge_at(60);
 if(fault||dut.viol||ack!=1||landing!=2||dut.mem[LAST]!=LASTDATA)$fatal(1,"provider timed terminal mismatch fault=%b code=%h ack=%0d land=%0d",fault,code,ack,landing);
 cred[0+:3]=1;cred[127*3+:3]=1;@(negedge hclk);cred=0;@(negedge hclk);
 if(dut.lpend[0]||dut.lpend[127]||fault)$fatal(1,"actual finite credit return mismatch");
 // A real out-of-bounds row/WR capture must fault and retain backing;
 // numerical provider never fabricates a completion or falls back to zero.
 hcv[0]=1;dut.wc_pend[0]=1;dut.wc_addr[0]=36*131072;dut.wc_now[0]=dut.hcyc*1024;
 sec[23:0]=36*131072;@(negedge hclk);hcv=0;@(negedge hclk);
 if(!fault||!code[8]||ack!=1||dut.mem[LAST]!=LASTDATA)$fatal(1,"bounds fault produced false ACK/backing change");
 $display("PASS canonical full36 numeric provider layer35 PC0/127 capturedWR timedACK RD lastword finitecredit and boundsfault; simulation only");$finish;
end
endmodule
