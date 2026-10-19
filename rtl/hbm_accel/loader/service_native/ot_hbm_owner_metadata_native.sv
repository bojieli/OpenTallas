`default_nettype none
// Actual immutable owner record, opt-in separate component. No canonical edits.
(* keep_hierarchy = "yes" *)
module ot_hbm_owner_metadata_half #(parameter integer W=12,HALF=0)(
 input wire clk,first_rst_n,input wire write_v,input wire [4:0] write_addr,read_addr,
 input wire [W-1:0] write_data,output reg [W-1:0] half_q
);
 (* keep = "yes" *) reg rst_q;
 always @(posedge clk or negedge first_rst_n)if(!first_rst_n)rst_q<=0;else rst_q<=1;
 (* keep = "yes" *) reg [4:0] wa_q,ra_q;
 reg [W-1:0] data_q;
 (* keep = "yes" *) reg [15:0] ws_q,rs_q;
 reg wv_q,wv_d;
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin wv_q<=0;wv_d<=0;end
  else begin wv_q<=write_v;wv_d<=wv_q;end
 always @(posedge clk)begin wa_q<=write_addr;ra_q<=read_addr;data_q<=write_data;end
 reg [W-1:0] data_d;
 always @(posedge clk)data_d<=data_q;
 reg [W-1:0] words[0:15];
 for(genvar row=0;row<16;row=row+1)begin:g_word
  always @(posedge clk)begin
   ws_q[row]<=wa_q==5'(HALF*16+row);
   rs_q[row]<=ra_q==5'(HALF*16+row);
   if(wv_d&&ws_q[row])words[row]<=data_d;
  end
 end
 reg [W-1:0] read_pick;integer i;
 always @*begin read_pick=0;for(i=0;i<16;i=i+1)read_pick=read_pick|(words[i]&{W{rs_q[i]}});end
 always @(posedge clk)half_q<=read_pick;
endmodule

module ot_hbm_owner_metadata_native #(parameter integer MUT=0)(
 input wire clk,rst_n,write_v,input wire [4:0] write_addr,
 input wire [46:0] write_data,input wire read_v,input wire [4:0] read_addr,
 output reg [46:0] read_data,output reg read_valid,write_done
);
 (* keep = "yes" *) reg [1:0] first_rst;
 always @(posedge clk or negedge rst_n)if(!rst_n)first_rst<=0;else first_rst<=3;
 wire [46:0] half_data[0:1];
 for(genvar field=0;field<4;field=field+1)begin:g_field
  localparam integer W=(field==3)?11:12;
  for(genvar half=0;half<2;half=half+1)begin:g_half
   ot_hbm_owner_metadata_half #(.W(W),.HALF(half)) u_half(
    .clk(clk),.first_rst_n(first_rst[field/2]),.write_v(write_v),
    .write_addr(write_addr),.read_addr((MUT==1)?read_addr^5'd1:read_addr),
    .write_data(write_data[field*12+:W]),.half_q(half_data[half][field*12+:W]));
  end
 end
 always @(posedge clk)read_data<=(MUT==2)?half_data[0]:half_data[0]|half_data[1];
 reg ctrl_rst;
 always @(posedge clk or negedge first_rst[0])if(!first_rst[0])ctrl_rst<=0;else ctrl_rst<=1;
 reg [1:0] wp,rrp,wrp;reg [3:0] read_ring,write_ring;reg read_vq,write_vq;
 always @(posedge clk or negedge ctrl_rst)
  if(!ctrl_rst)begin wp<=0;rrp<=2;wrp<=3;read_ring<=0;write_ring<=0;read_vq<=0;write_vq<=0;read_valid<=0;write_done<=0;end
  else begin
   wp<=wp+1'b1;rrp<=rrp+1'b1;wrp<=wrp+1'b1;
   read_vq<=read_v;write_vq<=write_v;read_ring[wp]<=read_vq;write_ring[wp]<=write_vq;
   read_valid<=read_ring[(MUT==3)?wrp:rrp];write_done<=write_ring[wrp];
  end
endmodule
`default_nettype wire
