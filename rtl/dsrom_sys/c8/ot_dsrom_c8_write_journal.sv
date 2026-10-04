`timescale 1ns/1ps
// Native per-PC accepted-write enrollment and real backend visible receipts.
// No data-store observation, request grant or engine-done substitutes for ACK.
module ot_dsrom_c8_write_journal #(
 parameter integer NPC=128, DEPTH=64, AW=30, IDW=47, TAGW=17,
 parameter integer PW=$clog2(DEPTH), CW=$clog2(DEPTH+1)
)(
 input wire clk,rst_n,
 input wire [NPC-1:0] accepted_write, backend_wr_done,
 input wire [NPC*AW-1:0] accepted_addr,backend_done_addr,
 input wire [NPC*TAGW-1:0] accepted_tag,backend_done_tag,
 input wire [NPC*2-1:0] accepted_writer,
 input wire [IDW-1:0] accepted_identity,
 output reg [NPC-1:0] visible_v,
 output reg [NPC*IDW-1:0] visible_identity,
 output reg [NPC*AW-1:0] visible_addr,
 output reg [NPC*2-1:0] visible_writer,
 output wire quiet,
 output wire [NPC*CW-1:0] debt,
 output reg quarantine=0, fault=0
);
 reg [IDW+AW+2-1:0] journal[0:NPC-1][0:DEPTH-1];
 reg [TAGW-1:0] tags[0:NPC-1][0:DEPTH-1];
 reg [DEPTH-1:0] valid[0:NPC-1];
 reg [CW-1:0] count[0:NPC-1];
 wire [NPC-1:0] empty;
 genvar g;
 generate for(g=0;g<NPC;g=g+1) begin:g_ports
  assign empty[g]=count[g]==0;
  assign debt[g*CW+:CW]=count[g];
 end endgenerate
 assign quiet=(&empty)&&!(|accepted_write)&&!(|backend_wr_done)&&!quarantine&&!fault;
 integer p,k,matched,match_count,free_seat;
 initial begin
  visible_v=0;visible_identity=0;visible_addr=0;visible_writer=0;
  for(integer q=0;q<NPC;q=q+1) begin valid[q]=0;count[q]=0;end
 end
 // Cold initialization above is diagnostic only. Warm reset preserves debt;
 // no reset/empty signal authorizes reconciliation or irreversible retirement.
 always @(posedge clk) begin
  visible_v<=0;
  if(!rst_n) begin
   if(!(&empty)) quarantine<=1;
   if(|accepted_write) begin fault<=1;quarantine<=1;end
  end else if(!quarantine&&!fault) begin
   for(p=0;p<NPC;p=p+1) begin
    matched=-1;match_count=0;free_seat=-1;
    for(k=0;k<DEPTH;k=k+1) begin
     if(!valid[p][k] && free_seat<0)free_seat=k;
     if(valid[p][k] && tags[p][k]==backend_done_tag[p*TAGW+:TAGW] && journal[p][k][2+:AW]==backend_done_addr[p*AW+:AW]) begin matched=k;match_count=match_count+1;end
    end
    if(backend_wr_done[p]&&match_count!=1) begin fault<=1;quarantine<=1;end
    if(accepted_write[p]&&count[p]==DEPTH&&!backend_wr_done[p]) begin fault<=1;quarantine<=1;end
    if(backend_wr_done[p]&&match_count==1) begin
     visible_v[p]<=1;
     {visible_identity[p*IDW+:IDW],visible_addr[p*AW+:AW],visible_writer[p*2+:2]}<=journal[p][matched];
     valid[p][matched]<=0;
     if(free_seat<0)free_seat=matched;
    end
    if(accepted_write[p]&&(count[p]<DEPTH||backend_wr_done[p]&&match_count==1)) begin
     journal[p][free_seat]<={accepted_identity,accepted_addr[p*AW+:AW],accepted_writer[p*2+:2]};
     tags[p][free_seat]<=accepted_tag[p*TAGW+:TAGW];valid[p][free_seat]<=1;
    end
    case({accepted_write[p]&&(count[p]<DEPTH||backend_wr_done[p]&&match_count==1),backend_wr_done[p]&&match_count==1})
     2'b10:count[p]<=count[p]+1'b1;
     2'b01:count[p]<=count[p]-1'b1;
     default:count[p]<=count[p];
    endcase
   end
  end
 end
endmodule
