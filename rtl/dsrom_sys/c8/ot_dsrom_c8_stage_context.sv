`timescale 1ns/1ps
// Two admitted descriptors, one actual retained singleton engine. C8 measures
// actual engine entry, not queue admission, as the stage initiation interval.
module ot_dsrom_c8_stage_context #(
 parameter integer NW=21, UW=10, EW=16, PAW=14
)(
 input wire clk,rst_n,
 input wire offer_v,
 output wire offer_ready,
 input wire [NW-1:0] offer_token,offer_pos,
 input wire [UW-1:0] offer_user,
 input wire [EW-1:0] offer_epoch,
 input wire [PAW-1:0] offer_entry,
 output wire context_v,
 input wire context_restored,
 output wire [NW+UW+EW-1:0] context_identity,
 output wire [NW-1:0] context_token,
 output wire [PAW-1:0] context_entry,
 output reg engine_start=0,
 output reg [NW-1:0] engine_token=0,engine_pos=0,
 output reg [UW-1:0] engine_user=0,
 output reg [PAW-1:0] engine_entry=0,
 output reg [NW+UW+EW-1:0] engine_identity=0,
 input wire engine_done,write_journal_quiet,write_quarantine,write_fault,
 output reg retire_v=0,
 output reg [NW+UW+EW-1:0] retire_identity=0,
 output reg active=0,quarantine=0
);
 localparam integer DW=2*NW+UW+EW+PAW;
 reg [DW-1:0] slots[0:1];
 reg rp=0,wp=0;reg [1:0] count=0;reg done_seen=0,done_armed=0;
 wire launch=context_v&&context_restored;
 wire push=offer_v&&offer_ready;
 assign offer_ready=rst_n&&!quarantine&&!write_quarantine&&!write_fault&&(count+active)<2;
 assign context_v=rst_n&&!quarantine&&!active&&count!=0&&write_journal_quiet&&!write_quarantine&&!write_fault;
 wire [EW-1:0] head_epoch;wire [UW-1:0] head_user;wire [NW-1:0] head_pos,head_token;wire [PAW-1:0] head_entry;
 assign {head_epoch,head_user,head_pos,head_token,head_entry}=slots[rp];
 assign context_identity={head_epoch,head_user,head_pos};
 assign context_token=head_token;assign context_entry=head_entry;
 always @(posedge clk) begin
  engine_start<=0;retire_v<=0;
  if(!rst_n) begin if(active||count!=0) quarantine<=1;end
  else if(!quarantine) begin
   if(write_quarantine||write_fault) quarantine<=1;
   if(push) begin slots[wp]<={offer_epoch,offer_user,offer_pos,offer_token,offer_entry};wp<=!wp;end
   if(launch) begin
    rp<=!rp;active<=1;done_seen<=0;done_armed<=0;engine_start<=1;
    engine_token<=head_token;engine_pos<=head_pos;engine_user<=head_user;engine_entry<=head_entry;
    engine_identity<=context_identity;
   end
   case({push,launch}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
   if(active&&!engine_start&&!engine_done)done_armed<=1;
   if(active&&done_armed&&engine_done)done_seen<=1;
   if(active&&(done_seen||(done_armed&&engine_done))&&write_journal_quiet&&!write_quarantine&&!write_fault) begin
    active<=0;done_seen<=0;retire_v<=1;retire_identity<=engine_identity;
   end
  end
 end
endmodule
