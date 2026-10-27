module ep_f6_copy_miter #(parameter MUT=0)(input clk,rst_n,we,slot_v,input[5:0]wa,slot_index,input[2:0]state,input[6:0]issued,words,input[305:0]din,output ok);
wire issue=slot_v && state==3'd4 && issued<words && slot_index==issued[5:0];
reg [305:0] dq,dq0,dq1;
reg [5:0] aq,aq0,aq1,ra,ra0,ra1;
reg wq,wq0,wq1;
always@(posedge clk)begin dq<=din;aq<=wa;wq<=we;dq0<=din;aq0<=wa;wq0<=we;dq1<=din^(MUT==1?306'd1:306'd0);aq1<=wa;wq1<=we;end
always@(posedge clk or negedge rst_n)begin
if(!rst_n)begin ra<=0;ra0<=0;ra1<=0;end
else if(issue)begin ra<=slot_index;ra0<=slot_index;ra1<=slot_index^(MUT==2?6'd1:6'd0);end
end
reg seen=0,seen_reset=0;
always@(posedge clk)begin seen<=1;if(!rst_n)seen_reset<=1;end
assign ok=(!seen||({dq,aq,wq}=={dq0,aq0,wq0}&&{dq,aq,wq}=={dq1,aq1,wq1}))&&(!seen_reset||(ra==ra0&&ra==ra1));
endmodule
