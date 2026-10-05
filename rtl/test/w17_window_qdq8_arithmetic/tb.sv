`timescale 1ns/1ps
// Prepared only: original QE arithmetic -> original packed producer and guard.
// Expected memories feed assertions exclusively; input memory feeds synchronous xr_q.
module tb;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0,go=0;
 integer cycle=0,which=0,reads=0,captures=0,writes=0,blocks=0,flags=0,global_flags=0,aq_blocks=0;
 reg [31:0] expected_block_cycle[0:15];
 `include "calendar.svh"
 reg [1023:0] inputs[0:15],expected_bf16[0:15];
 reg [255:0] expected_codes[0:15];reg [7:0] expected_scale[0:15];
 reg [1023:0] xr_q=0;
 wire ready,idle,xr_re,vi_re,qr_re,qfault,cap_v,cap_fault;
 wire [29:0] xr_addr,vi_addr,qr_addr,w_addr,cap_addr;
 wire [0:0] w_we;wire [31:0] w_mask;wire [1023:0] w_data;
 wire [255:0] cap_codes;wire [7:0] cap_scale;
 ot_hdc_v41_qe #(.AW(30),.NW(21),.BL(16),.IL(8),.NBMAX(192),.CHUNK8(1),.QLB(272),.MP(1)) qe (
  .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),
  .i_mode(2'd1),.i_fp4(1'b0),.i_unrounded(1'b0),.i_xbase(30'd54720),.i_nb(8'd16),
  .i_nout(21'd0),.i_tiles(21'd0),.i_wbase(30'd0),.i_ind(1'b0),.i_ibase(30'd0),
  .i_istride(30'd0),.i_obase(30'd55232),.i_m(3'd0),.i_xps(30'd0),.i_ops(30'd0),
  .vi_re(vi_re),.vi_addr(vi_addr),.vi_q(32'd0),.xr_re(xr_re),.xr_addr(xr_addr),.xr_q(xr_q),
  .w_we(w_we),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),
  .kvb_v(cap_v),.kvb_src_addr(cap_addr),.kvb_codes(cap_codes),.kvb_scale(cap_scale),.kvb_fault(cap_fault),
  .qr_re(qr_re),.qr_addr(qr_addr),.qr_q(4352'd0),.qr_issue_ready(1'b1),.fault(qfault));
 wire cap_ready,producer_idle,issue_ready,blk_v,pfault;wire [29:0] cap_base,kvt_base,first;
 wire [20:0] abs_row,local_row;wire [3:0] idx;wire [255:0] codes;wire [7:0] scale;
 reg issue=0;reg blk_ready=0;
 reg [9:0] external_user=37,window_user=0;reg [20:0] step_pos=0;
 // Mirrors pinned die host step-start user latch; it is fixture ownership, not whole wrapper qualification.
 always @(posedge clk)if(rst_n&&go)begin window_user<=external_user;step_pos<=21'd1048575;end
 ot_hdc_v41x_window_kv_blocks #(.AW(30),.POS_W(21),.KVT_SH(13),.SEPARATE_ROWS(1)) producer (
  .clk(clk),.rst_n(rst_n),.cap_v(cap_v),.cap_src_addr(cap_addr),.cap_codes(cap_codes),.cap_scale(cap_scale),
  .cap_ready(cap_ready),.cap_src_base(cap_base),.idle(producer_idle),
  .issue(issue),.issue_src_base(30'd55232),.issue_kvt_base(30'd0),.issue_row(21'd127),.issue_abs_row(21'd1048575),
  .issue_ready(issue_ready),.blk_v(blk_v),.blk_ready(blk_ready),.blk_kvt_base(kvt_base),.blk_row(abs_row),
  .blk_kvt_row(local_row),.blk_idx(idx),.blk_first_elem(first),.blk_codes(codes),.blk_scale(scale),.fault(pfault));
 wire [6:0] slot;wire [30:0] expected_first;wire bad;
 ot_chip_v41x_window_block_guard guard (.step_pos(step_pos),.blk_abs_row(abs_row),.blk_kvt_row(local_row),
   .blk_idx(idx),.kvt_base(kvt_base),.first_elem(first),.hbm_slot(slot),.expected_first(expected_first),.bad(bad));
 reg held=0;reg [255:0] held_codes;reg [7:0] held_scale;reg [29:0] held_first;reg [3:0] held_idx;
 initial begin
  if(!$value$plusargs("CASE=%d",which))$fatal(1,"declared CASE required");
  if(which<0||which>2)$fatal(1,"invalid CASE");
  $readmemh("input.mem",inputs);$readmemh("codes.mem",expected_codes);
  $readmemh("block_cycles.mem",expected_block_cycle);
  $readmemh("scale.mem",expected_scale);$readmemh("bf16.mem",expected_bf16);
  repeat(5)@(negedge clk);rst_n=1;go=1;
 end
 always @(negedge clk)if(rst_n)begin
  if(cycle>0)begin go=0;external_user=999;end
  issue=(which!=2&&cycle==ISSUE_SAMPLE);
  blk_ready=(cycle%5!=0);
 end
 always @(posedge clk)if(rst_n)begin
  if(vi_re||qr_re)$fatal(1,"QDQ8 issued index/weight request");
  if(pfault)$fatal(1,"producer fault");
  if(xr_re)begin
   if(cycle!=reads+2||reads>=16||xr_addr!=54720+32*reads)$fatal(1,"read calendar/address");
   xr_q<=inputs[reads];reads=reads+1;
   $display("XR_SAMPLE cycle=%0d block=%0d address=%0d",cycle,reads-1,xr_addr);
  end
  if(qe.u_aq.vo)begin
   if(aq_blocks>=16||cycle!=FIRST_CAPTURE-1+aq_blocks||qe.u_aq.fault!==(which==2))$fatal(1,"AQ calendar/fault");
   if(which!=2&&(qe.u_aq.q!==expected_codes[aq_blocks]||qe.u_aq.e!=integer'(expected_scale[aq_blocks])-127))$fatal(1,"AQ code/exponent");
   aq_blocks=aq_blocks+1;
  end
  if(w_we[0])begin
   if(writes>=16||cycle!=FIRST_CAPTURE+writes||w_addr!=55232+32*writes||w_mask!==32'hffffffff)
    $fatal(1,"VM output cycle/address/mask");
   if(which!=2&&w_data!==expected_bf16[writes])$fatal(1,"BF16 arithmetic block=%0d actual=%h expected=%h",writes,w_data,expected_bf16[writes]);
   if(cap_v!==(which!=2)||cap_fault!==(which==2))$fatal(1,"capture flag alignment");
   $display("VM_SAMPLE cycle=%0d block=%0d address=%0d data=%h",cycle,writes,w_addr,w_data);
   writes=writes+1;
  end
  if(cap_v||cap_fault)begin
   if(cycle!=FIRST_CAPTURE+captures+flags||cap_addr!=55232+32*(captures+flags))$fatal(1,"sideband sample cycle/provenance");
   if(which==2)begin
    if(cap_v||!cap_fault)$fatal(1,"nonfinite fail-closed");flags=flags+1;
   end else begin
    if(!cap_v||cap_fault||!cap_ready||cap_codes!==expected_codes[captures]||cap_scale!==expected_scale[captures])
     $fatal(1,"QDQ8 code/scale/fault block=%0d",captures);
    $display("CAPTURE cycle=%0d block=%0d address=%0d codes=%h scale=%h",cycle,captures,cap_addr,cap_codes,cap_scale);
    captures=captures+1;
   end
  end
  if(qfault)begin
   if(which!=2||cycle!=FIRST_CAPTURE+1+global_flags)$fatal(1,"QE fault edge");global_flags=global_flags+1;
  end
  if(idle&&cycle>0&&cycle<IDLE_SAMPLE)$fatal(1,"QE idle before drain");
  if(cycle==IDLE_SAMPLE&&!idle)$fatal(1,"QE idle late");
  if(issue&&(!issue_ready||captures!=16||cap_base!=55232||!idle))$fatal(1,"issue before full QE drain");
  if(held&&(!blk_v||codes!==held_codes||scale!==held_scale||first!==held_first||idx!==held_idx))$fatal(1,"held block changed");
  held=blk_v&&!blk_ready;
  if(held)begin held_codes=codes;held_scale=scale;held_first=first;held_idx=idx;end
  if(blk_v&&blk_ready)begin
   if(cycle!=expected_block_cycle[blocks]||which==2||idx!=blocks||window_user!=37||bad||slot!=127||abs_row!=1048575||local_row!=127||
     first!=57359+512*blocks||codes!==expected_codes[blocks]||scale!==expected_scale[blocks])$fatal(1,"block arithmetic/provenance");
   $display("BLOCK_ACCEPT cycle=%0d block=%0d first=%0d user=%0d codes=%h scale=%h",cycle,blocks,first,window_user,codes,scale);
   blocks=blocks+1;
  end
  #0.001;
  if(cycle==((which==2)?INVALID_TERMINAL_SAMPLE:HEALTHY_TERMINAL_SAMPLE))begin
   if(aq_blocks!=16||reads!=16||writes!=16||!idle||!ready||!producer_idle||pfault||
      captures!=((which==2)?0:16)||flags!=((which==2)?16:0)||
      global_flags!=((which==2)?16:0)||blocks!=((which==2)?0:16))$fatal(1,"terminal counters/drain");
   $display("QDQ8_ARITHMETIC_PASS case=%0d cycle=%0d reads=%0d VMblocks=%0d captures=%0d blocks=%0d faults=%0d",which,cycle,reads,writes,captures,blocks,flags);
   $finish;
  end
  cycle=cycle+1;
  if(cycle>128)$fatal(1,"bounded arithmetic timeout");
 end
endmodule
