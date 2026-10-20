module leaf(input a,b,output y); assign y=a&b; endmodule
module coupon #(parameter MUT=0)(input clk,rst_n,push_req,pop_req,input [9:0] first_data,input hgo_hit,output ok);
  reg [3:0] count;
  reg [1:0] hf;
  reg [9:0] copy0,copy1;
  wire pop=(count!=0)&&pop_req;
  wire push=push_req&&(count<8);
  wire [3:0] nx=count+(push?4'd1:4'd0)-(pop?4'd1:4'd0);
  wire en=pop?(hf[1]||push):(hf[0]&&push);
  always @(posedge clk) begin
    if(!rst_n) begin count<=0;hf<=2'b01;end
    else begin count<=nx;hf<={nx>1,nx==0};end
    if(en) copy0<=first_data;
    if(MUT==2 ? (en&&pop):en) copy1<=(MUT==1)?~first_data:first_data;
  end
  reg [191:0] hgo;
  for(genvar g=0;g<24;g=g+1) begin:decision
    wire set_group;
    leaf u(.a(hgo_hit),.b(rst_n),.y(set_group));
    always @(posedge clk)
      if(!rst_n) hgo[g*8+:8] <= (MUT==3 && g==23)?8'hff:8'h00;
      else if(set_group) hgo[g*8+:8]<=8'hff;
  end
  assign ok=(!rst_n)||((count==0||copy0==copy1)&&(hgo=={192{hgo[0]}}));
endmodule
