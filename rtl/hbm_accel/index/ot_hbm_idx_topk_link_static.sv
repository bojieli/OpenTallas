`default_nettype none
// Actual512-result native collective producer. Eight real memory banks absorb
// up to64chosen records/edge. Compiler issues exactly171ingest edges, fixed
// flush, then16 four-flit emit beats at8-edge intervals. No ready/credits.
// NL (HBM-BIND B2 2026-10-24, lane hbm-bind-idx): number of 16-lane selector lists on selected_line (NL*592 b) =
// the selector's NL. Default 4 = as built (bit-identical; bench rtl/test/hbm_idx_static/run_idx_link_nl.sh). The ingest
// packs up to 16*NL records an edge (lists 0..NL-1, lanes 0..15, in that order); the carry holds (16*NL+8) records
// (4,608 b at NL 4). The eight 64 x 512 banks, the 512-record / 64-flit frame, the 16 four-flit emit beats and every
// edge are unchanged. B2 die (NW + NE): NL 1 (list 0 = {NE, NW}, as list 1 of the as-built 4-list master).
// MUT 3 (bench only): list NL-1 is not ingested.
module ot_hbm_idx_topk_link_static_core #(parameter integer MUT=0, parameter integer NL=4)(
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[NL*592-1:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output wire[9:0]selected_count
);
 localparam integer CW=(16*NL+8)*64;
 reg[CW-1:0]carry;
 reg[2:0]fill;
 reg[6:0]flits;
 reg[9:0]total;
 assign selected_count=total;
 reg[CW-1:0]packed_next;
 integer n,nf,count,bank,row;
 reg[7:0]we;
 reg[47:0]wa;
 reg[4095:0]wd;
 wire[4095:0]rd;
 reg[511:0]flit;
 reg[63:0]record;
 always @*begin
  packed_next=carry;n=int'(fill);count=0;
  if(ingest_v)for(integer q=0;q<((MUT==3)?NL-1:NL);q=q+1)for(integer l=0;l<16;l=l+1)begin
   if(selected_line[q*592+l*37])begin
    record={12'd0,selected_line[q*592+l*37+17+:20],selected_line[q*592+l*37+1+:16],16'd0};
    if(MUT==1)record={record[31:0],record[63:32]};
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
   we[bank]=1;wa[bank*6+:6]=6'(row);wd[bank*512+:512]=flit;
  end
 end
 for(genvar b=0;b<8;b=b+1)begin:gm
  wire re=emit_v&&(b/4==int'(emit_group[0]));
  ot_sram_1r1w_64x512_m1_r2c2 mem(.clk(clk_mem[b]),.r_ce_in(re),.r_addr_in({3'd0,emit_group[3:1]}),.rd_out(rd[b*512+:512]),
   .w_ce_in(we[b]),.w_addr_in(wa[b*6+:6]),.wd_in(wd[b*512+:512]),.w_mask_in({512{1'b1}}),
   .rr_en(2'd0),.rr_addr(12'd0),.cr_en(2'd0),.cr_sel(18'd0));
 end
 reg read_v;reg[3:0]read_group;reg[7:0]read_rank,read_gbase;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin carry<=0;fill<=0;flits<=0;total<=0;fault<=0;read_v<=0;tx_v<=0;read_group<=0;read_rank<=0;read_gbase<=0;end
  else begin
   read_v<=emit_v;read_group<=emit_group;read_rank<=rank;read_gbase<=gbase;tx_v<={4{read_v}};
   if(clear)begin carry<=0;fill<=0;flits<=0;total<=0;end
   if(ingest_v)begin
    carry<=packed_next>>(nf*512);fill<=3'(n%8);flits<=flits+7'(nf);total<=total+10'(count);
    if(int'(total)+count>512||int'(flits)+nf>64)fault<=1;
   end
   if(emit_v&&rank<gbase)fault<=1;
   if(flush&&(total!=512||flits!=64||fill!=0))fault<=1;
   if((clear&&ingest_v)||(emit_v&&(ingest_v||flits!=64)))fault<=1;
   for(integer l=0;l<4;l=l+1)if(read_v)begin
    tx[l*545+:545]<={1'b1,8'hff,read_rank,16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l),rd[(int'(read_group[0])*4+l)*512+:512]};
    if(MUT==2)tx[l*545+512+:16]<=16'((int'(read_rank)-int'(read_gbase))*64+int'(read_group)*4+l)^16'd1;
   end
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// ---------------------------------------------------------------------------
// PIN-REGISTERED TILE (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): the die
// master ot_hbm_idx_topk_link_static is this shell. Every data input and every output passes ONE kept
// flop at the pin (clocks pass through; rst_n enters a 2-flop release synchroniser); the unchanged arithmetic/control is
// ot_hbm_idx_topk_link_static_core. Latency: +1 edge on every input, +1 edge on every output; the IDX
// calendar compiler (tools/hbm_idx_static_calendar.py, PIN table) schedules them.
// Pin flops have no reset (as physical/common_flow/ot_pin_regs.tcl); the core is reset.
module ot_hbm_idx_topk_link_static #(parameter integer MUT=0, parameter integer NL=4)(   // NL: see the core
 input wire clk,input wire[7:0]clk_mem,input wire rst_n,
 input wire clear,ingest_v,input wire[NL*592-1:0]selected_line,
 input wire flush,emit_v,input wire[3:0]emit_group,input wire[7:0]rank,gbase,
 output reg[3:0]tx_v,output reg[2179:0]tx,
 output reg fault,output reg[9:0]selected_count
);
 // rst_n: async assert, 2-edge release on clk; the core's resets (async and synchronous uses on every
 // same-PLL phase-0 root) come from this one kept register, so no input port feeds another root's data pins.
 (* keep *) reg [1:0] rst_sync;
 always @(posedge clk or negedge rst_n) if(!rst_n) rst_sync<=2'b00; else rst_sync<={rst_sync[0],1'b1};
 wire rst_core_n=rst_sync[1];
 (* keep *) reg clear_r,ingest_r,flush_r,emit_r;(* keep *) reg[NL*592-1:0]line_r;(* keep *) reg[3:0]group_r;(* keep *) reg[7:0]rank_r,gbase_r;
 wire[3:0]c_tx_v;wire[2179:0]c_tx;wire c_fault;wire[9:0]c_count;
 always @(posedge clk)begin
  clear_r<=clear;ingest_r<=ingest_v;line_r<=selected_line;flush_r<=flush;emit_r<=emit_v;group_r<=emit_group;rank_r<=rank;gbase_r<=gbase;
  tx_v<=c_tx_v;tx<=c_tx;fault<=c_fault;selected_count<=c_count;
 end
 ot_hbm_idx_topk_link_static_core #(.MUT(MUT),.NL(NL)) core(.clk(clk),.clk_mem(clk_mem),.rst_n(rst_core_n),.clear(clear_r),.ingest_v(ingest_r),
  .selected_line(line_r),.flush(flush_r),.emit_v(emit_r),.emit_group(group_r),.rank(rank_r),.gbase(gbase_r),
  .tx_v(c_tx_v),.tx(c_tx),.fault(c_fault),.selected_count(c_count));
endmodule
`default_nettype wire
