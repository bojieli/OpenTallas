`timescale 1ns/1ps
`default_nettype none
// HBM-SVGREL8 2026-10-20: HARDENED copy of ot_hbm_svc_prefetch_overlap_owner_rel_id (that module stays byte-identical):
// the same address map (sub-row slot base[9:7], row_low permutation, PC hash), tag table, response checks and faults.
// Changes:
//   * the block is issued from the REGISTERED block fields only (the producer loads them at descriptor_fire; this owner
//     starts at blk_start = the next hbm edge, t = 0): no descriptor-vs-block 2:1 mux on ~95 bits per owner, driven by
//     the descriptor_fire strobe (+1 hbm edge descriptor -> first command; HBM side, elastic);
//   * reset only on control (ticket, valid, sticky, issuing) from rst_n[2:0] leaves; the 32-entry tag table is datapath:
//     a FREE entry captures the current issue fields every edge (enable = !valid, KEPT copies per <= 32 flops), so at the
//     allocating edge it holds exactly what the original wrote; an entry is only read while valid;
//   * the per-entry seen mask clears with the same free-entry capture.
module ot_hbm_svc_prefetch_owner_rel_h #(
 parameter integer OWNER_AW=5,parameter integer LB=1
)(
 input wire [4:0] pc_id,
 input wire clk,input wire[2:0]rst_n,
 input wire blk_start,
 input wire block_active,input wire [29:0] block_base,input wire [19:0] block_pcs,
 input wire [14:0] block_row_base,input wire [11:0] block_total,input wire [LB-1:0] block_bank,
 input wire [15:0] block_epoch,input wire stop,k_ready,kr_v,input wire [16:0] kr_tag,
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
 localparam integer ENTRIES=1<<OWNER_AW,GW=17-OWNER_AW;
 initial if(ENTRIES!=32)$fatal(1,"owner_rel_h: OWNER_AW 5 (reset leaves sized for 32 entries)");
 reg [4:0] pc_q;always @(posedge clk)pc_q<=pc_id; // strap identity (static), this owner's physical PC
 reg [16:0] ticket;reg [9:0] cursor;reg sticky;reg issuing_q;
 reg [ENTRIES-1:0] valid_q;
 (* keep="true",dont_touch="true" *) reg [ENTRIES-1:0] vfree_a,vfree_b,vfree_c,vfree_d;   // KEPT copies of !valid_q (table capture enables)
 reg [GW-1:0] generation_q[0:ENTRIES-1];reg [15:0] epoch_q[0:ENTRIES-1];
 reg [LB-1:0] bank_q[0:ENTRIES-1];reg permuted_q[0:ENTRIES-1];reg [1:0] row_low_q[0:ENTRIES-1];
 reg [10:0] ordinal_q[0:ENTRIES-1];reg [2:0] length_q[0:ENTRIES-1];reg [3:0] seen_q[0:ENTRIES-1];
 wire [19:0] pcs=block_pcs;
 wire [14:0] row_base=block_row_base;
 wire [11:0] total=block_total;
 wire [15:0] epoch=block_epoch;
 wire [LB-1:0] bank=block_bank;
 // Four eight-entry table regions own field copies. Sampling a stable block
 // field every edge replaces a shared input driving all 32 entries per owner.
 // First issue is held during blk_start, allowing these copies to land: +1
 // hbm edge descriptor-to-first-request, before elastic block-ready; go unchanged.
 localparam integer RG=4;
 (* keep="true",dont_touch="true" *) reg [15:0] epoch_local[0:RG-1];
 (* keep="true",dont_touch="true" *) reg [LB-1:0] bank_local[0:RG-1];
 (* keep="true",dont_touch="true" *) reg [1:0] row_local[0:RG-1];
 integer rg;
 always @(posedge clk)for(rg=0;rg<RG;rg=rg+1)begin
  epoch_local[rg]<=block_epoch;bank_local[rg]<=block_bank;row_local[rg]<=block_row_base[1:0];
 end
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
 wire [OWNER_AW-1:0] alloc=ticket[OWNER_AW-1:0],ret=kr_tag[OWNER_AW-1:0];
 // Local row-select branches drive <=16 bits each. The binary tag decoder
 // feeds four real gate inputs, instead of one selected-row net driving51 bits.
 wire [ENTRIES-1:0] rgen_sel,rep_sel,rord_sel,rctl_sel;
 for(genvar rs=0;rs<ENTRIES;rs=rs+1)begin:g_return_select
  wire hit=ret==rs;
  ot_hbm_svc_local_and2 u_g(.a(hit),.b(1'b1),.y(rgen_sel[rs]));
  ot_hbm_svc_local_and2 u_e(.a(hit),.b(1'b1),.y(rep_sel[rs]));
  ot_hbm_svc_local_and2 u_o(.a(hit),.b(1'b1),.y(rord_sel[rs]));
  ot_hbm_svc_local_and2 u_c(.a(hit),.b(1'b1),.y(rctl_sel[rs]));
 end
 reg [GW-1:0] generation_r;
 reg [15:0] epoch_r;reg [LB-1:0]bank_r;reg [10:0]ordinal_r;
 reg [2:0]length_r;reg permuted_r;reg [1:0]row_low_r;
 reg [3:0]seen_r;reg valid_r;integer rr;
 always @*begin
  generation_r=0;epoch_r=0;bank_r=0;ordinal_r=0;
  length_r=0;permuted_r=0;row_low_r=0;seen_r=0;valid_r=0;
  for(rr=0;rr<ENTRIES;rr=rr+1)begin
   generation_r=generation_r|(generation_q[rr]&{GW{rgen_sel[rr]}});
   epoch_r=epoch_r|(epoch_q[rr]&{16{rep_sel[rr]}});
   bank_r=bank_r|(bank_q[rr]&{LB{rord_sel[rr]}});
   ordinal_r=ordinal_r|(ordinal_q[rr]&{11{rord_sel[rr]}});
   length_r=length_r|(length_q[rr]&{3{rctl_sel[rr]}});
   permuted_r=permuted_r|(permuted_q[rr]&rctl_sel[rr]);
   row_low_r=row_low_r|(row_low_q[rr]&{2{rctl_sel[rr]}});
   seen_r=seen_r|(seen_q[rr]&{4{rctl_sel[rr]}});
   valid_r=valid_r|(valid_q[rr]&rctl_sel[rr]);
  end
 end
 assign k_v=block_active&&!blk_start&&selected&&t<words&&!valid_q[alloc]&&!sticky&&!stop;
 assign response_ok=kr_v&&valid_r&&generation_r==kr_tag[16:OWNER_AW]&&kr_beat<length_r&&!seen_r[kr_beat]&&!sticky&&!stop;
 wire [1:0] word_offset=permuted_r?(kr_beat[1:0]^row_low_r):2'd0;
 assign response_ordinal=ordinal_r+{7'd0,word_offset,2'b0};
 assign response_epoch=epoch_r;assign response_bank=bank_r;assign fault=sticky;
 wire issuing=block_active&&selected&&t<words;
 assign issue_done=!issuing;
 function automatic [3:0] mask_for(input [2:0] n);
  case(n)1:mask_for=1;4:mask_for=15;default:mask_for=0;endcase
 endfunction
 // Actual local library gates distribute each issue field to eight table rows.
 // The Boolean model is the official AND2 function with B tied high: zero cycles.
 wire [GW-1:0] generation_local[0:RG-1];
 wire [10:0] ordinal_local[0:RG-1];
 wire [2:0] length_local[0:RG-1];
 wire [10:0] ordinal_d={t[8:0],2'b0}+lane;
 for(genvar gr=0;gr<RG;gr=gr+1)begin:g_issue_field_tree
  for(genvar gb=0;gb<GW;gb=gb+1)begin:g_gen
   ot_hbm_svc_local_and2 u_buf(.a(ticket[OWNER_AW+gb]),.b(1'b1),.y(generation_local[gr][gb]));
  end
  for(genvar ob=0;ob<11;ob=ob+1)begin:g_ord
   ot_hbm_svc_local_and2 u_buf(.a(ordinal_d[ob]),.b(1'b1),.y(ordinal_local[gr][ob]));
  end
  ot_hbm_svc_local_and2 u_len0(.a(length[0]),.b(1'b1),.y(length_local[gr][0]));
  assign length_local[gr][1]=1'b0;
  ot_hbm_svc_local_and2 u_len2(.a(length[2]),.b(1'b1),.y(length_local[gr][2]));
 end
 wire fire=k_v&&k_ready;
 wire fire_ticket_lo,fire_ticket_hi,fire_cursor;
 ot_hbm_svc_local_and2 u_ftl(.a(fire),.b(1'b1),.y(fire_ticket_lo));
 ot_hbm_svc_local_and2 u_fth(.a(fire),.b(1'b1),.y(fire_ticket_hi));
 ot_hbm_svc_local_and2 u_fc(.a(fire),.b(1'b1),.y(fire_cursor));
 wire[3:0] beat_local[0:3];
 for(genvar bg=0;bg<4;bg=bg+1)begin:g_beat_local
  for(genvar bb=0;bb<4;bb=bb+1)begin:g_bit
   ot_hbm_svc_local_and2 u_buf(.a(kr_beat==bb),.b(1'b1),.y(beat_local[bg][bb]));
  end
 end
 wire [3:0] seen_ret=seen_r|(4'b1<<kr_beat);
 wire[3:0] response_take_local;
 genvar rt;
 generate for(rt=0;rt<4;rt=rt+1)begin:response_local
  ot_hbm_svc_local_and2 u_buf(.a(response_take),.b(1'b1),.y(response_take_local[rt]));
 end endgenerate
 wire ret_done=response_take&&seen_ret==mask_for(length_r);
 // next valid (allocate at fire, free at the last beat)
 reg [ENTRIES-1:0] valid_n;integer e;
 always @*begin
  valid_n=valid_q;
  if(fire)valid_n[alloc]=1;
  if(ret_done)valid_n[ret]=0;
 end
 // rst_n[0]: ticket / sticky / issuing (19); rst_n[1]: valid (32); rst_n[2]: !valid copy a (32)
 always @(posedge clk or negedge rst_n[0])begin
  if(!rst_n[0])begin ticket<=0;sticky<=0;issuing_q<=0;end
  else begin
   issuing_q<=issuing;
   if(blk_start&&issuing_q)sticky<=1;
   if(fire_ticket_lo)ticket[8:0]<=ticket[8:0]+1'b1;
   if(fire_ticket_hi)ticket[16:9]<=ticket[16:9]+(&ticket[8:0]);
   if(kr_v&&!response_ok)sticky<=1;
  end
 end
 always @(posedge clk or negedge rst_n[1])if(!rst_n[1])valid_q<=0;else valid_q<=valid_n;
 always @(posedge clk or negedge rst_n[2])if(!rst_n[2])vfree_a<={ENTRIES{1'b1}};else vfree_a<=~valid_n;
 // vfree_b: no reset -- a pure function of the reset valid_q (all free one edge into reset)
 always @(posedge clk)begin
  vfree_b<=(HM==5)?~valid_q:~valid_n;
  vfree_d<=(HM==5)?~valid_q:~valid_n;
  vfree_c<=~valid_n;
 end
 // datapath: cursor + tag table (no reset)
 always @(posedge clk)begin
  if(blk_start)cursor<=0;
  if(fire_cursor)cursor<=t+length;
  for(e=0;e<ENTRIES;e=e+1)begin
   // Kept free copies bound actual mux pins, not just the number of flops:
   // each hold mux consumes two enable pins. Epoch16 =>32; generation12 =>24.
   if(vfree_a[e])generation_q[e]<=generation_local[e/8];
   if(vfree_c[e])epoch_q[e]<=epoch_local[e/8];
   if(vfree_d[e])begin bank_q[e]<=bank_local[e/8];ordinal_q[e]<=ordinal_local[e/8];end
   if(vfree_b[e])begin                                                                          // 23 flops
    length_q[e]<=length_local[e/8];
    seen_q[e]<=0;permuted_q[e]<=length_local[e/8][2];row_low_q[e]<=row_local[e/8];
   end
   else if(response_take_local[e/8]&&ret==e)seen_q[e]<=seen_q[e]|beat_local[e/8];
  end
 end
endmodule
`default_nettype wire
