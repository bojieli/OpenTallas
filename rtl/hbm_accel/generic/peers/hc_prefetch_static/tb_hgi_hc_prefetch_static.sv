`timescale 1ps/1fs
module tb_hgi_hc_prefetch_static;
 parameter integer MUT=0;
 reg stream_clk=0,hbm_clk=0;always #416.666 stream_clk=~stream_clk;always #512 hbm_clk=~hbm_clk;
 reg stream_rst_n=0,hbm_rst_n=0,row_v=0,row_slot=0;
 reg [34:0] row_local_byte=35'd21474836480;reg [15:0] row_epoch=16'h6001;
 reg reserve_v=0,reserve_half=0,drain_v=0,drain_half=0,pad_v=0,deliver_v=0,deliver_half=0;
 wire [3:0] reserve_ready;wire [7:0] fetched_ready;wire [1:0] delivery_ready;
 reg [7:0] read_v=0,read_slot=0;reg [55:0] read_row=0;
 wire [2223:0] ap;wire [7:0] read_valid,write_done;wire [8191:0] raw_weight;wire fault;
 wire [127:0] k_v,k_we,kr_rdy;reg [127:0] k_rdy='1,k_wr_done=0,kr_v=0;
 wire [3839:0] k_addr;wire [511:0] k_len;wire [2175:0] k_tag;
 wire [32767:0] k_wdata;wire [4095:0] k_wstrb;
 reg [2175:0] kr_tag=0;reg [511:0] kr_beat=0;reg [32767:0] kr_data=0;
 reg [255:0] image[0:2559];reg pending[0:127];integer delay_q[0:127];
 reg [16:0] tag_q[0:127];reg [255:0] data_q[0:127];
 integer requests=0,responses=0,checked=0,stream_cycles=0,last_ap_commit=0;
 always @(negedge stream_clk)if(|write_done)last_ap_commit=stream_cycles;
 string image_path;
 ot_hgi_hc_prefetch_static #(.MUT(MUT)) dut(.*);
 function automatic [4:0] pc_of(input [29:0] s);pc_of=s[6:2]^s[11:7]^s[16:12];endfunction
 always @(posedge hbm_clk)begin:phy
  integer s,pc,i,bank,offset;reg [29:0] sector;reg [34:0] byte_address;
  if(hbm_rst_n)begin
   for(i=0;i<128;i=i+1)begin
    if(kr_v[i]&&kr_rdy[i])begin kr_v[i]<=0;responses=responses+1;end
    if(pending[i])begin
     if(delay_q[i]==0&&!kr_v[i])begin
      kr_v[i]<=1;kr_tag[i*17+:17]<=tag_q[i];kr_data[i*256+:256]<=data_q[i];pending[i]=0;
     end else if(delay_q[i]>0)delay_q[i]=delay_q[i]-1;
    end
    if(k_v[i]&&k_rdy[i])begin
     s=i/32;pc=i%32;sector=k_addr[i*30+:30];byte_address={sector,5'b0};
     if(pc_of(sector)!=pc)$fatal(1,"actual XOR PC mismatch");
     if(k_we[i]||k_len[i*4+:4]!=1||pending[i]||kr_v[i])$fatal(1,"PHY command ownership");
     if(byte_address<row_local_byte||byte_address>=row_local_byte+81920)$fatal(1,"not actual20GiB row address %h",byte_address);
     bank=(byte_address-row_local_byte)/10240;offset=((byte_address-row_local_byte)%10240)/32;
     if(bank%4!=s||offset>=320)$fatal(1,"stripe bank stack/segment mismatch");
     data_q[i]=image[bank*320+offset];tag_q[i]=k_tag[i*17+:17];pending[i]=1;delay_q[i]=(requests*7+i)%13;
     requests=requests+1;
    end
   end
  end
 end
 always @(posedge stream_clk)begin
  stream_cycles=stream_cycles+1;
  if(stream_rst_n&&fault)$fatal(1,"actual prefetch/landing/aperture fault cycle%0d",stream_cycles);
 end
 task tick;begin @(posedge stream_clk);#2;end endtask
 task idle(input integer n);begin repeat(n)tick();@(negedge stream_clk);end endtask
 task pulse_row;begin @(negedge stream_clk);row_v=1;tick();@(negedge stream_clk);row_v=0;idle(6);end endtask
 task reserve(input bit half);integer n;begin
  @(negedge stream_clk);reserve_half=half;reserve_v=1;#2;
  if(reserve_ready!=15)$fatal(1,"boundary reserve not admitted");tick();@(negedge stream_clk);reserve_v=0;
  n=0;while((fetched_ready&(half?8'haa:8'h55))!=(half?8'haa:8'h55))begin
   tick();n=n+1;if(n>10000)$fatal(1,"PHY block completion timeout");
  end
 end endtask
 task drain(input bit half);begin
  @(negedge stream_clk);drain_half=half;drain_v=1;tick();@(negedge stream_clk);drain_v=0;
  //40 fixed bursts II8, then serializer/landing pipeline: no ready tests.
  idle(330);
 end endtask
 task deliver(input bit half);begin
  @(negedge stream_clk);deliver_half=half;deliver_v=1;tick();@(negedge stream_clk);deliver_v=0;
  idle(264);
 end endtask
 initial begin:run
  integer slot,r,b,q,pos,row_start,prefetch0_done,prefetch1_done,drain0_done,drain1_done,padding_done,delivery0_done;reg [255:0] expected;
  if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"IMAGE required");$readmemh(image_path,image);
  for(integer i=0;i<128;i=i+1)begin pending[i]=0;delay_q[i]=0;end
  idle(4);stream_rst_n=1;hbm_rst_n=1;idle(12);
  for(slot=0;slot<2;slot=slot+1)begin
   row_slot=slot;row_epoch=16'h6001+slot;row_start=stream_cycles;pulse_row();reserve(0);prefetch0_done=stream_cycles;reserve(1);prefetch1_done=stream_cycles;drain(0);drain0_done=stream_cycles;drain(1);drain1_done=stream_cycles;
   pad_v=1;tick();@(negedge stream_clk);pad_v=0;idle(196);padding_done=stream_cycles;
   if(delivery_ready!=3)$fatal(1,"two full actual landing blocks missing %b",delivery_ready);
   deliver(0);delivery0_done=stream_cycles;deliver(1);
   $display("HC_PREFETCH_PHASE slot=%0d start=%0d prefetch0_ready=%0d prefetch1_ready=%0d drain0_end=%0d drain1_end=%0d pad_end=%0d deliver0_end=%0d last_ap_commit=%0d all_done=%0d",slot,row_start,prefetch0_done,prefetch1_done,drain0_done,drain1_done,padding_done,delivery0_done,last_ap_commit,stream_cycles);
   for(r=0;r<128;r=r+1)begin
    @(negedge stream_clk);read_v=255;read_slot={8{1'(slot)}};
    for(b=0;b<8;b=b+1)read_row[b*7+:7]=r;
    tick();if(read_valid!=255)$fatal(1,"missing actual aperture read");
    for(b=0;b<8;b=b+1)for(q=0;q<4;q=q+1)begin
     pos=r*4+q;expected=pos<320?image[b*320+pos]:256'd0;
     if(raw_weight[b*1024+q*256+:256]!==expected)$fatal(1,"actual aperture memory mismatch slot%0d bank%0d position%0d",slot,b,pos);
     checked=checked+1;
    end
   end
   @(negedge stream_clk);read_v=0;idle(3);
  end
  if(requests!=5120||responses!=5120||checked!=8192||fault)$fatal(1,"count/fault mismatch");
  $display("HC_PREFETCH_STATIC PASS requests=%0d responses=%0d actualSRAMreadbacks=%0d cycles=%0d slots=2 paddingSectors=3072 HBMclock1024 streamclock833",requests,responses,checked,stream_cycles);$finish;
 end
 initial begin #50000000;$fatal(1,"timeout");end
endmodule
