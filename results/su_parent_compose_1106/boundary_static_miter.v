module su_boundary_miter #(parameter MUT=0)(input [6143:0] old_q,input [767:0] old_vm_addr,input [767:0] old_kv_addr,input [31:0] vm_we,output equal);
wire [5119:0] compact;
genvar n,p;
generate for(n=0;n<32;n=n+1)begin
assign compact[n*160+:160]={old_q[n*192+160+:32],old_q[n*192+:128]};
end endgenerate
wire [4095:0] old_operands,new_operands;
generate for(n=0;n<32;n=n+1)begin for(p=0;p<4;p=p+1)begin
assign old_operands[(n*4+p)*32+:32]=old_q[n*192+p*32+:32];
assign new_operands[(n*4+p)*32+:32]=compact[n*160+((MUT==2)?(p^1):p)*32+:32];
end end endgenerate
wire [1023:0] old_drain,new_drain;
genvar hh,ii;
generate for(hh=0;hh<2;hh=hh+1)begin for(ii=0;ii<2;ii=ii+1)begin for(n=0;n<8;n=n+1)begin
assign old_drain[(hh*16+ii*8+n)*32+:32]=old_q[(8*hh+16*ii+n)*192+160+:32];
assign new_drain[(hh*16+ii*8+n)*32+:32]=compact[(8*hh+16*ii+n)*160+((MUT==1)?3:4)*32+:32];
end end end endgenerate
wire [575:0] new_vm_addr,new_kv_addr;
wire [575:0] old_selected,new_selected;
generate for(n=0;n<32;n=n+1)begin
assign new_vm_addr[n*18+:18]=old_vm_addr[n*24+:18];
assign new_kv_addr[n*18+:18]=old_kv_addr[n*24+:18];
assign old_selected[n*18+:18]=vm_we[n]?old_vm_addr[n*24+:18]:old_kv_addr[n*24+:18];
assign new_selected[n*18+:18]=vm_we[n]?new_vm_addr[n*18+:18]:new_kv_addr[n*18+:18];
end endgenerate
assign equal=(old_selected==new_selected)&&(old_operands==new_operands)&&(old_drain==new_drain);
endmodule
