`timescale 1ns/1ps
module tb_hbm_accel_direct_links_faults;
 localparam integer FW=512,PW=551;
 reg clk=0; always #0.416666667 clk=~clk;
 reg rst_n=0,iv=0; wire ir,ov,last,fault;
 reg [511:0] idata=0; reg [31:0] itag=0;
 wire [19:0] tv,rr; reg [19:0] tr=0,rv=0;
 wire [20*PW-1:0] tx; reg [20*PW-1:0] rx=0;
 wire [511:0] od; wire [6:0] rank; wire [31:0] tag;
 integer checks=0,errors=0;
 ot_hbm_accel_gather_die #(.ENABLE(1),.RANK(0)) dut(
 .clk(clk),.rst_n(rst_n),.in_valid(iv),.in_ready(ir),.in_data(idata),.in_tag(itag),
 .tx_valid(tv),.tx_ready(tr),.tx_record(tx),.rx_valid(rv),.rx_ready(rr),.rx_record(rx),
 .out_valid(ov),.out_ready(1'b1),.out_data(od),.out_rank(rank),.out_tag(tag),.out_last(last),.fault(fault));
 task automatic check(input bit ok);
 begin checks=checks+1; if(!ok) errors=errors+1; end endtask
 task automatic reset_start;
 begin
 @(negedge clk); rst_n=0; iv=0; rv=0; tr=0;
 repeat(2) @(negedge clk); rst_n=1;
 check(ir && !fault && !ov && rr==0);
 iv=1; idata={16{32'h3f800000}}; itag=32'h12345678;
 @(negedge clk); iv=0;
 check(!ir && !fault && tv=='1);
 idata='1; itag='1;
 repeat(3) begin @(negedge clk);
 check(tx[0+:PW]=={32'h12345678,7'd0,{16{32'h3f800000}}}); end
 end endtask
 task automatic inject(input integer port,src,input reg [31:0] packet_tag);
 begin
 rv=0; rx=0; rv[port]=1;
 rx[port*PW+:PW]={packet_tag,7'(src),{16{32'h40400000}}};
 @(negedge clk); rv=0;
 end endtask
 task automatic sticky_fault;
 begin
 check(fault && !ir && !ov && rr==0 && tv==0);
 repeat(3) @(negedge clk);
 check(fault && !ir && !ov);
 end endtask
 initial begin
 reset_start(); inject(0,1,32'hbad); sticky_fault();
 reset_start(); inject(0,96,32'h12345678); sticky_fault();
 reset_start(); inject(15,32,32'h12345678); sticky_fault();
 reset_start(); inject(0,2,32'h12345678); sticky_fault();
 reset_start(); inject(0,1,32'h12345678); check(!fault);
 inject(0,1,32'h12345678); sticky_fault();
 reset_start(); inject(19,80,32'h12345678); check(!fault);
 // Stall local TX while a different global source arrives: own packet stays captured.
 inject(15,16,32'h12345678); check(!fault);
 check(tx[0+:PW]=={32'h12345678,7'd0,{16{32'h3f800000}}});
 $display("HA2_FAULT_TERMINAL checks=%0d mismatches=%0d",checks,errors);
 if(errors) $fatal(1,"fault contract mismatch");
 $finish;
 end
endmodule
