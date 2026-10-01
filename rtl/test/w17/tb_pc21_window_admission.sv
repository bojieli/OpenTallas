`timescale 1ns/1ps
module tb_pc21_window_admission;
  localparam FULL_SHAPE=1, KV_HBM=1, NW=30, MC_A=1;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, cap_v=0, launch=0, blk_ready=0;
  reg [2:0] d_unit=2; reg [1:0] dst=3,a_src=0,me_cls=0;
  reg [29:0] a_base=4096,cap_src_addr=0;
  reg [29:0] su_nout=1,su_nin=512;
  reg kv_ok=0,kvd_v=0;
  reg [255:0] cap_codes=0; reg [7:0] cap_scale=0;
  wire win_idle,win_issue_ready,cap_ready,fault,blk_v;
  wire [29:0] win_cap_src_base,blk_kvt_base,blk_first_elem;
  wire [20:0] blk_row,blk_kvt_row;wire [3:0]blk_idx;
  wire [255:0]blk_codes;wire [7:0]blk_scale;
  `include "actual_admission.svh"
  wire issue=launch && kv_gate && win_su_match && win_issue_ready;
  ot_hdc_v41x_window_kv_blocks #(.SEPARATE_ROWS(1)) writer(
   .clk(clk),.rst_n(rst_n),.cap_v(cap_v),.cap_src_addr(cap_src_addr),.cap_codes(cap_codes),.cap_scale(cap_scale),
   .cap_ready(cap_ready),.cap_src_base(win_cap_src_base),.idle(win_idle),.issue(issue),.issue_src_base(a_base),
   .issue_kvt_base(30'd32768),.issue_row(21'd127),.issue_abs_row(21'd1048575),.issue_ready(win_issue_ready),
   .blk_v(blk_v),.blk_ready(blk_ready),.blk_kvt_base(blk_kvt_base),.blk_row(blk_row),.blk_kvt_row(blk_kvt_row),
   .blk_idx(blk_idx),.blk_first_elem(blk_first_elem),.blk_codes(blk_codes),.blk_scale(blk_scale),.fault(fault));
  task reset_writer; begin rst_n=0;cap_v=0;launch=0;blk_ready=0;repeat(2)@(negedge clk);rst_n=1;@(negedge clk);if(!win_idle||win_issue_ready||blk_v||fault)$fatal(1,"reset did not clear writer");end endtask
  task capture(input integer n); integer k;begin for(k=0;k<n;k=k+1)begin if(!cap_ready)$fatal(1,"capture blocked");cap_v=1;cap_src_addr=4096+k*32;cap_codes={32{8'(k)}};cap_scale=8'(127+k);@(negedge clk);end cap_v=0;end endtask
  integer b;
  initial begin
    reset_writer();capture(8);#1;if(win_admit||kv_gate||win_issue_ready)$fatal(1,"partial capture admitted");reset_writer();
    capture(16);#1;if(win_idle||!win_issue_ready||!win_su_match||!win_admit||!kv_gate)$fatal(1,"PC21 matching FULL producer drain blocked");
    a_base=8192;#1;if(win_su_match||win_admit||kv_gate)$fatal(1,"nonmatching source admitted");a_base=4096;
    su_nin=511;#1;if(win_admit||kv_gate)$fatal(1,"nonmatching shape admitted");su_nin=512;
    d_unit=1;me_cls=MC_A;kv_ok=1;#1;if(win_admit||kv_gate)$fatal(1,"unrelated attention admitted while FULL");d_unit=2;me_cls=0;
    launch=1;@(negedge clk);launch=0;#1;
    if(win_issue_ready||win_admit||kv_gate)$fatal(1,"readyfalse DRAIN readmitted");
    for(b=0;b<16;b=b+1)begin
      if(!blk_v||blk_idx!==4'(b)||blk_codes!=={32{8'(b)}}||blk_scale!==8'(127+b)||blk_row!==21'd1048575||blk_kvt_row!==21'd127||blk_first_elem!==30'(32768+(7<<13)+(b<<9)+15))$fatal(1,"payload/address mismatch block%0d",b);
      repeat(3)@(negedge clk);
      if(blk_idx!==4'(b)||blk_codes!=={32{8'(b)}}||blk_scale!==8'(127+b))$fatal(1,"stalled output changed");
      blk_ready=1;@(negedge clk);blk_ready=0;
    end
    #1;if(!win_idle||blk_v||fault)$fatal(1,"drain incomplete");
    d_unit=1;me_cls=MC_A;kv_ok=0;kvd_v=0;#1;if(kv_gate)$fatal(1,"attention kv_ok guard lost");kv_ok=1;kvd_v=1;#1;if(kv_gate)$fatal(1,"attention descriptor guard lost");kvd_v=0;#1;if(!kv_gate)$fatal(1,"ready attention blocked when empty");
    d_unit=2;me_cls=0;capture(16);reset_writer();capture(16);launch=1;@(negedge clk);launch=0;repeat(3)@(negedge clk);reset_writer();
    $display("PASS PC21 producer/drain exact16blocks stalls reset FILL/FULL/DRAIN nonmatch readyfalse attentionguards");$finish;
  end
endmodule
