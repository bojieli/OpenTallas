module hist_proof(input wire[15:0] v,output wire bad);
 function automatic [4:0] pop16(input [15:0] v);
  reg[1:0] p[0:7];reg[2:0] q[0:3];reg[3:0] h[0:1];
  begin
   for(integer i=0;i<8;i=i+1)p[i]={1'b0,v[2*i]}+{1'b0,v[2*i+1]};
   for(integer i=0;i<4;i=i+1)q[i]={1'b0,p[2*i]}+{1'b0,p[2*i+1]};
   for(integer i=0;i<2;i=i+1)h[i]={1'b0,q[2*i]}+{1'b0,q[2*i+1]};
   pop16={1'b0,h[0]}+{1'b0,h[1]};
  end
 endfunction
 integer old_count;
 always @*begin
  old_count=0;
  for(integer l=0;l<16;l=l+1)if(v[l])old_count=old_count+1;
 end
 assign bad=(old_count!=32'(pop16(v)));
endmodule
