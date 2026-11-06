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
