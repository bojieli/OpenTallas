// Stream half of ot_hbm_svc_sm4pc_cdc_rel_id: reserve, block bookkeeping, drain. Reads and data cross to the bank tiles, 2 edges each way, so the out_* word
// is delayed DLY = 4 edges and meets its data. reserve_ready no longer reads the descriptor FIFO: at most LBANKS blocks are allocated and the FIFO holds 4.
// MUT (bench): 1 = DLY 3 (data off by one word), 2 = read row of bank 5 not offset by drain, 3 = complete dropped on bank 2 at the 3rd event.
module ot_svgr_prod_s #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,parameter integer OPEN_IL=0,parameter integer MUT=0)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,input wire stream_clk,stream_rst_n,hbm_rst_n,
 output wire seam_res_v,output wire[96:0]seam_res_word,output wire seam_s_fault,input wire seam_h_fault,
 output wire seam_stop,output wire[7:0]seam_read_v,output wire[1:0]seam_read_bank,output wire[47:0]seam_read_row,
 input wire[7:0]seam_complete,input wire[15:0]seam_complete_bank,input wire[7:0]seam_bfault,input wire[2047:0]seam_read_data,
 input wire [14:0] reserve_row_base,input wire reserve_v,output wire reserve_ready,input wire [31:0] reserve_base,
 input wire [11:0] reserve_total,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 output wire [LBANKS-1:0] block_ready,
 input wire start_v,input wire [LB-1:0] start_bank,input wire [15:0] start_epoch,
 output wire out_v,output wire [3:0] out_mask,output wire [1023:0] out_data,
 output wire [10:0] out_ordinal,output wire [LB-1:0] out_bank,output wire [15:0] out_epoch,output wire out_last,output wire fault
);
 localparam integer DLY=(MUT==1)?3:4;
 reg [1:0] stack_s;reg [2:0] sm_s;
 always @(posedge stream_clk)begin stack_s<=id_stack;sm_s<=id_sm;end
 wire [19:0] reserve_pcs={sm_s,2'd3,sm_s,2'd2,sm_s,2'd1,sm_s,2'd0};
 wire reset_both=stream_rst_n&&hbm_rst_n;wire srst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+reserve_total;
 wire pcs_unique=1'b1; // four distinct low bits by construction
 wire descriptor_ok=pcs_unique&&reserve_base[29:10]==0&&reserve_base[6:0]==0&&reserve_row_base<32768&&reserve_total!=0&&reserve_total<=512&&reserve_base[31:30]==stack_s&&reserve_end<=33'h040000000;
 reg [LBANKS-1:0] allocated,ready_q,announced;
 reg [15:0] bank_epoch[0:LBANKS-1];reg [11:0] bank_total[0:LBANKS-1];
 reg [7:0] completed_q[0:LBANKS-1];reg stream_fault;
 reg [7:0] complete_event[0:LBANKS-1];
 wire [LB-1:0] bank_complete_bank[0:7];
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:cb assign bank_complete_bank[g]=seam_complete_bank[2*g+:2];end endgenerate
 assign fault=stream_fault||seam_h_fault||(|seam_bfault);
 assign seam_s_fault=stream_fault;assign seam_stop=fault;
 assign reserve_ready=srst&&!allocated[reserve_bank]&&!fault;
 wire reserve_fire=reserve_v&&reserve_ready&&descriptor_ok;
 assign seam_res_v=reserve_fire;
 assign seam_res_word={reserve_pcs,reserve_row_base,reserve_base,reserve_total,reserve_bank,reserve_epoch};
 reg draining;reg [LB-1:0] drain_bank;reg [10:0] drain_ordinal;reg [10:0] read_ordinal_q;reg [2:0] drain_phase;
 assign block_ready=(OPEN_IL!=0)?(ready_q&{LBANKS{~draining}}):ready_q;
 wire [2:0] drain_count=drain_phase==4?3'd1:3'd4;
 assign seam_read_bank=drain_bank;
 generate for(g=0;g<8;g=g+1)begin:ordinal_bank
  wire [11:0] candidate={3'b0,drain_ordinal[8:3],3'(g)}+((g<drain_ordinal[2:0])?12'd8:12'd0);
  assign seam_read_v[g]=draining&&candidate<drain_ordinal+drain_count&&candidate<bank_total[drain_bank];
  assign seam_read_row[6*g+:6]=(MUT==2&&g==5)?drain_ordinal[8:3]+6'd1:candidate[8:3];
 end endgenerate
 integer ci,rb;integer mc=0;
 always @*begin
  for(rb=0;rb<LBANKS;rb=rb+1)complete_event[rb]=0;
  for(ci=0;ci<8;ci=ci+1)if(seam_complete[ci]&&!(MUT==3&&ci==2&&mc==2))complete_event[bank_complete_bank[ci]][ci]=1;
 end
 always @(posedge stream_clk)if(seam_complete[2])mc<=mc+1;
 reg o_v;reg [3:0] o_mask;reg [10:0] o_ord,o_rq;reg [LB-1:0] o_bank;reg [15:0] o_epoch;reg o_last;
 reg [DLY-1:0] p_v,p_last;reg [3:0] p_mask[0:DLY-1];reg [10:0] p_ord[0:DLY-1];reg [LB-1:0] p_bank[0:DLY-1];reg [15:0] p_ep[0:DLY-1];reg [10:0] p_rq[0:DLY-1];
 integer d;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin p_v<=0;p_last<=0;for(d=0;d<DLY;d=d+1)begin p_mask[d]<=0;p_ord[d]<=0;p_bank[d]<=0;p_ep[d]<=0;p_rq[d]<=0;end end
  else begin
   p_v<={p_v[DLY-2:0],o_v};p_last<={p_last[DLY-2:0],o_last};
   p_mask[0]<=o_mask;p_ord[0]<=o_ord;p_bank[0]<=o_bank;p_ep[0]<=o_epoch;p_rq[0]<=read_ordinal_q;
   for(d=1;d<DLY;d=d+1)begin p_mask[d]<=p_mask[d-1];p_ord[d]<=p_ord[d-1];p_bank[d]<=p_bank[d-1];p_ep[d]<=p_ep[d-1];p_rq[d]<=p_rq[d-1];end
  end
 end
 assign out_v=p_v[DLY-1];assign out_mask=p_mask[DLY-1];assign out_ordinal=p_ord[DLY-1];assign out_bank=p_bank[DLY-1];assign out_epoch=p_ep[DLY-1];assign out_last=p_last[DLY-1];
 generate for(g=0;g<4;g=g+1)begin:out_lane
  assign out_data[256*g+:256]=seam_read_data[256*((p_rq[DLY-1][2:0]+g)%8)+:256];
 end endgenerate
 integer si,sb;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;ready_q<=0;announced<=0;stream_fault<=0;
   draining<=0;drain_bank<=0;drain_ordinal<=0;read_ordinal_q<=0;drain_phase<=0;
   o_v<=0;o_mask<=0;o_ord<=0;o_bank<=0;o_epoch<=0;o_last<=0;
   for(sb=0;sb<LBANKS;sb=sb+1)begin bank_epoch[sb]<=0;bank_total[sb]<=0;completed_q[sb]<=0;end
  end else begin
   o_v<=0;o_last<=0;o_mask<=0;
   if(reserve_v)begin
    if(!reserve_ready||!descriptor_ok)stream_fault<=1;
    else begin
     allocated[reserve_bank]<=1;bank_epoch[reserve_bank]<=reserve_epoch;bank_total[reserve_bank]<=reserve_total;
     for(si=0;si<8;si=si+1)completed_q[reserve_bank][si]<=reserve_total<=si;
     ready_q[reserve_bank]<=0;announced[reserve_bank]<=0;
    end
   end
   for(sb=0;sb<LBANKS;sb=sb+1)if(|complete_event[sb])begin
    completed_q[sb]<=completed_q[sb]|complete_event[sb];
    if(&(completed_q[sb]|complete_event[sb]))ready_q[sb]<=1;
   end
   if(start_v)begin
    if(draining||!ready_q[start_bank]||start_epoch!=bank_epoch[start_bank]||fault)stream_fault<=1;
    else begin draining<=1;drain_bank<=start_bank;drain_ordinal<=0;drain_phase<=0;ready_q[start_bank]<=0;end
   end
   if(draining&&!fault)begin
    o_v<=1;o_bank<=drain_bank;o_epoch<=bank_epoch[drain_bank];o_ord<=drain_ordinal;
    read_ordinal_q<=drain_ordinal;drain_phase<=drain_phase==4?0:drain_phase+1'b1;
    for(si=0;si<4;si=si+1)if(si<drain_count&&drain_ordinal+si<bank_total[drain_bank])o_mask[si]<=1;
    if(drain_ordinal+drain_count>=bank_total[drain_bank])begin
     o_last<=1;draining<=0;allocated[drain_bank]<=0;
    end else drain_ordinal<=drain_ordinal+drain_count;
   end
  end
 end
