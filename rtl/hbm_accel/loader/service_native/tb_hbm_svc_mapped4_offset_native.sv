`timescale 1ps/1fs
module tb_hbm_svc_mapped4_offset_native;
 parameter integer STACK=0,MODE=1;
 reg[31:0]reserve_base=0;reg[11:0]reserve_total=73;integer offset_arg=4,invalid=0;
 reg stream_clk=0,hbm_clk=0;
 initial forever begin #416.666 stream_clk=1;#416.667 stream_clk=0;end
 initial begin #173;forever #512 hbm_clk=~hbm_clk;end
 reg stream_rst_n=0,hbm_rst_n=0,reserve_v=0,start_v=0;
 reg [19:0] reserve_pcs;reg [14:0] reserve_row_base=16640;
 wire reserve_ready;wire [1:0]block_ready;wire block_ready_v,block_ready_bank;wire[15:0]block_ready_epoch;
 wire out_v,out_bank,out_last,fault;wire[3:0]out_mask;wire[1023:0]out_data;wire[10:0]out_ordinal;wire[15:0]out_epoch;
 wire [31:0]k_v,k_rdy,k_we,k_wr_done,kr_v,kr_rdy;wire[959:0]k_addr;wire[127:0]k_len,kr_beat;wire[543:0]k_tag,kr_tag;wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;
 ot_hbm_svc_prefetch_mapped4_offset_cdc #(.STACK(STACK),.PACKED_OFFSET_MODE(MODE)) dut(
 .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
 .stream_bank_clk({4{stream_clk}}),.hbm_fifo_clk({8{hbm_clk}}),.hbm_pc_clk({32{hbm_clk}}),
 .reserve_pcs(reserve_pcs),.reserve_row_base(reserve_row_base),.reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_total(reserve_total),.reserve_bank(1'b0),.reserve_epoch(16'd51),
 .block_ready(block_ready),.block_ready_v(block_ready_v),.block_ready_bank(block_ready_bank),.block_ready_epoch(block_ready_epoch),
 .start_v(start_v),.start_bank(1'b0),.start_epoch(16'd51),.out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(fault),
 .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 wire native_fault;wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;
 ot_hbm_svc_native_sector_prefetch_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1)) controller(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.pc_clk({32{hbm_clk}}),.k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(32'h20800000),.K_MEM(65536)) dram(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 function automatic[29:0]address(input integer pc,input integer anchor,input integer t);reg[29:0]s;integer r,b;begin
  r=anchor+t/1024;b=(((t>>7)&7)<<2)|(t&3);s=r<<15;s[14:12]=(b>>2)^((r>>2)&7);s[11:7]=(t>>2)&31;s[1:0]=(b&3)^(r&3);s[6:2]=pc^s[11:7]^s[16:12];address=s;
 end endfunction
 function automatic[255:0]pattern(input integer ordinal);integer j;begin for(j=0;j<8;j=j+1)pattern[j*32+:32]=32'h8517ac39^(ordinal*32'h10021)^(j*32'h1234567);end endfunction
 integer checked=0,reqsectors=0,edges=0,guard,ordinal,pcslot,t,addr;reg[2047:0]seen=0;
 always @(posedge hbm_clk)if(hbm_rst_n)begin
  if(native_fault)$fatal(1,"offset native controller fault");
  for(integer p=0;p<32;p=p+1)if(k_v[p]&&k_rdy[p])begin
   if(((k_addr[p*30+:30]>>2)^(k_addr[p*30+:30]>>7)^(k_addr[p*30+:30]>>12))%32!=p||k_we[p])$fatal(1,"offset actual XOR PC failure");
   reqsectors=reqsectors+k_len[p*4+:4];
  end
 end
 always @(posedge stream_clk)begin #1;
  if(!invalid&&stream_rst_n&&hbm_rst_n&&fault)$fatal(1,"offset CDC fault");
  if(out_v)begin
   edges=edges+1;
   for(integer l=0;l<4;l=l+1)if(out_mask[l])begin
    ordinal=out_ordinal+l;
    if(ordinal>=reserve_total||seen[ordinal]||out_data[l*256+:256]!==pattern(ordinal))$fatal(1,"offset exact payload mismatch ordinal=%0d",ordinal);
    seen[ordinal]=1;checked=checked+1;
   end
  end
 end
 task tick;begin @(posedge stream_clk);#1;end endtask
 initial begin
  if(!$value$plusargs("OFFSET=%d",offset_arg))offset_arg=4;
  if($value$plusargs("INVALID=%d",invalid))begin end
  reserve_pcs={5'd27,5'd18,5'd9,5'd3};reserve_base=(STACK<<30)+(MODE?offset_arg:0);
  if($value$plusargs("TOTAL=%d",t))reserve_total=t;
  case(invalid)
   1:reserve_base=reserve_base|1;
   2:begin reserve_row_base=18687;reserve_base=(STACK<<30)+4092;reserve_total=8;end
   3:reserve_base=reserve_base^(1<<30);
   4:reserve_pcs={5'd27,5'd18,5'd9,5'd9};
  endcase
  if(!invalid)for(integer n=0;n<reserve_total;n=n+1)begin
   pcslot=n%4;t=(MODE?offset_arg/4:0)+n/4;addr=address(reserve_pcs[pcslot*5+:5],reserve_row_base,t);
   if(addr<32'h20800000||addr>=32'h20810000)$fatal(1,"test image aperture");dram.mem[addr-32'h20800000]=pattern(n);
  end
  repeat(4)tick;stream_rst_n=1;hbm_rst_n=1;repeat(20)tick;
  if(!reserve_ready)$fatal(1,"offset reservation not online");reserve_v=1;tick;reserve_v=0;
  if(invalid)begin repeat(5)tick;if(!fault||dut.allocated||k_v)$fatal(1,"invalid descriptor allocated/issued or failed to fault");$display("MAPPED4_OFFSET_INVALID PASS case=%0d",invalid);$finish;end
  guard=0;while(!block_ready_v)begin tick;guard=guard+1;if(guard>10000)$fatal(1,"offset blockready timeout");end
  start_v=1;tick;start_v=0;guard=0;
  while(checked<reserve_total)begin tick;guard=guard+1;if(guard>1000)$fatal(1,"offset drain timeout");end
  tick;if(reqsectors!=reserve_total)$fatal(1,"offset request coverage");
  $display("MAPPED4_OFFSET_NATIVE PASS mode=%0d offset=%0d sectors=%0d exact_payloads=%0d fixed_edges=%0d native_RD=%0d RL23",MODE,offset_arg,reserve_total,checked,edges,dram.reads);$finish;
 end
 initial begin #20000000;$fatal(1,"offset timeout");end
endmodule
