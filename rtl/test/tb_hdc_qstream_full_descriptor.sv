`timescale 1ns/1ps
module tb_hdc_qstream_full_descriptor;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,tok_start=0;
  reg [159:0] entries[0:0];
  integer expect_fault, id, expected_addr, expected_rom, expected_count, expected_ibase;
  integer cycles=0;
  wire hq_v,fault,vi_re;
  wire [29:0] hq_addr,vi_addr;
  initial begin
    $readmemh("entry.hex",entries);
    if (!$value$plusargs("FAULT=%d",expect_fault)) $fatal;
    if (!$value$plusargs("ID=%d",id)) $fatal;
    if (!$value$plusargs("ADDR=%d",expected_addr)) $fatal;
    if (!$value$plusargs("ROM=%d",expected_rom)) $fatal;
    if (!$value$plusargs("COUNT=%d",expected_count)) $fatal;
    if (!$value$plusargs("IBASE=%d",expected_ibase)) $fatal;
    repeat(3) @(negedge clk);rst_n=1;tok_start=1;
    @(negedge clk);tok_start=0;
  end
  ot_hdc_qstream #(.FULL_SHAPE(1),.LWIN(3),.LA(2)) dut(
    .clk(clk),.rst_n(rst_n),.cfg_base(30'h10000000),.cfg_lbase(12'd0),
    .cfg_lead(21'd1),.cfg_rate(16'd256),.tok_start(tok_start),.pos(21'd1),
    .l_q(entries[0]),.vi_q(32'(id)),.vi_re(vi_re),.vi_addr(vi_addr),.wrel_v(1'b0),
    .qd_v(1'b0),.qd_nb(8'd0),.qd_tiles(21'd0),.qr_re(1'b0),.qr_addr(30'd0),
    .win_q(4352'd0),.hq_v(hq_v),.hq_addr(hq_addr),.hq_rdy(1'b1),.hq_room(8'hff),
    .hr_v(8'd0),.hr_tag(24'd0),.hr_beat(40'd0),.hr_data(2048'd0),.fault(fault));
  always @(posedge clk) begin
    cycles<=cycles+1;
    if (vi_re && vi_addr !== 30'(expected_ibase)) $fatal(1,"indirect VM address truncated");
    if (fault) begin
      if (!expect_fault || hq_v) $fatal(1,"unexpected fault/request");
      $display("QSTREAM_DESCRIPTOR_FAULT_PASS");$finish;
    end
    if (hq_v) begin
      if (expect_fault) $fatal(1,"request escaped invalid descriptor");
      if (hq_addr !== 30'(expected_addr) || dut.e_n !== 21'(expected_count) ||
          dut.of_n[0] !== 21'(expected_count) || dut.of_rom[0] !== 30'(expected_rom))
          $fatal(1,"descriptor/address/count mismatch addr=%h n=%d",hq_addr,dut.e_n);
      $display("QSTREAM_DESCRIPTOR_PASS addr=%h n=%d",hq_addr,dut.e_n);$finish;
    end
    if (cycles>80) $fatal(1,"timeout");
  end
endmodule
