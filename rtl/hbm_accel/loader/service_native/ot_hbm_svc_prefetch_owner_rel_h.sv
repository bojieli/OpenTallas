`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED copy of ot_hbm_svc_prefetch_overlap_owner_rel_id (that module stays byte-identical):
// the same address map (sub-row slot base[9:7], row_low permutation, PC hash), tag numbering, response checks and faults.
// Changes:
//   * the block is issued from the REGISTERED block fields only (the producer loads them at descriptor_fire; this owner
//     starts at blk_start = the next hbm edge, t = 0) (+1 hbm edge descriptor -> first command; HBM side, elastic);
//   * round 3 (native census): per-BLOCK fields (epoch, row_low) live in a 4-entry table indexed by the landing bank, not
//     in each of the 32 tag entries: a landing bank has at most one block in flight (the producer admits a descriptor for
//     bank b only when every response of b's previous block has returned), so {epoch, row_low}[bank] is constant while
//     any entry of that bank is outstanding (the original copied the same 18 bits into every entry);
//   * the tag entry is written one hbm edge after its request fires, from a registered stage (KEPT copies, one per 16
//     entries) through a registered one-hot write select: the response of a request needs >> 1 edge (pin skids, PC,
//     DRAM), the entry's valid bit is still set on the fire edge (k_v blocks reuse exactly as before);
//   * response lookup by the registered ONE-HOT of the response tag (2 KEPT copies, from the response pin skid) instead
//     of a binary 32:1 decode / mux tree on the tag bits;
//   * reset only on control (ticket, valid, sticky, issuing, write select) from rst_n[2:0] leaves.
module ot_hbm_svc_prefetch_owner_rel_h #(
 parameter integer OWNER_AW=5,parameter integer LB=1
)(
 input wire [4:0] pc_id,
 input wire clk,input wire[2:0]rst_n,
 input wire blk_start,
 input wire block_active,input wire [29:0] block_base,input wire [19:0] block_pcs,
 input wire [14:0] block_row_base,input wire [11:0] block_total,input wire [LB-1:0] block_bank,
 input wire [15:0] block_epoch,input wire stop,k_ready,kr_v,input wire [16:0] kr_tag,
 input wire [63:0] kr_ret_oh,           // {copy B, copy A}: one-hot of kr_tag[4:0] (registered with kr_tag in the pin skid)
 input wire [3:0] kr_beat,input wire response_take,
 output wire k_v,output wire [29:0] k_addr,output wire [3:0] k_len,output wire [16:0] k_tag,
 output wire response_ok,output wire [10:0] response_ordinal,
 output wire [15:0] response_epoch,output wire [LB-1:0] response_bank,output wire fault,
 output wire issue_done
);
`ifdef SVGH_MUT
 localparam integer HM=`SVGH_MUT;     // HBM-SVGREL8 bench negative controls (see the kit README)
`else
 localparam integer HM=0;
