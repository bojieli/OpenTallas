module native_writer(input ck,rsi,input[23:0]i,output[191:0]bank,output[7:0]vld);
wire[31:0]epo;
ot_pl_land_n32_local_w #(.W(24),.D(8)) u(ck,rsi,i,bank,epo,vld);
endmodule
