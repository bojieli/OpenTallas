`timescale 1ns/1ps
// Root identity is captured from the actual core launch. Native owner debt must
// be empty before publishing core completion to the stage/controller.
module ot_dsrom_root_visible #(
 parameter integer NW=16, UW=8, EW=16, IDW=47
)(
 input wire clk,rst_n,start,
 input wire [NW-1:0] pos,
 input wire [UW-1:0] user,
 input wire engine_done,owners_quiet,owner_fault,owner_quarantine,
 output reg [IDW-1:0] root_identity=0,
 output reg active=0,done=0,retire_v=0,quarantine=0,fault=0
);
 reg [EW-1:0] epoch=0;
 reg armed=0,done_seen=0,start_seen=0;
 wire launch=start&&!start_seen;
 always @(posedge clk) begin
  retire_v<=0;
  if(!rst_n)begin
   if(active || !owners_quiet || start)quarantine<=1;
   // Outstanding identity/epoch/debt survive reset. No reset reconciliation.
  end else if(!quarantine&&!fault)begin
   start_seen<=start;
   if(owner_fault || owner_quarantine)begin fault<=owner_fault;quarantine<=1;end
   if(launch)begin
    if(active || !owners_quiet || epoch=={EW{1'b1}})begin fault<=1;quarantine<=1;end
    else begin
     epoch<=epoch+1'b1;root_identity<={16'(epoch+1'b1),10'(user),21'(pos)};
     active<=1;done<=0;armed<=0;done_seen<=0;
    end
   end
   if(active&&!engine_done&&!start)armed<=1;
   if(active&&armed&&engine_done)done_seen<=1;
   if(active&&(done_seen||(armed&&engine_done))&&owners_quiet&&!owner_fault&&!owner_quarantine)begin
    active<=0;done<=1;retire_v<=1;
   end
  end
 end
endmodule
