`timescale 1ns/1ps
`default_nettype none
// Actual source front shared by the full arithmetic parent and its independent
// exact port-trace proof. All state is flops or real programme/query macros.
module ot_hbm_attn_physical_program_query_front_local #(
 // LG=1: GEO-H four bank-pair LG read port groups (ot_hbm_attn_lg_read_group) at the VM face: same rq cycle,
 // +1 registered rr edge (FILL_LAT 8->9). LG=0 keeps the previous single-cluster face unchanged.
 parameter integer LG=0,
 parameter integer LGMUT=0 // bench only: 1 gives port group 1 group 0's bank-address offset
)(
 input wire clk,rst_n,input wire[3:0]bank_clk,input wire[3:0]lg_clk,input wire instruction_v,input wire[222:0]instruction,
 output wire[135:0]query_rq,input wire[2055:0]query_rr,
 output wire[6:0]events,output wire[9:0]phase,output wire event_valid,
 output wire[15:0]rows,output wire pv_only,output wire[8191:0]q_words,
 output wire q_present,output wire[8191:0]q_fields,output wire[4095:0]p_fields,output wire[1023:0]p_words,output wire p_present,output wire fault
);
 wire query_epoch,fr,fv,fe;wire[15:0]fs;wire[3:0]fh;wire[2:0]fb;wire pf,qf;
 wire pfv,pfe,pfault,ppv;wire[3:0]pfh,pfb;wire[15:0]pfs,pfr;
 localparam integer FL=8+(LG!=0?1:0);
 wire[135:0]qrq,prq,rq_face;wire[2055:0]qrr,prr,rr_face;reg[FL-1:0]qowners,powners;reg front_fault,p_hold;
 reg[9:0]p_row;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  qowners<=0;powners<=0;front_fault<=0;p_row<=0;p_hold<=0;
 end else begin
  qowners<={qowners[FL-2:0],fv};powners<={powners[FL-2:0],pfv};
  for(integer b=0;b<8;b=b+1)begin
   if(rr_face[b*257+256]!=(qowners[FL-1]|powners[FL-1]))front_fault<=1;
   if(qrq[b*17+16]&&prq[b*17+16])front_fault<=1;
  end
  if(events[0])begin p_row<=0;p_hold<=0;end
  else begin if(events[3])p_row<=p_row+4; if(ppv)p_hold<=1;end
 end
 for(genvar b=0;b<8;b=b+1)begin:g_source_owner
  assign rq_face[b*17+:17]=qrq[b*17+16]?qrq[b*17+:17]:(prq[b*17+16]?prq[b*17+:17]:17'd0);
  assign qrr[b*257+:257]={rr_face[b*257+256]&&qowners[FL-1],rr_face[b*257+:256]};
  assign prr[b*257+:257]={rr_face[b*257+256]&&powners[FL-1],rr_face[b*257+:256]};
 end
 generate if(LG!=0)begin:lg_groups
  for(genvar k=0;k<4;k=k+1)begin:g
   ot_hbm_attn_lg_read_group #(.GROUP((LGMUT==1&&k==1)?0:k))port_group(.clk(lg_clk[k]),.rst_n(rst_n),
    .q_fetch_v(fv),.q_fetch_base(fs),.p_fetch_v(pfv),.p_fetch_base(pfs),
    .rq(query_rq[k*34+:34]),.rr_i(query_rr[k*514+:514]),.rr_o(rr_face[k*514+:514]));
  end
 end else begin:single_cluster
  assign query_rq=rq_face;assign rr_face=query_rr;
 end endgenerate
 wire pread=pv_only&&(events[0]||(events[3]&&p_row+4<rows));
 ot_hbm_attn_p_prefetch_fields #(.FILL_LAT(FL))u_p(.clk(clk),.bank_clk(bank_clk),.rst_n(rst_n),.fetch_v(pfv),.fetch_epoch(pfe),.fetch_head(pfh),.fetch_burst(pfb),
  .fetch_base_sector(pfs),.profile_rows(rows_for_P),.rq(prq),.rr(prr),.read_v(pread),.read_epoch(query_epoch),
  .read_row(events[0]?10'd0:p_row+10'd4),.p_v(ppv),.p_w(p_words),.field_p_w(p_fields),.fault(pfault));
 // Pfetch carries its frozen T128/T640 profile before the launch rows latch.
 wire[15:0]rows_for_P=pfv?pfr:rows;
 assign p_present=ppv|p_hold;
 reg[3:0]qh;
 always @(posedge clk or negedge rst_n)if(!rst_n)qh<=0;
 else if(events[0])qh<=0;else if(events[1])qh<=qh+1'b1;
 wire qread=!pv_only&&(events[0]||(events[1]&&qh!=15));
 wire[3:0]qreadhead=events[0]?4'd0:qh+1'b1;
 ot_hbm_attn_physical_program_consumer u_program(.clk(clk),.rst_n(rst_n),.instruction_v(instruction_v),.instruction(instruction),
  .events(events),.phase(phase),.event_valid(event_valid),.rows(rows),.pv_only(pv_only),.query_epoch(query_epoch),
  .fetch_v(fv),.fetch_epoch(fe),.fetch_head(fh),.fetch_burst(fb),.fetch_base_sector(fs),
  .p_fetch_v(pfv),.p_fetch_epoch(pfe),.p_fetch_head(pfh),.p_fetch_burst(pfb),.p_fetch_base_sector(pfs),.p_fetch_rows(pfr),.running(fr),.fault(pf));
 ot_hbm_attn_query_prefetch_partitioned #(.FILL_LAT(FL))u_query(.clk(clk),.rst_n(rst_n),.fetch_v(fv),.fetch_epoch(fe),.fetch_head(fh),.fetch_burst(fb),.fetch_base_sector(fs),
  .rq(qrq),.rr(qrr),.read_v(qread),.read_epoch(query_epoch),.read_head(qreadhead),.q_v(q_present),.q_w(q_words),.field_q_w(q_fields),.fault(qf));
 assign fault=pf|qf|pfault|front_fault;
endmodule
`default_nettype wire
