module skid_old #(parameter integer WIDTH=1,MUT=0)(
    input wire clk,rst_n,input wire in_v,output wire in_r,
    input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
    output wire [WIDTH-1:0]out_data
);
    // kshare4c (DIE-HBM-66): same port behaviour as the head/tail skid. Two entries with pointers: a pop moves only rp, so the
    // ready pin has no fan-out into the data flops; data flops sit outside the async-reset block, so reset has none either.
    reg [1:0]cnt;reg wp,rp;
    reg [WIDTH-1:0]e0,e1;
    wire push=in_v&&in_r,pop=out_v&&out_r;
    assign in_r=cnt!=2'd2;assign out_v=cnt!=2'd0;assign out_data=rp?e1:e0;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin cnt<=2'd0;wp<=1'b0;rp<=1'b0;end
        else begin
            cnt<=cnt+{1'b0,push}-{1'b0,pop};
            if(push)wp<=!wp;
            if(pop)rp<=!rp;
        end
    always @(posedge clk)begin
        if(push&&!wp)e0<=in_data;
        if(push&&wp)e1<=in_data;
        // Checked negative control: illegally overwrite a stalled head.
        if(MUT!=0&&push&&out_v&&!out_r)begin if(rp)e1<=in_data;else e0<=in_data;end
    end
endmodule
