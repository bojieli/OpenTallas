module gate #(parameter integer MUT=0)(input clk,r_ce_in,input[4:0]r_addr_in,output reg[127:0]rd_out,input w_ce_in,input[4:0]w_addr_in,input[127:0]wd_in,w_mask_in);
reg[127:0]arr[0:31]; reg[127:0]delayed_read;
integer i;
always @(posedge clk)begin
 if(r_ce_in)begin
  if(MUT==1)begin delayed_read<=arr[r_addr_in];rd_out<=delayed_read;end
  else if(MUT==3 && w_ce_in && w_addr_in==r_addr_in)rd_out<=(arr[r_addr_in]&~w_mask_in)|(wd_in&w_mask_in);
  else rd_out<=arr[r_addr_in];
 end
 if(w_ce_in)for(i=0;i<128;i=i+1)if(MUT==2 || w_mask_in[i])arr[w_addr_in][i]<=wd_in[i];
end
endmodule
