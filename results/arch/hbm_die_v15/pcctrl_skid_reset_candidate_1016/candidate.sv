module candidate_skid #(parameter integer WIDTH=1,MUT=0)(
 input wire clk,rst_n,in_v,output wire in_r,input wire [WIDTH-1:0]in_data,
 output wire out_v,input wire out_r,output wire[WIDTH-1:0]out_data);
 reg head_valid,tail_valid;reg[WIDTH-1:0]head_data,tail_data;
 wire push=in_v&&in_r,pop=out_v&&out_r;
 assign in_r=!tail_valid;assign out_v=head_valid;assign out_data=head_data;
 wire head_load=(push&&(!head_valid||pop))||(pop&&tail_valid);
 wire tail_load=push&&head_valid&&!pop;
 always @(posedge clk)begin
   if(head_load) head_data<=push?in_data:tail_data;
   if(tail_load) tail_data<=in_data;
   if(MUT!=0 && push && head_valid && !out_r)head_data<=in_data;
 end
 always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin head_valid<=0;tail_valid<=0;end
   else if(push)begin head_valid<=1;tail_valid<=head_valid&&!pop;end
   else if(pop)begin head_valid<=tail_valid;tail_valid<=0;end
 end
endmodule
