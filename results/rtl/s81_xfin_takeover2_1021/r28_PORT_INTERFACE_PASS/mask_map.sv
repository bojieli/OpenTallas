(* keep_hierarchy=1 *) module mask_new #(parameter integer LO=0)(input wire[11:0] power,output wire[7:0] mr,ms);
 wire[11:0] sub=-($signed(power)+12'sd149);
 wire[5:0] sh=($signed(sub)>12'sd63)?6'd63:sub[5:0];
 for(genvar g=0;g<8;g=g+1)begin:g_b
  assign mr[g]=({6'd0,6'(LO+g)}=={6'd0,sh}-12'd1);
  assign ms[g]=({6'd0,6'(LO+g)}<{6'd0,sh}-12'd1);
 end
endmodule
module mask_map(input wire[11:0] power,output wire[47:0] mr,ms);
for(genvar g=0;g<6;g=g+1)begin:g_m
 mask_new #(.LO(8*g)) u_m(.power(power),.mr(mr[g*8+:8]),.ms(ms[g*8+:8]));
end
endmodule
