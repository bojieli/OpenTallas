`timescale 1ns/1ps
`default_nettype none
// Real HOST(b) consumer composition: source landing plus the existing six-slot
// static starter. Test this minimum component independently of the sequencer.
// Slot identity rides beside the descriptor at the same explicit landing age.
module dsdv_hostb_source #(parameter integer HOSTB_ENABLE=0, STATIC_KS6=0,
 parameter integer STATIC_KS_SPAN=0, parameter [31:0] STATIC_KS_GRAPH_TAG=0)(
 input wire ck,rst_n,select_hbe,upstream_fault,
 input wire [514:0] f_host,hbe_f_host,
 input wire [52:0] f_ks,starter_f_ks,input wire [2:0] hbe_ks_slot,
 output wire [514:0] issue_host,output wire [52:0] issue_ks,engram_f_ks,
 output wire [2:0] hostb_fault,output wire hb_starter_armed);
 wire [514:0] landed_host;wire [52:0] landed_ks, landed_engram;
 wire [2:0] landing_fault;
 wire [3:0] starter_fault;wire source_slot_fault;
 assign hostb_fault={landing_fault[2]|(|starter_fault)|source_slot_fault,landing_fault[1:0]};
 generate if(STATIC_KS6!=0)begin:g_starter
  wire selected, armed, done;wire [52:0] timed_ks;
  reg [2:0] slot_q, next_slot;reg slot_fault;
  always @(posedge ck)slot_q<=hbe_ks_slot;
  wire arm_word=landed_host[0]&&landed_host[514:513]==0&&landed_host[8:1]==8'h17;
  wire slot_bad=select_hbe&&landed_ks[52]&&(!selected||!armed||slot_q!=next_slot||next_slot>=6);
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin next_slot<=0;slot_fault<=0;end
   else if(arm_word)next_slot<=0;
   else if(select_hbe&&landed_ks[52])begin
    if(slot_bad)slot_fault<=1;
    else next_slot<=next_slot+1'b1;
   end
  end
  wire control_csr=landed_host[0]&&landed_host[514:513]==0&&
     (landed_host[8:1]==8'h17||landed_host[8:1]==8'h18||landed_host[8:1]==8'h19);
  dsdv_static_ks6 #(.SPAN(STATIC_KS_SPAN),.GRAPH_TAG(STATIC_KS_GRAPH_TAG)) u_static(
   .ck(ck),.rst_n(rst_n),.f_host(landed_host),.f_ks(landed_ks),
   .upstream_fault((|landing_fault)||upstream_fault||slot_fault||slot_bad),.timed_ks(timed_ks),
   .selected(selected),.armed(armed),.done(done),.fault(starter_fault));
  assign issue_host=control_csr?515'd0:landed_host;
  assign source_slot_fault=slot_fault||slot_bad;
  assign issue_ks=(select_hbe||selected||(control_csr&&landed_host[8:1]==8'h17))?timed_ks:landed_ks;
  assign engram_f_ks=issue_ks;
  assign hb_starter_armed=armed;
 end else begin:g_external
  assign issue_host=landed_host;assign issue_ks=landed_ks;
  assign engram_f_ks=landed_engram;assign hb_starter_armed=1'b0;assign starter_fault=0;assign source_slot_fault=0;
 end endgenerate
 dsdv_hostb_landing #(.ENABLE(HOSTB_ENABLE)) u_landing(.ck(ck),.rst_n(rst_n),.select_hbe(select_hbe),
 .legacy_f_host(f_host),.hbe_f_host(hbe_f_host),.legacy_f_ks(f_ks),.starter_f_ks(starter_f_ks),
 .seq_f_host(landed_host),.seq_f_ks(landed_ks),.engram_f_ks(landed_engram),.fault(landing_fault));
endmodule
`default_nettype wire
