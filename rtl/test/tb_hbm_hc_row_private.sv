`timescale 1ns/1ps
module tb_hbm_hc_row_private(input wire clk);
 reg rst_n=0,cv=0;wire cr,qv,rr,ov,flt;wire [29:0]qa;
 wire [2:0]ql;wire [9:0]qt;reg rv=0;reg [9:0]rt=0;reg [1:0]rb=0;
 reg [255:0]rd=0;wire xready;reg xv=0;reg[15:0]xl=16'h1234;reg[10:0]xb=0;reg[255:0]xd=0;integer xs=0,natural,bankidx;wire[15:0]outlease;reg badlease=0;
 wire [4:0]row;wire [31:0]y;
 reg [31:0]wm[0:20479];reg [15:0]xm[0:20479];reg[31:0]exp[0:0];
 integer cyc=0,sent=0,sector=0,left=0,base=0,beat=0,start=0,b,l;
 reg[9:0]tag;reg mutant=0;
 wire qr=(left==0 && (cyc%7!=0));wire oready=(cyc%11==0);
 ot_hbm_hc_row_private dut(.clk(clk),.rst_n(rst_n),.cmd_valid(cv),.cmd_ready(cr),
  .cmd_row(5'd17),.cmd_lease(16'h1234),.cmd_weight_base(30'd0),.cmd_eps(32'h358637bd),
  .hq_v(qv),.hq_rdy(qr),.hq_addr(qa),.hq_len(ql),.hq_tag(qt),
  .hr_v(rv),.hr_rdy(rr),.hr_tag(rt),.hr_beat(rb),.hr_data(rd),
  .x_valid(xv),.x_ready(xready),.x_lease(xl),.x_beat(xb),.x_data(xd),.o_valid(ov),.o_ready(oready),
  .o_row(row),.o_lease(outlease),.o_data(y),.fault(flt));
 initial begin
  $readmemh("hcp_w.mem",wm);$readmemh("hcp_x.mem",xm);$readmemh("expected.mem",exp);
  mutant=$test$plusargs("MUTANT");badlease=$test$plusargs("BADLEASE");
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
  xv<=0;
  if(xready && xs<1280 && cyc%7!=0)begin
   xv<=1;xb<=11'(xs);xl<=badlease?16'h1235:16'h1234;
   for(l=0;l<16;l=l+1)begin
    natural=xs*16+l;bankidx=natural%8;
    xd[l*16+:16]<=xm[bankidx*2560+natural/8];
   end
   xs=xs+1;
  end
  if(rst_n&&flt)begin
   if(badlease)begin $display("HC_PRIVATE_BADLEASE_REJECTED");$finish;end
   else $fatal(1,"fault at %0d",cyc);
  end
  if(ov&&oready)begin
   if(y!==exp[0] || row!==17 || outlease!==16'h1234 || sector!=2560 || xs!=1280)$fatal(1,"mismatch %08x expected %08x sectors%0d",y,exp[0],sector);
   $display("HC_PRIVATE_PASS K=20480 W=32 sectors=%0d total_cycles=%0d result=%08x",sector,cyc-start,y);$finish;
  end
  if(cyc>30000)$fatal(1,"protocol timeout");
 end
endmodule
