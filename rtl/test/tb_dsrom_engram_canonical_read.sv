`timescale 1ns/1ps
// Actual32-PC timing model on each stack, actual sector-count requests.
module tb_dsrom_engram_canonical_read #(parameter [71:0] INJECT=0)(input wire clk);
    localparam integer PCBASE=2929688;
    reg rst_n=0,hqv=0,hrr=0;
    reg [30:0] atom=0;reg [2:0] tag=0;
    wire hqr,hrv,ce,fault;
    wire [2:0] hrt;wire [3:0] hri;wire [255:0] hrd;
    reg aperture_valid=1;
    reg [1919:0] pc_base=0,pc_limit=0;
    wire [21823:0] rq;wire [17791:0] rd;
    wire [63:0] pv,pr;wire [255:0] pb;wire [1087:0] pt;wire [16383:0] pd;
    integer cycle=0,p,t,i,localatom,expected_pc,logical,requests=0,received=0,corrected=0,mode=0;
    reg [53:0] asked=0,seen=0;reg [3:0] lengths=0;
    reg [340:0] word;reg [29:0] address;
    function automatic [29:0] inverse(input integer pc,input integer a);
        integer hi,bank;
        begin hi=a>>2;bank=(pc^hi^(hi>>5))&31;inverse=(hi<<7)|(bank<<2)|(a&3);end
    endfunction
    function automatic [255:0] pattern(input [29:0] s);
        integer w;begin for(w=0;w<8;w=w+1) pattern[32*w+:32]=(s*32'd8+w)*32'h9e3779b1^32'h5bd1e995;end
    endfunction
    ot_dsrom_engram_rowstripe_read #(.CANONICAL(1),.APERTURE(1),.HISTORICAL_FLOP_ECC(INJECT!=0),.READ_INJECT(INJECT)) dut(
        .ck(clk),.rst_n(rst_n),.aperture_valid(aperture_valid),.pc_base(pc_base),.pc_limit(pc_limit),
        .hq_valid(hqv),.hq_ready(hqr),.hq_atom(atom),.hq_len(4'd9),.hq_tag(tag),.rq(rq),.rd(rd),
        .hr_valid(hrv),.hr_ready(hrr),.hr_tag(hrt),.hr_idx(hri),.hr_data(hrd),.ce(ce),.fault(fault));
    genvar stack,j;
    generate for(stack=0;stack<2;stack=stack+1) begin:g_stack
        wire [31:0] v,we;wire [959:0] addr;wire [127:0] len;wire [543:0] tags;
        wire [8191:0] data;wire [1023:0] strb;
        for(j=0;j<32;j=j+1) begin:g_pc
            assign {data[j*256+:256],strb[j*32+:32],tags[j*17+:17],len[j*4+:4],addr[j*30+:30],we[j],v[j]}=rq[(stack*32+j)*341+:341];
            assign rd[stack*8896+j*256+:256]=pd[(stack*32+j)*256+:256];
            assign rd[stack*8896+8192+j*17+:17]=pt[(stack*32+j)*17+:17] ^ ((mode==1 && stack==0 && j==0) ? 17'd32 : 0);
            assign rd[stack*8896+8736+j*4+:4]=pb[(stack*32+j)*4+:4];
            assign rd[stack*8896+8864+j]=pv[stack*32+j];
        end
        ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.CLK_PS(833),.MEM_MODE(1),.MEM_WORDS(1)) phy(
            .clk(clk),.rst_n(rst_n),.req_v(v),.req_rdy(pr[stack*32+:32]),.req_addr(addr),.req_len(len),.req_tag(tags),
            .req_we(we),.req_wdata(data),.req_wstrb(strb),.wr_done(),.rsp_v(pv[stack*32+:32]),.rsp_rdy(32'hffffffff),
            .rsp_tag(pt[stack*32*17+:32*17]),.rsp_beat(pb[stack*32*4+:32*4]),.rsp_data(pd[stack*32*256+:32*256]));
    end endgenerate
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        for(p=0;p<64;p=p+1) begin pc_base[p*30+:30]=PCBASE;pc_limit[p*30+:30]=PCBASE+100;end
        if(mode==2) pc_limit[0+:30]=PCBASE+8;
        if(mode==3) pc_limit[0+:30]=19775389;
        if(mode==4) aperture_valid=0;
    end
    always @(posedge clk) begin
        cycle=cycle+1;rst_n<=cycle>=10;hqv<=0;
        if(cycle>=20 && cycle<32 && cycle%2==0) begin
            t=(cycle-20)/2;atom<=(64*t+t)*9;tag<=t;hqv<=1;
        end
        hrr<=cycle>100 && cycle%7>=3;
        if(rst_n) begin
            if(mode!=0 && fault) begin
                $display("ENGRAM_CANONICAL_READ NEG mode=%0d caught",mode);$finish;
            end
            if(INJECT==5 && fault) begin
                if(received!=0) $fatal(1,"uncorrectable payload escaped");
                $display("ENGRAM_CANONICAL_READ ECC double caught");$finish;
            end
            if(mode==0 && INJECT!=5 && fault) $fatal(1,"canonical read unexpected fault");
            if(cycle>20000) $fatal(1,"canonical read drain");
            if(ce) corrected=corrected+1;
            for(p=0;p<64;p=p+1) begin
                word=rq[p*341+:341];
                if(word[0]) begin
                    t=word[40:38];address=word[31:2];
                    if(!pr[p] || t>=6 || word[1]!=0 || word[35:32]<1 || word[35:32]>4) $fatal(1,"canonical request shape/credit");
                    lengths[word[35:32]-1]=1;
                    expected_pc=(t%2)*32+t/2;
                    if(p!=expected_pc) $fatal(1,"canonical reserved PC identity");
                    for(i=0;i<word[35:32];i=i+1) begin
                        if((((address+i)>>2)^((address+i)>>7)^((address+i)>>12))%32!=p%32) $fatal(1,"actual pc_of per beat");
                        localatom=((address+i)>>7)*4+((address+i)&3);
                        logical=localatom-PCBASE-t*9;
                        if(logical<0 || logical>=9 || asked[t*9+logical]) $fatal(1,"canonical burst edge/duplicate");
                        asked[t*9+logical]=1;
                    end
                    requests=requests+1;
                end
            end
            if(hrv && hrr) begin
                p=(hrt%2)*32+hrt/2;address=inverse(p%32,PCBASE+hrt*9+hri);
                if(hrt>=6 || hri>=9 || seen[hrt*9+hri] || hrd!==pattern(address)) $fatal(1,"actual PHY pattern payload identity");
                seen[hrt*9+hri]=1;received=received+1;
            end
            if(received==54 && cycle%16==0) begin
                if(requests!=18 || asked!={54{1'b1}} || seen!={54{1'b1}} || lengths!=15 || (INJECT!=0 && corrected!=54)) $fatal(1,"canonical fullshape exact/count/ECC");
                $display("ENGRAM_CANONICAL_READ PASS rows=6 requests=18 atoms=54 lengths=1:4 actual_PHY=1 inject=%0d cycles=%0d",INJECT,cycle);$finish;
            end
        end
    end
endmodule
