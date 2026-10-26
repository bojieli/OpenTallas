`timescale 1ps/1fs
module tb_hbm_svc_prefetch_mapped4_checkpoint;
 parameter integer STACK=0;
 reg stream_clk=0,hbm_clk=0;
 initial forever begin #416.666 stream_clk=1;#416.667 stream_clk=0;end
 initial begin #173;forever #512 hbm_clk=~hbm_clk;end
 reg stream_rst_n=0,hbm_rst_n=0,reserve_v=0,start_v=0;
 reg [19:0] reserve_pcs;reg [14:0] reserve_row_base=20738;
 wire reserve_ready;wire [1:0]block_ready;wire block_ready_v,block_ready_bank;wire[15:0]block_ready_epoch;
 wire out_v,out_bank,out_last,fault;wire[3:0]out_mask;wire[1023:0]out_data;wire[10:0]out_ordinal;wire[15:0]out_epoch;
 wire [31:0]k_v,k_rdy,k_we,k_wr_done,kr_v,kr_rdy;wire[959:0]k_addr;wire[127:0]k_len,kr_beat;wire[543:0]k_tag,kr_tag;wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;
 ot_hbm_svc_prefetch_mapped4_cdc #(.STACK(STACK)) dut(
 .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
 .stream_bank_clk({4{stream_clk}}),.hbm_fifo_clk({8{hbm_clk}}),.hbm_pc_clk({32{hbm_clk}}),
 .reserve_pcs(reserve_pcs),.reserve_row_base(reserve_row_base),.reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(32'(STACK<<30)),.reserve_total(12'd172),.reserve_bank(1'b0),.reserve_epoch(16'd51),
 .block_ready(block_ready),.block_ready_v(block_ready_v),.block_ready_bank(block_ready_bank),.block_ready_epoch(block_ready_epoch),
 .start_v(start_v),.start_bank(1'b0),.start_epoch(16'd51),.out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(fault),
 .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 wire k_oor,w_oor;wire[63:0]refreshes;wire[31:0]w_reads;
 ot_chip_v41x_hbm3e_phy #(.K_AW(30),.KTAGW(17),.K_MEM(65536),.K_BASE(64'h28810000),.CLK_PS(1024)) phy(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
 .w_v(1'b0),.w_rdy(),.w_addr(24'b0),.w_len(6'b0),.w_tag(10'b0),.w_room(),.wr_v(),.wr_rdy(8'b0),.wr_tag(),.wr_beat(),.wr_data(),.k_oor(k_oor),.w_oor(w_oor),.refreshes(refreshes),.w_reads(w_reads));
 reg [9:0]tag_base;integer tag_arg;
 reg formatter_open=0,formatter_read=0;reg[5:0]read_row=0;reg[9:0]read_tag=0;
 wire[1:0]formatter_ready,formatter_owned;wire formatter_busy,formatter_fault;wire[1098:0]packet;
 wire[95:0]indices;wire[63:0]epochs;
 genvar l;generate for(l=0;l<4;l=l+1)begin
  assign indices[l*24+:24]=out_ordinal+l;assign epochs[l*16+:16]=out_epoch;
 end endgenerate
 ot_hbm_svc_static_sm_packed136 #(.PACKED136(1)) formatter(
 .clk(stream_clk),.rst_n(stream_rst_n),.open_v(formatter_open),.open_bank(1'b0),.open_epoch(16'd51),.open_count(7'd40),.open_tag_base(tag_base),
 .sector_v(out_v?out_mask:4'b0),.sector_index(indices),.sector_epoch(epochs),.sector_data(out_data),
 .read_v(formatter_read),.read_bank(1'b0),.read_epoch(16'd51),.read_row(read_row),.read_tag(read_tag),.retire_v(1'b0),.retire_bank(1'b0),.retire_epoch(16'd0),
 .block_ready(formatter_ready),.bank_owned(formatter_owned),.busy(formatter_busy),.fault(formatter_fault),.out_packet(packet));
 reg[255:0]expected[0:171];reg[1087:0]records[0:39];string dir;integer sm,checks=0,sectorchecks=0,requests=0,cycles=0;integer req_sectors=0;
 real begin_at,ready_at;
 function automatic integer pc_of(input integer s);pc_of=((s>>2)^(s>>7)^(s>>12))&31;endfunction
 always @(posedge hbm_clk)if(hbm_rst_n)begin
  if(k_oor||w_oor)$fatal(1,"actual allocation aperture");
  for(integer p=0;p<32;p=p+1)if(k_v[p]&&k_rdy[p])begin
   if(pc_of(k_addr[p*30+:30])!=p||k_we[p])$fatal(1,"mapped checkpoint PHY PC");
   for(integer b=0;b<4;b=b+1)if(b<k_len[p*4+:4]&&pc_of(k_addr[p*30+:30]+b)!=p)$fatal(1,"burst crossed actual PC");
   requests=requests+1;req_sectors=req_sectors+k_len[p*4+:4];
  end
 end
 always @(posedge stream_clk)begin
  cycles=cycles+1;#1;
  if(stream_rst_n&&hbm_rst_n)begin
   if(fault||formatter_fault)$fatal(1,"mapped checkpoint boundary/formatter fault cycle%0d",cycles);
   if(block_ready_v)ready_at=$realtime;
   if(out_v)for(integer l=0;l<4;l=l+1)if(out_mask[l])begin
    if(out_data[l*256+:256]!==expected[out_ordinal+l])$fatal(1,"checkpoint actual sector mismatch ordinal%0d",out_ordinal+l);
    sectorchecks=sectorchecks+1;
   end
   if(packet[1098])begin
    if(packet[1097:1088]!=10'(tag_base+checks)||packet[1087:0]!==records[checks])$fatal(1,"checkpoint scale/weight/tag mismatch row%0d",checks);
    checks=checks+1;
   end
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("SM=%d",sm)||!$value$plusargs("TAGBASE=%d",tag_arg))$fatal(1,"checkpoint directory and SM mandatory");
  tag_base=tag_arg;
  for(integer i=0;i<4;i=i+1)reserve_pcs[i*5+:5]=4*(sm%8)+i;
  $readmemh({dir,"/backing.hex"},phy.u_k.mem);$readmemh({dir,"/sectors.hex"},expected);$readmemh({dir,"/records.hex"},records);
  repeat(4)@(negedge stream_clk);stream_rst_n=1;repeat(3)@(negedge hbm_clk);hbm_rst_n=1;repeat(20)@(negedge stream_clk);
  reserve_v=1;#1;if(!reserve_ready)$fatal(1,"reservation unavailable");begin_at=$realtime;
  @(negedge stream_clk);reserve_v=0;wait(block_ready[0]);
  @(negedge stream_clk);start_v=1;
  @(negedge stream_clk);start_v=0;formatter_open=1;
  @(negedge stream_clk);formatter_open=0;
  wait(formatter_ready[0]);
  @(negedge stream_clk);
  for(integer r=0;r<40;r=r+1)begin formatter_read=1;read_row=r;read_tag=tag_base+r;@(negedge stream_clk);end
  formatter_read=0;repeat(4)@(negedge stream_clk);
  if(checks!=40||sectorchecks!=172||req_sectors!=172)$fatal(1,"actual checkpoint counts");
  $display("MAPPED4_CHECKPOINT PASS sm=%0d stack=%0d exact_records=%0d sectors=%0d PHY_bursts=%0d row_base=20738 cold_prefetch_ps=%0f full_price_qualified=0",sm,STACK,checks,sectorchecks,requests,ready_at-begin_at);$finish;
 end
 initial begin #300000000;$fatal(1,"mapped checkpoint timeout");end
endmodule
