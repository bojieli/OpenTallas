`timescale 1ns/1ps
module tb_dsrom_engram_rowstripe_service;
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,hqv=0;
    reg [30:0] atom=0;reg [2:0] tag=0;
    wire credit,hrv,fault;wire [2:0] hrt;wire [3:0] hri;wire [255:0] hrd;
    wire [64*341-1:0] rq;reg [2*8896-1:0] rd=0;
    integer requests=0,credits=0,received=0,n,cycles=0,pending=-1,waitcycles=0,idx=0,mode=0;
    reg [53:0] seen=0;reg [16:0] identity;
    reg [340:0] word;
    ot_dsrom_engram_rowstripe_service dut(.ck(ck),.rst_n(rst_n),.hq_v(hqv),.hq_atom(atom),.hq_tag(tag),.hq_cred(credit),
        .rq(rq),.rd(rd),.hr_v(hrv),.hr_tag(hrt),.hr_idx(hri),.hr_d(hrd),.fault(fault));
    always @(negedge ck) if(rst_n && mode==0) begin
        cycles=cycles+1;if(cycles>1000) $fatal(1,"credit service drain");
        rd=0;word=rq[0+:341];
        if(word[0]) begin
            if(pending!=-1 || word[1]!=0 || word[35:32]!=8 || word[31:2]!=(word[38:36]+1)*9) $fatal(1,"samePC request reservation");
            pending=word[38:36];identity=word[52:36];idx=0;waitcycles=15;requests=requests+1;
        end
        if(pending>=0) begin
            if(waitcycles>0) waitcycles=waitcycles-1;
            else begin
                rd[0+:256]=pending*100+idx;rd[8192+:17]=identity;rd[8736+:4]=idx;rd[8864]=1;
                idx=idx+1;if(idx==9) pending=-1;
            end
        end
    end
    always @(posedge ck) if(rst_n) begin
        if(credit) credits=credits+1;
        if(hrv) begin
            if(hrt>=6 || hri>=9 || seen[hrt*9+hri] || hrd!==hrt*100+hri) $fatal(1,"credit service payload/tag");
            seen[hrt*9+hri]=1;received=received+1;
        end
    end
    initial begin
        if($value$plusargs("MODE=%d",mode)) begin end
        repeat(4) @(posedge ck);#1;rst_n=1;
        for(n=0;n<(mode==0 ? 6 : 10);n=n+1) begin
            @(posedge ck);#1;hqv=1;tag=n%6;atom=(64+64*(n%6))*9;
        end
        @(posedge ck);#1;hqv=0;
        if(mode!=0) begin
            repeat(20) @(posedge ck);
            if(!fault) $fatal(1,"overcredit producer not rejected");
            $display("ENGRAM_SERVICE NEG overcredit caught");$finish;
        end
        wait(received==54);repeat(8) @(posedge ck);
        if(fault || requests!=6 || credits!=6 || seen!={54{1'b1}}) $fatal(1,"finite service credit completion");
        $display("ENGRAM_SERVICE PASS queued=6 same_pc=1 atoms=54 credit=6 delayed=1");$finish;
    end
endmodule