`endif
 localparam integer ENTRIES=1<<OWNER_AW,GW=17-OWNER_AW,NB=1<<LB;
 initial if(ENTRIES!=32)$fatal(1,"owner_rel_h: OWNER_AW 5");
 reg [4:0] pc_q;always @(posedge clk)pc_q<=pc_id; // strap identity (static), this owner's physical PC
 reg [16:0] ticket;reg [9:0] cursor;reg sticky;reg issuing_q;
 reg [ENTRIES-1:0] valid_q;
 // per-landing-bank block fields (loaded at blk_start for block_bank)
 reg [15:0] bep[0:NB-1];reg [1:0] brl[0:NB-1];
 // tag entries: generation, landing bank, ordinal, full-group (= length 4 and permuted), seen beats
 reg [GW-1:0] generation_q[0:ENTRIES-1];reg [LB-1:0] bank_q[0:ENTRIES-1];
 reg [10:0] ordinal_q[0:ENTRIES-1];reg fg_q[0:ENTRIES-1];reg [3:0] seen_q[0:ENTRIES-1];
 wire [19:0] pcs=block_pcs;
 wire [14:0] row_base=block_row_base;
 wire [11:0] total=block_total;
 reg selected;reg [1:0] lane;integer j;
 always @*begin
  selected=0;lane=0;
  for(j=0;j<4;j=j+1)if(pcs[j*5+:5]==pc_q)begin selected=1;lane=j;end
 end
 wire [9:0] t=blk_start?10'd0:cursor;
 wire [10:0] words=total>lane?(total+3-lane)/4:0;
 wire full_group=words>={1'b0,t}+4;
 wire [2:0] length=full_group?3'd4:3'd1;
 wire [14:0] row=row_base;
 wire [2:0] slot=block_base[9:7];
 wire [9:0] t_s={t[9:7]|slot,t[6:0]};
 wire [9:0] mapped_t=full_group?{t_s[9:2],row[1:0]}:t_s;
 wire [4:0] dram_bank={mapped_t[9:7],mapped_t[1:0]};
 wire [4:0] col=mapped_t[6:2];
 wire [2:0] bhi=dram_bank[4:2]^row[4:2];
 wire [1:0] blo=dram_bank[1:0]^row[1:0];
 wire [4:0] hi5={row[1:0],bhi};
 assign k_addr={row,bhi,col,pc_q^col^hi5,blo};
 assign k_len={1'b0,length};assign k_tag=ticket;
 wire [OWNER_AW-1:0] alloc=ticket[OWNER_AW-1:0];
 assign k_v=block_active&&selected&&t<words&&!valid_q[alloc]&&!sticky&&!stop;
 wire fire=k_v&&k_ready;
 // response lookup by one-hot (copy A: generation / bank / ordinal; copy B: valid / fg / seen)
 wire [31:0] oa=kr_ret_oh[31:0],ob=kr_ret_oh[63:32];
 reg [GW-1:0] r_gen;reg [LB-1:0] r_bank;reg [10:0] r_ord;reg r_fg,r_valid;reg [3:0] r_seen;integer e;
 always @*begin
  r_gen=0;r_bank=0;r_ord=0;r_fg=0;r_valid=0;r_seen=0;
  for(e=0;e<ENTRIES;e=e+1)begin
   if(oa[e])begin r_gen=r_gen|generation_q[e];r_bank=r_bank|bank_q[e];r_ord=r_ord|ordinal_q[e];end
   if(ob[e])begin r_fg=r_fg|fg_q[e];r_valid=r_valid|valid_q[e];r_seen=r_seen|seen_q[e];end
  end
 end
 wire [2:0] r_len=r_fg?3'd4:3'd1;
 assign response_ok=kr_v&&r_valid&&r_gen==kr_tag[16:OWNER_AW]&&kr_beat<r_len&&!r_seen[kr_beat]&&!sticky&&!stop;
 wire [1:0] word_offset=r_fg?(kr_beat[1:0]^brl[r_bank]):2'd0;
 assign response_ordinal=r_ord+{7'd0,word_offset,2'b0};
 assign response_epoch=bep[r_bank];assign response_bank=r_bank;assign fault=sticky;
 wire issuing=block_active&&selected&&t<words;
 assign issue_done=!issuing;
 function automatic [3:0] mask_for(input [2:0] n);
  case(n)1:mask_for=1;4:mask_for=15;default:mask_for=0;endcase
 endfunction
 wire [3:0] seen_new=r_seen|(4'b1<<kr_beat);
 wire ret_done=response_take&&seen_new==mask_for(r_len);
 // registered write stage: KEPT copies of {generation, bank, ordinal, fg} (copy 0 -> entries 0-15, copy 1 -> 16-31)
 localparam integer SW=GW+LB+11+1;
 (* keep="true",dont_touch="true" *) reg [SW-1:0] stg0,stg1;
 reg [ENTRIES-1:0] wsel_q;            // one-hot entry written this edge (the request fired last edge)
 reg [LB-1:0] lbank;                  // local copy of the block's landing bank (blk_start)
 always @(posedge clk)begin
  stg0<={ticket[16:OWNER_AW],blk_start?block_bank:lbank,{t[8:0],2'b0}+11'(lane),full_group};
  stg1<={ticket[16:OWNER_AW],blk_start?block_bank:lbank,{t[8:0],2'b0}+11'(lane),full_group};
 end
 // rst_n[0]: ticket / sticky / issuing (19); rst_n[1]: valid (32); rst_n[2]: write select (32)
 always @(posedge clk or negedge rst_n[0])begin
  if(!rst_n[0])begin ticket<=0;sticky<=0;issuing_q<=0;end
  else begin
   issuing_q<=issuing;
   if(blk_start&&issuing_q)sticky<=1;
   if(fire)ticket<=ticket+1'b1;
   if(kr_v&&!response_ok)sticky<=1;
  end
 end
 integer v;
 always @(posedge clk or negedge rst_n[1])begin
  if(!rst_n[1])valid_q<=0;
  else for(v=0;v<ENTRIES;v=v+1)begin
   if(fire&&alloc==v)valid_q[v]<=1;
   else if(ret_done&&ob[v])valid_q[v]<=0;
  end
 end
 always @(posedge clk or negedge rst_n[2])begin
  if(!rst_n[2])wsel_q<=0;
  else for(v=0;v<ENTRIES;v=v+1)wsel_q[v]<=fire&&alloc==((HM==5)?5'(v+1):5'(v));
 end
 // datapath: cursor, block fields, tag table (no reset)
 always @(posedge clk)begin
  if(blk_start)begin cursor<=0;lbank<=block_bank;bep[block_bank]<=block_epoch;brl[block_bank]<=row_base[1:0];end
  if(fire)cursor<=t+length;
  for(e=0;e<ENTRIES;e=e+1)begin
   if(wsel_q[e])begin
    {generation_q[e],bank_q[e],ordinal_q[e],fg_q[e]}<=(e<16)?stg0:stg1;seen_q[e]<=0;
   end else if(response_take&&ob[e])seen_q[e]<=seen_q[e]|(4'b1<<kr_beat);
  end
 end
endmodule
`default_nettype wire
