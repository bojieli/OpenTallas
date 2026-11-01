module t #(parameter integer MUT=0)(input wire [3:0] a, output wire [5:0] y0, output wire [5:0] y1, output wire [5:0] y2);
 for(genvar l=0;l<3;l=l+1)begin:g
  wire [5:0] y = {a,(2'(l)^(MUT==2?2'd1:2'd0))};
 end
 assign y0=g[0].y; assign y1=g[1].y; assign y2=g[2].y;
endmodule
