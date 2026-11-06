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
module ot_tkm_merge_parallel #(parameter MUT=0)(input [343:0] entry, input [7:0] entry_tag, output [343:0] eso);
  wire [85:0] e0=entry[0+:86], e1=entry[86+:86], e2=entry[172+:86], e3=entry[258+:86];
  wire [86:0] k0={e0[85:1],~entry_tag[0+:2]}, k1={e1[85:1],~entry_tag[2+:2]}, k2={e2[85:1],~entry_tag[4+:2]}, k3={e3[85:1],~entry_tag[6+:2]};
  wire c02=k0>=k2, c13=k1>=k3;
  wire c21=k2>=k1, c23=k2>=k3, c01=k0>=k1, c03=k0>=k3;
  wire cm=c02 ? (c13 ? c21 : c23) : (c13 ? c01 : c03);
  wire pick=(MUT==1)?~cm:cm;
  wire [85:0] m0=c02?e2:e0, m1=c13?e1:e3;
  assign eso[0+:86]=c02?e0:e2;
  assign eso[258+:86]=c13?e3:e1;
  assign eso[86+:86]=pick?m0:m1;
  assign eso[172+:86]=(MUT==2)?(pick?m0:m1):(pick?m1:m0);
endmodule
