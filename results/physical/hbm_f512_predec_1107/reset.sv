`default_nettype none
(* keep_hierarchy, keep *) module ot_hbm_face_rst_relay #(parameter integer W=1,N=1)(input wire clk,input wire[W-1:0] rst_ni,output wire[W-1:0] rst_no);
for(genvar b=0;b<W;b=b+1)begin:g
reg q;always @(posedge clk or negedge rst_ni[b]) if(!rst_ni[b])q<=1'b0;else q<=1'b1;assign rst_no[b]=q;
end
endmodule
