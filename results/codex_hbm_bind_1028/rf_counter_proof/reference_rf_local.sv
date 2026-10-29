module old(input wire clk_ctl,rst_n,input wire[127:0]rf_bword,input wire[255:0]rf_dsec,input wire[35:0]rf_bcmd,
output wire[127:0]rf_bword_u,output wire[255:0]rf_dsec_u,output wire[35:0]rf_bcmd_u);
 generate if(1)begin:g_rf_local
  // local copy beside the bank group: data words without reset; command valids reset (fault checks stay clean)
  reg [4*32-1:0] rf_bword_l; reg [255:0] rf_dsec_l; reg [4*8-1:0] rf_badr_l; reg [3:0] rf_bv_l; integer vb;
  always @(posedge clk_ctl)begin
   rf_bword_l<=rf_bword; rf_dsec_l<=rf_dsec;
   for(vb=0;vb<4;vb=vb+1)rf_badr_l[vb*8+:8]<=rf_bcmd[vb*9+:8];
  end
  always @(posedge clk_ctl or negedge rst_n)
   if(!rst_n)rf_bv_l<=4'd0;
   else for(vb=0;vb<4;vb=vb+1)rf_bv_l[vb]<=rf_bcmd[vb*9+8];
  wire [4*9-1:0] rf_bcmd_l={rf_bv_l[3],rf_badr_l[24+:8],rf_bv_l[2],rf_badr_l[16+:8],rf_bv_l[1],rf_badr_l[8+:8],rf_bv_l[0],rf_badr_l[0+:8]};
  assign rf_bword_u=rf_bword_l; assign rf_bcmd_u=rf_bcmd_l; assign rf_dsec_u=rf_dsec_l;

 end endgenerate
endmodule
