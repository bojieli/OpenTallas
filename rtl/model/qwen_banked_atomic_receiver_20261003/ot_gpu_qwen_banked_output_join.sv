`timescale 1ps/1ps
// No state or synthetic completion. All receiver edges are common actual edges.
module ot_gpu_qwen_banked_output_join #(parameter bit ENABLE=0)(
 input wire [63:0] profile_valid,input wire [4095:0] required_banks,
 input wire [63:0] root_busy,root_fault,
 input wire [15295:0] root_held_tuple,root_visible_tuple,root_publish_tuple,
 input wire [3519:0] root_held_owner,root_publish_owner,
 input wire [2047:0] root_publish_mask,
 input wire [63:0] root_ack_ready,root_visible_valid,root_publish_valid,
 input wire [63:0] bank_live,bank_started,bank_fault,
 input wire [15295:0] bank_tuple,bank_ack_tuple,
 input wire [3519:0] bank_ack_owner,
 input wire [2047:0] bank_ack_mask,
 input wire [4095:0] bank_required_union,bank_required_input,bank_required_output,
 input wire [63:0] bank_ack_valid,bank_visible_ready,bank_publish_ready,
 output reg [63:0] root_ack_valid,root_visible_ready,root_publish_ready,
 output wire [15295:0] root_ack_tuple,
 output wire [3519:0] root_ack_owner,
 output reg [2047:0] root_ack_mask,
 output reg [255:0] root_output_presence,
 output reg [63:0] bank_ack_ready,bank_visible_valid,bank_publish_valid,
 output wire [15295:0] bank_visible_tuple,bank_publish_tuple,
 output reg [3519:0] bank_publish_owner,
 output reg [2047:0] bank_publish_mask
);
 assign root_ack_tuple=root_held_tuple;assign root_ack_owner=root_held_owner;
 assign bank_visible_tuple=bank_tuple;assign bank_publish_tuple=bank_tuple;
 integer a,b,actor;reg okay,ack_ok,vis_ok,pub_ok;reg [63:0] needed,outs,ins;
 reg [238:0] held,bt;reg [31:0] root_pages,local_pages;
 function automatic [31:0] pages(input [238:0] t);
  integer n;begin n=t[9:0]-{1'b0,t[18:10]};if(n<1||n>32)pages=0;else pages=32'hffffffff>>(32-n);end
 endfunction
 always @* begin
  root_ack_valid=0;root_visible_ready=0;root_publish_ready=0;root_ack_mask=0;root_output_presence=0;
  bank_ack_ready=0;bank_visible_valid=0;bank_publish_valid=0;bank_publish_owner=0;bank_publish_mask=0;
  okay=0;ack_ok=0;vis_ok=0;pub_ok=0;needed=0;outs=0;ins=0;held=0;bt=0;root_pages=0;local_pages=0;actor=0;
  for(a=0;a<64;a=a+1)begin
   held=root_held_tuple[a*239+:239];needed=required_banks[a*64+:64];
   outs=bank_required_output[a*64+:64];ins=bank_required_input[a*64+:64];
   root_pages=outs!=0?pages(held):0;
   // The actor participates even if it owns no physical input/output RF home.
   root_output_presence[a*4+:4]=ENABLE&&profile_valid[a]&&(outs!=0)?4'd1:4'd0;
   okay=ENABLE&&profile_valid[a]&&needed[a]&&root_busy[a]&&!root_fault[a]&&held[35:30]==a;
   ack_ok=okay;vis_ok=okay&&(root_visible_tuple[a*239+:239]==held);
   pub_ok=okay&&(root_publish_tuple[a*239+:239]==held)&&(root_publish_owner[a*55+:55]==root_held_owner[a*55+:55])&&(root_publish_mask[a*32+:32]==root_pages);
   for(b=0;b<64;b=b+1)if(needed[b])begin
    bt=bank_tuple[b*239+:239];local_pages=outs[b]?root_pages:0;
    if(!bank_live[b]||!bank_started[b]||bank_fault[b]||bt!=held||bank_required_union[b*64+:64]!=needed||bank_required_input[b*64+:64]!=ins||bank_required_output[b*64+:64]!=outs)begin ack_ok=0;vis_ok=0;pub_ok=0;end
    if(!bank_ack_valid[b]||bank_ack_tuple[b*239+:239]!=held||bank_ack_owner[b*55+:55]!=root_held_owner[a*55+:55]||bank_ack_mask[b*32+:32]!=local_pages)ack_ok=0;
    if(!bank_visible_ready[b])vis_ok=0;
    if(!bank_publish_ready[b])pub_ok=0;
   end
   root_ack_valid[a]=ack_ok;root_ack_mask[a*32+:32]=root_pages;
   root_visible_ready[a]=vis_ok;root_publish_ready[a]=pub_ok;
  end
  for(b=0;b<64;b=b+1)begin
   bt=bank_tuple[b*239+:239];actor=bt[35:30];needed=required_banks[actor*64+:64];outs=bank_required_output[actor*64+:64];
   if(ENABLE&&profile_valid[actor]&&needed[b]&&bank_live[b]&&bt==root_held_tuple[actor*239+:239])begin
    bank_ack_ready[b]=root_ack_ready[actor]&&root_ack_valid[actor];
    bank_visible_valid[b]=root_visible_valid[actor]&&root_visible_ready[actor];
    bank_publish_valid[b]=root_publish_valid[actor]&&root_publish_ready[actor];
    bank_publish_owner[b*55+:55]=root_held_owner[actor*55+:55];
    bank_publish_mask[b*32+:32]=outs[b]?root_publish_mask[actor*32+:32]:0;
   end
  end
 end
endmodule
