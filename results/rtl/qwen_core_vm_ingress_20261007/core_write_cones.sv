module core_boundary0(input wire[47:0]me_o_we,input wire me_mx_we,me_en,output wire[47:0]vw_me_we,output wire vw_mx_we);
localparam G=6144,SMIN=7,VM_OWNED_RAW=0;
    assign vw_me_we = me_o_we & {(G >> SMIN){me_en}};
    assign vw_mx_we = me_mx_we & me_en;
endmodule
module core_boundary1(input wire[47:0]me_o_we,input wire me_mx_we,me_en,output wire[47:0]vw_me_we,output wire vw_mx_we);
localparam G=6144,SMIN=7,VM_OWNED_RAW=1;
    assign vw_me_we = me_o_we & {(G >> SMIN){(VM_OWNED_RAW != 0) || me_en}};
    assign vw_mx_we = me_mx_we & ((VM_OWNED_RAW != 0) || me_en);
endmodule
