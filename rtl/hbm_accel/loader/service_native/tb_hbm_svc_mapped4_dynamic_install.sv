`timescale 1ps/1fs
module tb_hbm_svc_mapped4_dynamic_install;
 parameter integer STACK=0,MODE=1,IMAGE_OFFSET=136048;
 localparam integer IMAGE_BASE=(16640+(IMAGE_OFFSET>>12))<<15;
 reg[31:0]reserve_base=0;reg[11:0]reserve_total=73;integer offset_arg=4,invalid=0;
 reg stream_clk=0,hbm_clk=0;
 initial forever begin #416.666 stream_clk=1;#416.667 stream_clk=0;end
 initial begin #173;forever #512 hbm_clk=~hbm_clk;end
 reg stream_rst_n=0,hbm_rst_n=0,reserve_v=0,start_v=0;
 reg [10:0] start_ordinal=0;reg [11:0] start_count=272;reg start_release=0;
 integer segment_lasts=0,segment_edges=0;
 reg [19:0] reserve_pcs;reg [14:0] reserve_row_base=16640;
 wire reserve_ready;wire [1:0]block_ready;wire block_ready_v,block_ready_bank;wire[15:0]block_ready_epoch;
 wire out_v,out_bank,out_last,fault;wire[3:0]out_mask;wire[1023:0]out_data;wire[10:0]out_ordinal;wire[15:0]out_epoch;
 wire [31:0]k_v,k_rdy,k_we,k_wr_done,kr_v,kr_rdy;wire[959:0]k_addr;wire[127:0]k_len,kr_beat;wire[543:0]k_tag,kr_tag;wire[8191:0]k_wdata,kr_data;wire[1023:0]k_wstrb;
 ot_hbm_svc_prefetch_mapped4_slice_cdc #(.STACK(STACK),.PACKED_OFFSET_MODE(MODE)) dut(
 .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
 .stream_bank_clk({4{stream_clk}}),.hbm_fifo_clk({8{hbm_clk}}),.hbm_pc_clk({32{hbm_clk}}),
 .reserve_pcs(reserve_pcs),.reserve_row_base(reserve_row_base),.reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base(reserve_base),.reserve_total(reserve_total),.reserve_bank(1'b0),.reserve_epoch(16'd51),
 .block_ready(block_ready),.block_ready_v(block_ready_v),.block_ready_bank(block_ready_bank),.block_ready_epoch(block_ready_epoch),
 .start_v(start_v),.start_bank(1'b0),.start_epoch(16'd51),.start_ordinal(start_ordinal),.start_count(start_count),.start_release(start_release),.out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(fault),
 .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
 wire native_fault;wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;
 wire[31:0]actual_wr_done;
 assign k_wr_done=installing?32'b0:actual_wr_done;
 reg installing=1;reg[31:0]install_v=0;reg[959:0]install_addr=0;reg[8191:0]install_data=0;
 wire[31:0]actual_v=installing?install_v:k_v;
 wire[31:0]actual_we=installing?install_v:k_we;
 wire[959:0]actual_addr=installing?install_addr:k_addr;
 wire[127:0]actual_len=installing?{32{4'd1}}:k_len;
 wire[8191:0]actual_data=installing?install_data:k_wdata;
 wire[1023:0]actual_strb=installing?{1024{1'b1}}:k_wstrb;
 reg[29:0]image_addr[0:1835];reg[255:0]image_data[0:1835];reg[1087:0]records[0:431];
 reg[255:0]expected[0:1835];reg[1087:0]reconstructed[0:431];
 integer file_fd,scan_result,loaded=0,install_acks=0,install_accepted=0,record_checks=0;
 integer next_image[0:31];string image_dir;
 function automatic integer pc_of(input[29:0]a);begin pc_of=(a[6:2]^a[11:7]^a[16:12]);end endfunction
 function automatic integer next_for_pc(input integer first,input integer pc);begin
  next_for_pc=1836;for(integer z=1835;z>=first;z=z-1)if(pc_of(image_addr[z])==pc)next_for_pc=z;
 end endfunction
 always @*begin
  install_v=0;install_addr=0;install_data=0;
  for(integer p=0;p<32;p=p+1)if(installing&&next_image[p]<1836)begin
   install_v[p]=1;install_addr[p*30+:30]=image_addr[next_image[p]];install_data[p*256+:256]=image_data[next_image[p]];
  end
 end
 always @(posedge hbm_clk)if(hbm_rst_n&&installing)begin
  for(integer p=0;p<32;p=p+1)begin
   if(actual_v[p]&&k_rdy[p])begin next_image[p]<=next_for_pc(next_image[p]+1,p);install_accepted=install_accepted+1;end
   if(actual_wr_done[p])install_acks=install_acks+1;
  end
 end
 ot_hbm_svc_native_sector_dynamic_stack #(.DYNAMIC_CA(1),.INTENT_PREVIEW(1),.REGISTERED_HEAD_BYPASS(1),.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1)) controller(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.pc_clk({32{hbm_clk}}),.k_v(actual_v),.k_rdy(k_rdy),.k_we(actual_we),.k_addr(actual_addr),.k_len(actual_len),.k_tag(k_tag),.k_wdata(actual_data),.k_wstrb(actual_strb),.k_wr_done(actual_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(IMAGE_BASE),.K_MEM(65536)) dram(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 function automatic[29:0]address(input integer pc,input integer anchor,input integer t);reg[29:0]s;integer r,b;begin
  r=anchor+t/1024;b=(((t>>7)&7)<<2)|(t&3);s=r<<15;s[14:12]=(b>>2)^((r>>2)&7);s[11:7]=(t>>2)&31;s[1:0]=(b&3)^(r&3);s[6:2]=pc^s[11:7]^s[16:12];address=s;
 end endfunction
 function automatic[255:0]pattern(input integer ordinal);integer j;begin for(j=0;j<8;j=j+1)pattern[j*32+:32]=32'h8517ac39^(ordinal*32'h10021)^(j*32'h1234567);end endfunction
 realtime install_begin,install_end,reserve_begin,resident_at;
 integer hbm_cycles=0,min_act_gap=100000,act_pairs=0,last_act[0:31];
 initial for(integer p=0;p<32;p=p+1)last_act[p]=-100000;
 always @(posedge hbm_clk)begin
  hbm_cycles=hbm_cycles+1;
  if(hbm_rst_n)for(integer p=0;p<32;p=p+1)if(row_v[p]&&row_op[p*3+:3]==1)begin
   if(last_act[p]>=0)begin act_pairs=act_pairs+1;if(hbm_cycles-last_act[p]<min_act_gap)min_act_gap=hbm_cycles-last_act[p];end
   last_act[p]=hbm_cycles;
  end
 end
 integer checked=0,reqsectors=0,edges=0,guard,ordinal,pcslot,t,addr;reg[2047:0]seen=0;
 always @(posedge hbm_clk)if(hbm_rst_n&&!installing)begin
  if(native_fault)$fatal(1,"offset native controller fault");
  for(integer p=0;p<32;p=p+1)if(k_v[p]&&k_rdy[p])begin
   if(((k_addr[p*30+:30]>>2)^(k_addr[p*30+:30]>>7)^(k_addr[p*30+:30]>>12))%32!=p||k_we[p])$fatal(1,"offset actual XOR PC failure");
   reqsectors=reqsectors+k_len[p*4+:4];
  end
 end
 always @(posedge stream_clk)begin #1;
  if(!invalid&&stream_rst_n&&hbm_rst_n&&fault)$fatal(1,"offset CDC fault");
  if(out_v)begin
   edges=edges+1;segment_edges=segment_edges+1;
   if(out_last)segment_lasts=segment_lasts+1;
   for(integer l=0;l<4;l=l+1)if(out_mask[l])begin
    ordinal=out_ordinal+l;
    if(ordinal>=reserve_total||seen[ordinal]||out_data[l*256+:256]!==expected[ordinal])$fatal(1,"offset exact payload mismatch ordinal=%0d",ordinal);
    for(integer by=0;by<32;by=by+1)if(ordinal*32+by<432*136)reconstructed[(ordinal*32+by)/136][((ordinal*32+by)%136)*8+:8]=out_data[l*256+by*8+:8];
    seen[ordinal]=1;checked=checked+1;
   end
  end
 end
 task tick;begin @(posedge stream_clk);#1;end endtask
 initial begin
  if(!$value$plusargs("DIR=%s",image_dir))$fatal(1,"actual image directory required");
  reserve_pcs={5'd3,5'd2,5'd1,5'd0};offset_arg=IMAGE_OFFSET;reserve_base=IMAGE_OFFSET;reserve_total=1836;
  $readmemh({image_dir,"/records.hex"},records);
  file_fd=$fopen({image_dir,"/physical.hex"},"r");if(!file_fd)$fatal(1,"actual physical image unavailable");
  for(integer n=0;n<1836;n=n+1)begin
   scan_result=$fscanf(file_fd,"@%h\n%h\n",image_addr[n],image_data[n]);if(scan_result!=2)$fatal(1,"physical image parse ordinal%0d",n);
   if(image_addr[n]<IMAGE_BASE||image_addr[n]>=IMAGE_BASE+65536)$fatal(1,"actual image window");
   if(image_addr[n]!==address(reserve_pcs[(n%4)*5+:5],reserve_row_base,IMAGE_OFFSET/4+n/4))$fatal(1,"actual installer image address mapping differs from descriptor");
   expected[n]=image_data[n];loaded=loaded+1;
  end
  $fclose(file_fd);
  if($test$plusargs("WRONGADDR"))image_addr[0]=image_addr[4];
  for(integer p=0;p<32;p=p+1)next_image[p]=1836;
  repeat(4)tick;stream_rst_n=1;hbm_rst_n=1;repeat(20)tick;
  for(integer p=0;p<32;p=p+1)next_image[p]=next_for_pc($test$plusargs("DROP")?1:0,p);
  install_begin=$realtime;guard=0;while(($test$plusargs("EARLYACK")?install_accepted:install_acks)<1836)begin tick;guard=guard+1;if(guard>20000)$fatal(1,"actual installation ACK timeout accepted%0d ACK%0d",install_accepted,install_acks);end
  if(install_acks!=1836||install_accepted!=1836||dram.writes!=1836)$fatal(1,"installation completion coverage");
  install_end=$realtime;installing=0;repeat(4)tick;
  if(!reserve_ready)$fatal(1,"offset reservation not online");reserve_begin=$realtime;reserve_v=1;tick;reserve_v=0;
  if(invalid)begin repeat(5)tick;if(!fault||dut.allocated||k_v)$fatal(1,"invalid descriptor allocated/issued or failed to fault");$display("MAPPED4_OFFSET_INVALID PASS case=%0d",invalid);$finish;end
  guard=0;while(!block_ready_v)begin tick;guard=guard+1;if(guard>10000)$fatal(1,"offset blockready timeout");end
  resident_at=$realtime;
  $display("MAPPED4_DYNAMIC_LATENCY install_true_ACK_HBM=%0f reserve_to_resident_HBM=%0f",(install_end-install_begin)/1024.0,(resident_at-reserve_begin)/1024.0);
  // Every start is a fixed compiler slot, independent of out_v or completion.
  for(integer seg=0;seg<7;seg=seg+1)begin
   start_ordinal=272*seg;start_count=(seg<6)?272:204;start_release=(seg==6);
   if($test$plusargs("WRONG_SLICE") && seg==1)start_ordinal=start_ordinal+4;
   if($test$plusargs("EARLY_RELEASE") && seg==0)start_release=1;
   if($test$plusargs("ZERO_COUNT") && seg==0)start_count=0;
   if($test$plusargs("OUT_OF_RANGE") && seg==0)begin start_ordinal=1830;start_count=20;end
   segment_edges=0;start_v=1;tick;start_v=0;
   repeat(111)tick;
   if(segment_lasts!=seg+1 || segment_edges!=((seg<6)?80:60))$fatal(1,"fixed segment timing/count");
   if(checked!=((seg<6)?272*(seg+1):1836))$fatal(1,"fixed segment payload coverage");
   if(seg<6 && (!dut.allocated[0] || !block_ready[0]))$fatal(1,"resident bank released before final compiled segment");
   if(seg==6 && (dut.allocated[0] || block_ready[0]))$fatal(1,"final compiled release missing");
  end
  tick;if(reqsectors!=reserve_total)$fatal(1,"offset request coverage");
  for(integer n=0;n<432;n=n+1)begin if(reconstructed[n]!==records[n])$fatal(1,"actual checkpoint reconstructed record mismatch %0d",n);record_checks=record_checks+1;end
  $display("MAPPED4_DYNAMIC_ACT pairs=%0d min_gap=%0d",act_pairs,min_act_gap);
  $display("MAPPED4_SLICE_INSTALL PASS actual_WR=%0d real_ACK=%0d actual_RD=%0d exact_sectors=%0d actual_records=%0d offset=%0d",dram.writes,install_acks,dram.reads,checked,record_checks,IMAGE_OFFSET);
  $display("MAPPED4_SLICE_NATIVE PASS mode=%0d offset=%0d sectors=%0d exact_payloads=%0d fixed_edges=%0d native_RD=%0d RL23",MODE,offset_arg,reserve_total,checked,edges,dram.reads);$finish;
 end
 initial begin #20000000;$fatal(1,"offset timeout");end
endmodule
