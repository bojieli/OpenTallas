`timescale 1ns/1ps
// Real macro instances for one full HC row:32 data +8 packed-check macros.
// Fixed read latency3 cycles (SRAM1 + SECDED2); writes encode1cycle before
// SRAM capture. Read permission follows all2560 unique sectors COMMITTED.
// SRAM mask convention:1 writes that bit. All transactions retain bank,word,
// beat identity; duplicate/unrequested/out-of-bounds responses poison window.
module ot_hbm_hc_row_operand_epoch #(parameter ENABLE_EPOCH_IDENTITY=0)(
 input wire clk,rst_n,start,release_window,input wire[29:0] hbm_base,
 input wire[15:0]command_lease,output wire[15:0]hq_lease,input wire[15:0]hr_lease,
 output wire ready,output wire hq_v,input wire hq_rdy,
 output wire[29:0]hq_addr,output wire[2:0]hq_len,output wire[9:0]hq_tag,
 input wire hr_v,output wire hr_rdy,input wire[9:0]hr_tag,
 input wire[1:0]hr_beat,input wire[255:0]hr_data,
 input wire[7:0]rom_re,input wire[127:0]rom_addr,
 output wire[8191:0]rom_q,output reg fault,
 output wire[31:0]ce_seen,ue_seen
);
 reg active;reg[15:0]active_lease;assign hq_lease=active_lease;reg[29:0]base;reg[6:0]iw;reg[2:0]ib;
 reg[1023:0]issued;reg[4095:0]seen;reg[11:0]committed;
 reg wr_v;reg[9:0]wr_tag;reg[1:0]wr_beat;
 wire[265:0]encoded;
 wire[9:0]word_index={hr_tag[9:7],hr_tag[6:0]};
 wire[11:0]sector_index=({2'b0,hr_tag}<<2)+hr_beat;
 wire accept=hr_v&&hr_rdy;
 wire bad_rsp=(ENABLE_EPOCH_IDENTITY && hr_lease!=active_lease) || hr_tag[6:0]>=80 || !issued[word_index] || seen[sector_index];
 wire[30:0]end_addr={1'b0,hbm_base}+31'd4096;
 assign hq_v=active&&!fault&&!issued[975];
 // Address reserves128 words/bank, while only80 words are requested.
 assign hq_addr=base+({20'd0,ib,iw}<<2);
 assign hq_len=3'd4;assign hq_tag={ib,iw};
 assign hr_rdy=active&&!fault;
 assign ready=active&&!fault&&(committed==2560)&&!wr_v;
 wire[31:0]ce,ue;
 assign ce_seen=ce;assign ue_seen=ue;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;active_lease<=0;fault<=0;issued<=0;seen<=0;committed<=0;wr_v<=0;ib<=0;iw<=0;end
  else begin
   wr_v<=accept&&!bad_rsp;
   if(accept)begin
    if(bad_rsp)fault<=1;
    else begin seen[sector_index]<=1;wr_tag<=hr_tag;wr_beat<=hr_beat;end
   end
   if(wr_v)committed<=committed+1'b1;
   if(start)begin
    if(active || end_addr[30])fault<=1;
    else begin active<=1;active_lease<=command_lease;base<=hbm_base;issued<=0;seen<=0;committed<=0;ib<=0;iw<=0;end
   end
   if(hq_v&&hq_rdy)begin
    issued[{ib,iw}]<=1;
    if(iw==79)begin iw<=0;ib<=ib+1'b1;end else iw<=iw+1'b1;
   end
   if(release_window)begin if(!ready)fault<=1;else active<=0;end
   if(|ue)fault<=1;
   for(integer k=0;k<8;k=k+1)
    if(rom_re[k]&&(!ready || rom_addr[k*16+:16]>=80))fault<=1;
  end
 end
 ot_secded_enc #(.K(256),.R(10)) enc(.clk(clk),.d(hr_data),.q(encoded));
 genvar b,s;generate for(b=0;b<8;b=b+1)begin:bank
  wire[255:0]checks;wire we=wr_v&&(wr_tag[9:7]==b);
  wire[255:0]check_d=({246'd0,encoded[265:256]}<<(wr_beat*10));
  wire[255:0]check_mask=({246'd0,10'h3ff}<<(wr_beat*10));
  wire[6:0]ra=rom_addr[b*16+:7];reg rv;
  always @(posedge clk or negedge rst_n)if(!rst_n)rv<=0;else rv<=rom_re[b]&&ready;
  ot_sram_1r1w_128x256_m1_r2c2 ck(.clk(clk),.r_ce_in(rom_re[b]&&ready),.r_addr_in(ra),.rd_out(checks),
   .w_ce_in(we),.w_addr_in(wr_tag[6:0]),.wd_in(check_d),.w_mask_in(check_mask),
   .rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(16'd0));
  for(s=0;s<4;s=s+1)begin:sector
   wire[255:0]d,q;wire ov;
   ot_sram_1r1w_128x256_m1_r2c2 ram(.clk(clk),.r_ce_in(rom_re[b]&&ready),.r_addr_in(ra),.rd_out(d),
    .w_ce_in(we&&(wr_beat==s)),.w_addr_in(wr_tag[6:0]),.wd_in(encoded[255:0]),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(12'd0),.cr_en(2'b0),.cr_sel(16'd0));
   ot_secded_dec #(.K(256),.R(10)) dec(.clk(clk),.rst_n(rst_n),.v(rv),.w({checks[s*10+:10],d}),
    .ov(ov),.d(q),.ce(ce[b*4+s]),.ue(ue[b*4+s]),.n_ce(),.n_ue());
   assign rom_q[(b*4+s)*256+:256]=ue[b*4+s]?256'd0:q;
  end
 end endgenerate
endmodule
