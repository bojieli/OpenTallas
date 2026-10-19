`timescale 1ns/1ps
// Actual production-parameter native QM: legal host FIFO-credit burst of CSR0
// writes. Check every consumed source event reaches the destination with its
// corresponding payload, rather than merely comparing two copies of the RTL.
module tb_hkv_cdc_csr_temporal;
 parameter integer HOLD_ACK=1;
 reg rst_n=0,ck=0,clk_h=0,clk_i=0;
 always #0.416667 ck=~ck;
 initial begin #0.137; forever #0.500 clk_h=~clk_h; end
 initial begin #0.277; forever #0.833334 clk_i=~clk_i; end
 reg h_v=0; reg[1:0]h_cls=0;reg[511:0]h_d=0;
 wire[4:0]h_crn;wire t_v,o_v,o_we,fault,quiet_h,quiet_i,quiet_c;
 wire[63:0]t_d;wire[31:0]o_addr;wire[255:0]o_d;
 qkd_hr_native_qm_cdc #(.CSR_HOLD_ACK(HOLD_ACK)) dut(.rst_n(rst_n),.ck(ck),.clk_h(clk_h),.clk_i(clk_i),
 .clk_i_bank({2{clk_i}}),.clk_i_out(clk_i),.h_v(h_v),.h_cls(h_cls),.h_d(h_d),.h_crn(h_crn),
 .t_v(t_v),.t_d(t_d),.t_cr(1'b0),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),.o_d(o_d),
 .o_cr(1'b0),.i_rv(1'b0),.i_rd(256'b0),.fault(fault),.quiet_h(quiet_h),.quiet_i(quiet_i),.quiet_c(quiet_c));
 reg[8:0]expected[0:15];integer published=0,captured=0,n=0;
 always @(posedge clk_i) if(dut.rn_i && dut.hv_i && dut.hx_pop && !dut.f_any && dut.hcl==0 && dut.hx_head[7:0]==0)begin
  expected[published]=dut.hx_head[40:32];published=published+1;
 end
 always @(posedge ck)if(dut.rn_c && (HOLD_ACK != 0 ? dut.tg_s[2]!=dut.csr_ack : dut.tg_s[2]!=dut.tg_s[1]))begin
  #0.001;
  if(captured>=published || dut.share_c!==expected[captured])
   $fatal(1,"CSR_TEMPORAL payload mismatch event=%0d published=%0d expected=%0d got=%0d",captured,published,expected[captured],dut.share_c);
  captured=captured+1;
 end
 initial begin
  repeat(20)@(negedge clk_h);rst_n=1;repeat(20)@(negedge clk_h);
  for(n=1;n<=8;n=n+1)begin h_v=1;h_d=0;h_d[40:32]=n;@(negedge clk_h);end
  h_v=0;repeat(200)@(negedge ck);
  if(fault || published!=8 || captured!=8)$fatal(1,"CSR_TEMPORAL count/fault published=%0d captured=%0d fault=%0b",published,captured,fault);
  $display("CSR_TEMPORAL PASS events=%0d",captured);$finish;
 end
endmodule
