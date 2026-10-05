`timescale 1ps/1fs
// HA8 stream bench: ot_hbmacc_qwen_wstream with an always-ready consumer (C follows A minus LAG words),
// measuring the sustained per-die stream rate over WORDS stream words.  Prints the rate in TB/s per stack.
module tb_hbmacc_wstream_bw;
  parameter integer NSTK = 4, WORDS = 992, REF_MODE = 1, WINW = 160, LAG = 40, CRED = 32;
  reg clk = 0, rst_n = 0, go = 0;
  always #512 clk = ~clk;
  wire [31:0] a_gray; reg [31:0] c_gray = 0; wire fault;
  wire [31:0] st_cycles, st_rd, st_room, st_gap, st_words;
  ot_hbmacc_qwen_wstream #(.ENABLE(1), .NSTK(NSTK), .REF_MODE(REF_MODE), .WINW(WINW), .CRED(CRED)) dut (
    .clk(clk), .rst_n(rst_n), .go(go), .cfg_words(WORDS), .c_gray(c_gray), .a_gray(a_gray), .fault(fault),
    .st_cycles(st_cycles), .st_rd(st_rd), .st_room_block(st_room), .st_desc_gap(st_gap), .st_words(st_words));
  integer cyc = 0;
  always @(posedge clk) begin
    if (rst_n) cyc <= cyc + 1;
    c_gray <= ((st_words > LAG ? st_words - LAG : 0) ^ ((st_words > LAG ? st_words - LAG : 0) >> 1));
    if (fault) begin $display("FAULT at %0d", cyc); $finish; end
    if (st_words == WORDS) begin
      $display("RESULT nstk=%0d words=%0d ref_mode=%0d cycles=%0d rd=%0d room_block=%0d desc_gap_pc_cycles=%0d bytes=%0d ns=%0d TBps_per_stack=%0.4f",
               NSTK, WORDS, REF_MODE, st_cycles, st_rd, st_room, st_gap, WORDS * 98304, st_cycles * 1024 / 1000,
               (WORDS * 98304.0) / (st_cycles * 1.024e-9) / 1e12 / NSTK);
      $finish;
    end
  end
  initial begin repeat (4) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk); go = 1; end
endmodule
