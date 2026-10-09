`timescale 1ns/1ps
module tb_dsrom_engram_rowstripe_read;
    parameter [71:0] INJECT=0;
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,hqv=0,hrr=0;
    wire hqr,hrv,ce,fault;
    reg [30:0] atom=0;reg [2:0] tag=0;
    wire [2:0] hrt;wire [3:0] hri;wire [255:0] hrd;
    wire [64*341-1:0] rq;reg [2*8896-1:0] rd=0;
    integer pcs[0:5];reg [16:0] ids[0:5];
    integer t,p,n,idx,base,localpc,cycles=0,received=0,requests=0,mode=0;
    reg [53:0] seen=0;
    reg [340:0] word;
    ot_dsrom_engram_rowstripe_read #(.HISTORICAL_FLOP_ECC(INJECT!=0),.READ_INJECT(INJECT)) dut(.ck(ck),.rst_n(rst_n),
        .hq_valid(hqv),.hq_ready(hqr),.hq_atom(atom),.hq_len(4'd9),.hq_tag(tag),
        .rq(rq),.rd(rd),.hr_valid(hrv),.hr_ready(hrr),.hr_tag(hrt),.hr_idx(hri),.hr_data(hrd),.ce(ce),.fault(fault));
    always @(negedge ck) if(rst_n) begin
        cycles=cycles+1;
        if(cycles>1000) $fatal(1,"read adapter drain");
        for(p=0;p<64;p=p+1) begin
            word=rq[p*341+:341];
            if(word[0]) begin
                t=word[38:36];
                if(t>=6 || word[1]!=0 || word[35:32]!=8 || word[31:2]!=9) $fatal(1,"read rq shape");
                if(p!=(t%2)*32+(t/2)) $fatal(1,"read PC identity");
                pcs[t]=p;ids[t]=word[52:36];requests=requests+1;
            end
        end
    end
    always @(posedge ck) if(rst_n && hrv && hrr) begin
        if(hrt>=6 || hri>=9 || seen[hrt*9+hri]) $fatal(1,"read output identity");
        if(hrd!==hrt*100+hri) $fatal(1,"read payload wrong");
        seen[hrt*9+hri]=1;received=received+1;
    end
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        repeat(4) @(posedge ck);#1;rst_n=1;
        for(n=0;n<6;n=n+1) begin
            @(posedge ck);#1;atom=(64+n)*9;tag=n;hqv=0;#1;
            while(!hqr) begin @(posedge ck);#1;end
            hqv=1;@(posedge ck);#1;hqv=0;
        end
        repeat(5) @(posedge ck);
        if(requests!=6) $fatal(1,"missing reserved requests");
        // Six simultaneous streams, permuted atom order, stalled consumer.
        for(n=0;n<9;n=n+1) begin
            @(posedge ck);#1;rd=0;idx=(n*5)%9;
            for(t=0;t<6;t=t+1) begin
                p=pcs[t];
                if(mode==2 && n==0 && t==0) p=15;
                base=(p/32)*8896;localpc=p%32;
                rd[base+localpc*256+:256]=t*100+idx;
                rd[base+8192+localpc*17+:17]=ids[t]^(mode==1 && n==0 && t==0 ? 17'd8 : 0);
                rd[base+8736+localpc*4+:4]=(mode==3 && n==1 && t==0) ? 0 : idx;
                rd[base+8864+localpc]=1;
            end
        end
        @(posedge ck);#1;rd=0;
        repeat(10) @(posedge ck);
        if(mode!=0) begin
            if(!fault) $fatal(1,"invalid return identity not rejected");
            $display("ENGRAM_READ NEG mode=%0d caught",mode);$finish;
        end
        if(INJECT==3) begin
            if(!fault || received!=0) $fatal(1,"double error not rejected");
            $display("ENGRAM_READ ECC double caught");$finish;
        end
        if(fault || received!=0) $fatal(1,"consumer stall lost reservation");
        for(n=0;n<120;n=n+1) begin
            @(posedge ck);#1;hrr=(n%7>=3);
        end
        @(posedge ck);#1;hrr=0;
        if(received!=54 || seen!={54{1'b1}} || fault) $fatal(1,"read exact drain failure");
        $display("ENGRAM_READ PASS rows=6 atoms=54 concurrent_returns=6 stalled=1 inject=%0d",INJECT);$finish;
    end
endmodule
