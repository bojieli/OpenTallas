module m(input clk,rst_n,m_issue, input [15:0] lm_seen, input [3:0] issue,done_seen,input [255:0] zflat,input [63:0] zmask,input start_q,sq,act_q,other_fault, output eq);
wire [63:0] zseen[0:3];
for(genvar a=0;a<4;a=a+1) assign zseen[a]=zflat[64*a+:64];
reg gq;reg [16:0] cq;reg gf,cf;
always @(posedge clk or negedge rst_n) if(!rst_n)gq<=0;else begin
            gq<=(m_issue && lm_seen!=16'hffff) ||
                ((|issue) && (done_seen!=4'hf || zseen[0][63:0]!=zmask || zseen[1][63:0]!=zmask ||
                    zseen[2][63:0]!=zmask || zseen[3][63:0]!=zmask));
end
always @(posedge clk or negedge rst_n) if(!rst_n)cq<=0;else begin
            // Same-edge captures; the existing |gqv consumer observes the identical error.
            cq[0]<=(m_issue && lm_seen!=16'hffff) || ((|issue) && done_seen!=4'hf);
            for(integer fg_a=0;fg_a<4;fg_a=fg_a+1)
                for(integer fg_s=0;fg_s<4;fg_s=fg_s+1)
                    cq[1+4*fg_a+fg_s] <= (|issue) &&
                        (zseen[fg_a][16*fg_s+:16] != zmask[16*fg_s+:16]);
end
wire captured=(|cq);
always @(posedge clk or negedge rst_n)if(!rst_n)gf<=0;else if(start_q)gf<=sq;else if(act_q&&(gq||other_fault))gf<=1;
always @(posedge clk or negedge rst_n)if(!rst_n)cf<=0;else if(start_q)cf<=sq;else if(act_q&&(captured||other_fault))cf<=1;
assign eq=(gq==captured)&&(gf==cf);
endmodule
