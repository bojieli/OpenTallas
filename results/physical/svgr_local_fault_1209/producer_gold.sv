module producer_gold #(parameter integer LBANKS=4,parameter integer LB=(LBANKS>2)?2:1,parameter integer OPEN_IL=0,parameter integer MUT=0,parameter integer OREG=0)(
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
 reg r_v;
 assign block_ready=(OPEN_IL!=0)?(ready_q&{LBANKS{~draining&&!o_v&&p_v==0&&!((OREG!=0)&&r_v)}}):ready_q;
 integer d;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin p_v<=0;p_last<=0;for(d=0;d<DLY;d=d+1)begin p_mask[d]<=0;p_ord[d]<=0;p_bank[d]<=0;p_ep[d]<=0;p_rq[d]<=0;end end
  else begin
   p_v<={p_v[DLY-2:0],o_v};p_last<={p_last[DLY-2:0],o_last};
   p_mask[0]<=o_mask;p_ord[0]<=o_ord;p_bank[0]<=o_bank;p_ep[0]<=o_epoch;p_rq[0]<=read_ordinal_q;
   for(d=1;d<DLY;d=d+1)begin p_mask[d]<=p_mask[d-1];p_ord[d]<=p_ord[d-1];p_bank[d]<=p_bank[d-1];p_ep[d]<=p_ep[d-1];p_rq[d]<=p_rq[d-1];end
  end
 end
 wire[1023:0]rot_data;
 generate for(g=0;g<4;g=g+1)begin:out_lane
  assign rot_data[256*g+:256]=seam_read_data[256*((p_rq[DLY-1][2:0]+g)%8)+:256];
 end endgenerate
 reg r_last;reg[3:0]r_mask;reg[1023:0]r_data;reg[10:0]r_ord;reg[LB-1:0]r_bank;reg[15:0]r_ep;
 always @(posedge stream_clk)if(OREG!=0)begin r_data<=rot_data;r_ord<=p_ord[DLY-1];r_bank<=p_bank[DLY-1];r_ep<=p_ep[DLY-1];end
 always @(posedge stream_clk or negedge srst)if(!srst)begin r_v<=0;r_last<=0;r_mask<=0;end
  else if(OREG!=0)begin r_v<=p_v[DLY-1];r_last<=p_last[DLY-1];r_mask<=p_mask[DLY-1];end
 assign out_v=(OREG!=0)?r_v:p_v[DLY-1];assign out_mask=(OREG!=0)?r_mask:p_mask[DLY-1];assign out_ordinal=(OREG!=0)?r_ord:p_ord[DLY-1];
 assign out_bank=(OREG!=0)?r_bank:p_bank[DLY-1];assign out_epoch=(OREG!=0)?r_ep:p_ep[DLY-1];assign out_last=(OREG!=0)?r_last:p_last[DLY-1];
 assign out_data=(OREG!=0)?r_data:rot_data;
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