endmodule

// K request across the kit shell. The leaf takes a word in the edge after p_v (out face); its k_rdy for that edge comes back 2 edges after p_v.
// So one word at a time: present 1 edge, read the answer 2 edges later, present again if not taken. At most 1 request per 3 edges.
// MUT (bench): 1 = answer read 1 edge early.
module ot_svgr_k_out #(parameter integer W=51,parameter integer MUT=0)(input wire clk,rst_n,input wire i_v,output wire i_rdy,input wire [W-1:0] i_d,output reg p_v,input wire p_rdy,output reg [W-1:0] p_d);
 reg [1:0] st;
 assign i_rdy=st==0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin st<=0;p_v<=0;p_d<=0;end
  else begin
   p_v<=0;
   case(st)
    0:if(i_v)begin p_d<=i_d;p_v<=1;st<=1;end
    1:begin st<=2;if(MUT==1&&p_rdy)st<=0;end
    2:st<=3;
    3:if(p_rdy)st<=0;else begin p_v<=1;st<=1;end
   endcase
  end
 end
endmodule

// K response across the kit shell. p_rdy reaches the leaf 1 edge later and its word comes back 1 edge after that, so a word taken by p_rdy of edge t reads here in t+2.
// The queue holds what is already asked for: 4 entries keeps 1 word per edge.
// MUT (bench): 1 = capture 1 edge late (reads the next word).
module ot_svgr_kr_in #(parameter integer W=277,parameter integer D=4,parameter integer MUT=0)(input wire clk,rst_n,input wire p_v,output wire p_rdy,input wire [W-1:0] p_d,output wire i_v,input wire i_rdy,output wire [W-1:0] i_d);
 reg [W-1:0] m[0:D-1];reg [1:0] wp,rp;reg [2:0] n;reg r1,r2,r3;
 wire cap=(MUT==1?r3:r2)&&p_v;wire pop=i_v&&i_rdy;
 assign p_rdy=rst_n&&(3'(n)+3'(r1)+3'(r2)<3'(D));
 assign i_v=n!=0;assign i_d=m[rp];
 always @(posedge clk)if(cap)m[wp]<=p_d;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;n<=0;r1<=0;r2<=0;r3<=0;end
  else begin r1<=p_rdy;r2<=r1;r3<=r2;if(cap)wp<=wp+1'b1;if(pop)rp<=rp+1'b1;n<=n+3'(cap)-3'(pop);end
 end
