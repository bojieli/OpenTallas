module tree_old(input clk, input fin, input [263:0] ik, input [143:0] ii,
 input [255:0] ib, input [7:0] iv, output [83:0] result);
localparam LP=8, IW=18, LL=3;
reg [32:0] tk[0:LL][0:LP-1]; reg [IW-1:0] ti[0:LL][0:LP-1];
reg [31:0] tbits[0:LL][0:LP-1]; reg tvl[0:LL][0:LP-1];
wire [32:0] bk[0:LP-1]; wire [IW-1:0] bi[0:LP-1]; wire [31:0] bv_bits[0:LP-1];
wire [7:0] seen=iv;
genvar i; generate for(i=0;i<8;i=i+1) begin
 assign bk[i]=ik[33*i+:33]; assign bi[i]=ii[18*i+:18]; assign bv_bits[i]=ib[32*i+:32];
end endgenerate
assign result={tvl[LL][0],tk[LL][0],ti[LL][0],tbits[LL][0]};
integer lv,e;
    always @(posedge clk) begin
        if (fin) begin
            for (e = 0; e < LP; e = e + 1) begin
                tbits[0][e] <= bv_bits[e]; tk[0][e] <= bk[e]; ti[0][e] <= bi[e]; tvl[0][e] <= seen[e];
            end
        end
        for (lv = 0; lv < LL; lv = lv + 1) begin
            for (e = 0; e < (LP >> (lv + 1)); e = e + 1) begin
                if (!tvl[lv][2*e+1] || (tvl[lv][2*e] && (tk[lv][2*e] > tk[lv][2*e+1] ||
                    (tk[lv][2*e] == tk[lv][2*e+1] && ti[lv][2*e] < ti[lv][2*e+1])))) begin
                    tbits[lv+1][e] <= tbits[lv][2*e]; tk[lv+1][e] <= tk[lv][2*e]; ti[lv+1][e] <= ti[lv][2*e]; tvl[lv+1][e] <= tvl[lv][2*e];
                end else begin
                    tbits[lv+1][e] <= tbits[lv][2*e+1]; tk[lv+1][e] <= tk[lv][2*e+1]; ti[lv+1][e] <= ti[lv][2*e+1]; tvl[lv+1][e] <= tvl[lv][2*e+1];
                end
            end
        end
    end
endmodule
module tree_new(input clk, input fin, input [263:0] ik, input [143:0] ii,
 input [255:0] ib, input [7:0] iv, output [83:0] result);
localparam LP=8, IW=18, LL=3;
reg [32:0] tk[0:LL][0:LP-1]; reg [IW-1:0] ti[0:LL][0:LP-1];
reg [31:0] tbits[0:LL][0:LP-1]; reg tvl[0:LL][0:LP-1];
wire [32:0] bk[0:LP-1]; wire [IW-1:0] bi[0:LP-1]; wire [31:0] bv_bits[0:LP-1];
wire [7:0] seen=iv;
genvar i; generate for(i=0;i<8;i=i+1) begin
 assign bk[i]=ik[33*i+:33]; assign bi[i]=ii[18*i+:18]; assign bv_bits[i]=ib[32*i+:32];
end endgenerate
assign result={tvl[LL][0],tk[LL][0],ti[LL][0],tbits[LL][0]};
    genvar tl, te;
    generate
        for (te = 0; te < LP; te = te + 1) begin : g_tree_capture
            always @(posedge clk) if (fin) begin
                tbits[0][te] <= bv_bits[te]; tk[0][te] <= bk[te];
                ti[0][te] <= bi[te]; tvl[0][te] <= seen[te];
            end
        end
        for (tl = 0; tl < LL; tl = tl + 1) begin : g_tree_level
            for (te = 0; te < (LP >> (tl + 1)); te = te + 1) begin : g_pair
                wire take_left = (tl == 0 && te == 0) ? 1'b0 : !tvl[tl][2*te+1] || (tvl[tl][2*te] &&
                    (tk[tl][2*te] > tk[tl][2*te+1] ||
                    (tk[tl][2*te] == tk[tl][2*te+1] && ti[tl][2*te] < ti[tl][2*te+1])));
                always @(posedge clk) begin
                    tbits[tl+1][te] <= take_left ? tbits[tl][2*te] : tbits[tl][2*te+1];
                    tk[tl+1][te] <= take_left ? tk[tl][2*te] : tk[tl][2*te+1];
                    ti[tl+1][te] <= take_left ? ti[tl][2*te] : ti[tl][2*te+1];
                    tvl[tl+1][te] <= take_left ? tvl[tl][2*te] : tvl[tl][2*te+1];
                end
            end
        end
    endgenerate
endmodule
