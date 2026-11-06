module ot_tkm_merge_gold(input[343:0]entry,input[7:0]entry_tag,output[343:0]out);
localparam EW=86;reg[EW-1:0]es[0:3],eso[0:3];reg[1:0]et[0:3];
 function automatic [EW:0] stable_key(input[EW-1:0]e,input[1:0]tag);
  stable_key={e[EW-1:1],~tag};
 endfunction
 always @*begin:merge_sort
  reg[EW-1:0]m0,m1;reg[1:0]t0,t1;
  for(integer s=0;s<4;s=s+1)begin es[s]=entry[EW*s+:EW];et[s]=entry_tag[2*s+:2];end
  if(stable_key(es[0],et[0])>=stable_key(es[2],et[2]))begin
   eso[0]=es[0];m0=es[2];t0=et[2];
  end else begin eso[0]=es[2];m0=es[0];t0=et[0];end
  if(stable_key(es[1],et[1])>=stable_key(es[3],et[3]))begin
   eso[3]=es[3];m1=es[1];t1=et[1];
  end else begin eso[3]=es[1];m1=es[3];t1=et[3];end
  if(stable_key(m0,t0)>=stable_key(m1,t1))begin eso[1]=m0;eso[2]=m1;end
  else begin eso[1]=m1;eso[2]=m0;end
 end

assign out={eso[3],eso[2],eso[1],eso[0]};
endmodule
