`timescale 1ps/1fs
`default_nettype none
// Actual memory roundtrip: no preload, replacement response data, or synthetic
// write completions. The authoritative HBM controller owns mutable backing RAM.
module tb_hbm_svc_block_roundtrip;
 reg stream_clk=0,hbm_clk=0;
 initial forever begin #416.666 stream_clk=1;#416.667 stream_clk=0;end
 initial begin #173;forever #512 hbm_clk=~hbm_clk;end
 reg stream_rst_n=0,hbm_rst_n=0;
 localparam integer BASE=4099,TOTAL=640;
 reg wb_reserve_v=0,wb_fill_start=0;reg [2311:0] wd=0;
 wire wb_reserve_ready,wb_fill_done,wb_done_v,wb_done_bank,wb_fault;
 wire [15:0] wb_done_epoch;wire [11:0] wb_done_sectors;wire [1:0] wb_bank_owned;
 wire [31:0] wb_k_v,wb_k_rdy,wb_k_we;wire [959:0] wb_k_addr;
 wire [127:0] wb_k_len;wire [543:0] wb_k_tag;wire [8191:0] wb_k_data;wire [1023:0] wb_k_strb;
 ot_hbm_svc_wb_block_cdc u_wb(
 .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
 .reserve_v(wb_reserve_v),.reserve_ready(wb_reserve_ready),.reserve_bank(1'b0),.reserve_epoch(16'd41),.reserve_base(32'(BASE)),.reserve_total(12'(TOTAL)),
 .fill_start(wb_fill_start),.fill_start_bank(1'b0),.fill_start_epoch(16'd41),.wd(wd),
 .fill_done(wb_fill_done),.done_v(wb_done_v),.done_bank(wb_done_bank),.done_epoch(wb_done_epoch),.done_sectors(wb_done_sectors),.bank_owned(wb_bank_owned),.fault(wb_fault),
 .k_v(wb_k_v),.k_rdy(wb_k_rdy),.k_addr(wb_k_addr),.k_len(wb_k_len),.k_tag(wb_k_tag),.k_we(wb_k_we),.k_wdata(wb_k_data),.k_wstrb(wb_k_strb),.k_wr_done(k_wr_done));
 reg pf_reserve_v=0,pf_start_v=0;
 wire pf_reserve_ready,pf_ready_v,pf_ready_bank,pf_out_v,pf_out_bank,pf_out_last,pf_fault;
 wire [15:0] pf_ready_epoch,pf_out_epoch;wire [1:0] pf_ready;
 wire [7:0] pf_out_mask;wire [10:0] pf_out_ordinal;wire [2047:0] pf_out_data;
 wire [31:0] pf_k_v,pf_k_rdy,pf_k_we;wire [959:0] pf_k_addr;
 wire [127:0] pf_k_len;wire [543:0] pf_k_tag;wire [8191:0] pf_k_data;wire [1023:0] pf_k_strb;
 ot_hbm_svc_prefetch_block_cdc u_pf(
 .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
 .reserve_v(pf_reserve_v),.reserve_ready(pf_reserve_ready),.reserve_base(32'(BASE)),.reserve_total(12'(TOTAL)),.reserve_bank(1'b1),.reserve_epoch(16'd42),
 .block_ready(pf_ready),.block_ready_v(pf_ready_v),.block_ready_bank(pf_ready_bank),.block_ready_epoch(pf_ready_epoch),
 .start_v(pf_start_v),.start_bank(1'b1),.start_epoch(16'd42),
 .out_v(pf_out_v),.out_mask(pf_out_mask),.out_data(pf_out_data),.out_ordinal(pf_out_ordinal),.out_bank(pf_out_bank),.out_epoch(pf_out_epoch),.out_last(pf_out_last),.fault(pf_fault),
 .k_v(pf_k_v),.k_rdy(pf_k_rdy),.k_addr(pf_k_addr),.k_len(pf_k_len),.k_tag(pf_k_tag),.k_we(pf_k_we),.k_wdata(pf_k_data),.k_wstrb(pf_k_strb),.k_wr_done(32'd0),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 wire [31:0] k_v,k_rdy,k_we,k_wr_done,kr_v,kr_rdy;
 wire [959:0] k_addr;wire [127:0] k_len,kr_beat;wire [543:0] k_tag,kr_tag;
 wire [8191:0] k_wdata,kr_data;wire [1023:0] k_wstrb;
 ot_hbm_svc_phy_mux u_mux(
 .hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
 .rd_v(pf_k_v),.rd_rdy(pf_k_rdy),.rd_addr(pf_k_addr),.rd_len(pf_k_len),.rd_tag(pf_k_tag),
 .wb_v(wb_k_v),.wb_rdy(wb_k_rdy),.wb_addr(wb_k_addr),.wb_len(wb_k_len),.wb_tag(wb_k_tag),.wb_data(wb_k_data),.wb_strb(wb_k_strb),
 .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb));
 wire k_oor,w_oor;wire [63:0] refreshes;wire [31:0] w_reads;
 ot_chip_v41x_hbm3e_phy #(.K_AW(30),.KTAGW(17),.K_MEM(32768),.CLK_PS(1024)) u_phy(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
 .w_v(1'b0),.w_rdy(),.w_addr(24'b0),.w_len(6'b0),.w_tag(10'b0),.w_room(),.wr_v(),.wr_rdy(8'b0),.wr_tag(),.wr_beat(),.wr_data(),
 .k_oor(k_oor),.w_oor(w_oor),.refreshes(refreshes),.w_reads(w_reads));
 function automatic [255:0] data_for(input integer sector);
  integer j;begin for(j=0;j<8;j=j+1)data_for[j*32+:32]=32'hd14bf234^(sector*32'h10021)^(j*32'h23571113);end
 endfunction
 integer writes=0,acks=0,reads=0,outputs=0,output_cycles=0,stream_edges=0,hbm_edges=0;
 integer last_out=-1;reg wb_complete=0,ready_seen=0;
 reg [TOTAL-1:0] seen_w=0,seen_r=0;
 always @(posedge hbm_clk)if(hbm_rst_n)begin
  hbm_edges=hbm_edges+1;
  if(k_oor||w_oor)$fatal(1,"PHY aperture");
  for(integer p=0;p<32;p=p+1)begin
   if(k_wr_done[p])acks=acks+1;
   if(k_v[p]&&k_rdy[p])begin:check_request
    integer s,j,pc;s=k_addr[p*30+:30];j=s-BASE;pc=((s>>2)^(s>>7)^(s>>12))&31;
    if(pc!=p||j<0||j>=TOTAL||k_len[p*4+:4]!=1)$fatal(1,"actual PHY address/hash");
    if(k_we[p])begin
     if(seen_w[j]||k_wdata[p*256+:256]!==data_for(s))$fatal(1,"actual PHY write");
     seen_w[j]=1;writes=writes+1;
    end else begin
     if(!wb_complete||seen_r[j])$fatal(1,"read before true WB ACK or duplicate");
     seen_r[j]=1;reads=reads+1;
    end
   end
  end
 end
 always @(posedge stream_clk)begin
  stream_edges=stream_edges+1;#1;
  if(stream_rst_n&&hbm_rst_n)begin
   if(wb_fault||pf_fault)$fatal(1,"boundary fault");
   if(wb_done_v)begin
    if(wb_done_bank||wb_done_epoch!=41||wb_done_sectors!=TOTAL||acks!=TOTAL)$fatal(1,"posted completion identity/count");
    wb_complete=1;
   end
   if(pf_ready_v)begin
    if(!pf_ready_bank||pf_ready_epoch!=42||reads!=TOTAL)$fatal(1,"resident completion identity");
    ready_seen=1;
   end
   if(pf_out_v)begin
    if(pf_out_ordinal!=outputs||pf_out_epoch!=42||!pf_out_bank||pf_out_mask!=8'hff||pf_out_last!==(outputs+8==TOTAL))$fatal(1,"static output metadata");
    if(last_out>=0&&stream_edges!=last_out+1)$fatal(1,"static output wait");
    last_out=stream_edges;output_cycles=output_cycles+1;
    for(integer l=0;l<8;l=l+1)if(pf_out_data[l*256+:256]!==data_for(BASE+outputs+l))$fatal(1,"actual HBM roundtrip data sector%0d",BASE+outputs+l);
    outputs=outputs+8;
   end
  end
 end
 initial begin
  repeat(4)@(negedge stream_clk);stream_rst_n=1;
  repeat(3)@(negedge hbm_clk);hbm_rst_n=1;
  repeat(20)@(negedge stream_clk);
  wb_reserve_v=1;#1;if(!wb_reserve_ready)$fatal(1,"WB reserve");
  @(negedge stream_clk);wb_reserve_v=0;wb_fill_start=1;
  @(negedge stream_clk);wb_fill_start=0;
  for(integer row=0;row<TOTAL/8;row=row+1)begin
   for(integer l=0;l<8;l=l+1)wd[l*289+:289]={1'b1,32'(BASE+row*8+l),data_for(BASE+row*8+l)};
   @(negedge stream_clk);
  end
  wd=0;wait(wb_complete);
  @(negedge stream_clk);pf_reserve_v=1;#1;if(!pf_reserve_ready)$fatal(1,"PF reserve");
  @(negedge stream_clk);pf_reserve_v=0;
  wait(ready_seen);
  @(negedge stream_clk);pf_start_v=1;
  @(negedge stream_clk);pf_start_v=0;
  wait(outputs==TOTAL);repeat(8)@(negedge stream_clk);
  if(writes!=TOTAL||acks!=TOTAL||reads!=TOTAL||output_cycles!=80||seen_w!=='1||seen_r!=='1)$fatal(1,"joint final count");
  $display("BLOCK_ROUNDTRIP PASS actualPHY=1 preload=0 SRAMs=64 sectors=%0d writes=%0d realACKs=%0d reads=%0d fixedInputCycles=80 fixedOutputCycles=%0d streamEdges=%0d hbmEdges=%0d",TOTAL,writes,acks,reads,output_cycles,stream_edges,hbm_edges);
  $finish;
 end
 initial begin #300000000;$fatal(1,"roundtrip timeout");end
endmodule
`default_nettype wire
