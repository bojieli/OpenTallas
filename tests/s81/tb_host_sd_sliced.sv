`timescale 1ns/1ps
module tb_host_sd_sliced;
 parameter integer MUT=0,STARVE=0;
 reg ck=0,rst=0;always #3 ck=~ck;
 reg iv=0,we=1;reg[31:0]a=0;reg[255:0]d=0;reg[8:0]hc=0;
 wire[291:0]hw,href;wire cr,cref,f,fref;wire[7:0]ack,ackref;
 wire rn;ot_reset_sync rr(.clk(ck),.async_rst_n(rst),.sync_rst_n(rn));
 wire[255:0]dut_d=MUT?(d^(256'd1 << (64*(MUT-1)+5))):d;
 dsfd_host_sd_sliced dut(.ck_control(ck),.ck_data({4{ck}}),.rst_n(rst),.o_v(iv),.o_we(we),.o_addr(a),.o_d(dut_d),.o_cr(cr),.hw(hw),.hc(hc),.host_ack_n(ack),.fault(f));
 // Legacy decoder owns the same native boundary input and conditioned reset.
 // In STARVE mode the reference receives the compiler-reserved return pulse;
 // the candidate misses it and must fault while preserving that emit calendar.
 wire[8:0]hc_ref=STARVE?{8'd0,href[0]}:hc;
 dsfd_host_sd ref_dut(.ck(ck),.rst_n(rn),.o_v(iv),.o_we(we),.o_addr(a),.o_d(d),.o_cr(cref),.hw(href),.hc(hc_ref),.host_ack_n(ackref),.fault(fref));
 integer cyc=0,emits=0,checked=0;reg fault_seen=0;
 initial begin #29 rst=1;end
 always @(negedge ck)if(rst)begin
  cyc=cyc+1;iv=0;hc=0;
  if(!STARVE)hc={8'(cyc%5),href[0]};
  if(cyc>30&&cyc<1500&&cyc%7==0)begin
   iv=1;a=cyc*32;d={8{32'(cyc*917+17)}};
   if(cyc%35==0)begin a=32'hffffffff;d[65:64]=2;end
  end
  if(cyc==1700)begin
   if(emits<190 || (STARVE&&!fault_seen) || (!STARVE&&f))$fatal(1,"SD_SLICED FAIL count/fault emits=%0d fault=%b",emits,f);
   $display("SD_SLICED PASS full256 exact_calendar edges=%0d emits=%0d STARVE=%0d",checked,emits,STARVE);$finish;
  end
 end
 always @(posedge ck)if(rst)begin
  #0.01;
  if(cyc>10)begin
   checked=checked+1;fault_seen=fault_seen|f;
   if(hw!==href || cr!==cref || (!STARVE&&({ack,f}!=={ackref,fref})))
    $fatal(1,"SD_SLICED FAIL reconstruction/calendar edge=%0d actual=%h ref=%h",cyc,hw,href);
   if(hw[0])emits=emits+1;
   // Every projected leaf must advance the source-equal local FIFO state;
   // no pointer value is supplied from the reference or another DUT leaf.
   if({dut.g_data[0].leaf.u_sd.wp,dut.g_data[0].leaf.u_sd.rp,dut.g_data[0].leaf.u_sd.n}!=={dut.control.u_sd.wp,dut.control.u_sd.rp,dut.control.u_sd.n} ||
      {dut.g_data[1].leaf.u_sd.wp,dut.g_data[1].leaf.u_sd.rp,dut.g_data[1].leaf.u_sd.n}!=={dut.control.u_sd.wp,dut.control.u_sd.rp,dut.control.u_sd.n} ||
      {dut.g_data[2].leaf.u_sd.wp,dut.g_data[2].leaf.u_sd.rp,dut.g_data[2].leaf.u_sd.n}!=={dut.control.u_sd.wp,dut.control.u_sd.rp,dut.control.u_sd.n} ||
      {dut.g_data[3].leaf.u_sd.wp,dut.g_data[3].leaf.u_sd.rp,dut.g_data[3].leaf.u_sd.n}!=={dut.control.u_sd.wp,dut.control.u_sd.rp,dut.control.u_sd.n})
    $fatal(1,"SD_SLICED FAIL local pointer equality");
  end
 end
endmodule
