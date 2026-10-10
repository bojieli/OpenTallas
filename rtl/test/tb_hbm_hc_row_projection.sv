`timescale 1ns/1ps
module tb_hbm_hc_row_projection(input wire clk);
 reg rst_n=0,cv=0;wire cr,qv,rr,ov,flt;wire [29:0]qa;
 wire [2:0]ql;wire [9:0]qt;reg rv=0;reg [9:0]rt=0;reg [1:0]rb=0;
 reg [255:0]rd=0;wire [7:0]xr;wire [127:0]xa;reg [4095:0]x0,x1;
 wire [4:0]row;wire [31:0]y;
 reg [31:0]wm[0:20479];reg [15:0]xm[0:20479];reg[31:0]exp[0:0];
 integer cyc=0,sent=0,sector=0,left=0,base=0,beat=0,start=0,b,l;
 reg[9:0]tag;reg mutant=0;
 wire qr=(left==0 && (cyc%7!=0));wire oready=(cyc%11==0);
 ot_hbm_hc_row_projection dut(.clk(clk),.rst_n(rst_n),.cmd_valid(cv),.cmd_ready(cr),
  .cmd_row(5'd17),.cmd_weight_base(30'd0),.cmd_eps(32'h358637bd),
  .hq_v(qv),.hq_rdy(qr),.hq_addr(qa),.hq_len(ql),.hq_tag(qt),
  .hr_v(rv),.hr_rdy(rr),.hr_tag(rt),.hr_beat(rb),.hr_data(rd),
  .x_re(xr),.x_addr(xa),.x_data(x1),.o_valid(ov),.o_ready(oready),
  .o_row(row),.o_data(y),.fault(flt));
 initial begin
  $readmemh("hcp_w.mem",wm);$readmemh("hcp_x.mem",xm);$readmemh("expected.mem",exp);
  mutant=$test$plusargs("MUTANT");
 end
 always @(posedge clk) begin
  cyc<=cyc+1;if(cyc==4)rst_n<=1;
  if(rst_n&&cr&&!sent)begin cv<=1;sent<=1;end
  if(cv&&cr)begin cv<=0;start<=cyc;end
  rv<=0;
  if(qv&&qr)begin base=qa;tag=qt;beat=0;left=ql;end
  else if(left>0 && (cyc%5!=0))begin
   rv<=1;rt<=tag;rb<=2'(beat);
   for(l=0;l<8;l=l+1)rd[l*32+:32]<=wm[((base+beat)/512)*2560+((base+beat)%512)*8+l];
   // Address is bank-contiguous with128 reserved1024b words per bank.
   if(mutant && sector==0)rd[31]<=~wm[0][31];
   sector=sector+1;beat=beat+1;left=left-1;
  end
  for(b=0;b<8;b=b+1)for(l=0;l<32;l=l+1)
   x0[(b*32+l)*16+:16]<=xm[b*2560+int'(xa[b*16+:16])*32+l];
  x1<=x0;
  if(rst_n&&flt)$fatal(1,"fault at %0d",cyc);
  if(ov&&oready)begin
   if(y!==exp[0] || row!==17 || sector!=2560)$fatal(1,"mismatch %08x expected %08x sectors%0d",y,exp[0],sector);
   $display("HC_ROW_PASS K=20480 W=32 sectors=%0d total_cycles=%0d result=%08x",sector,cyc-start,y);$finish;
  end
  if(cyc>30000)$fatal(1,"protocol timeout");
 end
endmodule
