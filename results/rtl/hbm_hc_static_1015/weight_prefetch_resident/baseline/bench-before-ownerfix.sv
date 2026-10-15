`timescale 1ps/1fs
module tb_hgi_hc_prefetch_direct_controller_static;
 parameter integer MUT=0;
 parameter integer PERIOD=1080;
 parameter integer PHY_LATENCY=80;
 parameter integer ROWS=24;
 parameter integer BADTAG=0;
 parameter integer MAX_OUTSTANDING=8;
 reg stream_clk=0,hbm_clk=0;always #416.666 stream_clk=~stream_clk;always #512 hbm_clk=~hbm_clk;
 reg stream_rst_n=0,hbm_rst_n=0;
 reg reserve_v=0,reserve_half=0;reg [34:0] reserve_row_local_byte=35'd21474836480;
 reg [15:0] reserve_epoch=16'h6001;wire [3:0] reserve_ready;wire [7:0] fetched_ready;wire [31:0] resident_ready;
 reg drain_v=0,drain_half=0,drain_slot=0;reg [15:0] drain_epoch=16'h6001;
 wire half_done,done_half;wire [2223:0] ap;wire fault;
 reg [7:0] read_v=0,read_slot=0;reg [55:0] read_row=0;
 wire [7:0] read_valid,write_done;wire [8191:0] raw_weight;wire afault;
 wire [127:0] k_v,k_we,kr_rdy,k_rdy,k_wr_done,kr_v;
 wire [3839:0] k_addr;wire [511:0] k_len;wire [2175:0] k_tag;
 wire [32767:0] k_wdata;wire [4095:0] k_wstrb;
 wire [2175:0] kr_tag;wire [511:0] kr_beat;wire [32767:0] kr_data;reg image_loaded=0;
 reg [255:0] image[0:61439];reg pending[0:127][0:7];integer delay_q[0:127][0:7];
 reg [16:0] tag_q[0:127][0:7];reg [255:0] data_q[0:127][0:7];
 reg injected=0;reg [16:0] oldest_tag[0:127];reg have_oldest[0:127];
 integer fault_mode=BADTAG;integer phase_delay=0,pre_idle=3871;bit stale_epoch=0,wrong_tag=0;wire [2175:0] kr_tag_native;
 assign kr_tag=kr_tag_native ^ (wrong_tag&&(|kr_v)?2176'd1:2176'd0);
 integer run_period=PERIOD;integer requests=0,responses=0,checked=0,stream_cycles=0,last_ap_commit=0;
 string image_path;
 ot_hgi_hc_prefetch_resident_static #(.MUT(MUT),.MAX_OUTSTANDING(MAX_OUTSTANDING)) dut(.*);
 ot_hgi_hc_aperture_static u_store(.clk(stream_clk),.rst_n(stream_rst_n),.ap(ap),.write_done(write_done),
  .read_v(read_v),.read_slot(read_slot),.read_row(read_row),.read_valid(read_valid),.raw_weight(raw_weight),.fault(afault));
 function automatic [4:0] pc_of(input [29:0] s);pc_of=s[6:2]^s[11:7]^s[16:12];endfunction
 for(genvar st=0;st<4;st=st+1)begin:physical_stack
  wire native_fault;wire [31:0] row_v,col_v,col_we,dram_rvalid;
  wire [95:0] row_op;wire [159:0] row_bank,col_bank,col_col;wire [607:0] row_row;
  wire [8191:0] col_data,dram_rdata;wire [1023:0] col_strb;
  wire [31:0] pc_clk={32{hbm_clk}};
  ot_hbm_svc_native_sector_owned_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1),.COLUMN_CLOSE_GUARD(1)) u_controller(
   .clk(hbm_clk),.rst_n(hbm_rst_n),.pc_clk(pc_clk),
   .k_v(k_v[st*32+:32]),.k_rdy(k_rdy[st*32+:32]),.k_we(k_we[st*32+:32]),.k_addr(k_addr[st*960+:960]),.k_len(k_len[st*128+:128]),
   .k_tag(k_tag[st*544+:544]),.k_wdata(k_wdata[st*8192+:8192]),.k_wstrb(k_wstrb[st*1024+:1024]),.k_wr_done(k_wr_done[st*32+:32]),
   .kr_v(kr_v[st*32+:32]),.kr_rdy(kr_rdy[st*32+:32]),.kr_tag(kr_tag_native[st*544+:544]),.kr_beat(kr_beat[st*128+:128]),.kr_data(kr_data[st*8192+:8192]),
   .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
   .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
  ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(671088640),.K_MEM(61440)) dram(
   .clk(hbm_clk),.rst_n(hbm_rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),
   .col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
  initial begin wait(image_loaded);#1;for(integer a=0;a<61440;a=a+1)dram.mem[a]=image[a];if($test$plusargs("PAYLOAD_MUTANT")&&st==1)dram.mem[5*320+319]^=256'd1;end
  always @(posedge hbm_clk)if(hbm_rst_n&&native_fault)$fatal(1,"actual native command controller fault stack%0d",st);
 end
 always @(posedge hbm_clk)begin:check_actual_phy
  integer pc,st,bank,row,offset;reg [29:0]sector;reg [34:0]byte_address;
  if(hbm_rst_n)for(integer i=0;i<128;i=i+1)begin
   if(k_v[i]&&k_rdy[i])begin
    st=i/32;pc=i%32;sector=k_addr[i*30+:30];byte_address={sector,5'b0};
    if(pc_of(sector)!=pc||k_we[i]||k_len[i*4+:4]!=1)$fatal(1,"actual PHY command/PC error");
    if(byte_address<35'd21474836480||byte_address>=35'd21474836480+24*81920)$fatal(1,"actual20GiB image bounds");
    bank=((byte_address-35'd21474836480)%81920)/10240;
    if(bank%4!=st)$fatal(1,"actual stripe stack mismatch");
    requests=requests+1;
   end
   if(kr_v[i]&&kr_rdy[i])responses=responses+1;
  end
 end
 always @(negedge stream_clk)if(|write_done)last_ap_commit=stream_cycles;
 always @(posedge stream_clk)begin
  stream_cycles=stream_cycles+1;
  if(stream_rst_n&&(stale_epoch||wrong_tag)&&fault)begin $display("HC_REGION_OWNER_MUTANT PASS full_epoch_or_wrong_tag_rejected stale=%0d wrongtag=%0d",stale_epoch,wrong_tag);$finish;end
  if(stream_rst_n&&fault_mode!=0&&injected&&fault)begin $display("HC_DIRECT_BADTAG PASS actualPHYunknownownerrefused mode%0d",fault_mode);$finish;end
  else if(stream_rst_n&&(fault||afault))$fatal(1,"actual direct prefetch/aperture fault cycle%0d",stream_cycles);
 end
 task tick;begin @(posedge stream_clk);#2;end endtask
 task idle(input integer n);begin repeat(n)tick();@(negedge stream_clk);end endtask
 task configure_reserve(input integer row,input bit half);begin
  reserve_row_local_byte=35'd21474836480+row*81920;reserve_half=half;reserve_epoch=16'h6001+row;
  reserve_v=1;#2;if(reserve_ready!=15)$fatal(1,"reserved source bank not free row%0d half%0d",row,half);
 end endtask
 task configure_drain(input integer row,input bit half);begin
  drain_v=1;drain_half=half;drain_slot=row%2;drain_epoch=16'h6001+row+(stale_epoch?4:0);#2;
  if((fetched_ready&(half?8'haa:8'h55))!=(half?8'haa:8'h55))$fatal(1,"compiler deadline missed row%0d half%0d cycle%0d ready%b",row,half,stream_cycles,fetched_ready);
 end endtask
 initial begin:run
  integer row,t,b,q,pos,r,start_cycle,relative_commit,cold_start;reg [255:0] expected;
  if($value$plusargs("PERIOD=%d",run_period))begin end
  if($value$plusargs("PHASE_DELAY=%d",phase_delay))begin end
  if($value$plusargs("PRE_IDLE=%d",pre_idle))begin end
  stale_epoch=$test$plusargs("STALE_EPOCH");wrong_tag=$test$plusargs("WRONGTAG");
  if($value$plusargs("FAULT=%d",fault_mode))begin end
  if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"IMAGE required");$readmemh(image_path,image);image_loaded=1;
  for(integer i=0;i<128;i=i+1)begin have_oldest[i]=0;oldest_tag[i]=0;for(integer os=0;os<8;os=os+1)begin pending[i][os]=0;delay_q[i][os]=0;end end
  idle(5);stream_rst_n=1;hbm_rst_n=1;idle(pre_idle);cold_start=stream_cycles;
  // Only the explicit cold block boundary may wait. All production slots below
  // are fixed and checked; four actual released rows occupy eight regions.
  for(row=0;row<4;row=row+1)for(b=0;b<2;b=b+1)begin
   reserve_row_local_byte=35'd21474836480+row*81920;reserve_half=1'(b);reserve_epoch=16'h6001+row;
   #2;t=0;while(reserve_ready!=15)begin tick();@(negedge stream_clk);t=t+1;if(t>20000)$fatal(1,"cold descriptor timeout");end
   reserve_v=1;tick();@(negedge stream_clk);reserve_v=0;
  end
  t=0;while(resident_ready!=32'hffffffff)begin tick();@(negedge stream_clk);t=t+1;if(t>20000)$fatal(1,"cold four-row prefetch timeout");end
  $display("HC_REGION_COLD_BOUNDARY start=%0d ready=%0d cold_cycles=%0d resident=%h",cold_start,stream_cycles,stream_cycles-cold_start,resident_ready);
  idle(phase_delay);start_cycle=stream_cycles;
  for(row=0;row<ROWS;row=row+1)begin
   for(t=0;t<run_period;t=t+1)begin
    reserve_v=0;drain_v=0;read_v=0;
    if(t==0)configure_drain(row,0);
    if(t==330)begin
     configure_drain(row,1);
     if(row<ROWS-4)configure_reserve(row+4,0);
    end
    if(t==660&&row<ROWS-4)configure_reserve(row+4,1);
    // Direct producer writes end by cycle653; actual HC store commits by655.
    // Verify every consumed source sector through synchronous SRAM reads.
    if(t>=670&&t<750)begin
     read_v=255;read_slot={8{1'(row%2)}};r=t-670;
     for(b=0;b<8;b=b+1)read_row[b*7+:7]=r;
    end
    tick();
    if(t>=670&&t<750)begin
     if(read_valid!=255)$fatal(1,"missing actual HC read row%0d",row);
     for(b=0;b<8;b=b+1)for(q=0;q<4;q=q+1)begin
      pos=(t-670)*4+q;expected=image[row*2560+b*320+pos];
      if(raw_weight[b*1024+q*256+:256]!==expected)$fatal(1,"actual aperture memory mismatch row%0d bank%0d position%0d",row,b,pos);
      checked=checked+1;
     end
    end
    if(t==760)begin
     relative_commit=last_ap_commit-(start_cycle+row*run_period);
     if(relative_commit>660)$fatal(1,"late direct store commit age%0d",relative_commit);
     $display("HC_DIRECT_ROW row=%0d fixed_start=%0d last_actual_store_age=%0d next_ready=%h",row,start_cycle+row*run_period,relative_commit,fetched_ready);
    end
    @(negedge stream_clk);
   end
  end
  if(requests!=ROWS*2560||responses!=ROWS*2560||checked!=ROWS*2560||fault||afault)$fatal(1,"count/fault mismatch req%0d rsp%0d checked%0d",requests,responses,checked);
  $display("HC_PREFETCH_RESIDENT_ACTUAL_CONTROLLER PASS rows=%0d actualPHYrequests=%0d responses=%0d actualSRAMreadbacks=%0d steady_row_period=%0d production_edges=%0d actualSRAMs=320 HBM1024 stream833 strictcommandDRAM23",ROWS,requests,responses,checked,run_period,ROWS*run_period);$finish;
 end
 initial begin #60000000;$fatal(1,"timeout");end
endmodule
