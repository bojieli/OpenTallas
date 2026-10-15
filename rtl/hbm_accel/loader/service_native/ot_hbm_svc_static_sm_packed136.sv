`default_nettype none
// Static successor reuses ot_gpu_payload_assemble's exact 1280-bit gather,
// phase*64 shift and 4/4/4/5 head advance. Its handshake machinery is absent.
// Source sectors follow 4,4,4,4,1 fixed pulses per five edges; missing slots
// fault, never hold/retry. Each record is 128 weight bytes then8 scale bytes.
module ot_hbm_svc_static_sm_packed136 #(parameter integer PACKED136=0)(
 input wire clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,input wire [9:0] open_tag_base,
 input wire [3:0] sector_v,input wire [95:0] sector_index,input wire [63:0] sector_epoch,input wire [1023:0] sector_data,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_row,input wire [9:0] read_tag,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 output wire [1:0] block_ready,bank_owned,output wire busy,fault,output wire [1098:0] out_packet
);
 generate if(!PACKED136)begin:g_off
  assign block_ready=0;assign bank_owned=0;assign busy=0;assign fault=0;assign out_packet=0;
 end else begin:g_on
  reg [1:0] owned;reg [15:0] epoch[0:1];reg [6:0] count[0:1];
  reg [63:0] valid[0:1];reg [9:0] tags[0:127];
  reg running,load_bank,sticky;reg [15:0] load_epoch;reg [6:0] load_rows,emitted;
  reg [9:0] tag_base;reg [8:0] received,total_sectors,head;
  reg [2:0] slot_phase;reg [8:0] elapsed;
  reg [1:0] record_phase;reg [15:0] present;reg [255:0] words[0:15];
  reg [1279:0] gathered;reg complete;reg [2:0] expected_sectors;
  reg [1:0] ready;integer b,r,j;
  wire [255:0] cache_data[0:4];reg out_valid;reg [9:0] out_tag;
  wire [6:0] read_addr={read_bank,read_row};
  wire row_slot=running&&elapsed>=2&&slot_phase!=1&&emitted<load_rows;
  wire [1087:0] row_data=gathered>>(record_phase*64);
  wire row_write=row_slot&&complete&&!sticky;
  wire open_ok=open_v&&!running&&!owned[open_bank]&&open_count!=0&&open_count<=64&&!sticky&&!(retire_v&&retire_bank==open_bank);
  wire read_ok=read_v&&ready[read_bank]&&read_epoch==epoch[read_bank]&&{1'b0,read_row}<count[read_bank]&&
    read_tag==tags[read_addr]&&!sticky&&!(retire_v&&retire_bank==read_bank);
  always @*begin
   ready=owned;complete=1;gathered=0;expected_sectors=0;
   for(b=0;b<2;b=b+1)begin
    if(count[b]==0)ready[b]=0;
    for(r=0;r<64;r=r+1)if(r<count[b]&&!valid[b][r])ready[b]=0;
   end
   for(j=0;j<5;j=j+1)begin
    if(!present[(head+j)%16])complete=0;
    gathered[j*256+:256]=words[(head+j)%16];
   end
   if(running&&received<total_sectors)begin
    expected_sectors=slot_phase==4?1:4;
    if(total_sectors-received<expected_sectors)expected_sectors=total_sectors-received;
   end
  end
  assign block_ready=ready;assign bank_owned=owned;assign busy=running;assign fault=sticky;
  assign out_packet={out_valid&&!sticky,out_tag,cache_data[4][63:0],cache_data[3],cache_data[2],cache_data[1],cache_data[0]};
  integer i;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    owned<=0;epoch[0]<=0;epoch[1]<=0;count[0]<=0;count[1]<=0;valid[0]<=0;valid[1]<=0;
    running<=0;load_bank<=0;sticky<=0;load_epoch<=0;load_rows<=0;emitted<=0;tag_base<=0;received<=0;total_sectors<=0;
    head<=0;slot_phase<=0;elapsed<=0;record_phase<=0;present<=0;out_valid<=0;out_tag<=0;
    for(i=0;i<128;i=i+1)tags[i]<=0;
   end else begin
    out_valid<=read_ok;if(read_ok)out_tag<=tags[read_addr];
    if(open_v&&!open_ok)sticky<=1;
    if(open_ok)begin
     owned[open_bank]<=1;epoch[open_bank]<=open_epoch;count[open_bank]<=open_count;valid[open_bank]<=0;
     running<=1;load_bank<=open_bank;load_epoch<=open_epoch;load_rows<=open_count;emitted<=0;tag_base<=open_tag_base;
     received<=0;total_sectors<=((open_count*136+127)/128)*4;head<=0;slot_phase<=0;elapsed<=0;record_phase<=0;present<=0;
    end
    if(read_v&&!read_ok)sticky<=1;
    if(running&&!sticky)begin
     slot_phase<=slot_phase==4?0:slot_phase+1'b1;elapsed<=elapsed+1'b1;
     for(i=0;i<4;i=i+1)begin
      if(sector_v[i]!=(i<expected_sectors))sticky<=1;
      if(sector_v[i])begin
       if(sector_epoch[i*16+:16]!=load_epoch||sector_index[i*24+:24]!=received+i||present[(received+i)%16])sticky<=1;
       else begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end
      end
     end
     received<=received+expected_sectors;
     if(row_slot)begin
      if(!complete)sticky<=1;
      else begin
       tags[{load_bank,emitted[5:0]}]<=tag_base+emitted;
       valid[load_bank][emitted[5:0]]<=1;emitted<=emitted+1'b1;
       for(i=0;i<5;i=i+1)if(i<(record_phase==3?5:4))present[(head+i)%16]<=0;
       head<=head+(record_phase==3?5:4);record_phase<=record_phase+1'b1;
      end
     end
     if(emitted==load_rows&&received==total_sectors)running<=0;
    end else if(!open_v&&|sector_v)sticky<=1;
    if(retire_v)begin
     if(!owned[retire_bank]||retire_epoch!=epoch[retire_bank]||(running&&load_bank==retire_bank)||
       (read_v&&read_bank==retire_bank)||(open_v&&open_bank==retire_bank))sticky<=1;
     else owned[retire_bank]<=0;
    end
   end
  end
  genvar p;for(p=0;p<5;p=p+1)begin:g_cache
   wire [1279:0] padded_row={192'b0,row_data};
   wire [255:0] write_data=padded_row[p*256+:256];
   ot_sram_1r1w_128x256_m1_r2c2 u_payload(
    .clk(clk),.r_ce_in(read_ok),.r_addr_in(read_addr),.rd_out(cache_data[p]),
    .w_ce_in(row_write),.w_addr_in({load_bank,emitted[5:0]}),.wd_in(write_data),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
 end endgenerate
endmodule
`default_nettype wire
