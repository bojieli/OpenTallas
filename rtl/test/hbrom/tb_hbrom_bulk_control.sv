`timescale 1ns/1ps
module tb_hbrom_bulk_control;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,d_valid=0,s_ready=0; wire d_ready,req_v,s_valid,idle,fault;
 wire[31:0] req_addr;wire[9:0] req_tag;wire[1223:0] s_data;wire[9:0] outstanding;
 reg[6:0] rv=0;reg[9:0] tags[0:6];reg[31:0] addr[0:6];
 wire[1223:0] rd={{38{addr[6]}},addr[6][7:0]};
 integer cycle=0,got=0,issued=0,maxused=0,k;
 ot_hbrom_bulk_copy_control_protected #(.PROTECT(1),.ENABLE(1),.LINE_BITS(1224),
 .DEPTH(1024),.MAX_OUT(512),.SRAM_RING(1),.RING_MACRO(1)) dut(
 .clk(clk),.rst_n(rst_n),.d_valid(d_valid),.d_ready(d_ready),.d_base(32'd0),.d_lines(24'd1300),
 .req_v(req_v),.req_ready(1'b1),.req_addr(req_addr),.req_tag(req_tag),.rsp_v(rv[6]),
 .rsp_tag(tags[6]),.rsp_data(rd),.s_valid(s_valid),.s_ready(s_ready),.s_data(s_data),
 .outstanding(outstanding),.idle(idle),.control_fault(fault));
 always @(posedge clk) begin
  if(!rst_n) begin rv<=0;issued<=0;got<=0;cycle<=0;end
  else begin
   cycle<=cycle+1;rv<={rv[5:0],req_v};
   tags[0]<=req_tag;addr[0]<=req_addr;
   for(k=1;k<7;k=k+1)begin tags[k]<=tags[k-1];addr[k]<=addr[k-1];end
   if(req_v) issued<=issued+1;
   if(s_valid&&s_ready)begin
    if(s_data!=={{38{32'(got)}},8'(got)})$fatal(1,"payload/order got=%0d data=%h",got,s_data[39:8]);
    got<=got+1;
   end
   if(dut.g_protected.primary.g_lookahead.used>maxused)maxused=dut.g_protected.primary.g_lookahead.used;
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;d_valid=1;
  @(negedge clk);while(!d_ready)@(negedge clk);d_valid=0;
  repeat(1400)@(negedge clk);
  if(fault)$fatal(1,"unexpected fault during finite stall");
  if(issued>1027)$fatal(1,"overrun during stall %0d",issued);
  s_ready=1;
  while(got<1300 && cycle<5000)begin @(negedge clk);s_ready=(cycle%7!=0);end
  if(got!=1300||issued!=1300)$fatal(1,"flow incomplete %0d %0d",got,issued);
  repeat(8)@(negedge clk);
  if(fault||!idle)$fatal(1,"bad completion");
  force dut.g_protected.shadow.g_lookahead.full[17]=1'b1;
  #0.1;if(!fault||req_v||s_valid)$fatal(1,"bitmap fault not gated");
  @(negedge clk);release dut.g_protected.shadow.g_lookahead.full[17];
  #0.1;if(!fault)$fatal(1,"fault not sticky");
  rst_n=0;repeat(3)@(negedge clk);rst_n=1;
  force dut.g_protected.shadow.g_lookahead.alloc_p=11'd1;
  #0.1;if(!fault||req_v||s_valid)$fatal(1,"pointer fault not gated");
  @(negedge clk);release dut.g_protected.shadow.g_lookahead.alloc_p;
  rst_n=0;repeat(3)@(negedge clk);rst_n=1;
  force dut.g_protected.shadow.g_lookahead.g_sram.u_we0.q=20'd1;
  #0.1;if(!fault||req_v||s_valid)$fatal(1,"write enable fault not gated");
  @(negedge clk);release dut.g_protected.shadow.g_lookahead.g_sram.u_we0.q;
  $display("PASS native bulk DMR full1024ring512outstanding1224bits:1300linewrap stall maxused=%0d bitmap/pointer/WEfaults",maxused);$finish;
 end
endmodule
