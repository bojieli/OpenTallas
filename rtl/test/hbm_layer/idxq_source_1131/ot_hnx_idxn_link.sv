`default_nettype none
// HBM-NEXT-UNITS-IDXN 2026-10-19: copy-fork of rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv (core + pin shell)
// with ROW SLOTS for pipelined N-row IDX.INDEX records. The 8 real 64 x 512 banks held one row (64 flits = 8 bank
// rows); they now hold 8 row slots (bank row = 8 x slot + flit / 8, the macros' unused rows), so row r+1 is ingested
// (slot (r+1) mod 8) while row r is still being emitted (slot r mod 8): 1R1W banks, no new SRAM.
// Ingest side: `row_clear` (the frame's link clear, [5]&[4]) opens slot `in_slot` (counters reset); `flush` closes it
// (512 records, 64 flits, no carry) and marks it FULL. Emit side: `emit_v` reads slot `emit_slot`, group order as d4g;
// group 15 empties the slot. Faults (static schedule, collision = fault): ingest into a FULL slot or with no open slot,
// clear of a slot still FULL (unemitted results), emit of a slot that is not FULL, the d4g flush/count checks.
// `clear` (record start) resets everything to slot 0 open: with the d4g programme (no row clear) this is the d4g link.
module ot_hnx_idxn_link_core #(parameter integer MUT=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,row_clear,input wire[2:0]in_slot,input wire ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[2:0]emit_slot,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output wire[9:0]selected_count
);
 reg[4607:0]carry;
 reg[2:0]fill;
 reg[6:0]flits;
 reg[9:0]total;
 reg[2:0]wslot;reg open;reg[7:0]full;
 assign selected_count=total;
 reg[4607:0]packed_next;
 integer n,nf,count,bank,row;
 reg[7:0]we;
 reg[47:0]wa;
 reg[4095:0]wd;
 wire[4095:0]rd;
 reg[511:0]flit;
 reg[63:0]record;
 always @*begin
  packed_next=carry;n=int'(fill);count=0;
  if(ingest_v)for(integer q=0;q<4;q=q+1)for(integer l=0;l<16;l=l+1)begin
   if(selected_line[q*592+l*37])begin
    record={12'd0,selected_line[q*592+l*37+17+:20],selected_line[q*592+l*37+1+:16],16'd0};
    packed_next[n*64+:64]=record;n=n+1;count=count+1;
   end
  end
  nf=n/8;we=0;wa=0;wd=0;flit=0;bank=0;row=0;
  for(integer j=0;j<8;j=j+1)if(j<nf)begin
   flit=0;
   for(integer r=0;r<8;r=r+1)begin
    flit[r*32+:32]=packed_next[(j*8+r)*64+:32];
    flit[256+r*32+:32]=packed_next[(j*8+r)*64+32+:32];
   end
   bank=(int'(flits)+j)%8;row=(int'(flits)+j)/8;
   we[bank]=1;wa[bank*6+:6]=6'(int'(wslot)*8+row);wd[bank*512+:512]=flit;
  end
 end
 for(genvar b=0;b<8;b=b+1)begin:gm
  wire re=emit_v&&(b/4==int'(emit_group[0]));
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(clk_mem[b]),.r_ce_in(re),.r_addr_in({emit_slot,emit_group[3:1]}),.rd_out(rd[b*512+:512]),
   .w_ce_in(we[b]),.w_addr_in(wa[b*6+:6]),.wd_in(wd[b*512+:512]),.w_mask_in({512{1'b1}}),
   .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
 end
 reg read_v;reg[3:0]read_group;reg[7:0]read_rank,read_gbase;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin carry<=0;fill<=0;flits<=0;total<=0;fault<=0;read_v<=0;tx_v<=0;read_group<=0;read_rank<=0;read_gbase<=0;
   wslot<=0;open<=0;full<=0;end
  else begin
   read_v<=emit_v;read_group<=emit_group;read_rank<=rank;read_gbase<=gbase;tx_v<={4{read_v}};
   if(clear)begin carry<=0;fill<=0;flits<=0;total<=0;wslot<=0;open<=1;full<=0;end
   else if(row_clear)begin
    carry<=0;fill<=0;flits<=0;total<=0;wslot<=in_slot;open<=1;
    if(full[in_slot]||(open&&total!=0))fault<=1;            // overwrite of unemitted results / of an open row
   end
   if(ingest_v)begin
    carry<=packed_next>>(nf*512);fill<=3'(n%8);flits<=flits+7'(nf);total<=total+10'(count);
    if(int'(total)+count>512||int'(flits)+nf>64||!open||full[wslot])fault<=1;
   end
   if(emit_v&&rank<gbase)fault<=1;
   if(flush)begin
    if(total!=512||flits!=64||fill!=0||!open)fault<=1;
    else begin full[wslot]<=1;open<=0;end
   end
   if(emit_v)begin
    if(!full[emit_slot])fault<=1;
    else if(emit_group==4'd15)full[emit_slot]<=0;
   end
   if((clear||row_clear)&&ingest_v)fault<=1;
   for(integer l=0;l<4;l=l+1)if(read_v)begin
    tx[l*545+:545]<={1'b1,8'hff,read_rank,16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l),rd[(int'(read_group[0])*4+l)*512+:512]};
   end
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// PIN-REGISTERED TILE (as the d4g ot_hbm_idx_topk_link_static shell): every data input and output passes ONE kept flop.
module ot_hnx_idxn_link #(parameter integer MUT=0)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,row_clear,input wire[2:0]in_slot,input wire ingest_v,input wire[2367:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[2:0]emit_slot,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output reg[9:0]selected_count
);
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg clear_r,rclear_r,ingest_r,flush_r,emit_r;(* keep *) reg[2367:0]line_r;(* keep *) reg[3:0]group_r;
 (* keep *) reg[2:0]islot_r,eslot_r;(* keep *) reg[7:0]rank_r,gbase_r;
 wire[3:0]c_tx_v;wire[2179:0]c_tx;wire c_fault;wire[9:0]c_count;
 always @(posedge clk)begin
  clear_r<=clear;rclear_r<=row_clear;islot_r<=in_slot;ingest_r<=ingest_v;line_r<=selected_line;flush_r<=flush;emit_r<=emit_v;
  group_r<=emit_group;eslot_r<=emit_slot;rank_r<=rank;gbase_r<=gbase;
  tx_v<=c_tx_v;tx<=c_tx;fault<=c_fault;selected_count<=c_count;
 end
 ot_hnx_idxn_link_core #(.MUT(MUT)) core(.clk(clk),.clk_mem(clk_mem),.rst_n(rst_core_n),.clear(clear_r),.row_clear(rclear_r),
  .in_slot(islot_r),.ingest_v(ingest_r),.selected_line(line_r),.flush(flush_r),.emit_v(emit_r),.emit_group(group_r),
  .emit_slot(eslot_r),.rank(rank_r),.gbase(gbase_r),.tx_v(c_tx_v),.tx(c_tx),.fault(c_fault),.selected_count(c_count));
endmodule
`default_nettype wire
