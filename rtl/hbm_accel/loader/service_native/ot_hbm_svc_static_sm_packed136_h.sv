`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED ot_hbm_svc_static_sm_packed136 #(PACKED136 1) (that module stays byte-identical):
// same ports, same cache SRAMs (5 x 128x256), same open / read / retire rules, same out_packet on every edge, same
// faults in every fault-free run.  The r11 mapped netlist had 4.7k / 3.5k / ~30 x 1.28k-load row-decode nets here and a
// 4 kb runtime-indexed flop ring.  Structure now:
//   * GATHER = a 2-edge sector pipeline, not a 16 x 256 b ring: the source pattern is fixed (4,4,4,4,1 sectors per 5
//     edges from the open, every other pattern is a sticky fault), so row n of a fill (record phase k = n % 4, group
//     g = n / 4, written at elapsed 5g + 2 + k) is always {sector 17g+4k+4 = lane 0 of the edge before, sectors
//     17g+4k .. +3 = lanes 0..3 of two edges before} >> 64k.  d1 / d2 capture the sector bus every edge (no enables);
//     the 4:1 record-phase shift uses REGISTERED one-hot phase copies, KEPT per 32-bit slice.  The original's
//     `complete' (all 5 sectors present) holds by construction whenever no sticky fault is set, and a missing,
//     extra, out-of-order or wrong-epoch sector is the same sticky fault as before (lane valid / index / epoch checks
//     unchanged), so row_write is identical;
//   * TAGS: tags[{bank,row}] was written tag_base + row at the row's write and read only for a READY bank (every row of
//     the current fill written), so it is replaced by the per-bank tag base: expected tag = tag_base[bank] + row, and
//     out_tag = read_tag on a passing read;
//   * VALID: ready[b] = owned && count != 0 && every row < count written in this fill == owned && count != 0 &&
//     filled[b] (rows are written in order; filled set with the last row, cleared at the bank's open);
//   * reset only on control (owned, filled, running, sticky, out_valid); datapath unreset.
module ot_hbm_svc_static_sm_packed136_h (
 input wire clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,input wire [9:0] open_tag_base,
 input wire [3:0] sector_v,input wire [95:0] sector_index,input wire [63:0] sector_epoch,input wire [1023:0] sector_data,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_row,input wire [9:0] read_tag,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 output wire [1:0] block_ready,bank_owned,output wire busy,fault,output wire [1098:0] out_packet
);
 localparam integer NPS=34;                          // 1088-bit row = 34 x 32-bit slices
 reg [1:0] owned,filled;reg [15:0] epoch[0:1];reg [6:0] count[0:1];reg [9:0] tagb[0:1];
 reg running,load_bank,sticky;reg [15:0] load_epoch;reg [6:0] load_rows,emitted;
 reg [8:0] received,total_sectors;
 reg [2:0] slot_phase;reg [8:0] elapsed;
 reg [1:0] record_phase;
 (* keep="true",dont_touch="true" *) reg [4*NPS-1:0] rph_k;   // [slice*4+k] = (record_phase == k)
 reg [1023:0] d1,d2;
 reg [2:0] expected_sectors;reg [1:0] ready;integer b,j,i;
 wire [255:0] cache_data[0:4];reg out_valid;reg [9:0] out_tag;
 wire [6:0] read_addr={read_bank,read_row};
 wire row_slot=running&&elapsed>=2&&slot_phase!=1&&emitted<load_rows;
 wire [1279:0] gathered={d1[255:0],d2};
 reg [1087:0] row_data;
 always @*begin
  for(i=0;i<1088;i=i+1)begin
   row_data[i]=0;
   for(j=0;j<4;j=j+1)if(rph_k[(i/32)*4+j])row_data[i]=row_data[i]|gathered[i+64*j];
  end
 end
 wire row_write=row_slot&&!sticky;
 wire open_ok=open_v&&!running&&!owned[open_bank]&&open_count!=0&&open_count<=64&&!sticky&&!(retire_v&&retire_bank==open_bank);
 wire [9:0] exp_tag=tagb[read_bank]+{4'd0,read_row};
 wire read_ok=read_v&&ready[read_bank]&&read_epoch==epoch[read_bank]&&{1'b0,read_row}<count[read_bank]&&
   read_tag==exp_tag&&!sticky&&!(retire_v&&retire_bank==read_bank);
 always @*begin
  expected_sectors=0;
  for(b=0;b<2;b=b+1)ready[b]=owned[b]&&count[b]!=0&&filled[b];
  if(running&&received<total_sectors)begin
   expected_sectors=slot_phase==4?1:4;
   if(total_sectors-received<expected_sectors)expected_sectors=3'(total_sectors-received);
  end
 end
 assign block_ready=ready;assign bank_owned=owned;assign busy=running;assign fault=sticky;
 assign out_packet={out_valid&&!sticky,out_tag,cache_data[4][63:0],cache_data[3],cache_data[2],cache_data[1],cache_data[0]};
 // next record phase (registered one-hot copies)
 wire [1:0] rph_n=open_ok?2'd0:((running&&!sticky&&row_slot)?record_phase+2'd1:record_phase);
 // next running / owned (registered + KEPT copies that enable the datapath captures)
 wire retire_ok=retire_v&&!(!owned[retire_bank]||retire_epoch!=epoch[retire_bank]||(running&&load_bank==retire_bank)||
      (read_v&&read_bank==retire_bank)||(open_v&&open_bank==retire_bank));
 wire run_end=running&&!sticky&&emitted==load_rows&&received==total_sectors;
 wire running_n=open_ok?1'b1:(run_end?1'b0:running);
 reg [1:0] owned_n;
 always @*begin
  owned_n=owned;
  if(open_ok)owned_n[open_bank]=1;
  if(retire_ok)owned_n[retire_bank]=0;
 end
 (* keep="true",dont_touch="true" *) reg [1:0] nrun_k;   // = !running: the fill registers load while idle (61 flops)
 (* keep="true",dont_touch="true" *) reg [3:0] nown_k;   // [b*2+c] = !owned[b]: bank fields load while unowned (33 flops)
 // control
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   owned<=0;filled<=0;running<=0;sticky<=0;out_valid<=0;nrun_k<=2'b11;nown_k<=4'hf;
  end else begin
   out_valid<=read_ok;running<=running_n;owned<=owned_n;
   nrun_k<={2{!running_n}};nown_k<={{2{!owned_n[1]}},{2{!owned_n[0]}}};
   if(open_v&&!open_ok)sticky<=1;
   if(open_ok)filled[open_bank]<=0;
   if(read_v&&!read_ok)sticky<=1;
   if(running&&!sticky)begin
    for(i=0;i<4;i=i+1)begin
     if(sector_v[i]!=(i<expected_sectors))sticky<=1;
     if(sector_v[i]&&(sector_epoch[i*16+:16]!=load_epoch||sector_index[i*24+:24]!=24'(received)+i))sticky<=1;
    end
    if(row_slot&&emitted+1'b1==load_rows)filled[load_bank]<=1;
   end else if(!open_v&&|sector_v)sticky<=1;
   if(retire_v&&!retire_ok)sticky<=1;
  end
 end
 // datapath (no reset): bank fields while the bank is unowned, fill registers while idle, counters while running
 always @(posedge clk)begin
  d1<=sector_data;d2<=d1;
  for(i=0;i<NPS;i=i+1)for(j=0;j<4;j=j+1)rph_k[i*4+j]<=rph_n==j;
  record_phase<=rph_n;
  if(read_ok)out_tag<=read_tag;
  for(b=0;b<2;b=b+1)begin
   if(nown_k[b*2])begin epoch[b]<=open_epoch;count[b]<=open_count;end
   if(nown_k[b*2+1])tagb[b]<=open_tag_base;
  end
  if(nrun_k[0])begin load_bank<=open_bank;load_epoch<=open_epoch;load_rows<=open_count;emitted<=0;end
  if(nrun_k[1])begin received<=0;total_sectors<=9'(((open_count*136+127)/128)*4);slot_phase<=0;elapsed<=0;end
  if(running&&!sticky)begin
   slot_phase<=slot_phase==4?0:slot_phase+1'b1;elapsed<=elapsed+1'b1;
   received<=received+expected_sectors;
   if(row_slot)emitted<=emitted+1'b1;
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
endmodule
`default_nettype wire
