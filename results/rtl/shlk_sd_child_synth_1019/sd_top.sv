module shlk_sd_child(input ck,rst_n,o_v,o_we,input[31:0]o_addr,input[255:0]o_d,output o_cr,output[583:0]hw,input[17:0]hc,output[7:0]host_ack_n,output fault);
dsdv_sh_sd #(.NS(2),.KVS(3),.ENG(-1),.STATIC(1),.HALF(1)) u_sd(.*);
endmodule
