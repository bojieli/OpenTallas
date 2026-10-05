`timescale 1ns/1ps
module tb_hbm_tu_shared8;
reg clk=0,pclk=0,rst_n=0,prst_n=0;always #5 clk=~clk;always #7 pclk=~pclk;
reg req=0,mode=0,finish=0,release_v=0;
reg[31:0] release_phase=9;reg[7:0] ar_tx=0,ga_tx=0,ph_rx=0,credit=0;
wire ready,busy,fault,retired;wire[1:0] go;wire[7:0] tx,ar_rx,ga_rx,ar_cr,ga_cr;
ot_hbm_tu_shared8 #(.ENABLE(1)) dut(
 .clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),.request_valid(req),.request_ready(ready),.request_mode(mode),
 .request_rank(8'd3),.request_pf(16'd64),.request_operation(64'd77),.request_phase(32'd9),
 .endpoint_rearm_ready(2'b11),.endpoint_quiet_core(2'b11),.endpoint_quiet_phy(2'b11),
 .finish_valid(finish),.finish_operation(64'd77),.finish_phase(32'd9),
 .fabric_release_valid(release_v),.fabric_release_operation(64'd77),.fabric_release_phase(release_phase),
 .ar_tx_v(ar_tx),.ga_tx_v(ga_tx),.ar_tx_flit(4360'd123),.ga_tx_flit(4360'd456),.ph_tx_v(tx),
 .ph_rx_v(ph_rx),.ph_rx_flit(4360'd789),.ar_rx_v(ar_rx),.ga_rx_v(ga_rx),
 .sw_cr_ret(credit),.ar_cr_ret(ar_cr),.ga_cr_ret(ga_cr),.ar_rx_credit(8'd0),.ga_rx_credit(8'd0),
 .endpoint_go(go),.retired(retired),.busy(busy),.fault(fault));
task step;begin @(posedge clk);#1;end endtask
integer i;reg seen;
initial begin
 repeat(3)step();rst_n=1;prst_n=1;repeat(4)step();
 @(negedge clk);req=1;step();@(negedge clk);req=0;
 seen=0;for(i=0;i<12;i=i+1)begin step();if(go==1)seen=1;end
 if(!seen||!busy||fault)$fatal(1,"AR ownership/GO");
 @(negedge pclk);ar_tx=1;repeat(3)@(posedge pclk);#1;if(tx!=1)$fatal(1,"AR TX");
 @(negedge pclk);ar_tx=0;ph_rx=2;#1;if(ar_rx!=2||ga_rx!=0)$fatal(1,"RX owner");
 ph_rx=0;credit=4;#1;if(ar_cr!=4||ga_cr!=0)$fatal(1,"credit owner");credit=0;
 repeat(8)step();@(negedge clk);finish=1;step();@(negedge clk);finish=0;
 repeat(4)step();if(!busy||ready)$fatal(1,"must retain before matched fabric release");
 @(negedge clk);release_v=1;step();@(negedge clk);release_v=0;
 seen=0;for(i=0;i<12;i=i+1)begin step();if(retired)seen=1;end
 if(!seen||busy||fault)$fatal(1,"positive handoff");
 @(negedge clk);mode=1;req=1;step();@(negedge clk);req=0;
 seen=0;for(i=0;i<12;i=i+1)begin step();if(go==2)seen=1;end
 if(!seen)$fatal(1,"gather GO");
 @(negedge clk);finish=1;step();@(negedge clk);finish=0;
 @(negedge clk);release_phase=10;release_v=1;step();@(negedge clk);release_v=0;
 repeat(6)step();if(!fault||!busy)$fatal(1,"foreign release must retain owner");
 $display("PASS_SHARED8_AR_GATHER_ROUTING_MATCHED_RELEASE_FOREIGN_HOLD");$finish;
end
endmodule
