module formal(input wire clk,input wire[15:0]mask,input wire[31:0]payload,output wire bad);
 wire[31:0]y;wire[95:0]pair;wire[119:0]quad;
 hidx_c1_compact #(.ID(0)) c(.clk(clk),.lane_v(mask[7:0]),.payload(payload),.y(y));
 hidx_c1_count #(.ID(0),.N(8),.W(4))p(.clk(clk),.lane_v(mask[7:0]),.selects(pair));
 hidx_c1_count #(.ID(1),.N(16),.W(5))q(.clk(clk),.lane_v(mask),.selects(quad));
 reg[31:0]refc,refq;reg[15:0]saved_mask;reg[3:0]pc,pr;reg[4:0]qc,qr;
 integer k,s;always @*begin refc=0;s=0;for(k=0;k<8;k=k+1)if(mask[k])begin refc[s*4+:4]=payload[k*4+:4];s=s+1;end end
 always @*begin pc=0;qc=0;for(k=0;k<16;k=k+1)if(saved_mask[k])begin qc=qc+1;if(k<8)pc=pc+1;end end
 always @(posedge clk)begin refq<=refc;saved_mask<=mask;pr<=pc;qr<=qc;end
 assign bad=(y!=refq)||(pair!={24{pr}})||(quad!={24{qr}});
endmodule
