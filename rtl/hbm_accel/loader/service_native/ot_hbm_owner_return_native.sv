`default_nettype none
(* keep_hierarchy = "yes" *)
module ot_hbm_owner_return_ring_slice #(parameter integer W=6)(
 input wire clk,first_rst_n,input wire [W-1:0] d,output wire [W-1:0] selected
);
 reg rst_q;always @(posedge clk or negedge first_rst_n)if(!first_rst_n)rst_q<=0;else rst_q<=1;
 (* keep = "yes" *) reg [1:0] wp,rp;reg [W-1:0] slots[0:3];
 always @(posedge clk or negedge rst_q)if(!rst_q)begin wp<=0;rp<=0;end else begin wp<=wp+1'b1;rp<=rp+1'b1;end
 always @(posedge clk)slots[wp]<=d;
 assign selected=slots[rp];
endmodule

// Real owner return datapath. Issue/reservation producer remains a separate obligation.
module ot_hbm_owner_return_native #(parameter integer J=0,MUT=0)(
 input wire clk,rst_n,alloc_v,input wire [16:0] alloc_tag,input wire [46:0] alloc_metadata,
 input wire return_v,input wire [16:0] return_tag,input wire [3:0] return_beat,
 input wire [255:0] return_data,input wire stop,input wire [1:0] target_reserved,
 output wire pair_v,pair_target,output wire [284:0] pair_packet,output reg fault,
 output wire [31:0] live
);
 wire [31:0] accepted;wire tag_ok,tag_fault;wire [16:0] at_q,rt_q;
 wire [2:0] len_q;wire [3:0] beat_q;wire av_q,rv_q;
 ot_hbm_owner_tags_native tags(.clk(clk),.rst_n(rst_n),.alloc_v(alloc_v),.alloc_tag(alloc_tag),
  .alloc_len(alloc_metadata[2:0]),.return_v(return_v),.return_tag(return_tag),.return_beat(return_beat),.stop(stop),
  .accepted_entry(accepted),.live(live),.response_ok(tag_ok),.fault(tag_fault),
  .alloc_tag_capture(at_q),.return_tag_capture(rt_q),.alloc_len_capture(len_q),
  .return_beat_capture(beat_q),.alloc_v_capture(av_q),.return_v_capture(rv_q));
 reg [43:0] metadata_input_q;reg [255:0] data_input_q;
 always @(posedge clk)begin metadata_input_q<=alloc_metadata[46:3];data_input_q<=return_data;end
 wire [46:0] metadata;wire metadata_v,metadata_written;
 ot_hbm_owner_metadata_native meta(.clk(clk),.rst_n(rst_n),.write_v(av_q),.write_addr(at_q[4:0]),
  .write_data({metadata_input_q,len_q}),.read_v(rv_q),.read_addr(rt_q[4:0]),
  .read_data(metadata),.read_valid(metadata_v),.write_done(metadata_written));
 wire [1:0] first_rst;
 for(genvar b=0;b<2;b=b+1)begin:g_first
  ot_hbm_owner_link_first_reset u_first(.clk(clk),.rst_n(rst_n),.q(first_rst[b]));
 end
 wire [277:0] ring_input={rv_q,rt_q,beat_q,data_input_q};wire [277:0] selected;
 for(genvar k=0;k<47;k=k+1)begin:g_ring
  localparam integer W=(k==46)?2:6;
  ot_hbm_owner_return_ring_slice #(.W(W)) u_slice(.clk(clk),.first_rst_n(first_rst[k/24]),
   .d(ring_input[k*6+:W]),.selected(selected[k*6+:W]));
 end
 reg ctrl_rst;always @(posedge clk or negedge first_rst[0])if(!first_rst[0])ctrl_rst<=0;else ctrl_rst<=1;
 reg [1:0] wp,ep;reg [3:0] eligible_ring;
 wire [3:0] selected_beat=selected[259:256];wire [16:0] selected_tag=selected[276:260];
 wire [1:0] offset=metadata[16]?(selected_beat[1:0]^metadata[15:14]):2'b0;
 wire [10:0] ordinal=metadata[13:3]+{7'd0,offset,2'b0};
 wire identity=selected[277]&&metadata[46:35]==selected_tag[16:5]&&selected_beat<metadata[2:0]&&ordinal[1:0]==2'(J);
 reg packet_v,packet_target;reg [284:0] packet;
 wire link_fault;
 always @(posedge clk or negedge ctrl_rst)
  if(!ctrl_rst)begin wp<=0;ep<=2;eligible_ring<=0;packet_v<=0;packet_target<=0;fault<=0;end
  else begin
   wp<=wp+1'b1;ep<=ep+1'b1;eligible_ring[wp]<=tag_ok;
   packet_v<=metadata_v&&eligible_ring[ep]&&identity&&!fault;
   packet_target<=ordinal[2];
   if(tag_fault||link_fault||(av_q&&metadata_input_q[43:32]!=at_q[16:5])||
     (metadata_v&&eligible_ring[ep]&&!identity))fault<=1;
  end
 always @(posedge clk)packet<={ordinal,metadata[18:17],metadata[34:19],selected[255:0]};
 ot_hbm_owner_pair_link #(.J(J),.MUT(MUT)) point_link(.clk(clk),.rst_n(rst_n),
  .in_v(packet_v),.stop(fault),.in_packet(packet),.in_target(packet_target),.target_reserved(target_reserved),
  .out_v(pair_v),.out_packet(pair_packet),.out_target(pair_target),.fault(link_fault));
endmodule
`default_nettype wire
