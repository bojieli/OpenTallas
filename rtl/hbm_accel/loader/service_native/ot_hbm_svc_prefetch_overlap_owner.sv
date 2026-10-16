`default_nettype none
// H-DIE 2026-10-15 OVERLAP variant of ot_hbm_svc_prefetch_mapped4_owner (that module stays byte-identical): the next
// block's descriptor may arrive once THIS owner has issued every command of the current block (issue_done), while the
// current block's responses are still returning -- each tag entry carries its own bank/epoch, so responses of two
// blocks on different landing banks never mix.  A descriptor while still issuing is a fault (static schedule error).
// Allocated four-PC packed image owner. Logical sectors rotate among four
// explicitly named PCs. Real native burst order permutes logical t low bits
// by row[1:0]; metadata records that permutation before any PHY acceptance.
module ot_hbm_svc_prefetch_overlap_owner #(
 parameter [4:0] PC=0,parameter integer OWNER_AW=5
)(
 input wire clk,rst_n,descriptor_v,input wire [29:0] descriptor_base,
 input wire [19:0] descriptor_pcs,input wire [14:0] descriptor_row_base,
 input wire [11:0] descriptor_total,input wire descriptor_bank,input wire [15:0] descriptor_epoch,
 input wire block_active,input wire [29:0] block_base,input wire [19:0] block_pcs,
 input wire [14:0] block_row_base,input wire [11:0] block_total,input wire block_bank,
 input wire [15:0] block_epoch,input wire stop,k_ready,kr_v,input wire [16:0] kr_tag,
 input wire [3:0] kr_beat,input wire response_take,
 output wire k_v,output wire [29:0] k_addr,output wire [3:0] k_len,output wire [16:0] k_tag,
 output wire response_ok,output wire [10:0] response_ordinal,
 output wire [15:0] response_epoch,output wire response_bank,output wire fault,
 output wire issue_done
);
 localparam integer ENTRIES=1<<OWNER_AW,GW=17-OWNER_AW;
 reg [16:0] ticket;reg [9:0] cursor;reg sticky;reg issuing_q;
 reg [ENTRIES-1:0] valid_q;
 reg [GW-1:0] generation_q[0:ENTRIES-1];reg [15:0] epoch_q[0:ENTRIES-1];
 reg bank_q[0:ENTRIES-1],permuted_q[0:ENTRIES-1];reg [1:0] row_low_q[0:ENTRIES-1];
 reg [10:0] ordinal_q[0:ENTRIES-1];reg [2:0] length_q[0:ENTRIES-1];reg [3:0] seen_q[0:ENTRIES-1];
 wire [19:0] pcs=descriptor_v?descriptor_pcs:block_pcs;
 wire [14:0] row_base=descriptor_v?descriptor_row_base:block_row_base;
 wire [11:0] total=descriptor_v?descriptor_total:block_total;
 wire [15:0] epoch=descriptor_v?descriptor_epoch:block_epoch;
 wire bank=descriptor_v?descriptor_bank:block_bank;
 reg selected;reg [1:0] lane;integer j;
 always @*begin
  selected=0;lane=0;
  for(j=0;j<4;j=j+1)if(pcs[j*5+:5]==PC)begin selected=1;lane=j;end
 end
 wire [9:0] t=descriptor_v?10'd0:cursor;
 wire [10:0] words=total>lane?(total+3-lane)/4:0;
 wire full_group=words>={1'b0,t}+4;
 wire [2:0] length=full_group?3'd4:3'd1;
 wire [14:0] row=row_base; // total<=2048 => t<512, never advances a DRAM row.
 wire [9:0] mapped_t=full_group?{t[9:2],row[1:0]}:t;
 wire [4:0] dram_bank={mapped_t[9:7],mapped_t[1:0]};
 wire [4:0] col=mapped_t[6:2];
 wire [2:0] bhi=dram_bank[4:2]^row[4:2];
 wire [1:0] blo=dram_bank[1:0]^row[1:0];
 wire [4:0] hi5={row[1:0],bhi};
 assign k_addr={row,bhi,col,PC^col^hi5,blo};
 assign k_len={1'b0,length};assign k_tag=ticket;
 wire [OWNER_AW-1:0] alloc=ticket[OWNER_AW-1:0],ret=kr_tag[OWNER_AW-1:0];
 assign k_v=(block_active||descriptor_v)&&selected&&t<words&&!valid_q[alloc]&&!sticky&&!stop;
 assign response_ok=kr_v&&valid_q[ret]&&generation_q[ret]==kr_tag[16:OWNER_AW]&&kr_beat<length_q[ret]&&!seen_q[ret][kr_beat]&&!sticky&&!stop;
 wire [1:0] word_offset=permuted_q[ret]?(kr_beat[1:0]^row_low_q[ret]):2'd0;
 assign response_ordinal=ordinal_q[ret]+{7'd0,word_offset,2'b0};
 assign response_epoch=epoch_q[ret];assign response_bank=bank_q[ret];assign fault=sticky;
 wire issuing=block_active&&!descriptor_v&&selected&&t<words;
 assign issue_done=!issuing;
 function automatic [3:0] mask_for(input [2:0] n);
  case(n)1:mask_for=1;4:mask_for=15;default:mask_for=0;endcase
 endfunction
 integer e;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   ticket<=0;cursor<=0;valid_q<=0;sticky<=0;issuing_q<=0;
   for(e=0;e<ENTRIES;e=e+1)begin generation_q[e]<=0;epoch_q[e]<=0;bank_q[e]<=0;permuted_q[e]<=0;row_low_q[e]<=0;ordinal_q[e]<=0;length_q[e]<=0;seen_q[e]<=0;end
  end else begin
   issuing_q<=issuing;
   if(descriptor_v)begin if(issuing_q)sticky<=1;cursor<=0;end
   if(k_v&&k_ready)begin
    valid_q[alloc]<=1;generation_q[alloc]<=ticket[16:OWNER_AW];epoch_q[alloc]<=epoch;bank_q[alloc]<=bank;
    ordinal_q[alloc]<={t[8:0],2'b0}+lane;length_q[alloc]<=length;seen_q[alloc]<=0;
    permuted_q[alloc]<=full_group;row_low_q[alloc]<=row[1:0];ticket<=ticket+1'b1;cursor<=t+length;
   end
   if(kr_v&&!response_ok)sticky<=1;
   if(response_take)begin
    seen_q[ret]<=seen_q[ret]|(4'b1<<kr_beat);
    if((seen_q[ret]|(4'b1<<kr_beat))==mask_for(length_q[ret]))valid_q[ret]<=0;
   end
  end
 end
endmodule
`default_nettype wire
