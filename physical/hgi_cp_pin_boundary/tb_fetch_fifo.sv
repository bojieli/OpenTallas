`timescale 1ns/1ps
module tb_fetch_fifo;
  reg clk=0; always #1 clk=~clk;
  reg rst_n=0, iv=0, ready=0;
  reg [39:0] addr=0;
  wire ov; wire [39:0] oa;
  ot_hgi_cp #(.USE_MACRO(0), .FETCH_PIN_FIFO(1)) dut
    (.clk(clk), .rst_n(rst_n), .cmd_we(1'b0), .cmd_addr(6'b0), .cmd_wdata(64'b0),
     .units_busy(1'b0), .rank(8'b0), .db_v(1'b0), .db_token(18'b0), .db_pos(20'b0),
     .db_job(32'b0), .db_gen(4'b0), .db_entry(2'b0), .db_ncol(4'b0), .db_kernel(4'b0),
     .f_req_v(ov), .f_req_rdy(ready), .f_req_addr(oa), .f_rsp_v(1'b0), .f_rsp_data(256'b0),
     .vr_rdy(1'b0), .vr_rsp_v(1'b0), .vr_rsp_data(32'b0), .u_rdy(16'b0), .u_done(16'b0),
     .u_fault(16'b0), .wr_quiet(1'b1), .cpl_rdy(1'b1));
  integer sent=0, received=0, cycles=0, fails=0, full_seen=0, simultaneous=0;
  reg stalled=0; reg [39:0] held=0;
  initial begin
    force dut.sf_v=iv;
    force dut.sf_addr=addr;
    repeat(4) @(negedge clk);
    rst_n=1;
    while(received<500 && cycles<4000) begin
      iv=(sent<500); addr=40'h1a00000000+sent;
      ready=(cycles%73>=41);
      @(posedge clk);
      if(stalled && (!ov || oa!==held)) begin
        $display("FAIL stalled address/valid changed"); fails=fails+1;
      end
      if(ov && ready) begin
        if(oa!==(40'h1a00000000+received)) begin
          $display("FAIL req %0d got %h",received,oa); fails=fails+1;
        end
        received=received+1;
      end
      if(iv && dut.sf_rdy) sent=sent+1;
      if(dut.g_fetch_pin.back_v) full_seen=full_seen+1;
      if(iv && dut.sf_rdy && ov && ready) simultaneous=simultaneous+1;
      stalled=ov && !ready; held=oa;
      cycles=cycles+1;
      @(negedge clk);
    end
    if(received!=500 || sent!=500 || full_seen<10 || simultaneous<100 || fails) begin
      $display("FETCH_FIFO FAIL sent%0d received%0d full%0d simultaneous%0d errors%0d",sent,received,full_seen,simultaneous,fails);
      $fatal(1);
    end
    $display("FETCH_FIFO PASS sent%0d received%0d cycles%0d full%0d simultaneous%0d",sent,received,cycles,full_seen,simultaneous);
    $finish;
  end
endmodule
