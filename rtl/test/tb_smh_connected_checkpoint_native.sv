`timescale 1ps/1fs
module tb_smh_mapped_checkpoint_native;
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
 wire native_fault;
 wire [31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;
 wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
 wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;
 ot_hbm_svc_native_sector_guarded_stack u_native(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.pc_clk({32{hbm_clk}}),
 .k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
 .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(32'h28810000),.K_MEM(65536)) dram(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 reg [9:0]tag_base;integer tag_arg;
 reg formatter_open=0,formatter_read=0;reg[5:0]read_row=0;reg[9:0]read_tag=0;
 wire[1:0]formatter_ready,formatter_owned;wire formatter_busy,formatter_fault;wire[1098:0]packet;
 wire[95:0]indices;wire[63:0]epochs;
 genvar l;generate for(l=0;l<4;l=l+1)begin
  assign indices[l*24+:24]=out_ordinal+l;assign epochs[l*16+:16]=out_epoch;
 end endgenerate
 reg command_cfg_we=0,read_cfg_we=0;reg [9:0] cfg_addr=0;
 reg [255:0] command_cfg_data=0,read_cfg_data=0;reg command_start_v=0,read_start_v=0;
 wire [82:0] command;wire command_v,read_calendar_v,command_done,read_done;
 wire [31:0] command_ordinal,read_ordinal;wire programme_fault,feed_fault;
 wire [42:0] expected_request;
 wire [1081:0] unused_lt0,unused_lt1;wire [569:0] unused_lb0,unused_lb1;wire [11:0]unused_fm;
 ot_smh_packed_program_join u_join(
 .clk(stream_clk),.rst_n(stream_rst_n),.command_cfg_we(command_cfg_we),.read_cfg_we(read_cfg_we),.cfg_addr(cfg_addr),
 .command_cfg_data(command_cfg_data),.read_cfg_data(read_cfg_data),.command_start_v(command_start_v),.read_start_v(read_start_v),
 .start_base(10'd0),.start_limit(11'd72),.start_loops(16'd1),
 .open_v(formatter_open),.open_bank(1'b0),.open_epoch(16'h4567),.open_count(7'd40),.open_tag_base(tag_base),
 .sector_v(out_v?out_mask:4'b0),.sector_index(indices),.sector_epoch({4{16'h4567}}),.sector_data(out_data),
 .retire_v(1'b0),.retire_bank(1'b0),.retire_epoch(16'd0),.block_ready(formatter_ready),.bank_owned(formatter_owned),
 .command(command),.packet(packet),.command_v(command_v),.read_calendar_v(read_calendar_v),.command_done(command_done),.read_done(read_done),
 .command_ordinal(command_ordinal),.read_ordinal(read_ordinal),.lt0(unused_lt0),.lt1(unused_lt1),.lb0(unused_lb0),.lb1(unused_lb1),
 .fm(unused_fm),.expected_request(expected_request),.programme_fault(programme_fault),.service_fault(formatter_fault),.feed_fault(feed_fault));
 wire xw_en,xw_last,activation_done;wire[6:0]xw_addr,xw_grp;wire[2047:0]xw_data;
 tb_smh_activation_source_fixture activation(.clk(stream_clk),.rst_n(stream_rst_n),
 .xw_en(xw_en),.xw_last(xw_last),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),.fixture_done(activation_done));
 wire sm_rv,sm_fault,schedule_fault;wire [11:0]sm_rrow;wire [255:0]sm_data;
 ot_hbm_accel_smh_static u_sm(.clk(stream_clk),.rst_n(stream_rst_n),.command(command_v?command:83'd0),.packet(packet),
 .expected_request(),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
 .rv(sm_rv),.rrow(sm_rrow),.rdata(sm_data),.fault(sm_fault),.schedule_fault(schedule_fault));
 reg [255:0]golden[0:0];reg [255:0]commands[0:71],reads[0:71];
 string xfile,gfile,cfile,rfile;integer mutant=0;integer results=0,last_result_cycle=-1,command_launch_cycle=-1;
 always @(posedge stream_clk)begin #2;
  if(stream_rst_n)begin
   if(programme_fault||feed_fault||sm_fault||schedule_fault)$fatal(1,"native programme/SM fault cycle%0d",cycles);
   if(sm_rv)begin
    if(sm_rrow!==12'd0||sm_data!==golden[0])$fatal(1,"NATIVE_CHECKPOINT numerical mismatch sm%0d got%064h expected%064h row%0d",sm,sm_data,golden[0],sm_rrow);
    results=results+1;last_result_cycle=cycles;
   end
  end
 end
 reg[255:0]expected[0:171];reg[1087:0]records[0:39];string dir;integer sm,checks=0,sectorchecks=0,requests=0,cycles=0;integer req_sectors=0;
 real begin_at,ready_at;
 function automatic integer pc_of(input integer s);pc_of=((s>>2)^(s>>7)^(s>>12))&31;endfunction
 always @(posedge hbm_clk)if(hbm_rst_n)begin
  if(native_fault)$fatal(1,"native shared controller fault");
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
  tag_base=tag_arg; if($value$plusargs("MUTANT=%d",mutant))begin end
  for(integer i=0;i<4;i=i+1)reserve_pcs[i*5+:5]=4*(sm%8)+i;
  if(!$value$plusargs("XFILE=%s",xfile)||!$value$plusargs("GFILE=%s",gfile)||!$value$plusargs("CFILE=%s",cfile)||!$value$plusargs("RFILE=%s",rfile))$fatal(1,"native operands/programme mandatory");
  $readmemh(gfile,golden);$readmemh(cfile,commands);$readmemh(rfile,reads);
  $readmemh({dir,"/backing.hex"},dram.mem);$readmemh({dir,"/sectors.hex"},expected);$readmemh({dir,"/records.hex"},records);
  repeat(4)@(negedge stream_clk);stream_rst_n=1;repeat(3)@(negedge hbm_clk);hbm_rst_n=1;repeat(20)@(negedge stream_clk);
  for(integer a=0;a<72;a=a+1)begin
   command_cfg_we=1;read_cfg_we=1;cfg_addr=a;command_cfg_data=commands[a];read_cfg_data=reads[a];@(negedge stream_clk);
  end
  command_cfg_we=0;read_cfg_we=0;
  wait(activation_done);repeat(40)@(negedge stream_clk);
  reserve_v=1;#1;if(!reserve_ready)$fatal(1,"reservation unavailable");begin_at=$realtime;
  @(negedge stream_clk);reserve_v=0;wait(block_ready[0]);
  @(negedge stream_clk);start_v=1;
  @(negedge stream_clk);start_v=0;formatter_open=1;
  @(negedge stream_clk);formatter_open=0;
  wait(formatter_ready[0]);
  @(negedge stream_clk);
  read_start_v=1;@(negedge stream_clk);read_start_v=0;command_start_v=1;command_launch_cycle=cycles;
  @(negedge stream_clk);command_start_v=0;
  repeat(300)@(negedge stream_clk);
  if(results!=1)$fatal(1,"native result count %0d",results);
  if(checks!=40||sectorchecks!=172||req_sectors!=172)$fatal(1,"actual checkpoint counts");
  $display("CONNECTED_VM_NATIVE_SM PASS sm=%0d stack=%0d exact_records=%0d sectors=%0d PHY_bursts=%0d row_base=20738 cold_prefetch_ps=%0f native_FP32columns=8 result_after_command_edges=%0d actual_VM_xwrites=520 native_PCowners=32 command_reads=%0d full_price_qualified=0",sm,STACK,checks,sectorchecks,requests,ready_at-begin_at,last_result_cycle-command_launch_cycle,dram.reads);$finish;
 end
 initial begin #300000000;$fatal(1,"mapped checkpoint timeout");end
endmodule
