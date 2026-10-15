`default_nettype none
// Variable arbitration is confined to the physical HBM boundary. No on-chip
// engine sees this ready. Sources hold each request until actual acceptance.
module ot_hbm_svc_phy_mux (
 input wire hbm_clk,hbm_rst_n,
 input wire [31:0] rd_v,output wire [31:0] rd_rdy,
 input wire [959:0] rd_addr,input wire [127:0] rd_len,input wire [543:0] rd_tag,
 input wire [31:0] wb_v,output wire [31:0] wb_rdy,
 input wire [959:0] wb_addr,input wire [127:0] wb_len,input wire [543:0] wb_tag,
 input wire [8191:0] wb_data,input wire [1023:0] wb_strb,
 output wire [31:0] k_v,input wire [31:0] k_rdy,
 output wire [959:0] k_addr,output wire [127:0] k_len,output wire [543:0] k_tag,
 output wire [31:0] k_we,output wire [8191:0] k_wdata,output wire [1023:0] k_wstrb
);
 reg [31:0] held,held_wb,prefer_wb;
 genvar p;generate for(p=0;p<32;p=p+1)begin:pc
  wire choose_wb=held[p]?held_wb[p]:(wb_v[p]&&(!rd_v[p]||prefer_wb[p]));
  assign k_v[p]=choose_wb?wb_v[p]:rd_v[p];
  assign rd_rdy[p]=!choose_wb&&k_rdy[p];
  assign wb_rdy[p]=choose_wb&&k_rdy[p];
  assign k_addr[p*30+:30]=choose_wb?wb_addr[p*30+:30]:rd_addr[p*30+:30];
  assign k_len[p*4+:4]=choose_wb?wb_len[p*4+:4]:rd_len[p*4+:4];
  assign k_tag[p*17+:17]=choose_wb?wb_tag[p*17+:17]:rd_tag[p*17+:17];
  assign k_we[p]=choose_wb;
  assign k_wdata[p*256+:256]=choose_wb?wb_data[p*256+:256]:256'd0;
  assign k_wstrb[p*32+:32]=choose_wb?wb_strb[p*32+:32]:32'd0;
  always @(posedge hbm_clk or negedge hbm_rst_n)begin
   if(!hbm_rst_n)begin held[p]<=0;held_wb[p]<=0;prefer_wb[p]<=0;end
   else if(k_v[p])begin
    if(k_rdy[p])begin held[p]<=0;prefer_wb[p]<=!choose_wb;end
    else begin held[p]<=1;held_wb[p]<=choose_wb;end
   end
  end
 end endgenerate
endmodule
`default_nettype wire