endmodule

// Hbm half: descriptor FIFO, 4 PC owners, response arbiter with one credit counter per landing bank, K pins.
// MUT (bench): 1 = credit counter starts one over the FIFO depth, 2 = a freed credit is dropped on bank 6 at count 20.
module ot_svgr_own #(parameter integer OWNER_AW=5,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=4,parameter integer LB=2,parameter integer MUT=0)(
 input wire [1:0] id_stack,input wire [2:0] id_sm,input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,input wire [3:0] hbm_pc_clk,
 input wire seam_res_v,input wire[96:0]seam_res_word,input wire seam_s_fault,output wire seam_h_fault,
 output reg [7:0] bk_in_v,output wire [2279:0] bk_in_data,input wire [7:0] bk_cr,
 output wire [3:0] k_v,input wire [3:0] k_rdy,output wire [119:0] k_addr,output wire [15:0] k_len,output wire [67:0] k_tag,output wire [3:0] k_we,
 output wire [1023:0] k_wdata,output wire [127:0] k_wstrb,input wire [3:0] k_wr_done,
 input wire [3:0] kr_v,output wire [3:0] kr_rdy,input wire [67:0] kr_tag,input wire [15:0] kr_beat,input wire [1023:0] kr_data
);
 wire [3:0] i_k_v,i_k_rdy,i_kr_v;wire [119:0] i_k_addr;wire [15:0] i_k_len;wire [67:0] i_k_tag;reg [3:0] i_kr_rdy;wire [67:0] i_kr_tag;wire [15:0] i_kr_beat;wire [1023:0] i_kr_data;
 reg [1:0] stack_h;always @(posedge hbm_clk)stack_h<=id_stack;
 localparam integer T0=16+LB,A0=28+LB,S0=58+LB,R0=60+LB,P0=75+LB,DW=95+LB,IW=283+LB;
 wire reset_both=stream_rst_n&&hbm_rst_n;wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 reg hbm_fault;wire hbf2,stf2,desc_ov,desc_un,desc_wr_ready;
 ot_hbm_svc_fault_cdc u_hbm_fault_cdc(.wr_clk(hbm_clk),.wr_rst_n(hrst),.rd_clk(stream_clk),.rd_rst_n(srst),.src_fault(hbm_fault),.dst_fault(hbf2),.wr_overflow(),.rd_underflow());
 ot_hbm_svc_fault_cdc u_stream_fault_cdc(.wr_clk(stream_clk),.wr_rst_n(srst),.rd_clk(hbm_clk),.rd_rst_n(hrst),.src_fault(seam_s_fault),.dst_fault(stf2),.wr_overflow(),.rd_underflow());
 assign seam_h_fault=hbf2||desc_ov||(seam_res_v&&!desc_wr_ready);
 wire desc_rd_valid,desc_rd_ready;wire [DW-1:0] desc_data;
 ot_hbm_svc_async_fifo #(.WIDTH(DW),.DEPTH(4)) u_descriptor(.wr_clk(stream_clk),.wr_rst_n(srst),.wr_valid(seam_res_v),.wr_ready(desc_wr_ready),.wr_data(seam_res_word),.wr_overflow(desc_ov),
  .rd_clk(hbm_clk),.rd_rst_n(hrst),.rd_valid(desc_rd_valid),.rd_ready(desc_rd_ready),.rd_data(desc_data),.rd_underflow(desc_un));
 reg h_active;reg [LB-1:0] h_bank;reg [15:0] h_epoch;reg [29:0] h_base;reg [11:0] h_total;reg [19:0] h_pcs;reg [14:0] h_row_base;
 reg [11:0] rx_left[0:LBANKS-1];reg h_fresh;wire [3:0] issue_done;integer rb;
 wire [3:0] pc_fault,response_ok;wire [LB-1:0] response_bank[0:3];wire [10:0] response_ordinal[0:3];wire [15:0] response_epoch[0:3];
 reg [3:0] response_accepted;
 wire descriptor_fire=desc_rd_valid&&desc_rd_ready;
 reg rx_any;always @*begin rx_any=0;for(rb=0;rb<LBANKS;rb=rb+1)if(rx_left[rb]!=0)rx_any=1;end
 assign desc_rd_ready=!h_active&&!hbm_fault&&hrst&&desc_rd_valid&&rx_left[desc_data[T0-1:16]]==0;
 assign k_we=0;assign k_wdata=0;assign k_wstrb=0;
 reg [3:0] credit[0:7];reg cr_ov;integer cc=0;
 wire [7:0] fifo_wr_ready;
 reg [IW-1:0] fifo_wr_data[0:7];
 genvar pc,g;
 generate for(pc=0;pc<4;pc=pc+1)begin:pc_owner
  ot_hbm_svc_prefetch_overlap_owner_rel_id #(.OWNER_AW(OWNER_AW),.LB(LB)) u_owner(
   .pc_id({id_sm,2'(pc)}),.clk(hbm_pc_clk[pc]),.rst_n(hrst),.descriptor_v(descriptor_fire),
   .descriptor_base(desc_data[A0+29:A0]),.descriptor_pcs(desc_data[P0+19:P0]),.descriptor_row_base(desc_data[R0+14:R0]),.descriptor_total(desc_data[T0+11:T0]),
   .descriptor_bank(desc_data[T0-1:16]),.descriptor_epoch(desc_data[15:0]),
   .block_active(h_active),.block_base(h_base),.block_pcs(h_pcs),.block_row_base(h_row_base),.block_total(h_total),
   .block_bank(h_bank),.block_epoch(h_epoch),.stop(hbm_fault),
   .k_ready(i_k_rdy[pc]),.kr_v(i_kr_v[pc]),.kr_tag(i_kr_tag[17*pc+:17]),
   .kr_beat(i_kr_beat[4*pc+:4]),.response_take(response_accepted[pc]),
   .k_v(i_k_v[pc]),.k_addr(i_k_addr[30*pc+:30]),.k_len(i_k_len[4*pc+:4]),.k_tag(i_k_tag[17*pc+:17]),
   .response_ok(response_ok[pc]),.response_ordinal(response_ordinal[pc]),
   .response_epoch(response_epoch[pc]),.response_bank(response_bank[pc]),.fault(pc_fault[pc]),.issue_done(issue_done[pc]));
  ot_svgr_k_out #(.W(51),.MUT(MUT==3?1:0)) u_k_out(.clk(hbm_pc_clk[pc]),.rst_n(hrst),.i_v(i_k_v[pc]),.i_rdy(i_k_rdy[pc]),.i_d({i_k_addr[30*pc+:30],i_k_len[4*pc+:4],i_k_tag[17*pc+:17]}),
   .p_v(k_v[pc]),.p_rdy(k_rdy[pc]),.p_d({k_addr[30*pc+:30],k_len[4*pc+:4],k_tag[17*pc+:17]}));
  ot_svgr_kr_in #(.W(277),.MUT(MUT==4?1:0)) u_kr_in(.clk(hbm_pc_clk[pc]),.rst_n(hrst),.p_v(kr_v[pc]),.p_rdy(kr_rdy[pc]),.p_d({kr_tag[17*pc+:17],kr_beat[4*pc+:4],kr_data[256*pc+:256]}),
   .i_v(i_kr_v[pc]),.i_rdy(i_kr_rdy[pc]),.i_d({i_kr_tag[17*pc+:17],i_kr_beat[4*pc+:4],i_kr_data[256*pc+:256]}));
 end endgenerate
 reg [1:0] arb_cursor[0:7];reg [1:0] arb_selected[0:7];
 generate for(g=0;g<8;g=g+1)begin:response_fairness
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)arb_cursor[g]<=0;else if(bk_in_v[g])arb_cursor[g]<=arb_selected[g]+1'b1;
  end
  assign fifo_wr_ready[g]=credit[g]!=0;
  assign bk_in_data[IW*g+:IW]=fifo_wr_data[g];
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)credit[g]<=(MUT==1)?4'(RESPONSE_DEPTH+1):4'(RESPONSE_DEPTH);
   else credit[g]<=credit[g]-4'(bk_in_v[g])+4'(bk_cr[g]&&!(MUT==2&&g==6&&cc>=20));
  end
 end endgenerate
 always @(posedge hbm_clk)if(bk_in_v[6])cc<=cc+1;
 integer p,l,offset,ta,tb;
 reg [2:0] h_take_b[0:LBANKS-1];
 always @*begin
  for(tb=0;tb<LBANKS;tb=tb+1)begin
   h_take_b[tb]=0;
   for(ta=0;ta<4;ta=ta+1)if(response_accepted[ta]&&int'(response_bank[ta])==tb)h_take_b[tb]=h_take_b[tb]+3'd1;
  end
 end
 always @*begin
  i_kr_rdy=0;bk_in_v=0;response_accepted=0;
  for(l=0;l<8;l=l+1)begin
   fifo_wr_data[l]=0;arb_selected[l]=0;
   for(offset=0;offset<4;offset=offset+1)begin
    p=(arb_cursor[l]+offset)&3;
    if(response_ok[p]&&response_ordinal[p][2:0]==l&&!bk_in_v[l]&&fifo_wr_ready[l])begin
     i_kr_rdy[p]=1;bk_in_v[l]=1;arb_selected[l]=p;response_accepted[p]=1;
     fifo_wr_data[l]={response_ordinal[p],response_bank[p],response_epoch[p],i_kr_data[256*p+:256]};
    end
   end
  end
 end
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   h_active<=0;h_bank<=0;h_epoch<=0;h_base<=0;h_total<=0;h_pcs<=0;h_row_base<=0;
   for(rb=0;rb<LBANKS;rb=rb+1)rx_left[rb]<=0;h_fresh<=0;hbm_fault<=0;
  end else begin
   if(stf2||desc_un||(|k_wr_done)||(|pc_fault))hbm_fault<=1;
   if(descriptor_fire)begin
    if(desc_data[S0+1:S0]!=stack_h||desc_data[T0+11:T0]==0||desc_data[T0+11:T0]>512||{3'b0,desc_data[A0+29:A0]}+desc_data[T0+11:T0]>33'h040000000)hbm_fault<=1;
    else begin h_active<=1;h_base<=desc_data[A0+29:A0];h_pcs<=desc_data[P0+19:P0];h_row_base<=desc_data[R0+14:R0];h_total<=desc_data[T0+11:T0];
     h_bank<=desc_data[T0-1:16];h_epoch<=desc_data[15:0];end
   end
   h_fresh<=descriptor_fire;
   if(h_active&&!descriptor_fire&&!h_fresh&&(&issue_done))h_active<=0;
   if(descriptor_fire&&rx_left[desc_data[T0-1:16]]!=0)hbm_fault<=1;
   for(rb=0;rb<LBANKS;rb=rb+1)begin
    rx_left[rb]<=((descriptor_fire&&desc_data[T0-1:16]==rb)?desc_data[T0+11:T0]:rx_left[rb])-12'(h_take_b[rb]);
    if(h_take_b[rb]!=0&&rx_left[rb]==0)hbm_fault<=1;
   end
   if(|i_kr_v&&!descriptor_fire&&!rx_any)hbm_fault<=1;
  end
 end
endmodule

// Four landing banks of one fifo clock group: the response FIFO returns one credit per freed entry, in the write domain.
module ot_svgr_landing #(parameter integer LBANKS=4,parameter integer LB=2,parameter integer IW=283+LB)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,input wire [2:0] bank_id,
 input wire in_v,input wire [IW-1:0] in_data,output wire [1:0] freed,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,output wire [255:0] read_data
);
 wire packet_v,packet_take,full,empty;wire [IW-1:0] packet;wire [2:0] rf;reg ov;
 ot_hbm_accel_cdc_fifo #(.W(IW),.AW(3)) u_response(.wclk(hbm_clk),.wrst_n(hbm_rst_n),.we(in_v),.wdata(in_data),.full(full),.rd_freed(rf),
  .rclk(stream_clk),.rrst_n(stream_rst_n),.re(packet_take),.rdata(packet),.empty(empty));
 assign packet_v=!empty;assign freed=rf[1:0];
 reg [LBANKS-1:0] valid_q;reg [15:0] epoch_q[0:LBANKS-1];reg [6:0] count_q[0:LBANKS-1],received_q[0:LBANKS-1];
 reg [63:0] seen_q[0:LBANKS-1];reg sticky;
 wire [10:0] ordinal=packet[IW-1:IW-11];wire [LB-1:0] bank=packet[271+LB:272];wire [15:0] epoch=packet[271:256];wire [5:0] row=ordinal[8:3];
 wire identity_ok=valid_q[bank]&&epoch_q[bank]==epoch&&ordinal[2:0]==bank_id&&{1'b0,row}<count_q[bank]&&!seen_q[bank][row];
 wire landing_write=packet_v&&!stop&&!sticky&&identity_ok;
 assign packet_take=packet_v&&!stop&&!sticky;
 assign complete_v=landing_write&&received_q[bank]+1'b1==count_q[bank];
 assign complete_bank=bank;assign fault=sticky||ov;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)ov<=0;else if(in_v&&full)ov<=1;
 integer b;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   valid_q<=0;sticky<=0;
   for(b=0;b<LBANKS;b=b+1)begin epoch_q[b]<=0;count_q[b]<=0;received_q[b]<=0;seen_q[b]<=0;end
  end else begin
   if(reserve_v)begin
    valid_q[reserve_bank]<=1;epoch_q[reserve_bank]<=reserve_epoch;
    count_q[reserve_bank]<=reserve_total>12'(bank_id)?(reserve_total+12'd7-12'(bank_id))/8:0;
    received_q[reserve_bank]<=0;seen_q[reserve_bank]<=0;
   end
   if(packet_take)begin
    if(!identity_ok)sticky<=1;
    else begin seen_q[bank][row]<=1;received_q[bank]<=received_q[bank]+1'b1;end
   end
  end
 end
 ot_sram_1r1w_256x256_m2_r2c2 u_payload(.clk(stream_clk),.r_ce_in(read_v&&!stop&&!sticky),.r_addr_in({read_bank,read_row}),.rd_out(read_data),
  .w_ce_in(landing_write),.w_addr_in({bank,row}),.wd_in(packet[255:0]),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
endmodule

module ot_svgr_bk #(parameter integer LBANKS=4,parameter integer LB=2,parameter integer IW=283+LB)(
 input wire hbm_clk,stream_clk,stream_rst_n,hbm_rst_n,input wire bk_hi,
 input wire [3:0] in_v,input wire [4*IW-1:0] in_data,output reg [3:0] cr,
 input wire res_v,input wire [LB-1:0] res_bank,input wire [15:0] res_epoch,input wire [11:0] res_total,input wire stop,
 input wire [3:0] read_v,input wire [LB-1:0] read_bank,input wire [23:0] read_row,
 output wire [3:0] complete,output wire [7:0] complete_bank,output wire [3:0] bfault,output wire [1023:0] read_data
);
 wire reset_both=stream_rst_n&&hbm_rst_n;wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 wire [1:0] fr[0:3];reg [3:0] owe[0:3];
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:u
  ot_svgr_landing #(.LBANKS(LBANKS),.LB(LB)) u_bank(.hbm_clk(hbm_clk),.hbm_rst_n(hrst),.stream_clk(stream_clk),.stream_rst_n(srst),.bank_id({bk_hi,2'(g)}),
   .in_v(in_v[g]),.in_data(in_data[IW*g+:IW]),.freed(fr[g]),.reserve_v(res_v),.reserve_bank(res_bank),.reserve_epoch(res_epoch),.reserve_total(res_total),.stop(stop),
   .complete_v(complete[g]),.complete_bank(complete_bank[2*g+:2]),.fault(bfault[g]),.read_v(read_v[g]),.read_bank(read_bank),.read_row(read_row[6*g+:6]),.read_data(read_data[256*g+:256]));
  // one credit per edge on the seam; owe holds what the synchroniser freed together
  always @(posedge hbm_clk or negedge hrst)begin
   if(!hrst)begin owe[g]<=0;cr[g]<=0;end
   else begin cr[g]<=(owe[g]!=0)||(fr[g]!=0);owe[g]<=owe[g]+4'(fr[g])-4'((owe[g]!=0)||(fr[g]!=0));end
  end
 end endgenerate
endmodule
