`timescale 1ps/1ps
module tb_guard;
reg h=0,i=0,c=0,rst=0,hv=0;always #500 h=~h;always #833 i=~i;always #416 c=~c;
reg[1:0]cls=0;reg[511:0]data=0;wire[4:0]cr;wire tv,fault,ed;wire[63:0]td;wire[255:0]dd;
integer test=0,accepts=0,fwords=0,case_accept=0,case_fault=0;reg[255:0]descriptor;
qkd_hr_ingest_cdc_shell #(.IKEY_GUARD(1))dut(
 .rst_n(rst),.clk_h(h),.h_v(hv),.h_cls(cls),.h_d(data),.h_crn(cr),.t_v(tv),.t_d(td),.t_cr(tv),
 .clk_i(i),.e_rst_n(),.e_dv(ed),.e_ddata(dd),.e_inv_a(),.e_inv_b(),.e_indata(),.e_wrdy_o(),
 .e_drdy(1'b1),.e_inrdy(1'b1),.e_wv(1'b0),.e_wv_c(20'd0),.e_waddr(32'd0),.e_wdata(256'd0),
 .e_rv(1'b0),.e_raddr(32'd0),.e_done(1'b0),.e_done_a(1'b0),.e_done_c(1'b0),.e_done_b(1'b0),.e_tag(8'd0),.e_busy(1'b0),.e_nsec(32'd0),
 .ck(c),.o_v(),.o_we(),.o_addr(),.o_d(),.o_cr(1'b0),.i_rv(1'b0),.i_rd(256'd0),.fault(fault),.quiet_h(),.quiet_i(),.quiet_c());
always @(posedge i)if(rst&&ed)begin accepts=accepts+1;if(test<3)$fatal(1,"GUARD_ACCEPTED_MALFORMED test=%0d",test);end
always @(posedge h)if(rst&&tv)begin if(td!==64'hff00000000000008)$fatal(1,"WRONG_FAULT_WORD %h",td);fwords=fwords+1;end
task send(input[1:0]cl,input[511:0]d);begin @(negedge h);hv=1;cls=cl;data=d;@(negedge h);hv=0;end endtask
initial begin
 for(test=0;test<4;test=test+1)begin
  rst=0;hv=0;repeat(12)@(negedge h);rst=1;repeat(40)@(negedge h);
  descriptor=0;descriptor[3:0]=3;descriptor[199:184]=16;descriptor[255:240]=17;
  if(test==0)descriptor[167:144]=1;
  if(test==1)descriptor[199:184]=1;
  if(test==2)descriptor[255:240]=16;
  case_accept=accepts;case_fault=fwords;
  send(1,{256'd0,descriptor});send(2,512'h1234);send(2,512'h5678);
  repeat(200)@(negedge h);
  if(test<3)begin
   if(accepts!=case_accept||fwords!=case_fault+1||dut.f_code!=8||!dut.hx_empty)$fatal(1,"GUARD_FAIL test=%0d accepted=%0d faultwords=%0d code=%0d empty=%0d",test,accepts-case_accept,fwords-case_fault,dut.f_code,dut.hx_empty);
  end else if(accepts!=case_accept+1||fwords!=case_fault||fault)$fatal(1,"LEGAL_DESCRIPTOR_CHANGED");
  $display("GUARD_CASE_PASS test=%0d accepted=%0d faultwords=%0d",test,accepts-case_accept,fwords-case_fault);
 end
 $display("SPIPE6_GUARD_PASS");$finish;
end
initial begin #4000000;$fatal(1,"GUARD_TIMEOUT");end
endmodule
