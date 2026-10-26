`timescale 1ns/1ps
`default_nettype none
// Actual source front shared by the full arithmetic parent and its independent
// exact port-trace proof. All state is flops or real programme/query macros.
module ot_hbm_attn_physical_program_query_front(
 input wire clk,rst_n,input wire instruction_v,input wire[222:0]instruction,
 output wire[135:0]query_rq,input wire[2055:0]query_rr,
 output wire[6:0]events,output wire[9:0]phase,output wire event_valid,
 output wire[15:0]rows,output wire pv_only,output wire[8191:0]q_words,
 output wire q_present,output wire[1023:0]p_words,output wire p_present,output wire fault
);
 wire query_epoch,fr,fv,fe;wire[15:0]fs;wire[3:0]fh;wire[2:0]fb;wire pf,qf;
 wire pfv,pfe,pfault,ppv;wire[3:0]pfh,pfb;wire[15:0]pfs,pfr;
 wire[135:0]qrq,prq;wire[2055:0]qrr,prr;reg[7:0]qowners,powners;reg front_fault,p_hold;
 reg[9:0]p_row;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  qowners<=0;powners<=0;front_fault<=0;p_row<=0;p_hold<=0;
 end else begin
  qowners<={qowners[6:0],fv};powners<={powners[6:0],pfv};
  for(integer b=0;b<8;b=b+1)begin
   if(query_rr[b*257+256]!=(qowners[7]|powners[7]))front_fault<=1;
   if(qrq[b*17+16]&&prq[b*17+16])front_fault<=1;
  end
  if(events[0])begin p_row<=0;p_hold<=0;end
  else begin if(events[3])p_row<=p_row+4; if(ppv)p_hold<=1;end
 end
 for(genvar b=0;b<8;b=b+1)begin:g_source_owner
  assign query_rq[b*17+:17]=qrq[b*17+16]?qrq[b*17+:17]:(prq[b*17+16]?prq[b*17+:17]:17'd0);
  assign qrr[b*257+:257]={query_rr[b*257+256]&&qowners[7],query_rr[b*257+:256]};
  assign prr[b*257+:257]={query_rr[b*257+256]&&powners[7],query_rr[b*257+:256]};
 end
 wire pread=pv_only&&(events[0]||(events[3]&&p_row+4<rows));
 ot_hbm_attn_p_prefetch u_p(.clk(clk),.rst_n(rst_n),.fetch_v(pfv),.fetch_epoch(pfe),.fetch_head(pfh),.fetch_burst(pfb),
  .fetch_base_sector(pfs),.profile_rows(rows_for_P),.rq(prq),.rr(prr),.read_v(pread),.read_epoch(query_epoch),
  .read_row(events[0]?10'd0:p_row+10'd4),.p_v(ppv),.p_w(p_words),.fault(pfault));
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
 ot_hbm_attn_query_prefetch u_query(.clk(clk),.rst_n(rst_n),.fetch_v(fv),.fetch_epoch(fe),.fetch_head(fh),.fetch_burst(fb),.fetch_base_sector(fs),
  .rq(qrq),.rr(qrr),.read_v(qread),.read_epoch(query_epoch),.read_head(qreadhead),.q_v(q_present),.q_w(q_words),.fault(qf));
 assign fault=pf|qf|pfault|front_fault;
endmodule
`default_nettype wire
