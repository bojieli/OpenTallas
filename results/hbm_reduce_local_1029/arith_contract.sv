module ot_hgi_coll_pring_static_add_lane #(parameter LAT=8)(input clk,rst_n,valid_in,input [31:0] a,b,output [31:0] y,output valid_out);
reg [31:0] d[0:LAT-1];reg [LAT-1:0] v;
always @(posedge clk)begin d[0]<=a^b;for(integer k=1;k<LAT;k=k+1)d[k]<=d[k-1];end
always @(posedge clk or negedge rst_n)if(!rst_n)v<=0;else v<={v[LAT-2:0],valid_in};
assign y=d[LAT-1];assign valid_out=v[LAT-1];endmodule
