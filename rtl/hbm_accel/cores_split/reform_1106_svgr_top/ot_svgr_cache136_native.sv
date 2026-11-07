// Native source-preserving helper cut. RW_SRAM defaults OFF. Source SHA256 f06fc1118b435ef275bf52bcd152c33fa8dab4bf56bf8659afab372c8dd20fc5
`default_nettype none
// Static successor reuses ot_gpu_payload_assemble's exact 1280-bit gather,
// phase*64 shift and 4/4/4/5 head advance. Its handshake machinery is absent.
// Source sectors follow 4,4,4,4,1 fixed pulses per five edges; missing slots
// fault, never hold/retry. Each record is 128 weight bytes then8 scale bytes.
// HBM-GAPS-8 SVGR_TOP P1: WPIPE 1 = the row commit (SRAM write port, tags[] and valid[]) is registered one edge after the
// row slot, so the 5-of-16 gather + shift ends at a register, not at the SRAM pins; ready/busy follow one edge later.
// DIE-HBM-87 vL7 (all default 0 = unchanged):
//  WDECOUPLE 1: an arriving sector writes its staging word whenever sector_v[i] (in the running && !sticky slot); the
//   index / epoch / present compare only sets sticky (words[] and present[] are written by sector_v alone).  Exact at
//   the ports: sticky never clears except by reset; a word / present bit written in a mismatch edge is read (gather,
//   complete) one edge later at the earliest, and from then on row_write (hence the SRAM write, WPIPE or not),
//   out_valid, open_ok and the whole running branch are off, and present[] is cleared only by open_ok or reset.
//  GSEL 1: the five gather selects (head+j)%16 are registered one-hot vectors (reset / open: 1<<j, row advance: rotate
//   by 4 or 5 with head); gather, complete and the present clear use them, no adder or decode in front of the mux.
//   GREP = kept replicas per gather lane (each drives 256/GREP bits).  Cycle-exact.
module ot_svgr_cache136_native #(parameter integer PACKED136=0, parameter integer RW_SRAM=0, parameter integer WPIPE=0,
 parameter integer WDECOUPLE=0,parameter integer GSEL=0,parameter integer GREP=1)(
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
  reg [1:0] ready;integer b,r,j,gk,gc;
  localparam integer GCW=256/GREP;wire [80*GREP-1:0] gsel;
  wire [255:0] cache_data[0:4];reg out_valid;reg [9:0] out_tag;
  wire [6:0] read_addr={read_bank,read_row};
  wire row_slot=running&&elapsed>=2&&slot_phase!=1&&emitted<load_rows;
  wire [1087:0] row_data=gathered>>(record_phase*64);
  wire row_write=row_slot&&complete&&!sticky;
  reg w_q;reg[6:0]w_addr_q;reg[9:0]w_tag_q;reg[1087:0]w_data_q;
  wire c_we=(WPIPE!=0)?w_q:row_write;wire[6:0]c_wa=(WPIPE!=0)?w_addr_q:{load_bank,emitted[5:0]};
  wire[1087:0]c_wd=(WPIPE!=0)?w_data_q:row_data;
  always @(posedge clk)if(WPIPE!=0)begin w_addr_q<={load_bank,emitted[5:0]};w_tag_q<=tag_base+emitted;w_data_q<=row_data;end
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
    if(GSEL!=0)begin
     if((gsel[j*GREP*16+:16]&present)==16'd0)complete=0;
     for(gk=0;gk<16;gk=gk+1)for(gc=0;gc<GREP;gc=gc+1)
      if(gsel[(j*GREP+gc)*16+gk])gathered[j*256+gc*GCW+:GCW]=gathered[j*256+gc*GCW+:GCW]|words[gk][gc*GCW+:GCW];
    end else begin
    if(!present[(head+j)%16])complete=0;
    gathered[j*256+:256]=words[(head+j)%16];
    end
   end
   if(running&&received<total_sectors)begin
    expected_sectors=slot_phase==4?1:4;
    if(total_sectors-received<expected_sectors)expected_sectors=total_sectors-received;
   end
  end
  assign block_ready=ready;assign bank_owned=owned;assign busy=running||((WPIPE!=0)&&w_q);assign fault=sticky;
  assign out_packet={out_valid&&!sticky,out_tag,cache_data[4][63:0],cache_data[3],cache_data[2],cache_data[1],cache_data[0]};
`ifdef CACHE_TRACE
  // Diagnostic only: report the exact violated existing predicate, never change it.
  always @(posedge clk)if(rst_n)begin
   if(open_v)$display("CACHE_OPEN bank=%0d epoch=%0d count=%0d ok=%0d running=%0d owned=%b emitted=%0d rows=%0d received=%0d total=%0d",open_bank,open_epoch,open_count,open_ok,running,owned,emitted,load_rows,received,total_sectors);
   if(read_v&&!read_ok)$display("CACHE_READ_BAD bank=%0d ready=%b epoch=%0d expected_epoch=%0d row=%0d count=%0d tag=%0d expected_tag=%0d sticky=%0d retire_collision=%0d",read_bank,ready,read_epoch,epoch[read_bank],read_row,count[read_bank],read_tag,tags[read_addr],sticky,retire_v&&retire_bank==read_bank);
   if(retire_v)$display("CACHE_RETIRE bank=%0d epoch=%0d expected=%0d owned=%b running=%0d load_bank=%0d read_collision=%0d open_collision=%0d",retire_bank,retire_epoch,epoch[retire_bank],owned,running,load_bank,read_v&&read_bank==retire_bank,open_v&&open_bank==retire_bank);
  end
