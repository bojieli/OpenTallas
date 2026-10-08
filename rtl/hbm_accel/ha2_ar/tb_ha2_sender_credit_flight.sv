`timescale 1ns/1ps
// Isolate the actual sender, receiver pin capture, FD8 FIFO and registered
// threshold-ready mechanism. No arithmetic/core needed to test finite flight.
module tb_ha2_sender_credit_flight #(
 parameter integer DATA_DELAY=0, READY_DELAY=0
);
 localparam integer W=544,ROWS=192;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,issue_v=0;reg[W-1:0] issue_data=0;
 wire issue_ready,arrival_v,send_v,quiet,fault;
 wire[W-1:0] arrival_data,send_data;
 wire hub_idle;
 ot_ha2_delay_quiet #(.W(W),.D(35)) u_hub
  (.clk(clk),.rst_n(rst_n),.v_in(issue_v),.d_in(issue_data),
   .v_out(arrival_v),.d_out(arrival_data),.quiet(hub_idle));
 wire ready_wire;
 reg ready=0;
 if(READY_DELAY==0)begin assign ready_wire=ready;end
 else begin:g_return
  reg[READY_DELAY-1:0] r;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)r<=0;else begin r[0]<=ready;for(integer i=1;i<READY_DELAY;i=i+1)r[i]<=r[i-1];end
  assign ready_wire=r[READY_DELAY-1];
 end
 ot_ha2_hub_credit_sender_capture #(.W(W),.INJ(1),.CAPTURE(1)) u_sender
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(arrival_v),
   .arrival_data(arrival_data),.receiver_ready(ready_wire),.issue_ready(issue_ready),
   .send_v(send_v),.send_data(send_data),.quiet(quiet),.fault(fault));
 wire wire_v;wire[W-1:0] wire_d;
 if(DATA_DELAY==0)begin assign wire_v=send_v;assign wire_d=send_data;end
 else begin:g_forward
  ot_ha2_delay_quiet #(.W(W),.D(DATA_DELAY)) u_delay
   (.clk(clk),.rst_n(rst_n),.v_in(send_v),.d_in(send_data),
    .v_out(wire_v),.d_out(wire_d),.quiet());
 end
 reg pin_v=0;reg[W-1:0] pin_d;
 always @(posedge clk or negedge rst_n)if(!rst_n)pin_v<=0;else pin_v<=wire_v;
 always @(posedge clk)pin_d<=wire_d;
 wire[W-1:0] head;wire nonempty,overflow;wire[3:0] count;
 integer cycle=0,issued=0,received=0,peak=0;
 wire pop=cycle>=300 && cycle%2==0 && nonempty;
 ot_ha2_hr_fifo #(.W(W),.D(8)) u_receiver
  (.clk(clk),.rst_n(rst_n),.wv(pin_v),.wd(pin_d),.pop(pop),
   .hd(head),.nonempty(nonempty),.cnt(count),.ovf(overflow));
 always @(posedge clk or negedge rst_n)if(!rst_n)ready<=0;else ready<=count<=3;
 function automatic[W-1:0] row(input integer n);
  for(integer j=0;j<W/32;j=j+1)row[j*32+:32]=32'h12345678^(n<<8)^j;
 endfunction
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(cycle=0;cycle<2000;cycle=cycle+1)begin
   @(negedge clk);issue_v=issue_ready&&issued<ROWS;issue_data=row(issued);
   @(posedge clk);
   if(issue_v)issued=issued+1;
   if(pop)begin
    if(head!==row(received))$fatal(1,"FLIGHT_DATA_FAIL row=%0d",received);
    received=received+1;
   end
   #1;
   if(count>peak)peak=count;
   if(overflow)$fatal(1,"FLIGHT_OVERFLOW data=%0d return=%0d peak=%0d",DATA_DELAY,READY_DELAY,peak);
   if(fault)$fatal(1,"FLIGHT_SENDER_FAIL");
   if(received==ROWS)begin
    $display("PASS_FLIGHT data=%0d return=%0d rows=%0d peak=%0d",DATA_DELAY,READY_DELAY,received,peak);$finish;
   end
  end
  $fatal(1,"FLIGHT_TIMEOUT rows=%0d",received);
 end
endmodule
