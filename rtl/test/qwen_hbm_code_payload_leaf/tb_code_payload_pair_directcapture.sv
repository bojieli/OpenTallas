`timescale 1ps/1fs
module tb_code_payload_pair_directcapture;
  import ot_hbm_r14_pkg::*;
  reg clk=0,por_n=0;
  always #416.6665 clk=~clk;
  reg wr_v=0,wr_span_bound=0,wr_kind=0,visible_r=0;
  reg [12:0] wr_row=0;reg[11:0] wr_column=0;
  owned_t wr_owned;
  wire wr_r,visible_v,fault;
  identity_t visible_id;
  wire[11:0] visible_tag,visible_column;wire[4:0] visible_beat;wire[12:0] visible_row;
  reg[1:0] rd_v=0,rd_span_bound=0,rd_published=0;
  reg[25:0] rd_row=0;
  wire[1:0] rd_r,rd_rsp_v,rd_corrected,rd_uncorrectable;
  wire[511:0] rd_data;
  ot_qwen_hbm_code_payload_pair_directcapture #(.ENABLE(1)) dut(.*);
  wire off_ready,off_visible,off_fault;wire[1:0] off_rsp;wire[511:0] off_data;
  ot_qwen_hbm_code_payload_pair_directcapture off(.clk(clk),.por_n(por_n),.wr_v(wr_v),.wr_r(off_ready),
    .wr_owned(wr_owned),.wr_span_bound(wr_span_bound),.wr_kind(wr_kind),.wr_row(wr_row),.wr_column(wr_column),
    .visible_v(off_visible),.visible_r(visible_r),.visible_id(),.visible_tag(),.visible_beat(),.visible_row(),.visible_column(),
    .rd_v(rd_v),.rd_span_bound(rd_span_bound),.rd_published(rd_published),.rd_row(rd_row),.rd_r(),.rd_rsp_v(off_rsp),
    .rd_data(off_data),.rd_corrected(),.rd_uncorrectable(),.fault(off_fault));
  integer checks=0;
  task step;begin @(posedge clk);#1;checks=checks+1;
    if(off_ready||off_visible||off_fault||off_rsp||off_data)$fatal(1,"default off drives activity");end endtask
  task offer(input integer row,input integer col,input[255:0] data);
    begin @(negedge clk);wr_v=1;wr_row=row;wr_column=col;wr_owned.data=data;
      wr_owned.id.producer=64'h105017;wr_owned.id.transport=32'h709;
      wr_owned.id.stack=2'd3;wr_owned.id.sector=34'h123456;
      wr_owned.physical_tag=12'h39a;wr_owned.beat=5'd7;
    end
  endtask
  task finish_write;
    begin step;if(!visible_v || visible_id!=wr_owned.id || visible_tag!=12'h39a ||
      visible_beat!=7 || visible_row!=wr_row || visible_column!=wr_column)$fatal(1,"joint write receipt identity");
      @(negedge clk);wr_v=0;visible_r=1;step;@(negedge clk);visible_r=0;end
  endtask
  task read_check(input integer row,input integer col,input[255:0] expected,input integer corrected);
    begin @(negedge clk);rd_row[col*13+:13]=row;rd_v=2'(1<<col);
      step;if(rd_rsp_v[col])$fatal(1,"read response bypassed priced capture");
      @(negedge clk);rd_v=0;step;
      if(!rd_rsp_v[col] || rd_data[col*256+:256]!=expected || rd_corrected[col]!=corrected || rd_uncorrectable[col] || fault)
        $fatal(1,"read/ECC mismatch row%0d col%0d",row,col);
      step;if(rd_rsp_v[col])$fatal(1,"read valid held after pulse");end
  endtask
  reg[255:0] a,b;
  initial begin
    wr_owned='0;a=256'hfedcba98765432100123456789abcdef5a5a55aa0f0ff0f0123456789abcdef0;
    b=~a;
    step;step;@(negedge clk);por_n=1;
    offer(7,0,a);step;step;
    if(wr_r||visible_v||fault)$fatal(1,"unbound span wrote");
    @(negedge clk);wr_span_bound=1;finish_write;
    // Without parent publication authorization the initialized macro is unreadable.
    @(negedge clk);rd_v=1;rd_row[12:0]=7;rd_span_bound=3;step;
    if(rd_r||rd_rsp_v)$fatal(1,"unpublished read admitted");
    @(negedge clk);rd_v=0;rd_published=3;
    read_check(7,0,a,0);
    offer(8,1,b);step;
    if(!visible_v)$fatal(1,"accepted write not visible");
    // Hold the write receipt while a following sector remains offered; no overwrite.
    offer(8,1,a);step;step;if(wr_r)$fatal(1,"held receipt lost backpressure");
    read_check(8,1,b,0);
    @(negedge clk);visible_r=1;finish_write;
    read_check(8,1,a,0);
    // Same-edge read and rewrite must capture the old data AND old packed checks.
    offer(7,0,b);@(negedge clk);rd_row[12:0]=7;rd_v=1;
    step; // write happened on preceding offer edge; replace with a for the simultaneous edge below
    @(negedge clk);wr_v=0;rd_v=0;visible_r=1;step;
    @(negedge clk);visible_r=0;
    offer(7,0,a);rd_row[12:0]=7;rd_v=1;step;
    @(negedge clk);wr_v=0;rd_v=0;visible_r=1;step;
    if(!rd_rsp_v[0]||rd_data[255:0]!=b)$fatal(1,"same edge was not old before write");
    @(negedge clk);visible_r=0;step;
    read_check(7,0,a,0);
    offer(1023,0,b);finish_write;read_check(1023,0,b,0);
    offer(1024,1,a);finish_write;read_check(1024,1,a,0);
    offer(4495,1,b);finish_write;read_check(4495,1,b,0);
    // Changed-source check: different physical banks/check slots in each
    // column, a bank switch EVERY edge, and bubbles. Reuse real SRAM writes.
    for(integer bank=0;bank<5;bank=bank+1) begin
      offer(bank*1024+bank,0,a ^ 256'(bank));finish_write;
      offer(bank*1024+7-bank,1,b ^ 256'(bank));finish_write;
    end
    for(integer cycle=0;cycle<7;cycle=cycle+1) begin
      @(negedge clk);
      if(cycle<5) begin
        rd_v=3;
        rd_row[12:0]=13'(cycle*1024+cycle);
        rd_row[25:13]=13'((4-cycle)*1024+7-(4-cycle));
      end else rd_v=0;
      step;
      if(cycle==0 || cycle==6) begin
        if(rd_rsp_v!==0) $fatal(1,"banklocal unexpected bubble response");
      end else begin
        if(rd_rsp_v!==3 || rd_data[255:0]!=(a ^ 256'(cycle-1)) ||
           rd_data[511:256]!=(b ^ 256'(5-cycle)) || fault)
          $fatal(1,"banklocal II1 bank/checkslot/column alignment cycle%0d",cycle);
      end
    end
    // Restore row7 before the unchanged ECC fault tests below.
    offer(7,0,a);finish_write;
    // Existing SRAM model corruption; existing W6 decoder must correct one data bit.
    @(negedge clk);dut.on.column[0].bank[0].data_store.word_write(7,a^256'b1,{256{1'b1}});
    read_check(7,0,a,1);
    // Two-bit error is a visible fault, never an exact-data/publication success.
    @(negedge clk);dut.on.column[0].bank[0].data_store.word_write(7,a^256'b11,{256{1'b1}});
    rd_row[12:0]=7;rd_v=1;step;@(negedge clk);rd_v=0;step;
    if(!rd_uncorrectable[0]||!fault||rd_rsp_v[0]||wr_r)$fatal(1,"uncorrectable read admitted");
    step;if(!fault)$fatal(1,"fault not retained");
    $display("PASS_CODE_PAYLOAD_PAIR_DIRECTCAPTURE checks=%0d actual_joint_SRAM_capture=1 old_read=1 corrected=1 uncorrectable_quarantine=1 rows=4496 defaultoff=1",checks);
    $finish;
  end
endmodule
