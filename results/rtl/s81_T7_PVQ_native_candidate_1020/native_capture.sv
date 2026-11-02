module native_capture(input clk,dr_on,input[2:0]p_i,input[2119:0]pb,input[439:0]pv_provenance,output reg[512:0]pv_od);
localparam PVB=2120,NT=4,H=16;
always @(posedge clk) if (dr_on)
        pv_od <= (p_i == 0) ? {1'b1, pv_provenance, pb[PVB-1 -: 8], pb[NT*H-1:0]} : {1'b0, pb[NT*H + 32'(p_i - 1)*H*32 +: H*32]};
endmodule
