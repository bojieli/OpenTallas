// One arbitrary 16-lane histogram-bin transition. Includes simultaneous clear
// and read-return, whose existing priority uses the OLD histogram value.
module hist_split_transition #(parameter MUT=0)(
 input [15:0] hits,input [13:0] old_hist,input [3:0] op,rop,
 input rv,rst_n,output bad);
 integer count;
 reg[13:0] ref_next,new_next;
 wire accumulate=(rv&&rop==4)||op==2;
 function automatic [4:0] pop16(input [15:0] v);
  reg[1:0] p[0:7];reg[2:0] q[0:3];reg[3:0] h[0:1];
  begin
   for(integer i=0;i<8;i=i+1)p[i]={1'b0,v[2*i]}+{1'b0,v[2*i+1]};
   for(integer i=0;i<4;i=i+1)q[i]={1'b0,p[2*i]}+{1'b0,p[2*i+1]};
   for(integer i=0;i<2;i=i+1)h[i]={1'b0,q[2*i]}+{1'b0,q[2*i+1]};
   pop16={1'b0,h[0]}+{1'b0,h[1]};
  end
 endfunction
 always @*begin
  count=0;
  for(integer l=0;l<16;l=l+1)if(hits[l])count=count+1;
  ref_next=old_hist;
  if(!rst_n)ref_next=0;
  else begin
   if(op==3)ref_next=0;
   if(accumulate)ref_next=old_hist+14'(count);
  end
 end
 always @*begin
  new_next=old_hist;
  if(!rst_n)new_next=0;
  else begin
   if(op==3)new_next=0;
   if(accumulate)new_next=old_hist+14'(pop16(hits));
   if(MUT&&op==3)new_next=0;
  end
 end
 assign bad=(new_next!=ref_next);
endmodule
