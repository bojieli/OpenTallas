
`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0,sel=0;wire re;wire[14:0]addr;reg[511:0]rq=0;
reg[2:0]rx=0;wire fault;wire[5:0]fc;
ot_chip_v41x_ckv_die_service #(.K(512),.NSLOT(64),.COLLECTOR_CLEAR_PRIORITY(1)) dut(.clk(clk),.rst_n(rst_n),.sel_v(sel),.sel_vmword(15'd0),.nw_we(1'b0),.nw_addr(30'd0),.nw_data(1024'd0),.vm_re(re),.vm_raddr(addr),.vm_rq(rq),.vm_busy(),.c_v(),.c_rdy(4'hf),.c_addr(),.c_len(),.c_tag(),.c_we(),.c_wdata(),.c_wstrb(),.c_wr_done(4'd0),.c_sv(4'd0),.c_srdy(),.c_stag(64'd0),.c_sbeat(16'd0),.c_sdata(1024'd0),.ag_tx_valid(),.ag_tx_ready(1'b1),.ag_tx_rank(),.ag_tx_gid(),.ag_tx_row(),.ag_rx_valid(rx),.ag_rx_rank({10'd0,10'd0,10'd16}),.ag_rx_gid({21'd0,21'd0,21'd16}),.ag_rx_row(6912'd0),.job_v(1'b0),.job_ready(),.kv_v(),.kv_ready(1'b0),.kv_m(),.kv_w(),.job_done(),.fault(fault),.fault_code(fc),.rows_ready(),.st_rows_local(),.st_rows_remote(),.st_cycles_to_ready());
integer cyc=0;
always @(posedge clk)if(re===1'b1)for(integer j=0;j<16;j=j+1)rq[j*32+:32]<=32'(addr*16+j);
always @(negedge clk)begin
 cyc=cyc+1;if(cyc==5)rst_n=1;sel=(cyc==7||cyc==210);rx=(cyc==200||cyc==211)?3'b001:0;
 if(cyc==199)begin
  if(fault!==1'b0||dut.id_done!==1'b1||dut.id_count!==10'd512||dut.rd_act!==1'b0)$fatal(1,"fixture ID pipeline not retired");
 end
 if(cyc==202)begin
  if(fault!==1'b0||dut.npresent!==11'd1||dut.present[16]!==1'b1)$fatal(1,"fixture prior row not captured");
 end
 if(cyc==212)begin
  $display("DELAYED_OBSERVATION fault=%0d code=%0d count=%0d present16=%0d remote_stats=%0d",fault,fc,dut.npresent,dut.present[16],dut.st_rows_remote);
  if(fault!==1'b1||fc[2]!==1'b1||dut.present!==512'd0||dut.npresent!==11'd0||dut.st_rows_remote!==32'd0)$fatal(1,"delayed old response mutated new collector state");
  $display("DELAYED_OLD_RESPONSE_REJECT_PASS");$finish;
 end
 if(cyc==300)$fatal(1,"collector fixture finite bound");
end
endmodule
