`timescale 1ns/1ps
// Counter boundary test: seed only reservation counters, leaving actual SRAM
// and codec intact. Streaming reuse is exercised separately for1024frames.
module tb_hgi_coll_static_link_seq_overflow;
 reg clk=0,rst_n=0,epoch_begin=0,wr_v=0,rd_v=0,ev=0;
 reg [15:0] seq=0;
 wire abort,retry,tv,rv;wire[611:0]tf;wire[544:0]rf;wire[10:0]cause;
 ot_hgi_coll_static_link_seq d(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h55),
 .wr_v(wr_v),.wr_observed_v(1'b1),.wr_seq(seq),.wr_flit(545'b0),.rd_v(rd_v),.rd_seq(seq),
 .rx_expect_v(ev),.rx_expect_seq(seq),.phy_up(1'b1),.tx_pin_v(tv),.tx_pin_flit(tf),
 .rx_pin_v(1'b0),.rx_pin_flit(612'b0),.rx_v(rv),.rx_flit(rf),.epoch_abort(abort),.retry_requested(retry),.fault_cause(cause));
 task tick;begin #5;clk=1;#1;#4;clk=0;end endtask
 initial begin
  tick();rst_n=1;epoch_begin=1;tick();epoch_begin=0;
  // Test final two legal writes then refuse a16bit wrap. No fake SRAM state.
  d.write_sequence=17'd65534;
  wr_v=1;seq=65534;tick();if(abort)$fatal(1,"65534 refused");
  seq=65535;tick();if(abort)$fatal(1,"65535 refused");
  seq=0;tick();if(!abort||!cause[8])$fatal(1,"65536 wrap accepted");
  // Read and RX counters use identical saturated17b boundary independently.
  epoch_begin=1;wr_v=0;tick();epoch_begin=0;
  d.tx_sequence=17'd65536;rd_v=1;tick();if(!abort||!cause[8])$fatal(1,"read wrap accepted");
  epoch_begin=1;rd_v=0;tick();epoch_begin=0;
  d.rx_sequence=17'd65536;ev=1;tick();if(!abort||!cause[8])$fatal(1,"RX wrap accepted");
  $display("HBM_STATIC_LINK_SEQ_OVERFLOW_PASS seeded_boundary_write_read_receive");$finish;
 end
endmodule