`endif
  integer i;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    owned<=0;epoch[0]<=0;epoch[1]<=0;count[0]<=0;count[1]<=0;valid[0]<=0;valid[1]<=0;
    running<=0;load_bank<=0;sticky<=0;load_epoch<=0;load_rows<=0;emitted<=0;tag_base<=0;received<=0;total_sectors<=0;
    head<=0;slot_phase<=0;elapsed<=0;record_phase<=0;present<=0;out_valid<=0;out_tag<=0;w_q<=0;
    for(i=0;i<128;i=i+1)tags[i]<=0;
   end else begin
    out_valid<=read_ok;if(read_ok)out_tag<=tags[read_addr];
    w_q<=(WPIPE!=0)&&row_write;
    if(WPIPE!=0&&w_q)begin tags[w_addr_q]<=w_tag_q;valid[w_addr_q[6]][w_addr_q[5:0]]<=1;end
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
       else if(WDECOUPLE==0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end
       if(WDECOUPLE!=0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end
      end
     end
     received<=received+expected_sectors;
     if(row_slot)begin
      if(!complete)sticky<=1;
      else begin
       if(WPIPE==0)begin tags[{load_bank,emitted[5:0]}]<=tag_base+emitted;valid[load_bank][emitted[5:0]]<=1;end
       emitted<=emitted+1'b1;
       if(GSEL!=0)begin for(i=0;i<5;i=i+1)if(i<(record_phase==3?5:4))for(gk=0;gk<16;gk=gk+1)if(gsel[i*GREP*16+gk])present[gk]<=0;end
       else
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
  if(GSEL!=0)begin:g_gsel
   // one-hot of (head+j)%16 per gather lane j and replica c; head changes only at reset, open_ok (head<=0) and the row
   // advance (running && !sticky && row_slot && complete: head += 4 or 5), so the vectors follow it edge for edge.
   (* keep *) reg [80*GREP-1:0] q;integer qj,qc;
   always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)q[(qj*GREP+qc)*16+:16]<=16'd1<<qj;end
    else if(open_ok)begin for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)q[(qj*GREP+qc)*16+:16]<=16'd1<<qj;end
    else if(running&&!sticky&&row_slot&&complete)begin
     for(qj=0;qj<5;qj=qj+1)for(qc=0;qc<GREP;qc=qc+1)
      q[(qj*GREP+qc)*16+:16]<=(record_phase==3)?{q[(qj*GREP+qc)*16+:11],q[(qj*GREP+qc)*16+11+:5]}
                                              :{q[(qj*GREP+qc)*16+:12],q[(qj*GREP+qc)*16+12+:4]};
    end
   end
   assign gsel=q;
  end else begin:g_nsel
   assign gsel=0;
  end
  genvar p;for(p=0;p<5;p=p+1)begin:g_cache
   wire [1279:0] padded_row={192'b0,c_wd};
   wire [255:0] write_data=padded_row[p*256+:256];
   if (RW_SRAM!=0) begin:g_rw
    ot_sram_1r1w_128x256_m1_r0c0_g256 u_payload(
     .clk(clk),.r_ce_in(read_ok),.r_addr_in(read_addr),.rd_out(cache_data[p]),
     .w_ce_in(c_we),.w_addr_in(c_wa),.wd_in(write_data),.w_mask_in(1'b1));
   end else begin:g_original
   ot_sram_1r1w_128x256_m1_r2c2 u_payload(
    .clk(clk),.r_ce_in(read_ok),.r_addr_in(read_addr),.rd_out(cache_data[p]),
    .w_ce_in(c_we),.w_addr_in(c_wa),.wd_in(write_data),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
   end
  end
 end endgenerate
endmodule
`default_nettype wire
