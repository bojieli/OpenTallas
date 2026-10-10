`timescale 1ns/1ps
module tb_dsrom_engram_canonical_boot(input wire clk);
    localparam integer PCBASE=2929688;
    reg rst_n=0,iv=0,valid=1;reg [31:0] addr=0;reg [255:0] data=0;
    reg [1919:0] pc_base=0,pc_limit=0;
    wire credit,ready,fault;wire [21823:0] rq;wire [63:0] wd,pr;
    integer cycle=0,credits=8,sent=0,writes=0,completed=0,p,n,row,index,localatom,pc,stack,globalatom,mode=0;
    reg marker=0;reg [575:0] seen=0;reg [340:0] word;
    function automatic integer inverse(input integer p,input integer a);
        integer t,bank;
        begin t=a>>2;bank=(p^t^(t>>5))&31;inverse=(t<<7)|(bank<<2)|(a&3);end
    endfunction
    ot_dsrom_engram_boot_path #(.ROWSTRIPE(1),.CANONICAL(1),.APERTURE(1),.EXPECT_SECTORS(576)) dut(
        .ck(clk),.rst_n(rst_n),.aperture_valid(valid),.pc_base(pc_base),.pc_limit(pc_limit),
        .i_v(iv),.i_addr(addr),.i_d(data),.i_cred(credit),.rq(rq),.wd(wd),.ready(ready),.fault(fault));
    genvar st,j;
    generate for(st=0;st<2;st=st+1) begin:g_stack
        wire [31:0] v,we;wire [959:0] a;wire [127:0] len;wire [543:0] tags;wire [8191:0] d;wire [1023:0] strb;
        for(j=0;j<32;j=j+1) begin:g_pc
            assign {d[j*256+:256],strb[j*32+:32],tags[j*17+:17],len[j*4+:4],a[j*30+:30],we[j],v[j]}=rq[(st*32+j)*341+:341];
        end
        ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.CLK_PS(833),.MEM_MODE(0),.MEM_WORDS(1024)) phy(
            .clk(clk),.rst_n(rst_n),.req_v(v),.req_rdy(pr[st*32+:32]),.req_addr(a),.req_len(len),.req_tag(tags),
            .req_we(we),.req_wdata(d),.req_wstrb(strb),.wr_done(wd[st*32+:32]),.rsp_v(),.rsp_rdy(32'hffffffff),.rsp_tag(),.rsp_beat(),.rsp_data());
    end endgenerate
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        for(p=0;p<64;p=p+1) begin pc_base[p*30+:30]=PCBASE;pc_limit[p*30+:30]=PCBASE+9;end
        if(mode==1) pc_limit[0+:30]=PCBASE+8;
    end
    always @(posedge clk) begin
        cycle=cycle+1;rst_n<=cycle>=10;iv<=0;
        if(rst_n) begin
            credits=credits+credit-iv;
            if(cycle>=20 && credits>0 && !marker) begin
                iv<=1;
                if(sent<576) begin addr<=32'hc0000000+sent;data<=sent;sent=sent+1;end
                else begin addr<=32'hffffffff;data<={190'd0,2'b11,32'd0,32'd576};marker=1;end
            end
            if(mode==1 && fault) begin $display("ENGRAM_CANONICAL_BOOT NEG exclusive end caught");$finish;end
            if(mode==2 && cycle>1000) begin
                if(ready || completed!=0) $fatal(1,"zero-count mutation did not lose completion");
                $display("ENGRAM_CANONICAL_BOOT NEG zero-count noops caught");$finish;
            end
            if(mode!=1 && fault) $fatal(1,"canonical boot unexpected fault");
            if(cycle>50000) $fatal(1,"canonical boot drain");
            for(p=0;p<64;p=p+1) begin
                if(wd[p]) completed=completed+1;
                word=rq[p*341+:341];
                if(word[0]) begin
                    n=word[116:85];row=n/9;index=n%9;
                    pc=(row%2)*32+(row/2)%32;globalatom=inverse(p%32,PCBASE+index);
                    if(!pr[p] || word[1]!=1 || word[35:32]!=(mode==2 ? 0 : 1) || n>=576 || seen[n] || p!=pc || word[31:2]!=globalatom) $fatal(1,"canonical boot actual request/count/PC");
                    seen[n]=1;writes=writes+1;
                end
            end
            if(ready) begin
                if(writes!=576 || completed!=576 || seen!={576{1'b1}}) $fatal(1,"marker before actual write completion");
                for(n=0;n<576;n=n+1) begin
                    row=n/9;index=n%9;stack=row%2;pc=(row/2)%32;globalatom=inverse(pc,PCBASE+index);
                    // This minimum first-row-perPC image has no aliases in
                    // the model's1024-sector backing array; all576 sectors
                    // remain distinct within their two separate stacks.
                    if(stack==0) begin
                        if(g_stack[0].phy.mem[globalatom%1024]!==n) $fatal(1,"SW backing payload mismatch");
                    end else if(g_stack[1].phy.mem[globalatom%1024]!==n) $fatal(1,"SE backing payload mismatch");
                end
                $display("ENGRAM_CANONICAL_BOOT PASS sectors=576 PCs=64 actual_wd=576 actual_PHY=1 marker=1 cycles=%0d",cycle);$finish;
            end
        end
    end
endmodule
