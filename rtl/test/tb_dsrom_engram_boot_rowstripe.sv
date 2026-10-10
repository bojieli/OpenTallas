`timescale 1ns/1ps
module tb_dsrom_engram_boot_rowstripe;
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,iv=0;
    reg [31:0] addr=0;
    reg [255:0] data=0;
    wire credit,ready,fault;
    wire [64*341-1:0] rq;
    reg [63:0] wd=0;
    integer timer[0:63];
    integer p,n,credits=8,sent=0,writes=0,ticks=0;
    integer logical_atom,row,index,expected_pc,expected_atom;
    reg [575:0] seen=0;
    reg [340:0] word;
    ot_dsrom_engram_boot_path #(.ROWSTRIPE(1),.EXPECT_SECTORS(576)) dut(
        .ck(ck),.rst_n(rst_n),.i_v(iv),.i_addr(addr),.i_d(data),.i_cred(credit),
        .rq(rq),.wd(wd),.ready(ready),.fault(fault));
    always @(posedge ck) if(rst_n) begin
        if(credit) credits=credits+1;
        if(iv) begin credits=credits-1;if(addr!=32'hffffffff) sent=sent+1;end
    end
    always @(negedge ck) if(rst_n) begin
        wd=0;ticks=ticks+1;
        for(p=0;p<64;p=p+1) begin
            if(timer[p]>0) begin
                timer[p]=timer[p]-1;
                if(timer[p]==0) wd[p]=1;
            end
            word=rq[p*341+:341];
            if(word[0]) begin
                logical_atom=word[116:85];row=logical_atom/9;index=logical_atom%9;
                expected_pc=((row%2)*32)+((row/2)%32);
                expected_atom=(row/64)*9+index;
                if(p!=expected_pc || word[31:2]!=expected_atom) $fatal(1,"rowstripe PC/address identity");
                if(word[1]!=1 || word[35:32]!=0 || word[84:53]!=32'hffffffff) $fatal(1,"controller write packing");
                if(logical_atom>=576 || seen[logical_atom]) $fatal(1,"duplicate logical atom");
                if(timer[p]!=0) $fatal(1,"PC request reused before completion");
                seen[logical_atom]=1;writes=writes+1;
                timer[p]=p%3+4+(p==15 ? 25 : 0);
            end
        end
        if(fault) $fatal(1,"unexpected rowstripe fault");
        if(ticks>10000) $fatal(1,"rowstripe boot drain");
    end
    initial begin
        for(p=0;p<64;p=p+1) timer[p]=0;
        repeat(4) @(posedge ck);#1;rst_n=1;
        for(n=0;n<576;n=n+1) begin
            @(posedge ck);#1;
            iv=0;
            while(credits==0) begin @(posedge ck);#1;end
            iv=1;addr=32'hc0000000+n;data=n;
        end
        @(posedge ck);#1;iv=0;
        @(posedge ck);#1;iv=1;addr=32'hffffffff;data={190'd0,2'b11,32'd0,32'd576};
        @(posedge ck);#1;iv=0;
        wait(ready);repeat(3) @(posedge ck);
        if(writes!=576 || seen!={576{1'b1}} || credits!=8) $fatal(1,"publication before exact completion");
        $display("ENGRAM_ROWSTRIPE_BOOT PASS atoms=576 rows=64 PCs=64 exact=1 stalls=1 completion=1");$finish;
    end
endmodule
