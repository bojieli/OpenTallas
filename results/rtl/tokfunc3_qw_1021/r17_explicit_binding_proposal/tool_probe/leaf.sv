module leaf #(parameter integer N=32)(input wire clk,rst_n,input wire[31:0]x,output wire[31:0]y);
reg[31:0]state[0:N-1];
always @(posedge clk or negedge rst_n)begin
 if(!rst_n)for(integer k=0;k<N;k=k+1)state[k]<=0;
 else begin state[0]<=x;for(integer k=1;k<N;k=k+1)state[k]<=state[k-1]+32'(k);end
end
assign y=state[N-1];
endmodule
