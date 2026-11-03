module writer_gold(input [7:0] sw_v,input [119:0] sw_addr,input [63:0] sw_mask,input [2047:0] sw_d,
 output [15:0] we,output[175:0] wa,output[511:0] wd,output collision);
 localparam N=16,NS=8,LWB=15,LN=4,RB=11,NLW=0,NL=1,AW=24,NROT=1,M=16,MUT_XBAR=0;
 wire[0:0]lw=0;wire[23:0]lwa=0;wire[31:0]lwd=0;
 wire s1_v=0;wire[14:0]s1_a=0;wire[31:0]s1_d=0;
 integer b;
 function automatic[3:0]cbank(input integer l,input integer k);cbank=0;endfunction
    reg  [N-1:0] b_we; reg [RB-1:0] b_wa [0:N-1]; reg [31:0] b_wd [0:N-1];
    reg  wcoll;
    always @* begin : wsel
        integer wl_, wj_, wk_, ws_; reg [LWB-1:0] sb; reg [LN-1:0] wb_; reg ok_;
        sb = {LWB{1'b0}}; wb_ = {LN{1'b0}}; ok_ = 1'b0;
        for (b = 0; b < N; b = b + 1) begin b_we[b] = 1'b0; b_wa[b] = {RB{1'b0}}; b_wd[b] = 32'd0; end
        wcoll = 1'b0;
        for (ws_ = 0; ws_ < NS; ws_ = ws_ + 1) if (sw_v[ws_])
            for (wj_ = 0; wj_ < 8; wj_ = wj_ + 1) if (sw_mask[ws_*8 + wj_]) begin
                sb = sw_addr[ws_*LWB +: LWB] + wj_;
                if (b_we[sb[LN-1:0]]) wcoll = 1'b1;           
                b_we[sb[LN-1:0]] = 1'b1; b_wa[sb[LN-1:0]] = sb[LWB-1:LN]; b_wd[sb[LN-1:0]] = sw_d[ws_*256 + 32*wj_ +: 32];
            end
        if (NLW > 0) begin
            if (|sw_v && |lw) wcoll = 1'b1;
            for (wl_ = 0; wl_ < NL; wl_ = wl_ + 1)
                if (lw[wl_]) begin
                    wb_ = lwa[wl_*AW +: LN]; ok_ = (wl_ == 0);
                    for (wk_ = 0; wk_ < NROT; wk_ = wk_ + 1) if (cbank(wl_, wk_) == wb_) ok_ = 1'b1;
                    if (!ok_) wcoll = 1'b1;
                     
                    if (b_we[wb_] && b_wa[wb_] != lwa[wl_*AW + LN +: RB]) wcoll = 1'b1;
                    if (!(|sw_v)) begin b_we[wb_] = 1'b1; b_wa[wb_] = lwa[wl_*AW + LN +: RB]; b_wd[wb_] = lwd[32*wl_ +: 32]; end
                end
        end
        if (s1_v) begin
            if (b_we[s1_a[LN-1:0]]) wcoll = 1'b1;
            b_we[s1_a[LN-1:0]] = 1'b1; b_wa[s1_a[LN-1:0]] = s1_a[LWB-1:LN]; b_wd[s1_a[LN-1:0]] = s1_d;
        end
    end
     
assign we=b_we;assign collision=wcoll;
 for(genvar i=0;i<16;i=i+1)begin assign wa[11*i+:11]=b_wa[i];assign wd[32*i+:32]=b_wd[i];end
 endmodule

module writer_regional(input [15:0] sw_v,input [239:0] sw_addr,input [127:0] sw_mask,input [4095:0] sw_d,
 output [15:0] we,output[175:0] wa,output[511:0] wd,output collision);
 localparam N=16,NS=8,LWB=15,LN=4,RB=11,NLW=0,NL=1,AW=24,NROT=1,M=16,MUT_XBAR=0;
 wire[0:0]lw=0;wire[23:0]lwa=0;wire[31:0]lwd=0;
 wire s1_v=0;wire[14:0]s1_a=0;wire[31:0]s1_d=0;
 integer b;
 function automatic[3:0]cbank(input integer l,input integer k);cbank=0;endfunction
    // Exact selected SOURCE13 StoreA specialization: NLW0 and s1_v0.
    // Each half receives its own already-captured same-edge source fields.
    initial if(N!=16 || M!=16 || LWB!=15 || AW!=24 || NS!=8 || NLW!=0 || MUT_XBAR!=0)
        $fatal(1,"regional writer requires exact selected StoreA parameters");
    wire [N-1:0] b_we;
    wire [RB-1:0] b_wa[0:N-1];
    wire [31:0] b_wd[0:N-1];
    wire [1:0] local_wcoll;
    wire wcoll=|local_wcoll;
    for(genvar region=0;region<2;region=region+1)begin:g_write_region
        reg collision;
        reg[7:0] rwe;
        reg[RB-1:0] rwa[0:7];
        reg[31:0] rwd[0:7];
        for(genvar bj=0;bj<8;bj=bj+1)begin
            assign b_we[(bj/2)*4+2*region+(bj%2)]=rwe[bj];
        end
        for(genvar bi=0;bi<8;bi=bi+1)begin
            assign b_wa[(bi/2)*4+2*region+(bi%2)]=rwa[bi];
            assign b_wd[(bi/2)*4+2*region+(bi%2)]=rwd[bi];
        end
        assign local_wcoll[region]=collision;
        always @* begin : wsel
            integer bb,ws,wj;
            reg [LWB-1:0] sb;
            sb=0; collision=0;
            for(bb=0;bb<8;bb=bb+1)begin
                rwe[bb]=0; rwa[bb]=0; rwd[bb]=0;
            end
            for(ws=0;ws<NS;ws=ws+1)if(sw_v[region*NS+ws])
                for(wj=0;wj<8;wj=wj+1)if(sw_mask[region*NS*8+ws*8+wj])begin
                    sb=sw_addr[region*NS*LWB+ws*LWB+:LWB]+wj;
                    if(sb[1]==region)begin
                        if(rwe[{sb[3:2],sb[0]}])collision=1;
                        rwe[{sb[3:2],sb[0]}]=1;
                        rwa[{sb[3:2],sb[0]}]=sb[LWB-1:LN];
                        rwd[{sb[3:2],sb[0]}]=sw_d[region*NS*256+ws*256+32*wj+:32];
                    end
                end
        end
    end
assign we=b_we;assign collision=wcoll;
 for(genvar i=0;i<16;i=i+1)begin assign wa[11*i+:11]=b_wa[i];assign wd[32*i+:32]=b_wd[i];end
 endmodule
