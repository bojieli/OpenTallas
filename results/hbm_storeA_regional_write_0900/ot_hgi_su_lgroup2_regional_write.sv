module ot_hgi_su_lgroup2_regional_write #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24,
    parameter integer NLW = 0,              
    parameter integer MACRO = 1,
    parameter integer MUT_XBAR = 0,         
    parameter integer LAT = 0,              
    parameter integer NS = 1                
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      rq,                     
    input  wire [N-1:0]      rr,                     
    input  wire [N*AW-1:0]   ra,
    output wire [N*32-1:0]   rd,
    input  wire [NS-1:0]     sr_v,                   
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_d,
    output wire [NS-1:0]     sr_rv,                  
    input  wire [2*NS-1:0]     sw_v,                   
    input  wire [2*NS*LWB-1:0] sw_addr,
    input  wire [2*NS*8-1:0]   sw_mask,
    input  wire [2*NS*256-1:0] sw_d,
    output reg               flt
);
    localparam integer LN = $clog2(N), RB = LWB - LN, NROT = N / M, NHALF = (2 * N) / M, HM = (M / 2 > 0) ? M / 2 : 1;
    localparam integer NCAND = 2 * NROT + NHALF;
    localparam integer NL = (NLW > 0) ? NLW : 1;
     
    function automatic [LN-1:0] cbank(input integer l, input integer k);
        integer j;
        if (k < NROT) cbank = (l + k * M) % N;
        else if (k < 2 * NROT) begin j = k - NROT; cbank = ((l ^ 1) + j * M) % N; end
        else begin j = k - 2 * NROT; cbank = ((l >> 1) + j * HM) % N; end
    endfunction
     
    reg  [N-1:0]  b_re; reg [RB-1:0] b_ra [0:N-1];
    wire [31:0]   b_rd [0:N-1];
    reg  [N-1:0]  lok;                                
    integer b, l, k;
    reg src;                                          
    always @* begin : rsel
        integer rj_, sl_; reg [LWB-1:0] sa; reg [LN-1:0] bl;
        sa = {LWB{1'b0}}; bl = {LN{1'b0}};
        for (b = 0; b < N; b = b + 1) begin b_re[b] = 1'b0; b_ra[b] = {RB{1'b0}}; end
        for (l = 0; l < N; l = l + 1) begin
            bl = ra[l*AW +: LN]; lok[l] = (l == 0);
            for (k = 0; k < NCAND; k = k + 1) if (cbank(l, k) == bl) lok[l] = 1'b1;
        end
        src = 1'b0;
        if (|sr_v) begin
             
            for (sl_ = 0; sl_ < NS; sl_ = sl_ + 1) if (sr_v[sl_])
                for (rj_ = 0; rj_ < 8; rj_ = rj_ + 1) begin
                    sa = sr_addr[sl_*LWB +: LWB] + rj_;
                    if (b_re[sa[LN-1:0]] && b_ra[sa[LN-1:0]] != sa[LWB-1:LN]) src = 1'b1;
                    b_re[sa[LN-1:0]] = 1'b1; b_ra[sa[LN-1:0]] = sa[LWB-1:LN];
                end
        end else begin
             
            for (l = N - 1; l >= 0; l = l - 1)
                if (rr[l] && lok[l]) begin
                    bl = ra[l*AW +: LN]; b_re[bl] = 1'b1; b_ra[bl] = ra[l*AW + LN +: RB];
                end
        end
    end
    reg [LN-1:0] lb_q [0:N-1]; reg [LN-1:0] sr_lo [0:NS-1];
    reg [LN-1:0] lb_q2 [0:N-1]; reg [LN-1:0] sr_lo2 [0:NS-1]; reg [NS-1:0] srv1, srv2;
    integer s_;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) if (rr[l]) lb_q[l] <= ra[l*AW +: LN];
        for (s_ = 0; s_ < NS; s_ = s_ + 1) begin if (sr_v[s_]) sr_lo[s_] <= sr_addr[s_*LWB +: LN]; sr_lo2[s_] <= sr_lo[s_]; end
        for (l = 0; l < N; l = l + 1) lb_q2[l] <= lb_q[l];
        srv2 <= srv1;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) srv1 <= {NS{1'b0}}; else srv1 <= sr_v;
     
     
    assign sr_rv = (LAT == 1) ? srv2 : (LAT == 2) ? sr_v : srv1;
    wire [LN-1:0] lb_s [0:N-1];
    for (genvar gs_ = 0; gs_ < N; gs_ = gs_ + 1) begin : g_ls
        assign lb_s[gs_] = (LAT == 1) ? lb_q2[gs_] : (LAT == 2) ? ra[gs_*AW +: LN] : lb_q[gs_];
    end
     
    genvar gl, gj, gk;
    for (gl = 0; gl < N; gl = gl + 1) begin : g_rd
        if (gl == 0) begin : g_any
            wire [LN-1:0] bs = lb_s[gl] + MUT_XBAR[LN-1:0];
            assign rd[0 +: 32] = b_rd[bs];
        end else begin : g_c
            reg [31:0] dv;
            always @* begin : mx
                integer kk;
                dv = 32'd0;
                for (kk = NCAND - 1; kk >= 0; kk = kk - 1)
                    if (lb_s[gl] == cbank(gl, kk)) dv = b_rd[(cbank(gl, kk) + MUT_XBAR) % N];
            end
            assign rd[32*gl +: 32] = dv;
        end
    end
    for (gk = 0; gk < NS; gk = gk + 1) begin : g_srl
        wire [LN-1:0] sr_s = (LAT == 1) ? sr_lo2[gk] : (LAT == 2) ? sr_addr[gk*LWB +: LN] : sr_lo[gk];
        for (gj = 0; gj < 8; gj = gj + 1) begin : g_sr
            wire [LN-1:0] bj = sr_s + gj;
            assign sr_d[256*gk + 32*gj +: 32] = b_rd[bj];
        end
    end
     
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
    reg [N-1:0] rq_q, lok_q; reg [RB-1:0] lr_q [0:N-1]; reg [RB-1:0] br_q [0:N-1]; reg srv_q, wcoll_q;
    always @(posedge clk) begin
        rq_q <= (|sr_v) ? {N{1'b0}} : rq; lok_q <= lok; srv_q <= ((|sr_v) && |rq) || src; wcoll_q <= wcoll;
        for (l = 0; l < N; l = l + 1) lr_q[l] <= ra[l*AW + LN +: RB];
        for (b = 0; b < N; b = b + 1) br_q[b] <= b_ra[b];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else begin
            if (srv_q || wcoll_q) flt <= 1'b1;
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]])) flt <= 1'b1;
 
              
              
                       
                       
                       
                              


        end
    end
    genvar gb;
    for (gb = 0; gb < N; gb = gb + 1) begin : g_bank
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
    end
endmodule
