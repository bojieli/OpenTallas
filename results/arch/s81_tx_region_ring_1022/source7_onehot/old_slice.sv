module old_slice #(parameter integer W=16, D=4, K=2, ID=0,
    AW=$clog2(D)) (
    input wire src_ck,dst_ck,src_rn,dst_rn,input wire[W-1:0]d,output reg[W-1:0]q);
    (* keep="true" *) reg[AW-1:0]wp,rp;
    reg[$clog2(K+2)-1:0]warm;
    (* keep="true" *) reg[W-1:0]bank[0:D-1];
    always @(posedge src_ck or negedge src_rn)
        if(!src_rn)wp<=0;else wp<=wp+1'b1;
    for(genvar s=0;s<D;s=s+1)begin:g_slot
        always @(posedge src_ck)if(wp==AW'(s))bank[s]<=d;
    end
    always @(posedge dst_ck or negedge dst_rn)
        if(!dst_rn)begin rp<=0;warm<=0;end
        else begin rp<=rp+1'b1;if(warm<K+1)warm<=warm+1'b1;end
    always @(posedge dst_ck)q<=(warm>=K)?bank[AW'(rp-K)]:{W{1'b0}};
endmodule
