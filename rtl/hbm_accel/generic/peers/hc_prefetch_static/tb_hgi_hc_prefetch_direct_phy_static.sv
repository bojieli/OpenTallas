`timescale 1ps/1fs
module tb_hgi_hc_prefetch_direct_phy_static;
 parameter integer MUT=0;
 parameter integer PERIOD=1080;
 parameter integer PHY_LATENCY=80;
 parameter integer ROWS=24;
 parameter integer BADTAG=0;
 parameter integer MAX_OUTSTANDING=8;
 reg stream_clk=0,hbm_clk=0;always #416.666 stream_clk=~stream_clk;always #512 hbm_clk=~hbm_clk;
 reg stream_rst_n=0,hbm_rst_n=0;
 reg reserve_v=0,reserve_half=0;reg [34:0] reserve_row_local_byte=35'd21474836480;
 reg [15:0] reserve_epoch=16'h6001;wire [3:0] reserve_ready;wire [7:0] fetched_ready;
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
 integer fault_mode=BADTAG;
 integer run_period=PERIOD;integer requests=0,responses=0,checked=0,stream_cycles=0,last_ap_commit=0;
 string image_path;
 ot_hgi_hc_prefetch_direct_static #(.MUT(MUT),.MAX_OUTSTANDING(MAX_OUTSTANDING)) dut(.*);
 ot_hgi_hc_aperture_static u_store(.clk(stream_clk),.rst_n(stream_rst_n),.ap(ap),.write_done(write_done),
  .read_v(read_v),.read_slot(read_slot),.read_row(read_row),.read_valid(read_valid),.raw_weight(raw_weight),.fault(afault));
 function automatic [4:0] pc_of(input [29:0] s);pc_of=s[6:2]^s[11:7]^s[16:12];endfunction
 for(genvar st=0;st<4;st=st+1)begin:physical_stack
  wire k_oor,w_oor;wire [63:0] refreshes;
  ot_chip_v41x_hbm3e_phy #(.K_AW(30),.KTAGW(17),.K_MEM(61440),.K_BASE(64'd671088640),.CLK_PS(1024)) u_phy(
   .clk(hbm_clk),.rst_n(hbm_rst_n),.k_v(k_v[st*32+:32]),.k_rdy(k_rdy[st*32+:32]),.k_addr(k_addr[st*960+:960]),.k_len(k_len[st*128+:128]),
   .k_tag(k_tag[st*544+:544]),.k_we(k_we[st*32+:32]),.k_wdata(k_wdata[st*8192+:8192]),.k_wstrb(k_wstrb[st*1024+:1024]),.k_wr_done(k_wr_done[st*32+:32]),
   .kr_v(kr_v[st*32+:32]),.kr_rdy(kr_rdy[st*32+:32]),.kr_tag(kr_tag[st*544+:544]),.kr_beat(kr_beat[st*128+:128]),.kr_data(kr_data[st*8192+:8192]),
   .w_v(1'b0),.w_rdy(),.w_addr(24'b0),.w_len(6'b0),.w_tag(10'b0),.w_room(),.wr_v(),.wr_rdy(8'b0),.wr_tag(),.wr_beat(),.wr_data(),
   .k_oor(k_oor),.w_oor(w_oor),.refreshes(refreshes),.w_reads());
  initial begin wait(image_loaded);#1;for(integer a=0;a<61440;a=a+1)u_phy.u_k.mem[(64'd671088640+a)%61440]=image[a];end
  always @(posedge hbm_clk)if(hbm_rst_n&&(k_oor||w_oor))$fatal(1,"actual PHY address aperture error");
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
  drain_v=1;drain_half=half;drain_slot=row%2;drain_epoch=16'h6001+row;
  if((fetched_ready&(half?8'haa:8'h55))!=(half?8'haa:8'h55))$fatal(1,"compiler deadline missed row%0d half%0d cycle%0d ready%b",row,half,stream_cycles,fetched_ready);
 end endtask
 initial begin:run
  integer row,t,b,q,pos,r,start_cycle,relative_commit;reg [255:0] expected;
  if($value$plusargs("PERIOD=%d",run_period))begin end
  if($value$plusargs("FAULT=%d",fault_mode))begin end
  if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"IMAGE required");$readmemh(image_path,image);image_loaded=1;
  for(integer i=0;i<128;i=i+1)begin have_oldest[i]=0;oldest_tag[i]=0;for(integer os=0;os<8;os=os+1)begin pending[i][os]=0;delay_q[i][os]=0;end end
  idle(4);stream_rst_n=1;hbm_rst_n=1;idle(12);
  // Explicit initialization block boundary. Steady-state below never waits.
  configure_reserve(0,0);tick();@(negedge stream_clk);reserve_v=0;
  configure_reserve(0,1);tick();@(negedge stream_clk);reserve_v=0;
  t=0;while(fetched_ready!=255)begin tick();t=t+1;if(t>20000)$fatal(1,"initial boundary prefetch timeout");end
  @(negedge stream_clk);start_cycle=stream_cycles;
  for(row=0;row<ROWS;row=row+1)begin
   for(t=0;t<run_period;t=t+1)begin
    reserve_v=0;drain_v=0;read_v=0;
    if(t==0)configure_drain(row,0);
    if(t==330)begin
     configure_drain(row,1);
     if(row<ROWS-1)configure_reserve(row+1,0);
    end
    if(t==660&&row<ROWS-1)configure_reserve(row+1,1);
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
  $display("HC_PREFETCH_DIRECT_ACTUAL_PHY PASS rows=%0d actualPHYrequests=%0d responses=%0d actualSRAMreadbacks=%0d steady_row_period=%0d production_edges=%0d actualSRAMs=192 HBM1024 stream833 PHYlatency=%0d",ROWS,requests,responses,checked,run_period,ROWS*run_period,PHY_LATENCY);$finish;
 end
 initial begin #60000000;$fatal(1,"timeout");end
endmodule
