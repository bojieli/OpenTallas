module slice #(parameter IW=285, HEAD_REPL=0, MUT=0)(input hbm_clk,input [4*IW-1:0] heads,input [31:0] grants,output [8*IW-1:0] out);
wire [IW-1:0] head_c[0:3];reg [IW-1:0] head_q[0:3];
for(genvar p=0;p<4;p=p+1)begin assign head_c[p]=heads[IW*p+:IW];always @(posedge hbm_clk)head_q[p]<=head_c[p];end
for(genvar g=0;g<8;g=g+1)begin:response_fairness
wire[3:0]lg=grants[4*g+:4];
  wire [IW-1:0] lane_head[0:3];
  if(HEAD_REPL!=0)begin:g_head_rep
   for(genvar hp=0;hp<4;hp=hp+1)begin:g_pc
    (* keep *) reg [IW-1:0] q;
    always @(posedge hbm_clk)q<=head_c[hp];
    assign lane_head[hp]=head_c[hp];
   end
  end else begin:g_head_shared
   for(genvar hp=0;hp<4;hp=hp+1)begin:g_pc
    assign lane_head[hp]=head_q[hp];
   end
  end
  wire [IW-1:0] h0=(MUT==11)?head_c[0]:lane_head[0],h1=(MUT==11)?head_c[1]:lane_head[1],h2=(MUT==11)?head_c[2]:lane_head[2],h3=(MUT==11)?head_c[3]:lane_head[3];
  reg [IW-1:0] lane_d_q;
  always @(posedge hbm_clk)lane_d_q<=({IW{lg[0]}}&h0)|({IW{lg[1]}}&h1)|({IW{lg[2]}}&h2)|({IW{lg[3]}}&h3);
  assign out[IW*g+:IW]=lane_d_q;
end
endmodule
