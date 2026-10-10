`timescale 1ns/1ps
module tb_hgi_coll_mode_guard;
 reg clk=0; always #0.4166665 clk=~clk;
 reg rst_n=0,go=0; reg[3:0]gsz=0;
 wire[1:0]ir;wire[7:0]txv,rxc;wire[31:0]ii;wire[4359:0]txf;wire[3:0]dv;wire[2179:0]dfl;wire fault;wire[31:0]st;
 ot_hbm_accel_tu_endpoint_psg #(.ENABLE(1),.NC(8),.NOG(12),.PFMAX(16)) dut(
 .clk(clk),.rst_n(rst_n),.pclk(clk),.prst_n(rst_n),.rank(8'd0),.pf(16'd16),.mcast_all(1'b0),.mcast_group_size(8'd96),.gsz(gsz),.byp(1'b0),.go(go),
 .inj_idx(ii),.inj_rd(ir),.inj_data(1024'd0),.ph_tx_v(txv),.ph_tx_flit(txf),.sw_cr_ret(8'd0),
 .ph_rx_v(8'd0),.ph_rx_flit(4360'd0),.rx_credit(rxc),.del_valid(dv),.del_flit(dfl),.fault(fault),.stat_credit_stall(st));
 initial begin
  for(integer code=4;code<15;code=code+1) begin
   rst_n=0;go=0;gsz=4'(code);repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);go=1;
   repeat(200)begin @(negedge clk);if(ir!==0||txv!==0||dv!==0)$fatal(1,"BAD_MODE_ACTIVITY code=%0d",code);end
   if(fault!==1)$fatal(1,"BAD_MODE_NO_FAULT code=%0d",code);
   $display("MODE_REJECT PASS code=%0d",code);
  end
  rst_n=0;go=0;gsz=0;repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);go=1;
  repeat(200)begin @(negedge clk);if(ir!==0||txv!==0||dv!==0)$fatal(1,"BAD_MODE_ACTIVITY capacity");end
  if(fault!==1)$fatal(1,"BAD_MODE_NO_FAULT capacity");
  $display("MODE_GUARD PASS 11 reserved codes + oversized groupone");$finish;
 end
endmodule
