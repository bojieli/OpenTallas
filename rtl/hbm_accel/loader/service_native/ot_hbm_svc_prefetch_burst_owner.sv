`default_nettype none
// One physical PC's burst ownership and return validation. The caller supplies
// descriptor_v and block controls synchronous to clk, using the same fixed
// HBM-domain clock phase as the original inlined owner.
module ot_hbm_svc_prefetch_burst_owner #(
 parameter [4:0] PC=0,
 parameter integer OWNER_AW=5
)(
 input wire clk,rst_n,
 input wire descriptor_v,input wire [29:0] descriptor_base,
 input wire [11:0] descriptor_total,input wire descriptor_bank,input wire [15:0] descriptor_epoch,
 input wire block_active,input wire [29:0] block_base,
 input wire [11:0] block_total,input wire block_bank,
 input wire [15:0] block_epoch,input wire stop,
 input wire k_ready,input wire kr_v,input wire [16:0] kr_tag,
 input wire [3:0] kr_beat,input wire response_take,
 output wire k_v,output wire [29:0] k_addr,
 output wire [3:0] k_len,output wire [16:0] k_tag,
 output wire response_ok,output wire [10:0] response_ordinal,
 output wire [15:0] response_epoch,output wire response_bank,
 output wire fault
);
 localparam integer ENTRIES=1<<OWNER_AW;
 localparam integer GW=17-OWNER_AW;
 reg [16:0] next_ticket;
 reg [22:0] group_q;
 reg [ENTRIES-1:0] valid_q;
 reg [GW-1:0] generation_q[0:ENTRIES-1];
 reg [15:0] epoch_q[0:ENTRIES-1];reg bank_q[0:ENTRIES-1];
 reg [10:0] ordinal_q[0:ENTRIES-1];
 reg [2:0] length_q[0:ENTRIES-1];reg [3:0] seen_q[0:ENTRIES-1];
 reg sticky;
 wire [OWNER_AW-1:0] alloc_index=next_ticket[OWNER_AW-1:0];
 wire [OWNER_AW-1:0] return_index=kr_tag[0+:OWNER_AW];
 wire [GW-1:0] return_generation=kr_tag[OWNER_AW+:GW];
 wire [3:0] beat=kr_beat;
 wire [29:0] effective_base=descriptor_v?descriptor_base:block_base;
 wire [11:0] effective_total=descriptor_v?descriptor_total:block_total;
 wire [15:0] effective_epoch=descriptor_v?descriptor_epoch:block_epoch;
 wire effective_bank=descriptor_v?descriptor_bank:block_bank;
 wire [22:0] first_group=initial_group+(({1'b0,initial_sector}+4<={1'b0,descriptor_base})?1'b1:1'b0);
 wire [22:0] effective_group=descriptor_v?first_group:group_q;
 wire [4:0] chunk_pc=PC^effective_group[4:0]^effective_group[9:5];
 wire [29:0] chunk_sector={effective_group,chunk_pc,2'b0};
 wire [30:0] block_end={1'b0,effective_base}+effective_total;
 wire [30:0] chunk_end={1'b0,chunk_sector}+4;
 wire [29:0] lo=chunk_sector<effective_base?effective_base:chunk_sector;
 wire [30:0] hi=chunk_end>block_end?block_end:chunk_end;
 wire [3:0] burst_length=hi-{1'b0,lo};
 wire [22:0] initial_group=descriptor_base[29:7];
 wire [4:0] initial_chunk_pc=PC^initial_group[4:0]^initial_group[9:5];
 wire [29:0] initial_sector={initial_group,initial_chunk_pc,2'b0};
 function automatic [3:0] mask_for(input [2:0] n);
  case(n)1:mask_for=1;2:mask_for=3;3:mask_for=7;4:mask_for=15;default:mask_for=0;endcase
 endfunction
 assign k_v=(block_active||descriptor_v)&&effective_total!=0&&effective_total<=2048&&block_end<=31'h40000000&&hi>{1'b0,lo}&&{1'b0,chunk_sector}<block_end&&
                     !valid_q[alloc_index]&&!sticky&&!stop;
 assign k_addr=lo;
 assign k_len=burst_length;
 assign k_tag=next_ticket;
 assign response_ok=kr_v&&valid_q[return_index]&&
      generation_q[return_index]==return_generation&&beat<length_q[return_index]&&
      !seen_q[return_index][beat]&&!sticky&&!stop;
 assign response_ordinal=ordinal_q[return_index]+beat;
 assign response_epoch=epoch_q[return_index];
 assign response_bank=bank_q[return_index];
 assign fault=sticky;
 integer e;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   next_ticket<=0;group_q<=0;valid_q<=0;sticky<=0;
   for(e=0;e<ENTRIES;e=e+1)begin
    generation_q[e]<=0;epoch_q[e]<=0;bank_q[e]<=0;ordinal_q[e]<=0;length_q[e]<=0;seen_q[e]<=0;
   end
  end else begin
   if(descriptor_v)begin
    if(|valid_q)sticky<=1;
    group_q<=initial_group+(({1'b0,initial_sector}+4<={1'b0,descriptor_base})?1'b1:1'b0);
   end
   if(k_v&&k_ready)begin
    if(burst_length==0||burst_length>4)sticky<=1;
    valid_q[alloc_index]<=1;generation_q[alloc_index]<=next_ticket[16:OWNER_AW];
    epoch_q[alloc_index]<=effective_epoch;bank_q[alloc_index]<=effective_bank;
    ordinal_q[alloc_index]<=lo-effective_base;length_q[alloc_index]<=burst_length[2:0];seen_q[alloc_index]<=0;
    next_ticket<=next_ticket+1'b1;group_q<=effective_group+1'b1;
   end
   if(kr_v&&!response_ok)sticky<=1;
   if(response_take)begin
    seen_q[return_index]<=seen_q[return_index]|(4'b1<<beat);
    if((seen_q[return_index]|(4'b1<<beat))==mask_for(length_q[return_index]))valid_q[return_index]<=0;
   end
  end
 end
endmodule
`default_nettype wire
