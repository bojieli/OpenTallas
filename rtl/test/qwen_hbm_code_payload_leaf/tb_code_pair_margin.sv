`timescale 1ps/1fs
// Exact gate for ot_qwen_hbm_code_pair_margin against the unchanged
// ot_qwen_hbm_code_pair_context (bank-local leaf + fixed II1 read pipeline).
// Both receive identical random legal traffic. Same-cycle handshake outputs
// must be identical; rom_rd/rsp_v/rd_corrected/rd_uncorrectable of the margin
// top must equal the original's exactly LAT_DELTA cycles earlier.
// Then: single-bit SRAM corruption (both DUTs) must stay equivalent;
// double-bit corruption (+NEG_UE) or a duplicated-request mismatch (+NEG_DMR)
// must never deliver the response valid and must raise the sticky fault.
module tb_code_pair_margin #(parameter integer M2=0);
  import ot_hbm_r14_pkg::*;
  localparam integer LAT_DELTA=(M2>=2?11:(M2?9:6)), ROWS=4496;
  reg clk=0, por_n=0;
  always #416.6665 clk=~clk;
  reg wr_v=0, wr_span_bound=0, wr_kind=0, visible_r=0;
  reg [12:0] wr_row=0; reg [11:0] wr_column=0;
  owned_t wr_owned;
  reg [1:0] rd_v=0, rd_span_bound=0, rd_published=0;
  reg [25:0] rd_row=0;
  reg [5:0] virtual_bank=0;
  // M2 (registered credits): the original is driven with the margin's ACCEPTED transactions at the same pin cycle
  // (transaction-level exactness); results/receipts are compared as ordered streams, latency may differ.
  wire m_wr_r; wire [1:0] m_rd_r;
  wire fmt_ok=!wr_kind && (wr_column<2) && (wr_row<ROWS);
  wire wr_v_o = M2 ? (wr_v && m_wr_r && wr_span_bound && fmt_ok) : wr_v;
  wire wr_span_o = M2 ? 1'b1 : wr_span_bound;
  wire visible_r_o = M2 ? 1'b1 : visible_r;
  wire [1:0] rd_v_o, rd_span_o, rd_pub_o;
  for(genvar gp=0;gp<2;gp=gp+1) begin : rdo
    assign rd_v_o[gp] = M2 ? (rd_v[gp] && rd_span_bound[gp] && rd_published[gp] && m_rd_r[gp] && (rd_row[gp*13+:13]<ROWS)) : rd_v[gp];
    assign rd_span_o[gp] = M2 ? 1'b1 : rd_span_bound[gp];
    assign rd_pub_o[gp] = M2 ? 1'b1 : rd_published[gp];
  end
  // original
  wire o_wr_r, o_visible_v, o_fault; identity_t o_id;
  wire [11:0] o_tag, o_col; wire [4:0] o_beat; wire [12:0] o_row;
  wire [1:0] o_rd_r, o_rsp_v, o_corr, o_unc; wire [2659:0] o_rom;
  ot_qwen_hbm_code_pair_context #(.ENABLE(1),.COLUMN_BASE(0),.ROWS(ROWS)) dut_o(
    .clk(clk),.por_n(por_n),.wr_v(wr_v_o),.wr_r(o_wr_r),.wr_owned(wr_owned),.wr_span_bound(wr_span_o),
    .wr_kind(wr_kind),.wr_row(wr_row),.wr_column(wr_column),.visible_v(o_visible_v),.visible_r(visible_r_o),
    .visible_id(o_id),.visible_tag(o_tag),.visible_beat(o_beat),.visible_row(o_row),.visible_column(o_col),
    .rd_v(rd_v_o),.rd_span_bound(rd_span_o),.rd_published(rd_pub_o),.rd_row(rd_row),.rd_r(o_rd_r),
    .rsp_v(o_rsp_v),.virtual_bank(virtual_bank),.rom_rd(o_rom),.rd_corrected(o_corr),
    .rd_uncorrectable(o_unc),.fault(o_fault));
  // margin
  wire m_visible_v, m_fault; identity_t m_id;
  wire [11:0] m_tag, m_col; wire [4:0] m_beat; wire [12:0] m_row;
  wire [1:0] m_rsp_v, m_corr, m_unc; wire [2659:0] m_rom;
  ot_qwen_hbm_code_pair_margin #(.ENABLE(1),.COLUMN_BASE(0),.ROWS(ROWS),.MARGIN2(M2)) dut_m(
    .clk(clk),.por_n(por_n),.wr_v(wr_v),.wr_r(m_wr_r),.wr_owned(wr_owned),.wr_span_bound(wr_span_bound),
    .wr_kind(wr_kind),.wr_row(wr_row),.wr_column(wr_column),.visible_v(m_visible_v),.visible_r(visible_r),
    .visible_id(m_id),.visible_tag(m_tag),.visible_beat(m_beat),.visible_row(m_row),.visible_column(m_col),
    .rd_v(rd_v),.rd_span_bound(rd_span_bound),.rd_published(rd_published),.rd_row(rd_row),.rd_r(m_rd_r),
    .rsp_v(m_rsp_v),.virtual_bank(virtual_bank),.rom_rd(m_rom),.rd_corrected(m_corr),
    .rd_uncorrectable(m_unc),.fault(m_fault));
  // default-off margin top drives nothing
  wire [2659:0] off_rom; wire [1:0] off_rsp, off_rd_r; wire off_wr_r, off_fault, off_vis;
  ot_qwen_hbm_code_pair_margin #(.ENABLE(0)) dut_off(
    .clk(clk),.por_n(por_n),.wr_v(wr_v),.wr_r(off_wr_r),.wr_owned(wr_owned),.wr_span_bound(wr_span_bound),
    .wr_kind(wr_kind),.wr_row(wr_row),.wr_column(wr_column),.visible_v(off_vis),.visible_r(visible_r),
    .visible_id(),.visible_tag(),.visible_beat(),.visible_row(),.visible_column(),
    .rd_v(rd_v),.rd_span_bound(rd_span_bound),.rd_published(rd_published),.rd_row(rd_row),.rd_r(off_rd_r),
    .rsp_v(off_rsp),.virtual_bank(virtual_bank),.rom_rd(off_rom),.rd_corrected(),.rd_uncorrectable(),.fault(off_fault));

  reg [2659:0] h_rom [0:LAT_DELTA];
  reg [1:0] h_rsp [0:LAT_DELTA], h_corr [0:LAT_DELTA], h_unc [0:LAT_DELTA];
  integer cyc=0, compared=0, valid_rsp=0, corrected_seen=0, handshake_checks=0;
  integer rows [0:39]; integer nrows=0;
  reg compare_on=0;
  reg [$bits(identity_t)+12+5+13+12-1:0] rq [0:255]; integer rq_w=0, rq_r=0, rcpt=0; reg m_wr_r_d=0;
  // Compare inside the cycle, after the negedge-driven inputs settle.
  always @(negedge clk) begin
    #300;
    if(off_rom!==0 || off_rsp!==0 || off_rd_r!==0 || off_wr_r!==0 || off_fault!==0 || off_vis!==0)
      $fatal(1,"default-off margin top drives activity");
    if(compare_on) begin
      if(o_fault!==0 || m_fault!==0) $fatal(1,"fault in fault-free phase cyc%0d o%b m%b",cyc,o_fault,m_fault);
      if(!M2) begin
      if(o_rd_r!==m_rd_r || o_wr_r!==m_wr_r || o_visible_v!==m_visible_v)
        $fatal(1,"handshake mismatch cyc%0d rd_r %b/%b wr_r %b/%b vis %b/%b",cyc,o_rd_r,m_rd_r,o_wr_r,m_wr_r,o_visible_v,m_visible_v);
      if(o_visible_v && (o_id!==m_id || o_tag!==m_tag || o_beat!==m_beat || o_row!==m_row || o_col!==m_col))
        $fatal(1,"visible receipt mismatch cyc%0d",cyc);
      end else begin
        // receipts: ordered stream compare (original delivers every write at once; margin on its own credits)
        if(o_visible_v) begin rq[rq_w%256]={o_id,o_tag,o_beat,o_row,o_col}; rq_w=rq_w+1; end
        if(m_visible_v && visible_r) begin
          if(rq_r>=rq_w) $fatal(1,"receipt delivered with none outstanding cyc%0d",cyc);
          if(rq[rq_r%256]!=={m_id,m_tag,m_beat,m_row,m_col}) $fatal(1,"receipt content/order mismatch cyc%0d",cyc);
          rq_r=rq_r+1; rcpt=rcpt+1;
        end
        if(cyc>2 && m_rd_r!==2'b11) $fatal(1,"rd_r credit low in fault-free phase cyc%0d",cyc);
      end
      handshake_checks=handshake_checks+1;
    end
    for(integer k=LAT_DELTA;k>0;k=k-1) begin
      h_rom[k]=h_rom[k-1]; h_rsp[k]=h_rsp[k-1]; h_corr[k]=h_corr[k-1]; h_unc[k]=h_unc[k-1];
    end
    h_rom[0]=o_rom; h_rsp[0]=o_rsp_v; h_corr[0]=o_corr; h_unc[0]=o_unc;
    if(compare_on && cyc>=LAT_DELTA) begin
      if(m_rom!==h_rom[LAT_DELTA] || m_rsp_v!==h_rsp[LAT_DELTA] ||
         m_corr!==h_corr[LAT_DELTA] || m_unc!==h_unc[LAT_DELTA])
        $fatal(1,"delayed response mismatch cyc%0d rsp m%b o%b corr m%b o%b",cyc,m_rsp_v,h_rsp[LAT_DELTA],m_corr,h_corr[LAT_DELTA]);
      compared=compared+1;
      if(m_rsp_v!=0) valid_rsp=valid_rsp+1;
      if(m_corr!=0) corrected_seen=corrected_seen+1;
    end
    cyc=cyc+1;
  end
  function automatic [255:0] rnd256();
    for(integer i=0;i<8;i=i+1) rnd256[i*32+:32]=$urandom;
  endfunction
  task idle(input integer k); begin
    for(integer i=0;i<k;i=i+1) begin @(negedge clk); rd_v=0; wr_v=0; end
  end endtask
  task write_row(input integer row, input integer col, input [255:0] data); begin
    @(negedge clk); rd_v=0; wr_v=1; wr_span_bound=1; wr_row=row; wr_column=col;
    wr_owned.data=data; wr_owned.physical_tag=$urandom; wr_owned.beat=$urandom;
    wr_owned.id.sector=$urandom; visible_r=1;
    if(M2) begin
      #100; while(!m_wr_r) begin @(negedge clk); #100; end
    end else begin
      @(posedge clk); while(!o_wr_r) @(posedge clk);
    end
    @(negedge clk); wr_v=0;
  end endtask
  task read_one(input integer col, input integer row, input integer vb); begin
    @(negedge clk); wr_v=0; rd_v=2'(1<<col); rd_row=0; rd_row[col*13+:13]=row;
    virtual_bank=0; virtual_bank[col*3+:3]=vb;
    @(negedge clk); rd_v=0;
  end endtask
  // Margin read response for (col) over the next window; returns whether any valid was seen.
  integer seed;
  reg neg_ue, neg_dmr, neg_meta;
  integer saw_valid, saw_unc;
  initial begin
    if(!$value$plusargs("seed=%d",seed)) seed=1;
    void'($urandom(seed));
    neg_ue=$test$plusargs("NEG_UE"); neg_dmr=$test$plusargs("NEG_DMR"); neg_meta=$test$plusargs("NEG_META");
    wr_owned='0;
    for(integer k=0;k<=LAT_DELTA;k=k+1) begin h_rom[k]=0;h_rsp[k]=0;h_corr[k]=0;h_unc[k]=0; end
    for(integer b=0;b<5;b=b+1) begin
      rows[nrows]=b*1024; rows[nrows+1]=b*1024+1; rows[nrows+2]=b*1024+7; rows[nrows+3]=b*1024+8;
      rows[nrows+4]=b*1024+9; rows[nrows+5]=b*1024+15; rows[nrows+6]=b*1024+16;
      rows[nrows+7]=(b<4)?b*1024+1023:4495;
      nrows=nrows+8;
    end
    repeat(3) @(negedge clk); por_n=1; rd_span_bound=3; rd_published=3; wr_span_bound=1;
    compare_on=1; cyc=0;
    // Phase 1: populate every chosen row in both columns.
    for(integer i=0;i<nrows;i=i+1) for(integer c=0;c<2;c=c+1) write_row(rows[i],c,rnd256());
    $display("WRITE_RATE m2=%0d writes=%0d cycles=%0d", M2, nrows*2, cyc);
    // Phase 1b: back-to-back write burst, consumer always ready (original: one accept per cycle)
    begin : burst
      integer acc; acc=0;
      @(negedge clk); wr_v=1; wr_span_bound=1; wr_kind=0; visible_r=1;
      for(integer i=0;i<64;i=i+1) begin
        wr_row=rows[i%nrows]; wr_column=i%2; wr_owned.data=rnd256(); wr_owned.physical_tag=$urandom; wr_owned.beat=$urandom;
        wr_owned.id.sector=$urandom;
        #100; if(M2 ? m_wr_r : o_wr_r) acc=acc+1;
        @(negedge clk);
      end
      wr_v=0; idle(14);
      $display("BURST_RATE m2=%0d accepted=%0d of 64", M2, acc);
      if(acc<63) $fatal(1,"write burst rate %0d/64 below the original's back-to-back rate", acc);
    end
    // Phase 2: random mixed traffic, back-to-back II1 reads on both ports,
    // same-edge read/write, bubbles, denied reads, held receipts.
    for(integer t=0;t<6000;t=t+1) begin
      @(negedge clk);
      for(integer p=0;p<2;p=p+1) begin
        rd_v[p]=($urandom%10)<7;
        rd_row[p*13+:13]=rows[$urandom%nrows];
        virtual_bank[p*3+:3]=$urandom%5;
        rd_span_bound[p]=($urandom%40)!=0;
        rd_published[p]=($urandom%40)!=0;
      end
      wr_v=($urandom%10)<3; wr_span_bound=($urandom%30)!=0;
      wr_row=rows[$urandom%nrows]; wr_column=$urandom%2; wr_owned.data=rnd256();
      wr_owned.physical_tag=$urandom; wr_owned.beat=$urandom; wr_owned.id.sector=$urandom;
      wr_owned.id.producer={$urandom,$urandom};
      visible_r=($urandom%10)<7;
    end
    @(negedge clk); rd_v=0; wr_v=0; rd_span_bound=3; rd_published=3; wr_span_bound=1; visible_r=1;
    idle(10);
    // Phase 3: identical single-bit SRAM corruption in both DUTs, then reads.
    begin : single_bit
      reg [255:0] a;
      for(integer j=0;j<24;j=j+1) begin
        integer col, b, row, bit_i;
        a=rnd256(); col=j%2; b=j%5; row=b*1024+7; bit_i=(j*41+(j/6)*7)%256;
        write_row(row,col,a); idle(M2>=2?22:(M2?14:8));
        case(col*5+b)
          0: begin dut_o.u_leaf.on.column[0].bank[0].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[0].bank[0].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          1: begin dut_o.u_leaf.on.column[0].bank[1].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[0].bank[1].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          2: begin dut_o.u_leaf.on.column[0].bank[2].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[0].bank[2].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          3: begin dut_o.u_leaf.on.column[0].bank[3].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[0].bank[3].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          4: begin dut_o.u_leaf.on.column[0].bank[4].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[0].bank[4].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          5: begin dut_o.u_leaf.on.column[1].bank[0].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[1].bank[0].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          6: begin dut_o.u_leaf.on.column[1].bank[1].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[1].bank[1].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          7: begin dut_o.u_leaf.on.column[1].bank[2].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[1].bank[2].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          8: begin dut_o.u_leaf.on.column[1].bank[3].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[1].bank[3].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          9: begin dut_o.u_leaf.on.column[1].bank[4].data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}});
                   dut_m.on.column[1].bank[4].u_bank.data_store.word_write(7,a^(256'b1<<bit_i),{256{1'b1}}); end
          default: $fatal(1,"bad injection target");
        endcase
        read_one(col,row,j%5); idle(LAT_DELTA+6);
      end
    end
    if(corrected_seen<24) $fatal(1,"single-bit corrections not observed (%0d)",corrected_seen);
    if(M2 && rcpt<200) $fatal(1,"too few receipts compared (%0d)",rcpt);
    if(valid_rsp<1000) $fatal(1,"too few valid responses compared (%0d)",valid_rsp);
    // Phase 4 (optional negatives; fault is sticky, so each is its own run).
    if(neg_meta) begin : negmeta
      // flip ONE copy of the visible receipt metadata while it is held (consumer not ready): fault must be raised
      compare_on=0;
      @(negedge clk); visible_r=0; wr_v=0; rd_v=0;
      @(negedge clk); wr_v=1; wr_span_bound=1; wr_row=1*1024+3; wr_column=0; wr_owned.data=rnd256(); wr_owned.physical_tag=$urandom; wr_owned.beat=$urandom; wr_owned.id.sector=$urandom;
      #100; while(!m_wr_r) begin @(negedge clk); #100; end
      @(negedge clk); wr_v=0; visible_r=0;
      repeat(30) @(negedge clk);
      if(!m_visible_v) $fatal(1,"NEGATIVE: no receipt held");
      dut_m.on.vq_meta_b[7]=~dut_m.on.vq_meta_b[7];
      repeat(6) @(negedge clk);
      if(!m_fault) $fatal(1,"NEGATIVE: receipt copy mismatch not detected");
      $display("PASS_CODE_PAIR_MARGIN_NEGATIVE kind=META fault=1");
      $finish;
    end
    if(neg_ue || neg_dmr) begin
      reg [255:0] a;
      compare_on=0;
      a=rnd256(); write_row(3*1024+9,1,a); idle(M2>=2?22:(M2?14:8));
      if(neg_ue) begin
        dut_m.on.column[1].bank[3].u_bank.data_store.word_write(9,a^256'b11,{256{1'b1}});
        dut_o.u_leaf.on.column[1].bank[3].data_store.word_write(9,a^256'b11,{256{1'b1}});
        read_one(1,3*1024+9,2);
      end else begin
        @(negedge clk); wr_v=0; rd_v=2'b10; rd_row=0; rd_row[25:13]=3*1024+9; virtual_bank=6'(2<<3);
        repeat(M2>=2?3:(M2?2:1)) @(posedge clk); #1 dut_m.on.u_req_b.q[1]=1'b0;   // upset ONE copy (the kept shadow) of the registered request
        @(negedge clk); rd_v=0;
      end
      saw_valid=0; saw_unc=0;
      for(integer i=0;i<24;i=i+1) begin
        @(negedge clk); #300;
        if(m_rsp_v!=0) saw_valid=1;
        if(m_unc!=0) saw_unc=1;
      end
      if(saw_valid) $fatal(1,"NEGATIVE: corrupted response delivered valid");
      if(!m_fault) $fatal(1,"NEGATIVE: sticky fault not raised");
      if(m_rd_r!=0 || m_wr_r!=0) $fatal(1,"NEGATIVE: acceptance after fault");
      if(neg_ue && (!saw_unc || !o_fault)) $fatal(1,"NEGATIVE: uncorrectable not reported (m%0d o%0d)",saw_unc,o_fault);
      $display("PASS_CODE_PAIR_MARGIN_NEGATIVE kind=%s fault=1 delivered_valid=0", neg_ue ? "UE" : "DMR");
    end
    $display("PASS_CODE_PAIR_MARGIN_EXACT m2=%0d receipts=%0d seed=%0d lat_delta=%0d compared_cycles=%0d valid_responses=%0d corrected=%0d handshake_checks=%0d rows=%0d",
             M2, rcpt, seed, LAT_DELTA, compared, valid_rsp, corrected_seen, handshake_checks, ROWS);
    $finish;
  end
endmodule
